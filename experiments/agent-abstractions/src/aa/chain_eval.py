"""Chain evaluator (study 2, plan Task 4): one ``result.json`` per chain step and one
``chain_result.json`` per chain.

Inputs
------
Task side (``tasks2/<zone>/``; shape loaded by :mod:`aa.chains`, plan Task 2):

- ``chain.json``: ``zone``; ``steps`` (``["T1", ...]`` or ``[{"id": "T1", "kind":
  "rule", "consumers": [...]}, ...]``); ``zone_files`` (list, or ``{"R": [...], "F":
  [...]}``; repo-relative, or relative to ``packages/loot-core/src`` as in the spec's
  zone table); optional ``t2_reuse`` (``{"helpers": {"F": [names], "R": [names]},
  "markers": [regex, ...]}``); optional per-step ``depends_on_f_comment_fact``
  (bool, copied into each result). Step kinds default to T1/T3 ``rule``, T2
  ``consumer``, T4 ``build``.
- ``T<k>/statement.md``, ``T<k>/hidden/<repo-relative test path>`` (every file under
  ``hidden/`` is a hidden test of that step), ``T<k>/consumers.json``
  (``{test name: consumer id}``; a test name is the vitest ``fullName`` or
  ``<file>::<fullName>``, file relative to ``packages/loot-core`` or to the repo).

Run side (``runs2/<agent>/<cond>/<zone>/<chain>/T<k>/``, :mod:`aa.chain_runner`):
``agent.json`` (``status``, ``usage``, ``wall_s``, ``carry``), ``start.json`` (the
carry plan: ``from`` = ``image`` or ``T<j>/tree.tar``, ``patches`` = ``T<i>/diff.patch``
in order), ``start_tree`` / ``post_tree`` (git tree ids recorded by the runner),
``diff.patch`` + ``diff_ok`` (the diff reproduces the agent's tree) or ``tree.tar``
(the tree as the agent left it, when the diff does not), ``transcript.jsonl``.

Per step, in a fresh container of ``aa-actual:<cond>`` (network off; the chain dir
mounted read-only at /chain)
--------------------------------------------------------------------------------
1. commit the image tree as ``evalbase`` (the runner's ``image`` commit);
2. rebuild the step's start tree exactly as the runner did (``tree.tar`` base, then
   the carried patches with ``git apply --3way``; failure -> ``eval_error=
   "pre_image"``); its tree id must equal the runner's ``start_tree`` (verified
   pre-image, ``tree_check.start``); dump it as ``pre_image.patch`` (vs the image);
   jscpd on the zone's source files plus the source files the chain's agents created
   under the zone files' directories (added vs the image) -> duplication before the
   step;
3. the agent's step: ``diff.patch`` (failure -> ``eval_error="diff_apply"``), or
   ``tree.tar`` when the runner had no verified diff; the tree id must equal the
   runner's ``post_tree`` (``tree_check.post``); dump ``post_tree.patch`` (vs the
   image: the chain's cumulative diff at that step) and ``step.patch`` (start ->
   post); jscpd again -> duplication after;
4. ``yarn lint`` / ``yarn tsgo -b`` on the tree exactly as the agent left it;
5. test infra (vitest configs, ``src/mocks``, ``src/server/tests``, every
   ``__mocks__``) restored from ``evalbase``, i.e. the pristine image, never from a
   previous agent's tree (Review Focus 2); every hidden test of steps 1..k is
   removed and replaced by the staged task copy, so an agent that edited or created
   a file at a hidden path changes nothing;
6. seed + one clean vitest pass over the hidden tests of steps 1..k (no probe:
   study 2 has no invariant checker). An unparseable tree still runs every file; a
   file that fails to load counts as failing every test in it (Review Focus 1).

On the host: ``correct`` (step k's tests), per-consumer coverage, ``missed_copy``
(spec §5.2, rule steps only, over every consumer of the step),
``missed_copy_preexisting`` (the same, restricted to the consumers listed at T1 of the
zone's ``chain.json``: the primary measure, since a consumer the agent added at T2 can
fail at T3 because T2 failed, not because a copy was missed), ``t2_consumer_ok`` (the
consumers not listed at T1, i.e. added at T2, all updated on this step),
``carried_defects`` (steps 1..k-1's tests failing on
this tree), ``new_carried_defects`` (of those, the ones that passed in the previous
step's evaluation), efficiency fields as study 1, ``t2_reuses_logic`` (static, on the
consumer step), jscpd duplication restricted to the zone source files and the source
files agents created in the zone's directories (Review Focus 4).

Per chain: ``chain_result.json`` with duplication ``T0`` (start of the chain) ..
``T4``, the cumulative diff (``cumulative.patch``), cost growth and per-step
summaries. Design-review packets with verified pre-images:
:func:`export_review_packets`.

Study 3 (``runs3/``: arms R, RG, RL, RC; plan Task 5): the same evaluation plus the
step's own ``start`` commit for ``yarn lint``, the ratchet, the static T2 / rule-step
labels, lint runs, gaming flags and rule citations, and RC's T0 step; see
:mod:`aa.chain_eval3`.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aa import chains as chain_tasks
from aa import config
from aa.checker import SEED_CONFIG_DST, SEED_CONFIG_SRC, SEED_DST, SEED_SRC, vitest_clean_cmd
from aa.evaluate import (CLEAN_DONE, EVALUATED, HIDDEN_SRC, MOCKS_DIR, STEP_TIMEOUT_S,
                         TEST_INFRA_DIRS, TEST_INFRA_FILES, _read_int, _read_text, _write_json,
                         contamination, diff_files, diff_stats, docker_execute, extract_trace,
                         stage_hidden_tests, touches_test_infra)
from aa.suite import SuiteResult, parse_vitest_json

RUNS2 = config.ROOT / os.environ.get("AA_RUNS2_DIR", "runs2")
TASKS2 = chain_tasks.TASKS2
CHAIN_FILE = "chain.json"
CONSUMERS_FILE = "consumers.json"
STATEMENT = "statement.md"
# eval outputs (under <step>/eval/)
PRE_IMAGE = "pre_image.patch"  # the step's start tree vs the image
POST_TREE = "post_tree.patch"  # the agent's tree after the step vs the image
STEP_PATCH = "step.patch"  # start tree -> agent's tree (what the design review reads)
DIFF_APPLIED = "diff_applied"
PACKET_PRE_IMAGE = "pre-image.patch"
CUMULATIVE = "cumulative.patch"
CHAIN_RESULT = "chain_result.json"
EVAL_DIR = "eval"
CONTAINER_LOOT = f"/work/actual/{config.LOOT}"
LOOT_SRC = f"{config.LOOT}/src"
# lint, typecheck, two jscpd passes, one vitest pass + slack
HOST_TIMEOUT_S = 6 * STEP_TIMEOUT_S
JSCPD_TIMEOUT_S = 300
# jscpd is pinned in the R/F images (plan Task 1). Fixed detection settings, the same
# for every tree: jscpd's default token threshold, JSON report only.
JSCPD_ARGS = ("jscpd", "--min-tokens", "50", "--reporters", "json", "--silent")
DEFAULT_KINDS = {"T1": "rule", "T2": "consumer", "T3": "rule", "T4": "build"}
STEP_DIR = re.compile(r"^T(\d+)$")
EVAL_ERRORS_NOTHING_RAN = ("evalbase", "pre_image", "diff_apply", "post_tree")
T2_LABELS = {"F": "helper", "R": "copy"}

Executor = Callable[[list[str], int], int]


# --------------------------------------------------------------------------- task side

@dataclass
class Step:
    id: str
    index: int
    kind: str
    dir: Path
    hidden: list[str]  # repo-relative hidden test paths
    tests: dict[str, str]  # test name -> consumer id
    consumers: list[str]
    # chain.json ``depends_on_f_comment_fact`` (spec amendment 2026-10-08, item 10):
    # the step's hidden tests depend on a fact stated only in F's doc comments.
    # None when chain.json does not tag the step.
    depends_on_f_comment_fact: bool | None = None


@dataclass
class Chain:
    zone: str
    dir: Path
    steps: list[Step]
    zone_files: dict[str, list[str]] | list[str]
    t2_reuse: dict[str, Any] = field(default_factory=dict)
    # {superseding step id: {earlier step id: [test names]}}: earlier tests a later
    # step deliberately contradicts (chain.json ``supersedes`` on the later step).
    supersedes: dict[str, dict[str, list[str]]] = field(default_factory=dict)

    def superseded(self, at: "Step", prev: "Step") -> frozenset[str]:
        """Tests of ``prev`` that steps up to ``at`` supersede: from ``at`` on they are
        expected to fail and are neither carried defects nor part of prev's
        correctness on this tree."""
        out: set[str] = set()
        for s in self.steps[prev.index:at.index]:
            out |= set(self.supersedes.get(s.id, {}).get(prev.id, ()))
        return frozenset(out)

    def step(self, step_id: str) -> Step:
        for s in self.steps:
            if s.id == step_id:
                return s
        raise KeyError(f"{self.zone}: no step {step_id}")

    def files_for(self, cond: str) -> list[str]:
        files = self.zone_files.get(zone_cond(cond, self.zone_files), []) \
            if isinstance(self.zone_files, dict) else self.zone_files
        return zone_source_files(files)

    def dirs_for(self, cond: str) -> list[str]:
        """The directories of the zone's source files: new source files an agent
        creates there are scanned by jscpd too (a helper or a copy moved to a new
        file still counts)."""
        return sorted({f.rsplit("/", 1)[0] for f in self.files_for(cond) if "/" in f})

    @property
    def preexisting_consumers(self) -> list[str]:
        """The consumers listed at T1 (the first step) of chain.json: the ones that
        exist before the chain. Consumers added later (the T2 one) are not."""
        return list(self.steps[0].consumers) if self.steps else []


def zone_cond(cond: str, by_cond: dict) -> str:
    """The condition whose per-condition entry (zone files, T2 helpers) applies: the
    study-3 arms are R plus one lever, so RG/RL/RC read R's when they have none."""
    if cond in by_cond:
        return cond
    return "R" if cond in config.CONDITIONS3 else cond


