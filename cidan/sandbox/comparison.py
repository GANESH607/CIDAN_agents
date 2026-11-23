from datetime import datetime, timezone

from cidan.sandbox.rule_engine import evaluate
from cidan.sandbox.schemas import ExecutionResult, SandboxRule, TestCase


def compare_case(
    case: TestCase,
    baseline: SandboxRule,
    proposed: SandboxRule,
) -> ExecutionResult:
    old = evaluate(baseline, case.input_data)
    new = evaluate(proposed, case.input_data)
    executable = old.status != "manual_review" and new.status != "manual_review"
    old_matches = old.outcome == case.expected_old_result
    new_matches = new.outcome == case.expected_proposed_result
    passed = executable and old_matches and new_matches
    failure_reason = None
    if not executable:
        failure_reason = old.detail if old.status == "manual_review" else new.detail
    elif not old_matches or not new_matches:
        mismatches = []
        if not old_matches:
            mismatches.append(
                f"Baseline expected {case.expected_old_result!r}, got {old.outcome!r}."
            )
        if not new_matches:
            mismatches.append(
                f"Proposed expected {case.expected_proposed_result!r}, got {new.outcome!r}."
            )
        failure_reason = " ".join(mismatches)
    return ExecutionResult(
        test_id=case.test_id,
        rule_id=case.rule_id,
        change_id=case.change_id,
        input_data=case.input_data,
        expected_old_result=case.expected_old_result,
        actual_old_result=old.outcome,
        expected_proposed_result=case.expected_proposed_result,
        actual_proposed_result=new.outcome,
        status="pending" if not executable else "passed" if passed else "failed",
        failure_reason=failure_reason,
        executed_at=datetime.now(timezone.utc).isoformat(),
    )

