import pytest
from unittest.mock import MagicMock

from cidan.agents import rule_authoring
from cidan.models import Citation, Obligation, PolicyFinding, RuleCondition, RuleProposal
from cidan.sandbox.schemas import RuleCondition as SbRuleCondition, SandboxRule
from cidan.services import agent3_storage
from cidan.services.demo_seeder import CIDAN_001_ID, seed_cidan_001_if_needed


def _make_citation(chunk_id="chunk-1", doc_type="circular", page=1, excerpt="Test excerpt"):
    return Citation(
        document_id="doc-1",
        filename="circular.pdf" if doc_type == "circular" else "handbook.pdf",
        document_type=doc_type,
        page=page,
        excerpt=excerpt,
        chunk_id=chunk_id,
    )


def _make_obligation(ob_id="OBL-001", clause="2.1"):
    cite = _make_citation(chunk_id=f"chunk-circ-{clause}", doc_type="circular", excerpt=f"Circular clause {clause} requirement")
    return {
        "obligation_id": ob_id,
        "clause_id": clause,
        "text": f"Requirement for {clause} with senior citizen service differentiation.",
        "applicability": "Senior citizens",
        "product_type": "retail_banking",
        "amount_threshold": None,
        "currency": None,
        "effective_date": "2026-04-01",
        "responsible_function": "Branch Operations",
        "required_action": f"Action for clause {clause}",
        "deadline_or_frequency": "immediate",
        "exceptions": [],
        "source": cite.model_dump(mode="json"),
        "confidence": 0.9,
    }


def _fast_empty_llm(*_args, **_kwargs):
    return rule_authoring.ProposalBatch(proposals=[])



def _make_finding(ob_id="OBL-001", status="partially_covered", clause="2.1"):
    circ_cite = _make_citation(chunk_id=f"chunk-circ-{clause}", doc_type="circular", excerpt=f"Circular clause {clause} requirement")
    pol_cite = _make_citation(chunk_id=f"chunk-pol-{clause}", doc_type="policy_handbook", excerpt=f"Internal policy clause {clause} position")
    return PolicyFinding(
        obligation_id=ob_id,
        status=status,
        matching_policy_provision=f"Clause {clause} Priority Service",
        circular_citation=circ_cite,
        policy_citations=[pol_cite],
        reasoning=f"Reasoning for {ob_id} with status {status}",
        missing_or_inconsistent="Missing tiered service bands",
        operational_impact="Inconsistent branch queuing",
        recommended_action="Update operational manual",
        confidence=0.82,
    )


def test_proposal_generation_only_for_eligible_findings():
    """Verify proposals are only generated for partially_covered and potential_conflict findings."""
    ob1 = _make_obligation("OBL-001", "2.1")
    ob2 = _make_obligation("OBL-002", "2.2")
    ob3 = _make_obligation("OBL-003", "2.3")
    ob4 = _make_obligation("OBL-004", "2.4")
    ob5 = _make_obligation("OBL-005", "2.5")

    f1 = _make_finding("OBL-001", "covered", "2.1")
    f2 = _make_finding("OBL-002", "partially_covered", "2.2")
    f3 = _make_finding("OBL-003", "not_found", "2.3")
    f4 = _make_finding("OBL-004", "requires_human_review", "2.4")
    f5 = _make_finding("OBL-005", "potential_conflict", "2.5")

    proposals = rule_authoring.run(
        [ob1, ob2, ob3, ob4, ob5],
        [f1, f2, f3, f4, f5],
        llm_call=_fast_empty_llm,
    )

    # Only OBL-002 (partially_covered) and OBL-005 (potential_conflict) are eligible
    assert len(proposals) == 2
    target_obs = {p.source_obligation_ids[0] for p in proposals}
    assert target_obs == {"OBL-002", "OBL-005"}


