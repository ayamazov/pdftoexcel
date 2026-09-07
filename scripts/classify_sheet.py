#!/usr/bin/env python3
"""
Classify Sheet Generator for Estratto di Conto Corrente

Creates contact sheets (stacked page headers) from low-res (110 DPI) PNG images
for quick visual classification of bank statement pages.

Usage:
    python classify_sheet.py lo-*.png --out sheet --frac 0.42x0.17

    --out sheet        Output filename (will create sheet0.png, sheet1.png, etc.)
    --frac 0.42x0.17   Crop fraction (width x height) to extract from each page
    --rows 8           Number of pages per contact sheet (default: 8)
    --height 2800      Contact sheet height in pixels (auto-calculated if not set)
"""

import sys
import argparse
from pathlib import Path
from typing import List, Tuple
import logging

from PIL import Image, ImageDraw, ImageFont


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_frac(frac_str: str) -> Tuple[float, float]:
    """Parse fraction string 'WxH' (e.g., '0.42x0.17') into (width, height) tuple."""
    parts = frac_str.lower().split('x')
    if len(parts) != 2:
        raise ValueError(f"Invalid fraction format: {frac_str}. Use WxH (e.g., 0.42x0.17)")
    return float(parts[0]), float(parts[1])


def extract_header_region(img: Image.Image, frac_w: float, frac_h: float) -> Image.Image:
    """
    Extract header region from page image.

    Args:
        img: PIL Image (full page)
        frac_w: Width fraction (0-1)
        frac_h: Height fraction (0-1)

    Returns:
        Cropped Image containing header region
    """
    w, h = img.size
    left = int(w * 0.0)
    top = int(h * 0.0)
    right = int(w * frac_w)
    bottom = int(h * frac_h)
    return img.crop((left, top, right, bottom))


def create_contact_sheet(
    image_paths: List[str],
    frac_w: float,
    frac_h: float,
    rows_per_sheet: int = 8,
    out_prefix: str = "sheet"
) -> List[str]:
    """
    Create contact sheets from list of page images.

    Args:
        image_paths: List of PNG file paths
        frac_w: Width fraction of header to extract
        frac_h: Height fraction of header to extract
        rows_per_sheet: Number of pages per contact sheet
        out_prefix: Output filename prefix

    Returns:
        List of output PNG paths
    """
    if not image_paths:
        logger.error("No image files provided")
        return []

    output_files = []
    headers = []

    # Extract headers from all images
    logger.info(f"Extracting headers from {len(image_paths)} pages...")
    for i, img_path in enumerate(image_paths):
        try:
            img = Image.open(img_path)
            header = extract_header_region(img, frac_w, frac_h)
            headers.append(header)
            logger.debug(f"Page {i+1}: {img_path} ({header.size[0]}x{header.size[1]})")
        except Exception as e:
            logger.error(f"Failed to process {img_path}: {e}")
            continue

    if not headers:
        logger.error("No headers extracted")
        return []

    # Create contact sheets (multiple headers per sheet)
    logger.info(f"Creating contact sheets ({rows_per_sheet} pages per sheet)...")
    header_width = headers[0].width
    header_height = headers[0].height

    for sheet_idx in range(0, len(headers), rows_per_sheet):
        sheet_headers = headers[sheet_idx:sheet_idx + rows_per_sheet]
        sheet_height = len(sheet_headers) * header_height + (len(sheet_headers) + 1) * 20

        # Create blank sheet
        sheet = Image.new('RGB', (header_width + 40, sheet_height), color=(255, 255, 255))
        draw = ImageDraw.Draw(sheet)

        # Stack headers vertically with page labels
        y_offset = 20
        for i, header in enumerate(sheet_headers):
            page_num = sheet_idx + i + 1

            # Add page number label
            try:
                # Try to use default font, fall back to default if unavailable
                font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()

            draw.text((20, y_offset - 15), f"Page {page_num}", fill=(0, 0, 0), font=font)

            # Paste header
            sheet.paste(header, (20, y_offset))
            y_offset += header_height + 20

        # Save contact sheet
        out_filename = f"{out_prefix}{sheet_idx // rows_per_sheet}.png"
        sheet.save(out_filename)
        logger.info(f"Saved: {out_filename} ({sheet.size[0]}x{sheet.size[1]})")
        output_files.append(out_filename)

    return output_files


def main():
    parser = argparse.ArgumentParser(
        description="Create contact sheets from bank statement page images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python classify_sheet.py lo-*.png --out sheet --frac 0.42x0.17
  python classify_sheet.py lo-*.png --out sheet --frac 0.42x0.17 --rows 6
        """
    )

    parser.add_argument(
        "images",
        nargs="+",
        help="Input PNG files (e.g., lo-*.png)"
    )
    parser.add_argument(
        "--out",
        default="sheet",
        help="Output filename prefix (default: sheet)"
    )
    parser.add_argument(
        "--frac",
        default="0.42x0.17",
        help="Crop fraction WxH (default: 0.42x0.17)"
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=8,
        help="Pages per contact sheet (default: 8)"
    )

    args = parser.parse_args()

    try:
        frac_w, frac_h = parse_frac(args.frac)
    except ValueError as e:
        logger.error(f"Invalid --frac: {e}")
        sys.exit(1)

    # Expand glob patterns if needed
    image_paths = []
    for img_glob in args.images:
        paths = list(Path(".").glob(img_glob))
        image_paths.extend(sorted(str(p) for p in paths))

    if not image_paths:
        logger.error(f"No images found matching: {args.images}")
        sys.exit(1)

    logger.info(f"Processing {len(image_paths)} images: {image_paths[0]}, ...")

    output_files = create_contact_sheet(
        image_paths,
        frac_w,
        frac_h,
        rows_per_sheet=args.rows,
        out_prefix=args.out
    )

    if output_files:
        logger.info(f"✓ Created {len(output_files)} contact sheet(s)")
        for f in output_files:
            print(f)
    else:
        logger.error("No contact sheets created")
        sys.exit(1)


if __name__ == "__main__":
    main()
