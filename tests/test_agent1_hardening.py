import json
from pathlib import Path
import pymupdf
import pytest
from langchain_core.documents import Document

from cidan.agents import circular_understanding
from cidan.ingestion import chunking, document_classifier, pdf_loader
from cidan.models import Citation, Obligation
from cidan.services import agent1_storage


def create_multi_page_pdf(tmp_path: Path, filename: str, pages_text: list[str]) -> Path:
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    file_path = tmp_path / filename
    doc.save(str(file_path))
    doc.close()
    return file_path


# --- Task 1 Tests ---

def test_classify_document_content_first(tmp_path):
    """Content-first classification: amendment text beats 'Policy' in filename."""
    pdf_path = create_multi_page_pdf(
        tmp_path,
        "Credit_Policy_Amendment_2026.pdf",
        [
            "RESERVE BANK OF INDIA\n"
            "Amendment to Master Directions 2025\n"
            "This amendment supersedes Clause 2.1 of the 2025 lending framework with effect from 01-04-2026."
        ],
    )
    res = document_classifier.DocumentClassifier.classify_text_and_name(
        pdf_path.name,
        "RESERVE BANK OF INDIA\nAmendment to Master Directions 2025\nThis amendment supersedes Clause 2.1 of the 2025 lending framework with effect from 01-04-2026."
    )
    assert res["document_type"] == "amendment"
    assert "signals" in res
    assert any("supersedes" in s.lower() or "amendment" in s.lower() for s in res["signals"])


def test_classify_document_revised_policy_not_policy_handbook(tmp_path):
    """Revised lending policy must be classified as amendment, not policy_handbook."""
    res = document_classifier.DocumentClassifier.classify_text_and_name(
        "Revised_Lending_Policy.pdf",
        "Modifications to credit policy guidelines. The following provisions are hereby substituted."
    )
    assert res["document_type"] == "amendment"


def test_pdf_header_footer_removal(tmp_path):
    """Detect headers/footers repeated on >50% of pages and strip them from body text."""
    pages = [
        "CONFIDENTIAL BANKING COMPLIANCE MANUAL\nSection 1.1: General Governance\nPage 1 of 3",
        "CONFIDENTIAL BANKING COMPLIANCE MANUAL\nSection 1.2: Capital Adequacy\nPage 2 of 3",
        "CONFIDENTIAL BANKING COMPLIANCE MANUAL\nSection 1.3: Reporting Timelines\nPage 3 of 3",
    ]
    pdf_path = create_multi_page_pdf(tmp_path, "header_test.pdf", pages)
    docs = pdf_loader.load_pdf(pdf_path)
    assert len(docs) == 3
    for d in docs:
        assert "headers_removed" in d.metadata
        assert "CONFIDENTIAL BANKING COMPLIANCE MANUAL" not in d.page_content
        assert "Page 1 of 3" not in d.page_content


def test_pdf_table_reconstruction_no_fused_words_and_dedup(tmp_path):
    """Table cells must preserve spaces and row structure without duplicating page text."""
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=400)
    # Draw table grid with lines so PyMuPDF find_tables detects it
    rect = pymupdf.Rect(50, 50, 550, 200)
    page.draw_rect(rect)
    page.draw_line((50, 100), (550, 100))
    page.draw_line((180, 50), (180, 200))
    page.draw_line((360, 50), (360, 200))
    # Insert text inside table
    page.insert_text((60, 80), "Clause ID")
    page.insert_text((200, 80), "Existing Requirement")
    page.insert_text((380, 80), "Amended Requirement")
    page.insert_text((60, 130), "Clause 2.1")
    page.insert_text((200, 130), "General verification rule applies.")
    page.insert_text((380, 130), "Expedited verification rule applies.")
    # Text outside table
    page.insert_text((60, 250), "Following the table above, all branches must comply.")
    pdf_path = tmp_path / "table_doc.pdf"
    doc.save(str(pdf_path))
    doc.close()

    docs = pdf_loader.load_pdf(pdf_path)
    assert len(docs) == 1
    content = docs[0].page_content
    # Table row must format with column names
    assert "[TABLE" in content
    # No fused words like "Clause21" or "ClauseID"
    assert "Clause 2.1" in content
    assert "General verification rule applies." in content
    # Text inside table should not be repeated twice (once in plain text, once in table markdown)
    assert content.count("General verification rule applies.") == 1


