from datetime import datetime, timezone

from cidan.models import ApprovalRecord
from cidan.sandbox import repository as sandbox_repository
from cidan.sandbox.service import get_suite
from cidan.workflow.persistence import audit, list_workflows, save_workflow


def _require_successful_sandbox(
    rule_id: str,
    change_id: str | None,
    version: int,
) -> None:
    if not change_id:
        raise ValueError("Rule approval requires a traceable proposed change ID.")
    suites = sandbox_repository.suites_for_rule(rule_id, change_id)
    if not suites:
        raise ValueError("Rule approval requires a completed 50-case sandbox suite.")
    report = get_suite(suites[0]["suite_id"])
    if (
        report["status"] != "completed"
        or report["change_id"] != change_id
        or report["proposed_rule"]["version"] != version
        or report["total_generated"] != 50
        or report["total_executed"] != 50
        or report["passed"] != 50
        or report["failed"] != 0
        or report["pending"] != 0
        or len(report["regression_results"]) != 50
        or any(item["passed"] is not True for item in report["regression_results"])
    ):
        raise ValueError("Rule approval requires 50 passing executions and regressions.")


def approve_rule(rule_id: str, reviewer_id: str, note: str = "") -> dict:
    if not reviewer_id.strip():
        raise ValueError("Reviewer identifier is required.")
    for workflow in list_workflows():
        for rule in workflow.get("proposals", []):
            if rule.get("rule_id") != rule_id:
                continue
            if rule.get("status") != "validated":
                raise ValueError("Rule approval requires successful validation.")
            tests = workflow.get("tests", [])
            if not tests or any(test["failed"] or test["invalid"] for test in tests):
                raise ValueError("Rule approval requires executed, passing validation tests.")
            _require_successful_sandbox(
                rule_id, rule.get("change_id"), rule["version"]
            )
            approval = ApprovalRecord(
                rule_id=rule_id,
                version=rule["version"],
                reviewer_id=reviewer_id,
                decision="approve",
                approved_at=datetime.now(timezone.utc),
                note=note,
            )
            rule["status"] = "approved_for_export"
            rule["approval"] = approval.model_dump(mode="json")
            save_workflow(workflow)
            audit("rule_approved_locally", {
                "workflow_id": workflow["workflow_id"], "rule_id": rule_id,
                "version": rule["version"], "reviewer_id": reviewer_id,
            })
            return rule
    raise FileNotFoundError(f"Rule not found: {rule_id}")


def export_preview(rule_id: str) -> dict:
    for workflow in list_workflows():
        for rule in workflow.get("proposals", []):
            if rule.get("rule_id") != rule_id:
                continue
            if rule.get("status") != "approved_for_export" or not rule.get("approval"):
                raise PermissionError("Explicit local human approval is required before export.")
            tests = workflow.get("tests", [])
            if not tests or any(test["failed"] or test["invalid"] for test in tests):
                raise ValueError("Export requires completed validation with no failed or invalid tests.")
            _require_successful_sandbox(
                rule_id, rule.get("change_id"), rule["version"]
            )
            package = {
                "environment": "SIMULATION_ONLY",
                "rule": rule,
                "validation": tests,
                "source_evidence": rule["supporting_citations"],
                "rollback_notes": rule["rollback_considerations"],
                "disclaimer": "Local preview only. Not legal approval or production deployment.",
            }
            audit("rule_export_previewed", {
                "workflow_id": workflow["workflow_id"], "rule_id": rule_id,
            })
            return package
    raise FileNotFoundError(f"Rule not found: {rule_id}")
