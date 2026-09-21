#!/usr/bin/env python3
"""Package source and already-redacted results for the local article download."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments/prompt-meaning"
TARGET = ROOT / "public/downloads/prompt-meaning-pilots.zip"


def main():
    # Only these public directories and extensions; never recurse into runs/.
    files = {EXPERIMENT / ".gitignore"}
    for directory, patterns in [
        (EXPERIMENT, ("*.py", "*.md", "config*.example.json")),
        (EXPERIMENT / "tests", ("*.py",)),
        (EXPERIMENT / "v2", ("*.py", "*.md")),
        (EXPERIMENT / "results/pilot-2026-09-21", ("*.json", "*.md")),
        (EXPERIMENT / "v2/results/pilot-2026-09-21-v2", ("*.json", "*.md")),
        (EXPERIMENT / "v3", ("*.py", "*.md")),
        (EXPERIMENT / "v3/results/pilot-2026-09-21-v3", ("*.json", "*.md", "*.png")),
        (EXPERIMENT / "v4", ("*.py", "*.md", "UPSTREAM-LICENSE.txt")),
        (EXPERIMENT / "v4/sources", ("*.py", "*.md", "manifest.json")),
        (EXPERIMENT / "v4/results", ("*.json", "*.md")),
    ]:
        for pattern in patterns:
            files.update(directory.glob(pattern))
    files.discard(EXPERIMENT / "v2/results/pilot-2026-09-21-v2/article-review.md")
    files.add(ROOT / "docs/superpowers/specs/2026-09-21-invented-terminology-design.md")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(TARGET, "w", ZIP_DEFLATED) as bundle:
        for path in sorted(files):
            assert path.is_file() and not path.is_symlink()
            bundle.write(path, path.relative_to(ROOT))
    with ZipFile(TARGET) as bundle:
        assert bundle.testzip() is None
        assert not any("runs" in Path(name).parts for name in bundle.namelist())
    print(f"Packaged {len(files)} public files: {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
