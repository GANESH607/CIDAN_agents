import json
import os
import re
import sys
import time
from pathlib import Path
import difflib

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from langchain_core.documents import Document
from cidan.ingestion import pdf_loader, chunking
from cidan.agents import circular_understanding
from cidan.agents.amendment_alignment import normalize_text
from cidan.models import Obligation

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures" / "agent1"
GOLD_DIR = FIXTURES_DIR / "gold"
RESULTS_DIR = ROOT_DIR / "tests" / "eval" / "results"


def make_stub_llm():
    """Deterministic stub LLM for reproducible testing of pipeline verification logic."""
    def stub(schema, _sys, prompt):
        candidates = []
        # Find passage labels and contents
        passages = re.findall(r"\[(\{.*?\})\]\n(.*?)(?=\n\n\[\{|\Z)", prompt, re.DOTALL)
        for meta_json, content in passages:
            meta = json.loads(meta_json)
            chunk_id = meta.get("chunk_id", "")
            lines = content.strip().split("\n")
            for line in lines:
                line_clean = line.strip()
                if not line_clean:
                    continue

                # Table row detection
                if line_clean.startswith("[TABLE ") and " ROW " in line_clean:
                    cells = dict(re.findall(r"([^|=]+)=([^|]+)", line_clean))
                    cid = "not_specified"
                    for k, v in cells.items():
                        if "clause" in k.lower():
                            cid = v.strip().replace("Clause", "").strip()

                    revised = None
                    existing = None
                    for k, v in cells.items():
                        if any(w in k.lower() for w in ("revised", "new", "amended")):
                            revised = v.strip()
                        if any(w in k.lower() for w in ("existing", "old", "previous")):
                            existing = v.strip()

                    text = revised or list(cells.values())[-1].strip()
                    candidates.append(circular_understanding.ObligationCandidate(
                        source_chunk_id=chunk_id,
                        clause_id=cid,
                        text=text,
                        applicability="regulated entities",
                        product_type="compliance",
                        responsible_function="Operations",
                        required_action=text,
                        supporting_excerpt=line_clean,
                        confidence=0.95,
                        change_classification="MODIFIED" if existing else "NEW",
                        previous_requirement=existing,
                        amended_requirement=revised,
                    ))
                    continue

                # Clause lines
                m = re.search(r"\bClause\s*([0-9]+(?:\.[0-9]+)*)[:\s]*(.*)", line_clean, re.IGNORECASE)
                if m:
                    cid = m.group(1).strip()
                    desc = m.group(2).strip()
                    # extract numbers if any
                    num_match = re.search(r"(\d[\d,]*(?:\.\d+)?)", desc)
                    thresh = float(num_match.group(1).replace(",", "")) if num_match else None

                    candidates.append(circular_understanding.ObligationCandidate(
                        source_chunk_id=chunk_id,
                        clause_id=cid,
                        text=desc or line_clean,
                        applicability="regulated entities",
                        product_type="compliance",
                        amount_threshold=thresh,
                        currency="INR" if "INR" in desc else None,
                        responsible_function="Compliance",
                        required_action=desc or line_clean,
                        supporting_excerpt=line_clean,
                        confidence=0.90,
                        change_classification="NEW",
                    ))

        return schema(obligations=candidates)
    return stub


