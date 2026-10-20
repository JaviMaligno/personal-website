"""Amendment 2026-10-17, load check of T1-T4: re-evaluate at low load every T1-T4 step
evaluated at >= 6 workers (result.json written after 2026-10-16 13:45 BST) whose result is
`correct = false`, then any later step of a chain whose re-evaluated step changed (its
`new_carried_defects` reads the previous result). Two chain-disjoint shards run at once
(the registered evaluation concurrency); steps of a chain run in order. Before/after
values go to out/study3/load-recheck/."""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

RUNS = Path("runs3"); OUT = Path("out/study3/load-recheck"); OUT.mkdir(parents=True, exist_ok=True)
W6 = datetime(2026, 10, 16, 13, 45).timestamp()
KEYS = ("correct", "consumers_passed", "consumers_total", "carried_defects",
        "new_carried_defects", "test_status", "lint_ok", "typecheck_ok", "eval_error")


def snap(d: Path) -> dict:
    r = json.loads((d / "result.json").read_text())
    return {k: r.get(k) for k in KEYS}


def run_shards(steps: list[Path], tag: str) -> None:
    chains: dict[Path, list[Path]] = {}
    for d in sorted(steps):
        chains.setdefault(d.parent, []).append(d)
    shards = [[], []]
    for i, c in enumerate(sorted(chains)):
        shards[i % 2] += chains[c]

    def go(k: int) -> None:
        if shards[k]:
            with open(OUT / f"{tag}-shard{k}.log", "w") as log:
                subprocess.run(["uv", "run", "aa", "chain", "evaluate", "--study", "3",
                                *map(str, shards[k])], stdout=log, stderr=subprocess.STDOUT)

    with ThreadPoolExecutor(2) as ex:
        list(ex.map(go, [0, 1]))


first = [Path(p).parent.resolve() for p in sorted(RUNS.glob("*/*/*/*/T[1-4]/result.json"))
         if os.path.getmtime(p) >= W6 and json.loads(Path(p).read_text()).get("correct") is False]
before = {str(d): snap(d) for d in first}
print(f"pass 1: {len(first)} steps", flush=True)
run_shards(first, "pass1")
changed = [d for d in first if snap(d) != before[str(d)]]
later = sorted({d.parent / f"T{k}" for d in changed for k in range(int(d.name[1]) + 1, 5)
                if (d.parent / f"T{k}" / "result.json").exists()} - set(first))
for d in later:
    before[str(d)] = snap(d)
print(f"pass 2: {len(later)} later steps of {len(changed)} changed", flush=True)
run_shards(later, "pass2")
rows = [{"step": s, "before": b, "after": snap(Path(s)), "pass": 1 if Path(s) in first else 2}
        for s, b in before.items()]
(OUT / "before-after.json").write_text(json.dumps(rows, indent=1) + "\n")
diff = [r for r in rows if r["before"] != r["after"]]
flip = [r for r in diff if r["before"]["correct"] != r["after"]["correct"]]
print(f"done: {len(rows)} re-evaluated, {len(diff)} changed, {len(flip)} changed `correct`", flush=True)
for r in flip:
    print(f"  {r['step'].split('runs3/')[1]}: correct {r['before']['correct']} -> {r['after']['correct']}")
