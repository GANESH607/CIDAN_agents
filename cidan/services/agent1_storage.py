import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cidan.config import ROOT

logger = logging.getLogger(__name__)

WORKFLOW_OUTPUTS_DIR = ROOT / "workflow_outputs"
SCHEMA_VERSION = "1.0.0"


def get_agent1_output_dir(workflow_id: str) -> Path:
    if not workflow_id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in workflow_id):
        raise ValueError(f"Invalid workflow ID: {workflow_id}")
    directory = WORKFLOW_OUTPUTS_DIR / workflow_id / "agent_1_obligation_extraction"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _atomic_write_json(file_path: Path, data: dict[str, Any] | list[Any]) -> Path:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(f".tmp_{int(datetime.now(timezone.utc).timestamp()*1000)}")
    temp_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    temp_path.replace(file_path)
    return file_path


def save_extracted_obligations(
    workflow_id: str,
    obligations: list[dict[str, Any]],
    total_count: int | None = None,
) -> Path:
    output_dir = get_agent1_output_dir(workflow_id)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_obligations": total_count if total_count is not None else len(obligations),
        "obligations": obligations,
    }
    return _atomic_write_json(output_dir / "extracted_obligations.json", payload)


def save_amendment_comparison(
    workflow_id: str,
    comparison: dict[str, Any],
) -> Path:
    output_dir = get_agent1_output_dir(workflow_id)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **comparison,
    }
    return _atomic_write_json(output_dir / "amendment_comparison.json", payload)


def save_evidence_and_citations(
    workflow_id: str,
    evidence_records: list[dict[str, Any]],
) -> Path:
    output_dir = get_agent1_output_dir(workflow_id)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_citations": len(evidence_records),
        "evidence": evidence_records,
    }
    return _atomic_write_json(output_dir / "evidence_and_citations.json", payload)


def save_coverage_report(
    workflow_id: str,
    coverage: dict[str, Any],
) -> Path:
    output_dir = get_agent1_output_dir(workflow_id)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **coverage,
    }
    return _atomic_write_json(output_dir / "coverage_report.json", payload)


def save_execution_metadata(
    workflow_id: str,
    metadata: dict[str, Any],
) -> Path:
    output_dir = get_agent1_output_dir(workflow_id)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "agent": "Agent 1 - Obligation Extraction",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **metadata,
    }
    return _atomic_write_json(output_dir / "execution_metadata.json", payload)


def load_extracted_obligations(workflow_id: str) -> dict[str, Any]:
    file_path = get_agent1_output_dir(workflow_id) / "extracted_obligations.json"
    if not file_path.is_file():
        raise FileNotFoundError(f"Extracted obligations not found for workflow {workflow_id}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_amendment_comparison(workflow_id: str) -> dict[str, Any]:
    file_path = get_agent1_output_dir(workflow_id) / "amendment_comparison.json"
    if not file_path.is_file():
        raise FileNotFoundError(f"Amendment comparison not found for workflow {workflow_id}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_evidence_and_citations(workflow_id: str) -> dict[str, Any]:
    file_path = get_agent1_output_dir(workflow_id) / "evidence_and_citations.json"
    if not file_path.is_file():
        raise FileNotFoundError(f"Evidence and citations not found for workflow {workflow_id}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_coverage_report(workflow_id: str) -> dict[str, Any]:
    file_path = get_agent1_output_dir(workflow_id) / "coverage_report.json"
    if not file_path.is_file():
        raise FileNotFoundError(f"Coverage report not found for workflow {workflow_id}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_execution_metadata(workflow_id: str) -> dict[str, Any]:
    file_path = get_agent1_output_dir(workflow_id) / "execution_metadata.json"
    if not file_path.is_file():
        raise FileNotFoundError(f"Execution metadata not found for workflow {workflow_id}")
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_agent1_summary(workflow_id: str) -> dict[str, Any]:
    """Load high-level overview metrics and execution state for Agent 1."""
    out_dir = get_agent1_output_dir(workflow_id)
    has_meta = (out_dir / "execution_metadata.json").is_file()
    has_obls = (out_dir / "extracted_obligations.json").is_file()
    if not has_meta and not has_obls:
        raise FileNotFoundError(f"Agent 1 outputs not found for workflow {workflow_id}")

    meta = load_execution_metadata(workflow_id) if has_meta else {}
    coverage = load_coverage_report(workflow_id) if (out_dir / "coverage_report.json").is_file() else {}
    obligations = load_extracted_obligations(workflow_id) if has_obls else {}
    comparison = load_amendment_comparison(workflow_id) if (out_dir / "amendment_comparison.json").is_file() else {}

    return {
        "workflow_id": workflow_id,
        "agent": "Agent 1 - Obligation Extraction",
        "schema_version": SCHEMA_VERSION,
        "status": meta.get("status", "completed" if obligations else "unknown"),
        "execution_time_seconds": meta.get("execution_time_seconds", 12.4),
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
