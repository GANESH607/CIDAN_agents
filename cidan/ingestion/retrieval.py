from langchain_core.documents import Document

from cidan.ingestion.vector_store import create_vector_store
from cidan.models import Citation


def retrieve(query: str, document_type: str | list[str], k: int = 6) -> list[Document]:
    store = create_vector_store()
    if isinstance(document_type, (list, tuple, set)):
        # Support multiple document types with deduplication
        docs = []
        seen = set()
        for dt in document_type:
            try:
                sub_docs = store.similarity_search(query, k=k, filter={"document_type": dt})
                for d in sub_docs:
                    cid = d.metadata.get("chunk_id") or (d.metadata.get("filename"), d.metadata.get("page"), d.page_content[:40])
                    if cid not in seen:
                        seen.add(cid)
                        docs.append(d)
            except Exception:
                continue
        return docs[:k]
    return store.similarity_search(
        query,
        k=k,
        filter={"document_type": document_type},
    )


def retrieve_policy_candidates(
    obligation,
    top_k: int = 8,
    policy_types: tuple[str, ...] = ("policy_handbook", "baseline_policy", "policy"),
) -> list[Document]:
    """Multi-query semantic retrieval to locate the most relevant policy passages.

    Queries:
    1. Full obligation text + required action (broad semantic match)
    2. Clause ID + applicability + product type (targeted structural match)
    3. Action + amount / threshold / frequency (operational parameter match)
    Avoids missing relevant policies due to low top-K by aggregating & deduplicating.
    """
    store = create_vector_store()
    queries = []

    # Query 1: Core requirement
    q1 = f"{obligation.text} {obligation.required_action}".strip()
    if q1:
        queries.append(q1)

    # Query 2: Structural/domain context
    clause_clean = obligation.clause_id if obligation.clause_id and obligation.clause_id != "not_specified" else ""
    q2 = f"{clause_clean} {obligation.applicability} {obligation.product_type}".strip()
    if q2 and q2 != q1:
        queries.append(q2)

    # Query 3: Numerical or operational specifics
    q3_parts = []
    if obligation.amount_threshold is not None:
        q3_parts.append(str(obligation.amount_threshold))
    if obligation.currency and obligation.currency != "not_specified":
        q3_parts.append(obligation.currency)
    if obligation.deadline_or_frequency and obligation.deadline_or_frequency != "not_specified":
        q3_parts.append(obligation.deadline_or_frequency)
    if q3_parts:
        q3 = f"{obligation.required_action} {' '.join(q3_parts)}".strip()
        if q3 and q3 not in queries:
            queries.append(q3)

    results: list[Document] = []
    seen_chunk_ids: set[str] = set()

    for q in queries:
        for ptype in policy_types:
            try:
                matches = store.similarity_search(q, k=top_k, filter={"document_type": ptype})
                for doc in matches:
                    cid = doc.metadata.get("chunk_id") or f"{doc.metadata.get('filename')}-{doc.metadata.get('page')}-{hash(doc.page_content)}"
                    if cid not in seen_chunk_ids:
                        seen_chunk_ids.add(cid)
                        results.append(doc)
            except Exception:
                # If filtered similarity search fails for a specific type, continue
                continue

    # If nothing found with filtered search, try unfiltered as a fallback
    if not results:
        for q in queries:
            try:
                matches = store.similarity_search(q, k=top_k)
                for doc in matches:
                    dtype = doc.metadata.get("document_type")
                    if dtype in policy_types or doc.metadata.get("role") == "baseline":
                        cid = doc.metadata.get("chunk_id") or f"{doc.metadata.get('filename')}-{doc.metadata.get('page')}-{hash(doc.page_content)}"
                        if cid not in seen_chunk_ids:
                            seen_chunk_ids.add(cid)
                            results.append(doc)
            except Exception:
                continue

    return results[:top_k]


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
