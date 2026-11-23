# Agent 1: Obligation Extraction Hardening Guide

## Overview
Agent 1 is the first stage of CIDAN's compliance intelligence pipeline. It is responsible for ingesting regulatory PDFs and internal policy handbooks, extracting compliance requirements (obligations), verifying cited evidence against the source text, aligning amendments with baseline policies, and generating structured artifacts for downstream policy mapping and rule authoring.

---

## Pipeline Architecture & Stages

```
                +---------------------------------------+
                |          PDF Ingestion                |
                |  - Multi-column reading order         |
                |  - Repeated header/footer removal     |
                |  - Table cell word repair & dedup     |
                |  - Scanned page & OCR detection       |
                |  - Content-first document classifier  |
                +-------------------+-------------------+
                                    |
                                    v
                +---------------------------------------+
                |       Structure-Aware Chunking        |
                |  - Discrete table row chunks          |
                |  - Intact clauses & qualifiers        |
                |  - Neighboring context (before/after) |
                |  - Stable IDs: {doc8}-p{page}-c{idx}  |
                +-------------------+-------------------+
                                    |
                                    v
                +---------------------------------------+
                |    Deterministic Amendment Alignment  |
                |  - Document relationship detector     |
                |  - Baseline matching & old/new diff   |
                |  - Deterministic classification       |
                |    (NEW, MODIFIED, UNCHANGED, etc.)   |
                +-------------------+-------------------+
                                    |
                                    v
                +---------------------------------------+
                | Evidence Verification & Extraction    |
                |  - Exact & fuzzy quote verification   |
                |  - Token-boundary clause check        |
                |  - Threshold extraction & Indian nums |
                |  - Cross-chunk duplicate removal      |
                |  - Per-chunk retry & batch splitting  |
                +-------------------+-------------------+
                                    |
                                    v
                +---------------------------------------+
                |   Atomic Storage & Verification       |
                |  - 5 independent JSON artifacts (1.1) |
                |  - Incremental execution tracking     |
                |  - Run archiving (extraction_run_id)  |
                +---------------------------------------+
```

### Stage 1: PDF Extraction (`cidan/ingestion/pdf_loader.py`)
- **Reading Order**: Multi-column pages are partitioned by block x-coordinates and ordered column-by-column (left-to-right, top-to-bottom).
- **Header & Footer Stripping**: Body lines occurring in the margin zones (>50% of pages or matching page-number patterns) are stripped and logged in page metadata (`headers_removed`).
- **Table Cell Word Repair**: `page.find_tables()` identifies table structures; each cell text is reconstructed by joining word bounding boxes with spaces (`page.get_text("words", clip=cell_bbox)`). Table rows are emitted once formatted as `[TABLE t1 ROW x] Col1=Val1 | Col2=Val2`. Text inside tables is excluded from the standard text blocks to eliminate duplicate text.
- **Scanned Page Detection & OCR**: If a page has fewer than 50 characters or large images, PyMuPDF's OCR hook is invoked. If Tesseract is unavailable on the system, the page is flagged with `ocr_status="unavailable"` and `page_status="skipped_no_text"` and reported in `coverage_report.json`.
- **Content-First Classification**: Content signals (e.g. "amendment to", "supersedes", "hereby substituted", "w.e.f.") take priority over filenames. Document dates, reference numbers, and amends targets are extracted via generic patterns.

### Stage 2: Structure-Aware Chunking (`cidan/ingestion/chunking.py`)
- Emits discrete chunks for individual table rows with attached column names.
- Preserves clauses and sub-clauses (`2.1`, `2.1.3`, `(a)`, `(i)`) and qualifiers (`Provided that`, `Except`, `Notwithstanding`).
- Attaches real neighboring chunk context (`context_before`, `context_after`, `surrounding_context`).
- Generates short, deterministic IDs: `{document_id[:8]}-p{page}-c{index}`.

### Stage 3: Deterministic Amendment Alignment (`cidan/agents/amendment_alignment.py`)
- Detects relationships between regulatory amendments and baseline policies.
- Standalone documents (no baseline) deterministically assign `change_type="NEW"` and `baseline_available=false`.
- Matches amended clauses to baseline chunks through explicit citations, table old/new position columns, or lexical similarity.
- Classifies requirements as `NEW`, `MODIFIED`, `UNCHANGED`, `SUPERSEDED`, `POTENTIAL_CONFLICT`, or `NEEDS_REVIEW`.
- Performs numeric/date diffing between baseline and amended requirements (`changed_values: [{field, old, new}]`).

