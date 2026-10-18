"""Study 3 design review (plan Task 7): packets blind to arm, one mixed batch pool
(Review Focus 5), judge-output normalisation, kappa, labels for tables3, H1 tables."""
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import pytest

from aa import review3, tables3

LOOT = "packages/loot-core"
A = f"{LOOT}/src/a.ts"
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _git(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", *a], cwd=repo,
                          check=True, capture_output=True, text=True).stdout


def patch(path: str, old: str | None, new: str) -> str:
    if old is None:
        lines = new.splitlines()
        return (f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n"
                f"+++ b/{path}\n@@ -0,0 +1,{len(lines)} @@\n"
                + "".join(f"+{ln}\n" for ln in lines))
    return (f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n"
            f"@@ -1 +1 @@\n-{old}\n+{new}\n")


def variant(root: Path, name: str, files: dict[str, str]) -> Path:
    repo = root / name
    for p, body in files.items():
        (repo / p).parent.mkdir(parents=True, exist_ok=True)
        (repo / p).write_text(body)
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "variant")
    return repo


def tasks(root: Path) -> tuple[Path, Path, Path]:
    t2 = root / "tasks2" / "Z1"
    t2.mkdir(parents=True)
    (t2 / "chain.json").write_text(json.dumps({
        "zone": "Z1", "steps": ["T1", "T2", "T3", "T4"], "zone_files": ["server/a.ts"],
        "t2_reuse": {"helpers": {"R": [], "F": []}, "markers": []}}))
    for k in range(1, 5):
        s = t2 / f"T{k}"
        h = s / "hidden" / LOOT / "src" / f"zone-t{k}.test.ts"
        h.parent.mkdir(parents=True)
        h.write_text(f"// HIDDEN T{k}\n")
        (s / "consumers.json").write_text(json.dumps({f"test {k}": "c"}))
        (s / "statement.md").write_text(f"Make the change of step {k}.\n")
    t0 = root / "tasks3" / "Z1" / "T0"
    t0.mkdir(parents=True)
    (t0 / "statement.md").write_text("Move this logic into one shared definition.\n")
    (t0 / "consumers.json").write_text("{}")
    (t0 / "sites.json").write_text(json.dumps({
        "zone": "Z1", "source": "docs/study2-variants.md; R form = the frozen R variant",
        "logic": "Which rows (tasks2/Z1/chain.json logic) an action writes",
        "decision": "the selection (scored on this decision, spec section 3; x counts)",
        "sites": [{"id": "s1", "file": "a.ts", "function": "f", "decides": "inlined ternary (R)"}],
        "preserved_inconsistencies": ["f writes hidden (hidden test: f-hidden)",
                                      "g is not awaited (excluded: z1-await)"],
        "f_reference": "F: helper()"}))
    pd = root / "patches"
    pd.mkdir()
    (pd / "rg.patch").write_text(patch("AGENTS.md", "# agents", "# agents + rule"))
    (pd / "rl.patch").write_text(patch("package.json", "{}", '{"lint": "dup"}')
                                 + patch(f"{LOOT}/bin/dup-check.mjs", None, "x"))
    return root / "tasks2", root / "tasks3", pd


def write_step(chain_dir: Path, sid: str, pre: str, step: str, post: str,
               status: str = "ok") -> None:
    d = chain_dir / sid
    (d / "eval").mkdir(parents=True)
    (d / "agent.json").write_text(json.dumps({"status": status}))
    (d / "diff.patch").write_text(step)
    (d / "eval/pre_image.patch").write_text(pre)
    (d / "eval/step.patch").write_text(step)
    (d / "eval/post_tree.patch").write_text(post)
    (d / "result.json").write_text(json.dumps({"status": status,
                                               "diff_applies_to_pre_image": True}))


def write_chain(runs: Path, agent: str, cond: str, states: list[str], *, t0: str | None = None,
                start: str = "one", extra: dict[str, str] | None = None) -> Path:
    """states = a.ts after T1..T4; t0 = a.ts after RC's T0; extra = {step: patch text
    added to that step's diff (and to every later pre-image / post tree)}."""
    cdir = runs / agent / cond / "Z1" / "0"
    extra = extra or {}
    acc = ""   # extra content accumulated so far (as patches from the untouched tree)
    prev = start
    if t0 is not None:
        write_step(cdir, "T0", "", patch(A, start, t0), patch(A, start, t0))
        prev = t0
    for k, s in enumerate(states, 1):
        sid = f"T{k}"
        pre = (patch(A, start, prev) if prev != start else "") + acc
        step = patch(A, prev, s) + extra.get(sid, "")
        acc += extra.get(sid, "")
        write_step(cdir, sid, pre, step, patch(A, start, s) + acc)
        prev = s
    (cdir / "cumulative.patch").write_text(patch(A, start, prev) + acc)
    (cdir / "chain_result.json").write_text(json.dumps({"complete": True}))
    return cdir


