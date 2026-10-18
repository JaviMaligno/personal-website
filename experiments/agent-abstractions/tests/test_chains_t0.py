"""Study 3 T0 task support (plan Task 2): loader, leak check, probe exclusions, sanity
script and verdicts. Pure parts, no Docker."""
import json
from pathlib import Path

import pytest

from aa import chains
from aa.chains import (T0Error, check_statements_t0, list_t0_zones, load_probe_exclusions,
                       load_t0, t0_script, t0_seed_verdict, t0_statement_leaks, t0_test_results)
from aa.probe2 import apply_exclusions, diff_probe

LOOT = "packages/loot-core"
ROOT = f"/work/actual/{LOOT}"
HID = f"{LOOT}/src/server/x/z9-inconsistencies.test.ts"


def _zone(tmp: Path, zone: str = "Z9", *, tests=True, seeds=True) -> Path:
    d = tmp / zone / "T0"
    d.mkdir(parents=True)
    (d / "statement.md").write_text("# Title\n\nMove this logic into one shared definition.\n")
    (d / "sites.json").write_text(json.dumps({"zone": zone, "sites": [{"id": "a"}]}))
    if tests:
        (d / "hidden" / Path(HID).parent).mkdir(parents=True)
        (d / "hidden" / HID).write_text("it('keeps the quirk', () => {});\n")
        (d / "consumers.json").write_text(json.dumps({"Z9 keeps the quirk": "quirk"}))
    else:
        (d / "consumers.json").write_text("{}\n")
    if seeds:
        (d / "sanity").mkdir()
        (d / "sanity" / "z9-unify.patch").write_text("diff --git a/x b/x\n")
        (d / "sanity" / "seeds.json").write_text(json.dumps(
            {"z9-unify": {"kind": "inconsistency", "target": "quirk"}}))
    return d


def test_load_t0(tmp_path):
    _zone(tmp_path)
    t = load_t0("Z9", tmp_path)
    assert t.zone == "Z9" and t.hidden == (HID,)
    assert t.tests == {"Z9 keeps the quirk": "quirk"}
    assert t.inconsistencies == ("quirk",)
    assert t.seeds == {"z9-unify": {"kind": "inconsistency", "target": "quirk"}}
    assert "one shared definition" in t.statement()
    assert chains.T0_LIMITS == {"minutes": 40, "turns": 90}
    assert list_t0_zones(tmp_path) == ["Z9"]


def test_load_t0_zone_without_inconsistencies(tmp_path):
    _zone(tmp_path, tests=False, seeds=False)
    t = load_t0("Z9", tmp_path)
    assert t.hidden == () and t.tests == {} and t.seeds == {}


def test_load_t0_behaviour_seed_without_inconsistency_tests(tmp_path):
    # Z4 has no inconsistency tests: its sanity rests on a seeded behaviour-changing
    # consolidation that the probe (minus exclusions) must see.
    d = _zone(tmp_path, tests=False, seeds=False)
    (d / "sanity").mkdir()
    (d / "sanity" / "z9-wrong-field.patch").write_text("diff --git a/x b/x\n")
    (d / "sanity" / "seeds.json").write_text(json.dumps(
        {"z9-wrong-field": {"kind": "behaviour", "target": "z9-weekend-mode"}}))
    t = load_t0("Z9", tmp_path)
    assert t.seeds == {"z9-wrong-field": {"kind": "behaviour", "target": "z9-weekend-mode"}}


@pytest.mark.parametrize("breakage", ["no-statement", "test-without-file", "seed-unknown-target",
                                      "seed-missing-patch", "hidden-outside-loot",
                                      "inconsistency-without-seed"])
def test_load_t0_rejects(tmp_path, breakage):
    d = _zone(tmp_path)
    if breakage == "no-statement":
        (d / "statement.md").write_text("  \n")
    elif breakage == "test-without-file":
        (d / "hidden" / HID).unlink()
    elif breakage == "seed-unknown-target":
        (d / "sanity" / "seeds.json").write_text(json.dumps(
            {"z9-unify": {"kind": "inconsistency", "target": "nope"}}))
    elif breakage == "seed-missing-patch":
        (d / "sanity" / "z9-unify.patch").unlink()
    elif breakage == "hidden-outside-loot":
        (d / "hidden" / "other").mkdir()
        (d / "hidden" / "other" / "a.test.ts").write_text("")
    elif breakage == "inconsistency-without-seed":
        (d / "sanity" / "seeds.json").write_text(json.dumps(
            {"z9-unify": {"kind": "excluded", "target": "x"}}))
    with pytest.raises(T0Error):
        load_t0("Z9", tmp_path)