def test_no_eligible_findings_returns_empty():
    """Verify empty list returned when no eligible findings are present."""
    ob = _make_obligation("OBL-001", "2.1")
    f = _make_finding("OBL-001", "covered", "2.1")
    proposals = rule_authoring.run([ob], [f], llm_call=_fast_empty_llm)
    assert proposals == []


def test_rule_proposal_structure_and_required_fields():
    """Verify all 8 requested attributes are present on each generated proposal."""
    ob = _make_obligation("OBL-002", "2.2")
    f = _make_finding("OBL-002", "partially_covered", "2.2")

    proposals = rule_authoring.run([ob], [f], llm_call=_fast_empty_llm)
    assert len(proposals) == 1
    p = proposals[0]

    # 1. Obligation ID
    assert p.obligation_id == "OBL-002"
    assert "OBL-002" in p.source_obligation_ids

    # 2. Existing policy provision
    assert p.existing_policy_provision is not None
    assert "2.2" in p.existing_policy_provision

    # 3. Proposed rule
    assert p.proposed_rule is not None
    assert len(p.proposed_rule) > 0

    # 4. Reason for change
    assert p.reason_for_change is not None

    # 5. Operational impact
    assert p.operational_impact == "Inconsistent branch queuing"

    # 6. Source citations
    assert len(p.supporting_citations) >= 1
    assert any(c.document_type == "circular" for c in p.supporting_citations)

    # 7. Confidence
    assert 0.0 <= p.confidence <= 1.0

    # 8. Proposal status
    assert p.status == "draft"


def test_draft_status_enforced_even_if_llm_reports_validated():
    """Verify proposal status is strictly held at draft until human approval."""
    ob = _make_obligation("OBL-002", "2.2")
    f = _make_finding("OBL-002", "partially_covered", "2.2")

    circ_cite = Citation.model_validate(ob["source"])
    mock_proposal = RuleProposal(
        rule_id="RULE-2-2",
        version=1,
        business_purpose="Automated proposal",
        source_obligation_ids=["OBL-002"],
        description="Flag review for 2.2",
        trigger_conditions=[RuleCondition(field="is_emergency", operator="eq", value=True)],
        required_inputs=["transaction_id", "is_emergency"],
        decision_outcomes=["flag_review"],
        validation_criteria=["Check emergency condition"],
        rollback_considerations="Restore baseline",
        supporting_citations=[circ_cite],
        action="flag_review",
        status="validated",  # LLM attempts to return validated
    )

    def fake_llm(schema, _system, _prompt):
        return schema(proposals=[mock_proposal])

    result = rule_authoring.run([ob], [f], llm_call=fake_llm)
    assert len(result) == 1
    assert result[0].status == "draft"


def test_citation_validation_against_source_evidence():
    """Verify citations are checked and unsupported citations raise ValueError."""
    ob = _make_obligation("OBL-002", "2.2")
    f = _make_finding("OBL-002", "partially_covered", "2.2")

    unsupported_cite = _make_citation(chunk_id="chunk-unsupported", doc_type="circular", excerpt="Invented quote")
    bad_proposal = RuleProposal(
        rule_id="RULE-BAD-CITE",
        version=1,
        business_purpose="Bad citation test",
        source_obligation_ids=["OBL-002"],
        description="Flag review",
        trigger_conditions=[RuleCondition(field="is_emergency", operator="eq", value=True)],
        required_inputs=["transaction_id", "is_emergency"],
        decision_outcomes=["flag_review"],
        validation_criteria=["Validation check"],
        rollback_considerations="Rollback",
        supporting_citations=[unsupported_cite],
        action="flag_review",
    )

    def fake_llm(schema, _system, _prompt):
        return schema(proposals=[bad_proposal])

    with pytest.raises(ValueError, match="unsupported source citation"):
        rule_authoring.run([ob], [f], llm_call=fake_llm)


