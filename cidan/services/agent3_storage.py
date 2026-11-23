import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cidan.config import ROOT

logger = logging.getLogger(__name__)

WORKFLOW_OUTPUTS_DIR = ROOT / "workflow_outputs"
SCHEMA_VERSION = "1.0.0"


def get_agent3_output_dir(workflow_id: str, create: bool = True) -> Path:
    if not workflow_id or not isinstance(workflow_id, str):
        raise ValueError("Workflow ID must be a non-empty string.")
    if not re.fullmatch(r"[a-zA-Z0-9_\-]+", workflow_id):
        raise ValueError(f"Invalid workflow ID: {workflow_id}")
    directory = WORKFLOW_OUTPUTS_DIR / workflow_id / "agent_3_rule_authoring"
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def _atomic_write_json(file_path: Path, data: dict[str, Any] | list[Any]) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(f".tmp_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    temp_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    temp_path.replace(file_path)
    return file_path


def _archive_run(output_dir: Path, filename: str, payload: dict[str, Any], run_id: str | None = None) -> None:
    arch_id = run_id or payload.get("run_id") or payload.get("authoring_run_id")
    if arch_id and re.fullmatch(r"[a-zA-Z0-9_\-]+", str(arch_id)):
        run_dir = output_dir / "runs" / str(arch_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(run_dir / filename, payload)


def save_rule_proposals(
    workflow_id: str,
    proposals: list[dict[str, Any]],
    eligible_count: int | None = None,
    run_id: str | None = None,
) -> Path:
    output_dir = get_agent3_output_dir(workflow_id, create=True)
    status_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    risk_counts: dict[str, int] = {}
    sandbox_ready_count = 0

    serialized_proposals = []
    for item in proposals:
        p_dict = item if isinstance(item, dict) else item.model_dump(mode="json")
        if not p_dict.get("obligation_id"):
            ob_ids = p_dict.get("source_obligation_ids", [])
            p_dict["obligation_id"] = ob_ids[0] if ob_ids else ""
        if not p_dict.get("proposed_rule"):
            p_dict["proposed_rule"] = p_dict.get("description", "")
        if not p_dict.get("reason_for_change"):
            p_dict["reason_for_change"] = p_dict.get("business_purpose", "")
        st = p_dict.get("status", "draft")
        status_counts[st] = status_counts.get(st, 0) + 1
        act = p_dict.get("action", "flag_review")
        action_counts[act] = action_counts.get(act, 0) + 1
        rk = p_dict.get("risk_level", "undetermined")
        risk_counts[rk] = risk_counts.get(rk, 0) + 1
        is_sandbox_ready = bool(p_dict.get("baseline_rule") and p_dict.get("sandbox_rule"))
        p_dict["sandbox_readiness"] = is_sandbox_ready
        if is_sandbox_ready:
            sandbox_ready_count += 1
        serialized_proposals.append(p_dict)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "authoring_run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_proposals": len(serialized_proposals),
        "eligible_findings_evaluated": eligible_count or len(serialized_proposals),
        "draft_count": status_counts.get("draft", len(serialized_proposals)),
        "sandbox_ready_count": sandbox_ready_count,
        "status_counts": status_counts,
        "action_counts": action_counts,
        "risk_counts": risk_counts,
        "proposals": serialized_proposals,
    }

    path = _atomic_write_json(output_dir / "rule_proposals.json", payload)
    _archive_run(output_dir, "rule_proposals.json", payload, run_id)
    return path


def save_evidence_and_citations(
    workflow_id: str,
    evidence_records: list[dict[str, Any]],
    run_id: str | None = None,
) -> Path:
    output_dir = get_agent3_output_dir(workflow_id, create=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "authoring_run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_citations": len(evidence_records),
        "evidence": evidence_records,
    }
    path = _atomic_write_json(output_dir / "evidence_and_citations.json", payload)
    _archive_run(output_dir, "evidence_and_citations.json", payload, run_id)
    return path


def save_rule_summary(
    workflow_id: str,
    summary: dict[str, Any],
    run_id: str | None = None,
) -> Path:
    output_dir = get_agent3_output_dir(workflow_id, create=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "authoring_run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **summary,
    }
    path = _atomic_write_json(output_dir / "rule_summary.json", payload)
    _archive_run(output_dir, "rule_summary.json", payload, run_id)
    return path


def save_execution_metadata(
    workflow_id: str,
    metadata: dict[str, Any],
    run_id: str | None = None,
) -> Path:
    output_dir = get_agent3_output_dir(workflow_id, create=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "authoring_run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **metadata,
    }
    path = _atomic_write_json(output_dir / "execution_metadata.json", payload)
    _archive_run(output_dir, "execution_metadata.json", payload, run_id)
    return path


def load_rule_proposals(workflow_id: str) -> dict[str, Any]:
    output_dir = get_agent3_output_dir(workflow_id, create=False)
    file_path = output_dir / "rule_proposals.json"
    if not file_path.exists():
        raise FileNotFoundError(f"Rule proposals not found for workflow {workflow_id}")
    data = json.loads(file_path.read_text(encoding="utf-8"))
    for p in data.get("proposals", []):
        if not p.get("obligation_id"):
            ob_ids = p.get("source_obligation_ids", [])
            p["obligation_id"] = ob_ids[0] if ob_ids else ""
        if not p.get("proposed_rule"):
            p["proposed_rule"] = p.get("description", "")
        if not p.get("reason_for_change"):
            p["reason_for_change"] = p.get("business_purpose", "")
    return data


def load_evidence_and_citations(workflow_id: str) -> dict[str, Any]:
    output_dir = get_agent3_output_dir(workflow_id, create=False)
    file_path = output_dir / "evidence_and_citations.json"
    if not file_path.exists():
        proposals_data = load_rule_proposals(workflow_id)
        evidence_records = []
        for p in proposals_data.get("proposals", []):
            rule_id = p.get("rule_id", "")
            ob_id = p.get("obligation_id") or (p.get("source_obligation_ids", [""])[0])
            for cite in p.get("supporting_citations", []):
                evidence_records.append({
                    "rule_id": rule_id,
                    "obligation_id": ob_id,
                    "document_id": cite.get("document_id"),
                    "filename": cite.get("filename"),
                    "document_type": cite.get("document_type"),
                    "page": cite.get("page", 1),
                    "chunk_id": cite.get("chunk_id", ""),
                    "excerpt": cite.get("excerpt", ""),
                    "is_valid": False,
                    "validation_status": "not_available",
                })
        return {
            "schema_version": SCHEMA_VERSION,
            "workflow_id": workflow_id,
            "total_citations": len(evidence_records),
            "evidence": evidence_records,
        }
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_rule_summary(workflow_id: str) -> dict[str, Any]:
    output_dir = get_agent3_output_dir(workflow_id, create=False)
    file_path = output_dir / "rule_summary.json"
    if not file_path.exists():
        proposals_data = load_rule_proposals(workflow_id)
        proposals = proposals_data.get("proposals", [])
        status_counts: dict[str, int] = {}
        action_counts: dict[str, int] = {}
        risk_counts: dict[str, int] = {}
        sandbox_ready = 0
        human_review = 0
        for p in proposals:
            st = p.get("status", "draft")
            status_counts[st] = status_counts.get(st, 0) + 1
            act = p.get("action", "flag_review")
            action_counts[act] = action_counts.get(act, 0) + 1
            rk = p.get("risk_level", "undetermined")
            risk_counts[rk] = risk_counts.get(rk, 0) + 1
            if p.get("sandbox_readiness") or (p.get("baseline_rule") and p.get("sandbox_rule")):
                sandbox_ready += 1
            if p.get("action") == "flag_review" or p.get("unresolved_questions") or p.get("review_reasons"):
                human_review += 1

        return {
            "schema_version": SCHEMA_VERSION,
            "workflow_id": workflow_id,
            "total_proposals": len(proposals),
            "draft_count": status_counts.get("draft", len(proposals)),
            "sandbox_ready_count": sandbox_ready,
            "human_review_required_count": human_review,
            "status_counts": status_counts,
            "action_counts": action_counts,
            "risk_counts": risk_counts,
        }
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_execution_metadata(workflow_id: str) -> dict[str, Any]:
    output_dir = get_agent3_output_dir(workflow_id, create=False)
    file_path = output_dir / "execution_metadata.json"
    if not file_path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "workflow_id": workflow_id,
            "status": "completed",
            "agent": "agent_3_rule_authoring",
        }
    return json.loads(file_path.read_text(encoding="utf-8"))


def list_agent3_workflows() -> list[str]:
    """List workflow IDs that have saved Agent 3 outputs."""
    if not WORKFLOW_OUTPUTS_DIR.is_dir():
        return []
    result = []
    for d in sorted(WORKFLOW_OUTPUTS_DIR.iterdir()):
        if d.is_dir() and (d / "agent_3_rule_authoring" / "rule_proposals.json").is_file():
            result.append(d.name)
    return result
