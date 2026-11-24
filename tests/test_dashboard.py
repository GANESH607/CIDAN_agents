from cidan.agents import testing_validation
from cidan.models import TestSummary as Agent4TestSummary
from cidan.services import agent1_storage, agent2_storage, agent3_storage
from cidan.services.demo_seeder import CIDAN_001_ID, seed_cidan_001_if_needed
import dashboard
from streamlit.testing.v1 import AppTest


def test_dashboard_data_connection():
    """Verify that dashboard loads actual Agent 1 outputs from independent JSON storage."""
    seed_cidan_001_if_needed(force=True)

    summary = agent1_storage.load_agent1_summary(CIDAN_001_ID)
    assert summary["workflow_id"] == CIDAN_001_ID
    assert summary["obligations_extracted"] == 6
    assert summary["coverage_percentage"] == 100.0

    obligations = agent1_storage.load_extracted_obligations(CIDAN_001_ID)
    assert len(obligations["obligations"]) == 6
    assert obligations["obligations"][0]["clause_id"] == "2.1"
    assert obligations["obligations"][0]["change_classification"] == "MODIFIED"

    comparison = agent1_storage.load_amendment_comparison(CIDAN_001_ID)
    assert comparison["summary"]["new"] == 3
    assert comparison["summary"]["modified"] == 3
    assert len(comparison["comparison_items"]) == 6

    evidence = agent1_storage.load_evidence_and_citations(CIDAN_001_ID)
    assert len(evidence["evidence"]) == 6
    assert evidence["evidence"][0]["exact_supporting_excerpt"]

    coverage = agent1_storage.load_coverage_report(CIDAN_001_ID)
    assert coverage["quality_checks"]["all_pages_processed"] is True
    assert coverage["quality_checks"]["extraction_quality_score"] == 94.0


def test_dashboard_agent2_data_connection():
    """Verify that dashboard loads actual Agent 2 outputs from independent JSON storage."""
    seed_cidan_001_if_needed(force=True)

    # 1. Workflow listing includes Agent 2 workflows
    wf_list = agent2_storage.list_agent2_workflows()
    assert CIDAN_001_ID in wf_list

    # 2. Findings load and contain all 5 status classifications
    findings_data = agent2_storage.load_policy_findings(CIDAN_001_ID)
    assert findings_data["workflow_id"] == CIDAN_001_ID
    findings = findings_data["findings"]
    assert len(findings) == 6

    statuses = {f["status"] for f in findings}
    assert "covered" in statuses
    assert "partially_covered" in statuses
    assert "potential_conflict" in statuses
    assert "not_found" in statuses
    assert "requires_human_review" in statuses

    # 3. Separated confidence fields are present and valid
    for f in findings:
        assert "confidence" in f
        assert "evidence_confidence" in f
        assert "model_reported_confidence" in f
        assert 0.0 <= f["confidence"] <= 1.0
        assert 0.0 <= f["evidence_confidence"] <= 1.0
        assert 0.0 <= f["model_reported_confidence"] <= 1.0

    # 4. Summary metrics
    summary = agent2_storage.load_mapping_summary(CIDAN_001_ID)
    assert summary["total_findings"] == 6
    assert summary["status_counts"]["covered"] >= 1
    assert summary["status_counts"]["partially_covered"] >= 1

    # 5. Evidence and citations load
    evidence = agent2_storage.load_evidence_and_citations(CIDAN_001_ID)
    assert "evidence" in evidence
    assert len(evidence["evidence"]) >= 1

    # 6. Status badge formatting helper in dashboard
    for st_name in ["covered", "partially_covered", "potential_conflict", "not_found", "requires_human_review"]:
        badge = dashboard.get_status_badge(st_name)
        assert "badge" in badge
        assert "span" in badge


def test_dashboard_agent3_data_connection():
    """Verify that dashboard loads actual Agent 3 outputs from independent JSON storage."""
    seed_cidan_001_if_needed(force=True)

    # 1. Workflow listing includes Agent 3 workflows
    wf_list = agent3_storage.list_agent3_workflows()
    assert CIDAN_001_ID in wf_list

    # 2. Proposals load and contain required fields
    proposals_data = agent3_storage.load_rule_proposals(CIDAN_001_ID)
    assert proposals_data["workflow_id"] == CIDAN_001_ID
    proposals = proposals_data["proposals"]
    assert len(proposals) == 2

    for p in proposals:
        assert p["status"] == "draft"
        assert p["obligation_id"]
        assert p["existing_policy_provision"]
        assert p["proposed_rule"]
        assert p["reason_for_change"]
        assert p["operational_impact"]
        assert 0.0 <= p["confidence"] <= 1.0
        assert len(p["supporting_citations"]) >= 1

    # 3. Summary metrics
    summary = agent3_storage.load_rule_summary(CIDAN_001_ID)
    assert summary["total_proposals"] == 2
    assert summary["draft_count"] == 2

    # 4. Evidence and citations load
    evidence = agent3_storage.load_evidence_and_citations(CIDAN_001_ID)
    assert "evidence" in evidence
    assert len(evidence["evidence"]) >= 1

    metadata = agent3_storage.load_execution_metadata(CIDAN_001_ID)
    assert metadata["status"] == "completed"

    # 5. Status badge helper supports draft status
    badge = dashboard.get_status_badge("draft")
    assert "badge-draft" in badge
    assert "Draft" in badge


