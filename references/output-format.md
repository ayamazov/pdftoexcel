# Output Format — Excel Workbook Schema for Estratto di Conto Corrente

This document defines the structure of the final Excel workbook generated from rows.json, including sheet layouts, column formulas, and the standardized descrizione vocabulary.

---

## Workbook Overview

**File**: `ricostruzione.xlsx`  
**Sheets**: 2 main sheets + optional summary sheets  
**Purpose**: Audit-ready reconstruction of bank statements with running balances and valuta analysis  
**Validation**: All formulas closed to the exact Lira (Axis 1 reconciliation)  

---

## Sheet 1: `originale` (Transaction Detail)

The main transaction list, transaction-by-transaction, matching the printed bank statement format.

### Columns

| Column | Type | Source | Formula | Notes |
|--------|------|--------|---------|-------|
| **FOGLIO** | Text | statement.foglio | (static) | Sheet number from statement header |
| **DATA_OPERAZIONE** | Date | row.op | (static) | Operation date (YYYY-MM-DD) |
| **DATA_VALUTA** | Date | row.val | (static) | Valuta date (YYYY-MM-DD) |
| **DESCRIZIONE** | Text | row.desc | (static) | Standardized transaction type (see vocabulary below) |
| **DARE** | Number | row.dare | (static) | Debit amount (money out), integers for ITL or 2-decimals for EUR |
| **AVERE** | Number | row.avere | (static) | Credit amount (money in), integers for ITL or 2-decimals for EUR |
| **SALDO** | Number | calculated | `=SALDO_PREVIOUS ± (DARE - AVERE)` | Running balance (debit convention: positive = money owed to bank) |
| **ANNOTAZIONI** | Text | (optional) | (empty or manual) | User notes, audit flags, anomalies |

### Row Structure

1. **Header row** (row 1):
   - Column labels as above
   - Frozen panes (row 1 frozen)

2. **Summary row** (row 2, optional):
   - FOGLIO: "RIEPILOGO"
   - DATA_OPERAZIONE, DATA_VALUTA: (empty)
   - DESCRIZIONE: "Saldo Iniziale"
   - DARE, AVERE: (empty)
   - SALDO: `=saldo_iniziale` (from first statement)

3. **Data rows** (rows 3+):
   - One row per transaction from rows.json
   - Sorted by DATA_OPERAZIONE (or DATA_VALUTA per analysis)
   - SALDO column carries running total

4. **Final balance row** (last row):
   - DESCRIZIONE: "Saldo Finale"
   - SALDO: `=saldo_finale` (must match bank statement exactly)

### Formulas

**SALDO column (Row N)**:
```excel
=IF(ROW()=2, [saldo_iniziale], [SALDO_N-1] + [DARE_N] - [AVERE_N])
```

Or simplified (if first data row is row 3):
```excel
=OFFSET(SALDO, -1, 0) + DARE3 - AVERE3  (for row 3 onwards)
```

**Validation**: SALDO[last] must equal printed SALDO FINALE exactly.

### Example (first 5 rows)

| FOGLIO | DATA_OPERAZIONE | DATA_VALUTA | DESCRIZIONE | DARE | AVERE | SALDO | ANNOTAZIONI |
|--------|-----------------|-------------|-------------|------|-------|-------|-------------|
| 1 | 31.03.1998 | 31.03.1998 | saldo_iniziale | | | 140,072,613 | Opening balance |
| 1 | 01.04.1998 | 01.04.1998 | assegno | 1000 | | 140,071,613 | Check withdrawal |
| 1 | 02.04.1998 | 02.04.1998 | versamento | | 5000 | 140,076,613 | Deposit |
| 1 | 05.04.1998 | 05.04.1998 | bonifico | 2500 | | 140,074,113 | Transfer out |
| ... | ... | ... | ... | ... | ... | ... | ... |

---

## Sheet 2: `data_valuta` (Valuta Analysis)

