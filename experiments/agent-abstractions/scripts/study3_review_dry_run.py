"""Dry run of the study-3 design-review export on study-2 data (plan Task 7), before any
study-3 run exists: proves that packets and batches build on real diffs and that the arm
cannot be read from a packet. No agent, no judge, no Docker; runs2/ is only read.

A stand-in runs3 tree is assembled in a scratch dir:
- R, RG, RL: every runs2 R chain, linked under each arm (the same agent work in three
  arms: their packets must be identical but for the ids);
- in one RG and one RL chain per agent the T4 step is a copy with arm artefacts injected
  (RG: an AGENTS.md edit and a comment quoting the rule; RL: a dup-check config edit, a
  `.jscpd.json`, `jscpd:ignore` markers and a pasted dup-check output file), which the
  export must strip;
- RC: one chain per zone, T0 = the zone's reference consolidation
  (tasks3/<zone>/T0/reference.R.patch) and T1..T4 small edits built with git on top of it;
- F: the study-2 F chains (runs2), as the real export does.

  uv run python scripts/study3_review_dry_run.py --scratch <dir>"""
import argparse
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

from aa import config, review3
from aa.chain_eval import CHAIN_RESULT, CUMULATIVE, EVAL_DIR, POST_TREE, PRE_IMAGE, STEP_PATCH

LOOT = "packages/loot-core"
RUNS2 = config.ROOT / "runs2"


def git(repo: Path, *a: str, input_text: str | None = None) -> str:
    return subprocess.run(["git", "-c", "user.email=d@r", "-c", "user.name=d", *a], cwd=repo,
                          check=True, capture_output=True, text=True, input=input_text).stdout


def new_file(path: str, body: str) -> str:
    lines = body.splitlines()
    return (f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n+++ b/{path}\n"
            f"@@ -0,0 +1,{len(lines)} @@\n" + "".join(f"+{x}\n" for x in lines))


INJECT = {
    "RG": ("diff --git a/AGENTS.md b/AGENTS.md\n--- a/AGENTS.md\n+++ b/AGENTS.md\n"
           "@@ -1 +1,2 @@\n # AGENTS.md\n+- Reuse shared helpers.\n"
           + new_file(f"{LOOT}/src/server/dry-run-rg.ts",
                      "// Do not copy logic: extract it into a shared function and reuse it\n"
                      "export const dryRunRg = 1;")),
    "RL": ("diff --git a/packages/loot-core/bin/dup-check.config.json "
           "b/packages/loot-core/bin/dup-check.config.json\n"
           "--- a/packages/loot-core/bin/dup-check.config.json\n"
           "+++ b/packages/loot-core/bin/dup-check.config.json\n"
           "@@ -1 +1 @@\n-{\"minTokens\": 35}\n+{\"minTokens\": 500}\n"
           + new_file(".jscpd.json", '{"ignore": ["**"]}')
           + new_file(f"{LOOT}/src/server/dry-run-rl.ts",
                      "// jscpd:ignore-start\nexport const dryRunRl = 1;\n// jscpd:ignore-end")
           + new_file(f"{LOOT}/lint-output.txt",
                      "dup-check: duplicated code on lines added or changed in this task:\n"
                      "  src/a.ts:1-9 ~ src/b.ts:1-9 (40 tokens)")),
}


def copy_chain(src: Path, dst: Path) -> None:
    """The text files the export reads (eval/ only its patches)."""
    for f in [CHAIN_RESULT, CUMULATIVE]:
        if (src / f).exists():
            dst.mkdir(parents=True, exist_ok=True)
            shutil.copy(src / f, dst / f)
    for sd in sorted(p for p in src.iterdir() if p.is_dir() and p.name.startswith("T")):
        (dst / sd.name / EVAL_DIR).mkdir(parents=True, exist_ok=True)
        for f in ("agent.json", "result.json", "diff.patch"):
            if (sd / f).exists():
                shutil.copy(sd / f, dst / sd.name / f)
        for f in (PRE_IMAGE, STEP_PATCH, POST_TREE):
            if (sd / EVAL_DIR / f).exists():
                shutil.copy(sd / EVAL_DIR / f, dst / sd.name / EVAL_DIR / f)


