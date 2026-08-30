#!/usr/bin/env python3
"""Render the deterministic hero for "Practices for Agents: Substrate"."""

from pathlib import Path

from PIL import Image, ImageDraw


WIDTH, HEIGHT = 1020, 510
SCALE = 3

INK = "#172329"
PAPER = "#F1F0EA"
GRID = "#D8D8D1"
MUTED = "#AEB4B1"
TEAL = "#149C91"
CORAL = "#E05B49"


def xy(box):
    return tuple(int(value * SCALE) for value in box)


def line(draw, points, fill, width=1, joint="curve"):
    draw.line(
        [(int(x * SCALE), int(y * SCALE)) for x, y in points],
        fill=fill,
        width=width * SCALE,
        joint=joint,
    )


def rounded(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(
        xy(box),
        radius=radius * SCALE,
        fill=fill,
        outline=outline,
        width=width * SCALE,
    )


def circle(draw, center, radius, fill=None, outline=None, width=1):
    x, y = center
    draw.ellipse(
        xy((x - radius, y - radius, x + radius, y + radius)),
        fill=fill,
        outline=outline,
        width=width * SCALE,
    )


def draw_module(draw, center, color, active=True, large=False):
    x, y = center
    w, h = (42, 27) if large else (34, 22)
    fill = color if active else PAPER
    outline = color if active else MUTED
    rounded(draw, (x - w / 2, y - h / 2, x + w / 2, y + h / 2), 5, fill, outline, 2)
    circle(draw, (x, y), 3 if large else 2, PAPER if active else outline)


def draw_budget_blocks(draw, y, filled, color, total=19):
    start_x, block_w, gap, height = 96, 32, 7, 16
    for index in range(total):
        x = start_x + index * (block_w + gap)
        active = index < filled
        rounded(
            draw,
            (x, y - height / 2, x + block_w, y + height / 2),
            3,
            color if active else None,
            color if active else MUTED,
            1,
        )


def render():
    image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), PAPER)
    draw = ImageDraw.Draw(image)

    # A restrained paper-like plotting grid; no noise, so the output stays crisp.
    for x in range(42, WIDTH, 32):
        line(draw, [(x, 34), (x, HEIGHT - 34)], GRID, 1)
    for y in range(34, HEIGHT, 32):
        line(draw, [(42, y), (WIDTH - 42, y)], GRID, 1)

    # Quiet framing and the shared, finite turn-budget ceiling.
    rounded(draw, (42, 34, WIDTH - 42, HEIGHT - 34), 14, None, INK, 2)
    ceiling_x = 836
    line(draw, [(ceiling_x, 72), (ceiling_x, 438)], INK, 4)
    line(draw, [(ceiling_x - 10, 72), (ceiling_x + 10, 72)], INK, 4)
    line(draw, [(ceiling_x - 10, 438), (ceiling_x + 10, 438)], INK, 4)

    # Upper system: short dependency chain, completed with ample budget remaining.
    upper_y = 164
    upper_nodes = [(104, upper_y), (220, upper_y), (336, upper_y), (452, upper_y), (568, upper_y)]
    line(draw, upper_nodes, TEAL, 5)
    for node in upper_nodes:
        draw_module(draw, node, TEAL)
    # A few bounded dependencies keep this visibly a small repository.
    line(draw, [(220, upper_y), (220, 118), (336, 118), (336, upper_y)], TEAL, 2)
    circle(draw, (278, 118), 5, TEAL)
    line(draw, [(452, upper_y), (508, 132), (568, upper_y)], TEAL, 2)
    circle(draw, (508, 132), 5, TEAL)
    # Completion marker and clearly preserved margin.
    circle(draw, (624, upper_y), 13, PAPER, TEAL, 4)
    circle(draw, (624, upper_y), 5, TEAL)
    line(draw, [(642, upper_y), (ceiling_x - 18, upper_y)], MUTED, 2)
    draw_budget_blocks(draw, 226, 13, TEAL)

    # Lower system: denser cross-linked graph makes each step costlier.
    lower_y = 336
    lower_nodes = [
        (104, lower_y), (184, lower_y), (264, lower_y), (344, lower_y),
        (424, lower_y), (504, lower_y), (584, lower_y), (664, lower_y),
        (744, lower_y), (816, lower_y),
    ]
    line(draw, lower_nodes, CORAL, 5)
    for node in lower_nodes:
        draw_module(draw, node, CORAL, large=True)

    upper_dependencies = [(144, 286), (224, 278), (304, 294), (384, 274), (464, 290), (544, 276), (624, 292), (704, 276)]
    lower_dependencies = [(144, 390), (224, 404), (304, 388), (384, 408), (464, 390), (544, 406), (624, 388), (704, 404)]
    for i, node in enumerate(upper_dependencies):
        draw_module(draw, node, CORAL, large=False)
        left = lower_nodes[i]
        right = lower_nodes[i + 1]
        line(draw, [left, node, right], CORAL, 2)
    for i, node in enumerate(lower_dependencies):
        draw_module(draw, node, CORAL, large=False)
        left = lower_nodes[i]
        right = lower_nodes[i + 1]
        line(draw, [left, node, right], CORAL, 2)

    # Cross-links make the lower system materially more interconnected.
    for a, b in ((0, 2), (1, 4), (2, 5), (3, 6), (4, 7), (5, 7)):
        line(draw, [upper_dependencies[a], lower_dependencies[b]], CORAL, 1)

    # The final module is clipped by the ceiling; a ghost path cannot continue.
    draw.polygon(
        [
            (ceiling_x * SCALE, (lower_y - 25) * SCALE),
            ((ceiling_x + 10) * SCALE, (lower_y - 15) * SCALE),
            ((ceiling_x + 10) * SCALE, (lower_y + 15) * SCALE),
            (ceiling_x * SCALE, (lower_y + 25) * SCALE),
        ],
        fill=INK,
    )
    for x in range(854, 930, 18):
        line(draw, [(x, lower_y), (min(x + 8, 930), lower_y)], MUTED, 2)
    draw_budget_blocks(draw, 454, 19, CORAL)

    # Minimal lane anchors reinforce comparison without introducing labels.
    line(draw, [(66, upper_y - 42), (66, upper_y + 42)], TEAL, 6)
    line(draw, [(66, lower_y - 58), (66, lower_y + 58)], CORAL, 6)

    image = image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    output = Path(__file__).resolve().parents[2] / "public/blog/practices-for-agents-substrate.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, "PNG", optimize=True)
    return output


if __name__ == "__main__":
    render()
