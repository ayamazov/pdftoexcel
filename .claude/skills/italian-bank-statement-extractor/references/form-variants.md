# Known form variants

Check here **before** deriving crop boxes — a preset turns Step 4 into a single command. Record every new variant with its identifying header string, orientation, amount and date formats, header-block fractions (Step 3) and column x-ranges (Step 4). That table is what makes the second document of the same kind fast.

**The form code does not determine orientation or amount format.** The same `MR R1287T` string appears in both a portrait and a landscape layout with different amount printing. Always decide by looking at the page.

---

## Banca di Roma — preprinted shaded form `MR R1287T`, portrait scan

- Portrait page 543×842 pts, content rotated 90° CCW → `--rotate 90`
- Amounts `1.234.567` · valuta `GG MM A` (**single-digit year**)
- Alternate-row grey shading · notice text printed over the unused right panel
- Companion `CONTO SCALARE` page with `SALDI PER VALUTA`

## Banca di Roma — `MR R1287T`, landscape scan (1994 run)

- Landscape page 842×781 pts, **already upright, no rotation**
- Amounts printed **without separators**: `170722074` = 170.722.074 · valuta `GGMMAA`
- Light alternate-row shading on some pages, clean on others
- Step 3 header block: `--frac 0.42x0.17`
- Step 4 at 300 DPI (page 3509×3255 px), table body y **560–1600**:

```bash
python scripts/compact.py hi-NN.png --rows 560-1600 \
  --cols 55-292,292-525,655-1135,1240-1625,1640-2790
#        DATA     VALUTA    DARE      AVERE      DESCRIZIONE
```

- Page set per quarter: `ESTRATTO AL` on a plain-numbered foglio (movements) + `RIASSUNTO SCALARE` + one or two `ELEMENTI PER IL CONTEGGIO` sheets + `VARIAZIONE DI TASSO` on fogli suffixed `1A`, `2A`, …

## Banca di Roma — plain form `MR R1286T`

- Landscape, already upright
- Amounts `140072613` (no separators) · valuta `GGMMAA`
- No shading, clean digits
- `SALDO INIZIALE AL ggmmaa` / `SALDO FINALE AL ggmmaa` printed **inside the DARE column**

## Banca di Roma — form `3002.3`, landscape (1996 run)

- Landscape, amounts without separators, valuta `GGMMAA`
- Descriptions absent from earlier years appear here: effetti ritirati, giroconto (several reasons, same bank), emissione assegni circolari, pagamento INPS/INAIL, pagamento ri.ba, bonifico — mappings **proposed, not yet confirmed** (see `output-format.md`)
- Header fractions and column x-ranges: **not yet recorded — fill in on the next run of this form**
