"""Descriptive, chain-aware analysis of exported calls. No model calls."""
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
import argparse
import protocol
import bank


def analyze(data):
    tasks = {t["id"]: t for t in data["tasks"]}
    parsed, invalid, usage, attempts = {}, [], defaultdict(Counter), []
    rows = []
    groups = defaultdict(Counter)
    invalid_generation = []
    for record in data["records"]:
        j, r = record["job"], record["attempts"][-1]
        for a in record["attempts"]:
            attempts.append(a)
            u = a.get("usage", {})
            usage[j["model_id"]]["input"] += u.get("input_tokens", u.get("prompt_tokens", 0))
            usage[j["model_id"]]["output"] += u.get("output_tokens", u.get("completion_tokens", 0))
        if j["stage"] not in ("visible", "final"):
            try:
                if r["status"] != "ok" or r.get("truncated"):
                    raise ValueError("Non-complete generation")
                protocol.guide(r["text"])
            except (ValueError, TypeError, KeyError):
                invalid_generation.append({"chain": j["chain_id"], "stage": j["stage"],
                                           "text": r.get("text", "")})
            continue
        cases = [c for c in tasks[j["task_id"]]["cases"] if j["stage"] == "final" or c["visible"]]
        for c in cases:
            subsets = ["all", "visible" if c["visible"] else "reserved"]
            if c["separating"]:
                subsets.append("separating")
            for subset in subsets:
                groups[(j["model_id"], j.get("variant", "visible"), subset)]["expected"] += 1
        key = (j["chain_id"], j["model_id"], j.get("variant", "visible"), j.get("repetition", 0))
        try:
            if r["status"] != "ok" or r.get("truncated"):
                raise ValueError("Non-complete response")
            labels = protocol.decisions(r["text"], cases)
        except (ValueError, TypeError, KeyError):
            invalid.append({"chain": j["chain_id"], "model": j["model_id"],
                            "stage": j["stage"], "variant": j.get("variant"),
                            "repetition": j.get("repetition"), "text": r.get("text", "")})
            continue
        parsed[key] = labels
        for c in cases:
            rows.append(dict(chain=j["chain_id"], task=j["task_id"], model=j["model_id"],
                stage=j["stage"], variant=j.get("variant", "visible"), repetition=j.get("repetition", 0),
                input_id=c["id"], visible=c["visible"], separating=c["separating"],
                expected=c["expected"], simplified=c["simplified"], action=labels[c["id"]]))
    for row in rows:
        for subset in ("all", "visible" if row["visible"] else "reserved"):
            key = (row["model"], row["variant"], subset)
            groups[key]["valid"] += 1
            groups[key]["correct"] += row["action"] == row["expected"]
        if row["separating"]:
            key = (row["model"], row["variant"], "separating")
            groups[key]["valid"] += 1
            groups[key]["correct"] += row["action"] == row["expected"]
    chains, drift, rename_effects, unstable = [], [], [], []
    transitions = Counter()
    for cid, artifacts in data["plans"]["final"]["artifacts"].items():
        task = tasks[cid.split("--")[0]]
        info = {"chain": cid, **artifacts, "executors": {}}
        for artifact in ("source", "received"):
            if artifacts.get(artifact):
                info[artifact + "_words"] = len(artifacts[artifact]["guide"].split())
        for model in ("gpt-sol", "claude-opus"):
            initial = parsed.get((cid, model, "visible", 0))
            tests = [c for c in task["cases"] if c["visible"]]
            initial_pass = initial is not None and all(initial[c["id"]] == c["expected"] for c in tests)
            result = {"initial_visible_pass": initial_pass, "variants": {}}
            for variant in ("canonical", "source", "received", "renamed"):
                samples = [parsed.get((cid, model, variant, r)) for r in range(2)]
                result["variants"][variant] = {
                    "valid_repetitions": sum(x is not None for x in samples),
                    "all_correct": all(s is not None and all(s[c["id"]] == c["expected"] for c in task["cases"]) for s in samples),
                    "visible_pass_both": all(s is not None and all(s[c["id"]] == c["expected"] for c in tests) for s in samples),
                    "reserved_errors": [c["id"] for c in task["cases"] if not c["visible"] and
                        any(s is not None and s[c["id"]] != c["expected"] for s in samples)]}
            info["executors"][model] = result
            for c in task["cases"]:
                obs = {v: [parsed.get((cid, model, v, r), {}).get(c["id"]) for r in range(2)]
                       for v in ("canonical", "source", "received", "renamed")}
                stable = {v: a[0] is not None and a[0] == a[1] for v, a in obs.items()}
                base = dict(chain=cid, model=model, input_id=c["id"], input=c["input"],
                            visible=c["visible"], expected=c["expected"], simplified=c["simplified"], observations=obs)
                if all(stable[v] for v in ("canonical", "source", "received")) and obs["canonical"][0] == c["expected"]:
                    old, new = obs["source"][0], obs["received"][0]
                    if old == new == c["expected"]:
                        category = "preserved_correct"
                    elif old == c["expected"]:
                        category = "introduced_error"
                    elif new == c["expected"]:
                        category = "repaired_error"
                    elif old == new:
                        category = "persistent_same_error"
                    else:
                        category = "changed_error"
                    transitions[category] += 1
                for v, a in obs.items():
                    if None not in a and a[0] != a[1]:
                        unstable.append({**base, "variant": v})
                if all(stable[v] for v in ("canonical", "source", "received")) and (
                        obs["canonical"][0] == obs["source"][0] == c["expected"] != obs["received"][0]):
                    drift.append({**base, "matches_simplification": obs["received"][0] == c["simplified"]})
                if stable["received"] and stable["renamed"] and obs["received"][0] != obs["renamed"][0]:
                    rename_effects.append(base)
        info["both_initial_visible_pass"] = all(v["initial_visible_pass"] for v in info["executors"].values())
        chains.append(info)
    costs = []
    for model, u in usage.items():
        rates = (4, 20) if model == "gpt-sol" else (5, 25)
        costs.append(dict(model=model, **u, reference_usd=(u["input"]*rates[0]+u["output"]*rates[1])/1e6))
    return dict(analysis_sha256=bank.digest(Path(__file__).read_text()),
        calls=len(data["records"]), attempts=len(attempts), invalid=invalid,
        invalid_generation=invalid_generation,
        wall_seconds=(max(datetime.fromisoformat(a["finished"]) for a in attempts) -
                      min(datetime.fromisoformat(a["started"]) for a in attempts)).total_seconds(),
        costs=costs, groups=[dict(model=k[0], variant=k[1], subset=k[2], **v) for k,v in groups.items()],
        chains=chains, stable_transitions=dict(transitions),
        stable_drift=drift, stable_rename_effects=rename_effects,
        unstable_inputs=unstable, rows=rows)


