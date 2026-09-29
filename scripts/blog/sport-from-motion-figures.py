"""Figures for the sport-from-motion article. Aggregate data only.

Numbers come from the experiment's final results (pre-registered run, 400 clips,
4 sports): https://github.com/JaviMaligno/sport-from-motion/blob/main/docs/results-final.md
Run: python scripts/blog/sport-from-motion-figures.py
"""
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parents[2] / 'public' / 'blog'
BG, FG, MUTED, TEAL, AMBER, SLATE = '#1a1a24', '#f8fafc', '#94a3b8', '#2dd4bf', '#fbbf24', '#64748b'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'text.color': FG,
                     'axes.labelcolor': FG, 'xtick.color': MUTED, 'ytick.color': FG,
                     'axes.facecolor': BG, 'figure.facecolor': BG, 'savefig.facecolor': BG,
                     'axes.edgecolor': SLATE})

MODELS = ['GPT-5.6 Sol', 'GPT-5.6 Terra', 'Claude Opus 5.5', 'Claude Sonnet 5', 'Gemini 3.1 Pro']

# motion/sheet: raw accuracy, prior-corrected accuracy and its 95% CI (results-final §6, §7.1)
RAW = [0.42, 0.38, 0.47, 0.28, 0.32]
PC = [0.44, 0.40, 0.47, 0.26, 0.32]
PC_CI = [(0.38, 0.52), (0.32, 0.47), (0.39, 0.57), (0.20, 0.30), (0.26, 0.39)]
SPEC = [('MiniRocket', 0.83, (0.80, 0.87)), ('DeepSets', 0.80, (0.76, 0.85))]

# order = motion - motion_shuffled, 4 s primary (§5) and 8 s exploratory without NFL (§9)
ORDER4 = [(0.01, -0.04, 0.06), (0.005, -0.05, 0.06), (0.10, 0.05, 0.16), (-0.02, -0.06, 0.03),
          (-0.01, -0.06, 0.05)]
ORDER8 = [(0.08, 0.01, 0.16), (0.03, -0.02, 0.09), (0.08, 0.02, 0.14), (0.01, -0.04, 0.07),
          (0.01, -0.06, 0.09)]
MR4, MR8 = (0.12, 0.07, 0.16), (0.11, 0.07, 0.16)

# recall on motion/sheet by sport (§7.2)
RECALL = [[0.92, 0.21, 0.07, 0.49], [0.53, 0.35, 0.06, 0.58], [0.85, 0.19, 0.04, 0.79],
          [0.01, 0.22, 0.15, 0.73], [0.88, 0.08, 0.11, 0.19], [0.90, 0.83, 0.79, 0.81]]


def txt(lang, es, en):
    return es if lang == 'es' else en


def accuracy(lang):
    fig, ax = plt.subplots(figsize=(10, 5.6))
    names = MODELS + [s[0] for s in SPEC]
    y = np.arange(len(names))[::-1]
    for i, yy in enumerate(y[:5]):
        lo, hi = PC_CI[i]
        ax.plot([lo, hi], [yy, yy], color=TEAL, lw=2.5, alpha=.6)
        ax.scatter(PC[i], yy, color=TEAL, s=70, zorder=3,
                   label=txt(lang, 'corregida por sesgo', 'bias-corrected') if i == 0 else None)
        ax.scatter(RAW[i], yy, facecolor='none', edgecolor=MUTED, s=60, zorder=3,
                   label=txt(lang, 'bruta', 'raw') if i == 0 else None)
    for (n, v, (lo, hi)), yy in zip(SPEC, y[5:]):
        ax.plot([lo, hi], [yy, yy], color=AMBER, lw=2.5, alpha=.6)
        ax.scatter(v, yy, color=AMBER, s=70, zorder=3)
    ax.axvline(0.25, color=MUTED, ls='--', lw=1)
    ax.text(0.255, y[-1] - 0.35, txt(lang, 'azar', 'chance'), color=MUTED, fontsize=10)
    ax.axhline(y[5] + 0.5, color=SLATE, lw=.8)
    ax.text(0.99, y[4] - 0.45, txt(lang, 'modelos frontera, sin entrenar', 'frontier models, zero-shot'),
            color=TEAL, fontsize=10, ha='right', transform=ax.get_yaxis_transform())
    ax.text(0.99, y[5] + 0.3, txt(lang, 'especialistas entrenados', 'trained specialists'),
            color=AMBER, fontsize=10, ha='right', transform=ax.get_yaxis_transform())
    ax.set_yticks(y, names)
    ax.set_xlim(0.1, 0.95)
    ax.set_xlabel(txt(lang, 'Exactitud (4 deportes, 8 instantes en orden)',
                      'Accuracy (4 sports, 8 snapshots in order)'))
    ax.set_title(txt(lang, 'Los especialistas reconocen el deporte; los modelos frontera, a medias',
                     'Specialists recognise the sport; frontier models only partly'),
                 fontsize=14, loc='left', pad=12)
    ax.legend(loc='upper right', frameon=False, fontsize=10)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / f'sport-from-motion-accuracy-{lang}.png', dpi=110)
    plt.close(fig)


