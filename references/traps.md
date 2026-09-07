# Transcription Traps — Common Errors in Italian Bank Statement Extraction

This document catalogs systematic errors that occur when manually reading scanned bank statements. Each trap includes: symptom, root cause, diagnostic test, and fix.

---

## Trap 1: Pen Tick Read as Amount

**Symptom**  
Axis 1 reconciliation delta is ±1, ±10, ±100, or ±1,000 (suspiciously round number). Most often discovered when one row's dare or avere is slightly off.

**Root Cause**  
Stray mark, pen annotation, or scanner artifact at the edge of the dare/avere column mistaken for a digit. Marks are especially common on vintage dot-matrix forms where handwritten notes overlay the printed table.

**Diagnostic Test**  
1. Note which row caused the delta (reconcile output names it)
2. Re-read that row at **8× zoom** focusing on the dare/avere column
3. Check for partial marks at column boundaries (especially right edge)

**Fix**  
Compare the zoomed image with surrounding rows' formatting:
- If marks exist outside the digit area → ignore, re-read without mark
- If ambiguous → check printed bank total SALDO FINALE; that row's contribution should match

**Example**  
- Delta: ±5 on page 3
- Row 45 shows: dare = 1,234,5** (unclear digit at column edge)
- At 8×: Zoomed image shows stray pen mark, not part of digit
- Correct value: 1,234,500 (not 1,234,505)

---

## Trap 2: Leading Digit Clipped

**Symptom**  
Axis 1 delta off by **factor of 10** (e.g., expected 1,000,000 but computed 100,000). Error typically affects all rows on a page equally, suggesting systematic crop alignment error.

**Root Cause**  
Image crop started at x=55 instead of x=0 (or similar), cutting off the leftmost column pixels. If a digit is split across the boundary, the leading part is missing.

**Diagnostic Test**  
1. Reload the original high-res 300 DPI image (hi-NN.png)
2. Check image dimensions and crop parameters used
3. Visually inspect the left edge: does the first digit look complete?

**Fix**  
Re-run `compact.py` with adjusted column x-range:
- If original: `--cols 55-292,...`, try `--cols 0-292,...`
- Re-read the cropped image and verify left edge includes full digits
- Re-transcribe rows.json with corrected amounts

**Prevention**  
Always include the true left edge of the data region. Use ±5 px margin for safety, but never start crop beyond the first digit's leftmost pixel.

---

## Trap 3: Valuta Date Misalignment

**Symptom**  
Axis 5 (data_valuta breakdown) reconciliation fails, but Axis 1 (saldo chain) closes perfectly. This suggests amounts are correct, but date assignments are wrong.

**Root Cause**  
1. **Transposed columns**: VAL column read as OP or vice versa
2. **Misaligned crop**: Crop started too late, mixing data from two columns
3. **Wrong variant**: Column ranges (from form-variants.md) don't match actual page

**Diagnostic Test**  
1. Extract one row from reconcile output that failed Axis 5
2. Check: is the row's `val` date outside the statement's expected range?
3. Compare that row's `op` and `val` in the original zoomed image
4. Cross-check against printed `SALDI PER VALUTA` section (pages 2–3)

**Fix**  
- If transposed: swap `op` ↔ `val` in rows.json for affected rows
- If misaligned: re-crop at correct x-ranges from form-variants.md
- If wrong variant: verify page orientation (portrait vs landscape) and re-map ranges

**Example**  
- Row reads: op="1998-01-15", val="1998-03-31" (val after statement end date!)
- Printed SALDI PER VALUTA show valuta entries up to 1998-02-28
- Fix: swap to op="1998-03-31", val="1998-01-15"

---

## Trap 4: Rotated Page Transcribed Upside-Down

**Symptom**  
Transaction dates are wildly out of sequence (e.g., 1995, 1997, 1994, 1998), or amounts look backwards (trailing zeros on left side instead of right). Axis 1 reconciliation fails with nonsensical deltas.