### Stage 4: Evidence Verification (`cidan/agents/circular_understanding.py`)
- **`verify_quote`**: Normalizes text (NFKC, whitespace, quotes, dashes) and maps character offsets back to the original source text (`excerpt_char_start`, `excerpt_char_end`). If exact normalization fails, a sliding-window fuzzy search (`difflib.SequenceMatcher` >= 0.92) flags `partially_verified` and records `model_quote`.
- **Clause Boundary Verification**: Regex `(?<![\d.])1\.1(?![\d])` prevents false positives (e.g., `1.1` matching `11.12`).
- **Threshold Extraction**: Generic numeric extraction accommodates Indian numbering (`5,00,000`), multipliers (`lakh`, `crore`), durations, and percentage values.
- **Near-Duplicate Deduplication**: `difflib.SequenceMatcher` (>= 0.90) identifies and removes cross-chunk duplicates.
- **Resilience**: Per-chunk try/except with exponential backoff (up to 3 retries), batch-splitting on failure, and schema validation re-prompting.

---

## Output Schemas (`schema_version: "1.1.0"`)

### Migration Note: 1.0.0 to 1.1.0
Schema 1.1.0 adds the following fields while maintaining backwards compatibility through property aliases:
- Added `schema_version: "1.1.0"`.
- Added `extraction_run_id` across all output files for versioned runs.
- Added `evidence_confidence` and `model_reported_confidence` (replacing opaque self-reported confidence).
- Added `model_quote`, `excerpt_char_start`, `excerpt_char_end`.
- Added `baseline_citation`, `changed_values`, `review_reasons`, and `extraction_method`.
- Replaced arbitrary quality scores with measured verification metrics (`evidence_pass_rate`).
- Added aliases: `change_type` -> `change_classification`, `source_page` -> `page_number`, `deadline` -> `deadline_or_frequency`, `validation_status` -> `verification_status`.

---

### 1. `extracted_obligations.json`
```json
{
  "schema_version": "1.1.0",
  "workflow_id": "string",
  "extraction_run_id": "string | null",
  "timestamp": "ISO-8601 UTC string",
  "total_obligations": 5,
  "obligations": [
    {
      "obligation_id": "OBL-001",
      "clause_id": "2.1",
      "text": "Transaction monitoring threshold is 250,000 INR for retail accounts.",
      "applicability": "retail accounts",
      "product_type": "retail_banking",
      "amount_threshold": 250000.0,
      "currency": "INR",
      "effective_date": "2026-04-01",
      "responsible_function": "Compliance",
      "required_action": "Apply 250,000 threshold",
      "deadline_or_frequency": "immediate",
      "exceptions": [],
      "source": {
        "document_id": "doc123",
        "filename": "amendment.pdf",
        "document_type": "amendment",
        "page": 1,
        "excerpt": "...",
        "chunk_id": "doc123-p1-c2"
      },
      "supporting_excerpt": "Exact quote from page text",
      "confidence": 0.95,
      "evidence_confidence": 0.95,
      "model_reported_confidence": 0.95,
      "ambiguities": [],
      "change_classification": "MODIFIED",
      "previous_requirement": "Transaction monitoring threshold is 100,000 INR",
      "amended_requirement": "Transaction monitoring threshold is 250,000 INR",
      "source_document": "amendment.pdf",
      "page_number": 1,
      "surrounding_context": "Full neighbouring chunk context...",
      "verification_status": "verified",
      "model_quote": null,
      "excerpt_char_start": 120,
      "excerpt_char_end": 185,
      "baseline_citation": {
        "document_id": "base01",
        "filename": "baseline.pdf",
        "document_type": "baseline_policy",
        "page": 1,
        "excerpt": "...",
        "chunk_id": "base01-p1-c2"
      },
      "changed_values": [
        {"field": "threshold_or_duration", "old": 100000.0, "new": 250000.0}
      ],
      "review_reasons": [],
      "extraction_method": "deterministic_verified",
      "baseline_available": true
    }
  ]
}
```

---

### 2. `amendment_comparison.json`
```json
{
  "schema_version": "1.1.0",
  "workflow_id": "string",
  "extraction_run_id": "string | null",
  "timestamp": "ISO-8601 UTC string",
  "summary": {
    "new": 1,
    "modified": 2,
    "unchanged": 1,
    "superseded": 1,
    "potential_conflict": 0,
    "needs_review": 0
  },
  "total_analyzed": 5,
  "comparison_items": [
    {
      "obligation_id": "OBL-001",
      "clause_id": "2.1",
      "classification": "MODIFIED",
      "baseline_requirement": "Old requirement text",
      "amended_requirement": "New requirement text",
      "effective_date": "2026-04-01",
      "responsible_function": "Compliance",
      "changed_values": [
        {"field": "threshold_or_duration", "old": 100000.0, "new": 250000.0}
      ],
      "baseline_citation": {},
      "source_document": "amendment.pdf",
      "page_number": 1
    }
  ]
}
```

