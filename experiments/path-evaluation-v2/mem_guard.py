"""Log free memory every minute; if it stays under a floor, ask one runner to stop.

    uv run python mem_guard.py b

Writes runs/mem.log. After 3 consecutive samples under 1500 MB it creates runs/STOP-<world>, which
run.py checks before each episode (the current episode finishes; nothing is killed). Exits when no
run.py is alive any more.
"""
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
FLOOR_MB, STRIKES = 1500, 3
world = sys.argv[1]


def free_mb() -> int:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"],
                         capture_output=True, text=True).stdout.strip()
    return int(out) // 1024


def runners_alive() -> bool:
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | Where-Object { $_.CommandLine -like '*run.py*' }).Count"],
                         capture_output=True, text=True).stdout.strip()
    return out not in ("", "0")


strikes = 0
log = HERE / "runs" / "mem.log"
while runners_alive():
    mb = free_mb()
    strikes = strikes + 1 if mb < FLOOR_MB else 0
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M} free={mb}MB strikes={strikes}\n")
    if strikes >= STRIKES:
        (HERE / "runs" / f"STOP-{world}").write_text(f"free memory under {FLOOR_MB} MB {STRIKES} times\n")
    time.sleep(60)
