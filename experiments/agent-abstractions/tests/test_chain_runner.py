"""Chain runner (study 2 plan Task 3, study 3 plan Task 4) with a fake agent.

The real container script runs locally under bash: a fresh copy of a small "image"
git repo stands in for each fresh container, and a fake agent (Python) acts on
``DO`` lines in its step statement. No Docker, no real agents.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from aa import chain_runner as cr


def untagged(name: str) -> str:
    """A container name without its runs-root tag."""
    return re.sub(r"^(aa\d)-[0-9a-f]{6}-", r"\1-", name)
from aa import runner
from aa.chains import ChainError, list_zones, load_chain

FAKE_AGENT = r'''
import json, os, shutil, subprocess, sys
out, prompt = sys.argv[1], sys.argv[2]
cmds = [l[3:].strip() for l in open(prompt).read().splitlines() if l.startswith("DO ")]
def result(turns=3):
    with open(os.path.join(out, "transcript.jsonl"), "w") as f:
        f.write(json.dumps({"type": "system", "subtype": "init", "model": "claude-sonnet-5-5"}) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {"model": "claude-sonnet-5-5",
                            "content": []}}) + "\n")
        f.write(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                            "num_turns": turns, "result": "done",
                            "usage": {"input_tokens": 10, "output_tokens": 5}}) + "\n")
for c in cmds:
    op, *rest = c.split(" ", 2)
    if op == "APPEND":          # APPEND <path> <text>
        os.makedirs(os.path.dirname(rest[0]) or ".", exist_ok=True)
        with open(rest[0], "a") as f:
            f.write(rest[1] + "\n")
    elif op == "DELETE":
        os.remove(rest[0])
    elif op == "COMMIT":
        subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-qam", "agent"], check=True)
    elif op == "RMGIT":
        shutil.rmtree(".git")
    elif op == "AMEND":         # rewrite the start commit itself (same message)
        subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-q", "-a", "--amend",
                        "-m", "start"], check=True)
    elif op == "REINIT":        # a fresh repository whose root is a new "start"
        shutil.rmtree(".git")
        subprocess.run(["git", "init", "-q", "-b", "main"], check=True)
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-qm", "start"], check=True)
    elif op == "ORPHAN":        # HEAD on an unrelated history; the old start still exists
        subprocess.run(["git", "checkout", "-q", "--orphan", "other"], check=True)
        subprocess.run(["git", "-c", "commit.gpgsign=false", "commit", "-qam", "other"], check=True)
    elif op == "ASSUME":        # hide a file's later edits from `git add -A`
        subprocess.run(["git", "update-index", "--assume-unchanged", rest[0]], check=True)
    elif op == "SKIPWT":
        subprocess.run(["git", "update-index", "--skip-worktree", rest[0]], check=True)
    elif op == "STASH":
        subprocess.run(["git", "stash", "-q"], check=True)
    elif op == "GITATTR":       # .gitattributes in the tree
        with open(".gitattributes", "a") as f:
            f.write("*.ts -diff\n")
    elif op == "NOATTR":        # replace .gitattributes, dropping the text=auto rule
        with open(".gitattributes", "w") as f:
            f.write("*.md -diff\n")
    elif op == "INFOATTR":      # attributes outside the tree
        with open(".git/info/attributes", "a") as f:
            f.write("*.ts -diff\n")
    elif op == "EXCLUDE":
        with open(".git/info/exclude", "a") as f:
            f.write("src/hidden.ts\n")
    elif op == "STALL":          # the API connection drops; the CLI retries until killed
        with open(os.path.join(out, "transcript.jsonl"), "w") as f:
            f.write(json.dumps({"type": "system", "subtype": "init"}) + "\n")
            f.write(json.dumps({"type": "assistant", "message": {"id": "m1", "model": "claude-sonnet-5-5",
                                "content": [{"type": "text", "text": "Working."}],
                                "usage": {"input_tokens": 10, "output_tokens": 5}}}) + "\n")
            for i in range(3):
                f.write(json.dumps({"type": "system", "subtype": "api_retry", "attempt": i + 1,
                                    "error": "Connection error."}) + "\n")
        sys.exit(124)
    elif op == "INFRA_ONCE":     # first attempt: crash before doing anything
        marker = rest[0]
        if not os.path.exists(marker):
            open(marker, "w").close()
            sys.exit(1)
result()
'''


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_AUTHOR_NAME", "t")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "t@t")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "t")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "t@t")
    monkeypatch.setattr(runner, "image_digest", lambda tag: "sha256:test")
    # "image": variant history (must never reach the agent) + an uncommitted
    # install-step edit + an ignored node_modules dir.
    image = tmp_path / "image"
    (image / "src").mkdir(parents=True)
    (image / "src" / "a.ts").write_text("export const a = 1;\n")
    (image / "src" / "b.ts").write_text("export const b = 2;\n")
    (image / ".gitignore").write_text("node_modules\n")
    _git(image, "init", "-q", "-b", "main")
    _git(image, "add", "-A")
    _git(image, "commit", "-qm", "variant: SECRET treatment commit")
    (image / "package.json").write_text('{"installed": true}\n')
    (image / "node_modules" / "x").mkdir(parents=True)
    (image / "node_modules" / "x" / "i.js").write_text("1\n")
    fake = tmp_path / "fake_agent.py"
    fake.write_text(FAKE_AGENT)
    ctrs = tmp_path / "containers"
    ctrs.mkdir()
    seen: list[dict] = []

    def launcher(agent, cond, name, prompt_file, out_dir, tmp, wall, turns):
        ctr = ctrs / f"{name}-{len(seen)}"
        shutil.copytree(image, ctr, symlinks=True)  # fresh container from the image
        seen.append({"name": name, "ctr": ctr, "wall": wall, "turns": turns, "cond": cond})
        cmd = f"cd '{ctr}' && '{sys.executable}' '{fake}' '{out_dir}' '{prompt_file}'"
        # HOME isolated: the git-hiding check reads ~/.config/git/{attributes,ignore}
        script = (f"export HOME='{tmp}'\n"
                  + cr.chain_container_script(agent, wall, workdir=str(ctr), out=str(out_dir),
                                              agent_cmd=cmd, auth="true", turn_limit=turns,
                                              version_cmd="echo '9.9.9 (Fake Code)'"))
        return ["bash", "-c", script], dict(os.environ)

    def executor(argv, env_, stdin_file, timeout_s, name):
        with stdin_file.open("rb") as fin:
            p = subprocess.run(argv, env=env_, stdin=fin, capture_output=True, timeout=120)
        return p.returncode, p.stderr.decode()[-4000:]

    return {"root": tmp_path, "image": image, "launcher": launcher, "executor": executor,
            "seen": seen, "tasks": tmp_path / "tasks2", "runs": tmp_path / "runs2",
            "tasks3": tmp_path / "tasks3", "runs3": tmp_path / "runs3"}


def make_chain(tasks: Path, zone: str, statements: list[str]) -> None:
    z = tasks / zone
    z.mkdir(parents=True, exist_ok=True)
    steps = []
    for i, s in enumerate(statements, start=1):
        (z / f"T{i}").mkdir(exist_ok=True)
        (z / f"T{i}" / "statement.md").write_text(s + "\n")
        (z / f"T{i}" / "hidden").mkdir(exist_ok=True)
        (z / f"T{i}" / "hidden" / "t.test.ts").write_text("HIDDEN TEST\n")
        steps.append({"id": f"T{i}", "kind": "rule", "consumers": ["c1"]})
    (z / "chain.json").write_text(json.dumps({"zone": zone, "steps": steps}))


def make_t0(tasks3: Path, zone: str, statement: str) -> None:
    d = tasks3 / zone / "T0"
    (d / "hidden").mkdir(parents=True, exist_ok=True)
    (d / "statement.md").write_text(statement + "\n")
    (d / "hidden" / "t0.test.ts").write_text("HIDDEN T0 TEST\n")


def run(env, agent="claude", cond="R", zone="Z1", chain=0, **kw):
    return cr.run_chain(agent, cond, zone, chain, runs_root=env["runs"], tasks_root=env["tasks"],
                        wall_limit_s=60, launcher=env["launcher"], executor=env["executor"], **kw)


def run3(env, cond="RC", agent="claude", zone="Z1", chain=0, **kw):
    return cr.run_chain(agent, cond, zone, chain, runs_root=env["runs3"],
                        tasks_root=env["tasks"], wall_limit_s=60, launcher=env["launcher"],
                        executor=env["executor"], study=3, t0_root=env["tasks3"], **kw)


def agent_json(d: Path) -> dict:
    return json.loads((d / "agent.json").read_text())


def tree_of(ctr: Path) -> dict[str, str]:
    return {str(p.relative_to(ctr)): p.read_text() for p in sorted(ctr.rglob("*"))
            if p.is_file() and ".git" not in p.parts and "node_modules" not in p.parts}


# --------------------------------------------------------------------------- loader

def test_load_chain_and_validation(tmp_path):
    make_chain(tmp_path, "Z1", ["s1", "s2"])
    ch = load_chain("Z1", tmp_path)
    assert ch.step_ids == ("T1", "T2") and ch.steps[0].consumers == ("c1",)
    assert list_zones(tmp_path) == ["Z1"]
    meta = json.loads((tmp_path / "Z1" / "chain.json").read_text())
    meta["steps"][1]["id"] = "T3"
    (tmp_path / "Z1" / "chain.json").write_text(json.dumps(meta))
    with pytest.raises(ChainError):
        load_chain("Z1", tmp_path)
    with pytest.raises(ChainError):
        load_chain("Z9", tmp_path)


# --------------------------------------------------------------------------- carrying

def test_state_carried_between_steps(env):
    make_chain(env["tasks"], "Z1", [
        "DO APPEND src/a.ts // T1",
        "DO APPEND src/new.ts // T2 new consumer",
        "DO DELETE src/b.ts",
        "DO APPEND src/a.ts // T4",
    ])
    res = run(env)
    assert res.status == "ok"
    cdir = cr.chain_dir("claude", "R", "Z1", 0, env["runs"])
    recs = [agent_json(cdir / f"T{i}") for i in range(1, 5)]
    assert [r["status"] for r in recs] == ["ok"] * 4
    # Tree ids chain exactly: start of k == post of k-1.
    for prev, cur in zip(recs, recs[1:]):
        assert cur["carry"]["start_tree"] == prev["post_tree"]
        assert cur["carry"]["exact"] is True
    assert recs[0]["carry"] == {"from": "image", "patches": [], "expected_start_tree": None,
                                "start_tree": recs[0]["carry"]["start_tree"], "exact": None}
    assert recs[3]["carry"]["patches"] == ["T1/diff.patch", "T2/diff.patch", "T3/diff.patch"]
    # The container of T4 started with T1..T3's work.
    t4 = env["seen"][3]["ctr"]
    tree = tree_of(t4)
    assert tree["src/a.ts"] == "export const a = 1;\n// T1\n// T4\n"
    assert "src/new.ts" in tree and "src/b.ts" not in tree
    # Each step's diff holds only that step's change.
    d4 = (cdir / "T4" / "diff.patch").read_text()
    assert "+// T4" in d4 and "new.ts" not in d4
    chain = json.loads((cdir / "chain.json").read_text())
    assert chain["status"] == "ok" and set(chain["steps"].values()) == {"ok"}


def test_no_history_hidden_tests_or_bundle_reach_the_agent(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1", "DO APPEND src/a.ts // T2"])
    assert run(env).status == "ok"
    t2 = env["seen"][1]["ctr"]
    log = _git(t2, "log", "--format=%s", "--all")
    assert "SECRET" not in log and "agent" not in log.split()  # only the fresh start commit
    assert log.split() == ["start"]
    assert not any("HIDDEN" in v for v in tree_of(t2).values())
    assert not any(p.suffix in (".patch", ".tar") for p in t2.rglob("*")
                   if "node_modules" not in p.parts)


def test_agent_commit_is_kept_in_diff(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1\nDO COMMIT x",
                                    "DO APPEND src/b.ts // T2"])
    assert run(env).status == "ok"
    cdir = cr.chain_dir("claude", "R", "Z1", 0, env["runs"])
    assert "+// T1" in (cdir / "T1" / "diff.patch").read_text()
    assert tree_of(env["seen"][1]["ctr"])["src/a.ts"] == "export const a = 1;\n// T1\n"
    assert agent_json(cdir / "T2")["carry"]["exact"] is True


def _start_record(cdir: Path, step: str) -> dict:
    r = agent_json(cdir / step)
    return {k: r.get(k) for k in ("start_commit", "start_commit_after",
                                  "start_commit_ancestor", "start_commit_rewritten")}


def test_start_commit_recorded_before_and_after_the_agent(env):
    # Agent commits on top of `start` (allowed): the start commit is unchanged.
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1\nDO COMMIT x",
                                    "DO APPEND src/b.ts // T2"])
    assert run(env).status == "ok"
    cdir = cr.chain_dir("claude", "R", "Z1", 0, env["runs"])
    for step in ("T1", "T2"):
        rec = _start_record(cdir, step)
        assert len(rec["start_commit"]) == 40
        assert rec == {"start_commit": rec["start_commit"],
                       "start_commit_after": rec["start_commit"],
                       "start_commit_ancestor": True, "start_commit_rewritten": False}


@pytest.mark.parametrize("op", ["AMEND", "REINIT", "ORPHAN", "RMGIT"])
def test_start_commit_rewritten_is_flagged(env, op):
    make_chain(env["tasks"], "Z1", [f"DO APPEND src/a.ts // T1\nDO {op} x"])
    assert run(env).status == "ok"
    cdir = cr.chain_dir("claude", "R", "Z1", 0, env["runs"])
    rec = _start_record(cdir, "T1")
    assert len(rec["start_commit"]) == 40
    assert rec["start_commit_rewritten"] is True
    if op in ("AMEND", "REINIT"):
        assert rec["start_commit_after"] not in (None, rec["start_commit"])
    if op == "RMGIT":
        assert rec["start_commit_after"] is None and rec["start_commit_ancestor"] is None
    if op == "ORPHAN":
        assert rec["start_commit_ancestor"] is False
    from aa import static3
    assert static3.runner_flags(agent_json(cdir / "T1")) == {"start_commit_rewritten": ["start"]}


def test_tree_fallback_when_agent_destroys_git(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1\nDO RMGIT x",
                                    "DO APPEND src/b.ts // T2",
                                    "DO APPEND src/b.ts // T3"])
    assert run(env).status == "ok"
    cdir = cr.chain_dir("claude", "R", "Z1", 0, env["runs"])
    r1, r2, r3 = (agent_json(cdir / f"T{i}") for i in (1, 2, 3))
    assert r1["status"] == "ok" and not r1["diff_ok"] and r1["tree_fallback"]
    with tarfile.open(cdir / "T1" / "tree.tar") as t:
        names = t.getnames()
    assert not any("node_modules" in n or n.rstrip("/") == "./.git" or n.startswith("./.git/") for n in names)
    assert "./src/a.ts" in names
    assert r2["carry"]["from"] == "T1/tree.tar" and r2["carry"]["patches"] == []
    assert r3["carry"] == r3["carry"] | {"from": "T1/tree.tar", "patches": ["T2/diff.patch"],
                                         "exact": True}
    tree = tree_of(env["seen"][2]["ctr"])
    assert "// T1" in tree["src/a.ts"] and tree["src/b.ts"].endswith("// T2\n// T3\n")


def test_broken_step_does_not_stop_the_chain(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts this is {{ not typescript",
                                    "DO APPEND src/b.ts // T2"])
    res = run(env)
    assert res.status == "ok"
    tree = tree_of(env["seen"][1]["ctr"])
    assert "not typescript" in tree["src/a.ts"]


def test_chains_are_isolated(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // CHAIN-X", "DO APPEND src/b.ts // s2"])
    assert run(env, chain=0).status == "ok"
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // CHAIN-Y", "DO APPEND src/b.ts // s2"])
    assert run(env, chain=1).status == "ok"
    assert run(env, cond="F", chain=0).status == "ok"
    t2_chain1 = tree_of(env["seen"][3]["ctr"])
    assert "CHAIN-Y" in t2_chain1["src/a.ts"] and "CHAIN-X" not in t2_chain1["src/a.ts"]
    t2_f = tree_of(env["seen"][5]["ctr"])
    assert "CHAIN-Y" in t2_f["src/a.ts"] and "CHAIN-X" not in t2_f["src/a.ts"]
    dirs = {cr.chain_dir("claude", c, "Z1", i, env["runs"]) for c, i in (("R", 0), ("R", 1), ("F", 0))}
    assert len(dirs) == 3 and all((d / "T2" / "agent.json").exists() for d in dirs)
    names = [untagged(e["name"]) for e in env["seen"]]
    assert names[0] == "aa2-claude-r-z1-0-t1" and names[2] == "aa2-claude-r-z1-1-t1"


def test_infra_stops_chain_and_resume_continues(env):
    marker = env["root"] / "infra-marker"
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1",
                                    f"DO INFRA_ONCE {marker}\nDO APPEND src/b.ts // T2",
                                    "DO APPEND src/a.ts // T3"])
    res = run(env)
    assert res.status == "infra" and res.step_path.name == "T2"
    cdir = cr.chain_dir("claude", "R", "Z1", 0, env["runs"])
    assert not (cdir / "T3").exists()
    t1_before = (cdir / "T1" / "agent.json").read_text()
    res = run(env)
    assert res.status == "ok"
    assert (cdir / "T1" / "agent.json").read_text() == t1_before  # not re-run
    assert len(env["seen"]) == 4  # T1, T2 (infra), T2, T3


def test_rerunning_a_step_drops_later_steps(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1", "DO APPEND src/b.ts // T2",
                                    "DO APPEND src/a.ts // T3"])
    assert run(env).status == "ok"
    cdir = cr.chain_dir("claude", "R", "Z1", 0, env["runs"])
    res = run(env, only_step="T2")
    assert res.status == "ok" and res.step_path.name == "T2"
    assert not (cdir / "T3").exists()
    assert run(env).status == "ok" and (cdir / "T3" / "agent.json").exists()


def test_only_step_requires_carried_predecessors(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1", "DO APPEND src/b.ts // T2"])
    res = run(env, only_step="T2")
    assert res.status != "ok" and res.step_path.name == "T1"
    assert env["seen"] == []


def test_carry_mismatch_is_setup_error(env, monkeypatch):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1", "DO APPEND src/b.ts // T2"])
    assert run(env, only_step="T1").status == "ok"
    cdir = cr.chain_dir("claude", "R", "Z1", 0, env["runs"])
    (cdir / "T1" / "post_tree").write_text("0" * 40 + "\n")
    res = run(env)
    assert res.status == "setup_error"
    rec = agent_json(cdir / "T2")
    assert rec["carry"]["exact"] is False and "carry mismatch" in rec["error"]
    assert json.loads((cdir / "chain.json").read_text())["status"] == "setup_error"
    assert run(env).status == "setup_error"  # final: not re-run
    assert len(env["seen"]) == 2


def test_missing_statement_is_harness_error_record(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1"])
    (env["tasks"] / "Z1" / "T1" / "statement.md").unlink()
    with pytest.raises(ChainError):
        run(env)


# --------------------------------------------------------------------------- container / argv

def test_docker_argv_isolation(tmp_path):
    argv = cr.chain_docker_argv("codex", "F", "aa2-codex-f-z1-0-t1", tmp_path / "p.txt",
                                tmp_path / "out", tmp_path / "auth", 1500)
    assert argv[:4] == ["docker", "run", "--rm", "-i"]
    assert "aa-actual:F" in argv
    mounts = [argv[i + 1] for i, a in enumerate(argv) if a == "-v"]
    assert mounts == [f"{tmp_path / 'p.txt'}:/task/prompt.txt:ro", f"{tmp_path / 'out'}:/out",
                      f"{tmp_path / 'auth'}:/codex-auth:ro"]
    assert "github.com:0.0.0.0" in argv
    script = argv[-1]
    assert "timeout 1500" in script and "model_reasoning_effort=medium" in script
    assert "--disable apps" in script and "hidden" not in script
    claude = cr.chain_docker_argv("claude", "R", "n", tmp_path / "p", tmp_path / "o")
    assert "CLAUDE_CODE_OAUTH_TOKEN" in claude and "--disallowedTools WebSearch,WebFetch" in claude[-1]
    with pytest.raises(ValueError):
        cr.chain_docker_argv("codex", "R", "n", tmp_path / "p", tmp_path / "o")


# --------------------------------------------------------------------------- scheduler

def test_build_chain_queue_and_indices():
    q = cr.build_chain_queue("claude", ["R", "F"], ["Z1", "Z2"], [0, 1])
    assert len(q) == 8 and len(set(q)) == 8
    assert {(j.zone, j.chain_idx) for j in q[:2]} == {("Z1", 0)}
    assert q == cr.build_chain_queue("claude", ["R", "F"], ["Z1", "Z2"], [0, 1])
    assert cr.parse_indices("3") == [0, 1, 2]
    assert cr.parse_indices("0,2-4") == [0, 2, 3, 4]


def test_scheduler_infra_backoff_and_exhaustion(tmp_path):
    jobs = cr.build_chain_queue("claude", ["R", "F"], ["Z1"], [0])
    step = tmp_path / "T2"
    step.mkdir()
    (step / "agent.json").write_text(json.dumps({"status": "infra"}))
    calls: dict[cr.ChainJob, int] = {}
    sleeps: list[float] = []

    def run_(j):
        calls[j] = calls.get(j, 0) + 1
        if j.cond == "R":
            return cr.ChainResult("infra", step)
        return cr.ChainResult("infra", step) if calls[j] == 1 else cr.ChainResult("ok", None)

    res = cr.ChainScheduler(jobs, run=run_, status_of=lambda j: None, workers=1,
                            sleep=sleeps.append, max_infra_attempts=3, log=lambda m: None).execute()
    r = next(j for j in jobs if j.cond == "R")
    f = next(j for j in jobs if j.cond == "F")
    assert res[r] == "infra_exhausted" and calls[r] == 3
    assert res[f] == "ok" and calls[f] == 2
    assert json.loads((step / "agent.json").read_text())["status"] == "infra_exhausted"
    assert sleeps  # global pause applied


def test_scheduler_skips_finished_chains_and_survives_exceptions():
    jobs = cr.build_chain_queue("codex", ["R", "F"], ["Z1"], [0])
    ran: list = []

    def run_(j):
        ran.append(j)
        raise RuntimeError("boom")

    res = cr.ChainScheduler(jobs, run=run_, workers=2, log=lambda m: None,
                            status_of=lambda j: "ok" if j.cond == "R" else None).execute()
    assert [j.cond for j in ran] == ["F"]
    assert {j.cond: s for j, s in res.items()} == {"R": "ok", "F": "harness_error"}


# --------------------------------------------------------------------------- CLI

def test_cli_chain_run_validates_and_dispatches(tmp_path, monkeypatch, capsys):
    from aa import cli
    assert cli.main(["chain", "run", "--agent", "claude", "--tasks", str(tmp_path)]) == 2
    make_chain(tmp_path, "Z2", ["s"])
    assert cli.main(["chain", "run", "--agent", "claude", "--conds", "A",
                     "--tasks", str(tmp_path)]) == 2
    seen = {}

    def fake_all(agent, conds, zones, chains, workers, runs_root, tasks_root, study=None,
                 t0_root=None):
        seen.update(agent=agent, conds=conds, zones=zones, chains=chains, workers=workers)
        return {}

    monkeypatch.setattr(cr, "run_all_chains", fake_all)
    assert cli.main(["chain", "run", "--agent", "codex", "--chains", "0,2", "--workers", "2",
                     "--tasks", str(tmp_path), "--runs", str(tmp_path / "r")]) == 0
    assert seen == {"agent": "codex", "conds": ["R", "F"], "zones": ["Z2"], "chains": [0, 2],
                    "workers": 2}


# =========================================================================== study 3

def _tree_id_of(image: Path, patches: list[Path], scratch: Path) -> str:
    """git tree id of the image's files + ``patches`` applied, outside the runner."""
    w = scratch / "replay"
    shutil.copytree(image, w, symlinks=True)
    shutil.rmtree(w / ".git")
    _git(w, "init", "-q", "-b", "main")
    _git(w, "add", "-A")
    for p in patches:
        _git(w, "apply", "--index", str(p))
    return _git(w, "write-tree").strip()


