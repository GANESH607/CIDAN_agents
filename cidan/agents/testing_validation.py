from typing import Any, Callable

from cidan.models import RuleProposal, TestResult, TestSummary
from cidan.sandbox import service as sandbox_service
from cidan.sandbox.schemas import SandboxRule


def run(
    rule: RuleProposal,
    *,
    baseline_rule: SandboxRule | None = None,
    document_id: str | None = None,
    unrelated_product_types: list[str] | None = None,
    llm_call: Callable[..., Any] | None = None,
) -> TestSummary:
    baseline = baseline_rule or rule.baseline_rule
    proposed = rule.sandbox_rule
    source_document_id = document_id or rule.supporting_citations[0].document_id
    change_id = rule.change_id or rule.rule_id
    review_reasons = []
    if not rule.change_id:
        review_reasons.append("The rule proposal has no traceable change ID.")
    if baseline is None or proposed is None:
        review_reasons.append("No deterministic baseline/proposed rule pair is supported by evidence.")
    if not rule.unrelated_product_types and not unrelated_product_types:
        review_reasons.append("No evidence-backed unrelated products are available for regression tests.")
    if proposed and (proposed.rule_id != rule.rule_id or proposed.version != rule.version):
        review_reasons.append("Sandbox rule identity does not match the rule proposal.")
    if proposed and rule.change_id and proposed.change_id != rule.change_id:
        review_reasons.append("Sandbox rule change ID does not match the proposal.")
    if baseline and proposed:
        if baseline.manual_review_reason or proposed.manual_review_reason:
            review_reasons.append("At least one rule is explicitly marked for manual review.")
        if baseline.rule_id != proposed.rule_id:
            review_reasons.append("Baseline and proposed rules do not share a rule ID.")
        if baseline.version == proposed.version:
            review_reasons.append("Baseline and proposed rule versions are not distinct.")
        if baseline.product_type.casefold() != proposed.product_type.casefold():
            review_reasons.append("Baseline and proposed rules target different products.")
        if any(
            item.casefold() == proposed.product_type.casefold()
            for item in (unrelated_product_types or rule.unrelated_product_types)
        ):
            review_reasons.append(
                "Regression product evidence includes the compared rule's product."
            )
    if review_reasons:
        suite = sandbox_service.record_manual_review(
            document_id=source_document_id,
            rule_id=rule.rule_id,
            change_id=change_id,
            reason=" ".join(review_reasons),
        )
        return TestSummary(
            total=0,
            passed=0,
            failed=0,
            skipped=0,
            invalid=0,
            pending=1,
            pass_rate=None,
            results=[TestResult(
                transaction_id="MANUAL_REVIEW",
                rule_id=rule.rule_id,
                passed=False,
                expected="Evidence-backed baseline, proposed rule, and unrelated products",
                actual=None,
                message=suite["failure_reason"],
            )],
            sandbox_suite_id=suite["suite_id"],
        )
    if baseline is None or proposed is None:
        raise ValueError("Sandbox rules remain unavailable after manual-review checks.")
    generated = sandbox_service.generate_suite(
        document_id=source_document_id,
        change_id=change_id,
        baseline_rule=baseline,
        proposed_rule=proposed,
        unrelated_product_types=(
            unrelated_product_types or rule.unrelated_product_types
        ),
        llm_call=llm_call,
    )
    report = sandbox_service.run_suite(generated["suite_id"])
    results = [
        TestResult(
            transaction_id=item["test_id"],
            rule_id=item["rule_id"],
            passed=item["status"] == "passed",
            expected={
                "old": item["expected_old_result"],
                "proposed": item["expected_proposed_result"],
            },
            actual={
                "old": item["actual_old_result"],
                "proposed": item["actual_proposed_result"],
            },
            message=item["failure_reason"] or "Both rule versions matched expected results.",
        )
        for item in report["execution_results"]
    ]
    passed = report["passed"]
    failed = report["failed"]
    pending = report["pending"]
    total = report["total_generated"]
    return TestSummary(
        total=total,
        passed=passed,
        failed=failed,
        skipped=0,
        invalid=pending,
        pending=pending,
        pass_rate=passed / total if total else None,
        results=results,
        sandbox_suite_id=report["suite_id"],
    )
