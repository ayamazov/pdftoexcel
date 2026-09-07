# Output format — the ricostruzione workbook

Read at Step 6, and whenever a descrizione needs mapping. **A client-supplied target workbook wins over everything here** — open it first, read its sheet shapes, saldo formula, sign convention and existing descrizione values, and match them exactly. This file documents one real client format: a default, not a standard.

`scripts/build_workbook.py` implements all of it. Change the script, not the output by hand.

## Foglio `originale` — operation-date order

- **Row 1 empty. Header on row 2**, exactly, including the leading space in A:
  `' operazione'`, `'valuta'`, `'descrizione operazione'`, `'dare'`, `'avere'`, `'saldo'`
- Six columns only. No `estratto al`, no `pag. PDF`, no title block, no bank name, no bold, no fill, no totals row. The sheet is machine input, not a report.
- Data from row 3, in operation-date order as printed.

## Foglio `data valuta` — the same rows in value-date order

- Header on row 1 (no blank row), `freeze_panes = "B2"`.
- Same rows, **stably sorted by `valuta`**, opening row pinned first. Stable: rows sharing a valuta keep their operation order.
- `saldo` recomputed down this sheet's own order — that is the whole point, and it is Axis 5.

## Shared rules

- **Sign convention:** `saldo = F{prev} + D{row} - E{row}`. Dare increases the balance, avere decreases it, so **positive saldo = conto a debito (scoperto)** — the opposite of the bank's printed `-`. An account overdrawn all year shows *positive* saldi here. Getting this backwards is the single easiest way to ruin the file.
- `dare` = addebiti, `avere` = accrediti, exactly as printed.
- **Dates are real `datetime` values**, never text. Number format `D/M/YYYY`.
- **Amounts:** Lire `#,##0` (no decimals); EUR post-2002 `#,##0.00`.
- **Only the opening balance is a typed number.** Every other `saldo` cell is a formula, with a cell comment naming the PDF page and printed row it came from.
- The opening row carries both dates, an empty descrizione, empty dare and avere, and the hardcoded saldo.
- **Omit intermediate SALDO INIZIALE / SALDO FINALE rows.** They are balances; their chaining is proven on `Verifica`.
- Saldo formula extends ~200 rows past the data on both sheets, so appending the next year is a paste into A:E.
- Column widths: A 11.57 · B 12.86 · C 50.86 · D 12.71 · F 13.57 (E default).

## Foglio `Verifica` (optional third sheet)

Allowed and useful provided it changes nothing about the two sheets above. One row per statement: computed saldo, printed saldo, difference, `=IF(ROUND(diff,0)=0,"OK","DIFFERENZA")`. Plus a row checking `data valuta` ends on the same saldo as `originale`. Below it: the mapping table, the cheque-series check, every reading assumption. Tell the user it is deletable.

## Descrizione — controlled vocabulary

The downstream sheets filter on `descrizione operazione`, so free text breaks them. **Read the client workbook's existing values before inventing a term.**

| Printed on the estratto | Goes in as |
|---|---|
| `ASSEGNO N.RO nnnnn` | `assegno` — **the number is dropped** |
| `INTERESSI E COMPETENZE` | `interessi e competenze` |
| `BOLLI, IMPOSTE E TASSE` | `imposta di bollo` |
| `SPESE ELABORAZIONE ESTRATTI CONTO` | `spese e commissioni` |
| `COSTO LIBRETTI ASSEGNI` | `spese e commissioni` |
| `SPESE ISTRUTTORIA` | `spese istruttoria` — **kept separate**: one-off fee on the fido, may be treated on its own for the TEG |
| `VERSAMENTO ASSEGNI BANCARI SU PIAZZA` | `incasso assegno` |
| `VERSAMENTO CONTANTE` | `versamento contante` |

Other terms seen in real workbooks: `incasso ri.ba`, `commissione ri.ba`, `insoluti ri.ba`, `cartasi`, `pagamento tramite carta`, `rata mutuo`, `pagamento RID`, `pagamento f24`, `prelevamento`, `giroconto`, `bonifico`. Bonifici keep the counterparty: `bon. NOME` incoming, `A FAV. NOME` outgoing.

**Proposed, not yet confirmed** (1996 run, Banca di Roma 3002.3): `effetti ritirati`, `giroconto`, `emissione assegni circolari`, `pagamento INPS/INAIL`, `pagamento ri.ba`, `bonifico`. Confirm with the user before treating any of these as settled, then move them into the table above.

**A new mapping is a fiscal classification, not a formatting choice. Never decide one silently** — propose it, say what it affects downstream, let the user confirm before delivery. Record every mapping in `Verifica`. Keep the printed wording in `raw` in `rows.json` so a mapping can be revisited without re-reading the PDF.