def test_duplicate_proposals_prevented():
    """Verify duplicate proposal handling for repeated obligation findings."""
    ob = _make_obligation("OBL-002", "2.2")
    f1 = _make_finding("OBL-002", "partially_covered", "2.2")
    f2 = _make_finding("OBL-002", "partially_covered", "2.2")

    proposals = rule_authoring.run([ob], [f1, f2], llm_call=_fast_empty_llm)
    # Duplicate obligation in findings list is deduplicated to at most one proposal
    assert len(proposals) == 1


def test_llm_exception_fails_safe_to_human_review():
    """Verify that external LLM failure fails safe to a human review draft proposal."""
    ob = _make_obligation("OBL-002", "2.2")
    f = _make_finding("OBL-002", "partially_covered", "2.2")

    def failing_llm(*_args, **_kwargs):
        raise RuntimeError("Groq rate limit exceeded / connection error")

    proposals = rule_authoring.run([ob], [f], llm_call=failing_llm)
    assert len(proposals) == 1
    p = proposals[0]
    assert p.status == "draft"
    assert p.action == "flag_review"
    assert p.baseline_rule is None
    assert p.sandbox_rule is None
    assert p.trigger_conditions == []
    assert p.required_inputs == []
    assert len(p.unresolved_questions) >= 1
    assert "human review" in p.unresolved_questions[0].lower()


def test_missing_obligation_is_recorded_for_human_review(tmp_path, monkeypatch):
    monkeypatch.setattr(agent3_storage, "WORKFLOW_OUTPUTS_DIR", tmp_path)
    finding = _make_finding("OBL-MISSING", "partially_covered")

    proposals = rule_authoring.run([], [finding], workflow_id="WF-MISSING-OBL")

    assert len(proposals) == 1
    proposal = proposals[0]
    assert proposal.source_obligation_ids == ["OBL-MISSING"]
    assert proposal.action == "flag_review"
    assert proposal.trigger_conditions == []
    assert proposal.required_inputs == []
    assert any("no matching obligation record" in reason for reason in proposal.review_reasons)
    assert proposal.supporting_citations == [finding.circular_citation, *finding.policy_citations[:2]]

    saved_proposals = agent3_storage.load_rule_proposals("WF-MISSING-OBL")
    assert saved_proposals["total_proposals"] == 1
    assert saved_proposals["proposals"][0]["action"] == "flag_review"


def test_empty_agent3_run_persists_zero_counts_and_execution_status(tmp_path, monkeypatch):
    monkeypatch.setattr(agent3_storage, "WORKFLOW_OUTPUTS_DIR", tmp_path)
    finding = _make_finding("OBL-001", "covered")

    assert rule_authoring.run([_make_obligation()], [finding], workflow_id="WF-NO-PROPOSALS") == []

    summary = agent3_storage.load_rule_summary("WF-NO-PROPOSALS")
    metadata = agent3_storage.load_execution_metadata("WF-NO-PROPOSALS")
    assert summary["total_proposals"] == 0
    assert summary["draft_count"] == 0
    assert summary["sandbox_ready_count"] == 0
    assert summary["human_review_required_count"] == 0
    assert metadata["status"] == "completed"


def test_agent3_storage_and_json_persistence(tmp_path, monkeypatch):
    """Verify independent JSON storage schema and loading for Agent 3."""
    monkeypatch.setattr(agent3_storage, "WORKFLOW_OUTPUTS_DIR", tmp_path)

    test_wf = "WF-AGENT3-TEST"
    ob = _make_obligation("OBL-002", "2.2")
    f = _make_finding("OBL-002", "partially_covered", "2.2")

    proposals = rule_authoring.run([ob], [f], workflow_id=test_wf, llm_call=_fast_empty_llm)
    assert len(proposals) == 1

    # Verify files created in independent storage directory
    wf_dir = tmp_path / test_wf / "agent_3_rule_authoring"
    assert (wf_dir / "rule_proposals.json").is_file()
    assert (wf_dir / "evidence_and_citations.json").is_file()
    assert (wf_dir / "rule_summary.json").is_file()
    assert (wf_dir / "execution_metadata.json").is_file()

    # Verify loading functions
    loaded_proposals = agent3_storage.load_rule_proposals(test_wf)
    assert loaded_proposals["workflow_id"] == test_wf
    assert loaded_proposals["total_proposals"] == 1
    assert loaded_proposals["proposals"][0]["obligation_id"] == "OBL-002"

    loaded_summary = agent3_storage.load_rule_summary(test_wf)
    assert loaded_summary["draft_count"] == 1

    loaded_evidence = agent3_storage.load_evidence_and_citations(test_wf)
    assert loaded_evidence["total_citations"] >= 1
    assert all(record["validation_status"] == "validated" for record in loaded_evidence["evidence"])
    assert all(record["is_valid"] is True for record in loaded_evidence["evidence"])

    wf_list = agent3_storage.list_agent3_workflows()
    assert test_wf in wf_list


