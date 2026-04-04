"""High-level convenience API for pyhwpxlib.

Usage::

    from pyhwpxlib.api import create_document, add_paragraph, save

    doc = create_document()
    add_paragraph(doc, "Hello, World!")
    save(doc, "output.hwpx")
"""
from __future__ import annotations

import io as _io
import logging
import pathlib as _pathlib
import re as _re
import random as _random
from typing import List, Optional

logger = logging.getLogger(__name__)

from .hwpx_file import HWPXFile
from .objects.section.paragraph import Para, Run, T


def create_document() -> HWPXFile:
    """Create a new blank HWPX document ready for content."""
    from .tools.blank_file_maker import BlankFileMaker
    return BlankFileMaker.make()


def save(hwpx_file: HWPXFile, filepath: str) -> None:
    """Save an HWPX file to disk as a .hwpx (ZIP) file."""
    from .writer.hwpx_writer import HWPXWriter
    HWPXWriter.to_filepath(hwpx_file, filepath)


def add_table(
    hwpx_file: HWPXFile,
    rows: int,
    cols: int,
    data: list[list[str]] | None = None,
    width: int = 42520,
    merge_info: list[tuple[int, int, int, int]] | None = None,
    cell_colors: dict[tuple[int, int], str] | None = None,
    col_widths: list[int] | None = None,
    row_heights: list[int] | None = None,
    cell_margin: tuple[int, int, int, int] | None = None,
    cell_gradients: dict[tuple[int, int], dict] | None = None,
    section_index: int = 0,
) -> Para:
    """Add a table to the document.

    *col_widths* is a list of column widths in HWPX units. If None, distributed evenly.
    *row_heights* is a list of row heights. If None, defaults to 3600 per row.
    *cell_margin* is (left, right, top, bottom) in HWPX units.
    *cell_gradients* maps ``(row, col)`` to gradient config dicts with keys:
        ``start``, ``end``, ``type`` (default ``"LINEAR"``), ``angle`` (default 0).
    """
    from .writer.shape_writer import build_table_xml
    from .style_manager import ensure_border_fill, ensure_gradient_border_fill

    cell_border_fill_ids: dict[tuple[int, int], str] | None = None
    if cell_colors or cell_gradients:
        cell_border_fill_ids = cell_border_fill_ids or {}

    if cell_colors:
        if cell_border_fill_ids is None:
            cell_border_fill_ids = {}
        for (r, c), color in cell_colors.items():
            bf_id = ensure_border_fill(
                hwpx_file, face_color=color, border_type="SOLID",
            )
            cell_border_fill_ids[(r, c)] = bf_id

    if cell_gradients:
        if cell_border_fill_ids is None:
            cell_border_fill_ids = {}
        for (r, c), grad_cfg in cell_gradients.items():
            bf_id = ensure_gradient_border_fill(
                hwpx_file,
                start_color=grad_cfg.get("start", "#FFFFFF"),
                end_color=grad_cfg.get("end", "#000000"),
                gradient_type=grad_cfg.get("type", "LINEAR"),
                angle=grad_cfg.get("angle", 0),
            )
            cell_border_fill_ids[(r, c)] = bf_id

    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = False
    para.column_break = False
    para.merged = False
    para.raw_xml_content = build_table_xml(
        rows, cols, data, width,
        merge_info=merge_info,
        cell_border_fill_ids=cell_border_fill_ids,
        col_widths=col_widths,
        row_heights=row_heights,
        cell_margin=cell_margin,
    )
    return para


def set_columns(
    hwpx_file: HWPXFile,
    col_count: int = 2,
    same_gap: int = 1200,
    separator_type: Optional[str] = "SOLID",
    col_type: str = "NEWSPAPER",
    layout: str = "LEFT",
    section_index: int = 0,
) -> Para:
    """Set column layout for the current position in the document.

    Inserts a column-property control (``colPr``) that changes the
    column layout from this point forward.

    Parameters
    ----------
    col_count : int
        Number of columns. Use 1 to reset to single-column layout.
    same_gap : int
        Gap between columns in HWPX units (default 1200).
    separator_type : str or None
        Column separator line type (e.g. ``"SOLID"``). None = no separator.
    col_type : str
        Column type (default ``"NEWSPAPER"``).
    layout : str
        Layout direction (default ``"LEFT"``).

    Returns
    -------
    Para
        The paragraph containing the column control.
    """
    from .writer.shape_writer import build_columns_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_columns_xml(
        col_count=col_count,
        col_type=col_type,
        layout=layout,
        same_gap=same_gap,
        separator_type=separator_type,
    )
    return para


def set_cell_gradient(
    hwpx_file: HWPXFile,
    table_para_index: int,
    row: int,
    col: int,
    *,
    start_color: str = "#FFFFFF",
    end_color: str = "#000000",
    gradient_type: str = "LINEAR",
    angle: int = 0,
    section_index: int = 0,
) -> None:
    """Apply a gradient fill to a specific cell in an existing table.

    This modifies the table paragraph's raw XML to update the
    ``borderFillIDRef`` of the target cell.

    Parameters
    ----------
    table_para_index : int
        Index of the table paragraph in the section.
    row, col : int
        Cell coordinates (0-based).
    start_color, end_color : str
        Gradient stop colors.
    gradient_type : str
        Gradient type (default ``"LINEAR"``).
    angle : int
        Gradient angle in degrees.
    """
    from .style_manager import ensure_gradient_border_fill

    bf_id = ensure_gradient_border_fill(
        hwpx_file,
        start_color=start_color,
        end_color=end_color,
        gradient_type=gradient_type,
        angle=angle,
    )

    section = hwpx_file.section_xml_file_list.get(section_index)
    paras = section.paras()

    if table_para_index < 0 or table_para_index >= len(paras):
        raise IndexError(f"table_para_index {table_para_index} out of range.")

    para = paras[table_para_index]
    if para.raw_xml_content is None:
        raise ValueError("Paragraph has no raw XML content (not a table).")

    # Find the target cell by counting <hp:tc> and <hp:cellAddr> elements
    xml = para.raw_xml_content
    import re as _re_local

    # Find all tc elements and match by cellAddr
    tc_pattern = _re_local.compile(
        r'(<hp:tc\b[^>]*borderFillIDRef=")(\d+)(".*?'
        r'<hp:cellAddr\s+colAddr="(\d+)"\s+rowAddr="(\d+)")',
        _re_local.DOTALL,
    )

    def _replace_bf(m):
        tc_col = int(m.group(4))
        tc_row = int(m.group(5))
        if tc_row == row and tc_col == col:
            return m.group(1) + bf_id + m.group(3)
        return m.group(0)

    new_xml = tc_pattern.sub(_replace_bf, xml)
    para.raw_xml_content = new_xml


