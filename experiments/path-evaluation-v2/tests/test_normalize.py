from pathlib import Path

from normalize import from_claude, from_codex, from_qwen

FIX = Path(__file__).parent / "fixtures"
ROOT = r"C:\Users\Usuario\AppData\Local\Temp\claude\C--Users-Usuario-GitHub-personal-website\10666dcd-b5a2-42dc-8f5f-d2b757da6664\scratchpad\probe-cc"


def seq(actions):
    return [(a["kind"], a["target"]) for a in actions]


def test_claude_code_trace():
    acts = from_claude((FIX / "claude_code_ordinal.jsonl").read_text(encoding="utf-8").splitlines(), ROOT)
    s = seq(acts)
    assert s[0] == ("read", "tests/test_issue.py")
    assert ("edit", "src/humanize/number.py") in s
    assert s[-1] == ("run_tests", "")
    assert s.index(("edit", "src/humanize/number.py")) < len(s) - 1


def test_codex_trace():
    acts = from_codex((FIX / "codex_ordinal.jsonl").read_text(encoding="utf-8").splitlines(), ROOT)
    s = seq(acts)
    assert ("run_tests", "") in s
    assert ("edit", "tests/test_number.py") in s and ("edit", "src/humanize/number.py") in s
    assert s.index(("run_tests", "")) < s.index(("edit", "src/humanize/number.py"))


def test_qwen_steps():
    steps = [{"tool": "read_file", "args": {"path": "src/a.py"}},
             {"tool": "run_command", "args": {"command": "python -m pytest -q"}},
             {"tool": "replace_in_file", "args": {"path": "src/a.py", "old": "x", "new": "y"}}]
    assert seq(from_qwen(steps, "/w")) == [("read", "src/a.py"), ("run_tests", ""), ("edit", "src/a.py")]
