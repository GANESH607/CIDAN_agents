import pytest
from langchain_core.documents import Document

from cidan.config import ROOT
from cidan.ingestion import pdf_loader
from cidan.agents import amendment_alignment, circular_understanding


def test_clause_normalization_and_metadata_standardization():
    """Verify that normalize_clause_id handles diverse representations and pdf_loader sets standardized fields."""
    norm = pdf_loader.normalize_clause_id
    assert norm("Clause 2.1") == "2.1"
    assert norm("clause 2.1") == "2.1"
    assert norm("2.1 Eligibility") == "2.1"
    assert norm("Clause 2.5: Grievance SLA") == "2.5"
    assert norm("Section 3.2") == "3.2"
    assert norm("Para 4.1") == "4.1"
    assert norm("2.1") == "2.1"
    assert norm("Article 5(2)") == "Article 5(2)"

    # Test detection from text
    sample_text = (
        "Section 1.1: General Scope.\n"
        "[TABLE t1 ROW 1] Clause=2.1 Priority service | col2=val2\n"
        "[TABLE t1 ROW 2] Clause=2.2 Assisted digital service | col2=val2\n"
        "[TABLE t1 ROW 3] Clause=2.4 Grievance handling | col2=val2\n"
    )
    detected = pdf_loader.detect_clause_ids(sample_text)
    assert "1.1" in detected
    assert "2.1" in detected
    assert "2.2" in detected
    assert "2.4" in detected

    # Test missing clause gap detection using normalized identifiers
    gaps = circular_understanding.detect_clause_gaps(detected)
    assert "2.3" in gaps


def test_amendment_table_alignment_and_sla_diff():
    """Verify table row parsing, classification, and SLA numeric diffing."""
    row_mod = (
        "[TABLE t2 ROW 5] Clause=2.5 Grievance SLA | "
        "2025 position=Acknowledge within 2 working days; target resolution within 10 working days. | "
        "2026 amended position=Acknowledge senior-citizen complaints within 1 working day; target resolution within 7 working days. | "
        "Change=Modified"
    )
    row_new = (
        "[TABLE t2 ROW 2] Clause=2.2 Assisted digital service | "
        "2025 position=General assistance is provided on request. | "
        "2026 amended position=Offer assisted digital-banking support to customers aged 60+. Staff must never ask for PIN, password or OTP. | "
        "Change=New"
    )

    pos_mod = amendment_alignment.extract_table_positions(row_mod)
    assert pdf_loader.normalize_clause_id(pos_mod["clause"]) == "2.5"
    assert "2 working days" in pos_mod["previous"]
    assert "1 working day" in pos_mod["amended"]
    assert pos_mod["change"] == "Modified"

    pos_new = amendment_alignment.extract_table_positions(row_new)
    assert pdf_loader.normalize_clause_id(pos_new["clause"]) == "2.2"
    assert pos_new["change"] == "New"

    # Test align_obligation on table rows
    base_doc = Document(
        page_content="Clause 2.5: Complaints must be acknowledged within 2 working days and resolved in 10 working days.",
        metadata={"document_id": "base-doc", "filename": "Policy_2025.pdf", "page": 2, "chunk_id": "b-c1", "clause_ids": ["2.5"]},
    )
    rel = {"has_baseline": True, "mode": "amendment", "baseline_doc_id": "base-doc"}

    class_mod, prev_mod, cit_mod = amendment_alignment.align_obligation(
        clause_id="2.5",
        text=pos_mod["amended"],
        relationships=rel,
        baseline_docs=[base_doc],
        table_cell_text=row_mod,
    )
    assert class_mod == "MODIFIED"
    assert prev_mod == pos_mod["previous"]
    assert cit_mod is not None

    class_new, prev_new, cit_new = amendment_alignment.align_obligation(
        clause_id="2.2",
        text=pos_new["amended"],
        relationships=rel,
        baseline_docs=[base_doc],
        table_cell_text=row_new,
    )
    assert class_new == "NEW"

    # Test SLA diff values
    diffs = amendment_alignment.diff_values(pos_mod["previous"], pos_mod["amended"])
    old_vals = [d["old"] for d in diffs]
    new_vals = [d["new"] for d in diffs]
    assert "2 working days" in old_vals or "2 days" in old_vals
    assert "1 working day" in new_vals or "1 day" in new_vals


