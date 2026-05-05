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
import itertools as _itertools
import random as _random

# Random start + sequential increment: unique within session,
# and unlikely to collide when merging documents from different sessions.
_para_id_counter = _itertools.count(_random.randint(1_000_000_000, 3_000_000_000))
from typing import List, Optional

logger = logging.getLogger(__name__)

from .hwpx_file import HWPXFile
from .objects.section.paragraph import Para, Run, T


def _init_para(para, para_pr_id_ref="0", style_id_ref="0", page_break=False):
    """Initialize common paragraph attributes."""
    para.id = str(next(_para_id_counter))
    para.para_pr_id_ref = para_pr_id_ref
    para.style_id_ref = style_id_ref
    para.page_break = page_break
    para.column_break = False
    para.merged = False


def create_document(font_set=None) -> HWPXFile:
    """Create a new blank HWPX document ready for content.

    Args:
        font_set: Optional FontSet from themes.py. If provided, registers
                  all theme fonts in header.xml fontfaces instead of the
                  default pair (함초롬돋움/함초롬바탕).
    """
    from .tools.blank_file_maker import BlankFileMaker
    return BlankFileMaker.make(font_set=font_set)


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
    cell_aligns: dict[tuple[int, int], str] | None = None,
    cell_styles: dict[tuple[int, int], dict] | None = None,
    section_index: int = 0,
    *,
    page_break: str = "CELL",
    repeat_header: bool = False,
) -> Para:
    """Add a table to the document.

    *col_widths* is a list of column widths in HWPX units. If None, distributed evenly.
    *row_heights* is a list of row heights. If None, defaults to 3600 per row.
    *cell_margin* is (left, right, top, bottom) in HWPX units.
    *cell_gradients* maps ``(row, col)`` to gradient config dicts with keys:
        ``start``, ``end``, ``type`` (default ``"LINEAR"``), ``angle`` (default 0).
    *cell_aligns* maps ``(row, col)`` to alignment string
        (``"CENTER"``, ``"LEFT"``, ``"RIGHT"``).
    *cell_styles* maps ``(row, col)`` to char style dict with keys:
        ``bold``, ``text_color``, ``font_size``.

    Page-break controls (v0.18.1+, keyword-only):
    *page_break* — ``"CELL"`` (default, split between rows), ``"TABLE"``
    (push entire table to next page if it doesn't fit), ``"NONE"`` (no split).
    *repeat_header* — when True, row 0 repeats at the top of every page the
    table spans. Hancom UI: 표 속성 → "여러 쪽 지원" / "제목 줄 반복".
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

    # cell_aligns → cell_para_pr_ids
    cell_para_pr_ids: dict[tuple[int, int], str] | None = None
    if cell_aligns:
        from .style_manager import ensure_para_style
        cell_para_pr_ids = {}
        for (r, c), align in cell_aligns.items():
            cell_para_pr_ids[(r, c)] = ensure_para_style(hwpx_file, align=align)

    # cell_styles → cell_char_pr_ids
    cell_char_pr_ids: dict[tuple[int, int], str] | None = None
    if cell_styles:
        from .style_manager import ensure_char_style, font_size_to_height
        cell_char_pr_ids = {}
        for (r, c), style in cell_styles.items():
            cell_char_pr_ids[(r, c)] = ensure_char_style(
                hwpx_file,
                bold=style.get('bold', False),
                text_color=style.get('text_color'),
                height=font_size_to_height(style.get('font_size')),
            )

    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    _init_para(para)
    para.raw_xml_content = build_table_xml(
        rows, cols, data, width,
        merge_info=merge_info,
        cell_border_fill_ids=cell_border_fill_ids,
        col_widths=col_widths,
        row_heights=row_heights,
        cell_margin=cell_margin,
        cell_para_pr_ids=cell_para_pr_ids,
        cell_char_pr_ids=cell_char_pr_ids,
        page_break=page_break,
        repeat_header=repeat_header,
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
    _init_para(para)
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
    _init_para(para)
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
    _init_para(para)
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
    _init_para(para)
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
    _init_para(para)
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
    _init_para(para)
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
    _init_para(para)
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
    _init_para(para, para_pr_id_ref=para_pr_id_ref, style_id_ref=style_id_ref)

    run = para.add_new_run()
    run.char_pr_id_ref = char_pr_id_ref

    t = run.add_new_t()
    t.add_text(_sanitize_text(text))

    return para


_ILLEGAL_XML_CHARS = _re.compile(
    r"[\x00-\x08\x0b\x0c\x0d\x0e-\x1f\ufffe\uffff]"
)


def _sanitize_text(value: str) -> str:
    """Remove control characters that are invalid in XML text nodes.

    Only strips illegal XML chars (control characters).
    XML special characters (&, <, >) are NOT escaped here —
    the serialization layer (lxml/python-hwpx) handles escaping
    automatically when writing element text content.
    """
    return _ILLEGAL_XML_CHARS.sub("", value)


def _new_raw_para(hwpx_file: HWPXFile, section_index: int = 0) -> Para:
    """Create and return a new blank paragraph attached to the section."""
    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    _init_para(para)
    return para


# ======================================================================
# Bullet list
# ======================================================================

def add_bullet_list(
    hwpx_file: HWPXFile,
    items: List[str],
    bullet_char: str = "\u25cf",
    char_pr_id_ref: str = "0",
    margin_left: int = 0,
    section_index: int = 0,
) -> List[Para]:
    """Add a bullet list to the document using native HWPX bullet definitions.

    Each item becomes a separate paragraph linked to a bullet definition
    in the header.  The bullet character is rendered automatically by
    the word processor -- no text prefix is inserted.

    *margin_left* adds left margin (indent) to the bullet paragraphs.

    Returns the list of created :class:`Para` objects.
    """
    from .style_manager import ensure_bullet, ensure_heading_para_style

    bullet_id = ensure_bullet(hwpx_file, char=bullet_char)
    para_pr_id = ensure_heading_para_style(
        hwpx_file, heading_type="BULLET", heading_id_ref=bullet_id,
        margin_left=margin_left,
    )

    paras: list[Para] = []
    for item in items:
        para = add_paragraph(
            hwpx_file, item,  # add_paragraph handles sanitization
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
            hwpx_file, item,  # add_paragraph handles sanitization
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
    bg_color: Optional[str] = None,
    char_pr_id_ref: Optional[str] = None,
    section_index: int = 0,
) -> Para:
    """Add a styled paragraph to the document.

    Style options:
    - *bold*, *italic*, *underline*: text decoration flags
    - *font_size*: font size in pt (e.g. 12, 16, 20)
    - *text_color*: hex color string (e.g. "#FF0000")
    - *font_name*: font face name (e.g. "D2Coding"); auto-registered
    - *bg_color*: background color hex string (e.g. "#E8F5E9")
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

    if bg_color:
        # 배경색이 있으면 highlight로 처리
        return add_highlight(hwpx_file, text, color=bg_color,
                             char_pr_id_ref=char_pr_id_ref,
                             section_index=section_index)

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
    _init_para(para)
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
    _init_para(para)
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
    3: (1600, True),
    4: (1400, True),
}


