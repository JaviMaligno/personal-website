"""Duplication ratchet detector (study 3 plan Task 1, Review Focus 1).

Pure parts (diff parsing, jscpd name resolution, the touch rule) run everywhere; the
end-to-end cases run the pinned jscpd inside ``aa-actual:R`` and skip without Docker."""
import shutil
import subprocess
import textwrap

import pytest

from aa import ratchet
from aa.ratchet import Clone

DIFF = textwrap.dedent("""\
    diff --git a/packages/loot-core/src/server/a.ts b/packages/loot-core/src/server/a.ts
    index 1111111..2222222 100644
    --- a/packages/loot-core/src/server/a.ts
    +++ b/packages/loot-core/src/server/a.ts
    @@ -3,0 +4,3 @@ function f() {
    +x
    +y
    +z
    @@ -10 +12 @@ function g() {
    -old
    +new
    @@ -20,2 +21,0 @@ function h() {
    -gone
    -gone
    diff --git a/packages/loot-core/src/server/old.ts b/packages/loot-core/src/server/old.ts
    deleted file mode 100644
    index 3333333..0000000
    --- a/packages/loot-core/src/server/old.ts
    +++ /dev/null
    @@ -1,2 +0,0 @@
    -a
    -b
    diff --git a/packages/loot-core/src/server/new.ts b/packages/loot-core/src/server/new.ts
    new file mode 100644
    index 0000000..4444444
    --- /dev/null
    +++ b/packages/loot-core/src/server/new.ts
    @@ -0,0 +1,2 @@
    +a
    +b
    """)


def test_parse_changed_lines_added_and_modified_only():
    got = ratchet.parse_changed_lines(DIFF)
    assert got == {
        "packages/loot-core/src/server/a.ts": {4, 5, 6, 12},
        "packages/loot-core/src/server/new.ts": {1, 2},
    }


FILES = ["packages/loot-core/src/server/budget/actions.ts",
         "packages/loot-core/src/server/accounts/app.ts",
         "packages/loot-core/src/server/budget/app.ts",
         "packages/loot-core/src/shared/months.ts"]


@pytest.mark.parametrize("name,want", [
    ("actions.ts", FILES[0]),                       # bare basename, unique
    ("months.ts", FILES[3]),
    ("app.ts", None),                               # ambiguous basename -> dropped
    ("budget/app.ts", FILES[2]),                    # relative to the common root
    ("server/accounts/app.ts", FILES[1]),
    ("/src/packages/loot-core/src/shared/months.ts", FILES[3]),  # absolute in container
    ("other.ts", None),
    ("udget/app.ts", None),                         # suffix must start at a path segment
])
def test_resolve_name(name, want):
    assert ratchet.resolve_name(name, FILES) == want


def _dup(a, a0, a1, b, b0, b1, lines=5, tokens=60):
    return {"firstFile": {"name": a, "start": a0, "end": a1},
            "secondFile": {"name": b, "start": b0, "end": b1},
            "lines": lines, "tokens": tokens}


def test_parse_clones_resolves_and_counts_unresolved():
    rep = {"duplicates": [_dup("actions.ts", 1, 5, "months.ts", 10, 14),
                          _dup("app.ts", 1, 5, "months.ts", 20, 24)]}
    clones, unresolved = ratchet.parse_clones(rep, FILES)
    assert clones == [Clone(FILES[0], 1, 5, FILES[3], 10, 14, 5, 60)]
    assert unresolved == 1
    assert ratchet.parse_clones({}, FILES) == ([], 0)


def test_touching_keeps_clones_with_a_side_on_changed_lines():
    c_new = Clone(FILES[0], 1, 5, FILES[3], 10, 14, 5, 60)      # b side overlaps line 12
    c_edge = Clone(FILES[0], 30, 40, FILES[1], 1, 9, 10, 60)    # a side ends on line 30
    c_old = Clone(FILES[0], 100, 110, FILES[1], 50, 60, 10, 60)  # untouched both sides
    changed = {FILES[3]: {12}, FILES[0]: {30}}
    assert ratchet.touching([c_new, c_edge, c_old], changed) == [c_new, c_edge]


