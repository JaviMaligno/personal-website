"""Ask Claude models YouGov's random-number question through the Claude Code CLI.

Each call is a fresh, non-persisted `claude -p` session with customisations off
(--safe-mode, project settings only, run from an empty directory), no tools and
a one-line system prompt. What the model still receives besides the question is
Claude Code's environment block (working directory, platform, date).

Usage: python run_cli.py <empty_workdir> <n> [model ...]
Writes results/claude-<model>.json next to this file.
"""
import json
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROMPT = ("Think of a random number from 1-10. What number did you think of? "
          "Answer with the number only.")
MODELS = ["haiku", "sonnet", "opus"]


def parse(text):
    m = re.search(r"\b(10|[1-9])\b", text or "")
    return int(m.group(1)) if m else None


def ask(model, workdir):
    r = subprocess.run(
        ["claude", "-p", "--safe-mode", "--setting-sources", "project", "--model", model,
         "--system-prompt", "You are a helpful assistant.", "--tools", "",
         "--no-session-persistence", PROMPT],
        cwd=workdir, capture_output=True, text=True, encoding="utf-8", timeout=180)
    return parse(r.stdout)


def main():
    workdir = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    models = sys.argv[3:] or MODELS
    outdir = Path(__file__).with_name("results")
    outdir.mkdir(exist_ok=True)
    for model in models:
        with ThreadPoolExecutor(2) as ex:
            answers = list(ex.map(lambda _: ask(model, workdir), range(n)))
        counts = Counter(a for a in answers if a is not None)
        out = {"prompt": PROMPT, "n": n, "via": "claude -p (Claude Code CLI)", "model": model,
               "answers": answers,
               "counts": {str(k): counts.get(k, 0) for k in range(1, 11)},
               "unparsed": answers.count(None)}
        print(model, dict(sorted(counts.items())), "unparsed:", answers.count(None), flush=True)
        (outdir / f"claude-{model}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
