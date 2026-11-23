import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from cidan.config import get_settings
from cidan.sandbox.schemas import (
    ExecutionResult,
    RegressionResult,
    RuleExecution,
    SandboxExecutionHistory,
    SandboxRule,
    SandboxTestSuite,
    TestCase,
    TestExecutionResult,
)


def _database_path() -> Path:
    return get_settings().outputs_directory / "sandbox.sqlite3"


def _connect() -> sqlite3.Connection:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize() -> None:
    with _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sandbox_test_suites (
                suite_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                change_id TEXT NOT NULL,
                status TEXT NOT NULL,
                baseline_rule_json TEXT,
                proposed_rule_json TEXT,
                generated_at TEXT NOT NULL,
                failure_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS test_cases (
                test_id TEXT PRIMARY KEY,
                suite_id TEXT NOT NULL REFERENCES sandbox_test_suites(suite_id),
                category TEXT NOT NULL,
                case_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rule_executions (
                execution_id TEXT PRIMARY KEY,
                suite_id TEXT NOT NULL REFERENCES sandbox_test_suites(suite_id),
                test_id TEXT NOT NULL REFERENCES test_cases(test_id),
                rule_id TEXT NOT NULL,
                rule_version INTEGER NOT NULL,
                input_json TEXT NOT NULL,
                expected_result TEXT NOT NULL,
                actual_result TEXT NOT NULL,
                status TEXT NOT NULL,
                failure_reason TEXT,
                executed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS test_execution_results (
                result_id TEXT PRIMARY KEY,
                suite_id TEXT NOT NULL REFERENCES sandbox_test_suites(suite_id),
                test_id TEXT NOT NULL REFERENCES test_cases(test_id),
                result_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS regression_results (
                regression_id TEXT PRIMARY KEY,
                suite_id TEXT NOT NULL REFERENCES sandbox_test_suites(suite_id),
                test_id TEXT NOT NULL REFERENCES test_cases(test_id),
                result_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sandbox_execution_history (
                history_id TEXT PRIMARY KEY,
                suite_id TEXT NOT NULL REFERENCES sandbox_test_suites(suite_id),
                event TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_test_cases_suite ON test_cases(suite_id);
            CREATE INDEX IF NOT EXISTS idx_execution_results_suite ON test_execution_results(suite_id);
            CREATE INDEX IF NOT EXISTS idx_history_suite ON sandbox_execution_history(suite_id);
            """
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_suite(
    suite_id: str,
    document_id: str,
    rule_id: str,
    change_id: str,
) -> None:
    initialize()
    with _connect() as connection:
        connection.execute(
            """INSERT INTO sandbox_test_suites
               (suite_id, document_id, rule_id, change_id, status, generated_at)
               VALUES (?, ?, ?, ?, 'generating', ?)""",
            (suite_id, document_id, rule_id, change_id, _now()),
        )
        _history(connection, suite_id, "generation_started", {"rule_id": rule_id, "change_id": change_id})


def save_generated_cases(
    suite_id: str,
    baseline: SandboxRule,
    proposed: SandboxRule,
    cases: list[TestCase],
) -> None:
    initialize()
    with _connect() as connection:
        connection.execute(
            """UPDATE sandbox_test_suites
               SET baseline_rule_json = ?, proposed_rule_json = ?, status = 'ready',
                   failure_reason = NULL
               WHERE suite_id = ?""",
            (
                baseline.model_dump_json(),
                proposed.model_dump_json(),
                suite_id,
            ),
        )
        if connection.total_changes == 0:
            raise FileNotFoundError(f"Sandbox suite not found: {suite_id}")
        connection.executemany(
            "INSERT INTO test_cases (test_id, suite_id, category, case_json) VALUES (?, ?, ?, ?)",
            [
                (case.test_id, suite_id, case.category, case.model_dump_json())
                for case in cases
            ],
        )
        _history(
            connection,
            suite_id,
            "generation_completed",
            {"generated_count": len(cases)},
        )


def mark_generation_failed(suite_id: str, reason: str) -> None:
    initialize()
    with _connect() as connection:
        connection.execute(
            "UPDATE sandbox_test_suites SET status = 'generation_failed', failure_reason = ? WHERE suite_id = ?",
            (reason[:2000], suite_id),
        )
        _history(connection, suite_id, "generation_failed", {"reason": reason[:2000]})


def mark_manual_review(suite_id: str, reason: str) -> None:
    initialize()
    with _connect() as connection:
        connection.execute(
            "UPDATE sandbox_test_suites SET status = 'manual_review', failure_reason = ? WHERE suite_id = ?",
            (reason[:2000], suite_id),
        )
        _history(connection, suite_id, "manual_review_required", {"reason": reason[:2000]})


def load_suite(suite_id: str) -> dict[str, Any]:
    initialize()
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM sandbox_test_suites WHERE suite_id = ?", (suite_id,)
        ).fetchone()
        if row is None:
            raise FileNotFoundError(f"Sandbox suite not found: {suite_id}")
        cases = connection.execute(
            "SELECT case_json FROM test_cases WHERE suite_id = ? ORDER BY rowid",
            (suite_id,),
        ).fetchall()
        results = connection.execute(
            "SELECT result_json FROM test_execution_results WHERE suite_id = ? ORDER BY rowid",
            (suite_id,),
        ).fetchall()
        regressions = connection.execute(
            "SELECT result_json FROM regression_results WHERE suite_id = ? ORDER BY rowid",
            (suite_id,),
        ).fetchall()
        suite = {
            "suite_id": row["suite_id"],
            "document_id": row["document_id"],
            "rule_id": row["rule_id"],
            "change_id": row["change_id"],
            "status": row["status"],
            "failure_reason": row["failure_reason"],
            "generated_at": row["generated_at"],
            "baseline_rule": json.loads(row["baseline_rule_json"]) if row["baseline_rule_json"] else None,
            "proposed_rule": json.loads(row["proposed_rule_json"]) if row["proposed_rule_json"] else None,
            "test_cases": [json.loads(item["case_json"]) for item in cases],
            "execution_results": [json.loads(item["result_json"]) for item in results],
            "regression_results": [json.loads(item["result_json"]) for item in regressions],
        }
        return SandboxTestSuite.model_validate(suite).model_dump(mode="json")


def list_suites() -> list[dict[str, Any]]:
    initialize()
    with _connect() as connection:
        rows = connection.execute(
            """SELECT suite_id, document_id, rule_id, change_id, status,
                      generated_at, failure_reason
               FROM sandbox_test_suites ORDER BY generated_at DESC"""
        ).fetchall()
        return [dict(row) for row in rows]


def suites_for_rule(
    rule_id: str,
    change_id: str,
) -> list[dict[str, Any]]:
    initialize()
    with _connect() as connection:
        rows = connection.execute(
            """SELECT suite_id, document_id, rule_id, change_id, status, generated_at
               FROM sandbox_test_suites
               WHERE rule_id = ? AND change_id = ?
               ORDER BY generated_at DESC""",
            (rule_id, change_id),
        ).fetchall()
        return [dict(row) for row in rows]


def history(suite_id: str) -> list[dict[str, Any]]:
    initialize()
    with _connect() as connection:
        exists = connection.execute(
            "SELECT 1 FROM sandbox_test_suites WHERE suite_id = ?", (suite_id,)
        ).fetchone()
        if exists is None:
            raise FileNotFoundError(f"Sandbox suite not found: {suite_id}")
        rows = connection.execute(
            """SELECT event, timestamp, details_json FROM sandbox_execution_history
               WHERE suite_id = ? ORDER BY timestamp, rowid""",
            (suite_id,),
        ).fetchall()
        return [
            {
                "event": row["event"],
                "timestamp": row["timestamp"],
                "details": json.loads(row["details_json"]),
            }
            for row in rows
        ]


def save_execution(
    suite_id: str,
    results: list[ExecutionResult],
    regressions: list[RegressionResult],
) -> None:
    initialize()
    suite = load_suite(suite_id)
    statuses = [result.status for result in results]
    status = "completed" if results and all(item == "passed" for item in statuses) else (
        "execution_pending" if not results or "pending" in statuses else "execution_failed"
    )
    with _connect() as connection:
        connection.execute(
            "UPDATE sandbox_test_suites SET status = ? WHERE suite_id = ?",
            (status, suite_id),
        )
        for result in results:
            for rule_version, expected, actual in (
                (
                    suite["baseline_rule"]["version"],
                    result.expected_old_result,
                    result.actual_old_result,
                ),
                (
                    suite["proposed_rule"]["version"],
                    result.expected_proposed_result,
                    result.actual_proposed_result,
                ),
            ):
                execution = RuleExecution(
                    execution_id=str(uuid4()),
                    suite_id=suite_id,
                    test_id=result.test_id,
                    rule_id=result.rule_id,
                    rule_version=rule_version,
                    input_data=result.input_data,
                    expected_result=expected,
                    actual_result=actual,
                    status=result.status,
                    failure_reason=result.failure_reason,
                    executed_at=result.executed_at,
                )
                connection.execute(
                    """INSERT INTO rule_executions
                       (execution_id, suite_id, test_id, rule_id, rule_version,
                        input_json, expected_result, actual_result, status,
                        failure_reason, executed_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        execution.execution_id, execution.suite_id, execution.test_id,
                        execution.rule_id, execution.rule_version,
                        json.dumps(execution.input_data, allow_nan=False),
                        execution.expected_result, execution.actual_result,
                        execution.status, execution.failure_reason, execution.executed_at,
                    ),
                )
            result_record = TestExecutionResult(
                result_id=str(uuid4()), **result.model_dump()
            )
            connection.execute(
                "INSERT INTO test_execution_results (result_id, suite_id, test_id, result_json) VALUES (?, ?, ?, ?)",
                (
                    result_record.result_id,
                    suite_id,
                    result.test_id,
                    result_record.model_dump_json(),
                ),
            )
        connection.executemany(
            "INSERT INTO regression_results (regression_id, suite_id, test_id, result_json) VALUES (?, ?, ?, ?)",
            [
                (str(uuid4()), suite_id, item.test_id, item.model_dump_json())
                for item in regressions
            ],
        )
        _history(
            connection,
            suite_id,
            "execution_completed",
            {
                "executed_count": len(results),
                "passed": statuses.count("passed"),
                "failed": statuses.count("failed"),
                "pending": statuses.count("pending"),
                "regressions": len(regressions),
                "status": status,
            },
        )


def _history(
    connection: sqlite3.Connection,
    suite_id: str,
    event: str,
    details: dict[str, Any],
) -> None:
    record = SandboxExecutionHistory(
        history_id=str(uuid4()),
        suite_id=suite_id,
        event=event,
        timestamp=_now(),
        details=details,
    )
    connection.execute(
        """INSERT INTO sandbox_execution_history
           (history_id, suite_id, event, timestamp, details_json)
           VALUES (?, ?, ?, ?, ?)""",
        (
            record.history_id,
            record.suite_id,
            record.event,
            record.timestamp,
            json.dumps(record.details, allow_nan=False),
        ),
    )
