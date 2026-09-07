#!/usr/bin/env python3
"""Stack header crops from many pages into contact sheets, so one Read
classifies up to 10 pages.

    python classify_sheet.py "lo-*.png" --out sheet --frac 0.42x0.17
    python classify_sheet.py "hi-*.png" --out scal --box 0.55,0.60,1.0,0.95 --per 6

--frac W x H  crop the top-RIGHT block (default, for page headers)
--box l,t,r,b fractional box anywhere on the page (for SALDI PER VALUTA blocks)
"""
import argparse, glob, sys
from PIL import Image, ImageDraw

MAX_EDGE = 1568   # beyond this the API downscales before you ever see it
TOK_PER_PX = 1 / 750.0   # an image costs about (w*h)/750 tokens, every turn it stays in context

p = argparse.ArgumentParser()
p.add_argument("pattern")
p.add_argument("--out", default="sheet")
p.add_argument("--frac", default="0.42x0.17", help="WxH of the top-right header block")
p.add_argument("--box", help="l,t,r,b as fractions of the page; overrides --frac")
p.add_argument("--per", type=int, default=10, help="pages per contact sheet")
p.add_argument("--tokens", type=int, default=900,
               help="token budget per contact sheet (default 900)")
a = p.parse_args()

files = sorted(glob.glob(a.pattern))
if not files:
    sys.exit("no files match %s" % a.pattern)

strips = []
for f in files:
    im = Image.open(f).convert("L")
    W, H = im.size
    if a.box:
        l, t, r, b = (float(x) for x in a.box.split(","))
        box = (int(W * l), int(H * t), int(W * r), int(H * b))
    else:
        fw, fh = (float(x) for x in a.frac.lower().split("x"))
        box = (W - int(W * fw), 0, W, int(H * fh))
    strips.append((f, im.crop(box)))

for k in range(0, len(strips), a.per):
    grp = strips[k:k + a.per]
    bw = max(s.size[0] for _, s in grp)
    bh = max(s.size[1] for _, s in grp)
    sheet = Image.new("L", (bw + 70, bh * len(grp)), 255)
    d = ImageDraw.Draw(sheet)
    for i, (f, s) in enumerate(grp):
        sheet.paste(s, (70, i * bh))
        d.text((6, i * bh + bh // 2 - 6), "p%02d" % (k + i + 1), fill=0)
        d.line([(0, i * bh), (sheet.size[0], i * bh)], fill=0, width=2)
    w, h = sheet.size                              # spend exactly the budget, no more
    sc = (a.tokens / (w * h * TOK_PER_PX)) ** 0.5
    if max(w, h) * sc > MAX_EDGE:
        sc = MAX_EDGE / float(max(w, h))
    if abs(sc - 1.0) > 0.02:
        sheet = sheet.resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.LANCZOS)
    name = "%s%d.png" % (a.out, k // a.per)
    sheet.save(name, optimize=True)
    print("%s %dx%d ~%d tok  pages %d-%d"
          % (name, sheet.size[0], sheet.size[1], int(sheet.size[0] * sheet.size[1] * TOK_PER_PX),
             k + 1, k + len(grp)))
