"""Study 3 design review: packets, mixed batches, judge-output analysis (plan Task 7;
spec 2026-10-10 sections 3, 6, 7; rubric `docs/design-review-rubric.md`, study-3
addendum). No judging happens here: this module builds what the judges read and reads
back what they wrote.

Packets (:func:`export_review_packets3`)
----------------------------------------
Salt scheme as study 2 (:func:`aa.chain_eval._neutral` over kind, agent, arm, zone,
chain[, step]; salt ``study3``). Per study-3 chain (``runs3/<agent>/<arm>/<zone>/<chain>``):

- ``step``: one per evaluated T1..T4 step that changed something (as study 2: the
  evaluator's measured change must be the agent's own diff).
- ``t0`` (RC): the T0 step, its statement, its diff and the zone's copy sites
  (``sites.json``, judge-facing: :func:`judge_sites`) for completeness and interface.
- ``chain`` (H1 primary): the T1..T4 chain diff. R, RG, RL: the untouched start ->
  T4 post (``cumulative.patch``), empty pre-image. RC: the agent's T0 tree -> T4 post,
  the pre-image (folded into the packet's tree) being T0's tree (T1's verified pre-image, checked equal to T0's
  ``post_tree.patch``); computed by :class:`ChainDiffer` from the two trees.
- ``chain_full`` (RC, secondary): T0..T4 (``cumulative.patch``), statements of T0..T4.
- Study-2 F chains (``runs2/<agent>/F/...``): ``chain`` packets, same scheme, judged in
  the same batches (spec section 7).

Blind to arm (Review Focus 5 and the rubric addendum): every R-based arm (R, RG, RL,
RC) uses ONE neutral base tree, the untouched R variant (F its own, as study 2), never
the arm image. File sections of AGENTS.md (any), the dup-check script and config,
``.jscpd*`` and dup-check files are stripped from every pre-image and diff, in every arm;
the arm patches' ``package.json`` files are kept (dependency changes are design) with
their dup-check lines redacted, and stripped only when the redacted section does not
apply to the neutral base (recorded as ``package_json_stripped``). Lines carrying jscpd
or dup-check, the RG rule's phrases or paraphrases, AGENTS.md, or words naming a
duplication lint/ratchet are dropped (hunks recounted); file sections holding dup-check
output are stripped. What was stripped is recorded in the mapping (outside the
packets). Every packet file is then scanned (:func:`packet_leaks`); a packet with a leak
is not exported (``bad``). Diffs are checked with ``git apply --check`` on the base tree
+ pre-image after sanitising.

Per-packet trees (:class:`PacketTrees`): the sanitised pre-image is applied to the base
tree inside ONE neutral bare repository, one parentless commit per packet; ``tree.txt``
names the repository and that commit; no packet ships a pre-image. So RC's chain and T1
packets no longer differ in form from the other arms' (before: a non-empty pre-image
where every R/RG/RL T1 and chain packet had an empty one).

Partial blindness that remains, documented in the rubric: the content of RC's start
tree (the agent's T0 refactor) is in its trees; T0 and ``chain_full`` packets exist only
in RC; F's helpers are recognisable (study 2).

Batches (:func:`make_batches`): one seeded shuffle of every packet id (all arms + F),
cut in batches of at most 12 with at most one packet per chain; a second judge on a
seeded 25 % of T0 packets and 15 % of the rest.
"""
from __future__ import annotations

import json
import os
import random
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from aa import chains as chain_tasks
from aa import config
from aa.chain_eval import (CHAIN_RESULT, CUMULATIVE, EVAL_DIR, POST_TREE,
                           PRE_IMAGE, STATEMENT, STEP_PATCH, PreImageChecker, _git, _neutral,
                           _same_patch, chain_dirs, load_chain)
from aa.evaluate import EVALUATED, _read_text, _write_json

SALT = "study3"
SEED = 20261011
BATCH_SIZE = 12
SECOND_SHARE = {"t0": 0.25, "other": 0.15}
REVIEW3 = config.WORK / "review3"
MAPPING3 = config.WORK / "review3-mapping.json"
RUNS3 = config.ROOT / "runs3"
STUDY3_PATCHES = config.PATCHES / "study3"
QUESTIONS = "questions.json"
SITES = "sites.json"
KINDS = ("step", "t0", "chain", "chain_full")

DIMS = ("reuse", "duplication", "placement", "scope", "maintainability")
DESIGN_Q = DIMS + ("bypasses_abstraction", "duplicated_blocks", "would_merge")
T2_REUSE = ("helper", "copy", "reimplements")
WOULD_MERGE = ("yes", "with_changes", "no")


def base_variant(cond: str) -> str:
    """The judge's base tree: F for study-2 F, the untouched R variant for every
    study-3 arm (never the arm image: RG's AGENTS.md rule, RL's dup-check)."""
    return "F" if cond == "F" else "R"


def trees_repo_name(salt: str = SALT) -> str:
    """The one repository holding every packet's tree (:class:`PacketTrees`)."""
    return f"trees-{_neutral(salt, 'trees')}.git"


def questions_for(kind: str, step_kind: str | None = None) -> list[str]:
    """The rubric questions a packet asks (rubric study-3 addendum). Depends on the
    packet kind and the step kind only, never on the arm."""
    if kind == "t0":
        return ["completeness", "interface", "disguised_duplication"]
    q = list(DESIGN_Q) + ["disguised_duplication"]
    if kind in ("chain", "chain_full"):
        return q + ["abstraction_drift"]
    if step_kind == "consumer":
        q.append("t2_reuse")
    elif step_kind == "rule":
        q.append("one_place")
    return q


# --------------------------------------------------------------------------- sanitising

_DIFF_HEAD = re.compile(r"^diff --git a/(.+?) b/(.+)$")
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")
RULE_PHRASES = r"do not copy logic|change it in one place|extract it into a shared function"
# Paraphrases of the RG rule and words naming the RL lint or the agent instructions, as
# an agent may write them in a code comment (review of plan Task 7, LOW).
RULE_PARAPHRASES = (
    r"(?:do not|don't|never|avoid) (?:copy(?:ing)?|duplicat(?:e|ing)) (?:the |any )?"
    r"(?:logic|code|behaviou?r)"
    r"|extract(?:ed|ing|s)? (?:it|this|that|the (?:logic|behaviou?r|code)) into "
    r"(?:a|one) shared (?:function|helper)"
    r"|(?:change|update)[sd]? (?:it|the rule|a rule|rules) in (?:one|a single) place")
ARM_WORDS = r"agents\.md|duplication (?:lint|check|ratchet)|\bratchet\b"
DUP_CHECK_OUTPUT = r"dup-check: duplicated code|the check passes when no duplicated block"
REDACT_LINE = re.compile(rf"jscpd|dup-check|{RULE_PHRASES}|{RULE_PARAPHRASES}|"
                         rf"{ARM_WORDS}|{DUP_CHECK_OUTPUT}", re.I)


