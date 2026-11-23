import json
from pathlib import Path

import pymupdf
import pytest
from langchain_core.documents import Document

from cidan.agents import circular_understanding
from cidan.ingestion import chunking, document_classifier, pdf_loader
from cidan.models import Citation, Obligation
from cidan.services import agent1_storage


def create_test_pdf(tmp_path: Path, filename: str, pages_text: list[str]) -> Path:
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    file_path = tmp_path / filename
    doc.save(str(file_path))
    doc.close()
    return file_path


def test_document_classification_various_types(tmp_path):
    classifier = document_classifier.DocumentClassifier

    # 1. Circular / regulatory
    circ = classifier.classify_text_and_name(
        "RBI_Master_Direction_2026.pdf",
        "Reserve Bank of India Master Direction on Lending Norms and Approvals."
    )
    assert circ["document_type"] == "circular"
    assert circ["is_regulatory"] is True

    # 2. Amendment document
    amd = classifier.classify_text_and_name(
        "Amendment_Policy_2026.pdf",
        "Amendment to Lending Guidelines 2025. Clause 2.1 is hereby modified."
    )
    assert amd["document_type"] == "amendment"
    assert amd["is_amendment"] is True

    # 3. Policy handbook / Baseline
    policy = classifier.classify_text_and_name(
        "Credit_Risk_Policy_Handbook.pdf",
        "Internal Policy Handbook and Operational Guidelines for Credit Appraisal."
    )
    assert policy["document_type"] in ("policy_handbook", "baseline_policy")
    assert policy["is_policy"] is True

    # 4. Standalone document
    standalone = classifier.classify_text_and_name(
        "Special_Advisory_Framework.pdf",
        "Advisory guidance for retail branch audit compliance."
    )
    assert standalone["document_type"] in ("standalone_document", "circular")


def test_pdf_clause_detection_and_tables(tmp_path):
    page_text = (
        "Section 2: Loan Approval Obligations\n\n"
        "Clause 2.1: Loans exceeding 80,000 INR require secondary senior manager sign-off.\n"
        "Clause 2.2: Digital assisted support must be available.\n"
        "Clause 2.4: Outbound verification calls are required for customer age 80+.\n"
    )
    pdf_path = create_test_pdf(tmp_path, "sample_clauses.pdf", [page_text])
    docs = pdf_loader.load_pdf(pdf_path)

    assert len(docs) == 1
    detected = docs[0].metadata["detected_clauses"]
    assert "2.1" in detected
    assert "2.2" in detected
    assert "2.4" in detected


def test_clause_aware_chunking_preserves_context(tmp_path):
    page_text = (
        "Section 1: General Principles\n"
        "Clause 1.1: Every applicant must be verified.\n\n"
        "Section 2: Lending Safeguards\n"
        "Clause 2.5: Senior citizen complaints must be resolved in 7 working days."
    )
    doc = Document(
        page_content=page_text,
        metadata={"document_id": "test-doc-id", "filename": "sample.pdf", "page": 1, "document_type": "circular"},
    )
    chunks = chunking.split_documents([doc], chunk_size=200, chunk_overlap=30)
    assert len(chunks) >= 1
    assert all("chunk_id" in c.metadata for c in chunks)
    assert any(c.metadata.get("clause_id") != "not_specified" for c in chunks)
    assert all("surrounding_context" in c.metadata for c in chunks)


def test_supporting_excerpt_not_overwritten(tmp_path):
    """Verifies that the candidate's exact verbatim excerpt is preserved

    in supporting_excerpt and surrounding context is stored separately in surrounding_context.
    """
    page_content = (
        "Section 2.5: Senior citizen grievances.\n"
        "Acknowledge within 1 working day and resolve within 7 working days.\n"
        "All complaints must be logged into the central compliance tracking system."
    )
    exact_quote = "Acknowledge within 1 working day and resolve within 7 working days."

    candidate = circular_understanding.ObligationCandidate(
        source_chunk_id="chunk-test-1",
        clause_id="2.5",
        text="Acknowledge within 1 working day and resolve within 7 working days.",
        applicability="senior citizens",
        product_type="grievance",
        effective_date="2026-04-01",
        responsible_function="Customer Grievance",
        required_action="Acknowledge in 1 day and resolve in 7 days",
        supporting_excerpt=exact_quote,
        confidence=0.95,
        change_classification="MODIFIED",
        previous_requirement="Acknowledge in 2 days and resolve in 10 days.",
        amended_requirement=exact_quote,
    )

    doc = Document(
        page_content=page_content,
        metadata={
            "document_id": "doc-test",
            "filename": "Amendment_2026.pdf",
            "document_type": "circular",
            "page": 2,
            "chunk_id": "chunk-test-1",
            "total_pages": 3,
        },
    )

    def fake_llm(schema, _sys, _prompt):
        return schema(obligations=[candidate])

    results = circular_understanding.run([doc], llm_call=fake_llm, workflow_id="test-excerpt-workflow")
    assert len(results) == 1
    obl = results[0]

    # Crucial assertion: supporting_excerpt is the exact quote, NOT the entire page_content
    assert obl.supporting_excerpt == exact_quote
    assert obl.supporting_excerpt != page_content
    assert obl.surrounding_context == page_content
    assert obl.verification_status == "verified"
    assert obl.change_classification == "MODIFIED"
    assert obl.previous_requirement == "Acknowledge in 2 days and resolve in 10 days."


