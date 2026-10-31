"""Check the author's (Astra's) miniF2F proofs with the experiment's own judge before a problem may
enter the Mathlib trial: statement intact, compiles, no sorry, standard axioms only.

    uv run python verify_f2f_proofs.py C:/Users/Usuario/lean/astra-f2f/out
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import agents
import world_b

SRC = Path.home() / "lean" / "miniF2F-lean4" / "MiniF2F" / "Test"
os.environ["LEAN_PATH"] = agents.env_for("c")["LEAN_PATH"]

for proof in sorted(Path(sys.argv[1]).glob("*.lean")):
    name = proof.stem
    text = (SRC / f"{name}.lean").read_text(encoding="utf-8").replace("maxHeartbeats 0", "maxHeartbeats 400000")
    i = text.index("theorem ")
    task = {"id": f"f2f-{name}", "name": name, "prelude": text[:i],
            "statement": text[i:text.rindex(":= by")].rstrip(), "proofs": []}
    with tempfile.TemporaryDirectory() as d:
        work = world_b.materialize(task, Path(d) / "w")
        (work / "Main.lean").write_text(proof.read_text(encoding="utf-8"), encoding="utf-8")
        try:
            j = world_b.judge(task, work, [])
        except subprocess.TimeoutExpired:  # a proof agents could not re-check in time is no use either
            print(name, "TIMEOUT (> 300 s to compile)", flush=True)
            continue
    print(name, "VALID" if j["truth"] else "INVALID",
          json.dumps({k: j[k] for k in ("E0", "sorry", "statement_intact", "axioms")}), flush=True)
