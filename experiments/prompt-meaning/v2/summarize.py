"""Descriptive aggregation of the exported pilot, without additional model calls."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path


def summarize(out):
    data = json.loads((out / "data.json").read_text())
    report = json.loads((out / "report.json").read_text())
    groups = defaultdict(Counter)
    for row in report["prediction_comparisons"]:
        key = (row["kind"], row.get("label_category"), row["explainer"], row["executor"], row["variant"])
        for name, value in row.items():
            if type(value) is int:
                groups[key][name] += value
    authors = defaultdict(Counter)
    cases = {c["id"]: c for c in data["selection"]["cases"]}
    for row in report["correctness"]:
        if row["kind"] != "unmodified":
            continue
        case = cases[row["case_id"]]
        key = (row["task_id"], case["writer_id"], row["model_id"])
        for k in ("correct", "expected_decisions", "valid_decisions"):
            authors[key][k] += row[k]
    costs = []
    for mid, usage in report["usage"].items():
        inputs = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        outputs = usage.get("output_tokens", usage.get("completion_tokens", 0))
        rates = (4, 20) if mid == "gpt-sol" else (5, 25)
        costs.append({"model": mid, "input_tokens": inputs, "output_tokens": outputs,
                      "reference_usd": (inputs * rates[0] + outputs * rates[1]) / 1e6})
    attempts = [a for history in data["records"] for a in history["attempts"]]
    start = min(datetime.fromisoformat(a["started"]) for a in attempts)
    end = max(datetime.fromisoformat(a["finished"]) for a in attempts if "finished" in a)
    summary = {
        "notice": "Descriptive counts; cells reuse four policies and their inputs, not independent samples.",
        "calls": len(data["records"]), "attempts": len(attempts),
        "wall_seconds_including_review": (end - start).total_seconds(),
        "reference_costs": costs,
        "predictions": [{"kind": k[0], "label_category": k[1], "explainer": k[2],
                         "executor": k[3], "variant": k[4], **v} for k, v in groups.items()],
        "handoffs": [{"task": k[0], "writer": k[1], "executor": k[2], **v} for k, v in authors.items()],
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    lines = ["# Agregación descriptiva", "", summary["notice"], "",
        "## Predicciones", "",
        "Pares: repeticiones incluidas. Estables: cada input se cuenta una vez por comparación,",
        "solo cuando ambas variantes coinciden consigo mismas entre las dos repeticiones.", "",
        "| Tipo / etiqueta | Explica → ejecuta | Intervención | Pares evaluables / previstos | Exactos | Abstenciones | Detecta cambio | Sin cambio (referencia) | Exactos / evaluables estables | Inputs inestables |",
        "|---|---|---|---|---|---|---|---|---|---|"]
    for r in summary["predictions"]:
        lines.append(f"| {r['kind']} / {r['label_category'] or '—'} | {r['explainer']} → {r['executor']} | {r['variant']} | "
            f"{r.get('scorable_pairs', 0)}/{r['expected_pairs']} | {r.get('exact_action_pair_matches', 0)} | "
            f"{r.get('abstained_pairs', 0)} | {r.get('change_detection_matches', 0)} | "
            f"{r.get('always_no_change_baseline_matches', 0)} | {r.get('stable_exact_matches', 0)}/{r.get('stable_scorable_inputs', 0)} | "
            f"{r.get('unstable_inputs', 0)} |")
    lines += ["", "## Traspasos sin modificar", "",
              "| Tarea | Escritor | Ejecutor | Correctas / previstas | Válidas |",
              "|---|---|---|---|---|"]
    for r in summary["handoffs"]:
        lines.append(f"| {r['task']} | {r['writer']} | {r['executor']} | {r['correct']}/{r['expected_decisions']} | {r['valid_decisions']} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ('predictions', 'handoffs')}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    summarize(parser.parse_args().out)
