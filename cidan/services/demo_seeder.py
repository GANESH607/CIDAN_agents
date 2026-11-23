"""Seeds the benchmark demonstration workflow CIDAN-001 matching the Jatayu design."""

import os
import sys
from datetime import datetime, timezone
from cidan.services import agent1_storage

CIDAN_001_ID = "CIDAN-001"


def seed_cidan_001_if_needed(force: bool = False, demo_fixture_enabled: bool = False) -> None:
    if not force and not demo_fixture_enabled and "--demo-fixture" not in sys.argv and not os.getenv("CIDAN_DEMO_FIXTURE"):
        return

    out_dir = agent1_storage.get_agent1_output_dir(CIDAN_001_ID, create=True)
    if not force and (out_dir / "extracted_obligations.json").is_file():
        return

    timestamp = "2025-04-23T10:24:00+00:00"

    obligations = [
        {
            "obligation_id": "OBL-001",
            "clause_id": "2.1",
            "text": "Priority service for senior citizens (60+) with service bands introduced.",
            "applicability": "Senior citizen account holders (aged 60 and above)",
            "product_type": "retail_banking",
            "amount_threshold": None,
            "currency": None,
            "effective_date": "2026-04-01",
            "responsible_function": "Branch Operations & Customer Service",
            "required_action": "Implement priority service desk and dedicated queue bands",
            "deadline_or_frequency": "immediate",
            "exceptions": [],
            "source": {
                "document_id": "doc-amd-2026",
                "filename": "Amendment Policy_2026.pdf",
                "document_type": "amendment",
                "page": 1,
                "excerpt": "Clause 2.1: Priority service for senior citizens (60+) with dedicated service bands shall be introduced across all retail branches.",
                "chunk_id": "chunk-amd-2026-p1-c2.1",
            },
            "supporting_excerpt": "Priority service for senior citizens (60+) with dedicated service bands shall be introduced across all retail branches.",
            "confidence": 0.95,
            "ambiguities": [],
            "source_label": "synthetic_demo_source",
            "status": "needs_review",
            "change_classification": "MODIFIED",
            "previous_requirement": "General queuing and service priority applied to all retail customer tiers without age-specific differentiation.",
            "amended_requirement": "Priority service for senior citizens (60+) with dedicated service bands shall be introduced across all retail branches.",
            "source_document": "Amendment Policy_2026.pdf",
            "page_number": 1,
            "evidence_references": [
                {
                    "document_id": "doc-amd-2026",
                    "filename": "Amendment Policy_2026.pdf",
                    "document_type": "amendment",
                    "page": 1,
                    "excerpt": "Clause 2.1: Priority service for senior citizens (60+) with dedicated service bands shall be introduced across all retail branches.",
                    "chunk_id": "chunk-amd-2026-p1-c2.1",
                }
            ],
            "surrounding_context": "Section 2: Senior Citizen Care and Assisted Services\nClause 2.1: Priority service for senior citizens (60+) with dedicated service bands shall be introduced across all retail branches. This supersedes the previous uniform queuing framework.",
            "verification_status": "verified",
        },
        {
            "obligation_id": "OBL-002",
            "clause_id": "2.2",
            "text": "Assisted digital support for customers aged 60+.",
            "applicability": "Senior citizen customers using internet/mobile banking",
            "product_type": "digital_banking",
            "amount_threshold": None,
            "currency": None,
            "effective_date": "2026-04-01",
            "responsible_function": "Digital Banking & Branch Support",
            "required_action": "Provide guided onboarding and designated branch assistance",
            "deadline_or_frequency": "on_request",
            "exceptions": [],
            "source": {
                "document_id": "doc-amd-2026",
                "filename": "Amendment Policy_2026.pdf",
                "document_type": "amendment",
                "page": 1,
                "excerpt": "Clause 2.2: Branches must provide dedicated assisted digital support for customers aged 60+ seeking self-service digital adoption.",
                "chunk_id": "chunk-amd-2026-p1-c2.2",
            },
            "supporting_excerpt": "Branches must provide dedicated assisted digital support for customers aged 60+ seeking self-service digital adoption.",
            "confidence": 0.94,
            "ambiguities": [],
            "source_label": "synthetic_demo_source",
            "status": "needs_review",
            "change_classification": "NEW",
            "previous_requirement": "None (New requirement introduced in 2026 amendment)",
            "amended_requirement": "Branches must provide dedicated assisted digital support for customers aged 60+ seeking self-service digital adoption.",
            "source_document": "Amendment Policy_2026.pdf",
            "page_number": 1,
            "evidence_references": [],
            "surrounding_context": "Clause 2.2: Branches must provide dedicated assisted digital support for customers aged 60+ seeking self-service digital adoption. Staff shall be trained on assisted kiosk workflows.",
            "verification_status": "verified",
        },
        {
            "obligation_id": "OBL-003",
            "clause_id": "2.3",
            "text": "Priority routing and support for customers aged 70+ with access difficulties.",
            "applicability": "Elderly customers (70+) and persons with accessibility constraints",
            "product_type": "contact_center",
            "amount_threshold": None,
            "currency": None,
            "effective_date": "2026-05-01",
            "responsible_function": "Contact Center Operations",
            "required_action": "Route inbound calls directly to specialized senior support agents without IVR loops",
            "deadline_or_frequency": "continuous",
            "exceptions": [],
            "source": {
                "document_id": "doc-amd-2026",
                "filename": "Amendment Policy_2026.pdf",
                "document_type": "amendment",
                "page": 2,
                "excerpt": "Clause 2.3: Inbound customer care systems shall provide priority routing and direct specialist access for customers aged 70+ with access difficulties.",
                "chunk_id": "chunk-amd-2026-p2-c2.3",
            },
            "supporting_excerpt": "Inbound customer care systems shall provide priority routing and direct specialist access for customers aged 70+ with access difficulties.",
            "confidence": 0.93,
            "ambiguities": [],
            "source_label": "synthetic_demo_source",
            "status": "needs_review",
            "change_classification": "NEW",
            "previous_requirement": "None (New requirement introduced in 2026 amendment)",
            "amended_requirement": "Inbound customer care systems shall provide priority routing and direct specialist access for customers aged 70+ with access difficulties.",
            "source_document": "Amendment Policy_2026.pdf",
            "page_number": 2,
            "evidence_references": [],
            "surrounding_context": "Clause 2.3: Inbound customer care systems shall provide priority routing and direct specialist access for customers aged 70+ with access difficulties, bypassing multi-level automated menus.",
            "verification_status": "verified",
        },
        {
            "obligation_id": "OBL-004",
            "clause_id": "2.4",
            "text": "Additional transaction alert safeguards for customers aged 80+.",
            "applicability": "Super-senior customers (80+) and high-value outbound transfers",
            "product_type": "payments_and_transfers",
            "amount_threshold": 50000,
            "currency": "INR",
            "effective_date": "2026-05-01",
            "responsible_function": "Fraud Risk & Monitoring",
            "required_action": "Implement mandatory multi-channel confirmation and verbal check for transfers > 50,000",
            "deadline_or_frequency": "per_transaction",
            "exceptions": ["Pre-registered recurring standing instructions"],
            "source": {
                "document_id": "doc-amd-2026",
                "filename": "Amendment Policy_2026.pdf",
                "document_type": "amendment",
                "page": 2,
                "excerpt": "Clause 2.4: Additional transaction alert safeguards including outbound verification call for transactions exceeding 50,000 shall be enforced for customers aged 80+.",
                "chunk_id": "chunk-amd-2026-p2-c2.4",
            },
            "supporting_excerpt": "Additional transaction alert safeguards including outbound verification call for transactions exceeding 50,000 shall be enforced for customers aged 80+.",
            "confidence": 0.96,
            "ambiguities": [],
            "source_label": "synthetic_demo_source",
            "status": "needs_review",
            "change_classification": "NEW",
            "previous_requirement": "None (New safeguard threshold introduced in 2026 amendment)",
            "amended_requirement": "Additional transaction alert safeguards including outbound verification call for transactions exceeding 50,000 shall be enforced for customers aged 80+.",
            "source_document": "Amendment Policy_2026.pdf",
            "page_number": 2,
            "evidence_references": [],
            "surrounding_context": "Clause 2.4: Additional transaction alert safeguards including outbound verification call for transactions exceeding 50,000 shall be enforced for customers aged 80+. Exemption applies only to recurring pre-authorized mandates.",
            "verification_status": "verified",
        },
        {
            "obligation_id": "OBL-005",
            "clause_id": "2.5",
            "text": "Acknowledge within 1 working day and resolve within 7 working days.",
            "applicability": "Senior citizen grievances and complaints across all channels",
            "product_type": "grievance_redressal",
            "amount_threshold": None,
            "currency": None,
            "effective_date": "2026-04-01",
            "responsible_function": "Customer Grievance Redressal Cell",
            "required_action": "Acknowledge receipt in 1 working day; achieve complete dispute resolution in 7 working days",
            "deadline_or_frequency": "1_day_ack_7_day_resolution",
            "exceptions": [],
            "source": {
                "document_id": "doc-amd-2026",
                "filename": "Amendment Policy_2026.pdf",
                "document_type": "amendment",
                "page": 2,
                "excerpt": "Acknowledge senior-citizen complaints within 1 working day and target resolution within 7 working days.",
                "chunk_id": "chunk-amd-2026-p2-c2.5",
            },
            "supporting_excerpt": "Acknowledge senior-citizen complaints within 1 working day and target resolution within 7 working days.",
            "confidence": 0.98,
            "ambiguities": [],
            "source_label": "synthetic_demo_source",
            "status": "needs_review",
            "change_classification": "MODIFIED",
            "previous_requirement": "Acknowledge complaint within 2 working days; target dispute resolution within 10 working days.",
            "amended_requirement": "Acknowledge senior-citizen complaints within 1 working day and target resolution within 7 working days.",
            "source_document": "Amendment Policy_2026.pdf",
            "page_number": 2,
            "evidence_references": [
                {
                    "document_id": "doc-amd-2026",
                    "filename": "Amendment Policy_2026.pdf",
                    "document_type": "amendment",
                    "page": 2,
                    "excerpt": "Acknowledge senior-citizen complaints within 1 working day and target resolution within 7 working days.",
                    "chunk_id": "chunk-amd-2026-p2-c2.5",
                }
            ],
            "surrounding_context": "Clause 2.5: Dispute and Grievance Resolution for Elderly Customers.\nAcknowledge senior-citizen complaints within 1 working day and target resolution within 7 working days. Replaces earlier SLA of 2 working days acknowledgement and 10 working days resolution from 2025 Baseline Policy.",
            "verification_status": "verified",
        },
        {
            "obligation_id": "OBL-006",
            "clause_id": "2.6",
            "text": "Enhanced records, monthly review and quarterly reporting.",
            "applicability": "Senior citizen banking service metrics and audit reporting",
            "product_type": "regulatory_reporting",
            "amount_threshold": None,
            "currency": None,
            "effective_date": "2026-04-01",
            "responsible_function": "Compliance & Regulatory Affairs",
            "required_action": "Maintain granular logs, conduct monthly grievance reviews, submit quarterly regulatory return",
            "deadline_or_frequency": "monthly_review_quarterly_reporting",
            "exceptions": [],
            "source": {
                "document_id": "doc-amd-2026",
                "filename": "Amendment Policy_2026.pdf",
                "document_type": "amendment",
                "page": 3,
                "excerpt": "Clause 2.6: Compliance records shall be maintained with mandatory monthly internal reviews and quarterly reporting to the customer service committee.",
                "chunk_id": "chunk-amd-2026-p3-c2.6",
            },
            "supporting_excerpt": "Clause 2.6: Compliance records shall be maintained with mandatory monthly internal reviews and quarterly reporting to the customer service committee.",
            "confidence": 0.94,
            "ambiguities": [],
            "source_label": "synthetic_demo_source",
            "status": "needs_review",
            "change_classification": "MODIFIED",
            "previous_requirement": "Annual compliance summary and standard dispute log review.",
            "amended_requirement": "Compliance records shall be maintained with mandatory monthly internal reviews and quarterly reporting to the customer service committee.",
            "source_document": "Amendment Policy_2026.pdf",
            "page_number": 3,
            "evidence_references": [],
            "surrounding_context": "Clause 2.6: Reporting Cadence and Oversight.\nCompliance records shall be maintained with mandatory monthly internal reviews and quarterly reporting to the customer service committee. Prior provisions for annual review are hereby superseded.",
            "verification_status": "verified",
        },
    ]

    comparison = {
        "summary": {
            "new": 3,
            "modified": 3,
            "unchanged": 0,
            "superseded": 0,
            "potential_conflict": 0,
            "needs_review": 0,
        },
        "total_analyzed": 6,
        "comparison_items": [
            {
                "obligation_id": "OBL-001",
                "clause_id": "2.1",
                "classification": "MODIFIED",
                "baseline_requirement": "Uniform general queuing without service bands.",
                "amended_requirement": "Priority service for senior citizens (60+) with service bands introduced.",
                "effective_date": "2026-04-01",
                "responsible_function": "Branch Operations",
                "key_changes": ["Status: MODIFIED", "Action: Dedicated priority queue bands"],
                "source_document": "Amendment Policy_2026.pdf",
                "page_number": 1,
            },
            {
                "obligation_id": "OBL-002",
                "clause_id": "2.2",
                "classification": "NEW",
                "baseline_requirement": "None (New requirement introduced)",
                "amended_requirement": "Assisted digital support for customers aged 60+.",
                "effective_date": "2026-04-01",
                "responsible_function": "Digital Banking",
                "key_changes": ["Status: NEW", "Action: Branch digital assistance"],
                "source_document": "Amendment Policy_2026.pdf",
                "page_number": 1,
            },
            {
                "obligation_id": "OBL-003",
                "clause_id": "2.3",
                "classification": "NEW",
                "baseline_requirement": "None (New requirement introduced)",
                "amended_requirement": "Priority routing and support for customers aged 70+ with access difficulties.",
                "effective_date": "2026-05-01",
                "responsible_function": "Contact Center",
                "key_changes": ["Status: NEW", "Action: Direct specialist routing without IVR"],
                "source_document": "Amendment Policy_2026.pdf",
                "page_number": 2,
            },
            {
                "obligation_id": "OBL-004",
                "clause_id": "2.4",
                "classification": "NEW",
                "baseline_requirement": "None (New requirement introduced)",
                "amended_requirement": "Additional transaction alert safeguards for customers aged 80+.",
                "effective_date": "2026-05-01",
                "responsible_function": "Fraud Risk",
                "key_changes": ["Status: NEW", "Threshold: > 50,000 INR verification call"],
                "source_document": "Amendment Policy_2026.pdf",
                "page_number": 2,
            },
            {
                "obligation_id": "OBL-005",
                "clause_id": "2.5",
                "classification": "MODIFIED",
                "baseline_requirement": "Acknowledge within 2 working days; resolution within 10 working days.",
                "amended_requirement": "Acknowledge within 1 working day and resolve within 7 working days.",
                "effective_date": "2026-04-01",
                "responsible_function": "Grievance Redressal",
                "key_changes": [
                    "Status: MODIFIED",
                    "Acknowledgement SLA: 2 working days -> 1 working day",
                    "Resolution SLA: 10 working days -> 7 working days",
                ],
                "before_after_metrics": {
                    "baseline_label": "2025 (Baseline)",
                    "amendment_label": "2026 (Amendment)",
                    "metrics": [
                        {
                            "label": "Acknowledge within",
                            "before": "2 working days",
                            "after": "1 working day",
                        },
                        {
                            "label": "Target resolution",
                            "before": "10 working days",
                            "after": "7 working days",
                        },
                    ],
                },
                "source_document": "Amendment Policy_2026.pdf",
                "page_number": 2,
            },
            {
                "obligation_id": "OBL-006",
                "clause_id": "2.6",
                "classification": "MODIFIED",
                "baseline_requirement": "Annual compliance summary and dispute logs.",
                "amended_requirement": "Enhanced records, monthly review and quarterly reporting.",
                "effective_date": "2026-04-01",
                "responsible_function": "Compliance",
                "key_changes": ["Status: MODIFIED", "Cadence: Annual -> Monthly review + Quarterly reporting"],
                "source_document": "Amendment Policy_2026.pdf",
                "page_number": 3,
            },
        ],
    }

    evidence = [
        {
            "obligation_id": o["obligation_id"],
            "clause_id": o["clause_id"],
            "source_document": o["source_document"],
            "page_number": o["page_number"],
            "exact_supporting_excerpt": o["supporting_excerpt"],
            "surrounding_context": o["surrounding_context"],
            "verification_status": o["verification_status"],
            "confidence": o["confidence"],
            "ambiguities": o["ambiguities"],
        }
        for o in obligations
    ]

    coverage = {
        "workflow_id": CIDAN_001_ID,
        "documents_count": 2,
        "document_names": ["Baseline_Policy_2025.pdf", "Amendment_Policy_2026.pdf"],
        "document_types": ["baseline_policy", "amendment"],
        "total_pages": 7,
        "pages_processed": 7,
        "coverage_percentage": 100.0,
        "total_chunks": 14,
        "chunks_processed": 14,
        "chunk_coverage_percentage": 100.0,
        "quality_checks": {
            "all_pages_processed": True,
            "clause_and_table_extraction": True,
            "amendment_relationship_detected": True,
            "duplicate_obligations_checked": True,
            "source_excerpts_preserved": True,
            "extraction_quality_score": 94.0,
            "missing_clauses": [],
            "duplicates_detected": [],
            "human_review_required": 0,
        },
    }

    metadata = {
        "status": "completed",
        "started_at": timestamp,
        "completed_at": timestamp,
        "execution_time_seconds": 12.4,
        "documents_processed": 2,
        "document_names": ["Baseline_Policy_2025.pdf", "Amendment_Policy_2026.pdf"],
        "total_obligations": 6,
        "change_breakdown": {"new": 3, "modified": 3, "unchanged": 0},
    }

    for o in obligations:
        o["synthetic_fixture"] = True
    comparison["synthetic_fixture"] = True
    for e in evidence:
        e["synthetic_fixture"] = True
    coverage["synthetic_fixture"] = True
    metadata["synthetic_fixture"] = True

    agent1_storage.save_extracted_obligations(CIDAN_001_ID, obligations)
    agent1_storage.save_amendment_comparison(CIDAN_001_ID, comparison)
    agent1_storage.save_evidence_and_citations(CIDAN_001_ID, evidence)
    agent1_storage.save_coverage_report(CIDAN_001_ID, coverage)
    agent1_storage.save_execution_metadata(CIDAN_001_ID, metadata)

    # Seed Agent 2 outputs matching the benchmark obligations
    from cidan.services import agent2_storage
    findings = [
        {
            "obligation_id": "OBL-001",
            "status": "partially_covered",
            "matching_policy_provision": "Clause 2.1 Priority service",
            "circular_citation": obligations[0]["source"],
            "policy_citations": [
                {
                    "document_id": "doc-policy-2025",
                    "filename": "Baseline_Policy_2025.pdf",
                    "document_type": "policy_handbook",
                    "page": 2,
                    "excerpt": "Clause 2.1 Priority service: Provide a clearly marked priority queue or counter for customers aged 60+. Staff must offer assistance where requested.",
                    "chunk_id": "chunk-pol-2025-p2-c2.1",
                }
            ],
            "reasoning": "Existing policy provides senior priority counters but lacks the newly mandated differentiated assistance age bands.",
            "missing_or_inconsistent": "Dedicated service bands for age brackets (60–69, 70–79, 80+) are not defined in current policy.",
            "operational_impact": "Branch operations must implement tiered age-band routing rules.",
            "recommended_action": "Update branch service handbook to specify procedures for each age band.",
            "confidence": 0.85,
            "evidence_confidence": 0.85,
            "model_reported_confidence": 0.95,
            "evidence_limitations": ["Current policy only defines uniform 60+ priority."],
            "synthetic_fixture": True,
        },
        {
            "obligation_id": "OBL-002",
            "status": "partially_covered",
            "matching_policy_provision": "Clause 2.2 Digital assistance",
            "circular_citation": obligations[1]["source"],
            "policy_citations": [
                {
                    "document_id": "doc-policy-2025",
                    "filename": "Baseline_Policy_2025.pdf",
                    "document_type": "policy_handbook",
                    "page": 2,
                    "excerpt": "Clause 2.2 Digital banking support: General assistance provided upon customer request at branch kiosks.",
                    "chunk_id": "chunk-pol-2025-p2-c2.2",
                }
            ],
            "reasoning": "General assistance exists but does not mandate credential safety safeguards for assisted digital banking.",
            "missing_or_inconsistent": "Explicit prohibition on staff collecting customer credentials/OTP during assisted sessions is missing.",
            "operational_impact": "Potential security vulnerability during branch kiosk assistance.",
            "recommended_action": "Incorporate credential protection guidelines into digital customer service SOP.",
            "confidence": 0.80,
            "evidence_confidence": 0.80,
            "model_reported_confidence": 0.90,
            "evidence_limitations": ["Credential protection policy is separate from general service SOP."],
            "synthetic_fixture": True,
        },
        {
            "obligation_id": "OBL-003",
            "status": "not_found",
            "matching_policy_provision": None,
            "circular_citation": obligations[2]["source"],
            "policy_citations": [],
            "reasoning": "Contact center policy does not have any dedicated routing workflow or IVR bypass for customers aged 70+.",
            "missing_or_inconsistent": "Priority case routing and callback mechanism for 70+ customers is completely missing.",
            "operational_impact": "70+ customers experience standard IVR queue times.",
            "recommended_action": "Configure telephony routing rules to identify 70+ callers and route to senior support queue.",
            "confidence": 0.70,
            "evidence_confidence": 0.70,
            "model_reported_confidence": 0.90,
            "evidence_limitations": ["Contact center telephony guidelines were reviewed; no 70+ routing rule exists."],
            "synthetic_fixture": True,
        },
        {
            "obligation_id": "OBL-004",
            "status": "requires_human_review",
            "matching_policy_provision": "Section 4 Fraud controls",
            "circular_citation": obligations[3]["source"],
            "policy_citations": [
                {
                    "document_id": "doc-policy-2025",
                    "filename": "Baseline_Policy_2025.pdf",
                    "document_type": "policy_handbook",
                    "page": 3,
                    "excerpt": "Section 4: High-value transaction verification procedures for unusual account activity.",
                    "chunk_id": "chunk-pol-2025-p3-c4.1",
                }
            ],
            "reasoning": "Fraud controls require secondary confirmation for high-value transactions, but specific age 80+ welfare confirmation rules need compliance review.",
            "missing_or_inconsistent": "Unclear whether existing fraud triggers satisfy the specific 80+ welfare check requirement.",
            "operational_impact": "Risk of inappropriately delaying transactions or failing to perform required welfare checks.",
            "recommended_action": "Fraud risk committee must review and calibrate the high-value rule threshold for 80+ customers.",
            "confidence": 0.35,
            "evidence_confidence": 0.40,
            "model_reported_confidence": 0.35,
            "evidence_limitations": ["General fraud policy passages do not reference age-based welfare confirmation."],
            "synthetic_fixture": True,
        },
        {
            "obligation_id": "OBL-005",
            "status": "potential_conflict",
            "matching_policy_provision": "Clause 2.5 Grievance handling",
            "circular_citation": obligations[4]["source"],
            "policy_citations": [
                {
                    "document_id": "doc-policy-2025",
                    "filename": "Baseline_Policy_2025.pdf",
                    "document_type": "policy_handbook",
                    "page": 2,
                    "excerpt": "Clause 2.5 Grievance handling: Acknowledge senior-citizen complaints within 2 working days; target resolution within 10 working days.",
                    "chunk_id": "chunk-pol-2025-p2-c2.5",
                }
            ],
            "reasoning": "Existing policy specifies 2-day acknowledgment and 10-day resolution, conflicting with mandated 1-day and 7-day SLAs.",
            "missing_or_inconsistent": "SLA conflict: 2 days vs 1 day acknowledgment, and 10 days vs 7 days resolution.",
            "operational_impact": "Direct regulatory breach if complaints are processed under the existing 2-day/10-day SLA.",
            "recommended_action": "Immediately update grievance management system timers to 1 day acknowledgment and 7 days resolution.",
            "confidence": 0.85,
            "evidence_confidence": 0.85,
            "model_reported_confidence": 0.95,
            "evidence_limitations": ["Conflict confirmed against Clause 2.5 of the 2025 policy handbook."],
            "synthetic_fixture": True,
        },
        {
            "obligation_id": "OBL-006",
            "status": "covered",
            "matching_policy_provision": "Clause 2.6 Audit evidence",
            "circular_citation": obligations[5]["source"],
            "policy_citations": [
                {
                    "document_id": "doc-policy-2025",
                    "filename": "Baseline_Policy_2025.pdf",
                    "document_type": "policy_handbook",
                    "page": 3,
                    "excerpt": "Clause 2.6 Record retention: Maintain monthly branch logs of priority service and quarterly compliance review reports for audit.",
                    "chunk_id": "chunk-pol-2025-p3-c2.6",
                }
            ],
            "reasoning": "Existing policy mandates monthly branch records and quarterly compliance review, fully satisfying the circular requirement.",
            "missing_or_inconsistent": "None identified; existing policy satisfies required retention and review schedules.",
            "operational_impact": "Continue current branch record-keeping procedures without modification.",
            "recommended_action": "Maintain existing record retention controls and quarterly compliance reviews.",
            "confidence": 0.90,
            "evidence_confidence": 0.95,
            "model_reported_confidence": 0.90,
            "evidence_limitations": [],
            "synthetic_fixture": True,
        },
    ]
    agent2_storage.save_policy_findings(CIDAN_001_ID, findings, obligations)
    ev_records = []
    for f in findings:
        for pc in f.get("policy_citations", []):
            ev_records.append({
                "obligation_id": f["obligation_id"],
                "status": f["status"],
                "circular_chunk_id": f["circular_citation"]["chunk_id"],
                "policy_chunk_id": pc["chunk_id"],
                "policy_filename": pc["filename"],
                "policy_page": pc["page"],
                "policy_excerpt": pc["excerpt"],
                "synthetic_fixture": True,
            })
    agent2_storage.save_evidence_and_citations(CIDAN_001_ID, ev_records)
    status_counts = {"covered": 1, "partially_covered": 2, "potential_conflict": 1, "not_found": 1, "requires_human_review": 1}
    agent2_storage.save_mapping_summary(CIDAN_001_ID, {
        "total_obligations": 6,
        "total_findings": 6,
        "status_counts": status_counts,
        "fully_covered_count": 1,
        "partially_covered_count": 2,
        "potential_conflict_count": 1,
        "not_found_count": 1,
        "requires_human_review_count": 1,
        "synthetic_fixture": True,
    })
    agent2_storage.save_execution_metadata(CIDAN_001_ID, {
        "status": "completed",
        "completed_at": timestamp,
        "execution_time_seconds": 8.6,
        "synthetic_fixture": True,
    })

    # Seed Agent 3 Outputs for benchmark CIDAN-001
    from cidan.services import agent3_storage

    proposals = [
        {
            "rule_id": "RULE-2-2-REV",
            "version": 1,
            "change_id": "CHG-2-2",
            "business_purpose": "Mandate credential protection safeguards during assisted digital banking sessions for senior citizens.",
            "source_obligation_ids": ["OBL-002"],
            "source_policy_references": ["Clause 2.2 Digital assistance"],
            "description": "Require exception reason logging and prohibit staff capture of credentials/OTP during branch kiosk assistance.",
            "trigger_conditions": [
                {"field": "is_emergency", "operator": "eq", "value": True}
            ],
            "required_inputs": ["transaction_id", "is_emergency"],
            "decision_outcomes": ["require_exception_reason"],
            "exceptions": ["Supervised emergency recovery by branch manager"],
            "effective_date": "2026-04-01",
            "assumptions": ["Branch kiosks support guided assistance mode"],
            "unresolved_questions": ["Requires compliance confirmation of kiosk supervisor override protocol."],
            "risk_level": "medium",
            "validation_criteria": ["Verify credential entry is blocked during assisted kiosk session."],
            "rollback_considerations": "Revert to standard staff assistance guidelines with supervisory log.",
            "supporting_citations": [
                obligations[1]["source"],
                findings[1]["policy_citations"][0],
            ],
            "baseline_rule": None,
            "sandbox_rule": None,
            "unrelated_product_types": ["trade_finance"],
            "action": "require_exception_reason",
            "status": "draft",
            "existing_policy_provision": "Clause 2.2 Digital assistance",
            "proposed_rule": "Require exception reason logging and prohibit staff capture of credentials/OTP during branch kiosk assistance.",
            "reason_for_change": "Existing policy provides general assistance but lacks credential safety safeguards against OTP/PIN capture.",
            "operational_impact": "Prevents potential security breaches during assisted digital banking kiosk adoption.",
            "confidence": 0.80,
            "review_reasons": ["Supervisory override protocol requires operational compliance approval."],
            "sandbox_readiness": False,
            "synthetic_fixture": True,
        },
        {
            "rule_id": "RULE-2-5-SLA",
            "version": 1,
            "change_id": "CHG-2-5",
            "business_purpose": "Update senior citizen grievance escalation timers to align with mandated 1-day acknowledgment and 7-day resolution SLAs.",
            "source_obligation_ids": ["OBL-005"],
            "source_policy_references": ["Clause 2.5 Grievance handling"],
            "description": "Flag grievance cases exceeding 7 days retention/resolution time for mandatory second review.",
            "trigger_conditions": [
                {"field": "retention_days", "operator": "gt", "value": 7}
            ],
            "required_inputs": ["transaction_id", "retention_days"],
            "decision_outcomes": ["second_review"],
            "exceptions": ["Legal or regulatory escalation holds"],
            "effective_date": "2026-04-01",
            "assumptions": ["Grievance tracking CRM records resolution elapsed days"],
            "unresolved_questions": [],
            "risk_level": "high",
            "validation_criteria": ["Verify complaint cases open > 7 days trigger second review alert."],
            "rollback_considerations": "Maintain prior 10-day timer threshold in sandbox staging environment.",
            "supporting_citations": [
                obligations[4]["source"],
                findings[4]["policy_citations"][0],
            ],
            "baseline_rule": {
                "rule_id": "RULE-2-5-SLA",
                "version": 1,
                "change_id": "CHG-2-5",
                "product_type": "retail_banking",
                "conditions": [
                    {"field": "retention_days", "operator": "gt", "value": 10}
                ],
                "logical_operator": "AND",
                "outcome_when_matched": "second_review",
                "outcome_when_unmatched": "standard_processing",
                "manual_review_reason": None,
            },
            "sandbox_rule": {
                "rule_id": "RULE-2-5-SLA",
                "version": 2,
                "change_id": "CHG-2-5",
                "product_type": "retail_banking",
                "conditions": [
                    {"field": "retention_days", "operator": "gt", "value": 7}
                ],
                "logical_operator": "AND",
                "outcome_when_matched": "second_review",
                "outcome_when_unmatched": "standard_processing",
                "manual_review_reason": None,
            },
            "unrelated_product_types": ["commercial_loans"],
            "action": "second_review",
            "status": "draft",
            "existing_policy_provision": "Clause 2.5 Grievance handling: Target resolution within 10 working days.",
            "proposed_rule": "Flag grievance cases exceeding 7 days retention/resolution time for mandatory second review.",
            "reason_for_change": "Direct conflict between existing 10-day resolution SLA and circular mandated 7-day SLA.",
            "operational_impact": "Eliminates risk of regulatory non-compliance for unresolved senior citizen grievances.",
            "confidence": 0.85,
            "review_reasons": [],
            "sandbox_readiness": True,
            "synthetic_fixture": True,
        },
    ]

    agent3_storage.save_rule_proposals(CIDAN_001_ID, proposals, eligible_count=2)
    ev_records_3 = []
    for p in proposals:
        for c in p.get("supporting_citations", []):
            ev_records_3.append({
                "rule_id": p["rule_id"],
                "obligation_id": p["source_obligation_ids"][0],
                "document_id": c["document_id"],
                "filename": c["filename"],
                "document_type": c["document_type"],
                "page": c["page"],
                "chunk_id": c["chunk_id"],
                "excerpt": c["excerpt"],
                "is_valid": True,
                "synthetic_fixture": True,
            })
    agent3_storage.save_evidence_and_citations(CIDAN_001_ID, ev_records_3)
    agent3_storage.save_rule_summary(CIDAN_001_ID, {
        "workflow_id": CIDAN_001_ID,
        "total_proposals": 2,
        "eligible_findings": 2,
        "draft_count": 2,
        "sandbox_ready_count": 1,
        "human_review_required_count": 1,
        "status_counts": {"draft": 2},
        "action_counts": {"require_exception_reason": 1, "second_review": 1},
        "risk_counts": {"medium": 1, "high": 1},
        "synthetic_fixture": True,
    })
    agent3_storage.save_execution_metadata(CIDAN_001_ID, {
        "status": "completed",
        "completed_at": timestamp,
        "execution_time_seconds": 6.4,
        "synthetic_fixture": True,
    })