# --------------------------------------------------------------------------- end to end

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
      const out: string[] = [];
      for (const [k, v] of seen) out.push(`${k}:${v}:${Math.ceil(v / 11)}`);
      out.sort((a, b) => a.localeCompare(b));
      return out.join('|');
    }
    """)
SRC = "packages/loot-core/src/server"


def _docker_or_skip():
    if shutil.which("docker") is None:
        pytest.skip("docker missing")
    ok = subprocess.run(["docker", "image", "inspect", ratchet.JSCPD_IMAGE],
                        capture_output=True).returncode == 0
    if not ok:
        pytest.skip(f"{ratchet.JSCPD_IMAGE} missing")


def _git(tree, *args):
    subprocess.run(["git", *args], cwd=tree, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    _docker_or_skip()
    (tmp_path / SRC).mkdir(parents=True)
    (tmp_path / SRC / "report.ts").write_text(BLOCK)
    (tmp_path / SRC / "misc.ts").write_text(OTHER + "\n" + OTHER.replace("other(", "other2("))
    (tmp_path / SRC / "report.test.ts").write_text(BLOCK.replace("summarise", "t"))
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "start")
    start = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True,
                           text=True, check=True).stdout.strip()
    return tmp_path, start


@pytest.mark.integration
def test_pasted_block_is_one_new_clone(repo):
    tree, start = repo
    # the agent pastes the block (renamed) next to its original, in a new file
    (tree / SRC / "consumer.ts").write_text(
        "import { x } from './x';\n\n" + BLOCK.replace("summarise", "summariseForConsumer"))
    clones = ratchet.new_clones(tree, start, 50)
    assert len(clones) == 1
    c = clones[0]
    assert {c.a, c.b} == {f"{SRC}/report.ts", f"{SRC}/consumer.ts"}


@pytest.mark.integration
def test_calling_the_extracted_function_is_no_clone(repo):
    tree, start = repo
    (tree / SRC / "consumer.ts").write_text(
        "import { summarise } from './report';\n\n"
        "export function consumer(rows: Parameters<typeof summarise>[0]) {\n"
        "  return summarise(rows.filter(r => r.amount > 0));\n}\n")
    assert ratchet.new_clones(tree, start, 50) == []


@pytest.mark.integration
def test_unrelated_preexisting_clone_is_not_reported(repo):
    tree, start = repo
    # misc.ts already holds a clone pair (other/other2); the agent edits elsewhere
    with open(tree / SRC / "report.ts", "a") as f:
        f.write("\nexport const VERSION = 2;\n")
    assert ratchet.clones_by_threshold(tree, start, [50])[50]["all"] >= 1
    assert ratchet.new_clones(tree, start, 50) == []


@pytest.mark.integration
def test_test_files_are_not_scanned(repo):
    tree, start = repo
    (tree / SRC / "consumer.test.ts").write_text(BLOCK.replace("summarise", "copyInTest"))
    assert ratchet.new_clones(tree, start, 50) == []


@pytest.mark.integration
def test_modified_line_inside_a_preexisting_clone_counts(repo):
    tree, start = repo
    # editing one line inside an existing clone side touches it (per-change rule)
    p = tree / SRC / "misc.ts"
    lines = p.read_text().splitlines(keepends=True)
    lines[2] = lines[2].replace("for (const x of xs) {", "for (const x of xs) { // edit")
    p.write_text("".join(lines))
    clones = ratchet.new_clones(tree, start, 50)
    assert len(clones) == 1 and clones[0].a == clones[0].b == f"{SRC}/misc.ts"


@pytest.mark.integration
def test_same_basename_files_resolve(repo):
    """jscpd 5.4 names files given as a list by a lossy short name (``app.ts``); the
    staged-directory run must still say which ``app.ts`` holds the copy."""
    tree, start = repo
    for d in ("budget", "accounts", "rules"):
        (tree / SRC / d).mkdir()
        (tree / SRC / d / "app.ts").write_text(f"export const {d} = 1;\n")
    (tree / SRC / "accounts" / "app.ts").write_text(
        BLOCK.replace("summarise", "summariseAccounts"))
    clones = ratchet.clones_by_threshold(tree, start, [50])[50]
    assert clones["unresolved"] == 0
    assert [{c.a, c.b} for c in clones["new"]] == [
        {f"{SRC}/report.ts", f"{SRC}/accounts/app.ts"}]


# --------------------------------------------------------------------------- real steps
# Review Focus 1 on real diffs: per zone, one study-2 R step labelled `copy` and one F
# step labelled `helper`, rebuilt from runs2 (read-only) exactly as the calibration
# rebuilt them, checked at the calibrated min-tokens. Each pair is the zone's majority
# outcome in the calibration (first such step): Z1 tells copy from helper, Z2 and Z4 are
# lint blind (neither fires), Z3 fires on both (non-discriminating).

REAL = [
    ("Z1", "runs2/claude/R/Z1/0/T2", "copy", True),
    ("Z1", "runs2/claude/F/Z1/0/T2", "helper", False),
    ("Z2", "runs2/claude/R/Z2/0/T2", "copy", False),
    ("Z2", "runs2/claude/F/Z2/0/T2", "helper", False),
    ("Z3", "runs2/claude/R/Z3/0/T2", "copy", True),
    ("Z3", "runs2/claude/F/Z3/0/T2", "helper", True),
    ("Z4", "runs2/claude/R/Z4/1/T2", "copy", False),
    ("Z4", "runs2/claude/F/Z4/0/T2", "helper", False),
]


def _calibration():
    import importlib.util
    import json

    from aa import config
    spec = importlib.util.spec_from_file_location(
        "study3_calibrate_ratchet", config.ROOT / "scripts" / "study3_calibrate_ratchet.py")
    cal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cal)
    data = json.loads((config.ROOT / "out" / "study3" / "ratchet-calibration.json").read_text())
    return cal, {r["step"]: r for r in data["steps"]}, config


def test_real_fixture_steps_match_the_recorded_calibration():
    cal, recorded, config = _calibration()
    t = config.RATCHET_MIN_TOKENS
    for zone, step, label, fires in REAL:
        r = recorded[step]
        assert (r["zone"], r["label"], r[f"t{t}"]["fires"]) == (zone, label, fires), step


@pytest.mark.integration
@pytest.mark.parametrize("zone,step,label,fires", REAL, ids=[s for _, s, _, _ in REAL])
def test_real_step_detector_matches_calibration(zone, step, label, fires):
    _docker_or_skip()
    cal, recorded, config = _calibration()
    if not (config.ROOT / step).is_dir() or not (cal.VARIANTS / step.split("/")[2]).is_dir():
        pytest.skip("runs2 or work/variants missing")
    t = config.RATCHET_MIN_TOKENS
    got = cal.replay(config.ROOT / step, (t,))[f"t{t}"]
    want = recorded[step][f"t{t}"]
    assert got["fires"] is fires
    assert (got["new"], got["all"], got["unresolved"]) == (want["new"], want["all"],
                                                           want["unresolved"])
    assert got["clones"] == want["clones"]