def test_rc_t1_pre_image_is_the_t0_diff(env):
    """Review Focus 3: an RC chain runs T0 first and T1 starts from exactly T0's tree."""
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1 rule",
                                    "DO APPEND src/new.ts // T2 consumer"])
    make_t0(env["tasks3"], "Z1", "DO APPEND src/shared.ts export const shared = 1;\n"
                                 "DO APPEND src/a.ts // T0 uses shared")
    res = run3(env)
    assert res.status == "ok"
    cdir = cr.chain_dir("claude", "RC", "Z1", 0, env["runs3"])
    t0, t1, t2 = (agent_json(cdir / s) for s in ("T0", "T1", "T2"))
    assert [r["status"] for r in (t0, t1, t2)] == ["ok"] * 3
    # T1's start = image + T0's verified diff, and its tree id is T0's post tree.
    assert t1["carry"]["from"] == "image" and t1["carry"]["patches"] == ["T0/diff.patch"]
    assert t1["carry"]["start_tree"] == t0["post_tree"] and t1["carry"]["exact"] is True
    assert t1["carry"]["start_tree"] == _tree_id_of(env["image"], [cdir / "T0" / "diff.patch"],
                                                    env["root"])
    assert t2["carry"]["patches"] == ["T0/diff.patch", "T1/diff.patch"]
    # The container of T1 held T0's work (then T1's edit); T1's diff holds only T1's change.
    tree = tree_of(env["seen"][1]["ctr"])
    assert tree["src/shared.ts"] == "export const shared = 1;\n"
    assert tree["src/a.ts"] == "export const a = 1;\n// T0 uses shared\n// T1 rule\n"
    d1 = (cdir / "T1" / "diff.patch").read_text()
    added = [ln for ln in d1.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    assert added == ["+// T1 rule"] and "shared.ts" not in d1
    # No T0 hidden test or history reaches T1's agent.
    assert not any("HIDDEN" in v for v in tree.values())
    assert _git(env["seen"][1]["ctr"], "log", "--format=%s", "--all").split() == ["start"]


def test_rc_t0_limits_and_indices(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1", "DO APPEND src/b.ts // T2"])
    make_t0(env["tasks3"], "Z1", "DO APPEND src/a.ts // T0")
    assert run3(env).status == "ok"
    cdir = cr.chain_dir("claude", "RC", "Z1", 0, env["runs3"])
    t0, t1, t2 = (agent_json(cdir / s) for s in ("T0", "T1", "T2"))
    # T0: 40 min / 90 turns, outside the T1..T4 indices; T1..: the chain's limits.
    assert t0["limits"] == {"wall_s": 40 * 60, "turns": 90} and t0["step_index"] is None
    assert t1["limits"] == {"wall_s": 60, "turns": 60} and t1["step_index"] == 0
    assert t2["step_index"] == 1 and t0["study"] == t1["study"] == 3
    assert [(e["wall"], e["turns"]) for e in env["seen"]] == [(2400, 90), (60, 60), (60, 60)]
    assert [untagged(e["name"]) for e in env["seen"]] == ["aa3-claude-rc-z1-0-t0", "aa3-claude-rc-z1-0-t1",
                                                "aa3-claude-rc-z1-0-t2"]
    chain = json.loads((cdir / "chain.json").read_text())
    assert chain["steps"] == {"T0": "ok", "T1": "ok", "T2": "ok"}
    assert chain["status"] == "ok" and chain["study"] == 3


def test_t0_turn_limit_classifies_timeout_at_90_not_60(env, monkeypatch):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1"])
    make_t0(env["tasks3"], "Z1", "DO APPEND src/a.ts // T0")
    real = cr.parse_stream

    def parse(agent, lines):  # 75 turns: over T1's 60, under T0's 90
        usage, outcome = real(agent, lines)
        usage.turns = 75
        return usage, outcome

    monkeypatch.setattr(cr, "parse_stream", parse)
    assert run3(env).status == "ok"
    cdir = cr.chain_dir("claude", "RC", "Z1", 0, env["runs3"])
    assert agent_json(cdir / "T0")["status"] == "ok"
    assert agent_json(cdir / "T1")["status"] == "timeout"


def test_rc_rerun_of_t0_drops_t1_and_resume(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1"])
    make_t0(env["tasks3"], "Z1", "DO APPEND src/a.ts // T0")
    assert run3(env).status == "ok"
    cdir = cr.chain_dir("claude", "RC", "Z1", 0, env["runs3"])
    res = run3(env, only_step="T0")
    assert res.status == "ok" and not (cdir / "T1").exists()
    assert run3(env).status == "ok" and (cdir / "T1" / "agent.json").exists()


def test_rc_without_t0_statement_fails_loudly(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1"])
    from aa.chains import T0Error
    with pytest.raises(T0Error):
        run3(env)
    assert env["seen"] == []


@pytest.mark.parametrize("cond", ["R", "RG", "RL"])
def test_other_arms_run_t1_to_t4_on_their_image(env, cond):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1", "DO APPEND src/b.ts // T2"])
    make_t0(env["tasks3"], "Z1", "DO APPEND src/a.ts // T0")
    assert run3(env, cond=cond).status == "ok"
    cdir = cr.chain_dir("claude", cond, "Z1", 0, env["runs3"])
    assert sorted(p.name for p in cdir.iterdir() if p.is_dir()) == ["T1", "T2"]
    assert [e["cond"] for e in env["seen"]] == [cond, cond]
    assert "T0" not in tree_of(env["seen"][0]["ctr"])["src/a.ts"]


def test_study3_chains_isolated_per_agent_arm_zone_chain(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1"])
    make_chain(env["tasks"], "Z2", ["DO APPEND src/b.ts // Z2-T1"])
    make_t0(env["tasks3"], "Z1", "DO APPEND src/a.ts // RC-T0")
    make_t0(env["tasks3"], "Z2", "DO APPEND src/b.ts // RC-T0")
    for agent, cond, zone, chain in (("claude", "RC", "Z1", 0), ("claude", "R", "Z1", 0),
                                     ("claude", "RC", "Z1", 1), ("haiku", "RC", "Z1", 0),
                                     ("claude", "RC", "Z2", 0)):
        assert run3(env, cond=cond, agent=agent, zone=zone, chain=chain).status == "ok"
    dirs = {cr.chain_dir(a, c, z, i, env["runs3"]) for a, c, z, i in (
        ("claude", "RC", "Z1", 0), ("claude", "R", "Z1", 0), ("claude", "RC", "Z1", 1),
        ("haiku", "RC", "Z1", 0), ("claude", "RC", "Z2", 0))}
    assert len(dirs) == 5
    # each T1 started from its own chain's T0 only (one T0 line, not two)
    for e in env["seen"]:
        if e["name"].endswith("-t1") and "-rc-z1-" in e["name"]:
            assert tree_of(e["ctr"])["src/a.ts"].count("RC-T0") == 1
    # the R chain never saw RC's T0
    r_t1 = next(e for e in env["seen"] if untagged(e["name"]) == "aa3-claude-r-z1-0-t1")
    assert "RC-T0" not in tree_of(r_t1["ctr"])["src/a.ts"]
    assert not env["runs"].exists()  # study 3 never writes into runs2


def test_study_conditions_validated():
    assert cr.study_of(["R", "F"]) == 2 and cr.study_of(["R"]) == 2
    assert cr.study_of(["R", "RG"]) == 3 and cr.study_of(["R"], 3) == 3
    with pytest.raises(ValueError):
        cr.study_of(["F"], 3)
    with pytest.raises(ValueError):
        cr.study_of(["RC"], 2)
    with pytest.raises(ValueError):
        cr.study_of(["RC", "F"])
    with pytest.raises(ValueError):
        cr.study_of(["A"])
    with pytest.raises(ValueError):
        cr.run_chain("claude", "RC", "Z1", 0, study=2)


# --------------------------------------------------------------------------- run records

def test_model_and_cli_version_recorded(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1"])
    assert run(env).status == "ok"
    rec = agent_json(cr.chain_dir("claude", "R", "Z1", 0, env["runs"]) / "T1")
    assert rec["model"] == "claude-sonnet-5-5" and rec["cli_version"] == "2.1.289"
    assert rec["model_reported"] == ["claude-sonnet-5-5"]
    assert rec["cli_version_reported"] == "9.9.9 (Fake Code)"


def test_reported_models_parsing():
    lines = [json.dumps({"type": "system", "subtype": "init", "model": "claude-haiku-5-5"}),
             json.dumps({"type": "assistant", "message": {"model": "claude-haiku-5-5"}}),
             json.dumps({"type": "assistant", "message": {"model": "claude-sonnet-5-5"}}),
             "not json", json.dumps({"type": "item.completed", "item": {"type": "x"}})]
    assert cr.reported_models(lines) == ["claude-haiku-5-5", "claude-sonnet-5-5"]
    assert cr.reported_models([json.dumps({"type": "turn.started"})]) == []


def test_reported_models_on_study2_transcripts():
    """Real study-2 transcripts (read-only fixtures): Claude Code names its model, Codex none."""
    base = Path(__file__).resolve().parents[1] / "runs2"
    cases = {"claude": ["claude-sonnet-5-5"], "haiku": ["claude-haiku-5-5"], "codex": []}
    for agent, want in cases.items():
        t = base / agent / "R" / "Z1" / "0" / "T1" / "transcript.jsonl"
        if not t.exists():
            pytest.skip("runs2 fixtures not present")
        got = cr.reported_models(t.read_text(errors="replace").splitlines())
        assert got[:1] == want[:1] and (want or not got)


def test_docker_argv_records_cli_version_and_turn_limit(tmp_path):
    claude = cr.chain_docker_argv("claude", "RC", "n", tmp_path / "p", tmp_path / "o",
                                  wall_limit_s=2400, turn_limit=90)
    assert "aa-actual:RC" in claude
    script = claude[-1]
    assert "claude --version > \"$O/cli_version\"" in script
    assert "--max-turns 90" in script and "timeout 2400" in script
    codex = cr.chain_docker_argv("codex", "RL", "n", tmp_path / "p", tmp_path / "o",
                                 tmp_path / "auth")
    assert "codex --version > \"$O/cli_version\"" in codex[-1] and "aa-actual:RL" in codex
    # T1..T4 default stays 60 turns
    assert "--max-turns 60" in cr.chain_docker_argv("haiku", "R", "n", tmp_path / "p",
                                                    tmp_path / "o")[-1]


# --------------------------------------------------------------------------- git hiding

def _hiding(env, statement: str) -> tuple[dict, dict]:
    make_chain(env["tasks"], "Z1", [statement])
    assert run(env).status == "ok"
    rec = agent_json(cr.chain_dir("claude", "R", "Z1", 0, env["runs"]) / "T1")
    from aa import static3
    return rec["git_hiding"], static3.runner_flags(rec)


def test_git_hiding_clean_run(env):
    gh, flags = _hiding(env, "DO APPEND src/a.ts // T1")
    assert gh == {"gitattributes_changed": [], "attributes_sources": [], "index_flags": [],
                  "excludes_sources": [], "stash_present": False}
    assert flags == {}


def test_git_hiding_gitattributes_added(env):
    gh, flags = _hiding(env, "DO APPEND src/a.ts // T1\nDO GITATTR x")
    assert gh["gitattributes_changed"] == [".gitattributes"]
    assert flags == {"git_diff_suppressed": [".gitattributes"]}


def test_git_hiding_info_attributes(env):
    gh, flags = _hiding(env, "DO APPEND src/a.ts // T1\nDO INFOATTR x")
    assert gh["attributes_sources"] == ["info/attributes"]
    assert flags == {"git_diff_suppressed": ["info/attributes"]}


def test_git_hiding_assume_unchanged(env):
    gh, flags = _hiding(env, "DO ASSUME src/a.ts\nDO APPEND src/a.ts // hidden edit")
    assert gh["index_flags"] == ["h src/a.ts"]
    assert flags == {"index_hidden_files": ["src/a.ts"]}


def test_git_hiding_skip_worktree(env):
    gh, flags = _hiding(env, "DO SKIPWT src/b.ts\nDO APPEND src/b.ts // hidden edit")
    assert gh["index_flags"] == ["S src/b.ts"]
    assert flags == {"index_hidden_files": ["src/b.ts"]}


def test_git_hiding_info_exclude(env):
    gh, flags = _hiding(env, "DO EXCLUDE x\nDO APPEND src/hidden.ts // new file")
    assert gh["excludes_sources"] == ["info/exclude"]
    assert flags == {"index_hidden_files": ["info/exclude"]}


def test_git_hiding_stash(env):
    gh, flags = _hiding(env, "DO APPEND src/a.ts // stashed\nDO STASH x")
    assert gh["stash_present"] is True
    assert flags == {"stash_present": ["refs/stash"]}


def test_git_hiding_unreadable_without_git(env):
    gh, flags = _hiding(env, "DO APPEND src/a.ts // T1\nDO RMGIT x")
    assert gh is None and flags == {"start_commit_rewritten": ["start"]}


# --------------------------------------------------------------------------- scheduler (study 3)

def test_queue3_rotates_arm_order_by_chain_index():
    q = cr.build_chain_queue3("claude", ["R", "RG", "RL", "RC"], ["Z1", "Z2"], range(8))
    assert len(q) == 8 * 2 * 4 and len(set(q)) == len(q)
    assert [j.chain_idx for j in q] == sorted(j.chain_idx for j in q)  # by chain index
    arms = list(cr.ARMS)
    assert arms == ["R", "RG", "RL", "RC"]
    for i in range(8):
        for zi, z in enumerate(("Z1", "Z2")):
            order = [j.cond for j in q if j.chain_idx == i and j.zone == z]
            # amendment 2026-10-11e: offset by the zone index too
            assert order == [arms[(i + k + zi) % 4] for k in range(4)]
    firsts = [q[k].cond for k in range(0, len(q), 4)]
    assert {a: firsts.count(a) for a in arms} == {a: 4 for a in arms}  # each first equally
    assert q[:4] == [cr.ChainJob("claude", a, "Z1", 0) for a in ("R", "RG", "RL", "RC")]
    assert [j.cond for j in q[8:12]] == ["RG", "RL", "RC", "R"]  # chain 1, Z1


def test_queue3_pilot_each_arm_first_in_one_zone():
    """Spec amendment 2026-10-11e: with one chain per cell (the pilot) every zone used to
    run R, RG, RL, RC in the same order; offsetting by the zone index makes each arm
    first in exactly one zone."""
    q = cr.build_chain_queue3("claude", list(cr.ARMS), ["Z1", "Z2", "Z3", "Z4"], [0])
    firsts = {z: next(j.cond for j in q if j.zone == z) for z in ("Z1", "Z2", "Z3", "Z4")}
    assert firsts == {"Z1": "R", "Z2": "RG", "Z3": "RL", "Z4": "RC"}
    # the zone index is the zone's own (Z3 alone still starts at RL), not its list position
    q3 = cr.build_chain_queue3("claude", list(cr.ARMS), ["Z3"], [0])
    assert [j.cond for j in q3] == ["RL", "RC", "R", "RG"]


def test_queue3_balanced_over_eight_chains_per_zone():
    q = cr.build_chain_queue3("codex", list(cr.ARMS), ["Z1", "Z2", "Z3", "Z4"], range(8))
    for z in ("Z1", "Z2", "Z3", "Z4"):
        for pos in range(4):
            at = [[j.cond for j in q if j.chain_idx == i and j.zone == z][pos]
                  for i in range(8)]
            assert {a: at.count(a) for a in cr.ARMS} == {a: 2 for a in cr.ARMS}, (z, pos)


def test_queue3_subset_and_validation():
    q = cr.build_chain_queue3("haiku", ["RC", "R"], ["Z3"], [0, 1])
    assert [j.cond for j in q] == ["R", "RC", "RC", "R"]
    with pytest.raises(ValueError):
        cr.build_chain_queue3("haiku", ["R", "F"], ["Z3"], [0])


# build_chain_queue's output before study 3 touched the module (same seed, same order).
STUDY2_QUEUE = [("R", "Z1", 0), ("F", "Z1", 0), ("F", "Z2", 0), ("R", "Z2", 0),
                ("R", "Z1", 1), ("F", "Z1", 1), ("F", "Z2", 1), ("R", "Z2", 1)]


def test_study2_queue_unchanged():
    """Regression: study 2's seeded shuffle, as runs2 was scheduled."""
    q = cr.build_chain_queue("claude", ["R", "F"], ["Z1", "Z2"], [0, 1])
    assert [(j.cond, j.zone, j.chain_idx) for j in q] == STUDY2_QUEUE


def test_run_all_chains_dispatches_by_study(env, monkeypatch):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1"])
    make_t0(env["tasks3"], "Z1", "DO APPEND src/a.ts // T0")
    r2, r3 = env["root"] / "default-runs2", env["root"] / "default-runs3"
    monkeypatch.setitem(cr.STUDY_RUNS, 2, r2)
    monkeypatch.setitem(cr.STUDY_RUNS, 3, r3)
    calls: list[tuple] = []

    def fake_run_chain(agent, cond, zone, idx, runs_root, tasks_root, study=2, t0_root=None):
        calls.append((cond, idx, runs_root, study, t0_root))
        return cr.ChainResult("ok", None)

    monkeypatch.setattr(cr, "run_chain", fake_run_chain)
    cr.run_all_chains("claude", ["R", "F"], ["Z1"], [0], workers=1, tasks_root=env["tasks"])
    assert {c[2] for c in calls} == {r2} and {c[3] for c in calls} == {2}
    assert [c[0] for c in calls] == [j.cond for j in cr.build_chain_queue(
        "claude", ["R", "F"], ["Z1"], [0])]
    calls.clear()
    cr.run_all_chains("claude", ["R", "RG", "RL", "RC"], ["Z1"], [0, 1], workers=1,
                      tasks_root=env["tasks"], t0_root=env["tasks3"])
    assert {c[2] for c in calls} == {r3} and {c[3] for c in calls} == {3}
    assert [c[0] for c in calls] == ["R", "RG", "RL", "RC", "RG", "RL", "RC", "R"]
    assert {c[4] for c in calls} == {env["tasks3"]}
    calls.clear()
    cr.run_all_chains("claude", ["R"], ["Z1"], [0], workers=1, tasks_root=env["tasks"],
                      study=3, t0_root=env["tasks3"])
    assert calls == [("R", 0, r3, 3, env["tasks3"])]
    with pytest.raises(ValueError):
        cr.run_all_chains("claude", ["RC", "F"], ["Z1"], [0], tasks_root=env["tasks"])


def test_status_of_counts_t0_for_rc(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1"])
    make_t0(env["tasks3"], "Z1", "DO APPEND src/a.ts // T0")
    assert run3(env, only_step="T0").status == "ok"
    status_of = cr._default_status_of(env["runs3"], env["tasks"], env["tasks3"])
    job = cr.ChainJob("claude", "RC", "Z1", 0)
    assert status_of(job) is None  # T1 still missing
    assert run3(env).status == "ok" and status_of(job) == "ok"


# --------------------------------------------------------------------------- CLI (study 3)

def _cli_capture(monkeypatch):
    seen: dict = {}

    def fake_all(agent, conds, zones, chains, workers, runs_root, tasks_root, study=None,
                 t0_root=None):
        seen.update(agent=agent, conds=conds, zones=zones, chains=chains, workers=workers,
                    runs=runs_root, tasks=tasks_root, study=study, t0=t0_root)
        return {}

    monkeypatch.setattr(cr, "run_all_chains", fake_all)
    return seen


def test_cli_chain_run_study3(tmp_path, monkeypatch):
    from aa import cli
    make_chain(tmp_path / "t2", "Z1", ["s"])
    seen = _cli_capture(monkeypatch)
    base = ["chain", "run", "--agent", "haiku", "--tasks", str(tmp_path / "t2")]
    # arms imply study 3 -> runs3, absolute
    assert cli.main(base + ["--conds", "R,RG,RL,RC"]) == 0
    assert seen["study"] == 3 and seen["runs"] == cr.RUNS3 and seen["runs"].is_absolute()
    assert seen["conds"] == ["R", "RG", "RL", "RC"] and seen["t0"] == cli_tasks3()
    # --study 3 alone: every arm
    assert cli.main(base + ["--study", "3"]) == 0
    assert seen["conds"] == list(cr.ARMS) and seen["study"] == 3
    # pilot dir
    assert cli.main(base + ["--study", "3", "--pilot"]) == 0
    assert seen["runs"] == cr.RUNS_PILOT[3]
    # relative --runs made absolute
    monkeypatch.chdir(tmp_path)
    assert cli.main(base + ["--conds", "RC", "--runs", "rel3"]) == 0
    assert seen["runs"] == (tmp_path / "rel3").resolve()
    # invalid mixes
    assert cli.main(base + ["--conds", "RC,F"]) == 2
    assert cli.main(base + ["--conds", "F", "--study", "3"]) == 2


def test_cli_chain_run_study2_unchanged(tmp_path, monkeypatch):
    from aa import cli
    make_chain(tmp_path / "t2", "Z1", ["s"])
    seen = _cli_capture(monkeypatch)
    assert cli.main(["chain", "run", "--agent", "claude", "--tasks", str(tmp_path / "t2")]) == 0
    assert seen["conds"] == ["R", "F"] and seen["study"] == 2 and seen["runs"] == cr.RUNS2


def test_cli_chain_run_one_accepts_arms(tmp_path, monkeypatch):
    from aa import cli
    got = {}

    def fake_chain(agent, cond, zone, chain, runs_root=None, tasks_root=None, only_step=None,
                   study=2, t0_root=None):
        got.update(cond=cond, runs=runs_root, study=study, step=only_step)
        return cr.ChainResult("ok", None)

    monkeypatch.setattr(cr, "run_chain", fake_chain)
    assert cli.main(["chain", "run-one", "--agent", "codex", "--cond", "RC", "--zone", "Z1",
                     "--step", "T0"]) == 0
    assert got == {"cond": "RC", "runs": cr.RUNS3, "study": 3, "step": "T0"}
    assert cli.main(["chain", "run-one", "--agent", "codex", "--cond", "R", "--zone", "Z1"]) == 0
    assert got["study"] == 2 and got["runs"] == cr.RUNS2


def cli_tasks3() -> Path:
    from aa.chains import TASKS3
    return TASKS3


def test_gitattributes_change_still_carries_exactly(env):
    """An agent that drops ``* text=auto`` must not break the carry: the next step's
    fresh ``git add -A`` hashes CRLF files under the new attributes, so the dump
    renormalizes when a .gitattributes changed (found by the Docker smoke on Actual)."""
    image = env["image"]
    (image / ".gitattributes").write_text("* text=auto\n")
    (image / "src" / "crlf.txt").write_bytes(b"one\r\ntwo\r\n")
    # old, as in the image (a fresh file is racily clean and git re-hashes it anyway)
    os.utime(image / "src" / "crlf.txt", (1_600_000_000, 1_600_000_000))
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1\nDO NOATTR x",
                                    "DO APPEND src/b.ts // T2", "DO APPEND src/b.ts // T3"])
    assert run(env).status == "ok"
    cdir = cr.chain_dir("claude", "R", "Z1", 0, env["runs"])
    recs = [agent_json(cdir / f"T{i}") for i in (1, 2, 3)]
    assert [r["status"] for r in recs] == ["ok"] * 3
    assert recs[1]["carry"]["exact"] is True and recs[2]["carry"]["exact"] is True
    assert recs[0]["git_hiding"]["gitattributes_changed"] == [".gitattributes"]
    # the working files are untouched by the renormalization (only the index is)
    assert (env["seen"][1]["ctr"] / "src" / "crlf.txt").read_bytes() == b"one\r\ntwo\r\n"


def test_container_names_carry_the_runs_root_tag(tmp_path):
    a = cr.container_name("claude", "RC", "Z1", 0, "T0", 3, runs_root=tmp_path / "runs3")
    b = cr.container_name("claude", "RC", "Z1", 0, "T0", 3, runs_root=tmp_path / "runs3-pilot")
    assert a != b and untagged(a) == untagged(b) == "aa3-claude-rc-z1-0-t0"
    assert cr.root_tag(tmp_path / "runs3") in a


def test_runner_uses_the_runs_root_tag(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1"])
    assert run(env, chain=0).status == "ok"
    assert env["seen"][0]["name"] == cr.container_name(
        "claude", "R", "Z1", 0, "T1", 2, runs_root=env["runs"])


# --------------------------------------------------------------------------- study-3 pilot item 1

STALL_TRANSCRIPT = [
    {"type": "system", "subtype": "init"},
    {"type": "assistant", "message": {"id": "m1", "model": "claude-sonnet-5-5",
                                      "content": [{"type": "text", "text": "Working."}],
                                      "usage": {"input_tokens": 10, "output_tokens": 5}}},
    {"type": "system", "subtype": "api_retry", "attempt": 1, "error": "Connection error."},
]


def test_network_stall_during_a_step_is_infra_and_not_carried(env):
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1", "DO STALL", "DO APPEND src/a.ts // T3"])
    res = run(env)
    cdir = cr.chain_dir("claude", "R", "Z1", 0, env["runs"])
    assert res.status == "infra" and res.step_path.name == "T2"
    a = agent_json(cdir / "T2")
    assert a["exit_code"] == 124 and a["status"] == "infra"
    assert not (cdir / "T3").exists()


def test_reclassified_pilot_step_is_resumed_and_its_later_steps_discarded(env, capsys):
    """The pilot's codex/R/Z3/0/T1 and codex/RC/Z3/0/T2 shape: a step stored as `timeout`
    (exit 124) whose transcript ends in transport errors, with later steps carried from
    it. `aa chain reclassify` makes it infra; `aa chain run` resumes there and drops the
    later steps (listed by --dry-run)."""
    from aa import cli, rederive
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1", "DO APPEND src/b.ts // T2",
                                    "DO APPEND src/a.ts // T3"])
    assert run(env).status == "ok"
    cdir = cr.chain_dir("claude", "R", "Z1", 0, env["runs"])
    # rewrite T2 as the pilot stored it (evidence shape, in a test tree)
    (cdir / "T2" / "transcript.jsonl").write_text(
        "\n".join(json.dumps(e) for e in STALL_TRANSCRIPT) + "\n")
    a = agent_json(cdir / "T2")
    a.update(status="timeout", outcome="infra", exit_code=124)
    (cdir / "T2" / "agent.json").write_text(json.dumps(a))
    (cdir / "T2" / "result.json").write_text(json.dumps({"status": "timeout", "correct": True}))
    t1_before = (cdir / "T1" / "agent.json").read_text()

    dry = rederive.reclassify_runs(env["runs"], apply=False)
    assert [r["step"] for r in dry["applied"]] == ["claude/R/Z1/0/T2"]
    assert agent_json(cdir / "T2")["status"] == "timeout"  # dry run writes nothing
    out = rederive.reclassify_runs(env["runs"])
    assert out["applied"][0]["reason"] == "transport_stall" and out["other"] == []
    a2 = agent_json(cdir / "T2")
    assert a2["status"] == "infra"
    assert a2["status_reclassified"]["from"] == "timeout" and a2["status_reclassified"]["to"] == "infra"
    assert a2["exit_code"] == 124 and a2["usage"] == a["usage"]  # nothing else rewritten
    assert json.loads((cdir / "T2" / "result.json").read_text())["status"] == "infra"
    assert json.loads((cdir / "chain.json").read_text())["status"] is None
    log = [json.loads(ln) for ln in (env["runs"] / "rederive-log.jsonl").read_text().splitlines()]
    assert log[0]["kind"] == "reclassify" and log[0]["step"] == "claude/R/Z1/0/T2"
    # a second pass finds nothing (idempotent)
    assert rederive.reclassify_runs(env["runs"])["applied"] == []

    assert cr.resume_plan(cdir, ["T1", "T2", "T3"]) == {"resume_from": "T2", "status": "infra",
                                                        "discard": ["T3"]}
    assert cli.main(["chain", "run", "--agent", "claude", "--conds", "R", "--zones", "Z1",
                     "--chains", "1", "--runs", str(env["runs"]), "--tasks", str(env["tasks"]),
                     "--dry-run"]) == 0
    assert "claude/R/Z1/0\tresume T2 (infra), discard T3" in capsys.readouterr().out
    n = len(env["seen"])
    assert run(env).status == "ok"
    assert [untagged(e["name"]) for e in env["seen"][n:]] == ["aa2-claude-r-z1-0-t2",
                                                             "aa2-claude-r-z1-0-t3"]
    assert (cdir / "T1" / "agent.json").read_text() == t1_before
    assert "status_reclassified" not in agent_json(cdir / "T2")  # a fresh run
    assert cr.resume_plan(cdir, ["T1", "T2", "T3"])["resume_from"] is None


def test_reclassify_leaves_real_agent_timeouts_and_ok_steps(env):
    from aa import rederive
    make_chain(env["tasks"], "Z1", ["DO APPEND src/a.ts // T1"])
    assert run(env).status == "ok"
    cdir = cr.chain_dir("claude", "R", "Z1", 0, env["runs"])
    a = agent_json(cdir / "T1")
    a.update(status="timeout", exit_code=124)  # killed while working: stays a timeout
    (cdir / "T1" / "agent.json").write_text(json.dumps(a))
    assert rederive.reclassify_runs(env["runs"])["applied"] == []
    assert agent_json(cdir / "T1")["status"] == "timeout"
