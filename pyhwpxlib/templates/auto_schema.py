"""Auto-generate a fill-template schema from a HWPX form.

Heuristic
---------
1. For each table, extract every cell with its (row, col) and span.
2. Detect a *grid sub-region*: contiguous run of value-only rows (≥3) sharing
   the same column set (size ≥2). That's where repeated participants live.
3. For each value cell:
   - **Label cells** (short text, no placeholder): skip.
   - **Inside grid region**: combine row-group label (rs>1 cell to the left)
     + per-column header → ``member_1_name``, ``member_2_dept`` etc.
   - **Outside grid region**: find adjacent label (cellSpan-aware: a header
     with colSpan=2 covers two columns, a row-label with rowSpan=4 covers
     four rows).
4. Build field key from label via :mod:`slugify`, disambiguating collisions.

Output schema follows the format used by ``skill/templates/*.schema.json``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pyhwpxlib.templates.slugify import label_to_key, slugify


_PLACEHOLDER_PATTERNS = [
    re.compile(r"x{2,}\.x{2,}", re.IGNORECASE),       # 2026.xx.xx
    re.compile(r"x{2,}\s*\.\s*x{2,}", re.IGNORECASE), # xx . xx
    re.compile(r"^[0\-]+\s*회차"),                    # 0회차
    re.compile(r"\(예시\)"),
    re.compile(r"\(별도\s*기재\)"),
    re.compile(r"^\s*-{2,}\s*$"),
    re.compile(r"^\s*\.{3,}\s*$"),
]


@dataclass
class GridRegion:
    """A contiguous block of value-only rows sharing the same column set."""
    start: int
    end: int
    cols: frozenset

    @property
    def length(self) -> int:
        return self.end - self.start + 1

    def contains(self, row: int, col: int) -> bool:
        return self.start <= row <= self.end and col in self.cols


def _is_placeholder(text: str) -> bool:
    if not text or not text.strip():
        return False
    return any(p.search(text) for p in _PLACEHOLDER_PATTERNS)


def _find_balanced_tables(xml: str):
    """Yield (start, end) of each top-level <hp:tbl>...</hp:tbl> (depth-aware)."""
    pos = 0
    while True:
        m = re.search(r"<hp:tbl\b", xml[pos:])
        if not m:
            return
        s = pos + m.start()
        depth = 1
        scan = s + len(m.group(0))
        scan = xml.find(">", scan) + 1
        while depth > 0:
            o = xml.find("<hp:tbl", scan)
            c = xml.find("</hp:tbl>", scan)
            if c == -1:
                break
            if o != -1 and o < c:
                depth += 1
                scan = o + 7
            else:
                depth -= 1
                scan = c + 9
        yield s, scan
        pos = scan


def _extract_cells(tbl_xml: str) -> list[dict]:
    """Return [{row, col, rs, cs, text}] for every cell in a table (depth-aware)."""
    cells = []
    for m in re.finditer(r"<hp:tc\b", tbl_xml):
        s = m.start()
        depth = 1
        scan = m.end()
        while depth > 0:
            o = tbl_xml.find("<hp:tc", scan)
            c = tbl_xml.find("</hp:tc>", scan)
            if c == -1:
                break
            if o != -1 and o < c:
                depth += 1
                scan = o + 6
            else:
                depth -= 1
                scan = c + 7
        cell_xml = tbl_xml[s:scan]
        addr = re.search(
            r"<hp:cellAddr\b[^/]*colAddr=\"(\d+)\"[^/]*rowAddr=\"(\d+)\"",
            cell_xml,
        )
        if not addr:
            continue
        col, row = int(addr.group(1)), int(addr.group(2))
        span = re.search(
            r"<hp:cellSpan\b[^/]*colSpan=\"(\d+)\"[^/]*rowSpan=\"(\d+)\"",
            cell_xml,
        )
        cs, rs = (int(span.group(1)), int(span.group(2))) if span else (1, 1)
        ts = re.findall(r"<hp:t[^>]*>([^<]*)</hp:t>", cell_xml)
        text = " / ".join(t.strip() for t in ts if t.strip())
        cells.append({"row": row, "col": col, "rs": rs, "cs": cs, "text": text})
    return cells


def _is_label(text: str, max_len: int = 20) -> bool:
    """Heuristic: short text, not a placeholder, looks like a label."""
    if not text:
        return False
    if _is_placeholder(text):
        return False
    if len(text) > max_len:
        return False
    return True


def _find_label_for(
    value_cell: dict, cells: list[dict], *, prefer_header: bool = True
) -> Optional[str]:
    """For a value cell, find the closest label (cellSpan-aware).

    A header at ``(r, c)`` with ``colSpan=cs`` covers columns ``[c, c+cs)``,
    so a value cell at any of those columns matches. Same for rowSpan with
    a row-label.

    With ``prefer_header=True`` (used inside grid sub-regions), a column
    header in a row above wins over a left-side row label.
    """
    row, col = value_cell["row"], value_cell["col"]
    above = [
        c for c in cells
        if c["row"] < row
        and c["col"] <= col < c["col"] + c["cs"]
        and _is_label(c["text"])
    ]
    left = [
        c for c in cells
        if c["col"] < col
        and c["row"] <= row < c["row"] + c["rs"]
        and _is_label(c["text"])
    ]
    if prefer_header and above:
        return max(above, key=lambda c: c["row"])["text"]
    if left:
        return max(left, key=lambda c: c["col"])["text"]
    if above:
        return max(above, key=lambda c: c["row"])["text"]
    return None


def _find_row_group_label(value_cell: dict, cells: list[dict]) -> Optional[str]:
    """Return the rowSpan>1 group label that covers this value cell, if any.

    Looks for cells to the left whose rowSpan range includes ``value_cell.row``.
    Used to detect "참 여 자" (rs=4) row group in repeated grids.
    """
    row, col = value_cell["row"], value_cell["col"]
    candidates = [
        c for c in cells
        if c["col"] < col
        and c["rs"] >= 2  # only true row-group cells, not single cells to the left
        and c["row"] <= row < c["row"] + c["rs"]
        and _is_label(c["text"])
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda c: c["col"])["text"]


def _find_grid_subregion(cells: list[dict]) -> Optional[GridRegion]:
    """Find the longest contiguous run of value-only rows with identical col set.

    Conditions:
      1. Run length >= 3 rows
      2. All rows in the run consist solely of value cells (empty/placeholder)
         on the same set of columns
      3. Column set size >= 2

    Returns the longest such region, or ``None``.
    """
    by_row: dict[int, set[int]] = {}
    for c in cells:
        if not c["text"] or _is_placeholder(c["text"]):
            by_row.setdefault(c["row"], set()).add(c["col"])
    if not by_row:
        return None

    rows = sorted(by_row)
    best: Optional[GridRegion] = None
    i = 0
    while i < len(rows):
        cols_i = by_row[rows[i]]
        if len(cols_i) < 2:
            i += 1
            continue
        j = i
        while j + 1 < len(rows) and rows[j + 1] == rows[j] + 1 and by_row[rows[j + 1]] == cols_i:
            j += 1
        run = j - i + 1
        if run >= 3 and (best is None or run > best.length):
            best = GridRegion(start=rows[i], end=rows[j], cols=frozenset(cols_i))
        i = j + 1
    return best


def _build_field_in_grid(
    cell: dict, cells: list, grid: GridRegion, used_keys: set, fallback_index: list
) -> dict:
    """Build a field for a value cell that lies inside a grid sub-region."""
    col_header = _find_label_for(cell, cells, prefer_header=True)
    row_group = _find_row_group_label(cell, cells)
    row_idx = cell["row"] - grid.start + 1  # 1-based

    if row_group and col_header:
        group_part = slugify(row_group, fallback_index=fallback_index[0])
        field_part = slugify(col_header, fallback_index=fallback_index[0])
        candidate = f"{group_part}_{row_idx}_{field_part}"
        # disambiguate against used_keys
        key = candidate
        n = 2
        while key in used_keys:
            key = f"{candidate}_{n}"
            n += 1
        used_keys.add(key)
        label = f"{row_group} {row_idx} {col_header}".strip()
    elif col_header:
        fallback_index[0] += 1
        key = label_to_key(
            f"{col_header}_{row_idx}", used_keys, fallback_index=fallback_index[0]
        )
        label = col_header
    else:
        fallback_index[0] += 1
        key = f"field_{cell['row']}_{cell['col']}"
        used_keys.add(key)
        label = ""

    field = {
        "key": key,
        "cell": [cell["row"], cell["col"]],
        "label": label,
    }
    if (cell["rs"], cell["cs"]) != (1, 1):
        field["span"] = [cell["rs"], cell["cs"]]
    if _is_placeholder(cell["text"]):
        field["placeholder"] = cell["text"]
    return field


def _build_field_single(
    cell: dict, cells: list, used_keys: set, fallback_index: list
) -> dict:
    """Build a field for a value cell outside any grid sub-region."""
    label = _find_label_for(cell, cells, prefer_header=False)
    label_for_key = label or cell["text"] or f"cell_{cell['row']}_{cell['col']}"
    fallback_index[0] += 1
    key = label_to_key(label_for_key, used_keys, fallback_index=fallback_index[0])
    field = {
        "key": key,
        "cell": [cell["row"], cell["col"]],
        "label": label or "",
    }
    if (cell["rs"], cell["cs"]) != (1, 1):
        field["span"] = [cell["rs"], cell["cs"]]
    if _is_placeholder(cell["text"]):
        field["placeholder"] = cell["text"]
    return field


def generate_schema(
    section_xml: str,
    *,
    name: str,
    title: Optional[str] = None,
    source: Optional[str] = None,
) -> dict:
    """Generate a schema dict from a section XML string."""
    used_keys: set[str] = set()
    fallback_index = [0]
    schema = {
        "name": name,
        "title": title or name,
        "description": f"Auto-generated schema for {name}",
        "version": "1.0",
        "auto_generated": True,
        "source": source or "",
        "tables": [],
    }

    for t_idx, (ts, te) in enumerate(_find_balanced_tables(section_xml)):
        tbl_xml = section_xml[ts:te]
        cells = _extract_cells(tbl_xml)
        if not cells:
            continue
        max_row = max(c["row"] for c in cells)
        max_col = max(c["col"] for c in cells)

        grid = _find_grid_subregion(cells)
        fields = []
        for cell in cells:
            text = cell["text"]
            is_empty = not text
            is_ph = _is_placeholder(text)
            if not (is_empty or is_ph):
                continue  # label cell

            if grid is not None and grid.contains(cell["row"], cell["col"]):
                field = _build_field_in_grid(cell, cells, grid, used_keys, fallback_index)
            else:
                field = _build_field_single(cell, cells, used_keys, fallback_index)
            fields.append(field)

        schema["tables"].append({
            "index": t_idx,
            "rows": max_row + 1,
            "cols": max_col + 1,
            "fields": fields,
        })

    return schema


def generate_schema_from_hwpx(path: str | Path, *, name: str) -> dict:
    """Convenience: open the HWPX file and run generate_schema on section0."""
    import zipfile
    p = Path(path)
    with zipfile.ZipFile(p) as z:
        section_xml = z.read("Contents/section0.xml").decode("utf-8")
    return generate_schema(section_xml, name=name, title=p.stem, source=str(p))
