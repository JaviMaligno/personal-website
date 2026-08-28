#!/usr/bin/env python3
"""Programmatic geometry figures for the two paper-3 blog articles.

The house convention for in-body figures on this blog is INLINE SVG inside a
`<figure class="cwm-fig">` (that is how the danger-curve chart is done), so
these are emitted as SVG markup rather than as image files, and injected
between markers in the markdown:

    <figure class="cwm-fig">
    <!-- fig:instrument-knobs -->
    ... generated, do not hand-edit ...
    <!-- /fig:instrument-knobs -->
    <figcaption>hand-written, and translated per language</figcaption>
    </figure>

Captions stay hand-written because they are prose. Everything between the
markers is owned by this script.

    python ring_figures.py --list
    python ring_figures.py --preview out/          # standalone HTML per figure
    python ring_figures.py --write <file.md> ...   # patch markers in place

Geometry follows the instrument: band from r_in = 3.5 to r_out = 5.0 around a
lode at the centre, start outside to the west, channel of angular width gamma.
Drawn to scale within each panel.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import re
import sys

# --- palette (matches the site's figure cards) ------------------------------
PANEL = "#1a1a24"
EDGE = "rgba(255,255,255,0.10)"
INK = "#f8fafc"
MUTED = "#94a3b8"
DIM = "#64748b"
SAFE = "#6366f1"
SAFE_L = "#818cf8"
DANGER = "#f43f5e"
DANGER_L = "#fb7185"
CYAN = "#22d3ee"
GOLD = "#fbbf24"
MONO = "ui-monospace,'JetBrains Mono',monospace"

R_IN, R_OUT = 3.5, 5.0


# --- tiny SVG helpers ------------------------------------------------------
def _xy(cx: float, cy: float, r: float, deg: float, s: float) -> tuple[float, float]:
    """Math angle (CCW from east, y up) -> screen coords (y down)."""
    t = math.radians(deg)
    return cx + s * r * math.cos(t), cy - s * r * math.sin(t)


def annulus(cx, cy, s, *, gap_deg=0.0, gap_at=180.0, colour=DANGER, opacity=0.9):
    """The band, as a thick stroked circle with the channel cut by a dash gap.

    Avoids arc-path flag arithmetic entirely: one dash of length
    (circumference - gap) positioned so the gap is centred on `gap_at`.
    """
    r_mid = (R_IN + R_OUT) / 2 * s
    width = (R_OUT - R_IN) * s
    if gap_deg <= 0:
        return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r_mid:.2f}" fill="none" '
                f'stroke="{colour}" stroke-width="{width:.2f}" stroke-opacity="{opacity}"/>')
    circ = 2 * math.pi * r_mid
    gap = circ * gap_deg / 360
    line = circ - gap
    # SVG circles start at east and run clockwise; math angles run CCW.
    d_centre = ((-gap_at) % 360) / 360 * circ
    offset = line - d_centre + gap / 2
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r_mid:.2f}" fill="none" '
            f'stroke="{colour}" stroke-width="{width:.2f}" stroke-opacity="{opacity}" '
            f'stroke-dasharray="{line:.2f} {gap:.2f}" stroke-dashoffset="{offset:.2f}"/>')


def disc(cx, cy, s, r=R_IN, *, colour=DANGER, opacity=0.28):
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r * s:.2f}" fill="{colour}" '
            f'fill-opacity="{opacity}"/>')


def star(cx, cy, s, *, r=1.15, colour=GOLD, halo=True):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.44
        x, y = _xy(cx, cy, rr, 90 + i * 36, s)
        pts.append(f"{x:.1f},{y:.1f}")
    glow = (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r * s * 1.9:.1f}" fill="{colour}" '
            f'fill-opacity="0.10"/>') if halo else ""
    return glow + f'<polygon points="{" ".join(pts)}" fill="{colour}"/>' 


def dot(x, y, *, r=3.6, colour=INK):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{colour}"/>'


def cross(x, y, *, size=5.0, colour=INK, w=2.4):
    return (f'<path d="M{x - size:.1f},{y - size:.1f} L{x + size:.1f},{y + size:.1f} '
            f'M{x + size:.1f},{y - size:.1f} L{x - size:.1f},{y + size:.1f}" '
            f'stroke="{colour}" stroke-width="{w}" stroke-linecap="round"/>')


def arrow(x1, y1, x2, y2, *, mid, colour=INK, dash="5 3", w=2.0):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{colour}" stroke-width="{w}" stroke-dasharray="{dash}" '
            f'marker-end="url(#{mid})"/>')


def marker_def(mid, colour=INK):
    return (f'<defs><marker id="{mid}" viewBox="0 0 10 10" refX="8" refY="5" '
            f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M0,1 L9,5 L0,9 z" fill="{colour}"/></marker></defs>')


def text(x, y, s, *, size=11, colour=MUTED, anchor="middle", mono=True,
         weight=None, italic=False):
    fam = f' font-family="{MONO}"' if mono else ""
    wt = f' font-weight="{weight}"' if weight else ""
    it = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{colour}" '
            f'text-anchor="{anchor}"{fam}{wt}{it}>{s}</text>')


def frame(x, y, w, h):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="none" '
            f'stroke="{EDGE}"/>')


def svg(body: str, *, w=600, h=260, label="") -> str:
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n'
            f'{body}\n</svg>')


# --- the figures -----------------------------------------------------------
def fig_instrument_knobs() -> tuple[str, str]:
    """Four panels: closed, facing channel, hidden channel, inside start."""
    label = ("Four configurations of the same instrument: a closed band, a channel "
             "facing the start, the same channel hidden behind the goal, and a start "
             "inside the hole")
    pw, gap_x, top = 142, 6, 26
    s = 6.6  # px per world unit; the start sits at r = 9.5, so it fits in pw
    out = [marker_def("mk-knobs")]
    panels = [
        ("closed", 0.0, 180.0, "outside", DANGER, "inside unreachable"),
        ("facing", 34.0, 180.0, "outside", SAFE, "the plan drives through"),
        ("hidden", 34.0, 0.0, "outside", DANGER, "same gap, unreachable"),
        ("inside", 0.0, 180.0, "inside", CYAN, "the inside is sampled"),
    ]
    for i, (name, gap, at, start, colour, note) in enumerate(panels):
        x0 = 6 + i * (pw + gap_x)
        cx, cy = x0 + pw / 2 + 7, top + 82   # nudged right: the approach needs room
        out.append(frame(x0, top, pw, 150))
        out.append(text(cx, top - 8, name, size=11.5, weight="bold",
                        colour=MUTED if name != "inside" else CYAN))
        out.append(annulus(cx, cy, s, gap_deg=gap, gap_at=at, colour=colour))
        out.append(star(cx, cy, s, r=1.3, halo=False))
        if start == "outside":
            sx, sy = _xy(cx, cy, 9.5, 180, s)
            out.append(dot(sx, sy, r=3.0))
            if gap > 0 and at == 180.0:
                tx, ty = _xy(cx, cy, 1.5, 180, s)
                out.append(arrow(sx + 5, sy, tx, ty, mid="mk-knobs"))
            else:
                tx, ty = _xy(cx, cy, R_OUT + 1.25, 180, s)
                out.append(arrow(sx + 5, sy, tx, ty, mid="mk-knobs"))
                bx, by = _xy(cx, cy, R_OUT + 0.15, 180, s)
                out.append(cross(bx, by, size=4.4))
        else:
            sx, sy = _xy(cx, cy, 2.6, 232, s)
            out.append(dot(sx, sy, r=3.0))
            # contacts on the inner rim: from inside, the interior IS sampled
            for a in (52, 96, 140, 300, 340):
                ex, ey = _xy(cx, cy, R_IN + 0.05, a, s)
                out.append(dot(ex, ey, r=2.4, colour=INK))
        out.append(text(x0 + pw / 2, top + 168, note, size=9.5, colour=DIM))
    return svg("\n".join(out), w=600, h=214, label=label), label


def fig_gauge_unfalsifiable() -> tuple[str, str]:
    """Truth vs filled disc, with the samples that cannot separate them."""
    label = ("The truth and the filled-disc artifact differ only inside the hole, "
             "where no sampled rollout can ever be")
    s = 15.0
    out = [marker_def("mk-gauge")]
    for i, (title, filled) in enumerate((("the truth", False),
                                         ("what the model wrote", True))):
        x0 = 10 + i * 295
        cx, cy = x0 + 138, 110
        out.append(frame(x0, 24, 285, 172))
        out.append(text(cx, 16, title, size=11.5, weight="bold", colour=MUTED))
        if filled:
            out.append(disc(cx, cy, s, colour=DANGER, opacity=0.30))
        out.append(annulus(cx, cy, s, colour=DANGER if filled else SAFE))
        out.append(star(cx, cy, s, r=0.95, halo=False))
        # a handful of sampled rollouts, all stopping at the rim
        for a in (150, 168, 186, 205, 224):
            fx, fy = _xy(cx, cy, 7.4, a, s)
            tx, ty = _xy(cx, cy, R_OUT + 0.5, a, s)
            bx, by = _xy(cx, cy, R_OUT + 0.02, a, s)
            out.append(arrow(fx, fy, tx, ty, mid="mk-gauge", dash="4 3",
                             colour=MUTED, w=1.4))
            out.append(dot(bx, by, r=2.6, colour=INK))
        out.append(text(cx, 214,
                        "the whole inside frozen" if filled else "the inside is free",
                        size=10.5, colour=DANGER_L if filled else SAFE_L))
    out.append(text(300, 236,
                    "every sample lands on the rim  ·  the two differ only inside it",
                    size=11, colour=INK))
    return svg("\n".join(out), w=600, h=250, label=label), label


def fig_fence_covering() -> tuple[str, str]:
    """Point fences vs a fence matched to the boundary's dimension."""
    label = ("Point fences leave gaps along a one-dimensional boundary; a fence built "
             "from tangential segments covers it")
    s = 15.0
    out = [marker_def("mk-fence")]
    for i, (title, kind) in enumerate((("point fences", "points"),
                                       ("dimension-matched", "segments"))):
        x0 = 10 + i * 295
        cx, cy = x0 + 152, 116
        out.append(frame(x0, 24, 285, 186))
        out.append(text(cx, 16, title, size=11.5, weight="bold", colour=MUTED))
        # faint: the planner cannot see the band at all, only the fences
        out.append(annulus(cx, cy, s, colour=DANGER, opacity=0.32))
        if kind == "points":
            for a in (128, 152, 208, 232):
                bx, by = _xy(cx, cy, (R_IN + R_OUT) / 2, a, s)
                out.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{0.5 * s:.1f}" '
                           f'fill="none" stroke="{CYAN}" stroke-width="1.6" '
                           f'stroke-dasharray="3 2"/>')
            fx, fy = _xy(cx, cy, 7.6, 180, s)
            tx, ty = _xy(cx, cy, 1.2, 180, s)
            out.append(arrow(fx, fy, tx, ty, mid="mk-fence", colour=INK))
            out.append(text(cx, 196, "it re-routes through an unfenced arc",
                            size=9.5, colour=DIM))
        else:
            arcs = []
            for a in range(112, 249, 4):
                bx, by = _xy(cx, cy, (R_IN + R_OUT) / 2, a, s)
                arcs.append(f"{bx:.1f},{by:.1f}")
            out.append(f'<polyline points="{" ".join(arcs)}" fill="none" '
                       f'stroke="{CYAN}" stroke-width="{0.95 * s:.1f}" '
                       f'stroke-opacity="0.55" stroke-linecap="round"/>')
            fx, fy = _xy(cx, cy, 7.6, 180, s)
            tx, ty = _xy(cx, cy, R_OUT + 1.35, 180, s)
            bx, by = _xy(cx, cy, R_OUT + 0.9, 180, s)
            out.append(arrow(fx, fy, tx, ty, mid="mk-fence", colour=INK))
            out.append(cross(bx, by, colour=CYAN))
            out.append(text(cx, 196, "no unfenced arc left to use",
                            size=9.5, colour=DIM))
        out.append(star(cx, cy, s, r=0.95, halo=False))
    out.append(text(300, 232,
                    "sealing a curve with balls costs boundary length / fence radius",
                    size=11, colour=INK))
    return svg("\n".join(out), w=600, h=246, label=label), label


