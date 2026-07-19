"""End-to-end pipeline demo on synthetic data — zero API calls.

    python -m wheresball.demo [--n-items 200] [--seed 0]

Generates a stratified synthetic set, freezes it (manifest + hash), runs the
B0-B4 baselines and the mock VLM through the full harness with caching, and
prints the evaluation report. This is the executable proof that Phases 2-3
plumbing works before any SoccerNet data or model API is touched.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from .baselines import default_baselines
from .dataset import freeze, generate_items
from .harness import BaselineSystem, MockVLMClient, ResponseCache, evaluate, run_matrix
from .schema import Condition, Knowledge, Masking, TemporalContext


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-items", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=Path, default=None, help="working dir (default: temp)")
    args = parser.parse_args()

    workdir = args.out or Path(tempfile.mkdtemp(prefix="wheresball-demo-"))
    print(f"working dir: {workdir}")

    items = generate_items(n_total=args.n_items, seed=args.seed)
    digest = freeze(items, workdir / "eval-set.json")
    print(f"frozen synthetic set: {len(items)} items, sha256 {digest[:16]}…")

    conditions = [
        Condition(TemporalContext.SINGLE_FRAME, Knowledge.NEUTRAL, Masking.NATURAL),
        Condition(TemporalContext.MULTI_FRAME, Knowledge.INFORMED, Masking.NATURAL),
    ]
    systems = [BaselineSystem(b) for b in default_baselines(seed=args.seed)]
    systems.append(MockVLMClient(seed=args.seed))

    cache = ResponseCache(workdir / "cache")
    rows = run_matrix(items, systems, conditions, cache=cache)
    print(f"ran {len(rows)} (system × condition × item) cells; cache size {len(cache)}")

    report = evaluate(rows, items, bootstrap_replicates=2000)

    print("\nmedian localization error (normalized units, first condition):")
    condition_key = conditions[0].key
    ranked = sorted(
        report["systems"].items(),
        key=lambda kv: kv[1][condition_key]["error"]["median"],
    )
    for system, per_condition in ranked:
        entry = per_condition[condition_key]
        lo, hi = entry["error_median_ci95"]
        print(
            f"  {system:24s} median={entry['error']['median']:.3f} "
            f"CI95=[{lo:.3f}, {hi:.3f}]  PCK@0.05={entry['pck'][0.05]:.2f}"
        )

    from .harness import save_report

    save_report(report, workdir / "report.json")
    print(f"\nfull report: {workdir / 'report.json'}")


if __name__ == "__main__":
    main()
