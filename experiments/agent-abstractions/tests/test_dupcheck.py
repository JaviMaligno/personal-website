"""RL's duplication ratchet, ``packages/loot-core/bin/dup-check.mjs`` (plan Task 3,
Review Focus 1/2), run from ``substrate/patches/study3/rl.patch`` on fixture repos.

Static checks (patch wiring, pinned threshold) run everywhere; the script itself runs
with node and the pinned jscpd inside ``aa-actual:RL`` (the arm's own image) and skips
without Docker. Each fixture repo is built the way the chain runner builds a step
(``git init`` + one commit named ``start``); the agent's work is the working tree on
top of it. The smoke tests at the end run the real ``yarn lint`` entry points on the
Actual tree inside ``aa-actual:RL``."""
import json
import re
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

import pytest

from aa import config, ratchet, runner

RL_PATCH = config.PATCHES / "study3" / "rl.patch"
SCRIPT = "packages/loot-core/bin/dup-check.mjs"
CONFIG = "packages/loot-core/bin/dup-check.config.json"
SRC = "packages/loot-core/src/server"
CHECK = f"node {SCRIPT}"
RL_IMAGE = "aa-actual:RL"
HEADER = "dup-check: duplicated code on lines added or changed in this task:"
PASS_CONDITION = ("The check passes when no duplicated block includes a line added or "
                  "changed in this task.")


def _added_file(patch: str, path: str) -> str:
    """Content of a file the patch creates."""
    block = patch.split(f"+++ b/{path}\n", 1)[1].split("\ndiff --git ", 1)[0]
    return "".join(ln[1:] + "\n" for ln in block.splitlines() if ln.startswith("+"))


# --------------------------------------------------------------------------- static

def test_rl_patch_pins_the_calibrated_threshold():
    assert config.RATCHET_MIN_TOKENS == 35  # spec amendment 2026-10-11 (supersedes 25)
    cfg = json.loads(_added_file(RL_PATCH.read_text(), CONFIG))
    assert cfg == {"minTokens": config.RATCHET_MIN_TOKENS, "scope": ratchet.SCOPE}


# Every lint entry point runs the check, and runs it even when the command before it
# failed (an agent fixing a type or format error still sees its clones); the script
# fails when either part failed. Shell: yarn 4's portable shell (`;`, `$?`, `[`).
def _then_check(before: str, check: str) -> str:
    return f"{before}; a=$?; {check}; b=$?; [ $a -eq 0 ] && [ $b -eq 0 ]"


LOOT_CHECK = "node bin/dup-check.mjs"  # loot-core scripts run with cwd packages/loot-core
WIRING = {
    "package.json": [
        ("lint", "oxfmt --check . && oxlint --type-aware --quiet", CHECK),
        ("lint:fix", "oxfmt . && oxlint --fix --type-aware --quiet", CHECK),
    ],
    # the prompt's `yarn lint` in packages/loot-core (lint-script.patch: `tsgo -b`)
    "packages/loot-core/package.json": [("lint", "tsgo -b", LOOT_CHECK)],
}


def _patch_block(patch: str, path: str) -> list[str]:
    return patch.split(f"+++ b/{path}\n", 1)[1].split("\ndiff --git ", 1)[0].splitlines()


def test_rl_patch_wires_the_check_into_every_lint_script():
    patch = RL_PATCH.read_text()
    touched = re.findall(r"^\+\+\+ b/(\S+)$", patch, re.M)
    assert sorted(touched) == sorted([*WIRING, SCRIPT, CONFIG])
    for path, scripts in WIRING.items():
        block = _patch_block(patch, path)
        added = [ln[1:].strip() for ln in block if ln.startswith("+")]
        removed = [ln[1:].strip() for ln in block if ln.startswith("-")]
        assert added == [f'"{k}": "{_then_check(b, c)}",' for k, b, c in scripts], path
        assert removed == [f'"{k}": "{b}",' for k, b, _ in scripts], path


def test_lint_script_patch_still_gives_loot_core_lint_as_tsgo():
    # RL rewrites the loot-core `lint` line that lint-script.patch adds (R's lint).
    lp = (config.PATCHES / "lint-script.patch").read_text()
    assert '+    "lint": "tsgo -b",' in lp


# --------------------------------------------------------------------------- runs

