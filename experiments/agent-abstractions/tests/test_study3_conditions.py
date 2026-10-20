"""Study 3, plan Task 3: arms R/RG/RL/RC in config, patches, CLI and image builds."""
import re

import pytest

from aa import config
from aa.cli import build_parser

SPEC = config.ROOT / "docs" / "specs" / "2026-10-10-agent-as-designer-design.md"
R_PATCHES = ("lint-script.patch", "study2/r.patch")


def test_arms():
    assert config.CONDITIONS3 == ("R", "RG", "RL", "RC")
    # R is study 2's R (same patches, same image); the new arms extend ALL_CONDITIONS.
    assert config.ALL_CONDITIONS == config.CONDITIONS + config.CONDITIONS2 + ("RG", "RL", "RC")


def test_arm_patches_are_r_plus_one_lever():
    assert config.CONDITION_PATCHES["R"] == R_PATCHES
    assert config.CONDITION_PATCHES["RG"] == (*R_PATCHES, "study3/rg.patch")
    assert config.CONDITION_PATCHES["RL"] == (*R_PATCHES, "study3/rl.patch")
    assert config.CONDITION_PATCHES["RC"] == R_PATCHES  # T0 is a step, not an image change
    for cond in config.CONDITIONS3:
        for p in config.CONDITION_PATCHES[cond]:
            assert (config.PATCHES / p).is_file(), p


def _spec_rule() -> str:
    sec = SPEC.read_text().split("## 4. RG", 1)[1].split("\n## ", 1)[0]
    return re.search(r'"(Do not copy logic:.*?)"', " ".join(sec.split()), re.S).group(1)


def test_rg_patch_adds_exactly_the_spec_rule_to_agents_md():
    patch = (config.PATCHES / "study3" / "rg.patch").read_text()
    assert re.findall(r"^\+\+\+ b/(\S+)$", patch, re.M) == ["AGENTS.md"]
    added = [ln[1:] for ln in patch.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    removed = [ln for ln in patch.splitlines() if ln.startswith("-") and not ln.startswith("---")]
    assert added == [f"- {_spec_rule()}"] and removed == []
    # in the conventions section (Code Style & Conventions > Code Structure)
    assert "Prefer iteration and modularization over code duplication" in patch


def test_rg_rule_matches_tasks3_when_frozen():
    frozen = config.ROOT / "tasks3" / "rg-rule.md"
    if not frozen.exists():
        pytest.skip("tasks3/rg-rule.md not written yet (plan Task 2)")
    assert _spec_rule() in " ".join(frozen.read_text().split())


@pytest.mark.parametrize("argv,func", [
    (["variant", "build", "RG"], "_cmd_variant_build"),
    (["variant", "build", "RL"], "_cmd_variant_build"),
    (["variant", "build", "RC"], "_cmd_variant_build"),
    (["image", "build", "RG"], "_cmd_image_build"),
    (["image", "build", "RL"], "_cmd_image_build"),
    (["image", "build", "RC"], "_cmd_image_build"),
])
def test_parser_accepts_study3_arms(argv, func):
    assert build_parser().parse_args(argv).func.__name__ == func


def test_study3_images_have_jscpd_like_r():
    # Every arm runs on the same stage as R (the `study2` stage, with pinned jscpd):
    # RL's lint needs jscpd, and the arms must differ only by their patch.
    from aa.runner import image_target
    assert [image_target(c) for c in config.CONDITIONS3] == ["study2"] * 4


def test_rl_ratchet_is_in_the_lint_the_prompt_names():
    # The prompt (same in every arm) says `yarn lint` in packages/loot-core must pass; in
    # R that is `tsgo -b` (lint-script.patch). RL must put the ratchet in that command,
    # not only in the root lint the agent is never told to run.
    prompt = (config.ROOT / "src" / "aa" / "prompt.md").read_text()
    assert "`yarn lint` in packages/loot-core must pass" in " ".join(prompt.split())
    rl = (config.PATCHES / "study3" / "rl.patch").read_text()
    loot = rl.split("+++ b/packages/loot-core/package.json\n", 1)[1].split("\ndiff --git ", 1)[0]
    added = [ln for ln in loot.splitlines() if ln.startswith('+    "lint":')]
    assert len(added) == 1 and "tsgo -b" in added[0] and "dup-check.mjs" in added[0]
    for p in config.CONDITION_PATCHES["R"]:  # R's own loot-core lint has no ratchet
        assert "dup-check" not in (config.PATCHES / p).read_text()
