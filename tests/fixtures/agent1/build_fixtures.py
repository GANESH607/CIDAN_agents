import json
from pathlib import Path
import pymupdf

FIXTURES_DIR = Path(__file__).resolve().parent
GOLD_DIR = FIXTURES_DIR / "gold"


def build_all_fixtures():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Baseline Policy
    doc_base = pymupdf.open()
    page1 = doc_base.new_page(width=600, height=800)
    page1.insert_text((50, 70), "MASTER POLICY GUIDELINES 2024", fontsize=14)
    page1.insert_text((50, 100), "Document Reference: POL-2024-01 | Effective Date: 01-01-2024")
    page1.insert_text((50, 140), "Clause 1.1: Customer onboarding identity verification within 3 working days.")
    page1.insert_text((50, 180), "Clause 2.1: Transaction monitoring threshold is 100,000 INR for retail accounts.")
    page1.insert_text((50, 220), "Clause 3.1: Retention period for audit logs is 5 years from creation date.")
    page1.insert_text((50, 260), "Clause 4.1: Quarterly reporting to the risk committee within 15 days of quarter end.")
    base_path = FIXTURES_DIR / "baseline_policy.pdf"
    doc_base.save(str(base_path))
    doc_base.close()

    # 2. Amendment Policy (with old/new table columns, deleted clause, new clause, unchanged clause, diff requirement)
    doc_amd = pymupdf.open()
    page1 = doc_amd.new_page(width=600, height=800)
    page1.insert_text((50, 70), "AMENDMENT TO MASTER POLICY GUIDELINES 2024", fontsize=14)
    page1.insert_text((50, 95), "Ref: AMD-2026-01 | Effective Date: 01-04-2026 | Amends POL-2024-01")
    page1.insert_text((50, 130), "Clause 1.1: Customer onboarding identity verification within 3 working days.")
    page1.insert_text((50, 170), "Clause 2.1: Transaction monitoring threshold is 250,000 INR for retail accounts.")
    page1.insert_text((50, 210), "Clause 3.1 of Master Policy Guidelines 2024 is hereby deleted, omitted, and superseded.")
    page1.insert_text((50, 250), "Clause 5.1: Automated suspicious activity alerting within 2 hours of detection.")

    # Table with old/new positions
    rect = pymupdf.Rect(50, 300, 550, 420)
    page1.draw_rect(rect)
    page1.draw_line((50, 340), (550, 340))
    page1.draw_line((150, 300), (150, 420))
    page1.draw_line((350, 300), (350, 420))
    page1.insert_text((60, 325), "Clause ID")
    page1.insert_text((160, 325), "Existing Position")
    page1.insert_text((360, 325), "Revised Position")
    page1.insert_text((60, 380), "Clause 6.1")
    page1.insert_text((160, 380), "Annual compliance audit required.")
    page1.insert_text((360, 380), "Semi-annual compliance audit required.")

    page1.insert_text((50, 460), "All retail branches and functions must implement these amended provisions w.e.f. 01-04-2026.")
    amd_path = FIXTURES_DIR / "amendment_policy.pdf"
    doc_amd.save(str(amd_path))
    doc_amd.close()

    # 3. Standalone KYC Circular (unrelated domain)
    doc_kyc = pymupdf.open()
    page1 = doc_kyc.new_page(width=600, height=800)
    page1.insert_text((50, 70), "CENTRAL REGULATORY ADVISORY ON KYC & DATA REPORTING", fontsize=14)
    page1.insert_text((50, 95), "Circular No: CIR/KYC/2026/08 | Dated: 15-03-2026")
    page1.insert_text((50, 140), "Clause 1.1: Regulated entities must upload KYC records to Central Registry within 10 days.")
    page1.insert_text((50, 180), "Clause 1.2: Periodic risk re-categorization of low-risk clients every 8 years and high-risk clients every 2 years.")
    page1.insert_text((50, 220), "Clause 1.3: Cash transactions exceeding 10,00,000 INR require monthly CTR filing.")
    kyc_path = FIXTURES_DIR / "standalone_kyc_circular.pdf"
    doc_kyc.save(str(kyc_path))
    doc_kyc.close()

    # 4. Table-heavy PDF
    doc_tbl = pymupdf.open()
    page1 = doc_tbl.new_page(width=600, height=800)
    page1.insert_text((50, 60), "SCHEDULE OF REGULATORY THRESHOLDS & FEES", fontsize=14)
    # Draw table
    rect = pymupdf.Rect(50, 100, 550, 260)
    page1.draw_rect(rect)
    page1.draw_line((50, 140), (550, 140))
    page1.draw_line((50, 200), (550, 200))
    page1.draw_line((180, 100), (180, 260))
    page1.draw_line((360, 100), (360, 260))
    page1.insert_text((60, 125), "Clause ID")
    page1.insert_text((190, 125), "Exposure Tier")
    page1.insert_text((370, 125), "Mandatory Reserve Ratio")
    page1.insert_text((60, 175), "Clause 2.1")
    page1.insert_text((190, 175), "Tier 1: Above 50,00,000 INR")
    page1.insert_text((370, 175), "15% liquid assets")
    page1.insert_text((60, 235), "Clause 2.2")
    page1.insert_text((190, 235), "Tier 2: Above 10,00,000 INR")
    page1.insert_text((370, 235), "10% liquid assets")
    tbl_path = FIXTURES_DIR / "table_heavy.pdf"
    doc_tbl.save(str(tbl_path))
    doc_tbl.close()

    # 5. Two-column PDF
    doc_col = pymupdf.open()
    page1 = doc_col.new_page(width=600, height=800)
    # Left column (x: 50..280)
    page1.insert_text((50, 60), "Section 1: Left Column Norms", fontsize=12)
    page1.insert_text((50, 90), "Clause 1.1: Identity cards must be verified prior to account creation.")
    page1.insert_text((50, 120), "Clause 1.2: Mobile verification is required for web access.")
    # Right column (x: 320..550)
    page1.insert_text((320, 60), "Section 2: Right Column Safeguards", fontsize=12)
    page1.insert_text((320, 90), "Clause 2.1: Dual authorization for payments above 50,000 INR.")
    page1.insert_text((320, 120), "Clause 2.2: Daily transaction limits capped at 2,00,000 INR.")
    col_path = FIXTURES_DIR / "two_column.pdf"
    doc_col.save(str(col_path))
    doc_col.close()

    # 6. Scanned-style PDF (rasterized page)
    doc_scan_src = pymupdf.open()
    page_src = doc_scan_src.new_page(width=600, height=800)
    page_src.insert_text((50, 100), "CONFIDENTIAL SCANNED MEMORANDUM", fontsize=14)
    page_src.insert_text((50, 150), "Clause 1.1: Scanned image instruction requires secondary audit review.")
    pix = page_src.get_pixmap(dpi=150)
    doc_scan_src.close()

    doc_scan = pymupdf.open()
    page_scan = doc_scan.new_page(width=600, height=800)
    page_scan.insert_image(page_scan.rect, pixmap=pix)
    scan_path = FIXTURES_DIR / "scanned_page.pdf"
    doc_scan.save(str(scan_path))
    doc_scan.close()

    # 7. 10+ Page Document
    doc_10p = pymupdf.open()
    for p_num in range(1, 12):
        page = doc_10p.new_page(width=600, height=800)
        page.insert_text((50, 60), f"REGULATORY HANDBOOK CHAPTER {p_num}", fontsize=14)
        page.insert_text((50, 100), f"Clause {p_num}.1: Mandatory compliance obligation on page {p_num}.")
        page.insert_text((50, 140), f"Reporting threshold is {p_num * 10000} INR.")
        page.insert_text((50, 750), f"Page {p_num} of 11")
    p10_path = FIXTURES_DIR / "ten_plus_pages.pdf"
    doc_10p.save(str(p10_path))
    doc_10p.close()

    # 8. Ambiguous / Conflicting Clauses
    doc_conf = pymupdf.open()
    page1 = doc_conf.new_page(width=600, height=800)
    page1.insert_text((50, 70), "CIRCULAR ON EMERGENCY WITHDRAWAL LIMITS", fontsize=14)
    page1.insert_text((50, 120), "Clause 2.1: Emergency cash withdrawal limit is capped at 50,000 INR per day.")
    page1.insert_text((50, 170), "Clause 2.2: Branches may permit emergency cash withdrawals up to 75,000 INR per day.")
    conf_path = FIXTURES_DIR / "conflicting_clauses.pdf"
    doc_conf.save(str(conf_path))
    doc_conf.close()

    # 9. Repeated Headers / Footers
    doc_hf = pymupdf.open()
    for p_num in range(1, 5):
        page = doc_hf.new_page(width=600, height=800)
        page.insert_text((50, 40), "OFFICIAL REGULATORY COMPLIANCE DIRECTIVE 2026")
        page.insert_text((50, 120), f"Clause {p_num}.1: Operating standard for section {p_num}.")
        page.insert_text((50, 760), f"Page {p_num} of 4 - Strictly Confidential")
    hf_path = FIXTURES_DIR / "repeated_headers_footers.pdf"
    doc_hf.save(str(hf_path))
    doc_hf.close()

    # -------------------------------------------------------------
    # Hand-written Gold JSON files
    # -------------------------------------------------------------
    gold_amendment = {
        "fixture_name": "amendment_policy.pdf",
        "baseline_fixture": "baseline_policy.pdf",
        "expected_obligations": [
            {
                "clause_id": "1.1",
                "key_phrase": "Customer onboarding identity verification within 3 working days",
                "expected_change_type": "UNCHANGED",
                "expected_numeric_values": [3],
                "expected_page": 1,
            },
            {
                "clause_id": "2.1",
                "key_phrase": "Transaction monitoring threshold is 250,000 INR",
                "expected_change_type": "MODIFIED",
                "expected_numeric_values": [250000],
                "expected_page": 1,
            },
            {
                "clause_id": "3.1",
                "key_phrase": "deleted, omitted, and superseded",
                "expected_change_type": "SUPERSEDED",
                "expected_numeric_values": [],
                "expected_page": 1,
            },
            {
                "clause_id": "5.1",
                "key_phrase": "Automated suspicious activity alerting within 2 hours",
                "expected_change_type": "NEW",
                "expected_numeric_values": [2],
                "expected_page": 1,
            },
            {
                "clause_id": "6.1",
                "key_phrase": "Semi-annual compliance audit required",
                "expected_change_type": "MODIFIED",
                "expected_numeric_values": [],
                "expected_page": 1,
            },
        ],
    }
    (GOLD_DIR / "amendment_policy_gold.json").write_text(json.dumps(gold_amendment, indent=2), encoding="utf-8")

    gold_kyc = {
        "fixture_name": "standalone_kyc_circular.pdf",
        "baseline_fixture": None,
        "expected_obligations": [
            {
                "clause_id": "1.1",
                "key_phrase": "upload KYC records to Central Registry within 10 days",
                "expected_change_type": "NEW",
                "expected_numeric_values": [10],
                "expected_page": 1,
            },
            {
                "clause_id": "1.2",
                "key_phrase": "Periodic risk re-categorization of low-risk clients every 8 years and high-risk clients every 2 years",
                "expected_change_type": "NEW",
                "expected_numeric_values": [8, 2],
                "expected_page": 1,
            },
            {
                "clause_id": "1.3",
                "key_phrase": "Cash transactions exceeding 10,00,000 INR require monthly CTR filing",
                "expected_change_type": "NEW",
                "expected_numeric_values": [1000000],
                "expected_page": 1,
            },
        ],
    }
    (GOLD_DIR / "standalone_kyc_circular_gold.json").write_text(json.dumps(gold_kyc, indent=2), encoding="utf-8")

    gold_table = {
        "fixture_name": "table_heavy.pdf",
        "baseline_fixture": None,
        "expected_obligations": [
            {
                "clause_id": "2.1",
                "key_phrase": "Tier 1: Above 50,00,000 INR | 15% liquid assets",
                "expected_change_type": "NEW",
                "expected_numeric_values": [5000000, 15],
                "expected_page": 1,
            },
            {
                "clause_id": "2.2",
                "key_phrase": "Tier 2: Above 10,00,000 INR | 10% liquid assets",
                "expected_change_type": "NEW",
                "expected_numeric_values": [1000000, 10],
                "expected_page": 1,
            },
        ],
    }
    (GOLD_DIR / "table_heavy_gold.json").write_text(json.dumps(gold_table, indent=2), encoding="utf-8")


if __name__ == "__main__":
    build_all_fixtures()
    print("Built all synthetic fixtures and gold files in tests/fixtures/agent1/")
