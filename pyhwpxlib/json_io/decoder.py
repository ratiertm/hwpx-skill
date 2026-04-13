"""JSON → HWPX decoder and patcher.

from_json: Creates new HWPX from JSON using HwpxBuilder.
patch: Replaces section text in existing HWPX, preserving everything else.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Optional

from .schema import HwpxJsonDocument


def from_json(data: dict, output_path: str) -> str:
    """Create a new HWPX document from JSON structure.

    Uses HwpxBuilder for document generation. Best for new documents.

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

    for section in doc.sections:
        for para in section.paragraphs:
            if para.page_break:
                b.add_page_break()

            for run in para.runs:
                c = run.content
                if c.type == "text" and c.text:
                    b.add_paragraph(c.text)
                elif c.type == "table" and isinstance(c.table, int):
                    # Reference to tables list
                    if c.table < len(section.tables):
                        tbl = section.tables[c.table]
                        table_data = [
                            [cell.text for cell in row.cells]
                            for row in tbl.rows
                        ]
                        col_widths = tbl.col_widths or None
                        row_heights = [row.height for row in tbl.rows] if tbl.rows else None
                        b.add_table(table_data, col_widths=col_widths, row_heights=row_heights)

    return b.save(output_path)


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