def fig_plain_setup() -> tuple[str, str]:
    """The explainer's setup: fence, goal, robot, the route it wants."""
    label = ("The setup: a robot outside a fenced band, the high-value spot inside it, "
             "and the straight route the robot wants to take")
    s = 17.0
    cx, cy = 300, 128
    out = [marker_def("mk-setup")]
    out.append(annulus(cx, cy, s, colour=DANGER, opacity=0.85))
    out.append(star(cx, cy, s, r=1.05, halo=False))
    sx, sy = _xy(cx, cy, 8.3, 180, s)
    out.append(dot(sx, sy, r=4.2))
    tx, ty = _xy(cx, cy, R_OUT + 0.75, 180, s)
    bx, by = _xy(cx, cy, R_OUT + 0.1, 180, s)
    out.append(arrow(sx + 6, sy, tx, ty, mid="mk-setup"))
    out.append(cross(bx, by, size=5.5))
    out.append(text(sx, sy - 16, "the robot", size=11, colour=INK))
    out.append(text(cx + 96, cy + 5, "what it wants", size=11, colour=GOLD,
                    anchor="start"))
    out.append(text(cx, cy - 96, "the fence — not in the description it was given",
                    size=11, colour=DANGER_L))
    out.append(text(30, 226, "it stops here — and the model never mentioned it",
                    size=10, colour=DIM, anchor="start"))
    return svg("\n".join(out), w=600, h=252, label=label), label


