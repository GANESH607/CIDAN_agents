import logging
import re
import difflib
import unicodedata
from typing import Any

from langchain_core.documents import Document
from cidan.models import Citation
from cidan.ingestion.retrieval import citation_for
from cidan.ingestion.pdf_loader import normalize_clause_id, detect_clause_ids

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize text with NFKC, lowercase, collapsed spaces, and unified quotes/dashes."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", text)
    norm = re.sub(r"[\u2018\u2019\u201A\u201B`]", "'", norm)
    norm = re.sub(r"[\u201C\u201D\u201E\u201F]", '"', norm)
    norm = re.sub(r"[\u2013\u2014\u2015\u2212]", "-", norm)
    # Remove hyphenated linebreaks
    norm = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", norm)
    norm = " ".join(norm.split())
    return norm.strip()


def extract_numbers_and_dates(text: str) -> list[dict[str, Any]]:
    """Extract numbers, currency thresholds, durations, and dates generically."""
    results = []

    # Indian digit grouping and standard numbers: 5,00,000 or 50,000 or 12.5
    for m in re.finditer(r"\b(?:\$|€|£|₹|INR|Rs\.?|USD)?\s*(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(lakh|crore|k|m|million|billion)?\b", text, re.IGNORECASE):
        raw_num = m.group(1).replace(",", "")
        unit = (m.group(2) or "").lower()
        try:
            val = float(raw_num)
            if unit == "lakh":
                val *= 100000
            elif unit == "crore":
                val *= 10000000
            elif unit == "million" or unit == "m":
                val *= 1000000
            elif unit == "k":
                val *= 1000
            results.append({"type": "number", "raw": m.group(0).strip(), "value": val})
        except ValueError:
            pass

    # Durations: e.g. "7 working days", "24 hours", "30 days", "1 month"
    for m in re.finditer(r"\b(\d+)\s*(working\s+days?|days?|hours?|weeks?|months?|years?)\b", text, re.IGNORECASE):
        results.append({
            "type": "duration",
            "raw": m.group(0).strip(),
            "value": f"{m.group(1)} {m.group(2).lower()}",
        })

    # Dates: DD/MM/YYYY or YYYY-MM-DD
    for m in re.finditer(r"\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b", text):
        results.append({"type": "date", "raw": m.group(0).strip(), "value": m.group(0).strip()})

    return results


def diff_values(old_text: str, new_text: str) -> list[dict[str, Any]]:
    """Extract numbers, units, durations and dates from both texts and report changed values."""
    old_items = extract_numbers_and_dates(old_text)
    new_items = extract_numbers_and_dates(new_text)

    changes = []
    old_nums = [it["value"] for it in old_items if it["type"] in ("number", "duration")]
    new_nums = [it["value"] for it in new_items if it["type"] in ("number", "duration")]

    if old_nums != new_nums:
        for idx in range(max(len(old_nums), len(new_nums))):
            o_val = old_nums[idx] if idx < len(old_nums) else None
            n_val = new_nums[idx] if idx < len(new_nums) else None
            if o_val != n_val:
                changes.append({
                    "field": "threshold_or_duration",
                    "old": o_val,
                    "new": n_val,
                })

    return changes


