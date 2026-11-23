import hashlib
import re
from typing import Any

from langchain_core.documents import Document

from cidan.ingestion.pdf_loader import detect_clauses_with_hierarchy, normalize_clause_id


def _split_long_text(text: str, max_size: int) -> list[str]:
    """Split text exceeding max_size cleanly at sub-clauses or sentence boundaries."""
    if len(text) <= max_size:
        return [text]

    # Try splitting at subclauses first
    subclause_splits = re.split(r"(?=\n\s*(?:\([a-z]\)|\([ivxlcdm]+\))\s*)", text)
    if len(subclause_splits) > 1 and all(len(s) <= max_size for s in subclause_splits):
        return [s.strip() for s in subclause_splits if s.strip()]

    # Otherwise split at sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current: list[str] = []
    current_len = 0
    for sent in sentences:
        if current_len + len(sent) + 1 > max_size and current:
            chunks.append(" ".join(current))
            current = [sent]
            current_len = len(sent)
        else:
            current.append(sent)
            current_len += len(sent) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def split_documents(
    pages: list[Document], chunk_size: int = 1000, chunk_overlap: int = 150
) -> list[Document]:
    """Build structure-aware chunks:

    - One chunk per table row (with column names attached).
    - One chunk per top-level clause including sub-clauses, qualifiers ('Provided that', 'Except', 'Notwithstanding').
    - Only split when clause exceeds chunk_size, splitting at sub-clause or sentence boundaries.
    - Metadata: clause_ids (all), parent_clause_id, page_start, page_end, source_char_start/end,
      chunk_kind, context_before, context_after, and short stable chunk IDs ({doc_hash8}-p{page}-c{index}).
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")

    raw_units: list[tuple[str, str, int, int, int, list[str], str | None, dict[str, Any]]] = []

    for page in pages:
        content = page.page_content
        page_num = int(page.metadata.get("page", 1))
        doc_id = str(page.metadata.get("document_id", "doc"))[:8]

        # Scan clauses on page
        hierarchy = detect_clauses_with_hierarchy(content)
        clause_map = {item["clause_id"]: item for item in hierarchy}

        # Divide content into blocks: table rows vs text paragraphs/clauses
        lines = content.split("\n")
        idx = 0
        current_block: list[str] = []
        current_block_start = 0

        while idx < len(lines):
            line = lines[idx]
            # Table row is a self-contained unit
            if line.startswith("[TABLE ") and " ROW " in line:
                if current_block:
                    block_text = "\n".join(current_block).strip()
                    if block_text:
                        raw_units.append((
                            block_text,
                            "clause" if bool(re.search(r"\bClause|\bArticle|\b\d+\.\d+", block_text)) else "paragraph",
                            page_num,
                            current_block_start,
                            current_block_start + len(block_text),
                            [c for c in clause_map if c in block_text],
                            None,
                            dict(page.metadata),
                        ))
                    current_block = []
                # Add table row unit
                row_start = content.find(line, current_block_start)
                row_end = row_start + len(line) if row_start >= 0 else 0
                row_clauses = [c for c in clause_map if c in line]
                raw_units.append((
                    line,
                    "table_row",
                    page_num,
                    row_start,
                    row_end,
                    row_clauses,
                    None,
                    dict(page.metadata),
                ))
                current_block_start = row_end
                idx += 1
                continue

            # Check if this line starts a new top-level clause
            is_new_clause = bool(re.match(
                r"^(?:(?:Clause|Section|Article|Para(?:graph)?)\s*[0-9]+(?:\.[0-9]+)*)|(?:^[0-9]+\.[0-9]+(?:\.[0-9]+)*\b)",
                line.strip(),
                re.IGNORECASE,
            ))
            # Keep qualifying sentences with parent clause
            is_qualifier = bool(re.match(
                r"^(?:Provided\s+that|Except\s+that|Notwithstanding|Subject\s+to|Where|In\s+case)\b",
                line.strip(),
                re.IGNORECASE,
            ))

            if is_new_clause and not is_qualifier and current_block:
                block_text = "\n".join(current_block).strip()
                if block_text:
                    raw_units.append((
                        block_text,
                        "clause",
                        page_num,
                        current_block_start,
                        current_block_start + len(block_text),
                        [c for c in clause_map if c in block_text],
                        None,
                        dict(page.metadata),
                    ))
                current_block = [line]
                current_block_start = content.find(line, current_block_start)
            else:
                current_block.append(line)
            idx += 1

        if current_block:
            block_text = "\n".join(current_block).strip()
            if block_text:
                raw_units.append((
                    block_text,
                    "clause" if bool(re.search(r"\bClause|\bArticle|\b\d+\.\d+", block_text)) else "paragraph",
                    page_num,
                    current_block_start,
                    current_block_start + len(block_text),
                    [c for c in clause_map if c in block_text],
                    None,
                    dict(page.metadata),
                ))

    # Split oversized units & generate chunks
    chunks: list[Document] = []
    chunk_index = 1

    for text, kind, page_num, start_char, end_char, cids, parent_cid, meta in raw_units:
        doc_id8 = str(meta.get("document_id", "doc"))[:8]
        pieces = _split_long_text(text, chunk_size) if (kind != "table_row" and len(text) > chunk_size) else [text]

        for p_idx, piece in enumerate(pieces):
            cid_str = f"{doc_id8}-p{page_num}-c{chunk_index}"
            chunk_index += 1

            # Match clauses inside this piece
            piece_cids = [c for c in cids if c in piece]
            raw_primary = piece_cids[0] if piece_cids else (cids[0] if cids else "not_specified")
            primary_cid = normalize_clause_id(raw_primary)
            norm_cids = [normalize_clause_id(c) for c in (piece_cids or cids)]

            chunk_meta = dict(meta)
            chunk_meta.update({
                "chunk_id": cid_str,
                "clause_id": primary_cid,
                "clause_ids": norm_cids,
                "parent_clause_id": parent_cid,
                "chunk_kind": kind,
                "page_start": page_num,
                "page_end": page_num,
                "source_char_start": start_char,
                "source_char_end": end_char,
                "has_table_content": kind == "table_row" or "[TABLE" in piece,
            })
            chunks.append(Document(page_content=piece, metadata=chunk_meta))

    # Second pass: attach neighbouring context (context_before / context_after)
    for i, chunk in enumerate(chunks):
        before = chunks[i - 1].page_content if i > 0 else ""
        after = chunks[i + 1].page_content if i < len(chunks) - 1 else ""
        chunk.metadata["context_before"] = before
        chunk.metadata["context_after"] = after
        chunk.metadata["surrounding_context"] = (
            (before + "\n\n" if before else "")
            + chunk.page_content
            + ("\n\n" + after if after else "")
        )

    return chunks