# --- leak check -----------------------------------------------------------------

@pytest.mark.parametrize("zone,text,bad", [
    ("Z1", "Move this logic into one shared definition.", False),
    ("Z1", "The logic lives in setZero and copyPreviousMonth.", True),          # names
    ("Z1", "Call `getBulkBudgetCategories` from the actions.", True),           # code span
    ("Z1", "It is repeated in five places.", True),                             # count
    ("Z1", "It is repeated in 5 actions.", True),
    ("Z1", "Both actions select categories themselves.", True),
    ("Z1", "The copies are all in the same file.", True),                       # location
    ("Z1", "See the budget module.", True),
    ("Z3", "Linking from GoCardless works differently.", True),                 # names a site
    ("Z3", "Each provider links on its own.", True),                            # study-2 hint
    ("Z1", "Copy last month and set to zero select differently.", True),        # enumeration
    ("Z2", "A schedule's amount can be a range (between two values).", False),
    ("Z4", "Move an occurrence that falls on a weekend to the nearest weekday.", False),
])
def test_t0_statement_leaks(zone, text, bad):
    assert bool(t0_statement_leaks(text, zone)) is bad


def test_committed_t0_statements_are_clean():
    assert list_t0_zones() == ["Z1", "Z2", "Z3", "Z4"]
    assert check_statements_t0() == {}


def test_committed_t0_tasks_load():
    for z in list_t0_zones():
        t = load_t0(z)
        # Z4 has no observable inconsistency listed in spec section 3
        assert bool(t.tests) is (z != "Z4")
        assert json.loads((t.dir / "sites.json").read_text())["sites"]


# --- probe exclusions -----------------------------------------------------------

def test_apply_exclusions_drops_cases_and_rows():
    doc = {"failed": [], "db": {
        "Z1/a": {"ok": [{"category": "x", "amount": 1}, {"category": "orphan", "amount": 2}]},
        "Z1/b": {"error": "boom"},
        "Z3/c": {"ok": 1}},
        "template": {"t": {"ok": 0}}}
    ex = [{"id": "rows", "cases": ["db:Z1/a", "db:Z1/b"], "rows_where": {"category": "orphan"}},
          {"id": "whole", "cases": ["db:Z3/c"]},
          {"id": "none", "cases": []}]
    out = apply_exclusions(doc, ex)
    assert out["db"]["Z1/a"] == {"ok": [{"category": "x", "amount": 1}]}
    assert out["db"]["Z1/b"] == {"error": "boom"}          # an error is kept as is
    assert "Z3/c" not in out["db"] and out["template"] == doc["template"]
    assert doc["db"]["Z1/a"]["ok"][1]["category"] == "orphan"   # input untouched


def test_diff_probe_with_exclusions():
    a = {"failed": [], "db": {"k": {"ok": [{"category": "o", "amount": 1}]}, "w": {"ok": 1}},
         "template": {}}
    b = {"failed": [], "db": {"k": {"ok": [{"category": "o", "amount": 2}]}, "w": {"ok": 2}},
         "template": {}}
    assert diff_probe(a, b) == ["db:k", "db:w"]
    ex = [{"id": "r", "cases": ["db:k"], "rows_where": {"category": "o"}}]
    assert diff_probe(a, b, ex) == ["db:w"]


def test_committed_probe_exclusions():
    ex = load_probe_exclusions()
    assert {e["id"] for e in ex} == {"z1-unawaited-6-12-month", "z1-missing-group-null",
                                     "z3-insert-key-set"}
    for e in ex:
        assert e["reason"] and isinstance(e["cases"], list)
        assert all(c.startswith(("db:", "template:")) for c in e["cases"])
    mg = next(e for e in ex if e["id"] == "z1-missing-group-null")
    assert mg["rows_where"] == {"category": "c-orphan"} and len(mg["cases"]) == 10


def test_load_probe_exclusions_rejects_bad_ids(tmp_path):
    (tmp_path / "probe-exclusions.json").write_text(json.dumps(
        {"exclusions": [{"id": "x", "reason": "r", "cases": ["Z1/a"]}]}))
    with pytest.raises(T0Error):
        load_probe_exclusions(tmp_path)


# --- sanity script and verdicts -------------------------------------------------