def add_heading(
    hwpx_file: HWPXFile,
    text: str,
    level: int = 1,
    section_index: int = 0,
    height: int | None = None,
    font_name: str | None = None,
    text_color: str | None = None,
) -> Para:
    """Add a heading paragraph to the document.

    Headings are regular paragraphs with larger, bold charPr:
    - level 1: 24pt bold
    - level 2: 18pt bold
    - level 3: 14pt bold
    - level 4: 12pt bold

    Optional overrides (used by theme integration):
    - height: override the default charPr height for this level
    - font_name: override the default font
    - text_color: override the default text color
    """
    from .style_manager import ensure_char_style

    default_height, bold = _HEADING_STYLES.get(level, (1200, True))
    if height is None:
        height = default_height

    style_kwargs: dict = dict(bold=bold, height=height)
    if font_name is not None:
        style_kwargs['font_name'] = font_name
    if text_color is not None:
        style_kwargs['text_color'] = text_color

    char_pr_id = ensure_char_style(hwpx_file, **style_kwargs)
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
            hwpx_file, text,  # add_paragraph handles sanitization
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
            hwpx_file, text,  # add_paragraph handles sanitization
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


def convert_html_file_to_hwpx(html_path: str, hwpx_path: str, strip_links: bool = True) -> None:
    """Convert an HTML file to a HWPX file.

    Parameters
    ----------
    strip_links : bool
        If True (default), remove ``<a>`` tags and keep only their text.
        Prevents Whale rendering errors caused by fieldBegin/fieldEnd.
    """
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if strip_links:
        content = _re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', content, flags=_re.DOTALL)
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

        # Parse section XML directly to preserve block order
        import zipfile
        import xml.etree.ElementTree as _ET
        _HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"

        with zipfile.ZipFile(path) as zf:
            sec_names = sorted(n for n in zf.namelist()
                              if n.startswith('Contents/section') and n.endswith('.xml'))

            for sec_idx, sec_name in enumerate(sec_names):
                if not first_file:
                    _add_page_break(doc)

                sec_root = _ET.fromstring(zf.read(sec_name).decode('utf-8'))
                tables = src.sections[sec_idx].tables if sec_idx < len(src.sections) else []
                tbl_idx = 0

                for child in sec_root:
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if tag == 'p':
                        texts = []
                        for t_el in child.iter(f'{{{_HP_NS}}}t'):
                            if t_el.text:
                                texts.append(t_el.text)
                        text = ''.join(texts).strip()
                        if text:
                            add_paragraph(doc, text)
                    elif tag == 'tbl':
                        if tbl_idx < len(tables):
                            grid = tables[tbl_idx].to_2d()
                            if grid:
                                rows = len(grid)
                                cols = max(len(r) for r in grid) if grid else 0
                                padded = [r + [""] * (cols - len(r)) for r in grid]
                                add_table(doc, rows, cols, data=padded)
                            tbl_idx += 1

                first_file = False

    save(doc, output_path)


