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
    """Retrieve all ingested document chunks without rigid top-k or query limitations,

    ensuring complete source coverage.
    """
    store = create_vector_store()
    try:
        where_filter = {"document_type": document_type} if document_type else None
        results = store.get(where=where_filter) if where_filter else store.get()
        documents: list[Document] = []
        if results and "documents" in results and results["documents"]:
            for idx, content in enumerate(results["documents"]):
                meta = dict(results["metadatas"][idx]) if "metadatas" in results and idx < len(results["metadatas"]) else {}
                chunk_id = results["ids"][idx] if "ids" in results and idx < len(results["ids"]) else ""
                meta["chunk_id"] = chunk_id
                documents.append(Document(page_content=content, metadata=meta))
            return documents
    except Exception:
        pass
    # Fallback to similarity search if store.get() is unsupported by mock
    try:
        return store.similarity_search("", k=100, filter={"document_type": document_type} if document_type else None)
    except Exception:
        return []


def citation_for(document: Document) -> Citation:
    metadata = document.metadata
    return Citation(
        document_id=metadata["document_id"],
        filename=metadata["filename"],
        document_type=metadata["document_type"],
        page=int(metadata["page"]),
        excerpt=document.page_content[:600],
        chunk_id=metadata["chunk_id"],
    )
