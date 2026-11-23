import json

import pytest

from cidan.services.approval_service import approve_rule, export_preview
from cidan.services import approval_service
from cidan.workflow import persistence


def proposal(status):
    return {
        "rule_id": "draft-1", "version": 1, "change_id": "change-1", "status": status,
        "supporting_citations": [{"filename": "circular.pdf", "page": 1}],
        "rollback_considerations": "Restore prior local config.",
    }


def write_workflow(directory, status):
    directory.mkdir(parents=True, exist_ok=True)
    data = {
        "workflow_id": "workflow-1", "proposals": [proposal(status)],
        "tests": [{"failed": 0, "invalid": 0, "total": 1, "passed": 1}],
    }
    (directory / "workflow-1.json").write_text(json.dumps(data), encoding="utf-8")


def test_draft_approval_requires_completed_validation_and_reviewer(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "WORKFLOWS_DIR", tmp_path / "workflows")
    monkeypatch.setattr(persistence, "AUDIT_PATH", tmp_path / "audit.jsonl")
    write_workflow(tmp_path / "workflows", "draft")
    path = tmp_path / "workflows" / "workflow-1.json"
    workflow = json.loads(path.read_text(encoding="utf-8"))
    workflow["tests"] = [{"failed": 1, "invalid": 0, "total": 1, "passed": 0}]
    path.write_text(json.dumps(workflow), encoding="utf-8")
    with pytest.raises(ValueError, match="Reviewer identifier"):
        approve_rule("draft-1", "")
    with pytest.raises(ValueError, match="executed, passing validation tests"):
        approve_rule("draft-1", "reviewer-7")


def test_validated_draft_stays_unapproved_until_human_approval(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "WORKFLOWS_DIR", tmp_path / "workflows")
    monkeypatch.setattr(persistence, "AUDIT_PATH", tmp_path / "audit.jsonl")
    write_workflow(tmp_path / "workflows", "draft")
    monkeypatch.setattr(approval_service, "_require_successful_sandbox", lambda *_args: None)

    approved = approve_rule("draft-1", "reviewer-7", "Reviewed local test results.")

    assert approved["status"] == "approved_for_export"
    assert approved["approval"]["reviewer_id"] == "reviewer-7"


def test_approval_is_audited_after_sandbox_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "WORKFLOWS_DIR", tmp_path / "workflows")
    monkeypatch.setattr(persistence, "AUDIT_PATH", tmp_path / "audit.jsonl")
    write_workflow(tmp_path / "workflows", "validated")
    with pytest.raises(PermissionError):
        export_preview("draft-1")
    with pytest.raises(ValueError, match="completed 50-case sandbox suite"):
        approve_rule("draft-1", "reviewer-7", "Reviewed locally.")
    monkeypatch.setattr(approval_service, "_require_successful_sandbox", lambda *_args: None)
    approved = approve_rule("draft-1", "reviewer-7", "Reviewed locally.")
    assert approved["status"] == "approved_for_export"
    assert approved["approval"]["reviewer_id"] == "reviewer-7"
    package = export_preview("draft-1")
    assert package["environment"] == "SIMULATION_ONLY"
    audit = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert "rule_approved_locally" in audit
    assert "rule_export_previewed" in audit


def test_manual_review_suite_cannot_approve_rule(tmp_path, monkeypatch):
    from cidan.sandbox import repository

    monkeypatch.setenv("OUTPUTS_DIRECTORY", str(tmp_path / "outputs"))
    monkeypatch.setattr(persistence, "WORKFLOWS_DIR", tmp_path / "workflows")
    write_workflow(tmp_path / "workflows", "validated")
    repository.create_suite("suite-manual", "doc-1", "draft-1", "change-1")
    repository.mark_manual_review("suite-manual", "No deterministic baseline.")
    with pytest.raises(ValueError, match="50 passing executions and regressions"):
        approve_rule("draft-1", "reviewer-7")
