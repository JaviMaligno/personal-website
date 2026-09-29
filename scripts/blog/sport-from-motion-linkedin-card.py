"""Compose LinkedIn cards from the original experimental contact sheet.

Requires Pillow. Run from any directory:
    python3 scripts/blog/sport-from-motion-linkedin-card.py

The sheet is only uniformly resized with LANCZOS; it is never redrawn,
cropped, recoloured, or overlaid with text or borders.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parents[2] / 'public' / 'blog'
SIZE = (1200, 627)
BG, FG, MUTED, TEAL = '#1a1a24', '#f8fafc', '#94a3b8', '#2dd4bf'
HEADER_HEIGHT, MARGIN, BORDER = 120, 32, 2
COPY = {
    'en': ('Which sport is it?',
           '10 players, 8 snapshots. No pitch, no ball, no kits.'),
    'es': ('¿Qué deporte es?',
           '10 jugadores, 8 instantes. Sin campo, sin balón, sin camisetas.'),
}


def font(size, bold=False):
    """Use Unicode sans-serif fonts with Spanish glyphs on macOS or Linux."""
    candidates = [
        (Path('/System/Library/Fonts/Supplemental') /
         ('Arial Bold.ttf' if bold else 'Arial.ttf'), 0),
        (Path('/System/Library/Fonts/Helvetica.ttc'), 1 if bold else 0),
        (Path('/usr/share/fonts/truetype/dejavu') /
         ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'), 0),
    ]
    for path, index in candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size, index=index)
    raise FileNotFoundError('Install Arial, Helvetica, or DejaVu Sans to render the cards.')


def centered_text(draw, text, top, face, fill):
    left, upper, right, bottom = draw.textbbox((0, 0), text, font=face)
    width = right - left
    if width > SIZE[0] - 2 * MARGIN:
        raise ValueError(f'Text exceeds the available width: {text}')
    draw.text(((SIZE[0] - width) / 2 - left, top - upper),
              text, font=face, fill=fill)
    return top + bottom - upper


def main():
    title_font, subtitle_font = font(54, bold=True), font(24)
    with Image.open(OUT / 'sport-from-motion-quiz.png') as source:
        # One common scale factor, rounded only to whole output pixels.
        available = (SIZE[0] - 2 * (MARGIN + BORDER),
                     SIZE[1] - HEADER_HEIGHT - 2 * (MARGIN + BORDER))
        scale = min(1, available[0] / source.width, available[1] / source.height)
        sheet_size = tuple(round(dimension * scale) for dimension in source.size)
        sheet = source.resize(sheet_size, Image.Resampling.LANCZOS)

    x = (SIZE[0] - sheet.width) // 2
    y = HEADER_HEIGHT + (SIZE[1] - HEADER_HEIGHT - sheet.height) // 2
    for lang, (title, subtitle) in COPY.items():
        card = Image.new('RGB', SIZE, BG)
        draw = ImageDraw.Draw(card)
        title_bottom = centered_text(draw, title, 28, title_font, FG)
        subtitle_bottom = centered_text(draw, subtitle, 100, subtitle_font, MUTED)
        if title_bottom + 16 > 100 or subtitle_bottom + 24 > y - BORDER:
            raise ValueError('Insufficient spacing between the text and contact sheet.')
        # Draw entirely outside the sheet, preserving every resized pixel.
        draw.rectangle((x - BORDER, y - BORDER,
                        x + sheet.width + BORDER - 1,
                        y + sheet.height + BORDER - 1), fill=TEAL)
        card.paste(sheet, (x, y))
        output = OUT / f'sport-from-motion-linkedin-{lang}.png'
        card.save(output)
        with Image.open(output) as saved:
            print(f'{output.relative_to(OUT.parents[1])}: {saved.width}x{saved.height}')


if __name__ == '__main__':
    main()
