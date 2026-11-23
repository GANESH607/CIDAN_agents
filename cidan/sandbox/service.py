from typing import Any, Callable
from uuid import uuid4

from cidan.sandbox import repository
from cidan.sandbox.execution import execute_suite
from cidan.sandbox.generation import generate_cases
from cidan.sandbox.reporting import build_report
from cidan.sandbox.schemas import SandboxRule


def generate_suite(
    *,
    document_id: str,
    change_id: str,
    baseline_rule: SandboxRule,
    proposed_rule: SandboxRule,
    unrelated_product_types: list[str],
    llm_call: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    suite_id = str(uuid4())
    repository.create_suite(
        suite_id,
        document_id,
        proposed_rule.rule_id,
        change_id,
    )
    try:
        cases = generate_cases(
            baseline_rule,
            proposed_rule,
            unrelated_product_types=unrelated_product_types,
            **({"llm_call": llm_call} if llm_call else {}),
        )
        repository.save_generated_cases(suite_id, baseline_rule, proposed_rule, cases)
    except Exception as exc:
        repository.mark_generation_failed(suite_id, str(exc))
        raise
    return build_report(repository.load_suite(suite_id))


def record_manual_review(
    *,
    document_id: str,
    rule_id: str,
    change_id: str,
    reason: str,
) -> dict[str, Any]:
    suite_id = str(uuid4())
    repository.create_suite(suite_id, document_id, rule_id, change_id)
    repository.mark_manual_review(suite_id, reason)
    return build_report(repository.load_suite(suite_id))


def get_suite(suite_id: str) -> dict[str, Any]:
    return build_report(repository.load_suite(suite_id))


def run_suite(suite_id: str) -> dict[str, Any]:
    return build_report(execute_suite(suite_id))


def get_history(suite_id: str) -> list[dict[str, Any]]:
    return repository.history(suite_id)


def list_suites() -> list[dict[str, Any]]:
    return repository.list_suites()
