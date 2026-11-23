import re
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


Operator = Literal["gt", "gte", "lt", "lte", "eq", "ne", "between"]


class RuleCondition(StrictModel):
    field: str = Field(min_length=1, max_length=64)
    operator: Operator
    value: Any
    upper_value: Any | None = None

    @field_validator("field")
    @classmethod
    def validate_field(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value):
            raise ValueError("Rule fields must be simple identifiers.")
        return value

    @model_validator(mode="after")
    def validate_values(self) -> "RuleCondition":
        if any(
            isinstance(value, float) and not math.isfinite(value)
            for value in (self.value, self.upper_value)
        ):
            raise ValueError("Rule comparison values must be finite.")
        if self.operator == "between":
            if self.upper_value is None:
                raise ValueError("The between operator requires upper_value.")
            if (
                isinstance(self.value, bool)
                or isinstance(self.upper_value, bool)
                or not isinstance(self.value, (int, float))
                or not isinstance(self.upper_value, (int, float))
                or self.value > self.upper_value
            ):
                raise ValueError("Between bounds must be ordered numeric values.")
        elif self.upper_value is not None:
            raise ValueError("upper_value is only valid for the between operator.")

        if self.operator in {"gt", "gte", "lt", "lte"}:
            if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
                raise ValueError("Ordered comparisons require a numeric threshold.")
        elif self.operator in {"eq", "ne"} and not isinstance(
            self.value, (str, int, float, bool)
        ):
            raise ValueError("Equality comparisons require a scalar value.")
        return self


class SandboxRule(StrictModel):
    rule_id: str = Field(min_length=1, max_length=128)
    version: int = Field(ge=1)
    change_id: str = Field(min_length=1, max_length=128)
    product_type: str = Field(min_length=1, max_length=128)
    conditions: list[RuleCondition] = Field(default_factory=list)
    logical_operator: Literal["AND", "OR"] = "AND"
    outcome_when_matched: str = Field(min_length=1, max_length=128)
    outcome_when_unmatched: str = Field(min_length=1, max_length=128)
    manual_review_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_executable_condition(self) -> "SandboxRule":
        if not self.conditions and not self.manual_review_reason:
            raise ValueError(
                "A deterministic rule needs conditions or an explicit manual-review reason."
            )
        return self


class GeneratedTestCase(StrictModel):
    scenario: str = Field(min_length=1, max_length=500)
    input_data: dict[str, Any]


class TestCaseCandidate(StrictModel):
    category: Literal[
        "positive_normal",
        "negative",
        "boundary_value",
        "edge_case",
        "regression",
        "missing_data_exception",
        "conflicting_rule",
    ]
    scenario: str = Field(min_length=1, max_length=500)
    input_data: dict[str, Any]
    expected_old_result: str = Field(min_length=1, max_length=128)
    expected_proposed_result: str = Field(min_length=1, max_length=128)
    expected_outcome: Literal["behavior_changed", "behavior_unchanged"]

    @model_validator(mode="after")
    def check_expected_outcome(self) -> "TestCaseCandidate":
        changed = self.expected_old_result != self.expected_proposed_result
        if changed != (self.expected_outcome == "behavior_changed"):
            raise ValueError("Expected outcome does not match expected rule results.")
        if self.category == "conflicting_rule" and not changed:
            raise ValueError("Conflicting-rule cases must exercise differing rule results.")
        if self.category == "regression" and changed:
            raise ValueError("Regression cases must expect unchanged behavior.")
        return self


class TestCase(TestCaseCandidate):
    test_id: str = Field(min_length=1, max_length=128)
    rule_id: str = Field(min_length=1, max_length=128)
    change_id: str = Field(min_length=1, max_length=128)


class RuleEvaluation(StrictModel):
    rule_id: str
    version: int
    outcome: str
    status: Literal[
        "evaluated", "missing_input", "invalid_input", "manual_review"
    ]
    detail: str | None = None


class ExecutionResult(StrictModel):
    test_id: str
    rule_id: str
    change_id: str
    input_data: dict[str, Any]
    expected_old_result: str
    actual_old_result: str
    expected_proposed_result: str
    actual_proposed_result: str
    status: Literal["passed", "failed", "pending"]
    failure_reason: str | None = None
    executed_at: str


class TestExecutionResult(ExecutionResult):
    result_id: str


class RuleExecution(StrictModel):
    execution_id: str
    suite_id: str
    test_id: str
    rule_id: str
    rule_version: int = Field(ge=1)
    input_data: dict[str, Any]
    expected_result: str
    actual_result: str
    status: Literal["passed", "failed", "pending"]
    failure_reason: str | None = None
    executed_at: str


class RegressionResult(StrictModel):
    test_id: str
    product_type: str | None
    expected_behavior_change: bool
    actual_behavior_change: bool | None
    category: Literal[
        "expected_behavior_change",
        "unaffected",
        "unexpected_behavior_change",
        "unrelated_product_affected",
        "pending",
    ]
    passed: bool | None
    detail: str


class SandboxTestSuite(StrictModel):
    suite_id: str
    document_id: str
    rule_id: str
    change_id: str
    status: Literal[
        "generating",
        "generation_failed",
        "manual_review",
        "ready",
        "execution_pending",
        "execution_failed",
        "completed",
    ]
    generated_at: str
    failure_reason: str | None = None
    baseline_rule: SandboxRule | None = None
    proposed_rule: SandboxRule | None = None
    test_cases: list[TestCase] = Field(default_factory=list)
    execution_results: list[TestExecutionResult] = Field(default_factory=list)
    regression_results: list[RegressionResult] = Field(default_factory=list)


class SandboxExecutionHistory(StrictModel):
    history_id: str
    suite_id: str
    event: str
    timestamp: str
    details: dict[str, Any]
