import hashlib
import json
import logging
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymupdf
from langchain_core.documents import Document

from cidan.config import ROOT, Settings, get_settings
from cidan.ingestion.document_classifier import DocumentClassifier

logger = logging.getLogger(__name__)


def find_pdfs(settings: Settings | None = None) -> list[Path]:
    active = settings or get_settings()
    candidates = [active.source_pdf_directory, ROOT / "data", ROOT / "cidan" / "data", ROOT]
    for directory in candidates:
        if directory.is_dir():
            found = {
                str(path.resolve()).casefold(): path.resolve()
                for path in directory.glob("*.pdf")
            }
            if found:
                return sorted(found.values(), key=lambda path: path.name.casefold())
    return []


def classify_document(path: Path, sample_text: str = "") -> str:
    """Classifies a document based on name and content signals with content-first scoring."""
    res = DocumentClassifier.classify_text_and_name(path.name, sample_text)
    return str(res["document_type"])


def normalize_clause_id(cid: str) -> str:
    """Standardizes clause identifiers so 'Clause 2.1', 'clause 2.1', '2.1', '2.1 Eligibility' all normalize to '2.1'."""
    if not cid:
        return "not_specified"
    cid = str(cid).strip()
    m = re.match(r"^(?:(?:Clause|Section|Para(?:graph)?)\s*(?:=|:|\s)\s*)?([0-9]+(?:\.[0-9]+)*)(?:[\s:].*)?$", cid, re.IGNORECASE)
    if m:
        return m.group(1)
    return cid


def detect_clause_ids(text: str) -> list[str]:
    """Identify clause and subclause numbers (e.g., 2.1, 2.5, Clause 3.2)."""
    hierarchy = detect_clauses_with_hierarchy(text)
    return [normalize_clause_id(item["clause_id"]) for item in hierarchy]


def detect_clauses_with_hierarchy(text: str) -> list[dict[str, Any]]:
    """Detect clauses including complex forms (e.g., 2.1, 2.1.3, (a), (i), Clause 4, Article 5(2), Annex A)

    and compute parent/child hierarchy.
    """
    patterns = [
        (r"\b(?:Clause|Section|Para(?:graph)?)\s*(?:=|:|\s)\s*([0-9]+(?:\.[0-9]+)*)\b", "clause", False),
        (r"\bArticle\s*(?:=|:|\s)?\s*([0-9]+(?:\([0-9a-zA-Z]+\))*)(?=[.,;:\s]|$)", "article", True),
        (r"\bAnnex(?:ure)?\s*(?:=|:|\s)?\s*([A-Za-z0-9]+)\b", "annex", True),
        (r"(?:^|\n)\s*([0-9]+\.[0-9]+(?:\.[0-9]+)*)\b", "numbered", False),
        (r"(?:^|\n)\s*(\([a-z]\))(?=\s|$)", "alpha_subclause", False),
        (r"(?:^|\n)\s*(\([ivxlcdm]+\))(?=\s|$)", "roman_subclause", False),
    ]

    found_matches: list[tuple[int, str, str, str]] = []  # (start_pos, clause_id, full_match, kind)
    for pattern, kind, keep_prefix in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            full = m.group(0).strip()
            cid = full if keep_prefix else m.group(1).strip()
            found_matches.append((m.start(), normalize_clause_id(cid), full, kind))

    # Sort matches by appearance in text
    found_matches.sort(key=lambda x: x[0])

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_matches: list[tuple[str, str, str]] = []
    for _, cid, full, kind in found_matches:
        if cid not in seen:
            seen.add(cid)
            unique_matches.append((cid, full, kind))

    hierarchy: list[dict[str, Any]] = []
    recent_parents: dict[str, str] = {}  # kind -> latest_clause_id

    for cid, full, kind in unique_matches:
        parent_id = None
        if kind in ("numbered", "clause"):
            parts = cid.split(".")
            if len(parts) > 1:
                parent_candidate = ".".join(parts[:-1])
                parent_id = parent_candidate
        elif kind == "alpha_subclause":
            parent_id = recent_parents.get("numbered") or recent_parents.get("clause")
        elif kind == "roman_subclause":
            parent_id = recent_parents.get("alpha_subclause") or recent_parents.get("numbered")

        item = {
            "clause_id": cid,
            "full_match": full,
            "kind": kind,
            "parent_id": parent_id,
            "children": [],
        }
        hierarchy.append(item)
        recent_parents[kind] = cid

    return hierarchy


