"""Task miner (Task 6): candidate commits from Actual history, filters, materialisation.

Pipeline: ``list_candidates`` (git log on the base clone) -> ``filter_reason`` ->
``materialise`` (revert the commit on every variant tree, write ``tasks/<id>/``).

``sanity_check`` (plan Task 6 Step 4) runs the hidden tests in the condition images:
the untouched variant (= reference solution) must pass them on every condition,
with the hidden tests rewritten for A+ on AP/APL (``aa.hidden_tests``), and the
start tree must fail them. ``check_and_record`` writes the verdict to the ledger.

``mine`` and ``materialise`` refuse to run until the harness repo carries the
``aplus-frozen`` tag (spec 3, integrity rule 1: A+ is frozen before any task is
mined). ``preview`` only lists and filters candidates on the base clone; it never
looks at A+ and writes nothing under ``tasks/``, so it may run before the freeze.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from aa.config import CONDITIONS, LOOT, ROOT, TASKS, WORK
from aa.hidden_tests import REWRITTEN_CONDS

FROZEN_TAG = "aplus-frozen"
SINCE = "2024-10-01"

# --- protected calls (Javier's decision 2, 2026-10-05) ----------------------------
# A candidate counts when the commit modifies (or adds) a FUNCTION whose body, in
# the pre- or post-image, contains a protected call. Function-level: not line-level
# (a one-line tweak next to a db write counts), not file-level (a change elsewhere
# in a file with writes does not).
GENERIC_WRITE_FNS = ("update", "insert", "insertWithUUID", "delete_", "deleteAll",
                     "insertWithSchema", "updateWithSchema")
# Data-specific write functions of db/index.ts (A+ design, section 3).
DATA_WRITE_FNS = (
    "insertCategoryGroup", "updateCategoryGroup", "moveCategoryGroup", "deleteCategoryGroup",
    "insertCategory", "updateCategory", "moveCategory", "deleteCategory",
    "insertPayee", "deletePayee", "deleteTransferPayee", "updatePayee", "mergePayees",
    "insertAccount", "updateAccount", "deleteAccount", "moveAccount",
    "insertAccountGroup", "updateAccountGroup", "moveAccountGroup", "deleteAccountGroup",
    "insertTransaction", "updateTransaction", "deleteTransaction", "moveTransaction",
    "moveSchedule", "insertTag", "deleteTag", "updateTag",
)
# Synced tables (same set as substrate/checker/probe.setup.ts).
SYNCED_TABLES = ("transactions", "accounts", "categories", "category_groups", "payees",
                 "payee_mapping", "schedules", "rules", "notes", "tags", "zero_budgets",
                 "reflect_budgets", "custom_reports", "dashboard", "preferences",
                 "transaction_filters", "category_mapping")

_alt = lambda xs: "|".join(sorted(xs, key=len, reverse=True))  # noqa: E731
# db.<write API>( anywhere; data-specific names also bare (named imports), but not
# their own declaration ("function insertPayee(").
WRITE_RE = re.compile(rf"\bdb\.({_alt(GENERIC_WRITE_FNS + DATA_WRITE_FNS)})\s*\("
                      rf"|(?<![\w.$])(?<!function )({_alt(DATA_WRITE_FNS)})\s*\(")
# Inside src/server/db/ the generic API is called bare (update('categories', ...)).
DB_INTERNAL_WRITE_RE = re.compile(rf"(?<![\w.$])(?<!function )({_alt(GENERIC_WRITE_FNS)})\s*\(")
# Raw SQL write on a synced table (keywords upper-case, as in every base site, so
# prose such as "update payees" in a comment does not match), plus a SQL entry point.
RAW_SQL_WRITE_RE = re.compile(
    rf"\b(?:INSERT(?:\s+OR\s+\w+)?\s+INTO|UPDATE|DELETE\s+FROM|REPLACE\s+INTO)\s+[\"`']?"
    rf"(?:{_alt(SYNCED_TABLES)})\b")
SQL_CALL_RE = re.compile(r"\b(runQuery|run|execQuery|cache)\s*\(")
MONEY_RE = re.compile(r"\b(amountToInteger|integerToAmount)\s*\(")
UNDO_RE = re.compile(r"\b(mutator|undoable)\s*\(")

FUNCTIONS_MJS = ROOT / "substrate" / "tools" / "functions.mjs"
NODE_VERSION = "24.18.1"
_UNITS_CHUNK = 400  # sources per node invocation


def has_protected_call(body: str, path: str = "") -> bool:
    """True if ``body`` (a function or top-level statement) contains a protected call."""
    if WRITE_RE.search(body) or MONEY_RE.search(body) or UNDO_RE.search(body):
        return True
    if "/server/db/" in path and DB_INTERNAL_WRITE_RE.search(body):
        return True
    return bool(RAW_SQL_WRITE_RE.search(body) and SQL_CALL_RE.search(body))


TEST_FILE_RE = re.compile(r"\.(test|spec)\.[cm]?[jt]sx?$|(^|/)__tests__/")
# Files whose change would make the per-variant image (node_modules, schema) stale.
DEPS_RE = re.compile(r"(^|/)(package\.json|yarn\.lock|\.yarnrc\.yml|\.nvmrc)$|(^|/)\.yarn/|(^|/)migrations/")

# Files a task never reverts: changelog fragments (not code; Actual deletes them at
# every release, so the one a task commit added is usually absent at base and its
# revert would abort) and Playwright screenshot baselines (binary e2e assets the
# harness never runs; a later re-render makes their 3-way revert conflict).
NON_CODE_RE = re.compile(r"^upcoming-release-notes/|-snapshots/[^/]+\.(?:png|jpe?g)$")

_DIFF_GIT_RE = re.compile(r"^diff --git a/(.*) b/(.*)$")
_REC, _HDR_END, _FLD = "\x1e", "\x1d", "\x1f"


@dataclass
class Candidate:
    sha: str
    date: str  # YYYY-MM-DD (author date)
    subject: str
    files: list[str]  # every file the commit touches (not only loot-core/src)
    test_files: list[str]  # loot-core test files touched by the commit
    ai_label: bool  # "[AI]" in subject/body: recorded attribute, not a filter
    protected_hits: int = 0  # changed functions with a protected call (see units_hit)


@dataclass(frozen=True)
class DropReason:
    reason: str


TaskDir = Path


@dataclass
class Task:
    id: str
    sha: str
    date: str
    subject: str
    hidden_tests: list[str]
    touched_files: list[str]
    statement_path: str
    per_condition: dict[str, dict[str, str]]
    selected: bool = False
    dir: Path = field(default_factory=Path)


# --- pure helpers ---------------------------------------------------------------

def is_test_file(path: str) -> bool:
    return bool(TEST_FILE_RE.search(path))


def is_non_code(path: str) -> bool:
    return bool(NON_CODE_RE.search(path))


def code_files(files: list[str]) -> list[str]:
    """Non-test files of a commit that the task reverts (``is_non_code`` excluded)."""
    return [f for f in files if not is_test_file(f) and not is_non_code(f)]


def touches_deps(path: str) -> bool:
    return bool(DEPS_RE.search(path))


def filter_reason(c: Candidate) -> str | None:
    """First filter that drops ``c`` (spec 4, applied in this order), or None.

    ``ai_label`` is not a filter (Javier's decision, 2026-10-06): "[AI]"-labelled
    commits are mined like any other; the label is a recorded task attribute and
    results are reported split by it.
    """
    if any(touches_deps(f) for f in c.files):
        return "touches_deps"
    if not c.test_files:
        return "no_tests"
    if c.protected_hits <= 0:
        return "no_protected_sites"
    return None


@dataclass
class FileChange:
    """Changed line numbers of one file in a ``-U0`` patch (1-based)."""
    old: str | None  # pre-image path (None for an added file)
    new: str | None  # post-image path (None for a deleted file)
    removed: list[int] = field(default_factory=list)  # pre-image lines
    added: list[int] = field(default_factory=list)  # post-image lines

    @property
    def path(self) -> str:
        return self.new or self.old or ""


_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def parse_patch(patch: str) -> tuple[list[str], list[FileChange]]:
    """(files in order of appearance, per-file changed lines).

    Line numbers come from the ``@@`` headers, so the patch must be ``-U0`` (every
    hunk line is a change). Hunk bodies are skipped, so a removed line that starts
    with ``--`` (e.g. a SQL comment) is never mistaken for a ``---`` file header.
    """
    files: list[str] = []
    changes: list[FileChange] = []
    cur: FileChange | None = None
    in_hunk = False
    for line in patch.splitlines():
        m = _DIFF_GIT_RE.match(line)
        if m:
            a, b = m.group(1), m.group(2)
            for p in (a, b):
                if p not in files:
                    files.append(p)
            cur = FileChange(old=a, new=b)
            changes.append(cur)
            in_hunk = False
            continue
        if cur is None:
            continue
        if not in_hunk:
            if line.startswith("new file mode") or line == "--- /dev/null":
                cur.old = None
            elif line.startswith("deleted file mode") or line == "+++ /dev/null":
                cur.new = None
        h = _HUNK_RE.match(line)
        if h:
            in_hunk = True
            o_start, o_len = int(h.group(1)), int(h.group(2) or 1)
            n_start, n_len = int(h.group(3)), int(h.group(4) or 1)
            cur.removed.extend(range(o_start, o_start + o_len))
            cur.added.extend(range(n_start, n_start + n_len))
    return files, changes


# --- function units ---------------------------------------------------------------

@dataclass(frozen=True)
class Unit:
    kind: str  # "fn" (named function) | "stmt" (top-level statement)
    name: str
    start: int  # 1-based, inclusive
    end: int


def is_unit_source(path: str | None) -> bool:
    """Non-test TypeScript production source of loot-core (mocks are test support)."""
    return bool(path and path.startswith(f"{LOOT}/src/") and re.search(r"\.tsx?$", path)
                and not path.endswith(".d.ts") and not is_test_file(path)
                and not path.startswith(f"{LOOT}/src/mocks/"))


def _node() -> str | None:
    nvm = Path.home() / ".nvm" / "versions" / "node" / f"v{NODE_VERSION}" / "bin" / "node"
    if nvm.exists():
        return str(nvm)
    from shutil import which
    return which("node")


def _ts_dir() -> Path | None:
    for d in (os.environ.get("AA_TS_DIR"), WORK / "actual-base"):
        if d and (Path(d) / "node_modules" / "typescript" / "package.json").exists():
            return Path(d)
    return None


def _units_ts(sources: dict[str, str], node: str, ts_dir: Path) -> dict[str, list[Unit]]:
    out: dict[str, list[Unit]] = {}
    keys = sorted(sources)
    for i in range(0, len(keys), _UNITS_CHUNK):
        chunk = [{"key": k, "text": sources[k], "tsx": k.endswith("x")}
                 for k in keys[i:i + _UNITS_CHUNK]]
        r = subprocess.run([node, str(FUNCTIONS_MJS), str(ts_dir)], input=json.dumps(chunk),
                           capture_output=True, text=True, check=True, errors="surrogateescape")
        for k, us in json.loads(r.stdout).items():
            out[k] = [Unit(u["kind"], u["name"], u["start"], u["end"]) for u in us]
    return out


_FN_START_RES = (
    re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*([\w$]+)\s*[<(]"),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([\w$]+)\s*(?::[^=]+)?=\s*(?:async\s+)?"
               r"(?:function\b|(?:<[^>]*>)?\([^)]*\)?|[\w$]+\s*=>)"),
    re.compile(r"^\s*(?:(?:public|private|protected|static|async|readonly|get|set)\s+)*"
               r"(?!(?:if|for|while|switch|catch|return|function)\b)([\w$]+)\s*(?:<[^>]*>)?\([^;]*\)"
               r"\s*(?::\s*[^={;]+)?\{\s*$"),
)


def _block_end(lines: list[str], start: int) -> int:
    """Index of the line closing the first ``{`` at or after ``start`` (rough scanner:
    skips strings and comments; template ``${}`` braces are counted, which balances)."""
    depth, opened, in_block_comment = 0, False, False
    for i in range(start, len(lines)):
        s, j, q = lines[i], 0, None
        while j < len(s):
            ch = s[j]
            if in_block_comment:
                if s.startswith("*/", j):
                    in_block_comment, j = False, j + 1
            elif q:
                if ch == "\\":
                    j += 1
                elif ch == q:
                    q = None
            elif s.startswith("//", j):
                break
            elif s.startswith("/*", j):
                in_block_comment, j = True, j + 1
            elif ch in "'\"`":
                q = ch
            elif ch == "{":
                depth, opened = depth + 1, True
            elif ch == "}":
                depth -= 1
                if opened and depth == 0:
                    return i
            j += 1
        if not opened and i > start + 3:  # signature spans too many lines: give up
            return start
    return len(lines) - 1


def _units_regex(text: str) -> list[Unit]:
    """Fallback when node/typescript are unavailable: brace-matched named functions;
    every line outside them is its own one-line statement unit (line-level there)."""
    lines = text.split("\n")
    units = []
    for i, ln in enumerate(lines):
        for r in _FN_START_RES:
            m = r.match(ln)
            if m:
                units.append(Unit("fn", m.group(1), i + 1, _block_end(lines, i) + 1))
                break
    covered = {n for u in units for n in range(u.start, u.end + 1)}
    for i, ln in enumerate(lines):
        if i + 1 not in covered:
            units.append(Unit("stmt", ln.strip()[:120], i + 1, i + 1))
    return units


def function_units(sources: dict[str, str]) -> dict[str, list[Unit]]:
    """Units of every source (key -> text), via the TypeScript compiler when available."""
    node, ts_dir = _node(), _ts_dir()
    if sources and node and ts_dir:
        return _units_ts(sources, node, ts_dir)
    return {k: _units_regex(t) for k, t in sources.items()}


def _innermost(units: list[Unit], line: int) -> Unit | None:
    best = None
    for u in units:
        if u.start <= line <= u.end and (
                best is None or (u.end - u.start, u.kind != "fn") < (best.end - best.start, best.kind != "fn")):
            best = u
    return best


def _body(lines: list[str], u: Unit) -> str:
    return "\n".join(lines[u.start - 1:u.end])


def units_hit(fc: FileChange, pre: str | None, post: str | None,
              pre_units: list[Unit], post_units: list[Unit]) -> set[str]:
    """Names of the changed units of ``fc`` whose body has a protected call.

    A changed line maps to its innermost unit (removed lines in the pre-image,
    added lines in the post-image). A touched unit is a hit if its own body or the
    body of its same-named counterpart in the other image has a protected call
    (so deleting the write from a function, or adding one, both count).
    """
    def prot(text: str | None, units: list[Unit], path: str | None) -> dict[tuple[str, str], bool]:
        res: dict[tuple[str, str], bool] = {}
        lines = (text or "").split("\n")
        fns = [u for u in units if u.kind == "fn"]
        for u in units:
            k = (u.kind, u.name)
            body_lines = lines
            if u.kind == "stmt":
                # A statement's own code only: lines of named functions nested in it
                # (class methods, bound arrows) are their own units, so a class
                # property tweak does not inherit a method's db write.
                inner = {n for f in fns if u.start <= f.start and f.end <= u.end
                         and (f.start, f.end) != (u.start, u.end)
                         for n in range(f.start, f.end + 1)}
                if inner:
                    body_lines = [("" if i + 1 in inner else ln) for i, ln in enumerate(lines)]
            res[k] = res.get(k, False) or has_protected_call(_body(body_lines, u), path or "")
        return res

    pre_p = prot(pre, pre_units, fc.old)
    post_p = prot(post, post_units, fc.new)
    touched: set[tuple[str, str]] = set()
    for lines, units in ((fc.removed if pre is not None else [], pre_units),
                         (fc.added if post is not None else [], post_units)):
        for ln in lines:
            u = _innermost(units, ln)
            if u:
                touched.add((u.kind, u.name))
    return {f"{fc.path}::{k}:{n}" for k, n in touched
            if pre_p.get((k, n)) or post_p.get((k, n))}


def _read_blobs(base: Path, specs: list[str]) -> dict[str, str | None]:
    """``rev:path`` -> text (None if missing), with one ``git cat-file --batch``."""
    if not specs:
        return {}
    r = subprocess.run(["git", "cat-file", "--batch"], cwd=base, capture_output=True, check=True,
                       input=("\n".join(specs) + "\n").encode())
    out, buf, pos = {}, r.stdout, 0
    for spec in specs:
        nl = buf.index(b"\n", pos)
        hdr = buf[pos:nl].decode()
        pos = nl + 1
        if hdr.endswith(" missing") or hdr.endswith(" ambiguous"):
            out[spec] = None
            continue
        size = int(hdr.split()[2])
        out[spec] = buf[pos:pos + size].decode("utf-8", errors="surrogateescape")
        pos += size + 1
    return out


def compute_protected_hits(base: Path, commits: list[tuple[str, list[FileChange]]]) -> dict[str, int]:
    """sha -> number of distinct changed units with a protected call (decision 2)."""
    return {sha: len(names) for sha, names in compute_protected_units(base, commits).items()}


def compute_protected_units(base: Path, commits: list[tuple[str, list[FileChange]]]
                            ) -> dict[str, set[str]]:
    """sha -> the distinct changed units (``path::kind:name``) with a protected call."""
    specs: list[str] = []
    for sha, changes in commits:
        for fc in changes:
            if is_unit_source(fc.old) and fc.old is not None:
                specs.append(f"{sha}^:{fc.old}")
            if is_unit_source(fc.new) and fc.new is not None:
                specs.append(f"{sha}:{fc.new}")
    blobs = _read_blobs(base, sorted(set(specs)))
    units = function_units({k: v for k, v in blobs.items() if v is not None})
    hits: dict[str, set[str]] = {}
    for sha, changes in commits:
        names: set[str] = set()
        for fc in changes:
            if not (is_unit_source(fc.old) or is_unit_source(fc.new)):
                continue
            pk = f"{sha}^:{fc.old}" if is_unit_source(fc.old) else None
            nk = f"{sha}:{fc.new}" if is_unit_source(fc.new) else None
            pre, post = blobs.get(pk) if pk else None, blobs.get(nk) if nk else None
            names |= units_hit(fc, pre, post, units.get(pk, []) if pk else [],
                               units.get(nk, []) if nk else [])
        hits[sha] = names
    return hits


def _sort(cands: list[Candidate]) -> list[Candidate]:
    """2026 commits first, then newer first."""
    cands = sorted(cands, key=lambda c: (c.date, c.sha), reverse=True)
    return sorted(cands, key=lambda c: not c.date.startswith("2026"))


# --- git ------------------------------------------------------------------------

def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    # surrogateescape: diffs may contain non-UTF-8 bytes (e.g. windows-1252 test
    # fixtures); they must round-trip byte-exactly into the revert patches.
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True,
                          encoding="utf-8", errors="surrogateescape")


def _assert_frozen() -> None:
    r = _git(ROOT, "rev-parse", "-q", "--verify", f"refs/tags/{FROZEN_TAG}", check=False)
    if r.returncode != 0:
        raise RuntimeError(f"git tag {FROZEN_TAG!r} not found in {ROOT}: A+ must be frozen "
                           "(Tasks 2-4) before any task is mined or materialised")


def _base(base: Path | None) -> Path:
    if base is not None:
        return base
    from aa.substrate import fetch_base
    return fetch_base()


_NO_GC = ("-c", "gc.auto=0", "-c", "maintenance.auto=false")
_NULL_OID = "0" * 40


def _log_args(since: str) -> list[str]:
    return [f"--since={since}", "--no-merges", "--full-diff", "--", f"{LOOT}/src"]


def prefetch_blobs(base: Path, since: str = SINCE) -> int:
    """Fetch, in one batch, the blobs the candidate diffs need; returns how many.

    The base clone is blob-filtered. Letting ``git log -p`` fetch blobs lazily
    means one fetch (and one auto-gc) per blob, which races and dies with
    "in the commit graph file but not in the object database". Blob ids come
    from ``--raw`` (no blob content needed); missing ones are listed without
    triggering lazy fetches and fetched with a single ``--stdin`` request.
    """
    raw = _git(base, "log", "--format=", "--raw", "--no-abbrev", *_log_args(since)).stdout
    oids = sorted({o for line in raw.splitlines() if line.startswith(":")
                   for o in line.split()[2:4] if o != _NULL_OID})
    if not oids:
        return 0
    chk = subprocess.run(["git", "cat-file", "--batch-check=%(objectname)"], cwd=base,
                         input="\n".join(oids) + "\n", capture_output=True, text=True,
                         check=True, env={**os.environ, "GIT_NO_LAZY_FETCH": "1"})
    missing = [ln.split()[0] for ln in chk.stdout.splitlines() if ln.endswith(" missing")]
    if missing:
        subprocess.run(["git", *_NO_GC, "-c", "fetch.negotiationAlgorithm=noop", "fetch", "origin",
                        "--no-tags", "--no-write-fetch-head", "--recurse-submodules=no",
                        "--filter=blob:none", "--stdin"], cwd=base, input="\n".join(missing) + "\n",
                       capture_output=True, text=True, check=True)
    return len(missing)


def list_candidates(base: Path, since: str = SINCE) -> list[Candidate]:
    """Non-merge commits since ``since`` touching ``packages/loot-core/src``.

    One ``git log -p -U0 --full-diff`` pass: ``--full-diff`` makes the patch (and so
    ``files``) cover the whole commit, so a ``package.json`` touched alongside
    loot-core sources is seen by the ``touches_deps`` filter.
    """
    prefetch_blobs(base, since)
    fmt = f"{_REC}%H{_FLD}%ad{_FLD}%s{_FLD}%B{_HDR_END}"
    out = _git(base, *_NO_GC, "log", "--date=short", f"--format={fmt}", "-p", "-U0",
               "--no-color", "--no-ext-diff", *_log_args(since)).stdout
    cands, commits = [], []
    for rec in out.split(_REC)[1:]:
        hdr, _, patch = rec.partition(_HDR_END)
        sha, date, subject, body = hdr.split(_FLD, 3)
        files, changes = parse_patch(patch)
        commits.append((sha, changes))
        cands.append(Candidate(
            sha=sha, date=date, subject=subject, files=files,
            test_files=[f for f in files if is_test_file(f) and f.startswith(f"{LOOT}/")],
            ai_label="[AI]" in subject or "[AI]" in body,
        ))
    hits = compute_protected_hits(base, commits)
    for c in cands:
        c.protected_hits = hits.get(c.sha, 0)
    return _sort(cands)


def mine(since: str = SINCE, base: Path | None = None) -> list[Candidate]:
    """All candidates (unfiltered, sorted). Requires the ``aplus-frozen`` tag."""
    _assert_frozen()
    return list_candidates(_base(base), since)


def preview(since: str = SINCE, base: Path | None = None) -> Counter:
    """Read-only: counts per drop reason (``ok`` = survives the static filters).

    Does not need A+ and writes nothing under ``tasks/`` (git may lazily fetch
    missing blobs into the blob-filtered base clone).
    """
    return Counter(filter_reason(c) or "ok" for c in list_candidates(_base(base), since))


# --- materialisation --------------------------------------------------------------

# --- PR-number leaks (review 4, finding 2) -----------------------------------------
# Release notes at base list each merged PR as "- [#8114](...) <summary>": an agent
# grepping for the task's PR number would find the change's description (and the
# PR link). Every condition's start tree drops those lines.
_PR_SUBJECT_RE = re.compile(r"\(#(\d+)\)\s*$")
_PR_ANY_RE = re.compile(r"(?<![\w&])#(\d{3,})\b")
# Prose / data files where a mention is stripped line-wise (release notes, blog,
# changelogs, news feed). A mention in code is only reported (stripping a code
# line could break the build).
STRIPPABLE_RE = re.compile(r"\.(?:md|mdx|markdown|txt|rst|json)$"
                           r"|(?:^|/)(?:CHANGELOG|CHANGES|HISTORY|RELEASES?|NEWS)[^/]*$", re.I)


def pr_number(subject: str) -> str | None:
    """The PR number of a squash-merge subject ("... (#8114)"), else the first #NNN."""
    m = _PR_SUBJECT_RE.search(subject) or _PR_ANY_RE.search(subject)
    return m.group(1) if m else None


_UNESCAPED_QUOTE = re.compile(r'(?<!\\)"')


def _pr_token(pr: str) -> re.Pattern:
    return re.compile(rf"#{pr}(?!\d)")


def strip_pr_text(text: str, pr: str, json_file: bool = False) -> str | None:
    """``text`` without the lines that mention ``#<pr>`` (None if nothing to strip or,
    for JSON, if the result would not parse). Inside a line with escaped newlines
    (a JSON string holding markdown, e.g. the news feed) only the escaped "lines"
    that mention it are dropped, so the JSON stays valid."""
    tok = _pr_token(pr)
    if not tok.search(text):
        return None
    out = []
    for line in text.splitlines(keepends=True):
        if not tok.search(line):
            out.append(line)
        elif "\\n" in line:
            segs = line.split("\\n")
            keep: list[str] = []
            head = ""
            for i, seg in enumerate(segs):
                if not tok.search(seg):
                    keep.append(head + seg)
                    head = ""
                    continue
                # The first / last escaped line also holds the string's opening /
                # closing quote (and what precedes / follows it on the physical
                # line): keep that, glued to its neighbour without a newline.
                quotes = [m.start() for m in _UNESCAPED_QUOTE.finditer(seg)]
                if i == len(segs) - 1 and quotes:
                    tail = seg[quotes[0]:]
                    if keep:
                        keep[-1] += tail
                    else:
                        keep.append(head + tail)
                elif i == 0 and quotes:
                    head = seg[:quotes[-1] + 1]
            out.append("\\n".join(keep))
        # else: the whole line goes
    new = "".join(out)
    if json_file:
        try:
            json.loads(new)
        except ValueError:
            return None
    return new


def strip_pr_mentions(work: Path, pr: str | None, notes: list[str] = ()) -> dict[str, list[str]]:
    """Strip every mention of PR ``#<pr>`` from the tree at ``work`` (a git work tree)
    and stage the edits: lines of release notes / docs / changelogs / JSON data
    (``strip_pr_text``), the PR's own ``upcoming-release-notes/<pr>.md`` and the
    release-note files the commit itself added (``notes``: Actual names many of
    them by topic, e.g. ``fix-schedule-auto-post-same-day.md``, and the revert
    skips them, so an unreleased one would describe the change in the start tree).
    Returns {"stripped": files edited or removed, "left": files still mentioning it
    (code, tests, or a JSON edit that would not parse)}."""
    stripped, left = [], []
    for note in {*notes, *([f"upcoming-release-notes/{pr}.md"] if pr else [])}:
        if (work / note).is_file():
            _git(work, "rm", "-q", "--", note)
            stripped.append(note)
    if not pr:
        return {"stripped": sorted(stripped), "left": []}
    r = _git(work, "grep", "-l", "-I", "-P", rf"#{pr}(?!\d)", check=False)
    for f in r.stdout.split():
        if not STRIPPABLE_RE.search(f) or is_test_file(f) or "__snapshots__/" in f:
            left.append(f)
            continue
        fp = work / f
        new = strip_pr_text(fp.read_text(encoding="utf-8", errors="surrogateescape"), pr,
                            json_file=f.endswith(".json"))
        if new is None:
            left.append(f)
            continue
        fp.write_text(new, encoding="utf-8", errors="surrogateescape")
        _git(work, "add", "--", f)
        stripped.append(f)
    return {"stripped": sorted(stripped), "left": sorted(left)}


def task_id(c: Candidate) -> str:
    return c.sha[:10]


def _read_worktree(work: Path, paths: list[str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for f in paths:
        fp = work / f
        out[f] = fp.read_text(encoding="utf-8", errors="surrogateescape") if fp.is_file() else None
    return out


def _revert_on(variant: Path, base: Path, patches: list[Path], cond: str, *,
               test_files: list[str] = (),
               test_overrides: dict[str, str | None] | None = None,
               pr: str | None = None, notes: list[str] = (), strip_log: dict | None = None,
               ) -> tuple[str, dict[str, str | None]] | DropReason:
    """Apply reverse patches 3-way on a throwaway clone of ``variant``; then, if
    ``test_overrides`` is given, set each listed test file to its content (None:
    delete it) instead of reverting it; then, if ``pr`` is given, strip the
    mentions of the PR number (``strip_pr_mentions``; result into ``strip_log``).

    Returns (``git diff`` of the reverted tree vs the variant, contents of
    ``test_files`` in the reverted tree), or a DropReason. The base clone's object
    store is added as an alternate so the 3-way merge finds the commit's blobs
    (variants are history-less single-commit repos).
    """
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "t"
        _git(Path(tmp), "clone", "-q", "--shared", str(variant), str(work))
        alt = work / ".git" / "objects" / "info" / "alternates"
        base_objects = Path(_git(base, "rev-parse", "--path-format=absolute",
                                 "--git-common-dir").stdout.strip()) / "objects"
        alt.write_text(alt.read_text() + f"{base_objects}\n")
        for patch in patches:
            if patch.stat().st_size == 0:
                continue
            r = _git(work, "apply", "--3way", "--index", "--whitespace=nowarn", str(patch),
                     check=False)
            unmerged = _git(work, "diff", "--name-only", "--diff-filter=U").stdout.strip()
            if r.returncode != 0 or unmerged:
                return DropReason(f"revert_conflict:{cond}")
        for f, content in (test_overrides or {}).items():
            fp = work / f
            if content is None:
                if fp.exists():
                    _git(work, "rm", "-q", "--cached", "--ignore-unmatch", "--", f)
                    fp.unlink()
                continue
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8", errors="surrogateescape")
            _git(work, "add", "--", f)
        changed = _git(work, "diff", "--cached", "--name-only", "HEAD").stdout.split()
        if not [f for f in changed if not is_test_file(f)]:
            return DropReason(f"empty_revert:{cond}")
        if pr or notes:
            log = strip_pr_mentions(work, pr, notes)
            if strip_log is not None:
                strip_log.update(log)
        return (_git(work, "diff", "--cached", "--binary", "HEAD").stdout,
                _read_worktree(work, list(test_files)))


def derive_start_tests(a_tests: dict[str, str | None], cond: str,
                       names=None) -> dict[str, str | None]:
    """Start-tree test files of ``cond`` from A's (3-way reverted) ones: identity on
    A/AL, the A+ hidden-test rewrite (``aa.hidden_tests``) on AP/APL; a file absent
    from A's start tree is absent everywhere."""
    from aa.hidden_tests import rewrite_for_condition
    return {f: None if t is None else rewrite_for_condition(t, cond, f, names)
            for f, t in a_tests.items()}


def reference_patch(base: Path, c: Candidate) -> str:
    """The original commit's non-test diff (what the agent is asked to re-create)."""
    non_test = code_files(c.files)
    if not non_test:
        return ""
    return _git(base, "diff", "--binary", "--full-index", f"{c.sha}^", c.sha, "--", *non_test).stdout


def materialise(c: Candidate, *, base: Path | None = None, variants: Path | None = None,
                out: Path | None = None, conds: tuple[str, ...] = CONDITIONS) -> TaskDir | DropReason:
    """Write ``tasks/<id>/`` (task.json, revert.<cond>.patch, reference.patch) or return
    why it was dropped.

    The start tree of each condition = variant + full revert of the commit (test
    files included, so the agent never sees the hidden tests). Source files revert
    3-way on every condition. Test files revert 3-way on A only; AL, AP and APL get
    A's start-tree test files through ``derive_start_tests`` (the A+ rewrite on
    AP/APL, as for the hidden tests). Hidden tests = the commit's test files as
    they exist at base (the evaluator rewrites them per condition). Nothing is
    written unless every condition reverts cleanly.
    """
    _assert_frozen()
    base = _base(base)
    variants = variants or WORK / "variants"
    out = out or TASKS
    hidden = [f for f in c.test_files
              if _git(base, "cat-file", "-e", f"HEAD:{f}", check=False).returncode == 0]
    if not hidden:
        return DropReason("no_tests_at_base")
    test_paths = [f for f in c.files if is_test_file(f)]
    source_paths = code_files(c.files)
    pr = pr_number(c.subject)
    notes = [f for f in c.files if f.startswith("upcoming-release-notes/")
             and f != "upcoming-release-notes/README.md"]
    strip_logs: dict[str, dict] = {}

    def reverse(paths: list[str]) -> str:
        if not paths:
            return ""
        return _git(base, "diff", "--binary", "--full-index", "--no-renames", c.sha, f"{c.sha}^",
                    "--", *(f":(literal){f}" for f in paths)).stdout

    def tree(cond: str) -> Path:
        vt = variants / cond
        if not vt.exists():
            from aa.substrate import build_variant
            vt = build_variant(cond)
        return vt

    patches: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        src_pf, test_pf = Path(tmp) / "reverse.src.patch", Path(tmp) / "reverse.tests.patch"
        src_pf.write_text(reverse(source_paths), encoding="utf-8", errors="surrogateescape")
        test_pf.write_text(reverse(test_paths), encoding="utf-8", errors="surrogateescape")
        # A first: its 3-way test revert defines every condition's start-tree tests
        # (A+ rewrote Actual's tests, so reverting them 3-way on AP/APL would conflict
        # for no reason). Source files revert 3-way on each condition: a conflict
        # there is a real one.
        strip_logs["A"] = {}
        res = _revert_on(tree("A"), base, [src_pf, test_pf], "A", test_files=test_paths,
                         pr=pr, notes=notes, strip_log=strip_logs["A"])
        if isinstance(res, DropReason):
            return res
        a_patch, a_tests = res
        if "A" in conds:
            patches["A"] = a_patch
        names = None
        if test_paths and REWRITTEN_CONDS & set(conds):
            from aa.hidden_tests import moved_names
            names = moved_names(variants)
        for cond in conds:
            if cond == "A":
                continue
            strip_logs[cond] = {}
            res = _revert_on(tree(cond), base, [src_pf], cond,
                             test_overrides=derive_start_tests(a_tests, cond, names),
                             pr=pr, notes=notes, strip_log=strip_logs[cond])
            if isinstance(res, DropReason):
                return res
            patches[cond] = res[0]
    d = out / task_id(c)
    d.mkdir(parents=True, exist_ok=True)
    for cond, p in patches.items():
        (d / f"revert.{cond}.patch").write_text(p, encoding="utf-8", errors="surrogateescape")
    (d / "reference.patch").write_text(reference_patch(base, c), encoding="utf-8",
                                       errors="surrogateescape")
    # Hidden tests as they are at base: the evaluator rewrites these per condition.
    for f in hidden:
        dst = d / HIDDEN_DIR / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(subprocess.run(["git", "show", f"HEAD:{f}"], cwd=base, check=True,
                                       capture_output=True).stdout)
    meta = {
        "id": task_id(c), "sha": c.sha, "date": c.date, "subject": c.subject,
        "ai_label": c.ai_label,
        "pr": pr,
        # Mentions of the PR number stripped from every condition's start tree
        # (release notes, docs, news feed), and any left (code/tests: report only).
        "pr_mentions_stripped": strip_logs.get("A", {}).get("stripped", []),
        "pr_mentions_left": sorted({f for lg in strip_logs.values() for f in lg.get("left", [])}),
        "hidden_tests": hidden,
        "touched_files": code_files(c.files),
        "statement_path": "statement.md",
        "per_condition": {cond: {"revert_patch": f"revert.{cond}.patch"} for cond in patches},
        "start_tests": "A: 3-way revert; other conditions: derived from A (A+ rewrite on AP/APL)",
        "reference_patch": "reference.patch",
        "hidden_dir": HIDDEN_DIR,
        "selected": False,
    }
    (d / "task.json").write_text(json.dumps(meta, indent=2) + "\n")
    return d


# --- statements (plan Task 6 Step 5) ----------------------------------------------

# A statement describes behaviour only: it never names the protected APIs, the A+
# layer, or where the change goes.
FORBIDDEN = re.compile(r"\b(db\.|sendMessages|amountToInteger|integerToAmount|cents\b|Cents\b|"
                       r"domain/|mutator|undoable|runQuery|insert\w*\(|update\w*\()", re.I)
_CODE_EXT = r"(?:[cm]?[jt]sx?|json|sql|snap)"
FILE_PATH_RE = re.compile(
    rf"(?<![\w@])(?:[\w.-]+/)+[\w.-]+(?:\.{_CODE_EXT})?(?![\w/])"  # a/b/c(.ts)
    rf"|\b[\w-]+(?:\.[\w-]+)*\.{_CODE_EXT}\b")                     # actions.ts
# "a/b" prose (and/or, input/output) is not a path: require a code-ish segment.
_PATH_HINT = re.compile(r"\.|\b(?:src|server|packages|shared|client|platform|budget|accounts|"
                        r"transactions|db|sync|types|loot-core|desktop-client)/")


# Upstream pointers (decision 2026-10-06): an issue/PR number in prose ("issue 5694",
# "PR 8877"), the upstream repo slug, and any GitHub URL let the agent look the fix up.
UPSTREAM_REF_RE = re.compile(
    r"\b(?:issues?|bugs?|tickets?|PRs?|pull(?:\s+requests?)?|pulls?)\s*(?:no\.?\s*|number\s*)?#?\s*\d{3,}\b"
    r"|actualbudget/actual"
    r"|(?:https?://)?(?:[\w-]+\.)*github(?:usercontent)?\.com\b\S*", re.I)


def statement_leaks(text: str) -> list[str]:
    """Leak-check findings for one statement (empty = clean)."""
    found = [f"forbidden: {m.group(0)!r}" for m in FORBIDDEN.finditer(text)]
    found += [f"PR number: {m.group(0)!r}" for m in _PR_ANY_RE.finditer(text)]
    found += [f"upstream reference: {m.group(0)!r}" for m in UPSTREAM_REF_RE.finditer(text)]
    for m in FILE_PATH_RE.finditer(text):
        tok = m.group(0)
        if "/" in tok and not _PATH_HINT.search(tok):
            continue
        found.append(f"file path: {tok!r}")
    return found


def check_statements(root: Path | None = None) -> dict[str, list[str]]:
    """{task id: problems} for every materialised, not dropped task whose statement is
    missing or leaks (``statement_leaks``); empty dict = all clean."""
    root = root or TASKS
    ledger = read_ledger(root)
    out: dict[str, list[str]] = {}
    for tj in sorted(root.glob("*/task.json")):
        meta = json.loads(tj.read_text())
        if meta.get("dropped") or is_dropped(ledger, tj.parent.name):
            continue
        sp = tj.parent / meta.get("statement_path", "statement.md")
        if not sp.exists():
            out[tj.parent.name] = ["missing statement.md"]
            continue
        probs = statement_leaks(sp.read_text())
        if probs:
            out[tj.parent.name] = probs
    return out


# --- sanity check (plan Task 6 Step 4) ------------------------------------------

HIDDEN_DIR = "hidden"  # tasks/<id>/hidden/<path>: hidden tests at base (= aa.evaluate.TASK_HIDDEN)
NOT_PORTABLE = "hidden_tests_not_portable"


def run_hidden(task_dir: Path, cond: str, mode: str, *, execute=None,
               checker_dir: Path | None = None, work_root: Path | None = None) -> dict:
    """Run the task's hidden tests (rewritten for ``cond``) in the ``cond`` image on
    the start tree (``mode="start"``: revert applied) or on the untouched variant
    (``mode="reference"``: the reference solution). Lint and typecheck are skipped.
    Returns ``aa.evaluate.hidden_outcome`` plus ``eval_error``."""
    from aa import evaluate as ev

    if mode not in ("start", "reference"):
        raise ValueError(mode)
    task_dir = Path(task_dir).resolve()
    meta = json.loads((task_dir / "task.json").read_text())
    hidden = meta["hidden_tests"]
    base = (work_root or WORK / "sanity") / meta["id"] / cond
    run_dir, out = base / mode, base / f"{mode}-out"
    for d in (run_dir, out):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    (run_dir / "diff.patch").write_text("")
    ev.stage_hidden_tests(task_dir, hidden, cond, out)
    revert = meta["per_condition"][cond]["revert_patch"] if mode == "start" else None
    script = ev.eval_script(revert, hidden, static_checks=False)
    argv = ev.eval_docker_argv(cond, run_dir, task_dir, out, script,
                               checker_dir or ev.PROBE_SRC.parent)
    eval_error = None
    try:
        (execute or ev.docker_execute)(argv, ev.HOST_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        eval_error = "eval_timeout"
    if eval_error is None:
        e = (out / "eval_error").read_text().strip() if (out / "eval_error").exists() else ""
        eval_error = e or (None if (out / "eval_done").exists() else "container")
    report = None
    if (out / "report.json").exists():
        try:
            report = json.loads((out / "report.json").read_text())
        except json.JSONDecodeError:
            pass
    return {**ev.hidden_outcome(report, hidden), "eval_error": eval_error}


def sanity_check(task_dir: Path, *, conds: tuple[str, ...] = CONDITIONS,
                 details: dict | None = None, **kw) -> DropReason | None:
    """None if the task is usable on every condition, else why it is dropped (for all).

    1. Reference (untouched variant + hidden tests) must pass on every condition.
       A failure on A/AL -> ``reference_fails:<cond>``; A/AL pass but AP/APL fail
       with the rewritten tests -> ``hidden_tests_not_portable``.
    2. Start tree + hidden tests must fail on every condition -> ``not_discriminating``.
    An eval error (revert does not apply, container died) -> ``sanity_error:<cond>:<err>``.
    ``details`` (if given) receives every run's outcome.
    """
    details = {} if details is None else details
    for mode in ("reference", "start"):
        for cond in conds:
            res = run_hidden(task_dir, cond, mode, **kw)
            details[f"{cond}:{mode}"] = res
            if res["eval_error"]:
                return DropReason(f"sanity_error:{cond}:{res['eval_error']}")
        if mode == "reference":
            failing = [c for c in conds if not details[f"{c}:reference"]["correct"]]
            plain = [c for c in failing if c not in REWRITTEN_CONDS]
            if plain:
                return DropReason(f"reference_fails:{plain[0]}")
            if failing:
                return DropReason(NOT_PORTABLE)
    if any(details[f"{c}:start"]["correct"] for c in conds):
        return DropReason("not_discriminating")
    return None


def update_ledger(root: Path, tid: str, **fields) -> None:
    """Merge ``fields`` into the ledger entry of ``tid`` (same shapes as ``read_ledger``)."""
    p = root / "_ledger.json"
    raw = json.loads(p.read_text()) if p.exists() else {}
    if isinstance(raw, list):
        entry = next((e for e in raw if isinstance(e, dict) and e.get("id") == tid), None)
        if entry is None:
            entry = {"id": tid}
            raw.append(entry)
    else:
        entries = raw["tasks"] if isinstance(raw.get("tasks"), dict) else raw
        entry = entries.setdefault(tid, {})
    entry.update(fields)
    p.write_text(json.dumps(raw, indent=2) + "\n")


def check_and_record(task_dir: Path, root: Path | None = None, **kw) -> DropReason | None:
    """``sanity_check`` + bookkeeping: ``tasks/<id>/sanity.json`` with every run's
    outcome; the ledger entry gets ``sanity: "ok"`` or ``dropped: <reason>``; a
    dropped task is unselected in its task.json (for every condition)."""
    root = root or TASKS
    task_dir = Path(task_dir)
    tj = task_dir / "task.json"
    meta = json.loads(tj.read_text())
    details: dict = {}
    reason = sanity_check(task_dir, details=details, **kw)
    (task_dir / "sanity.json").write_text(json.dumps(
        {"reason": reason.reason if reason else None, "runs": details}, indent=2) + "\n")
    if reason is None:
        update_ledger(root, meta["id"], sanity="ok", dropped=None)
        meta.pop("dropped", None)
    else:
        update_ledger(root, meta["id"], sanity="dropped", dropped=reason.reason)
        meta["dropped"] = reason.reason
        meta["selected"] = False
    tj.write_text(json.dumps(meta, indent=2) + "\n")
    return reason


def read_ledger(root: Path) -> dict[str, dict]:
    """``tasks/_ledger.json`` as {id: entry}; accepts the dict, {"tasks": {...}} and
    list-of-entries shapes that ``memo_probe.mark_memorised`` handles."""
    p = root / "_ledger.json"
    if not p.exists():
        return {}
    raw = json.loads(p.read_text())
    if isinstance(raw, list):
        return {e["id"]: e for e in raw if isinstance(e, dict) and "id" in e}
    if isinstance(raw.get("tasks"), dict):
        return raw["tasks"]
    return {k: v for k, v in raw.items() if isinstance(v, dict)}


def is_memorised(ledger: dict[str, dict], tid: str) -> bool:
    return ledger.get(tid, {}).get("memorised") is True


def is_dropped(ledger: dict[str, dict], tid: str) -> bool:
    return bool(ledger.get(tid, {}).get("dropped"))


def load_tasks(selected_only: bool = True, root: Path | None = None) -> list[Task]:
    """Materialised tasks. ``selected_only`` keeps tasks marked ``selected`` and never
    returns one the memorisation probe flagged (``memorised: true`` in the ledger) or
    the sanity check dropped (``dropped`` in the ledger or task.json), even if its
    task.json says selected."""
    root = root or TASKS
    ledger = read_ledger(root)
    out = []
    for tj in sorted(root.glob("*/task.json")):
        meta = json.loads(tj.read_text())
        t = Task(**{k: meta[k] for k in ("id", "sha", "date", "subject", "hidden_tests",
                                          "touched_files", "statement_path", "per_condition")},
                 selected=bool(meta.get("selected", False)), dir=tj.parent)
        if not selected_only or (t.selected and not is_memorised(ledger, t.id)
                                 and not is_dropped(ledger, t.id) and not meta.get("dropped")):
            out.append(t)
    return out


def selection_preview(root: Path | None = None) -> list[dict]:
    """Every task id known to the ledger or materialised under ``root``, with whether it
    survives selection and, if not, why: the materialise drop reason, the sanity drop
    reason, ``memorised``, or ``unchecked`` (materialised, sanity check not run yet).
    ``memo`` is the memorisation-probe verdict (None: not probed). Read-only."""
    root = root or TASKS
    ledger = read_ledger(root)
    metas = {tj.parent.name: json.loads(tj.read_text()) for tj in sorted(root.glob("*/task.json"))}
    rows = []
    for tid in sorted(set(ledger) | set(metas)):
        e, meta = ledger.get(tid, {}), metas.get(tid)
        if meta is None:
            reason = e.get("reason") or ("not_materialised" if e.get("status") != "dropped"
                                         else "dropped")
        elif e.get("dropped") or meta.get("dropped"):
            reason = e.get("dropped") or meta.get("dropped")
        elif is_memorised(ledger, tid):
            reason = "memorised"
        elif e.get("sanity") != "ok":
            reason = "unchecked"
        else:
            reason = None
        rows.append({"id": tid, "survives": reason is None, "reason": reason,
                     "memo": e.get("memorised"), "date": e.get("date") or (meta or {}).get("date"),
                     "subject": e.get("subject") or (meta or {}).get("subject", "")})
    return rows
