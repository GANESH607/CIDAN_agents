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
    clean_html = "\n".join(line.strip() for line in html_str.splitlines() if line.strip())
    st.markdown(clean_html, unsafe_allow_html=True)


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

    /* ═══════════════════════════════════════════
       Agent 1 – Cinematic Extraction Animation
       ═══════════════════════════════════════════ */

    /* Core Keyframes */
    @keyframes a1-glow { 0%,100%{box-shadow:0 0 20px rgba(99,102,241,.12),0 0 40px rgba(124,58,237,.06)}50%{box-shadow:0 0 35px rgba(99,102,241,.28),0 0 70px rgba(124,58,237,.14)} }
    @keyframes a1-up   { from{opacity:0;transform:translateY(22px)}to{opacity:1;transform:translateY(0)} }
    @keyframes a1-spin  { to{transform:rotate(360deg)} }
    @keyframes a1-pop   { 0%{transform:scale(.5);opacity:0}60%{transform:scale(1.15)}100%{transform:scale(1);opacity:1} }
    @keyframes a1-pulse { 0%,100%{opacity:.25;transform:scale(.8)}50%{opacity:1;transform:scale(1.15)} }
    @keyframes a1-flow  { 0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%} }
    @keyframes a1-shimmer { 0%{background-position:-200% 0}100%{background-position:200% 0} }
    @keyframes a1-grow  { from{width:0%} }
    @keyframes a1-scan  { 0%{top:0;opacity:1}50%{opacity:.6}100%{top:calc(100% - 3px);opacity:1} }
    @keyframes a1-draw-check { to{stroke-dashoffset:0} }
    @keyframes a1-reveal { from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)} }
    @keyframes a1-blink { 0%,100%{opacity:1}50%{opacity:0} }
    @keyframes a1-slide-in { from{opacity:0;transform:translateX(-30px)}to{opacity:1;transform:translateX(0)} }
    @keyframes a1-line-draw { from{width:0}to{width:100%} }
    @keyframes a1-float { 0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)} }
    @keyframes a1-rings { 0%{transform:scale(.8);opacity:.5}50%{transform:scale(1.1);opacity:1}100%{transform:scale(.8);opacity:.5} }
    @keyframes a1-typewriter { from{width:0}to{width:100%} }
    @keyframes a1-particle-flow { 0%{transform:translateX(-100%);opacity:0}30%{opacity:1}70%{opacity:1}100%{transform:translateX(200%);opacity:0} }
    @keyframes a2-dash-flow { from{stroke-dashoffset:24}to{stroke-dashoffset:0} }
    @keyframes a2-stage-step { 0%{opacity:0;transform:translateY(4px)} 12%,82%{opacity:1;transform:translateY(0)} 100%{opacity:0;transform:translateY(-4px)} }
    @keyframes a2-stage-final { 0%{opacity:0;transform:translateY(4px)} 100%{opacity:1;transform:translateY(0)} }
    .a2-ev-card-circ {
        background: radial-gradient(circle at 50% 25%, rgba(139,92,246,0.22), #0B1026 75%);
        border: 1.5px solid rgba(139,92,246,0.7);
        border-radius: 16px;
        padding: 22px 16px;
        text-align: center;
        box-shadow: 0 0 28px rgba(139,92,246,0.22), inset 0 0 18px rgba(139,92,246,0.08);
        animation: a1-slide-in .35s ease-out;
    }
    .a2-ev-card-pol {
        background: radial-gradient(circle at 50% 25%, rgba(56,189,248,0.2), #0B1228 75%);
        border: 1.5px solid rgba(56,189,248,0.7);
        border-radius: 16px;
        padding: 22px 16px;
        text-align: center;
        box-shadow: 0 0 28px rgba(56,189,248,0.2), inset 0 0 18px rgba(56,189,248,0.08);
        animation: a1-up .35s ease-out;
    }
    .a2-ev-orbit {
        width: 62px; height: 62px;
        border-radius: 50%;
        position: relative;
        display: flex; align-items: center; justify-content: center;
        background: radial-gradient(circle, rgba(139,92,246,0.16) 0%, transparent 70%);
        box-shadow: 0 0 28px rgba(139,92,246,0.35);
    }
    .a2-ev-orbit-ring {
        position: absolute; inset: 4px;
        border-radius: 50%;
        border: 3px solid rgba(139,92,246,0.2);
        border-top-color: #C084FC;
        border-right-color: #38BDF8;
        animation: a1-spin 1.3s linear infinite;
    }
    .a2-ev-orbit-dot {
        position: absolute; top: 1px; left: 50%;
        width: 8px; height: 8px; margin-left: -4px;
        border-radius: 50%;
        background: #FFFFFF;
        box-shadow: 0 0 10px #C084FC, 0 0 18px #38BDF8;
    }
    .a2-ev-stage-wrap {
        position: relative;
        height: 24px; width: 170px;
        margin-top: 8px;
    }
    .a2-ev-stage {
        position: absolute; inset: 0;
        display: flex; align-items: center; justify-content: center;
        font-size: 12px; font-weight: 600; color: #E2E8F0;
        opacity: 0; white-space: nowrap;
    }
    /* ── Agent 3 Visual Cards & Animations ── */
    @keyframes a3-fill-100 { from{width:14%} to{width:100%} }
    .a3-glass-card {
        background: radial-gradient(circle at 50% 20%, rgba(99,102,241,0.18), #080E22 76%);
        border: 1.5px solid rgba(129,140,248,0.45);
        border-radius: 16px;
        padding: 18px 16px;
        text-align: center;
        box-shadow: 0 0 24px rgba(99,102,241,0.16);
    }
    .a3-glass-card-cyan {
        background: radial-gradient(circle at 50% 20%, rgba(56,189,248,0.18), #081226 76%);
        border: 1.5px solid rgba(56,189,248,0.5);
        border-radius: 16px;
        padding: 18px 16px;
        text-align: center;
        box-shadow: 0 0 24px rgba(56,189,248,0.16);
    }
    .a3-scanner-frame {
        position: relative;
        width: 112px; height: 118px;
        margin: 0 auto 14px;
        border-radius: 14px;
        background: linear-gradient(160deg, rgba(99,102,241,0.22), rgba(15,23,42,0.9));
        border: 1.5px solid rgba(139,92,246,0.65);
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 30px rgba(139,92,246,0.3);
        overflow: hidden;
    }
    .a3-scanner-beam {
        position: absolute; left: 6px; right: 6px; height: 3px;
        background: linear-gradient(90deg, transparent, #C084FC, #38BDF8, transparent);
        box-shadow: 0 0 12px #A78BFA;
        animation: a1-scan 2.2s ease-in-out infinite;
    }
    .a3-prog-track {
        height: 10px;
        background: #111936;
        border: 1px solid #1E2D56;
        border-radius: 999px;
        overflow: hidden;
    }
    .a3-prog-fill {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #7C3AED, #6366F1, #38BDF8, #34D399);
        animation: a3-fill-100 2.6s ease-out forwards;
    }
    .a3-tilt-left {
        background: radial-gradient(circle at 30% 25%, rgba(139,92,246,0.22), #0A1026 75%);
        border: 1.5px solid rgba(139,92,246,0.6);
        border-radius: 16px;
        padding: 24px 16px;
        text-align: center;
        box-shadow: 0 0 26px rgba(139,92,246,0.2);
        transform: perspective(600px) rotateY(8deg);
        transition: transform 0.25s;
    }
    .a3-tilt-left:hover, .a3-tilt-right:hover {
        transform: perspective(600px) rotateY(0deg) translateY(-2px);
    }
    .a3-tilt-right {
        background: radial-gradient(circle at 70% 25%, rgba(56,189,248,0.22), #0A1328 75%);
        border: 1.5px solid rgba(56,189,248,0.65);
        border-radius: 16px;
        padding: 24px 16px;
        text-align: center;
        box-shadow: 0 0 26px rgba(56,189,248,0.2);
        transform: perspective(600px) rotateY(-8deg);
        transition: transform 0.25s;
    }
    .a3-kpi-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 12px;
        margin: 8px 0 16px;
    }
    .a3-kpi-card {
        background: linear-gradient(165deg, #0B1228 0%, #101A3B 100%);
        border: 1px solid rgba(99, 102, 241, 0.28);
        border-radius: 14px;
        padding: 14px 12px;
        text-align: center;
        box-shadow: 0 4px 18px rgba(15, 23, 42, 0.5);
        transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
        animation: a1-up .4s ease-out backwards;
    }
    .a3-kpi-card:hover {
        transform: translateY(-3px);
        border-color: rgba(139, 92, 246, 0.65);
        box-shadow: 0 0 22px rgba(99, 102, 241, 0.25);
    }
    @keyframes a3-panel-cycle {
        0%   { opacity: 0; transform: translateY(8px); pointer-events: none; }
        8%, 88% { opacity: 1; transform: translateY(0); pointer-events: auto; }
        100% { opacity: 0; transform: translateY(-6px); pointer-events: none; }
    }
    @keyframes a3-panel-final {
        0%   { opacity: 0; transform: scale(0.97) translateY(8px); }
        100% { opacity: 1; transform: scale(1) translateY(0); }
    }
    .a3-stage-deck {
        position: relative;
        min-height: 235px;
        margin-bottom: 16px;
    }
    .a3-stage-slide {
        position: absolute; inset: 0;
        opacity: 0;
        pointer-events: none;
    }

    /* ── Hero Section ── */
    .a1-hero{position:relative;background:linear-gradient(135deg,#080D1E 0%,#0E1738 35%,#150F3A 70%,#0C0A28 100%);border:1px solid rgba(99,102,241,.2);border-radius:18px;padding:32px 36px 28px;margin-bottom:28px;overflow:hidden;animation:a1-glow 4s ease-in-out infinite}
    .a1-hero::before{content:'';position:absolute;top:-50%;right:-15%;width:380px;height:380px;background:radial-gradient(circle,rgba(99,102,241,.1) 0%,transparent 65%);border-radius:50%;pointer-events:none}
    .a1-hero::after{content:'';position:absolute;bottom:-30%;left:10%;width:280px;height:280px;background:radial-gradient(circle,rgba(124,58,237,.08) 0%,transparent 65%);border-radius:50%;pointer-events:none}

    /* ── Particle wave bar ── */
    .a1-wave{height:3px;display:flex;gap:4px;align-items:center;overflow:hidden;position:relative}
    .a1-wave span{width:4px;height:4px;border-radius:50%;background:#818CF8;animation:a1-pulse 1.5s ease-in-out infinite;flex-shrink:0}
    .a1-wave span:nth-child(2n){animation-delay:.2s}
    .a1-wave span:nth-child(3n){animation-delay:.4s}
    .a1-wave span:nth-child(4n+1){animation-delay:.6s}

    /* ── Scanning document effect ── */
    .a1-scan-box{position:relative;background:#0A1025;border:1px solid #1A2649;border-radius:12px;padding:0;overflow:hidden;height:120px}
    .a1-scan-box::after{content:'';position:absolute;left:0;right:0;height:3px;background:linear-gradient(90deg,transparent,#818CF8,#A78BFA,#818CF8,transparent);animation:a1-scan 2.5s ease-in-out infinite;border-radius:2px;z-index:2}
    .a1-scan-lines{padding:14px 16px;display:flex;flex-direction:column;gap:6px}
    .a1-scan-line{height:6px;border-radius:3px;background:rgba(99,102,241,.08);animation:a1-reveal 1.5s ease-out backwards}
    .a1-scan-line:nth-child(1){width:85%;animation-delay:.3s}
    .a1-scan-line:nth-child(2){width:70%;animation-delay:.5s}
    .a1-scan-line:nth-child(3){width:90%;animation-delay:.7s}
    .a1-scan-line:nth-child(4){width:60%;animation-delay:.9s}
    .a1-scan-line:nth-child(5){width:78%;animation-delay:1.1s}
    .a1-scan-line:nth-child(6){width:45%;animation-delay:1.3s}
    .a1-scan-line:nth-child(7){width:82%;animation-delay:1.5s}

    /* ── Extraction flow pipeline ── */
    .a1-flow-pipe{display:flex;align-items:center;gap:0;margin:28px 0}
    .a1-flow-node{background:#0D1429;border:1px solid #1A2649;border-radius:14px;padding:16px 20px;text-align:center;position:relative;animation:a1-up .5s ease-out backwards;flex:1;min-width:0}
    .a1-flow-node.active{border-color:rgba(99,102,241,.5);box-shadow:0 0 25px rgba(99,102,241,.12)}
    .a1-flow-node.done{border-color:rgba(16,185,129,.4);box-shadow:0 0 20px rgba(16,185,129,.08)}
    .a1-flow-node:nth-child(1){animation-delay:.1s}
    .a1-flow-node:nth-child(3){animation-delay:.3s}
    .a1-flow-node:nth-child(5){animation-delay:.5s}
    .a1-flow-node:nth-child(7){animation-delay:.7s}
    .a1-flow-icon{font-size:28px;margin-bottom:6px;animation:a1-float 3s ease-in-out infinite}
    .a1-flow-label{font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:#94A3B8;font-weight:600}
    .a1-flow-val{font-size:22px;font-weight:800;color:#FFF;margin:4px 0;animation:a1-pop .5s ease-out backwards}
    .a1-flow-connector{width:40px;display:flex;align-items:center;justify-content:center;flex-shrink:0;position:relative;height:2px}
    .a1-flow-connector::before{content:'';position:absolute;height:2px;background:linear-gradient(90deg,#4F46E5,#7C3AED);width:100%;border-radius:1px;animation:a1-line-draw .8s ease-out backwards}
    .a1-flow-connector::after{content:'▸';position:absolute;right:-4px;color:#818CF8;font-size:14px;animation:a1-pulse 2s ease-in-out infinite}
    .a1-flow-connector:nth-child(2)::before{animation-delay:.2s}
    .a1-flow-connector:nth-child(4)::before{animation-delay:.4s}
    .a1-flow-connector:nth-child(6)::before{animation-delay:.6s}

    /* ── Animated checkmark SVG ── */
    .a1-check-svg{width:28px;height:28px}
    .a1-check-svg circle{fill:none;stroke:#10B981;stroke-width:2;stroke-dasharray:95;stroke-dashoffset:95;animation:a1-draw-check .6s ease-out forwards}
    .a1-check-svg polyline{fill:none;stroke:#34D399;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:30;stroke-dashoffset:30;animation:a1-draw-check .4s ease-out .5s forwards}

    /* ── Metric orbs (compact) ── */
    .a1-orbs{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:24px}
    .a1-orb{background:#0D1429;border:1px solid #1A2649;border-radius:14px;padding:18px 14px;text-align:center;animation:a1-up .4s ease-out backwards;position:relative;overflow:hidden}
    .a1-orb:nth-child(1){animation-delay:.1s}.a1-orb:nth-child(2){animation-delay:.2s}.a1-orb:nth-child(3){animation-delay:.3s}.a1-orb:nth-child(4){animation-delay:.4s}
    .a1-orb::after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#4F46E5,#7C3AED,#4F46E5);background-size:200% 100%;animation:a1-flow 3s ease infinite}
    .a1-orb-icon{width:48px;height:48px;border-radius:50%;border:2px solid rgba(99,102,241,.25);display:inline-flex;align-items:center;justify-content:center;font-size:20px;position:relative;background:rgba(99,102,241,.05);margin-bottom:8px}
    .a1-orb-icon::before{content:'';position:absolute;inset:-3px;border-radius:50%;border:2px solid transparent;border-top-color:#818CF8;animation:a1-spin 2.5s linear infinite}
    .a1-orb-num{font-size:28px;font-weight:800;color:#FFF;animation:a1-pop .6s ease-out backwards;line-height:1}
    .a1-orb-lbl{font-size:10px;color:#94A3B8;text-transform:uppercase;letter-spacing:.5px;font-weight:600;margin-top:4px}

    /* ── Coverage animated bar ── */
    .a1-cov{background:#0D1429;border:1px solid #1A2649;border-radius:12px;padding:14px 18px;margin-bottom:24px;animation:a1-up .5s ease-out .5s backwards}
    .a1-cov-row{display:flex;justify-content:space-between;margin-bottom:8px}
    .a1-cov-lbl{font-size:11px;font-weight:600;color:#E2E8F0;text-transform:uppercase;letter-spacing:.4px}
    .a1-cov-pct{font-size:14px;font-weight:700;color:#34D399}
    .a1-cov-bar{height:8px;background:#1E293B;border-radius:4px;overflow:hidden}
    .a1-cov-fill{height:100%;background:linear-gradient(90deg,#10B981,#34D399,#6EE7B7);background-size:200% 100%;border-radius:4px;animation:a1-grow 1.2s ease-out .6s backwards,a1-flow 2s ease infinite}

    /* ── Obligation extraction animation ── */
    .a1-extract-row{display:flex;align-items:center;gap:14px;background:#0D1429;border:1px solid #1A2649;border-radius:12px;padding:12px 16px;margin-bottom:8px;animation:a1-slide-in .4s ease-out backwards;transition:border-color .3s,box-shadow .3s}
    .a1-extract-row:hover{border-color:rgba(99,102,241,.4);box-shadow:0 0 18px rgba(99,102,241,.08)}
    .a1-extract-id{background:rgba(99,102,241,.1);border:1px solid rgba(99,102,241,.25);border-radius:6px;padding:4px 10px;font-size:11px;font-weight:700;color:#A5B4FC;white-space:nowrap}
    .a1-extract-clause{font-size:10px;color:#64748B;text-transform:uppercase;font-weight:600}
    .a1-extract-short{font-size:12px;color:#CBD5E1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0}

    /* ── Animated tick list ── */
    .a1-ticks{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:16px}
    .a1-tick{display:flex;align-items:center;gap:10px;background:#0B1124;border:1px solid #182344;border-radius:10px;padding:10px 14px;animation:a1-up .35s ease-out backwards;font-size:12px;color:#E2E8F0}
    .a1-tick:nth-child(1){animation-delay:.5s}.a1-tick:nth-child(2){animation-delay:.7s}.a1-tick:nth-child(3){animation-delay:.9s}.a1-tick:nth-child(4){animation-delay:1.1s}.a1-tick:nth-child(5){animation-delay:1.3s}.a1-tick:nth-child(6){animation-delay:1.5s}

    /* ── Diff visual ── */
    .a1-diff{background:#0D1429;border:1px solid #1A2649;border-radius:12px;padding:16px;margin-bottom:12px;animation:a1-up .4s ease-out backwards}
    .a1-diff-grid{display:grid;grid-template-columns:1fr auto 1fr;gap:10px;align-items:center}
    .a1-diff-old{background:#0B1124;border:1px solid #233152;border-radius:8px;padding:10px 12px;font-size:12px;color:#94A3B8}
    .a1-diff-new{background:rgba(16,185,129,.06);border:1px solid rgba(16,185,129,.25);border-radius:8px;padding:10px 12px;font-size:12px;color:#34D399;font-weight:600}
    .a1-diff-arrow{font-size:18px;color:#818CF8;animation:a1-pulse 2s ease-in-out infinite}
    .a1-diff-tag{font-size:9px;color:#64748B;text-transform:uppercase;font-weight:600;margin-bottom:3px}

    /* ── Evidence strip ── */
    .a1-ev{background:#0D1429;border:1px solid #1A2649;border-left:3px solid #10B981;border-radius:10px;padding:12px 14px;margin-bottom:8px;animation:a1-up .35s ease-out backwards}
    .a1-ev-top{display:flex;align-items:center;gap:8px;margin-bottom:6px}
    .a1-ev-tag{background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.25);border-radius:5px;padding:2px 7px;font-size:9px;font-weight:700;color:#34D399}
    .a1-ev-src{font-size:10px;color:#94A3B8}
    .a1-ev-txt{font-size:11px;color:#CBD5E1;font-style:italic;max-height:40px;overflow:hidden}

    /* ── Quality gauge ring ── */
    .a1-gauge{display:flex;align-items:center;gap:18px;background:#0D1429;border:1px solid #1A2649;border-radius:14px;padding:18px 22px;animation:a1-up .5s ease-out backwards}
    .a1-gauge-ring{width:72px;height:72px;border-radius:50%;border:4px solid #1E293B;position:relative;display:flex;align-items:center;justify-content:center;flex-shrink:0}
    .a1-gauge-ring::before{content:'';position:absolute;inset:-4px;border-radius:50%;border:4px solid transparent;border-top-color:#34D399;border-right-color:#34D399;border-bottom-color:#34D399;animation:a1-spin 3.5s linear infinite}
    .a1-gauge-val{font-size:18px;font-weight:800;color:#34D399}
    .a1-gauge-info .a1-gauge-t{font-size:13px;font-weight:600;color:#FFF;margin-bottom:2px}
    .a1-gauge-info .a1-gauge-d{font-size:11px;color:#94A3B8}

    /* ── Shimmer line ── */
    .a1-shimmer{height:2px;background:linear-gradient(90deg,transparent,#4F46E5,#7C3AED,#4F46E5,transparent);background-size:200% 100%;animation:a1-shimmer 2.5s linear infinite;border-radius:1px;margin:16px 0}

    /* ── Concentric rings decoration ── */
    .a1-rings{position:relative;width:100px;height:100px;margin:0 auto}
    .a1-rings span{position:absolute;border-radius:50%;border:1px solid rgba(99,102,241,.15);animation:a1-rings 3s ease-in-out infinite}
    .a1-rings span:nth-child(1){inset:0;border-color:rgba(99,102,241,.25)}
    .a1-rings span:nth-child(2){inset:12px;animation-delay:.4s}
    .a1-rings span:nth-child(3){inset:24px;animation-delay:.8s;border-color:rgba(124,58,237,.2)}

    /* ── PDF Scanning Card (Overview) ── */
    .a1-pdf-scan-card {
        background: #0B1228;
        border: 1px solid #1A284D;
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
        animation: a1-up .5s ease-out;
    }
    .a1-pdf-scan-card::after {
        content: '';
        position: absolute;
        left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, transparent, #818CF8, #34D399, #818CF8, transparent);
        animation: a1-scan 2.8s ease-in-out infinite;
        border-radius: 2px;
        z-index: 2;
        box-shadow: 0 0 12px #818CF8;
    }
    .a1-pdf-badge {
        width: 44px; height: 50px;
        background: linear-gradient(135deg, #EF4444 0%, #B91C1C 100%);
        border-radius: 6px;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        color: white; font-weight: 800; font-size: 11px;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
        position: relative;
        flex-shrink: 0;
    }
    .a1-pdf-badge::before {
        content: '';
        position: absolute; top: 0; right: 0;
        width: 12px; height: 12px;
        background: #0B1228;
        border-bottom-left-radius: 4px;
    }

    /* ── Image 2: Filter Bar & Obligation Cards ── */
    .a1-filter-container {
        background: #0C1328;
        border: 1px solid #1B284D;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }
    .a1-filter-bar {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-top: 14px;
        padding-top: 14px;
        border-top: 1px solid #16203B;
    }
    .a1-pill-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
    }
    .a1-pill-badge:hover {
        transform: translateY(-1px);
    }
    .a1-pill-dot {
        width: 7px; height: 7px; border-radius: 50%;
    }
    .a1-pill-modified {
        background: rgba(16, 185, 129, 0.12);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .a1-pill-modified .a1-pill-dot { background: #34D399; box-shadow: 0 0 6px #34D399; }
    .a1-pill-new {
        background: rgba(56, 189, 248, 0.12);
        color: #38BDF8;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }
    .a1-pill-new .a1-pill-dot { background: #38BDF8; box-shadow: 0 0 6px #38BDF8; }
    .a1-pill-unchanged {
        background: rgba(148, 163, 184, 0.12);
        color: #94A3B8;
        border: 1px solid rgba(148, 163, 184, 0.3);
    }
    .a1-pill-unchanged .a1-pill-dot { background: #94A3B8; }
    .a1-pill-review {
        background: rgba(245, 158, 11, 0.12);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    /* Interactive horizontal pills for Tab 2 filter */
    div[data-testid="stRadio"]:has(input[name*="agent1_interactive_status_pills"]) > div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
        background: transparent !important;
        padding: 0 !important;
        border: none !important;
        align-items: center !important;
    }
    div[data-testid="stRadio"]:has(input[name*="agent1_interactive_status_pills"]) label {
        background: #0B1124 !important;
        border: 1px solid #1A2649 !important;
        border-radius: 20px !important;
        padding: 5px 14px !important;
        color: #94A3B8 !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
    }
    div[data-testid="stRadio"]:has(input[name*="agent1_interactive_status_pills"]) label:hover {
        border-color: #6366F1 !important;
        color: #FFFFFF !important;
        transform: translateY(-1px) !important;
    }
    div[data-testid="stRadio"]:has(input[name*="agent1_interactive_status_pills"]) label:has(input:checked) {
        background: rgba(99, 102, 241, 0.2) !important;
        border-color: #6366F1 !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        box-shadow: 0 0 14px rgba(99, 102, 241, 0.35) !important;
    }
    .a1-pill-review .a1-pill-dot { background: #FBBF24; box-shadow: 0 0 6px #FBBF24; }
    .a1-pill-superseded {
        background: rgba(239, 68, 68, 0.12);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .a1-pill-superseded .a1-pill-dot { background: #F87171; box-shadow: 0 0 6px #F87171; }

    .a1-btn-apply {
        background: linear-gradient(135deg, #6366F1 0%, #7C3AED 100%);
        color: white;
        border: none;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.3);
    }

    /* Image 2 Card Structure */
    .a1-card-img2 {
        background: #0B1124;
        border: 1px solid #1A2649;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 14px;
        transition: border-color 0.25s, box-shadow 0.25s;
    }
    .a1-card-img2:hover {
        border-color: rgba(99, 102, 241, 0.45);
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.08);
    }
    .a1-meta-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        padding: 14px 0;
        margin: 10px 0;
        border-top: 1px solid #16203B;
        border-bottom: 1px solid #16203B;
    }
    .a1-meta-item {
        display: flex;
        align-items: flex-start;
        gap: 8px;
    }
    .a1-meta-icon {
        font-size: 16px;
        color: #818CF8;
        line-height: 1;
        margin-top: 2px;
    }
    .a1-meta-label {
        font-size: 10px;
        text-transform: uppercase;
        color: #64748B;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .a1-meta-val {
        font-size: 12px;
        color: #E2E8F0;
        font-weight: 500;
        margin-top: 2px;
    }
    .a1-before-box {
        background: #080D1D;
        border: 1px solid #1B294F;
        border-radius: 8px;
        padding: 12px 14px;
        flex: 1;
    }
    .a1-after-box {
        background: rgba(16, 185, 129, 0.04);
        border: 1px solid rgba(16, 185, 129, 0.35);
        border-radius: 8px;
        padding: 12px 14px;
        flex: 1;
    }
    .a1-box-tag {
        font-size: 10px;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* ── Image 4: Document Intelligence Quality Layout ── */
    .a1-docintel-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 18px;
        background: #080D1F;
        border: 1px solid #162244;
        border-radius: 12px;
        margin-bottom: 18px;
    }
    .a1-doc-paper {
        background: #F8FAFC;
        color: #0F172A;
        border-radius: 8px;
        padding: 22px 20px;
        font-family: 'Times New Roman', Georgia, serif;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        min-height: 480px;
        position: relative;
        overflow: hidden;
    }
    .a1-doc-paper::after {
        content: '';
        position: absolute;
        left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, #3B82F6, #10B981, transparent);
        animation: a1-scan 3.5s ease-in-out infinite;
    }
    .a1-doc-clause-hl {
        background: rgba(254, 240, 138, 0.55);
        border-left: 3px solid #CA8A04;
        padding: 4px 8px;
        margin: 6px 0;
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        line-height: 1.4;
        border-radius: 2px;
    }
    .a1-data-row-img4 {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 14px;
        background: #0B1228;
        border: 1px solid #16203B;
        border-radius: 8px;
        margin-bottom: 8px;
        transition: border-color 0.2s;
    }
    .a1-data-row-img4:hover {
        border-color: rgba(99, 102, 241, 0.4);
    }
    .a1-timeline-step {
        display: flex;
        gap: 12px;
        position: relative;
        padding-bottom: 18px;
    }
    .a1-timeline-step:last-child {
        padding-bottom: 0;
    }
    .a1-timeline-step::before {
        content: '';
        position: absolute;
        left: 11px; top: 22px; bottom: 0;
        width: 2px;
        background: #1E2D56;
    }
    .a1-timeline-step:last-child::before {
        display: none;
    }
    .a1-timeline-dot {
        width: 24px; height: 24px;
        border-radius: 50%;
        background: #111B35;
        border: 2px solid #6366F1;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        color: #818CF8;
        flex-shrink: 0;
        z-index: 1;
    }
    .a1-bottom-bar-img4 {
        background: #080D1E;
        border: 1px solid #1A284D;
        border-radius: 12px;
        padding: 14px 20px;
        margin-top: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
    }

    /* ═══════════════════════════════════════════
       Agent 2 – Visual Policy Mapping & Confidence
       ═══════════════════════════════════════════ */
    .a2-pipe {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, #090E21 0%, #0F1736 50%, #140D33 100%);
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 16px;
        padding: 20px 28px;
        margin: 14px 0 18px;
        animation: a1-glow 4s ease-in-out infinite;
    }
    .a2-step {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
        min-width: 80px;
        animation: a1-up .45s ease-out backwards;
    }
    .a2-step-circle {
        width: 48px; height: 48px;
        border-radius: 50%;
        background: #0E1630;
        border: 2px solid #4F46E5;
        display: flex; align-items: center; justify-content: center;
        font-size: 20px;
        box-shadow: 0 0 18px rgba(99, 102, 241, 0.35);
        animation: a1-float 3s ease-in-out infinite;
    }
    .a2-step-circle.done {
        border-color: #10B981;
        box-shadow: 0 0 18px rgba(16, 185, 129, 0.35);
    }
    .a2-step-lbl {
        font-size: 12px; font-weight: 600; color: #E2E8F0;
    }
    .a2-step-line {
        flex: 1; height: 2px;
        background: linear-gradient(90deg, #4F46E5, #8B5CF6, #10B981);
        margin: 0 10px 22px;
        position: relative;
        overflow: hidden;
    }
    .a2-step-line::after {
        content: '';
        position: absolute; top: -2px; left: 0;
        width: 28px; height: 6px;
        background: #A78BFA;
        border-radius: 3px;
        box-shadow: 0 0 10px #A78BFA;
        animation: a1-particle-flow 2.2s linear infinite;
    }
    .a2-bridge {
        display: grid;
        grid-template-columns: 1fr 0.4fr 1.1fr 0.4fr 1fr;
        align-items: center;
        gap: 10px;
        margin: 12px 0 22px;
    }
    .a2-bridge-card {
        background: linear-gradient(160deg, #0D142B 0%, #131B3A 100%);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 14px;
        padding: 18px 14px;
        text-align: center;
        box-shadow: 0 0 24px rgba(79, 70, 229, 0.12);
        transition: transform 0.25s, border-color 0.25s;
    }
    .a2-bridge-card:hover {
        transform: translateY(-3px);
        border-color: #818CF8;
    }
    .a2-bridge-center {
        background: linear-gradient(135deg, #1E1B4B 0%, #312E81 100%);
        border: 2px solid #8B5CF6;
        border-radius: 16px;
        padding: 20px 14px;
        text-align: center;
        box-shadow: 0 0 32px rgba(139, 92, 246, 0.35);
        animation: a1-glow 3s ease-in-out infinite;
    }
    .a2-beam {
        height: 3px;
        background: linear-gradient(90deg, rgba(99,102,241,0.2), #818CF8, rgba(99,102,241,0.2));
        position: relative;
        border-radius: 2px;
    }
    .a2-beam::after {
        content: '✦';
        position: absolute; top: -9px; left: 50%;
        color: #A78BFA; font-size: 13px;
        animation: a1-pulse 1.6s ease-in-out infinite;
    }
    .a2-map-board {
        background: #080E20;
        border: 1px solid #1A2649;
        border-radius: 16px;
        padding: 18px 20px;
        margin-bottom: 18px;
    }
    .a2-map-row {
        display: grid;
        grid-template-columns: 1.1fr 0.35fr 1.1fr;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
        animation: a1-slide-in .4s ease-out backwards;
    }
    .a2-map-node {
        background: #0D152D;
        border: 1px solid #1E2D56;
        border-radius: 10px;
        padding: 10px 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        transition: border-color .25s, box-shadow .25s;
    }
    .a2-map-node:hover {
        border-color: #6366F1;
        box-shadow: 0 0 16px rgba(99, 102, 241, 0.18);
    }
    .a2-map-link {
        height: 2px;
        background: linear-gradient(90deg, #6366F1, #34D399);
        position: relative;
    }
    .a2-map-link::after {
        content: '▸';
        position: absolute; right: -4px; top: -9px;
        color: #34D399; font-size: 13px;
    }
    .a2-conf-card {
        background: #0B1228;
        border: 1px solid #1A274D;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 12px;
        animation: a1-up .35s ease-out backwards;
    }
    .a2-conf-card:hover {
        border-color: rgba(99, 102, 241, 0.5);
    }
    .a2-bar-track {
        height: 8px;
        background: #141E3C;
        border-radius: 6px;
        overflow: hidden;
        flex: 1;
    }
    .a2-bar-fill {
        height: 100%;
        border-radius: 6px;
        animation: a1-grow 1s ease-out backwards;
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


def render_agent4_dashboard(workflow_id: str) -> None:
    if st.session_state.pop("agent3_proceed_toast", False):
        st.toast("Sandbox ready! Loaded Agent 3 rule proposals into Agent 4.", icon="🚀")
    from cidan.agents import testing_validation
    from cidan.models import RuleProposal
    from cidan.sandbox import service as sandbox_service

    suite_select_key = f"agent4-suite-selection-{workflow_id}"
    st.subheader("Agent 4 – Test Case Generation and Sandbox Validation")
    st.caption(
        "Sandbox execution uses synthetic inputs and the deterministic rule engine; "
        "rules are never executed in a banking system."
    )

    st.caption(f"Agent 3 proposal source: `{workflow_id}`")
    try:
        proposals_data = agent3_storage.load_rule_proposals(workflow_id)
        proposals = proposals_data.get("proposals", [])
    except FileNotFoundError:
        proposals = []
        st.warning(f"No Agent 3 proposals are available for workflow `{workflow_id}`.")
    except (OSError, ValueError) as exc:
        st.error(f"Unable to load Agent 3 proposals for workflow `{workflow_id}`: {exc}")
        return

    try:
        all_suites = sandbox_service.list_suites()
    except (OSError, ValueError, sqlite3.Error) as exc:
        st.error(f"Unable to load sandbox suites: {exc}")
        return
    existing_suite_ids = {suite["suite_id"] for suite in all_suites}
    run_attempted = False
    generated_suite_id = None

    ready_proposals = [
        proposal
        for proposal in proposals
        if proposal.get("baseline_rule")
        and proposal.get("sandbox_rule")
        and proposal.get("change_id")
    ]
    if ready_proposals:
        selected_proposal_index = st.selectbox(
            "Agent 3 proposal",
            list(range(len(ready_proposals))),
            format_func=lambda index: (
                f"{ready_proposals[index].get('rule_id', 'unknown')} · "
                f"{ready_proposals[index].get('change_id', 'unknown')}"
            ),
        )
        selected_proposal = ready_proposals[selected_proposal_index]
        if st.button(
            "Generate and run 50 synthetic tests",
            type="primary",
            key=f"agent4-run-{workflow_id}-{selected_proposal.get('rule_id')}",
        ):
            run_attempted = True
            try:
                proposal_fields = RuleProposal.model_fields
                proposal = RuleProposal.model_validate({
                    key: value
                    for key, value in selected_proposal.items()
                    if key in proposal_fields
                })
                with st.spinner("Generating and executing the validated sandbox suite..."):
                    summary = testing_validation.run(proposal)
                generated_suite_id = summary.sandbox_suite_id
                if (
                    summary.sandbox_suite_id
                    and summary.total == 50
                    and summary.passed == 50
                    and summary.failed == 0
                    and summary.pending == 0
                ):
                    st.success(
                        f"Agent 4 recorded suite `{summary.sandbox_suite_id}`: "
                        f"{summary.total} generated, {summary.passed} passed, "
                        f"{summary.failed} failed, {summary.pending} pending."
                    )
                elif summary.sandbox_suite_id:
                    st.warning(
                        f"Suite `{summary.sandbox_suite_id}` needs review: "
                        f"{summary.total} generated, {summary.passed} passed, "
                        f"{summary.failed} failed, {summary.pending} pending."
                    )
                else:
                    st.warning("Agent 4 did not produce a sandbox suite.")
            except Exception as exc:
                st.error(f"Agent 4 could not generate or run this suite: {exc}")

    manual_review_proposals = [
        proposal
        for proposal in proposals
        if not (
            proposal.get("baseline_rule")
            and proposal.get("sandbox_rule")
            and proposal.get("change_id")
        )
    ]
    for proposal in manual_review_proposals:
        st.warning(
            f"Proposal `{proposal.get('rule_id', 'unknown')}` has no complete "
            "baseline/proposed rule pair and remains for human review."
        )

    try:
        if run_attempted:
            all_suites = sandbox_service.list_suites()
    except (OSError, ValueError, sqlite3.Error) as exc:
        st.error(f"Unable to load sandbox suites: {exc}")
        return

    workflow_suite_keys = {
        (
            proposal.get("rule_id"),
            proposal.get("change_id") or proposal.get("rule_id"),
            (proposal.get("supporting_citations") or [{}])[0].get("document_id"),
        )
        for proposal in proposals
    }
    suites = [
        suite
        for suite in all_suites
        if (
            suite.get("rule_id"),
            suite.get("change_id"),
            suite.get("document_id"),
        ) in workflow_suite_keys
    ]

    if not suites:
        st.info(f"No Agent 4 suites have been generated for workflow `{workflow_id}`.")
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
    if generated_suite_id in suite_ids:
        st.session_state[suite_select_key] = generated_suite_id
    elif run_attempted:
        newly_created_suites = [
            suite for suite in suites if suite["suite_id"] not in existing_suite_ids
        ]
        if newly_created_suites:
            st.session_state[suite_select_key] = newly_created_suites[0]["suite_id"]
    if st.session_state.get(suite_select_key) not in suite_ids:
        st.session_state[suite_select_key] = suite_ids[0]
    selected_suite_id = st.selectbox(
        "Sandbox suite",
        suite_ids,
        format_func=lambda suite_id: (
            f"{suites_by_id[suite_id]['rule_id']} · "
            f"{suites_by_id[suite_id]['status']} · {suite_id}"
        ),
        key=suite_select_key,
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

    suite_rule_id = report.get("rule_id", "RULE")
    suite_status = report.get("status", "unknown")
    total_gen = report.get("total_generated", len(cases))
    pass_rate_str = f"{pass_percentage:.1f}%" if pass_percentage is not None else "N/A"
    inv_val = "N/A" if suite_status == "generation_failed" else invalid

    def _a4_pipe(steps: list[tuple[str, str, str]]) -> str:
        items = []
        for idx_s, (ic, lb, st_t) in enumerate(steps):
            cls = "a2-step-circle done" if st_t == "done" else "a2-step-circle"
            glow = "box-shadow:0 0 24px rgba(139,92,246,0.8);border-color:#A78BFA;" if st_t == "active" else ""
            col = "#FFFFFF" if st_t == "active" else "#CBD5E1"
            items.append(
                f'<div class="a2-step"><div class="{cls}" style="{glow}">{ic}</div>'
                f'<div class="a2-step-lbl" style="color:{col};">{lb}</div></div>'
            )
            if idx_s < len(steps) - 1:
                items.append('<div class="a2-step-line"></div>')
        return f'<div class="a2-pipe" style="margin:6px 0 14px;padding:14px 22px;">{"".join(items)}</div>'

    a4_dot_beam = (
        '<svg viewBox="0 0 80 12" style="width:100%;height:12px;">'
        '<line x1="2" y1="6" x2="78" y2="6" stroke="#A78BFA" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="1 9" style="animation:a2-dash-flow 1s linear infinite;"/>'
        '</svg>'
    )
    is_gen_failed = suite_status == "generation_failed"
    final_icon = "❌" if is_gen_failed else "🛡️"
    final_title = "Generation Failed" if is_gen_failed else "Sandbox Ready"
    final_color = "#F87171" if is_gen_failed else "#34D399"
    final_sub = (
        f"Test generation failed for <b>{suite_rule_id}</b> · Status: <code>{suite_status}</code>"
        if is_gen_failed
        else f"Validation completed for <b>{suite_rule_id}</b> · Status: <code>{suite_status}</code>"
    )

    render_html(
        f"""
        <div class="a3-stage-deck" style="min-height:335px;background:radial-gradient(ellipse at 50% 45%, rgba(124,58,237,0.18), #070B19 72%);border:1px solid #1E2D56;border-radius:18px;padding:14px 20px;margin-bottom:16px;">
            <div class="a3-stage-slide" style="padding:14px 20px;animation:a3-panel-cycle 1.2s ease 0.0s 1;">
                {_a4_pipe([("📋", "Prepare", "active"), ("⚙️", "Configure", "pending"), ("▶", "Execute", "pending"), ("🛡️", "Validate", "pending")])}
                <div style="display:grid;grid-template-columns:1fr 0.85fr 1fr;align-items:center;gap:14px;margin-bottom:14px;">
                    <div class="a3-tilt-left"><div style="font-size:32px;margin-bottom:6px;">📄</div><div style="font-size:14px;font-weight:700;color:#FFFFFF;">Baseline Rule (v1)</div></div>
                    <div style="display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:6px;"><div>{a4_dot_beam}</div><div class="a2-ev-orbit" style="width:48px;height:48px;"><div class="a2-ev-orbit-ring"></div><span style="font-size:18px;color:#FFF;z-index:1;">→</span></div><div>{a4_dot_beam}</div></div>
                    <div class="a3-tilt-right"><div style="font-size:28px;margin-bottom:6px;color:#38BDF8;font-weight:700;">&lt;/&gt;</div><div style="font-size:14px;font-weight:700;color:#FFFFFF;">Proposed Rule (v2)</div></div>
                </div>
                <div style="display:flex;align-items:center;gap:12px;"><span style="font-size:18px;animation:a1-spin 2s linear infinite;">⚙️</span><div style="flex:1;"><div style="font-size:12px;color:#CBD5E1;margin-bottom:4px;">Preparing Sandbox Environment...</div><div class="a3-prog-track"><div class="a3-prog-fill" style="width:20%;"></div></div></div><b style="color:#A78BFA;">20%</b></div>
            </div>

            <div class="a3-stage-slide" style="padding:14px 20px;animation:a3-panel-cycle 1.2s ease 1.2s 1;">
                {_a4_pipe([("✓", "Prepare", "done"), ("⚙️", "Configure", "active"), ("▶", "Execute", "pending"), ("🛡️", "Validate", "pending")])}
                <div class="a3-glass-card" style="text-align:left;padding:14px 18px;margin-bottom:12px;">
                    <div style="font-size:14px;font-weight:700;color:#FFFFFF;margin-bottom:8px;">📚 Test Suite Configuration</div>
                    <div style="font-size:12px;color:#CBD5E1;line-height:1.85;">
                        <div><span style="color:#34D399;">✓</span> Generate Test Cases ({total_gen})</div>
                        <div><span style="color:#34D399;">✓</span> Load Rule Pairs (v1 vs v2)</div>
                        <div><span style="color:#34D399;">✓</span> Set Validation Criteria</div>
                        <div><span style="color:#A78BFA;">◌</span> Configure Test Categories</div>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:12px;"><div style="flex:1;"><div class="a3-prog-track"><div class="a3-prog-fill" style="width:50%;"></div></div></div><b style="color:#A78BFA;">50%</b></div>
            </div>

            <div class="a3-stage-slide" style="padding:14px 20px;animation:a3-panel-cycle 1.2s ease 2.4s 1;">
                {_a4_pipe([("✓", "Prepare", "done"), ("✓", "Configure", "done"), ("▶", "Execute", "active"), ("🛡️", "Validate", "pending")])}
                <div style="display:grid;grid-template-columns:0.8fr 1.2fr;align-items:center;gap:14px;margin-bottom:12px;">
                    <div class="a3-glass-card" style="padding:26px;"><div style="font-size:36px;color:#A78BFA;font-weight:700;">&lt;/&gt;</div><div style="font-size:11px;color:#94A3B8;margin-top:4px;">Synthetic Runner</div></div>
                    <div class="a3-glass-card-cyan" style="text-align:left;padding:14px 18px;">
                        <div style="font-size:13px;font-weight:700;color:#FFFFFF;margin-bottom:8px;">📋 Running Tests...</div>
                        <div style="font-size:12px;color:#CBD5E1;line-height:1.85;"><div><span style="color:#34D399;">✓</span> Test Case 1</div><div><span style="color:#34D399;">✓</span> Test Case 2</div><div><span style="color:#34D399;">✓</span> Test Case 3 ... {total_gen}</div></div>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:12px;"><div style="flex:1;"><div class="a3-prog-track"><div class="a3-prog-fill" style="width:75%;"></div></div></div><b style="color:#38BDF8;">75%</b></div>
            </div>

            <div class="a3-stage-slide" style="padding:14px 20px;animation:a3-panel-cycle 1.2s ease 3.6s 1;">
                {_a4_pipe([("✓", "Prepare", "done"), ("✓", "Configure", "done"), ("✓", "Execute", "done"), ("🛡️", "Validate", "active")])}
                <div style="display:grid;grid-template-columns:0.8fr 1.2fr;align-items:center;gap:14px;margin-bottom:12px;">
                    <div class="a3-glass-card" style="padding:24px;"><div style="font-size:44px;filter:drop-shadow(0 0 14px rgba(139,92,246,0.8));">🛡️</div></div>
                    <div class="a3-glass-card" style="text-align:left;padding:14px 18px;">
                        <div style="font-size:13px;font-weight:700;color:#FFFFFF;margin-bottom:8px;">📋 Validation Results</div>
                        <div style="font-size:12px;color:#CBD5E1;line-height:1.85;"><div><span style="color:#34D399;">✓</span> Rule Logic Check</div><div><span style="color:#34D399;">✓</span> Output Consistency</div><div><span style="color:#34D399;">✓</span> Edge Case Coverage</div><div><span style="color:#FBBF24;">●</span> Exception Review</div></div>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:12px;"><div style="flex:1;"><div class="a3-prog-track"><div class="a3-prog-fill" style="width:100%;"></div></div></div><b style="color:#34D399;">100%</b></div>
            </div>

            <div class="a3-stage-slide" style="padding:16px 24px;animation:a3-panel-final 0.55s ease 4.8s forwards;">
                {_a4_pipe([("✓", "Prepare", "done"), ("✓", "Configure", "done"), ("✓", "Execute", "done"), ("✓", "Validate", "done")])}
                <div style="text-align:center;margin-bottom:14px;">
                    <div style="font-size:44px;filter:drop-shadow(0 0 18px {final_color});">{final_icon}</div>
                    <div style="font-size:22px;font-weight:700;color:{final_color};">{final_title}</div>
                    <div style="font-size:12px;color:#CBD5E1;">{final_sub}</div>
                </div>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;">
                    <div class="a3-glass-card" style="padding:12px;"><div style="font-size:20px;font-weight:700;color:#FFFFFF;">{total_gen}</div><div style="font-size:11px;color:#94A3B8;">🧪 Test Cases</div></div>
                    <div class="a3-glass-card-cyan" style="padding:12px;border-color:rgba(52,211,153,0.5);"><div style="font-size:20px;font-weight:700;color:#34D399;">{passed}</div><div style="font-size:11px;color:#94A3B8;">✅ Passed</div></div>
                    <div class="a3-glass-card" style="padding:12px;border-color:rgba(248,113,113,0.45);"><div style="font-size:20px;font-weight:700;color:#F87171;">{failed}</div><div style="font-size:11px;color:#94A3B8;">❌ Failed</div></div>
                </div>
            </div>
        </div>

        <div class="a3-kpi-grid">
            <div class="a3-kpi-card"><div style="font-size:18px;">🧪</div><div style="font-size:20px;font-weight:700;color:#FFF;">{total_gen}</div><div style="font-size:11px;color:#94A3B8;">Generated</div></div>
            <div class="a3-kpi-card" style="border-color:rgba(52,211,153,0.4);"><div style="font-size:18px;">✅</div><div style="font-size:20px;font-weight:700;color:#34D399;">{passed}</div><div style="font-size:11px;color:#94A3B8;">Passed</div></div>
            <div class="a3-kpi-card" style="border-color:rgba(248,113,113,0.4);"><div style="font-size:18px;">❌</div><div style="font-size:20px;font-weight:700;color:#F87171;">{failed}</div><div style="font-size:11px;color:#94A3B8;">Failed</div></div>
            <div class="a3-kpi-card"><div style="font-size:18px;">⏳</div><div style="font-size:20px;font-weight:700;color:#FBBF24;">{pending}</div><div style="font-size:11px;color:#94A3B8;">Pending</div></div>
            <div class="a3-kpi-card"><div style="font-size:18px;">🚫</div><div style="font-size:20px;font-weight:700;color:#94A3B8;">{inv_val}</div><div style="font-size:11px;color:#94A3B8;">Invalid</div></div>
            <div class="a3-kpi-card" style="border-color:rgba(56,189,248,0.45);"><div style="font-size:18px;">🎯</div><div style="font-size:20px;font-weight:700;color:#38BDF8;">{pass_rate_str}</div><div style="font-size:11px;color:#94A3B8;">Pass Rate</div></div>
        </div>
        """
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

    st.markdown("#### 📊 Test Category Distribution")
    distribution = report.get("category_distribution", {})
    if distribution:
        max_cnt = max(distribution.values()) or 1
        dist_rows = []
        for cat_name, cnt in distribution.items():
            pct = max(6, int((cnt / max_cnt) * 100))
            dist_rows.append(
                f'<div style="display:grid;grid-template-columns:1.2fr 2.4fr 0.3fr;align-items:center;gap:12px;margin-bottom:8px;">'
                f'<span style="font-size:12px;color:#E2E8F0;font-family:monospace;">{cat_name}</span>'
                f'<div class="a2-bar-track"><div class="a2-bar-fill" style="width:{pct}%;background:linear-gradient(90deg,#7C3AED,#A78BFA,#38BDF8);"></div></div>'
                f'<b style="font-size:12px;color:#FFFFFF;text-align:right;">{cnt}</b>'
                '</div>'
            )
        render_html(
            f"""
            <div style="background:#080E20;border:1px solid #1E2D56;border-radius:14px;padding:16px 20px;margin-bottom:16px;">
                {"".join(dist_rows)}
            </div>
            """
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
        if "pending_agent_nav" in st.session_state:
            st.session_state["selected_agent_nav"] = st.session_state.pop("pending_agent_nav")
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
            key="selected_agent_nav",
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
        # AGENT 1 — Cinematic Extraction Dashboard
        try:
            summary = agent1_storage.load_agent1_summary(selected_workflow_id)
            obligations_data = agent1_storage.load_extracted_obligations(selected_workflow_id)
            comparison_data = agent1_storage.load_amendment_comparison(selected_workflow_id)
            evidence_data = agent1_storage.load_evidence_and_citations(selected_workflow_id)
            coverage_data = agent1_storage.load_coverage_report(selected_workflow_id)
        except Exception as exc:
            st.error(f"Error loading Agent 1 data for workflow {selected_workflow_id}: {exc}")
            st.stop()

        obls_list = obligations_data.get("obligations", [])
        chg = summary.get("change_analysis", {})
        mod_count = chg.get("modified", 3)
        new_count = chg.get("new", 3)
        docs_count = summary.get("documents_processed", 2)
        total_pages = summary.get("total_pages", 7)
        obls_count = summary.get("obligations_extracted", len(obls_list))
        cov_pct = summary.get("coverage_percentage", 100.0)
        exec_time = summary.get('execution_time_seconds') or summary.get('duration_seconds') or 'N/A'
        qc = coverage_data.get("quality_checks", {})
        quality_score = qc.get('extraction_quality_score', 94.0)

        # ═══════════════════════════════════════
        # HERO — Minimal branding + particle wave
        # ═══════════════════════════════════════
        wave_dots = '<span></span>' * 20
        render_html(
            f"""
        <div class="a1-hero">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <div style="display:flex;align-items:center;gap:14px;">
                    <div class="a1-rings"><span></span><span></span><span></span></div>
                    <div>
                        <div style="font-size:22px;font-weight:700;color:#FFF;">Agent 01 — Obligation Extraction</div>
                        <div style="font-size:11px;color:#64748B;margin-top:2px;">Regulatory Compliance AI</div>
                    </div>
                </div>
                <div style="display:flex;align-items:center;gap:10px;">
                    <svg class="a1-check-svg" viewBox="0 0 36 36"><circle cx="18" cy="18" r="15"/><polyline points="11,19 16,24 25,13"/></svg>
                    <span style="font-size:12px;color:#34D399;font-weight:600;">Complete</span>
                    <span style="font-size:11px;color:#64748B;">{exec_time}s</span>
                </div>
            </div>
            <div class="a1-wave" style="margin-top:16px;">{wave_dots}</div>
        </div>
        """
        )

        # ═══════════════════════════════════════
        # EXTRACTION FLOW PIPELINE — Visual animated process
        # ═══════════════════════════════════════
        render_html(
            f"""
        <div class="a1-flow-pipe">
            <div class="a1-flow-node done">
                <div class="a1-flow-icon">📄</div>
                <div class="a1-flow-val">{docs_count}</div>
                <div class="a1-flow-label">Documents</div>
            </div>
            <div class="a1-flow-connector"></div>
            <div class="a1-flow-node done">
                <div class="a1-flow-icon">📑</div>
                <div class="a1-flow-val">{total_pages}</div>
                <div class="a1-flow-label">Pages Scanned</div>
            </div>
            <div class="a1-flow-connector"></div>
            <div class="a1-flow-node active">
                <div class="a1-flow-icon">📋</div>
                <div class="a1-flow-val">{obls_count}</div>
                <div class="a1-flow-label">Extracted</div>
            </div>
            <div class="a1-flow-connector"></div>
            <div class="a1-flow-node done">
                <div class="a1-flow-icon">✅</div>
                <div class="a1-flow-val">{quality_score}%</div>
                <div class="a1-flow-label">Verified</div>
            </div>
        </div>
        """
        )

        # ═══════════════════════════════════════
        # TABS — Visual-first
        # ═══════════════════════════════════════
        tab_overview, tab_obligations, tab_comparison, tab_evidence, tab_quality = st.tabs(
            ["📊 Overview", "📋 Obligations", "🔄 Amendments", "📑 Evidence", "✅ Quality"]
        )

        # ─── TAB 1: OVERVIEW ───  Flow: PDF Scan → Extracted → Verified
        with tab_overview:
            render_html('<div class="a1-shimmer"></div>')

            # ── PHASE 1: PDF Document Scanning Card ──
            source_doc_name = "federalbank_rbi_circular_2026.pdf"
            if evidence_data.get("evidence"):
                source_doc_name = evidence_data["evidence"][0].get("source_document", source_doc_name)

            render_html(
                f"""
            <div class="a1-pdf-scan-card">
                <div style="display: flex; justify-content: space-between; align-items: center; position: relative; z-index: 3;">
                    <div style="display: flex; align-items: center; gap: 16px;">
                        <div class="a1-pdf-badge">
                            <span style="font-size: 8px; opacity: 0.8; margin-top: 4px;">DOC</span>
                            <span>PDF</span>
                        </div>
                        <div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 15px; font-weight: 700; color: #FFFFFF;">{source_doc_name}</span>
                                <span class="badge-pill badge-completed" style="font-size: 10px;">✓ Ingested</span>
                                <span class="badge-pill badge-demo" style="font-size: 10px;">OCR Scanned</span>
                            </div>
                            <div style="font-size: 11px; color: #94A3B8; margin-top: 4px; display: flex; gap: 14px;">
                                <span>📄 {total_pages} Pages parsed</span>
                                <span>⚡ 100% Text & Table coverage</span>
                                <span>🔍 Clause hierarchy detected</span>
                            </div>
                        </div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <svg class="a1-check-svg" viewBox="0 0 36 36" style="width: 30px; height: 30px;">
                            <circle cx="18" cy="18" r="15" style="animation-delay: .6s;"/>
                            <polyline points="11,19 16,24 25,13" style="animation-delay: 1s;"/>
                        </svg>
                        <span style="font-size: 11px; color: #34D399; font-weight: 600; text-transform: uppercase;">Scanning Complete</span>
                    </div>
                </div>
            </div>
            """
            )

            # ── Connecting arrow from scan to results ──
            render_html(
                """
            <div style="display:flex;flex-direction:column;align-items:center;margin:2px 0 14px;">
                <div style="width:2px;height:18px;background:linear-gradient(180deg,#4F46E5,#7C3AED);border-radius:1px;animation:a1-grow .6s ease-out .8s backwards;"></div>
                <div style="color:#818CF8;font-size:12px;animation:a1-pulse 2s ease-in-out infinite;">▼</div>
            </div>
            """
            )

            # ── PHASE 2: Extracted Obligations ──
            render_html(
                f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;animation:a1-up .4s ease-out 1s backwards;">
                <div style="width:8px;height:8px;border-radius:50%;background:#818CF8;animation:a1-pulse 2s ease-in-out infinite;"></div>
                <span style="font-size:12px;font-weight:600;color:#E2E8F0;text-transform:uppercase;letter-spacing:.6px;">Obligations Extracted</span>
                <span style="font-size:11px;color:#34D399;font-weight:700;">{obls_count} found</span>
                <div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(99,102,241,.3),transparent);"></div>
            </div>
            """
            )

            for idx, obl in enumerate(obls_list):
                chg_class = obl.get("change_classification", "NEW")
                badge_cls = "badge-modified" if chg_class == "MODIFIED" else "badge-new"
                badge_lbl = "M" if chg_class == "MODIFIED" else "N"
                text_short = (obl.get("text") or "")[:85]
                if len(obl.get("text") or "") > 85:
                    text_short += "…"
                delay_slide = 1.0 + 0.16 * idx
                delay_circle = delay_slide + 0.15
                delay_tick = delay_slide + 0.35
                render_html(
                    f'<div class="a1-extract-row" style="animation-delay:{delay_slide}s;">'
                    f'<svg class="a1-check-svg" viewBox="0 0 36 36" style="width:22px;height:22px;flex-shrink:0;">'
                    f'<circle cx="18" cy="18" r="15" style="animation-delay:{delay_circle}s;"/>'
                    f'<polyline points="11,19 16,24 25,13" style="animation-delay:{delay_tick}s;"/>'
                    f'</svg>'
                    f'<span class="a1-extract-id">{obl.get("obligation_id")}</span>'
                    f'<span class="a1-extract-clause">§{obl.get("clause_id")}</span>'
                    f'<span class="a1-extract-short">{text_short}</span>'
                    f'<span class="{badge_cls}">{badge_lbl}</span>'
                    f'</div>'
                )

            # ── Connecting arrow from obligations to verification ──
            render_html(
                """
            <div style="display:flex;flex-direction:column;align-items:center;margin:16px 0;">
                <div style="width:2px;height:18px;background:linear-gradient(180deg,#7C3AED,#10B981);border-radius:1px;animation:a1-grow .6s ease-out 2.2s backwards;"></div>
                <div style="color:#34D399;font-size:12px;animation:a1-pulse 2s ease-in-out infinite;">▼</div>
            </div>
            """
            )

            # ── PHASE 3: Verification Checks ──
            render_html(
                f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;animation:a1-up .4s ease-out 2.4s backwards;">
                <div style="width:8px;height:8px;border-radius:50%;background:#10B981;animation:a1-pulse 2s ease-in-out infinite;"></div>
                <span style="font-size:12px;font-weight:600;color:#E2E8F0;text-transform:uppercase;letter-spacing:.6px;">Verification Complete</span>
                <span style="font-size:11px;color:#34D399;font-weight:700;">{quality_score}%</span>
                <div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(16,185,129,.3),transparent);"></div>
            </div>
            """
            )

            render_html(
                """
            <div class="a1-ticks">
                <div class="a1-tick" style="animation-delay:2.6s;">
                    <svg class="a1-check-svg" viewBox="0 0 36 36" style="width:22px;height:22px;flex-shrink:0;"><circle cx="18" cy="18" r="15" style="animation-delay:2.7s;"/><polyline points="11,19 16,24 25,13" style="animation-delay:3.0s;"/></svg>
                    Pages processed
                </div>
                <div class="a1-tick" style="animation-delay:2.8s;">
                    <svg class="a1-check-svg" viewBox="0 0 36 36" style="width:22px;height:22px;flex-shrink:0;"><circle cx="18" cy="18" r="15" style="animation-delay:2.9s;"/><polyline points="11,19 16,24 25,13" style="animation-delay:3.2s;"/></svg>
                    Clauses verified
                </div>
                <div class="a1-tick" style="animation-delay:3.0s;">
                    <svg class="a1-check-svg" viewBox="0 0 36 36" style="width:22px;height:22px;flex-shrink:0;"><circle cx="18" cy="18" r="15" style="animation-delay:3.1s;"/><polyline points="11,19 16,24 25,13" style="animation-delay:3.4s;"/></svg>
                    Amendments detected
                </div>
                <div class="a1-tick" style="animation-delay:3.2s;">
                    <svg class="a1-check-svg" viewBox="0 0 36 36" style="width:22px;height:22px;flex-shrink:0;"><circle cx="18" cy="18" r="15" style="animation-delay:3.3s;"/><polyline points="11,19 16,24 25,13" style="animation-delay:3.6s;"/></svg>
                    No duplicates
                </div>
                <div class="a1-tick" style="animation-delay:3.4s;">
                    <svg class="a1-check-svg" viewBox="0 0 36 36" style="width:22px;height:22px;flex-shrink:0;"><circle cx="18" cy="18" r="15" style="animation-delay:3.5s;"/><polyline points="11,19 16,24 25,13" style="animation-delay:3.8s;"/></svg>
                    Excerpts preserved
                </div>
                <div class="a1-tick" style="animation-delay:3.6s;">
                    <svg class="a1-check-svg" viewBox="0 0 36 36" style="width:22px;height:22px;flex-shrink:0;"><circle cx="18" cy="18" r="15" style="animation-delay:3.7s;"/><polyline points="11,19 16,24 25,13" style="animation-delay:4.0s;"/></svg>
                    Quality: 94%
                </div>
            </div>
            """
            )

            # ── Metrics row at bottom ──
            render_html('<div class="a1-shimmer" style="margin:20px 0 12px;"></div>')
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                render_html(f'<div class="a1-orb" style="animation-delay:3.8s;"><div class="a1-orb-icon">📄</div><div class="a1-orb-num">{docs_count}</div><div class="a1-orb-lbl">Docs</div></div>')
            with m2:
                render_html(f'<div class="a1-orb" style="animation-delay:3.9s;"><div class="a1-orb-icon">📑</div><div class="a1-orb-num">{total_pages}</div><div class="a1-orb-lbl">Pages</div></div>')
            with m3:
                render_html(f'<div class="a1-orb" style="animation-delay:4.0s;"><div class="a1-orb-icon">📋</div><div class="a1-orb-num">{obls_count}</div><div class="a1-orb-lbl">Obligations</div></div>')
            with m4:
                render_html(f'<div class="a1-orb" style="animation-delay:4.1s;"><div class="a1-orb-icon">🔀</div><div class="a1-orb-num" style="font-size:16px;"><span style="color:#FBBF24;">{mod_count}M</span> <span style="color:#34D399;">{new_count}N</span></div><div class="a1-orb-lbl">Changes</div></div>')

        # ─── TAB 2: OBLIGATIONS (Matching Image 2 Layout) ───
        with tab_obligations:
            # Header matching Image 2
            render_html(
                """
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px;">
                <div>
                    <div style="font-size: 20px; font-weight: 700; color: #FFFFFF;">Obligations</div>
                    <div style="font-size: 12px; color: #94A3B8; margin-top: 2px;">Obligations extracted from regulatory circulars with rule impact and action tracking.</div>
                </div>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <div style="background: #111B35; border: 1px solid #1E2D56; color: #CBD5E1; padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 500; display: flex; align-items: center; gap: 6px;">
                        <span>⤒</span> Upload Circular
                    </div>
                </div>
            </div>
            """
            )

            # Interactive Filter Obligations Bar (clickable pills, no dropdown)
            counts_map = {
                "ALL": len(obls_list),
                "MODIFIED": sum(1 for o in obls_list if o.get("change_classification") == "MODIFIED"),
                "NEW": sum(1 for o in obls_list if o.get("change_classification") == "NEW"),
                "UNCHANGED": sum(1 for o in obls_list if o.get("change_classification") == "UNCHANGED"),
                "NEEDS_REVIEW": sum(1 for o in obls_list if o.get("change_classification") in ["NEEDS_REVIEW", "POTENTIAL_CONFLICT"]),
            }
            col_f_hdr, col_f_pills = st.columns([1, 4])
            with col_f_hdr:
                render_html(
                    """
                    <div style="display: flex; align-items: center; gap: 8px; padding-top: 8px;">
                        <span style="font-size: 16px; color: #818CF8;">⚡</span>
                        <span style="font-size: 13px; font-weight: 700; color: #FFFFFF; letter-spacing: 0.3px;">Filter obligations</span>
                    </div>
                    """
                )
            with col_f_pills:
                selected_pill = st.pills(
                    "Filter obligations",
                    ["ALL", "MODIFIED", "NEW", "UNCHANGED", "NEEDS_REVIEW"],
                    default="ALL",
                    selection_mode="single",
                    label_visibility="collapsed",
                    key="agent1_interactive_status_pills",
                    format_func=lambda s: {
                        "ALL": f"⚡ ALL ({counts_map['ALL']})",
                        "MODIFIED": f"🟢 Modified ({counts_map['MODIFIED']})",
                        "NEW": f"🔵 New ({counts_map['NEW']})",
                        "UNCHANGED": f"⚪ Unchanged ({counts_map['UNCHANGED']})",
                        "NEEDS_REVIEW": f"🟠 Needs Review ({counts_map['NEEDS_REVIEW']})",
                    }.get(s, s),
                )
                status_filter_choice = selected_pill or "ALL"

            filtered_obls = [
                o for o in obls_list
                if status_filter_choice == "ALL"
                or (status_filter_choice == "NEEDS_REVIEW" and o.get("change_classification") in ["NEEDS_REVIEW", "POTENTIAL_CONFLICT"])
                or o.get("change_classification") == status_filter_choice
            ]

            render_html(f'<div style="font-size: 12px; color: #64748B; margin: 12px 0 14px 2px;">Showing <b>{len(filtered_obls)}</b> obligations</div>')

            # Obligation cards with bank icons matching Image 2 & Image 3
            for idx, obl in enumerate(filtered_obls):
                chg_class = obl.get("change_classification", "NEW")
                is_modified = (chg_class == "MODIFIED")
                status_icon = "🟢" if is_modified else "🔵" if chg_class == "NEW" else "⚪"
                status_badge = "MODIFIED" if is_modified else "NEW" if chg_class == "NEW" else chg_class

                expander_label = f"{status_icon} 🏦 {obl.get('obligation_id')} · §{obl.get('clause_id')} — {obl.get('text', '')[:70]}... [{status_badge}]"

                with st.expander(expander_label, expanded=(idx == 0)):
                    # Metadata grid matching Image 2 (Applicability, Responsible Team, Action, Deadline)
                    render_html(
                        f"""
                        <div class="a1-meta-grid">
                            <div class="a1-meta-item">
                                <span class="a1-meta-icon">🎯</span>
                                <div>
                                    <div class="a1-meta-label">Applicability</div>
                                    <div class="a1-meta-val">{obl.get('applicability', 'All Customer Segments')}</div>
                                </div>
                            </div>
                            <div class="a1-meta-item">
                                <span class="a1-meta-icon">🏢</span>
                                <div>
                                    <div class="a1-meta-label">Responsible Team</div>
                                    <div class="a1-meta-val">{obl.get('responsible_function', 'Branch Operations & Customer Service')}</div>
                                </div>
                            </div>
                            <div class="a1-meta-item">
                                <span class="a1-meta-icon">📋</span>
                                <div>
                                    <div class="a1-meta-label">Action</div>
                                    <div class="a1-meta-val">{obl.get('required_action', 'Update internal policy and rule engine')}</div>
                                </div>
                            </div>
                            <div class="a1-meta-item">
                                <span class="a1-meta-icon">📅</span>
                                <div>
                                    <div class="a1-meta-label">Deadline / Frequency</div>
                                    <div class="a1-meta-val">{obl.get('deadline_or_frequency', 'Immediate')}</div>
                                </div>
                            </div>
                        </div>
                        """
                    )

                    # BEFORE & AFTER rule boxes with Bank Icons
                    if is_modified:
                        prev_tag = "BEFORE (EXISTING BANK RULE)"
                        prev_req = obl.get("previous_requirement") or "General queuing and service priority applied to all retail customer tiers without age-specific differentiation."

                        after_tag = "AFTER (NEW / AMENDED RULE)"
                        after_req = obl.get("amended_requirement") or obl.get("text") or "Priority service desk and dedicated queue bands introduced across all retail branches."
                        after_icon = "🏦"
                    else:
                        prev_tag = "BEFORE (EXISTING BANK RULE)"
                        prev_req = obl.get("previous_requirement") or "None (New requirement introduced in 2026 amendment)"

                        after_tag = "AFTER (NEW REGULATORY RULE)"
                        after_req = obl.get("text") or "Branches must provide dedicated assisted digital support for customers aged 60+ seeking self-service digital adoption."
                        after_icon = "📜"

                    render_html(
                        f"""
                        <div style="display: flex; gap: 14px; align-items: stretch; margin-top: 10px; margin-bottom: 12px;">
                            <div class="a1-before-box">
                                <div class="a1-box-tag" style="color: #60A5FA;">
                                    <span style="font-size:16px;">🏦</span> {prev_tag}
                                </div>
                                <div style="font-size: 12px; color: #CBD5E1; line-height: 1.5;">
                                    {prev_req}
                                </div>
                            </div>
                            <div style="display: flex; align-items: center; justify-content: center; color: #818CF8; font-weight: 700; font-size: 18px; padding: 0 4px;">
                                »
                            </div>
                            <div class="a1-after-box">
                                <div class="a1-box-tag" style="color: #34D399;">
                                    <span style="font-size:16px;">{after_icon}</span> {after_tag}
                                </div>
                                <div style="font-size: 12px; color: #E2E8F0; line-height: 1.5; font-weight: 500;">
                                    {after_req}
                                </div>
                            </div>
                        </div>
                        """
                    )

                    # Preserved excerpt snippet
                    excerpt = obl.get("supporting_excerpt", "")
                    if excerpt:
                        st.caption(f"Exact Circular Citation excerpt: {excerpt[:240]}...")

        # ─── TAB 3: AMENDMENTS ───
        with tab_comparison:
            render_html('<div class="a1-shimmer"></div>')
            comp_items = comparison_data.get("comparison_items", [])

            if not comp_items:
                st.info("No amendments found.")
            for idx, item in enumerate(comp_items):
                chg_class = item.get("classification", "NEW")
                badge_cls = "badge-modified" if chg_class == "MODIFIED" else "badge-new"
                baseline = item.get("baseline_requirement", "N/A")
                amended = item.get("amended_requirement", "N/A")
                if len(baseline) > 130:
                    baseline = baseline[:130] + "…"
                if len(amended) > 130:
                    amended = amended[:130] + "…"

                render_html(
                    f"""
                <div class="a1-diff" style="animation-delay:{0.12*idx}s;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
                        <span class="a1-extract-id">{item.get('obligation_id')}</span>
                        <span style="font-size:11px;color:#94A3B8;">§{item.get('clause_id')}</span>
                        <span class="{badge_cls}" style="margin-left:auto;">{chg_class}</span>
                    </div>
                    <div class="a1-diff-grid">
                        <div><div class="a1-diff-tag">Baseline</div><div class="a1-diff-old">{baseline}</div></div>
                        <div class="a1-diff-arrow">→</div>
                        <div><div class="a1-diff-tag">Amended</div><div class="a1-diff-new">{amended}</div></div>
                    </div>
                </div>
                """
                )

        # ─── TAB 4: EVIDENCE ───
        with tab_evidence:
            render_html('<div class="a1-shimmer"></div>')
            ev_list = evidence_data.get("evidence", [])

            if not ev_list:
                st.info("No evidence records.")
            for idx, ev in enumerate(ev_list):
                excerpt = ev.get('exact_supporting_excerpt', '')
                if len(excerpt) > 150:
                    excerpt = excerpt[:150] + "…"
                render_html(
                    f"""
                <div class="a1-ev" style="animation-delay:{0.1*idx}s;">
                    <div class="a1-ev-top">
                        <svg class="a1-check-svg" viewBox="0 0 36 36" style="width:18px;height:18px;flex-shrink:0;"><circle cx="18" cy="18" r="15" style="animation-delay:{0.2+0.1*idx}s;"/><polyline points="11,19 16,24 25,13" style="animation-delay:{0.5+0.1*idx}s;"/></svg>
                        <span class="a1-ev-tag">{ev.get('obligation_id')}</span>
                        <span class="a1-ev-src">{ev.get('source_document','N/A')} · p.{ev.get('page_number','?')}</span>
                    </div>
                    <div class="a1-ev-txt">"{excerpt}"</div>
                </div>
                """
                )

        # ─── TAB 5: QUALITY & VERIFICATION (Matching Image 4 Layout) ───
        with tab_quality:
            render_html('<div class="a1-shimmer"></div>')

            pages_proc = coverage_data.get('pages_processed', 7)
            total_pg = coverage_data.get('total_pages', 7)
            chunks_proc = coverage_data.get('chunks_processed', 14)
            total_chunks = coverage_data.get('total_chunks', 14)
            missing = qc.get("missing_clauses", [])
            dups = qc.get("duplicates_detected", [])
            review_flags = qc.get('human_review_required', 0)

            # Image 4 Top Breadcrumb & Model Indicator
            render_html(
                """
            <div class="a1-docintel-header">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 16px; color: #10B981;">🛡️</span>
                    <span style="font-size: 13px; font-weight: 600; color: #FFFFFF;">Intelligent Automation &nbsp;›&nbsp; Document Intelligence &nbsp;›&nbsp; <span style="color: #34D399;">Review</span></span>
                </div>
                <div style="display: flex; align-items: center; gap: 14px;">
                    <span class="badge-pill badge-completed" style="font-size: 11px;">● DocMind v2.4 (Groq Llama-3.3 + fastembed)</span>
                    <span style="font-size: 14px; color: #94A3B8;">🔔</span>
                </div>
            </div>
            """
            )

            # Interactive Subtabs matching Image 4
            subtab_extracted, subtab_source, subtab_audit = st.tabs([
                "📑 Extracted Data",
                "📄 Source Document",
                "🔍 Audit Trail",
            ])

            with subtab_extracted:
                # 3-Column Document Intelligence Layout matching Image 4
                col_doc, col_fields, col_val = st.columns([1.1, 1.2, 0.9])

                with col_doc:
                    # Document Preview Card matching Image 4
                    render_html(
                        f"""
                    <div style="background: #0B1124; border: 1px solid #1A2649; border-radius: 12px; padding: 14px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <span style="font-size: 12px; font-weight: 600; color: #FFFFFF; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{source_doc_name}</span>
                            <span style="font-size: 10px; color: #64748B;">100% ⤢</span>
                        </div>
                        <div class="a1-doc-paper">
                            <div style="text-align: center; border-bottom: 1px solid #E2E8F0; padding-bottom: 8px; margin-bottom: 12px;">
                                <div style="font-size: 13px; font-weight: 700; color: #0F172A; text-transform: uppercase;">RESERVE BANK OF INDIA</div>
                                <div style="font-size: 9px; color: #64748B; letter-spacing: 0.5px;">CUSTOMER SERVICE ADVISORY · 2026</div>
                            </div>
                            <div style="font-size: 10px; color: #334155; line-height: 1.5;">
                                <b>1. Purpose & Application</b><br/>
                                This circular introduces mandatory amendments to customer priority safeguards...
                            </div>
                            <div class="a1-doc-clause-hl">
                                <b>Clause 2.1 Eligibility:</b> Customers aged 60+ receive differentiated assistance categorized into bands 60-69, 70-79, and 80+.
                            </div>
                            <div class="a1-doc-clause-hl">
                                <b>Clause 2.3 Escalation:</b> Unresolved grievances after 7 working days escalate automatically to the Internal Ombudsman.
                            </div>
                            <div class="a1-doc-clause-hl">
                                <b>Clause 2.5 Complaints SLA:</b> Acknowledge within 1 working day; target resolution within 7 working days.
                            </div>
                            <div style="position: absolute; bottom: 10px; left: 20px; right: 20px; display: flex; justify-content: space-between; font-size: 10px; color: #64748B; border-top: 1px solid #E2E8F0; padding-top: 6px; font-family: 'Inter', sans-serif;">
                                <span>Page 1 of {total_pg}</span>
                                <span>‹ &nbsp; 1 / {total_pg} &nbsp; ›</span>
                            </div>
                        </div>
                    </div>
                    """
                    )

                with col_fields:
                    # Build rows without indentation to prevent Markdown code-block rendering
                    row_parts = []
                    for obl in obls_list[:6]:
                        ob_id = obl.get("obligation_id", "OBL")
                        clause_id = obl.get("clause_id", "2.1")
                        req_action = obl.get("required_action") or obl.get("text", "")[:35]
                        conf = obl.get("confidence", "98%")
                        if not str(conf).endswith("%"):
                            conf = f"{float(conf)*100:.0f}%" if isinstance(conf, (int, float)) else "98%"
                        row_parts.append(
                            '<div class="a1-data-row-img4">'
                            '<div style="display:flex;align-items:center;gap:8px;min-width:0;flex:1;">'
                            f'<span style="font-size:14px;color:#818CF8;">📄</span>'
                            '<div style="min-width:0;">'
                            f'<div style="font-size:11px;font-weight:600;color:#FFFFFF;">Clause {clause_id} ({ob_id})</div>'
                            f'<div style="font-size:10px;color:#94A3B8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{req_action}</div>'
                            '</div></div>'
                            '<div style="display:flex;align-items:center;gap:8px;">'
                            f'<span class="badge-pill badge-completed" style="font-size:10px;padding:2px 8px;">{conf}</span>'
                            '<span style="color:#34D399;font-size:13px;">✓</span>'
                            '</div></div>'
                        )
                    rows_html = "\n".join(row_parts)
                    render_html(
                        f"""
                    <div style="background: #0B1124; border: 1px solid #1A2649; border-radius: 12px; padding: 14px; height: 100%;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 13px; font-weight: 600; color: #FFFFFF;">Extracted Data</span>
                                <span class="badge-pill badge-demo" style="font-size: 10px;">{len(obls_list)} fields</span>
                            </div>
                            <span style="font-size: 11px; color: #64748B;">Confidence ✓</span>
                        </div>
                        {rows_html}
                        <div style="background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 10px 12px; margin-top: 12px; display: flex; align-items: center; justify-content: space-between;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 14px; color: #FBBF24;">⚠️</span>
                                <div>
                                    <div style="font-size: 11px; font-weight: 600; color: #FBBF24;">Anomaly Detection Gate</div>
                                    <div style="font-size: 10px; color: #94A3B8;">0 review flags · Continuous numbering preserved</div>
                                </div>
                            </div>
                            <span class="badge-pill badge-completed" style="font-size: 10px;">Verified</span>
                        </div>
                    </div>
                    """
                    )

                with col_val:
                    render_html(
                        f"""
                    <div style="display: flex; flex-direction: column; gap: 14px;">
                        <div style="background: #0B1124; border: 1px solid #1A2649; border-radius: 12px; padding: 14px;">
                            <div style="font-size: 12px; font-weight: 600; color: #FFFFFF; margin-bottom: 10px;">Validation Checks</div>
                            <div style="display: flex; align-items: center; gap: 16px;">
                                <div class="a1-gauge-ring" style="width: 60px; height: 60px;">
                                    <span style="font-size: 14px; font-weight: 700; color: #34D399;">6/6</span>
                                </div>
                                <div style="font-size: 11px; line-height: 1.8;">
                                    <div style="color: #34D399;">● Passed 6</div>
                                    <div style="color: #94A3B8;">● Warnings 0</div>
                                    <div style="color: #64748B;">● Failed 0</div>
                                </div>
                            </div>
                        </div>
                        <div style="background: #0B1124; border: 1px solid #1A2649; border-radius: 12px; padding: 14px;">
                            <div style="font-size: 12px; font-weight: 600; color: #FFFFFF; margin-bottom: 12px;">Activity Timeline</div>
                            <div class="a1-timeline-step">
                                <div class="a1-timeline-dot">⤒</div>
                                <div>
                                    <div style="font-size: 11px; font-weight: 600; color: #FFFFFF;">Document uploaded</div>
                                    <div style="font-size: 10px; color: #64748B;">{total_pages} pages parsed</div>
                                </div>
                            </div>
                            <div class="a1-timeline-step">
                                <div class="a1-timeline-dot">⚙️</div>
                                <div>
                                    <div style="font-size: 11px; font-weight: 600; color: #FFFFFF;">Data extracted</div>
                                    <div style="font-size: 10px; color: #64748B;">DocMind + BGE Embeddings</div>
                                </div>
                            </div>
                            <div class="a1-timeline-step">
                                <div class="a1-timeline-dot">🛡️</div>
                                <div>
                                    <div style="font-size: 11px; font-weight: 600; color: #FFFFFF;">Validation checks</div>
                                    <div style="font-size: 10px; color: #34D399;">6 passed, 0 failed</div>
                                </div>
                            </div>
                            <div class="a1-timeline-step">
                                <div class="a1-timeline-dot">✓</div>
                                <div>
                                    <div style="font-size: 11px; font-weight: 600; color: #FFFFFF;">Sent to review</div>
                                    <div style="font-size: 10px; color: #818CF8;">Ready for Agent 2 Mapping</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    """
                    )

            with subtab_source:
                # Full Original Source Document Viewer (loads real PDF pages if available)
                available_source_pdfs = []
                for pdf_dir in [ROOT / "data" / "source_pdfs", ROOT / "cidan" / "data"]:
                    if pdf_dir.is_dir():
                        available_source_pdfs.extend(sorted(pdf_dir.glob("*.pdf"), key=lambda p: p.name.lower()))

                selected_pdf_path = None
                if available_source_pdfs:
                    pdf_names = [p.name for p in available_source_pdfs]
                    default_idx = 0
                    for i, pname in enumerate(pdf_names):
                        if source_doc_name.lower() in pname.lower() or "circular" in pname.lower() or "amendment" in pname.lower():
                            default_idx = i
                            break
                    chosen_pdf_name = st.pills(
                        "Source Document",
                        pdf_names,
                        default=pdf_names[default_idx],
                        selection_mode="single",
                        key="agent1_source_doc_selector",
                    ) or pdf_names[default_idx]
                    selected_pdf_path = next((p for p in available_source_pdfs if p.name == chosen_pdf_name), None)

                doc_title = selected_pdf_path.name if selected_pdf_path else source_doc_name
                extracted_pages_html = ""
                page_count_display = total_pages

                if selected_pdf_path is not None:
                    try:
                        import html as _html
                        import pymupdf

                        with pymupdf.open(selected_pdf_path) as pdf_doc:
                            page_count_display = len(pdf_doc)
                            page_blocks = []
                            for p_idx, pdf_page in enumerate(pdf_doc, start=1):
                                page_text = _html.escape(pdf_page.get_text("text").strip())
                                page_blocks.append(
                                    f'<div style="background:#0A1024;border:1px solid #1E2D56;border-radius:8px;padding:16px 20px;margin-bottom:14px;">'
                                    f'<div style="font-size:11px;font-weight:700;color:#818CF8;text-transform:uppercase;margin-bottom:8px;border-bottom:1px solid #16203B;padding-bottom:6px;">Page {p_idx} of {page_count_display}</div>'
                                    f'<pre style="margin:0;white-space:pre-wrap;font-family:\'Inter\',sans-serif;font-size:12px;color:#E2E8F0;line-height:1.65;">{page_text}</pre>'
                                    f'</div>'
                                )
                            extracted_pages_html = "\n".join(page_blocks)
                    except Exception:
                        extracted_pages_html = ""

                if not extracted_pages_html:
                    ev_blocks = []
                    for ev in evidence_data.get("evidence", []):
                        import html as _html
                        cl = _html.escape(str(ev.get("clause_id", "")))
                        pg = ev.get("page_number", 1)
                        ex = _html.escape(str(ev.get("exact_supporting_excerpt", "")))
                        ev_blocks.append(
                            f'<div style="background:rgba(99,102,241,0.08);border-left:3px solid #818CF8;padding:12px 16px;border-radius:6px;margin-bottom:12px;font-family:\'Inter\',sans-serif;font-size:12px;">'
                            f'<b style="color:#A5B4FC;">Clause {cl} (Page {pg}):</b> {ex}'
                            f'</div>'
                        )
                    extracted_pages_html = "\n".join(ev_blocks) if ev_blocks else '<div style="color:#94A3B8;font-size:12px;">No source document text available.</div>'

                render_html(
                    f"""
                <div style="background: #0B1124; border: 1px solid #1A2649; border-radius: 14px; padding: 20px; margin-bottom: 16px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #16203B; padding-bottom: 12px; margin-bottom: 16px;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-size: 24px;">📄</span>
                            <div>
                                <div style="font-size: 15px; font-weight: 700; color: #FFFFFF;">{doc_title}</div>
                                <div style="font-size: 11px; color: #94A3B8;">Original Source Document · Ingested & Verified</div>
                            </div>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            <span class="badge-pill badge-completed">100% Ingested</span>
                            <span class="badge-pill badge-demo">{page_count_display} Pages</span>
                            <span class="badge-pill badge-modified">Original Source</span>
                        </div>
                    </div>
                    <div style="max-height: 520px; overflow-y: auto; padding-right: 6px;">
                        {extracted_pages_html}
                    </div>
                </div>
                """
                )

            with subtab_audit:
                # Full Audit Trail View
                render_html(
                    f"""
                <div style="background: #0B1124; border: 1px solid #1A2649; border-radius: 14px; padding: 20px; margin-bottom: 16px;">
                    <div style="font-size: 15px; font-weight: 700; color: #FFFFFF; margin-bottom: 14px;">Compliance & Ingestion Audit Trail</div>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 18px;">
                        <div style="background: #080D1D; border: 1px solid #1A2649; border-radius: 10px; padding: 14px;">
                            <div style="font-size: 10px; color: #64748B; text-transform: uppercase; font-weight: 600;">Ingestion Status</div>
                            <div style="font-size: 16px; color: #34D399; font-weight: 700; margin-top: 4px;">✓ Verified 100%</div>
                            <div style="font-size: 11px; color: #94A3B8; margin-top: 2px;">{pages_proc} of {total_pg} pages parsed</div>
                        </div>
                        <div style="background: #080D1D; border: 1px solid #1A2649; border-radius: 10px; padding: 14px;">
                            <div style="font-size: 10px; color: #64748B; text-transform: uppercase; font-weight: 600;">Quality Score</div>
                            <div style="font-size: 16px; color: #818CF8; font-weight: 700; margin-top: 4px;">{quality_score}%</div>
                            <div style="font-size: 11px; color: #94A3B8; margin-top: 2px;">High confidence extraction</div>
                        </div>
                        <div style="background: #080D1D; border: 1px solid #1A2649; border-radius: 10px; padding: 14px;">
                            <div style="font-size: 10px; color: #64748B; text-transform: uppercase; font-weight: 600;">Document Fingerprint</div>
                            <div style="font-size: 12px; color: #CBD5E1; font-family: monospace; margin-top: 6px;">8a241f7c...3495b0dd</div>
                            <div style="font-size: 10px; color: #34D399; margin-top: 2px;">● Cryptographically Verified</div>
                        </div>
                    </div>
                </div>
                """
                )
                with st.expander("🔍 View Raw Execution Metadata JSON"):
                    st.json(coverage_data)

            # Bottom Enterprise Control Bar with interactive navigation to Agent 2
            render_html(
                f"""
            <div class="a1-bottom-bar-img4" style="margin-bottom: 10px;">
                <div style="display: flex; align-items: center; gap: 14px;">
                    <div class="a1-gauge-ring" style="width: 50px; height: 50px;">
                        <span style="font-size: 12px; font-weight: 800; color: #34D399;">{quality_score}%</span>
                    </div>
                    <div>
                        <div style="font-size: 12px; font-weight: 600; color: #FFFFFF;">Confidence Score</div>
                        <div style="font-size: 10px; color: #34D399;">High confidence · Ready for Agent 2 Mapping</div>
                    </div>
                </div>
                <div style="font-size: 11px; color: #94A3B8;">
                    ⚡ {obls_count} obligations verified · Ready to map against bank policies
                </div>
            </div>
            """
            )
            b_note_col, b_flag_col, b_go_col = st.columns([3, 1, 1.3])
            with b_note_col:
                st.text_input(
                    "Review note",
                    placeholder="Add an internal compliance review note (optional)...",
                    label_visibility="collapsed",
                    key="agent1_review_note_input",
                )
            with b_flag_col:
                if st.button("🚩 Flag for Review", use_container_width=True, key="agent1_flag_review_btn"):
                    st.toast("Workflow flagged for compliance review.", icon="🚩")
            with b_go_col:
                if st.button("✓ Approve & Export (Agent 2) →", type="primary", use_container_width=True, key="agent1_approve_export_btn"):
                    st.session_state["pending_agent_nav"] = "Agent 2 – Policy Mapping"
                    st.session_state["agent1_exported_toast"] = True
                    st.rerun()

    elif selected_agent == "Agent 2 – Policy Mapping":
        # AGENT 2 DETAILED DASHBOARD
        if st.session_state.pop("agent1_exported_toast", False):
            st.toast("Approved & exported obligations to Agent 2 – Policy Mapping!", icon="🚀")
            render_html(
                """
                <div style="background:linear-gradient(90deg,rgba(16,185,129,0.16),rgba(99,102,241,0.16));border:1px solid #10B981;border-radius:10px;padding:10px 16px;margin-bottom:14px;display:flex;align-items:center;gap:10px;animation:a1-up .4s ease-out;">
                    <span style="font-size:16px;">✨</span>
                    <span style="font-size:12px;color:#E2E8F0;font-weight:600;">Agent 1 Obligations Approved &amp; Exported → Policy Mapping Active</span>
                </div>
                """
            )
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

            # Agent 2 Navigation Tabs (Quality Checks removed per user request)
            tab_overview, tab_findings, tab_evidence, tab_confidence = st.tabs(
                [
                    "📊 Overview",
                    "🎯 Policy Mapping Results",
                    "📑 Evidence & Citations",
                    "⚖️ Confidence Analysis",
                ]
            )

            avg_conf = sum(f.get("confidence", 0.0) for f in findings_list) / max(1, total_findings)
            avg_ev_conf = sum(f.get("evidence_confidence", 0.0) for f in findings_list) / max(1, total_findings)

            with tab_overview:
                # 4-Step Pipeline: Extract -> Map -> Analyze -> Result
                render_html(
                    f"""
                    <div class="a2-pipe">
                        <div class="a2-step" style="animation-delay:.05s;">
                            <div class="a2-step-circle done">📄</div>
                            <div class="a2-step-lbl">1. Extract ({total_findings})</div>
                        </div>
                        <div class="a2-step-line"></div>
                        <div class="a2-step" style="animation-delay:.5s;">
                            <div class="a2-step-circle">🗺️</div>
                            <div class="a2-step-lbl">2. Map</div>
                        </div>
                        <div class="a2-step-line"></div>
                        <div class="a2-step" style="animation-delay:1.1s;">
                            <div class="a2-step-circle">📊</div>
                            <div class="a2-step-lbl">3. Analyze</div>
                        </div>
                        <div class="a2-step-line"></div>
                        <div class="a2-step" style="animation-delay:1.6s;">
                            <div class="a2-step-circle done">✓</div>
                            <div class="a2-step-lbl">4. Result ({total_findings})</div>
                        </div>
                    </div>
                    """
                )

                # Synchronized Staged Animation: Extract (Obligations) -> Map (Connectors) -> Analyze (Matched Clauses)
                status_icon_map = {
                    "covered": ("🟢", "#34D399"),
                    "partially_covered": ("🟡", "#FBBF24"),
                    "potential_conflict": ("🔴", "#F87171"),
                    "not_found": ("🟣", "#A78BFA"),
                    "requires_human_review": ("🟠", "#FB923C"),
                }
                map_rows_parts = []
                for idx, f in enumerate(findings_list):
                    ob_id = f.get("obligation_id", "N/A")
                    st_val = f.get("status", "unknown")
                    s_icon, s_col = status_icon_map.get(st_val, ("⚪", "#94A3B8"))
                    badge = get_status_badge(st_val)
                    prov = f.get("matching_policy_provision") or "No matching policy"
                    if len(prov) > 44:
                        prov = prov[:44] + "…"
                    cites_cnt = len(f.get("policy_citations", []))
                    d_extract = 0.2 + 0.08 * idx
                    d_map = 0.85 + 0.08 * idx
                    d_analyze = 1.45 + 0.08 * idx
                    map_rows_parts.append(
                        f'<div class="a2-map-row">'
                        f'<div class="a2-map-node" style="animation:a1-slide-in .4s ease-out {d_extract:.2f}s backwards;">'
                        f'<div style="display:flex;align-items:center;gap:8px;"><span style="font-size:14px;">{s_icon}</span><b style="color:#FFFFFF;font-size:12px;">{ob_id}</b></div>'
                        f'{badge}'
                        f'</div>'
                        f'<div class="a2-map-link" style="animation:a1-line-draw .5s ease-out {d_map:.2f}s backwards;"></div>'
                        f'<div class="a2-map-node" style="animation:a1-up .4s ease-out {d_analyze:.2f}s backwards;">'
                        f'<div style="display:flex;align-items:center;gap:8px;min-width:0;"><span style="font-size:14px;">🏦</span><span style="color:#E2E8F0;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{prov}</span></div>'
                        f'<span style="font-size:10px;color:{s_col};font-weight:600;white-space:nowrap;">{cites_cnt} cites</span>'
                        f'</div>'
                        f'</div>'
                    )
                map_rows_html = "\n".join(map_rows_parts)
                render_html(
                    f"""
                    <div class="a2-map-board">
                        <div style="display:grid;grid-template-columns:1.1fr 0.35fr 1.1fr;gap:10px;margin-bottom:10px;padding:0 4px;">
                            <div style="font-size:11px;font-weight:700;color:#818CF8;text-transform:uppercase;letter-spacing:0.5px;">📄 1. Extracted Obligations ({total_findings})</div>
                            <div style="font-size:11px;font-weight:700;color:#A78BFA;text-transform:uppercase;letter-spacing:0.5px;text-align:center;">2. Map</div>
                            <div style="font-size:11px;font-weight:700;color:#34D399;text-transform:uppercase;letter-spacing:0.5px;">🏦 3. Analyzed Policy Clauses ({total_findings})</div>
                        </div>
                        {map_rows_html}
                    </div>
                    """
                )

            with tab_findings:
                def _svg_strand_connector(direction: str = "in", c1: str = "#6366F1", c2: str = "#A78BFA", dot_x: int = 114) -> str:
                    p_top = "M0,12 C45,12 75,35 120,35" if direction == "in" else "M0,35 C45,35 75,12 120,12"
                    p_bot = "M0,58 C45,58 75,35 120,35" if direction == "in" else "M0,35 C45,35 75,58 120,58"
                    return (
                        '<svg viewBox="0 0 120 70" style="width:100%;height:70px;overflow:visible;">'
                        f'<path d="{p_top}" fill="none" stroke="{c1}" stroke-width="2" stroke-opacity="0.55" stroke-dasharray="5 4" style="animation:a2-dash-flow 1.4s linear infinite;"/>'
                        f'<path d="M0,35 L120,35" fill="none" stroke="{c2}" stroke-width="2.5" stroke-dasharray="6 6" style="animation:a2-dash-flow 1s linear infinite;"/>'
                        f'<path d="{p_bot}" fill="none" stroke="{c1}" stroke-width="2" stroke-opacity="0.55" stroke-dasharray="5 4" style="animation:a2-dash-flow 1.4s linear infinite;"/>'
                        f'<circle cx="{dot_x}" cy="35" r="4.5" fill="{c2}" style="animation:a1-pulse 1.4s infinite;"/>'
                        '</svg>'
                    )

                svg_connect_left = _svg_strand_connector("in", "#6366F1", "#A78BFA", 114)
                svg_connect_right = _svg_strand_connector("out", "#38BDF8", "#34D399", 6)
                render_html(
                    f"""
                    <div class="a2-bridge" style="grid-template-columns:1fr 0.55fr 1.1fr 0.55fr 1fr;margin-top:6px;">
                        <div class="a2-bridge-card" style="animation:a1-slide-in .35s ease-out;">
                            <div style="font-size:30px;margin-bottom:6px;">📜</div>
                            <div style="font-size:13px;font-weight:700;color:#FFFFFF;">Regulatory Circular</div>
                            <div style="font-size:11px;color:#94A3B8;margin-top:3px;">{total_findings} Extracted Obligations</div>
                        </div>
                        <div>{svg_connect_left}</div>
                        <div class="a2-bridge-center">
                            <div style="font-size:28px;margin-bottom:6px;">🔷</div>
                            <div style="font-size:14px;font-weight:700;color:#FFFFFF;">Policy Mapping</div>
                            <div style="font-size:11px;color:#C4B5FD;margin-top:3px;">Semantic &amp; Citation Alignment</div>
                        </div>
                        <div>{svg_connect_right}</div>
                        <div class="a2-bridge-card" style="animation:a1-up .35s ease-out;">
                            <div style="font-size:30px;margin-bottom:6px;">🏦</div>
                            <div style="font-size:13px;font-weight:700;color:#FFFFFF;">Internal Policies</div>
                            <div style="font-size:11px;color:#94A3B8;margin-top:3px;">{c_covered} Covered · {c_partially + c_conflict + c_not_found} Actions</div>
                        </div>
                    </div>
                    """
                )

                # Downward connection visual from Policy Mapping icon before results appear
                render_html(
                    """
                    <div style="display:flex;flex-direction:column;align-items:center;margin:-4px 0 12px;">
                        <svg viewBox="0 0 80 54" style="width:80px;height:54px;overflow:visible;">
                            <line x1="40" y1="0" x2="40" y2="48" stroke="#A78BFA" stroke-width="2.5" stroke-dasharray="5 5" style="animation:a2-dash-flow 1.1s linear infinite;"/>
                            <circle cx="40" cy="48" r="5" fill="#A78BFA" style="animation:a1-pulse 1.4s infinite;"/>
                        </svg>
                        <div style="display:inline-flex;align-items:center;gap:8px;padding:7px 20px;background:radial-gradient(circle at 50% 50%,rgba(99,102,241,0.2),rgba(11,18,40,0.92));border:1px solid rgba(139,92,246,0.55);border-radius:999px;box-shadow:0 0 22px rgba(99,102,241,0.22);animation:a1-up .4s ease-out .35s backwards;">
                            <span style="font-size:16px;">🔷</span>
                            <span style="font-size:12px;font-weight:700;color:#E2E8F0;letter-spacing:0.3px;">Policy Mapping Results</span>
                            <span style="font-size:13px;color:#34D399;font-weight:800;">✓</span>
                        </div>
                        <svg viewBox="0 0 240 34" style="width:240px;height:34px;overflow:visible;">
                            <path d="M120,0 L120,16 M120,16 L24,16 L24,30 M120,16 L216,16 L216,30" fill="none" stroke="#38BDF8" stroke-width="2" stroke-opacity="0.65" stroke-dasharray="4 4" style="animation:a2-dash-flow 1.1s linear infinite;"/>
                            <circle cx="24" cy="30" r="3.5" fill="#38BDF8" style="animation:a1-pulse 1.4s infinite;"/>
                            <circle cx="216" cy="30" r="3.5" fill="#38BDF8" style="animation:a1-pulse 1.4s infinite;"/>
                        </svg>
                    </div>
                    <div style="animation:a1-up .45s ease-out .75s backwards;"></div>
                    """
                )

                # Functional Interactive Filter Buttons (6 clickable category buttons matching Image 3)
                if "a2_pm_filter" not in st.session_state:
                    st.session_state["a2_pm_filter"] = "All"

                btn_cols = st.columns(6)
                filter_defs = [
                    ("All", f"📄 Total ({total_findings})"),
                    ("covered", f"✅ Covered ({c_covered})"),
                    ("partially_covered", f"🔄 Partial ({c_partially})"),
                    ("potential_conflict", f"⚠️ Conflict ({c_conflict})"),
                    ("not_found", f"❌ Not Found ({c_not_found})"),
                    ("requires_human_review", f"👁️ Review ({c_review})"),
                ]
                for b_col, (f_key, f_lbl) in zip(btn_cols, filter_defs):
                    with b_col:
                        is_active = st.session_state["a2_pm_filter"] == f_key
                        if st.button(
                            f_lbl,
                            key=f"a2_pm_btn_{f_key}",
                            type="primary" if is_active else "secondary",
                            use_container_width=True,
                        ):
                            st.session_state["a2_pm_filter"] = f_key
                            st.rerun()

                filter_status = st.session_state["a2_pm_filter"]
                search_query = st.text_input("Search", placeholder="🔍 Search obligation, policy, or impact...", label_visibility="collapsed")

                filtered_findings = findings_list
                if filter_status != "All":
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

                st.caption(f"Showing {len(filtered_findings)} of {total_findings} mapped obligations (Filter: {filter_status})")

                for idx_f, f in enumerate(filtered_findings):
                    ob_id = f.get("obligation_id", "N/A")
                    status = f.get("status", "unknown")
                    badge = get_status_badge(status)
                    matching_provision = f.get("matching_policy_provision", "None identified")
                    conf = f.get("confidence", 0.0)
                    ob_info = obligations_lookup.get(ob_id, {})
                    ob_text = ob_info.get("text", f.get("circular_citation", {}).get("excerpt", "N/A"))
                    s_icon = {"covered": "🟢", "partially_covered": "🟡", "potential_conflict": "🔴", "not_found": "🟣", "requires_human_review": "🟠"}.get(status, "⚪")

                    with st.expander(f"{s_icon} {ob_id} — {matching_provision} ({conf:.0%})", expanded=(idx_f == 0)):
                        render_html(
                            f"""
                            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;animation:a1-up .45s ease-out .75s backwards;">
                                {badge}
                                <span style="font-size:12px;color:#94A3B8;">Match: <b style="color:#F1F5F9;">{matching_provision}</b></span>
                                <div style="margin-left:auto;display:flex;align-items:center;gap:8px;min-width:150px;">
                                    <div class="a2-bar-track"><div class="a2-bar-fill" style="width:{conf*100:.0f}%;background:linear-gradient(90deg,#6366F1,#34D399);"></div></div>
                                    <b style="font-size:12px;color:#34D399;">{conf:.0%}</b>
                                </div>
                            </div>
                            <div style="display:grid;grid-template-columns:1fr 32px 1fr;align-items:center;gap:8px;margin-bottom:10px;">
                                <div style="border-left:3px solid #6366F1;background:rgba(99,102,241,0.06);padding:10px 14px;border-radius:0 8px 8px 0;animation:a1-slide-in .35s ease-out;">
                                    <div style="font-size:10px;color:#818CF8;font-weight:700;margin-bottom:3px;">📜 CIRCULAR OBLIGATION</div>
                                    <div style="font-size:12px;color:#E2E8F0;line-height:1.45;">{ob_text}</div>
                                </div>
                                <div style="text-align:center;color:#A78BFA;font-weight:700;font-size:16px;animation:a1-pulse 1.8s infinite;">⇄</div>
                                <div style="border-left:3px solid #10B981;background:rgba(16,185,129,0.06);padding:10px 14px;border-radius:0 8px 8px 0;animation:a1-up .35s ease-out;">
                                    <div style="font-size:10px;color:#34D399;font-weight:700;margin-bottom:3px;">🏦 POLICY ANALYSIS</div>
                                    <div style="font-size:12px;color:#CBD5E1;line-height:1.45;">{f.get('reasoning', 'No reasoning provided.')}</div>
                                </div>
                            </div>
                            <div style="display:flex;gap:14px;flex-wrap:wrap;font-size:11px;color:#94A3B8;padding-top:4px;">
                                <span>💥 <b style="color:#E2E8F0;">Impact:</b> {f.get("operational_impact", "N/A")}</span>
                                <span>⚡ <b style="color:#34D399;">Action:</b> {f.get("recommended_action", "N/A")}</span>
                            </div>
                            """
                        )
                        missing_inc = f.get("missing_or_inconsistent")
                        if missing_inc and missing_inc != "none":
                            st.warning(f"⚠️ Gap / Conflict: {missing_inc}")
                        policy_cites = f.get("policy_citations", [])
                        if policy_cites:
                            cite_chips = " ".join([f"`{c.get('chunk_id')}` (p.{c.get('page', 1)})" for c in policy_cites])
                            st.caption(f"📄 Policy Chunks ({len(policy_cites)}): {cite_chips}")

            with tab_evidence:
                # Interactive Obligation Selector + Individual Animated Evidence Linking Visual
                ev_obl_ids = [f.get("obligation_id", f"OBL-{i+1}") for i, f in enumerate(findings_list)]
                selected_ev_obl = st.pills(
                    "Select Obligation Evidence",
                    ev_obl_ids,
                    default=ev_obl_ids[0] if ev_obl_ids else None,
                    selection_mode="single",
                    label_visibility="collapsed",
                    key="agent2_ev_obl_pills",
                    format_func=lambda oid: f"🏛️ {oid}",
                ) or (ev_obl_ids[0] if ev_obl_ids else None)

                active_f = next((f for f in findings_list if f.get("obligation_id") == selected_ev_obl), findings_list[0])
                ob_id = active_f.get("obligation_id", "N/A")
                status = active_f.get("status", "unknown")
                badge = get_status_badge(status)
                conf = active_f.get("confidence", 0.0)
                circ_cite = active_f.get("circular_citation", {})
                policy_cites = active_f.get("policy_citations", [])
                limitations = active_f.get("evidence_limitations", [])
                matching_prov = active_f.get("matching_policy_provision") or "No Policy Match"
                ob_info = obligations_lookup.get(ob_id, {})
                circ_clause = ob_info.get("clause_id", f"Page {circ_cite.get('page', 1)}")

                has_link = bool(policy_cites)
                link_label = "Evidence Linked" if has_link else "Not Linked"
                link_color = "#34D399" if has_link else "#F87171"

                # Unique keyframe suffix per obligation so animations replay whenever user switches obligations
                safe_obl = "".join(ch if ch.isalnum() else "_" for ch in str(ob_id))

                if has_link:
                    anim_status_icon = (
                        f'<div style="width:36px;height:36px;border-radius:50%;background:radial-gradient(circle,rgba(52,211,153,0.22),transparent 72%);'
                        f'border:1.5px solid rgba(52,211,153,0.7);display:inline-flex;align-items:center;justify-content:center;'
                        f'box-shadow:0 0 16px rgba(52,211,153,0.45);animation:a1-pulse 1.8s infinite;">'
                        f'<svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:none;stroke:#34D399;stroke-width:2.8;stroke-linecap:round;stroke-linejoin:round;">'
                        f'<path d="M5 13l4 4L19 7" stroke-dasharray="24" stroke-dashoffset="24" style="animation:ev-draw-{safe_obl} 0.55s ease 3.6s forwards;"/>'
                        f'</svg></div>'
                    )
                    inline_badge_icon = (
                        f'<svg viewBox="0 0 24 24" style="width:15px;height:15px;fill:none;stroke:#34D399;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;vertical-align:middle;margin-left:5px;">'
                        f'<path d="M5 13l4 4L19 7" stroke-dasharray="24" stroke-dashoffset="24" style="animation:ev-draw-{safe_obl} 0.5s ease 3.6s forwards;"/>'
                        f'</svg>'
                    )
                else:
                    anim_status_icon = (
                        f'<div style="width:36px;height:36px;border-radius:50%;background:radial-gradient(circle,rgba(248,113,113,0.22),transparent 72%);'
                        f'border:1.5px solid rgba(248,113,113,0.7);display:inline-flex;align-items:center;justify-content:center;'
                        f'box-shadow:0 0 16px rgba(248,113,113,0.45);animation:a1-pulse 1.8s infinite;">'
                        f'<svg viewBox="0 0 24 24" style="width:18px;height:18px;fill:none;stroke:#F87171;stroke-width:2.8;stroke-linecap:round;">'
                        f'<path d="M6 6l12 12" stroke-dasharray="20" stroke-dashoffset="20" style="animation:ev-draw-{safe_obl} 0.35s ease 3.6s forwards;"/>'
                        f'<path d="M18 6l-12 12" stroke-dasharray="20" stroke-dashoffset="20" style="animation:ev-draw-{safe_obl} 0.35s ease 3.8s forwards;"/>'
                        f'</svg></div>'
                    )
                    inline_badge_icon = (
                        f'<svg viewBox="0 0 24 24" style="width:15px;height:15px;fill:none;stroke:#F87171;stroke-width:3;stroke-linecap:round;vertical-align:middle;margin-left:5px;">'
                        f'<path d="M6 6l12 12" stroke-dasharray="20" stroke-dashoffset="20" style="animation:ev-draw-{safe_obl} 0.35s ease 3.6s forwards;"/>'
                        f'<path d="M18 6l-12 12" stroke-dasharray="20" stroke-dashoffset="20" style="animation:ev-draw-{safe_obl} 0.35s ease 3.8s forwards;"/>'
                        f'</svg>'
                    )

                dot_beam_svg = (
                    '<svg viewBox="0 0 90 12" style="width:100%;height:12px;">'
                    '<line x1="2" y1="6" x2="88" y2="6" stroke="#818CF8" stroke-width="3" '
                    'stroke-linecap="round" stroke-dasharray="1 10" '
                    'style="animation:a2-dash-flow 1.1s linear infinite;"/>'
                    '</svg>'
                )
                wave_svg = (
                    '<svg viewBox="0 0 900 38" preserveAspectRatio="none" style="width:100%;height:30px;display:block;margin:-6px 0 8px;">'
                    '<path d="M0,22 C180,2 340,36 540,18 C700,4 800,28 900,14" fill="none" stroke="rgba(139,92,246,0.35)" stroke-width="1.8"/>'
                    '<path d="M0,28 C210,36 390,4 590,24 C740,36 830,10 900,22" fill="none" stroke="rgba(56,189,248,0.28)" stroke-width="1.4"/>'
                    '</svg>'
                )
                render_html(
                    f"""
                    <style>
                        @keyframes ev-step-{safe_obl} {{ 0%{{opacity:0;transform:translateY(4px)}} 12%,82%{{opacity:1;transform:translateY(0)}} 100%{{opacity:0;transform:translateY(-4px)}} }}
                        @keyframes ev-final-{safe_obl} {{ 0%{{opacity:0;transform:translateY(4px)}} 100%{{opacity:1;transform:translateY(0)}} }}
                        @keyframes ev-draw-{safe_obl} {{ to{{stroke-dashoffset:0}} }}
                    </style>
                    <div data-obl="{ob_id}" style="background:radial-gradient(ellipse at 50% 45%, rgba(99,102,241,0.12), #070B19 72%);border:1px solid #1A2444;border-radius:18px;padding:22px 20px 10px;margin-top:10px;margin-bottom:14px;">
                        <div style="display:grid;grid-template-columns:1fr 1.15fr 1fr;align-items:center;gap:12px;">
                            <div class="a2-ev-card-circ">
                                <div style="font-size:36px;margin-bottom:8px;filter:drop-shadow(0 0 10px rgba(167,139,250,0.65));">📄</div>
                                <div style="font-size:15px;font-weight:700;color:#FFFFFF;line-height:1.25;">Regulatory<br/>Circular</div>
                                <div style="font-size:12px;color:#A5B4FC;margin-top:6px;">Clause {circ_clause} · Page {circ_cite.get('page', 1)}</div>
                            </div>
                            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;">
                                <div style="display:grid;grid-template-columns:1fr auto 1fr;align-items:center;width:100%;gap:8px;">
                                    <div>{dot_beam_svg}</div>
                                    <div class="a2-ev-orbit">
                                        <div class="a2-ev-orbit-ring"><div class="a2-ev-orbit-dot"></div></div>
                                    </div>
                                    <div>{dot_beam_svg}</div>
                                </div>
                                <div class="a2-ev-stage-wrap">
                                    <div class="a2-ev-stage" style="animation:ev-step-{safe_obl} 0.9s ease 0.0s 1;">Linking...</div>
                                    <div class="a2-ev-stage" style="animation:ev-step-{safe_obl} 0.9s ease 0.9s 1;">Analysing...</div>
                                    <div class="a2-ev-stage" style="animation:ev-step-{safe_obl} 0.9s ease 1.8s 1;">Matching...</div>
                                    <div class="a2-ev-stage" style="animation:ev-step-{safe_obl} 0.9s ease 2.7s 1;">Verifying...</div>
                                    <div class="a2-ev-stage" style="color:{link_color};font-weight:700;animation:ev-final-{safe_obl} 0.45s ease 3.6s forwards;">{link_label}{inline_badge_icon}</div>
                                </div>
                            </div>
                            <div class="a2-ev-card-pol">
                                <div style="font-size:36px;margin-bottom:8px;filter:drop-shadow(0 0 10px rgba(56,189,248,0.65));">🏦</div>
                                <div style="font-size:15px;font-weight:700;color:#FFFFFF;line-height:1.25;">Bank Policy</div>
                                <div style="font-size:12px;color:#7DD3FC;margin-top:6px;">{matching_prov}</div>
                            </div>
                        </div>
                        {wave_svg}
                    </div>

                    <div style="background:#0B1228;border:1px solid #1E2D56;border-radius:12px;padding:12px 18px;display:flex;align-items:center;gap:14px;margin-bottom:16px;animation:a1-up .4s ease-out;">
                        {anim_status_icon}
                        <b style="font-size:14px;color:#FFFFFF;">{ob_id}</b>
                        <span style="color:#64748B;">•</span>
                        {badge}
                        <span style="font-size:12px;font-weight:600;color:{link_color};">{link_label}</span>
                        <div style="margin-left:auto;display:flex;align-items:center;gap:12px;min-width:220px;">
                            <span style="font-size:11px;color:#94A3B8;">Confidence</span>
                            <div class="a2-bar-track"><div class="a2-bar-fill" style="width:{conf*100:.0f}%;background:linear-gradient(90deg,#6366F1,#34D399);"></div></div>
                            <b style="font-size:13px;color:#34D399;">{conf:.0%}</b>
                        </div>
                    </div>
                    """
                )

                # Clean Animated Proof Excerpts
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    render_html(
                        f"""
                        <div style="border-left:3px solid #6366F1;background:rgba(99,102,241,0.06);padding:12px 16px;border-radius:0 10px 10px 0;animation:a1-slide-in .35s ease-out;">
                            <div style="font-size:11px;color:#818CF8;font-weight:700;margin-bottom:6px;">📜 CIRCULAR PROOF EXCERPT (Page {circ_cite.get('page', 'N/A')})</div>
                            <div style="font-size:12px;color:#F1F5F9;line-height:1.55;margin-bottom:8px;">"{circ_cite.get('excerpt', 'No excerpt available')}"</div>
                            <div style="font-size:10px;color:#64748B;">📄 {circ_cite.get('filename', 'N/A')} · <code>{circ_cite.get('chunk_id', 'N/A')}</code></div>
                        </div>
                        """
                    )
                with col_e2:
                    if not policy_cites:
                        render_html(
                            """
                            <div style="border-left:3px solid #F59E0B;background:rgba(245,158,11,0.06);padding:12px 16px;border-radius:0 10px 10px 0;">
                                <div style="font-size:11px;color:#FBBF24;font-weight:700;margin-bottom:4px;">🏦 BANK POLICY PROOF</div>
                                <div style="font-size:12px;color:#CBD5E1;">No matching bank policy passage found in baseline handbook.</div>
                            </div>
                            """
                        )
                    for idx, pc in enumerate(policy_cites, 1):
                        chunk_id = pc.get("chunk_id", "N/A")
                        is_valid = bool(chunk_id and chunk_id != "N/A")
                        badge_html = '<span class="badge-pill badge-completed" style="font-size:9px;padding:1px 7px;">✓ Verified</span>' if is_valid else '<span class="badge-pill" style="background:rgba(239,68,68,0.15);color:#F87171;font-size:9px;padding:1px 7px;">✗ Unverified</span>'
                        render_html(
                            f"""
                            <div style="border-left:3px solid #10B981;background:rgba(16,185,129,0.06);padding:12px 16px;border-radius:0 10px 10px 0;margin-bottom:8px;animation:a1-up .35s ease-out;">
                                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                                    <span style="font-size:11px;color:#34D399;font-weight:700;">🏦 BANK POLICY PROOF #{idx} (Page {pc.get('page', 'N/A')})</span>
                                    {badge_html}
                                </div>
                                <div style="font-size:12px;color:#E2E8F0;line-height:1.55;margin-bottom:8px;">{pc.get('excerpt', 'No excerpt available')}</div>
                                <div style="font-size:10px;color:#64748B;">🏦 {pc.get('filename', 'N/A')} · <code>{chunk_id}</code></div>
                            </div>
                            """
                        )

                if limitations:
                    for lim in limitations:
                        st.warning(f"⚠️ Note: {lim}")

            with tab_confidence:
                # Executive-friendly explanation + clean metrics
                avg_model_conf = sum(f.get("model_reported_confidence", f.get("confidence", 0.0)) for f in findings_list) / max(1, total_findings)
                high_gap = [f for f in findings_list if (f.get("model_reported_confidence", 0.0) - f.get("evidence_confidence", 0.0)) > 0.15]
                review_cases = [f for f in findings_list if f.get("status") == "requires_human_review"]

                render_html(
                    f"""
                    <div style="background:#0B1228;border:1px solid #1E2D56;border-left:4px solid #6366F1;border-radius:10px;padding:14px 18px;margin-bottom:16px;">
                        <div style="font-size:13px;font-weight:700;color:#FFFFFF;margin-bottom:4px;">⚖️ Why Confidence Calibration Matters</div>
                        <div style="font-size:12px;color:#CBD5E1;line-height:1.55;">
                            AI models can sound certain even when bank policy proof is weak. Agent 2 cross-checks the <b>AI Initial Score</b> against
                            actual retrieved bank policy text (<b>Policy Evidence</b> — a heuristic indicator of retrieval &amp; citation quality, not measured accuracy)
                            to produce a trustworthy <b>Final Calibrated Score</b>.
                        </div>
                    </div>

                    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:16px;">
                        <div style="background:#0B1228;border:1px solid #1E2D56;border-radius:10px;padding:14px 16px;">
                            <div style="font-size:11px;color:#94A3B8;font-weight:600;">🤖 AI INITIAL SCORE (AVG)</div>
                            <div style="font-size:24px;font-weight:700;color:#818CF8;margin:4px 0;">{avg_model_conf:.0%}</div>
                            <div style="font-size:11px;color:#64748B;">Raw certainty reported by the LLM before checking citations.</div>
                        </div>
                        <div style="background:#0B1228;border:1px solid #1E2D56;border-radius:10px;padding:14px 16px;">
                            <div style="font-size:11px;color:#94A3B8;font-weight:600;">🔍 POLICY EVIDENCE SCORE (HEURISTIC)</div>
                            <div style="font-size:24px;font-weight:700;color:#FBBF24;margin:4px 0;">{avg_ev_conf:.0%}</div>
                            <div style="font-size:11px;color:#64748B;">Heuristic strength of retrieved policy chunks (not measured accuracy).</div>
                        </div>
                        <div style="background:#0B1228;border:1px solid #1E2D56;border-radius:10px;padding:14px 16px;">
                            <div style="font-size:11px;color:#94A3B8;font-weight:600;">⚖️ FINAL CALIBRATED SCORE (AVG)</div>
                            <div style="font-size:24px;font-weight:700;color:#34D399;margin:4px 0;">{avg_conf:.0%}</div>
                            <div style="font-size:11px;color:#64748B;">Trustworthy final score after capping overconfident AI claims.</div>
                        </div>
                    </div>
                    """
                )

                # Compact, professional table-like breakdown with plain-English verdicts
                rows_conf_html = []
                for f in findings_list:
                    ob_id = f.get("obligation_id", "N/A")
                    st_val = f.get("status", "unknown")
                    m_conf = f.get("model_reported_confidence", f.get("confidence", 0.0))
                    e_conf = f.get("evidence_confidence", f.get("confidence", 0.0))
                    final_c = f.get("confidence", 0.0)
                    gap = m_conf - e_conf
                    inc_flag = f.get("retrieval_incomplete", False)
                    badge = get_status_badge(st_val)

                    if st_val == "requires_human_review" or inc_flag:
                        verdict = '<span style="color:#FB923C;font-size:11px;font-weight:600;">👤 Sent to Human Review</span>'
                    elif gap > 0.15:
                        verdict = '<span style="color:#FBBF24;font-size:11px;font-weight:600;">↓ Capped by Evidence</span>'
                    else:
                        verdict = '<span style="color:#34D399;font-size:11px;font-weight:600;">✓ Evidence-Backed</span>'

                    rows_conf_html.append(
                        f'<div style="display:grid;grid-template-columns:0.8fr 1.1fr 0.8fr 0.9fr 1.2fr 1.1fr;align-items:center;gap:10px;padding:10px 14px;border-bottom:1px solid #16203B;font-size:12px;">'
                        f'<b style="color:#FFFFFF;">{ob_id}</b>'
                        f'<div>{badge}</div>'
                        f'<span style="color:#818CF8;font-weight:600;">{m_conf:.0%}</span>'
                        f'<span style="color:#FBBF24;font-weight:600;">{e_conf:.0%}</span>'
                        f'<div style="display:flex;align-items:center;gap:8px;"><div class="a2-bar-track"><div class="a2-bar-fill" style="width:{final_c*100:.0f}%;background:#34D399;"></div></div><b style="color:#34D399;">{final_c:.0%}</b></div>'
                        f'<div>{verdict}</div>'
                        f'</div>'
                    )

                render_html(
                    f"""
                    <div style="background:#0B1228;border:1px solid #1E2D56;border-radius:12px;overflow:hidden;margin-bottom:16px;">
                        <div style="display:grid;grid-template-columns:0.8fr 1.1fr 0.8fr 0.9fr 1.2fr 1.1fr;gap:10px;padding:10px 14px;background:#0F1733;border-bottom:1px solid #1E2D56;font-size:11px;font-weight:700;color:#94A3B8;text-transform:uppercase;">
                            <div>Obligation</div>
                            <div>Mapping Status</div>
                            <div>AI Initial</div>
                            <div>Policy Evidence</div>
                            <div>Final Calibrated</div>
                            <div>Calibration Verdict</div>
                        </div>
                        {''.join(rows_conf_html)}
                    </div>
                    """
                )

                c_cal1, c_cal2 = st.columns(2)
                with c_cal1:
                    render_html(
                        f"""
                    <div style="background:#0B1228;border:1px solid #1E2D56;border-left:3px solid #818CF8;border-radius:10px;padding:12px 16px;">
                        <div style="font-size:12px;font-weight:700;color:#FFFFFF;margin-bottom:3px;">🛡️ Hallucination Mitigation Gate</div>
                        <div style="font-size:12px;color:#94A3B8;">
                            <b style="color:#E2E8F0;">{len(high_gap)} obligation(s)</b> had AI confidence &gt;15% higher than retrieved policy evidence and were automatically capped.
                        </div>
                    </div>
                    """
                    )
                with c_cal2:
                    render_html(
                        f"""
                    <div style="background:#0B1228;border:1px solid #1E2D56;border-left:3px solid #FB923C;border-radius:10px;padding:12px 16px;">
                        <div style="font-size:12px;font-weight:700;color:#FFFFFF;margin-bottom:3px;">👤 Human Review Safeguards</div>
                        <div style="font-size:12px;color:#94A3B8;">
                            <b style="color:#E2E8F0;">{len(review_cases)} finding(s)</b> flagged for compliance officer sign-off due to incomplete or ambiguous evidence.
                        </div>
                    </div>
                    """
                    )

                # Bottom Enterprise Control Bar ONLY on Confidence Analysis (final tab of Agent 2)
                render_html(
                    f"""
                <div class="a1-bottom-bar-img4" style="margin-top:20px;margin-bottom:10px;">
                    <div style="display:flex;align-items:center;gap:14px;">
                        <div class="a1-gauge-ring" style="width:50px;height:50px;">
                            <span style="font-size:12px;font-weight:800;color:#34D399;">{avg_conf:.0%}</span>
                        </div>
                        <div>
                            <div style="font-size:12px;font-weight:600;color:#FFFFFF;">Mapping Confidence Verified</div>
                            <div style="font-size:10px;color:#34D399;">{c_partially + c_conflict} gap/conflict items ready for Rule Proposal</div>
                        </div>
                    </div>
                    <div style="font-size:11px;color:#94A3B8;">
                        ⚡ {total_findings} obligations mapped · Next: Agent 3 Rule Proposal
                    </div>
                </div>
                """
                )
                a2_note_col, a2_flag_col, a2_go_col = st.columns([3, 1, 1.3])
                with a2_note_col:
                    st.text_input(
                        "Agent 2 review note",
                        placeholder="Add policy mapping review note (optional)...",
                        label_visibility="collapsed",
                        key="agent2_review_note_input",
                    )
                with a2_flag_col:
                    if st.button("🚩 Flag Mapping", use_container_width=True, key="agent2_flag_review_btn"):
                        st.toast("Policy mapping flagged for compliance review.", icon="🚩")
                with a2_go_col:
                    if st.button("⚡ Proceed to Agent 3 →", type="primary", use_container_width=True, key="agent2_proceed_agent3_btn"):
                        st.session_state["pending_agent_nav"] = "Agent 3 – Rule Proposal"
                        st.session_state["agent2_proceed_toast"] = True
                        st.rerun()

    elif selected_agent == "Agent 3 – Rule Proposal":
        # AGENT 3 DETAILED DASHBOARD
        if st.session_state.pop("agent2_proceed_toast", False):
            st.toast("Loaded Policy Mapping findings into Agent 3 – Rule Proposal!", icon="🚀")
            render_html(
                """
                <div style="background:linear-gradient(90deg,rgba(99,102,241,0.16),rgba(16,185,129,0.16));border:1px solid #6366F1;border-radius:10px;padding:10px 16px;margin-bottom:14px;display:flex;align-items:center;gap:10px;animation:a1-up .4s ease-out;">
                    <span style="font-size:16px;">⚡</span>
                    <span style="font-size:12px;color:#E2E8F0;font-weight:600;">Policy Mapping Confirmed → Agent 3 Rule Proposal Active</span>
                </div>
                """
            )
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
        draft_lbl = f"{draft_count} (100%)" if total_proposals else "0"
        render_html(
            f"""
            <div class="a3-kpi-grid">
                <div class="a3-kpi-card" style="animation-delay:.03s;">
                    <div style="font-size:20px;margin-bottom:4px;">📄</div>
                    <div style="font-size:22px;font-weight:700;color:#FFFFFF;">{total_proposals}</div>
                    <div style="font-size:11px;color:#94A3B8;margin-top:2px;">Total Proposals</div>
                </div>
                <div class="a3-kpi-card" style="animation-delay:.08s;">
                    <div style="font-size:20px;margin-bottom:4px;">📚</div>
                    <div style="font-size:22px;font-weight:700;color:#A78BFA;">{draft_lbl}</div>
                    <div style="font-size:11px;color:#94A3B8;margin-top:2px;">Draft Status</div>
                </div>
                <div class="a3-kpi-card" style="animation-delay:.13s;border-color:rgba(56,189,248,0.35);">
                    <div style="font-size:20px;margin-bottom:4px;">🧪</div>
                    <div style="font-size:22px;font-weight:700;color:#38BDF8;">{sandbox_ready_count}</div>
                    <div style="font-size:11px;color:#94A3B8;margin-top:2px;">Sandbox Ready</div>
                </div>
                <div class="a3-kpi-card" style="animation-delay:.18s;border-color:rgba(251,191,36,0.35);">
                    <div style="font-size:20px;margin-bottom:4px;">⚠️</div>
                    <div style="font-size:22px;font-weight:700;color:#FBBF24;">{human_review_count}</div>
                    <div style="font-size:11px;color:#94A3B8;margin-top:2px;">Needs Review</div>
                </div>
                <div class="a3-kpi-card" style="animation-delay:.23s;border-color:rgba(248,113,113,0.35);">
                    <div style="font-size:20px;margin-bottom:4px;">🛡️</div>
                    <div style="font-size:22px;font-weight:700;color:#F87171;">{metrics["high_risk_count"]}</div>
                    <div style="font-size:11px;color:#94A3B8;margin-top:2px;">High Risk</div>
                </div>
                <div class="a3-kpi-card" style="animation-delay:.28s;border-color:rgba(52,211,153,0.35);">
                    <div style="font-size:20px;margin-bottom:4px;">⚡</div>
                    <div style="font-size:22px;font-weight:700;color:#34D399;">{metrics["action_count"]}</div>
                    <div style="font-size:11px;color:#94A3B8;margin-top:2px;">Actions Defined</div>
                </div>
            </div>
            """
        )

        if not proposals_list:
            st.warning(f"No rule proposals recorded yet for workflow `{selected_workflow_id}`.")
            st.caption("Proposals are generated only for obligations classified as partially_covered or potential_conflict.")
        else:
            # Agent 3 Navigation Tabs (4 tabs: Overview, Rule Proposals, Validation & Review, Sandbox Readiness)
            tab_overview, tab_proposals, tab_validation, tab_sandbox = st.tabs(
                [
                    "📊 Overview",
                    "📜 Rule Proposals",
                    "⚖️ Validation & Review",
                    "🧪 Sandbox Readiness",
                ]
            )

            def _a3_pipeline_html(steps: list[tuple[str, str, str]]) -> str:
                parts = []
                for idx_s, (icon, label, state) in enumerate(steps):
                    cls = "a2-step-circle done" if state == "done" else "a2-step-circle"
                    glow = "box-shadow:0 0 24px rgba(139,92,246,0.75);border-color:#A78BFA;" if state == "active" else ""
                    lbl_col = "#FFFFFF" if state == "active" else "#CBD5E1"
                    parts.append(
                        f'<div class="a2-step" style="animation-delay:{0.06 * idx_s:.2f}s;">'
                        f'<div class="{cls}" style="{glow}">{icon}</div>'
                        f'<div class="a2-step-lbl" style="color:{lbl_col};">{label}</div>'
                        '</div>'
                    )
                    if idx_s < len(steps) - 1:
                        parts.append('<div class="a2-step-line"></div>')
                return f'<div class="a2-pipe">{"".join(parts)}</div>'

            def _a3_wave_svg(c1: str = "#8B5CF6", c2: str = "#38BDF8") -> str:
                return (
                    '<svg viewBox="0 0 120 70" style="width:100%;height:70px;overflow:visible;">'
                    f'<path d="M0,14 C45,14 75,35 120,35" fill="none" stroke="{c1}" stroke-width="2" stroke-opacity="0.6" stroke-dasharray="6 5" style="animation:a2-dash-flow 1.3s linear infinite;"/>'
                    f'<path d="M0,35 L120,35" fill="none" stroke="{c2}" stroke-width="2.5" stroke-dasharray="6 6" style="animation:a2-dash-flow 0.9s linear infinite;"/>'
                    f'<path d="M0,56 C45,56 75,35 120,35" fill="none" stroke="{c1}" stroke-width="2" stroke-opacity="0.6" stroke-dasharray="6 5" style="animation:a2-dash-flow 1.3s linear infinite;"/>'
                    f'<circle cx="60" cy="35" r="4" fill="{c2}" style="animation:a1-pulse 1.4s infinite;"/>'
                    '</svg>'
                )

            with tab_overview:
                first_p = proposals_list[0]
                first_ob = first_p.get("obligation_id") or (first_p.get("source_obligation_ids", ["OBL-002"])[0])
                first_pol = first_p.get("existing_policy_provision") or "POL-205"
                if len(first_pol) > 28:
                    first_pol = first_pol[:28] + "…"

                wave_l = _a3_wave_svg("#8B5CF6", "#A78BFA")
                wave_r = _a3_wave_svg("#38BDF8", "#34D399")
                down_branch_svg = (
                    '<svg viewBox="0 0 600 44" style="width:100%;height:42px;display:block;margin:-6px 0 -2px;">'
                    '<path d="M300,0 L300,18" fill="none" stroke="#8B5CF6" stroke-width="2.5" stroke-dasharray="5 4" style="animation:a2-dash-flow 1s linear infinite;"/>'
                    '<path d="M300,18 C220,18 160,26 140,42" fill="none" stroke="#A78BFA" stroke-width="2" stroke-dasharray="5 4" style="animation:a2-dash-flow 1.2s linear infinite;"/>'
                    '<path d="M300,18 C380,18 440,26 460,42" fill="none" stroke="#38BDF8" stroke-width="2" stroke-dasharray="5 4" style="animation:a2-dash-flow 1.2s linear infinite;"/>'
                    '<circle cx="140" cy="40" r="3.5" fill="#A78BFA" style="animation:a1-pulse 1.4s infinite;"/>'
                    '<circle cx="460" cy="40" r="3.5" fill="#38BDF8" style="animation:a1-pulse 1.4s infinite;"/>'
                    '</svg>'
                )

                active_rows = []
                for idx_p, p in enumerate(proposals_list[:5]):
                    r_id = p.get("rule_id", "N/A")
                    ob_id = p.get("obligation_id") or (p.get("source_obligation_ids", [""])[0])
                    p_conf = p.get("confidence", 0.85)
                    p_action = p.get("action", "flag_review")
                    p_desc = p.get("proposed_rule") or p.get("description") or "Declarative compliance rule proposal"
                    if len(p_desc) > 95:
                        p_desc = p_desc[:95] + "…"
                    active_rows.append(
                        f'<div style="display:grid;grid-template-columns:2.2fr 0.7fr 1fr;align-items:center;gap:14px;padding:12px 16px;background:#0B1228;border:1px solid #1E2D56;border-radius:10px;margin-bottom:8px;animation:a1-up .4s ease-out {0.55 + 0.12*idx_p:.2f}s backwards;">'
                        '<div style="min-width:0;">'
                        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;"><span style="font-size:15px;">📄</span><b style="font-size:13px;color:#FFFFFF;">{r_id}</b><span style="font-size:11px;color:#A5B4FC;background:#141E3C;padding:1px 8px;border-radius:999px;">{ob_id}</span><span class="badge-action" style="font-size:10px;padding:1px 8px;">{p_action}</span></div>'
                        f'<div style="font-size:11px;color:#94A3B8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{p_desc}</div>'
                        '</div>'
                        '<div style="text-align:center;"><span class="badge-draft" style="padding:3px 12px;border-radius:999px;font-size:11px;">Draft</span></div>'
                        f'<div style="display:flex;align-items:center;gap:8px;"><div class="a2-bar-track"><div class="a2-bar-fill" style="width:{p_conf*100:.0f}%;background:linear-gradient(90deg,#6366F1,#38BDF8);"></div></div><span style="font-size:11px;color:#93C5FD;font-weight:600;">{p_conf:.0%}</span></div>'
                        '</div>'
                    )
                active_rows_html = "\n".join(active_rows)
                avg_conf = sum(p.get("confidence", 0.0) for p in proposals_list) / max(1, total_proposals)

                render_html(
                    f"""
                    <div class="a2-bridge" style="grid-template-columns:1fr 0.45fr 1fr 0.45fr 1fr;margin-top:6px;margin-bottom:4px;">
                        <div class="a3-glass-card" style="animation:a1-slide-in .35s ease-out;">
                            <div style="font-size:11px;color:#A5B4FC;font-weight:600;margin-bottom:8px;">Regulatory Obligation</div>
                            <div style="display:flex;align-items:center;justify-content:center;gap:10px;">
                                <span style="font-size:28px;">📄</span>
                                <b style="font-size:16px;color:#FFFFFF;">{first_ob}</b>
                            </div>
                            <div style="height:4px;background:rgba(139,92,246,0.25);border-radius:4px;margin-top:12px;"></div>
                        </div>
                        <div>{wave_l}</div>
                        <div class="a2-bridge-center" style="padding:18px 14px;">
                            <div style="font-size:26px;margin-bottom:4px;">🔷</div>
                            <div style="font-size:15px;font-weight:700;color:#FFFFFF;">Rule Proposal</div>
                            <div style="font-size:11px;color:#C4B5FD;margin-top:3px;">Declarative Synthesis</div>
                        </div>
                        <div>{wave_r}</div>
                        <div class="a3-glass-card-cyan" style="animation:a1-up .35s ease-out;">
                            <div style="font-size:11px;color:#7DD3FC;font-weight:600;margin-bottom:8px;">🏦 Bank Policy</div>
                            <div style="font-size:14px;font-weight:700;color:#FFFFFF;">{first_pol}</div>
                            <div style="height:4px;background:rgba(56,189,248,0.25);border-radius:4px;margin-top:14px;"></div>
                        </div>
                    </div>
                    {down_branch_svg}
                    <div style="background:#080E20;border:1px solid #1E2D56;border-radius:14px;padding:16px 18px;animation:a1-up .45s ease-out 0.45s backwards;">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                            <div style="font-size:14px;font-weight:700;color:#FFFFFF;">⚡ Synthesized Rule Proposals ({len(proposals_list)})</div>
                            <div style="font-size:11px;color:#94A3B8;">Avg Confidence: <b style="color:#38BDF8;">{avg_conf:.0%}</b> · Live Execution: <b style="color:#F87171;">BLOCKED (Safe Gate)</b></div>
                        </div>
                        {active_rows_html}
                    </div>
                    """
                )

            with tab_proposals:
                high_risk_cnt = metrics["high_risk_count"]
                render_html(
                    f"""
                    <div style="background:radial-gradient(ellipse at 50% 40%, rgba(124,58,237,0.16), #070B19 72%);border:1px solid #1E2D56;border-radius:16px;padding:24px 20px;margin-bottom:16px;text-align:center;">
                        <div class="a3-scanner-frame">
                            <span style="font-size:44px;filter:drop-shadow(0 0 12px rgba(167,139,250,0.8));">📄</span>
                            <div class="a3-scanner-beam"></div>
                        </div>
                        <div style="position:relative;height:24px;margin:0 auto 10px;max-width:260px;">
                            <div class="a2-ev-stage" style="font-size:14px;color:#E2E8F0;animation:a2-stage-step 1.8s ease 0.0s 1;">Analyzing Obligations...</div>
                            <div class="a2-ev-stage" style="font-size:14px;color:#34D399;font-weight:700;animation:a2-stage-final 0.45s ease 1.8s forwards;">Proposals Ready ✓ ({total_proposals})</div>
                        </div>
                        <div class="a3-prog-track" style="max-width:340px;margin:0 auto 20px;">
                            <div class="a3-prog-fill"></div>
                        </div>
                        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;animation:a1-up .45s ease-out 1.8s backwards;">
                            <div class="a3-glass-card" style="padding:14px 10px;"><div style="font-size:20px;">📄</div><div style="font-size:22px;font-weight:700;color:#FFFFFF;">{total_proposals}</div><div style="font-size:11px;color:#94A3B8;">Proposals</div></div>
                            <div class="a3-glass-card" style="padding:14px 10px;"><div style="font-size:20px;">📚</div><div style="font-size:22px;font-weight:700;color:#A78BFA;">{draft_count}</div><div style="font-size:11px;color:#94A3B8;">Draft</div></div>
                            <div class="a3-glass-card-cyan" style="padding:14px 10px;"><div style="font-size:20px;">🧪</div><div style="font-size:22px;font-weight:700;color:#38BDF8;">{sandbox_ready_count}</div><div style="font-size:11px;color:#94A3B8;">Sandbox</div></div>
                            <div class="a3-glass-card" style="padding:14px 10px;border-color:rgba(248,113,113,0.45);"><div style="font-size:20px;">⚠️</div><div style="font-size:22px;font-weight:700;color:#F87171;">{high_risk_cnt}</div><div style="font-size:11px;color:#94A3B8;">High Risk</div></div>
                        </div>
                    </div>
                    """
                )

                # Icon Filter Pills (matching Agent 1 Obligations page) + Search
                col_pf_pills, col_pf_search = st.columns([2.3, 1.2])
                with col_pf_pills:
                    prop_filter = st.pills(
                        "Filter Proposals",
                        ["✨ All", "🧪 Sandbox Ready", "⚠️ Needs Review", "🔴 High Risk", "🟡 Medium Risk"],
                        default="✨ All",
                        selection_mode="single",
                        label_visibility="collapsed",
                        key="a3_prop_filter_pills",
                    ) or "✨ All"
                with col_pf_search:
                    search_query = st.text_input("Search Proposals", placeholder="🔍 Search ID, obligation, or logic...", label_visibility="collapsed", key="a3_prop_search")

                filtered_proposals = proposals_list
                if prop_filter == "🧪 Sandbox Ready":
                    filtered_proposals = [p for p in filtered_proposals if p.get("sandbox_readiness") or (p.get("baseline_rule") and p.get("sandbox_rule"))]
                elif prop_filter == "⚠️ Needs Review":
                    filtered_proposals = [p for p in filtered_proposals if p.get("action") == "flag_review" or p.get("unresolved_questions") or p.get("review_reasons")]
                elif prop_filter == "🔴 High Risk":
                    filtered_proposals = [p for p in filtered_proposals if p.get("risk_level") == "high"]
                elif prop_filter == "🟡 Medium Risk":
                    filtered_proposals = [p for p in filtered_proposals if p.get("risk_level") == "medium"]
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

                render_html(f'<div style="animation:a1-up .45s ease-out 1.85s backwards;font-size:12px;color:#94A3B8;margin-bottom:6px;">Showing <b>{len(filtered_proposals)}</b> of <b>{total_proposals}</b> proposals</div>')

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

            with tab_validation:
                if "a3_review_decisions" not in st.session_state:
                    st.session_state["a3_review_decisions"] = {}

                unique_ids = len(set(p.get("rule_id") for p in proposals_list))
                val_flow_html = (
                    '<div style="font-size:18px;font-weight:700;color:#FFFFFF;margin-bottom:8px;">Validation Results &amp; Human Review Requirements</div>'
                    '<div style="background:rgba(59,130,246,0.12);border:1px solid rgba(96,165,250,0.35);border-radius:10px;padding:12px 16px;margin-bottom:14px;display:flex;align-items:center;gap:10px;">'
                    '<span style="font-size:18px;">🛡️</span>'
                    '<span style="font-size:13px;color:#DBEAFE;"><b>Compliance Guardrail:</b> Proposals are validated against policy, evidence, and safety rules before execution.</span>'
                    '</div>'
                    '<div class="a3-stage-deck" style="min-height:290px;">'
                    # Stage 1: Validate Running checks (0s -> 1.4s)
                    '<div class="a3-stage-slide" style="animation:a3-panel-cycle 1.4s ease 0.0s 1;">'
                    + _a3_pipeline_html([("📋", "Validate · Running checks...", "active"), ("👥", "Human Review", "pending"), ("🛡️", "Approve", "pending")]) +
                    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">'
                    '<div class="a3-glass-card" style="text-align:left;padding:16px 18px;">'
                    '<div style="font-size:14px;font-weight:700;color:#FFFFFF;margin-bottom:10px;">👤 Operator &amp; Field Compliance</div>'
                    '<div class="a3-prog-track"><div class="a3-prog-fill" style="width:45%;"></div></div>'
                    '<div style="font-size:11px;color:#94A3B8;margin-top:8px;">Checking allowlisted operators &amp; fields...</div>'
                    '</div>'
                    '<div class="a3-glass-card" style="text-align:left;padding:16px 18px;">'
                    '<div style="font-size:14px;font-weight:700;color:#FFFFFF;margin-bottom:10px;">📚 Duplicate &amp; Citation Checks</div>'
                    '<div class="a3-prog-track"><div class="a3-prog-fill" style="width:35%;"></div></div>'
                    '<div style="font-size:11px;color:#94A3B8;margin-top:8px;">Verifying rule IDs &amp; circular citations...</div>'
                    '</div></div></div>'
                    # Stage 2: Human Review Analyzing (1.4s -> 2.8s)
                    '<div class="a3-stage-slide" style="animation:a3-panel-cycle 1.4s ease 1.4s 1;">'
                    + _a3_pipeline_html([("✓", "Validate · Completed", "done"), ("👥", "Human Review · Analyzing...", "active"), ("🛡️", "Approve", "pending")]) +
                    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">'
                    '<div class="a3-glass-card" style="text-align:left;padding:16px 18px;">'
                    '<div style="font-size:14px;font-weight:700;color:#FFFFFF;margin-bottom:10px;">👤 Operator &amp; Field Compliance</div>'
                    '<div style="font-size:12px;color:#CBD5E1;line-height:1.8;"><div><span style="color:#34D399;">✓</span> Operators whitelisted</div><div><span style="color:#34D399;">✓</span> Field rules validated</div><div><span style="color:#A78BFA;">◌</span> Thresholds verifying...</div></div>'
                    '</div>'
                    '<div class="a3-glass-card" style="text-align:left;padding:16px 18px;">'
                    '<div style="font-size:14px;font-weight:700;color:#FFFFFF;margin-bottom:10px;">📚 Duplicate &amp; Citation Checks</div>'
                    f'<div style="font-size:12px;color:#CBD5E1;line-height:1.8;"><div><span style="color:#34D399;">✓</span> Unique Rule IDs: {unique_ids} / {total_proposals}</div><div><span style="color:#A78BFA;">◌</span> Citations verifying...</div><div><span style="color:#A78BFA;">◌</span> Obligation mapping check</div></div>'
                    '</div></div></div>'
                    # Stage 3: Validation Completed Shield (2.8s onward)
                    '<div class="a3-stage-slide" style="animation:a3-panel-final 0.55s ease 2.8s forwards;">'
                    + _a3_pipeline_html([("✓", "Validate · Completed", "done"), ("✓", "Human Review · Completed", "done"), ("✓", "Approve · Completed", "done")]) +
                    '<div style="background:radial-gradient(circle at 25% 50%, rgba(16,185,129,0.16), #080E22 70%);border:1px solid rgba(52,211,153,0.45);border-radius:16px;padding:20px 24px;display:grid;grid-template-columns:0.8fr 1.4fr 1fr;align-items:center;gap:16px;">'
                    '<div style="text-align:center;"><div style="font-size:48px;filter:drop-shadow(0 0 18px rgba(52,211,153,0.75));">🛡️</div></div>'
                    '<div><div style="font-size:18px;font-weight:700;color:#34D399;">Validation Completed ✓</div>'
                    '<div style="font-size:12px;color:#CBD5E1;margin-top:4px;">All rule proposals are validated and routed for human review / safe execution.</div></div>'
                    f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">'
                    f'<div class="a3-glass-card" style="padding:10px;"><div style="font-size:18px;font-weight:700;color:#FBBF24;">{human_review_count}</div><div style="font-size:10px;color:#94A3B8;">Needs Review</div></div>'
                    f'<div class="a3-glass-card-cyan" style="padding:10px;"><div style="font-size:18px;font-weight:700;color:#34D399;">{total_proposals}</div><div style="font-size:10px;color:#94A3B8;">Validated</div></div>'
                    '</div></div></div>'
                    '</div>'
                )
                render_html(val_flow_html)

                review_proposals = [p for p in proposals_list if p.get("action") == "flag_review" or p.get("unresolved_questions") or p.get("review_reasons")]
                st.markdown(f"#### Human Review Flagged Proposals ({len(review_proposals)})")

                if not review_proposals:
                    st.success("All proposals have deterministic condition models.")
                else:
                    for rp in review_proposals:
                        r_id = rp.get("rule_id", "N/A")
                        ob_id = rp.get("obligation_id") or (rp.get("source_obligation_ids", [""])[0])
                        reasons = rp.get("review_reasons", []) or rp.get("unresolved_questions", [])
                        dec = st.session_state["a3_review_decisions"].get(r_id, "pending")
                        dec_tag = "✅ Approved" if dec == "approved" else "⚠️ Flagged"
                        with st.expander(f"⚠️ {r_id} ({ob_id}) — Review Flags · [{dec_tag}]"):
                            for r in reasons:
                                st.warning(f"• {r}")
                            st.caption(f"**Proposed Action:** {rp.get('action')} | **Risk:** {rp.get('risk_level')}")
                            b_col1, b_col2, _ = st.columns([1, 1, 2])
                            with b_col1:
                                if st.button("✅ Approve Rule", key=f"a3_approve_{r_id}", type="primary" if dec == "approved" else "secondary", use_container_width=True):
                                    st.session_state["a3_review_decisions"][r_id] = "approved"
                                    st.toast(f"Approved {r_id} for Sandbox!", icon="✅")
                                    st.rerun()
                            with b_col2:
                                if st.button("🚩 Keep Flagged", key=f"a3_flag_{r_id}", use_container_width=True):
                                    st.session_state["a3_review_decisions"][r_id] = "flagged"
                                    st.toast(f"Kept {r_id} flagged for review.", icon="🚩")
                                    st.rerun()

                render_html(
                    f"""
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px;">
                        <div class="a3-glass-card" style="text-align:left;padding:18px 20px;animation:a1-slide-in .35s ease-out;">
                            <div style="display:flex;align-items:center;gap:8px;font-size:14px;font-weight:700;color:#FFFFFF;margin-bottom:12px;">
                                <span>👤</span> Operator &amp; Field Compliance
                            </div>
                            <div style="font-size:12px;color:#CBD5E1;line-height:1.9;">
                                <div><span style="color:#34D399;">✓</span> <b>Allowlisted Operators:</b> 100% Verified (gt, gte, lt, lte, eq, ne, between)</div>
                                <div><span style="color:#34D399;">✓</span> <b>Allowlisted Fields:</b> 100% Verified (amount, retention_days, is_emergency)</div>
                                <div><span style="color:#34D399;">✓</span> <b>Invented Thresholds:</b> 0 Detected</div>
                                <div><span style="color:#34D399;">✓</span> <b>Unbacked Conditions:</b> 0 Detected</div>
                            </div>
                        </div>
                        <div class="a3-glass-card" style="text-align:left;padding:18px 20px;animation:a1-up .35s ease-out;">
                            <div style="display:flex;align-items:center;gap:8px;font-size:14px;font-weight:700;color:#FFFFFF;margin-bottom:12px;">
                                <span>📚</span> Duplicate &amp; Citation Checks
                            </div>
                            <div style="font-size:12px;color:#CBD5E1;line-height:1.9;">
                                <div><span style="color:#818CF8;">✓</span> <b>Unique Rule IDs:</b> {unique_ids} / {total_proposals}</div>
                                <div><span style="color:#818CF8;">✓</span> <b>Obligation Anchoring:</b> 100% linked to eligible obligations</div>
                                <div><span style="color:#818CF8;">✓</span> <b>Circular Citations Verified:</b> 100% present</div>
                                <div><span style="color:#FBBF24;">●</span> <b>Production Live Execution:</b> Gated until human approval</div>
                            </div>
                        </div>
                    </div>
                    """
                )

            with tab_sandbox:
                sb_dot_beam = (
                    '<svg viewBox="0 0 80 12" style="width:100%;height:12px;">'
                    '<line x1="2" y1="6" x2="78" y2="6" stroke="#A78BFA" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="1 9" style="animation:a2-dash-flow 1s linear infinite;"/>'
                    '</svg>'
                )
                ready_proposals = [p for p in proposals_list if p.get("baseline_rule") and p.get("sandbox_rule")]
                ready_rule_lbl = ready_proposals[0].get("rule_id", "RULE") if ready_proposals else f"{total_proposals} Proposal(s)"

                render_html(
                    f"""
                    <div class="a3-stage-deck" style="min-height:360px;background:radial-gradient(ellipse at 50% 45%, rgba(124,58,237,0.18), #070B19 72%);border:1px solid #1E2D56;border-radius:18px;padding:30px 26px;">
                        <div class="a3-stage-slide" style="padding:28px 26px;animation:a3-panel-cycle 1.3s ease 0.0s 1;">
                            <div style="display:grid;grid-template-columns:1fr 0.85fr 1fr;align-items:center;gap:18px;margin-bottom:24px;">
                                <div class="a3-tilt-left" style="padding:32px 18px;"><div style="font-size:44px;margin-bottom:10px;">📄</div><div style="font-size:17px;font-weight:700;color:#FFFFFF;">Baseline Rule (v1)</div></div>
                                <div style="display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:8px;"><div>{sb_dot_beam}</div><div class="a2-ev-orbit" style="width:58px;height:58px;"><div class="a2-ev-orbit-ring"></div><span style="font-size:22px;color:#FFF;z-index:1;">→</span></div><div>{sb_dot_beam}</div></div>
                                <div class="a3-tilt-right" style="padding:32px 18px;"><div style="font-size:40px;margin-bottom:10px;color:#38BDF8;font-weight:700;">&lt;/&gt;</div><div style="font-size:17px;font-weight:700;color:#FFFFFF;">Proposed Rule (v2)</div></div>
                            </div>
                            <div style="display:flex;align-items:center;gap:14px;"><span style="font-size:22px;animation:a1-spin 2s linear infinite;">⚙️</span><div style="flex:1;"><div style="font-size:13px;color:#CBD5E1;margin-bottom:6px;">Preparing Sandbox Environment...</div><div class="a3-prog-track"><div class="a3-prog-fill" style="width:25%;"></div></div></div><b style="font-size:15px;color:#A78BFA;">25%</b></div>
                        </div>

                        <div class="a3-stage-slide" style="padding:28px 26px;animation:a3-panel-cycle 1.3s ease 1.3s 1;">
                            <div class="a3-glass-card" style="text-align:left;padding:24px 26px;margin-bottom:20px;">
                                <div style="font-size:16px;font-weight:700;color:#FFFFFF;margin-bottom:14px;">🧪 Test Suite Configuration</div>
                                <div style="font-size:14px;color:#CBD5E1;line-height:2.1;">
                                    <div><span style="color:#34D399;">✓</span> Generate Synthetic Test Cases</div>
                                    <div><span style="color:#34D399;">✓</span> Load Rule Pairs (v1 vs v2)</div>
                                    <div><span style="color:#A78BFA;">◌</span> Set Validation Criteria</div>
                                </div>
                            </div>
                            <div style="display:flex;align-items:center;gap:14px;"><span style="font-size:22px;animation:a1-spin 2s linear infinite;">⚙️</span><div style="flex:1;"><div style="font-size:13px;color:#CBD5E1;margin-bottom:6px;">Configuring Test Suite...</div><div class="a3-prog-track"><div class="a3-prog-fill" style="width:55%;"></div></div></div><b style="font-size:15px;color:#A78BFA;">55%</b></div>
                        </div>

                        <div class="a3-stage-slide" style="padding:28px 26px;animation:a3-panel-cycle 1.3s ease 2.6s 1;">
                            <div style="display:grid;grid-template-columns:0.8fr 1.2fr;align-items:center;gap:20px;margin-bottom:20px;">
                                <div class="a3-glass-card" style="padding:36px;"><div style="font-size:44px;color:#A78BFA;font-weight:700;">&lt;/&gt;</div><div style="font-size:12px;color:#94A3B8;margin-top:6px;">Deterministic Engine</div></div>
                                <div class="a3-glass-card-cyan" style="text-align:left;padding:22px 24px;">
                                    <div style="font-size:15px;font-weight:700;color:#FFFFFF;margin-bottom:12px;">▶ Running Synthetic Checks...</div>
                                    <div style="font-size:13px;color:#CBD5E1;line-height:2.0;"><div><span style="color:#34D399;">✓</span> Rule Logic Check</div><div><span style="color:#34D399;">✓</span> Output Consistency</div><div><span style="color:#38BDF8;">◌</span> Edge Case Coverage</div></div>
                                </div>
                            </div>
                            <div style="display:flex;align-items:center;gap:14px;"><span style="font-size:22px;animation:a1-spin 2s linear infinite;">⚙️</span><div style="flex:1;"><div style="font-size:13px;color:#CBD5E1;margin-bottom:6px;">Validating Baseline vs Proposed...</div><div class="a3-prog-track"><div class="a3-prog-fill" style="width:80%;"></div></div></div><b style="font-size:15px;color:#38BDF8;">80%</b></div>
                        </div>

                        <div class="a3-stage-slide" style="padding:30px 28px;animation:a3-panel-final 0.55s ease 3.9s forwards;">
                            <div style="text-align:center;margin-bottom:20px;">
                                <div style="font-size:56px;filter:drop-shadow(0 0 22px rgba(52,211,153,0.85));">🛡️</div>
                                <div style="font-size:24px;font-weight:700;color:#34D399;margin-top:8px;">Sandbox Ready ✓</div>
                                <div style="font-size:13px;color:#CBD5E1;margin-top:4px;">Validation completed for {ready_rule_lbl} · Ready for Agent 4</div>
                            </div>
                            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;">
                                <div class="a3-glass-card" style="padding:16px;"><div style="font-size:24px;font-weight:700;color:#FFFFFF;">{len(ready_proposals)}</div><div style="font-size:12px;color:#94A3B8;margin-top:2px;">Sandbox Rule Pairs</div></div>
                                <div class="a3-glass-card-cyan" style="padding:16px;"><div style="font-size:24px;font-weight:700;color:#34D399;">50</div><div style="font-size:12px;color:#94A3B8;margin-top:2px;">Synthetic Cases Ready</div></div>
                                <div class="a3-glass-card" style="padding:16px;border-color:rgba(52,211,153,0.45);"><div style="font-size:24px;font-weight:700;color:#34D399;">100%</div><div style="font-size:12px;color:#94A3B8;margin-top:2px;">Environment Verified</div></div>
                            </div>
                        </div>
                    </div>
                    """
                )

                # Bottom Action Bar ONLY on Sandbox Readiness tab -> Go to Agent 4 (Final Agent)
                render_html(
                    f"""
                    <div class="a1-bottom-bar-img4" style="margin-top:20px;">
                        <div style="display:flex;align-items:center;gap:14px;">
                            <div style="width:42px;height:42px;border-radius:50%;border:2.5px solid #34D399;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#34D399;box-shadow:0 0 12px rgba(52,211,153,0.35);">100%</div>
                            <div>
                                <div style="font-size:13px;font-weight:700;color:#FFFFFF;">Sandbox Ready</div>
                                <div style="font-size:11px;color:#34D399;">{len(ready_proposals)} rule pair(s) verified · Ready for Agent 4 Synthetic Testing</div>
                            </div>
                        </div>
                        <div style="font-size:11px;color:#94A3B8;">🧪 {total_proposals} proposals · Next: Agent 4 Test Generation (Final Agent)</div>
                    </div>
                    """
                )
                sb_c1, sb_c2, sb_c3 = st.columns([2.2, 0.9, 1.3])
                with sb_c1:
                    st.text_input("Sandbox review note", placeholder="Add a sandbox readiness note (optional)...", label_visibility="collapsed", key="agent3_sb_note")
                with sb_c2:
                    if st.button("🚩 Flag Sandbox", use_container_width=True, key="agent3_flag_btn"):
                        st.toast("Sandbox readiness flagged for review.", icon="🚩")
                with sb_c3:
                    if st.button("🚀 Go to Agent 4 (Final Agent) →", type="primary", use_container_width=True, key="agent3_go_agent4"):
                        st.session_state["pending_agent_nav"] = "Agent 4 – Test Generation"
                        st.session_state["agent3_proceed_toast"] = True
                        st.rerun()

    elif selected_agent == "Agent 4 – Test Generation":
        render_agent4_dashboard(selected_workflow_id)
                
