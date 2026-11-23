import json
import re
import sqlite3
from collections import Counter

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from cidan.api import app
from cidan.agents import rule_authoring, testing_validation
from cidan.models import Citation, PolicyFinding, RuleCondition, RuleProposal
from cidan.sandbox import generation, repository, service
from cidan.sandbox.execution import execute_suite
from cidan.sandbox.rule_engine import evaluate
from cidan.sandbox.schemas import (
    RegressionResult,
    SandboxRule,
)
from cidan.sandbox.validation import scenario_key, validate_case, validate_cases


def make_rule(version: int, operator: str = "gte", threshold: int = 60) -> SandboxRule:
    return SandboxRule(
        rule_id="loan-age-rule",
        version=version,
        change_id=f"loan-age-change-v{version}",
        product_type="personal_loan",
        conditions=[
            {"field": "customer_age", "operator": operator, "value": threshold}
        ],
        outcome_when_matched="ELIGIBLE",
        outcome_when_unmatched="NOT_ELIGIBLE",
    )


def make_candidate(category: str, index: int, old: SandboxRule, new: SandboxRule):
    if category == "positive_normal":
        product, age = "personal_loan", 80 + index
    elif category == "negative":
        product, age = "personal_loan", 20 + index
    elif category == "boundary_value":
        product, age = "personal_loan", (59, 60, 61, 69, 70, 71, 59, 60, 69, 70)[index]
    elif category == "edge_case":
        product, age = "personal_loan", 0 if index % 2 == 0 else 120 + index
    elif category == "regression":
        product, age = "credit_card", 40 + index
    elif category == "missing_data_exception":
        product, age = "personal_loan", None
    else:
        product, age = "personal_loan", 61 + index

    inputs = {"product_type": product}
    if age is not None:
        inputs["customer_age"] = age
    return {
        "scenario": f"{category} input scenario {index}",
        "input_data": inputs,
    }


def generated_candidates(old: SandboxRule, new: SandboxRule):
    next_indexes = Counter()

    def fake_llm(schema, _system, prompt):
        match = re.search(
            r"Generate exactly (\d+) cases in category '([^']+)'", prompt
        )
        assert match
        count, category = int(match.group(1)), match.group(2)
        start = next_indexes[category]
        next_indexes[category] += count
        return schema(cases=[
            make_candidate(category, index, old, new)
            for index in range(start, start + count)
        ])

    return fake_llm


@pytest.mark.parametrize(
    ("operator", "threshold", "actual", "expected"),
    [
        ("gt", 10, 11, True),
        ("gt", 10, 10, False),
        ("gte", 10, 10, True),
        ("lt", 10, 9, True),
        ("lt", 10, 10, False),
        ("lte", 10, 10, True),
        ("eq", 10, 10, True),
        ("eq", 10, 11, False),
        ("ne", 10, 11, True),
        ("ne", 10, 10, False),
        ("between", 10, 15, True),
        ("between", 10, 20, True),
        ("between", 10, 9, False),
    ],
)
def test_each_comparison_operator(operator, threshold, actual, expected):
    condition = {
        "field": "amount",
        "operator": operator,
        "value": threshold,
    }
    if operator == "between":
        condition["upper_value"] = 20
    rule = SandboxRule(
        rule_id="amount-rule",
        version=1,
        change_id="amount-change",
        product_type="loan",
        conditions=[condition],
        outcome_when_matched="YES",
        outcome_when_unmatched="NO",
    )
    assert evaluate(rule, {"product_type": "loan", "amount": actual}).outcome == (
        "YES" if expected else "NO"
    )


def test_boolean_and_or_and_between_boundaries():
    boolean_rule = SandboxRule(
        rule_id="bool-rule",
        version=1,
        change_id="bool-change",
        product_type="loan",
        logical_operator="AND",
        conditions=[
            {"field": "is_emergency", "operator": "eq", "value": True},
            {"field": "amount", "operator": "between", "value": 10, "upper_value": 20},
        ],
        outcome_when_matched="YES",
        outcome_when_unmatched="NO",
    )
    assert evaluate(
        boolean_rule,
        {"product_type": "loan", "is_emergency": True, "amount": 10},
    ).outcome == "YES"
    or_rule = boolean_rule.model_copy(update={"logical_operator": "OR"})
    assert evaluate(
        or_rule,
        {"product_type": "loan", "is_emergency": True, "amount": 0},
    ).outcome == "YES"
    assert evaluate(
        boolean_rule,
        {"product_type": "loan", "is_emergency": "true", "amount": 10},
    ).status == "invalid_input"


