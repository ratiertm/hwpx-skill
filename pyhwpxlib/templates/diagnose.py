"""Diagnostic CLI for auto_schema heuristics.

Run as::

    python -m pyhwpxlib.templates.diagnose <hwpx>
    pyhwpxlib template diagnose <hwpx> [--schema MANUAL.json] [--json]

Shows for each table in the HWPX:
  - dimensions and cell count
  - detected grid sub-region (rows / cols)
  - row-group label found (rs > 1)
  - per-cell field key derivation (label → slug)

Optionally compares the auto-generated schema against a manually authored
``.schema.json`` and reports overlap precision/recall — useful for tracking
how close auto_schema gets to ground truth on real forms.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from pyhwpxlib.templates.auto_schema import (
    GridRegion,
    _extract_cells,
    _find_balanced_tables,
    _find_grid_subregion,
    _find_label_for,
    _find_row_group_label,
    _is_placeholder,
    generate_schema_from_hwpx,
)


def _diagnose_one_table(t_idx: int, tbl_xml: str) -> dict:
    """Build a per-table diagnosis dict (text or JSON)."""
    cells = _extract_cells(tbl_xml)
    if not cells:
        return {"index": t_idx, "empty": True}

    rows = max(c["row"] for c in cells) + 1
    cols = max(c["col"] for c in cells) + 1
    grid = _find_grid_subregion(cells)
    grid_info = (
        {
            "start_row": grid.start,
            "end_row": grid.end,
            "cols": sorted(grid.cols),
            "length": grid.length,
        }
        if grid
        else None
    )

    # Sample row-group label from the first grid cell, if any.
    row_group = None
    if grid:
        first_grid_cell = next(
            (c for c in cells if grid.contains(c["row"], c["col"])
             and (not c["text"] or _is_placeholder(c["text"]))),
            None,
        )
        if first_grid_cell:
            row_group = _find_row_group_label(first_grid_cell, cells)

    # Per-column header detection within grid.
    headers = {}
    if grid:
        sample_row = grid.start
        for col in sorted(grid.cols):
            sample = {"row": sample_row, "col": col, "cs": 1, "rs": 1}
            label = _find_label_for(sample, cells, prefer_header=True)
            if label:
                headers[col] = label

    return {
        "index": t_idx,
        "rows": rows,
        "cols": cols,
        "cell_count": len(cells),
        "grid": grid_info,
        "row_group_label": row_group,
        "column_headers": headers,
    }


def _format_text(diagnoses: list[dict], schema: dict, manual: Optional[dict]) -> str:
    """Render diagnosis as a human-readable text report."""
    lines = []
    lines.append(f"Template: {schema.get('name', '?')}")
    lines.append(f"Source:   {schema.get('source', '?')}")
    lines.append("")

    for diag, tbl in zip(diagnoses, schema.get("tables", [])):
        ti = diag["index"]
        if diag.get("empty"):
            lines.append(f"Table {ti}: (empty)")
            continue
        lines.append(
            f"Table {ti}: {diag['rows']}x{diag['cols']} "
            f"({diag['cell_count']} cells)"
        )
        g = diag["grid"]
        if g:
            lines.append(
                f"  Grid sub-region: rows {g['start_row']}..{g['end_row']}, "
                f"cols {{{', '.join(map(str, g['cols']))}}} "
                f"({g['length']} rows × {len(g['cols'])} cols = "
                f"{g['length'] * len(g['cols'])} cells)"
            )
            if diag["row_group_label"]:
                lines.append(f"  Row group label: {diag['row_group_label']!r}")
            if diag["column_headers"]:
                hdrs = ", ".join(
                    f"{lbl!r}@col={c}" for c, lbl in sorted(diag["column_headers"].items())
                )
                lines.append(f"  Column headers: {hdrs}")
        else:
            lines.append("  Grid sub-region: (none — single-field table)")

        # Field keys
        lines.append(f"  Auto fields ({len(tbl['fields'])}):")
        for f in tbl["fields"][:12]:
            cell = f.get("cell", [None, None])
            label = f.get("label", "")
            in_grid = "grid" if (g and g["start_row"] <= cell[0] <= g["end_row"]
                                  and cell[1] in g["cols"]) else "single"
            lines.append(
                f"    {f['key']:<28} cell={cell} [{in_grid}] label={label!r}"
            )
        if len(tbl["fields"]) > 12:
            lines.append(f"    ... +{len(tbl['fields']) - 12} more")
        lines.append("")

    # Manual comparison
    if manual:
        lines.append("─── Comparison vs manual schema ───")
        auto_keys = {f["key"] for t in schema["tables"] for f in t["fields"]}
        manual_keys = {f["key"] for t in manual.get("tables", []) for f in t["fields"]}
        overlap = auto_keys & manual_keys
        ratio = len(overlap) / len(manual_keys) if manual_keys else 0.0
        lines.append(f"  Auto: {len(auto_keys)} keys")
        lines.append(f"  Manual: {len(manual_keys)} keys")
        lines.append(
            f"  Overlap: {len(overlap)}/{len(manual_keys)} = {ratio:.0%}"
        )

        # Per-table overlap
        for at, mt in zip(schema["tables"], manual.get("tables", [])):
            ak = {f["key"] for f in at["fields"]}
            mk = {f["key"] for f in mt["fields"]}
            o = ak & mk
            r = len(o) / len(mk) if mk else 0.0
            lines.append(
                f"    Table {at['index']}: {len(o)}/{len(mk)} = {r:.0%}  "
                f"(auto={len(ak)}, manual={len(mk)})"
            )

        missing = sorted(manual_keys - auto_keys)
        extra = sorted(auto_keys - manual_keys)
        if missing:
            lines.append(f"  In manual not in auto: {missing[:8]}"
                         f"{'...' if len(missing) > 8 else ''}")
        if extra:
            lines.append(f"  In auto not in manual: {extra[:8]}"
                         f"{'...' if len(extra) > 8 else ''}")

    return "\n".join(lines)


def _format_json(diagnoses: list[dict], schema: dict, manual: Optional[dict]) -> str:
    out = {
        "name": schema.get("name"),
        "source": schema.get("source"),
        "tables": diagnoses,
        "schema": schema,
    }
    if manual:
        auto_keys = {f["key"] for t in schema["tables"] for f in t["fields"]}
        manual_keys = {f["key"] for t in manual.get("tables", []) for f in t["fields"]}
        overlap = auto_keys & manual_keys
        out["comparison"] = {
            "auto_keys_count": len(auto_keys),
            "manual_keys_count": len(manual_keys),
            "overlap_count": len(overlap),
            "overlap_ratio": len(overlap) / len(manual_keys) if manual_keys else 0.0,
            "missing_in_auto": sorted(manual_keys - auto_keys),
            "extra_in_auto": sorted(auto_keys - manual_keys),
        }
    return json.dumps(out, ensure_ascii=False, indent=2)


def diagnose(
    hwpx_path: str | Path, *, manual_schema_path: Optional[str | Path] = None
) -> dict:
    """Programmatic API: returns per-table diagnosis dicts + optional comparison."""
    p = Path(hwpx_path)
    schema = generate_schema_from_hwpx(p, name=p.stem)

    import zipfile
    with zipfile.ZipFile(p) as z:
        section_xml = z.read("Contents/section0.xml").decode("utf-8")

    diagnoses = []
    for ti, (s, e) in enumerate(_find_balanced_tables(section_xml)):
        diagnoses.append(_diagnose_one_table(ti, section_xml[s:e]))

    result = {"schema": schema, "tables": diagnoses}
    if manual_schema_path:
        manual = json.loads(Path(manual_schema_path).read_text())
        auto_keys = {f["key"] for t in schema["tables"] for f in t["fields"]}
        manual_keys = {f["key"] for t in manual.get("tables", []) for f in t["fields"]}
        overlap = auto_keys & manual_keys
        result["comparison"] = {
            "auto_keys_count": len(auto_keys),
            "manual_keys_count": len(manual_keys),
            "overlap_count": len(overlap),
            "overlap_ratio": len(overlap) / len(manual_keys) if manual_keys else 0.0,
            "missing_in_auto": sorted(manual_keys - auto_keys),
            "extra_in_auto": sorted(auto_keys - manual_keys),
        }
    return result


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="pyhwpxlib.templates.diagnose",
        description="Diagnose auto_schema heuristics on a HWPX form.",
    )
    ap.add_argument("hwpx", help="path to .hwpx form")
    ap.add_argument(
        "--schema",
        help="optional path to a manually authored schema.json for overlap comparison",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="emit JSON instead of human-readable text",
    )
    args = ap.parse_args(argv)

    p = Path(args.hwpx)
    if not p.exists():
        print(f"File not found: {p}", file=sys.stderr)
        return 2
    if p.suffix.lower() != ".hwpx":
        print(f"Expected .hwpx (got {p.suffix})", file=sys.stderr)
        return 2

    schema = generate_schema_from_hwpx(p, name=p.stem)
    import zipfile
    with zipfile.ZipFile(p) as z:
        section_xml = z.read("Contents/section0.xml").decode("utf-8")
    diagnoses = [
        _diagnose_one_table(ti, section_xml[s:e])
        for ti, (s, e) in enumerate(_find_balanced_tables(section_xml))
    ]

    manual = None
    if args.schema:
        ms = Path(args.schema)
        if not ms.exists():
            print(f"Schema not found: {ms}", file=sys.stderr)
            return 2
        manual = json.loads(ms.read_text())

    if args.json:
        print(_format_json(diagnoses, schema, manual))
    else:
        print(_format_text(diagnoses, schema, manual))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