**Root Cause**  
Variant A pages are rotated 90° CCW in the PDF. If not detected and corrected before cropping, the image is read upside-down or sideways, scrambling all data.

**Diagnostic Test**  
1. Check page orientation in `pdfinfo` output (look for `Rotate:`)
2. Visually inspect the original 110 DPI low-res image: is text readable?
3. If text is sideways or inverted, a rotation correction is needed

**Fix**  
1. Re-rasterize with rotation flag: `pdftoppm -png -r 300 -f N -l N -rot 270 statement.pdf hi`
2. Or use `scripts/compact.py --rotate 90` before cropping
3. Re-transcribe rows.json with corrected, readable columns

**Prevention**  
- Always visually inspect contact sheets (Step 3) before transcription
- If a page's header is unreadable, suspect rotation
- Use form-variants.md to confirm expected orientation before cropping

---

## Trap 5: Dare/Avere Column Swap

**Symptom**  
Axis 1 reconciliation fails, but deltas are exactly negated (e.g., expected +100,000,000 but computed -100,000,000). Suggests columns are systematically reversed.

**Root Cause**  
DARE (debit, money out) and AVERE (credit, money in) columns swapped during transcription. The amounts are correct in magnitude but wrong in sign.

**Diagnostic Test**  
1. Check first row's dare/avere values against the printed description
2. Example: "ASSEGNO" (check withdrawal) should be in dare column (money out), not avere
3. If most rows are sign-reversed, this trap is likely

**Fix**  
Swap all dare ↔ avere in rows.json:
```python
for row in rows:
    row["dare"], row["avere"] = row["avere"], row["dare"]
```

Then re-run reconciliation.

**Prevention**  
- Verify column headers before reading (DATA OPERAZIONE, DATA VALUTA, DESCRIZIONE, DARE/MOV. A DEBITO, AVERE/MOV. A CREDITO)
- Cross-check first 3 rows against printed descriptions to confirm column identity
- Use descrizione mapping: assegno → dare, versamento → dare, etc.

---

## Trap 6: Decimal/Thousands Separator Confusion

**Symptom**  
Axis 1 delta off by orders of magnitude (off by 10, 100, 1000x). Especially common with post-2002 EUR amounts where decimals are used.

**Root Cause**  
1. **Pre-2002 (ITL)**: Amounts use thousands separators (e.g., "1.234.567" = 1,234,567 in English notation)
2. **Post-2002 (EUR)**: Amounts use decimal points (e.g., "1.234,56" = 1234.56 in English notation)
3. **Confusion**: Reading "1.234.567" as 1.234567 (decimal), or "1.234,56" as 1,234,560

**Diagnostic Test**  
1. Check statement currency from header: "ITL" or "EUR"?
2. Check saldo_finale amount: if 7–10 digits, it's ITL; if 5–7 digits, likely EUR
3. Manually verify one amount against printed bank total