def detect_document_relationships(documents: list[Document]) -> dict[str, Any]:
    """Detect relationships between documents (amendment to baseline, unrelated, or standalone).

    Decided by:
    (a) explicit references (title, reference number, 'amends'),
    (b) date ordering,
    (c) clause-level overlap and content similarity.
    Does not classify documents as amendments merely because a baseline exists.
    """
    baseline_types = ("baseline_policy", "policy_handbook")
    regulatory_types = ("amendment", "circular", "standalone_document", "unknown")

    baseline_docs = [d for d in documents if d.metadata.get("document_type") in baseline_types]
    regulatory_docs = [d for d in documents if d.metadata.get("document_type") in regulatory_types]

    if not baseline_docs:
        return {
            "has_baseline": False,
            "mode": "standalone",
            "relationships": [],
            "baseline_doc_id": None,
            "evidence": "No baseline policy document provided in input documents.",
        }

    # Extract all baseline clauses
    baseline_clauses = set()
    for b in baseline_docs:
        cids = b.metadata.get("clause_ids") or detect_clause_ids(b.page_content)
        for c in cids:
            if c and c != "not_specified":
                baseline_clauses.add(normalize_clause_id(c))

    # Baseline titles & references from filename and page 1 content
    baseline_titles = set()
    for b in baseline_docs:
        fn = b.metadata.get("filename", "")
        if fn:
            base_stem = fn.split(".")[0].lower().replace("_", " ")
            baseline_titles.add(base_stem)
        if b.page_content:
            first_lines = [normalize_text(line).lower() for line in b.page_content.split("\n")[:6] if len(line.strip()) > 5]
            for l in first_lines:
                if not any(k in l for k in ("draft", "confidential", "table of contents", "page", "reference:")):
                    baseline_titles.add(l)

    links = []
    baseline_names = {d.metadata.get("filename", "") for d in baseline_docs}
    baseline_id = baseline_docs[0].metadata.get("document_id")

    has_explicit_title_ref = False
    has_amendment_phrasing = False
    matching_clauses_count = 0

    for reg_doc in regulatory_docs:
        fn = reg_doc.metadata.get("filename", "")
        content_sample = reg_doc.page_content[:4000].lower()
        reg_norm = normalize_text(reg_doc.page_content).lower()

        # 1. Check explicit title or filename reference
        for b_title in baseline_titles:
            if b_title and len(b_title) >= 6 and (b_title in content_sample or b_title in reg_norm):
                has_explicit_title_ref = True
                links.append({
                    "amendment_doc": fn,
                    "baseline_doc": list(baseline_names)[0],
                    "link_type": "explicit_title_reference",
                    "evidence": f"Found reference to '{b_title}' in {fn}",
                })

        # 2. Check explicit modification phrasing
        if any(w in content_sample for w in ("amends", "supersedes", "in supersession of", "read together with", "shall be substituted", "hereby modified")):
            has_amendment_phrasing = True
            links.append({
                "amendment_doc": fn,
                "baseline_doc": list(baseline_names)[0],
                "link_type": "amendment_language",
                "evidence": f"Found explicit modification phrasing in {fn}",
            })

        # 3. Check clause overlap
        reg_cids = reg_doc.metadata.get("clause_ids") or detect_clause_ids(reg_doc.page_content)
        norm_reg_cids = {normalize_clause_id(c) for c in reg_cids if c and c != "not_specified"}
        overlapping = norm_reg_cids.intersection(baseline_clauses)
        if overlapping:
            matching_clauses_count += len(overlapping)
            links.append({
                "amendment_doc": fn,
                "baseline_doc": list(baseline_names)[0],
                "link_type": "clause_overlap",
                "evidence": f"Shared clause identifiers: {sorted(overlapping)}",
            })

    # Decision logic based on evidence strength
    is_amendment_doc = any(d.metadata.get("document_type") == "amendment" for d in regulatory_docs)
    if has_explicit_title_ref or (has_amendment_phrasing and matching_clauses_count >= 1) or matching_clauses_count >= 2 or (is_amendment_doc and matching_clauses_count >= 1):
        return {
            "has_baseline": True,
            "mode": "amendment",
            "relationships": links,
            "baseline_doc_id": baseline_id,
            "baseline_doc_count": len(baseline_docs),
            "evidence": f"Linked regulatory amendment to baseline with {len(links)} signals (explicit={has_explicit_title_ref}, phrasing={has_amendment_phrasing}, clause_overlap={matching_clauses_count}).",
        }
    elif has_amendment_phrasing or matching_clauses_count == 1:
        # Weak / ambiguous signals: return NEEDS_REVIEW
        return {
            "has_baseline": False,
            "mode": "NEEDS_REVIEW",
            "relationships": links,
            "baseline_doc_id": baseline_id,
            "baseline_doc_count": len(baseline_docs),
            "evidence": "Ambiguous relationship: weak signals detected but insufficient explicit or clause-level evidence to confirm amendment.",
        }
    else:
        # No connection between documents
        return {
            "has_baseline": False,
            "mode": "unrelated",
            "relationships": [],
            "baseline_doc_id": None,
            "baseline_doc_count": len(baseline_docs),
            "evidence": "Documents are unrelated: no title references, amendment phrasing, or clause overlaps found.",
        }


def extract_table_positions(row_text: str) -> dict[str, str | None]:
    """Extract clause, previous-position, amended-position, and change status from a table row line."""
    if not row_text or not (row_text.startswith("[TABLE ") and " ROW " in row_text):
        return {"clause": None, "previous": None, "amended": None, "change": None}

    cells_str = row_text.split("]", 1)[-1].strip()
    cells = [c.strip() for c in cells_str.split("|")]
    parsed: dict[str, str] = {}
    for cell in cells:
        if "=" in cell:
            col, val = cell.split("=", 1)
            parsed[col.strip().lower()] = val.strip()

    clause_val = None
    prev_val = None
    amended_val = None
    change_val = None

    for col, val in parsed.items():
        if any(k in col for k in ("clause", "section", "ref", "para")):
            clause_val = val
        if (
            any(k in col for k in ("exist", "prev", "earlier", "old", "baseline", "original", "prior"))
            or ("position" in col and not any(k in col for k in ("amend", "revis", "new")))
            or ("202" in col and any(k in col for k in ("position", "baseline", "requirement")) and not any(k in col for k in ("amend", "revis", "new")))
        ):
            prev_val = val
        if any(k in col for k in ("revis", "amend", "new", "proposed", "updated", "modified")):
            amended_val = val
        if any(k in col for k in ("change", "classification", "status")):
            change_val = val

    return {
        "clause": clause_val,
        "previous": prev_val,
        "amended": amended_val,
        "change": change_val,
    }


def _find_table_old_position(text: str) -> str | None:
    """Check if row format contains an old/existing column generically."""
    pos = extract_table_positions(text)
    return pos.get("previous")


