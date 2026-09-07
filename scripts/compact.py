#!/usr/bin/env python3
"""
Column Compaction & Zoom Script for Estratto di Conto Corrente

Crops specific columns from high-res (300 DPI) transaction images and creates
8× magnified zooms for uncertain digit verification.

Usage:
    # Crop columns into compact image
    python compact.py hi-03.png --cols 45-280,280-510,645-1100,1220-1600,1610-2750 \
        --rows 580-1650 --out p03.png

    # Create 8× zoom of a specific region (for digit verification)
    python compact.py hi-03.png --zoom 645,580,1100,610 --out doubt.png

    --cols X1-X2,X3-X4,...   Column x-ranges (pixels) to extract and compact
    --rows Y1-Y2             Row y-range (pixels) to extract
    --out FILE               Output filename
    --zoom X1,Y1,X2,Y2       Create zoom box (left,top,right,bottom) at 8×
    --rotate N               Rotate image by N degrees (90, 180, 270)
"""

import sys
import argparse
from pathlib import Path
from typing import Tuple, List, Optional
import logging

from PIL import Image


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_range(range_str: str) -> Tuple[int, int]:
    """Parse range string 'X1-X2' into (X1, X2) tuple."""
    parts = range_str.split('-')
    if len(parts) != 2:
        raise ValueError(f"Invalid range format: {range_str}. Use X1-X2")
    return int(parts[0]), int(parts[1])


def parse_col_ranges(cols_str: str) -> List[Tuple[int, int]]:
    """Parse column ranges string 'X1-X2,X3-X4,...' into list of tuples."""
    if not cols_str:
        return []
    ranges = []
    for col_spec in cols_str.split(','):
        col_spec = col_spec.strip()
        x1, x2 = parse_range(col_spec)
        ranges.append((x1, x2))
    return ranges


def crop_columns(
    img: Image.Image,
    col_ranges: List[Tuple[int, int]],
    row_range: Tuple[int, int]
) -> Image.Image:
    """
    Extract and compact multiple columns from image.

    Args:
        img: PIL Image (full page at 300 DPI)
        col_ranges: List of (x_left, x_right) column ranges
        row_range: (y_top, y_bottom) row range

    Returns:
        Compacted Image with columns arranged horizontally
    """
    y_top, y_bottom = row_range
    height = y_bottom - y_top

    # Extract each column
    columns = []
    for x_left, x_right in col_ranges:
        col = img.crop((x_left, y_top, x_right, y_bottom))
        columns.append(col)

    # Calculate total width (with small gaps)
    gap = 2
    total_width = sum(c.width for c in columns) + (len(columns) - 1) * gap
    compacted = Image.new('RGB', (total_width, height), color=(255, 255, 255))

    # Paste columns
    x_offset = 0
    for i, col in enumerate(columns):
        compacted.paste(col, (x_offset, 0))
        x_offset += col.width + gap

    return compacted


def create_zoom(
    img: Image.Image,
    zoom_box: Tuple[int, int, int, int],
    zoom_level: int = 8
) -> Image.Image:
    """
    Create magnified zoom of a specific region.

    Args:
        img: PIL Image
        zoom_box: (x_left, y_top, x_right, y_bottom) bounding box
        zoom_level: Magnification factor (default: 8×)

    Returns:
        Zoomed Image
    """
    x_left, y_top, x_right, y_bottom = zoom_box
    cropped = img.crop(zoom_box)
    zoomed_size = (
        cropped.width * zoom_level,
        cropped.height * zoom_level
    )
    return cropped.resize(zoomed_size, Image.Resampling.NEAREST)


def main():
    parser = argparse.ArgumentParser(
        description="Crop columns and create zooms from high-res bank statement images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compact multiple columns into single image
  python compact.py hi-03.png \\
    --cols 45-280,280-510,645-1100,1220-1600,1610-2750 \\
    --rows 580-1650 --out p03.png

  # Create 8× zoom of specific region for digit verification
  python compact.py hi-03.png --zoom 645,580,1100,610 --out zoom_detail.png

  # Rotate page before cropping
  python compact.py hi-03.png --rotate 90 --cols 45-280,... --rows 580-1650 --out p03.png
        """
    )

    parser.add_argument(
        "image",
        help="Input PNG file (high-res 300 DPI)"
    )
    parser.add_argument(
        "--cols",
        help="Column x-ranges (e.g., '45-280,280-510,645-1100,1220-1600,1610-2750')"
    )
    parser.add_argument(
        "--rows",
        help="Row y-range (e.g., '580-1650')"
    )
    parser.add_argument(
        "--zoom",
        help="Zoom box as 'X1,Y1,X2,Y2' (e.g., '645,580,1100,610')"
    )
    parser.add_argument(
        "--zoom-level",
        type=int,
        default=8,
        help="Zoom magnification (default: 8×)"
    )
    parser.add_argument(
        "--rotate",
        type=int,
        choices=[90, 180, 270],
        help="Rotate image by N degrees before cropping"
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output filename"
    )

    args = parser.parse_args()

    # Load image
    try:
        img = Image.open(args.image)
        logger.info(f"Loaded: {args.image} ({img.size[0]}x{img.size[1]})")
    except Exception as e:
        logger.error(f"Failed to load {args.image}: {e}")
        sys.exit(1)

    # Apply rotation if specified
    if args.rotate:
        rotation_map = {90: 3, 180: 2, 270: 1}  # PIL uses 90° increments
        img = img.rotate(args.rotate, expand=False)
        logger.info(f"Rotated {args.rotate}° ({img.size[0]}x{img.size[1]})")

    # Process zoom or compact
    if args.zoom:
        # Create zoom
        parts = args.zoom.split(',')
        if len(parts) != 4:
            logger.error(f"Invalid --zoom format: {args.zoom}. Use X1,Y1,X2,Y2")
            sys.exit(1)
        try:
            zoom_box = tuple(int(p) for p in parts)
        except ValueError as e:
            logger.error(f"Invalid --zoom coordinates: {e}")
            sys.exit(1)

        zoomed = create_zoom(img, zoom_box, args.zoom_level)
        zoomed.save(args.out)
        logger.info(f"Saved zoom: {args.out} ({zoomed.size[0]}x{zoomed.size[1]})")

    elif args.cols and args.rows:
        # Compact columns
        try:
            col_ranges = parse_col_ranges(args.cols)
            row_range = parse_range(args.rows)
        except ValueError as e:
            logger.error(f"Invalid column/row ranges: {e}")
            sys.exit(1)

        if not col_ranges:
            logger.error("No columns specified")
            sys.exit(1)

        compacted = crop_columns(img, col_ranges, row_range)
        compacted.save(args.out)
        logger.info(f"Saved compacted: {args.out} ({compacted.size[0]}x{compacted.size[1]})")

    else:
        logger.error("Specify either --zoom or (--cols and --rows)")
        sys.exit(1)


if __name__ == "__main__":
    main()