def arm_patch_paths(patch_dir: Path = STUDY3_PATCHES) -> frozenset[str]:
    """Every path a study-3 arm patch touches (RG: AGENTS.md; RL: dup-check script and
    config, the root and loot-core package.json with the lint scripts)."""
    out: set[str] = set()
    for p in sorted(Path(patch_dir).glob("*.patch")):
        for line in p.read_text().splitlines():
            m = _DIFF_HEAD.match(line)
            if m:
                out |= {m[1], m[2]}
    return frozenset(out)


def _arm_path(path: str, arm_paths: frozenset[str], strip_package_json: bool = False) -> bool:
    """A file section stripped whole. The arm patches' ``package.json`` files are not
    (their dependency changes are the agent's design; only RL's lint-script lines differ,
    and lines naming dup-check are redacted) unless ``strip_package_json``: the fallback
    when the redacted section does not apply to the neutral base (a hunk next to RL's
    lint scripts)."""
    base = path.rsplit("/", 1)[-1]
    if path in arm_paths and base == "package.json" and not strip_package_json:
        return False
    return (path in arm_paths or base.startswith(".jscpd") or "dup-check" in base
            or base.lower() == "agents.md")


def split_sections(text: str) -> list[tuple[tuple[str, str] | None, list[str]]]:
    """A git patch as file sections: ((a path, b path) or None for a preamble, lines)."""
    out: list[tuple[tuple[str, str] | None, list[str]]] = []
    for line in text.splitlines(keepends=True):
        m = _DIFF_HEAD.match(line.rstrip("\n"))
        if m:
            out.append(((m[1], m[2]), [line]))
        elif out:
            out[-1][1].append(line)
        elif line.strip():
            out.append((None, [line]))
    return out


def _redact_section(lines: list[str]) -> tuple[list[str], int]:
    """Drop body lines matching :data:`REDACT_LINE`, recount every hunk header, drop
    hunks left without a change. Binary sections are kept as they are."""
    if any(ln.startswith("GIT binary patch") for ln in lines):
        return lines, 0
    head: list[str] = []
    hunks: list[list[str]] = []
    for ln in lines:
        if _HUNK.match(ln.rstrip("\n")):
            hunks.append([ln])
        elif hunks:
            hunks[-1].append(ln)
        else:
            head.append(ln)
    if not hunks:
        return lines, 0
    dropped = 0
    out = list(head)
    kept_hunks = 0
    for h in hunks:
        m = _HUNK.match(h[0].rstrip("\n"))
        body: list[str] = []
        prev_dropped = False
        for ln in h[1:]:
            if ln.startswith("\\"):
                if not prev_dropped:
                    body.append(ln)
                continue
            if ln[:1] in (" ", "+", "-") and REDACT_LINE.search(ln[1:]):
                dropped += 1
                prev_dropped = True
                continue
            prev_dropped = False
            body.append(ln)
        if len(body) == len(h) - 1:   # nothing dropped: the hunk as it was
            out.extend(h)
            kept_hunks += 1
            continue
        if not any(b[:1] in ("+", "-") for b in body):
            continue
        old_n = sum(1 for b in body if b[:1] in (" ", "-"))
        new_n = sum(1 for b in body if b[:1] in (" ", "+"))
        old_s, new_s = int(m[1]), int(m[3])
        out.append(f"@@ -{old_s},{old_n} +{new_s},{new_n} @@{m[5]}\n")
        out.extend(body)
        kept_hunks += 1
    if kept_hunks == 0:
        return [], dropped
    return out, dropped


def sanitise_patch(text: str, arm_paths: frozenset[str] | None = None,
                   strip_package_json: bool = False) -> tuple[str, dict[str, Any]]:
    """The patch without anything that tells the arm (module docstring). Returns the
    sanitised text and what was removed (``stripped_paths``, ``redacted_lines``)."""
    arm_paths = arm_patch_paths() if arm_paths is None else arm_paths
    stripped: list[str] = []
    redacted = 0
    parts: list[str] = []
    dup_out = re.compile(DUP_CHECK_OUTPUT, re.I)
    for paths, lines in split_sections(text):
        if paths is None:
            continue
        a, b = paths
        body = "".join(lines)
        if _arm_path(a, arm_paths, strip_package_json) \
                or _arm_path(b, arm_paths, strip_package_json) or dup_out.search(body):
            stripped.append(b if b != "/dev/null" else a)
            continue
        new, n = _redact_section(lines)
        redacted += n
        if not new:
            stripped.append(b)
            continue
        parts.append("".join(new))
    out = "".join(parts)
    return out, {"stripped_paths": sorted(set(stripped)), "redacted_lines": redacted}


# Anything in a packet that would tell the arm, the agent or the study apart.
LEAKS = {
    "dup_check": re.compile(r"dup-check", re.I),
    "jscpd": re.compile(r"jscpd", re.I),
    "rg_rule": re.compile(rf"{RULE_PHRASES}|{RULE_PARAPHRASES}", re.I),
    "agents_md": re.compile(r"agents\.md", re.I),
    "lint_words": re.compile(r"duplication (?:lint|check|ratchet)|\bratchet\b", re.I),
    "run_path": re.compile(r"\bruns(?:[23]|-hard|-pilot)\b|\bruns[23]-pilot\b"),
    "arm_path": re.compile(r"(?<![\w-])(?:R|RG|RL|RC|F)/Z[1-4]\b"),
    "rf_frozen": re.compile(r"rf-frozen"),
}
# Only in what the harness writes (statement, tree.txt, questions, sites), not in code.
META_LEAKS = {
    "arm_name": re.compile(r"\b(?:R|F|RG|RL|RC)\b"),
    "agent_name": re.compile(r"\b(?:claude|codex|haiku|sonnet|gpt-\d)", re.I),
    "study_word": re.compile(r"\b(?:variants?|study)\b|\btasks[23]\b|spec section|\bZ[1-4]\b",
                             re.I),
}
META_FILES = (STATEMENT, "tree.txt", QUESTIONS, SITES)


def text_leaks(text: str, meta: bool = False) -> list[str]:
    pats = {**LEAKS, **(META_LEAKS if meta else {})}
    return sorted(k for k, p in pats.items() if p.search(text))


def packet_leaks(packet_dir: Path) -> dict[str, list[str]]:
    """{file name: leak kinds} for every file of a packet (empty when blind)."""
    out = {}
    for f in sorted(Path(packet_dir).iterdir()):
        hits = text_leaks(_read_text(f), meta=f.name in META_FILES)
        if hits:
            out[f.name] = hits
    return out