def test_clause_hierarchy_detection():
    """Clause detection supports complex patterns and returns hierarchy."""
    text = (
        "Clause 4 Governance Framework\n"
        "Article 5(2) Audit Scope\n"
        "2.1 Lending Safeguards\n"
        "2.1.3 Enhanced Due Diligence\n"
        "(a) Mandatory ID verification\n"
        "(i) Biometric authentication\n"
        "Annex A Technical Requirements"
    )
    detected = pdf_loader.detect_clauses_with_hierarchy(text)
    clause_ids = [item["clause_id"] for item in detected]
    assert "Clause 4" in clause_ids or "4" in clause_ids
    assert "Article 5(2)" in clause_ids or "5(2)" in clause_ids
    assert "2.1" in clause_ids
    assert "2.1.3" in clause_ids
    assert "(a)" in clause_ids
    assert "(i)" in clause_ids
    assert "Annex A" in clause_ids


# --- Task 2 Tests ---

def test_structure_aware_chunking():
    """Chunks must preserve table rows and clauses, with neighbouring context."""
    page_text = (
        "Clause 1.1: Scope and Application.\n"
        "This circular applies to all scheduled commercial banks.\n"
        "Provided that regional rural banks may follow relaxed timelines.\n\n"
        "[TABLE t1 ROW 1] Clause=2.1 | Existing=Standard verification | Revised=Priority desk\n"
        "[TABLE t1 ROW 2] Clause=2.2 | Existing=Paper receipt | Revised=Digital SMS alert\n\n"
        "Clause 3.1: Final Governance Provisions.\n"
        "Board of directors shall review compliance quarterly."
    )
    doc = Document(
        page_content=page_text,
        metadata={
            "document_id": "doc12345678abcdef",
            "filename": "circular.pdf",
            "page": 1,
            "document_type": "circular",
        },
    )
    chunks = chunking.split_documents([doc], chunk_size=300, chunk_overlap=0)
    assert len(chunks) >= 3
    # Check short chunk IDs: doc_hash8-p1-c...
    for c in chunks:
        assert c.metadata["chunk_id"].startswith("doc12345-p1-c")
        assert "context_before" in c.metadata
        assert "context_after" in c.metadata
        assert "chunk_kind" in c.metadata

    # Check table rows are separate table_row chunks
    table_chunks = [c for c in chunks if c.metadata.get("chunk_kind") == "table_row"]
    assert len(table_chunks) == 2
    assert "Clause=2.1" in table_chunks[0].page_content
    assert "Clause=2.2" in table_chunks[1].page_content


# --- Task 3 Tests ---

def test_deterministic_amendment_alignment_standalone_doc():
    """Standalone document without baseline must have change_type NEW and baseline_available False."""
    from cidan.agents import amendment_alignment

    doc = Document(
        page_content="Clause 1.1: Every bank must submit a quarterly compliance report.",
        metadata={"document_id": "stand-01", "filename": "Standalone_Circular.pdf", "document_type": "standalone_document", "page": 1},
    )
    relationships = amendment_alignment.detect_document_relationships([doc])
    assert relationships["has_baseline"] is False
    assert relationships["mode"] == "standalone"

    classification, prev_req, citation = amendment_alignment.align_obligation(
        clause_id="1.1",
        text="Every bank must submit a quarterly compliance report.",
        relationships=relationships,
        baseline_docs=[],
    )
    assert classification == "NEW"
    assert prev_req is None
    assert citation is None


def test_deterministic_amendment_different_requirement_same_clause():
    """Same clause number with different requirement is MODIFIED, not UNCHANGED."""
    from cidan.agents import amendment_alignment

    baseline_doc = Document(
        page_content="Clause 2.1: Credit approval threshold is 10,000 INR for retail borrowers.",
        metadata={"document_id": "base-01", "filename": "Base_Policy.pdf", "document_type": "policy_handbook", "page": 5, "chunk_id": "b-c1"},
    )
    relationships = {
        "has_baseline": True,
        "mode": "amendment",
        "baseline_doc_id": "base-01",
    }
    classification, prev_req, citation = amendment_alignment.align_obligation(
        clause_id="2.1",
        text="Credit approval threshold is 50,000 INR for retail borrowers.",
        relationships=relationships,
        baseline_docs=[baseline_doc],
    )
    assert classification == "MODIFIED"
    assert prev_req is not None
    assert "10,000" in prev_req
    assert citation is not None
    assert citation.page == 5


