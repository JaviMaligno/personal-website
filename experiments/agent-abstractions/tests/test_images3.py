"""Study 3 arm images built together: manifest checks (pure parts; no Docker)."""
import json
import textwrap
from pathlib import Path

import pytest

from aa import config, images3


def test_parse_listing_and_diff():
    a = images3.parse_listing("aa  ./x/a.js\nbb  ./x/b js with space.js\n\ncc *bin.node\n")
    assert a == {"x/a.js": "aa", "x/b js with space.js": "bb", "bin.node": "cc"}
    b = {"x/a.js": "aa", "x/b js with space.js": "BB", "new.js": "dd"}
    assert images3.listing_diff(a, b) == ["bin.node", "new.js", "x/b js with space.js"]
    assert images3.listing_diff(a, dict(a)) == []


def test_parse_facts():
    f = images3.parse_facts("variant_tree=abc\nworktree_tree=def\nnoise\n")
    assert f == {"variant_tree": "abc", "worktree_tree": "def"}


def test_lever_files_from_the_real_patches():
    assert images3.lever_files("R") == set()
    assert images3.lever_files("RC") == set()
    assert images3.lever_files("RG") == {"AGENTS.md"}
    assert images3.lever_files("RL") == {
        "package.json", "packages/loot-core/package.json",
        "packages/loot-core/bin/dup-check.mjs", "packages/loot-core/bin/dup-check.config.json"}


def test_patch_paths_handles_new_and_deleted_files(tmp_path):
    p = tmp_path / "x.patch"
    p.write_text(textwrap.dedent("""\
        diff --git a/new.txt b/new.txt
        new file mode 100644
        --- /dev/null
        +++ b/new.txt
        @@ -0,0 +1 @@
        +x
        diff --git a/old.txt b/old.txt
        deleted file mode 100644
        """))
    assert images3.patch_paths(p) == {"new.txt", "old.txt"}


def test_global_versions():
    ls = {"dependencies": {"jscpd": {"version": "5.4.0"},
                           "@openai/codex": {"version": "0.159.3"}}}
    assert images3.global_versions(ls) == {"@anthropic-ai/claude-code": None,
                                           "@openai/codex": "0.159.3", "jscpd": "5.4.0"}


def _arms(**over):
    base = {"variant_tree": "T", "worktree_tree": "W", "yarn_lock_sha256": "L",
            "yarn_state_sha256": "S", "global_versions": {"jscpd": "5.4.0"}}
    info = {a: dict(base) for a in ("R", "RG", "RL", "RC")}
    for a, d in over.items():
        info[a].update(d)
    nm = {"node_modules/x/index.js": "1"}
    glob = {"lib/node_modules/jscpd/index.js": "2"}
    wt = {"AGENTS.md": "a", "package.json": "p", "src/x.ts": "s"}
    listings = {a: {"worktree": dict(wt), "node_modules": dict(nm), "global": dict(glob)}
                for a in info}
    listings["RG"]["worktree"]["AGENTS.md"] = "a2"
    listings["RL"]["worktree"]["package.json"] = "p2"
    listings["RL"]["worktree"]["bin/dup-check.mjs"] = "d"
    levers = {"R": set(), "RC": set(), "RG": {"AGENTS.md"},
              "RL": {"package.json", "bin/dup-check.mjs"}}
    return info, listings, levers


def test_check_arms_all_ok():
    info, listings, levers = _arms(RG={"variant_tree": "TG", "worktree_tree": "WG"},
                                   RL={"variant_tree": "TL", "worktree_tree": "WL"})
    c = images3.check_arms(info, listings, levers)
    assert c["ok"] is True
    assert c["worktree_diffs_vs_R"] == {"RG": ["AGENTS.md"],
                                        "RL": ["bin/dup-check.mjs", "package.json"], "RC": []}
    assert c["node_modules_diffs_vs_R"]["RL"] == {"count": 0, "sample": []}


@pytest.mark.parametrize("arm,field", [("RC", "variant_tree"), ("RC", "worktree_tree"),
                                       ("RG", "yarn_lock_sha256"), ("RL", "yarn_state_sha256")])
def test_check_arms_flags_fact_mismatch(arm, field):
    info, listings, levers = _arms(**{arm: {field: "other"}})
    c = images3.check_arms(info, listings, levers)
    assert c["ok"] is False


def test_check_arms_flags_node_modules_drift_and_non_lever_worktree_diff():
    info, listings, levers = _arms()
    listings["RL"]["node_modules"]["node_modules/eslint/x.js"] = "drift"
    c = images3.check_arms(info, listings, levers)
    assert c["node_modules_identical"] is False and c["ok"] is False
    assert c["node_modules_diffs_vs_R"]["RL"] == {"count": 1,
                                                  "sample": ["node_modules/eslint/x.js"]}
    info, listings, levers = _arms()
    listings["RC"]["worktree"]["yarn.lock"] = "other"
    c = images3.check_arms(info, listings, levers)
    assert c["worktree_diffs_are_lever_files"] is False and c["ok"] is False


def test_build_study3_requires_r(tmp_path):
    with pytest.raises(ValueError):
        images3.build_study3(["RG"], build=False, manifest=tmp_path / "m.json")


def test_inspect_script_is_read_only_on_the_tree():
    s = images3.INSPECT_SCRIPT
    assert "GIT_INDEX_FILE=$I git add -A" in s and "git add -A >" not in s.replace(
        "GIT_INDEX_FILE=$I git add -A >", "")
    assert "git commit" not in s and "rm -rf" not in s


def test_cli_image_build_study3_dispatch(monkeypatch, capsys):
    from aa import cli
    got = {}

    def fake(arms=images3.ARMS, *, build=True, **kw):
        got.update(arms=list(arms), build=build)
        return {"images": {a: {"image_id": f"sha256:{a}"} for a in arms},
                "checks": {"ok": True}}

    monkeypatch.setattr(images3, "build_study3", fake)
    assert cli.main(["image", "build-study3"]) == 0
    assert got == {"arms": list(config.CONDITIONS3), "build": True}
    assert cli.main(["image", "build-study3", "--inspect-only"]) == 0
    assert got["build"] is False
    out = capsys.readouterr().out
    assert "sha256:RC" in out and "ok" in out
    monkeypatch.setattr(images3, "build_study3", lambda *a, **k: {
        "images": {}, "checks": {"ok": False}})
    assert cli.main(["image", "build-study3"]) == 1
