import pymupdf
import pytest
from fastapi.testclient import TestClient

from cidan.api import app


@pytest.fixture(autouse=True)
def configure_test_access_token(monkeypatch):
    monkeypatch.setenv("CIDAN_ACCESS_TOKEN", "test-access-token")


client = TestClient(app, headers={"Authorization": "Bearer test-access-token"})


def make_pdf(text):
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def test_health_does_not_expose_api_key(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    monkeypatch.setenv("CIDAN_ACCESS_TOKEN", "test-access-token")
    response = client.get("/health")
    assert response.status_code == 200
    assert "test-secret" not in response.text
    assert "api_key" not in response.text.casefold()
    assert "test-access-token" not in response.text
    assert response.json()["llm_provider"] == "groq"
    assert response.json()["embedding_provider"] == "fastembed_local"
    assert response.json()["llm_max_output_tokens"] == 400


def test_groq_configuration_does_not_use_openai_key(monkeypatch):
    from cidan.config import get_settings

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "unused-openai-test-key")
    assert get_settings().llm_configured is False
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    assert get_settings().llm_configured is True


def test_documents_finds_both_demo_pdfs():
    response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["expected_count"] == 2
    assert data["found_count"] == 2


def test_api_operations_require_bearer_token():
    response = TestClient(app).get("/documents")
    assert response.status_code == 401


def test_api_operations_fail_closed_without_configured_token(monkeypatch):
    monkeypatch.delenv("CIDAN_ACCESS_TOKEN")
    response = client.get("/documents")
    assert response.status_code == 503


