"""Study 3 design review, step 1 (plan Task 7): blind packets for every study-3 arm plus
the study-2 F chain packets, ONE seeded shuffled batch file over all of them (at most one
packet per chain in a batch), and the judges' trees (one neutral repository, one commit
per packet). No judge runs here (rubric: docs/design-review-rubric.md, study-3
addendum).

  uv run python scripts/study3_review_packets.py [--runs runs3] [--f-runs runs2]
      [--out work/review3] [--mapping work/review3-mapping.json]

Writes <out>/packets/<id>/, <out>/apply-check.json, <out>/batches.json and
<out>/trees/<neutral name>/ (bare); the mapping (packet id -> agent/arm/zone/chain/
step) goes outside <out> and is never shown to judges."""
import argparse
import sys
from collections import Counter
from pathlib import Path

from aa import config, review3
from aa.chain_eval import TASKS2
from aa.chains import TASKS3


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runs", type=Path, default=review3.RUNS3)
    ap.add_argument("--f-runs", type=Path, default=config.ROOT / "runs2")
    ap.add_argument("--out", type=Path, default=review3.REVIEW3)
    ap.add_argument("--mapping", type=Path, default=review3.MAPPING3)
    ap.add_argument("--variants", type=Path, default=config.WORK / "variants")
    ap.add_argument("--tasks", type=Path, default=TASKS2)
    ap.add_argument("--tasks3", type=Path, default=TASKS3)
    ap.add_argument("--seed", type=int, default=review3.SEED)
    a = ap.parse_args(argv)
    rep, mapping, batches = review3.export_and_batch(
        a.runs.resolve(), a.out, a.mapping, f_runs=a.f_runs.resolve(), tasks_root=a.tasks,
        tasks3_root=a.tasks3, variants_root=a.variants, seed=a.seed)
    kinds = Counter((m["cond"], m["kind"]) for m in mapping.values())
    for (cond, kind), n in sorted(kinds.items()):
        print(f"{cond}\t{kind}\t{n}")
    print(f"{len(rep['ok'])} packet(s), {len(rep['bad'])} not exported (apply-check.json); "
          f"{len(batches['main'])} main batch(es), "
          f"{sum(map(len, batches['second']))} packet(s) for the second judge")
    return 1 if rep["bad"] else 0


if __name__ == "__main__":
    sys.exit(main())
