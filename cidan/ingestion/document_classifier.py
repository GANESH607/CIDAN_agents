import re
from pathlib import Path
from typing import Literal

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

    metadata, and filename patterns. Does not rely on rigid hardcoded names.
    """

    AMENDMENT_KEYWORDS = [
        "amendment",
        "amended",
        "addendum",
        "revision",
        "modification",
        "corrigendum",
        "supersedes",
        "substituted",
        "revised guidelines",
        "amendment policy",
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
        "handbook",
        "rules",
        "standard operating procedure",
        "internal manual",
        "credit policy",
        "lending policy",
        "risk framework",
        "baseline",
    ]

    @classmethod
    def classify_text_and_name(
        cls, filename: str, sample_text: str = ""
    ) -> dict[str, str | float]:
        name_lower = filename.casefold()
        text_lower = sample_text[:4000].casefold()

        # Score calculations based on occurrences
        amendment_score = 0.0
        circular_score = 0.0
        policy_score = 0.0

        for kw in cls.AMENDMENT_KEYWORDS:
            if kw in name_lower:
                amendment_score += 2.0
            if kw in text_lower:
                amendment_score += 1.0

        for kw in cls.CIRCULAR_KEYWORDS:
            if kw in name_lower:
                circular_score += 1.5
            if kw in text_lower:
                circular_score += 1.0

        for kw in cls.POLICY_KEYWORDS:
            if kw in name_lower:
                policy_score += 1.5
            if kw in text_lower:
                policy_score += 1.0

        # Check for explicit amendment references in text
        if re.search(r"\bamend(?:ed|ing|ment)?\b", text_lower):
            amendment_score += 1.5
        if re.search(r"\bcircular\s+no\.?\b", text_lower):
            circular_score += 2.0
        if re.search(r"\bpolicy\s+handbook\b|\bmaster\s+policy\b", text_lower):
            policy_score += 2.0

        # Disambiguation
        if amendment_score > 0 and (amendment_score >= circular_score or amendment_score >= policy_score):
            doc_type = "amendment"
            confidence = min(0.95, 0.6 + amendment_score * 0.1)
        elif policy_score > circular_score:
            # Check if it is a baseline policy
            if "baseline" in name_lower or "baseline" in text_lower or (policy_score >= 2.0 and amendment_score == 0):
                doc_type = "baseline_policy" if "baseline" in name_lower or "baseline" in text_lower else "policy_handbook"
            else:
                doc_type = "policy_handbook"
            confidence = min(0.95, 0.6 + policy_score * 0.1)
        elif circular_score > 0:
            doc_type = "circular"
            confidence = min(0.95, 0.6 + circular_score * 0.1)
        elif sample_text:
            doc_type = "standalone_document"
            confidence = 0.5
        else:
            doc_type = "unknown"
            confidence = 0.3

        return {
            "document_type": doc_type,
            "confidence": round(confidence, 2),
            "is_amendment": doc_type == "amendment",
            "is_regulatory": doc_type in ("circular", "amendment", "standalone_document"),
            "is_policy": doc_type in ("policy_handbook", "baseline_policy"),
        }

    @classmethod
    def classify_document(cls, path: Path, sample_text: str = "") -> str:
        res = cls.classify_text_and_name(path.name, sample_text)
        return str(res["document_type"])