def _add_page_break(hwpx_file: HWPXFile, section_index: int = 0) -> Para:
    """Insert a paragraph that forces a page break."""
    section = hwpx_file.section_xml_file_list.get(section_index)
    para = section.add_new_para()
    _init_para(para, page_break=True)
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
    *,
    fix_linesegs: bool = False,
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
    fix_linesegs : bool, optional (default False)
        v0.14.0: opt-in to apply the precise textpos-overflow fix on save
        (Hancom security trigger workaround). The default preserves the
        template's original lineseg structures so external renderers see
        what was actually written.
    """
    import shutil

    # Namespace normalization
    from .reader import _normalize_ns, _SECTION_RE
    from .package_ops import read_zip_archive, update_entries, write_zip_archive

    if not data:
        # Nothing to replace — just copy the file
        shutil.copy2(template_path, output_path)
        return

    archive = read_zip_archive(template_path)
    section_names = sorted(n for n in archive.files if _SECTION_RE.match(n))
    if not section_names:
        shutil.copy2(template_path, output_path)
        return

    # Replace text inside <hp:t> nodes only — delegated to xml_ops
    from .xml_ops import replace_text_nodes
    archive = update_entries(
        archive,
        section_names,
        lambda _name, raw: replace_text_nodes(raw.decode("utf-8"), data).encode("utf-8"),
    )
    write_zip_archive(output_path, archive, strip_linesegs=("precise" if fix_linesegs else False))


def fill_template_checkbox(
    template_path: str,
    data: dict[str, str],
    checks: list[str] | None = None,
    output_path: str = "",
    *,
    fix_linesegs: bool = False,
) -> str:
    """Fill a template HWPX with data and checkbox marks.

    Combines text replacement with checkbox marking (□→■).

    Parameters
    ----------
    template_path : str
        Path to the template .hwpx file.
    data : dict of str to str
        Text replacements. e.g. ``{"성 명": "성 명  홍길동"}``
    checks : list of str, optional
        Checkbox labels to mark. Finds ``□`` after each label
        and replaces with ``■``. e.g. ``["민간기업"]``
        Use ``"__ALL__"`` to mark all checkboxes.
    output_path : str
        Path for output. If empty, adds ``_filled`` suffix.

    Returns
    -------
    str
        Path to the created file.
    """
    import shutil

    if not output_path:
        base, ext = _pathlib.Path(template_path).stem, _pathlib.Path(template_path).suffix
        output_path = str(_pathlib.Path(template_path).parent / f"{base}_filled{ext}")

    from .package_ops import read_zip_archive, write_zip_archive
    archive = read_zip_archive(template_path)
    section_names = [n for n in archive.files if 'section' in n and n.endswith('.xml')]

    for sec_name in section_names:
        text = archive.files[sec_name].decode("utf-8")

        # 1. Text replacements — only inside <hp:t> nodes
        if data:
            from .xml_ops import replace_text_nodes
            text = replace_text_nodes(text, data, support_braced_keys=False)

        # 2. Checkbox marks — 4가지 패턴 지원
        # □ (U+25A1) → ■ (U+25A0)
        # ☐ (U+2610) → ☑ (U+2611)
        # [  ] → [■]
        # [ ] → [■]
        _CHECK_PATTERNS = [
            ("□", "■"),
            ("☐", "☑"),
            ("[  ]", "[■]"),
            ("[ ]", "[■]"),
        ]
        if checks:
            if "__ALL__" in checks:
                for unchecked, checked in _CHECK_PATTERNS:
                    text = text.replace(unchecked, checked)
            else:
                for label in checks:
                    pos = text.find(label)
                    if pos < 0:
                        continue
                    # 라벨 주변에서 체크박스 탐색 (앞 50자 ~ 뒤 50자)
                    search_start = max(0, pos - 50)
                    search_end = min(len(text), pos + len(label) + 50)
                    region = text[search_start:search_end]
                    replaced = False
                    for unchecked, checked in _CHECK_PATTERNS:
                        # 라벨 앞의 체크박스 우선 (□예 패턴)
                        label_in_region = pos - search_start
                        before = region[:label_in_region]
                        box_before = before.rfind(unchecked)
                        if box_before >= 0:
                            abs_pos = search_start + box_before
                            text = text[:abs_pos] + checked + text[abs_pos + len(unchecked):]
                            replaced = True
                            break
                        # 라벨 뒤의 체크박스 (동의함 □ 패턴)
                        after = region[label_in_region + len(label):]
                        box_after = after.find(unchecked)
                        if box_after >= 0:
                            abs_pos = pos + len(label) + box_after
                            text = text[:abs_pos] + checked + text[abs_pos + len(unchecked):]
                            replaced = True
                            break

        archive.files[sec_name] = text.encode("utf-8")

    write_zip_archive(output_path, archive, strip_linesegs=("precise" if fix_linesegs else False))

    return output_path


def fill_template_batch(
    template_path: str,
    records: list[dict],
    output_dir: str = "",
    filename_field: str = "",
) -> list[str]:
    """Generate multiple filled documents from one template.

    Parameters
    ----------
    template_path : str
        Path to the template .hwpx file.
    records : list of dict
        Each dict has ``"data"`` (text replacements),
        optional ``"checks"`` (checkbox labels),
        optional ``"filename"`` (output filename).
    output_dir : str
        Directory for output files. Defaults to template's directory.
    filename_field : str
        Key in ``data`` to use for filename. e.g. ``"성 명"``

    Returns
    -------
    list of str
        Paths to all created files.
    """
    import os

    if not output_dir:
        output_dir = str(_pathlib.Path(template_path).parent)
    os.makedirs(output_dir, exist_ok=True)

    stem = _pathlib.Path(template_path).stem
    outputs = []

    for i, record in enumerate(records):
        data = record.get("data", {})
        checks = record.get("checks", [])
        fname = record.get("filename", "")

        if not fname and filename_field and filename_field in data:
            # Extract value from data (e.g. "성 명  홍길동" → "홍길동")
            val = data[filename_field]
            # Take the part after the label
            parts = val.split()
            fname = parts[-1] if len(parts) > 1 else parts[0]

        if not fname:
            fname = f"{i + 1}"

        out_path = os.path.join(output_dir, f"{stem}_{fname}.hwpx")
        fill_template_checkbox(template_path, data, checks, out_path)
        outputs.append(out_path)

    return outputs


def analyze_schema_with_llm(
    schema: dict,
    llm_call=None,
) -> dict:
    """LLM을 사용하여 서식 필드를 자동 분류.

    extract_schema() 결과를 LLM에 보내서 각 필드를
    'input'(사용자 입력), 'fixed'(고정 텍스트), 'header'(제목/섹션)로 분류.

    Parameters
    ----------
    schema : dict
        extract_schema()의 반환값
    llm_call : callable, optional
        LLM 호출 함수. ``llm_call(prompt) -> str`` 형태.
        None이면 규칙 기반 분류 사용.

    Returns
    -------
    dict
        ``template_schema`` — 분류된 필드 + 체크박스 + 메타데이터
    """
    fields = schema.get('fields', [])
    checkboxes = schema.get('checkboxes', [])

    if llm_call is not None:
        # LLM 기반 분류
        labels = [f['label'] for f in fields]
        checks = [c['raw_text'][:60] for c in checkboxes]

        prompt = f"""다음은 한국 정부/기업 서식(양식)에서 추출한 텍스트 라벨 목록입니다.