def test_t0_script_shape():
    s = t0_script([HID], patch=True)
    assert s.index("git apply") < s.index("z9-inconsistencies.test.ts")
    assert "/out/tests.json" in s and "/out/probe/report.json" in s
    assert "AA_PROBE_OUT=/out/probe" in s
    assert "src/server/aa-study2-probe-db.test.ts" in s
    u = t0_script([], patch=False)
    assert "git apply" not in u and "/out/tests.json" not in u and "/out/probe" in u


def _report(tests: dict[str, str], file: str) -> dict:
    return {"testResults": [{"name": f"{ROOT}/{file}", "status": "failed",
                             "assertionResults": [{"fullName": n, "status": s}
                                                  for n, s in tests.items()]}]}


def test_t0_test_results():
    rep = _report({"Z9 keeps the quirk": "failed", "other zone test": "passed"},
                  HID[len(LOOT) + 1:])
    assert t0_test_results(rep, {"Z9 keeps the quirk": "quirk"}) == {"Z9 keeps the quirk": "failed"}
    assert t0_test_results(None, {"Z9 keeps the quirk": "quirk"}) == {"Z9 keeps the quirk": "missing"}


def test_t0_seed_verdict():
    tests = {"t-a": "a", "t-b": "b"}
    v = t0_seed_verdict({"kind": "inconsistency", "target": "a"}, tests,
                        {"t-a": "failed", "t-b": "passed"}, raw=["db:x"], kept=["db:x"])
    assert v["ok"] and v["target_fails"] and v["probe_flags"] and v["other_tests_pass"]
    v = t0_seed_verdict({"kind": "inconsistency", "target": "a"}, tests,
                        {"t-a": "failed", "t-b": "passed"}, raw=["db:x"], kept=[])
    assert not v["ok"] and not v["probe_flags"]           # probe minus exclusions blind
    v = t0_seed_verdict({"kind": "inconsistency", "target": "a"}, tests,
                        {"t-a": "passed", "t-b": "passed"}, raw=["db:x"], kept=["db:x"])
    assert not v["ok"]                                      # test does not catch it
    v = t0_seed_verdict({"kind": "excluded", "target": "z"}, tests,
                        {"t-a": "passed", "t-b": "passed"}, raw=["db:x"], kept=[])
    assert v["ok"]                                          # excluded: invisible after exclusions
    v = t0_seed_verdict({"kind": "excluded", "target": "z"}, tests,
                        {"t-a": "failed", "t-b": "passed"}, raw=[], kept=[])
    assert not v["ok"]                                      # excluded but a test penalises it
    v = t0_seed_verdict({"kind": "inconsistency", "target": "a"}, tests,
                        {"t-a": "failed", "t-b": "failed"}, raw=["db:x"], kept=["db:x"])
    assert not v["other_tests_pass"] and not v["ok"]        # the seed also breaks another quirk
    v = t0_seed_verdict({"kind": "inconsistency", "target": "a"}, tests,
                        {"t-a": "failed", "t-b": "missing"}, raw=["db:x"], kept=["db:x"])
    assert not v["ok"]                                      # another test did not run
    v = t0_seed_verdict({"kind": "behaviour", "target": "w"}, {},
                        {}, raw=["template:x"], kept=["template:x"])
    assert v["ok"] and v["probe_flags"]                     # behaviour seed seen by the probe
    v = t0_seed_verdict({"kind": "behaviour", "target": "w"}, {}, {}, raw=["db:x"], kept=[])
    assert not v["ok"]                                      # only an excluded case moved
    v = t0_seed_verdict({"kind": "behaviour", "target": "w"}, tests,
                        {"t-a": "failed", "t-b": "passed"}, raw=["db:x"], kept=["db:x"])
    assert not v["ok"]                                      # it must not trip a T0 test either


def test_cli_wiring():
    from aa.cli import build_parser
    a = build_parser().parse_args(["chain", "t0-sanity", "Z1"])
    assert a.func.__name__ == "_cmd_chain_t0_sanity" and a.zones == ["Z1"]
    assert build_parser().parse_args(["chain", "check-statements"]).tasks3 == chains.TASKS3
    a = build_parser().parse_args(["chain", "t0-reference", "Z2", "--workers", "2"])
    assert a.func.__name__ == "_cmd_chain_t0_reference" and a.zones == ["Z2"] and a.workers == 2
    # the Docker VM (6 GB) holds one reference run (typecheck + lint + tests + probe)
    assert build_parser().parse_args(["chain", "t0-reference"]).workers == 1
    assert build_parser().parse_args(["chain", "t0-sanity"]).workers <= 2


