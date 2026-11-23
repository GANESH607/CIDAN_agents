import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cidan.config import ROOT

logger = logging.getLogger(__name__)

WORKFLOW_OUTPUTS_DIR = ROOT / "workflow_outputs"
SCHEMA_VERSION = "1.1.0"


def get_agent1_output_dir(workflow_id: str, create: bool = True) -> Path:
    if not workflow_id or not isinstance(workflow_id, str):
        raise ValueError("Workflow ID must be a non-empty string.")
    if not re.fullmatch(r"[a-zA-Z0-9_\-]+", workflow_id):
        raise ValueError(f"Invalid workflow ID: {workflow_id}")
    directory = WORKFLOW_OUTPUTS_DIR / workflow_id / "agent_1_obligation_extraction"
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def _atomic_write_json(file_path: Path, data: dict[str, Any] | list[Any]) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(f".tmp_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    temp_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    temp_path.replace(file_path)
    return file_path


def _archive_run(output_dir: Path, filename: str, payload: dict[str, Any], extraction_run_id: str | None = None) -> None:
    run_id = extraction_run_id or payload.get("extraction_run_id")
    if run_id and re.fullmatch(r"[a-zA-Z0-9_\-]+", str(run_id)):
        run_dir = output_dir / "runs" / str(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write_json(run_dir / filename, payload)


def save_extracted_obligations(
    workflow_id: str,
    obligations: list[dict[str, Any]],
    total_count: int | None = None,
    extraction_run_id: str | None = None,
) -> Path:
    output_dir = get_agent1_output_dir(workflow_id, create=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "extraction_run_id": extraction_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_obligations": total_count if total_count is not None else len(obligations),
        "obligations": obligations,
    }
    path = _atomic_write_json(output_dir / "extracted_obligations.json", payload)
    _archive_run(output_dir, "extracted_obligations.json", payload, extraction_run_id)
    return path


def save_amendment_comparison(
    workflow_id: str,
    comparison: dict[str, Any],
    extraction_run_id: str | None = None,
) -> Path:
    output_dir = get_agent1_output_dir(workflow_id, create=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "extraction_run_id": extraction_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **comparison,
    }
    path = _atomic_write_json(output_dir / "amendment_comparison.json", payload)
    _archive_run(output_dir, "amendment_comparison.json", payload, extraction_run_id)
    return path


def save_evidence_and_citations(
    workflow_id: str,
    evidence_records: list[dict[str, Any]],
    extraction_run_id: str | None = None,
) -> Path:
    output_dir = get_agent1_output_dir(workflow_id, create=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "extraction_run_id": extraction_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_citations": len(evidence_records),
        "evidence": evidence_records,
    }
    path = _atomic_write_json(output_dir / "evidence_and_citations.json", payload)
    _archive_run(output_dir, "evidence_and_citations.json", payload, extraction_run_id)
    return path


def save_coverage_report(
    workflow_id: str,
    coverage: dict[str, Any],
    extraction_run_id: str | None = None,
) -> Path:
    output_dir = get_agent1_output_dir(workflow_id, create=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "extraction_run_id": extraction_run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **coverage,
    }
    path = _atomic_write_json(output_dir / "coverage_report.json", payload)
    _archive_run(output_dir, "coverage_report.json", payload, extraction_run_id)
    return path


def save_execution_metadata(
    workflow_id: str,
    metadata: dict[str, Any],
    extraction_run_id: str | None = None,
) -> Path:
    output_dir = get_agent1_output_dir(workflow_id, create=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "extraction_run_id": extraction_run_id or metadata.get("extraction_run_id"),
        "agent": "Agent 1 - Obligation Extraction",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **metadata,
    }
    path = _atomic_write_json(output_dir / "execution_metadata.json", payload)
    _archive_run(output_dir, "execution_metadata.json", payload, extraction_run_id)
    return path


def load_extracted_obligations(workflow_id: str) -> dict[str, Any]:
    file_path = get_agent1_output_dir(workflow_id, create=False) / "extracted_obligations.json"
    if not file_path.is_file():
        raise FileNotFoundError(f"Extracted obligations not found for workflow {workflow_id}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_amendment_comparison(workflow_id: str) -> dict[str, Any]:
    file_path = get_agent1_output_dir(workflow_id, create=False) / "amendment_comparison.json"
    if not file_path.is_file():
        raise FileNotFoundError(f"Amendment comparison not found for workflow {workflow_id}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_evidence_and_citations(workflow_id: str) -> dict[str, Any]:
    file_path = get_agent1_output_dir(workflow_id, create=False) / "evidence_and_citations.json"
    if not file_path.is_file():
        raise FileNotFoundError(f"Evidence and citations not found for workflow {workflow_id}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_coverage_report(workflow_id: str) -> dict[str, Any]:
    file_path = get_agent1_output_dir(workflow_id, create=False) / "coverage_report.json"
    if not file_path.is_file():
        raise FileNotFoundError(f"Coverage report not found for workflow {workflow_id}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_execution_metadata(workflow_id: str) -> dict[str, Any]:
    file_path = get_agent1_output_dir(workflow_id, create=False) / "execution_metadata.json"
    if not file_path.is_file():
        raise FileNotFoundError(f"Execution metadata not found for workflow {workflow_id}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_agent1_summary(workflow_id: str) -> dict[str, Any]:
    """Load high-level overview metrics and execution state for Agent 1."""
    out_dir = get_agent1_output_dir(workflow_id, create=False)
    has_meta = (out_dir / "execution_metadata.json").is_file()
    has_obls = (out_dir / "extracted_obligations.json").is_file()
    if not has_meta and not has_obls:
        raise FileNotFoundError(f"Agent 1 outputs not found for workflow {workflow_id}")

    meta = load_execution_metadata(workflow_id) if has_meta else {}
    coverage = load_coverage_report(workflow_id) if (out_dir / "coverage_report.json").is_file() else {}
    obligations = load_extracted_obligations(workflow_id) if has_obls else {}
    comparison = load_amendment_comparison(workflow_id) if (out_dir / "amendment_comparison.json").is_file() else {}

    exec_duration = meta.get("duration_seconds")
    if exec_duration is None:
        exec_duration = meta.get("execution_time_seconds")

    return {
        "workflow_id": workflow_id,
        "agent": "Agent 1 - Obligation Extraction",
        "schema_version": SCHEMA_VERSION,
        "status": meta.get("status", "completed" if obligations else "unknown"),
        "execution_time_seconds": exec_duration,
        "duration_seconds": exec_duration,
        "documents_processed": meta.get("documents_processed", coverage.get("documents_count", 0)),
        "document_names": meta.get("document_names", []),
        "total_pages": coverage.get("total_pages", 0),
        "obligations_extracted": obligations.get("total_obligations", len(obligations.get("obligations", []))),
        "coverage_percentage": coverage.get("coverage_percentage", 100.0),
        "change_analysis": comparison.get("summary", {
            "new": sum(1 for o in obligations.get("obligations", []) if o.get("change_classification") == "NEW"),
            "modified": sum(1 for o in obligations.get("obligations", []) if o.get("change_classification") == "MODIFIED"),
            "unchanged": sum(1 for o in obligations.get("obligations", []) if o.get("change_classification") == "UNCHANGED"),
        }),
        "quality_checks": coverage.get("quality_checks", {}),
    }


def list_agent1_workflows() -> list[str]:
    """List workflow IDs that have saved Agent 1 outputs."""
    if not WORKFLOW_OUTPUTS_DIR.is_dir():
        return []
    result = []
    for d in sorted(WORKFLOW_OUTPUTS_DIR.iterdir()):
        if d.is_dir() and (d / "agent_1_obligation_extraction" / "extracted_obligations.json").is_file():
            result.append(d.name)
    return result
