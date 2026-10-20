"""Hidden tests on A+ (Javier's decision, 2026-10-05).

A+ moves the CRDT write API of ``#server/db`` into ``#server/db/write``
(``docs/a-plus-design.md`` section 5, item 10). Actual's own 33 test files that
used a moved function were repointed mechanically when A+ was built; a hidden
test (the commit's test file as it exists at base) gets the same rewrite on AP
and APL, and none on A and AL:

1. ``<db>.<moved>`` (``<db>`` = a namespace import of ``#server/db``, or of
   ``./db`` / ``./index`` resolving to it) -> ``dbWrite.<moved>``, also as the
   object of ``vi.spyOn(<db>, '<moved>')``; moved names in a named import
   ``import { ... } from '#server/db'`` move to an import from ``#server/db/write``;
2. ``import * as dbWrite from '#server/db/write';`` is added in its
   alphabetical place among the ``#`` imports (as ``import/order`` sorts it),
   and the ``#server/db`` import is dropped when nothing else uses it;
3. an automock ``vi.mock('#server/db')`` gets a companion
   ``vi.mock('#server/db/write')`` plus ``vi.hoisted(() => vi.resetModules())``:
   the vitest setup file has already loaded the domain layer bound to the real
   db modules, so without the reset, writes reached through the domain are not
   the mocked ones.

The moved names are the exports of A+'s ``db/write.ts`` (read from the AP
variant tree, or from ``aplus.patch`` when the variant is not built).
A ``vi.mock('#server/db', factory)`` is left alone: whether the factory still
covers what the test needs is decided by the per-task sanity check
(``hidden_tests_not_portable``).
"""
from __future__ import annotations

import functools
import posixpath
import re
from collections.abc import Iterable
from pathlib import Path

from aa import config

REWRITTEN_CONDS = frozenset({"AP", "APL"})
DB_SPEC = "#server/db"
WRITE_SPEC = "#server/db/write"
WRITE_ALIAS = "dbWrite"
DB_DIR = f"{config.LOOT}/src/server/db"
WRITE_TS = f"{DB_DIR}/write.ts"
RESET_COMMENT = (
    "// The domain layer (#server/domain) is already loaded by the vitest setup file,\n"
    "// bound to the real db modules. Reset the registry so the code under test, and\n"
    "// the domain commands it calls, load fresh with the mocks below.\n"
)
RESET_LINE = "vi.hoisted(() => vi.resetModules());\n"

_EXPORT_RE = re.compile(
    r"^export\s+(?:default\s+)?(?:async\s+)?(?:function\s*\*?|const|let|var|class)\s+([A-Za-z_$][\w$]*)",
    re.M)
_EXPORT_LIST_RE = re.compile(r"^export\s*\{([^}]*)\}", re.M)


# --------------------------------------------------------------------------- moved names

def exported_names(ts_source: str) -> frozenset[str]:
    """Value exports of a TS module (functions, consts, classes, ``export { a as b }``)."""
    names = set(_EXPORT_RE.findall(ts_source))
    for body in _EXPORT_LIST_RE.findall(ts_source):
        for part in body.split(","):
            part = part.strip()
            if part and not part.startswith("type "):
                names.add(part.split(" as ")[-1].strip())
    return frozenset(names)


def _write_ts_from_patch(patch_text: str) -> str | None:
    """Post-image of ``db/write.ts`` from a patch that creates it."""
    out: list[str] = []
    inside = False
    for ln in patch_text.splitlines():
        if ln.startswith("diff --git "):
            if inside:
                break
            inside = ln.endswith(f" b/{WRITE_TS}")
            continue
        if inside and ln.startswith("+") and not ln.startswith("+++"):
            out.append(ln[1:])
    return "\n".join(out) + "\n" if out else None


