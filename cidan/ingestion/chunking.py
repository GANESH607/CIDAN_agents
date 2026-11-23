import hashlib
import re

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_documents(
    pages: list[Document], chunk_size: int = 1000, chunk_overlap: int = 150
) -> list[Document]:
    if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("Require chunk_size > chunk_overlap >= 0.")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    chunks: list[Document] = []
    for page in pages:
        page_chunks = splitter.split_documents([page])
        for piece in page_chunks:
            metadata = dict(piece.metadata)
            start_idx = metadata.get("start_index", 0)
            chunk_id = hashlib.sha256(
                f"{metadata['document_id']}:{metadata['page']}:"
                f"{start_idx}:{piece.page_content}".encode("utf-8")
            ).hexdigest()
            metadata["chunk_id"] = chunk_id

            # Clause-aware metadata
            clause_match = re.search(
                r"(?:(?:Clause|Section|Article|Para(?:graph)?)\s*([0-9]+(?:\.[0-9]+)+))|(?:\n|^)\s*([0-9]+\.[0-9]+(?:\.[0-9]+)*)\b",
                piece.page_content,
                re.IGNORECASE,
            )
            detected_clause = (clause_match.group(1) or clause_match.group(2)) if clause_match else None
            metadata["clause_id"] = detected_clause.strip() if detected_clause else "not_specified"
            metadata["has_table_content"] = "[TABLE" in piece.page_content or bool(metadata.get("has_tables"))
            metadata["surrounding_context"] = page.page_content[:1500]

            piece.metadata = metadata
            chunks.append(piece)
    return chunks