_SITE_SCRUB = (
    (re.compile(r"\s*\((?:no )?hidden test[^()]*\)"), ""),
    (re.compile(r"\s*\(excluded[^()]*\)"), " (not checked)"),
    (re.compile(r"\s*\(tasks[23]/[^()]*(?:\([^()]*\)[^()]*)*\)"), ""),
    (re.compile(r"\s*\(spec section \d+\)"), ""),
    (re.compile(r",?\s*spec section \d+;"), ";"),
    (re.compile(r",?\s*no hidden test listed in spec section \d+"), ""),
    (re.compile(r"\s*\(Z\d cases\)"), ""),
    (re.compile(r"\s*\((?:R|F)\)"), ""),
    (re.compile(r"\s+in (?:R|F)(?: too)?(?=[;,.)\"]|$)"), ""),
)
SITE_KEYS = ("logic", "decision", "sites", "existing_helper", "not_a_copy",
             "preserved_inconsistencies")


def _scrub(v: Any) -> Any:
    if isinstance(v, str):
        for pat, rep in _SITE_SCRUB:
            v = pat.sub(rep, v)
        return v
    if isinstance(v, list):
        return [_scrub(x) for x in v]
    if isinstance(v, dict):
        return {k: _scrub(x) for k, x in v.items()}
    return v


def judge_sites(sites: dict[str, Any]) -> dict[str, Any]:
    """The judge-facing copy sites: the zone's logic, decision, sites, existing helper /
    not-a-copy notes and the inconsistencies to preserve; without the zone id, the
    source note, F's reference and every mention of the variants, the tasks or the spec
    (:data:`_SITE_SCRUB`)."""
    return {k: _scrub(sites[k]) for k in SITE_KEYS if k in sites}


# --------------------------------------------------------------------------- trees and diffs

class ChainDiffer(PreImageChecker):
    """Also diffs two trees given as patches against the same variant (RC's chain diff:
    T0's tree -> T4's tree), through temporary indexes."""

    def _tree(self, cond: str, patch: str) -> str:
        repo = self.variants_root / cond
        idx = self.tmp / f"tree-{cond}-{abs(hash(patch))}.index"
        shutil.copy(self._base_index(cond), idx)
        env = {**os.environ, "GIT_INDEX_FILE": str(idx)}
        try:
            if patch.strip():
                p = _git(repo, "apply", "--cached", "--whitespace=nowarn", "-", env=env,
                         check=False, input_text=patch)
                if p.returncode:
                    raise ValueError(p.stderr.strip()[:300])
            return _git(repo, "write-tree", env=env).stdout.strip()
        finally:
            idx.unlink(missing_ok=True)

    def diff_between(self, cond: str, patch_a: str, patch_b: str) -> str:
        a, b = self._tree(cond, patch_a), self._tree(cond, patch_b)
        return _git(self.variants_root / cond, "diff-tree", "-p", "--binary", a, b).stdout


TREE_DATE = "2026-01-01T00:00:00+0000"
TREE_HOWTO = ("check out that commit of that repository (git --git-dir <repository> worktree "
              "add --detach <dir> <commit>) and read the change in diff.patch against it\n")


class PacketTrees:
    """The trees the judges read (review of plan Task 7, HIGH): ONE bare repository
    ``<out>/trees/<neutral name>`` with, per packet, a parentless commit of the packet's
    base tree (the untouched R variant for every study-3 arm, F for F) with the packet's
    sanitised pre-image already applied. Every ``tree.txt`` names the repository and the
    packet's own commit in the same form, whether the pre-image was empty (R/RG/RL T1 and
    chain packets) or not (RC's T1 and chain packets, every T2..T4 step), and no packet
    ships a pre-image, so a packet no longer shows that a T0 refactor preceded it.
    Commits carry a fixed date and the packet id as message: one commit per packet, and
    no trace of the export order (which follows the arms)."""

    def __init__(self, out_dir: Path, variants_root: Path, salt: str = SALT):
        self.name = trees_repo_name(salt)
        self.repo = Path(out_dir) / "trees" / self.name
        if self.repo.parent.exists():
            shutil.rmtree(self.repo.parent)
        self.repo.parent.mkdir(parents=True)
        _git(self.repo.parent, "init", "-q", "--bare", self.name)
        self.variants_root = Path(variants_root)
        self._base: dict[str, str] = {}

    def _env(self, **extra: str) -> dict[str, str]:
        return {**os.environ, "GIT_DIR": str(self.repo), **extra}

    def base_tree(self, cond: str) -> str:
        """The variant's working tree (as the pre-image checks see it) as a tree object of
        the trees repository, without the variant's history."""
        if cond not in self._base:
            variant = self.variants_root / cond
            with tempfile.TemporaryDirectory() as tmp:
                wt, vidx, idx = Path(tmp) / "wt", Path(tmp) / "v", Path(tmp) / "i"
                venv = {**os.environ, "GIT_INDEX_FILE": str(vidx)}
                _git(variant, "read-tree", "HEAD", env=venv)
                _git(variant, "add", "-A", env=venv)
                _git(variant, "checkout-index", "-a", "-f", f"--prefix={wt}/", env=venv)
                env = self._env(GIT_WORK_TREE=str(wt), GIT_INDEX_FILE=str(idx))
                _git(wt, "add", "-A", "-f", env=env)
                self._base[cond] = _git(wt, "write-tree", env=env).stdout.strip()
        return self._base[cond]

    def commit(self, cond: str, pre_image: str, pid: str) -> tuple[str, str]:
        """(commit, tree) of the packet's tree; ValueError when the pre-image does not
        apply."""
        with tempfile.TemporaryDirectory() as tmp:
            env = self._env(GIT_INDEX_FILE=str(Path(tmp) / "i"))
            _git(self.repo, "read-tree", self.base_tree(cond), env=env)
            if pre_image.strip():
                p = _git(self.repo, "apply", "--cached", "--whitespace=nowarn", "-", env=env,
                         check=False, input_text=pre_image)
                if p.returncode:
                    raise ValueError("pre_image: " + p.stderr.strip()[:300])
            tree = _git(self.repo, "write-tree", env=env).stdout.strip()
        cenv = self._env(GIT_AUTHOR_NAME="review", GIT_AUTHOR_EMAIL="review@local",
                         GIT_COMMITTER_NAME="review", GIT_COMMITTER_EMAIL="review@local",
                         GIT_AUTHOR_DATE=TREE_DATE, GIT_COMMITTER_DATE=TREE_DATE)
        commit = _git(self.repo, "-c", "commit.gpgsign=false", "commit-tree", tree, "-m", pid,
                      env=cenv).stdout.strip()
        _git(self.repo, "update-ref", f"refs/heads/{pid}", commit, env=cenv)
        return commit, tree

    def checkout(self, commit: str, dest: Path) -> Path:
        """What the judge's workflow does with ``tree.txt``: a detached worktree."""
        _git(self.repo, "worktree", "add", "--detach", str(dest), commit, env=self._env())
        return Path(dest)