def _repo_path(p: str) -> str:
    """Zone paths may be repo-relative or relative to packages/loot-core/src (spec table)."""
    p = p.strip()
    if p.startswith("./"):
        p = p[2:]
    return p if p.startswith("packages/") else f"{LOOT_SRC}/{p}"


def is_source_file(p: str) -> bool:
    """A non-test TypeScript/JavaScript source file (Review Focus 4: jscpd never sees
    tests, mocks, test helpers or node_modules)."""
    parts = p.split("/")
    if "node_modules" in parts or MOCKS_DIR in parts or "__tests__" in parts:
        return False
    if p in TEST_INFRA_FILES or any(p.startswith(d + "/") for d in TEST_INFRA_DIRS):
        return False
    if re.search(r"\.(test|spec)\.[cm]?[jt]sx?$", p) or ".d.ts" in p:
        return False
    return bool(re.search(r"\.[cm]?[jt]sx?$", p))


def zone_source_files(files: Iterable[str]) -> list[str]:
    out: list[str] = []
    for f in files:
        rp = _repo_path(f)
        if is_source_file(rp) and rp not in out:
            out.append(rp)
    return out


def load_chain(zone: str, tasks_root: Path | None = None) -> Chain:
    """``tasks2/<zone>/`` as the evaluator needs it: :func:`aa.chains.load_chain` (ids,
    kinds, consumers, statements) plus hidden tests, ``consumers.json``, zone files
    and the T2 reuse config. Raises ValueError on an inconsistent chain."""
    base = chain_tasks.load_chain(zone, tasks_root)
    raw = json.loads((base.root / CHAIN_FILE).read_text())
    steps: list[Step] = []
    seen_hidden: dict[str, str] = {}
    for i, bs in enumerate(base.steps, start=1):
        sid, sdir = bs.id, base.root / bs.id
        hdir = sdir / "hidden"
        hidden = sorted(p.relative_to(hdir).as_posix() for p in hdir.rglob("*") if p.is_file()) \
            if hdir.is_dir() else []
        if not hidden:
            raise ValueError(f"{zone}/{sid}: no hidden tests")
        for h in hidden:
            if not h.startswith(config.LOOT + "/"):
                raise ValueError(f"{sid}: hidden test outside {config.LOOT}: {h}")
            if is_source_file(h) or touches_test_infra(f"diff --git a/{h} b/{h}\n"):
                raise ValueError(f"{sid}: hidden path is not a plain test file: {h}")
            if h in seen_hidden:
                raise ValueError(f"{sid}: hidden test {h} already belongs to {seen_hidden[h]}")
            seen_hidden[h] = sid
        tests = json.loads((sdir / CONSUMERS_FILE).read_text())
        if not isinstance(tests, dict) or not tests:
            raise ValueError(f"{sid}: {CONSUMERS_FILE} must map test names to consumer ids")
        consumers = list(bs.consumers or dict.fromkeys(tests.values()))
        unknown = sorted(set(tests.values()) - set(consumers))
        untested = [c for c in consumers if c not in set(tests.values())]
        if unknown or untested:
            raise ValueError(f"{sid}: consumers without tests {untested}, "
                             f"tests mapped to unknown consumers {unknown}")
        info = (raw.get("steps") or [])[i - 1]
        fact = info.get("depends_on_f_comment_fact") if isinstance(info, dict) else None
        if fact is not None and not isinstance(fact, bool):
            raise ValueError(f"{sid}: depends_on_f_comment_fact must be true/false")
        steps.append(Step(id=sid, index=i, kind=bs.kind or DEFAULT_KINDS.get(sid, "other"),
                          dir=sdir, hidden=hidden, tests=dict(tests), consumers=consumers,
                          depends_on_f_comment_fact=fact))
    zf = raw.get("zone_files")
    if not zf:
        raise ValueError(f"{zone}: chain.json has no zone_files")
    supersedes: dict[str, dict[str, list[str]]] = {}
    for i, rs in enumerate(raw.get("steps") or [], start=1):
        sup = rs.get("supersedes") if isinstance(rs, dict) else None
        if not sup:
            continue
        for prev_id, names in sup.items():
            prev = next((p for p in steps[:i - 1] if p.id == prev_id), None)
            if prev is None:
                raise ValueError(f"T{i}: supersedes {prev_id!r}, not an earlier step")
            unknown = [n for n in names if n not in prev.tests]
            if unknown:
                raise ValueError(f"T{i}: supersedes unknown {prev_id} tests {unknown[:3]}")
        supersedes[f"T{i}"] = {k: list(v) for k, v in sup.items()}
    return Chain(zone=base.zone, dir=base.root, steps=steps, zone_files=zf,
                 t2_reuse=raw.get("t2_reuse") or {}, supersedes=supersedes)


# --------------------------------------------------------------------------- container

def _ere_path(p: str) -> str:
    return re.sub(r"([.+?*()\[\]{}|^$\\])", r"\\\1", p)


# grep -E filter mirroring is_source_file (the host re-checks every listed file).
NOT_SOURCE_ERE = "|".join([
    r"(^|/)(node_modules|__tests__|" + _ere_path(MOCKS_DIR) + r")/",
    r"\.(test|spec)\.[cm]?[jt]sx?$",
    r"\.d\.ts",
    *(f"^{_ere_path(d)}/" for d in TEST_INFRA_DIRS),
    *(f"^{_ere_path(f)}$" for f in TEST_INFRA_FILES),
])


def _jscpd_lines(files: list[str], out_name: str, dirs: list[str] = ()) -> list[str]:
    """jscpd over the zone files that exist in the current tree (cwd /work/actual) plus
    the source files under ``dirs`` that the image does not have (added by an agent:
    staged at the pre-image, untracked after the step). The list given to jscpd lands in
    /out/<out_name>_files, the rc in /out/<out_name>_rc (127 = jscpd missing)."""
    q = shlex.quote
    args = " ".join(q(a) for a in JSCPD_ARGS)
    flist = " ".join(q(f) for f in files)
    lines = [f'files=(); for f in {flist}; do [ -f "$f" ] && files+=("$f"); done']
    if dirs:
        dl = " ".join(q(d) for d in dirs)
        lines.append(
            "while IFS= read -r f; do [ -f \"$f\" ] || continue; dup=0; "
            'for g in ${files[@]+"${files[@]}"}; do [ "$g" = "$f" ] && dup=1; done; '
            '[ $dup = 0 ] && files+=("$f"); '
            f"done < <( {{ git diff --cached --no-renames --name-only --diff-filter=A HEAD "
            f"-- {dl}; git ls-files -o --exclude-standard -- {dl}; }} 2>/dev/null "
            f"| grep -E '\\.[cm]?[jt]sx?$' | grep -vE {q(NOT_SOURCE_ERE)} | sort -u )")
    return lines + [
        f'printf "%s\\n" ${{files[@]+"${{files[@]}}"}} > /out/{out_name}_files',
        f'if [ ${{#files[@]}} -gt 0 ]; then timeout {JSCPD_TIMEOUT_S} {args} '
        f'--output /out/{out_name} "${{files[@]}}" > /out/{out_name}.log 2>&1; '
        f'echo $? > /out/{out_name}_rc; else echo 0 > /out/{out_name}_rc; fi',
    ]


def carry_plan(step_dir: Path, meta: dict, index: int) -> dict:
    """The runner's carry plan for this step (``start.json``, else ``agent.json``'s
    ``carry``); without either, step 1 starts from the image, except RC's T1, which
    starts from T0's tree (an error then). Paths are relative to the chain dir."""
    plan: Any = None
    try:
        plan = json.loads((step_dir / "start.json").read_text())
    except (OSError, ValueError):
        plan = meta.get("carry")
    if not isinstance(plan, dict):
        if index == 1 and not (meta.get("cond") == "RC" and meta.get("step") != "T0"):
            return {"from": "image", "patches": []}
        raise ValueError("no carry plan (start.json / agent.json carry)")
    src, patches = plan.get("from") or "image", list(plan.get("patches") or [])
    for rel in ([] if src == "image" else [src]) + patches:
        if not re.fullmatch(r"T\d+/(diff\.patch|tree\.tar)", rel):
            raise ValueError(f"unexpected carry path {rel!r}")
    return {"from": src, "patches": patches}