BLOCK = textwrap.dedent("""\
    export function summarise(rows: Array<{ amount: number; hidden: number; income: number }>) {
      let total = 0;
      let hiddenTotal = 0;
      let incomeTotal = 0;
      for (const row of rows) {
        if (row.hidden === 1) {
          hiddenTotal += row.amount;
          continue;
        }
        if (row.income === 1) {
          incomeTotal += row.amount * 2 - Math.round(row.amount / 3);
        } else {
          total += Math.max(0, row.amount - Math.floor(row.amount / 7));
        }
      }
      return { total, hiddenTotal, incomeTotal, ratio: total / (incomeTotal || 1) };
    }
    """)
OTHER = textwrap.dedent("""\
    export function other(xs: Array<{ id: string; when: number; size: number }>) {
      const seen = new Map<string, number>();
      for (const x of xs) {
        const prev = seen.get(x.id) ?? 0;
        if (x.when > prev && x.size !== 42) {
          seen.set(x.id, x.when + x.size * 3 - prev);
        } else if (x.size === 42) {
          seen.delete(x.id);
        }
      }
      return [...seen.keys()].sort().join('|');
    }
    """)
HELPER_CALL = ("import { summarise } from './report';\n\n"
               "export function consumer(rows: Parameters<typeof summarise>[0]) {\n"
               "  return summarise(rows.filter(r => r.amount > 0));\n}\n")
PASTED = "import { x } from './x';\n\n" + BLOCK.replace("summarise", "summariseForConsumer")


def _docker_or_skip(image: str = RL_IMAGE):
    if shutil.which("docker") is None:
        pytest.skip("docker missing")
    if subprocess.run(["docker", "image", "inspect", image],
                      capture_output=True).returncode != 0:
        pytest.skip(f"{image} missing")


