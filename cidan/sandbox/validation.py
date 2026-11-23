import hashlib
import json
import re
from collections import Counter
from typing import Any

from cidan.sandbox.rule_engine import evaluate
from cidan.sandbox.schemas import SandboxRule, TestCase

CASE_DISTRIBUTION = {
    "positive_normal": 10,
    "negative": 10,
    "boundary_value": 10,
    "edge_case": 5,
    "regression": 5,
    "missing_data_exception": 5,
    "conflicting_rule": 5,
}


def canonical_input_key(inputs: dict[str, Any]) -> str:
    return json.dumps(inputs, sort_keys=True, separators=(",", ":"), allow_nan=False)


def scenario_key(case: TestCase) -> str:
    scenario = re.sub(r"\s+", " ", case.scenario).strip().casefold()
    return hashlib.sha256(
        f"{canonical_input_key(case.input_data)}\n{scenario}".encode("utf-8")
    ).hexdigest()


def _validate_relevance(
    case: TestCase,
    old_rule: SandboxRule,
    new_rule: SandboxRule,
    unrelated_product_types: list[str],
) -> None:
    product = case.input_data.get("product_type")
    if not isinstance(product, str):
        raise ValueError(f"{case.test_id} has no valid product_type.")
    same_product = product.casefold() == old_rule.product_type.casefold()
    unrelated = any(
        product.casefold() == item.casefold() for item in unrelated_product_types
    )
    required = {
        condition.field
        for condition in [*old_rule.conditions, *new_rule.conditions]
    }
    unsupported_fields = set(case.input_data) - required - {"product_type"}
    if unsupported_fields:
        raise ValueError(
            f"{case.test_id} contains unsupported input fields: "
            f"{', '.join(sorted(unsupported_fields))}."
        )
    if case.category == "regression":
        if same_product or not unrelated:
            raise ValueError(
                f"{case.test_id} must target a supplied unrelated product."
            )
        if (
            case.expected_old_result != "NOT_APPLICABLE"
            or case.expected_proposed_result != "NOT_APPLICABLE"
        ):
            raise ValueError(
                f"{case.test_id} must expect NOT_APPLICABLE for both rules."
            )
        return
    if not same_product:
        raise ValueError(f"{case.test_id} does not target the compared product.")

    if case.category == "missing_data_exception":
        if all(
            field in case.input_data and case.input_data[field] is not None
            for field in required
        ):
            raise ValueError(f"{case.test_id} does not exercise missing data.")
    elif any(field not in case.input_data for field in required):
        raise ValueError(f"{case.test_id} omits a required rule input.")


def validate_case(
    case: TestCase,
    old_rule: SandboxRule,
    new_rule: SandboxRule,
    unrelated_product_types: list[str],
) -> TestCase:
    if case.rule_id != new_rule.rule_id or case.change_id != new_rule.change_id:
        raise ValueError(f"{case.test_id} has an unrelated rule or change ID.")
    _validate_relevance(case, old_rule, new_rule, unrelated_product_types)
    old = evaluate(old_rule, case.input_data)
    new = evaluate(new_rule, case.input_data)
    if case.category == "positive_normal" and not (
        old.outcome == old_rule.outcome_when_matched
        or new.outcome == new_rule.outcome_when_matched
    ):
        raise ValueError(f"{case.test_id} does not exercise a positive rule outcome.")
    if case.category == "negative" and (
        old.outcome != old_rule.outcome_when_unmatched
        or new.outcome != new_rule.outcome_when_unmatched
    ):
        raise ValueError(f"{case.test_id} does not exercise negative outcomes.")
    if case.category == "boundary_value":
        boundaries = []
        for condition in [*old_rule.conditions, *new_rule.conditions]:
            if condition.field not in case.input_data:
                continue
            if isinstance(condition.value, bool) or not isinstance(
                condition.value, (int, float)
            ):
                continue
            actual = case.input_data[condition.field]
            if isinstance(actual, bool) or not isinstance(actual, (int, float)):
                continue
            bounds = [condition.value]
            if condition.operator == "between":
                bounds.append(condition.upper_value)
            boundaries.extend(abs(actual - bound) <= 1 for bound in bounds)
        if not any(boundaries):
            raise ValueError(f"{case.test_id} is not near a rule threshold.")
    if case.category == "edge_case":
        thresholds_by_field: dict[str, list[int | float]] = {}
        for condition in [*old_rule.conditions, *new_rule.conditions]:
            if isinstance(condition.value, bool) or not isinstance(
                condition.value, (int, float)
            ):
                continue
            thresholds = [condition.value]
            if condition.operator == "between":
                thresholds.append(condition.upper_value)
            thresholds_by_field.setdefault(condition.field, []).extend(thresholds)
        extremes = []
        for field, thresholds in thresholds_by_field.items():
            actual = case.input_data.get(field)
            if isinstance(actual, bool) or not isinstance(actual, (int, float)):
                continue
            extremes.append(actual < min(thresholds) - 1 or actual > max(thresholds) + 1)
        if not any(extremes):
            raise ValueError(
                f"{case.test_id} is not an evidence-grounded numeric edge case."
            )
    if case.category == "missing_data_exception" and (
        old.status not in {"missing_input", "invalid_input"}
        and new.status not in {"missing_input", "invalid_input"}
    ):
        raise ValueError(f"{case.test_id} does not trigger missing-input handling.")
    if case.category == "conflicting_rule" and old.outcome == new.outcome:
        raise ValueError(f"{case.test_id} does not exercise conflicting rule results.")
    if case.expected_old_result != old.outcome or case.expected_proposed_result != new.outcome:
        raise ValueError(f"{case.test_id} expectations do not match deterministic evaluation.")
    return case


def validate_cases(
    cases: list[TestCase],
    old_rule: SandboxRule,
    new_rule: SandboxRule,
    unrelated_product_types: list[str],
) -> list[TestCase]:
    if len(cases) != 50:
        raise ValueError(f"Exactly 50 test cases are required; received {len(cases)}.")
    if Counter(case.category for case in cases) != Counter(CASE_DISTRIBUTION):
        raise ValueError("Test case categories do not match the required distribution.")
    if len({case.test_id for case in cases}) != 50:
        raise ValueError("Test IDs must be unique.")

    scenarios_seen: set[str] = set()
    scenario_descriptions_seen: set[str] = set()
    for case in cases:
        validate_case(case, old_rule, new_rule, unrelated_product_types)
        key = scenario_key(case)
        if key in scenarios_seen:
            raise ValueError("Test suite contains duplicate input scenarios.")
        scenarios_seen.add(key)
        scenario_description = re.sub(r"\s+", " ", case.scenario).strip().casefold()
        if scenario_description in scenario_descriptions_seen:
            raise ValueError("Test suite contains duplicate scenario descriptions.")
        scenario_descriptions_seen.add(scenario_description)
    return cases
