"""Duplication ratchet detector (study 3, spec §5, plan Task 1).

A *new clone* is a jscpd clone over loot-core's non-test sources
(``packages/loot-core/src``, :func:`aa.chain_eval.is_source_file`) with at least one
side overlapping a line added or modified relative to the step's start commit
(``git diff -U0 <start>``; files untracked in the tree count as wholly added). The rule
is generic (no zone list) and per change: duplication elsewhere neither counts against
the change nor earns it slack.

jscpd is the pinned 5.4.0 inside ``aa-actual:R`` (the same binary study 2's evaluator
used), run with ``docker run --network none``. Given a list of files, jscpd 5.4 shortens
the reported names lossily (a bare ``app.ts`` for any of loot-core's many ``app.ts``;
cf. :func:`aa.chain_eval._resolve_jscpd`), so the scanned files are copied, at their
repo paths, into a staging directory that holds nothing else and jscpd is given that
directory: names come back relative to it and are resolved by unique path-segment
suffix (anything unresolved is dropped and counted).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from aa.chain_eval import is_source_file

SCOPE = "packages/loot-core/src"
JSCPD_IMAGE = "aa-actual:R"
JSCPD_VERSION = "5.4.0"
JSCPD_TIMEOUT_S = 600
CONTAINER_TREE = "/src"
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class Clone:
    a: str
    a_start: int
    a_end: int
    b: str
    b_start: int
    b_end: int
    lines: int
    tokens: int


# --------------------------------------------------------------------------- the change

def parse_changed_lines(diff: str) -> dict[str, set[int]]:
    """Post-image line numbers added or modified by a ``git diff -U0`` (deleted files
    and pure deletions contribute nothing)."""
    out: dict[str, set[int]] = {}
    cur: str | None = None
    for ln in diff.splitlines():
        if ln.startswith("+++ "):
            path = ln[4:].strip()
            cur = None if path == "/dev/null" else path[2:] if path.startswith("b/") else path
            continue
        m = HUNK.match(ln)
        if m and cur is not None:
            start, count = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
            if count:
                out.setdefault(cur, set()).update(range(start, start + count))
    return out


def _git(tree: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=tree, check=True, capture_output=True,
                          text=True).stdout


def _untracked(tree: Path) -> list[str]:
    return [p for p in _git(tree, "ls-files", "-o", "--exclude-standard", "--", SCOPE)
            .splitlines() if p]


def changed_lines(tree: Path, start_commit: str) -> dict[str, set[int]]:
    """Lines of the working tree added or modified since ``start_commit`` under
    :data:`SCOPE` (tracked changes via ``git diff -U0 --no-renames``, untracked files
    whole). The index is not touched."""
    out = parse_changed_lines(_git(tree, "diff", "-U0", "--no-renames", "--no-color",
                                   "--no-ext-diff", start_commit, "--", SCOPE))
    for p in _untracked(tree):
        f = tree / p
        if f.is_file():
            n = len(f.read_bytes().splitlines())
            if n:
                out[p] = set(range(1, n + 1))
    return out


def scanned_files(tree: Path) -> list[str]:
    """Non-test source files under :data:`SCOPE` present in the working tree (tracked
    or untracked), sorted."""
    tracked = _git(tree, "ls-files", "--", SCOPE).splitlines()
    files = {p for p in [*tracked, *_untracked(tree)] if p and is_source_file(p)}
    return sorted(p for p in files if (tree / p).is_file())


# --------------------------------------------------------------------------- jscpd

def resolve_name(name: str, files: Iterable[str]) -> str | None:
    """Map a jscpd name back to the one scanned path it denotes: exact, or a unique
    suffix starting at a path segment (names are relative to the common root of the
    inputs, absolute under :data:`CONTAINER_TREE` in some versions)."""
    files = list(files)
    for pre in (CONTAINER_TREE + "/", "./"):
        if name.startswith(pre):
            name = name[len(pre):]
    if name in files:
        return name
    hits = [f for f in files if f.endswith("/" + name)]
    return hits[0] if len(hits) == 1 else None


def parse_clones(report: dict | None, files: list[str]) -> tuple[list[Clone], int]:
    """(clones with both sides resolved, number of clones dropped as unresolved)."""
    clones: list[Clone] = []
    unresolved = 0
    for d in (report or {}).get("duplicates") or []:
        a, b = d.get("firstFile") or {}, d.get("secondFile") or {}
        na, nb = resolve_name(a.get("name", ""), files), resolve_name(b.get("name", ""), files)
        ends = (a.get("start"), a.get("end"), b.get("start"), b.get("end"))
        if na is None or nb is None or not all(isinstance(x, int) for x in ends):
            unresolved += 1
            continue
        clones.append(Clone(na, a["start"], a["end"], nb, b["start"], b["end"],
                            int(d.get("lines") or 0), int(d.get("tokens") or 0)))
    return clones, unresolved


def touching(clones: Iterable[Clone], changed: dict[str, set[int]]) -> list[Clone]:
    """Clones with a side overlapping a changed line (inclusive line ranges)."""
    def hit(f: str, s: int, e: int) -> bool:
        lines = changed.get(f)
        return bool(lines) and any(s <= ln <= e for ln in lines)
    return [c for c in clones if hit(c.a, c.a_start, c.a_end) or hit(c.b, c.b_start, c.b_end)]


def jscpd_script(thresholds: Iterable[int]) -> str:
    """Bash run in the container: the staged sources are under /src/<repo path>; one
    JSON report per threshold in /out/t<N>/."""
    runs = "; ".join(
        f"jscpd --min-tokens {int(t)} --reporters json --silent --output /out/t{int(t)} "
        f"{SCOPE} > /out/t{int(t)}.log 2>&1; echo $? > /out/t{int(t)}.rc"
        for t in thresholds)
    return f"set -u; cd {CONTAINER_TREE}; jscpd --version > /out/version; {runs}"


def jscpd_reports(tree: Path, files: list[str], thresholds: Iterable[int], *,
                  image: str = JSCPD_IMAGE) -> dict[int, dict[str, Any]]:
    """One container, every threshold: {min_tokens: jscpd JSON report} over exactly
    ``files`` (repo-relative, under :data:`SCOPE`)."""
    thresholds = list(dict.fromkeys(int(t) for t in thresholds))
    with tempfile.TemporaryDirectory(prefix="aa-ratchet-") as tmp:
        o, stage = Path(tmp) / "out", Path(tmp) / "src"
        o.mkdir()
        for f in files:
            if not f.startswith(SCOPE + "/"):
                raise ValueError(f"{f} is outside {SCOPE}")
            dst = stage / f
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(tree) / f, dst)
        (stage / SCOPE).mkdir(parents=True, exist_ok=True)
        argv = ["docker", "run", "--rm", "--network", "none",
                "-v", f"{stage}:{CONTAINER_TREE}:ro", "-v", f"{o}:/out",
                "--entrypoint", "bash", image, "-c", jscpd_script(thresholds)]
        subprocess.run(argv, check=True, capture_output=True, timeout=JSCPD_TIMEOUT_S)
        version = (o / "version").read_text().strip()
        if version != f"jscpd {JSCPD_VERSION}" and version != JSCPD_VERSION:
            raise RuntimeError(f"jscpd version {version!r}, want {JSCPD_VERSION}")
        reports: dict[int, dict[str, Any]] = {}
        for t in thresholds:
            rc = (o / f"t{t}.rc").read_text().strip()
            if rc != "0":
                log = (o / f"t{t}.log").read_text()[-2000:]
                raise RuntimeError(f"jscpd min-tokens {t} rc={rc}: {log}")
            p = o / f"t{t}" / "jscpd-report.json"
            reports[t] = json.loads(p.read_text()) if p.exists() else {"duplicates": []}
        return reports


def clones_by_threshold(tree: Path, start_commit: str, thresholds: Iterable[int], *,
                        image: str = JSCPD_IMAGE) -> dict[int, dict[str, Any]]:
    """Per threshold: ``new`` (clones touching the change), ``all`` (clones resolved),
    ``unresolved`` (dropped), plus the scanned file count and the changed lines."""
    tree = Path(tree)
    files = scanned_files(tree)
    changed = changed_lines(tree, start_commit)
    out: dict[int, dict[str, Any]] = {}
    for t, rep in jscpd_reports(tree, files, thresholds, image=image).items():
        clones, unresolved = parse_clones(rep, files)
        out[t] = {"new": touching(clones, changed), "all": len(clones),
                  "unresolved": unresolved, "files": len(files),
                  "changed_lines": sum(len(v) for v in changed.values())}
    return out


def new_clones(tree: Path, start_commit: str, min_tokens: int, *,
               image: str = JSCPD_IMAGE) -> list[Clone]:
    """Clones (jscpd at ``min_tokens``) with a side on lines added or modified since
    ``start_commit``."""
    return clones_by_threshold(tree, start_commit, [min_tokens], image=image)[min_tokens]["new"]