def tree_txt(repo_name: str, commit: str) -> str:
    return f"{repo_name}\n{commit}\n{TREE_HOWTO}"


def _has_arm_package_json(text: str, arm_paths: frozenset[str]) -> bool:
    return any(paths is not None and any(x in arm_paths and x.endswith("package.json")
                                         for x in paths)
               for paths, _ in split_sections(text))


# --------------------------------------------------------------------------- export

def _load_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return None


def _step_ok(sd: Path) -> tuple[dict | None, str]:
    """(result, step.patch) when the step can be a packet, else (None, '')."""
    r = _load_json(sd / "result.json")
    patch = _read_text(sd / EVAL_DIR / STEP_PATCH)
    if not r or r.get("status") not in EVALUATED or not r.get("diff_applies_to_pre_image") \
            or not patch.strip():
        return None, ""
    return r, patch


def export_review_packets3(runs_root: Path, out_dir: Path, mapping_path: Path, *,
                           f_runs: Path | None = None, tasks_root: Path | None = None,
                           tasks3_root: Path | None = None, variants_root: Path | None = None,
                           salt: str = SALT, patch_dir: Path = STUDY3_PATCHES,
                           checker: ChainDiffer | None = None) -> dict[str, Any]:
    """Study-3 packets + the study-2 F chain packets (module docstring). Writes
    ``<out>/packets/<id>/``, ``<out>/apply-check.json`` and the mapping (outside
    ``out``); returns the report ``{"ok": [...], "bad": [...]}``."""
    out_dir = Path(out_dir)
    packets = out_dir / "packets"
    if packets.exists():
        shutil.rmtree(packets)
    packets.mkdir(parents=True)
    arm_paths = arm_patch_paths(patch_dir)
    mapping: dict[str, dict] = {}
    report: dict[str, list] = {"ok": [], "bad": []}
    chains: dict[str, Any] = {}
    t0s: dict[str, Any] = {}
    with tempfile.TemporaryDirectory() as tmp:
        variants_root = Path(variants_root or config.WORK / "variants")
        chk = checker or ChainDiffer(variants_root, Path(tmp))
        trees = PacketTrees(out_dir, variants_root, salt)

        def emit(pid: str, cond: str, statement: str, diff_text: str, pre_image: str,
                 where: dict, problem: str | None = None, sites: dict | None = None) -> None:
            if pid in mapping:
                raise ValueError(f"packet id collision: {pid}")
            if problem:
                report["bad"].append({"id": pid, "reason": problem, **where})
                return
            base = base_variant(cond)

            def sanitised(strip_pj: bool):
                d, di = sanitise_patch(diff_text, arm_paths, strip_pj)
                p, pi = sanitise_patch(pre_image, arm_paths, strip_pj)
                if not d.strip():
                    return d, di, p, pi, "empty after sanitising"
                return d, di, p, pi, chk.check(base, p, d)

            diff_s, d_info, pre_s, p_info, reason = sanitised(False)
            pj_stripped = False
            if reason and _has_arm_package_json(diff_text + pre_image, arm_paths):
                retry = sanitised(True)   # a redacted package.json hunk that cannot apply
                if not retry[4]:
                    diff_s, d_info, pre_s, p_info, reason = retry
                    pj_stripped = True
            if reason:
                report["bad"].append({"id": pid, "reason": reason, **where})
                return
            try:
                commit, tree_id = trees.commit(base, pre_s, pid)
            except (ValueError, subprocess.CalledProcessError) as e:
                report["bad"].append({"id": pid, "reason": f"tree: {e}", **where})
                return
            d = packets / pid
            d.mkdir(parents=True)
            (d / STATEMENT).write_text(statement)
            (d / "diff.patch").write_text(diff_s)
            (d / "tree.txt").write_text(tree_txt(trees.name, commit))
            (d / QUESTIONS).write_text(json.dumps(
                {"questions": questions_for(where["kind"], where.get("step_kind"))}, indent=2)
                + "\n")
            if sites is not None:
                (d / SITES).write_text(json.dumps(sites, indent=2) + "\n")
            leaks = packet_leaks(d)
            if leaks:
                shutil.rmtree(d)
                report["bad"].append({"id": pid, "reason": f"leak: {leaks}", **where})
                return
            sanitised_info = {k: v for k, v in (("diff", d_info), ("pre_image", p_info))
                              if v["stripped_paths"] or v["redacted_lines"]}
            if pj_stripped:
                sanitised_info["package_json_stripped"] = True
            mapping[pid] = {**where, "tree": trees.name, "commit": commit, "tree_id": tree_id,
                            "base": base, "pre_image_empty": not pre_s.strip(),
                            **({"sanitised": sanitised_info} if sanitised_info else {})}
            report["ok"].append(pid)

        def chain_of(zone: str):
            if zone not in chains:
                chains[zone] = load_chain(zone, tasks_root)
            return chains[zone]

        def t0_of(zone: str):
            if zone not in t0s:
                t0s[zone] = chain_tasks.load_t0(zone, tasks3_root)
            return t0s[zone]

        def chain_statement(chain, with_t0: str | None = None) -> str:
            parts = ([f"## Step 0\n\n{with_t0}"] if with_t0 is not None else []) + [
                f"## Step {s.index}\n\n{_read_text(s.dir / STATEMENT)}" for s in chain.steps]
            return "\n\n".join(parts)

        for cdir in chain_dirs(runs_root):
            agent, cond, zone, cidx = cdir.parts[-4:]
            chain = chain_of(zone)
            base_where = {"agent": agent, "cond": cond, "zone": zone, "chain": cidx}
            has_t0 = (cdir / chain_tasks.T0_ID / "agent.json").exists()
            if has_t0:
                sd = cdir / chain_tasks.T0_ID
                r, patch = _step_ok(sd)
                if r is not None:
                    t0 = t0_of(zone)
                    problem = None if _same_patch(patch, _read_text(sd / "diff.patch")) \
                        else "step patch differs from the agent's diff"
                    emit(_neutral(salt, "step", agent, cond, zone, cidx, chain_tasks.T0_ID),
                         cond, t0.statement(), patch, _read_text(sd / EVAL_DIR / PRE_IMAGE),
                         {"kind": "t0", **base_where, "step": chain_tasks.T0_ID,
                          "step_kind": chain_tasks.T0_KIND, "run_dir": str(sd)},
                         problem, sites=judge_sites(t0.sites))
            for s in chain.steps:
                sd = cdir / s.id
                r, patch = _step_ok(sd)
                if r is None:
                    continue
                problem = None if _same_patch(patch, _read_text(sd / "diff.patch")) \
                    else "step patch differs from the agent's diff"
                emit(_neutral(salt, "step", agent, cond, zone, cidx, s.id), cond,
                     _read_text(s.dir / STATEMENT), patch, _read_text(sd / EVAL_DIR / PRE_IMAGE),
                     {"kind": "step", **base_where, "step": s.id, "step_kind": s.kind,
                      "run_dir": str(sd)}, problem)
            cres = _load_json(cdir / CHAIN_RESULT) or {}
            cum = _read_text(cdir / CUMULATIVE)
            if not cres.get("complete") or not cum.strip():
                continue
            where = {"kind": "chain", **base_where, "run_dir": str(cdir)}
            if not has_t0:
                emit(_neutral(salt, "chain", agent, cond, zone, cidx), cond,
                     chain_statement(chain), cum, "", where)
                continue
            # RC: primary = T0's tree -> T4's tree; secondary = T0..T4 from untouched R
            first, last = chain.steps[0], chain.steps[-1]
            t0_post = _read_text(cdir / chain_tasks.T0_ID / EVAL_DIR / POST_TREE)
            t1_pre = _read_text(cdir / first.id / EVAL_DIR / PRE_IMAGE)
            tn_post = _read_text(cdir / last.id / EVAL_DIR / POST_TREE)
            problem, diff = None, ""
            if not (cdir / first.id / EVAL_DIR / PRE_IMAGE).exists() or not tn_post.strip():
                problem = "rc: T1 pre-image or last post tree missing"
            elif not _same_patch(t0_post, t1_pre):
                problem = "rc: T1 pre-image is not T0's post tree"
            else:
                try:
                    diff = chk.diff_between(base_variant(cond), t1_pre, tn_post)
                except (ValueError, subprocess.CalledProcessError) as e:
                    problem = f"rc: chain diff: {e}"
            emit(_neutral(salt, "chain", agent, cond, zone, cidx), cond,
                 chain_statement(chain), diff, t1_pre, where, problem)
            emit(_neutral(salt, "chain_full", agent, cond, zone, cidx), cond,
                 chain_statement(chain, t0_of(zone).statement()), cum, "",
                 {**where, "kind": "chain_full"})

        if f_runs is not None and Path(f_runs).is_dir():
            for cdir in chain_dirs(f_runs):
                agent, cond, zone, cidx = cdir.parts[-4:]
                if cond != "F":
                    continue
                cres = _load_json(cdir / CHAIN_RESULT) or {}
                cum = _read_text(cdir / CUMULATIVE)
                if not cres.get("complete") or not cum.strip():
                    continue
                emit(_neutral(salt, "chain", agent, cond, zone, cidx), cond,
                     chain_statement(chain_of(zone)), cum, "",
                     {"kind": "chain", "agent": agent, "cond": cond, "zone": zone,
                      "chain": cidx, "run_dir": str(cdir), "study": 2})
    _write_json(out_dir / "apply-check.json", report)
    mapping_path = Path(mapping_path)
    if out_dir.resolve() in mapping_path.resolve().parents:
        raise ValueError("the mapping must live outside the packets' directory")
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(mapping_path, mapping)
    return report