Groups transactions by valuta date, supporting Axis 5 reconciliation (data_valuta breakdown).

### Columns

| Column | Type | Source | Notes |
|--------|------|--------|-------|
| **DATA_VALUTA** | Date | row.val (unique) | Valuta date, one row per unique date |
| **VALUTA** | Text | description | Readable label (e.g., "31/03/1998 – Opening") |
| **SALDO** | Number | calculated | Running balance at this valuta date |
| **MOVEMENT_COUNT** | Number | count | Number of transactions with this valuta date |
| **TOTAL_DARE** | Number | sum | Sum of all dare on this valuta date |
| **TOTAL_AVERE** | Number | sum | Sum of all avere on this valuta date |

### Example

| DATA_VALUTA | VALUTA | SALDO | MOVEMENT_COUNT | TOTAL_DARE | TOTAL_AVERE |
|-------------|--------|-------|----------------|------------|-------------|
| 31.03.1998 | Opening Balance | 140,072,613 | 0 | 0 | 0 |
| 01.04.1998 | 01/04/1998 | 140,071,613 | 3 | 2500 | 1000 |
| 02.04.1998 | 02/04/1998 | 140,076,613 | 2 | 500 | 5000 |
| ... | ... | ... | ... | ... | ... |

---

## Descrizione Vocabulary

Standard mappings from printed Italian descriptions to normalized, English-friendly codes.

### Mapping Table

| Printed Text (Raw) | Descrizione Code | Category | Sign Convention (Dare/Avere) |
|-------------------|------------------|----------|-------------------------------|
| ASSEGNO | assegno | Check | Dare (withdrawal) |
| GIRO ASSEGNO | giroassegno | Check Deposit | Dare (collection fee) or Avere (deposit) |
| BONIFICO BANCARIO | bonifico | Wire Transfer | Dare (out) or Avere (in) |
| VERSAMENTO | versamento | Cash Deposit | Avere (in) |
| PRELEVAMENTO | prelevamento | Cash Withdrawal | Dare (out) |
| PRELIEVO ATM | prelievo_atm | ATM Withdrawal | Dare (out) |
| COMMISSIONI CONTI | commissioni_conti | Account Fee | Dare (out) |
| COMMISSIONI ASSEGNO | commissioni_assegno | Check Fee | Dare (out) |
| INTERESSI ATTIVI | interessi_attivi | Interest Income | Avere (in) |
| INTERESSI PASSIVI | interessi_passivi | Interest Expense | Dare (out) |
| INTERESSE DEBITO | interesse_debito | Debit Interest | Dare (out) |
| CEDOLA | cedola | Dividend / Coupon | Avere (in) |
| CAMBIO | cambio | Foreign Exchange | Dare (out) or Avere (in) |
| GIRAMENTI | giramenti | Fund Transfer | Dare (out) or Avere (in) |
| RIMESSA BANCARIA | rimessa_bancaria | Bank Remittance | Avere (in) |
| SPESE | spese | Miscellaneous Expense | Dare (out) |
| RITIRATI | ritirati | Retrieved / Withdrawn | Dare (out) |
| STORNO | storno | Reversal / Correction | (either) |
| RETTIFICA | rettifica | Adjustment | (either) |
| SALDO | saldo_iniziale / saldo_finale | Balance | (marker only) |

### Extension Rules

When encountering a new descrizione not in this list:

1. **Check raw description** in rows.json (keep both `desc` and `raw`)
2. **Determine category** (fee, interest, transfer, etc.)
3. **Assign code** (lowercase, underscores, English-friendly)
4. **Document in metadati** (see Phase 2 output)
5. **Add to vocabulary** in future versions

**Example**:  
- Raw: "DISPOSIZIONE DI PRELEVAMENTO MEDIANTE ASSEGNO"
- Code: `prelevamento_assegno`
- Category: Check-based withdrawal

---

## Sign Convention

### Conto a Debito (Debit Account)

