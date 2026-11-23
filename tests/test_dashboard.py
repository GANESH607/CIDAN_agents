from cidan.services import agent1_storage, agent2_storage, agent3_storage
from cidan.services.demo_seeder import CIDAN_001_ID, seed_cidan_001_if_needed
import dashboard


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

    # 5. Status badge helper supports draft status
    badge = dashboard.get_status_badge("draft")
    assert "badge-draft" in badge
    assert "Draft" in badge