def test_agent3_sidebar_selection_loads_actual_dashboard_outputs(monkeypatch):
    seed_cidan_001_if_needed(force=True)
    loaded_outputs = set()
    loader_names = (
        "load_rule_proposals",
        "load_rule_summary",
        "load_evidence_and_citations",
        "load_execution_metadata",
    )
    for loader_name in loader_names:
        original_loader = getattr(agent3_storage, loader_name)

        def track_loader(workflow_id, _loader=original_loader, _name=loader_name):
            loaded_outputs.add(_name)
            return _loader(workflow_id)

        monkeypatch.setattr(agent3_storage, loader_name, track_loader)

    app = AppTest.from_file(dashboard.__file__).run(timeout=10)
    agent_selection = next(radio for radio in app.radio if radio.label == "Agent Selection")
    agent_selection.set_value(agent_selection.options[2]).run()

    assert any(
        caption.value.startswith("Agent 3 execution status:")
        for caption in app.caption
    )
    assert loaded_outputs == set(loader_names)


def test_dashboard_agent3_citation_validation_uses_backend_result():
    citation = {
        "document_id": "doc-1",
        "filename": "circular.pdf",
        "document_type": "circular",
        "page": 1,
        "chunk_id": "chunk-1",
        "excerpt": "Evidence excerpt",
    }

    assert dashboard.get_agent3_citation_validation_status(
        {"evidence": [{"rule_id": "RULE-1", **citation}]},
        "RULE-1",
        citation,
    ) == "not available"
    assert dashboard.get_agent3_citation_validation_status(
        {"evidence": [{"rule_id": "RULE-1", **citation, "validation_status": "validated"}]},
        "RULE-1",
        citation,
    ) == "validated"
    assert dashboard.get_agent3_citation_validation_status(
        {"evidence": [{"rule_id": "RULE-2", **citation, "validation_status": "validated"}]},
        "RULE-1",
        citation,
    ) == "not available"


def test_dashboard_agent3_metrics_show_zero_counts_without_proposals():
    assert dashboard.get_agent3_dashboard_metrics([]) == {
        "total_proposals": 0,
        "draft_count": 0,
        "sandbox_ready_count": 0,
        "human_review_count": 0,
        "high_risk_count": 0,
        "action_count": 0,
    }


def test_agent4_runs_and_selects_the_new_suite_for_selected_workflow(
    tmp_path, monkeypatch
):
    seed_cidan_001_if_needed(force=True)
    monkeypatch.setenv("OUTPUTS_DIRECTORY", str(tmp_path))
    calls = []
    suite_ids = []

    def fake_run(proposal):
        calls.append(proposal)
        from cidan.sandbox import service as sandbox_service

        suite = sandbox_service.record_manual_review(
            document_id=proposal.supporting_citations[0].document_id,
            rule_id=proposal.rule_id,
            change_id=proposal.change_id,
            reason="Test-only output for dashboard selection.",
        )
        suite_ids.append(suite["suite_id"])
        return Agent4TestSummary(
            total=0,
            passed=0,
            failed=0,
            skipped=0,
            invalid=0,
            pending=1,
            pass_rate=None,
            results=[],
            sandbox_suite_id=suite["suite_id"],
        )

    monkeypatch.setattr(testing_validation, "run", fake_run)
    app = AppTest.from_file(dashboard.__file__).run(timeout=10)
    agent_selection = next(radio for radio in app.radio if radio.label == "Agent Selection")
    agent_selection.set_value(agent_selection.options[3]).run(timeout=10)

    generate_button = next(
        button
        for button in app.button
        if button.label == "Generate and run 50 synthetic tests"
    )
    generate_button.click().run(timeout=10)

    assert len(calls) == 1
    assert calls[0].rule_id == "RULE-2-5-SLA"
    assert calls[0].sandbox_rule.version == 2
    suite_selector = next(item for item in app.selectbox if item.label == "Sandbox suite")
    assert suite_selector.value == suite_ids[0]


