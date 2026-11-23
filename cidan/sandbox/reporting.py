from collections import Counter
from typing import Any

from cidan.sandbox.schemas import TestCase


def build_report(suite: dict[str, Any]) -> dict[str, Any]:
    cases = [TestCase.model_validate(item) for item in suite["test_cases"]]
    results = suite.get("execution_results", [])[-len(cases):] if cases else []
    regressions = suite.get("regression_results", [])[-len(cases):] if cases else []
    counts = Counter(item["status"] for item in results)
    total = len(cases)
    executed = counts["passed"] + counts["failed"]
    return {
        "suite_id": suite["suite_id"],
        "document_id": suite["document_id"],
        "rule_id": suite["rule_id"],
        "change_id": suite["change_id"],
        "status": suite["status"],
        "total_generated": total,
        "total_executed": executed,
        "passed": counts["passed"],
        "failed": counts["failed"],
        "pending": total - executed,
        "pass_percentage": round(counts["passed"] / executed * 100, 2) if executed else 0.0,
        "category_distribution": dict(Counter(case.category for case in cases)),
        "test_cases": suite["test_cases"],
        "execution_results": results,
        "regression_results": regressions,
        "failure_reason": suite.get("failure_reason"),
        "generated_at": suite["generated_at"],
    }