def _git(tree, *args):
    return subprocess.run(["git", "-c", "user.email=a@b", "-c", "user.name=a", *args],
                          cwd=tree, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A step's start tree: loot-core sources (with one pre-existing clone pair in
    misc.ts and a test file), the RL check from the patch, committed as `start`."""
    _docker_or_skip()
    (tmp_path / SRC).mkdir(parents=True)
    (tmp_path / SRC / "report.ts").write_text(BLOCK)
    (tmp_path / SRC / "misc.ts").write_text(OTHER + "\n" + OTHER.replace("other(", "other2("))
    (tmp_path / SRC / "report.test.ts").write_text(BLOCK.replace("summarise", "t"))
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "apply", f"--include={SCRIPT}", f"--include={CONFIG}", str(RL_PATCH))
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "start")
    return tmp_path, _git(tmp_path, "rev-parse", "HEAD")


def run_check(tree, *args):
    """`node dup-check.mjs` in the image, from the repo root (as `yarn lint` runs it)."""
    env = ["-e", "GIT_CONFIG_COUNT=1", "-e", "GIT_CONFIG_KEY_0=safe.directory",
           "-e", "GIT_CONFIG_VALUE_0=*"]  # bind mount owned by the host user
    argv = ["docker", "run", "--rm", "--network", "none", "-v", f"{tree}:/work/t",
            "-w", "/work/t", *env, "--entrypoint", "node", RL_IMAGE, SCRIPT, *args]
    return subprocess.run(argv, capture_output=True, text=True, timeout=300)


@pytest.mark.integration
def test_pasted_copy_fails_and_lists_the_clone(repo):
    tree, _ = repo
    (tree / SRC / "consumer.ts").write_text(PASTED)
    r = run_check(tree)
    assert r.returncode == 1, r.stdout + r.stderr
    out = r.stdout + r.stderr
    assert f"{SRC}/report.ts:1-" in out and f"{SRC}/consumer.ts:3-" in out
    assert "misc.ts" not in out  # the pre-existing clone is not the agent's
    # Reported as a lint reports: the failing check, the clones, the pass condition;
    # no advice on how to fix it.
    assert r.stdout.splitlines()[0] == HEADER
    assert r.stdout.splitlines()[-1] == PASS_CONDITION
    assert "introduced" not in r.stdout  # the rule also covers edits inside old clones
    assert all(ln.startswith("  ") for ln in r.stdout.splitlines()[1:-1])


@pytest.mark.integration
def test_calling_a_helper_passes(repo):
    tree, _ = repo
    (tree / SRC / "consumer.ts").write_text(HELPER_CALL)
    r = run_check(tree)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "dup-check: ok" in r.stdout


@pytest.mark.integration
def test_unrelated_preexisting_clone_passes(repo):
    tree, _ = repo
    with open(tree / SRC / "report.ts", "a") as f:
        f.write("\nexport const VERSION = 2;\n")
    r = run_check(tree)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.integration
def test_copy_in_a_tracked_file_after_agent_commits_still_fails(repo):
    # The agent commits its work (twice): the check still diffs against `start`.
    tree, _ = repo
    with open(tree / SRC / "misc.ts", "a") as f:
        f.write("\n" + BLOCK.replace("summarise", "summariseAgain"))
    _git(tree, "commit", "-qam", "wip")
    _git(tree, "commit", "-q", "--allow-empty", "-m", "more")
    r = run_check(tree)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"{SRC}/misc.ts:" in r.stdout


@pytest.mark.integration
def test_repo_jscpd_config_does_not_silence_the_check(repo):
    tree, _ = repo
    (tree / ".jscpd.json").write_text('{"ignore": ["**/*.ts"], "minTokens": 500}')
    (tree / SRC / ".jscpd.json").write_text('{"ignore": ["**/*.ts"]}')
    (tree / SRC / "consumer.ts").write_text(PASTED)
    assert run_check(tree).returncode == 1


@pytest.mark.integration
def test_test_files_are_not_scanned(repo):
    tree, _ = repo
    (tree / SRC / "consumer.test.ts").write_text(PASTED)
    assert run_check(tree).returncode == 0


@pytest.mark.integration
def test_no_start_commit_is_an_error_not_a_pass(repo):
    tree, _ = repo
    shutil.rmtree(tree / ".git")
    (tree / SRC / "consumer.ts").write_text(PASTED)
    r = run_check(tree)
    assert r.returncode == 2
    assert "start commit" in r.stderr


@pytest.mark.integration
def test_same_clones_as_the_harness_detector(repo):
    # The in-image lint and the harness's ratchet (aa.ratchet, used for calibration
    # and ratchet_final) must agree on what a new clone is.
    tree, start = repo
    (tree / SRC / "consumer.ts").write_text(PASTED)
    with open(tree / SRC / "misc.ts", "a") as f:
        f.write("\n" + OTHER.replace("other(", "other3("))
    r = run_check(tree, "--json")
    assert r.returncode == 1, r.stderr
    got = json.loads(r.stdout)
    assert got["start"] == start and got["minTokens"] == config.RATCHET_MIN_TOKENS
    want = ratchet.new_clones(tree, start, config.RATCHET_MIN_TOKENS)
    key = lambda c: (c["a"], c["a_start"], c["a_end"], c["b"], c["b_start"], c["b_end"])  # noqa: E731
    assert sorted(map(key, got["clones"])) == sorted(
        (c.a, c.a_start, c.a_end, c.b, c.b_start, c.b_end) for c in want)
    assert len(want) >= 2 and got["unresolved"] == 0


def test_env_is_not_used_to_pick_the_start_commit():
    # The agent controls its own environment; the start commit must come from git.
    if not RL_PATCH.exists():
        pytest.skip("rl.patch missing")
    src = _added_file(RL_PATCH.read_text(), SCRIPT)
    assert "process.env" not in src


# --------------------------------------------------------------------------- RL smoke
# The real entry points in aa-actual:RL on the Actual tree, started as the chain runner
# starts a step (fresh repository, one commit named `start`). One container, serial
# (each `yarn lint` takes a while; the Docker VM holds two loot-core containers at most).

SMOKE = r"""
set -u
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
cd /work/actual
cp packages/loot-core/bin/dup-check.mjs /out/image-dup-check.mjs
node -e 'const r=require("./package.json").scripts, l=require("./packages/loot-core/package.json").scripts; console.log(JSON.stringify({lint: r.lint, "lint:fix": r["lint:fix"], loot_lint: l.lint}))' > /out/scripts.json
git add -A && git commit -q --allow-empty -m image
rm -rf .git && git init -q -b main && git add -A && git commit -qm start
run() { n=$1; d=$2; shift 2; ( cd "$d" && "$@" ) > /out/$n.log 2>&1; echo $? > /out/$n.rc; }
L=packages/loot-core
A=$L/src/server/budget/actions.ts
run untouched_loot $L yarn lint
# a pasted copy of set3MonthAvg (renamed), as an agent extending the pattern would
{ echo; sed -n '/^export async function set3MonthAvg/,/^}$/p' $A \
  | sed 's/set3MonthAvg/set4MonthAvg/; s/maxMonths: 3/maxMonths: 4/'; } >> $A
