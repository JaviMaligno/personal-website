"""Study 3 evaluator in the real arm images (plan Task 5; spec amendment 2026-10-11,
re-review MEDIUM finding). Docker only, marked integration; never more than one
loot-core container at a time (the Docker VM holds two at most).

Guard: in ``aa-actual:RL`` the evaluator's ``lint_ok`` (loot-core ``yarn lint`` =
``tsgo -b`` + dup-check) must judge the step against the step's own start tree. Before
the fix the evaluator's repository history was the image's (base -> variant ->
evalbase), dup-check took ``base`` as the start commit and failed on the untouched
tree with the R variant's own Z2 inlining clone (schedules/app.ts:591-601 ~
shared/schedules.ts:496-506)."""
import difflib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from aa import chain_eval, config

ACTIONS = "packages/loot-core/src/server/budget/actions.ts"


def _docker_or_skip(image: str) -> None:
    if shutil.which("docker") is None:
        pytest.skip("docker missing")
    if subprocess.run(["docker", "image", "inspect", image],
                      capture_output=True).returncode != 0:
        pytest.skip(f"{image} missing")


def _patch(path: str, old: str, new: str) -> str:
    body = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                        f"a/{path}", f"b/{path}"))
    return f"diff --git a/{path} b/{path}\n{body}"


def pasted_copy_patch(variant: Path) -> str:
    """A pasted, renamed copy of set3MonthAvg appended to actions.ts (as an agent
    extending the pattern would): a new clone on added lines."""
    old = (variant / ACTIONS).read_text()
    start = old.index("export async function set3MonthAvg")
    end = old.index("\n}\n", start) + 3
    copy = old[start:end].replace("set3MonthAvg", "set4MonthAvg").replace(
        "maxMonths: 3", "maxMonths: 4")
    return _patch(ACTIONS, old, old + "\n" + copy)


def make_rl_step(runs: Path, diff: str, chain: str = "0") -> Path:
    d = runs / "claude" / "RL" / "Z1" / chain / "T1"
    d.mkdir(parents=True)
    plan = {"from": "image", "patches": [], "expected_start_tree": None}
    (d / "start.json").write_text(json.dumps(plan))
    (d / "agent.json").write_text(json.dumps({
        "agent": "claude", "cond": "RL", "zone": "Z1", "chain": int(chain), "step": "T1",
        "study": 3, "status": "ok", "wall_s": 1.0, "carry": plan,
        "usage": {"input_tokens": 1, "output_tokens": 1, "turns": 1, "tool_calls": 0}}))
    (d / "diff.patch").write_text(diff)
    (d / "diff_ok").write_text("")
    (d / "transcript.jsonl").write_text("")
    return d


@pytest.fixture(scope="module")
def rl_results(tmp_path_factory):
    _docker_or_skip("aa-actual:RL")
    variant = config.WORK / "variants" / "RL"
    if not (variant / ACTIONS).exists():
        pytest.skip("work/variants/RL missing")
    runs = tmp_path_factory.mktemp("runs3")
    untouched = make_rl_step(runs, "", chain="0")
    pasted = make_rl_step(runs, pasted_copy_patch(variant), chain="1")
    out = {}
    for name, d in (("untouched", untouched), ("pasted", pasted)):  # serial: one container
        out[name] = chain_eval.evaluate_step(d, tests=False)
    yield out
    shutil.rmtree(runs, ignore_errors=True)


@pytest.mark.integration
def test_rl_untouched_step_tree_passes_the_evaluators_lint(rl_results):
    r = rl_results["untouched"]
    assert r["eval_error"] is None, r
    assert r["lint_ok"] is True
    assert r["ratchet_final"]["fires"] is False
    assert r["ratchet_kind"] is None


@pytest.mark.integration
def test_rl_pasted_copy_fails_the_evaluators_lint(rl_results):
    r = rl_results["pasted"]
    assert r["eval_error"] is None, r
    assert r["lint_ok"] is False
    assert r["ratchet_final"]["fires"] is True
    assert r["ratchet_kind"] == "adds_new_clone_side"
    assert any(c["a"] == ACTIONS and c["b"] == ACTIONS for c in r["ratchet_final"]["clones"])


@pytest.mark.integration
def test_fresh_start_tree_is_the_runners_start_tree(tmp_path):
    """The evaluator's `start` commit is the runner's: on a real study-2 R chain step
    (copied out of runs2, which stays read-only) its tree id equals the runner's
    recorded start_tree (the image repository's never does: its excludes differ). The
    step ran on aa-actual:R-study2 (its agent.json image_digest); aa-actual:R was rebuilt
    for study 3, and on it the check reports the mismatch, as it should."""
    _docker_or_skip("aa-actual:R-study2")
    src = Path("runs2/claude/R/Z1/0")
    if not (src / "T2" / "agent.json").exists():
        pytest.skip("runs2 missing")
    dst = tmp_path / "runs3" / "claude" / "R" / "Z1" / "0"
    for sid in ("T1", "T2"):
        (dst / sid).mkdir(parents=True)
        for f in ("agent.json", "start.json", "diff.patch", "diff_ok", "start_tree", "post_tree",
                  "transcript.jsonl"):
            if (src / sid / f).exists():
                shutil.copy(src / sid / f, dst / sid / f)
    meta = json.loads((dst / "T2" / "agent.json").read_text())
    (dst / "T2" / "agent.json").write_text(json.dumps({**meta, "study": 3}))
    from aa.evaluate import docker_execute
    image = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}",
                            "aa-actual:R-study2"], capture_output=True, text=True).stdout.strip()
    assert image == meta["image_digest"]

    def on_the_runs_image(argv, timeout):
        return docker_execute([a.replace("aa-actual:R", "aa-actual:R-study2")
                               if a == "aa-actual:R" else a for a in argv], timeout)
    r = chain_eval.evaluate_step(dst / "T2", tests=False, execute=on_the_runs_image)
    assert r["eval_error"] is None, r
    assert r["tree_check"]["start_fresh"] is True
    assert r["ratchet_error"] is None and r["ratchet_final"] is not None
    assert r["t2_reuses_logic"] == "copy"  # as the static check reads this R step


