"""Fill a template HWPX with values from a data dict, using the schema mapping.

Approach
--------
For each field in the schema:
- Locate the (table, row, col) cell in section0.xml (depth-aware match)
- Replace the first ``<hp:t>...</hp:t>`` text node inside the first paragraph
  of that cell with ``data[field.key]``

We replace **first hp:t only** (other hp:t in the same paragraph are emptied)
because OWPML allows a single hp:run/hp:t to carry the entire cell text. This
mirrors the pattern used in ``references/form_automation.md``.

XML escaping is applied to the new text (``& < >``).

After all replacements, save via :func:`pyhwpxlib.package_ops.write_zip_archive`
(default ``strip_linesegs="precise"``) so the output passes Hancom's security
check.
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


def _find_balanced_tables(xml: str):
    pos = 0
    while True:
        m = re.search(r"<hp:tbl\b", xml[pos:])
        if not m:
            return
        s = pos + m.start()
        depth = 1
        scan = xml.find(">", s + len(m.group(0))) + 1
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


def _find_cell(tbl_xml: str, target_row: int, target_col: int) -> tuple[int, int] | None:
    """Find (start, end) of the cell at (row, col) inside a table (depth-aware)."""
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
        cell = tbl_xml[s:scan]
        addr = re.search(
            r"<hp:cellAddr\b[^/]*colAddr=\"(\d+)\"[^/]*rowAddr=\"(\d+)\"",
            cell,
        )
        if not addr:
            continue
        col, row = int(addr.group(1)), int(addr.group(2))
        if (row, col) == (target_row, target_col):
            return s, scan
    return None


def _replace_first_paragraph_text(cell_xml: str, new_text: str) -> str:
    """Replace the first paragraph's first hp:t with new_text, blank the rest of that paragraph.

    Handles three text-node forms found in HWPX:
      - ``<hp:t>existing text</hp:t>`` — typical placeholder cell
      - ``<hp:t/>`` — self-closing empty tag, used in pristine empty cells
      - ``<hp:t></hp:t>`` — empty paired form
    For the first match we replace its content with ``new_text``; for any
    subsequent ``hp:t`` in the same paragraph we keep the open/close form but
    empty the content (so cell text stays clean across runs).
    """
    p_match = re.search(r"<hp:p[\s>].*?</hp:p>", cell_xml, re.DOTALL)
    if not p_match:
        return cell_xml
    p = p_match.group(0)
    first = [False]
    new_text_escaped = _escape_xml(new_text)

    # Combined pattern: matches either self-closing `<hp:t .../>` (group 1) or
    # paired `<hp:t ...>content</hp:t>` (groups 2,3,4).
    pattern = re.compile(
        r"(<hp:t[^>]*?/>)"                       # group 1: self-closing
        r"|"
        r"(<hp:t[^>]*>)([^<]*)(</hp:t>)"         # 2/3/4: paired
    )

    def t_repl(m):
        if m.group(1):  # self-closing form
            if not first[0]:
                first[0] = True
                return f"<hp:t>{new_text_escaped}</hp:t>"
            return "<hp:t></hp:t>"
        # paired form
        if not first[0]:
            first[0] = True
            return f"{m.group(2)}{new_text_escaped}{m.group(4)}"
        return f"{m.group(2)}{m.group(4)}"

    new_p = pattern.sub(t_repl, p)
    return cell_xml[: p_match.start()] + new_p + cell_xml[p_match.end():]


def fill_section(section_xml: str, schema: dict, data: dict[str, Any]) -> tuple[str, dict]:
    """Apply data to section_xml using schema. Returns (new_xml, summary)."""
    summary = {"filled": [], "skipped": [], "missing_in_data": []}
    tables = list(_find_balanced_tables(section_xml))
    if not tables:
        return section_xml, summary
    new_xml = section_xml

    for table in schema.get("tables", []):
        t_idx = table.get("index")
        if t_idx is None or t_idx >= len(tables):
            continue
        for field in table.get("fields", []):
            key = field.get("key")
            if key not in data:
                summary["missing_in_data"].append(key)
                continue
            value = str(data[key]) if data[key] is not None else ""
            cell = field.get("cell") or [None, None]
            row, col = cell[0], cell[1]
            if row is None or col is None:
                summary["skipped"].append({"key": key, "reason": "no cell"})
                continue
            # locate table fresh after each replace (positions shift)
            tables_now = list(_find_balanced_tables(new_xml))
            if t_idx >= len(tables_now):
                summary["skipped"].append({"key": key, "reason": "table missing"})
                continue
            ts, te = tables_now[t_idx]
            tbl_xml = new_xml[ts:te]
            rng = _find_cell(tbl_xml, row, col)
            if rng is None:
                summary["skipped"].append({"key": key, "reason": f"cell ({row},{col}) not found"})
                continue
            cs, ce = rng
            cell_xml = tbl_xml[cs:ce]
            new_cell = _replace_first_paragraph_text(cell_xml, value)
            new_tbl = tbl_xml[:cs] + new_cell + tbl_xml[ce:]
            new_xml = new_xml[:ts] + new_tbl + new_xml[te:]
            summary["filled"].append(key)

    return new_xml, summary


def fill_template_file(
    template_name_or_path: str,
    data: dict[str, Any] | str | Path,
    output_path: str | Path,
    *,
    schema_path: str | Path | None = None,
    fix_linesegs: bool = False,
) -> dict:
    """Fill a registered template (or hwpx file) with data, write to output_path.

    Parameters
    ----------
    template_name_or_path : registered template name (resolved via XDG/skill dir)
        or direct path to a .hwpx file.
    data : dict or path/str pointing to JSON file
    output_path : where to write the filled .hwpx
    schema_path : explicit schema path. If None, resolves alongside the template.
    fix_linesegs : when True, apply the precise textpos-overflow fix on save
        (Hancom security trigger workaround). Default False per v0.14.0
        rhwp-aligned policy: caller must opt in to silent corrections so
        external renderers / validators see the original structures.
    """
    from pyhwpxlib.templates.resolver import resolve_template_path
    from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

    # resolve template
    p = Path(template_name_or_path)
    if p.exists() and p.suffix == ".hwpx":
        hwpx_path = p
        if schema_path is None:
            cand = p.with_suffix(".schema.json")
            schema_path = cand if cand.exists() else None
    else:
        hwpx_path = resolve_template_path(template_name_or_path, suffix=".hwpx")
        if hwpx_path is None:
            raise FileNotFoundError(f"template not found: {template_name_or_path}")
        if schema_path is None:
            schema_path = resolve_template_path(
                template_name_or_path, suffix=".schema.json"
            )

    if schema_path is None or not Path(schema_path).exists():
        raise FileNotFoundError(
            f"schema not found for template {template_name_or_path}"
        )

    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))

    if isinstance(data, (str, Path)) and Path(data).exists():
        data = json.loads(Path(data).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("data must be a dict or a path to a JSON file")

    archive = read_zip_archive(str(hwpx_path))
    section_xml = archive.files["Contents/section0.xml"].decode("utf-8")
    new_xml, summary = fill_section(section_xml, schema, data)
    new_files = dict(archive.files)
    new_files["Contents/section0.xml"] = new_xml.encode("utf-8")
    from pyhwpxlib.package_ops import ZipArchive
    new_archive = ZipArchive(infos=archive.infos, files=new_files)
    strip_mode = "precise" if fix_linesegs else False
    fixed_count = write_zip_archive(str(output_path), new_archive, strip_linesegs=strip_mode)

    summary["template"] = str(hwpx_path)
    summary["output"] = str(output_path)
    summary["linesegs_fixed"] = fixed_count
    return summary