@pytest.fixture
def env(tmp_path):
    t2, t3, pd = tasks(tmp_path)
    variants = tmp_path / "variants"
    variant(variants, "R", {A: "one\n", "AGENTS.md": "# agents\n", "package.json": "{}\n"})
    variant(variants, "F", {A: "eff\n", "AGENTS.md": "# agents\n", "package.json": "{}\n"})
    runs, runs2 = tmp_path / "runs3", tmp_path / "runs2"
    states = ["s1", "s2", "s3", "s4"]
    write_chain(runs, "claude", "R", states)
    write_chain(runs, "claude", "RG", states, extra={
        "T2": patch("AGENTS.md", "# agents + rule", "# agents + rule + more")
        + patch(f"{LOOT}/src/c.ts", None,
                "// Do not copy logic: extract it into a shared function\nexport const c = 1;")})
    write_chain(runs, "claude", "RL", states, extra={
        "T4": patch(f"{LOOT}/bin/dup-check.mjs", "x", "y")
        + patch(f"{LOOT}/src/b.ts", None,
                "// jscpd:ignore-start\nexport const b = 1;\n// jscpd:ignore-end")})
    write_chain(runs, "claude", "RC", states, t0="t0")
    write_chain(runs2, "claude", "F", ["f1", "f2", "f3", "f4"], start="eff")
    write_chain(runs2, "claude", "R", states)   # study-2 R: never exported
    return {"root": tmp_path, "tasks2": t2, "tasks3": t3, "patches": pd, "variants": variants,
            "runs": runs, "runs2": runs2}


def export(env, **kw):
    out, mp = env["root"] / "review3", env["root"] / "review3-mapping.json"
    rep = review3.export_review_packets3(
        env["runs"], out, mp, f_runs=env["runs2"], tasks_root=env["tasks2"],
        tasks3_root=env["tasks3"], variants_root=env["variants"], patch_dir=env["patches"], **kw)
    return rep, out, json.loads(mp.read_text())


# --- sanitising ------------------------------------------------------------------------------

def test_arm_patch_paths_are_the_real_study3_patches():
    paths = review3.arm_patch_paths()
    assert {"AGENTS.md", "package.json", f"{LOOT}/package.json", f"{LOOT}/bin/dup-check.mjs",
            f"{LOOT}/bin/dup-check.config.json"} == set(paths)


def test_sanitise_strips_arm_paths_and_redacts_markers():
    text = (patch("AGENTS.md", "a", "b") + patch(f"{LOOT}/.jscpd.json", None, "{}")
            + patch(f"{LOOT}/src/x.ts", None, "// jscpd:ignore-start\nconst x = 1;\n"
                    "// jscpd:ignore-end")
            + patch(f"{LOOT}/src/y.ts", None, "dup-check: duplicated code on lines added")
            + patch(f"{LOOT}/src/z.ts", "old", "new"))
    out, info = review3.sanitise_patch(text, frozenset({"AGENTS.md"}))
    assert info["stripped_paths"] == ["AGENTS.md", f"{LOOT}/.jscpd.json", f"{LOOT}/src/y.ts"]
    assert info["redacted_lines"] == 2
    assert "jscpd" not in out and "AGENTS" not in out and "dup-check" not in out
    assert "@@ -0,0 +1,1 @@\n+const x = 1;\n" in out
    assert patch(f"{LOOT}/src/z.ts", "old", "new").split("@@")[0] in out
    assert review3.text_leaks(out) == []


def test_redaction_of_a_context_line_keeps_the_hunk_consistent():
    text = (f"diff --git a/f b/f\n--- a/f\n+++ b/f\n@@ -3,3 +3,4 @@ ctx\n"
            " keep\n // jscpd:ignore-start\n-old\n+new\n+more\n")
    out, info = review3.sanitise_patch(text, frozenset())
    assert info["redacted_lines"] == 1
    assert "@@ -3,2 +3,3 @@ ctx\n keep\n-old\n+new\n+more\n" in out


def test_leak_scan():
    assert review3.text_leaks("runs3/claude/RL/Z1/0") == ["arm_path", "run_path"]
    assert review3.text_leaks("node bin/dup-check.mjs") == ["dup_check"]
    assert "rg_rule" in review3.text_leaks("Do not copy logic: when new code needs")
    assert review3.text_leaks("const R = 1; // a variant", meta=False) == []
    assert set(review3.text_leaks("in R and in Z2 variants", meta=True)) >= {
        "arm_name", "study_word"}