각 라벨을 다음 3가지로 분류해주세요:

- input: 사용자가 직접 데이터를 입력하는 필드 (이름, 주소, 날짜 등)
- fixed: 고정 텍스트로 변경하면 안 되는 것 (제목, 안내문, 처리기관 등)
- header: 섹션 제목이나 구분선 역할 (큰 제목, 섹션명 등)

JSON 배열로 응답해주세요. 각 항목은 {{"label": "...", "type": "input|fixed|header"}} 형식.

라벨 목록:
{labels}

체크박스 목록 (이건 모두 "checkbox" 타입):
{checks}

JSON만 응답:"""

        try:
            response = llm_call(prompt)
            import json
            # JSON 배열 추출
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                classified = json.loads(response[start:end])
                return _build_template_schema(schema, classified, checkboxes)
        except Exception as e:
            logger.warning("LLM classification failed, falling back to rules: %s", e)

    # 규칙 기반 분류 (fallback)
    return _classify_fields_by_rules(schema)


def _classify_fields_by_rules(schema: dict) -> dict:
    """규칙 기반 필드 분류 (LLM 없을 때 fallback)"""
    # 입력 필드 패턴
    input_patterns = {
        '성 명', '주민등록번호', '주 소', '장애유형', '사업체명', '대표자',
        '소재지', '담당자명', '연락처', '사업자등록번호', '상시근로자 수',
        '장애인 근로자 수', '업종(주된 생산품)', '현 직장 취업일자', '기기명',
        '외국인등록번호', '보유기간',
    }
    # 고정 텍스트 패턴
    fixed_patterns = {
        '14일', '수수료', '신청서 작성', '접 수', '검 토', '결 재', '결정 통지',
        '처 리 기 관', '준영구', '동의함',
    }
    # 제목 패턴
    header_patterns = {
        '서비스 신청서', '서비스 신청 내용', '서비스 필요영역', '서비스 희망기간',
        '서비스 요청사항', '행정정보', '개인정보',
    }

    input_fields = []
    fixed_fields = []
    header_fields = []

    for f in schema.get('fields', []):
        label = f['label']
        if label in input_patterns or any(p in label for p in ['취득', '기간', '내용', '직무']):
            f['field_type'] = 'input'
            input_fields.append(f)
        elif label in fixed_patterns or any(p in label for p in fixed_patterns):
            f['field_type'] = 'fixed'
            fixed_fields.append(f)
        elif any(p in label for p in header_patterns):
            f['field_type'] = 'header'
            header_fields.append(f)
        elif len(label) <= 5:
            f['field_type'] = 'input'
            input_fields.append(f)
        else:
            f['field_type'] = 'fixed'
            fixed_fields.append(f)

    return {
        'title': schema.get('title', ''),
        'source': schema.get('source', ''),
        'input_fields': input_fields,
        'fixed_fields': fixed_fields,
        'header_fields': header_fields,
        'checkboxes': schema.get('checkboxes', []),
    }


def _build_template_schema(schema, classified, checkboxes):
    """LLM 분류 결과를 template_schema로 변환"""
    field_map = {f['label']: f for f in schema.get('fields', [])}

    input_fields = []
    fixed_fields = []
    header_fields = []

    for item in classified:
        label = item.get('label', '')
        field_type = item.get('type', 'fixed')
        f = field_map.get(label, {'label': label, 'type': 'text'})
        f['field_type'] = field_type

        if field_type == 'input':
            input_fields.append(f)
        elif field_type == 'header':
            header_fields.append(f)
        else:
            fixed_fields.append(f)

    return {
        'title': schema.get('title', ''),
        'source': schema.get('source', ''),
        'input_fields': input_fields,
        'fixed_fields': fixed_fields,
        'header_fields': header_fields,
        'checkboxes': checkboxes,
    }


def extract_schema(
    template_path: str,
) -> dict:
    """Extract fillable field schema from a HWPX/OWPML template.

    Analyzes table cells to detect labels, input fields, and checkboxes.
    Returns a JSON-serializable schema that describes what can be filled.

    Parameters
    ----------
    template_path : str
        Path to the template .hwpx or .owpml file.

    Returns
    -------
    dict
        Schema with ``title``, ``fields`` (label fields),
        ``checkboxes`` (checkbox groups), and ``format_info``.
    """
    import zipfile
    import xml.etree.ElementTree as ET

    _hp = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"

    with zipfile.ZipFile(template_path) as z:
        section = z.read("Contents/section0.xml").decode("utf-8")
    root = ET.fromstring(section)

    tables = root.findall(f".//{_hp}tbl")
    title = ""
    fields = []
    checkboxes = []

    # Body text 제목 탐지
    for p in root.findall(f"{_hp}p"):
        texts = []
        for run in p.findall(f"{_hp}run"):
            t = run.find(f"{_hp}t")
            if t is not None and t.text:
                texts.append(t.text.strip())
        combined = " ".join(texts).strip()
        if combined and not title:
            title = combined
            break

    for ti, tbl in enumerate(tables):
        rows_attr = tbl.get("rowCnt", "0")
        cols_attr = tbl.get("colCnt", "0")

        for tc in tbl.findall(f".//{_hp}tc"):
            t_elements = tc.findall(f".//{_hp}t")
            texts = [t.text for t in t_elements if t.text]
            cell_text = "".join(texts).strip()
            if not cell_text:
                continue

            # 체크박스 탐지: □ 또는 [  ] 포함
            has_checkbox = "□" in cell_text or "[  ]" in cell_text
            if has_checkbox:
                # 개별 체크 옵션 추출
                options = []
                import re
                # "국가 [  ] (공무원 [  ] ...), 민간기업 [  ]" 패턴
                for m in re.finditer(r"([\w()]+)\s*\[  \]", cell_text):
                    options.append(m.group(1))
                for m in re.finditer(r"([\w()]+)\s*□", cell_text):
                    options.append(m.group(1))
                if options:
                    checkboxes.append({
                        "table": ti,
                        "type": "checkbox",
                        "options": options,
                        "raw_text": cell_text[:80],
                    })
                continue

            # 라벨 필드 탐지: 짧은 텍스트 (2~20자)
            if 2 <= len(cell_text) <= 20:
                # 제목, 고정 텍스트 제외
                skip_words = ["접수번호", "접수일", "처리기간", "처리절차",
                              "첨부서류", "수수료", "신청인", "사업주동의",
                              "서명 또는 인", "귀하"]
                if any(w in cell_text for w in skip_words):
                    continue
                # 숫자만 있는 셀 제외
                if cell_text.replace(" ", "").isdigit():
                    continue

                fields.append({
                    "table": ti,
                    "type": "text",
                    "label": cell_text,
                    "fill_pattern": f">{cell_text}<",
                    "fill_example": f">{cell_text}  [값 입력]<",
                })

    return {
        "title": title,
        "source": str(_pathlib.Path(template_path).name),
        "tables": len(tables),
        "fields": fields,
        "checkboxes": checkboxes,
    }


# ======================================================================
# Insert image into existing document
# ======================================================================

def insert_image_to_existing(
    hwpx_path: str,
    image_path: str,
    output_path: str,
    width: int = 21260,
    height: int = 15000,
    position: str = 'end',
    section: int = 0,
) -> str:
    """Insert an image into an existing HWPX document.

    Args:
        hwpx_path: path to existing .hwpx file
        image_path: path to image file (PNG, JPEG, BMP, etc.)
        output_path: path for output .hwpx file
        width: display width in HWPX units (default ~75mm)
        height: display height in HWPX units (default ~53mm)
        position: 'end' (append) or 'start' (prepend after secPr)
        section: section index (default 0)

    Returns:
        output_path
    """
    import zipfile
    import tempfile
    import shutil
    from pathlib import Path

    img = Path(image_path)
    if not img.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    ext = img.suffix.lower().lstrip('.')
    if ext == 'jpg':
        ext = 'jpeg'
    mime_map = {'png': 'image/png', 'jpeg': 'image/jpeg', 'bmp': 'image/bmp',
                'gif': 'image/gif', 'tiff': 'image/tiff'}
    media_type = mime_map.get(ext, 'image/png')

    # Read image to get original dimensions
    img_data = img.read_bytes()
    org_w, org_h = width, height
    try:
        from PIL import Image as PILImage
        with PILImage.open(image_path) as pil_img:
            pw, ph = pil_img.size
            # Convert pixels to HWPX units (~7.2 units per pixel at 96dpi)
            org_w = int(pw * 7.2)
            org_h = int(ph * 7.2)
    except ImportError:
        pass

    # Unpack to temp directory
    tmp_dir = tempfile.mkdtemp(prefix='hwpx_insert_img_')
    try:
        with zipfile.ZipFile(hwpx_path) as z:
            z.extractall(tmp_dir)
            names = z.namelist()

        # Find next available BinData ID
        existing_bins = [n for n in names if n.startswith('BinData/')]
        bin_id = len(existing_bins) + 1
        bin_name = f"image{bin_id}"
        bin_filename = f"{bin_name}.{ext}"
        bin_path = f"BinData/{bin_filename}"

        # Copy image to BinData/
        bindata_dir = Path(tmp_dir) / 'BinData'
        bindata_dir.mkdir(exist_ok=True)
        (bindata_dir / bin_filename).write_bytes(img_data)

        # Update content.hpf manifest
        hpf_path = Path(tmp_dir) / 'Contents' / 'content.hpf'
        hpf = hpf_path.read_text(encoding='utf-8')
        manifest_item = f'<opf:item id="{bin_name}" href="BinData/{bin_filename}" media-type="{media_type}" isEmbeded="1"/>'
        hpf = hpf.replace('</opf:manifest>', f'  {manifest_item}\n</opf:manifest>')
        hpf_path.write_text(hpf, encoding='utf-8')

        # Build image paragraph XML
        import random
        pic_id = random.randint(1_000_000_000, 3_000_000_000)
        inst_id = random.randint(1_000_000_000, 3_000_000_000)
        para_id = random.randint(1_000_000_000, 3_000_000_000)

        scale_x = f"{width / org_w:.6f}" if org_w else "1"
        scale_y = f"{height / org_h:.6f}" if org_h else "1"

        img_para_xml = (
            f'<hp:p id="{para_id}" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="0">'
            f'<hp:pic id="{pic_id}" zOrder="0" numberingType="PICTURE" '
            f'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
            f'dropcapstyle="None" href="" groupLevel="0" instid="{inst_id}" reverse="0">'
            f'<hp:offset x="0" y="0"/>'
            f'<hp:orgSz width="{org_w}" height="{org_h}"/>'
            f'<hp:curSz width="{width}" height="{height}"/>'
            f'<hp:flip horizontal="0" vertical="0"/>'
            f'<hp:rotationInfo angle="0" centerX="{width//2}" centerY="{height//2}" rotateimage="1"/>'
            f'<hp:renderingInfo>'
            f'<hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
            f'<hc:scaMatrix e1="{scale_x}" e2="0" e3="0" e4="0" e5="{scale_y}" e6="0"/>'
            f'<hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
            f'</hp:renderingInfo>'
            f'<hp:imgRect>'
            f'<hc:pt0 x="0" y="0"/><hc:pt1 x="{org_w}" y="0"/>'
            f'<hc:pt2 x="{org_w}" y="{org_h}"/><hc:pt3 x="0" y="{org_h}"/>'
            f'</hp:imgRect>'
            f'<hp:imgClip left="0" top="0" right="0" bottom="0"/>'
            f'<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
            f'<hp:imgDim dimwidth="{org_w}" dimheight="{org_h}"/>'
            f'<hc:img binaryItemIDRef="{bin_name}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>'
            f'<hp:sz width="{width}" height="{height}" widthRelTo="ABSOLUTE" heightRelTo="ABSOLUTE" protect="0"/>'
            f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="1" '
            f'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" '
            f'vertOffset="0" horzOffset="0"/>'
            f'<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
            f'</hp:pic></hp:run></hp:p>'
        )

        # Insert into section XML
        sec_file = Path(tmp_dir) / 'Contents' / f'section{section}.xml'
        sec_xml = sec_file.read_text(encoding='utf-8')

        if position == 'end':
            sec_xml = sec_xml.replace('</hs:sec>', img_para_xml + '\n</hs:sec>')
        else:  # start — after first </hp:p> (secPr paragraph)
            first_p_end = sec_xml.find('</hp:p>')
            if first_p_end > 0:
                insert_pos = first_p_end + len('</hp:p>')
                sec_xml = sec_xml[:insert_pos] + '\n' + img_para_xml + sec_xml[insert_pos:]

        sec_file.write_text(sec_xml, encoding='utf-8')

        # Repack using pyhwpxlib pack
        from .cli import _cmd_pack
        import argparse
        pack_args = argparse.Namespace(input=tmp_dir, output=output_path)
        _cmd_pack(pack_args)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return output_path


# ───────────────────────────────────────────────────────────────────
# PNG preview rendering (v0.17.3+)
# ───────────────────────────────────────────────────────────────────

# Plan SC FR-03: process-lifetime monotonic flag — fontconfig setup happens
# at most once per process. Subsequent calls early-return without filesystem
# access. Reset only when an explicit non-default font_dir is passed.
_FONTS_REGISTERED: bool = False
_FONTS_REGISTERED_DIR: Optional[str] = None


def _register_bundled_fonts(font_dir: Optional[str] = None) -> str:
    """Idempotently copy bundled NanumGothic into a fontconfig-watched dir.

    Returns the directory path used. After the first successful call within
    a process, repeated calls with the same (or default) ``font_dir`` are a
    cheap no-op (no filesystem stat). ``fc-cache`` is invoked only when at
    least one font file was copied. Best-effort: failures (e.g. ``fc-cache``
    missing on Windows) are silently ignored — Cairo's font lookup may
    still succeed via other means.
    """
    import os
    import shutil
    import subprocess

    global _FONTS_REGISTERED, _FONTS_REGISTERED_DIR

    if font_dir is None:
        font_dir = os.path.expanduser("~/.local/share/fonts")

    # Fast path: same dir already registered in this process.
    if _FONTS_REGISTERED and _FONTS_REGISTERED_DIR == font_dir:
        return font_dir

    try:
        from pyhwpxlib.vendor import NANUM_GOTHIC_REGULAR, NANUM_GOTHIC_BOLD
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "Bundled NanumGothic font missing from pyhwpxlib.vendor. "
            "Reinstall pyhwpxlib."
        ) from e

    os.makedirs(font_dir, exist_ok=True)

    copied = False
    for src, dst_name in [
        (NANUM_GOTHIC_REGULAR, "NanumGothic-Regular.ttf"),
        (NANUM_GOTHIC_BOLD, "NanumGothic-Bold.ttf"),
    ]:
        dst = os.path.join(font_dir, dst_name)
        if not os.path.exists(dst):
            shutil.copy(str(src), dst)
            copied = True

    if copied:
        try:
            subprocess.run(
                ["fc-cache", "-fv", font_dir],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # fc-cache may not be installed; Cairo can still find fonts via other paths

    _FONTS_REGISTERED = True
    _FONTS_REGISTERED_DIR = font_dir
    return font_dir


def render_to_png(
    hwpx_path: str,
    output_path: Optional[str] = None,
    *,
    page: int = 0,
    scale: float = 1.2,
    font_name: str = "NanumGothic",
    register_fonts: bool = True,
    engine: Optional["RhwpEngine"] = None,  # noqa: F821 — forward ref to rhwp_bridge.RhwpEngine
) -> str:
    """Render one page of an HWPX document to PNG.

    Pipeline: ``RhwpEngine.render_page_svg`` → regex-substitute every
    ``font-family`` attribute to ``font_name`` → ``cairosvg.svg2png``.

    The font-family substitution is the crucial step: rhwp emits SVG
    referencing original Korean font names (e.g. ``함초롬바탕``), which
    Cairo / fontconfig fails to resolve in headless or sandboxed
    environments — text renders as tofu (□□□). Replacing every
    ``font-family`` to a single fontconfig-known name fixes it.

    Args:
        hwpx_path: input ``.hwpx`` file path.
        output_path: output ``.png`` path. Default: ``{stem}_preview_p{page}.png``.
        page: 0-based page index.
        scale: cairosvg DPI scale (default 1.2 ≈ 110 DPI).
        font_name: fontconfig name to substitute everywhere. Must resolve
            on the host. Default ``"NanumGothic"`` works after
            ``register_fonts=True`` (default) or manual install.
        register_fonts: when True, copy bundled NanumGothic into
            ``~/.local/share/fonts`` and refresh ``fc-cache`` (idempotent,
            one-time cost).
        engine: optional pre-built ``RhwpEngine``. When supplied, no new
            engine is created — useful for batch rendering N pages without
            paying the ~851ms per-engine WASM compile cost N times. The
            module-level Engine/Module cache (``rhwp_bridge._ENGINE_CACHE``)
            already amortizes that cost across calls, so passing ``engine=``
            mostly saves the per-call ``Store``/``Linker``/``Instance``
            setup (~5-10ms each). The caller owns the engine's lifecycle.

    Returns:
        Output PNG path.

    Raises:
        ImportError: when ``[preview]`` extra (rhwp/wasmtime) or
            ``cairosvg`` is missing. The message includes the
            ``pip install`` command to fix it.
        FileNotFoundError: when ``hwpx_path`` does not exist.
        ValueError: when ``page`` is out of range.
    """
    import os

    if not os.path.exists(hwpx_path):
        raise FileNotFoundError(f"HWPX file not found: {hwpx_path}")

    try:
        from pyhwpxlib.rhwp_bridge import (
            RhwpEngine,
            NANUM_GOTHIC_REGULAR,
        )
    except ImportError as e:
        raise ImportError(
            "render_to_png requires the [preview] extra. "
            "Install with: pip install 'pyhwpxlib[preview]'"
        ) from e

    try:
        import cairosvg
    except ImportError as e:
        raise ImportError(
            "render_to_png requires cairosvg. "
            "Install with: pip install cairosvg"
        ) from e

    if register_fonts:
        _register_bundled_fonts()

    if engine is None:
        # Map every Korean / generic font family to the bundled NanumGothic
        # so rhwp's text-measurement also resolves consistently. The regex
        # substitution below handles the SVG-emission side.
        font_map = {
            "함초롬바탕": NANUM_GOTHIC_REGULAR,
            "함초롬돋움": NANUM_GOTHIC_REGULAR,
            "휴먼명조": NANUM_GOTHIC_REGULAR,
            "바탕": NANUM_GOTHIC_REGULAR,
            "Batang": NANUM_GOTHIC_REGULAR,
            "NanumGothic": NANUM_GOTHIC_REGULAR,
            "나눔고딕": NANUM_GOTHIC_REGULAR,
            "serif": NANUM_GOTHIC_REGULAR,
            "sans-serif": NANUM_GOTHIC_REGULAR,
        }
        engine = RhwpEngine(font_map=font_map)

    doc = engine.load(hwpx_path)

    if page < 0 or page >= doc.page_count:
        raise ValueError(
            f"page {page} out of range (document has {doc.page_count} pages)"
        )

    svg = doc.render_page_svg(page)

    # Crucial: replace every font-family attr so cairosvg/Cairo finds the
    # font via fontconfig. Without this, Korean glyphs render as tofu.
    svg_fixed = _re.sub(
        r'font-family="[^"]*"',
        f'font-family="{font_name}"',
        svg,
    )

    if output_path is None:
        stem = os.path.splitext(hwpx_path)[0]
        output_path = f"{stem}_preview_p{page}.png"

    cairosvg.svg2png(
        bytestring=svg_fixed.encode("utf-8"),
        write_to=output_path,
        scale=scale,
        unsafe=True,
    )
    return output_path


def render_pages_to_png(
    hwpx_path: str,
    out_dir: Optional[str] = None,
    *,
    scale: float = 1.2,
    font_name: str = "NanumGothic",
    register_fonts: bool = True,
    max_workers: Optional[int] = None,
) -> List[str]:
    """Render all pages of an HWPX document to PNGs in parallel.

    Uses a thread pool to parallelize SVG generation and PNG conversion.
    Significantly faster than sequential render_to_png for multi-page docs.
    """
    import os
    from concurrent.futures import ThreadPoolExecutor
    from .rhwp_bridge import RhwpEngine, NANUM_GOTHIC_REGULAR

    if not os.path.exists(hwpx_path):
        raise FileNotFoundError(f"HWPX file not found: {hwpx_path}")

    try:
        import cairosvg
    except ImportError as e:
        raise ImportError("render_pages_to_png requires cairosvg. Install with: pip install cairosvg") from e

    if register_fonts:
        _register_bundled_fonts()

    if out_dir is None:
        out_dir = os.getcwd()
    os.makedirs(out_dir, exist_ok=True)

    font_map = {
        "함초롬바탕": NANUM_GOTHIC_REGULAR,
        "함초롬돋움": NANUM_GOTHIC_REGULAR,
        "휴먼명조": NANUM_GOTHIC_REGULAR,
        "바탕": NANUM_GOTHIC_REGULAR,
        "Batang": NANUM_GOTHIC_REGULAR,
        "NanumGothic": NANUM_GOTHIC_REGULAR,
        "나눔고딕": NANUM_GOTHIC_REGULAR,
        "serif": NANUM_GOTHIC_REGULAR,
        "sans-serif": NANUM_GOTHIC_REGULAR,
    }

    engine = RhwpEngine(font_map=font_map)
    doc = engine.load(hwpx_path)
    page_count = doc.page_count
    stem = os.path.splitext(os.path.basename(hwpx_path))[0]

    # 1. Parallel SVG rendering
    svgs = doc.render_all_svgs_parallel(embed_fonts=False, max_workers=max_workers)
    output_paths = [os.path.join(out_dir, f"{stem}_p{i}.png") for i in range(page_count)]

    # 2. Parallel SVG to PNG conversion
    def _to_png(idx):
        svg_fixed = _re.sub(r'font-family="[^"]*"', f'font-family="{font_name}"', svgs[idx])
        cairosvg.svg2png(
            bytestring=svg_fixed.encode("utf-8"),
            write_to=output_paths[idx],
            scale=scale,
            unsafe=True,
        )
        return output_paths[idx]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(_to_png, range(page_count)))

    doc.close()
    return output_paths
