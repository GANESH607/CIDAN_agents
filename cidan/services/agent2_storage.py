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


def get_agent2_output_dir(workflow_id: str, create: bool = True) -> Path:
    if not workflow_id or not isinstance(workflow_id, str):
        raise ValueError("Workflow ID must be a non-empty string.")
    if not re.fullmatch(r"[a-zA-Z0-9_\-]+", workflow_id):
        raise ValueError(f"Invalid workflow ID: {workflow_id}")
    directory = WORKFLOW_OUTPUTS_DIR / workflow_id / "agent_2_policy_mapping"
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def _atomic_write_json(file_path: Path, data: dict[str, Any] | list[Any]) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(f".tmp_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    temp_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    temp_path.replace(file_path)
    return file_path


def _archive_run(output_dir: Path, filename: str, payload: dict[str, Any], mapping_run_id: str | None = None) -> None:
    run_id = mapping_run_id or payload.get("mapping_run_id")
    if run_id and re.fullmatch(r"[a-zA-Z0-9_\-]+", str(run_id)):
        run_dir = output_dir / "runs" / str(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(run_dir / filename, payload)


def save_policy_findings(
    workflow_id: str,
    findings: list[dict[str, Any]],
    obligations: list[dict[str, Any]] | None = None,
    mapping_run_id: str | None = None,
) -> Path:
    output_dir = get_agent2_output_dir(workflow_id, create=True)
    status_counts: dict[str, int] = {}
    for finding in findings:
        status = finding.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "mapping_run_id": mapping_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_findings": len(findings),
        "status_counts": status_counts,
        "findings": findings,
    }
    if obligations is not None:
        payload["obligations_evaluated"] = len(obligations)

    path = _atomic_write_json(output_dir / "policy_findings.json", payload)
    _archive_run(output_dir, "policy_findings.json", payload, mapping_run_id)
    return path


def save_evidence_and_citations(
    workflow_id: str,
    evidence_records: list[dict[str, Any]],
    mapping_run_id: str | None = None,
) -> Path:
    output_dir = get_agent2_output_dir(workflow_id, create=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "mapping_run_id": mapping_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_citations": len(evidence_records),
        "evidence": evidence_records,
    }
    path = _atomic_write_json(output_dir / "evidence_and_citations.json", payload)
    _archive_run(output_dir, "evidence_and_citations.json", payload, mapping_run_id)
    return path


def save_mapping_summary(
    workflow_id: str,
    summary: dict[str, Any],
    mapping_run_id: str | None = None,
) -> Path:
    output_dir = get_agent2_output_dir(workflow_id, create=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "mapping_run_id": mapping_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **summary,
    }
    path = _atomic_write_json(output_dir / "mapping_summary.json", payload)
    _archive_run(output_dir, "mapping_summary.json", payload, mapping_run_id)
    return path


def save_execution_metadata(
    workflow_id: str,
    metadata: dict[str, Any],
    mapping_run_id: str | None = None,
) -> Path:
    output_dir = get_agent2_output_dir(workflow_id, create=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "mapping_run_id": mapping_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **metadata,
    }
    path = _atomic_write_json(output_dir / "execution_metadata.json", payload)
    _archive_run(output_dir, "execution_metadata.json", payload, mapping_run_id)
    return path


def load_policy_findings(workflow_id: str) -> dict[str, Any]:
    output_dir = get_agent2_output_dir(workflow_id, create=False)
    file_path = output_dir / "policy_findings.json"
    if not file_path.exists():
        raise FileNotFoundError(f"Policy findings not found for workflow {workflow_id}")
    return json.loads(file_path.read_text(encoding="utf-8"))
