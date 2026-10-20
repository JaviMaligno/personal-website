"""Study 3 arm images, rebuilt together and verified (re-review LOW finding: freshness).

R was built for study 2 (2026-10-08) and RG/RL/RC days later; the install step
(``install-lint-deps.sh``) resolves the eslint devDependencies from the registry at
build time, so images built on different days may differ in ``yarn.lock`` /
``node_modules`` and not only in their lever. :func:`build_study3` rebuilds the four
arms in one go:

1. the study-2 R image is kept under :data:`PRESERVED_R_TAG` (runs2 used it);
2. every arm's variant is rebuilt from BASE + its patches (``aa variant build``) and
   RC's variant tree must equal R's (RC = R, spec section 2);
3. the images are built in sequence on one cached ``cli`` stage (Node, agent CLIs)
   with the install stages rebuilt without cache (``--no-cache-filter``), so the
   four installs run minutes apart against the same registry state;
4. each image is inspected in a throwaway container (one at a time): the git tree of
   ``/work/actual`` as committed and as installed, ``yarn.lock``, the yarn install
   state, a per-file hash listing of every ``node_modules`` and of the global npm
   tree (agent CLIs, jscpd), and the global package versions;
5. the manifest ``out/study3/images.json`` records the image ids and the checks:
   RC's trees equal R's; ``yarn.lock``, ``node_modules`` and the global tree are
   identical across arms; the worktree differs from R's only in the arm's lever
   files (the paths its study-3 patch touches).

Listings go to ``work/study3/images/<arm>/`` (large, not committed).
"""
from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path

from aa import config, runner

ARMS: tuple[str, ...] = tuple(config.CONDITIONS3)
MANIFEST = config.ROOT / "out" / "study3" / "images.json"
LISTINGS = config.WORK / "study3" / "images"
PRESERVED_R_TAG = "aa-actual:R-study2"
# Rebuilt without cache; `cli` (apt, agent CLIs) stays cached and shared by all arms.
NO_CACHE_STAGES = ("actual", "study2")
GLOBAL_PACKAGES = ("@anthropic-ai/claude-code", "@openai/codex", "jscpd")
DIFF_SAMPLE = 20

# Runs in the image as its user; writes listings to /o. Read-only on the image's tree
# (the installed tree is hashed through a temporary index).
INSPECT_SCRIPT = r"""
set -euo pipefail
cd /work/actual
O=/o
{
  echo "variant_tree=$(git rev-parse 'HEAD^{tree}')"
  I=$(mktemp -u)
  echo "worktree_tree=$(GIT_INDEX_FILE=$I git add -A >/dev/null 2>&1 && GIT_INDEX_FILE=$I git write-tree)"
  rm -f "$I"
  echo "yarn_lock_sha256=$(sha256sum yarn.lock | cut -d' ' -f1)"
  echo "yarn_state_sha256=$(sha256sum node_modules/.yarn-state.yml | cut -d' ' -f1)"
} > "$O/facts.txt"
git ls-files -co --exclude-standard -z | sort -z | xargs -0 sha256sum > "$O/worktree.txt"
find . -path ./.git -prune -o -type d -name node_modules -prune -print | sort > "$O/nm_dirs.txt"
xargs -a "$O/nm_dirs.txt" -I{} find {} -type f -print0 | sort -z | xargs -0 sha256sum \
  > "$O/node_modules.txt"
xargs -a "$O/nm_dirs.txt" -I{} find {} -type l -printf '%p -> %l\n' | sort > "$O/node_modules_links.txt"
G=$(npm root -g)
(cd "$G" && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "$O/global.txt"
npm ls -g --depth=0 --json > "$O/npm_global.json" || true
"""


# --------------------------------------------------------------------------- pure parts

def parse_facts(text: str) -> dict[str, str]:
    return dict(ln.split("=", 1) for ln in text.splitlines() if "=" in ln)


