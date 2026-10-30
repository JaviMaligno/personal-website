"""Every theorem: each reference proof is true; ≥2 proofs with different tactic multisets."""
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

import world_b

bad = []
for p in sorted(Path(__file__).parent.glob("theorems/*.json")):
    t = json.loads(p.read_text(encoding="utf-8"))
    oks = []
    with tempfile.TemporaryDirectory() as d:
        for i, body in enumerate(t["proofs"]):
            work = world_b.materialize(t, Path(d) / str(i))
            (work / "Main.lean").write_text(world_b.header(t) + " := by\n" + body, encoding="utf-8")
            oks.append(world_b.judge(t, work, [])["truth"])
    multisets = {tuple(sorted(Counter(world_b.tactics(b)).items())) for b in t["proofs"]}
    ok = all(oks) and len(t["proofs"]) >= 2 and len(multisets) >= 2
    print(t["id"], t["difficulty"], "OK" if ok else f"FAIL truth={oks} distinct={len(multisets)}")
    if not ok:
        bad.append(t["id"])
sys.exit(1 if bad else 0)