def add_rectangle(
    hwpx_file: HWPXFile,
    width: int = 14400,
    height: int = 7200,
    line_color: str = "#000000",
    line_width: int = 283,
    fill_color: str | None = None,
    text: str | None = None,
    caption: str | None = None,
    shadow_type: str = "NONE",
    section_index: int = 0,
) -> Para:
    """Add a rectangle shape to the document.

    Parameters
    ----------
    text : str or None
        Text to display inside the rectangle (drawText).
    caption : str or None
        Caption text below the shape.
    shadow_type : str
        Shadow style: ``"NONE"``, ``"DROP"``, ``"OFFSET"``, etc.
    """
    from .writer.shape_writer import build_rectangle_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = False
    para.column_break = False
    para.merged = False
    para.raw_xml_content = build_rectangle_xml(
        width, height, line_color, line_width, fill_color,
        text=text, caption=caption, shadow_type=shadow_type,
    )
    return para


def add_ellipse(
    hwpx_file: HWPXFile,
    width: int = 10000,
    height: int = 8000,
    line_color: str = "#000000",
    line_width: int = 283,
    fill_color: str | None = None,
    text: str | None = None,
    caption: str | None = None,
    shadow_type: str = "NONE",
    section_index: int = 0,
) -> Para:
    """Add an ellipse shape to the document.

    Parameters
    ----------
    text : str or None
        Text to display inside the ellipse (drawText).
    caption : str or None
        Caption text below the shape.
    shadow_type : str
        Shadow style: ``"NONE"``, ``"DROP"``, ``"OFFSET"``, etc.
    """
    from .writer.shape_writer import build_ellipse_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = False
    para.column_break = False
    para.merged = False
    para.raw_xml_content = build_ellipse_xml(
        width, height, line_color, line_width, fill_color,
        text=text, caption=caption, shadow_type=shadow_type,
    )
    return para


def add_line(
    hwpx_file: HWPXFile,
    x1: int = 0,
    y1: int = 0,
    x2: int = 20000,
    y2: int = 0,
    line_color: str = "#000000",
    line_width: int = 283,
    head_style: str = "NORMAL",
    tail_style: str = "NORMAL",
    section_index: int = 0,
) -> Para:
    """Add a line shape to the document.

    Parameters
    ----------
    head_style : str
        Arrow head style: ``"NORMAL"``, ``"ARROW"``, ``"SPEAR"``,
        ``"CONCAVE_ARROW"``, ``"EMPTY_DIAMOND"``, ``"EMPTY_CIRCLE"``,
        ``"EMPTY_BOX"``.
    tail_style : str
        Arrow tail style (same values as head_style).
    """
    from .writer.shape_writer import build_line_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = False
    para.column_break = False
    para.merged = False
    para.raw_xml_content = build_line_xml(
        x1, y1, x2, y2, line_color, line_width,
        head_style=head_style, tail_style=tail_style,
    )
    return para


def add_arc(
    hwpx_file: HWPXFile,
    center_x: int,
    center_y: int,
    ax1_x: int,
    ax1_y: int,
    ax2_x: int,
    ax2_y: int,
    arc_type: str = "NORMAL",
    line_color: str = "#000000",
    line_width: int = 283,
    section_index: int = 0,
) -> Para:
    """Add an arc (ellipse with arc properties) to the document.

    Parameters
    ----------
    arc_type : str
        Arc type: ``"NORMAL"``, ``"PIE"``, ``"CHORD"``.
    """
    from .writer.shape_writer import build_arc_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = False
    para.column_break = False
    para.merged = False
    para.raw_xml_content = build_arc_xml(
        center_x, center_y, ax1_x, ax1_y, ax2_x, ax2_y,
        arc_type=arc_type, line_color=line_color, line_width=line_width,
    )
    return para


def add_polygon(
    hwpx_file: HWPXFile,
    points: list,
    line_color: str = "#000000",
    line_width: int = 283,
    fill_color: str | None = None,
    section_index: int = 0,
) -> Para:
    """Add a polygon shape to the document.

    Parameters
    ----------
    points : list of (x, y) tuples
        Polygon vertex coordinates in HWPX units.
    """
    from .writer.shape_writer import build_polygon_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = False
    para.column_break = False
    para.merged = False
    para.raw_xml_content = build_polygon_xml(
        points, line_color=line_color, line_width=line_width,
        fill_color=fill_color,
    )
    return para


def add_curve(
    hwpx_file: HWPXFile,
    segments: list,
    line_color: str = "#000000",
    line_width: int = 283,
    section_index: int = 0,
) -> Para:
    """Add a curve (bezier) shape to the document.

    Parameters
    ----------
    segments : list of dicts
        Each dict: ``{"type": "LINE"|"CURVE", "x1": int, "y1": int, "x2": int, "y2": int}``.
    """
    from .writer.shape_writer import build_curve_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = False
    para.column_break = False
    para.merged = False
    para.raw_xml_content = build_curve_xml(
        segments, line_color=line_color, line_width=line_width,
    )
    return para


def add_connect_line(
    hwpx_file: HWPXFile,
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    line_color: str = "#000000",
    line_width: int = 283,
    section_index: int = 0,
) -> Para:
    """Add a connect line to the document."""
    from .writer.shape_writer import build_connect_line_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = False
    para.column_break = False
    para.merged = False
    para.raw_xml_content = build_connect_line_xml(
        start_x, start_y, end_x, end_y,
        line_color=line_color, line_width=line_width,
    )
    return para


def add_paragraph(
    hwpx_file: HWPXFile,
    text: str,
    section_index: int = 0,
    style_id_ref: str = "0",
    para_pr_id_ref: str = "0",
    char_pr_id_ref: str = "0",
) -> Para:
    """Add a paragraph with text to the specified section.

    The blank first paragraph from BlankFileMaker is preserved as-is
    (it contains SecPr page setup). New text paragraphs are appended after it,
    matching the structure produced by python-hwpx / 한컴 오피스.
    """
    section = hwpx_file.section_xml_file_list.get(section_index)

    para = section.add_new_para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = para_pr_id_ref
    para.style_id_ref = style_id_ref
    para.page_break = False
    para.column_break = False
    para.merged = False

    run = para.add_new_run()
    run.char_pr_id_ref = char_pr_id_ref

    t = run.add_new_t()
    t.add_text(_sanitize_text(text))

    return para


_ILLEGAL_XML_CHARS = _re.compile(
    r"[\x00-\x08\x0b\x0c\x0d\x0e-\x1f\ufffe\uffff]"
)


def _sanitize_text(value: str) -> str:
    """Remove control characters that are invalid in XML text nodes."""
    return _ILLEGAL_XML_CHARS.sub("", value)


def _new_raw_para(hwpx_file: HWPXFile, section_index: int = 0) -> Para:
    """Create and return a new blank paragraph attached to the section."""
    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = False
    para.column_break = False
    para.merged = False
    return para


# ======================================================================
# Bullet list
# ======================================================================

