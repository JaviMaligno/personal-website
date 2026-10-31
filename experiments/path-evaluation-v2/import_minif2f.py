"""Turn miniF2F (Lean 4, MIT, github.com/yangky11/miniF2F-lean4 @ 5746b7d) problems into tasks.

    uv run python import_minif2f.py induction_12dvd4expnp1p20 ...

maxHeartbeats 0 (unlimited) becomes 400000 so a runaway tactic cannot hang the machine.
"""
import json
import sys
from pathlib import Path

SRC = Path.home() / "lean" / "miniF2F-lean4" / "MiniF2F" / "Test"
OUT = Path(__file__).parent / "theorems-mathlib"

OUT.mkdir(exist_ok=True)
for name in sys.argv[1:]:
    text = (SRC / f"{name}.lean").read_text(encoding="utf-8").replace("maxHeartbeats 0", "maxHeartbeats 400000")
    i = text.index("theorem ")
    statement = text[i:text.rindex(":= by")].rstrip()
    task = {"id": f"f2f-{name}", "name": name, "difficulty": "minif2f", "prelude": text[:i],
            "statement": statement, "proofs": [], "source": "miniF2F-lean4 @ 5746b7d (MIT)"}
    (OUT / f"f2f-{name}.json").write_text(json.dumps(task, ensure_ascii=False, indent=1), encoding="utf-8")
    print(task["id"])
