"""Generate HWPX from screenshot image using OpenCV grid detection + OCR.

Pipeline:
    1. Upload image (screenshot/scan of a form)
    2. OpenCV detects grid lines → row/col positions
    3. EasyOCR extracts text from each cell
    4. Generate HWPX with exact proportions
"""

from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass

from hwpx import HwpxDocument


@dataclass
class DetectedForm:
    """Result of image analysis."""
    rows: int
    cols: int
    row_heights_pct: list[float]   # percentage of total height
    col_widths_pct: list[float]    # percentage of total width
    cells: list[dict]              # [{row, col, row_span, col_span, text}]
    image_width: int
    image_height: int


def analyze_image(image_path: str) -> DetectedForm:
    """Analyze a form image and return detected grid + text."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot open: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 3)

    # Horizontal lines
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (w // 15, 1))
    h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)

    # Vertical lines (sensitive — short internal lines too)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, h // 50))
    v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)

    h_pos = _find_positions(h_lines, axis=0, img_size=w, min_ratio=0.08)
    v_pos = _find_positions(v_lines, axis=1, img_size=h, min_ratio=0.03)

    if len(h_pos) < 2 or len(v_pos) < 2:
        raise ValueError(f"Grid not detected (h={len(h_pos)}, v={len(v_pos)})")

    rows = len(h_pos) - 1
    cols = len(v_pos) - 1

    total_h = h_pos[-1] - h_pos[0]
    total_w = v_pos[-1] - v_pos[0]

    row_heights_pct = [round((h_pos[i+1] - h_pos[i]) / total_h * 100, 1) for i in range(rows)]
    col_widths_pct = [round((v_pos[i+1] - v_pos[i]) / total_w * 100, 1) for i in range(cols)]

    # Detect cells (with merge detection)
    cells = _detect_cells(h_lines, v_lines, h_pos, v_pos, rows, cols)

    # OCR
    cells = _ocr_cells(img, cells, h_pos, v_pos)

    return DetectedForm(
        rows=rows, cols=cols,
        row_heights_pct=row_heights_pct,
        col_widths_pct=col_widths_pct,
        cells=cells,
        image_width=w, image_height=h,
    )


def generate_hwpx(form: DetectedForm, output_path: str,
                   page_width: int = 42520, page_height: int = 60000) -> str:
    """Generate HWPX file from detected form structure."""
    doc = HwpxDocument.new()

    row_heights = [int(page_height * p / 100) for p in form.row_heights_pct]
    col_widths = [int(page_width * p / 100) for p in form.col_widths_pct]

    # Adjust rounding
    row_heights[-1] += page_height - sum(row_heights)
    col_widths[-1] += page_width - sum(col_widths)

    tbl = doc.add_table(form.rows, form.cols, width=page_width)
    tbl.set_row_heights(row_heights)
    tbl.set_col_widths(col_widths)

    # Set text first (before merges)
    for cell in form.cells:
        if cell["text"]:
            tbl.set_cell_text(cell["row"], cell["col"], cell["text"])

    # Apply merges (safe order: avoid empty rows)
    merges = _safe_merge_order(form.cells)
    for r1, c1, r2, c2 in merges:
        try:
            tbl.merge_cells(r1, c1, r2, c2)
        except (ValueError, IndexError):
            pass

    # Auto-style: center title row, align labels
    for cell in form.cells:
        r, c = cell["row"], cell["col"]
        try:
            if cell["row_span"] == form.rows or (r == 0 and cell["col_span"] == form.cols):
                tbl.set_cell_align(r, c, horizontal="CENTER", vertical="CENTER")
        except (IndexError, AttributeError):
            pass

    # Padding
    for r in range(form.rows):
        for c in range(form.cols):
            try:
                tbl.cell(r, c).set_margin(left=200, right=200, top=100, bottom=100)
            except (IndexError, AttributeError):
                pass

    doc.save_to_path(output_path)
    return output_path


def _find_positions(line_img: np.ndarray, axis: int,
                    img_size: int, min_ratio: float = 0.08) -> list[int]:
    if axis == 0:
        proj = np.sum(line_img, axis=1) / 255.0
    else:
        proj = np.sum(line_img, axis=0) / 255.0

    peaks = np.where(proj > img_size * min_ratio)[0]
    if len(peaks) == 0:
        return []

    merged = [int(peaks[0])]
    for p in peaks[1:]:
        if p - merged[-1] > 5:
            merged.append(int(p))
    return merged


def _has_line(line_img: np.ndarray, pos: int, start: int, end: int,
              vertical: bool, ratio: float = 0.3) -> bool:
    margin = max(2, (end - start) // 10)
    if vertical:
        region = line_img[start+margin:end-margin, max(0, pos-2):pos+3]
    else:
        region = line_img[max(0, pos-2):pos+3, start+margin:end-margin]
    if region.size == 0:
        return True
    return (np.sum(region > 0) / region.size) > ratio


def _detect_cells(h_lines, v_lines, h_pos, v_pos, rows, cols):
    visited = [[False]*cols for _ in range(rows)]
    cells = []

    for r in range(rows):
        for c in range(cols):
            if visited[r][c]:
                continue
            cs = 1
            for cc in range(c+1, cols):
                if not _has_line(v_lines, v_pos[cc], h_pos[r], h_pos[r+1], True):
                    cs += 1
                else:
                    break
            rs = 1
            for rr in range(r+1, rows):
                x2 = v_pos[min(c+cs, len(v_pos)-1)]
                if not _has_line(h_lines, h_pos[rr], v_pos[c], x2, False):
                    rs += 1
                else:
                    break
            for rr in range(r, r+rs):
                for cc in range(c, c+cs):
                    if rr < rows and cc < cols:
                        visited[rr][cc] = True
            cells.append({
                "row": r, "col": c,
                "row_span": rs, "col_span": cs,
                "text": "",
                "x": v_pos[c], "y": h_pos[r],
                "w": v_pos[min(c+cs, len(v_pos)-1)] - v_pos[c],
                "h": h_pos[min(r+rs, len(h_pos)-1)] - h_pos[r],
            })
    return cells


def _ocr_cells(img, cells, h_pos, v_pos):
    """Extract text from cells. Try Claude first, fall back to EasyOCR."""
    # Save full image to temp for Claude
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    cv2.imwrite(tmp.name, img)
    tmp.close()

    try:
        cells = _ocr_cells_claude(tmp.name, img, cells)
    except Exception:
        # Fallback to EasyOCR
        cells = _ocr_cells_easyocr(img, cells)
    finally:
        Path(tmp.name).unlink(missing_ok=True)

    return cells


def _ocr_cells_claude(image_path: str, img, cells) -> list[dict]:
    """Use Claude to read cell text — better Korean accuracy than EasyOCR."""
    import subprocess
    import json
    import os
    import base64

    claude_path = None
    for p in [os.path.expanduser("~/.local/bin/claude"), "/usr/local/bin/claude"]:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            claude_path = p
            break
    if claude_path is None:
        try:
            result = subprocess.run(["which", "claude"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                claude_path = result.stdout.strip()
        except Exception:
            pass
    if not claude_path:
        raise RuntimeError("claude CLI not found")

    # Save each cell as separate image
    import tempfile
    cell_images = []
    for i, cell in enumerate(cells):
        margin = 2
        x1 = max(0, cell["x"] + margin)
        y1 = max(0, cell["y"] + margin)
        x2 = min(img.shape[1], cell["x"] + cell["w"] - margin)
        y2 = min(img.shape[0], cell["y"] + cell["h"] - margin)
        if x2 <= x1 or y2 <= y1:
            cell_images.append(None)
            continue
        cell_img = img[y1:y2, x1:x2]
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        cv2.imwrite(tmp.name, cell_img)
        tmp.close()
        cell_images.append(tmp.name)

    # Build prompt with cell descriptions
    prompt = (
        "다음은 한국어 양식 문서의 각 셀 이미지입니다. "
        "각 셀에 있는 텍스트를 정확히 읽어주세요. "
        "빈 셀은 빈 문자열로 응답하세요. "
        "JSON 배열로만 응답하세요. 설명 없이 텍스트만.\n"
        f"총 {len(cells)}개 셀입니다. 각 셀의 텍스트를 순서대로 JSON 배열로 주세요.\n"
        '예: ["제목", "성명", "", "전화번호", ...]'
    )

    # Use full image + cell coordinates instead of individual images
    # (sending individual images is too many API calls)
    cell_descs = []
    for i, cell in enumerate(cells):
        span = ""
        if cell["row_span"] > 1 or cell["col_span"] > 1:
            span = f" (span {cell['row_span']}x{cell['col_span']})"
        cell_descs.append(f"셀[{cell['row']},{cell['col']}]{span}: 위치 x={cell['x']} y={cell['y']} w={cell['w']} h={cell['h']}")

    full_prompt = (
        "이 이미지는 한국어 양식 문서입니다. 각 셀의 텍스트를 읽어주세요.\n\n"
        "셀 위치:\n" + "\n".join(cell_descs) + "\n\n"
        "각 셀의 텍스트를 JSON 배열로 응답하세요. 빈 셀은 빈 문자열.\n"
        '형식: ["텍스트1", "텍스트2", "", ...]'
    )

    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    result = subprocess.run(
        [claude_path, "-p", full_prompt, "--output-format", "text"],
        capture_output=True, text=True, timeout=120,
        env=env, stdin=open(image_path, "rb"),
    )

    # Cleanup temp files
    for path in cell_images:
        if path:
            Path(path).unlink(missing_ok=True)

    if result.returncode != 0:
        raise RuntimeError(f"Claude failed: {result.stderr[:200]}")

    # Parse JSON response
    output = result.stdout.strip()
    # Find JSON array in output
    start = output.find("[")
    end = output.rfind("]") + 1
    if start >= 0 and end > start:
        texts = json.loads(output[start:end])
        for i, text in enumerate(texts):
            if i < len(cells):
                cells[i]["text"] = str(text).strip()

    return cells


def _ocr_cells_easyocr(img, cells) -> list[dict]:
    """Fallback: EasyOCR for text extraction."""
    try:
        import easyocr
        reader = easyocr.Reader(['ko', 'en'], gpu=False)
    except ImportError:
        return cells

    for cell in cells:
        margin = 3
        x1 = max(0, cell["x"] + margin)
        y1 = max(0, cell["y"] + margin)
        x2 = min(img.shape[1], cell["x"] + cell["w"] - margin)
        y2 = min(img.shape[0], cell["y"] + cell["h"] - margin)
        if x2 <= x1 or y2 <= y1:
            continue
        results = reader.readtext(img[y1:y2, x1:x2], detail=0, paragraph=True)
        cell["text"] = "\n".join(results).strip()
    return cells


def _safe_merge_order(cells):
    """Sort merges to avoid empty rows: horizontal first, then vertical."""
    h_merges = []  # colSpan only
    v_merges = []  # rowSpan only
    b_merges = []  # both

    for cell in cells:
        rs, cs = cell["row_span"], cell["col_span"]
        if rs <= 1 and cs <= 1:
            continue
        r1, c1 = cell["row"], cell["col"]
        r2, c2 = r1 + rs - 1, c1 + cs - 1
        if rs == 1:
            h_merges.append((r1, c1, r2, c2))
        elif cs == 1:
            v_merges.append((r1, c1, r2, c2))
        else:
            b_merges.append((r1, c1, r2, c2))

    # Horizontal first, then vertical, then block
    return h_merges + v_merges + b_merges
