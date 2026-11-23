from cidan.sandbox.schemas import (
    ExecutionResult,
    RegressionResult,
    SandboxRule,
    TestCase,
)


def analyze_regression(
    case: TestCase,
    result: ExecutionResult,
    baseline: SandboxRule,
    proposed: SandboxRule,
) -> RegressionResult:
    expected_change = case.expected_outcome == "behavior_changed"
    if result.status == "pending":
        return RegressionResult(
            test_id=case.test_id,
            product_type=case.input_data.get("product_type"),
            expected_behavior_change=expected_change,
            actual_behavior_change=None,
            category="pending",
            passed=None,
            detail=result.failure_reason or "Rule requires manual review.",
        )

    actual_change = result.actual_old_result != result.actual_proposed_result
    product = case.input_data.get("product_type")
    unrelated = isinstance(product, str) and product.casefold() not in {
        baseline.product_type.casefold(),
        proposed.product_type.casefold(),
    }
    if unrelated and actual_change:
        category = "unrelated_product_affected"
        passed = False
        detail = "A product outside the compared rule scope changed behavior."
    elif actual_change and expected_change:
        category = "expected_behavior_change"
        passed = True
        detail = "The expected baseline-to-proposed behavior change occurred."
    elif not actual_change:
        category = "unaffected"
        passed = not expected_change
        detail = (
            "Behavior was unchanged as expected."
            if passed
            else "An expected behavior change did not occur."
        )
    else:
        category = "unexpected_behavior_change"
        passed = False
        detail = "Behavior changed when the test case expected no change."
    return RegressionResult(
        test_id=case.test_id,
        product_type=product if isinstance(product, str) else None,
        expected_behavior_change=expected_change,
        actual_behavior_change=actual_change,
        category=category,
        passed=passed,
        detail=detail,
    )

