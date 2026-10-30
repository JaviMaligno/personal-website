"""Create .testenv: the interpreter that runs humanize's tests for agents and for truth."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ENV = HERE / ".testenv"


def python() -> Path:
    return ENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def main():
    if not python().exists():
        subprocess.run(["uv", "venv", "-q", "--python", "3.13", str(ENV)], check=True)
        subprocess.run(["uv", "pip", "install", "-q", "--python", str(ENV), "pytest", "freezegun"], check=True)
    print(python())


if __name__ == "__main__":
    main()