@functools.lru_cache(maxsize=None)
def moved_names(variants: Path | None = None, patches: Path | None = None) -> frozenset[str]:
    """Names exported by A+'s ``db/write.ts``: the AP (or APL) variant's file, else
    the file created by ``aplus.patch``."""
    variants = variants or config.WORK / "variants"
    for cond in ("AP", "APL"):
        p = variants / cond / WRITE_TS
        if p.exists():
            return exported_names(p.read_text(encoding="utf-8"))
    patch = (patches or config.PATCHES) / "aplus.patch"
    src = _write_ts_from_patch(patch.read_text(encoding="utf-8", errors="replace")) \
        if patch.exists() else None
    if not src:
        raise FileNotFoundError(f"no db/write.ts in {variants}/AP, {variants}/APL or {patch}")
    return exported_names(src)


# --------------------------------------------------------------------------- imports

_IMPORT_START = re.compile(r"^import\b")
_FROM_SPEC = re.compile(r"""\bfrom\s+['"]([^'"]+)['"]""")
_BARE_SPEC = re.compile(r"""^import\s+['"]([^'"]+)['"]""")


def _imports(lines: list[str]) -> list[tuple[int, int, str, str]]:
    """Top-level import statements as (first line, last line, specifier, text)."""
    out = []
    i = 0
    while i < len(lines):
        if _IMPORT_START.match(lines[i]):
            j = i
            text = lines[i]
            while not (_FROM_SPEC.search(text) or _BARE_SPEC.match(text)) and j + 1 < len(lines):
                j += 1
                text += lines[j]
            m = _FROM_SPEC.search(text) or _BARE_SPEC.match(text)
            out.append((i, j, m.group(1) if m else "", text))
            i = j + 1
        else:
            i += 1
    return out


def _is_db_spec(spec: str, path: str | None) -> bool:
    if spec in (DB_SPEC, f"{DB_SPEC}/index"):
        return True
    if not spec.startswith("."):
        return False
    if path:
        target = posixpath.normpath(posixpath.join(posixpath.dirname(path), spec))
        return target in (DB_DIR, f"{DB_DIR}/index")
    return bool(re.fullmatch(r"(?:\.\.?/)+(?:[\w.-]+/)*db(?:/index)?", spec))


def _insert_at(lines: list[str], imports: list[tuple[int, int, str, str]]) -> tuple[int, bool]:
    """Line index where the dbWrite import goes, and whether it opens its own group."""
    internal = [imp for imp in imports if imp[2].startswith("#")]
    if internal:
        for start, _end, spec, _t in internal:
            if spec.lower() > WRITE_SPEC:
                i = start
                while i > 0 and lines[i - 1].lstrip().startswith("//"):
                    i -= 1  # keep leading comments (e.g. // @ts-strict-ignore) below us
                return i, False
        return internal[-1][1] + 1, False
    external = [imp for imp in imports if not imp[2].startswith(".")]
    if external:
        return external[-1][1] + 1, True
    return 0, True


# --------------------------------------------------------------------------- rewrite

def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"(^|[ \t;{}(),])//[^\n]*", r"\1", text, flags=re.M)


def _uses(alias: str, text: str) -> bool:
    """``alias`` referenced in code (not in a comment)."""
    text = _strip_comments(text)
    return re.search(rf"(?<![\w$.]){re.escape(alias)}(?![\w$])", text) is not None


