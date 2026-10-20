"""Hidden checker, host side (spec section on the hidden checker; plan Task 5).

Two halves, applied identically to all four conditions:

* ``check_diff`` scans the *added* lines of the agent's diff (files under
  ``packages/loot-core/src/``, tests excluded) for four static patterns.
* ``probe_violations`` turns the JSONL events written by the runtime probe
  (``substrate/checker/probe.setup.ts``) into violations. A ``raw_write`` only
  counts when its caller (``src/...:line``) is a line the agent *added* in its
  diff (review finding 4): base writers, and base writers whose line merely
  shifted, are never blamed on the agent.

Every violation carries ``lint_visible`` (review finding 11): whether the visible
lint of the run's condition (plan Task 4 rule lists) would flag the same thing.
``A``/``AP`` have no custom lint (``lint`` = ``tsgo -b``), so nothing is visible
there; for ``AL``/``APL`` see :data:`LINT_VISIBLE_KINDS` and :func:`_visible`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from unidiff import PatchSet
from unidiff.errors import UnidiffParseError

from aa.config import CONDITIONS


@dataclass(frozen=True)
class Violation:
    kind: str
    file: str
    line: int
    detail: str
    lint_visible: bool = False

    def to_json(self) -> dict:
        return {"kind": self.kind, "file": self.file, "line": self.line,
                "detail": self.detail, "lint_visible": self.lint_visible}


# --- static checks ---------------------------------------------------------------------

LOOT_PREFIX = "packages/loot-core/"
SRC_PREFIX = LOOT_PREFIX + "src/"
_TEST_FILE = re.compile(r"(\.test\.|\.spec\.|/__tests__/|/__mocks__/|^packages/loot-core/src/mocks/)")
# Paths relative to SRC_PREFIX.
_DB_OR_SYNC = ("server/db/", "server/sync/")
_DOMAIN_OR_DB = ("server/domain/", "server/db/")
_MONEY_UTIL = "shared/util.ts"

_SEND_MESSAGES = re.compile(r"\bsendMessages\b")

_METHOD = re.compile(r"""\bapp\.method\(\s*(['"`])([\w:/-]+)\1\s*,\s*(.*)$""")
_READ_METHOD = re.compile(r"^(get|query|list)")
_MUTATOR = re.compile(r"^\s*mutator\s*\(")

_MONEY_WORD = r"(?:amount|balance|budgeted|spent|carryover)"
_MONEY = rf"(?:[\w$]+\??\.)*[\w$]*{_MONEY_WORD}[\w$]*"
_HUNDRED = r"(?:\b100\b(?!\.\d)|\b10\s*\*\*\s*\w+|Math\.pow\(\s*10\s*,[^)]*\))"
_FLOAT_MONEY = [
    # same as the no-float-money lint rule: money * or / 100 (or 10 ** n / Math.pow(10, n))
    re.compile(rf"{_MONEY}\s*[*/]\s*{_HUNDRED}", re.I),
    re.compile(rf"{_HUNDRED}\s*[*/]\s*{_MONEY}", re.I),
    # stricter than the lint rule: float parsing of an amount-named value ...
    re.compile(rf"\b(?:parseFloat|Number)\(\s*[^)]*\b{_MONEY}", re.I),
    # ... and toFixed on amounts
    re.compile(rf"{_MONEY}\s*\)?\s*\.toFixed\(", re.I),
]

_DB_WRITE_IMPORT = re.compile(
    r"""(?:\bfrom\s+|\brequire\(\s*|\bimport\(\s*|^\s*import\s+)"""
    r"""(['"])(?:#server/db/write|(?:\.\./)+db/write|\./db/write)(?:\.[jt]s)?\1"""
)


# --- visible lint per condition (plan Task 4) --------------------------------------------
#
# Which checker kinds the visible lint of each condition can see at all:
#   AL  = no-raw-synced-write, sendMessages restriction, no-float-money, mutator-required
#   APL = db/write import restriction, sendMessages restriction, mutator-required
#         (plus Cents cast / no-explicit-any / ban-ts-comment, which match no checker kind)
#   A, AP: `lint` is `tsgo -b` only.
# `non_integer_money` is a runtime property: no lint sees it in any condition.
LINT_VISIBLE_KINDS: dict[str, frozenset[str]] = {
    "A": frozenset(),
    "AP": frozenset(),
    "AL": frozenset({"raw_write", "send_messages_outside_db", "float_money_math", "unwrapped_mutation"}),
    "APL": frozenset({"db_write_import_outside_domain", "send_messages_outside_db", "unwrapped_mutation"}),
}
# eslint.agent.config.mjs lints `src/**/*.ts` only.
_LINTED_FILE = re.compile(r"\.ts$")
# Synced tables of the runtime probe. The no-raw-synced-write rule names all of
# these plus the other CRDT-written tables (account_groups, banks, cleanup_groups,
# dashboard_pages, payee_locations, schedules_next_date, zero_budget_months), so
# every raw_write the probe can report is on a table the rule names.
SYNCED_TABLES = frozenset({
    "transactions", "accounts", "categories", "category_groups", "payees", "payee_mapping",
    "schedules", "rules", "notes", "tags", "zero_budgets", "reflect_budgets", "custom_reports",
    "dashboard", "preferences", "transaction_filters", "category_mapping",
})
# no-raw-synced-write: runQuery/execQuery/run whose first argument is a string or
# template literal starting with a write keyword on a synced table. SQL built at
# runtime (variables, concatenation) is invisible to the rule.
_LINT_RAW_WRITE = re.compile(
    r"""\b(?:runQuery|execQuery|run)\s*\(\s*(['"`])\s*"""
    r"""(?:INSERT(?:\s+OR\s+\w+)?\s+INTO|UPDATE|DELETE\s+FROM|REPLACE\s+INTO)\s+["`]?(\w+)""",
    re.I,
)
# no-restricted-imports (APL): ESM imports/re-exports whose specifier matches the
# rule's regex `^(#server/db/write|(../)+db/write|./db/write)(.[jt]s)?$`.
# require()/import() are not seen by no-restricted-imports.
_LINT_DB_WRITE_IMPORT = re.compile(
    r"""(?:\bfrom\s+|^\s*import\s+)(['"])(?:#server/db/write|(?:\.\./)+db/write|\./db/write)(?:\.[jt]s)?\1"""
)
# no-float-money only knows `money * / 100` (and 10 ** n, Math.pow(10, n)); the
# first two _FLOAT_MONEY patterns. parseFloat/Number/toFixed are checker-only.
_LINT_FLOAT = _FLOAT_MONEY[:2]


def _visible(kind: str, path: str, text: str, next_text: str | None, cond: str) -> bool:
    """Would the visible lint of ``cond`` flag this violation (same file, same line)?"""
    if kind not in LINT_VISIBLE_KINDS[cond] or not _LINTED_FILE.search(path):
        return False
    if kind == "float_money_math":
        return any(p.search(text) for p in _LINT_FLOAT)
    if kind == "db_write_import_outside_domain":
        return _LINT_DB_WRITE_IMPORT.search(text) is not None
    if kind == "raw_write":
        joined = text if next_text is None else f"{text} {next_text}"
        m = _LINT_RAW_WRITE.search(joined)
        return m is not None and m.group(2).lower() in SYNCED_TABLES
    # send_messages_outside_db, unwrapped_mutation: the lint rule and the checker
    # use the same definition.
    return True


def _rel(path: str) -> str:
    return path[len(SRC_PREFIX):]


def _in(rel: str, prefixes: tuple[str, ...]) -> bool:
    return rel.startswith(prefixes)


def check_diff(diff_text: str, cond: str) -> list[Violation]:
    """Static violations in the added lines of ``diff_text``.

    ``cond`` does not change which violations are found: the hidden checker is
    identical for all conditions (``db_write_import_outside_domain`` is only
    meaningful on AP/APL but is computed everywhere). It only sets each
    violation's ``lint_visible``.
    """
    _check_cond(cond)
    if not diff_text.strip():
        return []

    out: list[Violation] = []
    for path, added in _added_lines(diff_text):
        if not path.startswith(SRC_PREFIX) or _TEST_FILE.search(path):
            continue
        rel = _rel(path)
        for no, text, next_added in added:

            def add(kind: str, detail: str) -> None:
                out.append(Violation(kind, path, no, detail,
                                     _visible(kind, path, text, next_added, cond)))

            if _SEND_MESSAGES.search(text) and not _in(rel, _DB_OR_SYNC):
                add("send_messages_outside_db", text.strip())

            m = _METHOD.search(text)
            if m and not _READ_METHOD.match(m.group(2)):
                handler = m.group(3)
                if not handler.strip() and next_added is not None:
                    handler = next_added
                if not _MUTATOR.match(handler):
                    add("unwrapped_mutation", m.group(2))

            if rel != _MONEY_UTIL and any(p.search(text) for p in _FLOAT_MONEY):
                add("float_money_math", text.strip())

            if _DB_WRITE_IMPORT.search(text) and not _in(rel, _DOMAIN_OR_DB):
                add("db_write_import_outside_domain", text.strip())
    return out


def _check_cond(cond: str) -> None:
    if cond not in CONDITIONS:
        raise ValueError(f"unknown condition {cond!r}; expected one of {CONDITIONS}")


AddedLine = tuple[int, str, str | None]  # (target line no, text, text of the next line if also added)


def added_source_lines(diff_text: str) -> dict[str, dict[int, tuple[str, str | None]]]:
    """``{"src/...": {line: (text, next added text)}}`` for non-test loot-core source
    files, keyed like the probe's callers (path relative to ``packages/loot-core``).

    Line numbers are target-side, i.e. line numbers in the evaluated tree, which is
    the start tree plus exactly this diff."""
    out: dict[str, dict[int, tuple[str, str | None]]] = {}
    if not diff_text.strip():
        return out
    for path, added in _added_lines(diff_text):
        if not path.startswith(SRC_PREFIX) or _TEST_FILE.search(path):
            continue
        key = path[len(LOOT_PREFIX):]
        out.setdefault(key, {}).update({no: (text, nxt) for no, text, nxt in added})
    return out


def _added_lines(diff_text: str) -> list[tuple[str, list[AddedLine]]]:
    """Added lines per target file. Uses unidiff; falls back to a lenient parser
    when hunk headers do not match their bodies (hand-written or truncated diffs),
    so a malformed agent diff never crashes the evaluator."""
    try:
        patch = PatchSet(diff_text)
    except UnidiffParseError:
        return _added_lines_lenient(diff_text)
    result = []
    for pf in patch:
        if pf.is_removed_file:
            continue
        added: list[AddedLine] = []
        for hunk in pf:
            lines = list(hunk)
            for i, ln in enumerate(lines):
                if ln.is_added:
                    nxt = lines[i + 1] if i + 1 < len(lines) else None
                    nxt_text = nxt.value.rstrip("\n") if nxt is not None and nxt.is_added else None
                    added.append((ln.target_line_no, ln.value.rstrip("\n"), nxt_text))
        result.append((pf.path, added))
    return result


_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _strip_prefix(p: str) -> str:
    p = p.split("\t", 1)[0].strip()
    return p[2:] if p.startswith(("a/", "b/")) else p


def _added_lines_lenient(diff_text: str) -> list[tuple[str, list[AddedLine]]]:
    result: list[tuple[str, list[AddedLine]]] = []
    raw = diff_text.splitlines()
    path: str | None = None
    added: list[AddedLine] = []
    lineno = 0
    in_hunk = False
    for i, line in enumerate(raw):
        if line.startswith("+++ ") and i > 0 and raw[i - 1].startswith("--- "):
            if path is not None:
                result.append((path, added))
            target = _strip_prefix(line[4:])
            path = None if target == "/dev/null" else target
            added, in_hunk = [], False
            continue
        if line.startswith("--- ") and i + 1 < len(raw) and raw[i + 1].startswith("+++ "):
            continue
        if line.startswith("diff --git "):
            in_hunk = False
            continue
        m = _HUNK.match(line)
        if m:
            lineno, in_hunk = int(m.group(1)), True
            continue
        if not in_hunk or path is None:
            continue
        if line.startswith("+"):
            nxt = raw[i + 1] if i + 1 < len(raw) else ""
            nxt_text = nxt[1:] if nxt.startswith("+") and not nxt.startswith("+++ ") else None
            added.append((lineno, line[1:], nxt_text))
            lineno += 1
        elif line.startswith(" ") or line == "":
            lineno += 1
        # "-" lines and "\ No newline" do not advance the target line
    if path is not None:
        result.append((path, added))
    return result


# --- runtime probe events --------------------------------------------------------------

def _split_caller(caller: str) -> tuple[str, int]:
    file, sep, line = caller.rpartition(":")
    if sep and line.isdigit():
        return file, int(line)
    return caller, 0


def load_baseline(path: Path) -> tuple[set[str], list[dict]]:
    """Read ``baseline-writers.json`` (``"src/...:line"`` strings or
    ``{"caller", "sql"}`` objects) -> ``(callers, object entries)``.

    No longer used to discount violations (only agent-added lines count, see
    :func:`probe_violations`); kept for the baseline report and the canary.
    """
    data = json.loads(Path(path).read_text())
    entries = data["writers"] if isinstance(data, dict) else data
    callers: set[str] = set()
    writers: list[dict] = []
    for e in entries:
        if isinstance(e, str):
            callers.add(e)
        else:
            callers.add(e["caller"])
            writers.append(e)
    return callers, writers


def probe_violations(events: list[dict], diff_text: str, cond: str) -> list[Violation]:
    """Violations from probe events, deduplicated by ``(kind, caller)``.

    ``raw_write`` counts only when its caller ``src/<file>:<line>`` falls on a line
    the agent *added* in ``diff_text`` (a non-test loot-core source file). Writers
    already on base -- including base writers whose line number shifted because the
    agent edited above them, and writers the agent merely calls into -- are never
    attributed to the agent. Unknown callers cannot be attributed and do not count.

    ``non_integer_money`` always counts: none occur on the untouched base
    (``aa checker baseline``), so any one is caused by the agent's change.

    Violation files are reported repo-relative (``packages/loot-core/src/...``), like
    the static checks.
    """
    _check_cond(cond)
    added = added_source_lines(diff_text)
    seen: set[tuple[str, str]] = set()
    out: list[Violation] = []
    for e in events:
        kind = e.get("kind")
        caller = e.get("caller", "unknown")
        if (kind, caller) in seen:
            continue
        file, line = _split_caller(caller)
        repo_file = LOOT_PREFIX + file if file.startswith("src/") else file
        if kind == "raw_write":
            hit = added.get(file, {}).get(line)
            if hit is None:
                continue
            detail = f"{e.get('table')}: {e.get('sql', '')}"
            visible = _visible(kind, repo_file, hit[0], hit[1], cond)
        elif kind == "non_integer_money":
            detail = f"{e.get('table')}.{e.get('column')}={e.get('value')}"
            visible = False
        else:
            continue
        seen.add((kind, caller))
        out.append(Violation(kind, repo_file, line, detail, visible))
    return out


def read_probe_events(path: Path) -> list[dict]:
    """Parse the probe's JSONL output; a missing file means no events."""
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