# --- Task 4 Tests ---

def test_verify_quote_exact_and_offsets():
    """verify_quote finds exact substring and returns start/end character offsets."""
    from cidan.agents import circular_understanding

    source_text = "Section 2.1 Obligations: The bank shall acknowledge all grievances within 24 hours."
    quote = "The bank shall acknowledge all grievances within 24 hours."
    verified, excerpt, start, end, status = circular_understanding.verify_quote(quote, source_text)
    assert verified is True
    assert status == "verified"
    assert excerpt == quote
    assert source_text[start:end] == quote


def test_verify_quote_fuzzy_fallback():
    """verify_quote falls back to fuzzy match (difflib >= 0.92) and sets partially_verified."""
    from cidan.agents import circular_understanding

    source_text = "Section 2.1 Obligations: The bank shall acknowledge all grievances within 24 hours."
    quote = "The bank shall acknowledge all grievance within 24 hour."  # slight typo
    verified, excerpt, start, end, status = circular_understanding.verify_quote(quote, source_text)
    assert verified is True
    assert status == "partially_verified"
    assert excerpt == "The bank shall acknowledge all grievances within 24 hours."
    assert source_text[start:end] == excerpt


def test_clause_token_boundary_regex():
    """Token-boundary regex prevents 1.1 matching 11.12 or 21.1."""
    from cidan.agents import circular_understanding

    source = "Under Clause 11.12 and 21.1, conditions apply."
    assert circular_understanding.is_clause_in_text("1.1", source) is False
    source2 = "Clause 1.1 applies to retail customers."
    assert circular_understanding.is_clause_in_text("1.1", source2) is True


def test_threshold_check_indian_and_phrasings():
    """Accepts varied threshold phrasings including Indian digit grouping and units."""
    from cidan.agents import circular_understanding

    text = "Loans up to 5,00,000 INR and exposures not exceeding 50 lakh require zonal review."
    numbers = circular_understanding.extract_numeric_expressions(text)
    values = [n["value"] for n in numbers]
    assert 500000 in values
    assert 5000000 in values or 50 in values


# --- Task 5 Tests ---

def test_agent1_storage_no_mkdir_on_read(tmp_path, monkeypatch):
    """get_agent1_output_dir(workflow_id, create=False) does not create directory."""
    monkeypatch.setattr(agent1_storage, "WORKFLOW_OUTPUTS_DIR", tmp_path / "wf_outputs")
    non_existent = "non-existent-wf-123"
    target_dir = agent1_storage.get_agent1_output_dir(non_existent, create=False)
    assert not target_dir.exists()


def test_storage_path_traversal_rejected(tmp_path, monkeypatch):
    """Path traversal attempts raise ValueError."""
    monkeypatch.setattr(agent1_storage, "WORKFLOW_OUTPUTS_DIR", tmp_path / "wf_outputs")
    for bad_id in ["../evil", "..\\evil", "foo/bar", "foo\\bar", "/absolute", "evil\x00path"]:
        with pytest.raises(ValueError):
            agent1_storage.get_agent1_output_dir(bad_id)


def test_load_agent1_summary_no_12_4_fallback(tmp_path, monkeypatch):
    """load_agent1_summary must not return 12.4 fallback when execution_time is missing."""
    monkeypatch.setattr(agent1_storage, "WORKFLOW_OUTPUTS_DIR", tmp_path / "wf_outputs")
    wf_id = "test-wf-no-fallback"
    out_dir = agent1_storage.get_agent1_output_dir(wf_id, create=True)
    (out_dir / "extracted_obligations.json").write_text(json.dumps({
        "schema_version": "1.1.0",
        "workflow_id": wf_id,
        "total_obligations": 0,
        "obligations": []
    }))
    (out_dir / "execution_metadata.json").write_text(json.dumps({
        "schema_version": "1.1.0",
        "workflow_id": wf_id,
        "status": "completed",
    }))
    summary = agent1_storage.load_agent1_summary(wf_id)
    assert summary.get("execution_time_seconds") is None or summary.get("execution_time_seconds") != 12.4