def test_missing_invalid_and_manual_review_inputs_fail_closed():
    rule = make_rule(1)
    missing = evaluate(rule, {"product_type": "personal_loan"})
    assert missing.outcome == "INVALID_INPUT"
    assert missing.status == "missing_input"
    invalid = evaluate(
        rule, {"product_type": "personal_loan", "customer_age": "sixty"}
    )
    assert invalid.outcome == "INVALID_INPUT"
    assert invalid.status == "invalid_input"
    manual = rule.model_copy(update={
        "conditions": [],
        "manual_review_reason": "Policy wording is ambiguous.",
    })
    assert evaluate(manual, {}).status == "manual_review"


def test_hypothetical_age_threshold_change_is_evaluated_independently():
    baseline, proposed = make_rule(1), make_rule(2, threshold=70)
    input_data = {"product_type": "personal_loan", "customer_age": 65}
    old_result = evaluate(baseline, input_data)
    proposed_result = evaluate(proposed, input_data)
    assert old_result.outcome == "ELIGIBLE"
    assert proposed_result.outcome == "NOT_ELIGIBLE"
    assert old_result.outcome != proposed_result.outcome


def test_invalid_rules_and_malformed_conditions_are_rejected():
    with pytest.raises(ValidationError):
        RuleCondition(field="amount", operator="greater_than", value=10)
    with pytest.raises(ValidationError):
        RuleCondition(field="__import__('os')", operator="eq", value="x")
    invalid = make_rule(1).model_dump(mode="json")
    invalid["conditions"][0]["operator"] = "greater_than"
    result = evaluate(invalid, {"product_type": "personal_loan", "customer_age": 70})
    assert result.status == "manual_review"
    assert result.outcome == "MANUAL_REVIEW"


def test_generation_enforces_exact_distribution_unique_cases_and_ids():
    old, new = make_rule(1), make_rule(2, threshold=70)
    cases = generation.generate_cases(
        old,
        new,
        unrelated_product_types=["credit_card", "home_loan"],
        llm_call=generated_candidates(old, new),
    )
    assert len(cases) == 50
    assert len({case.test_id for case in cases}) == 50
    assert len({scenario_key(case) for case in cases}) == 50
    assert Counter(case.category for case in cases) == Counter(generation.CASE_DISTRIBUTION)


def test_groq_generation_uses_json_mode_for_case_batch(monkeypatch):
    old, new = make_rule(1), make_rule(2, threshold=70)
    fake = generated_candidates(old, new)
    methods = []

    def invoke(schema, system, prompt, **kwargs):
        methods.append(kwargs["method"])
        return fake(schema, system, prompt)

    monkeypatch.setattr(generation, "invoke_structured", invoke)
    cases = generation.generate_cases(
        old,
        new,
        unrelated_product_types=["credit_card", "home_loan"],
    )

    assert len(cases) == 50
    assert methods and set(methods) == {"json_mode"}


def test_generation_rejects_bad_counts_and_duplicate_scenarios():
    old, new = make_rule(1), make_rule(2, threshold=70)

    def wrong_count(schema, _system, _prompt):
        return schema(cases=[
            make_candidate("positive_normal", 1, old, new),
            make_candidate("positive_normal", 2, old, new),
            make_candidate("positive_normal", 3, old, new),
        ])

    with pytest.raises(ValueError, match="expected 5"):
        generation.generate_cases(
            old,
            new,
            unrelated_product_types=["credit_card"],
            llm_call=wrong_count,
        )

    def duplicate(schema, _system, prompt):
        count = int(re.search(r"Generate exactly (\d+)", prompt).group(1))
        category = re.search(r"category '([^']+)'", prompt).group(1)
        candidate = make_candidate(category, 1, old, new)
        return schema(cases=[candidate] * count)

    with pytest.raises(ValueError, match="duplicate"):
        generation.generate_cases(
            old,
            new,
            unrelated_product_types=["credit_card"],
            llm_call=duplicate,
        )


