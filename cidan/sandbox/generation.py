import json
from typing import Any, Callable
from uuid import uuid4

from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel, Field

from cidan.agents.base import invoke_structured
from cidan.config import get_settings
from cidan.sandbox.rule_engine import evaluate
from cidan.sandbox.schemas import (
    GeneratedTestCase,
    SandboxRule,
    TestCase,
)
from cidan.sandbox.validation import (
    CASE_DISTRIBUTION,
    scenario_key,
    validate_case,
    validate_cases,
)

BATCH_SIZE = 5
MAX_BATCH_ATTEMPTS = 5


class CaseBatch(BaseModel):
    cases: list[GeneratedTestCase] = Field(min_length=1)


SYSTEM = """Generate synthetic policy comparison tests only from the supplied baseline
and proposed structured rules. Return exactly the requested number of cases in the
requested category. The category is assigned by the caller; do not include it in the
response. Each case must include only scenario and input_data. Expected old/proposed
outputs and behavior-change classification are independently derived by the
deterministic rule engine after input validation.
Do not invent rule thresholds, products, inputs, or outcomes. For missing-data cases,
omit a required field. For conflicting-rule cases, use inputs where the provided old
and proposed rules produce different results. Regression cases must keep behavior
unchanged and use only the supplied unrelated product list, expecting NOT_APPLICABLE
from both rule versions. Positive/normal cases should exercise a matching decision;
positive means at least one rule's matched outcome (not necessarily a behavior change).
Negative cases must produce the unmatched outcome for both versions; a value that only
fails one version is not negative. For changed numeric thresholds, derive values from
the supplied thresholds: choose clearly matched values for positive cases, values that
fail every version for negative cases, and values between thresholds when the versions
should disagree. Boundary cases should use values at or immediately around thresholds
in the supplied rules; edge cases should exercise meaningful extremes of the supplied
input domains without inventing fields or product types. Return an object
with a single "cases" array, with no notes or extra wrapper fields. Output structured
JSON only. Never include personal/customer data."""


def _category_guidance(
    category: str,
    old_rule: SandboxRule,
    proposed_rule: SandboxRule,
    unrelated_product_types: list[str],
) -> str:
    required_fields = sorted(
        {
            condition.field
            for condition in [*old_rule.conditions, *proposed_rule.conditions]
        }
    )
    if category == "positive_normal":
        return "Every case must match at least one rule version."
    if category == "negative":
        return (
            "Every case must produce each rule version's unmatched outcome. "
            "Do not choose inputs that match either version."
        )
    if category == "boundary_value":
        boundary_values: dict[str, set[int | float]] = {}
        for condition in [*old_rule.conditions, *proposed_rule.conditions]:
            if condition.operator in {"gt", "gte", "lt", "lte", "between"}:
                thresholds = [condition.value]
                if condition.operator == "between":
                    thresholds.append(condition.upper_value)
                for threshold in thresholds:
                    boundary_values.setdefault(condition.field, set()).update(
                        (threshold - 1, threshold, threshold + 1)
                    )
        return (
            "Every case must use a numeric field/value pair from these dynamically "
            "derived boundary values: "
            f"{json.dumps({field: sorted(values) for field, values in boundary_values.items()})}."
        )
    if category == "edge_case":
        return (
            "Use distinct meaningful numeric extremes around the supplied thresholds; "
            "do not invent input fields or claim unsupported domain limits."
        )
    if category == "regression":
        return (
            "Set product_type to one of these unrelated products only: "
            f"{json.dumps(unrelated_product_types)}. Both versions must return "
            "NOT_APPLICABLE."
        )
    if category == "missing_data_exception":
        return (
            "Every case must omit at least one required condition field entirely "
            "(do not set it to null). Required fields: "
            f"{json.dumps(required_fields)}. Keep product_type as "
            f"{json.dumps(old_rule.product_type)}."
        )
    if category == "conflicting_rule":
        return (
            "Every case must produce different outcomes under the supplied baseline "
            "and proposed rules."
        )
    raise ValueError(f"Unsupported sandbox test category: {category}")


