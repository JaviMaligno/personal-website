#!/usr/bin/env python3
"""Accessibility census on Windows: how much of each app does an agent reading the UIA tree see?

Same metrics and same protocol as the macOS census (../an-agent-sees-what-a-screen-reader-sees-census.csv),
so both CSVs can be compared row by row. Only aggregate counts are stored, never names or UI text.

For each app in apps-windows.txt:
  1. note whether it was already running;
  2. launch it if not (agent-desktop launch --activate) and wait;
  3. snapshot its main window 3 times;
  4. close it right away if this script opened it (graceful, then --force).

Usage (PowerShell, from this folder):
  python -I census_windows.py                      # all apps in apps-windows.txt
  python -I census_windows.py --only "Slack" "Spotify"
  python -I census_windows.py --out census-windows.csv --runs 3
"""
import argparse, collections, csv, json, os, platform, subprocess, sys, time

AD = os.environ.get("AGENT_DESKTOP", "agent-desktop")
INTERACTIVE = {"button", "textfield", "textarea", "checkbox", "radiobutton", "link", "menubutton",
               "popupbutton", "combobox", "slider", "switch", "tab", "cell", "menuitem", "searchfield"}


def ad(*args, timeout=120):
    try:
        p = subprocess.run([AD, *args], capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return json.loads(p.stdout)
    except Exception as e:  # timeout, bad JSON, missing binary
        return {"ok": False, "error": {"code": type(e).__name__}}


def running(app, tries=3):
    """True/False when list-apps answers; None when it can't tell (then the app is never closed)."""
    for _ in range(tries):
        j = ad("list-apps", "--app", app)
        if j.get("ok"):
            return bool((j.get("data") or {}).get("apps"))
        time.sleep(2)
    return None


def main_window(app):
    j = ad("list-windows", "--app", app)
    ws = [w for w in (j.get("data") or []) if w.get("bounds", {}).get("height", 0) > 40]
    ws.sort(key=lambda w: w["bounds"]["width"] * w["bounds"]["height"], reverse=True)
    return ws[0]["id"] if ws else None


def snapshot(app, timeout_ms, max_depth, window=None):
    args = ["snapshot", "--app", app, "--timeout-ms", str(timeout_ms), "--max-depth", str(max_depth)]
    if window:
        args += ["--window-id", window]
    t0 = time.time()
    j = ad(*args, timeout=timeout_ms / 1000 + 30)
    ms = int((time.time() - t0) * 1000)
    if not j.get("ok"):
        code = j.get("error", {}).get("code", "ERROR")
        if code == "AMBIGUOUS_TARGET" and not window:
            w = main_window(app)
            if w:
                return snapshot(app, timeout_ms, max_depth, w)
        return None, ms, code
    return j["data"], ms, ""


def metrics(tree):
    roles = collections.Counter(); n = named = inter = tf = 0; maxd = 0
    stack = [(tree, 0)]
    while stack:
        node, d = stack.pop(); n += 1; maxd = max(maxd, d)
        r = node.get("role", ""); roles[r] += 1
        if (node.get("name") or "").strip(): named += 1
        if r in INTERACTIVE or node.get("ref_id"): inter += 1
        if r in ("textfield", "textarea", "searchfield"): tf += 1
        stack.extend((c, d + 1) for c in node.get("children", []))
    return dict(nodes=n, named=named, named_ratio=round(named / n, 3) if n else 0, interactive=inter,
                textfields=tf, max_depth=maxd,
                roles=";".join(f"{k}:{v}" for k, v in roles.most_common(6)))


def load_apps(path):
    """Lines: launch_name|ax_name|wait_seconds|toolkit   (# comments allowed)."""
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        launch, ax, wait, kit = (line.split("|") + ["", "", "10", ""])[:4]
        out.append((launch.strip(), (ax or launch).strip(), int(wait or 10), kit.strip()))
    return out


def close(app):
    ad("close-app", app, timeout=60); time.sleep(3)
    if running(app) is not False:
        ad("close-app", app, "--force", timeout=60); time.sleep(2)
    return running(app) is False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apps", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps-windows.txt"))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--timeout-ms", type=int, default=20000)
    ap.add_argument("--max-depth", type=int, default=40)
    ap.add_argument("--out", default="census-windows.csv")
    a = ap.parse_args()

    apps = load_apps(a.apps)
    if a.only:
        apps = [x for x in apps if x[1] in a.only or x[0] in a.only]
    osname = f"{platform.system()} {platform.release()} ({platform.version()})"
    adver = subprocess.run([AD, "--version"], capture_output=True, text=True).stdout.strip()
    cols = ["ts", "os", "agent_desktop", "app", "toolkit", "run", "nodes", "named", "named_ratio",
            "interactive", "textfields", "max_depth", "roles", "ms", "error"]
    new = not os.path.exists(a.out)
    with open(a.out, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new: w.writeheader()
        for launch, ax, wait, kit in apps:
            was = running(ax)  # None = unknown -> measure but never close
            if was is not True:
                j = ad("launch", launch, "--activate", "--timeout", "60000", timeout=90)
                if not j.get("ok"):
                    code = j.get("error", {}).get("code", "LAUNCH_FAILED")
                    w.writerow(dict(ts=time.strftime("%Y-%m-%dT%H:%M:%S"), os=osname, agent_desktop=adver,
                                    app=ax, toolkit=kit, run=0, error=f"LAUNCH:{code}")); f.flush()
                    print(f"{ax:30s} launch failed: {code}", file=sys.stderr)
                    continue
                time.sleep(wait)
            for r in range(a.runs):
                data, ms, err = snapshot(ax, a.timeout_ms, a.max_depth)
                row = dict(ts=time.strftime("%Y-%m-%dT%H:%M:%S"), os=osname, agent_desktop=adver,
                           app=ax, toolkit=kit, run=r, ms=ms, error=err)
                if data: row.update(metrics(data["tree"]))
                w.writerow(row); f.flush()
                print(f"{ax:30s} run{r} nodes={row.get('nodes','-'):>5} named={row.get('named_ratio','-')} "
                      f"inter={row.get('interactive','-')} {ms}ms {err}", file=sys.stderr)
            if was is False:
                print(f"{ax:30s} closed={close(ax)}", file=sys.stderr)
            elif was is None:
                print(f"{ax:30s} left open: couldn't tell if it was running before", file=sys.stderr)


if __name__ == "__main__":
    main()
