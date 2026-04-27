"""Auto-generate a fill-template schema from a HWPX form.

Heuristic
---------
1. For each table, extract every cell with its (row, col) and span.
2. Classify each cell:
   - **label**: short text, no placeholder pattern (e.g. ``성명``, ``프로젝트명``)
   - **value-empty**: empty cell — needs to be filled
   - **value-placeholder**: has a placeholder text (e.g. ``2026.xx.xx.``,
     ``0회차 활동``, ``(예시)``) — needs to be replaced
3. For each value cell, find the **adjacent label**:
   - same row, smaller col (left neighbor) — most common
   - same col, smaller row (above) — vertical layouts
4. Build field key from label via :mod:`slugify`.

Output schema follows the format used by ``skill/templates/*.schema.json``.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

from pyhwpxlib.templates.slugify import label_to_key


_PLACEHOLDER_PATTERNS = [
    re.compile(r"x{2,}\.x{2,}", re.IGNORECASE),       # 2026.xx.xx
    re.compile(r"x{2,}\s*\.\s*x{2,}", re.IGNORECASE), # xx . xx
    re.compile(r"^[0\-]+\s*회차"),                    # 0회차
    re.compile(r"\(예시\)"),
    re.compile(r"\(별도\s*기재\)"),
    re.compile(r"^\s*-{2,}\s*$"),
    re.compile(r"^\s*\.{3,}\s*$"),
]


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
        # walk to matching close
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
    """For a value cell, find the closest label.

    With ``prefer_header=True`` (default for repeated-row tables), a column
    header in the topmost row(s) wins over a left-side row label. This makes
    grid-style tables like

        |       | 성명 | 학과 | 학번 | 서명 |
        | 참여자 |     |     |      |      |
        | 참여자 |     |     |      |      |

    correctly bind the empty cells to ``성명`` (header) instead of ``참여자``
    (row group label), so collisions disambiguate as ``name``, ``name_2``,
    ``name_3`` rather than ``field_2``, ``field_3``.
    """
    row, col = value_cell["row"], value_cell["col"]
    above_candidates = [
        c for c in cells
        if c["col"] == col and c["row"] < row and _is_label(c["text"])
    ]
    left_candidates = [
        c for c in cells
        if c["row"] == row and c["col"] < col and _is_label(c["text"])
    ]
    if prefer_header and above_candidates:
        return max(above_candidates, key=lambda c: c["row"])["text"]
    if left_candidates:
        return max(left_candidates, key=lambda c: c["col"])["text"]
    if above_candidates:
        return max(above_candidates, key=lambda c: c["row"])["text"]
    return None


def _detect_repeated_grid(cells: list[dict]) -> bool:
    """Heuristic: table has ≥3 value-rows where each row has the same set of cols.

    Triggers ``prefer_header=True`` for label resolution.
    """
    by_row = {}
    for c in cells:
        if not c["text"] or _is_placeholder(c["text"]):
            by_row.setdefault(c["row"], set()).add(c["col"])
    if len(by_row) < 3:
        return False
    col_sets = list(by_row.values())
    # all value-rows share at least 3 common columns
    common = set.intersection(*col_sets) if col_sets else set()
    return len(common) >= 2


def generate_schema(
    section_xml: str,
    *,
    name: str,
    title: Optional[str] = None,
    source: Optional[str] = None,
) -> dict:
    """Generate a schema dict from a section XML string.

    Parameters
    ----------
    section_xml : full ``Contents/section0.xml`` content
    name : ASCII template name (e.g. ``"makers_project_report"``)
    title : human-readable title (optional)
    source : original file path (optional)
    """
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
        fields = []
        prefer_header = _detect_repeated_grid(cells)

        for cell in cells:
            text = cell["text"]
            is_empty = not text
            is_ph = _is_placeholder(text)
            if not (is_empty or is_ph):
                continue  # this is a label, skip
            label = _find_label_for(cell, cells, prefer_header=prefer_header)
            label_for_key = label or text or f"cell_{cell['row']}_{cell['col']}"
            fallback_index[0] += 1
            key = label_to_key(label_for_key, used_keys, fallback_index=fallback_index[0])
            field = {
                "key": key,
                "cell": [cell["row"], cell["col"]],
                "label": label or "",
            }
            if (cell["rs"], cell["cs"]) != (1, 1):
                field["span"] = [cell["rs"], cell["cs"]]
            if is_ph:
                field["placeholder"] = text
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
