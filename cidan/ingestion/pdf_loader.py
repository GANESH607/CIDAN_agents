import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

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
    """Classifies a document based on name and content signals.

    Maintains backward compatibility with expected labels.
    """
    name = path.name.casefold()
    if any(token in name for token in ("policy", "handbook", "rules")):
        return "policy_handbook"
    if any(token in name for token in ("circular", "regulatory", "rbi")):
        return "circular"
    if any(token in name for token in ("amendment", "revised", "corrigendum", "addendum")):
        return "amendment"
    if "baseline" in name:
        return "baseline_policy"

    # Use multi-signal classifier
    res = DocumentClassifier.classify_text_and_name(path.name, sample_text)
    doc_type = str(res["document_type"])
    if doc_type in ("circular", "policy_handbook"):
        return doc_type
    if doc_type in ("amendment", "standalone_document"):
        return doc_type
    return "unknown"


def extract_tables_from_page(page: pymupdf.Page) -> tuple[str, bool, int]:
    """Detect and extract tabular structures from a page using PyMuPDF."""
    table_strings = []
    try:
        tabs = page.find_tables()
        if tabs and tabs.tables:
            for idx, tab in enumerate(tabs.tables, start=1):
                rows = tab.extract()
                if not rows or len(rows) < 2:
                    continue
                header = [str(c or "").strip().replace("\n", " ") for c in rows[0]]
                if not any(header):
                    continue
                tbl = [f"\n[TABLE {idx}]", "| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
                for row in rows[1:]:
                    row_str = "| " + " | ".join(str(c or "").strip().replace("\n", " ") for c in row) + " |"
                    tbl.append(row_str)
                table_strings.append("\n".join(tbl))
    except Exception as exc:
        logger.debug("Table detection error on page %s: %s", getattr(page, "number", "?"), exc)
    return "\n\n".join(table_strings), bool(table_strings), len(table_strings)


def detect_clause_ids(text: str) -> list[str]:
    """Identify clause and subclause numbers (e.g., 2.1, 2.5, Clause 3.2)."""
    found = set()
    for m in re.finditer(
        r"(?:(?:Clause|Section|Article|Para(?:graph)?)\s*([0-9]+(?:\.[0-9]+)+))|(?:\n|^)\s*([0-9]+\.[0-9]+(?:\.[0-9]+)*)\b",
        text,
        re.IGNORECASE,
    ):
        cid = m.group(1) or m.group(2)
        if cid:
            found.add(cid.strip())
    return sorted(found, key=lambda x: [int(p) if p.isdigit() else p for p in x.split(".")])


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

    try:
        with pymupdf.open(path) as pdf:
            total_pages = len(pdf)
            first_page_text = pdf[0].get_text("text") if total_pages > 0 else ""
            document_type = classify_document(path, first_page_text)

            for page_index, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()
                is_scanned = False

                # Scanned PDF handling: if text is empty or very sparse (<50 chars)
                if len(text) < 50:
                    is_scanned = True
                    try:
                        # Attempt PyMuPDF OCR if available on system
                        ocr_tp = page.get_textpage_ocr(language="eng")
                        ocr_text = ocr_tp.extractText().strip()
                        if len(ocr_text) > len(text):
                            text = ocr_text
                    except Exception:
                        pass

                # Detect and extract structured tables
                table_text, has_tables, table_count = extract_tables_from_page(page)
                combined_text = text
                if table_text and table_text not in text:
                    combined_text = f"{text}\n\n{table_text}" if text else table_text

                if not combined_text.strip():
                    logger.warning("No extractable text or tables in %s page %s", path.name, page_index)
                    continue

                clauses = detect_clause_ids(combined_text)

                pages.append(Document(
                    page_content=combined_text,
                    metadata={
                        "document_id": document_id,
                        "filename": path.name,
                        "document_type": document_type,
                        "page": page_index,
                        "total_pages": total_pages,
                        "ingested_at": ingested_at,
                        "has_tables": has_tables,
                        "table_count": table_count,
                        "detected_clauses": ", ".join(clauses) if clauses else "none",
                        "is_scanned": is_scanned,
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