def test_missing_clause_detection():
    gaps = circular_understanding.detect_clause_gaps(["2.1", "2.2", "2.4", "2.5"])
    assert "2.3" in gaps

    no_gaps = circular_understanding.detect_clause_gaps(["1.1", "1.2", "1.3"])
    assert len(no_gaps) == 0


def test_standalone_document_without_baseline(tmp_path):
    """Verifies that Agent 1 processes standalone circulars smoothly

    without requiring a baseline policy document.
    """
    page_text = "Clause 1.1: Standalone regulatory requirement. Banks must submit monthly audit returns."
    pdf_path = create_test_pdf(tmp_path, "standalone_circular.pdf", [page_text])
    docs = pdf_loader.load_pdf(pdf_path)

    candidate = circular_understanding.ObligationCandidate(
        source_chunk_id=docs[0].metadata["document_id"] + ":1:0:" + docs[0].page_content,
        clause_id="1.1",
        text="Banks must submit monthly audit returns.",
        applicability="all banks",
        product_type="audit",
        responsible_function="Compliance",
        required_action="Submit monthly returns",
        supporting_excerpt="Banks must submit monthly audit returns.",
        confidence=0.92,
        change_classification="NEW",
    )
    # Give document a chunk_id matching candidate
    docs[0].metadata["chunk_id"] = candidate.source_chunk_id

    def fake_llm(schema, _sys, _prompt):
        return schema(obligations=[candidate])

    results = circular_understanding.run(docs, llm_call=fake_llm, workflow_id="standalone-test-wf")
    assert len(results) == 1
    assert results[0].clause_id == "1.1"
    assert results[0].change_classification == "NEW"


def test_independent_json_storage_files_and_schemas(tmp_path):
    """Verifies that all 5 independent JSON files are saved properly for a workflow."""
    wf_id = "test-independent-storage-wf"
    out_dir = agent1_storage.get_agent1_output_dir(wf_id)

    page_content = "Clause 3.1: Minimum capital reserve requirement."
    candidate = circular_understanding.ObligationCandidate(
        source_chunk_id="chk-id-31",
        clause_id="3.1",
        text="Minimum capital reserve requirement.",
        applicability="scheduled banks",
        product_type="capital",
        responsible_function="Treasury",
        required_action="Maintain reserve ratio",
        supporting_excerpt="Minimum capital reserve requirement.",
        confidence=0.9,
        change_classification="UNCHANGED",
    )
    doc = Document(
        page_content=page_content,
        metadata={
            "document_id": "doc-cap",
            "filename": "Capital_Norms.pdf",
            "document_type": "circular",
            "page": 1,
            "chunk_id": "chk-id-31",
            "total_pages": 1,
        },
    )

    circular_understanding.run([doc], llm_call=lambda s, *_: s(obligations=[candidate]), workflow_id=wf_id)

    # Check 5 independent files
    expected_files = [
        "extracted_obligations.json",
        "amendment_comparison.json",
        "evidence_and_citations.json",
        "coverage_report.json",
        "execution_metadata.json",
    ]
    for fn in expected_files:
        fp = out_dir / fn
        assert fp.is_file(), f"Missing expected output file: {fn}"
        data = json.loads(fp.read_text(encoding="utf-8"))
        assert data.get("schema_version") == "1.0.0"
        assert data.get("workflow_id") == wf_id or data.get("agent") == "Agent 1 - Obligation Extraction"
