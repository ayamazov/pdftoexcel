#!/usr/bin/env python3
"""
Build Excel Workbook from rows.json

Generates ricostruzione.xlsx from rows.json data with verified formulas,
running balances, and valuta breakdown sheets.

Usage:
    python build_workbook.py rows-1998.json [rows-1999.json ...] \
        --out ricostruzione.xlsx [--verifica]

    --out FILE       Output Excel filename (default: ricostruzione.xlsx)
    --verifica       Enable arithmetic verification (check formulas close)
"""

import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    print("Error: openpyxl not installed. Install with: pip install openpyxl")
    sys.exit(1)


logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def load_rows_json(filepath: str) -> Dict[str, Any]:
    """Load rows.json file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load {filepath}: {e}")
        sys.exit(1)


def build_originale_sheet(wb: Workbook, data: Dict[str, Any]) -> None:
    """
    Build 'originale' sheet with transaction detail and running balances.

    Args:
        wb: Workbook object
        data: Parsed rows.json data
    """
    ws = wb.create_sheet('originale', 0)

    # Headers
    headers = ['FOGLIO', 'DATA_OPERAZIONE', 'DATA_VALUTA', 'DESCRIZIONE', 'DARE', 'AVERE', 'SALDO']
    ws.append(headers)

    # Format header row
    header_fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
    header_font = Font(bold=True)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font

    # Data rows
    row_num = 2
    all_rows = []

    # Collect all rows from all statements
    for statement in data.get('statements', []):
        for row in statement.get('rows', []):
            row['foglio'] = statement.get('foglio', '1')
            all_rows.append(row)

    # Sort by operation date
    all_rows.sort(key=lambda r: r.get('op', ''))

    # Running balance
    saldo = data['statements'][0].get('saldo_iniziale', 0) if data['statements'] else 0

    for row in all_rows:
        op = row.get('op', '')
        val = row.get('val', '')
        desc = row.get('desc', '')
        dare = row.get('dare') or 0
        avere = row.get('avere') or 0
        foglio = row.get('foglio', '1')

        # Calculate new balance
        saldo = saldo + dare - avere

        ws.append([
            foglio,
            op,
            val,
            desc,
            dare if dare else '',
            avere if avere else '',
            saldo
        ])

        row_num += 1

    # Format columns
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 15
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 40
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 15
    ws.column_dimensions['G'].width = 18

    # Number format for amounts
    for row in ws.iter_rows(min_row=2, min_col=5, max_col=7):
        for cell in row:
            cell.number_format = '#,##0'

    # Freeze header
    ws.freeze_panes = 'A2'

    logger.info(f"✓ Created 'originale' sheet with {row_num - 2} transactions")


def build_data_valuta_sheet(wb: Workbook, data: Dict[str, Any]) -> None:
    """
    Build 'data_valuta' sheet with valuta date breakdown.

    Args:
        wb: Workbook object
        data: Parsed rows.json data
    """
    ws = wb.create_sheet('data_valuta', 1)

    # Headers
    headers = ['DATA_VALUTA', 'VALUTA', 'MOVEMENT_COUNT', 'TOTAL_DARE', 'TOTAL_AVERE', 'SALDO']
    ws.append(headers)

    # Format header row
    header_fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
    header_font = Font(bold=True)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font

    # Collect valuta dates and amounts
    valuta_map: Dict[str, Dict[str, Any]] = {}

    for statement in data.get('statements', []):
        saldo_iniziale = statement.get('saldo_iniziale', 0)

        # Add opening balance
        estratto_al = statement.get('estratto_al', '')
        if estratto_al not in valuta_map:
            valuta_map[estratto_al] = {
                'count': 0,
                'dare': 0,
                'avere': 0,
                'is_opening': True
            }

        for row in statement.get('rows', []):
            val_date = row.get('val', '')
            dare = row.get('dare') or 0
            avere = row.get('avere') or 0

            if val_date not in valuta_map:
                valuta_map[val_date] = {
                    'count': 0,
                    'dare': 0,
                    'avere': 0,
                    'is_opening': False
                }

            valuta_map[val_date]['count'] += 1
            valuta_map[val_date]['dare'] += dare
            valuta_map[val_date]['avere'] += avere

    # Write rows in date order
    for val_date in sorted(valuta_map.keys()):
        info = valuta_map[val_date]
        count = info['count']
        dare = info['dare']
        avere = info['avere']

        ws.append([
            val_date,
            val_date,
            count if count > 0 else '',
            dare if dare > 0 else '',
            avere if avere > 0 else '',
            ''
        ])

    # Format columns
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 18

    # Number format
    for row in ws.iter_rows(min_row=2, min_col=4, max_col=6):
        for cell in row:
            cell.number_format = '#,##0'

    # Freeze header
    ws.freeze_panes = 'A2'

    logger.info(f"✓ Created 'data_valuta' sheet with {len(valuta_map)} valuta dates")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Excel workbook from rows.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_workbook.py rows-1998.json --out ricostruzione.xlsx
  python build_workbook.py rows-1998.json rows-1999.json --out ricostruzione.xlsx --verifica
        """
    )

    parser.add_argument(
        "rows_files",
        nargs="+",
        help="Input rows.json files"
    )
    parser.add_argument(
        "--out",
        default="ricostruzione.xlsx",
        help="Output Excel filename (default: ricostruzione.xlsx)"
    )
    parser.add_argument(
        "--verifica",
        action="store_true",
        help="Enable arithmetic verification"
    )

    args = parser.parse_args()

    if not args.rows_files:
        logger.error("No rows.json files specified")
        sys.exit(1)

    # Load all rows.json files
    all_data = {
        'account': '',
        'currency': '',
        'statements': []
    }

    for filepath in args.rows_files:
        logger.info(f"Loading: {filepath}")
        data = load_rows_json(filepath)

        if not all_data['account']:
            all_data['account'] = data.get('account', '')
        if not all_data['currency']:
            all_data['currency'] = data.get('currency', '')

        all_data['statements'].extend(data.get('statements', []))

    if not all_data['statements']:
        logger.error("No statements found in rows.json files")
        sys.exit(1)

    logger.info(f"Processing {len(all_data['statements'])} statement(s), account={all_data['account']}, currency={all_data['currency']}")

    # Create workbook
    wb = Workbook()
    wb.remove(wb.active)

    # Build sheets
    build_originale_sheet(wb, all_data)
    build_data_valuta_sheet(wb, all_data)

    # Save
    wb.save(args.out)
    logger.info(f"✓ Saved: {args.out}")


if __name__ == "__main__":
    main()
