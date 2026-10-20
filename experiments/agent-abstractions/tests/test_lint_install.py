"""The eslint devDependencies come from one shared install step (plan Task 4):
substrate/docker/install-lint-deps.sh, run by the Dockerfile in all four images and
by `aa variant install` for local trees, never from a variant patch."""
from __future__ import annotations

import re

from aa import runner, substrate
from aa.config import PATCHES

SCRIPT = runner.INSTALL_SCRIPT


def test_dockerfile_and_local_install_use_the_same_script() -> None:
    assert substrate.INSTALL_SCRIPT == SCRIPT
    docker = runner.DOCKERFILE.read_text()
    assert "install-lint-deps.sh" in docker
    assert "yarn add" not in docker  # only via the shared script


def test_script_pins_exact_versions_after_immutable_install() -> None:
    s = SCRIPT.read_text()
    assert s.index("yarn install --immutable") < s.index("yarn add -D")
    for pkg in ("eslint", "@typescript-eslint/parser", "typescript-eslint"):
        assert re.search(rf"\s{re.escape(pkg)}@\d+\.\d+\.\d+\b", s), pkg


def test_no_patch_carries_eslint_dependencies() -> None:
    for p in PATCHES.glob("*.patch"):
        text = p.read_text()
        assert "yarn.lock" not in text, p.name
        assert not re.search(r'^\+\s*"(eslint|typescript-eslint|@typescript-eslint/parser)"\s*:',
                             text, re.M), p.name
