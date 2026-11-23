import re
import re
from pathlib import Path
from typing import Any, Literal

DocumentClassificationType = Literal[
    "circular",
    "policy_handbook",
    "amendment",
    "baseline_policy",
    "standalone_document",
    "unknown",
]


class DocumentClassifier:
    """Classifies regulatory and compliance documents based on content signals,

    metadata, and filename patterns. Prioritizes explicit textual content over filenames.
    """

    EXPLICIT_AMENDMENT_PATTERNS = [
        (r"\bamendment\s+to\b", "Explicit 'amendment to' phrasing"),
        (r"\bsupersedes?\b|\bin\s+supersession\s+of\b", "Supersession language"),
        (r"\bhereby\s+substituted\b|\bis\s+substituted\b", "Substitution language"),
        (r"\bread\s+together\s+with\b", "Reference 'read together with'"),
        (r"\bw\.?e\.?f\.?\b|\bwith\s+effect\s+from\b", "Effective date marker 'w.e.f.'"),
        (r"\bpartial\s+modification\s+of\b", "Partial modification clause"),
        (r"\bcorrigendum\s+to\b|\baddendum\s+to\b", "Corrigendum/Addendum phrasing"),
        (r"\bclause\s+[0-9a-zA-Z.]+\s+is\s+(?:amended|modified|replaced|omitted)\b", "Explicit clause modification"),
    ]

    AMENDMENT_KEYWORDS = [
        "amendment",
        "amended",
        "addendum",
        "revision",
        "modification",
        "corrigendum",
        "supersedes",
        "substituted",
        "revised",
    ]

    CIRCULAR_KEYWORDS = [
        "circular",
        "regulatory",
        "rbi",
        "master direction",
        "notification",
        "advisory",
        "directive",
        "statutory",
        "guidelines",
        "compliance notice",
    ]

    POLICY_KEYWORDS = [
        "policy",
        "policy handbook",
        "standard operating procedure",
        "internal manual",
        "credit policy",
        "lending policy",
        "risk framework",
        "baseline policy",
        "rules and regulations",
        "operational manual",
    ]

    @classmethod
    def extract_document_entities(cls, text: str) -> dict[str, Any]:
        """Extract document date, reference number, and amended document references generically."""
        # 1. Document Date
        date_match = re.search(
            r"\b(?:dated|date[:\s]+)?([0-3]?[0-9][/\-.][0-1]?[0-9][/\-.](?:19|20)\d{2}|"
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+[0-3]?[0-9],\s*(?:19|20)\d{2}|"
            r"[0-3]?[0-9]\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d{2})\b",
            text[:3000],
            re.IGNORECASE,
        )
        document_date = date_match.group(1) if date_match else None

        # 2. Reference Number
        ref_match = re.search(
            r"\b(?:Ref(?:\.|erence)?\s*(?:No\.?|#)?\s*[:\s]*|Circular\s+No\.?\s*[:\s]*|Notification\s+No\.?\s*[:\s]*)([A-Z0-9/\-._]+(?:/\d+)+|[A-Z]{2,10}/[A-Z0-9/\-._]+)",
            text[:3000],
            re.IGNORECASE,
        )
        reference_number = ref_match.group(1) if ref_match else None

        # 3. Amends/supersedes references
        amends_match = re.search(
            r"\b(?:amends?|supersedes?|in\s+supersession\s+of|read\s+together\s+with|amendment\s+to|substituted\s+for)\s+([A-Za-z0-9\s,/\-._]{5,100}?)(?=\.|\n|with\s+effect|$)",
            text[:4000],
            re.IGNORECASE,
        )
        amends_reference = amends_match.group(1).strip() if amends_match else None

        return {
            "document_date": document_date,
            "reference_number": reference_number,
            "amends_reference": amends_reference,
        }

    @classmethod
    def classify_text_and_name(
        cls, filename: str, sample_text: str = ""
    ) -> dict[str, Any]:
        name_lower = filename.casefold()
        text_lower = sample_text[:5000].casefold()
        signals: list[str] = []

        # Content-first scoring
        amendment_score = 0.0
        circular_score = 0.0
        policy_score = 0.0

        # Check explicit high-priority amendment patterns in text
        for pattern, desc in cls.EXPLICIT_AMENDMENT_PATTERNS:
            if re.search(pattern, text_lower):
                amendment_score += 3.5
                signals.append(f"Content pattern: {desc}")

        # Keyword checks in content
        for kw in cls.AMENDMENT_KEYWORDS:
            if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                amendment_score += 1.0
                signals.append(f"Content keyword (amendment): {kw}")

        for kw in cls.CIRCULAR_KEYWORDS:
            if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                circular_score += 1.0
                signals.append(f"Content keyword (circular): {kw}")

        for kw in cls.POLICY_KEYWORDS:
            if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                policy_score += 1.5
                signals.append(f"Content keyword (policy): {kw}")

        # Filename signals (secondary to content)
        if any(kw in name_lower for kw in ("amendment", "revised", "corrigendum", "addendum")):
            amendment_score += 2.0
            signals.append("Filename contains amendment indicator")
        elif "baseline" in name_lower:
            policy_score += 2.0
            signals.append("Filename contains 'baseline'")
        elif any(kw in name_lower for kw in ("circular", "regulatory", "rbi")):
            circular_score += 1.5
            signals.append("Filename contains circular indicator")
        elif any(kw in name_lower for kw in ("policy", "handbook", "sop")):
            # If filename has amendment or content is clearly amendment, don't let "policy" hijack it
            if amendment_score == 0:
                policy_score += 1.5
                signals.append("Filename contains policy indicator")

        # Disambiguation with content-first priority
        extracted_entities = cls.extract_document_entities(sample_text)
        if extracted_entities.get("amends_reference"):
            amendment_score += 2.0
            signals.append(f"Found amendment target reference: {extracted_entities['amends_reference']}")

        if amendment_score >= 2.0 and amendment_score >= circular_score:
            doc_type = "amendment"
            confidence = min(0.98, 0.65 + amendment_score * 0.08)
        elif policy_score >= circular_score and amendment_score < 2.0:
            if "baseline" in name_lower or "baseline" in text_lower or policy_score >= 3.0 or ("policy" in name_lower and circular_score <= policy_score):
                doc_type = "baseline_policy" if ("baseline" in name_lower or "baseline" in text_lower) else "policy_handbook"
            else:
                doc_type = "policy_handbook"
            confidence = min(0.95, 0.6 + policy_score * 0.08)
        elif circular_score > 0:
            doc_type = "circular"
            confidence = min(0.95, 0.6 + circular_score * 0.08)
        elif sample_text.strip():
            doc_type = "standalone_document"
            confidence = 0.6
        else:
            doc_type = "unknown"
            confidence = 0.3

        return {
            "document_type": doc_type,
            "confidence": round(confidence, 2),
            "is_amendment": doc_type == "amendment",
            "is_regulatory": doc_type in ("circular", "amendment", "standalone_document"),
            "is_policy": doc_type in ("policy_handbook", "baseline_policy"),
            "signals": signals,
            **extracted_entities,
        }

    @classmethod
    def classify_document(cls, path: Path, sample_text: str = "") -> str:
        res = cls.classify_text_and_name(path.name, sample_text)
        return str(res["document_type"])