def markdown(report):
    lines = ["# Third study: a definition across an agent handoff", "",
        "Descriptive exploratory results. Four policies, eight source chains; repeated",
        "inputs and calls are not independent conceptual discoveries. Names were requested",
        "deliberately. The study does not measure spontaneous jargon or long-term adoption.", "",
        f"Completed call records: {report['calls']}; attempts: {report['attempts']}; "
        f"invalid execution outputs: {len(report['invalid'])}; "
        f"invalid generations: {len(report['invalid_generation'])}.", "",
        "## Correctness", "",
        "Expected denominators cover planned calls. A missing dependent variant following",
        "invalid generation is listed under chains rather than counted as a correct call.", "",
        "| Executor | Guide | Inputs | Correct / valid / expected |",
        "|---|---|---|---|"]
    for g in report["groups"]:
        if g["subset"] != "all":
            lines.append(f"| {g['model']} | {g['variant']} | {g['subset']} | "
                         f"{g.get('correct',0)} / {g.get('valid',0)} / {g['expected']} |")
    lines += ["", "## Each chain", ""]
    for c in report["chains"]:
        lines += [f"### {c['chain']}", "",
            f"Both initial executors passed visible cases: **{c['both_initial_visible_pass']}**.", ""]
        for which in ("source", "received"):
            artifact = c.get(which)
            if artifact:
                lines += [f"**{which}** — {artifact['term']} ({c[which+'_words']} words)", "",
                          artifact['guide'], ""]
            else:
                lines += [f"**{which}: unavailable**", ""]
        if c.get("received"):
            lines += [f"Occurrences of the local name inside the received executable guide: "
                      f"{c.get('rename_occurrences',0)}. Metadata name retained: {c.get('name_retained')}.", ""]
        lines += ["| Executor | Guide | Valid repetitions | Visible pass in both | Reserved inputs with errors |",
                  "|---|---|---|---|---|"]
        for mid, ex in c["executors"].items():
            for v, r in ex["variants"].items():
                lines.append(f"| {mid} | {v} | {r['valid_repetitions']} | {r['visible_pass_both']} | "
                             f"{', '.join(r['reserved_errors']) or '—'} |")
        lines.append("")
    for title, key in [("Repeated handoff losses with correct source and canonical policy", "stable_drift"),
                       ("Repeated effects of renaming alone", "stable_rename_effects")]:
        lines += ["## " + title, "", f"Input–executor–chain combinations: **{len(report[key])}**.", ""]
        for e in report[key]:
            lines += [f"- {e['chain']} / {e['model']} / {e['input_id']}: "
                      f"expected {e['expected']}, simpler rule {e['simplified']}; "
                      f"observed `{json.dumps(e['observations'])}`."]
    lines += ["", "## Usage and reference cost", "",
        f"First-to-last call: {report['wall_seconds']:.1f} seconds.", "",
        "Costs use the previous pilot's reference rates, not a provider invoice; exclude",
        "implementation, Codex assistance and previous studies.", ""]
    for c in report["costs"]:
        lines.append(f"- {c['model']}: {c['input']} input / {c['output']} output tokens; "
                     f"USD {c['reference_usd']:.4f}.")
    return "\n".join(lines)+"\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = analyze(json.loads((args.out / "data.json").read_text()))
    (args.out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    (args.out / "report.md").write_text(markdown(report))
    short = {k:v for k,v in report.items() if k not in ("rows", "chains", "invalid", "unstable_inputs")}
    short["invalid_calls"] = len(report["invalid"])
    short["unstable_input_conditions"] = len(report["unstable_inputs"])
    print(json.dumps(short, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
