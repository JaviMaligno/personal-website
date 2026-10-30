"""Validate every bugs/*.json; exit 1 if any check fails. Prints one line per bug."""
import json
import sys
import tempfile
from pathlib import Path

import world_a

bad = []
for p in sorted(Path(__file__).parent.glob("bugs/*.json")):
    bug = json.loads(p.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as t:
        r = world_a.validate(bug, Path(t))
    ok = all(r.values())
    print(bug["id"], "OK" if ok else f"FAIL {r}")
    if not ok:
        bad.append(bug["id"])
sys.exit(1 if bad else 0)
