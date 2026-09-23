"""Pad a 2:1 cover to 16:9 so LinkedIn's article cover crop keeps its edges.

LinkedIn crops article covers to 16:9. A 2:1 hero loses its sides, which cuts
labels and panels that sit near the border. Padding extends the first and last
rows of the image downward and upward, so each column keeps its own edge colour
and flat or gradient backgrounds look continuous.

Usage: python pad_cover_16x9.py <src.png> <dst.png>
"""
import sys

from PIL import Image

src, dst = sys.argv[1:3]
im = Image.open(src).convert("RGB")
w, h = im.size
target_h = round(w * 9 / 16)
if target_h <= h:
    raise SystemExit(f"already 16:9 or taller ({w}x{h}); upload it as is")
top = (target_h - h) // 2
bottom = target_h - h - top
out = Image.new("RGB", (w, target_h))
out.paste(im.crop((0, 0, w, 1)).resize((w, top)), (0, 0))
out.paste(im, (0, top))
out.paste(im.crop((0, h - 1, w, h)).resize((w, bottom)), (0, top + h))
out.save(dst)
print(f"{w}x{h} -> {out.size[0]}x{out.size[1]}")
