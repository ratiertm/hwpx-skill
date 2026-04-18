"""Table operations — create, list, inspect tables."""

from __future__ import annotations

from hwpx import HwpxDocument


def add_table(doc: HwpxDocument, rows: int, cols: int,
              header: str | list[str] | None = None,
              data: tuple[str, ...] | list[list[str]] | None = None) -> dict:
    """Add a table to the document with optional header and data.

    Args:
        doc: The HWPX document.
        rows: Number of rows.
        cols: Number of columns.
        header: Comma-separated string or list of header values.
        data: Tuple of comma-separated strings or 2D list of cell values.
    """
    tbl = doc.add_table(rows=rows, cols=cols)

    # Parse header
    header_list = None
    if header:
        header_list = [h.strip() for h in header.split(",")] if isinstance(header, str) else header
        for c, val in enumerate(header_list[:cols]):
            tbl.set_cell_text(0, c, val)

    # Parse data rows
    filled_rows = 0
    if data:
        start_row = 1 if header_list else 0
        for r_idx, row in enumerate(data):
            row_vals = [v.strip() for v in row.split(",")] if isinstance(row, str) else row
            for c, val in enumerate(row_vals[:cols]):
                if start_row + r_idx < rows:
                    tbl.set_cell_text(start_row + r_idx, c, val)
            filled_rows += 1

    return {
        "rows": rows,
        "cols": cols,
        "header": header_list,
        "data_rows": filled_rows,
        "status": "added",
    }


def list_tables(doc: HwpxDocument) -> list[dict]:
    """List all tables in the document with basic info."""
    results = []
    for sec_idx, section in enumerate(doc.sections):
        for para_idx, para in enumerate(section.paragraphs):
            para_tables = getattr(para, "tables", [])
            for tbl_idx, tbl in enumerate(para_tables):
                row_count = getattr(tbl, "row_count", len(getattr(tbl, "rows", [])))
                col_count = getattr(tbl, "column_count", 0)
                results.append({
                    "section": sec_idx,
                    "paragraph": para_idx,
                    "table_index": tbl_idx,
                    "rows": row_count,
                    "cols": col_count,
                })
    return results