grep -q set4MonthAvg $A || exit 3
cp $A /out/actions-with-copy.ts
run copy_loot $L yarn lint
run copy_root . yarn lint
run copy_root_fix . yarn lint:fix
# + a formatting error (oxfmt --check fails, so oxlint is skipped by its &&)
printf 'export const   fmtBad =1\n' > $L/src/server/fmt-bad.ts
run fmt_root . yarn lint
rm $L/src/server/fmt-bad.ts
# + an oxlint error, formatted: a `never` in a template literal
cat > $L/src/server/lint-bad.ts <<'TS'
export function lintBad(kind: 'a'): string {
  switch (kind) {
    case 'a':
      return 'a';
    default:
      throw new Error(`bad ${kind}`);
  }
}
TS
run oxlint_root . yarn lint
rm $L/src/server/lint-bad.ts
# + a type error (loot-core's lint starts with tsgo -b)
printf "export const typeBad: number = 'a';\n" > $L/src/server/type-bad.ts
run type_loot $L yarn lint
echo done > /out/done
"""


@pytest.fixture(scope="module")
def rl_smoke():
    _docker_or_skip(RL_IMAGE)
    out = Path(tempfile.mkdtemp(prefix="aa-rl-smoke-"))
    argv = ["docker", "run", "--rm", "--network", "none", "--cpus", runner.CPUS,
            "--memory", runner.MEMORY, "-v", f"{out}:/out", "--entrypoint", "bash",
            RL_IMAGE, "-c", SMOKE]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=3600)
    assert (out / "done").exists(), p.stdout[-2000:] + p.stderr[-2000:]

    def res(name):
        return int((out / f"{name}.rc").read_text()), (out / f"{name}.log").read_text()

    yield out, res
    shutil.rmtree(out, ignore_errors=True)


def _lists_the_clone(log: str) -> bool:
    a = "packages/loot-core/src/server/budget/actions.ts"
    rows = [ln for ln in log.splitlines() if ln.startswith("  ") and " ~ " in ln]
    return (HEADER in log and PASS_CONDITION in log
            and any(ln.count(a + ":") == 2 for ln in rows))


@pytest.mark.integration
def test_rl_image_carries_the_patch(rl_smoke):
    out, _ = rl_smoke
    assert (out / "image-dup-check.mjs").read_text() == _added_file(RL_PATCH.read_text(), SCRIPT)
    (root_lint, root_fix), (loot_lint,) = WIRING["package.json"], WIRING[
        "packages/loot-core/package.json"]
    assert json.loads((out / "scripts.json").read_text()) == {
        "lint": _then_check(*root_lint[1:]), "lint:fix": _then_check(*root_fix[1:]),
        "loot_lint": _then_check(*loot_lint[1:])}


@pytest.mark.integration
def test_rl_untouched_tree_passes_loot_core_lint(rl_smoke):
    _, res = rl_smoke
    rc, log = res("untouched_loot")
    assert rc == 0, log[-3000:]
    assert "dup-check: ok" in log


@pytest.mark.integration
@pytest.mark.parametrize("name", ["copy_loot", "copy_root", "copy_root_fix"])
def test_rl_pasted_copy_fails_every_lint_entry_point(rl_smoke, name):
    _, res = rl_smoke
    rc, log = res(name)
    assert rc != 0, log[-3000:]
    assert _lists_the_clone(log), log[-3000:]


@pytest.mark.integration
def test_rl_copy_alone_fails_only_the_ratchet(rl_smoke):
    # With only the copy, formatting and oxlint pass: the failure is the ratchet's.
    _, res = rl_smoke
    log = res("copy_root")[1]
    assert "All matched files use the correct format" in log
    assert re.search(r"Found \d+ warnings? and 0 errors?", log), log[-3000:]


@pytest.mark.integration
@pytest.mark.parametrize("name,marker", [
    ("fmt_root", "fmt-bad.ts"),                         # oxfmt --check failed
    ("oxlint_root", "restrict-template-expressions"),   # oxlint failed
    ("type_loot", "type-bad.ts"),                       # tsgo -b failed
])
def test_rl_check_still_runs_after_another_check_fails(rl_smoke, name, marker):
    _, res = rl_smoke
    rc, log = res(name)
    assert rc != 0
    assert marker in log, log[-3000:]
    assert _lists_the_clone(log), log[-3000:]