def run_evaluation() -> dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    is_live = bool(os.getenv("CIDAN_RUN_LLM_INTEGRATION") == "1" and os.getenv("GROQ_API_KEY"))
    llm_mode = "live" if is_live else "stub"
    llm_call = None if is_live else make_stub_llm()

    gold_files = sorted(GOLD_DIR.glob("*.json"))
    if not gold_files:
        raise FileNotFoundError("No gold files found in tests/fixtures/agent1/gold/")

    per_fixture_results = {}
    total_tp = 0
    total_fp = 0
    total_fn = 0
    citation_correct = 0
    citation_total = 0
    change_type_correct = 0
    change_type_total = 0
    confusion_matrix: dict[str, dict[str, int]] = {}
    valid_outputs_count = 0
    total_obligations_evaluated = 0

    all_possible_types = ["NEW", "MODIFIED", "UNCHANGED", "SUPERSEDED", "POTENTIAL_CONFLICT", "NEEDS_REVIEW"]
    for t1 in all_possible_types:
        confusion_matrix[t1] = {t2: 0 for t2 in all_possible_types}

    for gf in gold_files:
        gold_data = json.loads(gf.read_text(encoding="utf-8"))
        fixture_name = gold_data["fixture_name"]
        pdf_path = FIXTURES_DIR / fixture_name
        if not pdf_path.is_file():
            continue

        input_docs = pdf_loader.load_pdf(pdf_path)
        # If there is a baseline fixture, load and tag it
        if gold_data.get("baseline_fixture"):
            base_path = FIXTURES_DIR / gold_data["baseline_fixture"]
            if base_path.is_file():
                base_docs = pdf_loader.load_pdf(base_path)
                for b in base_docs:
                    b.metadata["role"] = "baseline"
                for d in input_docs:
                    d.metadata["role"] = "regulatory"
                input_docs = input_docs + base_docs

        chunks = chunking.split_documents(input_docs, chunk_size=1000)
        wf_id = f"eval-{fixture_name.replace('.pdf', '')}"
        extracted = circular_understanding.run(chunks, llm_call=llm_call, workflow_id=wf_id)

        expected_obls = gold_data.get("expected_obligations", [])
        matched_expected = set()
        fixture_tp = 0
        fixture_fp = 0

        for ext in extracted:
            total_obligations_evaluated += 1
            # Structured output check
            try:
                Obligation.model_validate(ext)
                valid_outputs_count += 1
            except Exception:
                pass

            # Match against expected gold items
            matched_gold_idx = None
            for idx, exp in enumerate(expected_obls):
                if idx in matched_expected:
                    continue
                # Match by clause_id and text similarity
                clause_match = (ext.clause_id == exp["clause_id"] or ext.clause_id in exp["clause_id"] or exp["clause_id"] in ext.clause_id)
                sim = difflib.SequenceMatcher(None, normalize_text(exp["key_phrase"]), normalize_text(ext.text)).ratio()
                if clause_match or sim >= 0.45 or exp["key_phrase"].lower() in ext.text.lower():
                    matched_gold_idx = idx
                    break

            if matched_gold_idx is not None:
                matched_expected.add(matched_gold_idx)
                fixture_tp += 1
                exp_item = expected_obls[matched_gold_idx]

                # Citation accuracy check
                citation_total += 1
                if ext.supporting_excerpt and ext.supporting_excerpt in ext.surrounding_context:
                    citation_correct += 1

                # Change type accuracy & confusion matrix
                exp_type = exp_item.get("expected_change_type", "NEW")
                pred_type = ext.change_classification
                change_type_total += 1
                if pred_type == exp_type:
                    change_type_correct += 1
                if exp_type in confusion_matrix and pred_type in confusion_matrix[exp_type]:
                    confusion_matrix[exp_type][pred_type] += 1
            else:
                fixture_fp += 1

        fixture_fn = len(expected_obls) - len(matched_expected)
        total_tp += fixture_tp
        total_fp += fixture_fp
        total_fn += fixture_fn

        f_prec = round(fixture_tp / max(1, fixture_tp + fixture_fp), 3)
        f_rec = round(fixture_tp / max(1, fixture_tp + fixture_fn), 3)
        f_f1 = round(2 * f_prec * f_rec / max(0.001, f_prec + f_rec), 3)

        per_fixture_results[fixture_name] = {
            "expected_count": len(expected_obls),
            "extracted_count": len(extracted),
            "true_positives": fixture_tp,
            "false_positives": fixture_fp,
            "false_negatives": fixture_fn,
            "precision": f_prec,
            "recall": f_rec,
            "f1": f_f1,
        }

    overall_prec = round(total_tp / max(1, total_tp + total_fp), 3)
    overall_rec = round(total_tp / max(1, total_tp + total_fn), 3)
    overall_f1 = round(2 * overall_prec * overall_rec / max(0.001, overall_prec + overall_rec), 3)
    citation_accuracy = round(citation_correct / max(1, citation_total), 3)
    change_type_acc = round(change_type_correct / max(1, change_type_total), 3)
    validity_rate = round(valid_outputs_count / max(1, total_obligations_evaluated), 3)

    eval_report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "llm_mode": llm_mode,
        "note": (
            "Stub-mode scores test the pipeline's deterministic verification, alignment, "
            "table parsing, and validation logic, not the generative capabilities of an LLM."
            if llm_mode == "stub"
            else "Live Groq LLM extraction against synthetic gold fixtures."
        ),
        "overall_metrics": {
            "obligation_precision": overall_prec,
            "obligation_recall": overall_rec,
            "obligation_f1": overall_f1,
            "citation_accuracy": citation_accuracy,
            "change_type_accuracy": change_type_acc,
            "structured_output_validity_rate": validity_rate,
            "total_obligations_extracted": total_obligations_evaluated,
            "fixtures_evaluated_count": len(per_fixture_results),
        },
        "confusion_matrix": confusion_matrix,
        "per_fixture": per_fixture_results,
    }

    # Save JSON results
    json_path = RESULTS_DIR / "agent1_eval.json"
    json_path.write_text(json.dumps(eval_report, indent=2), encoding="utf-8")

    # Generate Markdown Summary
    md_lines = [
        f"# Agent 1 Evaluation Report ({llm_mode.upper()} mode)",
        "",
        f"**Date:** {eval_report['timestamp']}  ",
        f"**LLM Mode:** `{llm_mode}`  ",
        f"> **Notice:** {eval_report['note']}",
        "",
        "## Overall Metrics",
        f"- **Obligation Precision:** {overall_prec * 100:.1f}%",
        f"- **Obligation Recall:** {overall_rec * 100:.1f}%",
        f"- **Obligation F1:** {overall_f1 * 100:.1f}%",
        f"- **Citation Accuracy:** {citation_accuracy * 100:.1f}%",
        f"- **Change-Type Classification Accuracy:** {change_type_acc * 100:.1f}%",
        f"- **Structured-Output Validity Rate:** {validity_rate * 100:.1f}%",
        "",
        "## Per-Fixture Performance",
        "| Fixture | Expected | Extracted | Precision | Recall | F1 |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for fix_name, fix_metrics in per_fixture_results.items():
        md_lines.append(
            f"| `{fix_name}` | {fix_metrics['expected_count']} | {fix_metrics['extracted_count']} | "
            f"{fix_metrics['precision']:.3f} | {fix_metrics['recall']:.3f} | {fix_metrics['f1']:.3f} |"
        )

    md_lines.extend([
        "",
        "## Change Type Confusion Matrix",
        "| Expected \\ Predicted | NEW | MODIFIED | UNCHANGED | SUPERSEDED | POTENTIAL_CONFLICT | NEEDS_REVIEW |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ])
    for exp_t in all_possible_types:
        row = [f"**{exp_t}**"]
        for pred_t in all_possible_types:
            row.append(str(confusion_matrix[exp_t].get(pred_t, 0)))
        md_lines.append("| " + " | ".join(row) + " |")

    md_path = RESULTS_DIR / "agent1_eval_summary.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return eval_report


if __name__ == "__main__":
    rep = run_evaluation()
    print(json.dumps(rep["overall_metrics"], indent=2))