def chain_eval_script(step_id: str, plan: dict, *, agent_tree: str, hidden_tests: list[str],
                      zone_files: list[str], static_checks: bool = True,
                      zone_dirs: list[str] | None = None, study3: bool = False,
                      t0: bool = False, tests: bool = True,
                      scope_tests: Iterable[str] = (), behaviour_only: bool = False) -> str:
    """Bash run inside the eval container. Mounts: /chain (ro, the chain dir: every
    step's diff.patch / tree.tar), /checker (ro, substrate/checker), /out (rw; staged
    hidden tests in /out/hidden_src). ``plan``: :func:`carry_plan`. ``agent_tree``:
    ``diff`` (apply ``<step>/diff.patch``) or ``tar`` (``<step>/tree.tar``, the
    runner's fallback when its diff did not reproduce the tree). ``hidden_tests`` =
    every hidden test of steps 1..k. ``zone_dirs``: where agent-created source files
    are scanned by jscpd too (:meth:`Chain.dirs_for`); default the zone files' dirs.

    Study 3 (:mod:`aa.chain_eval3`): ``study3`` gives the start tree a root commit
    ``start`` in a separate git dir (as the runner makes it) that ``yarn lint`` sees,
    scans the ratchet on the start and post trees and dumps the post tree's zone files;
    ``t0`` (RC's T0, needs /probe) replaces the static checks and the vitest pass by
    ``aa chain t0-reference``'s checks (``hidden_tests`` = the zone's T0 tests, may be
    empty); ``tests=False`` stops after the static checks (no vitest, no probe).

    ``scope_tests`` (study-3 pilot, blocking item 9): the zone's T0 inconsistency test
    files whose tests this step must still pass, staged (from /out/hidden_src) after the
    hidden tests ran and run on their own (/out/scope_tests.json, /out/scope_rc).
    ``behaviour_only``: only rebuild the post tree and run ``scope_tests`` (the
    behaviour check re-derived on an evaluated step: no jscpd, ratchet, lint, typecheck
    or hidden tests)."""
    from aa import chain_eval3 as ce3
    study3 = study3 or t0
    scope_tests = list(scope_tests)
    full = not behaviour_only
    q = shlex.quote
    if zone_dirs is None:
        zone_dirs = sorted({f.rsplit("/", 1)[0] for f in zone_files if "/" in f})
    rel_hidden = [t[len(config.LOOT) + 1:] for t in hidden_tests]
    clean = " ".join(q(a) for a in vitest_clean_cmd("/out/report.json", rel_hidden))
    infra = " ".join(q(p) for p in TEST_INFRA_FILES + TEST_INFRA_DIRS)
    loot = q(config.LOOT)
    commit = "git -c user.name=aa -c user.email=aa@local -c commit.gpgsign=false commit -q --no-verify"
    untar = 'git ls-files -z | xargs -0 rm -f; tar -xf {} && git add -A'
    lines = [
        "set -u",
        "cd /work/actual",
        # the image tree (variant + install changes) is the origin of every chain
        f"{{ git add -A && {commit} --allow-empty -m evalbase; }} > /out/apply.log 2>&1 "
        "|| { echo evalbase > /out/eval_error; exit 0; }",
    ]
    if plan["from"] != "image":
        lines.append(f"{{ git add -A && {untar.format('/chain/' + q(plan['from']))}; }} "
                     "2>> /out/apply.log || { echo pre_image > /out/eval_error; exit 0; }")
    for p in plan["patches"]:
        lines.append(f"git apply --3way --allow-empty --whitespace=nowarn /chain/{q(p)} "
                     "2>> /out/apply.log || { echo pre_image > /out/eval_error; exit 0; }")
    lines += [
        "{ git add -A && git write-tree > /out/start_tree "
        f"&& git diff --cached --binary HEAD > /out/{PRE_IMAGE}; }} 2>> /out/apply.log "
        "|| { echo pre_image > /out/eval_error; exit 0; }",
        *(ce3.start_commit_lines() if study3 and full else ()),
        *(_jscpd_lines(zone_files, "jscpd_pre", zone_dirs) if full else ()),
        *(ce3.ratchet_scan_lines("start") if study3 and full else ()),
    ]
    sd = f"/chain/{q(step_id)}"
    if agent_tree == "tar":
        lines.append(f"{{ {untar.format(sd + '/tree.tar')}; }} 2>> /out/apply.log "
                     "|| { echo diff_apply > /out/eval_error; exit 0; }")
    else:
        lines.append(f"if [ -s {sd}/diff.patch ]; then "
                     f"git apply --allow-empty --whitespace=nowarn {sd}/diff.patch "
                     "2>> /out/apply.log || { echo diff_apply > /out/eval_error; exit 0; }; fi")
    lines += [
        f"echo done > /out/{DIFF_APPLIED}",
        "{ git add -A && git write-tree > /out/post_tree "
        f"&& git diff --cached --binary HEAD > /out/{POST_TREE} "
        f'&& git diff --binary "$(cat /out/start_tree)" "$(cat /out/post_tree)" > /out/{STEP_PATCH} '
        "&& git reset -q; } 2>> /out/apply.log || { echo post_tree > /out/eval_error; exit 0; }",
        *(_jscpd_lines(zone_files, "jscpd_post", zone_dirs) if full else ()),
    ]
    if study3 and full:
        lines += [*ce3.ratchet_scan_lines("post"), *ce3.zone_dump_lines()]
    if behaviour_only:
        lines.append(f"cd {config.LOOT}")
    elif t0:
        # aa chain t0-reference's checks, on the tree exactly as the agent left it
        lines += [*chain_tasks.t0_typecheck_lines(), *chain_tasks.t0_lint_lines(ce3.START_GIT_ENV),
                  ce3.related_files_line(), f"cd {config.LOOT}"]
    else:
        lint_env = f"{ce3.START_GIT_ENV} " if study3 else ""
        lines.append(f"cd {config.LOOT}")
        if static_checks:
            lines += [
                f"{lint_env}timeout {STEP_TIMEOUT_S} yarn lint > /out/lint.log 2>&1; "
                "echo $? > /out/lint_rc",
                f"timeout {STEP_TIMEOUT_S} yarn tsgo -b > /out/typecheck.log 2>&1; "
                "echo $? > /out/typecheck_rc",
            ]
    if not tests:
        return "\n".join(lines + ["echo done > /out/eval_done"]) + "\n"
    lines += [
        # test infra back to the pristine image (evalbase), never to any agent's tree
        f"( cd /work/actual && for p in {infra}; do "
        'rm -rf "$p"; if git cat-file -e HEAD:"$p" 2>/dev/null; then '
        'git checkout HEAD -- "$p" || exit 1; fi; done ) 2>> /out/apply.log '
        "|| { echo test_infra_restore > /out/eval_error; exit 0; }",
        f"( cd /work/actual && {{ git ls-tree -r --name-only HEAD -- {loot} "
        f"| sed -n 's#^\\(.*/{MOCKS_DIR}\\)/.*#\\1#p'; "
        f"find {loot} -name node_modules -prune -o -type d -name {MOCKS_DIR} -print; }} "
        '| sort -u | while IFS= read -r p; do rm -rf "$p" || exit 1; '
        'if git cat-file -e HEAD:"$p" 2>/dev/null; then git checkout HEAD -- "$p" || exit 1; fi; '
        "done ) 2>> /out/apply.log "
        "|| { echo test_infra_restore > /out/eval_error; exit 0; }",
    ]
    if t0:  # existing tests related to the touched sources, before any hidden test is in place
        lines.append(f"( cd /work/actual && {chain_tasks.t0_related_from_file_line('/out/related_files')} )")
        lines.append(f"( cd /work/actual && {chain_tasks.t0_related_retry_line()} )")
    if hidden_tests:  # hidden tests of steps 1..k: whatever is at those paths goes, the staged copy wins
        lines.append(
            f"( cd /work/actual && for t in {' '.join(q(t) for t in hidden_tests)}; do "
            f'rm -rf "$t" && mkdir -p "$(dirname "$t")" && cp /out/{HIDDEN_SRC}/"$t" "$t" '
            "|| exit 1; done ) 2>> /out/apply.log "
            "|| { echo hidden_restore > /out/eval_error; exit 0; }")
    lines.append(f"cp /checker/{SEED_SRC.name} {SEED_DST} && "
                 f"cp /checker/{SEED_CONFIG_SRC.name} {SEED_CONFIG_DST} "
                 "|| { echo seed_install > /out/eval_error; exit 0; }")
    if t0:
        lines += [*(chain_tasks.t0_tests_lines(hidden_tests) if hidden_tests else ()),
                  *chain_tasks.t0_probe_lines()]
    elif full:
        lines += [f"ENV=node timeout {STEP_TIMEOUT_S} {clean} > /out/vitest.log 2>&1; "
                  "echo $? > /out/vitest_rc"]
    if scope_tests and not t0:
        # the T0 inconsistency tests still in scope at this step, on their own
        rel_scope = [t[len(config.LOOT) + 1:] for t in scope_tests]
        scmd = " ".join(q(a) for a in vitest_clean_cmd("/out/scope_tests.json", rel_scope))
        lines += [
            f"( cd /work/actual && for t in {' '.join(q(t) for t in scope_tests)}; do "
            f'rm -rf "$t" && mkdir -p "$(dirname "$t")" && cp /out/{HIDDEN_SRC}/"$t" "$t" '
            "|| exit 1; done ) 2>> /out/apply.log || echo 1 > /out/scope_stage_error",
            f"[ -f /out/scope_stage_error ] || {{ ENV=node timeout {STEP_TIMEOUT_S} {scmd} "
            "> /out/scope_tests.log 2>&1; echo $? > /out/scope_rc; }",
            f"rm -f {' '.join(q(r) for r in rel_scope)}"]
    lines += [f"echo done > /out/{CLEAN_DONE}", "echo done > /out/eval_done"]
    return "\n".join(lines) + "\n"


