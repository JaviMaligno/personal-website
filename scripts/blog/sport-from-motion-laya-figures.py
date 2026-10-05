"""Figures for the sport-from-motion follow-up (fine-tuned Laya). Aggregate data only.

Numbers come from the Laya arm's results (400 evaluation clips, 4 sports, 5 match-grouped
folds, 3 seeds): https://github.com/JaviMaligno/sport-from-motion/blob/main/docs/results-laya.md
Training curves are the per-epoch mean cross-entropy printed in the Kaggle logs.
Run: python scripts/blog/sport-from-motion-laya-figures.py
"""
from pathlib import Path

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parents[2] / 'public' / 'blog'
BG, FG, MUTED, TEAL, AMBER, SLATE = '#1a1a24', '#f8fafc', '#94a3b8', '#2dd4bf', '#fbbf24', '#64748b'
ROSE = '#fb7185'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'text.color': FG,
                     'axes.labelcolor': FG, 'xtick.color': MUTED, 'ytick.color': MUTED,
                     'axes.facecolor': BG, 'figure.facecolor': BG, 'savefig.facecolor': BG,
                     'axes.edgecolor': SLATE})
SLUG = 'sport-from-motion-laya'

# training cross-entropy per epoch, constant learning rate (DL1/DL2 schedule)
CONTROL = [1.429, 1.387, 2.036, 1.121, 0.721, 0.5, 0.553, 0.053, 0.784, 0.236] + [0.0] * 22
TAKEOFF = [1.399, 1.387, 1.392, 1.385, 1.388, 1.387, 1.387, 1.386, 1.386, 1.382, 1.337, 1.305,
           1.3, 1.269, 1.276, 1.26, 1.172, 1.107, 1.096, 1.001, 0.925, 0.972, 0.961, 0.863,
           0.784, 0.772, 0.772, 0.657, 0.68, 0.577, 0.503, 0.483]
LATE = [1.416, 1.389, 1.391, 1.386, 1.386, 1.388, 1.388, 1.386, 1.385, 1.384, 1.389, 1.385,
        1.384, 1.385, 1.388, 1.381, 1.385, 1.381, 1.385, 1.388, 1.383, 1.366, 1.349, 1.347,
        1.315, 1.307, 1.294, 1.24, 1.234, 1.182, 1.172, 1.131]
FLAT = [1.419, 1.394, 1.389, 1.388, 1.387, 1.389, 1.388, 1.387, 1.388, 1.386, 1.387, 1.398,
        1.386, 1.387, 1.387, 1.387, 1.386, 1.386, 1.384, 1.391, 1.401, 1.385, 1.383, 1.383,
        1.38, 1.382, 1.381, 1.383, 1.381, 1.378, 1.38, 1.379]

# accuracy on the 400 clips; 4 epochs = motion only, seed 0; 8 and 32 = mean of 3 seeds
CONFIGS = {'4': {'motion': 0.23}, '8': {'motion': 0.28, 'motion_shuffled': 0.22, 'formation': 0.25},
           '32': {'motion': 0.36, 'motion_shuffled': 0.27, 'formation': 0.27}}
UNTUNED, MINIROCKET = 0.24, 0.84

# DL2, motion: test accuracy per (seed, fold) and the epoch chosen on calibration
GRID = [[0.50, 0.42, 0.53, 0.46, 0.22], [0.47, 0.38, 0.53, 0.41, 0.22], [0.25, 0.20, 0.24, 0.23, 0.47]]
EPOCH = [[26, 25, 29, 26, 24], [19, 17, 26, 31, 2], [8, 3, 9, 6, 32]]


def txt(lang, es, en):
    return es if lang == 'es' else en


