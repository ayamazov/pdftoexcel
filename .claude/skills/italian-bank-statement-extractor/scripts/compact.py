#!/usr/bin/env python3
"""Compose the cheapest legible image for a question — and price it before you read it.

An image costs roughly (width x height) / 750 tokens, and it stays in context for
every turn that follows. So the size of what you read is a dial, not a constant:
--tokens sets the budget and the image is scaled (down OR up) to land on it.

    # full page: five columns pasted adjacent, no gutters, fitted to ~1500 tokens
    python compact.py hi-08.png --cols 55-292,292-525,655-1135,1240-1625,1640-2790 \
           --rows 560-1600 --out p08.png

    # every doubtful row on the page in ONE image, enlarged to fill the budget
    python compact.py hi-08.png --zoom 655,880,1135,910 --zoom 655,1210,1135,1240 \
           --out doubts.png

    # probe orientation cheaply
    python compact.py hi-08.png --rotate 90 --tokens 400 --out probe.png
"""
import argparse, sys
from PIL import Image

MAX_EDGE = 1568          # beyond this the API downscales anyway; never exceed it
TOK_PER_PX = 1 / 750.0


def tokens(size):
    return int(size[0] * size[1] * TOK_PER_PX)


def fit(im, budget):
    """Scale im so it costs about `budget` tokens. Scales UP as well as down."""
    w, h = im.size
    s = (budget / (w * h * TOK_PER_PX)) ** 0.5
    if max(w, h) * s > MAX_EDGE:
        s = MAX_EDGE / float(max(w, h))
    if abs(s - 1.0) < 0.02:
        return im
    return im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)


def ranges(s):
    out = []
    for part in s.split(","):
        a, b = part.split("-")
        out.append((int(a), int(b)))
    return out


def emit(im, name, gray):
    if gray:
        im = im.convert("L")
    im.save(name, optimize=True)
    print("%s %dx%d ~%d tok" % (name, im.size[0], im.size[1], tokens(im.size)))


p = argparse.ArgumentParser()
p.add_argument("image")
p.add_argument("--out", required=True)
p.add_argument("--cols", help="x-ranges 'a-b,c-d,...' in source pixels")
p.add_argument("--rows", help="y-range 'top-bottom' of the table body")
p.add_argument("--zoom", action="append", default=[],
               help="x0,y0,x1,y1 — repeat to montage several rows into ONE image")
p.add_argument("--tokens", type=int, default=1500,
               help="token budget for the emitted image (default 1500)")
p.add_argument("--rotate", type=int, default=0, help="CCW degrees before cropping")
p.add_argument("--split", type=int, default=1,
               help="emit N vertical slices, each fitted to --tokens (tall pages only)")
p.add_argument("--color", action="store_true", help="keep RGB (default: grayscale)")
a = p.parse_args()

im = Image.open(a.image)
if a.rotate:
    im = im.rotate(a.rotate, expand=True)

# ---- zoom: one or many regions, montaged, enlarged to fill the budget ----
if a.zoom:
    crops = []
    for z in a.zoom:
        x0, y0, x1, y1 = (int(v) for v in z.split(","))
        crops.append(im.crop((x0, y0, x1, y1)))
    w = max(c.size[0] for c in crops)
    gap = 6
    h = sum(c.size[1] for c in crops) + gap * (len(crops) - 1)
    out = Image.new("RGB", (w, h), "white")
    y = 0
    for c in crops:
        out.paste(c, (0, y))
        y += c.size[1] + gap
    emit(fit(out, a.tokens), a.out, not a.color)
    sys.exit()

if not a.cols:
    emit(fit(im, a.tokens), a.out, not a.color)
    sys.exit()

# ---- columns pasted adjacent, dead space dropped ------------------------
Y0, Y1 = (int(v) for v in a.rows.split("-")) if a.rows else (0, im.size[1])
cols = ranges(a.cols)
step = (Y1 - Y0) // a.split
stem = a.out[:-4] if a.out.lower().endswith(".png") else a.out

for n in range(a.split):
    y0 = Y0 + n * step
    y1 = Y1 if n == a.split - 1 else y0 + step
    parts = [im.crop((x0, y0, x1, y1)) for x0, x1 in cols]
    w = sum(q.size[0] for q in parts)
    out = Image.new("RGB", (w, y1 - y0), "white")
    x = 0
    for q in parts:
        out.paste(q, (x, 0))
        x += q.size[0]
    name = a.out if a.split == 1 else "%s_%d.png" % (stem, n + 1)
    emit(fit(out, a.tokens), name, not a.color)