**Fix**  
Normalize all amounts:
- **ITL**: Remove all dots (they're thousands separators): "1.234.567" → 1234567 (integer)
- **EUR**: Replace comma with dot, preserve 2 decimals: "1.234,56" → 1234.56 (float)

Verify currency in rows.json header: `"currency": "ITL"` or `"currency": "EUR"`

**Prevention**  
- Always inspect one full row (including saldo_finale) for currency and format
- Store amounts as integers (ITL) or 2-decimal floats (EUR), never as strings
- Add type validation in validate.py

---

## Trap 7: Duplicate Rows

**Symptom**  
One row appears twice in rows.json (same date, amount, description). Axis 1 delta is exactly 2× the row's amount, suggesting double-entry.

**Root Cause**  
1. **Misaligned crops**: Two page images overlap, causing shared rows to appear twice
2. **Copy-paste error**: Same row manually typed twice during transcription
3. **Page boundary**: Row appears on both page N and page N+1 (e.g., wrapped table)

**Diagnostic Test**  
1. Search rows.json for duplicate (op, val, desc, dare, avere) tuples
2. Cross-reference against page numbers: if same row appears on pages 3 and 4, check if it's a page-break artifact
3. Check printed statement for row count: does total transaction count match?

**Fix**  
Remove the duplicate entry, keeping the first occurrence. Re-reconcile.

**Prevention**  
- When transcribing multi-page tables, verify row boundaries at page breaks
- Visually inspect cropped images for overlapping content
- Deduplicate rows.json before reconciliation (sort by op, val, desc and flag duplicates)

---

## Trap 8: FOGLIO Letter Suffix Misread

**Symptom**  
Header shows "FOGLIO N. 2A" or "FOGLIO N. 3A" but transcribed as "2" or "3". Expected statement pages are missing from output.

**Root Cause**  
FOGLIO N. (sheet number) includes a letter suffix (A, B, C, etc.) on non-transaction pages. Variant A and some Variant B forms use this convention:
- "1A", "2A", "3A": Summary pages (no transaction rows)
- "1", "2", "3": Transaction pages (with rows)

**Diagnostic Test**  
1. Visually inspect the page header in contact sheet
2. Look for letter suffix after the sheet number
3. Check if page contains transaction table (rows) or just summary sections (saldo, interests)

**Fix**  
Record the complete FOGLIO value including letter: `"foglio": "2A"`, not `"foglio": "2"`.

Mark pages with letter suffix for skipping during transcription (they contain no movement rows).

**Prevention**  
- Always read sheet header completely, including letter suffix
- Use classification step (Step 3) to identify and skip non-transaction pages
- Document in classification output: e.g., "Page 3 = FOGLIO 2A (summary only, no rows)"

---

## Trap 9: Interest Amount in Wrong Row

**Symptom**  
One row has unusually large dare/avere that breaks Axis 4 reconciliation (sbilancio_competenze). Amount doesn't match any description in the transaction list.

**Root Cause**  
Interest, commission, or fee rows are printed at the bottom of the transaction table, but may be:
1. Misaligned during crop (included in DESCRIZIONE instead of separate row)
2. Read as part of another row's amount
3. Placed in a different section than expected (check `ELEMENTI PER IL CONTEGGIO DELLE COMPETENZE`)

**Diagnostic Test**  
1. Reconcile output shows Axis 4 delta (sbilancio_competenze mismatch)
2. Check printed page for `ELEMENTI PER IL CONTEGGIO DELLE COMPETENZE` section
3. Compare sbilancio_competenze value in JSON vs printed amount

**Fix**  
Verify that interest/commission rows are recorded in the `sbilancio_competenze` field (or `scalare` array for valuta-specific interest), not in the main `rows` list.

Re-read the competency section and update rows.json to match.

**Prevention**  
- During transcription (Step 4), distinguish between movement rows and competency rows
- Movement rows go in `rows[]`; interest/fees go in `sbilancio_competenze` (or `scalare` array for valuta breakdown)
- Verify against printed section headers

---

## General Prevention Rules

1. **Read at 8× zoom for uncertain digits** (do not guess)
2. **Cross-check one full row against printed amounts** before starting bulk transcription
3. **Verify column headers** (DATA OPERAZIONE, DARE, AVERE, etc.) before reading columns
4. **Use form-variants.md to confirm crop ranges** for the detected variant
5. **Run reconciliation after transcription** (never skip arithmetic verification)
6. **When reconciliation fails, re-read the failing row at 8×** (do not re-guess or adjust)

---

## Error Reporting Format

When a trap is encountered during reconciliation:

```json
{
  "trap": "pen_tick_read_as_amount",
  "page": 3,
  "row_index": 45,
  "expected_value": 1000000,
  "read_value": 1000005,
  "delta": 5,
  "action_taken": "re_read_at_8x",
  "corrected_value": 1000000
}
```

---

## References

- SKILL.md: Full extraction workflow
- form-variants.md: Column positions per variant
- output-format.md: Excel schema and validation rules