def export_and_batch(runs_root: Path, out_dir: Path, mapping_path: Path, *,
                     f_runs: Path | None, tasks_root: Path | None = None,
                     tasks3_root: Path | None = None, variants_root: Path | None = None,
                     seed: int = SEED) -> tuple[dict, dict, dict]:
    """Packets (:func:`export_review_packets3`) then ``<out>/batches.json``
    (:func:`make_batches`): what ``scripts/study3_review_packets.py`` and ``aa chain
    packets --study 3`` run. Returns (report, mapping, batches)."""
    rep = export_review_packets3(runs_root, out_dir, mapping_path, f_runs=f_runs,
                                 tasks_root=tasks_root, tasks3_root=tasks3_root,
                                 variants_root=variants_root)
    mapping = json.loads(Path(mapping_path).read_text())
    batches = make_batches(mapping, seed=seed)
    (Path(out_dir) / "batches.json").write_text(json.dumps(batches, indent=1) + "\n")
    return rep, mapping, batches


# --------------------------------------------------------------------------- batches

def chain_key(pid: str, m: dict[str, Any]) -> tuple:
    """The chain a packet comes from (agent, arm, zone, chain); the id itself when the
    mapping does not say."""
    keys = ("agent", "cond", "zone", "chain")
    return tuple(str(m[k]) for k in keys) if all(k in m for k in keys) else (pid,)


def _disjoint_batches(order: list[str], mapping: dict[str, dict], size: int) -> list[list[str]]:
    """``order`` cut in batches of at most ``size`` with at most ONE packet per chain in
    a batch (review of plan Task 7, HIGH: an RC chain's ``t0`` and ``chain_full`` packets,
    or its chain and step packets, side by side would link them). First fit in shuffled
    order: each id goes to the first open batch without a packet of its chain."""
    batches: list[list[str]] = []
    seen: list[set[tuple]] = []
    for pid in order:
        k = chain_key(pid, mapping[pid])
        for b, ks in zip(batches, seen):
            if len(b) < size and k not in ks:
                b.append(pid)
                ks.add(k)
                break
        else:
            batches.append([pid])
            seen.append({k})
    return batches


def make_batches(mapping: dict[str, dict], *, seed: int = SEED, size: int = BATCH_SIZE,
                 shares: dict[str, float] | None = None) -> dict[str, Any]:
    """ONE seeded shuffle of every packet id, all arms and F together (Review Focus 5),
    cut in batches of at most ``size`` holding at most one packet per chain
    (:func:`_disjoint_batches`); a second judge on a seeded share of T0 packets (25 %)
    and of the rest (15 %), shuffled and batched the same way."""
    shares = shares or SECOND_SHARE
    ids = sorted(mapping)
    pool = list(ids)
    random.Random(seed).shuffle(pool)
    rng = random.Random(seed + 1)
    t0 = [i for i in ids if mapping[i]["kind"] == "t0"]
    rest = [i for i in ids if mapping[i]["kind"] != "t0"]
    second = (rng.sample(t0, round(shares["t0"] * len(t0)))
              + rng.sample(rest, round(shares["other"] * len(rest))))
    rng.shuffle(second)
    return {"seed": seed, "batch_size": size, "second_share": shares, "pool": pool,
            "one_packet_per_chain": True,
            "main": _disjoint_batches(pool, mapping, size),
            "second": _disjoint_batches(second, mapping, size)}


# --------------------------------------------------------------------------- judge outputs

class JudgementError(ValueError):
    pass


def _flag(v: Any) -> dict[str, Any]:
    if isinstance(v, list):
        return {"value": v[0], "where": v[1] if len(v) > 1 else ""}
    if isinstance(v, dict):
        return {"value": v.get("value"), "where": v.get("where", v.get("why", ""))}
    return {"value": v, "where": ""}