Banca di Roma statements typically show balances as **conto a debito** (the customer is a creditor; the bank owes the customer money). In this convention:

- **DARE** (money going out of account) → **increases** balance (positive)
- **AVERE** (money coming in) → **decreases** balance (negative)

This is **opposite** to how most English-language spreadsheets work (where deposits are positive).

### Workbook Convention

The output Excel workbook uses the **logical/audit convention** (matching printed statement):

- All balances stored as **positive** (saldo_iniziale and saldo_finale are always > 0 for conto a debito)
- DARE = positive = increases balance
- AVERE = negative = decreases balance
- Formula: `SALDO = SALDO_PREVIOUS + DARE - AVERE`

### Example Balance Change

Print bank statement shows:
```
SALDO INIZIALE:       140,072,613
  DARE 1,000:              (decrease shown on bank)  →  SALDO = -1,000 in bank terms
  AVERE 5,000:             (increase shown on bank)  →  SALDO = +5,000 in bank terms
SALDO FINALE:         140,072,613 - 1,000 + 5,000 = 140,076,613
```

Workbook formula:
```
SALDO = 140,072,613 + 1,000 - 5,000 = 140,076,613  (opposite signs, same result)
```

---

## Summary Sections (Optional Sheets)

### Sheet 3: `riepilogo` (Summary)

One row per statement in the PDF, showing:

| STATEMENT_DATE | SALDO_INIZIALE | SALDO_FINALE | TOTAL_DARE | TOTAL_AVERE | SBILANCIO_COMPETENZE | PDF_PAGES |
|---|---|---|---|---|---|---|
| 31.03.1998 | 140,072,613 | 176,368,554 | ... | ... | 5,260,352 | 1-3 |
| 30.06.1999 | 176,368,554 | 195,641,498 | ... | ... | 4,064,078 | 4-6 |

---

### Sheet 4: `competenze` (Fees & Interest, Optional)

Detailed breakdown of SBILANCIO_COMPETENZE:

| STATEMENT_DATE | TIPO | DESCRIZIONE | IMPORTO |
|---|---|---|---|
| 31.03.1998 | INTERESSE | INTERESSI DEBITORI | 3,681,527 |
| 31.03.1998 | COMMISSIONE | COMMISSIONI MASSIMO SCOPERTO | 244,551 |
| 31.03.1998 | SPESA | SPESE | 138,000 |

---

## Workbook Validation Checklist

- [ ] **Headers row 1**: All columns labeled correctly
- [ ] **Formulas closed**: SALDO[last] = printed SALDO FINALE exactly
- [ ] **No gaps**: Every transaction from rows.json appears exactly once
- [ ] **Dare/Avere mutually exclusive**: Never both non-zero on same row
- [ ] **Dates sequential**: DATA_OPERAZIONE in ascending order (or DATA_VALUTA if sorted by valuta)
- [ ] **Currency consistent**: All amounts in same currency (ITL or EUR)
- [ ] **Decimals correct**: 0 for ITL, 2 for EUR
- [ ] **Sheet2 (data_valuta)**: Totals match Sheet1 for each valuta date
- [ ] **File readable**: Excel opens without errors, macros not required

---

## Generation Script Notes

The build_workbook.py script:

1. **Reads rows.json** (single source of truth)
2. **Creates Sheet1 (originale)**: Transaction-by-transaction with running saldo
3. **Creates Sheet2 (data_valuta)**: Valuta date breakdown
4. **Applies formatting**: Column widths, number formats, freeze panes
5. **Validates**: Closes all formulas to exact Lira, reports deltas if any
6. **Writes** `ricostruzione.xlsx`

### Command

```bash
python scripts/build_workbook.py rows-1998.json rows-1999.json ... \
  --out ricostruzione.xlsx --verifica
```

---

## References

- SKILL.md: Full extraction workflow
- form-variants.md: Column positions per variant
- traps.md: Common transcription errors and fixes