def runs_root_tag(step_dir: Path) -> str:
    """Short hash of a step dir's runs root (``<root>/<agent>/<cond>/<zone>/<chain>/<step>``),
    so evaluator containers of runs3, runs3-pilot and a pytest tree never share a name."""
    root = Path(step_dir).resolve().parents[4]
    return hashlib.sha256(str(root).encode()).hexdigest()[:6]


def chain_eval_docker_argv(cond: str, step_dir: Path, out_dir: Path, script: str,
                           checker_dir: Path = SEED_SRC.parent,
                           extra: Iterable[str] = ()) -> list[str]:
    """``extra``: more ``docker run`` options (T0: the probe mount). The container name
    carries the runs root's tag (:func:`runs_root_tag`) and the step's path."""
    name = f"aa-eval2-{runs_root_tag(step_dir)}-" + "-".join(Path(step_dir).parts[-5:])
    return ["docker", "run", "--rm", "--name", re.sub(r"[^\w.-]", "_", name),
            "--network", "none", "--cpus", "2", "--memory", "6g",
            "-v", f"{step_dir.parent}:/chain:ro", "-v", f"{checker_dir}:/checker:ro",
            "-v", f"{out_dir}:/out", *extra, f"aa-actual:{cond}", "bash", "-c", script]


# --------------------------------------------------------------------------- outcomes

def _loot_rel(p: str) -> str:
    return p[len(config.LOOT) + 1:] if p.startswith(config.LOOT + "/") else p


def _report_ids(report: dict | None) -> SuiteResult | None:
    return None if report is None else parse_vitest_json(report, root=CONTAINER_LOOT)


def test_status(res: SuiteResult | None, step: Step) -> dict[str, bool]:
    """``{test name: passed}`` for every test in ``consumers.json``. A name passes when
    it matches >= 1 test in the report and every match passed; a file that failed to
    load or is missing from the report fails all of its names."""
    files = {_loot_rel(h) for h in step.hidden}
    out: dict[str, bool] = {}
    if res is None:
        return dict.fromkeys(step.tests, False)
    every = res.passed | res.failed | res.skipped
    for name in step.tests:
        if "::" in name:
            f, full = name.split("::", 1)
            matches = [t for t in every if t == f"{_loot_rel(f)}::{full}"]
        else:
            matches = [t for t in every if t.split("::", 1)[0] in files
                       and t.split("::", 1)[1] == name]
        out[name] = bool(matches) and all(t in res.passed for t in matches)
    return out


def consumer_coverage(status: dict[str, bool], step: Step) -> dict[str, bool]:
    """A consumer is updated when every one of its tests passes."""
    return {c: all(ok for n, ok in status.items() if step.tests[n] == c) for c in step.consumers}


def _is_named(tid: str, name: str, files: set[str]) -> bool:
    """Whether report id ``<file>::<fullName>`` is the consumers.json test ``name``."""
    if "::" in name:
        f, full = name.split("::", 1)
        return tid == f"{_loot_rel(f)}::{full}"
    return tid.split("::", 1)[0] in files and tid.split("::", 1)[1] == name


def step_outcome(report: dict | None, step: Step,
                 ignore: frozenset[str] = frozenset()) -> dict[str, Any]:
    """correct = every hidden file of the step in the report, >= 1 pass, no failure in
    those files, and every consumers.json test passing. ``ignore``: consumers.json
    names superseded by a later step (:meth:`Chain.superseded`), left out of all of it;
    a consumer whose every test is ignored is left out too."""
    res = _report_ids(report)
    files = {_loot_rel(h) for h in step.hidden}
    if ignore:
        tests = {n: c for n, c in step.tests.items() if n not in ignore}
        step = Step(id=step.id, index=step.index, kind=step.kind, dir=step.dir,
                    hidden=step.hidden, tests=tests,
                    consumers=[c for c in step.consumers if c in set(tests.values())])
    status = test_status(res, step)
    cov = consumer_coverage(status, step)
    if res is None:
        passed = failed = []
        missing = list(step.hidden)
    else:
        passed = sorted(t for t in res.passed if t.split("::", 1)[0] in files)
        failed = sorted(t for t in res.failed if t.split("::", 1)[0] in files
                        and not any(_is_named(t, n, files) for n in ignore))
        present = {t.split("::", 1)[0] for t in res.passed | res.failed | res.skipped}
        present |= {os.path.relpath(f.get("name", ""), CONTAINER_LOOT)
                    for f in (report or {}).get("testResults", [])}
        missing = [h for h in step.hidden if _loot_rel(h) not in present]
    correct = bool(passed) and not failed and not missing and all(status.values())
    return {"correct": correct, "tests": status, "consumers": cov,
            "consumers_passed": sum(cov.values()), "consumers_total": len(cov),
            "passed": len(passed), "failed": len(failed), "failed_tests": failed[:50],
            "missing_files": missing}


def missed_copy(kind: str, consumers_passed: int, consumers_total: int) -> bool | None:
    """Spec §5.2: on a rule step, at least one consumer updated and at least one not.
    Zero consumers updated is simply incorrect, not a missed copy. None off rule steps."""
    if kind != "rule":
        return None
    return 0 < consumers_passed < consumers_total


def split_coverage(coverage: dict[str, bool], step: Step,
                   preexisting: Iterable[str]) -> dict[str, Any]:
    """Coverage split into the consumers listed at T1 (pre-existing) and the rest (the
    consumer added at T2). ``missed_copy_preexisting`` is :func:`missed_copy` over the
    pre-existing ones only (None off rule steps, or when the step has none of them);
    ``t2_consumer_ok``: every added consumer updated (None when the step has none)."""
    pre = set(preexisting)
    mine = {c: ok for c, ok in coverage.items() if c in pre}
    added = {c: ok for c, ok in coverage.items() if c not in pre}
    passed = sum(mine.values())
    return {"consumers_preexisting_passed": passed,
            "consumers_preexisting_total": len(mine),
            "missed_copy_preexisting": missed_copy(step.kind, passed, len(mine))
            if mine else None,
            "t2_consumer_ok": all(added.values()) if added else None}


# --------------------------------------------------------------------------- jscpd

def parse_jscpd(report: dict | None, files: list[str]) -> dict[str, Any] | None:
    """Clones whose both ends are zone source files (Review Focus 4, defensive: jscpd
    is only given those files). ``duplicated_lines`` = sum of clone lengths;
    ``duplicated_lines_unique`` = distinct (file, line) pairs covered by any clone."""
    if report is None:
        return None
    allowed = set(files)
    clones = []
    covered: set[tuple[str, int]] = set()
    unresolved = 0
    for d in report.get("duplicates") or []:
        a, b = d.get("firstFile") or {}, d.get("secondFile") or {}
        na, nb = (_resolve_jscpd(_norm_jscpd(x.get("name", "")), allowed) for x in (a, b))
        if na is None or nb is None:
            unresolved += 1
            continue
        lines = int(d.get("lines") or 0)
        clones.append({"a": na, "a_start": a.get("start"), "a_end": a.get("end"),
                       "b": nb, "b_start": b.get("start"), "b_end": b.get("end"),
                       "lines": lines})
        for name, end in ((na, a), (nb, b)):
            s, e = end.get("start"), end.get("end")
            if isinstance(s, int) and isinstance(e, int):
                covered.update((name, ln) for ln in range(s, e + 1))
    return {"clones": len(clones), "duplicated_lines": sum(c["lines"] for c in clones),
            "duplicated_lines_unique": len(covered), "files": len(files),
            "unresolved": unresolved, "clone_list": clones[:200]}


def _resolve_jscpd(name: str, allowed: set[str]) -> str | None:
    """jscpd 5.4 reports a bare basename (``actions.ts``) for files given on the
    command line: map it to the one allowed path with that basename; ambiguous or
    unknown names -> None (dropped, counted as ``unresolved``)."""
    if name in allowed:
        return name
    if "/" in name:
        return None
    hits = [f for f in allowed if f.rsplit("/", 1)[-1] == name]
    return hits[0] if len(hits) == 1 else None