def test_agent4_interface_compatibility_with_generated_proposal():
    """Verify that generated RuleProposal is completely compatible with Agent 4 testing_validation."""
    from cidan.agents import testing_validation

    # 1. Proposal requiring human review (no baseline/sandbox pair)
    ob = _make_obligation("OBL-002", "2.2")
    f = _make_finding("OBL-002", "partially_covered", "2.2")
    proposals = rule_authoring.run([ob], [f], llm_call=_fast_empty_llm)
    summary = testing_validation.run(proposals[0])
    assert summary.total == 0
    assert summary.pending == 1
    assert summary.sandbox_suite_id is not None

    # 2. Proposal with sandbox rule pair
    circ_cite = Citation.model_validate(ob["source"])
    pol_cite = f.policy_citations[0]
    sandbox_ready_proposal = RuleProposal(
        rule_id="RULE-SANDBOX-1",
        version=1,
        change_id="CHG-001",
        business_purpose="Sandbox test",
        source_obligation_ids=["OBL-002"],
        description="Flag loan amounts > 80000",
        trigger_conditions=[RuleCondition(field="amount", operator="gt", value=80000)],
        required_inputs=["transaction_id", "amount"],
        decision_outcomes=["second_review"],
        validation_criteria=["Boundary test"],
        rollback_considerations="Revert version",
        supporting_citations=[circ_cite, pol_cite],
        action="second_review",
        status="draft",
        baseline_rule=SandboxRule(
            rule_id="RULE-SANDBOX-1",
            version=1,
            change_id="CHG-001",
            product_type="retail_banking",
            conditions=[SbRuleCondition(field="amount", operator="gt", value=100000)],
            logical_operator="AND",
            outcome_when_matched="second_review",
            outcome_when_unmatched="standard",
        ),
        sandbox_rule=SandboxRule(
            rule_id="RULE-SANDBOX-1",
            version=2,
            change_id="CHG-001",
            product_type="retail_banking",
            conditions=[SbRuleCondition(field="amount", operator="gt", value=80000)],
            logical_operator="AND",
            outcome_when_matched="second_review",
            outcome_when_unmatched="standard",
        ),
        unrelated_product_types=["commercial_loans"],
    )

    # Calling testing_validation on sandbox_ready_proposal succeeds without schema issue
    summary2 = testing_validation.run(sandbox_ready_proposal)
    assert summary2 is not None


def test_cidan_001_seeded_agent3_outputs():
    """Verify benchmark CIDAN-001 has valid seeded Agent 3 outputs."""
    seed_cidan_001_if_needed(force=True)

    proposals_data = agent3_storage.load_rule_proposals(CIDAN_001_ID)
    assert proposals_data["workflow_id"] == CIDAN_001_ID
    assert proposals_data["total_proposals"] == 2
    for p in proposals_data["proposals"]:
        assert p["status"] == "draft"
        assert p["obligation_id"] in ["OBL-002", "OBL-005"]
        assert p["existing_policy_provision"]
        assert p["proposed_rule"]

    summary = agent3_storage.load_rule_summary(CIDAN_001_ID)
    assert summary["draft_count"] == 2
    assert summary["sandbox_ready_count"] >= 1
