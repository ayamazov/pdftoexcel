# Transcription traps and delta diagnosis

Read while transcribing (Step 4) and whenever a reconciliation delta appears (Step 5).

## Traps

**Alternate-row grey shading.** Preprinted forms shade every other line; the dots land on dot-matrix digits, so `3` reads as `5` and `4` as `6`. Note every ambiguous digit in a shaded row and re-read them together at the end of the page with one multi-`--zoom` call — never one read per doubt.

**Handwritten ✓ ticks live in the MOV. AVERE column.** Reconciliation marks made in pen, not amounts. Reading them as digits is the classic cause of "dare/avere swapped or empty". An entire year can legitimately have zero or one AVERE movement — the compacted image proves the column empty at a glance.

**A printed `*` after a cheque number is part of the printed description**, not a stray mark and not a digit. It reaches `raw`, never `desc`.

**Lire are integers.** Dots are thousands separators, never decimals. `8.802.731` = `8802731`. Pre-2002 there are no cents; never produce `140072.61` from `140072613`. EUR post-2002 *does* have two decimals.

**Amount format differs by form.** Some print `1.234.567`, others `140072613` with no separators at all. The dotted vertical rules of a preprinted grid look like thousands separators — decide by whether the dots align with the grid or with the digits.

**VALUTA format differs by form.** `181093` = 18/10/1993 (DDMMYY). `31 12 2` = 31/12/1992 — single-digit year, the last digit only.

**SALDO INIZIALE and SALDO FINALE are printed inside the DARE column.** They are balances, not movements. Never sum them as transactions and never emit them as rows — they go in the statement header fields of `rows.json`.

**Trailing `-` on the scalare means a debit balance** (`170.722.074-`). An account can be overdrawn all year. In `rows.json` that is stored as `+170722074`.

**Rows with a description and no amount exist** (e.g. `SALDO` on a value date). Keep the row, leave `dare` and `avere` null, and confirm against the scalare that the date carries no movement.

**Cheque numbers are a free integrity check — but check the set, not the order.** Cheques are debited in clearing order, not issue order, so `94405` legitimately precedes `94404`. Verify the range is complete (n numbers in the range, n rows, no gaps). A number outside the range is probably a misread — verify with a `--zoom` re-read before changing it, because genuine out-of-range cheques occur. Report the anomaly; never silently "fix" it. Record the series check in `Verifica` so the work is not lost.

**A real gap in the printed page is not yours to close.** One 1996 foglio had an 800.000 lire difference between its own movements and its own printed SALDO FINALE, independently confirmed by the RIASSUNTO SCALARE. That ships flagged `DA VERIFICARE`, not plugged.

## The delta names the error

Do not re-read everything. Recompute the delta in Python first — more than once the mismatch was a slip in the check, not in the transcription.

| Difference | Likely cause |
|---|---|
| Small, one digit place (e.g. 900) | single misread digit — find the row whose value could differ by exactly that |
| Exactly one row's amount | row missed, or counted twice |
| Exactly 2× a row's amount | amount on the wrong side (dare vs avere) |
| Divisible by 9 | two digits transposed |
| Equals a SALDO row | a balance line was summed as a movement |
| Axis 5 breaks at one line, Axes 1 and 2 close | a misread **valuta**, not an amount |
| Axis 4 only | the `INTERESSI E COMPETENZE` amount, or the wrong quarter's sbilancio |
| Axis 3 only, others clean | a missing statement (declare it with `--allow-gap`) or two accounts conflated |

Re-read the suspect row with `--zoom` (batching it with any other doubt still open), patch
`rows.json`, re-run `reconcile.py`. Repeat until zero.

**A low-resolution pass invents digits.** A ÷3-scale read produced `13.678.177` for
`13.178.177` and `2.166.900` for `2.166.000`; both were right at full resolution. This is
what `--tokens` is for: shrink the *page* image only down to where digits still separate
(~1500 tokens for a five-column crop), and let `--zoom` spend the budget back on the rows
you actually doubt.