def parse_listing(text: str) -> dict[str, str]:
    """``sha256sum`` output -> {path: sha} (paths normalised without a leading ./)."""
    out: dict[str, str] = {}
    for ln in text.splitlines():
        if not ln.strip():
            continue
        sha, sep, path = ln.partition("  ")
        if not sep:  # binary mode ("<sha> *<path>")
            sha, _, path = ln.partition(" *")
        out[path.removeprefix("./")] = sha
    return out


def listing_diff(ref: dict[str, str], other: dict[str, str]) -> list[str]:
    """Paths whose content differs, or that exist on one side only (sorted)."""
    return sorted(p for p in set(ref) | set(other) if ref.get(p) != other.get(p))


def patch_paths(patch: Path) -> set[str]:
    """Paths a git patch touches (both sides of ``diff --git``)."""
    out: set[str] = set()
    for ln in patch.read_text().splitlines():
        if ln.startswith("diff --git "):
            a, _, b = ln[len("diff --git "):].partition(" b/")
            out |= {a.removeprefix("a/"), b}
    return out


def lever_files(arm: str, patches: dict[str, tuple[str, ...]] | None = None,
                patch_dir: Path | None = None) -> set[str]:
    """Files an arm's own patches touch beyond R's (its lever): RG's AGENTS.md, RL's
    dup-check and lint wiring, none for RC."""
    patches = patches or config.CONDITION_PATCHES
    patch_dir = patch_dir or config.PATCHES
    extra = [p for p in patches[arm] if p not in patches["R"]]
    return set().union(*(patch_paths(patch_dir / p) for p in extra)) if extra else set()


def global_versions(npm_ls: dict) -> dict[str, str | None]:
    deps = npm_ls.get("dependencies") or {}
    return {p: (deps.get(p) or {}).get("version") for p in GLOBAL_PACKAGES}


def check_arms(info: dict[str, dict], listings: dict[str, dict[str, dict[str, str]]],
               levers: dict[str, set[str]], ref: str = "R") -> dict:
    """The manifest's checks. ``info[arm]``: facts + global versions; ``listings[arm]``:
    {"worktree": .., "node_modules": .., "global": ..} as {path: sha}."""
    arms = list(info)
    same = lambda key: len({info[a].get(key) for a in arms}) == 1  # noqa: E731
    out: dict = {
        "rc_variant_tree_equals_r": info.get("RC", {}).get("variant_tree")
        == info[ref].get("variant_tree"),
        "rc_worktree_tree_equals_r": info.get("RC", {}).get("worktree_tree")
        == info[ref].get("worktree_tree"),
        "yarn_lock_identical": same("yarn_lock_sha256"),
        "yarn_state_identical": same("yarn_state_sha256"),
        "global_versions_identical": len({json.dumps(info[a].get("global_versions"),
                                                     sort_keys=True) for a in arms}) == 1,
    }
    for kind in ("node_modules", "global"):
        diffs = {a: listing_diff(listings[ref][kind], listings[a][kind])
                 for a in arms if a != ref}
        out[f"{kind}_identical"] = not any(diffs.values())
        out[f"{kind}_diffs_vs_{ref}"] = {a: {"count": len(d), "sample": d[:DIFF_SAMPLE]}
                                        for a, d in diffs.items()}
    wt = {a: listing_diff(listings[ref]["worktree"], listings[a]["worktree"])
          for a in arms if a != ref}
    out[f"worktree_diffs_vs_{ref}"] = wt
    out["worktree_diffs_are_lever_files"] = all(set(d) == levers.get(a, set())
                                                for a, d in wt.items())
    out["ok"] = all(out[k] for k in ("rc_variant_tree_equals_r", "rc_worktree_tree_equals_r",
                                     "yarn_lock_identical", "yarn_state_identical",
                                     "global_versions_identical", "node_modules_identical",
                                     "global_identical", "worktree_diffs_are_lever_files"))
    return out


# --------------------------------------------------------------------------- docker parts

def _docker(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check)