def test_rg_rule_is_the_spec_wording():
    import re
    spec = (chains.config.ROOT / "docs/specs/2026-10-10-agent-as-designer-design.md").read_text()
    m = re.search(r'conventions\s+section, worded as a team rule and not as a hint about this '
                  r'code: "(.+?)"', spec, re.S)
    rule = " ".join(m.group(1).split())
    lines = [l for l in (chains.TASKS3 / "rg-rule.md").read_text().splitlines()
             if l.startswith("Do not copy logic")]
    assert lines == [rule]


def test_t0_sanity_with_fake_docker(tmp_path, monkeypatch):
    """Wiring of t0_sanity with a fake container: mounts are absolute, the seed patch is
    mounted, the R reference is diffed against each seed with the exclusions."""
    import shutil
    root = tmp_path / "tasks3"
    _zone(root)
    (root / "probe-exclusions.json").write_text(json.dumps({"exclusions": [
        {"id": "e", "reason": "r", "cases": ["db:orphan"], "rows_where": None}]}))
    seen = []

    def fake(argv, timeout):
        out = Path(next(a for a in argv if a.endswith(":/out"))[:-len(":/out")])
        seen.append(argv)
        assert out.is_absolute()
        seeded = any(a.endswith(":/seed:ro") for a in argv)
        (out / "probe").mkdir(exist_ok=True)
        (out / "tests.json").write_text(json.dumps(_report(
            {"Z9 keeps the quirk": "failed" if seeded else "passed"}, HID[len(LOOT) + 1:])))
        (out / "probe" / "report.json").write_text(json.dumps({"testResults": []}))
        (out / "probe" / "db.json").write_text(json.dumps(
            {"k": {"ok": 2 if seeded else 1}, "orphan": {"ok": 1}}))
        (out / "probe" / "template.json").write_text("{}")
        (out / "done").write_text("done")
        return 0

    monkeypatch.setattr(chains, "_image_id", lambda c: f"sha-{c}")
    monkeypatch.chdir(tmp_path)
    res = chains.t0_sanity(root=root, work=Path("rel-work"), runner=fake, workers=1)["Z9"]
    assert len(seen) == 3 and res["all_ok"], res
    assert res["seeds"]["z9-unify"]["probe_minus_exclusions"] == ["db:k"]
    assert json.loads((root / "Z9" / "T0" / "sanity.json").read_text())["all_ok"]
    shutil.rmtree(tmp_path / "rel-work")


# --- blind T0 reference implementations (plan Task 2: T0 is solvable) -------------

def test_t0_script_typecheck():
    s = t0_script([HID], patch=True, typecheck=True)
    assert s.index("git apply") < s.index("yarn tsgo -b") < s.index("z9-inconsistencies.test.ts")
    assert "/out/typecheck_rc" in s
    assert "tsgo" not in t0_script([HID], patch=True)
    assert "yarn typecheck" in s and "/out/typecheck_full_rc" in s
    s = t0_script([HID], patch=True, typecheck=True, lint=True, related=["src/server/x/impl.ts"])
    assert (s.index("git apply") < s.index("yarn lint > /out/lint_root.log")
            < s.index("vitest related") < s.index("z9-inconsistencies.test.ts"))
    assert "src/server/x/impl.ts" in s and "/out/related.json" in s
    assert "lint_root" not in t0_script([HID], patch=True)
    assert "related" not in t0_script([HID], patch=True)


def test_patch_sources():
    from aa.chains import _patch_sources
    text = (_ref_patch(["a"]) + _ref_patch(["b"], file=f"{LOOT}/src/server/x/impl.test.ts")
            + _ref_patch(["c"], file="packages/desktop-client/src/y.ts")
            + _ref_patch(["d"], file=f"{LOOT}/README.md"))
    assert _patch_sources(text) == ["src/server/x/impl.ts"]


