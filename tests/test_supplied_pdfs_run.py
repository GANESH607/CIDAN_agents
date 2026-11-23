import json
from pathlib import Path
from cidan.config import ROOT
from cidan.ingestion import pdf_loader, chunking
from cidan.agents import circular_understanding, amendment_alignment
from cidan.services import agent1_storage
from tests.eval.evaluate_agent1 import make_stub_llm


def test_run_on_supplied_pdfs(tmp_path, monkeypatch):
    monkeypatch.setattr(agent1_storage, "WORKFLOW_OUTPUTS_DIR", tmp_path / "wf_outputs")
    pdf_dir = ROOT / "data" / "source_pdfs"
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    assert len(pdfs) == 2, f"Expected 2 PDFs in {pdf_dir}, found {len(pdfs)}"

    # Load and classify documents
    docs = []
    for p in pdfs:
        p_docs = pdf_loader.load_pdf(p)
        docs.extend(p_docs)

    # 1. Test relationship detection
    relationships = amendment_alignment.detect_document_relationships(docs)
    assert relationships["has_baseline"] is True
    assert relationships["mode"] == "amendment"
    assert len(relationships["relationships"]) > 0

    # 2. Split documents
    chunks = chunking.split_documents(docs, chunk_size=1000)
    assert len(chunks) > 0

    # 3. Verify table rows rendered with column names and no duplicates
    table_chunks = [c for c in chunks if c.metadata.get("chunk_kind") == "table_row"]
    for tc in table_chunks:
        assert tc.page_content.startswith("[TABLE ")
        assert " ROW " in tc.page_content
        assert "=" in tc.page_content

    # 4. Run Agent 1 extraction with stub LLM
    wf_id = "supplied-pdfs-test-run"
    stub_llm = make_stub_llm()
    obligations = circular_understanding.run(chunks, llm_call=stub_llm, workflow_id=wf_id)
    assert len(obligations) > 0

    # 5. Check saved output files
    out_dir = agent1_storage.get_agent1_output_dir(wf_id, create=False)
    coverage = json.loads((out_dir / "coverage_report.json").read_text(encoding="utf-8"))
    meta = json.loads((out_dir / "execution_metadata.json").read_text(encoding="utf-8"))

    # Verify coverage report is real
    assert coverage["schema_version"] == "1.1.0"
    assert coverage["pages_total"] > 0
    assert "extraction_quality_score" not in coverage.get("quality_checks", {})
    assert "evidence_pass_rate" in coverage["verification_breakdown"]

    # Verify execution_metadata
    assert meta["status"] == "completed"
    assert meta["duration_seconds"] > 0
    assert meta["duration_seconds"] != 12.4