def order(lang):
    fig, ax = plt.subplots(figsize=(10, 6.2))
    names = MODELS + ['MiniRocket']
    y = np.arange(len(names))[::-1].astype(float)
    rows4 = ORDER4 + [MR4]
    rows8 = ORDER8 + [MR8]
    for i, yy in enumerate(y):
        d, lo, hi = rows4[i]
        sig = i in (2, 5)
        col = AMBER if i == 5 else (TEAL if sig else MUTED)
        ax.plot([lo, hi], [yy + .13, yy + .13], color=col, lw=2.5, alpha=.8)
        ax.scatter(d, yy + .13, color=col, s=70, zorder=3,
                   label=txt(lang, 'clips de 4 s (análisis pre-registrado)',
                             '4 s clips (pre-registered analysis)') if i == 0 else None)
        d8, lo8, hi8 = rows8[i]
        ax.plot([lo8, hi8], [yy - .17, yy - .17], color=col, lw=1.5, alpha=.5, ls=':')
        ax.scatter(d8, yy - .17, facecolor='none', edgecolor=col, s=55, zorder=3,
                   label=txt(lang, 'clips de 8 s, sin fútbol americano (exploratorio)',
                             '8 s clips, no American football (exploratory)') if i == 0 else None)
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_yticks(y, names)
    ax.set_xlim(-0.1, 0.2)
    ax.set_xlabel(txt(lang, 'Puntos de exactitud que se pierden al desordenar los instantes',
                      'Accuracy points lost when the snapshots are shuffled'))
    ax.set_title(txt(lang, '¿Importa el orden de los instantes?', 'Does the order of the snapshots matter?'),
                 fontsize=14, loc='left', pad=12)
    ax.legend(loc='upper center', bbox_to_anchor=(0.45, -0.16), ncol=2, frameon=False, fontsize=10)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / f'sport-from-motion-order-{lang}.png', dpi=110)
    plt.close(fig)


def recall(lang):
    fig, ax = plt.subplots(figsize=(10, 5.2))
    sports = txt(lang, ['Fútbol\namericano', 'Baloncesto', 'Balonmano', 'Fútbol'],
                 ['American\nfootball', 'Basketball', 'Handball', 'Soccer'])
    names = MODELS + ['MiniRocket']
    m = np.array(RECALL)
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list('t', ['#1f2533', '#155e63', TEAL])
    ax.imshow(m, cmap=cmap, vmin=0, vmax=1, aspect='auto')
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            ax.text(j, i, f'{m[i, j]:.2f}'.replace('.', ',' if lang == 'es' else '.'),
                    ha='center', va='center', color=FG if m[i, j] < .6 else BG, fontsize=12,
                    weight='bold' if m[i, j] >= .6 else None)
    ax.axhline(4.5, color=AMBER, lw=1.5)
    ax.set_xticks(range(4), sports)
    ax.set_yticks(range(len(names)), names)
    ax.tick_params(length=0)
    ax.set_title(txt(lang, 'Acierto por deporte (8 instantes en orden)', 'Recall by sport (8 snapshots in order)'),
                 fontsize=14, loc='left', pad=12)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / f'sport-from-motion-recall-{lang}.png', dpi=110)
    plt.close(fig)


def jitter(lang):
    fig, ax = plt.subplots(figsize=(10, 4.6))
    labels = txt(lang, ['Sin suavizar', 'Suavizando igual todas las fuentes'],
                 ['Unsmoothed', 'Same smoothing for every source'])
    inside, outside = [0.97, 0.95], [0.17, 0.89]
    x = np.arange(2)
    ax.bar(x - .18, inside, .34, color=SLATE, label=txt(lang, 'fuentes de entrenamiento', 'training sources'))
    ax.bar(x + .18, outside, .34, color=TEAL, label=txt(lang, 'fuente nunca vista (TeamTrack)',
                                                          'unseen source (TeamTrack)'))
    for xi, v in zip(x - .18, inside):
        ax.text(xi, v + .02, f'{v:.2f}'.replace('.', ',' if lang == 'es' else '.'), ha='center', fontsize=11)
    for xi, v in zip(x + .18, outside):
        ax.text(xi, v + .02, f'{v:.2f}'.replace('.', ',' if lang == 'es' else '.'), ha='center', fontsize=11,
                color=TEAL)
    ax.axhline(0.5, color=MUTED, ls='--', lw=1)
    ax.text(-0.45, 0.52, txt(lang, 'azar', 'chance'), color=MUTED, fontsize=10)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 1.3)
    ax.set_yticks([0, .2, .4, .6, .8, 1.0])
    ax.set_ylabel(txt(lang, 'Exactitud, fútbol frente a baloncesto', 'Accuracy, soccer vs basketball'))
    ax.set_title(txt(lang, 'Un clasificador entrenado aprende el temblor del tracker',
                     'A trained classifier learns the tracker\'s jitter'), fontsize=14, loc='left', pad=12)
    ax.legend(frameon=False, fontsize=10, loc='upper center', ncol=2)
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / f'sport-from-motion-jitter-{lang}.png', dpi=110)
    plt.close(fig)


if __name__ == '__main__':
    for lang in ('es', 'en'):
        accuracy(lang)
        order(lang)
        recall(lang)
        jitter(lang)
    print('ok')