def generate_cases(
    old_rule: SandboxRule,
    proposed_rule: SandboxRule,
    *,
    unrelated_product_types: list[str],
    llm_call: Callable[..., Any] | None = None,
) -> list[TestCase]:
    if old_rule.manual_review_reason or proposed_rule.manual_review_reason:
        raise ValueError("Manual-review rules cannot generate executable sandbox cases.")
    if old_rule.rule_id != proposed_rule.rule_id:
        raise ValueError("Baseline and proposed rules must share the same rule ID.")
    if old_rule.product_type.casefold() != proposed_rule.product_type.casefold():
        raise ValueError("Baseline and proposed rules must target the same product.")
    if old_rule.version == proposed_rule.version:
        raise ValueError("Baseline and proposed rule versions must differ.")
    unrelated = [item.strip() for item in unrelated_product_types if item.strip()]
    if not unrelated:
        raise ValueError("At least one known unrelated product is required for regression testing.")
    if any(item.casefold() == old_rule.product_type.casefold() for item in unrelated):
        raise ValueError("Unrelated products cannot include the rule's own product.")

    completed: list[TestCase] = []
    suite_token = uuid4().hex[:12]
    rule_context = json.dumps(
        {
            "baseline": old_rule.model_dump(mode="json"),
            "proposed": proposed_rule.model_dump(mode="json"),
        },
        sort_keys=True,
    )

    for category, required_count in CASE_DISTRIBUTION.items():
        remaining = required_count
        while remaining:
            count = min(BATCH_SIZE, remaining)
            prompt = (
                f"Rules:\n{rule_context}\n"
                f"Known unrelated products for regression testing:\n{json.dumps(unrelated)}\n"
                f"Previously accepted test scenarios and inputs:\n"
                f"{json.dumps([{'scenario': case.scenario, 'input_data': case.input_data} for case in completed])}\n"
                f"Generate exactly {count} cases in category {category!r}. "
                f"Category-specific constraint: "
                f"{_category_guidance(category, old_rule, proposed_rule, unrelated)} "
                "Each case must provide only input_data and scenario. Do not return "
                "expected outcomes, category labels, notes, or duplicate scenarios. "
                "All cases must be distinct from the previously accepted cases."
            )
            for attempt in range(MAX_BATCH_ATTEMPTS):
                attempted_batch: list[dict[str, Any]] = []
                try:
                    batch = (
                        llm_call(CaseBatch, SYSTEM, prompt)
                        if llm_call
                        else invoke_structured(
                            CaseBatch,
                            SYSTEM,
                            prompt,
                            max_tokens=get_settings().sandbox_llm_max_output_tokens,
                            method="json_mode",
                            temperature=0.2,
                        )
                    )
                    attempted_batch = [
                        {
                            **candidate.model_dump(),
                            "actual_old_result": evaluate(
                                old_rule, candidate.input_data
                            ).outcome,
                            "actual_proposed_result": evaluate(
                                proposed_rule, candidate.input_data
                            ).outcome,
                        }
                        for candidate in batch.cases
                    ]
                    if len(batch.cases) != count:
                        raise ValueError(
                            f"Groq returned {len(batch.cases)} cases for {category}; expected {count}."
                        )
                    batch_cases = []
                    for candidate in batch.cases:
                        old_result = evaluate(old_rule, candidate.input_data)
                        proposed_result = evaluate(proposed_rule, candidate.input_data)
                        case = TestCase(
                            **candidate.model_dump(),
                            category=category,
                            expected_old_result=old_result.outcome,
                            expected_proposed_result=proposed_result.outcome,
                            expected_outcome=(
                                "behavior_changed"
                                if old_result.outcome != proposed_result.outcome
                                else "behavior_unchanged"
                            ),
                            test_id=f"TC-{suite_token}-{len(completed) + len(batch_cases) + 1:02d}",
                            rule_id=proposed_rule.rule_id,
                            change_id=proposed_rule.change_id,
                        )
                        validate_case(
                            case, old_rule, proposed_rule, unrelated
                        )
                        batch_cases.append(case)
                    candidate_scenarios = {
                        scenario_key(case)
                        for case in [*completed, *batch_cases]
                    }
                    if len(candidate_scenarios) != len(completed) + len(batch_cases):
                        raise ValueError(
                            "Groq returned duplicate scenarios or inputs. Return "
                            "different scenarios with different input data."
                        )
                    completed.extend(batch_cases)
                    break
                except OutputParserException:
                    if attempt == MAX_BATCH_ATTEMPTS - 1:
                        raise
                    prompt += (
                        "\nThe previous response failed schema validation. Return "
                        "one JSON object with the required cases array and only "
                        "scenario and input_data for each case."
                    )
                except ValueError as exc:
                    if attempt == MAX_BATCH_ATTEMPTS - 1:
                        raise
                    prompt += (
                        f"\nThe previous batch was rejected: {exc}. Return a new "
                        "batch satisfying the requested category and rules. Recheck "
                        "every candidate against both rule versions before responding. "
                        "The actual_old_result and actual_proposed_result below were "
                        "calculated by the deterministic rule engine; correct any "
                        "input that does not meet the requested category. Do not repeat "
                        "any rejected or previously accepted scenario or input; provide "
                        "distinct input values and scenario descriptions. "
                        f"Rejected batch for correction: {json.dumps(attempted_batch)}"
                    )
            remaining -= count

    return validate_cases(
        completed, old_rule, proposed_rule, unrelated
    )