def fig_plain_free_vs_costly() -> tuple[str, str]:
    """Gap in front (route through, cheap) vs gap behind (blocked, costly)."""
    label = ("The same gap in the fence, in front of the robot and behind the goal, "
             "with the cost of the blind model in each case")
    s = 14.0
    out = [marker_def("mk-plain")]
    panels = [
        ("gap in front of the robot", 180.0, SAFE, "0.029", "the route goes through"),
        ("the same gap, round the back", 0.0, DANGER, "1.116", "the fence still blocks it"),
    ]
    for i, (title, at, colour, cost, note) in enumerate(panels):
        x0 = 10 + i * 295
        cx, cy = x0 + 142, 104
        out.append(frame(x0, 22, 285, 170))
        out.append(text(cx, 15, title, size=11.5, weight="bold", colour=MUTED))
        out.append(annulus(cx, cy, s, gap_deg=34.0, gap_at=at, colour=colour))
        out.append(star(cx, cy, s, r=0.95, halo=False))
        sx, sy = _xy(cx, cy, 7.8, 180, s)
        out.append(dot(sx, sy))
        if at == 180.0:
            tx, ty = _xy(cx, cy, 1.4, 180, s)
            out.append(arrow(sx + 5, sy, tx, ty, mid="mk-plain"))
        else:
            tx, ty = _xy(cx, cy, R_OUT + 0.7, 180, s)
            bx, by = _xy(cx, cy, R_OUT + 0.05, 180, s)
            out.append(arrow(sx + 5, sy, tx, ty, mid="mk-plain"))
            out.append(cross(bx, by))
        out.append(text(cx, 180, f"costs you  {cost}", size=15, colour=colour,
                        weight="bold"))
        out.append(text(cx, 210, note, size=9.5, colour=DIM))
    out.append(text(300, 232, "same model, same fence, same size of gap",
                    size=11.5, colour=INK, italic=True, mono=False))
    return svg("\n".join(out), w=600, h=244, label=label), label


