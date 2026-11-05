"""Accessibility census chart for an-agent-sees-what-a-screen-reader-sees.

Input: the CSV next to this file (agent-desktop snapshot of each app's main window, 3 runs,
measured 2026-11-02 on macOS 15.7, Intel MacBook Pro). Only aggregate numbers, no UI text.
Output: public/blog/an-agent-sees-what-a-screen-reader-sees-census.png
"""
import csv, os, statistics as st
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SLUG = 'an-agent-sees-what-a-screen-reader-sees'
NAMES = {'qemu-system-x86_64': 'Android emulator', 'System Settings': 'System Settings',
         'Microsoft Azure Storage Explorer': 'Azure Storage Explorer', 'DB Browser for SQLite': 'DB Browser (SQLite)',
         'Microsoft Excel': 'Excel', 'Microsoft Word': 'Word', 'Docker Desktop': 'Docker Desktop'}

rows = list(csv.DictReader(open(os.path.join(HERE, f'{SLUG}-census.csv'))))
by = {}
for r in rows:
    by.setdefault(r['app'], []).append(r)
data = []
for app, rs in by.items():
    ok = [r for r in rs if r['nodes']]
    if app in ('Figma', 'Cursor'):
        continue  # did not launch from `open -a` on this machine: not measured
    if not ok:
        data.append((NAMES.get(app, app), None, None)); continue
    nodes = [int(r['nodes']) for r in ok]
    named = [float(r['named_ratio']) for r in ok]
    data.append((NAMES.get(app, app), max(nodes) if app == 'ChatGPT' else int(st.median(nodes)), st.median(named)))
data.sort(key=lambda d: -1 if d[1] is None else d[1], reverse=True)  # most exposed on top, no-answer last

BG, FG, MUTED, TEAL, AMBER, SLATE = '#1a1a24', '#e2e8f0', '#94a3b8', '#2dd4bf', '#f59e0b', '#64748b'
fig, ax = plt.subplots(figsize=(10, 8.4), dpi=150)
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
cmap = matplotlib.colors.LinearSegmentedColormap.from_list('n', [AMBER, '#a3a35a', TEAL])
for i, (name, n, named) in enumerate(data):
    y = len(data) - 1 - i
    if n is None:
        ax.text(1.15, y, 'no answer in 45 s', va='center', color=MUTED, fontsize=10, style='italic')
    elif n <= 1:
        ax.barh(y, n, color=SLATE, height=0.66)
        ax.text(1.15, y, '1 element: the window itself', va='center', color=MUTED, fontsize=10, style='italic')
    else:
        ax.barh(y, n, color=cmap(named), height=0.66)
        ax.text(n * 1.08, y, f'{n:,}  ·  {named*100:.0f}% named', va='center', color=FG, fontsize=9.5)
ax.set_yticks(range(len(data))); ax.set_yticklabels([d[0] for d in reversed(data)], color=FG, fontsize=10.5)
ax.set_xscale('log'); ax.set_xlim(0.8, 20000)
ax.tick_params(axis='x', colors=MUTED); ax.tick_params(axis='y', length=0)
for s in ax.spines.values(): s.set_visible(False)
ax.grid(axis='x', color='#ffffff', alpha=0.07)
ax.set_xlabel('elements in the main window\'s accessibility tree (log scale)', color=MUTED, fontsize=10)
ax.set_title('What an agent can read in each app', color=FG, fontsize=15, loc='left', pad=14, fontweight='bold')
fig.text(0.012, 0.012, 'agent-desktop snapshot, median of 3 reads, macOS 15.7 · bar colour: share of elements with a name (amber low → teal high) · ChatGPT: 12 when cold, 406 loaded',
         color=MUTED, fontsize=8)
fig.tight_layout(rect=(0, 0.02, 1, 1))
out = os.path.join(ROOT, 'public', 'blog', f'{SLUG}-census.png')
fig.savefig(out, facecolor=BG); print(out)
