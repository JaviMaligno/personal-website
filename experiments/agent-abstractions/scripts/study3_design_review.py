"""Study 3 design review, analysis (plan Task 7), as pre-registered in
docs/design-review-rubric.md (study-3 addendum). Reads the judges' files (first judge
<review>/scores/<id>.json, second judge <review>/scores2/<id>.json; study 2's
abbreviated JSON shape is tolerated, aa.review3.normalise), reports agreement (kappa)
FIRST (and writes it as the flat JSON `aa tables3 --kappa` reads, --kappa-out), then,
only when the second judge has scored every packet of the planned second sample
(<review>/batches.json "second"), writes the labels JSON for `aa tables3 --labels` and the
H1 tables (per agent, each lever arm vs R and vs F, chain diffs primary). Otherwise the
labels and comparisons are refused (kappa before any comparison), unless
--allow-no-kappa.

  uv run python scripts/study3_design_review.py [--review work/review3]
      [--mapping work/review3-mapping.json] [--labels out/study3/design-labels.json]
      [--kappa-out out/study3/design-kappa.json] [--out out/study3/design_review3.md]"""
import argparse
import json
import sys
from pathlib import Path

from aa import config, review3


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--review", type=Path, default=review3.REVIEW3)
    ap.add_argument("--mapping", type=Path, default=review3.MAPPING3)
    ap.add_argument("--labels", type=Path, default=config.ROOT / "out/study3/design-labels.json")
    ap.add_argument("--out", type=Path, default=config.ROOT / "out/study3/design_review3.md")
    ap.add_argument("--kappa-out", type=Path,
                    default=config.ROOT / "out/study3/design-kappa.json",
                    help="flat {measure: kappa} JSON for `aa tables3 --kappa`")
    ap.add_argument("--allow-no-kappa", action="store_true")
    a = ap.parse_args(argv)
    res = review3.analyse(a.review / "scores", a.review / "scores2", a.mapping,
                          labels_out=a.labels, out_md=a.out, kappa_out=a.kappa_out,
                          batches=a.review / "batches.json",
                          allow_no_kappa=a.allow_no_kappa)
    rel = res["reliability"]
    print(f"## Reliability (second judge, {rel['n_packets']} packets)")
    for q, v in rel["questions"].items():
        print(f"{q}: kappa {v['kappa']} (n={v['n']}, {v['kind']})")
    if res["h1"] is None:
        print(res["refused"])
        return 1
    print(f"kappa -> {a.kappa_out}; labels -> {a.labels}; H1 tables -> {a.out}")
    a.out.with_suffix(".json").write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