FIGURES = {
    "instrument-knobs": fig_instrument_knobs,
    "gauge-unfalsifiable": fig_gauge_unfalsifiable,
    "fence-covering": fig_fence_covering,
    "plain-setup": fig_plain_setup,
    "plain-free-vs-costly": fig_plain_free_vs_costly,
}


# --- plumbing --------------------------------------------------------------
def write_into(path: pathlib.Path) -> int:
    t = path.read_text(encoding="utf-8")
    n = 0
    for name, build in FIGURES.items():
        body, _ = build()
        pat = re.compile(
            rf"<!-- fig:{re.escape(name)} -->.*?<!-- /fig:{re.escape(name)} -->", re.S)
        if pat.search(t):
            t = pat.sub(f"<!-- fig:{name} -->\n{body}\n<!-- /fig:{name} -->", t, count=1)
            n += 1
    path.write_text(t, encoding="utf-8")
    return n


def preview(outdir: pathlib.Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    for name, build in FIGURES.items():
        body, _ = build()
        html = (f'<!doctype html><meta charset="utf-8">'
                f'<body style="margin:0;background:{PANEL}">'
                f'<div style="width:620px;padding:10px">{body}</div></body>')
        (outdir / f"{name}.html").write_text(html, encoding="utf-8")
        (outdir / f"{name}.svg").write_text(
            body.replace("<svg ", f'<svg style="background:{PANEL}" ', 1),
            encoding="utf-8")
    print(f"wrote {len(FIGURES)} previews to {outdir}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--preview", metavar="DIR")
    ap.add_argument("--write", nargs="*", metavar="FILE")
    a = ap.parse_args()
    if a.list:
        for name, build in FIGURES.items():
            body, _ = build()
            print(f"{name:24s} {len(body):>6} bytes")
    if a.preview:
        preview(pathlib.Path(a.preview))
    for f in a.write or []:
        p = pathlib.Path(f)
        print(f"{f}: {write_into(p)} figure(s) patched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
