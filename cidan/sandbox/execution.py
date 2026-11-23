from typing import Any

from cidan.sandbox import repository
from cidan.sandbox.comparison import compare_case
from cidan.sandbox.regression import analyze_regression
from cidan.sandbox.schemas import (
    ExecutionResult,
    RegressionResult,
    SandboxRule,
    TestCase,
)


def execute_suite(suite_id: str) -> dict[str, Any]:
    suite = repository.load_suite(suite_id)
    if suite["status"] in {"generating", "generation_failed"}:
        raise ValueError("A complete generated test suite is required before execution.")
    if not suite["baseline_rule"] or not suite["proposed_rule"]:
        raise ValueError("Baseline and proposed rules are required before execution.")

    baseline = SandboxRule.model_validate(suite["baseline_rule"])
    proposed = SandboxRule.model_validate(suite["proposed_rule"])
    cases = [TestCase.model_validate(item) for item in suite["test_cases"]]
    if len(cases) != 50:
        raise ValueError(f"Expected 50 validated test cases; found {len(cases)}.")

    results: list[ExecutionResult] = []
    regressions: list[RegressionResult] = []
    for case in cases:
        result = compare_case(case, baseline, proposed)
        results.append(result)
        regressions.append(
            analyze_regression(case, result, baseline, proposed)
        )

    repository.save_execution(suite_id, results, regressions)
    suite_data = repository.load_suite(suite_id)
    suite_data["regression_results"] = [item.model_dump(mode="json") for item in regressions]
    return suite_data
