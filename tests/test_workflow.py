from cidan.workflow import graph as workflow_graph
from cidan.workflow.graph import run_graph
from cidan.models import (
    Citation,
    Obligation,
    PolicyFinding,
    RuleProposal,
    TestSummary as Agent4TestSummary,
)


def test_workflow_stops_when_ingestion_fails(monkeypatch):
    def fail_ingestion():
        raise RuntimeError("missing API key")

    monkeypatch.setattr(workflow_graph, "ingest", fail_ingestion)
    result = run_graph("blocked-test")
    assert result["stage"] == "failed"
    assert result["error"].startswith("ingestion:")
    assert "impact_reporting" in result["blocked_stages"]
    assert "obligations" not in result
    assert "report" not in result


def test_workflow_keeps_proposal_draft_after_successful_agent4_validation(monkeypatch):
    from cidan.ingestion import retrieval

    citation = Citation(
        document_id="doc",
        filename="circular.pdf",
        document_type="circular",
        page=1,
        excerpt="Synthetic requirement.",
        chunk_id="circular-1",
    )
    obligation = Obligation(
        obligation_id="OBL-1",
        clause_id="1",
        text="Synthetic requirement.",
        applicability="synthetic products",
        product_type="personal_loan",
        responsible_function="Review",
        required_action="Review",
        source=citation,
        supporting_excerpt=citation.excerpt,
    )
    finding = PolicyFinding(
        obligation_id="OBL-1",
        status="partially_covered",
        circular_citation=citation,
        reasoning="Synthetic finding.",
        missing_or_inconsistent="A rule change is required.",
        operational_impact="Review process changes.",
        recommended_action="Update the rule.",
        confidence=0.8,
    )
    proposal = RuleProposal(
        rule_id="RULE-1",
        version=2,
        change_id="CHANGE-1",
        business_purpose="Synthetic test proposal.",
        source_obligation_ids=["OBL-1"],
        description="Synthetic proposal.",
        trigger_conditions=[{"field": "amount", "operator": "gt", "value": 10}],
        required_inputs=["amount"],
        decision_outcomes=["review"],
        validation_criteria=["Validate locally."],
        rollback_considerations="Restore the baseline.",
        supporting_citations=[citation],
        action="second_review",
    )

    monkeypatch.setattr(workflow_graph, "ingest", lambda: None)
    monkeypatch.setattr(retrieval, "retrieve_all", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(retrieval, "retrieve_policy_candidates", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        workflow_graph.circular_understanding,
        "run",
        lambda *_args, **_kwargs: [obligation],
    )
    monkeypatch.setattr(
        workflow_graph.policy_mapping,
        "run",
        lambda *_args, **_kwargs: [finding],
    )
    monkeypatch.setattr(workflow_graph.policy_mapping, "_save_outputs", lambda *_args: None)
    monkeypatch.setattr(
        workflow_graph.rule_authoring,
        "run",
        lambda *_args, **_kwargs: [proposal],
    )
    monkeypatch.setattr(
        workflow_graph.testing_validation,
        "run",
        lambda *_args, **_kwargs: Agent4TestSummary(
            total=50,
            passed=50,
            failed=0,
            skipped=0,
            invalid=0,
            pending=0,
            pass_rate=1.0,
            results=[],
        ),
    )
    monkeypatch.setattr(workflow_graph.reporting, "run", lambda *_args, **_kwargs: {})

    result = run_graph("draft-through-sandbox")

    assert result["stage"] == "awaiting_human_review"
    assert result["proposals"][0]["status"] == "draft"
