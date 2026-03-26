"""Table operations — create, list, inspect tables."""

from __future__ import annotations

from hwpx import HwpxDocument


def add_table(doc: HwpxDocument, rows: int, cols: int,
              header: list[str] | None = None,
              data: list[list[str]] | None = None) -> dict:
    """Add a table to the document.

    Args:
        doc: The HWPX document.
        rows: Number of rows.
        cols: Number of columns.
        header: Optional header row values.
        data: Optional 2D list of cell values.

    Returns:
        Summary dict of the created table.
    """
    doc.add_table(rows=rows, cols=cols)
    return {
        "rows": rows,
        "cols": cols,
        "header": header,
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