def rewrite_for_condition(test_source: str, cond: str, path: str | None = None,
                          names: Iterable[str] | None = None) -> str:
    """The hidden test as it must run on ``cond``: identity on A/AL, the A+ rewrite on
    AP/APL. ``path`` (repo-relative) resolves relative imports of the db module."""
    if cond not in REWRITTEN_CONDS:
        return test_source
    moved = frozenset(names) if names is not None else moved_names()
    if not moved:
        return test_source
    alt = "|".join(sorted(map(re.escape, moved), key=len, reverse=True))
    lines = test_source.splitlines(keepends=True)
    imports = _imports(lines)

    db_aliases: list[tuple[int, int, str]] = []
    named_moved: list[str] = []
    named_edits: dict[int, tuple[int, str | None]] = {}  # start -> (end, new text or None)
    db_specs = {DB_SPEC}
    for start, end, spec, text in imports:
        if not _is_db_spec(spec, path):
            continue
        db_specs.add(spec)
        m = re.match(r"import\s+\*\s+as\s+([\w$]+)\s+from", text)
        if m:
            db_aliases.append((start, end, m.group(1)))
            continue
        m = re.match(r"import\s+(?!type\b)\{([^}]*)\}\s*from", text, re.S)
        if not m:
            continue
        specs = [s.strip() for s in m.group(1).split(",") if s.strip()]
        keep = [s for s in specs if s.startswith("type ") or s.split(" as ")[0].strip() not in moved]
        moving = [s for s in specs if s not in keep]
        if moving:
            named_moved += moving
            new = None if not keep else \
                f"import {{ {', '.join(keep)} }} from '{spec}';\n"
            named_edits[start] = (end, new)

    body = test_source
    alias_changed = False
    for _s, _e, alias in db_aliases:
        a = re.escape(alias)
        body, n1 = re.subn(rf"(?<![\w$.]){a}\.({alt})(?![\w$])", rf"{WRITE_ALIAS}.\1", body)
        body, n2 = re.subn(rf"(\bvi\.spyOn\(\s*){a}(\s*,\s*['\"](?:{alt})['\"])",
                           rf"\1{WRITE_ALIAS}\2", body)
        alias_changed |= bool(n1 or n2)
    if not (alias_changed or named_moved):
        return test_source

    lines = body.splitlines(keepends=True)
    imports = _imports(lines)  # same line numbers: substitutions never add lines
    import_lines = {i for s, e, _sp, _t in imports for i in range(s, e + 1)}
    rest = "".join(ln for i, ln in enumerate(lines) if i not in import_lines)

    drop: set[int] = set()
    for start, end, alias in db_aliases:
        if not _uses(alias, rest):
            drop.update(range(start, end + 1))
    replace: dict[int, str] = {}
    for start, (end, new) in named_edits.items():
        drop.update(range(start + 1, end + 1))
        if new is None:
            drop.add(start)
        else:
            replace[start] = new

    new_imports: list[str] = []
    has_write_ns = any(sp == WRITE_SPEC and re.match(rf"import\s+\*\s+as\s+{WRITE_ALIAS}\b", t)
                       for _s, _e, sp, t in imports)
    if alias_changed and not has_write_ns:
        new_imports.append(f"import * as {WRITE_ALIAS} from '{WRITE_SPEC}';\n")
    if named_moved:
        new_imports.append(f"import {{ {', '.join(named_moved)} }} from '{WRITE_SPEC}';\n")

    at, own_group = _insert_at(lines, [imp for imp in imports if imp[0] not in drop])
    block = new_imports
    if new_imports and own_group:
        block = new_imports + ["\n"] if at == 0 else ["\n"] + new_imports
    kept = [(i, replace.get(i, ln)) for i, ln in enumerate(lines) if i not in drop]
    out = [ln for i, ln in kept if i < at] + block + [ln for i, ln in kept if i >= at]
    text = re.sub(r"\n{3,}", "\n\n", "".join(out))
    return _add_write_mock(text, db_specs)


def _add_write_mock(text: str, db_specs: set[str]) -> str:
    """Companion automock + module-registry reset for ``vi.mock('<db>')`` automocks."""
    if re.search(rf"""vi\.mock\(\s*['"]{re.escape(WRITE_SPEC)}['"]""", text):
        return text
    specs = "|".join(re.escape(s) for s in sorted(db_specs))
    m = re.search(rf"""^vi\.mock\(\s*['"](?:{specs})['"]\s*\);[ \t]*\n""", text, re.M)
    if not m:
        return text
    reset = "" if "vi.resetModules()" in text[:m.start()] else RESET_COMMENT + RESET_LINE
    return (text[:m.start()] + reset + m.group(0) + f"vi.mock('{WRITE_SPEC}');\n"
            + text[m.end():])


def rewrite_files(sources: dict[str, str], cond: str,
                  names: Iterable[str] | None = None) -> dict[str, str]:
    """``rewrite_for_condition`` over {repo-relative path: source}."""
    names = frozenset(names) if names is not None else None
    return {p: rewrite_for_condition(s, cond, p, names) for p, s in sources.items()}