def test_bad_chunk_id_recovery_never_raises():
    """Bad chunk_id does not abort run, attempts recovery or marks needs_human_review."""
    doc = Document(
        page_content="Clause 1.1: Mandatory capital reserve ratio of 10%.",
        metadata={"document_id": "doc-01", "filename": "norm.pdf", "page": 1, "chunk_id": "doc-01-p1-c1"},
    )
    candidate = circular_understanding.ObligationCandidate(
        source_chunk_id="non-existent-chunk-999",  # Bad chunk id
        clause_id="1.1",
        text="Mandatory capital reserve ratio of 10%.",
        applicability="all banks",
        product_type="capital",
        responsible_function="Treasury",
        required_action="Maintain reserve ratio",
        supporting_excerpt="Mandatory capital reserve ratio of 10%.",
        confidence=0.9,
    )
    results = circular_understanding.run([doc], llm_call=lambda s, *_: s(obligations=[candidate]))
    assert len(results) == 1
    assert results[0].clause_id == "1.1"
    # Recovered chunk id or flagged with review reason
    assert len(results[0].review_reasons) > 0 or results[0].source.chunk_id == "doc-01-p1-c1"


def test_deliberately_failing_chunk_produces_completed_with_errors(tmp_path, monkeypatch):
    """A failing chunk produces status completed_with_errors and saves partial results."""
    monkeypatch.setattr(agent1_storage, "WORKFLOW_OUTPUTS_DIR", tmp_path / "wf_outputs")
    wf_id = "failing-chunk-wf"

    doc1 = Document(
        page_content="Clause 1.1: Good chunk that succeeds.",
        metadata={"document_id": "doc-good", "filename": "good.pdf", "page": 1, "chunk_id": "doc-p1-c1"},
    )
    doc2 = Document(
        page_content="Clause 1.2: Bad chunk that fails.",
        metadata={"document_id": "doc-bad", "filename": "bad.pdf", "page": 2, "chunk_id": "doc-p2-c2"},
    )

    def failing_llm(schema, _sys, prompt):
        if "Bad chunk" in prompt and "Good chunk" in prompt:
            raise RuntimeError("Simulated failure on combined batch")
        if "Bad chunk" in prompt:
            raise RuntimeError("Simulated timeout / JSON syntax error on bad chunk")
        if "Good chunk" in prompt:
            candidate = circular_understanding.ObligationCandidate(
                source_chunk_id="doc-p1-c1",
                clause_id="1.1",
                text="Good chunk requirement.",
                applicability="all",
                product_type="compliance",
                responsible_function="Operations",
                required_action="Action",
                supporting_excerpt="Good chunk that succeeds.",
                confidence=0.9,
            )
            return schema(obligations=[candidate])
        raise RuntimeError("Unknown prompt")

    results = circular_understanding.run([doc1, doc2], llm_call=failing_llm, workflow_id=wf_id)
    assert len(results) == 1
    assert results[0].clause_id == "1.1"

    out_dir = agent1_storage.get_agent1_output_dir(wf_id, create=False)
    meta = json.loads((out_dir / "execution_metadata.json").read_text(encoding="utf-8"))
    assert meta["status"] == "completed_with_errors"
    assert meta["chunk_status_table"]["doc-p2-c2"]["status"] == "failed"
    assert meta["chunk_status_table"]["doc-p1-c1"]["status"] == "processed"


def test_old_json_backward_compatibility():
    """Old format obligation JSON without new fields validates cleanly."""
    old_data = {
        "obligation_id": "OBL-001",
        "clause_id": "2.1",
        "text": "Priority service for customers.",
        "applicability": "retail customers",
        "product_type": "banking",
        "responsible_function": "Operations",
        "required_action": "Set up desks",
        "source": {
            "document_id": "doc1",
            "filename": "circular.pdf",
            "document_type": "circular",
            "page": 1,
            "excerpt": "Priority service for customers.",
            "chunk_id": "c1",
        },
        "supporting_excerpt": "Priority service for customers.",
        "confidence": 0.9,
    }
    obl = Obligation.model_validate(old_data)
    assert obl.obligation_id == "OBL-001"
    # Aliases
    assert obl.change_type == "NEW"
    assert obl.source_page == 1
    assert obl.deadline == "not_specified"

