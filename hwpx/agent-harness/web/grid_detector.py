"""Detect table grid structure from screenshot images.

Pipeline:
    1. OpenCV: detect horizontal/vertical lines → find intersections → derive grid
    2. EasyOCR: extract text from each cell region
    3. Output: YAML spec or Python code for HWPX generation
"""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class CellInfo:
    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    text: str = ""
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0


@dataclass
class GridResult:
    rows: int
    cols: int
    row_heights: list[int]
    col_widths: list[int]
    cells: list[CellInfo]
    image_width: int = 0
    image_height: int = 0


def detect_grid(image_path: str, min_line_length: int = 50,
                line_threshold: int = 10) -> GridResult:
    """Detect table grid from image.

    Args:
        image_path: Path to the screenshot image.
        min_line_length: Minimum line length to detect (pixels).
        line_threshold: Threshold for merging nearby lines (pixels).

    Returns:
        GridResult with detected grid structure.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot open image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Adaptive threshold for clean line detection
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 15, 5)

    # Detect horizontal lines
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w // 8, 40), 1))
    h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)

    # Detect vertical lines
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h // 8, 40)))
    v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)

    # Find line positions by projection
    h_positions = _find_line_positions(h_lines, axis=0, threshold=line_threshold)
    v_positions = _find_line_positions(v_lines, axis=1, threshold=line_threshold)

    if len(h_positions) < 2 or len(v_positions) < 2:
        raise ValueError(
            f"Could not detect enough grid lines. "
            f"Found {len(h_positions)} horizontal, {len(v_positions)} vertical.")

    rows = len(h_positions) - 1
    cols = len(v_positions) - 1

    # Calculate row heights and column widths (in pixels)
    row_heights_px = [h_positions[i+1] - h_positions[i] for i in range(rows)]
    col_widths_px = [v_positions[i+1] - v_positions[i] for i in range(cols)]

    # Detect merged cells by checking for missing internal lines
    cells = _detect_cells(h_lines, v_lines, h_positions, v_positions, rows, cols)

    return GridResult(
        rows=rows,
        cols=cols,
        row_heights=row_heights_px,
        col_widths=col_widths_px,
        cells=cells,
        image_width=w,
        image_height=h,
    )


def _find_line_positions(line_img: np.ndarray, axis: int,
                         threshold: int = 10) -> list[int]:
    """Find positions of lines by projecting along an axis.

    axis=0: horizontal lines → project vertically (sum each row)
    axis=1: vertical lines → project horizontally (sum each column)
    """
    if axis == 0:
        projection = np.sum(line_img, axis=1)  # sum each row
    else:
        projection = np.sum(line_img, axis=0)  # sum each column

    # Normalize
    projection = projection / 255.0

    # Find peaks (rows/columns with many white pixels)
    min_count = line_img.shape[1 - axis] * 0.15  # at least 15% of width/height
    peak_positions = np.where(projection > min_count)[0]

    if len(peak_positions) == 0:
        return []

    # Merge nearby positions (within threshold)
    merged = [peak_positions[0]]
    for pos in peak_positions[1:]:
        if pos - merged[-1] > threshold:
            merged.append(pos)
        else:
            # Update to average position
            merged[-1] = (merged[-1] + pos) // 2

    return merged


def _detect_cells(h_lines: np.ndarray, v_lines: np.ndarray,
                  h_pos: list[int], v_pos: list[int],
                  rows: int, cols: int) -> list[CellInfo]:
    """Detect individual cells and merged regions."""
    # Create a grid of which cells exist
    # Check if internal borders exist between adjacent cells
    visited = [[False] * cols for _ in range(rows)]
    cells = []

    for r in range(rows):
        for c in range(cols):
            if visited[r][c]:
                continue

            # Determine span by checking for missing borders
            row_span = 1
            col_span = 1

            # Check horizontal span (missing vertical lines to the right)
            for cc in range(c + 1, cols):
                x = v_pos[cc]
                y1 = h_pos[r]
                y2 = h_pos[r + 1]
                if not _has_line_at(v_lines, x, y1, y2, vertical=True):
                    col_span += 1
                else:
                    break

            # Check vertical span (missing horizontal lines below)
            for rr in range(r + 1, rows):
                y = h_pos[rr]
                x1 = v_pos[c]
                x2 = v_pos[c + col_span]
                if not _has_line_at(h_lines, y, x1, x2, vertical=False):
                    row_span += 1
                else:
                    break

            # Mark visited
            for rr in range(r, r + row_span):
                for cc in range(c, c + col_span):
                    if rr < rows and cc < cols:
                        visited[rr][cc] = True

            cell = CellInfo(
                row=r, col=c,
                row_span=row_span, col_span=col_span,
                x=v_pos[c], y=h_pos[r],
                w=v_pos[min(c + col_span, len(v_pos)-1)] - v_pos[c],
                h=h_pos[min(r + row_span, len(h_pos)-1)] - h_pos[r],
            )
            cells.append(cell)

    return cells


def _has_line_at(line_img: np.ndarray, pos: int,
                 start: int, end: int, vertical: bool,
                 sample_ratio: float = 0.3) -> bool:
    """Check if a line exists at position pos between start and end."""
    if vertical:
        # Check vertical line at x=pos from y=start to y=end
        margin = max(2, (end - start) // 10)
        region = line_img[start + margin:end - margin, max(0, pos-2):pos+3]
    else:
        # Check horizontal line at y=pos from x=start to x=end
        margin = max(2, (end - start) // 10)
        region = line_img[max(0, pos-2):pos+3, start + margin:end - margin]

    if region.size == 0:
        return True  # Edge case: assume line exists

    white_ratio = np.sum(region > 0) / region.size
    return white_ratio > sample_ratio


def extract_cell_text(image_path: str, grid: GridResult,
                      languages: list[str] | None = None) -> GridResult:
    """Extract text from each cell using EasyOCR.

    Args:
        image_path: Path to the screenshot.
        grid: GridResult from detect_grid.
        languages: OCR languages (default: ['ko', 'en']).

    Returns:
        Updated GridResult with cell text filled.
    """
    import easyocr
    if languages is None:
        languages = ['ko', 'en']

    reader = easyocr.Reader(languages, gpu=False)
    img = cv2.imread(image_path)

    for cell in grid.cells:
        # Crop cell region with small margin
        margin = 3
        x1 = max(0, cell.x + margin)
        y1 = max(0, cell.y + margin)
        x2 = min(img.shape[1], cell.x + cell.w - margin)
        y2 = min(img.shape[0], cell.y + cell.h - margin)

        if x2 <= x1 or y2 <= y1:
            continue

        cell_img = img[y1:y2, x1:x2]
        results = reader.readtext(cell_img, detail=0, paragraph=True)
        cell.text = "\n".join(results).strip()

    return grid


def grid_to_yaml(grid: GridResult, page_width: int = 42520) -> str:
    """Convert GridResult to YAML specification."""
    # Convert pixel dimensions to hwpunit
    total_px_w = sum(grid.col_widths)
    total_px_h = sum(grid.row_heights)

    col_widths_hw = [int(w / total_px_w * page_width) for w in grid.col_widths]
    # Adjust rounding
    diff = page_width - sum(col_widths_hw)
    if col_widths_hw:
        col_widths_hw[-1] += diff

    # Scale row heights proportionally (A4 body ≈ 60000 hwpunit)
    page_height = 60000
    row_heights_hw = [int(h / total_px_h * page_height) for h in grid.row_heights]

    lines = [
        f"# Auto-detected grid: {grid.rows} rows x {grid.cols} cols",
        f"grid: {grid.rows}x{grid.cols}",
        f"page_width: {page_width}",
        f"",
        f"row_heights: {row_heights_hw}",
        f"col_widths: {col_widths_hw}",
        f"",
        f"cells:",
    ]

    for cell in grid.cells:
        merge = ""
        if cell.row_span > 1 or cell.col_span > 1:
            merge = f"  merge: [{cell.row},{cell.col},{cell.row+cell.row_span-1},{cell.col+cell.col_span-1}]"
        text = cell.text.replace('"', '\\"') if cell.text else ""
        lines.append(f"  - row: {cell.row}")
        lines.append(f"    col: {cell.col}")
        if merge:
            lines.append(merge)
        if text:
            lines.append(f'    text: "{text}"')

    return "\n".join(lines)


def grid_to_python(grid: GridResult, page_width: int = 42520) -> str:
    """Generate Python code to create the HWPX table."""
    total_px_w = sum(grid.col_widths)
    total_px_h = sum(grid.row_heights)

    col_widths_hw = [int(w / total_px_w * page_width) for w in grid.col_widths]
    diff = page_width - sum(col_widths_hw)
    if col_widths_hw:
        col_widths_hw[-1] += diff

    page_height = 60000
    row_heights_hw = [int(h / total_px_h * page_height) for h in grid.row_heights]

    lines = [
        "from hwpx import HwpxDocument",
        "",
        "doc = HwpxDocument.new()",
        f"tbl = doc.add_table({grid.rows}, {grid.cols}, width={page_width})",
        f"tbl.set_row_heights({row_heights_hw})",
        f"tbl.set_col_widths({col_widths_hw})",
        "",
        "# Cell text",
    ]

    for cell in grid.cells:
        if cell.text:
            escaped = cell.text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            lines.append(f'tbl.set_cell_text({cell.row}, {cell.col}, "{escaped}")')

    lines.append("")
    lines.append("# Merges")
    for cell in grid.cells:
        if cell.row_span > 1 or cell.col_span > 1:
            er = cell.row + cell.row_span - 1
            ec = cell.col + cell.col_span - 1
            lines.append(f"tbl.merge_cells({cell.row}, {cell.col}, {er}, {ec})")

    lines.append("")
    lines.append('doc.save_to_path("output.hwpx")')

    return "\n".join(lines)
