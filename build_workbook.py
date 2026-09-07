#!/usr/bin/env python3
"""Build production Excel workbook from verified rows.json
Generates 3-sheet structure: originale, data_valuta, verifica
"""

import json
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter

def build_workbook(rows_file, output_file):
    """Build Excel with 3 sheets: originale, data_valuta, verifica"""

    with open(rows_file) as f:
        data = json.load(f)

    wb = Workbook()
    wb.remove(wb.active)  # Remove default sheet

    # ===== SHEET 1: ORIGINALE (transaction detail with running saldo)
    ws_orig = wb.create_sheet("originale")

    # Header style
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    # Column headers
    headers = ['FOGLIO', 'DATA_OPERAZIONE', 'DATA_VALUTA', 'DESCRIZIONE', 'DARE', 'AVERE', 'SALDO']
    for col, header in enumerate(headers, 1):
        cell = ws_orig.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border

    # Data rows
    row_idx = 2
    running_saldo = 0
    current_foglio = 1

    for stmt in data["statements"]:
        running_saldo = stmt["saldo_iniziale"]

        for i, row in enumerate(stmt["rows"]):
            dare = row.get("dare") or 0
            avere = row.get("avere") or 0

            # Calculate new saldo (debit convention: dare increases, avere decreases)
            running_saldo = running_saldo + dare - avere

            # Write row
            ws_orig.cell(row=row_idx, column=1, value=str(current_foglio))
            ws_orig.cell(row=row_idx, column=2, value=row["op"])
            ws_orig.cell(row=row_idx, column=3, value=row["val"])
            ws_orig.cell(row=row_idx, column=4, value=row["desc"])
            ws_orig.cell(row=row_idx, column=5, value=dare if dare else None)
            ws_orig.cell(row=row_idx, column=6, value=avere if avere else None)
            ws_orig.cell(row=row_idx, column=7, value=running_saldo)

            # Style
            for col in range(1, 8):
                cell = ws_orig.cell(row=row_idx, column=col)
                cell.border = thin_border
                if col in [2, 3]:  # Date columns
                    cell.number_format = 'yyyy-mm-dd'
                elif col in [5, 6, 7]:  # Number columns
                    cell.number_format = '#,##0'
                    cell.alignment = Alignment(horizontal='right')

            row_idx += 1

        current_foglio += 1

    # Column widths for originale
    ws_orig.column_dimensions['A'].width = 8
    ws_orig.column_dimensions['B'].width = 16
    ws_orig.column_dimensions['C'].width = 16
    ws_orig.column_dimensions['D'].width = 35
    ws_orig.column_dimensions['E'].width = 14
    ws_orig.column_dimensions['F'].width = 14
    ws_orig.column_dimensions['G'].width = 16

    # ===== SHEET 2: DATA_VALUTA (valuta date grouping summary)
    ws_valuta = wb.create_sheet("data_valuta")

    # Headers for data_valuta
    valuta_headers = ['DATA_VALUTA', 'DARE_TOTALE', 'AVERE_TOTALE', 'NETTO']
    for col, header in enumerate(valuta_headers, 1):
        cell = ws_valuta.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = thin_border

    # Build valuta summary
    valuta_summary = {}
    for stmt in data["statements"]:
        for row in stmt["rows"]:
            val = row["val"]
            dare = row.get("dare") or 0
            avere = row.get("avere") or 0

            if val not in valuta_summary:
                valuta_summary[val] = {"dare": 0, "avere": 0}

            valuta_summary[val]["dare"] += dare
            valuta_summary[val]["avere"] += avere

    # Write valuta rows (sorted by date)
    row_idx = 2
    for val_date in sorted(valuta_summary.keys()):
        ws_valuta.cell(row=row_idx, column=1, value=val_date)
        ws_valuta.cell(row=row_idx, column=2, value=valuta_summary[val_date]["dare"])
        ws_valuta.cell(row=row_idx, column=3, value=valuta_summary[val_date]["avere"])
        ws_valuta.cell(row=row_idx, column=4,
                      value=valuta_summary[val_date]["dare"] - valuta_summary[val_date]["avere"])

        for col in range(1, 5):
            cell = ws_valuta.cell(row=row_idx, column=col)
            cell.border = thin_border
            if col == 1:
                cell.number_format = 'yyyy-mm-dd'
            else:
                cell.number_format = '#,##0'
                cell.alignment = Alignment(horizontal='right')

        row_idx += 1

    ws_valuta.column_dimensions['A'].width = 16
    ws_valuta.column_dimensions['B'].width = 14
    ws_valuta.column_dimensions['C'].width = 14
    ws_valuta.column_dimensions['D'].width = 14

    # ===== SHEET 3: VERIFICA (reconciliation summary)
    ws_verifica = wb.create_sheet("verifica")

    # Statement summary
    ws_verifica.cell(row=1, column=1, value="VERIFICA RICONCILIAZIONE").font = Font(bold=True, size=12)

    row_idx = 3
    headers_verifica = ['ESTRATTO AL', 'SALDO_INIZIALE', 'SALDO_FINALE', 'TOTALE_DARE', 'TOTALE_AVERE', 'NETTO_CALCOLATO', 'VERIFICA']
    for col, header in enumerate(headers_verifica, 1):
        cell = ws_verifica.cell(row=row_idx, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = header_fill
        cell.border = thin_border

    # Write reconciliation for each statement
    row_idx += 1
    for stmt in data["statements"]:
        total_dare = sum(row.get("dare") or 0 for row in stmt["rows"])
        total_avere = sum(row.get("avere") or 0 for row in stmt["rows"])
        netto = total_dare - total_avere
        computed_finale = stmt["saldo_iniziale"] + netto
        verified = "✓" if computed_finale == stmt["saldo_finale"] else "✗"

        ws_verifica.cell(row=row_idx, column=1, value=stmt["estratto_al"])
        ws_verifica.cell(row=row_idx, column=2, value=stmt["saldo_iniziale"])
        ws_verifica.cell(row=row_idx, column=3, value=stmt["saldo_finale"])
        ws_verifica.cell(row=row_idx, column=4, value=total_dare)
        ws_verifica.cell(row=row_idx, column=5, value=total_avere)
        ws_verifica.cell(row=row_idx, column=6, value=computed_finale)
        ws_verifica.cell(row=row_idx, column=7, value=verified)

        for col in range(1, 8):
            cell = ws_verifica.cell(row=row_idx, column=col)
            cell.border = thin_border
            if col == 1:
                cell.number_format = 'yyyy-mm-dd'
            elif col >= 2:
                cell.number_format = '#,##0' if col < 7 else '@'
                cell.alignment = Alignment(horizontal='right')

        row_idx += 1

    ws_verifica.column_dimensions['A'].width = 14
    ws_verifica.column_dimensions['B'].width = 16
    ws_verifica.column_dimensions['C'].width = 16
    ws_verifica.column_dimensions['D'].width = 14
    ws_verifica.column_dimensions['E'].width = 14
    ws_verifica.column_dimensions['F'].width = 16
    ws_verifica.column_dimensions['G'].width = 10

    # Save workbook
    wb.save(output_file)
    print(f"✓ Excel workbook: {output_file}")
    print(f"  - Sheet 'originale': {row_idx-4} transactions with running saldo")
    print(f"  - Sheet 'data_valuta': {len(valuta_summary)} unique valuta dates")
    print(f"  - Sheet 'verifica': Reconciliation verification for all statements")

if __name__ == '__main__':
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "rows-1998.json"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "ricostruzione.xlsx"

    if Path(input_file).exists():
        build_workbook(input_file, output_file)
    else:
        print(f"❌ File not found: {input_file}")
        sys.exit(1)