def add_bullet_list(
    hwpx_file: HWPXFile,
    items: List[str],
    bullet_char: str = "\u25cf",
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> List[Para]:
    """Add a bullet list to the document using native HWPX bullet definitions.

    Each item becomes a separate paragraph linked to a bullet definition
    in the header.  The bullet character is rendered automatically by
    the word processor -- no text prefix is inserted.

    Returns the list of created :class:`Para` objects.
    """
    from .style_manager import ensure_bullet, ensure_heading_para_style

    bullet_id = ensure_bullet(hwpx_file, char=bullet_char)
    para_pr_id = ensure_heading_para_style(
        hwpx_file, heading_type="BULLET", heading_id_ref=bullet_id,
    )

    paras: list[Para] = []
    for item in items:
        para = add_paragraph(
            hwpx_file, _sanitize_text(item),
            section_index=section_index,
            para_pr_id_ref=para_pr_id,
            char_pr_id_ref=char_pr_id_ref,
        )
        paras.append(para)
    return paras


# ======================================================================
# Numbered list
# ======================================================================

def add_numbered_list(
    hwpx_file: HWPXFile,
    items: List[str],
    format_string: str = "^1.",
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> List[Para]:
    """Add a numbered list to the document using native HWPX numbering.

    Each item becomes a separate paragraph linked to a numbering definition
    in the header.  The number is rendered automatically by the word
    processor -- no text prefix is inserted.

    *format_string* is the HWPX paraHead text pattern (e.g. ``"^1."``
    for ``"1."``, ``"^1)"`` for ``"1)"``).

    Returns the list of created :class:`Para` objects.
    """
    from .style_manager import ensure_numbering, ensure_heading_para_style

    num_id = ensure_numbering(hwpx_file, format_string=format_string, force_new=True)
    para_pr_id = ensure_heading_para_style(
        hwpx_file, heading_type="NUMBER", heading_id_ref=num_id,
    )

    paras: list[Para] = []
    for item in items:
        para = add_paragraph(
            hwpx_file, _sanitize_text(item),
            section_index=section_index,
            para_pr_id_ref=para_pr_id,
            char_pr_id_ref=char_pr_id_ref,
        )
        paras.append(para)
    return paras


# ======================================================================
# Hyperlink
# ======================================================================

def add_hyperlink(
    hwpx_file: HWPXFile,
    text: str,
    url: str,
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> Para:
    """Add a paragraph containing a hyperlink.

    The hyperlink uses ``fieldBegin`` / ``fieldEnd`` control structure
    matching the Hancom Office OWPML output.
    """
    from .writer.shape_writer import build_hyperlink_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_hyperlink_xml(
        _sanitize_text(text), url, char_pr_id_ref,
    )
    return para


# ======================================================================
# Equation
# ======================================================================

def add_equation(
    hwpx_file: HWPXFile,
    script: str,
    width: int = 3750,
    height: int = 3375,
    section_index: int = 0,
) -> Para:
    """Add a paragraph containing an equation.

    *script* is the Hancom equation syntax (e.g. ``"x^2 + y^2 = r^2"``).
    """
    from .writer.shape_writer import build_equation_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_equation_xml(
        _sanitize_text(script), width, height,
    )
    return para


# ======================================================================
# Image
# ======================================================================

# Format → MIME type mapping (matches ratiertm-hwpx)
_FORMAT_TO_MEDIA_TYPE = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "tif": "image/tiff",
    "tiff": "image/tiff",
    "svg": "image/svg+xml",
}


def add_image(
    hwpx_file: HWPXFile,
    image_path: str,
    width: Optional[int] = None,
    height: Optional[int] = None,
    section_index: int = 0,
) -> Para:
    """Add an inline image to the document.

    *image_path* is the path to an image file on disk.
    *width* and *height* are optional display dimensions in hwpunit
    (1 hwpunit ~ 0.01mm).  If omitted, the image's pixel dimensions
    are converted at 28.35 hwpunit per pixel (~72 dpi).

    The image bytes are stored in ``hwpx_file._binary_attachments`` and
    a manifest entry is registered so the HWPX writer can inject them
    into the output ZIP.
    """
    from .writer.shape_writer import build_image_xml

    path = _pathlib.Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    img_data = path.read_bytes()
    fmt = path.suffix.lstrip(".").lower() or "png"
    media_type = _FORMAT_TO_MEDIA_TYPE.get(fmt, f"image/{fmt}")

    # Generate a unique item id
    if not hasattr(hwpx_file, "_binary_attachments"):
        hwpx_file._binary_attachments = {}  # type: ignore[attr-defined]
    if not hasattr(hwpx_file, "_image_counter"):
        hwpx_file._image_counter = 0  # type: ignore[attr-defined]

    hwpx_file._image_counter += 1  # type: ignore[attr-defined]
    item_id = f"image{hwpx_file._image_counter}"  # type: ignore[attr-defined]

    bin_data_name = f"{item_id}.{fmt}"
    bin_data_path = f"BinData/{bin_data_name}"

    # Store binary data for the writer
    hwpx_file._binary_attachments[bin_data_path] = img_data  # type: ignore[attr-defined]

    # Register manifest entry in content.hpf
    _register_manifest_item(hwpx_file, item_id, bin_data_path, media_type)

    # Detect original image pixel dimensions and convert to hwpunit
    org_width, org_height = 42520, 31890  # sensible defaults (~150x112 mm)
    try:
        from PIL import Image as _PILImage
        pil_img = _PILImage.open(_io.BytesIO(img_data))
        pw, ph = pil_img.size
        org_width = int(pw * 28.35)
        org_height = int(ph * 28.35)
    except ImportError:
        logger.debug("Pillow not installed; using default image dimensions")
    except Exception as e:
        logger.warning("Failed to read image dimensions via PIL: %s", e)

    disp_width = width if width is not None else org_width
    disp_height = height if height is not None else org_height

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_image_xml(
        item_id, disp_width, disp_height, org_width, org_height,
    )
    return para


def _register_manifest_item(
    hwpx_file: HWPXFile,
    item_id: str,
    href: str,
    media_type: str,
) -> None:
    """Register a new item in the content.hpf manifest."""
    manifest = hwpx_file.content_hpf_file.manifest
    if manifest is None:
        manifest = hwpx_file.content_hpf_file.create_manifest()

    item = manifest.add_new()
    item.id = item_id
    item.href = href
    item.media_type = media_type
    item.is_embedded = "1"


# ======================================================================
# Styled paragraph
# ======================================================================


def add_styled_paragraph(
    hwpx_file: HWPXFile,
    text: str,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    font_size: Optional[int] = None,
    text_color: Optional[str] = None,
    font_name: Optional[str] = None,
    char_pr_id_ref: Optional[str] = None,
    section_index: int = 0,
) -> Para:
    """Add a styled paragraph to the document.

    Style options:
    - *bold*, *italic*, *underline*: text decoration flags
    - *font_size*: font size in pt (e.g. 12, 16, 20)
    - *text_color*: hex color string (e.g. "#FF0000")
    - *font_name*: font face name (e.g. "D2Coding"); auto-registered
    - *char_pr_id_ref*: directly specify a charPr ID from the header.
      When provided, this overrides bold/italic/font_size/text_color.

    A matching charPr entry is dynamically created in the header if one
    does not already exist.
    """
    if char_pr_id_ref is None:
        from .style_manager import ensure_char_style, font_size_to_height
        char_pr_id_ref = ensure_char_style(
            hwpx_file,
            bold=bold,
            italic=italic,
            underline=underline,
            height=font_size_to_height(font_size),
            text_color=text_color,
            font_name=font_name,
        )

    return add_paragraph(
        hwpx_file,
        text,
        section_index=section_index,
        char_pr_id_ref=char_pr_id_ref,
    )


# ======================================================================
# Header / Footer
# ======================================================================

def add_header(
    hwpx_file: HWPXFile,
    text: str,
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> Para:
    """Add a header to the document section.

    The header is placed in its own paragraph inserted BEFORE the first
    paragraph (the SecPr paragraph), matching the Hancom Office structure.
    The header text appears at the top of every page in the section.
    """
    from .writer.shape_writer import build_header_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    para = Para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = False
    para.column_break = False
    para.merged = False
    para.raw_xml_content = build_header_xml(
        _sanitize_text(text), char_pr_id_ref,
    )
    # Insert before the last paragraph (which contains SecPr)
    n = section.count_of_para()
    insert_pos = max(0, n - 1)
    section.insert_para(para, insert_pos)
    return para


def add_footer(
    hwpx_file: HWPXFile,
    text: str,
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> Para:
    """Add a footer to the document section.

    The footer is placed in its own paragraph inserted BEFORE the last
    paragraph (the SecPr paragraph), matching the Hancom Office structure.
    The footer text appears at the bottom of every page in the section.
    """
    from .writer.shape_writer import build_footer_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    para = Para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = False
    para.column_break = False
    para.merged = False
    para.raw_xml_content = build_footer_xml(
        _sanitize_text(text), char_pr_id_ref,
    )
    # Insert before the last paragraph (which contains SecPr)
    n = section.count_of_para()
    insert_pos = max(0, n - 1)
    section.insert_para(para, insert_pos)
    return para


# ======================================================================
# Page number
# ======================================================================

def add_page_number(
    hwpx_file: HWPXFile,
    pos: str = "BOTTOM_CENTER",
    format_type: str = "DIGIT",
    side_char: str = "-",
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> Para:
    """Add a page number to the document.

    *pos* controls placement: ``BOTTOM_CENTER``, ``BOTTOM_LEFT``,
    ``BOTTOM_RIGHT``, ``TOP_CENTER``, ``TOP_LEFT``, ``TOP_RIGHT``.

    *format_type* controls numbering style: ``DIGIT``, ``CIRCLE``,
    ``ROMAN_CAPITAL``, ``ROMAN_SMALL``, ``LATIN_CAPITAL``, ``LATIN_SMALL``.
    """
    from .writer.shape_writer import build_page_number_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_page_number_xml(
        pos, format_type, side_char, char_pr_id_ref,
    )
    return para


# ======================================================================
# Footnote
# ======================================================================

def add_footnote(
    hwpx_file: HWPXFile,
    text: str,
    number: int = 1,
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> Para:
    """Add a footnote to the document.

    The footnote ctrl is appended to the LAST content paragraph (the
    anchor paragraph), matching the Hancom Office structure where the
    footnote reference appears inline within the paragraph text.

    *text* is the footnote content that appears at the bottom of the page.
    *number* is the footnote sequence number (1-based).
    """
    from .writer.shape_writer import build_footnote_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    paras = section.paras()

    # Find the last content paragraph (skip the SecPr paragraph at index 0)
    anchor_para = None
    for p in reversed(paras):
        # The first paragraph (index 0) is the SecPr paragraph -- skip it
        # when looking for an anchor; any paragraph with runs or raw_xml is fine
        if p.count_of_run() > 0 or (p.raw_xml_content and '<hp:header' not in p.raw_xml_content and '<hp:footer' not in p.raw_xml_content):
            anchor_para = p
            break

    if anchor_para is None or anchor_para.raw_xml_content is None:
        # Fallback: create a new paragraph
        anchor_para = _new_raw_para(hwpx_file, section_index)
        anchor_para.raw_xml_content = ""

    # Append the footnote run XML to the anchor paragraph's raw content
    footnote_xml = build_footnote_xml(
        _sanitize_text(text), number, char_pr_id_ref,
    )
    if anchor_para.raw_xml_content:
        anchor_para.raw_xml_content += footnote_xml
    else:
        anchor_para.raw_xml_content = footnote_xml
    return anchor_para


# ======================================================================
# Bookmark
# ======================================================================

def add_bookmark(
    hwpx_file: HWPXFile,
    name: str,
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> Para:
    """Add a bookmark to the document.

    *name* is the bookmark identifier that can be referenced by hyperlinks.
    """
    from .writer.shape_writer import build_bookmark_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_bookmark_xml(
        _sanitize_text(name), char_pr_id_ref,
    )
    return para


# ======================================================================
# Heading
# ======================================================================

_HEADING_STYLES: dict[int, tuple[int, bool]] = {
    1: (2400, True),
    2: (1800, True),
    3: (1400, True),
    4: (1200, True),
}


def add_heading(
    hwpx_file: HWPXFile,
    text: str,
    level: int = 1,
    section_index: int = 0,
) -> Para:
    """Add a heading paragraph to the document.

    Headings are regular paragraphs with larger, bold charPr:
    - level 1: 24pt bold
    - level 2: 18pt bold
    - level 3: 14pt bold
    - level 4: 12pt bold
    """
    from .style_manager import ensure_char_style

    height, bold = _HEADING_STYLES.get(level, (1200, True))
    char_pr_id = ensure_char_style(hwpx_file, bold=bold, height=height)
    return add_paragraph(
        hwpx_file, text,
        section_index=section_index,
        char_pr_id_ref=char_pr_id,
    )


# ======================================================================
# Nested bullet list
# ======================================================================

def add_nested_bullet_list(
    hwpx_file: HWPXFile,
    items: list[tuple[int, str]],
    bullet_chars: list[str] | None = None,
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> List[Para]:
    """Add a nested bullet list using native HWPX bullet definitions.

    *items* is a list of ``(level, text)`` tuples where *level* starts at 0.
    Each level uses a separate bullet definition with appropriate left margin.

    *bullet_chars* optionally specifies per-level bullet characters.
    Defaults to ``["\u25cf", "\u25cb", "\u25aa"]`` (filled circle, empty circle, small square).

    Returns the list of created :class:`Para` objects.
    """
    from .style_manager import ensure_bullet, ensure_heading_para_style

    if bullet_chars is None:
        bullet_chars = ["\u25cf", "\u25cb", "\u25aa"]

    # Cache per-level paraPr ids
    _level_cache: dict[int, str] = {}

    paras: list[Para] = []
    for level, text in items:
        if level not in _level_cache:
            bullet_char = bullet_chars[level % len(bullet_chars)]
            bullet_id = ensure_bullet(hwpx_file, char=bullet_char)
            margin_left = level * 1200
            para_pr_id = ensure_heading_para_style(
                hwpx_file,
                heading_type="BULLET",
                heading_id_ref=bullet_id,
                level=level,
                margin_left=margin_left,
            )
            _level_cache[level] = para_pr_id

        para = add_paragraph(
            hwpx_file, _sanitize_text(text),
            section_index=section_index,
            para_pr_id_ref=_level_cache[level],
            char_pr_id_ref=char_pr_id_ref,
        )
        paras.append(para)
    return paras


# ======================================================================
# Nested numbered list
# ======================================================================

def add_nested_numbered_list(
    hwpx_file: HWPXFile,
    items: list[tuple[int, str]],
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> List[Para]:
    """Add a nested numbered list using a single HWPX numbering with multi-level paraHeads.

    *items* is a list of ``(level, text)`` tuples where *level* starts at 0.
    A single numbering definition is created with one paraHead per level.
    Each paragraph references the same numbering but with a different heading
    level, so 한컴 manages hierarchical counters automatically.

    Returns the list of created :class:`Para` objects.
    """
    from .style_manager import ensure_heading_para_style
    from .objects.header.references.numbering import Numbering, ParaHead
    from .objects.header.enum_types import HorizontalAlign1, NumberType1, ValueUnit1

    # Determine max level used
    max_level = max(lv for lv, _ in items)

    # Create ONE numbering with paraHeads for each level (1-based)
    ref_list = hwpx_file.header_xml_file.refList
    if ref_list.numberings is None:
        ref_list.create_numberings()
    numberings = ref_list.numberings

    # Get next ID
    existing_ids = set()
    for n in numberings.items():
        try:
            existing_ids.add(int(n.id))
        except (ValueError, TypeError):
            pass
    new_id = str(max(existing_ids, default=0) + 1)

    new_n = Numbering()
    new_n.id = new_id
    new_n.start = 1

    # Format strings per level: "^1.", "^2.", "^3)", etc.
    level_formats = ["^1.", "^2.", "^3)", "^4)", "(^5)", "(^6)", "^7"]
    level_num_formats = [
        NumberType1.DIGIT,
        NumberType1.HANGUL_SYLLABLE,
        NumberType1.DIGIT,
        NumberType1.HANGUL_SYLLABLE,
        NumberType1.DIGIT,
        NumberType1.HANGUL_SYLLABLE,
        NumberType1.CIRCLED_DIGIT,
    ]

    for lv in range(max_level + 1):
        ph = new_n.add_new_para_head()
        ph.start = 1
        ph.level = lv + 1  # 1-based
        ph.align = HorizontalAlign1.LEFT
        ph.useInstWidth = True
        ph.autoIndent = True
        ph.widthAdjust = 0
        ph.textOffsetType = ValueUnit1.PERCENT
        ph.textOffset = 50
        ph.numFormat = level_num_formats[lv % len(level_num_formats)]
        ph.charPrIDRef = "4294967295"
        ph.checkable = False
        ph.text = level_formats[lv % len(level_formats)]

    numberings.add(new_n)

    # Create paraPr for each level, all referencing the SAME numbering id
    _level_para_pr: dict[int, str] = {}
    for lv in range(max_level + 1):
        margin_left = lv * 1200
        para_pr_id = ensure_heading_para_style(
            hwpx_file,
            heading_type="NUMBER",
            heading_id_ref=new_id,
            level=lv,
            margin_left=margin_left,
        )
        _level_para_pr[lv] = para_pr_id

    paras: list[Para] = []
    for level, text in items:
        para = add_paragraph(
            hwpx_file, _sanitize_text(text),
            section_index=section_index,
            para_pr_id_ref=_level_para_pr[level],
            char_pr_id_ref=char_pr_id_ref,
        )
        paras.append(para)
    return paras


# ======================================================================
# Code block
# ======================================================================

def add_code_block(
    hwpx_file: HWPXFile,
    code: str,
    language: Optional[str] = None,
    font: str = "D2Coding",
    bg_color: str = "#F5F5F5",
    char_pr_id_ref: Optional[str] = None,
    section_index: int = 0,
) -> List[Para]:
    """Add a code block to the document with monospace font and background.

    Each line of *code* becomes a separate paragraph with a monospace
    charPr and a shaded paraPr (paragraph background).

    *language* is an optional language label (currently unused, reserved
    for future syntax highlighting).
    *font* is the monospace font face name (default ``"D2Coding"``).
    *bg_color* is the background color (default ``"#F5F5F5"``).
    *char_pr_id_ref* overrides the dynamically created charPr if provided.

    Returns the list of created :class:`Para` objects (one per line).
    """
    from .style_manager import ensure_char_style, ensure_border_fill, ensure_para_style

    # 1. Create borderFill with background color
    bf_id = ensure_border_fill(hwpx_file, face_color=bg_color)

    # 2. Create charPr with monospace font
    if char_pr_id_ref is None:
        char_pr_id_ref = ensure_char_style(hwpx_file, font_name=font, height=900)

    # 3. Create paraPr referencing the borderFill
    para_id = ensure_para_style(hwpx_file, border_fill_id_ref=bf_id)

    # 4. Add each line as a paragraph
    lines = code.split('\n')
    paras: list[Para] = []
    for line in lines:
        para = add_paragraph(
            hwpx_file,
            line or ' ',
            para_pr_id_ref=para_id,
            char_pr_id_ref=char_pr_id_ref,
            section_index=section_index,
        )
        paras.append(para)
    return paras


# ======================================================================
# Markdown conversion
# ======================================================================

def add_textart(
    hwpx_file: HWPXFile,
    text: str,
    width: int = 14000,
    height: int = 7000,
    font_name: str = "\ud568\ucd08\ub86c\ubc14\ud0d5",
    text_shape: str = "WAVE1",
    fill_color: str = "#0000FF",
    section_index: int = 0,
) -> Para:
    """Add a TextArt shape to the document.

    Parameters
    ----------
    text : str
        Text content to display as TextArt.
    text_shape : str
        Shape of the text path: ``"WAVE1"``, ``"WAVE2"``,
        ``"THIN_CURVE_DOWN1"``, ``"THIN_CURVE_UP1"``, ``"TRIANGLE_UP"``, etc.
    fill_color : str
        Fill color for the text art (hex, e.g. ``"#0000FF"``).
    """
    from .writer.shape_writer import build_textart_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_textart_xml(
        _sanitize_text(text), width, height,
        font_name=font_name, text_shape=text_shape,
        fill_color=fill_color,
    )
    return para


def add_container(
    hwpx_file: HWPXFile,
    children_xml: list[str],
    width: int = 20000,
    height: int = 20000,
    section_index: int = 0,
) -> Para:
    """Add a group container wrapping multiple child shapes.

    Parameters
    ----------
    children_xml : list of str
        Pre-built shape XML strings.  Each element should be the
        **inner** shape XML (e.g. ``<hp:rect ...>...</hp:rect>``)
        without the outer ``<hp:run>`` wrapper.
    width, height : int
        Container bounding box dimensions in HWPX units.
    """
    from .writer.shape_writer import build_container_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_container_xml(
        children_xml, width, height,
    )
    return para


def add_rectangle_with_image_fill(
    hwpx_file: HWPXFile,
    image_path: str,
    width: int = 14400,
    height: int = 7200,
    mode: str = "STRETCH",
    line_color: str = "#000000",
    line_width: int = 283,
    text: str | None = None,
    section_index: int = 0,
) -> Para:
    """Add a rectangle shape with an image as background fill.

    Parameters
    ----------
    image_path : str
        Path to the image file on disk.
    mode : str
        Image fill mode: ``"TILE"``, ``"CENTER"``, ``"FIT"``, ``"STRETCH"``.
    text : str or None
        Optional text to display on top of the image fill.
    """
    from .writer.shape_writer import build_rectangle_with_image_fill_xml

    path = _pathlib.Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    img_data = path.read_bytes()
    fmt = path.suffix.lstrip(".").lower() or "png"
    media_type = _FORMAT_TO_MEDIA_TYPE.get(fmt, f"image/{fmt}")

    # Generate a unique item id
    if not hasattr(hwpx_file, "_binary_attachments"):
        hwpx_file._binary_attachments = {}  # type: ignore[attr-defined]
    if not hasattr(hwpx_file, "_image_counter"):
        hwpx_file._image_counter = 0  # type: ignore[attr-defined]

    hwpx_file._image_counter += 1  # type: ignore[attr-defined]
    item_id = f"image{hwpx_file._image_counter}"  # type: ignore[attr-defined]

    bin_data_name = f"{item_id}.{fmt}"
    bin_data_path = f"BinData/{bin_data_name}"

    # Store binary data for the writer
    hwpx_file._binary_attachments[bin_data_path] = img_data  # type: ignore[attr-defined]

    # Register manifest entry in content.hpf
    _register_manifest_item(hwpx_file, item_id, bin_data_path, media_type)

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_rectangle_with_image_fill_xml(
        item_id, width, height, mode=mode,
        line_color=line_color, line_width=line_width,
        text=text,
    )
    return para


# ======================================================================
# Form Controls  (Phase 4)
# ======================================================================

def add_checkbox(
    hwpx_file: HWPXFile,
    caption: str = "체크박스",
    checked: bool = False,
    name: str = "CheckBox1",
    width: int = 9921,
    height: int = 1984,
    section_index: int = 0,
) -> Para:
    """Add a checkbox form control to the document."""
    from .writer.shape_writer import build_checkbox_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_checkbox_xml(
        caption=caption, name=name, checked=checked,
        width=width, height=height,
    )
    return para


def add_radio_button(
    hwpx_file: HWPXFile,
    caption: str = "라디오",
    group: str = "",
    checked: bool = False,
    name: str = "Radio1",
    width: int = 8504,
    height: int = 1984,
    section_index: int = 0,
) -> Para:
    """Add a radio button form control to the document.

    Use *group* to link multiple radio buttons so only one can be selected.
    """
    from .writer.shape_writer import build_radio_button_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_radio_button_xml(
        caption=caption, name=name, group=group, checked=checked,
        width=width, height=height,
    )
    return para


def add_button(
    hwpx_file: HWPXFile,
    caption: str = "버튼",
    name: str = "Button1",
    width: int = 7087,
    height: int = 1984,
    section_index: int = 0,
) -> Para:
    """Add a push-button form control to the document."""
    from .writer.shape_writer import build_button_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_button_xml(
        caption=caption, name=name,
        width=width, height=height,
    )
    return para


def add_combobox(
    hwpx_file: HWPXFile,
    items: list[tuple[str, str]] | None = None,
    name: str = "ComboBox1",
    width: int = 9921,
    height: int = 1984,
    section_index: int = 0,
) -> Para:
    """Add a combo box form control to the document.

    *items* is a list of ``(display_text, value)`` tuples.
    """
    from .writer.shape_writer import build_combobox_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_combobox_xml(
        name=name, items=items,
        width=width, height=height,
    )
    return para


def add_listbox(
    hwpx_file: HWPXFile,
    items: list[tuple[str, str]] | None = None,
    name: str = "ListBox1",
    width: int = 9921,
    height: int = 3968,
    section_index: int = 0,
) -> Para:
    """Add a list box form control to the document.

    *items* is a list of ``(display_text, value)`` tuples.
    """
    from .writer.shape_writer import build_listbox_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_listbox_xml(
        name=name, items=items,
        width=width, height=height,
    )
    return para


def add_edit_field(
    hwpx_file: HWPXFile,
    text: str = "",
    name: str = "Edit1",
    multi_line: bool = False,
    width: int = 7087,
    height: int = 1984,
    section_index: int = 0,
) -> Para:
    """Add an edit (text input) form control to the document."""
    from .writer.shape_writer import build_edit_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_edit_xml(
        name=name, text=text, multi_line=multi_line,
        width=width, height=height,
    )
    return para


def add_scrollbar(
    hwpx_file: HWPXFile,
    name: str = "ScrollBar1",
    orientation: str = "HORIZONTAL",
    width: int = 14400,
    height: int = 1984,
    section_index: int = 0,
) -> Para:
    """Add a scroll bar form control to the document.

    *orientation*: ``"HORIZONTAL"`` or ``"VERTICAL"``.
    """
    from .writer.shape_writer import build_scrollbar_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_scrollbar_xml(
        name=name, orientation=orientation,
        width=width, height=height,
    )
    return para


# ======================================================================
# Inline / Special Characters  (Phase 4)
# ======================================================================

def add_highlight(
    hwpx_file: HWPXFile,
    text: str,
    color: str = "#FFFF00",
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> Para:
    """Add highlighted (markpen) text to the document.

    Creates a new paragraph containing the highlighted text.
    """
    from .writer.shape_writer import build_highlight_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_highlight_xml(
        _sanitize_text(text), color=color,
        char_pr_id_ref=char_pr_id_ref,
    )
    return para


def add_dutmal(
    hwpx_file: HWPXFile,
    main_text: str,
    sub_text: str,
    pos: str = "TOP",
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> Para:
    """Add ruby text (dutmal) to the document.

    *main_text* is the base text, *sub_text* is the ruby annotation.
    *pos*: ``"TOP"`` or ``"BOTTOM"``.
    """
    from .writer.shape_writer import build_dutmal_xml

    para = _new_raw_para(hwpx_file, section_index)
    para.raw_xml_content = build_dutmal_xml(
        _sanitize_text(main_text), _sanitize_text(sub_text),
        pos=pos, char_pr_id_ref=char_pr_id_ref,
    )
    return para


def add_hidden_comment(
    hwpx_file: HWPXFile,
    text: str,
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> Para:
    """Add a hidden comment annotation to the document.

    The comment is appended to the last content paragraph as an inline
    control, matching the Hancom Office structure.
    """
    from .writer.shape_writer import build_hidden_comment_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    paras = section.paras()

    # Find the last content paragraph
    anchor_para = None
    for p in reversed(paras):
        if p.count_of_run() > 0 or (
            p.raw_xml_content
            and '<hp:header' not in p.raw_xml_content
            and '<hp:footer' not in p.raw_xml_content
        ):
            anchor_para = p
            break

    if anchor_para is None or anchor_para.raw_xml_content is None:
        anchor_para = _new_raw_para(hwpx_file, section_index)
        anchor_para.raw_xml_content = ""

    comment_xml = build_hidden_comment_xml(
        _sanitize_text(text), char_pr_id_ref=char_pr_id_ref,
    )
    if anchor_para.raw_xml_content:
        anchor_para.raw_xml_content += comment_xml
    else:
        anchor_para.raw_xml_content = comment_xml
    return anchor_para


def add_indexmark(
    hwpx_file: HWPXFile,
    key: str,
    second_key: str | None = None,
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> Para:
    """Add an index mark to the document.

    The index mark is appended to the last content paragraph as an inline
    control.
    """
    from .writer.shape_writer import build_indexmark_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    paras = section.paras()

    anchor_para = None
    for p in reversed(paras):
        if p.count_of_run() > 0 or (
            p.raw_xml_content
            and '<hp:header' not in p.raw_xml_content
            and '<hp:footer' not in p.raw_xml_content
        ):
            anchor_para = p
            break

    if anchor_para is None or anchor_para.raw_xml_content is None:
        anchor_para = _new_raw_para(hwpx_file, section_index)
        anchor_para.raw_xml_content = ""

    mark_xml = build_indexmark_xml(
        _sanitize_text(key),
        second_key=_sanitize_text(second_key) if second_key else None,
        char_pr_id_ref=char_pr_id_ref,
    )
    if anchor_para.raw_xml_content:
        anchor_para.raw_xml_content += mark_xml
    else:
        anchor_para.raw_xml_content = mark_xml
    return anchor_para


def add_tab(
    hwpx_file: HWPXFile,
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> Para:
    """Add a tab character to the document.

    Appended to the last content paragraph.
    """
    from .writer.shape_writer import build_tab_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    paras = section.paras()

    anchor_para = None
    for p in reversed(paras):
        if p.count_of_run() > 0 or (
            p.raw_xml_content
            and '<hp:header' not in p.raw_xml_content
            and '<hp:footer' not in p.raw_xml_content
        ):
            anchor_para = p
            break

    if anchor_para is None or anchor_para.raw_xml_content is None:
        anchor_para = _new_raw_para(hwpx_file, section_index)
        anchor_para.raw_xml_content = ""

    tab_xml = build_tab_xml(char_pr_id_ref=char_pr_id_ref)
    if anchor_para.raw_xml_content:
        anchor_para.raw_xml_content += tab_xml
    else:
        anchor_para.raw_xml_content = tab_xml
    return anchor_para


def add_special_char(
    hwpx_file: HWPXFile,
    char_type: str = "nbspace",
    char_pr_id_ref: str = "0",
    section_index: int = 0,
) -> Para:
    """Add a special character to the document.

    *char_type*: ``"nbspace"`` (non-breaking space), ``"fwspace"``
    (full-width space), or ``"hyphen"`` (non-breaking hyphen).

    Appended to the last content paragraph.
    """
    from .writer.shape_writer import build_special_char_xml

    section = hwpx_file.section_xml_file_list.get(section_index)
    paras = section.paras()

    anchor_para = None
    for p in reversed(paras):
        if p.count_of_run() > 0 or (
            p.raw_xml_content
            and '<hp:header' not in p.raw_xml_content
            and '<hp:footer' not in p.raw_xml_content
        ):
            anchor_para = p
            break

    if anchor_para is None or anchor_para.raw_xml_content is None:
        anchor_para = _new_raw_para(hwpx_file, section_index)
        anchor_para.raw_xml_content = ""

    char_xml = build_special_char_xml(
        char_type=char_type, char_pr_id_ref=char_pr_id_ref,
    )
    if anchor_para.raw_xml_content:
        anchor_para.raw_xml_content += char_xml
    else:
        anchor_para.raw_xml_content = char_xml
    return anchor_para


def convert_md_to_hwpx(hwpx_file: HWPXFile, md_content: str, style: str = "github") -> int:
    """Convert Markdown content to HWPX elements in the document."""
    from .converter import convert_markdown_to_hwpx
    return convert_markdown_to_hwpx(hwpx_file, md_content, style)


def convert_md_file_to_hwpx(md_path: str, hwpx_path: str, style: str = "github") -> None:
    """Convert a .md file to .hwpx file."""
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    doc = create_document()
    convert_md_to_hwpx(doc, content, style)
    save(doc, hwpx_path)


# ======================================================================
# HTML conversion
# ======================================================================

def convert_html_to_hwpx(hwpx_file: HWPXFile, html_content: str) -> int:
    """Convert HTML content to HWPX elements in the document.

    Uses only Python standard library (``html.parser``) for parsing.
    Supports headings, paragraphs, bold/italic/underline, tables, lists,
    images (base64 and local files), hyperlinks, code blocks, form
    controls, ruby text, and inline CSS styles.
    """
    from .html_to_hwpx import convert_html_to_hwpx as _convert
    return _convert(hwpx_file, html_content)


def convert_html_file_to_hwpx(html_path: str, hwpx_path: str) -> None:
    """Convert an HTML file to a HWPX file."""
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    doc = create_document()
    convert_html_to_hwpx(doc, content)
    save(doc, hwpx_path)


# ======================================================================
# Reading & text extraction
# ======================================================================

def open_document(filepath: str):
    """Open an existing HWPX file for reading.

    Returns an :class:`~pyhwpxlib.reader.HwpxDocument` with parsed
    sections, paragraphs, tables, and image references.
    """
    from .reader import HwpxDocument
    return HwpxDocument.open(filepath)


def extract_text(filepath: str, separator: str = "\n") -> str:
    """Extract plain text from HWPX file."""
    from .reader import extract_text as _extract_text
    return _extract_text(filepath, separator=separator)


def extract_markdown(filepath: str) -> str:
    """Extract content from HWPX file as Markdown."""
    from .reader import extract_markdown as _extract_md
    return _extract_md(filepath)


def extract_html(filepath: str) -> str:
    """Extract content from HWPX file as HTML."""
    from .reader import extract_html as _extract_html
    return _extract_html(filepath)


# ======================================================================
# Page setup
# ======================================================================

_PAPER_SIZES: dict[str, tuple[int, int]] = {
    "A4": (59528, 84186),
    "A3": (84186, 119056),
    "B5": (51024, 72284),
    "LETTER": (61200, 79200),
    "LEGAL": (61200, 100800),
}


def set_page_setup(
    hwpx_file: HWPXFile,
    *,
    paper: Optional[str] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    landscape: Optional[bool] = None,
    margin_left: Optional[int] = None,
    margin_right: Optional[int] = None,
    margin_top: Optional[int] = None,
    margin_bottom: Optional[int] = None,
    margin_header: Optional[int] = None,
    margin_footer: Optional[int] = None,
    section_index: int = 0,
) -> None:
    """Modify page setup (size, orientation, margins) for a section.

    The section properties live in the SecPr of the first paragraph's
    first run, which is created by BlankFileMaker.

    Parameters
    ----------
    paper : str, optional
        Paper size name: ``"A4"``, ``"A3"``, ``"B5"``, ``"LETTER"``, ``"LEGAL"``.
        Sets both width and height (overridden by explicit width/height).
    width, height : int, optional
        Page dimensions in HWPX units (1/7200 inch).
    landscape : bool, optional
        If True, swap width/height and set landscape orientation.
    margin_left, margin_right, margin_top, margin_bottom : int, optional
        Page margins in HWPX units.
    margin_header, margin_footer : int, optional
        Header/footer margins in HWPX units.
    section_index : int
        Index of the section to modify (default 0).
    """
    from .objects.section.enum_types import PageDirection

    section = hwpx_file.section_xml_file_list.get(section_index)
    paras = section.paras()
    if not paras:
        raise ValueError("Section has no paragraphs; cannot find SecPr.")

    # SecPr is in the first paragraph's first run
    first_para = paras[0]
    sec_pr = None
    for run_idx in range(first_para.count_of_run()):
        run = first_para.get_run(run_idx)
        if run.sec_pr is not None:
            sec_pr = run.sec_pr
            break

    if sec_pr is None:
        raise ValueError(
            "No SecPr found in the first paragraph. "
            "Ensure the document was created with create_document()."
        )

    page_pr = sec_pr.page_pr
    if page_pr is None:
        raise ValueError("SecPr has no PagePr; document structure is unexpected.")

    # Apply paper size
    if paper is not None:
        key = paper.upper()
        if key not in _PAPER_SIZES:
            raise ValueError(
                f"Unknown paper size '{paper}'. "
                f"Choices: {', '.join(_PAPER_SIZES.keys())}"
            )
        pw, ph = _PAPER_SIZES[key]
        if width is None:
            width = pw
        if height is None:
            height = ph

    # Apply landscape: swap dimensions if needed
    if landscape is not None:
        if landscape:
            page_pr.landscape = PageDirection.NARROWLY
            # In landscape mode, width > height
            if width is not None and height is not None and width < height:
                width, height = height, width
            elif width is None and height is None:
                # Swap existing
                cur_w = page_pr.width
                cur_h = page_pr.height
                if cur_w is not None and cur_h is not None and cur_w < cur_h:
                    page_pr.width = cur_h
                    page_pr.height = cur_w
        else:
            page_pr.landscape = PageDirection.WIDELY
            # In portrait mode, height > width
            if width is not None and height is not None and width > height:
                width, height = height, width

    if width is not None:
        page_pr.width = width
    if height is not None:
        page_pr.height = height

    # Apply margins
    margin = page_pr.margin
    if margin is None:
        margin = page_pr.create_margin()

    if margin_left is not None:
        margin.left = margin_left
    if margin_right is not None:
        margin.right = margin_right
    if margin_top is not None:
        margin.top = margin_top
    if margin_bottom is not None:
        margin.bottom = margin_bottom
    if margin_header is not None:
        margin.header = margin_header
    if margin_footer is not None:
        margin.footer = margin_footer


# ======================================================================
# HWPX → HTML conversion
# ======================================================================

def convert_hwpx_to_html(
    hwpx_path: str,
    output_path: str | None = None,
    embed_images: bool = True,
    title: str = "HWPX Document",
) -> str:
    """Convert HWPX file to standalone HTML for browser viewing.

    Produces a self-contained HTML document with inline CSS and
    base64-encoded images.  Handles paragraphs, styled text runs,
    tables, shapes, images, equations, and hyperlinks.

    Parameters
    ----------
    hwpx_path : str
        Path to the input .hwpx file.
    output_path : str or None
        Path to write the output .html file.  If None, the HTML is
        returned as a string without writing to disk.
    embed_images : bool
        Whether to embed images as base64 data URIs (default True).
    title : str
        Title for the HTML ``<title>`` element.

    Returns
    -------
    str
        The generated HTML content.
    """
    from .html_converter import convert_hwpx_to_html as _convert
    return _convert(
        hwpx_path,
        output_path=output_path,
        embed_images=embed_images,
        title=title,
    )


# ======================================================================
# Document merge
# ======================================================================

def merge_documents(hwpx_paths: list[str], output_path: str) -> None:
    """Merge multiple HWPX files into one.

    Opens each input file, extracts text paragraphs and tables,
    and recreates them in a single new HWPX document.  A page break
    is inserted between documents.

    Parameters
    ----------
    hwpx_paths : list of str
        Paths to the input .hwpx files (in order).
    output_path : str
        Path for the merged output .hwpx file.
    """
    from .reader import HwpxDocument

    if not hwpx_paths:
        raise ValueError("hwpx_paths must contain at least one file path.")

    doc = create_document()
    first_file = True

    for path in hwpx_paths:
        src = HwpxDocument.open(path)

        for section in src.sections:
            if not first_file:
                # Insert a page-break paragraph between documents
                _add_page_break(doc)

            for para in section.paragraphs:
                text = para.text
                if text:
                    add_paragraph(doc, text)

            for table in section.tables:
                grid = table.to_2d()
                if grid:
                    rows = len(grid)
                    cols = max(len(r) for r in grid) if grid else 0
                    # Pad rows to uniform width
                    padded = [
                        r + [""] * (cols - len(r)) for r in grid
                    ]
                    add_table(doc, rows, cols, data=padded)

            first_file = False

    save(doc, output_path)


def _add_page_break(hwpx_file: HWPXFile, section_index: int = 0) -> Para:
    """Insert a paragraph that forces a page break."""
    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    para.id = str(_random.randint(1000000000, 4294967295))
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = True
    para.column_break = False
    para.merged = False
    run = para.add_new_run()
    run.char_pr_id_ref = "0"
    t = run.add_new_t()
    t.add_text("")
    return para


# ======================================================================
# Template fill
# ======================================================================

def fill_template(
    template_path: str,
    data: dict[str, str],
    output_path: str,
) -> None:
    """Fill a template HWPX with data by replacing placeholder text.

    Placeholders are ``{{key}}`` patterns **or** literal text strings
    in the template.  All occurrences in every ``<hp:t>`` element
    across all section files are replaced.

    The original formatting is preserved — only the text content of
    matching ``<hp:t>`` nodes is changed.

    Parameters
    ----------
    template_path : str
        Path to the template .hwpx file.
    data : dict of str to str
        Mapping of placeholder text to replacement values.
        Both ``{{key}}`` style and literal-match replacements
        are supported.
    output_path : str
        Path for the filled output .hwpx file.
    """
    import shutil
    import zipfile
    import xml.etree.ElementTree as ET

    # Namespace normalization
    from .reader import _normalize_ns, _SECTION_RE

    if not data:
        # Nothing to replace — just copy the file
        shutil.copy2(template_path, output_path)
        return

    # Work on a copy
    shutil.copy2(template_path, output_path)

    with zipfile.ZipFile(template_path, "r") as zf_in:
        names = zf_in.namelist()
        section_names = sorted(n for n in names if _SECTION_RE.match(n))

        if not section_names:
            return

        # Read all files into memory
        file_data: dict[str, bytes] = {}
        for name in names:
            file_data[name] = zf_in.read(name)

    # Process each section file
    for sec_name in section_names:
        raw = file_data[sec_name]
        text = raw.decode("utf-8")

        # Perform text replacements in the raw XML
        for placeholder, value in data.items():
            # Escape the replacement value for XML
            xml_safe_value = (
                value.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
            )
            # Also escape the placeholder for matching in XML context
            # (the placeholder itself might contain special chars)
            xml_safe_placeholder = (
                placeholder.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&apos;")
            )
            text = text.replace(xml_safe_placeholder, xml_safe_value)
            # Also try the raw placeholder (in case it's not escaped)
            text = text.replace(placeholder, value)

        file_data[sec_name] = text.encode("utf-8")

    # Write the modified ZIP
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf_out:
        for name in names:
            zf_out.writestr(name, file_data[name])
