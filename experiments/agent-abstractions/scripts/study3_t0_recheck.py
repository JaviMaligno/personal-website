"""List RC T0 steps evaluated after START (shared gate) with any failing check."""
import glob, json, os, sys
start = float(sys.argv[1])
for f in sorted(glob.glob('runs3/*/RC/*/*/T0/result.json')):
    if os.path.getmtime(f) < start:
        continue
    r = json.load(open(f))
    t0 = r.get('t0_tests') or {}
    bad = (r.get('correct') is not True or r.get('eval_error') or r.get('related_ok') is False
           or r.get('probe_unchanged') is False or r.get('typecheck_ok') is False
           or any(v is False for v in (t0.values() if isinstance(t0, dict) else [])))
    if bad:
        print(os.path.abspath(os.path.dirname(f)))