def test_t0_related_compare():
    from aa.chains import t0_related_compare
    f = f"/work/actual/{LOOT}/src/server/x/impl.test.ts"
    g = f"/work/actual/{LOOT}/src/server/other.test.ts"

    def rep(**st):
        by: dict[str, list] = {}
        for k, v in st.items():
            fn, name = k.split("__")
            by.setdefault({"f": f, "g": g}[fn], []).append(
                {"fullName": name, "status": v})
        return {"testResults": [{"name": n, "assertionResults": a} for n, a in by.items()]}
    base = rep(f__a="passed", f__b="failed", g__c="passed")
    ok = t0_related_compare(base, rep(f__a="passed", f__b="failed"), 1)
    assert ok["ok"] and ok["base_failed"] == ["src/server/x/impl.test.ts::b"]
    assert ok["missing"] == [] and ok["new_failures"] == []     # g not related to the zone
    bad = t0_related_compare(base, rep(f__a="failed", f__b="failed"), 1)
    assert not bad["ok"] and bad["new_failures"] == ["src/server/x/impl.test.ts::a"]
    gone = t0_related_compare(base, rep(f__b="failed"), 1)
    assert not gone["ok"] and gone["missing"] == ["src/server/x/impl.test.ts::a"]
    assert not t0_related_compare(base, None, 1)["ok"]
    assert not t0_related_compare(None, rep(f__a="passed"), 0)["ok"]
    assert not t0_related_compare(base, {"testResults": []}, 0)["ok"]   # ran nothing
    # a failure (or a test gone) that passes when its file is run again alone: flaky,
    # not counted; one that fails again still counts
    flaky = t0_related_compare(base, rep(f__a="failed", f__b="failed"), 1,
                               retry=rep(f__a="passed", f__b="failed"))
    assert flaky["ok"] and flaky["flaky"] == ["src/server/x/impl.test.ts::a"]
    assert flaky["new_failures"] == []
    again = t0_related_compare(base, rep(f__a="failed", f__b="failed"), 1,
                               retry=rep(f__a="failed", f__b="failed"))
    assert not again["ok"] and again["new_failures"] == ["src/server/x/impl.test.ts::a"]
    assert again["flaky"] == []


def test_related_retry_line_runs_only_after_a_failure():
    import subprocess as sp

    from aa.chains import t0_related_retry_line
    line = t0_related_retry_line()
    assert line.startswith("if [ -s /out/related_rc ]") and "related_retry.json" in line
    assert sp.run(["bash", "-n", "-c", line]).returncode == 0


def test_t0_reference_verdict():
    from aa.chains import t0_reference_verdict
    tests = {"t-a": "a"}
    v = t0_reference_verdict(tests, {"t-a": "passed"}, typecheck_rc=0, raw=["db:o"], kept=[])
    assert v["ok"] and v["typecheck_ok"] and v["tests_pass"] and v["probe_same"]
    assert v["probe_raw"] == ["db:o"]
    assert not t0_reference_verdict(tests, {"t-a": "failed"}, 0, [], [])["ok"]
    assert not t0_reference_verdict(tests, {"t-a": "missing"}, 0, [], [])["ok"]
    assert not t0_reference_verdict(tests, {"t-a": "passed"}, 2, [], [])["ok"]
    assert not t0_reference_verdict(tests, {"t-a": "passed"}, None, [], [])["ok"]
    assert not t0_reference_verdict(tests, {"t-a": "passed"}, 0, ["db:k"], ["db:k"])["ok"]
    assert t0_reference_verdict({}, {}, 0, [], [])["ok"]        # zone without tests
    assert not t0_reference_verdict(tests, {"t-a": "passed"}, 0, [], [], typecheck_full_rc=1)["ok"]
    assert not t0_reference_verdict(tests, {"t-a": "passed"}, 0, [], [], lint_root_rc=1)["ok"]
    assert not t0_reference_verdict(tests, {"t-a": "passed"}, 0, [], [], lint_rc=None)["ok"]
    assert not t0_reference_verdict(tests, {"t-a": "passed"}, 0, [], [],
                                    related={"ok": False})["ok"]
    assert t0_reference_verdict(tests, {"t-a": "passed"}, 0, [], [], related={"ok": True})["ok"]


def _ref_patch(added: list[str], file: str = f"{LOOT}/src/server/x/impl.ts") -> str:
    return (f"diff --git a/{file} b/{file}\n--- a/{file}\n+++ b/{file}\n@@ -1 +1,{len(added)} @@\n"
            + "".join(f"+{l}\n" for l in added))