---

### 3. `evidence_and_citations.json`
```json
{
  "schema_version": "1.1.0",
  "workflow_id": "string",
  "extraction_run_id": "string | null",
  "timestamp": "ISO-8601 UTC string",
  "total_citations": 5,
  "evidence": [
    {
      "obligation_id": "OBL-001",
      "clause_id": "2.1",
      "source_document": "amendment.pdf",
      "page_number": 1,
      "exact_supporting_excerpt": "Exact quote from document",
      "model_quote": null,
      "excerpt_char_start": 120,
      "excerpt_char_end": 185,
      "surrounding_context": "Real neighbouring context",
      "verification_status": "verified",
      "confidence": 0.95,
      "evidence_confidence": 0.95,
      "model_reported_confidence": 0.95,
      "ambiguities": [],
      "review_reasons": []
    }
  ]
}
```

---

### 4. `coverage_report.json`
```json
{
  "schema_version": "1.1.0",
  "workflow_id": "string",
  "extraction_run_id": "string | null",
  "documents_count": 2,
  "document_names": ["baseline.pdf", "amendment.pdf"],
  "pages_total": 4,
  "pages_with_text": 4,
  "pages_ocr": 0,
  "pages_skipped": [],
  "pages_with_obligations": [1, 2],
  "chunks_total": 8,
  "chunks_processed": 8,
  "chunks_failed": 0,
  "chunks_skipped": 0,
  "coverage_percentage": 100.0,
  "clauses_detected": ["1.1", "2.1", "3.1", "5.1", "6.1"],
  "clauses_with_obligations": ["1.1", "2.1", "3.1", "5.1", "6.1"],
  "candidate_misses": [],
  "missing_clauses": [],
  "duplicates_removed": 0,
  "duplicate_pairs": [],
  "verification_breakdown": {
    "verified_quotes": 5,
    "partially_verified_quotes": 0,
    "unverified_quotes": 0,
    "clause_verified": 5,
    "threshold_verified": 2,
    "baseline_matched": 4,
    "evidence_pass_rate": 100.0
  },
  "review_routing": []
}
```

---

### 5. `execution_metadata.json`
```json
{
  "schema_version": "1.1.0",
  "workflow_id": "string",
  "agent": "Agent 1 - Obligation Extraction",
  "extraction_run_id": "string | null",
  "timestamp": "ISO-8601 UTC string",
  "status": "completed | completed_with_errors | failed",
  "started_at": "ISO-8601 UTC string",
  "finished_at": "ISO-8601 UTC string",
  "duration_seconds": 1.45,
  "documents_processed": 2,
  "document_names": ["baseline.pdf", "amendment.pdf"],
  "total_obligations": 5,
  "change_breakdown": {"new": 1, "modified": 2, "unchanged": 1, "superseded": 1},
  "llm_calls_count": 4,
  "retries_count": 0,
  "chunk_status_table": {
    "doc123-p1-c1": {"status": "processed", "attempts": 1, "error": null, "duration_ms": 25}
  }
}
```

---

## Tesseract OCR Installation

### Linux / Docker
Tesseract is installed as a system dependency:
```bash
apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
```

### Windows
1. Download and run the official installer from UB-Mannheim:
   `https://github.com/UB-Mannheim/tesseract/wiki`
   or install via Windows Package Manager:
   ```powershell
   winget install UB-Mannheim.TesseractOCR
   ```
2. Add the Tesseract directory (typically `C:\Program Files\Tesseract-OCR`) to your system `PATH`.
3. Verify installation:
   ```powershell
   tesseract --version
   ```

> **Note:** If Tesseract is not installed, PyMuPDF OCR is safely bypassed. Scanned pages are logged as `ocr_status="unavailable"` and flagged for human review without crashing the pipeline.

---

## Running Tests & Evaluation

### 1. Run Complete Test Suite
```powershell
.\.venv\Scripts\python -m pytest tests/ -v
```

### 2. Generate Synthetic Fixtures
```powershell
.\.venv\Scripts\python tests/fixtures/agent1/build_fixtures.py
```

### 3. Run Agent 1 Benchmark Evaluation (Stub Mode)
```powershell
.\.venv\Scripts\python tests/eval/evaluate_agent1.py
```

### 4. Run Agent 1 Benchmark Evaluation (Live LLM Mode)
```powershell
$env:CIDAN_RUN_LLM_INTEGRATION="1"
$env:GROQ_API_KEY="your-groq-api-key"
.\.venv\Scripts\python tests/eval/evaluate_agent1.py
```
Output results are written to:
- `tests/eval/results/agent1_eval.json`
- `tests/eval/results/agent1_eval_summary.md`
