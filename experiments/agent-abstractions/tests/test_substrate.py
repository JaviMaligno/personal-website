import subprocess
from pathlib import Path

import aa.substrate as substrate


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout


def _make_src(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    (src / "node_modules" / "dep").mkdir(parents=True)
    (src / "node_modules" / "dep" / "index.js").write_text("x\n")
    (src / "pkg").mkdir()
    (src / "pkg" / "a.txt").write_text("one\n")
    _git(src, "init", "-q", "-b", "main")
    _git(src, "add", "pkg")
    _git(src, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c1")
    (src / "pkg" / "b.txt").write_text("two\n")
    _git(src, "add", "pkg")
    _git(src, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c2")
    return src


def test_fresh_repo_single_commit_without_node_modules(tmp_path):
    src = _make_src(tmp_path)
    dst = substrate.fresh_repo(src, tmp_path / "dst")
    assert _git(dst, "rev-list", "--count", "HEAD").strip() == "1"
    assert not (dst / "node_modules").exists()
    assert (dst / "pkg" / "a.txt").read_text() == "one\n"
    assert (dst / "pkg" / "b.txt").exists()


def test_fresh_repo_replaces_existing_destination(tmp_path):
    src = _make_src(tmp_path)
    dst = tmp_path / "dst"
    dst.mkdir()
    (dst / "stale.txt").write_text("old\n")
    substrate.fresh_repo(src, dst)
    assert not (dst / "stale.txt").exists()


def test_apply_patches_applies_and_commits(tmp_path, monkeypatch):
    src = _make_src(tmp_path)
    patches = tmp_path / "patches"
    patches.mkdir()
    (patches / "p.patch").write_text(
        "diff --git a/pkg/a.txt b/pkg/a.txt\n"
        "--- a/pkg/a.txt\n"
        "+++ b/pkg/a.txt\n"
        "@@ -1 +1 @@\n"
        "-one\n"
        "+uno\n"
    )
    monkeypatch.setattr(substrate, "PATCHES", patches)
    dst = substrate.fresh_repo(src, tmp_path / "dst")
    substrate.apply_patches(dst, ("p.patch",))
    assert (dst / "pkg" / "a.txt").read_text() == "uno\n"
    assert _git(dst, "rev-list", "--count", "HEAD").strip() == "2"
    assert _git(dst, "status", "--porcelain").strip() == ""


def test_apply_patches_noop_without_patches(tmp_path):
    src = _make_src(tmp_path)
    dst = substrate.fresh_repo(src, tmp_path / "dst")
    substrate.apply_patches(dst, ())
    assert _git(dst, "rev-list", "--count", "HEAD").strip() == "1"


def test_fresh_repo_strips_agent_config_keeps_agents_md(tmp_path):
    src = _make_src(tmp_path)
    for d in substrate.AGENT_CONFIG_DIRS:
        (src / d / "skills").mkdir(parents=True)
        (src / d / "skills" / "SKILL.md").write_text("x\n")
    (src / "AGENTS.md").write_text("agents\n")
    (src / "CLAUDE.md").write_text("claude\n")
    dst = substrate.fresh_repo(src, tmp_path / "dst")
    for d in (".claude", ".codex", ".agents", ".cursor"):
        assert not (dst / d).exists()
    assert (dst / "AGENTS.md").read_text() == "agents\n"
    assert (dst / "CLAUDE.md").read_text() == "claude\n"
    tracked = _git(dst, "ls-files").split()
    assert "AGENTS.md" in tracked and not any(t.startswith((".claude", ".codex", ".agents", ".cursor"))
                                              for t in tracked)
