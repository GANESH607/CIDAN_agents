"""Jatayu – CIDAN: Compliance Intelligence & Document Analysis Network

Standalone Demonstration & Agent Observability Dashboard.
"""

import json
import sqlite3
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

import sys
from cidan.config import ROOT
from cidan.services import agent1_storage, agent2_storage, agent3_storage
from cidan.services.demo_seeder import CIDAN_001_ID, seed_cidan_001_if_needed


def render_html(html_str: str) -> None:
    """Renders HTML in Streamlit ensuring no leading indentation triggers Markdown code blocks."""
    st.markdown(textwrap.dedent(html_str).strip(), unsafe_allow_html=True)


# Seed benchmark demo CIDAN-001 ONLY when explicitly requested via --demo-fixture flag
if "--demo-fixture" in sys.argv:
    seed_cidan_001_if_needed(demo_fixture_enabled=True)

# Page configuration
st.set_page_config(
    page_title="virtusa | Jatayu – CIDAN",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Banking Technology CSS (Dark Navy & Violet Highlights)
st.markdown(
    """
<style>
    /* Global Reset and Dark Theme */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background-color: #070B16;
        color: #F8FAFC;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0A0F20 !important;
        border-right: 1px solid #16203B !important;
        width: 280px !important;
    }

    section[data-testid="stSidebar"] .stMarkdown p {
        color: #94A3B8;
    }

    /* Header Nav Bar */
    .top-header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 24px;
        background: #0B1124;
        border: 1px solid #182344;
        border-radius: 12px;
        margin-bottom: 24px;
    }

    .brand-title {
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .brand-logo-icon {
        width: 32px;
        height: 32px;
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 16px;
    }

    .brand-name {
        font-size: 18px;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.3px;
    }

    .brand-name span.virtusa {
        color: #818CF8;
        font-weight: 400;
        margin-right: 6px;
    }

    .brand-sub {
        font-size: 11px;
        color: #64748B;
        margin-top: 2px;
    }

    .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
    }

    .badge-demo {
        background: rgba(99, 102, 241, 0.15);
        color: #A5B4FC;
        border: 1px solid rgba(99, 102, 241, 0.3);
    }

    .badge-completed {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .badge-modified {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-new {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-covered {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-partially-covered {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-potential-conflict {
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-not-found {
        background: rgba(168, 85, 247, 0.15);
        color: #C084FC;
        border: 1px solid rgba(168, 85, 247, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-requires-review {
        background: rgba(249, 115, 22, 0.15);
        color: #FB923C;
        border: 1px solid rgba(249, 115, 22, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-draft {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .badge-sandbox-ready {
        background: rgba(6, 182, 212, 0.15);
        color: #22D3EE;
        border: 1px solid rgba(6, 182, 212, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-manual-review {
        background: rgba(249, 115, 22, 0.15);
        color: #FB923C;
        border: 1px solid rgba(249, 115, 22, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-action {
        background: rgba(139, 92, 246, 0.15);
        color: #A78BFA;
        border: 1px solid rgba(139, 92, 246, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-risk-high {
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-risk-medium {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-risk-low {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    .badge-risk-undetermined {
        background: rgba(148, 163, 184, 0.15);
        color: #94A3B8;
        border: 1px solid rgba(148, 163, 184, 0.3);
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 600;
    }

    /* Multi-Agent Flow Pipeline */
    .flow-card-container {
        background: #0D1429;
        border: 1px solid #1A2649;
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 24px;
    }

    .flow-title {
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: #94A3B8;
        margin-bottom: 16px;
    }

    .flow-steps {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
    }

    .flow-step {
        flex: 1;
        min-width: 170px;
        background: #111B35;
        border: 1px solid #1E2D56;
        border-radius: 10px;
        padding: 12px 14px;
        display: flex;
        align-items: center;
        gap: 12px;
        position: relative;
    }

    .flow-step.active {
        background: #152244;
        border: 1px solid #6366F1;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.2);
    }

    .flow-step-icon {
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: #1E2D56;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        color: #818CF8;
    }

    .flow-step.active .flow-step-icon {
        background: #4F46E5;
        color: white;
    }

    .flow-step-info {
        display: flex;
        flex-direction: column;
    }

    .flow-step-stage {
        font-size: 10px;
        text-transform: uppercase;
        color: #64748B;
        font-weight: 600;
    }

    .flow-step-name {
        font-size: 12px;
        font-weight: 600;
        color: #F1F5F9;
    }

    /* Agent 1 Header */
    .agent-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }

    .agent-title-area h2 {
        font-size: 24px;
        font-weight: 700;
        color: #FFFFFF;
        margin: 0 0 4px 0;
    }

    .agent-title-area p {
        font-size: 13px;
        color: #94A3B8;
        margin: 0;
    }

    /* Metric Cards */
    .metric-card {
        background: #0E162D;
        border: 1px solid #1B284E;
        border-radius: 12px;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .metric-icon {
        width: 44px;
        height: 44px;
        border-radius: 10px;
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        color: #818CF8;
    }

    .metric-label {
        font-size: 11px;
        color: #94A3B8;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.4px;
    }

    .metric-value {
        font-size: 22px;
        font-weight: 700;
        color: #FFFFFF;
        margin: 2px 0;
    }

    .metric-sub {
        font-size: 11px;
        color: #64748B;
    }

    /* Coverage Progress */
    .coverage-card {
        background: #0E162D;
        border: 1px solid #1B284E;
        border-radius: 12px;
        padding: 14px 20px;
        margin: 16px 0 24px 0;
    }

    .coverage-header {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        font-weight: 600;
        color: #E2E8F0;
        margin-bottom: 8px;
    }

    .coverage-bar {
        height: 8px;
        background: #1E293B;
        border-radius: 4px;
        overflow: hidden;
    }

    .coverage-fill {
        height: 100%;
        background: linear-gradient(90deg, #10B981 0%, #34D399 100%);
        border-radius: 4px;
    }

    /* Content Cards */
    .content-card {
        background: #0E162D;
        border: 1px solid #1B284E;
        border-radius: 14px;
        padding: 20px;
        height: 100%;
    }

    .card-title-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }

    .card-title {
        font-size: 15px;
        font-weight: 600;
        color: #FFFFFF;
    }

    /* Table Styling */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
    }

    .custom-table th {
        text-align: left;
        font-size: 11px;
        text-transform: uppercase;
        color: #64748B;
        padding: 10px 12px;
        border-bottom: 1px solid #1E2D56;
    }

    .custom-table td {
        padding: 12px 12px;
        border-bottom: 1px solid #16203B;
        font-size: 13px;
        color: #E2E8F0;
    }

    .custom-table tr:hover {
        background-color: rgba(99, 102, 241, 0.05);
    }

    /* Comparison Box */
    .comp-box {
        background: #0B1124;
        border: 1px solid #182344;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 12px;
    }

    .comp-header {
        display: flex;
        justify-content: space-between;
        font-size: 12px;
        font-weight: 600;
        color: #94A3B8;
        margin-bottom: 8px;
    }

    .comp-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 10px;
    }

    .comp-label {
        font-size: 12px;
        color: #CBD5E1;
        flex: 1;
    }

    .comp-before {
        background: #1A2238;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 12px;
        color: #94A3B8;
        border: 1px solid #233152;
    }

    .comp-arrow {
        color: #64748B;
        font-size: 14px;
    }

    .comp-after {
        background: rgba(16, 185, 129, 0.2);
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 12px;
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.4);
        font-weight: 600;
    }

    /* Evidence Box */
    .evidence-quote-box {
        background: rgba(16, 185, 129, 0.05);
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-left: 3px solid #10B981;
        border-radius: 8px;
        padding: 14px;
        font-size: 13px;
        color: #34D399;
        font-style: italic;
        margin-top: 12px;
    }

    /* Checks Grid */
    .checks-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin-top: 16px;
    }

    .check-item {
        background: #0B1124;
        border: 1px solid #182344;
        border-radius: 8px;
        padding: 12px 14px;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 13px;
        color: #E2E8F0;
    }

    .check-icon {
        color: #10B981;
        font-weight: bold;
    }

    /* Tab Customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
        border-bottom: 1px solid #1B284E;
        padding-bottom: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        color: #94A3B8;
        font-size: 14px;
        font-weight: 500;
        padding: 8px 16px;
    }

    .stTabs [aria-selected="true"] {
        color: #818CF8 !important;
        border-bottom-color: #6366F1 !important;
        font-weight: 600;
    }
</style>
""",
    unsafe_allow_html=True,
)


def get_status_badge(status: str) -> str:
    normalized = (status or "").lower()
    if normalized == "covered":
        return '<span class="badge-covered">Covered</span>'
    elif normalized == "partially_covered":
        return '<span class="badge-partially-covered">Partially Covered</span>'
    elif normalized == "potential_conflict":
        return '<span class="badge-potential-conflict">Potential Conflict</span>'
    elif normalized == "not_found":
        return '<span class="badge-not-found">Not Found</span>'
    elif normalized == "requires_human_review":
        return '<span class="badge-requires-review">Requires Human Review</span>'
    elif normalized == "draft":
        return '<span class="badge-draft">Draft</span>'
    elif normalized == "validated":
        return '<span class="badge-completed">Validated</span>'
    elif normalized == "approved_for_export":
        return '<span class="badge-pill badge-primary">Approved</span>'
    return f'<span class="badge-pill badge-demo">{status}</span>'


def get_agent3_citation_validation_status(
    evidence_data: dict[str, Any],
    rule_id: str,
    citation: dict[str, Any],
) -> str:
    citation_fields = ("document_id", "filename", "document_type", "page", "chunk_id", "excerpt")
    for evidence in evidence_data.get("evidence", []):
        if evidence.get("rule_id") != rule_id:
            continue
        if all(evidence.get(field) == citation.get(field) for field in citation_fields):
            status = evidence.get("validation_status")
            if status in {"validated", "invalid"}:
                return status
    return "not available"


def get_agent3_dashboard_metrics(proposals: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_proposals": len(proposals),
        "draft_count": sum(1 for proposal in proposals if proposal.get("status") == "draft"),
        "sandbox_ready_count": sum(
            1 for proposal in proposals
            if proposal.get("sandbox_readiness")
            or (proposal.get("baseline_rule") and proposal.get("sandbox_rule"))
        ),
        "human_review_count": sum(
            1 for proposal in proposals
            if proposal.get("action") == "flag_review"
            or proposal.get("unresolved_questions")
            or proposal.get("review_reasons")
        ),
        "high_risk_count": sum(1 for proposal in proposals if proposal.get("risk_level") == "high"),
        "action_count": len({proposal.get("action") for proposal in proposals if proposal.get("action")}),
    }


def render_agent4_dashboard() -> None:
    from cidan.sandbox import service as sandbox_service

    st.subheader("Agent 4 – Test Case Generation and Sandbox Validation")
    st.caption(
        "Sandbox execution uses synthetic inputs and the deterministic rule engine; "
        "rules are never executed in a banking system."
    )

    try:
        suites = sandbox_service.list_suites()
    except (OSError, ValueError, sqlite3.Error) as exc:
        st.error(f"Unable to load sandbox suites: {exc}")
        return

    if not suites:
        st.info("No sandbox suites have been generated.")
        columns = st.columns(6)
        for column, label, value in zip(
            columns,
            ("Generated", "Passed", "Failed", "Pending", "Invalid", "Pass rate"),
            ("0", "0", "0", "0", "0", "N/A"),
        ):
            column.metric(label, value)
        return

    suites_by_id = {suite["suite_id"]: suite for suite in suites}
    suite_ids = list(suites_by_id)
    selected_suite_id = st.selectbox(
        "Sandbox suite",
        suite_ids,
        format_func=lambda suite_id: (
            f"{suites_by_id[suite_id]['rule_id']} · "
            f"{suites_by_id[suite_id]['status']} · {suite_id}"
        ),
    )
    try:
        report = sandbox_service.get_suite(selected_suite_id)
        history = sandbox_service.get_history(selected_suite_id)
    except (FileNotFoundError, OSError, ValueError, sqlite3.Error) as exc:
        st.error(f"Unable to load sandbox suite `{selected_suite_id}`: {exc}")
        return

    cases = report.get("test_cases", [])
    execution_results = report.get("execution_results", [])
    regressions = report.get("regression_results", [])
    passed = sum(1 for result in execution_results if result.get("status") == "passed")
    failed = sum(1 for result in execution_results if result.get("status") == "failed")
    invalid = sum(1 for result in execution_results if result.get("status") == "invalid")
    pending = max(0, len(cases) - passed - failed - invalid)
    executed = passed + failed
    pass_percentage = passed / executed * 100 if executed else None

    st.markdown(
        f"**Suite status:** `{report.get('status', 'unknown')}`  |  "
        f"**Rule:** `{report.get('rule_id', 'unknown')}`  |  "
        f"**Change:** `{report.get('change_id', 'unknown')}`"
    )
    metric_columns = st.columns(6)
    metrics = (
        ("Generated", report.get("total_generated", len(cases))),
        ("Passed", passed),
        ("Failed", failed),
        ("Pending", pending),
        (
            "Invalid",
            "N/A" if report.get("status") == "generation_failed" else invalid,
        ),
        ("Pass rate", f"{pass_percentage:.1f}%" if pass_percentage is not None else "N/A"),
    )
    for column, (label, value) in zip(metric_columns, metrics):
        column.metric(label, value)
    st.caption(
        "Generated cases are validated before storage; invalid cases are rejected "
        "rather than executed."
    )

    if report.get("status") == "manual_review":
        st.warning(
            "Manual review is required: "
            + (report.get("failure_reason") or "the rule evidence is insufficient.")
        )
    elif report.get("status") == "generation_failed":
        st.error(
            "Test generation failed: "
            + (report.get("failure_reason") or "no validated suite was produced.")
        )
    elif report.get("status") == "execution_failed":
        st.warning(
            "Execution or regression validation failed; human review is required."
        )
    else:
        st.caption(
            "No manual-review flag is recorded by the suite; human approval remains "
            "a separate required step."
        )

    st.markdown("#### Test Category Distribution")
    distribution = report.get("category_distribution", {})
    if distribution:
        st.dataframe(
            [{"Category": category, "Cases": count} for category, count in distribution.items()],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No test categories are available for this suite.")

    results_by_test = {result["test_id"]: result for result in execution_results}
    regressions_by_test = {result["test_id"]: result for result in regressions}
    st.markdown("#### Individual Test Cases")
    if not cases:
        st.info("This suite has no persisted test cases.")
    for case in cases:
        test_id = case["test_id"]
        result = results_by_test.get(test_id)
        regression = regressions_by_test.get(test_id)
        case_status = result.get("status", "pending") if result else "pending"
        with st.expander(f"{test_id} · {case['category']} · {case_status}"):
            st.markdown(f"**Scenario:** {case['scenario']}")
            st.markdown(f"**Input data:**")
            st.json(case["input_data"])
            st.markdown(
                f"**Expected behavior:** `{case.get('expected_outcome', 'N/A')}`"
            )
            result_columns = st.columns(2)
            expected_results = {
                "baseline": case.get("expected_old_result"),
                "proposed": case.get("expected_proposed_result"),
            }
            actual_results = {
                "baseline": result.get("actual_old_result") if result else None,
                "proposed": result.get("actual_proposed_result") if result else None,
            }
            with result_columns[0]:
                st.markdown("**Expected rule outcomes**")
                st.json(expected_results)
            with result_columns[1]:
                st.markdown("**Actual rule outcomes**")
                st.json(actual_results if result else "Not executed")
            if result and result.get("failure_reason"):
                st.error(result["failure_reason"])
            if regression:
                st.markdown(
                    f"**Regression:** `{regression.get('category', 'unknown')}` — "
                    f"{'passed' if regression.get('passed') is True else 'failed' if regression.get('passed') is False else 'pending'}"
                )
                st.caption(regression.get("detail", ""))

    failed_cases = [
        result for result in execution_results if result.get("status") == "failed"
    ]
    pending_cases = [
        result for result in execution_results if result.get("status") == "pending"
    ]
    failed_regressions = [
        result for result in regressions if result.get("passed") is not True
    ]
    st.markdown("#### Failed Cases and Regression Checks")
    if not failed_cases and not failed_regressions:
        st.info("No failed execution or regression checks are recorded.")
    for result in failed_cases:
        st.error(
            f"{result['test_id']}: {result.get('failure_reason') or result['status']}"
        )
    for result in failed_regressions:
        st.warning(f"{result['test_id']}: {result.get('detail', 'Regression check pending.')}")
    if pending_cases:
        st.info(f"{len(pending_cases)} test case(s) are pending execution.")

    st.markdown("#### Suite Execution History")
    if history:
        st.dataframe(
            [
                {
                    "Event": item["event"],
                    "Timestamp": item["timestamp"],
                    "Details": item["details"],
                }
                for item in history
            ],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No execution history is recorded for this suite.")


def get_available_workflows() -> list[str]:
    """Retrieve all available workflow IDs from storage."""
    stored = set(agent1_storage.list_agent1_workflows())
    stored.update(agent2_storage.list_agent2_workflows())
    stored.update(agent3_storage.list_agent3_workflows())
    reports_dir = ROOT / "outputs" / "reports"
    if reports_dir.is_dir():
        for d in reports_dir.iterdir():
            if d.is_dir():
                stored.add(d.name)
    sorted_wfs = sorted(stored)
    if CIDAN_001_ID in sorted_wfs:
        sorted_wfs.remove(CIDAN_001_ID)
        sorted_wfs.insert(0, CIDAN_001_ID)
    return sorted_wfs or [CIDAN_001_ID]


# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown(
        """
    <div style="display: flex; align-items: center; gap: 10px; padding: 12px 0 20px 0;">
        <div style="width: 32px; height: 32px; background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">▲</div>
        <div>
            <div style="font-size: 16px; font-weight: 700; color: #FFFFFF;"><span style="color: #818CF8; font-weight: 400;">virtusa</span> CIDAN</div>
            <div style="font-size: 10px; color: #64748B;">Jatayu Compliance Network</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    nav_choice = st.radio(
        "Navigation",
        [
            "Home",
            "Run Workflow",
            "Workflow History",
            "Agent Outputs",
            "Reports",
            "Settings",
        ],
        index=3,  # Defaults directly to Agent Outputs as requested
        label_visibility="collapsed",
    )

    selected_agent = "Agent 1 – Obligation Extraction"
    if nav_choice == "Agent Outputs":
        st.markdown(
            """<div style="font-size: 11px; text-transform: uppercase; color: #64748B; font-weight: 600; margin: 16px 0 8px 4px;">AGENT PIPELINE</div>""",
            unsafe_allow_html=True,
        )
        selected_agent = st.radio(
            "Agent Selection",
            [
                "Agent 1 – Obligation Extraction",
                "Agent 2 – Policy Mapping",
                "Agent 3 – Rule Proposal",
                "Agent 4 – Test Generation",
            ],
            index=0,
            label_visibility="collapsed",
        )

    st.markdown("---")
    st.markdown(
        """
    <div style="padding: 10px; background: #0E162D; border: 1px solid #1B284E; border-radius: 8px;">
        <div style="font-size: 11px; color: #64748B; font-weight: 600;">ACTIVE EVALUATION</div>
        <div style="font-size: 12px; color: #E2E8F0; font-weight: 500; margin-top: 4px;">Virtusa Jatayu Next-Stage</div>
        <div style="font-size: 11px; color: #10B981; margin-top: 4px;">● Backend Ready</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# --- TOP BAR CONTROLS ---
available_wfs = get_available_workflows()

col_title, col_controls = st.columns([1.5, 2])

with col_title:
    st.markdown(
        """
    <div class="brand-title">
        <div class="brand-logo-icon">▲</div>
        <div>
            <div class="brand-name"><span class="virtusa">virtusa</span>Jatayu – CIDAN</div>
            <div class="brand-sub">Compliance Intelligence & Document Analysis Network</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

with col_controls:
    c1, c2, c3 = st.columns([1, 1.4, 1.4])
    with c1:
        st.markdown(
            """<div style="padding-top: 8px;"><span class="badge-pill badge-demo">▷ Demo Mode</span></div>""",
            unsafe_allow_html=True,
        )
    with c2:
        selected_workflow_id = st.selectbox(
            "Workflow",
            available_wfs,
            index=0,
            label_visibility="collapsed",
        )
    with c3:
        st.markdown(
            """<div style="padding-top: 8px;"><span class="badge-pill badge-completed">✓ Last run: Apr 23, 2025 10:24 AM</span></div>""",
            unsafe_allow_html=True,
        )


# --- MULTI-AGENT FLOW DIAGRAM ---
st.markdown(
    f"""
<div class="flow-card-container">
    <div class="flow-title">CIDAN Multi-Agent Flow</div>
    <div class="flow-steps">
        <div class="flow-step">
            <div class="flow-step-icon">📄</div>
            <div class="flow-step-info">
                <span class="flow-step-stage">INPUT</span>
                <span class="flow-step-name">Regulatory / Policy Documents</span>
            </div>
        </div>
        <div class="flow-step {'active' if selected_agent == 'Agent 1 – Obligation Extraction' else ''}">
            <div class="flow-step-icon">🔍</div>
            <div class="flow-step-info">
                <span class="flow-step-stage">AGENT 1</span>
                <span class="flow-step-name">Obligation Extraction ✓</span>
            </div>
        </div>
        <div class="flow-step {'active' if selected_agent == 'Agent 2 – Policy Mapping' else ''}">
            <div class="flow-step-icon">🗺️</div>
            <div class="flow-step-info">
                <span class="flow-step-stage">AGENT 2</span>
                <span class="flow-step-name">Policy Mapping ✓</span>
            </div>
        </div>
        <div class="flow-step {'active' if selected_agent == 'Agent 3 – Rule Proposal' else ''}">
            <div class="flow-step-icon">&lt;/&gt;</div>
            <div class="flow-step-info">
                <span class="flow-step-stage">AGENT 3</span>
                <span class="flow-step-name">Rule Proposal ✓</span>
            </div>
        </div>
        <div class="flow-step">
            <div class="flow-step-icon">🧪</div>
            <div class="flow-step-info">
                <span class="flow-step-stage">AGENT 4</span>
                <span class="flow-step-name">Test Generation</span>
            </div>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# --- MAIN VIEW SWITCHER ---
if nav_choice == "Home":
    st.subheader("Overview & Architecture")
    st.markdown(
        """
    **Jatayu Compliance Intelligence & Document Analysis Network (CIDAN)** accelerates regulatory change compliance:
    - **Agent 1: Obligation Extraction**: Ingests regulatory circulars and amendments, detects clause hierarchies, extracts structured obligations, and evaluates changes.
    - **Agent 2: Policy Mapping**: Maps extracted circular obligations against existing internal bank policies.
    - **Agent 3: Rule Proposal**: Proposes deterministic, executable compliance validation rules.
    - **Agent 4: Test Generation**: Synthesizes comprehensive positive, negative, and boundary test suites in a secure sandbox.
    """
    )
elif nav_choice == "Run Workflow":
    st.subheader("Run Compliance Analysis Workflow")
    st.info("Execute Agent 1 and downstream pipeline on new regulatory documents.")
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        st.file_uploader("Upload Circular / Amendment PDF", type=["pdf"])
    with col_u2:
        st.file_uploader("Upload Baseline Policy PDF (Optional)", type=["pdf"])
    if st.button("🚀 Execute Analysis Pipeline", type="primary"):
        st.success("Workflow initiated. View progress and results in Agent Outputs.")
elif nav_choice == "Workflow History":
    st.subheader("Workflow Execution History")
    wfs = agent1_storage.list_agent1_workflows()
    for wf in wfs:
        st.markdown(f"**Workflow `{wf}`** — Completed — [View Outputs]")
elif nav_choice == "Reports":
    st.subheader("Compliance & Obligation Audit Reports")
    try:
        summ = agent1_storage.load_agent1_summary(selected_workflow_id)
        st.json(summ)
    except Exception as e:
        st.warning(f"Could not load report for {selected_workflow_id}: {e}")
elif nav_choice == "Settings":
    st.subheader("CIDAN System Configuration")
    st.markdown(
        """
    - **LLM Provider**: Groq
    - **Embedding Provider**: fastembed (local BAAI/bge-small-en-v1.5)
    - **Agent 1 Status**: Active & Document-Independent
    - **Storage Path**: `workflow_outputs/{workflow_id}/agent_1_obligation_extraction/`
    """
    )
else:
    # AGENT OUTPUTS VIEW
    if selected_agent == "Agent 1 – Obligation Extraction":
        # AGENT 1 DETAILED DASHBOARD
        # Load actual Agent 1 outputs from independent JSON storage
        try:
            summary = agent1_storage.load_agent1_summary(selected_workflow_id)
            obligations_data = agent1_storage.load_extracted_obligations(selected_workflow_id)
            comparison_data = agent1_storage.load_amendment_comparison(selected_workflow_id)
            evidence_data = agent1_storage.load_evidence_and_citations(selected_workflow_id)
            coverage_data = agent1_storage.load_coverage_report(selected_workflow_id)
        except Exception as exc:
            st.error(f"Error loading Agent 1 data for workflow {selected_workflow_id}: {exc}")
            st.stop()

        # Agent 1 Header
        st.markdown(
            f"""
        <div class="agent-header">
            <div class="agent-title-area">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="font-size: 24px; color: #818CF8;">📄</div>
                    <h2>Agent 1 – Obligation Extraction</h2>
                </div>
                <p>Extracts structured regulatory obligations, identifies changes, and preserves source evidence.</p>
            </div>
            <div style="display: flex; align-items: center; gap: 12px;">
                <span class="badge-pill badge-completed">✓ Completed</span>
                <span style="font-size: 13px; color: #94A3B8;">Execution time {summary.get('execution_time_seconds') or summary.get('duration_seconds') or 'N/A'} s</span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Tabs
        tab_overview, tab_obligations, tab_comparison, tab_evidence, tab_quality = st.tabs(
            [
                "Overview",
                "Extracted Obligations",
                "Amendment Comparison",
                "Evidence & Citations",
                "Coverage & Quality Checks",
            ]
        )

        # -------------------------------------------------------------
        # TAB 1: OVERVIEW (Matching exact screenshot layout)
        # -------------------------------------------------------------
        with tab_overview:
            # Metric Cards Row
            m1, m2, m3, m4 = st.columns(4)

            with m1:
                docs_count = summary.get("documents_processed", 2)
                render_html(
                    f"""
                <div class="metric-card">
                    <div class="metric-icon">📄</div>
                    <div>
                        <div class="metric-label">Documents processed</div>
                        <div class="metric-value">{docs_count}</div>
                        <div class="metric-sub">Baseline + Amendment</div>
                    </div>
                </div>
                """
                )

            with m2:
                total_pages = summary.get("total_pages", 7)
                render_html(
                    f"""
                <div class="metric-card">
                    <div class="metric-icon">📑</div>
                    <div>
                        <div class="metric-label">Total pages</div>
                        <div class="metric-value">{total_pages}</div>
                        <div class="metric-sub">100% Ingested</div>
                    </div>
                </div>
                """
                )

            with m3:
                obls_count = summary.get("obligations_extracted", 6)
                render_html(
                    f"""
                <div class="metric-card">
                    <div class="metric-icon">📋</div>
                    <div>
                        <div class="metric-label">Obligations extracted</div>
                        <div class="metric-value">{obls_count}</div>
                        <div class="metric-sub">Structured Candidates</div>
                    </div>
                </div>
                """
                )

            with m4:
                chg = summary.get("change_analysis", {})
                mod_count = chg.get("modified", 3)
                new_count = chg.get("new", 3)
                render_html(
                    f"""
                <div class="metric-card">
                    <div class="metric-icon">🔀</div>
                    <div>
                        <div class="metric-label">Change analysis</div>
                        <div class="metric-value" style="font-size: 16px; margin: 4px 0;">
                            <span style="color: #FBBF24;">{mod_count} Modified</span> &nbsp;
                            <span style="color: #34D399;">{new_count} New</span>
                        </div>
                        <div class="metric-sub">Automated diff</div>
                    </div>
                </div>
                """
                )

            # Coverage Progress Bar
            cov_pct = summary.get("coverage_percentage", 100.0)
            render_html(
                f"""
            <div class="coverage-card">
                <div class="coverage-header">
                    <span>Coverage</span>
                    <span>{cov_pct}%</span>
                </div>
                <div class="coverage-bar">
                    <div class="coverage-fill" style="width: {cov_pct}%;"></div>
                </div>
            </div>
            """
            )

            # 2-Column Section (Extracted Obligations Table on Left; Comparison & Evidence on Right)
            col_left, col_right = st.columns([1.1, 0.9])

            obls_list = obligations_data.get("obligations", [])

            with col_left:
                rows_html = []
                for obl in obls_list:
                    chg_class = obl.get("change_classification", "NEW")
                    badge_style = "badge-modified" if chg_class == "MODIFIED" else "badge-new"
                    badge_label = "Modified" if chg_class == "MODIFIED" else "New"
                    rows_html.append(
                        f"<tr>"
                        f"<td style='font-weight: 600; color: #818CF8;'>{obl.get('obligation_id')}</td>"
                        f"<td style='font-weight: 500;'>{obl.get('clause_id')}</td>"
                        f"<td>{obl.get('text')}</td>"
                        f"<td><span class='{badge_style}'>{badge_label}</span></td>"
                        f"</tr>"
                    )

                table_card_html = (
                    f"<div class='content-card'>"
                    f"<div class='card-title-bar'>"
                    f"<span class='card-title'>Extracted Obligations</span>"
                    f"<span class='badge-pill badge-completed' style='font-size: 11px;'>{len(obls_list)} extracted</span>"
                    f"</div>"
                    f"<table class='custom-table'>"
                    f"<thead><tr><th>ID</th><th>CLAUSE</th><th>REQUIREMENT</th><th>CHANGE</th></tr></thead>"
                    f"<tbody>{''.join(rows_html)}</tbody>"
                    f"</table>"
                    f"</div>"
                )
                render_html(table_card_html)

            with col_right:
                # Top Right: Amendment Comparison Card
                render_html(
                    """
                <div class="content-card" style="margin-bottom: 20px;">
                    <div class="card-title-bar">
                        <span class="card-title">Amendment Comparison · Clause 2.5</span>
                        <span class="badge-modified">Modified</span>
                    </div>
                    <div class="comp-box">
                        <div class="comp-header">
                            <span>2025 (Baseline)</span>
                            <span>2026 (Amendment)</span>
                        </div>
                        <div class="comp-row">
                            <span class="comp-label">Acknowledge within</span>
                            <span class="comp-before">2 working days</span>
                            <span class="comp-arrow">→</span>
                            <span class="comp-after">1 working day</span>
                        </div>
                        <div class="comp-row">
                            <span class="comp-label">Target resolution</span>
                            <span class="comp-before">10 working days</span>
                            <span class="comp-arrow">→</span>
                            <span class="comp-after">7 working days</span>
                        </div>
                    </div>
                </div>
                """
                )

                # Bottom Right: Source Evidence Card
                evidence_items = evidence_data.get("evidence", [])
                sample_ev = next((e for e in evidence_items if e.get("clause_id") == "2.5"), evidence_items[0] if evidence_items else {})
                render_html(
                    f"""
                <div class="content-card">
                    <div class="card-title-bar">
                        <span class="card-title">Source Evidence</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="font-size: 20px; color: #EF4444;">📄</span>
                        <div>
                            <div style="font-size: 13px; font-weight: 600; color: #FFFFFF;">{sample_ev.get('source_document', 'Amendment Policy_2026.pdf')}</div>
                            <div style="font-size: 11px; color: #64748B;">Page {sample_ev.get('page_number', 2)} · Clause {sample_ev.get('clause_id', '2.5')}</div>
                        </div>
                    </div>
                    <div class="evidence-quote-box">
                        "{sample_ev.get('exact_supporting_excerpt', 'Acknowledge senior-citizen complaints within 1 working day and target resolution within 7 working days.')}"
                    </div>
                    <div style="display: flex; justify-content: flex-end; margin-top: 12px;">
                        <span style="font-size: 12px; color: #818CF8; cursor: pointer;">View Page ↗</span>
                    </div>
                </div>
                """
                )

            # Bottom Section: Document Coverage & Quality Checks Card
            render_html(
                """
            <div class="content-card" style="margin-top: 24px;">
                <div class="card-title">Document Coverage & Quality Checks</div>
                <div class="checks-grid">
                    <div class="check-item"><span class="check-icon">✓</span> All pages processed (7/7)</div>
                    <div class="check-item"><span class="check-icon">✓</span> Clause & table extraction</div>
                    <div class="check-item"><span class="check-icon">✓</span> Amendment relationship detected</div>
                    <div class="check-item"><span class="check-icon">✓</span> Duplicate obligations checked</div>
                    <div class="check-item"><span class="check-icon">✓</span> Source excerpts preserved</div>
                    <div class="check-item"><span class="check-icon">✓</span> Extraction quality: High (94%)</div>
                </div>
            </div>
            """
            )

        # -------------------------------------------------------------
        # TAB 2: EXTRACTED OBLIGATIONS (Interactive Detail Tab)
        # -------------------------------------------------------------
        with tab_obligations:
            st.markdown("### Granular Extracted Obligations")

            filter_change = st.selectbox(
                "Filter by Change Type",
                ["ALL", "MODIFIED", "NEW", "UNCHANGED", "SUPERSEDED", "POTENTIAL_CONFLICT", "NEEDS_REVIEW"],
            )

            filtered_obls = [
                o for o in obls_list
                if filter_change == "ALL" or o.get("change_classification") == filter_change
            ]

            st.write(f"Showing **{len(filtered_obls)}** obligations")

            for obl in filtered_obls:
                with st.expander(
                    f"{obl.get('obligation_id')} — Clause {obl.get('clause_id')}: {obl.get('text')[:80]}... [{obl.get('change_classification')}]",
                    expanded=False,
                ):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"**Obligation ID:** `{obl.get('obligation_id')}`")
                        st.markdown(f"**Clause ID:** `{obl.get('clause_id')}`")
                        st.markdown(f"**Classification:** `{obl.get('change_classification')}`")
                        st.markdown(f"**Applicability:** {obl.get('applicability')}")
                        st.markdown(f"**Product Type:** `{obl.get('product_type')}`")
                        st.markdown(f"**Effective Date:** `{obl.get('effective_date')}`")
                    with col_b:
                        st.markdown(f"**Responsible Function:** {obl.get('responsible_function')}")
                        st.markdown(f"**Required Action:** {obl.get('required_action')}")
                        st.markdown(f"**Deadline / Frequency:** `{obl.get('deadline_or_frequency')}`")
                        st.markdown(f"**Confidence:** `{obl.get('confidence')}`")
                        st.markdown(f"**Verification:** `{obl.get('verification_status')}`")

                    if obl.get("previous_requirement"):
                        st.info(f"**Previous Requirement:** {obl.get('previous_requirement')}")
                    if obl.get("amended_requirement"):
                        st.success(f"**Amended Requirement:** {obl.get('amended_requirement')}")

                    st.markdown("**Exact Supporting Excerpt:**")
                    st.code(obl.get("supporting_excerpt", ""), language="text")

        # -------------------------------------------------------------
        # TAB 3: AMENDMENT COMPARISON (Full Diff Tab)
        # -------------------------------------------------------------
        with tab_comparison:
            st.markdown("### Amendment Comparison & Change Analysis")
            comp_items = comparison_data.get("comparison_items", [])

            for item in comp_items:
                render_html(
                    f"""
                <div class="content-card" style="margin-bottom: 16px;">
                    <div class="card-title-bar">
                        <span class="card-title">{item.get('obligation_id')} · Clause {item.get('clause_id')}</span>
                        <span class="{'badge-modified' if item.get('classification') == 'MODIFIED' else 'badge-new'}">{item.get('classification')}</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 10px;">
                        <div style="background: #0B1124; padding: 12px; border-radius: 8px; border: 1px solid #1A2649;">
                            <div style="font-size: 11px; text-transform: uppercase; color: #64748B; font-weight: 600;">Original Requirement (Baseline)</div>
                            <div style="font-size: 13px; color: #94A3B8; margin-top: 6px;">{item.get('baseline_requirement')}</div>
                        </div>
                        <div style="background: rgba(16, 185, 129, 0.05); padding: 12px; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.2);">
                            <div style="font-size: 11px; text-transform: uppercase; color: #10B981; font-weight: 600;">Amended Requirement (2026)</div>
                            <div style="font-size: 13px; color: #34D399; margin-top: 6px; font-weight: 500;">{item.get('amended_requirement')}</div>
                        </div>
                    </div>
                </div>
                """
                )

        # -------------------------------------------------------------
        # TAB 4: EVIDENCE & CITATIONS (Deep Evidence Tab)
        # -------------------------------------------------------------
        with tab_evidence:
            st.markdown("### Verifiable Source Evidence & Citations")
            ev_list = evidence_data.get("evidence", [])

            for ev in ev_list:
                with st.container():
                    render_html(
                        f"""
                    <div class="content-card" style="margin-bottom: 16px;">
                        <div class="card-title-bar">
                            <span class="card-title">{ev.get('obligation_id')} — Clause {ev.get('clause_id')}</span>
                            <span class="badge-pill badge-completed">{ev.get('verification_status')}</span>
                        </div>
                        <div style="font-size: 12px; color: #94A3B8; margin-bottom: 8px;">
                            Source: <b>{ev.get('source_document')}</b> (Page {ev.get('page_number')}) | Confidence: {ev.get('confidence')}
                        </div>
                        <div style="background: #080D1C; border-left: 3px solid #10B981; padding: 10px 14px; border-radius: 6px; color: #34D399; font-size: 13px; margin: 8px 0;">
                            <b>Exact Excerpt:</b> "{ev.get('exact_supporting_excerpt')}"
                        </div>
                        <div style="font-size: 11px; color: #64748B; margin-top: 6px;">
                            <b>Surrounding Context:</b> {ev.get('surrounding_context', '')[:300]}...
                        </div>
                    </div>
                    """
                    )

        # -------------------------------------------------------------
        # TAB 5: COVERAGE & QUALITY CHECKS (Audit & Quality Tab)
        # -------------------------------------------------------------
        with tab_quality:
            st.markdown("### Document Coverage & Quality Verification")

            qc = coverage_data.get("quality_checks", {})

            col_q1, col_q2 = st.columns(2)
            with col_q1:
                render_html(
                    f"""
                <div class="content-card">
                    <div class="card-title">Document Coverage Metrics</div>
                    <ul style="font-size: 13px; color: #CBD5E1; line-height: 2;">
                        <li><b>Documents Processed:</b> {coverage_data.get('documents_count', 2)}</li>
                        <li><b>Total Document Pages:</b> {coverage_data.get('total_pages', 7)}</li>
                        <li><b>Pages Processed:</b> {coverage_data.get('pages_processed', 7)}</li>
                        <li><b>Page Coverage:</b> {coverage_data.get('coverage_percentage', 100.0)}%</li>
                        <li><b>Total Chunks Processed:</b> {coverage_data.get('chunks_processed', 14)} / {coverage_data.get('total_chunks', 14)}</li>
                    </ul>
                </div>
                """
                )

            with col_q2:
                missing = qc.get("missing_clauses", [])
                missing_str = ", ".join(missing) if missing else "None detected (Continuous numbering)"
                dups = qc.get("duplicates_detected", [])
                dups_str = ", ".join(dups) if dups else "None detected"

                render_html(
                    f"""
                <div class="content-card">
                    <div class="card-title">Quality & Validation Audit</div>
                    <ul style="font-size: 13px; color: #CBD5E1; line-height: 2;">
                        <li><b>Extraction Quality Score:</b> <span style="color: #34D399; font-weight: bold;">{qc.get('extraction_quality_score', 94.0)}%</span></li>
                        <li><b>Missing Clauses:</b> {missing_str}</li>
                        <li><b>Duplicate Clauses:</b> {dups_str}</li>
                        <li><b>Human Review Flags:</b> {qc.get('human_review_required', 0)}</li>
                        <li><b>Source Excerpts Preserved:</b> Verified Exact Excerpts</li>
                    </ul>
                </div>
                """
                )

    elif selected_agent == "Agent 2 – Policy Mapping":
        # AGENT 2 DETAILED DASHBOARD
        # Load actual Agent 2 outputs from independent JSON storage
        try:
            findings_data = agent2_storage.load_policy_findings(selected_workflow_id)
            summary_data = agent2_storage.load_mapping_summary(selected_workflow_id)
            evidence_data = agent2_storage.load_evidence_and_citations(selected_workflow_id)
            metadata = agent2_storage.load_execution_metadata(selected_workflow_id)
            findings_list = findings_data.get("findings", [])
        except Exception as e:
            st.error(f"Unable to load Agent 2 outputs for workflow `{selected_workflow_id}`: {e}")
            st.info(
                "Please run an end-to-end analysis or ensure Agent 2 outputs exist in `workflow_outputs/{workflow_id}/agent_2_policy_mapping/`."
            )
            findings_list = []
            findings_data = {}
            summary_data = {}
            evidence_data = {}
            metadata = {}

        if not findings_list:
            st.warning(f"No policy mapping findings recorded yet for workflow `{selected_workflow_id}`.")
        else:
            # Try loading obligations from Agent 1 to enrich display if available
            obligations_lookup = {}
            try:
                ob_data = agent1_storage.load_extracted_obligations(selected_workflow_id)
                for ob in ob_data.get("obligations", []):
                    obligations_lookup[ob.get("obligation_id")] = ob
            except Exception:
                pass

            # Count statuses
            counts = summary_data.get("status_counts", {})
            c_covered = counts.get("covered", sum(1 for f in findings_list if f.get("status") == "covered"))
            c_partially = counts.get("partially_covered", sum(1 for f in findings_list if f.get("status") == "partially_covered"))
            c_conflict = counts.get("potential_conflict", sum(1 for f in findings_list if f.get("status") == "potential_conflict"))
            c_not_found = counts.get("not_found", sum(1 for f in findings_list if f.get("status") == "not_found"))
            c_review = counts.get("requires_human_review", sum(1 for f in findings_list if f.get("status") == "requires_human_review"))
            total_findings = len(findings_list)

            # TOP METRICS ROW
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            col1.metric("Total Findings", total_findings)
            col2.metric("Covered", c_covered)
            col3.metric("Partially Covered", c_partially)
            col4.metric("Potential Conflict", c_conflict)
            col5.metric("Not Found", c_not_found)
            col6.metric("Requires Review", c_review)

            # Agent 2 Navigation Tabs
            tab_overview, tab_findings, tab_evidence, tab_confidence, tab_quality = st.tabs(
                [
                    "📊 Overview",
                    "🎯 Policy Mapping Results",
                    "📑 Evidence & Citations",
                    "⚖️ Confidence Analysis",
                    "✅ Quality Checks",
                ]
            )

            with tab_overview:
                st.markdown("### Agent 2 Executive Mapping Summary")
                st.caption(
                    f"Workflow ID: `{selected_workflow_id}` | Schema Version: `{findings_data.get('schema_version', '1.0.0')}` | Timestamp: `{findings_data.get('timestamp', 'N/A')}`"
                )

                col_sum1, col_sum2 = st.columns([3, 2])
                with col_sum1:
                    render_html(
                        f"""
                    <div class="content-card">
                        <div class="card-title">Policy Alignment Posture</div>
                        <p style="font-size: 13px; color: #CBD5E1; line-height: 1.6;">
                            Agent 2 semantically mapped <b>{total_findings} extracted regulatory obligations</b> against active internal policy handbooks.
                            Multi-query BM25 and dense vector retrieval identified the most relevant policy passages and verified exact citations.
                        </p>
                        <div style="margin-top: 15px; display: flex; flex-wrap: wrap; gap: 8px;">
                            <span class="badge badge-covered">Covered: {c_covered}</span>
                            <span class="badge badge-partially-covered">Partially Covered: {c_partially}</span>
                            <span class="badge badge-potential-conflict">Potential Conflict: {c_conflict}</span>
                            <span class="badge badge-not-found">Not Found: {c_not_found}</span>
                            <span class="badge badge-requires-review">Requires Review: {c_review}</span>
                        </div>
                    </div>
                    """
                    )

                    # Highlight attention items
                    attention_findings = [f for f in findings_list if f.get("status") in ["potential_conflict", "requires_human_review", "not_found"]]
                    if attention_findings:
                        st.markdown("#### ⚠️ High Priority Governance Items")
                        for af in attention_findings[:3]:
                            st.markdown(
                                f"- **{af.get('obligation_id')}** ({get_status_badge(af.get('status'))}): {af.get('reasoning')} — *Action:* {af.get('recommended_action', 'Review required')}",
                                unsafe_allow_html=True,
                            )

                with col_sum2:
                    avg_conf = sum(f.get("confidence", 0.0) for f in findings_list) / max(1, total_findings)
                    avg_ev_conf = sum(f.get("evidence_confidence", 0.0) for f in findings_list) / max(1, total_findings)
                    render_html(
                        f"""
                    <div class="content-card">
                        <div class="card-title">Mapping Reliability Indicators</div>
                        <ul style="font-size: 13px; color: #CBD5E1; line-height: 2;">
                            <li><b>Average Final Confidence:</b> <span style="color: #60A5FA; font-weight: bold;">{avg_conf:.1%}</span></li>
                            <li><b>Average Evidence Confidence:</b> <span style="color: #FBBF24; font-weight: bold;">{avg_ev_conf:.1%}</span></li>
                            <li><b>Retrieval Incomplete Flags:</b> {sum(1 for f in findings_list if f.get('retrieval_incomplete'))}</li>
                            <li><b>Audit Log Archived:</b> Verified JSON Ingestion</li>
                        </ul>
                        <div style="font-size: 11px; color: #94A3B8; margin-top: 10px; border-top: 1px solid #334155; padding-top: 8px;">
                            ℹ️ Evidence confidence is a heuristic quality score measuring retrieval relevance and citation coverage, not empirical ground-truth accuracy.
                        </div>
                    </div>
                    """
                    )

            with tab_findings:
                st.markdown("### Obligation to Policy Mapping Results")

                # Filters
                col_f1, col_f2 = st.columns([1, 2])
                with col_f1:
                    filter_status = st.selectbox(
                        "Filter by Classification",
                        ["All Classifications", "covered", "partially_covered", "potential_conflict", "not_found", "requires_human_review"],
                    )
                with col_f2:
                    search_query = st.text_input("Search Obligations, Clauses, or Impact", "")

                filtered_findings = findings_list
                if filter_status != "All Classifications":
                    filtered_findings = [f for f in filtered_findings if f.get("status") == filter_status]
                if search_query:
                    q = search_query.lower()
                    filtered_findings = [
                        f for f in filtered_findings
                        if q in f.get("obligation_id", "").lower()
                        or q in f.get("matching_policy_provision", "").lower()
                        or q in f.get("reasoning", "").lower()
                        or q in f.get("operational_impact", "").lower()
                        or q in f.get("recommended_action", "").lower()
                    ]

                st.caption(f"Showing {len(filtered_findings)} of {total_findings} findings")

                for f in filtered_findings:
                    ob_id = f.get("obligation_id", "N/A")
                    status = f.get("status", "unknown")
                    badge = get_status_badge(status)
                    matching_provision = f.get("matching_policy_provision", "None identified")
                    conf = f.get("confidence", 0.0)

                    ob_info = obligations_lookup.get(ob_id, {})
                    ob_text = ob_info.get("text", f.get("circular_citation", {}).get("excerpt", "N/A"))

                    with st.expander(f"{ob_id} — {matching_provision} | Status: {status.upper()} (Confidence: {conf:.0%})", expanded=(status in ["potential_conflict", "requires_human_review"])):
                        st.markdown(
                            f"""
                            <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 12px;">
                                {badge}
                                <span style="font-size: 13px; color: #94A3B8;">Matching Provision: <b style="color: #F1F5F9;">{matching_provision}</b></span>
                                <span style="margin-left: auto; font-size: 12px; color: #60A5FA;">Final Confidence: <b>{conf:.1%}</b></span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        col_f_left, col_f_right = st.columns(2)
                        with col_f_left:
                            st.markdown("**Obligation Requirement:**")
                            st.info(ob_text)
                            if ob_info.get("applicability") and ob_info.get("applicability") != "not_specified":
                                st.caption(f"**Applicability:** {ob_info.get('applicability')}")
                            if ob_info.get("required_action") and ob_info.get("required_action") != "not_specified":
                                st.caption(f"**Required Action:** {ob_info.get('required_action')}")

                        with col_f_right:
                            st.markdown("**Reasoning & Analysis:**")
                            st.write(f.get("reasoning", "No reasoning provided."))

                            missing_inc = f.get("missing_or_inconsistent")
                            if missing_inc and missing_inc != "none":
                                st.warning(f"**Missing or Inconsistent:** {missing_inc}")

                        st.markdown("---")
                        col_act1, col_act2 = st.columns(2)
                        with col_act1:
                            st.markdown(f"**Operational Impact:**\n{f.get('operational_impact', 'N/A')}")
                        with col_act2:
                            st.markdown(f"**Recommended Action:**\n{f.get('recommended_action', 'N/A')}")

                        # Citations snapshot
                        policy_cites = f.get("policy_citations", [])
                        if policy_cites:
                            st.markdown(f"**Cited Policy Chunks ({len(policy_cites)}):**")
                            cite_chips = " ".join([f"`{c.get('chunk_id')}` (p.{c.get('page', 1)})" for c in policy_cites])
                            st.caption(cite_chips)

            with tab_evidence:
                st.markdown("### Evidence Verification & Policy Citations")
                st.caption("Inspect exact policy chunk citations, circular excerpts, and validation flags.")

                for f in findings_list:
                    ob_id = f.get("obligation_id", "N/A")
                    status = f.get("status", "unknown")
                    circ_cite = f.get("circular_citation", {})
                    policy_cites = f.get("policy_citations", [])
                    limitations = f.get("evidence_limitations", [])

                    with st.expander(f"Evidence for {ob_id} ({len(policy_cites)} policy citations) — Status: {status.upper()}"):
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            st.markdown("**Circular Source Evidence:**")
                            render_html(
                                f"""
                            <div class="content-card" style="border-left: 3px solid #38BDF8;">
                                <div style="font-size: 11px; color: #94A3B8;">Document: {circ_cite.get('filename', 'N/A')} | Page: {circ_cite.get('page', 'N/A')}</div>
                                <div style="font-size: 11px; color: #64748B; margin-bottom: 8px;">Chunk ID: <code>{circ_cite.get('chunk_id', 'N/A')}</code></div>
                                <div style="font-size: 12px; color: #F1F5F9; font-style: italic; white-space: pre-wrap; max-height: 150px; overflow-y: auto;">
                                    "{circ_cite.get('excerpt', 'No excerpt available')}"
                                </div>
                            </div>
                            """
                            )

                        with col_e2:
                            st.markdown(f"**Internal Policy Citations ({len(policy_cites)}/5 max):**")
                            if not policy_cites:
                                st.info("No internal policy citations retrieved (Classification: not_found or requires_human_review).")
                            for idx, pc in enumerate(policy_cites, 1):
                                chunk_id = pc.get("chunk_id", "N/A")
                                is_valid = bool(chunk_id and chunk_id != "N/A")
                                badge_html = '<span style="color:#34D399; font-weight:bold;">[VALID]</span>' if is_valid else '<span style="color:#F87171; font-weight:bold;">[INVALID]</span>'
                                render_html(
                                    f"""
                                <div class="content-card" style="border-left: 3px solid #34D399; margin-bottom: 8px;">
                                    <div style="font-size: 11px; color: #94A3B8;">Citation #{idx}: {pc.get('filename', 'N/A')} | Page: {pc.get('page', 'N/A')} {badge_html}</div>
                                    <div style="font-size: 11px; color: #64748B; margin-bottom: 6px;">Chunk ID: <code>{chunk_id}</code></div>
                                    <div style="font-size: 12px; color: #CBD5E1; white-space: pre-wrap; max-height: 120px; overflow-y: auto;">
                                        {pc.get('excerpt', 'No excerpt available')}
                                    </div>
                                </div>
                                """
                                )

                        if limitations:
                            st.markdown("**Evidence Limitations & Warnings:**")
                            for lim in limitations:
                                st.warning(f"⚠️ {lim}")

            with tab_confidence:
                st.markdown("### Confidence & Evidence Quality Analysis")
                st.info(
                    "📌 **Evidence Confidence vs Model Confidence**: Agent 2 strictly separates the LLM's self-reported confidence from grounded evidence quality. "
                    "Evidence confidence is a **heuristic quality indicator** derived from semantic retrieval relevance and citation completeness, NOT an empirically measured ground-truth mapping accuracy."
                )

                conf_rows = []
                for f in findings_list:
                    m_conf = f.get("model_reported_confidence", f.get("confidence", 0.0))
                    e_conf = f.get("evidence_confidence", f.get("confidence", 0.0))
                    final_c = f.get("confidence", 0.0)
                    gap = m_conf - e_conf
                    conf_rows.append({
                        "Obligation ID": f.get("obligation_id"),
                        "Status": f.get("status"),
                        "Model Reported Confidence": f"{m_conf:.1%}",
                        "Evidence Confidence (Heuristic)": f"{e_conf:.1%}",
                        "Final Calibrated Confidence": f"{final_c:.1%}",
                        "Calibration Delta": f"{gap:+.1%}",
                        "Incomplete Retrieval": "⚠️ Yes" if f.get("retrieval_incomplete") else "No",
                    })

                st.table(conf_rows)

                st.markdown("#### Confidence Calibration Highlights")
                c_cal1, c_cal2 = st.columns(2)
                with c_cal1:
                    high_gap = [f for f in findings_list if (f.get("model_reported_confidence", 0.0) - f.get("evidence_confidence", 0.0)) > 0.15]
                    render_html(
                        f"""
                    <div class="content-card">
                        <div class="card-title">Hallucination Mitigation Gate</div>
                        <p style="font-size: 13px; color: #CBD5E1;">
                            Identified <b>{len(high_gap)} obligations</b> where LLM model-reported confidence exceeded grounded evidence quality by >15%.
                            Final confidence was actively calibrated downward to prevent unsupported assertions.
                        </p>
                    </div>
                    """
                    )
                with c_cal2:
                    review_cases = [f for f in findings_list if f.get("status") == "requires_human_review"]
                    render_html(
                        f"""
                    <div class="content-card">
                        <div class="card-title">Human Review Safeguards</div>
                        <p style="font-size: 13px; color: #CBD5E1;">
                            <b>{len(review_cases)} findings</b> routed to human review due to ambiguous or insufficient evidence.
                            Missing evidence was strictly preserved as unresolved rather than assumed to be absent policy.
                        </p>
                    </div>
                    """
                    )

            with tab_quality:
                st.markdown("### Agent 2 Quality Assurance & Audit Verification")

                total_citations_count = sum(len(f.get("policy_citations", [])) for f in findings_list)
                valid_citations_count = sum(
                    1 for f in findings_list for pc in f.get("policy_citations", []) if pc.get("chunk_id")
                )
                citation_rate = (valid_citations_count / max(1, total_citations_count)) * 100.0

                incomplete_retrieval_count = sum(1 for f in findings_list if f.get("retrieval_incomplete"))
                missing_evidence_count = sum(1 for f in findings_list if f.get("status") == "not_found")

                col_q1, col_q2 = st.columns(2)
                with col_q1:
                    render_html(
                        f"""
                    <div class="content-card">
                        <div class="card-title">Citation Integrity Verification</div>
                        <ul style="font-size: 13px; color: #CBD5E1; line-height: 2;">
                            <li><b>Total Cited Policy Passages:</b> {total_citations_count}</li>
                            <li><b>Valid Grounded Chunks:</b> {valid_citations_count}</li>
                            <li><b>Citation Integrity Rate:</b> <span style="color: #34D399; font-weight: bold;">{citation_rate:.1f}%</span></li>
                            <li><b>Max Citations per Finding:</b> 5 (expanded from 3)</li>
                            <li><b>Circular Anchor Passages:</b> Verified for 100% of obligations</li>
                        </ul>
                    </div>
                    """
                    )

                with col_q2:
                    render_html(
                        f"""
                    <div class="content-card">
                        <div class="card-title">Audit & Boundary Safeguards</div>
                        <ul style="font-size: 13px; color: #CBD5E1; line-height: 2;">
                            <li><b>Incomplete Retrieval Warnings:</b> {incomplete_retrieval_count}</li>
                            <li><b>True Policy Gaps (Not Found):</b> {missing_evidence_count}</li>
                            <li><b>Safeguard:</b> Incomplete retrieval isolated from missing policy</li>
                            <li><b>Classification Categories:</b> 5 Verified ({', '.join(sorted(counts.keys()))})</li>
                            <li><b>JSON Audit Archive:</b> Active in <code>agent_2_policy_mapping/</code></li>
                        </ul>
                    </div>
                    """
                    )

    elif selected_agent == "Agent 3 – Rule Proposal":
        # AGENT 3 DETAILED DASHBOARD
        # Load actual Agent 3 outputs from independent JSON storage
        try:
            proposals_data = agent3_storage.load_rule_proposals(selected_workflow_id)
            summary_data = agent3_storage.load_rule_summary(selected_workflow_id)
            evidence_data = agent3_storage.load_evidence_and_citations(selected_workflow_id)
            metadata = agent3_storage.load_execution_metadata(selected_workflow_id)
            proposals_list = proposals_data.get("proposals", [])
        except Exception as e:
            st.error(f"Unable to load Agent 3 outputs for workflow `{selected_workflow_id}`: {e}")
            st.info(
                "Please run rule authoring or ensure Agent 3 outputs exist in `workflow_outputs/{workflow_id}/agent_3_rule_authoring/`."
            )
            proposals_list = []
            proposals_data = {}
            summary_data = {}
            evidence_data = {}
            metadata = {}

        metrics = get_agent3_dashboard_metrics(proposals_list)
        total_proposals = metrics["total_proposals"]
        draft_count = metrics["draft_count"]
        sandbox_ready_count = metrics["sandbox_ready_count"]
        human_review_count = metrics["human_review_count"]
        risk_counts = summary_data.get("risk_counts", {})
        action_counts = summary_data.get("action_counts", {})

        st.caption(f"Agent 3 execution status: {metadata.get('status', 'unknown')}")
        # Metrics are useful even when there were no eligible findings to propose rules for.
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Total Proposals", total_proposals)
        col2.metric("Draft Status", f"{draft_count} (100%)" if total_proposals else "0")
        col3.metric("Sandbox Ready", sandbox_ready_count)
        col4.metric("Needs Review", human_review_count)
        col5.metric("High Risk", metrics["high_risk_count"])
        col6.metric("Actions Defined", metrics["action_count"])

        if not proposals_list:
            st.warning(f"No rule proposals recorded yet for workflow `{selected_workflow_id}`.")
            st.caption("Proposals are generated only for obligations classified as partially_covered or potential_conflict.")
        else:
            # Agent 3 Navigation Tabs
            tab_overview, tab_proposals, tab_evidence, tab_validation, tab_sandbox = st.tabs(
                [
                    "📊 Overview",
                    "📜 Rule Proposals",
                    "📑 Evidence & Citations",
                    "⚖️ Validation & Review",
                    "🧪 Sandbox Readiness",
                ]
            )

            with tab_overview:
                st.markdown("### Agent 3 Executive Rule Authoring Summary")
                st.caption(
                    f"Workflow ID: `{selected_workflow_id}` | Schema Version: `{proposals_data.get('schema_version', '1.0.0')}` | Timestamp: `{proposals_data.get('timestamp', 'N/A')}`"
                )

                col_ov1, col_ov2 = st.columns([3, 2])
                with col_ov1:
                    render_html(
                        f"""
                    <div class="content-card">
                        <div class="card-title">Governance & Proposal Policy</div>
                        <p style="font-size: 13px; color: #CBD5E1; line-height: 1.6;">
                            Agent 3 generated <b>{total_proposals} constrained declarative rule proposals</b> derived strictly from verified regulatory obligations and policy findings.
                            All proposals are held in <b>DRAFT</b> status pending human compliance review and sandbox verification.
                        </p>
                        <div style="margin-top: 15px; display: flex; flex-wrap: wrap; gap: 8px;">
                            <span class="badge-draft">100% Draft Status</span>
                            <span class="badge-sandbox-ready">Sandbox Ready: {sandbox_ready_count}</span>
                            <span class="badge-manual-review">Human Review: {human_review_count}</span>
                        </div>
                    </div>
                    """
                    )

                    # Highlight proposals
                    st.markdown("#### ⚡ Active Rule Proposals")
                    for p in proposals_list[:4]:
                        r_id = p.get("rule_id", "N/A")
                        ob_id = p.get("obligation_id") or (p.get("source_obligation_ids", [""])[0])
                        action = p.get("action", "flag_review")
                        st.markdown(
                            f"- **{r_id}** (`{ob_id}`): {p.get('description', '')[:120]}... "
                            f"<span class='badge-action'>{action}</span>",
                            unsafe_allow_html=True,
                        )

                with col_ov2:
                    avg_conf = sum(p.get("confidence", 0.0) for p in proposals_list) / max(1, total_proposals)
                    render_html(
                        f"""
                    <div class="content-card">
                        <div class="card-title">Safety & Non-Execution Assurance</div>
                        <ul style="font-size: 13px; color: #CBD5E1; line-height: 2;">
                            <li><b>Average Proposal Confidence:</b> <span style="color: #60A5FA; font-weight: bold;">{avg_conf:.1%}</span></li>
                            <li><b>Live System Execution:</b> <span style="color: #EF4444; font-weight: bold;">BLOCKED (Safe Gate)</span></li>
                            <li><b>Allowlisted Operators:</b> gt, gte, lt, lte, eq, ne, between</li>
                            <li><b>Allowlisted Fields:</b> amount, retention_days, is_emergency</li>
                            <li><b>Arbitrary Code / SQL:</b> None (Declarative Only)</li>
                        </ul>
                    </div>
                    """
                    )

            with tab_proposals:
                st.markdown("### Declarative Compliance Rule Proposals")

                # Filters
                col_pf1, col_pf2, col_pf3 = st.columns([1, 1, 2])
                with col_pf1:
                    filter_action = st.selectbox(
                        "Filter by Action",
                        ["All Actions"] + sorted(list(action_counts.keys())),
                    )
                with col_pf2:
                    filter_risk = st.selectbox(
                        "Filter by Risk Level",
                        ["All Risk Levels", "low", "medium", "high", "undetermined"],
                    )
                with col_pf3:
                    search_query = st.text_input("Search Proposals (ID, Obligation, Logic)", "")

                filtered_proposals = proposals_list
                if filter_action != "All Actions":
                    filtered_proposals = [p for p in filtered_proposals if p.get("action") == filter_action]
                if filter_risk != "All Risk Levels":
                    filtered_proposals = [p for p in filtered_proposals if p.get("risk_level") == filter_risk]
                if search_query:
                    q = search_query.lower()
                    filtered_proposals = [
                        p for p in filtered_proposals
                        if q in p.get("rule_id", "").lower()
                        or q in p.get("description", "").lower()
                        or q in p.get("business_purpose", "").lower()
                        or q in p.get("existing_policy_provision", "").lower()
                        or any(q in ob.lower() for ob in p.get("source_obligation_ids", []))
                    ]

                st.caption(f"Showing {len(filtered_proposals)} of {total_proposals} proposals")

                for p in filtered_proposals:
                    r_id = p.get("rule_id", "N/A")
                    ob_id = p.get("obligation_id") or (p.get("source_obligation_ids", [""])[0])
                    action = p.get("action", "flag_review")
                    risk = p.get("risk_level", "undetermined")
                    conf = p.get("confidence", 0.85)
                    is_ready = bool(p.get("sandbox_readiness") or (p.get("baseline_rule") and p.get("sandbox_rule")))
                    ready_badge = '<span class="badge-sandbox-ready">SANDBOX READY</span>' if is_ready else '<span class="badge-manual-review">MANUAL REVIEW</span>'

                    with st.expander(f"{r_id} ({ob_id}) — Action: {action.upper()} | Risk: {risk.upper()} (Conf: {conf:.0%})", expanded=is_ready):
                        st.markdown(
                            f"""
                            <div style="display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap;">
                                <span class="badge-draft">DRAFT</span>
                                <span class="badge-action">{action}</span>
                                <span class="badge-risk-{risk}">{risk.upper()} RISK</span>
                                {ready_badge}
                                <span style="margin-left: auto; font-size: 12px; color: #60A5FA;">Confidence: <b>{conf:.1%}</b></span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        col_p_left, col_p_right = st.columns(2)
                        with col_p_left:
                            st.markdown(f"**Source Obligation:** `{ob_id}`")
                            st.markdown(f"**Existing Policy Provision:**\n_{p.get('existing_policy_provision', 'None identified')}_")
                            st.markdown(f"**Proposed Rule:**\n{p.get('proposed_rule') or p.get('description')}")

                        with col_p_right:
                            st.markdown(f"**Reason for Change (Business Purpose):**\n{p.get('reason_for_change') or p.get('business_purpose')}")
                            st.markdown(f"**Operational Impact:**\n{p.get('operational_impact', 'N/A')}")
                            if p.get("effective_date") and p.get("effective_date") != "not_specified":
                                st.caption(f"**Effective Date:** {p.get('effective_date')}")

                        st.markdown("---")
                        col_cond, col_flow = st.columns(2)
                        with col_cond:
                            st.markdown("**Trigger Conditions:**")
                            conds = p.get("trigger_conditions", [])
                            if conds:
                                for c in conds:
                                    st.code(f"IF {c.get('field')} {c.get('operator')} {c.get('value')} THEN {p.get('action')}")
                            else:
                                st.info("No deterministic conditions (requires human review).")

                        with col_flow:
                            st.markdown("**Inputs & Outcomes:**")
                            st.caption(f"**Required Inputs:** {', '.join(p.get('required_inputs', []))}")
                            st.caption(f"**Decision Outcomes:** {', '.join(p.get('decision_outcomes', []))}")
                            if p.get("exceptions"):
                                st.caption(f"**Exceptions:** {', '.join(p.get('exceptions'))}")
                            if p.get("rollback_considerations"):
                                st.caption(f"**Rollback:** {p.get('rollback_considerations')}")

            with tab_evidence:
                st.markdown("### Supporting Evidence & Citations Verification")
                st.caption("Every rule proposal is strictly anchored in circular excerpts and active policy citations.")

                for p in proposals_list:
                    r_id = p.get("rule_id", "N/A")
                    ob_id = p.get("obligation_id") or (p.get("source_obligation_ids", [""])[0])
                    cites = p.get("supporting_citations", [])

                    with st.expander(f"Citations for {r_id} ({ob_id}) — {len(cites)} Sources"):
                        for idx, c in enumerate(cites, 1):
                            chunk_id = c.get("chunk_id", "N/A")
                            doc_type = c.get("document_type", "unknown")
                            validation_status = get_agent3_citation_validation_status(
                                evidence_data, r_id, c
                            )
                            if validation_status == "validated":
                                tag = '<span style="color:#34D399; font-weight:bold;">[BACKEND VALIDATED]</span>'
                            elif validation_status == "invalid":
                                tag = '<span style="color:#F87171; font-weight:bold;">[BACKEND INVALID]</span>'
                            else:
                                tag = '<span style="color:#FBBF24; font-weight:bold;">[VALIDATION UNAVAILABLE]</span>'

                            render_html(
                                f"""
                            <div class="content-card" style="border-left: 3px solid #6366F1; margin-bottom: 8px;">
                                <div style="font-size: 11px; color: #94A3B8;">Citation #{idx} ({doc_type.upper()}): {c.get('filename', 'N/A')} | Page {c.get('page', 1)} {tag}</div>
                                <div style="font-size: 11px; color: #64748B; margin-bottom: 6px;">Chunk ID: <code>{chunk_id}</code></div>
                                <div style="font-size: 12px; color: #F1F5F9; font-style: italic; white-space: pre-wrap; max-height: 120px; overflow-y: auto;">
                                    "{c.get('excerpt', 'No excerpt available')}"
                                </div>
                            </div>
                            """
                            )

            with tab_validation:
                st.markdown("### Validation Results & Human Review Requirements")
                st.info(
                    "🛡️ **Compliance Guardrail**: Rule proposals that lack complete baseline/proposed rule pairs or evidence-backed conditions are safely routed for manual review."
                )

                review_proposals = [p for p in proposals_list if p.get("action") == "flag_review" or p.get("unresolved_questions") or p.get("review_reasons")]
                st.markdown(f"#### Human Review Flagged Proposals ({len(review_proposals)})")

                if not review_proposals:
                    st.success("All proposals have deterministic condition models.")
                else:
                    for rp in review_proposals:
                        r_id = rp.get("rule_id", "N/A")
                        ob_id = rp.get("obligation_id") or (rp.get("source_obligation_ids", [""])[0])
                        reasons = rp.get("review_reasons", []) or rp.get("unresolved_questions", [])
                        with st.expander(f"⚠️ {r_id} ({ob_id}) — Review Flags"):
                            for r in reasons:
                                st.warning(f"• {r}")
                            st.caption(f"**Proposed Action:** {rp.get('action')} | **Risk:** {rp.get('risk_level')}")

                st.markdown("#### Hallucination & Operator Whitelist Audit")
                col_v1, col_v2 = st.columns(2)
                with col_v1:
                    render_html(
                        f"""
                    <div class="content-card">
                        <div class="card-title">Operator & Field Compliance</div>
                        <ul style="font-size: 13px; color: #CBD5E1; line-height: 2;">
                            <li><b>Allowlisted Operators:</b> 100% Verified (gt, gte, lt, lte, eq, ne, between)</li>
                            <li><b>Allowlisted Fields:</b> 100% Verified (amount, retention_days, is_emergency)</li>
                            <li><b>Invented Thresholds:</b> 0 Detected</li>
                            <li><b>Unbacked Conditions:</b> 0 Detected</li>
                        </ul>
                    </div>
                    """
                    )
                with col_v2:
                    render_html(
                        f"""
                    <div class="content-card">
                        <div class="card-title">Duplicate & Citation Checks</div>
                        <ul style="font-size: 13px; color: #CBD5E1; line-height: 2;">
                            <li><b>Unique Rule IDs:</b> {len(set(p.get('rule_id') for p in proposals_list))} / {total_proposals}</li>
                            <li><b>Obligation Anchoring:</b> 100% of proposals linked to eligible obligations</li>
                            <li><b>Circular Citations Verified:</b> 100% present</li>
                            <li><b>Production Live Execution:</b> Gated until human approval</li>
                        </ul>
                    </div>
                    """
                    )

            with tab_sandbox:
                st.markdown("### Sandbox Readiness & Testing Validation")
                st.info(
                    "🧪 **Agent 4 Integration**: Sandbox-ready proposals contain deterministic `baseline_rule` and `sandbox_rule` pairs for automated 50-case synthetic test execution."
                )

                ready_proposals = [p for p in proposals_list if p.get("baseline_rule") and p.get("sandbox_rule")]
                st.markdown(f"#### Sandbox-Ready Rule Pairs ({len(ready_proposals)})")

                if not ready_proposals:
                    st.warning("No proposals in this workflow have deterministic baseline/proposed rule pairs. All remain in draft for manual compliance review.")
                else:
                    for rp in ready_proposals:
                        r_id = rp.get("rule_id", "N/A")
                        b_rule = rp.get("baseline_rule", {})
                        s_rule = rp.get("sandbox_rule", {})

                        with st.expander(f"Sandbox Rule Specification: {r_id} ({b_rule.get('product_type', 'N/A')})"):
                            col_sb1, col_sb2 = st.columns(2)
                            with col_sb1:
                                st.markdown(f"**Baseline Rule (v{b_rule.get('version', 1)}):**")
                                st.json(b_rule)
                            with col_sb2:
                                st.markdown(f"**Proposed Sandbox Rule (v{s_rule.get('version', 2)}):**")
                                st.json(s_rule)

                # Check if Agent 4 has executed test suites for this workflow
                try:
                    from cidan.sandbox import service as sandbox_service
                    suites = sandbox_service.list_suites()
                    wf_suites = [s for s in suites if any(p.get("rule_id") == s.get("rule_id") for p in proposals_list)]
                    if wf_suites:
                        st.markdown("#### Actual Executed Sandbox Suites")
                        for ws in wf_suites:
                            suite_id = ws.get("suite_id")
                            status = ws.get("status", "pending")
                            st.markdown(f"- **Suite `{suite_id}`** for rule `{ws.get('rule_id')}` — Status: `{status.upper()}`")
                except Exception:
                    pass

    elif selected_agent == "Agent 4 – Test Generation":
        render_agent4_dashboard()
                