def _norm_jscpd(name: str) -> str:
    for pre in ("/work/actual/", "./"):
        if name.startswith(pre):
            name = name[len(pre):]
    return name


def jscpd_scanned(eval_dir: Path, which: str, files: list[str]) -> tuple[list[str], list[str]]:
    """(every file jscpd may report on, the agent-created ones among them): the zone
    files plus the source files the script listed in ``<which>_files`` beyond them."""
    listed = [ln.strip() for ln in _read_text(eval_dir / f"{which}_files").splitlines()
              if ln.strip()]
    added = [f for f in dict.fromkeys(listed) if f not in files and is_source_file(f)]
    return list(files) + added, added


def read_jscpd(eval_dir: Path, which: str, files: list[str]) -> dict[str, Any] | None:
    rc = _read_int(eval_dir / f"{which}_rc")
    if rc is None or rc != 0:
        return None
    allowed, added = jscpd_scanned(eval_dir, which, files)
    p = eval_dir / which / "jscpd-report.json"
    try:
        # no report: jscpd ran on zero existing files (or found nothing to report)
        out = parse_jscpd(json.loads(p.read_text()) if p.exists() else {"duplicates": []},
                          allowed)
    except json.JSONDecodeError:
        return None
    return {**out, "agent_files": added}


# --------------------------------------------------------------------------- T2 static check

def added_source_lines(diff_text: str) -> list[tuple[str, str]]:
    """(file, text) of every added line in a non-test source file of the diff."""
    out: list[tuple[str, str]] = []
    cur: str | None = None
    for ln in diff_text.splitlines():
        if ln.startswith("+++ "):
            p = ln[4:].split("\t")[0]
            p = p[2:] if p.startswith("b/") else p
            cur = p if p != "/dev/null" and is_source_file(p) else None
        elif ln.startswith("diff --git "):
            cur = None
        elif cur and ln.startswith("+"):
            out.append((cur, ln[1:]))
    return out


