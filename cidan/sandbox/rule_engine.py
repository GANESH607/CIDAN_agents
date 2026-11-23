import math
from typing import Any

from pydantic import ValidationError

from cidan.sandbox.schemas import RuleEvaluation, SandboxRule


def _validate_actual(field: str, actual: Any, expected: Any) -> None:
    if isinstance(expected, bool):
        if not isinstance(actual, bool):
            raise TypeError(f"Input {field!r} must be a boolean.")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)):
            raise TypeError(f"Input {field!r} must be numeric.")
        if isinstance(actual, float) and not math.isfinite(actual):
            raise ValueError(f"Input {field!r} must be finite.")
    elif not isinstance(actual, type(expected)):
        raise TypeError(f"Input {field!r} must be a {type(expected).__name__}.")


def _condition_matches(condition: Any, inputs: dict[str, Any]) -> bool:
    if condition.field not in inputs:
        raise KeyError(f"Missing input: {condition.field}")
    actual = inputs[condition.field]
    _validate_actual(condition.field, actual, condition.value)

    if condition.operator in {"gt", "gte", "lt", "lte"} and isinstance(actual, bool):
        raise TypeError(f"Input {condition.field!r} must be numeric.")
    if condition.operator == "gt":
        return actual > condition.value
    if condition.operator == "gte":
        return actual >= condition.value
    if condition.operator == "lt":
        return actual < condition.value
    if condition.operator == "lte":
        return actual <= condition.value
    if condition.operator == "eq":
        return actual == condition.value
    if condition.operator == "ne":
        return actual != condition.value
    if condition.operator == "between":
        if isinstance(actual, bool) or not isinstance(actual, (int, float)):
            raise TypeError(f"Input {condition.field!r} must be numeric.")
        if isinstance(actual, float) and not math.isfinite(actual):
            raise ValueError(f"Input {condition.field!r} must be finite.")
        return condition.value <= actual <= condition.upper_value
    raise ValueError(f"Unsupported operator: {condition.operator}")


def evaluate(rule: SandboxRule | dict[str, Any], inputs: dict[str, Any]) -> RuleEvaluation:
    rule_id = "unknown"
    version = 0
    try:
        parsed = rule if isinstance(rule, SandboxRule) else SandboxRule.model_validate(rule)
        rule_id, version = parsed.rule_id, parsed.version
    except (ValidationError, TypeError, ValueError) as exc:
        return RuleEvaluation(
            rule_id=rule_id,
            version=version,
            outcome="MANUAL_REVIEW",
            status="manual_review",
            detail=f"Rule is not executable: {exc}",
        )

    if parsed.manual_review_reason:
        return RuleEvaluation(
            rule_id=rule_id,
            version=version,
            outcome="MANUAL_REVIEW",
            status="manual_review",
            detail=parsed.manual_review_reason,
        )
    if not isinstance(inputs, dict):
        return RuleEvaluation(
            rule_id=rule_id, version=version, outcome="INVALID_INPUT",
            status="invalid_input", detail="Rule inputs must be an object.",
        )
    if "product_type" not in inputs:
        return RuleEvaluation(
            rule_id=rule_id, version=version, outcome="INVALID_INPUT",
            status="missing_input", detail="Missing input: product_type",
        )
    if not isinstance(inputs["product_type"], str):
        return RuleEvaluation(
            rule_id=rule_id, version=version, outcome="INVALID_INPUT",
            status="invalid_input", detail="Input 'product_type' must be a string.",
        )
    if inputs["product_type"].casefold() != parsed.product_type.casefold():
        return RuleEvaluation(
            rule_id=rule_id, version=version, outcome="NOT_APPLICABLE",
            status="evaluated",
        )

    try:
        matched = (
            all(_condition_matches(condition, inputs) for condition in parsed.conditions)
            if parsed.logical_operator == "AND"
            else any(_condition_matches(condition, inputs) for condition in parsed.conditions)
        )
    except KeyError as exc:
        return RuleEvaluation(
            rule_id=rule_id, version=version, outcome="INVALID_INPUT",
            status="missing_input", detail=str(exc).strip("'"),
        )
    except (TypeError, ValueError) as exc:
        return RuleEvaluation(
            rule_id=rule_id, version=version, outcome="INVALID_INPUT",
            status="invalid_input", detail=str(exc),
        )

    return RuleEvaluation(
        rule_id=rule_id,
        version=version,
        outcome=parsed.outcome_when_matched if matched else parsed.outcome_when_unmatched,
        status="evaluated",
    )