def inject(cdir: Path, arm: str) -> None:
    extra = INJECT[arm]
    t4 = cdir / "T4"
    for f in (t4 / "diff.patch", t4 / EVAL_DIR / STEP_PATCH, t4 / EVAL_DIR / POST_TREE,
              cdir / CUMULATIVE):
        f.write_text(f.read_text() + extra)


def build_rc(fake: Path, zone: str, variant_repo: Path, tmp: Path) -> None:
    """runs3-shaped RC chain: T0 = the reference consolidation, T1..T4 one-line edits."""
    cdir = fake / "claude" / "RC" / zone / "0"
    wt = tmp / f"wt-{zone}"
    git(variant_repo, "worktree", "add", "--detach", str(wt), "HEAD")
    try:
        ref = config.ROOT / "tasks3" / zone / "T0" / "reference.R.patch"
        sites = json.loads((config.ROOT / "tasks3" / zone / "T0" / "sites.json").read_text())
        target = wt / LOOT / "src" / sites["sites"][0]["file"]
        prev_post = ""
        for k in range(0, 5):
            sid = f"T{k}"
            git(wt, "add", "-A")
            if k == 0:
                git(wt, "apply", str(ref))
            else:
                target.write_text(target.read_text() + f"// dry-run edit {k}\n")
            step = git(wt, "diff", "--binary")
            git(wt, "add", "-A")
            post = git(wt, "diff", "--cached", "--binary", "HEAD")
            d = cdir / sid
            (d / EVAL_DIR).mkdir(parents=True)
            (d / "agent.json").write_text(json.dumps({"status": "ok"}))
            (d / "result.json").write_text(json.dumps({"status": "ok",
                                                       "diff_applies_to_pre_image": True}))
            (d / "diff.patch").write_text(step)
            (d / EVAL_DIR / STEP_PATCH).write_text(step)
            (d / EVAL_DIR / PRE_IMAGE).write_text(prev_post)
            (d / EVAL_DIR / POST_TREE).write_text(post)
            prev_post = post
        (cdir / CUMULATIVE).write_text(prev_post)
        (cdir / CHAIN_RESULT).write_text(json.dumps({"complete": True}))
    finally:
        git(variant_repo, "worktree", "remove", "--force", str(wt))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scratch", type=Path, required=True)
    ap.add_argument("--variants", type=Path, default=config.WORK / "variants")
    a = ap.parse_args(argv)
    scratch = a.scratch.resolve()
    if scratch.exists():
        shutil.rmtree(scratch)
    fake = scratch / "runs3"
    injected: set[tuple[str, str, str, str]] = set()
    for agent_dir in sorted(p for p in RUNS2.iterdir() if (p / "R").is_dir()):
        agent = agent_dir.name
        for src in sorted(agent_dir.glob("R/*/*")):
            zone, cidx = src.parts[-2:]
            for arm in ("R", "RG", "RL"):
                dst = fake / agent / arm / zone / cidx
                if arm in INJECT and zone == "Z1" and cidx == "0":
                    copy_chain(src, dst)
                    inject(dst, arm)
                    injected.add((agent, arm, zone, cidx))
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.symlink_to(src)
    for zone in ("Z1", "Z2", "Z3", "Z4"):
        build_rc(fake, zone, a.variants / "R", scratch)

    out, mp = scratch / "review3", scratch / "review3-mapping.json"
    rep = review3.export_review_packets3(fake, out, mp, f_runs=RUNS2,
                                         variants_root=a.variants)
    mapping = json.loads(mp.read_text())
    batches = review3.make_batches(mapping)
    (out / "batches.json").write_text(json.dumps(batches, indent=1) + "\n")

    problems: list[str] = []
    kinds = Counter((m["cond"], m["kind"]) for m in mapping.values())
    print("packets by arm and kind:")
    for (cond, kind), n in sorted(kinds.items()):
        print(f"  {cond}\t{kind}\t{n}")
    bad = Counter(b["reason"].split(":")[0] for b in rep["bad"])
    print(f"not exported: {len(rep['bad'])} {dict(bad)}")
    by_src_arm: dict[tuple, dict[str, str]] = {}
    for pid, m in mapping.items():
        p = out / "packets" / pid
        leaks = review3.packet_leaks(p)
        if leaks:
            problems.append(f"leak in {pid}: {leaks}")
        key = (m["agent"], m["zone"], m["chain"], m["kind"], m.get("step"))
        by_src_arm.setdefault(key, {})[m["cond"]] = pid
    # same agent work, three arms: identical packets (but the injected T4 / chains)
    same = differ = 0
    for key, arms in by_src_arm.items():
        if not {"R", "RG", "RL"} <= set(arms):
            continue
        # tree.txt names each packet's own commit; the tree content is compared by id
        contents = {arm: (sorted((f.name, f.read_text())
                                 for f in (out / "packets" / arms[arm]).iterdir()
                                 if f.name != "tree.txt"), mapping[arms[arm]]["tree_id"])
                    for arm in ("R", "RG", "RL")}
        agent, zone, cidx = key[:3]
        touched = any((agent, arm, zone, cidx) in injected for arm in ("RG", "RL")) and \
            (key[3] == "chain" or key[4] == "T4")
        if contents["R"] == contents["RG"] == contents["RL"]:
            same += 1
        elif touched:
            # injected: the sanitised packet must still equal R's but for the agent's own
            # kept code lines (the new files minus their redacted lines)
            differ += 1
        else:
            problems.append(f"arm-dependent packet content without injection: {key}")
    print(f"R/RG/RL packets from the same work: {same} identical, {differ} differ "
          "(injected steps/chains only)")
    for pid, m in mapping.items():
        if (m["agent"], m["cond"], m["zone"], m["chain"]) in injected and "sanitised" in m:
            print(f"  sanitised {m['cond']} {m['kind']} {m.get('step') or ''}: "
                  f"{json.dumps(m['sanitised'])}")
    bases = {m["cond"]: m["base"] for m in mapping.values()}
    if {bases[c] for c in ("R", "RG", "RL", "RC") if c in bases} != {"R"}:
        problems.append(f"R-based arms do not share one base tree: {bases}")
    print(f"base trees: {sorted(set(bases.values()))}; one repository "
          f"{sorted({m['tree'] for m in mapping.values()})}")
    # every packet in the same form: no pre-image file, tree.txt = repository + commit
    import re
    form = re.compile(r"\Atrees-[0-9a-f]{10}\.git\n[0-9a-f]{40}\n" + re.escape(review3.TREE_HOWTO)
                      + r"\Z")
    for pid in mapping:
        p = out / "packets" / pid
        if (p / "pre-image.patch").exists() or not form.match((p / "tree.txt").read_text()):
            problems.append(f"packet form differs: {pid}")
    pre = Counter((m["cond"], m["kind"], m["pre_image_empty"]) for m in mapping.values()
                  if m["kind"] == "chain" or m.get("step") == "T1")
    print(f"pre-image empty (mapping only, folded into the trees): {dict(sorted(pre.items()))}")
    agents_md = git(a.variants / "R", "show", "HEAD:AGENTS.md")
    # R's own AGENTS.md names itself ("# AGENTS.md - Guide ..."); what must be absent is
    # the RG rule and any dup-check file
    if review3.LEAKS["rg_rule"].search(agents_md) or "dup-check" in git(a.variants / "R",
                                                                          "ls-files"):
        problems.append("the R base tree carries an arm artefact")
    pool = batches["pool"]
    flat = [i for b in batches["main"] for i in b]
    if sorted(pool) != sorted(mapping) or sorted(flat) != sorted(pool):
        problems.append("batches do not cover the shuffled pool exactly")
    for b in batches["main"] + batches["second"]:
        keys = [review3.chain_key(i, mapping[i]) for i in b]
        if len(keys) != len(set(keys)):
            problems.append(f"a batch holds two packets of one chain: {b}")
    mixed = Counter(len({mapping[i]["cond"] for i in b}) for b in batches["main"])
    print(f"batches: {len(batches['main'])} main of {batches['batch_size']}, arms per batch "
          f"{dict(sorted(mixed.items()))}; second judge {sum(map(len, batches['second']))} "
          f"({sum(mapping[i]['kind'] == 't0' for b in batches['second'] for i in b)} T0)")
    print("PROBLEMS:" if problems else "dry run ok: no leaks, arms indistinguishable")
    for p in problems[:50]:
        print("  " + p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