def _score(v: Any) -> dict[str, Any]:
    if isinstance(v, list):
        return {"score": v[0], "why": v[1] if len(v) > 1 else ""}
    if isinstance(v, dict):
        return {"score": v.get("score"), "why": v.get("why", "")}
    return {"score": v, "why": ""}


LEVEL_WEIGHT = {"full": 1.0, "partial": 0.5, "none": 0.0}


def _completeness_levels(per_site: Any, given: Any) -> dict[str, Any]:
    """Amendment 2026-10-12b item 8: ``completeness = (full + 0.5 x partial) / sites``
    from the judge's per-site levels (legacy booleans: true = full, false = none), with
    the lenient (partial = 1) and strict (partial = 0) sensitivities. A judge ``value``
    that disagrees with its own levels is replaced by the levels' value and recorded in
    ``value_mismatch``."""
    if not isinstance(per_site, dict) or not per_site:
        raise JudgementError("completeness per_site must be a non-empty object")
    levels: dict[str, str] = {}
    for site, lv in per_site.items():
        lv = {True: "full", False: "none"}.get(lv, lv) if isinstance(lv, bool) else lv
        if lv not in LEVEL_WEIGHT:
            raise JudgementError(f"completeness level {lv!r} for {site!r}")
        levels[str(site)] = lv
    n = len(levels)
    full = sum(lv == "full" for lv in levels.values())
    partial = sum(lv == "partial" for lv in levels.values())
    value = (full + 0.5 * partial) / n
    out: dict[str, Any] = {"per_site": levels, "sites_full": full, "sites_partial": partial,
                           "sites_total": n, "value": value,
                           "lenient": (full + partial) / n, "strict": full / n}
    if isinstance(given, (int, float)) and not isinstance(given, bool) \
            and abs(float(given) - value) > 1e-9:
        out["value_mismatch"] = {"given": float(given), "levels": value}
    return out


def normalise(x: dict[str, Any]) -> dict[str, Any]:
    """A judge file in the rubric's shape. Tolerates study 2's abbreviated shape
    (``[score, why]`` for a dimension; ``bp`` / ``db`` / ``wm``) and the same
    list / bare-value shortcuts for the study-3 questions; checks ranges."""
    out = dict(x)
    for d in DIMS + ("interface",):
        if d in x:
            out[d] = _score(x[d])
            s = out[d]["score"]
            if not isinstance(s, int) or isinstance(s, bool) or not 1 <= s <= 5:
                raise JudgementError(f"{d}: score {s!r} not in 1..5")
    if "bp" in x:
        out["bypasses_abstraction"] = _flag(x["bp"])
    if "db" in x:
        out["duplicated_blocks"] = x["db"]
    if "wm" in x:
        out["would_merge"] = x["wm"]
    for k in ("bypasses_abstraction", "disguised_duplication", "one_place"):
        if k in out:
            out[k] = _flag(out[k])
            if not isinstance(out[k]["value"], bool):
                raise JudgementError(f"{k}: value {out[k]['value']!r} is not a boolean")
    for k in ("bp", "db", "wm"):
        out.pop(k, None)
    if "would_merge" in out and out["would_merge"] not in WOULD_MERGE:
        raise JudgementError(f"would_merge {out['would_merge']!r}")
    if "t2_reuse" in out:
        v = out["t2_reuse"]
        v = v.get("value") if isinstance(v, dict) else (v[0] if isinstance(v, list) else v)
        if v not in T2_REUSE:
            raise JudgementError(f"t2_reuse {v!r} not in {T2_REUSE}")
        out["t2_reuse"] = v
    if "completeness" in out:
        c = out["completeness"]
        if isinstance(c, list):
            c = {"value": c[0], "why": c[1] if len(c) > 1 else ""}
        elif not isinstance(c, dict):
            c = {"value": c}
        c = dict(c)
        if "per_site" in c:
            c.update(_completeness_levels(c["per_site"], c.get("value")))
        elif c.get("value") is None and c.get("sites_total"):
            c["value"] = c.get("sites_shared", 0) / c["sites_total"]
        v = c.get("value")
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v <= 1:
            raise JudgementError(f"completeness {v!r} not in 0..1")
        c["value"] = float(v)
        out["completeness"] = c
    if "abstraction_drift" in out:
        a = out["abstraction_drift"]
        if not isinstance(a, dict):
            raise JudgementError("abstraction_drift must be an object")
        a = dict(a)
        for k in ("parameters_added", "special_case_branches", "bypassing_call_sites"):
            a[k] = int(a.get(k) or 0)
        a["value"] = bool(a.get("value", any(a[k] for k in (
            "parameters_added", "special_case_branches", "bypassing_call_sites"))))
        out["abstraction_drift"] = a
    return out


def load_judgements(d: Path) -> dict[str, dict]:
    """``<d>/<packet id>.json`` -> {id: normalised judgement}."""
    d = Path(d)
    if not d.is_dir():
        return {}
    out = {}
    for f in sorted(d.glob("*.json")):
        try:
            out[f.stem] = normalise(json.loads(f.read_text()))
        except JudgementError as e:
            raise JudgementError(f"{f}: {e}") from e
    return out


def qwk(a: list[Any], b: list[Any], categories: list[Any]) -> float | None:
    """Quadratic-weighted Cohen's kappa over ordered ``categories`` (own implementation,
    as study 2). None when undefined (no pairs, or no expected disagreement)."""
    if not a or len(a) != len(b):
        return None
    k = len(categories)
    pos = {c: i for i, c in enumerate(categories)}
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[pos[x]][pos[y]] += 1
    n = len(a)
    rows = [sum(r) for r in obs]
    cols = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = [[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)]
    num = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k))
    den = sum(w[i][j] * rows[i] * cols[j] / n for i in range(k) for j in range(k))
    return None if den == 0 else 1 - num / den


def cohen_kappa(a: list[Any], b: list[Any]) -> float | None:
    """Unweighted Cohen's kappa (nominal labels)."""
    if not a or len(a) != len(b):
        return None
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    cats = set(a) | set(b)
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return None if pe == 1 else (po - pe) / (1 - pe)


def _quarter(v: float) -> float:
    return round(v * 4) / 4


RELIABILITY = (
    *((d, "qwk") for d in DIMS),
    ("interface", "qwk"),
    ("completeness", "qwk"),
    ("t2_reuse", "nominal"),
    ("one_place", "nominal"),
    ("disguised_duplication", "nominal"),
    ("bypasses_abstraction", "nominal"),
    ("would_merge", "nominal"),
    ("abstraction_drift", "nominal"),
)


