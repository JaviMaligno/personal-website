from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from aa.config import ACTUAL_URL, BASE_COMMIT, CONDITION_PATCHES, PATCHES, WORK


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


def fetch_base() -> Path:
    """Full-history (blob-filtered) clone of Actual, detached at BASE_COMMIT."""
    base = WORK / "actual-base"
    if not base.exists():
        WORK.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", ACTUAL_URL, str(base)], check=True)
    _git(base, "checkout", "--detach", BASE_COMMIT)
    return base


# Repo-provided agent configuration (skills, settings, hooks) is removed from
# every variant so neither agent gets tool-specific help the other lacks.
# AGENTS.md and CLAUDE.md stay: identical across conditions and agents.
AGENT_CONFIG_DIRS = (".claude", ".codex", ".agents", ".cursor")


def fresh_repo(src: Path, dst: Path) -> Path:
    """Copy a tree without history and commit it once (the agent can't mine git log).

    Drops `.git`, `node_modules` and the agent config dirs (AGENT_CONFIG_DIRS).
    """
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True,
                    ignore=shutil.ignore_patterns(".git", "node_modules", *AGENT_CONFIG_DIRS))
    _git(dst, "init", "-q", "-b", "main")
    _git(dst, "add", "-A")
    _git(dst, "-c", "user.name=aa", "-c", "user.email=aa@local", "commit", "-qm", "base")
    return dst


def apply_patches(tree: Path, patches: tuple[str, ...]) -> None:
    for p in patches:
        _git(tree, "apply", "--index", "--whitespace=nowarn", str(PATCHES / p))
    if patches:
        _git(tree, "-c", "user.name=aa", "-c", "user.email=aa@local", "commit", "-qm", "variant")


def build_variant(cond: str) -> Path:
    base = fetch_base()
    dst = fresh_repo(base, WORK / "variants" / cond)
    apply_patches(dst, CONDITION_PATCHES[cond])
    return dst


INSTALL_SCRIPT = PATCHES.parent / "docker" / "install-lint-deps.sh"


def install_variant(cond: str) -> Path:
    """Install a built variant the way the Docker image does (install-lint-deps.sh).

    The eslint devDependencies land in the working tree only (package.json and
    yarn.lock modified, never committed), so the variant's commits stay exactly
    base + patches; the change is identical in all four conditions.
    """
    tree = WORK / "variants" / cond
    if not (tree / ".git").exists():
        raise FileNotFoundError(f"{tree} is not a built variant; run `aa variant build {cond}`")
    subprocess.run(["bash", str(INSTALL_SCRIPT)], cwd=tree, check=True)
    return tree