def _call_re(name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![\w$]){re.escape(name)}\s*(?:<[^<>()]*>)?\s*\(")


def _is_definition(line: str, name: str) -> bool:
    n = re.escape(name)
    return bool(re.search(rf"\bfunction\s*\*?\s*{n}\b", line)
                or re.search(rf"(?<![\w$.]){n}\s*[:=]\s*(?:async\s*)?(?:function\b|\()", line)
                or re.search(rf"^\s*(?:export\s+)?(?:async\s+)?{n}\s*\([^)]*\)\s*[:{{]", line))


def t2_reuse(diff_text: str, cond: str, cfg: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    """Static check of the consumer step (spec §5.2). Label: ``helper`` (F: the new code
    calls a factored helper), ``copy`` (R: calls an existing copy, or copies the logic,
    detected by the zone's markers), ``reimplements`` (F: the logic's markers without a
    helper call), or None (no source change, or neither a call nor a marker: left for
    the design review rather than guessed)."""
    added = added_source_lines(diff_text)
    helpers = list((cfg.get("helpers") or {}).get(cond) or [])
    markers = [re.compile(m) for m in cfg.get("markers") or []]
    calls = sorted({h for _, t in added for h in helpers
                    if _call_re(h).search(t) and not _is_definition(t, h)})
    hits = sorted({m.pattern for _, t in added for m in markers if m.search(t)})
    detail = {"added_source_lines": len(added), "calls": calls, "markers": hits,
              "helpers_checked": helpers}
    if not added:
        return None, {**detail, "reason": "no_source_change"}
    if calls:
        return T2_LABELS.get(cond, "helper"), detail
    if hits:
        return ("copy" if cond == "R" else "reimplements"), detail
    return None, {**detail, "reason": "no_call_no_marker"}


# --------------------------------------------------------------------------- result

def step_meta(step_dir: Path) -> dict:
    meta = json.loads((step_dir / "agent.json").read_text())
    agent, cond, zone, chain, step = step_dir.parts[-5:]
    meta.setdefault("agent", agent)
    meta.setdefault("cond", cond)
    meta.setdefault("zone", zone)
    meta.setdefault("chain", chain)
    meta.setdefault("step", step)
    return meta


def _step_id(v: Any) -> str:
    s = str(v)
    return s if s.upper().startswith("T") else f"T{s}"


def _chain_value(v: Any) -> Any:
    try:
        return int(v)
    except (TypeError, ValueError):
        return v


USAGE_KEYS = ("input_tokens", "output_tokens", "cached_input_tokens", "turns", "tool_calls")


def _opt_int(v: Any) -> int | None:
    return None if v is None else int(v)


def usage_fields(meta: dict, transcript: list[str]) -> dict[str, Any]:
    """A step's efficiency fields for result.json: ``tokens`` ({input, output,
    cached_input}, None when the stream never reported them: study-3 pilot, blocking
    item 3), ``turns``, ``tool_calls``, ``usage_missing``, ``usage_source``.

    Parsed from the transcript with the current parser (:func:`aa.agents.parse_stream`:
    Claude usage summed over every ``result``, blocking item 2) when there is one, else
    agent.json's ``usage`` as the runner recorded it. When the parse differs from the
    runner's record, both are kept (``usage_reparsed``); agent.json is never rewritten."""
    from dataclasses import asdict

    from aa.agents import parse_stream
    recorded = meta.get("usage") or {}
    if transcript:
        parsed = asdict(parse_stream(meta["agent"], transcript)[0])
        source = "transcript"
    else:
        parsed = {k: recorded.get(k) for k in USAGE_KEYS}
        source = "agent_json"
    tokens = {"input": _opt_int(parsed.get("input_tokens")),
              "output": _opt_int(parsed.get("output_tokens")),
              "cached_input": _opt_int(parsed.get("cached_input_tokens"))}
    out: dict[str, Any] = {
        "tokens": tokens, "turns": int(parsed.get("turns") or 0),
        "tool_calls": int(parsed.get("tool_calls") or 0),
        "usage_missing": tokens["input"] is None or tokens["output"] is None,
        "usage_source": source, "usage_reparsed": None}
    if source == "transcript" and recorded and any(
            recorded.get(k) != parsed.get(k) for k in USAGE_KEYS):
        out["usage_reparsed"] = {"agent_json": {k: recorded.get(k) for k in USAGE_KEYS},
                                 "parsed": {k: parsed.get(k) for k in USAGE_KEYS}}
    return out


def step_tokens(r: dict) -> int | None:
    """Input + output tokens of a step result; None when missing."""
    t = r.get("tokens") or {}
    if t.get("input") is None or t.get("output") is None:
        return None
    return int(t["input"]) + int(t["output"])


def _carried_text(chain_dir: Path | None, plan: dict | None) -> str:
    """The carried patches' text (for the test-infra flag of the pre-image)."""
    if chain_dir is None or not plan:
        return ""
    return "".join(_read_text(chain_dir / p) for p in plan.get("patches") or [])


def assemble_step_result(meta: dict, chain: Chain, diff_text: str, eval_dir: Path | None,
                         transcript: list[str], eval_error: str | None = None, *,
                         prev_result: dict | None = None, runner_trees: dict | None = None,
                         carried_text: str = "") -> dict:
    """Pure: build a step's result.json from agent.json, the chain, the agent's diff and
    the eval outputs. Field names follow aa.tables2's input contract. ``runner_trees``:
    ``{"start": <start_tree>, "post": <post_tree>}`` as the runner recorded them."""
    agent, cond = meta["agent"], meta["cond"]
    step = chain.step(_step_id(meta["step"]))
    status = meta.get("status")
    files = chain.files_for(cond)
    result: dict[str, Any] = {
        "agent": agent, "cond": cond, "zone": chain.zone, "chain": _chain_value(meta["chain"]),
        "step": step.index, "step_id": step.id, "kind": step.kind, "status": status,
        "depends_on_f_comment_fact": step.depends_on_f_comment_fact,
        "correct": False,
        "consumers_passed": 0, "consumers_total": len(step.consumers), "consumers": None,
        "missed_copy": None,
        "consumers_preexisting_passed": None,
        "consumers_preexisting_total": len([c for c in step.consumers
                                            if c in set(chain.preexisting_consumers)]),
        "missed_copy_preexisting": None, "t2_consumer_ok": None,
        "carried_defects": None, "carried_steps_failing": None, "carried_detail": None,
        "new_carried_defects": None,
        "test_status": None,
        "lint_ok": None, "typecheck_ok": None,
        **usage_fields(meta, transcript),
        "wall_s": meta.get("wall_s"),
        "diff": diff_stats(diff_text),
        "agent_touched_test_infra": touches_test_infra(diff_text),
        "agent_touched_hidden_paths": sorted(
            diff_files(diff_text) & {h for s in chain.steps for h in s.hidden}),
        "pre_image_touched_test_infra": touches_test_infra(carried_text),
        "agent_tree_from": "tar" if meta.get("tree_fallback") and not meta.get("diff_ok")
        else "diff",
        "diff_applies_to_pre_image": None,
        "tree_check": None,
        "t2_reuses_logic": None, "t2_reuse_detail": None,
        "duplication_pre": None, "duplication_post": None,
        "trace": extract_trace(agent, transcript),
        "contamination_markers": contamination(agent, transcript, ()),
        "eval_error": None,
        "hidden": None,
    }
    result["contamination_flag"] = bool(result["contamination_markers"])
    for k in ("infra_retries", "infra_attempts"):
        if k in meta:
            result[k] = meta[k]
    if step.kind == "consumer":
        result["t2_reuses_logic"], result["t2_reuse_detail"] = t2_reuse(
            diff_text, zone_cond(cond, (chain.t2_reuse or {}).get("helpers") or {}),
            chain.t2_reuse)
    if status not in EVALUATED:
        result["eval_error"] = "not_evaluated"
        return result

    if eval_error is None and eval_dir is not None:
        eval_error = _read_text(eval_dir / "eval_error").strip() or None
    if eval_error is None and (eval_dir is None or not (eval_dir / "eval_done").exists()):
        eval_error = "container"
    result["eval_error"] = eval_error
    if eval_dir is not None:
        rt = runner_trees or {}
        mine = {k: _read_text(eval_dir / f"{k}_tree").strip() or None for k in ("start", "post")}
        result["tree_check"] = {k: None if not (rt.get(k) and mine[k]) else rt[k] == mine[k]
                                for k in ("start", "post")}
        result["duplication_pre"] = read_jscpd(eval_dir, "jscpd_pre", files)
    if eval_dir is None or eval_error in EVAL_ERRORS_NOTHING_RAN:
        if eval_error == "diff_apply":
            result["diff_applies_to_pre_image"] = False
        return result
    result["diff_applies_to_pre_image"] = (eval_dir / DIFF_APPLIED).exists() or None
    result["duplication_post"] = read_jscpd(eval_dir, "jscpd_post", files)
    lint_rc, tc_rc = _read_int(eval_dir / "lint_rc"), _read_int(eval_dir / "typecheck_rc")
    result["lint_ok"] = None if lint_rc is None else lint_rc == 0
    result["typecheck_ok"] = None if tc_rc is None else tc_rc == 0
    report_p = eval_dir / "report.json"
    try:
        report = json.loads(report_p.read_text()) if report_p.exists() else None
    except json.JSONDecodeError:
        report = None
    if report is None and eval_error is not None:
        return result  # nothing reliable ran (container died, restore failed)

    own = step_outcome(report, step)
    result["hidden"] = {k: own[k] for k in ("passed", "failed", "failed_tests", "missing_files")}
    result["correct"] = own["correct"] and eval_error is None
    result["consumers"] = own["consumers"]
    result["consumers_passed"] = own["consumers_passed"]
    result["missed_copy"] = missed_copy(step.kind, own["consumers_passed"], own["consumers_total"])
    result.update(split_coverage(own["consumers"], step, chain.preexisting_consumers))
    statuses = {step.id: own["tests"]}
    carried_detail: dict[str, Any] = {}
    for prev in chain.steps[:step.index - 1]:
        sup = chain.superseded(step, prev)
        o = step_outcome(report, prev, sup)
        statuses[prev.id] = o["tests"]
        carried_detail[prev.id] = {"correct": o["correct"],
                                   "superseded_tests": len(sup),
                                   "failed_tests": sum(not v for v in o["tests"].values()),
                                   "consumers_passed": o["consumers_passed"],
                                   "consumers_total": o["consumers_total"]}
    result["test_status"] = statuses
    result["carried_detail"] = carried_detail
    result["carried_defects"] = sum(d["failed_tests"] for d in carried_detail.values())
    result["carried_steps_failing"] = [s for s, d in carried_detail.items() if d["failed_tests"]]
    prev_status = (prev_result or {}).get("test_status")
    if isinstance(prev_status, dict):
        result["new_carried_defects"] = sum(
            1 for sid in carried_detail for n, ok in statuses[sid].items()
            if not ok and (prev_status.get(sid) or {}).get(n) is True)
    return result


class ContainerGate:
    """Shared / exclusive admission of evaluator containers (writer-preferring). T1-T4
    containers enter shared (``aa chain evaluate --workers`` of them at once); RC's T0
    evaluation (its untouched-R reference run and its container, both as heavy as
    ``aa chain t0-reference``, which runs out of memory two at a time in the 6 GB Docker
    VM) enters exclusive: it waits for running containers and none starts beside it."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._shared = 0
        self._writer = False
        self._waiting = 0

    @contextmanager
    def shared(self):
        with self._cond:
            while self._writer or self._waiting:
                self._cond.wait()
            self._shared += 1
        try:
            yield
        finally:
            with self._cond:
                self._shared -= 1
                self._cond.notify_all()

    @contextmanager
    def exclusive(self):
        with self._cond:
            self._waiting += 1
            while self._writer or self._shared:
                self._cond.wait()
            self._waiting -= 1
            self._writer = True
        try:
            yield
        finally:
            with self._cond:
                self._writer = False
                self._cond.notify_all()


# One gate per process: every evaluation of this process (evaluate_all's workers)
GATE = ContainerGate()


def evaluate_step(step_dir: Path, *, tasks_root: Path | None = None,
                  execute: Executor = docker_execute,
                  checker_dir: Path = SEED_SRC.parent, t0_root: Path | None = None,
                  t0_reference: Any = None, tests: bool = True) -> dict | None:
    """Evaluate one chain step dir and write its ``result.json``. None when the step is
    not final yet (no agent.json, or status ``infra``). Study-3 steps (agent.json
    ``study`` 3, or an RG/RL/RC arm) get :mod:`aa.chain_eval3`'s measures; RC's T0 is
    evaluated by :func:`aa.chain_eval3.evaluate_t0_step` (``t0_root``: tasks3/,
    ``t0_reference``: the untouched-R reference or a callable returning it).
    ``tests=False``: static checks only (no vitest)."""
    from aa import chain_eval3 as ce3
    step_dir = Path(step_dir).resolve()
    if not (step_dir / "agent.json").exists():
        return None
    meta = step_meta(step_dir)
    status = meta.get("status")
    if status == "infra":
        return None
    if _step_id(meta["step"]) == chain_tasks.T0_ID:
        # T0 runs alone (reference + its container), unless AA_T0_SHARED=1 (12 GB VM,
        # amendment 2026-10-16: a T0 with any failing check is re-evaluated alone after)
        gate = GATE.shared if os.environ.get("AA_T0_SHARED") == "1" else GATE.exclusive
        with gate():
            return ce3.evaluate_t0_step(step_dir, tasks_root=tasks_root, execute=execute,
                                        checker_dir=checker_dir, t0_root=t0_root,
                                        reference=t0_reference, tests=tests)
    study3 = ce3.is_study3(meta)
    transcript = _read_text(step_dir / "transcript.jsonl").splitlines()
    diff_text = _read_text(step_dir / "diff.patch")
    chain = load_chain(meta["zone"], tasks_root)
    step = chain.step(_step_id(meta["step"]))
    prev_result = None
    if step.index > 1:
        try:
            prev_result = json.loads(
                (step_dir.parent / chain.steps[step.index - 2].id / "result.json").read_text())
        except (OSError, ValueError):
            prev_result = None
    runner_trees = {"start": _read_text(step_dir / "start_tree").strip()
                    or (meta.get("carry") or {}).get("start_tree"),
                    "post": _read_text(step_dir / "post_tree").strip() or meta.get("post_tree")}
    eval_error: str | None = None
    eval_dir: Path | None = None
    plan: dict | None = None
    if status in EVALUATED:
        eval_dir = step_dir / EVAL_DIR
        try:
            if eval_dir.exists():
                shutil.rmtree(eval_dir)
            eval_dir.mkdir()
            plan = carry_plan(step_dir, meta, step.index)
            every_hidden: list[str] = []
            for s in chain.steps[:step.index]:
                every_hidden += stage_hidden_tests(s.dir, s.hidden, meta["cond"], eval_dir)
            scope_files: list[str] = []
            if study3:  # pilot blocking item 9: T0 inconsistency tests still in scope
                t0_task, in_scope = ce3.step_scope(chain.zone, step.id, t0_root)
                if in_scope:
                    scope_files = stage_hidden_tests(t0_task.dir, list(t0_task.hidden),
                                                     meta["cond"], eval_dir)
            tar = not (step_dir / "diff_ok").exists() and (step_dir / "tree.tar").exists()
            script = chain_eval_script(step.id, plan, agent_tree="tar" if tar else "diff",
                                       hidden_tests=every_hidden,
                                       zone_files=chain.files_for(meta["cond"]),
                                       zone_dirs=chain.dirs_for(meta["cond"]),
                                       study3=study3, tests=tests, scope_tests=scope_files)
            argv = chain_eval_docker_argv(meta["cond"], step_dir, eval_dir, script, checker_dir)
        except (OSError, KeyError, ValueError) as exc:
            eval_error = f"setup:{type(exc).__name__}: {exc}"[:300]
            eval_dir = None
        else:
            try:
                with GATE.shared():
                    execute(argv, HOST_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                eval_error = "eval_timeout"
            except Exception:  # docker missing / daemon down -> `container` below
                pass
    meta = {**meta, "diff_ok": (step_dir / "diff_ok").exists(),
            "tree_fallback": (step_dir / "tree.tar").exists()}
    result = assemble_step_result(meta, chain, diff_text, eval_dir, transcript, eval_error,
                                  prev_result=prev_result, runner_trees=runner_trees,
                                  carried_text=_carried_text(step_dir.parent, plan))
    if study3:
        try:
            sites: dict | None = chain_tasks.load_t0(chain.zone, t0_root).sites
        except chain_tasks.T0Error:
            sites = None
        ce3.study3_fields(result, meta=meta, chain=chain, step=step, eval_dir=eval_dir,
                          diff_text=diff_text, transcript=transcript, sites=sites,
                          runner_trees=runner_trees)
        if eval_dir is not None and tests and result.get("eval_error") is None:
            _, in_scope = ce3.step_scope(chain.zone, step.id, t0_root)
            result["inconsistencies_unified_step"], result["inconsistency_scope_detail"] = \
                ce3.scope_outcome(eval_dir, in_scope)
    _write_json(step_dir / "result.json", result)
    return result


# --------------------------------------------------------------------------- chain level

def chain_dirs(root: Path) -> list[Path]:
    """Every ``<agent>/<cond>/<zone>/<chain>`` dir holding at least one step dir."""
    out = {p.parent.parent for p in Path(root).glob("*/*/*/*/T*/agent.json")
           if STEP_DIR.match(p.parent.name)}
    return sorted(out)


def _steps_of(chain_dir: Path) -> list[Path]:
    return sorted((d for d in chain_dir.iterdir() if d.is_dir() and STEP_DIR.match(d.name)),
                  key=lambda d: int(d.name[1:]))


def summarise_chain(chain_dir: Path, chain: Chain) -> dict:
    """``chain_result.json``: duplication T0..Tk, cumulative diff (written to
    ``cumulative.patch`` when the chain starts from the untouched variant), cost
    growth (T4 tokens / T1 tokens) and per-step summaries.

    An RC chain (study 3) also has the directed-refactor step ``T0`` in front of T1:
    its summary goes to ``t0``; ``duplication.T0`` / ``duplication_delta`` /
    ``cost_growth`` stay T1..Tn measures (T1 starts from the agent's T0 tree), the
    untouched start is ``duplication.start``; ``cumulative.patch`` is T0..Tn (secondary,
    spec section 7); ``totals`` gives tokens and wall time with and without T0."""
    agent, cond, zone, cidx = chain_dir.parts[-4:]
    results: dict[str, dict] = {}
    for s in chain.steps:
        try:
            results[s.id] = json.loads((chain_dir / s.id / "result.json").read_text())
        except (OSError, ValueError):
            pass
    has_t0 = (chain_dir / chain_tasks.T0_ID / "agent.json").exists()
    t0: dict | None = None
    if has_t0:
        try:
            t0 = json.loads((chain_dir / chain_tasks.T0_ID / "result.json").read_text())
        except (OSError, ValueError):
            t0 = None
    first, last = chain.steps[0], chain.steps[-1]
    dup: dict[str, Any] = {}
    if first.id in results and results[first.id].get("duplication_pre") is not None:
        dup["T0"] = _dup_summary(results[first.id]["duplication_pre"])
    for s in chain.steps:
        d = (results.get(s.id) or {}).get("duplication_post")
        if d is not None:
            dup[s.id] = _dup_summary(d)
    out: dict[str, Any] = {
        "agent": agent, "cond": cond, "zone": zone, "chain": _chain_value(cidx),
        "complete": all(s.id in results for s in chain.steps) and (t0 is not None or not has_t0),
        "steps": {sid: {k: r.get(k) for k in ("status", "correct", "consumers_passed",
                                              "consumers_total", "missed_copy",
                                              "missed_copy_preexisting", "t2_consumer_ok",
                                              "carried_defects", "eval_error")}
                  for sid, r in results.items()},
        "duplication": dup,
        # duplication.T0 is the tree T1 starts from: the untouched variant, or in an RC
        # chain the agent's post-T0 tree (the untouched start is then duplication.start)
        "duplication_T0_tree": "agent_t0_post" if has_t0 else "untouched_variant",
        "duplication_delta": ({k: dup[last.id][k] - dup["T0"][k] for k in dup["T0"]}
                              if "T0" in dup and last.id in dup else None),
        "cumulative_diff": None,
        "cost_growth": None,
    }
    t1, tn = results.get(first.id), results.get(last.id)
    if t1 and tn:
        a, b = step_tokens(t1), step_tokens(tn)
        out["cost_growth"] = {"t1_tokens": a, "last_tokens": b,
                              "ratio": round(b / a, 4) if a and b is not None else None}
    if has_t0:
        out["t0"] = None if t0 is None else {k: t0.get(k) for k in (
            "status", "correct", "probe_unchanged", "probe_changed_cases",
            "inconsistencies_unified", "typecheck_ok", "lint_ok", "related_ok", "eval_error")}
        if t0 is not None and t0.get("duplication_pre") is not None:
            dup["start"] = _dup_summary(t0["duplication_pre"])
    every = ([t0] if t0 else []) + [results[s.id] for s in chain.steps if s.id in results]
    t1_tn = [results[s.id] for s in chain.steps if s.id in results]

    def total(rs: list[dict]) -> dict[str, Any]:
        # tokens None when any step's usage is missing (blocking item 3): not a sum of 0s
        toks = [step_tokens(r) for r in rs]
        return {"tokens": None if any(t is None for t in toks) else sum(toks),
                "tokens_missing_steps": sum(t is None for t in toks),
                "wall_s": round(sum(float(r.get("wall_s") or 0) for r in rs), 1),
                "steps": len(rs)}
    out["totals"] = {"all_steps": total(every), "t1_tn": total(t1_tn)}
    head = chain_tasks.T0_ID if has_t0 else first.id
    start = _read_text(chain_dir / head / EVAL_DIR / PRE_IMAGE)
    post = chain_dir / last.id / EVAL_DIR / POST_TREE
    if has_t0 and not (chain_dir / head / EVAL_DIR / PRE_IMAGE).exists():
        out["cumulative_diff"] = {"error": "t0_not_evaluated"}
    elif start.strip():
        out["cumulative_diff"] = {"error": "chain_start_not_untouched_variant"}
    elif tn and tn.get("diff_applies_to_pre_image") and post.exists():
        text = _read_text(post)
        (chain_dir / CUMULATIVE).write_text(text)
        out["cumulative_diff"] = {"path": CUMULATIVE, "from": head, **diff_stats(text)}
    _write_json(chain_dir / CHAIN_RESULT, out)
    return out


def _dup_summary(d: dict) -> dict[str, int]:
    return {k: int(d.get(k) or 0) for k in ("clones", "duplicated_lines", "duplicated_lines_unique")}


def pending_steps(chain_dir: Path, force: bool = False) -> list[Path]:
    out = []
    for d in _steps_of(chain_dir):
        try:
            status = json.loads((d / "agent.json").read_text()).get("status")
        except (OSError, ValueError):
            continue
        if status == "infra":
            continue
        if force or not (d / "result.json").exists():
            out.append(d)
    return out


def evaluate_chain(chain_dir: Path, *, tasks_root: Path | None = None, force: bool = False,
                   log: Callable[[str], None] = print, **kw: Any) -> dict:
    """Evaluate a chain's pending steps in order (T1 before T2: ``new_carried_defects``
    reads the previous step's result), then write ``chain_result.json``."""
    chain_dir = Path(chain_dir).resolve()
    chain = load_chain(chain_dir.parts[-2], tasks_root)
    for d in pending_steps(chain_dir, force):
        try:
            r = evaluate_step(d, tasks_root=tasks_root, **kw)
        except Exception as exc:  # one step never stops the chain or the batch
            log(f"{d}: evaluator crashed: {type(exc).__name__}: {exc}")
            continue
        if r is not None:
            log(step_log_line(d, r))
    return summarise_chain(chain_dir, chain)


def step_log_line(d: Path, r: dict) -> str:
    """One progress line per evaluated step. Reads only keys every result may lack (an
    RC chain's T0 result has no consumers or carried defects but the probe and the
    inconsistency tests), so logging never stops a chain."""
    parts = [f"status={r.get('status')}", f"correct={r.get('correct')}"]
    if "consumers_total" in r:
        parts.append(f"consumers={r.get('consumers_passed')}/{r.get('consumers_total')}")
    if "carried_defects" in r:
        parts.append(f"carried={r.get('carried_defects')}")
    if "probe_changed_cases" in r:
        parts.append(f"probe_changed={len(r.get('probe_changed_cases') or [])}")
    if "inconsistencies_unified" in r:
        parts.append(f"unified={r.get('inconsistencies_unified')}")
    parts.append(f"eval_error={r.get('eval_error')}")
    return f"{d}: " + " ".join(parts)


def evaluate_all(root: Path | None = None, *, force: bool = False, workers: int = 2,
                 log: Callable[[str], None] = print, **kw: Any) -> dict[Path, dict | None]:
    """`aa chain evaluate --all`: chains in parallel, steps within a chain in series."""
    results: dict[Path, dict | None] = {}

    def one(c: Path) -> None:
        try:
            results[c] = evaluate_chain(c, force=force, log=log, **kw)
        except Exception as exc:
            log(f"{c}: chain evaluation crashed: {type(exc).__name__}: {exc}")
            results[c] = None

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(one, chain_dirs(root or RUNS2)))
    return results


# --------------------------------------------------------------------------- review packets

def _git(repo: Path, *args: str, env: dict | None = None, check: bool = True,
         input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, env=env, check=check, capture_output=True,
                          text=True, input=input_text)


class PreImageChecker:
    """``git apply --check`` of a diff against a pre-image, without materialising a
    tree: a temporary index per condition holds the variant's working tree (so the
    image's install changes are there when the variant was installed), the pre-image
    is applied to a copy of it with ``--cached``, then the diff is checked the same way."""

    def __init__(self, variants_root: Path, tmp: Path):
        self.variants_root, self.tmp = Path(variants_root), Path(tmp)
        self._base: dict[str, Path] = {}

    def _base_index(self, cond: str) -> Path:
        if cond not in self._base:
            repo = self.variants_root / cond
            idx = self.tmp / f"base-{cond}.index"
            env = {**os.environ, "GIT_INDEX_FILE": str(idx)}
            _git(repo, "read-tree", "HEAD", env=env)
            _git(repo, "add", "-A", env=env)
            self._base[cond] = idx
        return self._base[cond]

    def check(self, cond: str, pre_image: str, diff_text: str) -> str | None:
        """None when the diff applies to the pre-image, else the reason."""
        repo = self.variants_root / cond
        idx = self.tmp / f"check-{cond}-{os.getpid()}-{id(diff_text)}.index"
        shutil.copy(self._base_index(cond), idx)
        env = {**os.environ, "GIT_INDEX_FILE": str(idx)}
        try:
            if pre_image.strip():
                p = _git(repo, "apply", "--cached", "--whitespace=nowarn", "-", env=env,
                         check=False, input_text=pre_image)
                if p.returncode:
                    return "pre_image: " + p.stderr.strip()[:300]
            if diff_text.strip():
                p = _git(repo, "apply", "--cached", "--check", "--whitespace=nowarn", "-",
                         env=env, check=False, input_text=diff_text)
                if p.returncode:
                    return "diff: " + p.stderr.strip()[:300]
            return None
        finally:
            idx.unlink(missing_ok=True)


def materialise_pre_image(variant_repo: Path, pre_image: Path | None, dest: Path) -> Path:
    """A detached worktree of the variant with the pre-image applied: the tree a judge
    reads for a packet (``tree.txt`` names it)."""
    _git(Path(variant_repo), "worktree", "add", "--detach", str(dest), "HEAD")
    if pre_image is not None and pre_image.exists() and pre_image.read_text().strip():
        _git(dest, "apply", "--whitespace=nowarn", str(pre_image.resolve()))
    return dest


def _same_patch(a: str, b: str) -> bool:
    """Two diffs equal up to ``index``/``similarity`` header lines."""
    def norm(t: str) -> list[str]:
        return [ln for ln in t.splitlines() if not ln.startswith(("index ", "similarity"))]
    return norm(a) == norm(b)


def _neutral(salt: str, *parts: Any) -> str:
    return hashlib.sha256("\x00".join([salt, *map(str, parts)]).encode()).hexdigest()[:10]


def export_review_packets(runs_root: Path, out_dir: Path, mapping_path: Path, *,
                          tasks_root: Path | None = None, variants_root: Path | None = None,
                          salt: str = "study2", checker: PreImageChecker | None = None
                          ) -> dict[str, Any]:
    """Blind design-review packets (pre-registered rubric, docs/design-review-rubric.md):
    one per evaluated step that changed something, and one per complete chain
    (cumulative diff, statements T1..Tn, the untouched variant as pre-image). Each
    packet holds ``statement.md``, ``diff.patch`` (the step's start -> agent tree
    diff from the evaluation), ``pre-image.patch`` (possibly empty) and ``tree.txt``
    (a neutral base-tree name; the judge's tree is that base with the pre-image
    applied, :func:`materialise_pre_image`).

    Pre-images are verified twice before export: the change the evaluator measured on
    its rebuilt start tree equals the agent's own ``diff.patch`` (:func:`_same_patch`;
    the runner/evaluator tree ids differ by repo scope, see below), and the diff is
    checked against the variant + pre-image with ``git apply --check``. Failures are
    listed under ``bad`` in ``apply-check.json`` and not exported. The mapping (packet
    id -> agent/cond/zone/chain/step) goes to ``mapping_path``, outside ``out_dir``."""
    out_dir = Path(out_dir)
    packets = out_dir / "packets"
    packets.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, dict] = {}
    report: dict[str, list] = {"ok": [], "bad": []}
    chains: dict[str, Chain] = {}
    with tempfile.TemporaryDirectory() as tmp:
        chk = checker or PreImageChecker(variants_root or config.WORK / "variants", Path(tmp))

        def emit(pid: str, cond: str, statement: str, diff_text: str, pre_image: str,
                 where: dict, problem: str | None = None) -> None:
            reason = problem or chk.check(cond, pre_image, diff_text)
            if reason:
                report["bad"].append({"id": pid, "reason": reason, **where})
                return
            tree = f"tree-{_neutral(salt, 'tree', cond)}"
            d = packets / pid
            d.mkdir(parents=True, exist_ok=True)
            (d / STATEMENT).write_text(statement)
            (d / "diff.patch").write_text(diff_text)
            (d / PACKET_PRE_IMAGE).write_text(pre_image)
            (d / "tree.txt").write_text(
                f"{tree}\n" + (f"apply {PACKET_PRE_IMAGE} to that tree first\n"
                               if pre_image.strip() else ""))
            mapping[pid] = {**where, "tree": tree}
            report["ok"].append(pid)

        for cdir in chain_dirs(runs_root):
            agent, cond, zone, cidx = cdir.parts[-4:]
            if zone not in chains:
                chains[zone] = load_chain(zone, tasks_root)
            chain = chains[zone]
            for s in chain.steps:
                sd = cdir / s.id
                try:
                    r = json.loads((sd / "result.json").read_text())
                except (OSError, ValueError):
                    continue
                step_patch = _read_text(sd / EVAL_DIR / STEP_PATCH)
                if r.get("status") not in EVALUATED or not r.get("diff_applies_to_pre_image") \
                        or not step_patch.strip():
                    continue
                # The runner hashes a fresh `git init` of the tree, the evaluator the
                # image's repo (whose excludes hide ~30 docs/e2e files), so their tree
                # ids never match (2026-10-10). Content check instead: the change the
                # evaluator measured must be the agent's own diff.
                problem = None if _same_patch(step_patch, _read_text(sd / "diff.patch")) \
                    else "step patch differs from the agent's diff"
                where = {"kind": "step", "agent": agent, "cond": cond, "zone": zone,
                         "chain": cidx, "step": s.id, "run_dir": str(sd)}
                emit(_neutral(salt, "step", agent, cond, zone, cidx, s.id), cond,
                     _read_text(s.dir / STATEMENT), step_patch,
                     _read_text(sd / EVAL_DIR / PRE_IMAGE), where, problem)
            cum = cdir / CUMULATIVE
            try:
                complete = json.loads((cdir / CHAIN_RESULT).read_text()).get("complete")
            except (OSError, ValueError):
                complete = False
            if complete and cum.exists() and _read_text(cum).strip():
                statement = "\n\n".join(f"## Step {s.index}\n\n{_read_text(s.dir / STATEMENT)}"
                                        for s in chain.steps)
                where = {"kind": "chain", "agent": agent, "cond": cond, "zone": zone,
                         "chain": cidx, "run_dir": str(cdir)}
                emit(_neutral(salt, "chain", agent, cond, zone, cidx), cond, statement,
                     _read_text(cum), "", where)
    _write_json(out_dir / "apply-check.json", report)
    mapping_path = Path(mapping_path)
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(mapping_path, mapping)
    return report


def rescan_duplication(root: Path | None = None, *, tasks_root: Path | None = None) -> int:
    """Re-read the jscpd reports already on disk into every step's ``result.json``
    (``duplication_pre`` / ``duplication_post``) and rewrite ``chain_result.json``.
    No container runs: for parser fixes only (2026-10-10, bare-basename names)."""
    n = 0
    for chain_dir in chain_dirs(root or RUNS2):
        chain = load_chain(chain_dir.parts[-2], tasks_root)
        for d in _steps_of(chain_dir):
            rp, ed = d / "result.json", d / EVAL_DIR
            if not rp.exists() or not ed.is_dir():
                continue
            r = json.loads(rp.read_text())
            files = chain.files_for(r["cond"])
            if r.get("duplication_pre") is not None:
                r["duplication_pre"] = read_jscpd(ed, "jscpd_pre", files)
            if r.get("duplication_post") is not None:
                r["duplication_post"] = read_jscpd(ed, "jscpd_post", files)
            _write_json(rp, r)
            n += 1
        summarise_chain(chain_dir, chain)
    return n
