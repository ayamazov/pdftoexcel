---
name: italian-bank-statement-extractor
description: "Extract scanned Italian bank statement PDFs into the 'ricostruzione' Excel (fogli 'originale' + 'data valuta') used for anatocismo/usura recalculation. Every amount proven by arithmetic reconciliation before delivery. Use for estratti conto, conto scalare, historical bank PDFs."
---

# Estratti conto italiani → Excel di ricostruzione

Convert scanned Italian bank statement PDFs into the verified input workbook for a *ricostruzione del conto corrente* (anatocismo / usura / CMS disputes).

**You read the page images yourself with the Read tool.** No OCR engine, no pytesseract, no API key. Rasterize, crop, read.

**You produce the INPUT, not the analysis.** Deliver `originale` and `data valuta` only. `depurato`, `interessi e spese`, `solo spese`, `solo interessi`, `RICALCOLO` are the dominus's work — never generate them.

## Start here — you were handed a PDF

```bash
python scripts/prep.py estratti.pdf
```

One command: inventory, low-res rasterize, header contact sheets. It prints the page
geometry, whether the PDF is scanned, the contact sheets to read and their token cost,
and the exact next commands. Read the sheets it names and nothing else.

Then Step 3 onward below. Steps 1–3 are what `prep.py` already did — read them only if it
failed or the PDF is unusual.

## One PDF, one session

**Start a new chat for each PDF.** Context is re-sent on every turn, so a session that has
already converted one statement set carries that weight through the whole of the next one.
Two PDFs in one chat is not twice the cost — it is worse than twice.

Within a single conversion, staying in the same chat is correct: the crop boxes, the page
classification and the reconciliation deltas all need to be in one place.

The exception is a **follow-up on a workbook you just built** — a mapping to confirm, one
row to correct. That is cheap and belongs in the same chat. Converting another PDF does not.

## Three laws

1. **Nothing ships until the arithmetic closes.** It reconciles to the printed SALDO FINALE to the exact Lira, or it has an error you have not found. Never round, never plug, never guess a digit. If it will not close, say so and name the row.
2. **Transcribe once, into `rows-*.json`.** One file per statement, written by the subagent that
   read it. Never retype rows into a later script, a table, or a chat message — not even to
   report them. Everything downstream reads the files. (See *Data contract*.)
3. **Spend CPU, not reads, and read where the image will not follow you.** One dense image
   answering many questions beats many answering one each — and an image read inside a
   subagent is paid for once, not replayed for the rest of the run.

## Budget

An image costs about **(width x height) / 750 tokens**, and it is **re-sent on every
turn that follows it**. Both halves matter:

| | |
|---|---|
| Size is a dial, not a constant | 1568x1568 is ~3,300 tokens; 1200x950 is ~1,500. Every script takes `--tokens` and scales the image to land on it. Ask for the smallest image that answers the question. |
| Residency is the real cost | Ten page images read in the main context of a 50-turn run are not 25,000 tokens. They are 25,000 tokens billed ~35 more times as the conversation replays them. |

So the budget is about **where** an image lives, not just how many there are:

| Resource | Target | Ceiling |
|---|---|---|
| Images resident in the **main** context | 2 (the classification sheets) | 3 |
| Images total, main + subagents, 20-page PDF | 12 | 18 |
| Tokens per image (`--tokens`) | 1500 | 2200 |
| Python authored inline | ~0 lines — use `scripts/` | one throwaway probe |
| Rows echoed into context | never — subagents write `rows-*.json` | never |

**Page images are read inside subagents, never in the main context** (Step 4). A subagent
holds its images for the three or four turns it needs them and is then discarded; the main
context receives one line of text per page. This is the difference between a run that
finishes and a run that hits the limit.

Speed is safe *because* the arithmetic is the backstop. A shortcut that drops a row fails
loudly. Optimise the search aggressively; never optimise the verification.

---

## Pipeline

### 1. Inventory

```bash
pdfinfo -f 1 -l 99 file.pdf | grep -i "page.*size"   # dimensions vary WITHIN one PDF
pdffonts file.pdf                                    # empty = scanned
```

Page size and orientation change mid-document (real case: pp. 1–6 portrait with content rotated 90°, pp. 7–12 landscape and upright). **The filename lies about the year** — a file named `1993.pdf` held a `CONTO SCALARE AL 31/03/94`. Year comes from each statement's own header.

### 2. Rasterize in two passes

```bash
pdftoppm -png -r 110 file.pdf lo             # whole doc, classification only  (~8 s)
pdftoppm -png -r 300 -f 8 -l 8 file.pdf hi   # only movement pages          (~3 s/page)
```