def _value(j: dict, q: str) -> Any:
    v = j.get(q)
    if v is None:
        return None
    if q in DIMS or q == "interface":
        return v["score"]
    if q == "completeness":
        return _quarter(v["value"])
    if isinstance(v, dict):
        return v.get("value")
    return v


def reliability(a: dict[str, dict], b: dict[str, dict],
                mapping: dict[str, dict] | None = None) -> dict[str, Any]:
    """Agreement of the two judges on the packets both scored, per question, BEFORE any
    comparison: quadratic-weighted kappa for 1..5 scores and completeness (in quarters),
    Cohen's kappa for labels; T0 packets also on their own (25 % sample)."""
    common = sorted(set(a) & set(b))
    out: dict[str, Any] = {"n_packets": len(common), "questions": {}}
    for q, kind in RELIABILITY:
        pairs = [(_value(a[i], q), _value(b[i], q)) for i in common]
        pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
        xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
        if kind == "qwk":
            cats = [0.0, 0.25, 0.5, 0.75, 1.0] if q == "completeness" else [1, 2, 3, 4, 5]
            k = qwk(xs, ys, cats)
        else:
            k = cohen_kappa(xs, ys)
        out["questions"][q] = {"n": len(pairs), "kind": kind,
                               "kappa": None if k is None else round(k, 3),
                               "agreement": round(sum(x == y for x, y in pairs) / len(pairs), 3)
                               if pairs else None}
    # amendment 2026-10-12b item 8: per-site agreement on the three levels over the
    # sites of the double-judged T0 packets (Cohen's kappa, descriptive)
    sa: list[str] = []
    sb: list[str] = []
    for i in common:
        pa = (a[i].get("completeness") or {}).get("per_site")
        pb = (b[i].get("completeness") or {}).get("per_site")
        if pa and pb:
            for site in sorted(set(pa) & set(pb)):
                sa.append(pa[site])
                sb.append(pb[site])
    k = cohen_kappa(sa, sb)
    out["per_site"] = {"n_sites": len(sa), "kappa": None if k is None else round(k, 3),
                       "agreement": round(sum(x == y for x, y in zip(sa, sb)) / len(sa), 3)
                       if sa else None}
    if mapping is not None:
        out["n_t0"] = sum(1 for i in common if mapping.get(i, {}).get("kind") == "t0")
    return out


def label_key(m: dict[str, Any]) -> str:
    """tables3's key: ``<agent>/<arm>/<zone>/<chain>/T<k>`` for step and T0 packets;
    chain packets ``.../chain`` and ``.../chain_full`` (tables3 ignores them)."""
    tail = m["step"] if m["kind"] in ("step", "t0") else m["kind"]
    return f"{m['agent']}/{m['cond']}/{m['zone']}/{m['chain']}/{tail}"


def labels_from(judgements: dict[str, dict], mapping: dict[str, dict]) -> dict[str, dict]:
    """The ``--labels`` JSON of ``aa tables3`` (first judge): per step ``t2_reuse``
    (T2), ``one_place`` (T1/T3), ``completeness`` and ``interface`` (T0), plus the
    design scores and flags of every packet."""
    out: dict[str, dict] = {}
    for pid, j in sorted(judgements.items()):
        m = mapping.get(pid)
        if m is None:
            raise JudgementError(f"judgement for unknown packet {pid}")
        lab: dict[str, Any] = {"packet": pid, "kind": m["kind"]}
        if "t2_reuse" in j:
            lab["t2_reuse"] = j["t2_reuse"]
        if "one_place" in j:
            lab["one_place"] = bool(j["one_place"]["value"])
        if "completeness" in j:
            lab["completeness"] = j["completeness"]["value"]
            for k in ("lenient", "strict"):
                if k in j["completeness"]:
                    lab[f"completeness_{k}"] = j["completeness"][k]
        if "interface" in j:
            lab["interface"] = j["interface"]["score"]
        for d in DIMS:
            if d in j:
                lab[d] = j[d]["score"]
        for k in ("bypasses_abstraction", "disguised_duplication"):
            if k in j:
                lab[k] = bool(j[k]["value"])
        if "duplicated_blocks" in j:
            lab["duplicated_blocks"] = int(j["duplicated_blocks"])
        if "would_merge" in j:
            lab["would_merge"] = j["would_merge"]
        if "abstraction_drift" in j:
            lab["abstraction_drift"] = {k: j["abstraction_drift"][k] for k in (
                "value", "parameters_added", "special_case_branches", "bypassing_call_sites")}
        out[label_key(m)] = lab
    return out


# --------------------------------------------------------------------------- H1 tables

H1_METRICS = DIMS + ("duplicated_blocks",)
LEVERS = ("RG", "RL", "RC")
SCOPES = {"all": ("Z1", "Z2", "Z3", "Z4"), "without_Z4": ("Z1", "Z2", "Z3"),
          "non_blind": ("Z1", "Z3")}


def h1_rows(judgements: dict[str, dict], mapping: dict[str, dict]) -> list[dict]:
    rows = []
    for pid, j in judgements.items():
        m = mapping[pid]
        row = {"id": pid, "kind": m["kind"], "agent": m["agent"], "cond": m["cond"],
               "zone": m["zone"], "chain": m["chain"], "step": m.get("step")}
        for d in DIMS:
            row[d] = j[d]["score"] if d in j else None
        row["duplicated_blocks"] = j.get("duplicated_blocks")
        row["drift"] = (j["abstraction_drift"]["value"] if "abstraction_drift" in j else None)
        rows.append(row)
    return rows


def compare(arm_rows: list[dict], ref_rows: list[dict], metric: str,
            zones: tuple[str, ...]) -> dict[str, Any]:
    """arm vs reference on ``metric``: means, medians, Mann-Whitney, per-zone sign test."""
    from statistics import mean, median

    from aa.stats import mann_whitney_u
    from aa.tables2 import sign_test
    a = [r[metric] for r in arm_rows if r["zone"] in zones and r[metric] is not None]
    b = [r[metric] for r in ref_rows if r["zone"] in zones and r[metric] is not None]
    hi = lo = 0
    for z in zones:
        za = [r[metric] for r in arm_rows if r["zone"] == z and r[metric] is not None]
        zb = [r[metric] for r in ref_rows if r["zone"] == z and r[metric] is not None]
        if za and zb:
            diff = mean(za) - mean(zb)
            hi += diff > 0
            lo += diff < 0
    return {"n_arm": len(a), "n_ref": len(b),
            "mean_arm": round(mean(a), 3) if a else None,
            "mean_ref": round(mean(b), 3) if b else None,
            "median_arm": median(a) if a else None, "median_ref": median(b) if b else None,
            "mw_p": round(mann_whitney_u(a, b)[1], 4) if a and b else None,
            "zones_higher": hi, "zones_lower": lo,
            "sign_p": round(sign_test(hi, lo), 4)}


