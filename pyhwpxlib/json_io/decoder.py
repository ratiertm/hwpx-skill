"""JSON → HWPX decoder and patcher.

from_json: Creates new HWPX from JSON using HwpxBuilder.
patch: Replaces section text in existing HWPX, preserving everything else.

v0.15.0: extended to dispatch all 16 builder methods (was 3 in v0.14.0).
See ``docs/02-design/features/json-schema-expansion.design.md``.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from .schema import (
    HwpxJsonDocument, Section, Run, Image, Shape,
)

if TYPE_CHECKING:
    from ..builder import HwpxBuilder


def from_json(data: dict, output_path: str) -> str:
    """Create a new HWPX document from JSON structure.

    Uses HwpxBuilder. Supports the full set of 16 add_* methods exposed
    by the builder; see the schema module for recognized RunContent types.

    Order of execution:
      1. Normal pass — paragraphs/runs in their declared order.
      2. Deferred pass — top-level header / footer / page_number applied
         last to avoid the Whale SecPr ordering bug (mirrors HwpxBuilder's
         own deferred list).

    Parameters
    ----------
    data : dict
        JSON dict (HwpxJsonDocument format)
    output_path : str
        Output .hwpx file path

    Returns
    -------
    str
        The output path
    """
    from ..builder import HwpxBuilder

    doc = HwpxJsonDocument.from_dict(data)
    b = HwpxBuilder()

    # Normal pass
    for section in doc.sections:
        for para in section.paragraphs:
            if para.page_break:
                b.add_page_break()
            for run in para.runs:
                _apply_run(b, run, section)

    # Deferred pass (Whale SecPr-bug-safe — same order as HwpxBuilder)
    if doc.header is not None:
        b.add_header(doc.header.text)
    if doc.footer is not None:
        b.add_footer(doc.footer.text)
    if doc.page_number is not None:
        b.add_page_number(doc.page_number.pos)

    return b.save(output_path)


# ── dispatch helpers ───────────────────────────────────────────────


def _apply_run(b: "HwpxBuilder", run: Run, section: Section) -> None:
    """Map a single Run to the matching HwpxBuilder.add_* call.

    Raises
    ------
    ValueError
        If ``run.content.type`` is unknown or the matching nested object is
        missing. Per the v0.14.0 rhwp-aligned policy we do not silently
        skip malformed input.
    """
    c = run.content
    t = c.type

    if t == "text":
        if c.text is None:
            raise ValueError("RunContent.type='text' requires 'text' field")
        b.add_paragraph(c.text)

    elif t == "heading":
        if c.heading is None:
            raise ValueError("RunContent.type='heading' requires 'heading' object")
        b.add_heading(c.heading.text, level=c.heading.level,
                      alignment=c.heading.alignment)

    elif t == "image":
        _apply_image(b, c.image)

    elif t == "table":
        _apply_table(b, c.table, section)

    elif t == "bullet_list":
        bl = c.bullet_list
        if bl is None:
            raise ValueError("RunContent.type='bullet_list' requires 'bullet_list' object")
        b.add_bullet_list(bl.items, bullet_char=bl.bullet_char,
                          indent=bl.indent, native=bl.native)

    elif t == "numbered_list":
        nl = c.numbered_list
        if nl is None:
            raise ValueError("RunContent.type='numbered_list' requires 'numbered_list' object")
        b.add_numbered_list(nl.items, format_string=nl.format_string)

    elif t == "nested_bullet_list":
        nbl = c.nested_bullet_list
        if nbl is None:
            raise ValueError(
                "RunContent.type='nested_bullet_list' requires 'nested_bullet_list' object")
        b.add_nested_bullet_list([(it.depth, it.text) for it in nbl.items])

    elif t == "nested_numbered_list":
        nnl = c.nested_numbered_list
        if nnl is None:
            raise ValueError(
                "RunContent.type='nested_numbered_list' requires 'nested_numbered_list' object")
        b.add_nested_numbered_list([(it.depth, it.text) for it in nnl.items])

    elif t == "footnote":
        fn = c.footnote
        if fn is None:
            raise ValueError("RunContent.type='footnote' requires 'footnote' object")
        b.add_footnote(fn.text, number=fn.number)

    elif t == "equation":
        eq = c.equation
        if eq is None:
            raise ValueError("RunContent.type='equation' requires 'equation' object")
        b.add_equation(eq.script)

    elif t == "highlight":
        hl = c.highlight
        if hl is None:
            raise ValueError("RunContent.type='highlight' requires 'highlight' object")
        b.add_highlight(hl.text, color=hl.color)

    elif t == "shape_line":
        b.add_line()

    elif t == "shape_rect":
        _apply_shape(b, c.shape, "shape_rect")

    elif t == "shape_draw_line":
        _apply_shape(b, c.shape, "shape_draw_line")

    else:
        raise ValueError(f"Unknown RunContent.type: {t!r}")


def _apply_image(b: "HwpxBuilder", img: Optional[Image]) -> None:
    if img is None:
        raise ValueError("RunContent.type='image' requires 'image' object")
    if img.image_path and img.image_url:
        raise ValueError(
            "Image: provide image_path OR image_url, not both")
    if img.image_path:
        b.add_image(img.image_path, width=img.width, height=img.height)
    elif img.image_url:
        b.add_image_from_url(
            img.image_url, filename=img.filename or "",
            width=img.width, height=img.height,
        )
    else:
        raise ValueError("Image: image_path or image_url is required")


def _apply_shape(b: "HwpxBuilder", shape: Optional[Shape], type_: str) -> None:
    if shape is None:
        raise ValueError(f"RunContent.type={type_!r} requires 'shape' object")
    if type_ == "shape_rect":
        b.add_rectangle(width=shape.width, height=shape.height,
                        line_color=shape.line_color, line_width=shape.line_width)
    elif type_ == "shape_draw_line":
        b.add_draw_line(x1=shape.x1, y1=shape.y1, x2=shape.x2, y2=shape.y2,
                        line_color=shape.line_color, line_width=shape.line_width)


def _apply_table(b: "HwpxBuilder", table_idx, section: Section) -> None:
    """Resolve table reference index and call b.add_table.

    Silently no-ops on a missing or non-int reference (preserves prior
    behaviour from v0.14.0 — the table reference is optional metadata).
    """
    if not isinstance(table_idx, int):
        return
    if table_idx < 0 or table_idx >= len(section.tables):
        raise ValueError(
            f"table index {table_idx} out of range "
            f"(section has {len(section.tables)} tables)")
    tbl = section.tables[table_idx]
    table_data = [[cell.text for cell in row.cells] for row in tbl.rows]
    col_widths = tbl.col_widths or None
    row_heights = [row.height for row in tbl.rows] if tbl.rows else None
    b.add_table(table_data, col_widths=col_widths, row_heights=row_heights)


# ── patch (unchanged from 0.14.0) ──────────────────────────────────


def patch(
    hwpx_path: str,
    section_idx: int,
    edits: dict[str, str],
    output_path: str,
) -> str:
    """Patch an existing HWPX by replacing text in a specific section.

    Preserves all non-text content (images, styles, layout) byte-for-byte.

    Parameters
    ----------
    hwpx_path : str
        Original .hwpx file
    section_idx : int
        Which section to patch (0-based)
    edits : dict
        Mapping of {old_text: new_text} for string replacements
    output_path : str
        Output .hwpx file path

    Returns
    -------
    str
        The output path
    """
    import tempfile

    work_dir = Path(tempfile.mkdtemp(prefix="hwpx_patch_"))

    try:
        # Unpack
        subprocess.run(
            [sys.executable, "-m", "pyhwpxlib", "unpack", hwpx_path, "-o", str(work_dir)],
            check=True, capture_output=True,
        )

        # Find and edit section file
        sec_file = work_dir / "Contents" / f"section{section_idx}.xml"
        if not sec_file.exists():
            raise FileNotFoundError(f"Section {section_idx} not found")

        xml = sec_file.read_text(encoding="utf-8")

        # Apply text replacements (raw string replacement, preserving XML structure)
        for old_text, new_text in edits.items():
            xml = xml.replace(old_text, new_text)

        sec_file.write_text(xml, encoding="utf-8")

        # Repack
        if Path(output_path).exists():
            Path(output_path).unlink()
        subprocess.run(
            [sys.executable, "-m", "pyhwpxlib", "pack", str(work_dir), "-o", output_path],
            check=True, capture_output=True,
        )

        return output_path
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