def align_obligation(
    clause_id: str,
    text: str,
    relationships: dict[str, Any],
    baseline_docs: list[Document],
    table_cell_text: str | None = None,
    model_proposal: dict[str, Any] | None = None,
) -> tuple[str, str | None, Citation | None]:
    """Deterministically align an obligation against baseline documents.

    Returns (classification, previous_requirement, baseline_citation).
    If no baseline is available or documents are unrelated, returns ('NEW', None, None).
    If relationship is ambiguous (NEEDS_REVIEW), returns ('NEEDS_REVIEW', None, None).
    """
    if relationships.get("mode") == "NEEDS_REVIEW":
        return "NEEDS_REVIEW", None, None

    if not relationships.get("has_baseline", False) or relationships.get("mode") in ("standalone", "unrelated"):
        return "NEW", None, None

    # 1. Check table positions using table_cell_text (or text if table-formatted)
    target_table_text = table_cell_text if (table_cell_text and table_cell_text.startswith("[TABLE ")) else (text if text.startswith("[TABLE ") else None)
    if target_table_text:
        table_pos = extract_table_positions(target_table_text)
        old_position = table_pos.get("previous")
        new_position = table_pos.get("amended") or text
        effective_clause = normalize_clause_id(table_pos.get("clause") or clause_id)
        explicit_change = table_pos.get("change")

        # Find matching baseline citation
        base_citation = None
        if baseline_docs:
            for b_doc in baseline_docs:
                if effective_clause and effective_clause != "not_specified":
                    b_content = b_doc.page_content
                    escaped_c = re.escape(effective_clause)
                    if re.search(rf"(?<![\d.]){escaped_c}(?![\d])", b_content, re.IGNORECASE):
                        base_citation = citation_for(b_doc)
                        break
                if old_position and old_position in b_doc.page_content:
                    base_citation = citation_for(b_doc)
                    break

        if explicit_change:
            up_change = explicit_change.upper()
            if "NEW" in up_change:
                return "NEW", old_position, base_citation
            elif "MODIF" in up_change:
                return "MODIFIED", old_position, base_citation
            elif "UNCHANG" in up_change:
                return "UNCHANGED", old_position, base_citation
            elif "SUPERSED" in up_change:
                return "SUPERSEDED", old_position, base_citation

        if old_position:
            norm_old = normalize_text(old_position)
            norm_new = normalize_text(new_position)

            if any(p in norm_old.lower() for p in ("no separate", "none", "not applicable", "n/a", "no existing")):
                return "NEW", old_position, base_citation

            if any(w in norm_new.lower() for w in ("deleted", "omitted", "repealed", "shall be omitted", "superseded")):
                return "SUPERSEDED", old_position, base_citation

            if norm_old == norm_new:
                return "UNCHANGED", old_position, base_citation
            else:
                return "MODIFIED", old_position, base_citation

    # 2. Check baseline documents
    if not baseline_docs:
        return "NEW", None, None

    clean_clause = normalize_clause_id(clause_id).strip().lower()
    norm_new = normalize_text(text)

    best_match_doc = None
    best_similarity = 0.0

    for b_doc in baseline_docs:
        b_content = b_doc.page_content
        b_norm = normalize_text(b_content)

        # Check clause id match
        has_clause = False
        if clean_clause and clean_clause != "not_specified":
            escaped_cid = re.escape(clean_clause)
            if re.search(rf"(?<![\d.]){escaped_cid}(?![\d])", b_content, re.IGNORECASE):
                has_clause = True

        sim = difflib.SequenceMatcher(None, norm_new, b_norm).ratio()
        if has_clause:
            sim += 0.35  # Boost when clause matches

        if sim > best_similarity:
            best_similarity = sim
            best_match_doc = b_doc

    # Threshold for a credible baseline match
    if best_match_doc and best_similarity >= 0.45:
        base_norm = normalize_text(best_match_doc.page_content)
        cit = citation_for(best_match_doc)

        # Check if model proposed a specific previous_requirement that is verified in the baseline text
        prev_req_text = best_match_doc.page_content
        if model_proposal and model_proposal.get("previous_requirement"):
            cand_prev = str(model_proposal["previous_requirement"]).strip()
            if cand_prev and cand_prev in best_match_doc.page_content:
                prev_req_text = cand_prev
            elif cand_prev:
                s_cand = difflib.SequenceMatcher(None, normalize_text(cand_prev), base_norm)
                if s_cand.ratio() >= 0.85:
                    prev_req_text = cand_prev

        # If normalized text is identical or nearly identical without numeric differences
        if base_norm == norm_new or (difflib.SequenceMatcher(None, base_norm, norm_new).ratio() >= 0.95 and not diff_values(best_match_doc.page_content, text)):
            return "UNCHANGED", prev_req_text, cit

        # Superseded language check
        if any(w in text.lower() for w in ("deleted", "omitted", "repealed", "shall be omitted", "superseded")):
            return "SUPERSEDED", prev_req_text, cit

        # Modified requirement
        return "MODIFIED", prev_req_text, cit

    # No baseline match found
    if model_proposal and model_proposal.get("change_classification") in ("MODIFIED", "UNCHANGED"):
        return "NEEDS_REVIEW", None, None

    return "NEW", None, None