@pytest.mark.parametrize("zone", ["Z1", "Z2", "Z3", "Z4"])
def test_real_sites_scrub_clean(zone):
    sites = json.loads((Path(__file__).parent.parent / "tasks3" / zone / "T0" /
                        "sites.json").read_text())
    js = review3.judge_sites(sites)
    text = json.dumps(js)
    assert review3.text_leaks(text, meta=True) == [], text
    assert {"zone", "source", "f_reference"}.isdisjoint(js)
    assert [s["id"] for s in js["sites"]] == [s["id"] for s in sites["sites"]]
    assert len(js["preserved_inconsistencies"]) == len(sites["preserved_inconsistencies"])


# --- export ----------------------------------------------------------------------------------

@needs_git
def test_export_kinds_trees_and_questions(env):
    rep, out, mapping = export(env)
    assert rep["bad"] == []
    kinds = Counter((m["cond"], m["kind"]) for m in mapping.values())
    assert kinds == {("R", "step"): 4, ("R", "chain"): 1, ("RG", "step"): 4, ("RG", "chain"): 1,
                     ("RL", "step"): 4, ("RL", "chain"): 1, ("RC", "t0"): 1, ("RC", "step"): 4,
                     ("RC", "chain"): 1, ("RC", "chain_full"): 1, ("F", "chain"): 1}
    bases = {m["cond"]: m["base"] for m in mapping.values()}
    assert bases["R"] == bases["RG"] == bases["RL"] == bases["RC"] == "R" != bases["F"]
    assert {m["tree"] for m in mapping.values()} == {review3.trees_repo_name()}
    assert len({m["commit"] for m in mapping.values()}) == len(mapping)   # one per packet
    for pid, m in mapping.items():
        q = json.loads((out / "packets" / pid / "questions.json").read_text())["questions"]
        if m["kind"] == "t0":
            assert q == ["completeness", "interface", "disguised_duplication"]
            continue
        assert "disguised_duplication" in q and "maintainability" in q
        assert ("abstraction_drift" in q) == (m["kind"] in ("chain", "chain_full"))
        assert ("t2_reuse" in q) == (m.get("step") == "T2")
        assert ("one_place" in q) == (m.get("step") in ("T1", "T3"))
    assert out not in (env["root"] / "review3-mapping.json").parents


@needs_git
def test_packets_are_blind_to_arm(env):
    rep, out, mapping = export(env)
    for pid in mapping:
        p = out / "packets" / pid
        assert review3.packet_leaks(p) == {}, pid
        text = "".join(f.read_text() for f in p.iterdir())
        for leak in ("claude", "RG", "RL", "RC", "runs", "dup-check", "jscpd", "AGENTS.md",
                     "Do not copy logic", "Z1"):
            assert leak not in text, (pid, leak)
    # the same agent work gives the same packet whatever the arm (ids differ only)
    by = {(m["cond"], m["kind"], m.get("step")): pid for pid, m in mapping.items()}
    for step in ("T1", "T2", "T3", "T4"):
        for kind_files in ("statement.md", "questions.json"):
            assert (out / "packets" / by[("R", "step", step)] / kind_files).read_text() == \
                (out / "packets" / by[("RL", "step", step)] / kind_files).read_text()
        # the same tree content, behind a different commit
        assert mapping[by[("R", "step", step)]]["tree_id"] == \
            mapping[by[("RL", "step", step)]]["tree_id"]
    for arm in ("RG", "RL"):
        a, b = out / "packets" / by[("R", "step", "T1")], out / "packets" / by[(arm, "step", "T1")]
        assert sorted(f.read_text() for f in a.iterdir() if f.name != "tree.txt") == \
            sorted(f.read_text() for f in b.iterdir() if f.name != "tree.txt")
    # what was stripped is in the mapping, outside the packets
    rl4 = mapping[by[("RL", "step", "T4")]]["sanitised"]["diff"]
    assert rl4 == {"stripped_paths": [f"{LOOT}/bin/dup-check.mjs"], "redacted_lines": 2}
    rg2 = mapping[by[("RG", "step", "T2")]]["sanitised"]["diff"]
    assert rg2["stripped_paths"] == ["AGENTS.md"] and rg2["redacted_lines"] == 1
    rg3 = mapping[by[("RG", "step", "T3")]]["sanitised"]["pre_image"]
    assert rg3["stripped_paths"] == ["AGENTS.md"]
    # the RG chain still holds the agent's c.ts, minus the quoted rule
    chain = (out / "packets" / by[("RG", "chain", None)] / "diff.patch").read_text()
    assert "export const c = 1;" in chain