def curves(lang):
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ep = np.arange(1, 33)
    ax.axhline(np.log(4), color=SLATE, ls=':', lw=1)
    ax.text(32.4, np.log(4), txt(lang, 'azar (ln 4)', 'chance (ln 4)'), color=MUTED, va='center', fontsize=10)
    for x, lab in [(4, txt(lang, 'receta oficial', 'official recipe')), (8, txt(lang, '8 épocas', '8 epochs'))]:
        ax.axvline(x, color=SLATE, lw=1)
        ax.text(x + 0.3, 2.02, lab, color=MUTED, fontsize=10, va='top')
    ax.plot(ep, CONTROL, color=AMBER, lw=2, label=txt(lang, 'control: etiqueta arbitraria', 'control: arbitrary tag'))
    ax.plot(ep, TAKEOFF, color=TEAL, lw=2.2, label=txt(lang, 'movimiento: despega', 'motion: takes off'))
    ax.plot(ep, LATE, color=TEAL, lw=1.6, ls='--', label=txt(lang, 'movimiento: despega tarde', 'motion: takes off late'))
    ax.plot(ep, FLAT, color=ROSE, lw=2, label=txt(lang, 'movimiento: no despega', 'motion: never takes off'))
    ax.set_xlim(1, 32)
    ax.set_ylim(-0.05, 2.1)
    ax.set_xlabel(txt(lang, 'época', 'epoch'))
    ax.set_ylabel(txt(lang, 'entropía cruzada de entrenamiento', 'training cross-entropy'))
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, loc='lower left', fontsize=10.5, labelcolor=FG)
    fig.tight_layout()
    fig.savefig(OUT / f'{SLUG}-curves-{lang}.png', dpi=150)
    plt.close(fig)


def configs(lang):
    fig, ax = plt.subplots(figsize=(10, 5.2))
    conds = [('motion', txt(lang, 'en orden', 'in order'), TEAL),
             ('motion_shuffled', txt(lang, 'barajados', 'shuffled'), AMBER),
             ('formation', txt(lang, 'una sola foto', 'single snapshot'), MUTED)]
    groups = [('4', txt(lang, '4 épocas\n(receta oficial)', '4 epochs\n(official recipe)')),
              ('8', txt(lang, '8 épocas', '8 epochs')),
              ('32', txt(lang, 'hasta 32 épocas\n(parada temprana)', 'up to 32 epochs\n(early stopping)'))]
    w = 0.25
    for gi, (key, _) in enumerate(groups):
        for ci, (c, lab, col) in enumerate(conds):
            v = CONFIGS[key].get(c)
            if v is None:
                continue
            x = gi + (ci - 1) * w
            ax.bar(x, v, w * 0.9, color=col, label=lab if gi == 2 else None)
            ax.text(x, v + 0.012, f'{v:.2f}'.replace('.', ',') if lang == 'es' else f'{v:.2f}',
                    ha='center', color=FG, fontsize=10)
    ax.axhline(0.25, color=SLATE, ls=':', lw=1)
    ax.text(-0.42, 0.255, txt(lang, 'azar', 'chance'), color=MUTED, va='bottom', fontsize=10, ha='left')
    ax.axhline(MINIROCKET, color=SLATE, ls='--', lw=1)
    ax.text(2.48, MINIROCKET, 'MiniRocket', color=MUTED, va='bottom', fontsize=10, ha='right')
    ax.set_xticks(range(3), [g[1] for g in groups])
    ax.set_ylim(0, 0.92)
    ax.set_ylabel(txt(lang, 'acierto (400 clips)', 'accuracy (400 clips)'))
    for s in ('top', 'right'):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, loc='upper left', bbox_to_anchor=(0.0, 0.88), fontsize=10.5, labelcolor=FG)
    fig.tight_layout()
    fig.savefig(OUT / f'{SLUG}-configs-{lang}.png', dpi=150)
    plt.close(fig)


def seeds(lang):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    g = np.array(GRID)
    from matplotlib.colors import to_rgb
    # two colours: folds that learned (>= 0.30) in teal, folds left at chance in rose
    rgb = np.array([[to_rgb(TEAL) if v >= 0.30 else to_rgb(ROSE) for v in row] for row in g])
    alpha = np.clip((np.abs(g - 0.30) + 0.12) / 0.35, 0.35, 1.0)[..., None]
    ax.imshow(rgb * alpha + np.array(to_rgb(BG)) * (1 - alpha), aspect='auto')
    for i in range(3):
        for j in range(5):
            v = f'{g[i, j]:.2f}'
            if lang == 'es':
                v = v.replace('.', ',')
            ax.text(j, i - 0.08, v, ha='center', va='center', color=FG, fontsize=14, fontweight='bold')
            ax.text(j, i + 0.25, txt(lang, f'época {EPOCH[i][j]}', f'epoch {EPOCH[i][j]}'),
                    ha='center', va='center', color=FG, fontsize=9.5, alpha=0.85)
    ax.set_xticks(range(5), [f'fold {j}' for j in range(5)])
    ax.set_yticks(range(3), [txt(lang, f'semilla {i}', f'seed {i}') for i in range(3)])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / f'{SLUG}-seeds-{lang}.png', dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    for lang in ('en', 'es'):
        curves(lang)
        configs(lang)
        seeds(lang)