def preserve_study2_r() -> str | None:
    """Tag the current aa-actual:R as PRESERVED_R_TAG unless that tag exists; its id."""
    have = runner.image_digest(PRESERVED_R_TAG)
    if have:
        return have
    cur = runner.image_digest(runner.image_tag("R"))
    if cur:
        _docker("tag", runner.image_tag("R"), PRESERVED_R_TAG)
    return cur


def inspect_image(arm: str, out_dir: Path) -> dict:
    """Run INSPECT_SCRIPT in a throwaway container of aa-actual:<arm>; facts + listings."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.iterdir():
        f.unlink()
    _docker("run", "--rm", "--cpus", runner.CPUS, "--memory", runner.MEMORY, "--network", "none",
            "-v", f"{out_dir.resolve()}:/o", runner.image_tag(arm), "bash", "-c", INSPECT_SCRIPT)
    facts = parse_facts((out_dir / "facts.txt").read_text())
    facts["global_versions"] = global_versions(json.loads((out_dir / "npm_global.json").read_text()))
    facts["image_id"] = runner.image_digest(runner.image_tag(arm))
    return facts


def load_listings(out_dir: Path) -> dict[str, dict[str, str]]:
    return {k: parse_listing((out_dir / f"{k}.txt").read_text())
            for k in ("worktree", "node_modules", "global")}


def build_study3(arms: Iterable[str] = ARMS, *, build: bool = True,
                 manifest: Path = MANIFEST, listings_root: Path = LISTINGS,
                 log: Callable[[str], None] = print) -> dict:
    """Rebuild (unless ``build`` is False) and inspect the study-3 arm images; write
    and return the manifest."""
    from aa.substrate import build_variant
    arms = [a for a in ARMS if a in set(arms)]
    if "R" not in arms:
        raise ValueError("R is the reference arm and must be built with the others")
    previous = {a: runner.image_digest(runner.image_tag(a)) for a in arms}
    preserved = None
    variants: dict[str, dict[str, str]] = {}
    started = datetime.now(timezone.utc).isoformat()
    if build:
        preserved = preserve_study2_r()
        for a in arms:
            v = build_variant(a)
            variants[a] = {
                "commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=v, check=True,
                                         capture_output=True, text=True).stdout.strip(),
                "tree": subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=v, check=True,
                                       capture_output=True, text=True).stdout.strip()}
            log(f"variant {a}: tree {variants[a]['tree']}")
        if "RC" in variants and variants["RC"]["tree"] != variants["R"]["tree"]:
            raise RuntimeError(f"RC variant tree {variants['RC']['tree']} != R's "
                               f"{variants['R']['tree']}")
        for a in arms:
            log(f"building aa-actual:{a}")
            runner.build_image(a, no_cache_stages=NO_CACHE_STAGES)
    info: dict[str, dict] = {}
    listings: dict[str, dict[str, dict[str, str]]] = {}
    for a in arms:  # one container at a time
        log(f"inspecting aa-actual:{a}")
        d = listings_root / a
        info[a] = inspect_image(a, d)
        listings[a] = load_listings(d)
        info[a]["node_modules_files"] = len(listings[a]["node_modules"])
    levers = {a: lever_files(a) for a in arms}
    rec = {
        "built_at": started if build else None,
        "inspected_at": datetime.now(timezone.utc).isoformat(),
        "no_cache_stages": list(NO_CACHE_STAGES) if build else None,
        "images": {a: {"tag": runner.image_tag(a), **info[a],
                       "variant_commit": variants.get(a, {}).get("commit"),
                       "lever_files": sorted(levers[a])} for a in arms},
        "previous_image_ids": previous,
        "preserved": {PRESERVED_R_TAG: preserved} if preserved else {},
        "checks": check_arms(info, listings, levers),
        "listings": str(listings_root.relative_to(config.ROOT))
        if listings_root.is_relative_to(config.ROOT) else str(listings_root),
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(rec, indent=2) + "\n")
    return rec