def _is_page_number_pattern(line: str) -> bool:
    clean = line.strip().casefold()
    if re.fullmatch(r"(?:page\s+)?\d+(?:\s*(?:of|/)\s*\d+)?", clean):
        return True
    if re.fullmatch(r"-\s*\d+\s*-", clean):
        return True
    if re.fullmatch(r"\d+", clean):
        return True
    return False


def detect_repeated_headers_footers(pdf: pymupdf.Document) -> set[str]:
    """Detect lines appearing in the top 15% or bottom 15% of pages on >50% of pages."""
    total_pages = len(pdf)
    if total_pages < 2:
        return set()

    line_counts: dict[str, int] = {}
    for page in pdf:
        height = page.rect.height
        top_cutoff = height * 0.15
        bottom_cutoff = height * 0.85
        page_seen: set[str] = set()

        for block in page.get_text("blocks"):
            if len(block) >= 5 and block[4].strip():
                y0, y1, text = block[1], block[3], block[4]
                if y0 <= top_cutoff or y1 >= bottom_cutoff:
                    for line in text.split("\n"):
                        clean = " ".join(line.split())
                        if clean and len(clean) > 3 and clean not in page_seen:
                            page_seen.add(clean)
                            line_counts[clean] = line_counts.get(clean, 0) + 1

    threshold = max(2, total_pages * 0.5)
    repeated = {line for line, count in line_counts.items() if count >= threshold}
    return repeated


def _bbox_overlap_ratio(bbox1: tuple[float, float, float, float], bbox2: tuple[float, float, float, float]) -> float:
    """Calculate the overlap ratio of bbox1 covered by bbox2."""
    x0 = max(bbox1[0], bbox2[0])
    y0 = max(bbox1[1], bbox2[1])
    x1 = min(bbox1[2], bbox2[2])
    y1 = min(bbox1[3], bbox2[3])

    if x1 <= x0 or y1 <= y0:
        return 0.0

    intersection = (x1 - x0) * (y1 - y0)
    area1 = max(1.0, (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1]))
    return intersection / area1