def test_upload_replaces_source_pdfs_with_classified_pair(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_PDF_DIRECTORY", str(tmp_path / "source_pdfs"))
    response = client.post(
        "/documents/upload",
        files={
            "handbook": (
                "sample_policy_handbook.pdf",
                make_pdf("Policy handbook sample text."),
                "application/pdf",
            ),
            "circular": (
                "sample_circular.pdf",
                make_pdf("Circular sample text."),
                "application/pdf",
            ),
        },
    )
    assert response.status_code == 201
    assert response.json()["message"].startswith("Both source PDFs were stored")
    documents = response.json()["documents"]
    assert [item["document_type"] for item in documents] == [
        "policy_handbook", "circular"
    ]
    assert len(list((tmp_path / "source_pdfs").glob("*.pdf"))) == 2


def test_upload_rejects_files_with_wrong_document_names(tmp_path, monkeypatch):
    monkeypatch.setenv("SOURCE_PDF_DIRECTORY", str(tmp_path / "source_pdfs"))
    response = client.post(
        "/documents/upload",
        files={
            "handbook": ("sample_circular.pdf", make_pdf("Circular text."), "application/pdf"),
            "circular": ("another_circular.pdf", make_pdf("Circular text."), "application/pdf"),
        },
    )
    assert response.status_code == 400
    assert not (tmp_path / "source_pdfs").exists()


def test_upload_rejects_non_pdf_content_without_replacing_source(tmp_path, monkeypatch):
    source_directory = tmp_path / "source_pdfs"
    source_directory.mkdir()
    original = source_directory / "existing_policy_handbook.pdf"
    original.write_bytes(b"existing")
    monkeypatch.setenv("SOURCE_PDF_DIRECTORY", str(source_directory))
    response = client.post(
        "/documents/upload",
        files={
            "handbook": ("new_policy_handbook.pdf", b"not a PDF", "application/pdf"),
            "circular": ("new_circular.pdf", make_pdf("Circular sample text."), "application/pdf"),
        },
    )
    assert response.status_code == 400
    assert original.read_bytes() == b"existing"


def test_approval_request_validation():
    response = client.post("/rules/not-found/approve", json={"reviewer_id": ""})
    assert response.status_code == 422


def test_agent1_endpoints_return_stored_results(tmp_path, monkeypatch):
    import cidan.services.agent1_storage as storage
    monkeypatch.setattr(storage, "WORKFLOW_OUTPUTS_DIR", tmp_path / "workflow_outputs")
    from cidan.services.demo_seeder import seed_cidan_001_if_needed
    seed_cidan_001_if_needed(force=True)

    # 1. Overview
    res = client.get("/workflows/CIDAN-001/agents/obligation-extraction")
    assert res.status_code == 200
    data = res.json()
    assert data["workflow_id"] == "CIDAN-001"
    assert data["obligations_extracted"] == 6
    assert data["coverage_percentage"] == 100.0
    assert data["change_analysis"]["modified"] == 3
    assert data["change_analysis"]["new"] == 3

    # 2. Obligations
    res_obls = client.get("/workflows/CIDAN-001/agents/obligation-extraction/obligations")
    assert res_obls.status_code == 200
    obls_data = res_obls.json()
    assert len(obls_data["obligations"]) == 6
    assert obls_data["obligations"][0]["obligation_id"] == "OBL-001"
    assert obls_data["obligations"][0]["clause_id"] == "2.1"
    assert obls_data["obligations"][0]["change_classification"] == "MODIFIED"

    # 3. Comparison
    res_comp = client.get("/workflows/CIDAN-001/agents/obligation-extraction/comparison")
    assert res_comp.status_code == 200
    comp_data = res_comp.json()
    assert comp_data["summary"]["modified"] == 3
    assert comp_data["summary"]["new"] == 3
    assert len(comp_data["comparison_items"]) == 6

    # 4. Evidence
    res_evi = client.get("/workflows/CIDAN-001/agents/obligation-extraction/evidence")
    assert res_evi.status_code == 200
    evi_data = res_evi.json()
    assert evi_data["total_citations"] == 6
    assert evi_data["evidence"][0]["exact_supporting_excerpt"]

    # 5. Metrics
    res_met = client.get("/workflows/CIDAN-001/agents/obligation-extraction/metrics")
    assert res_met.status_code == 200
    met_data = res_met.json()
    assert met_data["coverage_percentage"] == 100.0
    assert met_data["quality_checks"]["all_pages_processed"] is True
    assert met_data["quality_checks"]["extraction_quality_score"] == 94.0


def test_agent1_endpoints_404_on_missing_workflow(tmp_path, monkeypatch):
    import cidan.services.agent1_storage as storage
    monkeypatch.setattr(storage, "WORKFLOW_OUTPUTS_DIR", tmp_path / "workflow_outputs")
    res = client.get("/workflows/nonexistent-workflow-999/agents/obligation-extraction")
    assert res.status_code == 404


def test_agent3_endpoints_return_stored_results():
    from cidan.services.demo_seeder import seed_cidan_001_if_needed
    seed_cidan_001_if_needed(force=True)

    # 1. Summary
    res_summary = client.get("/workflows/CIDAN-001/agents/rule-proposal")
    assert res_summary.status_code == 200
    summary_data = res_summary.json()
    assert summary_data["total_proposals"] == 2
    assert summary_data["draft_count"] == 2

    # 2. Proposals
    res_props = client.get("/workflows/CIDAN-001/agents/rule-proposal/proposals")
    assert res_props.status_code == 200
    props_data = res_props.json()
    assert props_data["total_proposals"] == 2
    for p in props_data["proposals"]:
        assert p["status"] == "draft"
        assert p["existing_policy_provision"]
        assert p["proposed_rule"]

    # 3. Evidence
    res_evi = client.get("/workflows/CIDAN-001/agents/rule-proposal/evidence")
    assert res_evi.status_code == 200
    evi_data = res_evi.json()
    assert evi_data["total_citations"] >= 1

    # 4. Global /rules endpoint
    res_rules = client.get("/rules")
    assert res_rules.status_code == 200
    rules_list = res_rules.json()
    assert any(r.get("rule_id") == "RULE-2-5-SLA" for r in rules_list)


def test_agent3_endpoints_404_on_missing_workflow(tmp_path, monkeypatch):
    import cidan.services.agent3_storage as storage
    monkeypatch.setattr(storage, "WORKFLOW_OUTPUTS_DIR", tmp_path / "workflow_outputs")
    res = client.get("/workflows/nonexistent-workflow-999/agents/rule-proposal")
    assert res.status_code == 404