def test_document_relationship_detection_unrelated_and_ambiguous():
    """Verify document relationship logic does not assume amendment merely because baseline exists."""
    base_doc = Document(
        page_content="IT Security Policy 2025. Clause 1.1: Password rotation every 90 days. Clause 1.2: MFA required.",
        metadata={"document_id": "it-base", "filename": "IT_Security_Policy_2025.pdf", "document_type": "baseline_policy", "page": 1, "clause_ids": ["1.1", "1.2"]},
    )

    # 1. Completely unrelated document
    unrelated_doc = Document(
        page_content="Retail Credit Card Guidelines 2026. Clause 7.1: Minimum repayment is 5% of outstanding balance.",
        metadata={"document_id": "card-reg", "filename": "Credit_Card_Norms_2026.pdf", "document_type": "circular", "page": 1, "clause_ids": ["7.1"]},
    )
    rel_unrelated = amendment_alignment.detect_document_relationships([base_doc, unrelated_doc])
    assert rel_unrelated["has_baseline"] is False
    assert rel_unrelated["mode"] == "unrelated"
    assert len(rel_unrelated["relationships"]) == 0

    # 2. Ambiguous document: mentions 'amendment' generically but zero shared clauses and no baseline reference
    ambiguous_doc = Document(
        page_content="General Regulatory Amendment Circular. This circular amends general guidelines across banking operations.",
        metadata={"document_id": "amb-reg", "filename": "General_Amendment_2026.pdf", "document_type": "circular", "page": 1, "clause_ids": ["9.1"]},
    )
    rel_ambiguous = amendment_alignment.detect_document_relationships([base_doc, ambiguous_doc])
    assert rel_ambiguous["has_baseline"] is False
    assert rel_ambiguous["mode"] == "NEEDS_REVIEW"


def test_all_six_amendments_classified_correctly_on_supplied_pdfs():
    """Verify all 6 amendments in the supplied 2026 amendment table are classified correctly."""
    pdf_dir = ROOT / "data" / "source_pdfs"
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    assert len(pdfs) == 2

    base_docs = pdf_loader.load_pdf(pdfs[0])
    reg_docs = pdf_loader.load_pdf(pdfs[1])

    rel = amendment_alignment.detect_document_relationships(base_docs + reg_docs)
    assert rel["has_baseline"] is True
    assert rel["mode"] == "amendment"

    # Extract all table rows from the amendment document
    table_rows = []
    for d in reg_docs:
        for line in d.page_content.split("\n"):
            if line.startswith("[TABLE t2 ROW "):
                table_rows.append(line)

    assert len(table_rows) == 6, f"Expected 6 amendment rows in Table t2, found {len(table_rows)}"

    expected_results = {
        "2.1": "MODIFIED",
        "2.2": "NEW",
        "2.3": "NEW",
        "2.4": "NEW",
        "2.5": "MODIFIED",
        "2.6": "MODIFIED",
    }

    actual_classifications = {}
    for row in table_rows:
        pos = amendment_alignment.extract_table_positions(row)
        cid = pdf_loader.normalize_clause_id(pos["clause"])
        classification, prev_req, base_cit = amendment_alignment.align_obligation(
            clause_id=cid,
            text=pos["amended"],
            relationships=rel,
            baseline_docs=base_docs,
            table_cell_text=row,
        )
        actual_classifications[cid] = classification
        assert prev_req is not None, f"Clause {cid} must have previous_requirement extracted from table"

    assert actual_classifications == expected_results
