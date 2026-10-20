"""Study 3, cross-family judge (exploratory, added 2026-10-18 after the registered review was
read): GPT-6.1 Sol through Codex re-scores the H1 chain packets with the same blind judge
rubric, to test whether the Opus judge prefers code written by its own family (Claude
agents) over Codex's. One `codex exec` per packet, read-only sandbox, cwd = the packet's
packet directory; the pre-change tree is read straight from the bare repository with git
read commands (no checkout: materialising one worktree per packet was CPU-bound under the
host's file scanner). Resumable: an existing output is
skipped.

  uv run python scripts/study3_cross_judge.py [--kind chain] [--workers 4] [--limit N]
      [--ids id1,id2] [--out work/review3/scores_sol]"""
import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from aa import config, review3

R3 = config.ROOT / "work/review3"
MODEL = "gpt-6.1-sol"

PROMPT = """You are a senior TypeScript reviewer judging the DESIGN of a code change. Apply this rubric exactly:

<rubric>
{rubric}
</rubric>

The packet:
- The request the change answers: {packet}/statement.md
- The change: {packet}/diff.patch
- The questions to answer: {packet}/questions.json
- The code tree the change applies to is commit {commit} of the bare git repository {gitdir}. Read it without checking it out, to see which helpers, copies and layers exist BEFORE the change:
    git --git-dir {gitdir} ls-tree -r --name-only {commit} -- <dir>
    git --git-dir {gitdir} show {commit}:<path>
    git --git-dir {gitdir} grep -n -e <pattern> {commit} -- <path or dir>

Read ONLY those packet files and that commit's tree. Do not run tests, builds, git log/diff on the history, or modify anything. Judge design only, not whether the behaviour is correct.

Your final message must be ONLY one JSON object, no prose, no code fence: "id": "{pid}" and exactly the keys questions.json lists, in the shapes the rubric's Output section gives (scores {{"score": 1-5, "why": str}}, flags {{"value": bool, "where": str}}, duplicated_blocks int, would_merge "yes"|"with_changes"|"no", abstraction_drift {{"value": bool, "parameters_added": int, "special_case_branches": int, "bypassing_call_sites": int, "where": str}}, disguised_duplication {{"value": bool, "where": str}})."""


def _ids(kind: str) -> list[str]:
    m = json.loads((config.ROOT / "work/review3-mapping.json").read_text())
    return sorted(k for k, v in m.items() if v["kind"] == kind)


def _parse(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[1]
    a, b = text.find("{"), text.rfind("}")
    return json.loads(text[a:b + 1])


def judge(pid: str, out: Path, rubric: str) -> str:
    dest = out / f"{pid}.json"
    if dest.exists():
        return "skip"
    pk = R3 / "packets" / pid
    repo, commit = pk.joinpath("tree.txt").read_text().split()[:2]
    gitdir = R3 / "trees" / repo
    last = out / f".{pid}.last"
    try:
        t0 = time.time()
        r = subprocess.run(
            ["codex", "exec", "-m", MODEL, "-s", "read-only", "--skip-git-repo-check",
             "--ephemeral", "-C", str(pk), "-o", str(last),
             PROMPT.format(rubric=rubric, packet=pk, pid=pid, commit=commit, gitdir=gitdir)],
            capture_output=True, text=True, timeout=1800, stdin=subprocess.DEVNULL)
        q = json.loads(pk.joinpath("questions.json").read_text())["questions"]
        s = _parse(last.read_text())
        s["id"] = pid
        missing = set(q) - set(s)
        if missing:
            return f"fail missing {sorted(missing)}"
        review3.normalise(s)
        s["_judge"] = {"model": MODEL, "tree_access": "git", "wall_s": round(time.time() - t0, 1)}
        dest.write_text(json.dumps(s, indent=1) + "\n")
        return "ok"
    except Exception as e:  # recorded and retried on the next run
        return f"fail {type(e).__name__}: {str(e)[:200]}"
    finally:
        last.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--kind", default="chain")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids")
    ap.add_argument("--out", type=Path, default=R3 / "scores_sol")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    rubric = (R3 / "judge-rubric.md").read_text()
    ids = a.ids.split(",") if a.ids else _ids(a.kind)
    if a.limit:
        ids = ids[:a.limit]
    with ThreadPoolExecutor(a.workers) as ex:
        for pid, res in zip(ids, ex.map(lambda p: judge(p, a.out, rubric), ids)):
            print(pid, res, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