def test_validation_rejects_unsupported_inputs_and_misclassified_edge_cases():
    old, new = make_rule(1), make_rule(2, threshold=70)
    cases = generation.generate_cases(
        old,
        new,
        unrelated_product_types=["credit_card"],
        llm_call=generated_candidates(old, new),
    )
    unsupported = cases[0].model_copy(update={
        "input_data": {**cases[0].input_data, "unrelated_threshold": 42}
    })
    with pytest.raises(ValueError, match="unsupported input fields"):
        validate_case(unsupported, old, new, ["credit_card"])

    boundary_case = next(case for case in cases if case.category == "boundary_value")
    ordinary = boundary_case.model_copy(update={"category": "edge_case"})
    with pytest.raises(ValueError, match="edge case"):
        validate_case(ordinary, old, new, ["credit_card"])

    duplicate_scenario_cases = list(cases)
    duplicate_scenario_cases[1] = duplicate_scenario_cases[1].model_copy(
        update={"scenario": duplicate_scenario_cases[0].scenario}
    )
    with pytest.raises(ValueError, match="duplicate scenario descriptions"):
        validate_cases(
            duplicate_scenario_cases, old, new, ["credit_card"]
        )


def test_invalid_groq_response_and_provider_failure_are_not_success(tmp_path, monkeypatch):
    old, new = make_rule(1), make_rule(2, threshold=70)
    monkeypatch.setenv("OUTPUTS_DIRECTORY", str(tmp_path))

    def malformed(schema, _system, _prompt):
        return schema(cases=[{"category": "unknown"}])

    with pytest.raises(ValidationError):
        generation.generate_cases(
            old,
            new,
            unrelated_product_types=["credit_card"],
            llm_call=malformed,
        )

    def provider_failure(_schema, _system, _prompt):
        raise RuntimeError("Groq unavailable")

    with pytest.raises(RuntimeError, match="Groq unavailable"):
        service.generate_suite(
            document_id="doc",
            change_id=new.change_id,
            baseline_rule=old,
            proposed_rule=new,
            unrelated_product_types=["credit_card"],
            llm_call=provider_failure,
        )
    failed_suite = service.list_suites()[0]
    assert failed_suite["status"] == "generation_failed"
    stored = repository.load_suite(failed_suite["suite_id"])
    assert stored["test_cases"] == []
    assert stored["failure_reason"] == "Groq unavailable"


