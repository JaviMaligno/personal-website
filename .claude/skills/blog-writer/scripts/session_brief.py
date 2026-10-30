#!/usr/bin/env python3
"""Collect everything Javier said about an article, across the Claude Code sessions that touched it.

Compaction drops early messages from the agent's context, and messages sent while the agent was
working arrive as attachments that are easy to miss. Both stay in the session JSONL files, so this
script reads them back: typed messages, queued messages and Telegram messages, in order.

Usage:
  python3 session_brief.py far-points-are-not-ideas steam "latent gap"   # any term matches
  python3 session_brief.py --days 60 --max-chars 600 pareto
  python3 session_brief.py --until 2026-10-30T11:42 pareto      # the brief as it stood then

A session is included when any term appears in it (case-insensitive). Output is grouped by session,
oldest first, one line per message: timestamp, kind (typed/queued/telegram) and the text.
"""
import argparse
import glob
import json
import os
import re
import time

QUEUED = 'The user sent a new message while you were working:'


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ' '.join(x.get('text', '') for x in content if isinstance(x, dict) and x.get('type') == 'text')
    return ''


def messages(path):
    for line in open(path, errors='ignore'):
        # Only user turns and queued commands can hold his words; tool results are the bulk.
        if not ('"type":"user"' in line or 'queued_command' in line) or '"tool_use_id"' in line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get('isSidechain') or d.get('isMeta'):
            continue
        ts = (d.get('timestamp') or '')[:16]
        if d.get('type') == 'user':
            t = text_of(d.get('message', {}).get('content')).strip()
            if t.startswith('<channel source="telegram'):
                yield ts, 'telegram', re.sub(r'<[^>]+>', '', t).strip()
            elif QUEUED in t:
                yield ts, 'queued', t.split(QUEUED, 1)[1].split('</system-reminder>')[0].strip()
            elif t and not t.startswith(('<', 'This session is being continued')):
                yield ts, 'typed', t
        elif d.get('type') == 'attachment':
            att = d.get('attachment') or {}
            human = (att.get('origin') or {}).get('kind') == 'human' or att.get('humanTurn')
            if att.get('type') == 'queued_command' and human and isinstance(att.get('prompt'), str):
                yield ts, 'queued', att['prompt'].strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('terms', nargs='+')
    ap.add_argument('--days', type=int, default=45)
    ap.add_argument('--max-chars', type=int, default=1500)
    ap.add_argument('--until', default='', help='ISO timestamp (UTC, e.g. 2026-10-30T11:42); later messages are left out')
    a = ap.parse_args()
    since = time.time() - a.days * 86400
    files = [f for f in glob.glob(os.path.expanduser('~/.claude/projects/*/*.jsonl')) if os.path.getmtime(f) >= since]
    found = []
    # A session counts when a term appears anywhere in it (often in tool output, not in a message).
    # bytes.lower() + `in` runs in C: ~10 s over 1.5 GB, where re.I takes ~40 s and the system
    # grep -i over two minutes.
    terms = [t.lower().encode() for t in a.terms]
    for f in files:
        with open(f, 'rb') as fh:
            data = fh.read().lower()
        if not any(t in data for t in terms):
            continue
        msgs = list(messages(f))
        if msgs:
            found.append((msgs[0][0], f, msgs))
    seen = set()
    for _, f, msgs in sorted(found):
        print(f'\n## {os.path.basename(f)[:8]}  ({os.path.basename(os.path.dirname(f))})')
        for ts, kind, t in msgs:
            if a.until and ts > a.until:
                continue
            key = (ts, t[:80])
            if key in seen:
                continue
            seen.add(key)
            t = t.replace('\n', ' ')
            print(f'- {ts} [{kind}] {t[:a.max_chars]}')


if __name__ == '__main__':
    main()
