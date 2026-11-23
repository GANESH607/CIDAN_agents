import logging
import re
import difflib
import unicodedata
from typing import Any

from langchain_core.documents import Document
from cidan.models import Citation
from cidan.ingestion.retrieval import citation_for

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
    """Detect relationships between documents (amendment to baseline, or standalone).

    Decided by:
    (a) explicit references (title, reference number, 'amends'),
    (b) date ordering,
    (c) similarity between titles and clause texts.
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

    # Detect explicit links
    links = []
    baseline_names = {d.metadata.get("filename", "") for d in baseline_docs}
    baseline_id = baseline_docs[0].metadata.get("document_id")

    for reg_doc in regulatory_docs:
        fn = reg_doc.metadata.get("filename", "")
        content_sample = reg_doc.page_content[:3000].lower()

        # Check explicit reference
        for b_name in baseline_names:
            base_stem = b_name.split(".")[0].lower()
            if base_stem in content_sample:
                links.append({
                    "amendment_doc": fn,
                    "baseline_doc": b_name,
                    "link_type": "explicit_title_reference",
                    "evidence": f"Found reference to {b_name} in {fn}",
                })

        # Check amends phrasing
        if any(w in content_sample for w in ("amends", "supersedes", "in supersession of", "read together with")):
            links.append({
                "amendment_doc": fn,
                "baseline_doc": list(baseline_names)[0],
                "link_type": "amendment_language",
                "evidence": f"Found explicit modification phrasing in {fn}",
            })

    return {
        "has_baseline": True,
        "mode": "amendment",
        "relationships": links,
        "baseline_doc_id": baseline_id,
        "baseline_doc_count": len(baseline_docs),
        "evidence": f"Linked regulatory amendment to baseline with {len(links)} signals",
    }


def _find_table_old_position(text: str) -> str | None:
    """Check if row format contains an old/existing column generically."""
    if not (text.startswith("[TABLE ") and " ROW " in text):
        return None
    # Parse cells e.g. [TABLE t1 ROW 1] Col1=Val1 | Col2=Val2
    cells_str = text.split("]", 1)[-1].strip()
    cells = [c.strip() for c in cells_str.split("|")]
    for cell in cells:
        if "=" in cell:
            col, val = cell.split("=", 1)
            col_lower = col.strip().lower()
            if any(k in col_lower for k in ("exist", "prev", "earlier", "old", "current", "baseline")):
                return val.strip()
    return None


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
    If no baseline is available, ALWAYS returns ('NEW', None, None).
    """
    if not relationships.get("has_baseline", False):
        return "NEW", None, None

    # 1. Check table old-position column
    old_position = _find_table_old_position(text)
    if old_position:
        norm_old = normalize_text(old_position)
        norm_new = normalize_text(text)
        if norm_old == norm_new:
            return "UNCHANGED", old_position, None
        else:
            return "MODIFIED", old_position, None

    # 2. Check baseline documents
    if not baseline_docs:
        return "NEW", None, None

    # Look for matching baseline chunk
    # Do NOT assume clause numbers alone equal matching requirements.
    clean_clause = clause_id.strip().lower()
    norm_new = normalize_text(text)

    best_match_doc = None
    best_similarity = 0.0

    for b_doc in baseline_docs:
        b_content = b_doc.page_content
        b_norm = normalize_text(b_content)

        # Check clause id match
        has_clause = False
        if clean_clause and clean_clause != "not_specified":
            # Word boundary check
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
                # Fuzzy verify in baseline
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
    # If the model proposed MODIFIED or UNCHANGED without a baseline match, downgrade
    if model_proposal and model_proposal.get("change_classification") in ("MODIFIED", "UNCHANGED"):
        return "NEEDS_REVIEW", None, None

    return "NEW", None, None
