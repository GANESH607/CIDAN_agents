from langchain_core.documents import Document

from cidan.ingestion.vector_store import create_vector_store
from cidan.models import Citation


def retrieve(query: str, document_type: str, k: int = 6) -> list[Document]:
    store = create_vector_store()
    return store.similarity_search(
        query,
        k=k,
        filter={"document_type": document_type},
    )


def retrieve_all(document_type: str | None = None) -> list[Document]:
    """Retrieve all ingested document chunks with store.get() and pagination.

    Does not swallow retrieval errors or fall back to arbitrary similarity search.
    """
    store = create_vector_store()
    where_filter = {"document_type": document_type} if document_type else None
    documents: list[Document] = []
    offset = 0
    page_limit = 200

    try:
        while True:
            # Query chroma vector store with pagination
            try:
                results = store.get(where=where_filter, limit=page_limit, offset=offset)
            except TypeError:
                # Store mock or implementation without pagination parameters
                results = store.get(where=where_filter) if where_filter else store.get()

            if not results or "documents" not in results or not results["documents"]:
                break

            batch_docs = results["documents"]
            metadatas = results.get("metadatas") or []
            ids = results.get("ids") or []

            for idx, content in enumerate(batch_docs):
                meta = dict(metadatas[idx]) if idx < len(metadatas) and metadatas[idx] else {}
                chunk_id = ids[idx] if idx < len(ids) else ""
                meta["chunk_id"] = chunk_id
                documents.append(Document(page_content=content, metadata=meta))

            # If fewer returned than limit or no pagination, finished
            if len(batch_docs) < page_limit or "offset" not in locals():
                break
            offset += len(batch_docs)

        return documents
    except Exception as exc:
        raise RuntimeError(f"Failed to retrieve ingested documents from vector store: {exc}") from exc


def citation_for(document: Document) -> Citation:
    metadata = document.metadata
    doc_type = metadata.get("document_type") or "circular"
    if doc_type not in ("circular", "policy_handbook", "amendment", "baseline_policy", "standalone_document", "unknown"):
        doc_type = "unknown"
    return Citation(
        document_id=str(metadata.get("document_id", "doc")),
        filename=str(metadata.get("filename", "unknown.pdf")),
        document_type=doc_type,
        page=int(metadata.get("page", 1)),
        excerpt=document.page_content[:600],
        chunk_id=str(metadata.get("chunk_id", "chunk-0")),
    )