300 DPI for the whole document costs 65 s and is wasted — most pages are never transcribed. 300 DPI is the floor for anything you read; 150 loses digits. Decide rotation by looking, per page group (`scripts/compact.py --rotate 90 --tokens 400`); `rotate(90)` and `rotate(-90)` differ by 180°, and upside-down text is the tell.

### 3. Classify all pages in ONE read

```bash
python scripts/classify_sheet.py "lo-*.png" --out sheet --frac 0.42x0.17 --tokens 900
```

Crops the top-right header block from every page and stacks 10 per contact sheet with the page number burned in. Read `sheet0.png`, `sheet1.png` — 2 reads, ~900 tokens each, for 20 pages. These are the only page images that belong in the main context.

| Header | Action |
|---|---|
| `ESTRATTO AL gg/mm/aa` | **extract** — the transaction table |
| `CONTO SCALARE` + `SALDI PER VALUTA` | **verify** — Axes 2 and 5 |
| `CONTO SCALARE` + `ELEMENTI PER IL CONTEGGIO` | **verify** — Axis 4 |
| `VARIAZIONE DI TASSO` / `COMUNICAZIONE DEL …` | context only |

Record per page: account number, `FOGLIO N.`, statement date. A `FOGLIO N.` with a letter suffix (`1A`, `2A`) carries no movements. `FOGLIO N.` is **not** the page order and not a reliable sequence — order statements by their `ESTRATTO AL` date. An account number that changes may still be the same conto; prove it by the saldo chain before splitting.

**Do not OCR the header.** Tested on a real dot-matrix scan, tesseract garbled 9 of 20 pages at 110 DPI and still missed 3 of the 4 `ESTRATTO AL` pages at 300 with a tight crop — the header sits at a different height between form printings, and the failures land exactly on the pages that carry the movements.

### 4. Transcribe — one subagent per statement, images never in the main context

Derive the crop boxes **once**, in the main context, from a single cheap probe:

```bash
python scripts/compact.py hi-08.png --tokens 500 --out probe.png   # ~500 tok, enough to see the grid
```

Look up `references/form-variants.md` first — the variant may already be known, and then you
skip the probe entirely.

Then dispatch **one subagent per statement** (they run in parallel), each with the crop boxes
and its page numbers. Each subagent reads its own page images, writes its own
`rows-<estratto_al>.json` against the *Data contract* below, and returns **one line**:
the file it wrote, the row count, and any digit it could not resolve. It returns no rows,
no tables, no images.

Give each subagent exactly this and nothing more:

- the `hi-*.png` paths for its statement, and the `--cols` / `--rows` values
- the *Data contract* JSON shape, the transcription rules below, and `references/traps.md`
- the output path it must write

Transcription rules, for the subagent and for you:

```bash
python scripts/compact.py hi-08.png --cols 55-292,292-525,655-1135,1240-1625,1640-2790 \
       --rows 560-1600 --out p08.png                      # ~1500 tok, one image, whole page
python scripts/compact.py hi-08.png --zoom 655,880,1135,910 --zoom 655,1210,1135,1240 \
       --out doubts.png                                    # EVERY doubtful row, ONE image
```

The printed table is mostly dead space; cropping the five columns adjacent puts every field
of a page into one legible image. Column x-ranges are per form variant.

- **Collect doubts, then resolve them in one image.** Note every uncertain digit while
  reading the page, and re-read them all with a single multi-`--zoom` call at the end.
  One read of ten stacked rows costs about what three separate reads cost — and saves nine
  turns of context replay. Never re-read a row the moment you doubt it.
- `--zoom` scales the montage **up** to fill `--tokens`, so a row crop arrives far larger
  than it was on the page. (The old `--factor 8` was fiction: 8x a 480px row was clipped
  back to 1568px, i.e. 3.3x. The budget now decides, and it prints what you actually get.)
- **Include DATA from the true left edge** (x=0 if need be). The leading digit clips,
  turning `31/03` into `1/03`. Never infer a tens digit.
- A page that will not fit at `--tokens 2200` gets `--split 2` — not four. Each slice is
  fitted to the budget separately.
- Dare and avere sitting side by side is also *safer*: the pen-tick-read-as-an-amount trap
  becomes obvious instead of hiding in a crop seen in isolation.

If a subagent reports an unresolved digit, that is a *reconciliation* problem, not a reading
problem — let Step 5 locate it. The delta names the row, and re-reading one named row is
cheaper than re-reading a page on suspicion.

### 5. Reconcile

```bash
python scripts/reconcile.py rows.json          # all 5 axes, prints deltas only
```

