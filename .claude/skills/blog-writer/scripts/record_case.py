#!/usr/bin/env python3
"""Keep a finished article (or article video) as a test case for the skills.

Claude Code deletes session transcripts after cleanupPeriodDays (30 by default), and with them the
only record of what Javier asked for and what he corrected. This script copies that record out of
the transcripts while they still exist, so the skills can later be replayed against real cases:

  python3 record_case.py there-is-no-best-model                 # article
  python3 record_case.py there-is-no-best-model --kind video    # its video script

It finds the first draft (the first Write of src/content/blog/en/<slug>.md, or of a
video/<slug>/script.md or examples/<slug>/script.md), the session that wrote it, every message
Javier sent in that session before and after it (typed, queued, Telegram), and the main commit the
first draft was written against. Output: ~/Documents/experiment-data/skill-cases/<kind>/<slug>.json (private: his
messages can carry work material, so this never goes into the public repo).
"""
import argparse
import glob
import json
import os
import re
import subprocess
import time

from session_brief import messages

OUT = os.path.expanduser('~/Documents/experiment-data/skill-cases')


def first_write(slug, kind):
    pat = (re.compile(rf'src/content/blog/en/{re.escape(slug)}\.md$') if kind == 'article'
           else re.compile(rf'(video|examples)/{re.escape(slug)}/script\.md$'))
    best = None
    # Main sessions and their subagents (scripts are often written by workflow agents); skip
    # throwaway sessions run from temporary folders (replays, experiments).
    files = glob.glob(os.path.expanduser('~/.claude/projects/*/*.jsonl')) + \
        glob.glob(os.path.expanduser('~/.claude/projects/*/*/subagents/**/*.jsonl'), recursive=True)
    for f in (f for f in files if '-private-tmp-' not in f):
        with open(f, 'rb') as fh:
            if slug.encode() not in fh.read():
                continue
        for line in open(f, errors='ignore'):
            if '"Write"' not in line or slug not in line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not d.get('timestamp'):
                continue
            for x in d.get('message', {}).get('content', []) or []:
                if isinstance(x, dict) and x.get('type') == 'tool_use' and x.get('name') == 'Write' \
                        and pat.search(x.get('input', {}).get('file_path', '')):
                    if not best or d['timestamp'] < best[0]:
                        best = (d['timestamp'], parent_session(f))
    return best


def parent_session(f):
    """A subagent transcript lives under <project>/<session>/subagents/; its messages from Javier
    are in <project>/<session>.jsonl."""
    parts = f.split(os.sep)
    if 'subagents' in parts:
        i = parts.index('subagents')
        return os.sep.join(parts[:i - 1] + [parts[i - 1] + '.jsonl'])
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slug')
    ap.add_argument('--kind', choices=('article', 'video'), default='article')
    a = ap.parse_args()
    found = first_write(a.slug, a.kind)
    if not found:
        raise SystemExit(f'no first draft of {a.slug} ({a.kind}) in the transcripts still on disk')
    ts, f = found
    msgs = list(messages(f))
    before = [dict(ts=t, kind=k, text=x) for t, k, x in msgs if t <= ts[:16]]
    after = [dict(ts=t, kind=k, text=x) for t, k, x in msgs if t > ts[:16]]
    # The state of main right before the first draft: the article is not on it yet.
    base = subprocess.run(['git', 'rev-list', '-1', f'--before={ts}', 'origin/main'],
                          capture_output=True, text=True).stdout.strip() if a.kind == 'article' else None
    case = dict(slug=a.slug, kind=a.kind, session=os.path.basename(f)[:-6], first_draft_ts=ts,
                base_commit=base, before=before, after=after,
                recorded_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    os.makedirs(f'{OUT}/{a.kind}', exist_ok=True)
    path = f'{OUT}/{a.kind}/{a.slug}.json'
    json.dump(case, open(path, 'w'), ensure_ascii=False, indent=1)
    print(f'{path}: {len(before)} messages before the first draft, {len(after)} after (base {(base or '-')[:8]})')


if __name__ == '__main__':
    main()
