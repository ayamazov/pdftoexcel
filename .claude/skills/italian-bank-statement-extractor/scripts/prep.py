#!/usr/bin/env python3
"""One command from PDF to 'ready to read'. Run this first, once, per PDF.

    python scripts/prep.py estratti.pdf

Does the whole front half of the pipeline in a single turn — inventory,
low-res rasterize, header contact sheets — and prints what to read next.
Doing it as one command instead of five saves four turns of context replay.

    --dpi-lo 110   classification raster (cheap, never transcribed from)
    --per 10       pages per contact sheet
    --tokens 900   token budget per contact sheet
    --workdir DIR  where the PNGs go (default: <pdf stem>_work)
"""
import argparse, os, subprocess, sys, glob, re

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def rng(pgs):
    """[1,2,3,7,8] -> '1-3,7-8'"""
    out, i = [], 0
    while i < len(pgs):
        j = i
        while j + 1 < len(pgs) and pgs[j + 1] == pgs[j] + 1:
            j += 1
        out.append(str(pgs[i]) if i == j else "%d-%d" % (pgs[i], pgs[j]))
        i = j + 1
    return ",".join(out)


def need(tool):
    if not run(["which", tool]).stdout.strip():
        sys.exit("missing tool: %s (install poppler-utils)" % tool)


p = argparse.ArgumentParser()
p.add_argument("pdf")
p.add_argument("--dpi-lo", type=int, default=110)
p.add_argument("--per", type=int, default=10)
p.add_argument("--tokens", type=int, default=900)
p.add_argument("--workdir")
a = p.parse_args()

if not os.path.exists(a.pdf):
    sys.exit("no such file: %s" % a.pdf)
for t in ("pdfinfo", "pdffonts", "pdftoppm"):
    need(t)

work = a.workdir or os.path.splitext(os.path.basename(a.pdf))[0] + "_work"
os.makedirs(work, exist_ok=True)

# ---- inventory -----------------------------------------------------------
info = run(["pdfinfo", "-f", "1", "-l", "9999", a.pdf]).stdout
npages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
sizes = {}
for m in re.finditer(r"Page\s+(\d+)\s+size:\s+([\d.]+)\s+x\s+([\d.]+)", info):
    n, w, h = int(m.group(1)), float(m.group(2)), float(m.group(3))
    sizes.setdefault(("landscape" if w > h else "portrait", round(w), round(h)), []).append(n)

fonts = run(["pdffonts", a.pdf]).stdout.strip().splitlines()
scanned = len(fonts) <= 2  # header + rule only

print("PDF        %s  (%d pages)" % (a.pdf, npages))
print("Text layer %s" % ("none — scanned, read the images" if scanned
                         else "PRESENT — check pdftotext before reading images"))
for (orient, w, h), pgs in sorted(sizes.items(), key=lambda kv: kv[1][0]):
    print("Geometry   %-9s %sx%s pts  pages %s" % (orient, w, h, rng(sorted(pgs))))
if len(sizes) > 1:
    print("           ^ geometry changes mid-document: decide rotation per group, not once")

# ---- rasterize low-res + contact sheets ----------------------------------
print("\nrasterizing at %d dpi ..." % a.dpi_lo)
r = run(["pdftoppm", "-png", "-r", str(a.dpi_lo), a.pdf, os.path.join(work, "lo")])
if r.returncode:
    sys.exit("pdftoppm failed:\n" + r.stderr)

r = run([sys.executable, os.path.join(HERE, "classify_sheet.py"),
         os.path.join(work, "lo-*.png"), "--out", os.path.join(work, "sheet"),
         "--frac", "0.42x0.17", "--per", str(a.per), "--tokens", str(a.tokens)])
if r.returncode:
    sys.exit("classify_sheet failed:\n" + r.stderr)
print(r.stdout.strip())

sheets = sorted(glob.glob(os.path.join(work, "sheet*.png")))
total = a.tokens * len(sheets)
print("""
NEXT — read these %d contact sheet(s) (~%d tokens total), and nothing else yet:
  %s

For each page record: ESTRATTO AL date, FOGLIO N., account number, and which of
  extract / verify / context  it is. Then, per statement with movements:

  pdftoppm -png -r 300 -f N -l N %s %s/hi
  python %s/compact.py %s/hi-NN.png --tokens 500 --out %s/probe.png   # crop boxes, once

and dispatch ONE SUBAGENT PER STATEMENT to read its pages and write
%s/rows-<estratto_al>.json.  Do not read hi-*.png in this context.
""" % (len(sheets), total, "\n  ".join(sheets), a.pdf, work, HERE, work, work, work))