@pytest.fixture(scope="module")
def t0_reference(tmp_path_factory):
    _docker_or_skip("aa-actual:R")
    from aa import chain_eval3
    return chain_eval3.untouched_reference(tmp_path_factory.mktemp("ref") / "ref.json")


def _rc_t0_step(runs: Path, diff: str) -> Path:
    d = runs / "claude" / "RC" / "Z1" / "0" / "T0"
    d.mkdir(parents=True)
    plan = {"from": "image", "patches": [], "expected_start_tree": None}
    (d / "start.json").write_text(json.dumps(plan))
    (d / "agent.json").write_text(json.dumps({
        "agent": "claude", "cond": "RC", "zone": "Z1", "chain": 0, "step": "T0", "study": 3,
        "status": "ok", "wall_s": 1.0, "carry": plan,
        "usage": {"input_tokens": 1, "output_tokens": 1, "turns": 1, "tool_calls": 0}}))
    (d / "diff.patch").write_text(diff)
    (d / "diff_ok").write_text("")
    (d / "transcript.jsonl").write_text("")
    return d


@pytest.mark.integration
@pytest.mark.parametrize("seed,unified,probe_flags", [
    ("z1-setzero-skips-hidden", ["setzero-writes-hidden"], True),
    ("z1-excluded-missing-group", [], False),   # Review Focus 4: an excluded case only
])
def test_t0_evaluation_in_the_rc_image(tmp_path, t0_reference, seed, unified, probe_flags):
    _docker_or_skip("aa-actual:RC")
    from aa import chains
    t0 = chains.load_t0("Z1")
    sd = _rc_t0_step(tmp_path / "runs3", t0.seed_patch(seed).read_text())
    r = chain_eval.evaluate_step(sd, t0_reference=t0_reference)
    assert r["eval_error"] is None, (r, (sd / "eval" / "apply.log").read_text()[-2000:])
    assert r["inconsistencies_unified"] == unified
    assert bool(r["probe_changed_cases"]) is probe_flags, r["probe_changed_cases"]
    if not probe_flags:
        assert r["probe_changed_raw"]  # the excluded row changed, and was dropped
    assert r["correct"] is (not unified and not probe_flags)
    assert r["typecheck_ok"] is True and r["lint_ok"] is True, r
    assert r["related"] is not None and r["related_ok"] is True, r["related"]
    assert r["duplication_pre"] is not None and r["duplication_post"] is not None
    assert r["ratchet_error"] is None
    assert (sd / r["t0_packet"] / "sites.json").exists()


# --------------------------------------------------------------- pilot blocking item 9

def _z3_step(runs: Path, chain: str, diff: str) -> Path:
    d = runs / "claude" / "R" / "Z3" / chain / "T1"
    d.mkdir(parents=True)
    plan = {"from": "image", "patches": [], "expected_start_tree": None}
    (d / "start.json").write_text(json.dumps(plan))
    (d / "agent.json").write_text(json.dumps({
        "agent": "claude", "cond": "R", "zone": "Z3", "chain": int(chain), "step": "T1",
        "study": 3, "status": "ok", "carry": plan}))
    (d / "diff.patch").write_text(diff)
    (d / "diff_ok").write_text("")
    (d / "result.json").write_text(json.dumps({
        "agent": "claude", "cond": "R", "zone": "Z3", "chain": int(chain), "step": 1,
        "step_id": "T1", "study": 3, "status": "ok", "eval_error": None}))
    return d


@pytest.mark.integration
def test_behaviour_check_on_a_t1_post_tree_in_the_r_image(tmp_path):
    """The in-scope Z3 T0 inconsistency tests on a T1 post tree: an untouched tree keeps
    all three differences; the seeded Akahu unification (tasks3 sanity seed) is caught as
    akahu-changed-tables. Serial: one container at a time."""
    from aa import rederive
    from aa.chains import TASKS3
    _docker_or_skip("aa-actual:R")
    seed = (TASKS3 / "Z3" / "T0" / "sanity" / "z3-akahu-reports-accounts.patch").read_text()
    runs = tmp_path / "runs3"
    plain, unified = _z3_step(runs, "0", ""), _z3_step(runs, "1", seed)
    got = {}
    for name, d in (("plain", plain), ("unified", unified)):
        got[name] = rederive.behaviour_check_step(d)[1]
    assert got["plain"]["inconsistencies_unified_step"] == [], got["plain"]
    assert got["unified"]["inconsistencies_unified_step"] == ["akahu-changed-tables"], \
        got["unified"]
    assert set(got["plain"]["inconsistency_scope_detail"]["results"].values()) == {"passed"}
