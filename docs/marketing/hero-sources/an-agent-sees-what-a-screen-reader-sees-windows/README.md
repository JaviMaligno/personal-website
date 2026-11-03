# Follow-up: the same accessibility census on Windows

**Status:** not started. Picked up from PR #191 (the macOS article, published 2026-11-05).
**Goal:** a follow-up article — *same agent, same apps, two operating systems: how much does it see on each?*

## Why it isn't just a re-run
On macOS agent-desktop reads the AX tree (what VoiceOver reads). On Windows it reads **UI Automation**
(what Narrator/NVDA read): different API, different role mapping, and the apps change toolkit
(Telegram is native Swift on macOS but Qt on Windows; Office, Notepad, Explorer are their own stacks).
Expected: Electron/Chromium apps (Slack, Spotify, ChatGPT, Claude, Cursor, Postman) come out similar
because Chromium exposes the same tree on both; the real differences should be the native and Qt/Java
apps and the cases that were empty on macOS (Android emulator = 1 element, Docker Desktop = timeout).
The article is worth writing if the numbers move; if they don't, that's a short "it's the toolkit, not the OS" note.

## Steps (on the Windows machine)
1. Install agent-desktop **1.0.2** (same version as the macOS run) and check: `agent-desktop --version`,
   `agent-desktop skills get platform` (read it: Windows specifics), `agent-desktop snapshot -i` on any app.
2. Check the app names: open each app once, `agent-desktop list-apps`, fix `ax_name` in `apps-windows.txt`,
   comment out what isn't installed. Close them again.
3. Quiet machine (no heavy jobs; on macOS a loaded machine gave APP_UNRESPONSIVE and timeouts).
4. Run: `python -I census_windows.py --out census-windows-YYYY-MM-DD.csv`
   It opens each app that wasn't running, measures 3 times and **closes it straight away**. Apps already open
   are measured and left open. Only counts are saved, never names or UI text.
5. Android emulator: start the same AVD by hand, then
   `python -I census_windows.py --only qemu-system-x86_64` (check the process name with `list-apps`), then stop it.
6. Copy the CSV next to this README and commit it on a new branch from `main`.

## Comparison to build afterwards
- Per app, macOS vs Windows: nodes, named share, interactive count (median of the 3 runs).
  macOS data: `../an-agent-sees-what-a-screen-reader-sees-census.csv`; chart script `../an-agent-sees-what-a-screen-reader-sees-census.py`.
- Group by toolkit (column `toolkit`): does the gap follow the OS or the toolkit?
- Re-check on Windows the practical findings from the macOS article (menus disabled when the app isn't in
  front, file dialogs in another process, only the visible desktop is seen) — note which hold.
- Optional: the article's task (collage → Telegram "To my phone") once on Windows, to see whether Telegram-Qt
  is as operable as Telegram-Swift.

## Rules
- Close every app the script opened (it does it; check nothing is left behind).
- Don't capture private content: metrics only; screenshots only of neutral windows.
- Measure warm: an app just launched can look empty (ChatGPT on macOS did). If a row looks suspiciously
  small, re-run that app alone after it has fully loaded.