def h1_tables(rows: list[dict]) -> dict[str, Any]:
    """Per agent, each lever arm vs R and vs F, on chain packets (primary: RC from its T0
    tree; ``chain_full`` for RC secondary), every metric, all zones / without Z4, and
    RL's confirmatory non-blind Z1+Z3. Step packets by arm, descriptive."""
    out: dict[str, Any] = {}
    agents = sorted({r["agent"] for r in rows})
    for agent in agents:
        g = [r for r in rows if r["agent"] == agent]
        chain = [r for r in g if r["kind"] == "chain"]
        ref = {"R": [r for r in chain if r["cond"] == "R"],
               "F": [r for r in chain if r["cond"] == "F"]}
        res: dict[str, Any] = {}
        for arm in LEVERS:
            arm_rows = [r for r in chain if r["cond"] == arm]
            scopes = ["all", "without_Z4"] + (["non_blind"] if arm == "RL" else [])
            res[arm] = {vs: {sc: {m: compare(arm_rows, ref[vs], m, SCOPES[sc])
                                  for m in H1_METRICS} for sc in scopes}
                        for vs in ("R", "F")}
        full = [r for r in g if r["kind"] == "chain_full" and r["cond"] == "RC"]
        res["RC_T0_T4_secondary"] = {sc: {m: compare(full, ref["R"], m, SCOPES[sc])
                                          for m in H1_METRICS}
                                     for sc in ("all", "without_Z4")}
        res["R_vs_F"] = {m: compare(ref["R"], ref["F"], m, SCOPES["all"]) for m in H1_METRICS}
        steps = [r for r in g if r["kind"] == "step"]
        res["steps_descriptive"] = {
            arm: {f"T{k}": compare([r for r in steps if r["cond"] == arm and r["step"] == f"T{k}"],
                                   [r for r in steps if r["cond"] == "R" and r["step"] == f"T{k}"],
                                   "maintainability", SCOPES["all"])
                  for k in range(1, 5)}
            for arm in LEVERS}
        out[agent] = res
    return out


def render_h1(rel: dict[str, Any], tables: dict[str, Any]) -> str:
    lines = ["# Study 3 design review (H1)", "",
             f"## Reliability (second judge, {rel['n_packets']} packets"
             + (f", {rel['n_t0']} T0" if "n_t0" in rel else "") + ")", "",
             "| question | n | kappa | kind | raw agreement |", "|---|---|---|---|---|"]
    for q, v in rel["questions"].items():
        lines.append(f"| {q} | {v['n']} | {v['kappa']} | {v['kind']} | {v['agreement']} |")
    lines.append("")
    for agent, res in tables.items():
        lines += [f"## {agent}", "", "Chain packets (T1–T4 diff; RC from its T0 tree). "
                  "Primary: maintainability.", "",
                  "| arm | vs | scope | metric | arm mean (n) | ref mean (n) | MW p | zones +/− "
                  "| sign p |", "|---|---|---|---|---|---|---|---|---|"]
        for arm in LEVERS:
            for vs, by_scope in res[arm].items():
                for sc, by_m in by_scope.items():
                    for m, c in by_m.items():
                        lines.append(
                            f"| {arm} | {vs} | {sc} | {m} | {c['mean_arm']} ({c['n_arm']}) | "
                            f"{c['mean_ref']} ({c['n_ref']}) | {c['mw_p']} | "
                            f"{c['zones_higher']}/{c['zones_lower']} | {c['sign_p']} |")
        lines += ["", "RC T0..T4 (secondary) vs R:", ""]
        for sc, by_m in res["RC_T0_T4_secondary"].items():
            c = by_m["maintainability"]
            lines.append(f"- {sc}: maintainability {c['mean_arm']} ({c['n_arm']}) vs "
                         f"{c['mean_ref']} ({c['n_ref']}), MW p={c['mw_p']}")
        lines.append("")
    lines.append("Nothing near p = 0.05 is read as an effect on its own.")
    return "\n".join(lines) + "\n"


KAPPA_MEASURES = ("t2_reuse", "one_place", "completeness", "interface")


def flat_kappa(rel: dict[str, Any]) -> dict[str, float | None]:
    """The ``aa tables3 --kappa`` JSON: {judged measure: kappa} (:data:`KAPPA_MEASURES`)."""
    return {q: rel["questions"].get(q, {}).get("kappa") for q in KAPPA_MEASURES}


def second_sample(batches_path: Path | None) -> list[str] | None:
    try:
        b = json.loads(Path(batches_path).read_text()) if batches_path else None
    except (OSError, ValueError):
        return None
    return None if b is None else [i for x in b.get("second", []) for i in x]


def analyse(scores: Path, scores2: Path, mapping_path: Path, *, labels_out: Path | None = None,
            out_md: Path | None = None, kappa_out: Path | None = None,
            batches: Path | None = None, allow_no_kappa: bool = False) -> dict[str, Any]:
    """Kappa FIRST (written to ``kappa_out`` as the flat JSON ``aa tables3 --kappa``
    reads); then, only when the second judge has scored its whole planned sample (the
    ``second`` batches of ``batches``; without a batch file, at least one packet), the
    labels for tables3 and the H1 tables. Otherwise nothing but the kappa is written and
    the comparisons are refused, unless ``allow_no_kappa``."""
    mapping = json.loads(Path(mapping_path).read_text())
    a, b = load_judgements(scores), load_judgements(scores2)
    rel = reliability(a, b, mapping)
    result: dict[str, Any] = {"reliability": rel, "kappa": flat_kappa(rel)}
    if kappa_out is not None:
        Path(kappa_out).parent.mkdir(parents=True, exist_ok=True)
        Path(kappa_out).write_text(json.dumps(result["kappa"], indent=2) + "\n")
    planned = second_sample(batches)
    refused = None
    if planned is not None:
        missing = sorted(set(planned) - (set(a) & set(b)))
        rel["second_planned"], rel["second_missing"] = len(planned), len(missing)
        if missing:
            refused = (f"second-judge sample incomplete: {len(missing)}/{len(planned)} "
                       "planned packets lack both judgements; kappa must be complete "
                       "before comparisons")
    elif rel["n_packets"] == 0:
        refused = "no second-judge overlap: kappa must be reported before comparisons"
    if refused and not allow_no_kappa:
        result["h1"] = None
        result["refused"] = refused
        return result
    if labels_out is not None:
        Path(labels_out).parent.mkdir(parents=True, exist_ok=True)
        Path(labels_out).write_text(json.dumps(labels_from(a, mapping), indent=2) + "\n")
    result["h1"] = h1_tables(h1_rows(a, mapping))
    if out_md is not None:
        Path(out_md).parent.mkdir(parents=True, exist_ok=True)
        Path(out_md).write_text(render_h1(rel, result["h1"]))
    return result