| Axis | Check |
|---|---|
| 1 | `SALDO INIZIALE ± movimenti = SALDO FINALE` (always available) |
| 2 | movements grouped by valuta vs printed `SALDI PER VALUTA` |
| 3 | statement chaining: `finale[n] == iniziale[n+1]` |
| 4 | `INTERESSI E COMPETENZE` vs the previous quarter's `SBILANCIO COMPETENZE` |
| 5 | running saldo of `data valuta` reproduces `SALDI PER VALUTA` line for line |

Axis 2 proves the amounts; Axis 5 proves the amounts **and** every valuta **and** the sort, over the whole file at once — a mistyped valuta that Axis 2 absorbs inside a group shows up here as a broken line. Axes 1+2 = effectively proven. Axis 1 alone = re-read the amounts at 8× before delivery.

Montage the `SALDI PER VALUTA` blocks from every statement into one image and read it in a
single call — `classify_sheet.py "hi-*.png" --box 0.55,0.60,1.0,0.95 --per 6 --tokens 1200`.

When it does not close, **the delta names the error** — table in `references/traps.md`. Recompute the delta in Python before re-reading anything; more than once the mismatch was a slip in the check itself, and chasing it burns the most expensive thing you have.

### 6. Build the workbook

```bash
python scripts/build_workbook.py rows-1993.json rows-1994.json rows-1996.json \
       --out ricostruzione.xlsx --verifica
python /mnt/skills/public/xlsx/scripts/recalc.py ricostruzione.xlsx   # expect total_errors: 0
```

One workbook holds **all years** — the recalculation runs over the life of the conto, so each year is appended to the same file. Sheet shapes, sign convention, formats and the descrizione vocabulary live in `references/output-format.md`. **A client-supplied target workbook wins over that file** — open it first and match its shapes, formulas, sign convention and existing descrizione values exactly.

### 7. Report

Separate **proven** (amounts, valute, saldo — arithmetic closes on N axes) from **read twice, no arithmetic backstop** (operation dates, raw descriptions) from **judgment the user must confirm** (every new descrizione mapping, zero-amount rows, inferred years) from **anomalies found in the data** (out-of-sequence cheques, gaps — report, never silently normalise). Never claim 100% on a field arithmetic cannot reach.

---

## Data contract — `rows.json`

Written once at Step 4, one file per statement, by the subagent that read that statement;
read by every script after it (`reconcile.py rows-*.json` globs them). Amounts are integers in Lire (2-dp floats in EUR post-2002). **Saldi are stored positive = conto a debito**, the workbook convention, which is the opposite of the bank's printed trailing `-`.

```json
{"account": "745154", "currency": "ITL", "year": 1994,
 "statements": [{
   "estratto_al": "1994-03-31", "saldo_iniziale_al": "1993-12-31",
   "foglio": "1", "pdf_pages": [3],
   "saldo_iniziale": 140072613, "saldo_finale": 176368554,
   "sbilancio_competenze": 5260352,
   "scalare": [{"valuta": "1993-12-31", "saldo": 176368554}],
   "rows": [{"op": "1994-01-05", "val": "1993-12-31",
             "desc": "assegno", "raw": "ASSEGNO N.RO 94403*",
             "dare": 10000, "avere": null, "page": 3}]}]}
```

`desc` is the controlled-vocabulary term, `raw` the printed wording — keep both, so a mapping can be revisited without re-reading the PDF. `saldo_iniziale_al`, `sbilancio_competenze` and `scalare` are optional; the axes that need them are skipped and reported as N/A.

## References — read only when needed

| File | When |
|---|---|
| `references/form-variants.md` | **first**, before deriving crop boxes — the variant may already be known |
| `references/traps.md` | while transcribing, and whenever a delta appears |
| `references/output-format.md` | at Step 6, and whenever a descrizione needs mapping |

## Scripts

| Script | Does |
|---|---|
| `prep.py` | PDF → inventory + contact sheets, one command. Run first. |
| `classify_sheet.py` | stack crops from many pages into one budgeted image |
| `compact.py` | compose one page's columns, or montage doubtful rows, to a token budget |
| `reconcile.py` | all five axes over `rows-*.json`; prints deltas only, exit 1 on failure |
| `build_workbook.py` | `rows-*.json` → `ricostruzione.xlsx` |

## Extending this skill

A PDF that does not fit is a gap in the skill, not a one-off. Extract what reconciles, report what did not and why, diagnose what is structurally different (orientation, column order, amount format, date format, currency — EUR post-2002 *does* have decimals and the Lira integer rule must not be applied), tell the user, then write it down: new variant with its header string and x-ranges → `form-variants.md`; new trap with the symptom that revealed it → `traps.md`; new confirmed mapping → `output-format.md`; new verification axis → `scripts/reconcile.py`. If a run blew the read budget, say so in the report and fix the step that leaked them.