def extract_page_tables_and_text(
    page: pymupdf.Page,
    repeated_headers: set[str],
    page_index: int,
) -> tuple[str, list[dict[str, Any]], int, list[str]]:
    """Extract page content with:

    1. Multi-column reading order.
    2. Header/footer stripping.
    3. Rebuilt table cells from words with spacing & punctuation preserved.
    4. Row format: [TABLE t1 ROW x] Col1=Val1 | Col2=Val2.
    5. Region-based dedup (table text excluded from normal text flow).
    """
    headers_removed: list[str] = []
    structured_tables: list[dict[str, Any]] = []
    table_bboxes: list[tuple[float, float, float, float]] = []

    # 1. Detect Tables
    try:
        tabs = page.find_tables()
        if tabs and tabs.tables:
            for t_idx, tab in enumerate(tabs.tables, start=1):
                t_bbox = (tab.bbox[0], tab.bbox[1], tab.bbox[2], tab.bbox[3])
                table_bboxes.append(t_bbox)

                # Extract header row
                raw_rows = tab.extract()
                if not raw_rows:
                    continue

                # Header names
                header_row = [str(c or "").strip().replace("\n", " ") for c in raw_rows[0]]
                if not any(header_row):
                    header_row = [f"Col{i+1}" for i in range(len(raw_rows[0]))]

                # Rebuild each cell's text using words inside cell bbox
                table_rows = []
                for r_idx, row_data in enumerate(raw_rows[1:], start=1):
                    row_cells: dict[str, str] = {}
                    for c_idx, cell_value in enumerate(row_data):
                        col_name = header_row[c_idx] if c_idx < len(header_row) else f"Col{c_idx+1}"
                        # Try to get cell bbox from tab.cells if available
                        cell_text = str(cell_value or "").strip().replace("\n", " ")
                        try:
                            if hasattr(tab, "rows") and r_idx < len(tab.rows):
                                row_cells_bboxes = tab.rows[r_idx].cells
                                if c_idx < len(row_cells_bboxes):
                                    c_bbox = row_cells_bboxes[c_idx]
                                    if c_bbox and isinstance(c_bbox, (tuple, list)) and len(c_bbox) == 4:
                                        words = page.get_text("words", clip=c_bbox)
                                        if words:
                                            sorted_words = sorted(words, key=lambda w: (round(w[1], 1), w[0]))
                                            repaired = " ".join(w[4] for w in sorted_words).strip()
                                            if repaired:
                                                cell_text = repaired
                        except Exception:
                            pass
                        row_cells[col_name] = cell_text

                    table_rows.append({"row_index": r_idx, "cells": row_cells})

                structured_tables.append({
                    "table_id": f"t{t_idx}",
                    "bbox": list(t_bbox),
                    "header_row": header_row,
                    "rows": table_rows,
                })
    except Exception as exc:
        logger.debug("Table detection error on page %s: %s", page_index, exc)

    # 2. Extract Blocks and handle multi-column clustering
    blocks = page.get_text("blocks", sort=True)
    body_blocks: list[tuple[float, float, float, float, str]] = []

    for b in blocks:
        if len(b) < 5 or not b[4].strip():
            continue
        bbox = (b[0], b[1], b[2], b[3])
        block_text = b[4]

        # Region-based dedup: exclude blocks inside any detected table bbox
        if any(_bbox_overlap_ratio(bbox, tb) > 0.4 for tb in table_bboxes):
            continue

        # Filter repeated headers and footers
        clean_lines = []
        for line in block_text.split("\n"):
            clean = " ".join(line.split())
            if not clean:
                continue
            if clean in repeated_headers or _is_page_number_pattern(clean):
                headers_removed.append(clean)
            else:
                clean_lines.append(line)

        if clean_lines:
            body_blocks.append((bbox[0], bbox[1], bbox[2], bbox[3], "\n".join(clean_lines)))

    # Handle multi-column layout by clustering blocks by horizontal midpoint
    page_width = page.rect.width
    left_column = []
    right_column = []
    multi_column = False

    # Check if page looks two-column (blocks distinctly on left and right)
    if len(body_blocks) >= 4:
        midpoint = page_width / 2.0
        left_only = all(b[2] <= midpoint * 1.15 for b in body_blocks if b[0] < midpoint * 0.8)
        right_only = all(b[0] >= midpoint * 0.85 for b in body_blocks if b[2] > midpoint * 1.2)
        if left_only and right_only:
            multi_column = True
            for b in body_blocks:
                if (b[0] + b[2]) / 2.0 < midpoint:
                    left_column.append(b)
                else:
                    right_column.append(b)
            # Sort each column top to bottom
            left_column.sort(key=lambda b: b[1])
            right_column.sort(key=lambda b: b[1])
            body_blocks = left_column + right_column

    text_parts: list[str] = [b[4].strip() for b in body_blocks if b[4].strip()]

    # Format table rows cleanly: [TABLE t1 ROW 1] Col1=Val1 | Col2=Val2
    table_text_lines = []
    for tab in structured_tables:
        t_id = tab["table_id"]
        for row in tab["rows"]:
            r_idx = row["row_index"]
            cell_strs = [f"{col}={val}" for col, val in row["cells"].items()]
            table_text_lines.append(f"[TABLE {t_id} ROW {r_idx}] " + " | ".join(cell_strs))

    combined_sections = []
    if text_parts:
        combined_sections.append("\n\n".join(text_parts))
    if table_text_lines:
        combined_sections.append("\n".join(table_text_lines))

    final_text = "\n\n".join(combined_sections).strip()
    return final_text, structured_tables, len(structured_tables), headers_removed