def test_t0_reference_leaks(tmp_path):
    from aa.chains import t0_reference_leaks
    root = tmp_path / "tasks3"
    d = _zone(root)
    (d / "hidden" / HID).write_text(
        "describe('Z9', () => {\n  it('keeps the quirk', async () => {\n"
        "    expect(await runTheHandlerWith({ budgetMonth: '2024-02' })).toEqual(42);\n"
        "    const msg = 'a distinctive hidden literal';\n  });\n});\n")
    variant = tmp_path / "variant"
    (variant / LOOT / "src/server/x").mkdir(parents=True)
    (variant / LOOT / "src/server/x/impl.ts").write_text("// a distinctive hidden literal\n")
    (d / "reference.R.patch").write_text(_ref_patch(["export const x = 1;"]))
    clean = t0_reference_leaks("Z9", root=root, variant=variant)
    assert clean["clean"] and clean["files"] == [f"{LOOT}/src/server/x/impl.ts"]
    (d / "reference.R.patch").write_text(_ref_patch([
        "// keeps the quirk",
        "const m = 'a distinctive hidden literal';",               # already in the variant
        "    expect(await runTheHandlerWith({ budgetMonth: '2024-02' })).toEqual(42);"]))
    bad = t0_reference_leaks("Z9", root=root, variant=variant)
    assert not bad["clean"]
    assert bad["test_names"] == ["keeps the quirk"]
    assert bad["literals"] == ["keeps the quirk"]     # the variant one is not reported
    assert bad["lines"] == ["expect(await runTheHandlerWith({ budgetMonth: '2024-02' })).toEqual(42);"]
    (d / "reference.R.patch").write_text(_ref_patch(["x"], file=HID))
    assert t0_reference_leaks("Z9", root=root, variant=variant)["hidden_or_test_files"] == [HID]
    (d / "reference.R.patch").unlink()
    assert t0_reference_leaks("Z9", root=root, variant=variant) == {"missing": True, "clean": False}


def test_t0_reference_check_with_fake_docker(tmp_path, monkeypatch):
    """Wiring: one untouched-R baseline plus one container per zone with its reference
    patch mounted as the seed and the typecheck on; verdict written next to the patch."""
    root = tmp_path / "tasks3"
    d = _zone(root)
    (d / "reference.R.patch").write_text(_ref_patch(["export const x = 1;"]))
    (root / "probe-exclusions.json").write_text(json.dumps({"exclusions": [
        {"id": "e", "reason": "r", "cases": ["db:orphan"], "rows_where": None}]}))
    seen = []

    def fake(argv, timeout):
        out = Path(next(a for a in argv if a.endswith(":/out"))[:-len(":/out")])
        seen.append(argv)
        patched = any(a.endswith(":/seed:ro") for a in argv)
        assert "yarn tsgo -b" in argv[-1] and "vitest related" in argv[-1]
        assert "src/server/x/impl.ts" in argv[-1]
        if patched:
            assert (out / "seed" / "seed.patch").read_text() == (d / "reference.R.patch").read_text()
        for n in ("typecheck_rc", "typecheck_full_rc", "lint_root_rc", "lint_rc"):
            (out / n).write_text("0\n")
        (out / "related.json").write_text(json.dumps({"testResults": [{
            "name": f"/work/actual/{LOOT}/src/server/x/impl.test.ts",
            "assertionResults": [{"fullName": "works", "status": "passed"}]}]}))
        (out / "probe").mkdir(exist_ok=True)
        (out / "tests.json").write_text(json.dumps(_report(
            {"Z9 keeps the quirk": "passed"}, HID[len(LOOT) + 1:])))
        (out / "probe" / "report.json").write_text(json.dumps({"testResults": []}))
        (out / "probe" / "db.json").write_text(json.dumps(
            {"k": {"ok": 1}, "orphan": {"ok": 2 if patched else 1}}))
        (out / "probe" / "template.json").write_text("{}")
        (out / "done").write_text("done")
        return 0

    monkeypatch.setattr(chains, "_image_id", lambda c: f"sha-{c}")
    variant = tmp_path / "variant"
    variant.mkdir()
    res = chains.t0_reference_check(root=root, work=tmp_path / "w", runner=fake, workers=1,
                                    variant=variant)["Z9"]
    assert len(seen) == 2 and res["ok"], res
    assert res["probe_raw"] == ["db:orphan"] and res["probe_minus_exclusions"] == []
    assert res["leaks"]["clean"] and res["image"] == "sha-R"
    assert res["lint_ok"] and res["typecheck_ok"] and res["related"]["passed"] == 1
    assert res["untouched_R"]["related"]["passed"] == 1
    assert json.loads((d / "reference_check.json").read_text())["ok"]