def checkout(out: Path, packet: Path, dest: Path) -> Path:
    """What the judge's workflow does with tree.txt."""
    repo, commit = (packet / "tree.txt").read_text().splitlines()[:2]
    subprocess.run(["git", "--git-dir", str(out / "trees" / repo), "worktree", "add",
                    "--detach", str(dest), commit], check=True, capture_output=True)
    return dest


TREE_TXT = re.compile(r"\Atrees-[0-9a-f]{10}\.git\n[0-9a-f]{40}\n" + re.escape(review3.TREE_HOWTO)
                      + r"\Z")


@needs_git
def test_rc_chain_packet_starts_from_the_t0_tree(env):
    rep, out, mapping = export(env)
    by = {(m["cond"], m["kind"]): pid for pid, m in mapping.items() if m["kind"] != "step"}
    p = out / "packets" / by[("RC", "chain")]
    assert not (p / "pre-image.patch").exists()
    assert "## Step 0" not in (p / "statement.md").read_text()
    tree = checkout(out, p, env["root"] / "wt-rc")
    assert (tree / A).read_text() == "t0\n"
    subprocess.run(["git", "apply", str(p / "diff.patch")], cwd=tree, check=True)
    assert (tree / A).read_text() == "s4\n"
    full = out / "packets" / by[("RC", "chain_full")]
    assert (checkout(out, full, env["root"] / "wt-full") / A).read_text() == "one\n"
    assert (full / "statement.md").read_text().startswith("## Step 0")
    t0 = out / "packets" / by[("RC", "t0")]
    sites = json.loads((t0 / "sites.json").read_text())
    assert "zone" not in sites and "f_reference" not in sites
    assert sites["sites"][0]["decides"] == "inlined ternary"
    # the F chain is study 2's, on F's own tree, same salt scheme
    f = mapping[by[("F", "chain")]]
    assert f["study"] == 2 and by[("F", "chain")] == review3._neutral(
        review3.SALT, "chain", "claude", "F", "Z1", "0")
    assert (checkout(out, out / "packets" / by[("F", "chain")], env["root"] / "wt-f") / A
            ).read_text() == "eff\n"


@needs_git
def test_rc_chain_and_t1_packets_have_the_form_of_every_arm(env):
    """Review of plan Task 7 (HIGH): RC's chain and T1 packets used to carry T0's tree as
    a non-empty pre-image (and a tree.txt saying to apply it) where every R/RG/RL chain
    and T1 packet had an empty one. Now every packet names its own commit of one neutral
    repository, in the same form, and ships no pre-image."""
    rep, out, mapping = export(env)
    assert rep["bad"] == []
    for pid in mapping:
        p = out / "packets" / pid
        assert TREE_TXT.match((p / "tree.txt").read_text()), pid
        names = {f.name for f in p.iterdir()}
        assert names in ({"statement.md", "diff.patch", "tree.txt", "questions.json"},
                         {"statement.md", "diff.patch", "tree.txt", "questions.json",
                          "sites.json"}), (pid, names)
    by = {(m["cond"], m["kind"], m.get("step")): m for m in mapping.values()}
    for kind, step in (("chain", None), ("step", "T1")):
        assert by[("R", kind, step)]["pre_image_empty"] is True
        assert by[("RC", kind, step)]["pre_image_empty"] is False   # recorded, not shown
    # commits: parentless, fixed date, the packet id as message (no export order)
    repo = out / "trees" / review3.trees_repo_name()
    for pid, m in mapping.items():
        log = subprocess.run(["git", "--git-dir", str(repo), "log", "--format=%P|%at|%ct|%s",
                              m["commit"]], capture_output=True, text=True, check=True).stdout
        assert log.strip() == f"|1767225600|1767225600|{pid}"
    # the repository holds no variant history and no name of an arm
    refs = subprocess.run(["git", "--git-dir", str(repo), "for-each-ref", "--format=%(refname)"],
                          capture_output=True, text=True, check=True).stdout.split()
    assert sorted(refs) == sorted(f"refs/heads/{pid}" for pid in mapping)


@needs_git
def test_rc_t1_pre_image_must_be_t0_tree(env):
    (env["runs"] / "claude/RC/Z1/0/T0/eval/post_tree.patch").write_text(patch(A, "one", "zz"))
    rep, out, mapping = export(env)
    bad = [b for b in rep["bad"] if b["kind"] == "chain" and b["cond"] == "RC"]
    assert bad and bad[0]["reason"].startswith("rc: T1 pre-image")


