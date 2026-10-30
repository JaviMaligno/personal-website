from shellcmd import classify, split_segments, unwrap_powershell


def kinds(cmd, root="/w"):
    return [(a["kind"], a["target"]) for a in classify(cmd, root)]


def test_split_on_separators_but_not_inside_quotes():
    assert split_segments("cat a.py; grep -n 'x;y' b.py && ls | head") == ["cat a.py", "grep -n 'x;y' b.py", "ls", "head"]


def test_basic_kinds():
    assert kinds("cat tests/test_issue.py; ls; grep -rn ordinal --include=*.py .") == [
        ("read", "tests/test_issue.py"), ("list", ""), ("search", "")]
    assert kinds("python -m pytest -q tests/test_issue.py") == [("run_tests", "")]
    assert kinds("sed -n 100,140p src/humanize/number.py") == [("read", "src/humanize/number.py")]
    assert kinds("sed -i 's/a/b/' src/x.py") == [("edit", "src/x.py")]
    assert kinds("lean Main.lean") == [("compile", "")]
    assert kinds("git status --short") == [("run_other", "")]


def test_pipeline_counts_its_first_segment_only():
    assert kinds("python -m pytest -q 2>&1 | tail -n 2") == [("run_tests", "")]


def test_powershell_unwrap_and_cmdlets():
    raw = '"C:\\\\Windows\\\\System32\\\\WindowsPowerShell\\\\v1.0\\\\powershell.exe" -Command \'Get-Content tests/test_issue.py; rg -n def src/humanize/number.py\''
    inner = unwrap_powershell(raw)
    assert inner == "Get-Content tests/test_issue.py; rg -n def src/humanize/number.py"
    assert kinds(inner) == [("read", "tests/test_issue.py"), ("search", "")]


def test_heredoc_script_is_one_command_and_comparisons_are_not_redirects():
    cmd = "python - <<'EOF'\nimport humanize\nprint(delta.days >= 5 * 365 / 12)\nx = a > b\nEOF"
    assert kinds(cmd) == [("run_other", "")]
    assert kinds('python -c "print(1 > 0)"') == [("run_other", "")]


def test_real_redirects_are_edits_but_null_sinks_and_fd_dups_are_not():
    assert kinds("echo hi > out.txt") == [("edit", "out.txt")]
    assert kinds("cat > src/a.py <<'EOF'\nx >= 1\nEOF") == [("edit", "src/a.py")]
    assert kinds("ls 2>/dev/null") == [("list", "")]
    assert kinds("python -m pytest -q 2>&1") == [("run_tests", "")]


def test_absolute_paths_become_relative():
    assert kinds("cat /w/src/humanize/number.py", root="/w") == [("read", "src/humanize/number.py")]
