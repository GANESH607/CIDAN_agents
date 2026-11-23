from cidan.services import agent1_storage
from cidan.services.demo_seeder import CIDAN_001_ID, seed_cidan_001_if_needed


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