@needs_git
def test_leaky_packet_is_not_exported(env):
    d = env["runs"] / "claude/R/Z1/0/T1"
    leaky = patch(A, "one", "s1") + patch(f"{LOOT}/src/l.ts", None, "see runs3/claude")
    (d / "diff.patch").write_text(leaky)
    (d / "eval/step.patch").write_text(leaky)
    rep, out, mapping = export(env)
    bad = [b for b in rep["bad"] if b.get("step") == "T1" and b["cond"] == "R"]
    assert bad and bad[0]["reason"].startswith("leak:")
    assert not (out / "packets" / bad[0]["id"]).exists()


@needs_git
def test_packet_trees_rebuilt_fresh(env):
    rep, out, mapping = export(env)
    stale = out / "trees" / "stale"
    stale.mkdir()
    rep2, out2, mapping2 = export(env)
    assert not stale.exists() and set(mapping2) == set(mapping)
    assert {m["commit"] for m in mapping2.values()} == {m["commit"] for m in mapping.values()}


@needs_git
def test_package_json_dependency_change_is_kept(env):
    """Review LOW: package.json was stripped in every arm, hiding legitimate dependency
    changes; now only its dup-check lines are redacted (stripped only as a fallback)."""
    dep = patch("package.json", "{}", '{"dependencies": {"left-pad": "1"}}')
    for arm in ("R", "RL"):
        d = env["runs"] / "claude" / arm / "Z1" / "0" / "T4"
        for f in (d / "diff.patch", d / "eval/step.patch"):
            f.write_text(f.read_text() + dep)
    rep, out, mapping = export(env)
    assert rep["bad"] == []
    by = {(m["cond"], m["kind"], m.get("step")): pid for pid, m in mapping.items()}
    for arm in ("R", "RL"):
        text = (out / "packets" / by[(arm, "step", "T4")] / "diff.patch").read_text()
        assert "left-pad" in text, arm
    assert "package_json_stripped" not in mapping[by[("RL", "step", "T4")]].get("sanitised", {})


def test_package_json_lint_lines_are_redacted():
    text = ("diff --git a/package.json b/package.json\n--- a/package.json\n+++ b/package.json\n"
            "@@ -1,3 +1,4 @@\n {\n-  \"lint\": \"tsgo -b; node bin/dup-check.mjs\",\n"
            "+  \"lint\": \"tsgo -b; node bin/dup-check.mjs\",\n+  \"dep\": \"1\",\n }\n")
    out, info = review3.sanitise_patch(text, frozenset({"package.json"}))
    assert "dup-check" not in out and '"dep"' in out and info["redacted_lines"] == 2
    out2, info2 = review3.sanitise_patch(text, frozenset({"package.json"}), strip_package_json=True)
    assert out2 == "" and info2["stripped_paths"] == ["package.json"]


@needs_git
def test_package_json_fallback_strips_when_redaction_cannot_apply(env):
    """A hunk whose context holds RL's lint line cannot apply to the neutral base once
    that line is redacted: the section is then stripped and that is recorded."""
    rl_line = '"lint": "x; node bin/dup-check.mjs"'
    d = env["runs"] / "claude" / "RL" / "Z1" / "0" / "T4"
    hunk = ("diff --git a/package.json b/package.json\n--- a/package.json\n+++ b/package.json\n"
            f"@@ -1,3 +1,4 @@\n {{}}\n {rl_line}\n \"tail\": 0\n+\"dep\": 1\n")
    for f in (d / "diff.patch", d / "eval/step.patch"):
        f.write_text(f.read_text() + hunk)
    rep, out, mapping = export(env)
    m = next(m for m in mapping.values() if m["cond"] == "RL" and m.get("step") == "T4")
    assert m["sanitised"]["package_json_stripped"] is True
    assert "package.json" in m["sanitised"]["diff"]["stripped_paths"]


# --- batches (Review Focus 5) ----------------------------------------------------------------

def synthetic_mapping(n_chains=8) -> dict[str, dict]:
    m = {}
    for agent in ("claude", "codex", "haiku"):
        for cond in ("R", "RG", "RL", "RC", "F"):
            for z in ("Z1", "Z2", "Z3", "Z4"):
                for c in range(n_chains):
                    where = {"agent": agent, "cond": cond, "zone": z, "chain": str(c)}
                    m[review3._neutral("t", "chain", agent, cond, z, c)] = {
                        "kind": "chain", **where}
                    if cond == "F":
                        continue
                    for k in range(1, 5):
                        m[review3._neutral("t", "step", agent, cond, z, c, k)] = {
                            "kind": "step", "step": f"T{k}", **where}
                    if cond == "RC":
                        m[review3._neutral("t", "t0", agent, cond, z, c)] = {
                            "kind": "t0", **where}
                        m[review3._neutral("t", "chain_full", agent, cond, z, c)] = {
                            "kind": "chain_full", **where}
    return m