def test_invalid_persisted_case_fails_and_blocks_approval(tmp_path, monkeypatch):
    from cidan.services.approval_service import approve_rule
    from cidan.workflow import persistence

    old, new = make_rule(1), make_rule(2, threshold=70)
    monkeypatch.setenv("OUTPUTS_DIRECTORY", str(tmp_path / "outputs"))
    monkeypatch.setattr(persistence, "WORKFLOWS_DIR", tmp_path / "workflows")
    monkeypatch.setattr(persistence, "AUDIT_PATH", tmp_path / "audit.jsonl")
    suite = service.generate_suite(
        document_id="doc",
        change_id=new.change_id,
        baseline_rule=old,
        proposed_rule=new,
        unrelated_product_types=["credit_card"],
        llm_call=generated_candidates(old, new),
    )
    database = sqlite3.connect(tmp_path / "outputs" / "sandbox.sqlite3")
    row = database.execute(
        "SELECT test_id, case_json FROM test_cases WHERE suite_id = ? ORDER BY rowid LIMIT 1",
        (suite["suite_id"],),
    ).fetchone()
    corrupted = json.loads(row[1])
    corrupted["expected_old_result"] = "INCORRECT_EXPECTATION"
    corrupted["expected_outcome"] = "behavior_changed"
    database.execute(
        "UPDATE test_cases SET case_json = ? WHERE test_id = ?",
        (json.dumps(corrupted), row[0]),
    )
    database.commit()
    database.close()

    with pytest.raises(ValueError, match="expectations do not match deterministic evaluation"):
        service.run_suite(suite["suite_id"])
    report = service.get_suite(suite["suite_id"])
    assert report["status"] == "execution_failed"
    assert "expectations do not match deterministic evaluation" in report["failure_reason"]

    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "workflow.json").write_text(
        '{"workflow_id":"workflow","proposals":[{"rule_id":"loan-age-rule","version":2,'
        '"change_id":"loan-age-change-v2","status":"validated"}],'
        '"tests":[{"failed":0,"invalid":0,"total":50,"passed":50}]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="50 passing executions and regressions"):
        approve_rule("loan-age-rule", "reviewer")


def test_full_api_generation_execution_regression_and_history(tmp_path, monkeypatch):
    old, new = make_rule(1), make_rule(2, threshold=70)
    cases = generation.generate_cases(
        old,
        new,
        unrelated_product_types=["credit_card", "home_loan"],
        llm_call=generated_candidates(old, new),
    )
    monkeypatch.setenv("OUTPUTS_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("CIDAN_ACCESS_TOKEN", "sandbox-test-token")
    monkeypatch.setattr(
        service,
        "generate_cases",
        lambda _old, _new, **_kwargs: cases,
    )
    client = TestClient(
        app, headers={"Authorization": "Bearer sandbox-test-token"}
    )
    payload = {
        "document_id": "synthetic-handbook-and-circular",
        "change_id": new.change_id,
        "baseline_rule": old.model_dump(mode="json"),
        "proposed_rule": new.model_dump(mode="json"),
        "unrelated_product_types": ["credit_card", "home_loan"],
    }
    generated = client.post("/sandbox/suites", json=payload)
    assert generated.status_code == 201, generated.text
    report = generated.json()
    assert report["total_generated"] == 50
    assert report["total_executed"] == 0
    assert report["pending"] == 50
    assert report["category_distribution"] == generation.CASE_DISTRIBUTION
    assert client.get("/sandbox/suites").json()[0]["suite_id"] == report["suite_id"]
    assert client.get(f"/sandbox/suites/{report['suite_id']}").json()["total_generated"] == 50

    executed = client.post(f"/sandbox/suites/{report['suite_id']}/execute")
    assert executed.status_code == 200, executed.text
    execution = executed.json()
    assert execution["total_generated"] == 50
    assert execution["total_executed"] == 50
    assert execution["passed"] == 50
    assert execution["failed"] == 0
    assert execution["pending"] == 0
    assert len(execution["regression_results"]) == 50
    assert all(item["passed"] for item in execution["regression_results"])

    history = client.get(f"/sandbox/suites/{report['suite_id']}/history")
    assert history.status_code == 200
    assert [item["event"] for item in history.json()] == [
        "generation_started", "generation_completed", "execution_completed"
    ]
    assert len(repository.load_suite(report["suite_id"])["test_cases"]) == 50


def _make_rule_proposal(baseline: SandboxRule, proposed: SandboxRule) -> RuleProposal:
    citation = Citation(
        document_id="synthetic-document",
        filename="synthetic-circular.pdf",
        document_type="circular",
        page=1,
        excerpt="Synthetic rule evidence.",
        chunk_id="synthetic-circular-chunk",
    )
    return RuleProposal(
        rule_id=proposed.rule_id,
        version=proposed.version,
        change_id=proposed.change_id,
        business_purpose="Validate a proposed synthetic threshold change.",
        source_obligation_ids=["OBL-SYNTHETIC"],
        description="Use a synthetic threshold to verify rule comparison.",
        trigger_conditions=[RuleCondition(field="amount", operator="gte", value=60)],
        required_inputs=["amount"],
        decision_outcomes=["ELIGIBLE", "NOT_ELIGIBLE"],
        validation_criteria=["Compare both deterministic rule outcomes."],
        rollback_considerations="Restore the baseline rule in the local sandbox.",
        supporting_citations=[citation],
        baseline_rule=baseline,
        sandbox_rule=proposed,
        unrelated_product_types=["credit_card"],
        action="second_review",
    )


def test_agent3_proposal_runs_through_agent4_validation(tmp_path, monkeypatch):
    baseline, proposed = make_rule(1), make_rule(2, threshold=70)
    citation = Citation(
        document_id="synthetic-document",
        filename="synthetic-circular.pdf",
        document_type="circular",
        page=1,
        excerpt="Synthetic rule evidence.",
        chunk_id="synthetic-circular-chunk",
    )
    obligation = {
        "obligation_id": "OBL-SYNTHETIC",
        "text": "Apply the proposed age threshold.",
        "required_action": "Review age threshold decisions.",
        "source": citation.model_dump(mode="json"),
    }
    finding = PolicyFinding(
        obligation_id="OBL-SYNTHETIC",
        status="partially_covered",
        matching_policy_provision="Synthetic policy provision",
        circular_citation=citation,
        reasoning="The baseline and proposed thresholds differ.",
        missing_or_inconsistent="The age threshold needs review.",
        operational_impact="Eligibility decisions change.",
        recommended_action="Update the decision rule.",
        confidence=0.9,
    )
    generated_proposal = RuleProposal(
        rule_id=proposed.rule_id,
        version=proposed.version,
        change_id=proposed.change_id,
        business_purpose="Validate a proposed synthetic threshold change.",
        source_obligation_ids=["OBL-SYNTHETIC"],
        description="Use a synthetic threshold to verify rule comparison.",
        trigger_conditions=[RuleCondition(field="amount", operator="gte", value=60)],
        required_inputs=["amount"],
        decision_outcomes=["ELIGIBLE", "NOT_ELIGIBLE"],
        validation_criteria=["Compare both deterministic rule outcomes."],
        rollback_considerations="Restore the baseline rule in the local sandbox.",
        supporting_citations=[citation],
        baseline_rule=baseline,
        sandbox_rule=proposed,
        unrelated_product_types=["credit_card"],
        action="second_review",
    )

    def agent3_llm(schema, _system, _prompt):
        return schema(proposals=[generated_proposal])

    monkeypatch.setenv("OUTPUTS_DIRECTORY", str(tmp_path))
    proposals = rule_authoring.run(
        [obligation],
        [finding],
        llm_call=agent3_llm,
    )
    assert len(proposals) == 1
    assert proposals[0].status == "draft"

    summary = testing_validation.run(
        proposals[0],
        llm_call=generated_candidates(baseline, proposed),
    )

    assert summary.total == 50
    assert summary.passed == 50
    assert summary.failed == 0
    assert summary.pending == 0
    assert summary.invalid == 0
    suite = service.get_suite(summary.sandbox_suite_id)
    assert suite["category_distribution"] == generation.CASE_DISTRIBUTION
    assert all(result["status"] == "passed" for result in suite["execution_results"])
    assert all(result["passed"] is True for result in suite["regression_results"])


def test_agent4_records_manual_review_when_numeric_tests_are_unsupported(
    tmp_path, monkeypatch
):
    baseline = SandboxRule(
        rule_id="account-rule",
        version=1,
        change_id="account-change-v1",
        product_type="personal_loan",
        conditions=[{"field": "account_type", "operator": "eq", "value": "standard"}],
        outcome_when_matched="ELIGIBLE",
        outcome_when_unmatched="NOT_ELIGIBLE",
    )
    proposed = baseline.model_copy(update={
        "version": 2,
        "change_id": "account-change-v2",
    })
    monkeypatch.setenv("OUTPUTS_DIRECTORY", str(tmp_path))

    summary = testing_validation.run(
        _make_rule_proposal(baseline, proposed),
        llm_call=lambda *_args: pytest.fail("No unsupported test cases should be generated."),
    )

    assert summary.total == 0
    assert summary.pending == 1
    suite = service.get_suite(summary.sandbox_suite_id)
    assert suite["status"] == "manual_review"
    assert "numeric thresholds" in suite["failure_reason"]


def test_agent4_summary_fails_when_regression_fails(tmp_path, monkeypatch):
    baseline, proposed = make_rule(1), make_rule(2, threshold=70)
    monkeypatch.setenv("OUTPUTS_DIRECTORY", str(tmp_path))
    run_suite = testing_validation.sandbox_service.run_suite

    def with_failed_regression(suite_id):
        report = run_suite(suite_id)
        report["regression_results"][0].update({
            "category": "unexpected_behavior_change",
            "passed": False,
            "detail": "Injected regression failure for summary verification.",
        })
        return report

    monkeypatch.setattr(
        testing_validation.sandbox_service, "run_suite", with_failed_regression
    )
    summary = testing_validation.run(
        _make_rule_proposal(baseline, proposed),
        llm_call=generated_candidates(baseline, proposed),
    )

    assert summary.total == 50
    assert summary.failed == 1
    assert summary.passed == 49
    assert "Injected regression failure" in summary.results[0].message


def test_regression_failure_prevents_suite_completion(tmp_path, monkeypatch):
    from cidan.sandbox.schemas import ExecutionResult

    baseline, proposed = make_rule(1), make_rule(2, threshold=70)
    monkeypatch.setenv("OUTPUTS_DIRECTORY", str(tmp_path))
    suite = service.generate_suite(
        document_id="synthetic-document",
        change_id=proposed.change_id,
        baseline_rule=baseline,
        proposed_rule=proposed,
        unrelated_product_types=["credit_card"],
        llm_call=generated_candidates(baseline, proposed),
    )
    service.run_suite(suite["suite_id"])
    stored = repository.load_suite(suite["suite_id"])
    executions = [
        ExecutionResult.model_validate({
            key: value for key, value in item.items() if key != "result_id"
        })
        for item in stored["execution_results"]
    ]
    regressions = [
        RegressionResult.model_validate(item)
        for item in stored["regression_results"]
    ]
    regressions[0] = regressions[0].model_copy(update={
        "category": "unexpected_behavior_change",
        "passed": False,
        "detail": "Unexpected change in the regression outcome.",
    })

    repository.save_execution(suite["suite_id"], executions, regressions)

    assert service.get_suite(suite["suite_id"])["status"] == "execution_failed"


def test_invalid_persisted_case_fails_execution_and_is_recorded(tmp_path, monkeypatch):
    baseline, proposed = make_rule(1), make_rule(2, threshold=70)
    monkeypatch.setenv("OUTPUTS_DIRECTORY", str(tmp_path))
    suite = service.generate_suite(
        document_id="synthetic-document",
        change_id=proposed.change_id,
        baseline_rule=baseline,
        proposed_rule=proposed,
        unrelated_product_types=["credit_card"],
        llm_call=generated_candidates(baseline, proposed),
    )
    database = sqlite3.connect(tmp_path / "sandbox.sqlite3")
    row = database.execute(
        "SELECT test_id, case_json FROM test_cases WHERE suite_id = ? ORDER BY rowid LIMIT 1",
        (suite["suite_id"],),
    ).fetchone()
    corrupted = json.loads(row[1])
    corrupted["input_data"]["unsupported_field"] = 1
    database.execute(
        "UPDATE test_cases SET case_json = ? WHERE test_id = ?",
        (json.dumps(corrupted), row[0]),
    )
    database.commit()
    database.close()

    with pytest.raises(ValueError, match="unsupported input fields"):
        execute_suite(suite["suite_id"])
    report = service.get_suite(suite["suite_id"])
    assert report["status"] == "execution_failed"
    assert "unsupported input fields" in report["failure_reason"]
    assert repository.history(suite["suite_id"])[-1]["event"] == "execution_failed"


def test_agent4_dashboard_reads_suite_results_from_sqlite(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    import dashboard

    baseline, proposed = make_rule(1), make_rule(2, threshold=70)
    monkeypatch.setenv("OUTPUTS_DIRECTORY", str(tmp_path))
    suite = service.generate_suite(
        document_id="synthetic-document",
        change_id=proposed.change_id,
        baseline_rule=baseline,
        proposed_rule=proposed,
        unrelated_product_types=["credit_card"],
        llm_call=generated_candidates(baseline, proposed),
    )
    service.run_suite(suite["suite_id"])

    app_test = AppTest.from_file(dashboard.__file__).run()
    agent_selection = next(
        radio for radio in app_test.radio if radio.label == "Agent Selection"
    )
    agent_selection.set_value(agent_selection.options[3]).run()

    assert any(
        "Agent 4 – Test Case Generation" in header.value
        for header in app_test.subheader
    )
    assert any(
        metric.label == "Generated" and str(metric.value) == "50"
        for metric in app_test.metric
    )
    assert any(
        "Individual Test Cases" in item.value
        for item in app_test.markdown
    )
    assert not app_test.exception
