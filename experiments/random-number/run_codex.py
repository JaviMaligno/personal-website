"""Ask GPT YouGov's random-number question through the Codex CLI.

Each call is a fresh, ephemeral `codex exec` session in an empty directory with
a read-only sandbox. Codex keeps its own agent system prompt, which cannot be
replaced from the CLI. The model is Codex's default (recorded in the output).

Usage: python run_codex.py <empty_workdir> <n> [model ...]
Writes results/codex-<model>.json next to this file.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROMPT = ("Think of a random number from 1-10. What number did you think of? "
          "Answer with the number only.")


def parse(text):
    m = re.search(r"\b(10|[1-9])\b", text or "")
    return int(m.group(1)) if m else None


def ask(workdir, model=None):
    with tempfile.TemporaryDirectory() as tmp:
        last = Path(tmp) / "last.txt"
        r = subprocess.run(
            [shutil.which("codex"), "exec", "--skip-git-repo-check", "-s", "read-only", "--ephemeral",
             *(["-m", model] if model else []), "-o", str(last), PROMPT],
            cwd=workdir, capture_output=True, text=True, encoding="utf-8", timeout=300)
        model = (re.search(r"^model: (\S+)", r.stdout + r.stderr, re.M) or [None, None])[1]
        return parse(last.read_text(encoding="utf-8") if last.exists() else ""), model


def main():
    workdir = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    outdir = Path(__file__).with_name("results")
    outdir.mkdir(exist_ok=True)
    for requested in sys.argv[3:] or [None]:
        with ThreadPoolExecutor(2) as ex:
            res = list(ex.map(lambda _: ask(workdir, requested), range(n)))
        answers = [a for a, _ in res]
        seen = sorted({m for _, m in res if m})
        model = requested or (",".join(seen) or "codex-default")
        counts = Counter(a for a in answers if a is not None)
        out = {"prompt": PROMPT, "n": n, "via": "codex exec (Codex CLI)", "model": model,
               "reported_models": seen, "answers": answers,
               "counts": {str(k): counts.get(k, 0) for k in range(1, 11)},
               "unparsed": answers.count(None)}
        print(model, dict(sorted(counts.items())), "unparsed:", answers.count(None), flush=True)
        (outdir / f"codex-{model}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