def test_every_batch_draws_from_one_shuffled_pool():
    m = synthetic_mapping()
    b = review3.make_batches(m, seed=7)
    assert sorted(b["pool"]) == sorted(m)                    # all arms + F, once each
    flat = [i for batch in b["main"] for i in batch]
    assert sorted(flat) == sorted(b["pool"]) and len(flat) == len(set(flat))
    assert all(len(x) <= 12 for x in b["main"])
    assert len(b["main"]) <= -(-len(m) // 12) + 2            # first fit wastes ~nothing
    # batches keep the shuffled order: each batch's ids appear in pool order
    pos = {i: k for k, i in enumerate(b["pool"])}
    assert all([pos[i] for i in x] == sorted(pos[i] for i in x) for x in b["main"])
    assert {m[i]["cond"] for i in b["pool"]} == {"R", "RG", "RL", "RC", "F"}
    # mixed: no batch file per arm, and batches hold several arms
    mixed = [len({m[i]["cond"] for i in x}) for x in b["main"]]
    assert sum(k >= 3 for k in mixed) > 0.9 * len(mixed)
    assert b["pool"] != sorted(m, key=lambda i: m[i]["cond"])
    assert review3.make_batches(m, seed=7) == b              # seeded
    assert review3.make_batches(m, seed=8)["pool"] != b["pool"]


@pytest.mark.parametrize("seed", [7, 20261011])
def test_no_batch_holds_two_packets_of_one_chain(seed):
    """Review of plan Task 7 (HIGH): an RC chain's t0 and chain_full packets (or its
    chain and step packets) in one batch would link them for the judge."""
    m = synthetic_mapping()
    b = review3.make_batches(m, seed=seed)
    for x in b["main"] + b["second"]:
        keys = [review3.chain_key(i, m[i]) for i in x]
        assert len(keys) == len(set(keys)), x
    # the unconstrained cut would have put some together (the constraint is doing work)
    cut = [b["pool"][i:i + 12] for i in range(0, len(b["pool"]), 12)]
    assert any(len({review3.chain_key(i, m[i]) for i in x}) < len(x) for x in cut)


def test_second_judge_shares():
    m = synthetic_mapping()
    b = review3.make_batches(m, seed=7)
    second = [i for x in b["second"] for i in x]
    assert len(second) == len(set(second)) and set(second) <= set(m)
    t0 = [i for i in m if m[i]["kind"] == "t0"]
    rest = [i for i in m if m[i]["kind"] != "t0"]
    assert sum(m[i]["kind"] == "t0" for i in second) == round(0.25 * len(t0))
    assert sum(m[i]["kind"] != "t0" for i in second) == round(0.15 * len(rest))
    assert all(len(x) <= 12 for x in b["second"])


# --- judge outputs -----------------------------------------------------------------------------

FULL = {"reuse": {"score": 4, "why": "w"}, "duplication": {"score": 3, "why": "w"},
        "placement": {"score": 5, "why": "w"}, "scope": {"score": 4, "why": "w"},
        "maintainability": {"score": 4, "why": "w"},
        "bypasses_abstraction": {"value": False, "where": ""}, "duplicated_blocks": 0,
        "would_merge": "yes", "disguised_duplication": {"value": False, "where": ""}}


def test_normalise_tolerates_study2_abbreviated_shape():
    short = {"reuse": [4, "w"], "duplication": [3, "w"], "placement": [5, "w"],
             "scope": [4, "w"], "maintainability": [4, "w"], "bp": [False, ""], "db": 0,
             "wm": "yes", "disguised_duplication": [False, ""]}
    assert review3.normalise(short) == review3.normalise(FULL) == FULL
    n = review3.normalise({**FULL, "t2_reuse": {"value": "helper"}, "one_place": True,
                           "completeness": {"sites_total": 4, "sites_shared": 3},
                           "interface": [4, "ok"],
                           "abstraction_drift": {"parameters_added": 2}})
    assert n["t2_reuse"] == "helper" and n["one_place"] == {"value": True, "where": ""}
    assert n["completeness"]["value"] == 0.75 and n["interface"]["score"] == 4
    assert n["abstraction_drift"]["value"] is True
    for bad in ({**FULL, "maintainability": 6}, {**FULL, "t2_reuse": "inline"},
                {**FULL, "completeness": 1.5}, {**FULL, "would_merge": "maybe"},
                {**FULL, "one_place": "yes"}):
        with pytest.raises(review3.JudgementError):
            review3.normalise(bad)


def test_completeness_from_per_site_levels():
    """Amendment 2026-10-12b item 8: value = (full + 0.5 x partial) / sites; a judge value
    that disagrees with its levels is replaced and recorded; lenient / strict beside it."""
    c = review3.normalise({"completeness": {
        "per_site": {"s1": "full", "s2": "partial", "s3": "none", "s4": True},
        "value": 0.625}})["completeness"]
    assert c["value"] == 0.625 and "value_mismatch" not in c
    assert c["per_site"] == {"s1": "full", "s2": "partial", "s3": "none", "s4": "full"}
    assert (c["lenient"], c["strict"]) == (0.75, 0.5)
    bad = review3.normalise({"completeness": {"per_site": {"a": "partial", "b": "full"},
                                              "value": 1.0}})["completeness"]
    assert bad["value"] == 0.75 and bad["value_mismatch"] == {"given": 1.0, "levels": 0.75}
    with pytest.raises(review3.JudgementError):
        review3.normalise({"completeness": {"per_site": {"a": "most"}}})
    with pytest.raises(review3.JudgementError):
        review3.normalise({"completeness": {"per_site": {}}})


def test_per_site_kappa_over_double_judged_t0():
    def j(levels):
        return review3.normalise({"completeness": {"per_site": levels}})
    a = {"p": j({"x": "full", "y": "partial"}), "q": j({"x": "none", "y": "full"}),
         "r": FULL}
    b = {"p": j({"x": "full", "y": "none"}), "q": j({"x": "none", "y": "full"}),
         "r": FULL}
    ps = review3.reliability(a, b)["per_site"]
    assert ps["n_sites"] == 4 and ps["agreement"] == 0.75
    assert ps["kappa"] == pytest.approx(review3.cohen_kappa(
        ["full", "partial", "none", "full"], ["full", "none", "none", "full"]), abs=1e-3)


def test_kappas():
    assert review3.qwk([1, 2, 3], [1, 2, 3], [1, 2, 3, 4, 5]) == 1
    assert review3.qwk([1, 2], [2, 1], [1, 2]) == -1
    assert review3.qwk([3, 3], [3, 3], [1, 2, 3, 4, 5]) is None
    assert review3.cohen_kappa(["x", "x", "y", "y"], ["x", "y", "y", "y"]) == pytest.approx(0.5)
    a = {"p": FULL, "q": {**FULL, "maintainability": {"score": 2, "why": ""}}}
    b = {"p": FULL, "q": FULL, "r": FULL}
    rel = review3.reliability(a, b)
    assert rel["n_packets"] == 2
    assert rel["questions"]["maintainability"]["n"] == 2
    assert rel["questions"]["reuse"]["agreement"] == 1


def test_labels_match_tables3_keys():
    mapping = {"a": {"kind": "t0", "agent": "claude", "cond": "RC", "zone": "Z1",
                     "chain": "3", "step": "T0"},
               "b": {"kind": "step", "agent": "codex", "cond": "RL", "zone": "Z2",
                     "chain": "0", "step": "T2"},
               "c": {"kind": "step", "agent": "codex", "cond": "R", "zone": "Z2",
                     "chain": "0", "step": "T1"},
               "d": {"kind": "chain", "agent": "codex", "cond": "R", "zone": "Z2",
                     "chain": "0"}}
    judg = {"a": review3.normalise({"completeness": 0.5, "interface": 3,
                                    "disguised_duplication": False}),
            "b": review3.normalise({**FULL, "t2_reuse": "copy"}),
            "c": review3.normalise({**FULL, "one_place": [False, "two sites"]}),
            "d": review3.normalise({**FULL, "abstraction_drift": {"value": False}})}
    labels = review3.labels_from(judg, mapping)
    t0 = {"agent": "claude", "cond": "RC", "zone": "Z1", "chain": 3, "step": 0}
    t2 = {"agent": "codex", "cond": "RL", "zone": "Z2", "chain": 0, "step": "T2"}
    t1 = {"agent": "codex", "cond": "R", "zone": "Z2", "chain": 0, "step": "T1"}
    assert tables3.label(t0, labels, "completeness") == 0.5
    assert tables3.label(t0, labels, "completeness_lenient") is None   # legacy value only
    assert tables3.label(t0, labels, "interface") == 3
    assert tables3.label(t2, labels, "t2_reuse") == "copy"
    assert tables3.label(t1, labels, "one_place") is False
    assert labels["codex/R/Z2/0/chain"]["maintainability"] == 4
    assert labels["codex/RL/Z2/0/T2"]["maintainability"] == 4


def test_analyse_refuses_comparisons_without_kappa(tmp_path):
    mapping = {}
    s1, s2 = tmp_path / "scores", tmp_path / "scores2"
    s1.mkdir(), s2.mkdir()
    i = 0
    for cond, score in (("R", 3), ("RG", 4), ("RL", 4), ("RC", 5), ("F", 4)):
        for z in ("Z1", "Z2", "Z3", "Z4"):
            for c in range(3):
                pid = f"p{i}"
                i += 1
                mapping[pid] = {"kind": "chain", "agent": "claude", "cond": cond, "zone": z,
                                "chain": str(c)}
                j = {**FULL, "maintainability": {"score": score, "why": ""},
                     "abstraction_drift": {"value": False}}
                (s1 / f"{pid}.json").write_text(json.dumps(j))
    mp = tmp_path / "m.json"
    mp.write_text(json.dumps(mapping))
    res = review3.analyse(s1, s2, mp, labels_out=tmp_path / "labels.json",
                          kappa_out=tmp_path / "kappa.json")
    assert res["h1"] is None and "kappa" in res["refused"]
    # review LOW: nothing but the kappa is written before the kappa check passes
    assert not (tmp_path / "labels.json").exists()
    assert json.loads((tmp_path / "kappa.json").read_text()) == dict.fromkeys(
        review3.KAPPA_MEASURES)
    for pid in ("p0", "p20"):
        shutil.copy(s1 / f"{pid}.json", s2 / f"{pid}.json")
    # the planned second sample (batches.json) must be complete, not just non-empty
    batches = tmp_path / "batches.json"
    batches.write_text(json.dumps({"second": [["p0", "p20"], ["p40"]]}))
    res = review3.analyse(s1, s2, mp, labels_out=tmp_path / "labels.json", batches=batches)
    assert res["h1"] is None and "1/3" in res["refused"]
    assert not (tmp_path / "labels.json").exists()
    shutil.copy(s1 / "p40.json", s2 / "p40.json")
    res = review3.analyse(s1, s2, mp, out_md=tmp_path / "h1.md", batches=batches,
                          labels_out=tmp_path / "labels.json")
    assert (tmp_path / "labels.json").exists()
    assert res["reliability"]["second_missing"] == 0
    res = review3.analyse(s1, s2, mp, out_md=tmp_path / "h1.md")
    assert res["reliability"]["n_packets"] == 3
    c = res["h1"]["claude"]["RC"]["R"]["all"]["maintainability"]
    assert (c["mean_arm"], c["mean_ref"], c["zones_higher"]) == (5, 3, 4)
    assert "non_blind" in res["h1"]["claude"]["RL"]["R"]
    md = (tmp_path / "h1.md").read_text()
    assert md.index("Reliability") < md.index("## claude")


def test_flat_kappa_reaches_tables3(tmp_path):
    rel = {"questions": {"t2_reuse": {"kappa": 0.7}, "one_place": {"kappa": None},
                         "maintainability": {"kappa": 0.5}}}
    flat = review3.flat_kappa(rel)
    assert flat == {"t2_reuse": 0.7, "one_place": None, "completeness": None, "interface": None}
    f = tmp_path / "k.json"
    f.write_text(json.dumps(flat))
    assert tables3.load_kappa(f)["t2_reuse"] == 0.7
    full = tmp_path / "design_review3.json"         # the script's full result JSON
    full.write_text(json.dumps({"reliability": rel, "h1": {}}))
    assert tables3.load_kappa(full)["t2_reuse"] == 0.7
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"maintainability": 0.5}))
    with pytest.raises(ValueError):
        tables3.load_kappa(bad)
    with pytest.raises(OSError):
        tables3.load_kappa(tmp_path / "missing.json")
    assert tables3.load_kappa(None) == {}


def test_leak_scan_catches_paraphrases_and_lint_words():
    for text in ("// see AGENTS.md", "// agents.md says so", "// keep the duplication lint happy",
                 "// the ratchet fires here", "// Don't duplicate logic here",
                 "// extracted the logic into a shared helper", "// change it in a single place"):
        assert review3.text_leaks(text), text
        out, info = review3.sanitise_patch(patch(A, None, text + "\nconst k = 1;"), frozenset())
        assert info["redacted_lines"] == 1 and review3.text_leaks(out) == [], text
    # real code words stay
    for text in ("ratchetIncreasePct?: number;", "| 'ratcheting'", "const shared = 1;"):
        assert review3.text_leaks(text) == [], text


def test_any_agents_md_section_is_stripped():
    out, info = review3.sanitise_patch(patch("packages/x/AGENTS.md", None, "rules"), frozenset())
    assert out == "" and info["stripped_paths"] == ["packages/x/AGENTS.md"]
