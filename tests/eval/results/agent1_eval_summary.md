# Agent 1 Evaluation Report (STUB mode)

**Date:** 2026-11-23T12:57:28Z  
**LLM Mode:** `stub`  
> **Notice:** Stub-mode scores test the pipeline's deterministic verification, alignment, table parsing, and validation logic, not the generative capabilities of an LLM.

## Overall Metrics
- **Obligation Precision:** 100.0%
- **Obligation Recall:** 90.0%
- **Obligation F1:** 94.7%
- **Citation Accuracy:** 100.0%
- **Change-Type Classification Accuracy:** 77.8%
- **Structured-Output Validity Rate:** 100.0%

## Per-Fixture Performance
| Fixture | Expected | Extracted | Precision | Recall | F1 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `amendment_policy.pdf` | 5 | 5 | 1.000 | 1.000 | 1.000 |
| `standalone_kyc_circular.pdf` | 3 | 3 | 1.000 | 1.000 | 1.000 |
| `table_heavy.pdf` | 2 | 1 | 1.000 | 0.500 | 0.667 |

## Change Type Confusion Matrix
| Expected \ Predicted | NEW | MODIFIED | UNCHANGED | SUPERSEDED | POTENTIAL_CONFLICT | NEEDS_REVIEW |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **NEW** | 5 | 0 | 0 | 0 | 0 | 0 |
| **MODIFIED** | 0 | 1 | 0 | 0 | 0 | 1 |
| **UNCHANGED** | 0 | 1 | 0 | 0 | 0 | 0 |
| **SUPERSEDED** | 0 | 0 | 0 | 1 | 0 | 0 |
| **POTENTIAL_CONFLICT** | 0 | 0 | 0 | 0 | 0 | 0 |
| **NEEDS_REVIEW** | 0 | 0 | 0 | 0 | 0 | 0 |