def load_pdf(path: Path, max_bytes: int = 25 * 1024 * 1024) -> list[Document]:
    if path.suffix.casefold() != ".pdf":
        raise ValueError(f"Unsupported source file type: {path.name}")
    if not path.is_file():
        raise FileNotFoundError(f"PDF does not exist: {path}")
    if path.stat().st_size > max_bytes:
        raise ValueError(f"PDF exceeds the configured size limit: {path.name}")

    document_id = hashlib.sha256(path.read_bytes()).hexdigest()
    ingested_at = datetime.now(timezone.utc).isoformat()
    pages: list[Document] = []
    has_tesseract = shutil.which("tesseract") is not None

    try:
        with pymupdf.open(path) as pdf:
            total_pages = len(pdf)
            first_page_text = pdf[0].get_text("text") if total_pages > 0 else ""
            classification_info = DocumentClassifier.classify_text_and_name(path.name, first_page_text)
            document_type = classification_info["document_type"]

            # First pass: detect global repeated headers/footers
            repeated_headers = detect_repeated_headers_footers(pdf)

            for page_index, page in enumerate(pdf, start=1):
                raw_text = page.get_text("text").strip()
                is_scanned = False
                ocr_status = "not_needed"
                page_status = "processed"

                # Check for scanned page (< 50 chars or large image covering page)
                images = page.get_images()
                page_area = page.rect.width * page.rect.height
                has_large_image = False
                for img in images:
                    try:
                        bbox = page.get_image_bbox(img)
                        if bbox and (bbox.width * bbox.height) / max(1.0, page_area) > 0.5:
                            has_large_image = True
                            break
                    except Exception:
                        pass

                if len(raw_text) < 50 or has_large_image:
                    is_scanned = True
                    if has_tesseract:
                        try:
                            ocr_tp = page.get_textpage_ocr(language="eng")
                            ocr_text = ocr_tp.extractText().strip()
                            if len(ocr_text) > len(raw_text):
                                raw_text = ocr_text
                            ocr_status = "completed"
                        except Exception as ocr_err:
                            logger.debug("PyMuPDF OCR failed on page %s: %s", page_index, ocr_err)
                            ocr_status = "failed"
                    else:
                        ocr_status = "unavailable"
                        if len(raw_text) < 50:
                            page_status = "skipped_no_text"

                # Extract content with tables, headers stripped, and region-dedup
                content, structured_tables, table_count, headers_removed = extract_page_tables_and_text(
                    page, repeated_headers, page_index
                )

                if not content.strip() and raw_text:
                    content = raw_text

                if not content.strip():
                    logger.warning("No extractable text or tables in %s page %s", path.name, page_index)
                    if page_status == "processed":
                        page_status = "skipped_no_text"

                clauses = detect_clause_ids(content)

                pages.append(Document(
                    page_content=content,
                    metadata={
                        "document_id": document_id,
                        "filename": path.name,
                        "document_type": document_type,
                        "document_classification": classification_info,
                        "page": page_index,
                        "total_pages": total_pages,
                        "ingested_at": ingested_at,
                        "has_tables": table_count > 0,
                        "table_count": table_count,
                        "tables": structured_tables,
                        "clause_ids": clauses,
                        "detected_clauses": ", ".join(clauses) if clauses else "none",
                        "is_scanned": is_scanned,
                        "ocr_status": ocr_status,
                        "page_status": page_status,
                        "headers_removed": headers_removed,
                    },
                ))
    except (pymupdf.FileDataError, RuntimeError) as exc:
        raise ValueError(f"Could not parse PDF {path.name}: {exc}") from exc

    if not pages:
        raise ValueError(f"PDF contains no extractable text: {path.name}")
    return pages


def load_source_pdfs(settings: Settings | None = None) -> list[Document]:
    active = settings or get_settings()
    pdfs = find_pdfs(active)
    if not pdfs:
        raise FileNotFoundError(
            f"No source PDFs discovered. Place documents in {active.source_pdf_directory}."
        )

    # Multi-document and standalone support:
    # If 2 PDFs, check classification for backward compatibility with 2-doc workflows
    if len(pdfs) == 2:
        types = {classify_document(path) for path in pdfs}
        valid_pairs = (
            {"policy_handbook", "circular"},
            {"baseline_policy", "amendment"},
            {"policy_handbook", "amendment"},
            {"baseline_policy", "circular"},
        )
        if not any(types.issubset(vp) or vp.issubset(types) for vp in valid_pairs):
            logger.warning("Discovered 2 PDFs with types: %s", types)

    documents: list[Document] = []
    for path in pdfs:
        documents.extend(load_pdf(path, active.max_pdf_bytes))
    return documents


def ingestion_status(settings: Settings | None = None) -> dict[str, str]:
    active = settings or get_settings()
    manifest_path = active.chroma_persist_directory.parent / "ingestion_manifest.json"
    if not manifest_path.is_file():
        return {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read local ingestion manifest")
        return {}
    indexed = {
        item["filename"]: item for item in manifest.get("documents", [])
    }
    status: dict[str, str] = {}
    for path in find_pdfs(active):
        manifest_item = indexed.get(path.name)
        if manifest_item is None:
            status[path.name] = "not_indexed"
        elif (
            hashlib.sha256(path.read_bytes()).hexdigest() != manifest_item["document_id"]
            or manifest.get("embedding_model") != active.embedding_model
        ):
            status[path.name] = "stale"
        else:
            status[path.name] = "indexed"
    return status
