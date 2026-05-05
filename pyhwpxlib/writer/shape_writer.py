"""Direct XML writers for table and shape elements.

These functions build XML strings that exactly match the reference patterns
extracted from ratiertm-hwpx. They are independent of the object model --
they take simple Python parameters and return XML strings.
"""
from __future__ import annotations

from typing import List, Optional, Tuple


def _id() -> str:
    """Generate a random element ID."""
    import random
    return str(random.randint(1000000000, 4294967295))


def _escape(text: str) -> str:
    """Escape XML special characters in text content."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


# ======================================================================
# Common sub-element builders
# ======================================================================

def _sz_xml(width: int, height: int) -> str:
    return (
        f'<hp:sz width="{width}" widthRelTo="ABSOLUTE"'
        f' height="{height}" heightRelTo="ABSOLUTE" protect="0"/>'
    )


def _pos_xml() -> str:
    return (
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1"'
        ' allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA"'
        ' horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT"'
        ' vertOffset="0" horzOffset="0"/>'
    )


def _out_margin_xml() -> str:
    return '<hp:outMargin left="0" right="0" top="0" bottom="0"/>'


def _in_margin_xml() -> str:
    return '<hp:inMargin left="0" right="0" top="0" bottom="0"/>'


def _rendering_info_xml() -> str:
    return (
        '<hp:renderingInfo>'
        '<hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
        '<hc:scaMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
        '<hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
        '</hp:renderingInfo>'
    )


def _line_shape_xml(
    color: str,
    width: int,
    head_style: str = "NORMAL",
    tail_style: str = "NORMAL",
) -> str:
    return (
        f'<hp:lineShape color="{color}" width="{width}" style="SOLID"'
        f' endCap="FLAT" headStyle="{head_style}" tailStyle="{tail_style}"'
        ' headfill="1" tailfill="1" headSz="SMALL_SMALL" tailSz="SMALL_SMALL"'
        ' outlineStyle="NORMAL" alpha="0"/>'
    )


def _fill_brush_xml(fill_color: Optional[str]) -> str:
    if fill_color is None:
        return ''
    return (
        '<hc:fillBrush>'
        f'<hc:winBrush faceColor="{fill_color}" hatchColor="#FFFFFF" alpha="0"/>'
        '</hc:fillBrush>'
    )


def _shadow_xml(shadow_type: str = "NONE") -> str:
    if shadow_type == "NONE":
        return '<hp:shadow type="NONE" color="#B2B2B2" offsetX="0" offsetY="0" alpha="0"/>'
    return (
        f'<hp:shadow type="{shadow_type}" color="#B2B2B2"'
        f' offsetX="283" offsetY="283" alpha="0"/>'
    )


def _draw_text_xml(text: str, width: int) -> str:
    """Build drawText XML to place text inside a shape."""
    p_id = _id()
    escaped = _escape(text)
    return (
        f'<hp:drawText lastWidth="{width}" name="" editable="0">'
        '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK"'
        ' vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0"'
        ' textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
        f'<hp:p id="{p_id}" paraPrIDRef="0" styleIDRef="0" pageBreak="0"'
        ' columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="0"><hp:t>{escaped}</hp:t></hp:run>'
        '</hp:p>'
        '</hp:subList>'
        '<hp:textMargin left="283" right="283" top="283" bottom="283"/>'
        '</hp:drawText>'
    )


def _caption_xml(text: str, width: int) -> str:
    """Build caption XML to attach a caption to a shape."""
    p_id = _id()
    escaped = _escape(text)
    return (
        f'<hp:caption side="BOTTOM" fullSz="0" width="{width}" gap="850"'
        f' lastWidth="{width}">'
        '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK"'
        ' vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0"'
        ' textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
        f'<hp:p id="{p_id}" paraPrIDRef="0" styleIDRef="0" pageBreak="0"'
        ' columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="0"><hp:t>{escaped}</hp:t></hp:run>'
        '</hp:p>'
        '</hp:subList>'
        '</hp:caption>'
    )


def _shape_common_attrs(eid: str, extra: str = "") -> str:
    """Common attributes for drawing objects (rect, ellipse, line)."""
    return (
        f'{extra}id="{eid}" zOrder="0" numberingType="NONE" lock="0"'
        f' dropcapstyle="None" href="" groupLevel="0" instid="{eid}"'
    )


def _shape_header_xml(width: int, height: int) -> str:
    """offset, orgSz, curSz, flip, rotationInfo, renderingInfo."""
    cx = width // 2
    cy = height // 2
    return (
        '<hp:offset x="0" y="0"/>'
        f'<hp:orgSz width="{width}" height="{height}"/>'
        f'<hp:curSz width="{width}" height="{height}"/>'
        '<hp:flip horizontal="0" vertical="0"/>'
        f'<hp:rotationInfo angle="0" centerX="{cx}" centerY="{cy}" rotateimage="1"/>'
        + _rendering_info_xml()
    )


# ======================================================================
# TABLE
# ======================================================================

def build_table_xml(
    rows: int,
    cols: int,
    data: Optional[List[List[str]]] = None,
    width: int = 42520,
    border_fill_id: str = "3",
    merge_info: Optional[List[Tuple[int, int, int, int]]] = None,
    cell_colors: Optional[dict] = None,
    cell_border_fill_ids: Optional[dict] = None,
    col_widths: Optional[List[int]] = None,
    row_heights: Optional[List[int]] = None,
    cell_margin: Optional[Tuple[int, int, int, int]] = None,
    cell_para_pr_ids: Optional[dict] = None,
    cell_char_pr_ids: Optional[dict] = None,
    *,
    page_break: str = "CELL",
    repeat_header: bool = False,
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:tbl>`` element.

    Parameters
    ----------
    merge_info : list of (start_row, start_col, end_row, end_col) tuples
        Cell merge regions. The anchor cell gets colSpan/rowSpan; covered
        cells are skipped entirely.
    cell_colors : dict mapping (row, col) to borderFillIDRef str
        Per-cell background color overrides. The caller must have already
        created the borderFill entries and pass the IDs here via
        *cell_border_fill_ids*.
    cell_border_fill_ids : dict mapping (row, col) to borderFillIDRef str
        Pre-resolved borderFill IDs per cell (created by api.py).
    page_break : "CELL" | "TABLE" | "NONE"
        Page-break policy when the table overflows the current page (v0.18.1+):
        ``"CELL"`` (default) — split between rows, continue on next page.
        ``"TABLE"`` — push the entire table to a new page if it doesn't fit.
        ``"NONE"`` — never split (overflow is clipped). Hancom UI: 표 속성 →
        "여러 쪽 지원".
    repeat_header : bool
        When True (v0.18.1+), the first row repeats at the top of every page
        the table spans. Hancom UI: 표 속성 → "제목 줄 반복". Set this only
        when row 0 is actually a header — otherwise duplicate data renders
        on every page.

    Returns raw XML to be stored in ``Para.raw_xml_content``.
    """
    if page_break not in ("CELL", "TABLE", "NONE"):
        raise ValueError(
            f"page_break must be 'CELL', 'TABLE', or 'NONE'; got {page_break!r}"
        )
    _repeat_header_attr = "1" if repeat_header else "0"
    # Column widths: use provided or distribute evenly
    if col_widths:
        _col_widths = col_widths
    else:
        _col_widths = [width // cols] * cols
    # Row heights: use provided or default
    if row_heights:
        _row_heights = row_heights
    else:
        _row_heights = [3600] * rows
    # Cell margin
    cm_l, cm_r, cm_t, cm_b = cell_margin if cell_margin else (0, 0, 0, 0)
    has_margin = "1" if cell_margin else "0"

    # Build merge lookup: which cells are covered vs anchor
    # anchor_spans: (r,c) -> (col_span, row_span)
    # covered: set of (r,c) that are hidden by a merge
    anchor_spans: dict[tuple[int, int], tuple[int, int]] = {}
    covered: set[tuple[int, int]] = set()
    if merge_info:
        for sr, sc, er, ec in merge_info:
            cs = ec - sc + 1
            rs = er - sr + 1
            anchor_spans[(sr, sc)] = (cs, rs)
            for mr in range(sr, er + 1):
                for mc in range(sc, ec + 1):
                    if (mr, mc) != (sr, sc):
                        covered.add((mr, mc))

    tbl_id = _id()
    parts: list[str] = []

    # <hp:run charPrIDRef="0">
    parts.append('<hp:run charPrIDRef="0">')

    # <hp:tbl ...>
    parts.append(
        f'<hp:tbl id="{tbl_id}" zOrder="0" numberingType="TABLE"'
        f' textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0"'
        f' dropcapstyle="None" pageBreak="{page_break}"'
        f' repeatHeader="{_repeat_header_attr}"'
        f' rowCnt="{rows}" colCnt="{cols}" cellSpacing="0"'
        f' borderFillIDRef="{border_fill_id}" noAdjust="0">'
    )

    # sz, pos, outMargin, inMargin
    total_height = sum(_row_heights)
    parts.append(_sz_xml(width, total_height))
    parts.append(_pos_xml())
    parts.append(_out_margin_xml())
    parts.append(_in_margin_xml())

    # rows
    for r in range(rows):
        parts.append('<hp:tr>')
        for c in range(cols):
            if (r, c) in covered:
                continue

            cell_text = ""
            if data and r < len(data) and c < len(data[r]):
                cell_text = data[r][c] or ""

            # Split on newlines to produce multiple <hp:p> elements
            lines = cell_text.split("\n")

            # Determine borderFillIDRef for this cell
            cell_bf = border_fill_id
            if cell_border_fill_ids and (r, c) in cell_border_fill_ids:
                cell_bf = cell_border_fill_ids[(r, c)]

            # Determine span
            col_span, row_span = anchor_spans.get((r, c), (1, 1))
            cell_w = sum(_col_widths[c:c+col_span])
            cell_h = sum(_row_heights[r:r+row_span])

            parts.append(
                f'<hp:tc name="" header="0" hasMargin="{has_margin}" protect="0"'
                f' editable="0" dirty="0" borderFillIDRef="{cell_bf}">'
            )
            parts.append(
                f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK"'
                f' vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0"'
                f' textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
            )
            # Per-cell paragraph style (for text alignment)
            cell_ppr = "0"
            if cell_para_pr_ids and (r, c) in cell_para_pr_ids:
                cell_ppr = cell_para_pr_ids[(r, c)]
            # Per-cell character style (for text color, bold, etc.)
            cell_cpr = "0"
            if cell_char_pr_ids and (r, c) in cell_char_pr_ids:
                cell_cpr = cell_char_pr_ids[(r, c)]

            for line in lines:
                escaped_line = (
                    line.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
                p_id = _id()
                parts.append(
                    f'<hp:p paraPrIDRef="{cell_ppr}" styleIDRef="0" pageBreak="0"'
                    f' columnBreak="0" merged="0" id="{p_id}">'
                )
                parts.append(
                    f'<hp:run charPrIDRef="{cell_cpr}"><hp:t>{escaped_line}</hp:t></hp:run>'
                )
                parts.append('</hp:p>')
            parts.append('</hp:subList>')
            parts.append(f'<hp:cellAddr colAddr="{c}" rowAddr="{r}"/>')
            parts.append(f'<hp:cellSpan colSpan="{col_span}" rowSpan="{row_span}"/>')
            parts.append(f'<hp:cellSz width="{cell_w}" height="{cell_h}"/>')
            parts.append(f'<hp:cellMargin left="{cm_l}" right="{cm_r}" top="{cm_t}" bottom="{cm_b}"/>')
            parts.append('</hp:tc>')
        parts.append('</hp:tr>')

    parts.append('</hp:tbl>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# RECTANGLE
# ======================================================================

def build_rectangle_xml(
    width: int = 14400,
    height: int = 7200,
    line_color: str = "#000000",
    line_width: int = 283,
    fill_color: Optional[str] = None,
    text: Optional[str] = None,
    caption: Optional[str] = None,
    shadow_type: str = "NONE",
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:rect>`` element."""
    eid = _id()
    parts: list[str] = []

    parts.append('<hp:run charPrIDRef="0">')
    parts.append(
        f'<hp:rect ratio="0" {_shape_common_attrs(eid)}>'
    )
    parts.append(_shape_header_xml(width, height))
    parts.append(_line_shape_xml(line_color, line_width))
    parts.append(_fill_brush_xml(fill_color))
    parts.append(_shadow_xml(shadow_type))

    # pt0-pt3 (corner points)
    parts.append(f'<hc:pt0 x="0" y="0"/>')
    parts.append(f'<hc:pt1 x="{width}" y="0"/>')
    parts.append(f'<hc:pt2 x="{width}" y="{height}"/>')
    parts.append(f'<hc:pt3 x="0" y="{height}"/>')

    # drawText (text inside shape)
    if text is not None:
        parts.append(_draw_text_xml(text, width))

    # caption
    if caption is not None:
        parts.append(_caption_xml(caption, width))

    # sz, pos, outMargin at the END
    parts.append(_sz_xml(width, height))
    parts.append(_pos_xml())
    parts.append(_out_margin_xml())

    parts.append('</hp:rect>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# ELLIPSE
# ======================================================================

def build_ellipse_xml(
    width: int = 10000,
    height: int = 8000,
    line_color: str = "#000000",
    line_width: int = 283,
    fill_color: Optional[str] = None,
    text: Optional[str] = None,
    caption: Optional[str] = None,
    shadow_type: str = "NONE",
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:ellipse>`` element."""
    eid = _id()
    cx = width // 2
    cy = height // 2
    parts: list[str] = []

    parts.append('<hp:run charPrIDRef="0">')
    parts.append(
        f'<hp:ellipse intervalDirty="0" hasArcPr="0" arcType="NORMAL"'
        f' {_shape_common_attrs(eid)}>'
    )
    parts.append(_shape_header_xml(width, height))
    parts.append(_line_shape_xml(line_color, line_width))
    parts.append(_fill_brush_xml(fill_color))
    parts.append(_shadow_xml(shadow_type))

    # Ellipse geometry
    parts.append(f'<hc:center x="{cx}" y="{cy}"/>')
    parts.append(f'<hc:ax1 x="{width}" y="{cy}"/>')
    parts.append(f'<hc:ax2 x="{cx}" y="{height}"/>')
    parts.append(f'<hc:start1 x="{width}" y="{cy}"/>')
    parts.append(f'<hc:end1 x="{width}" y="{cy}"/>')
    parts.append(f'<hc:start2 x="{width}" y="{cy}"/>')
    parts.append(f'<hc:end2 x="{width}" y="{cy}"/>')

    # drawText (text inside shape)
    if text is not None:
        parts.append(_draw_text_xml(text, width))

    # caption
    if caption is not None:
        parts.append(_caption_xml(caption, width))

    # sz, pos, outMargin at the END
    parts.append(_sz_xml(width, height))
    parts.append(_pos_xml())
    parts.append(_out_margin_xml())

    parts.append('</hp:ellipse>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# LINE
# ======================================================================

def build_line_xml(
    x1: int = 0,
    y1: int = 0,
    x2: int = 20000,
    y2: int = 0,
    line_color: str = "#000000",
    line_width: int = 283,
    head_style: str = "NORMAL",
    tail_style: str = "NORMAL",
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:line>`` element."""
    eid = _id()
    # Line dimensions: width = dx, height = dy
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    cx = w // 2
    cy = h // 2

    # Determine if reversed
    is_reverse = "0"

    parts: list[str] = []

    parts.append('<hp:run charPrIDRef="0">')
    parts.append(
        f'<hp:line isReverseHV="{is_reverse}"'
        f' {_shape_common_attrs(eid)}>'
    )
    parts.append(_shape_header_xml(w, h))
    parts.append(_line_shape_xml(line_color, line_width, head_style, tail_style))
    parts.append(_shadow_xml())

    # Start and end points
    parts.append(f'<hc:startPt x="{x1}" y="{y1}"/>')
    parts.append(f'<hc:endPt x="{x2}" y="{y2}"/>')

    # sz, pos, outMargin at the END
    parts.append(_sz_xml(w, h))
    parts.append(_pos_xml())
    parts.append(_out_margin_xml())

    parts.append('</hp:line>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# ARC (ellipse with arc properties)
# ======================================================================

def build_arc_xml(
    center_x: int,
    center_y: int,
    ax1_x: int,
    ax1_y: int,
    ax2_x: int,
    ax2_y: int,
    arc_type: str = "NORMAL",
    line_color: str = "#000000",
    line_width: int = 283,
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:ellipse>`` with arc properties.

    Arc types: ``NORMAL``, ``PIE``, ``CHORD``.
    """
    eid = _id()
    # Bounding box from center and axes
    width = max(abs(ax1_x - center_x), abs(ax2_x - center_x)) * 2
    height = max(abs(ax1_y - center_y), abs(ax2_y - center_y)) * 2
    if width == 0:
        width = abs(ax1_x - center_x) * 2 or abs(ax2_x - center_x) * 2 or 10000
    if height == 0:
        height = abs(ax1_y - center_y) * 2 or abs(ax2_y - center_y) * 2 or 10000

    parts: list[str] = []

    parts.append('<hp:run charPrIDRef="0">')
    parts.append(
        f'<hp:ellipse intervalDirty="0" hasArcPr="1" arcType="{arc_type}"'
        f' {_shape_common_attrs(eid)}>'
    )
    parts.append(_shape_header_xml(width, height))
    parts.append(_line_shape_xml(line_color, line_width))
    parts.append(_fill_brush_xml(None))
    parts.append(_shadow_xml())

    # Ellipse geometry with arc endpoints
    parts.append(f'<hc:center x="{center_x}" y="{center_y}"/>')
    parts.append(f'<hc:ax1 x="{ax1_x}" y="{ax1_y}"/>')
    parts.append(f'<hc:ax2 x="{ax2_x}" y="{ax2_y}"/>')
    parts.append(f'<hc:start1 x="{ax1_x}" y="{ax1_y}"/>')
    parts.append(f'<hc:end1 x="{ax2_x}" y="{ax2_y}"/>')
    parts.append(f'<hc:start2 x="{ax1_x}" y="{ax1_y}"/>')
    parts.append(f'<hc:end2 x="{ax2_x}" y="{ax2_y}"/>')

    # sz, pos, outMargin at the END
    parts.append(_sz_xml(width, height))
    parts.append(_pos_xml())
    parts.append(_out_margin_xml())

    parts.append('</hp:ellipse>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# POLYGON
# ======================================================================

def build_polygon_xml(
    points: List[Tuple[int, int]],
    line_color: str = "#000000",
    line_width: int = 283,
    fill_color: Optional[str] = None,
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:polygon>`` element.

    *points* is a list of ``(x, y)`` tuples defining the polygon vertices.
    """
    eid = _id()
    # Compute bounding box
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max_x - min_x or 1
    height = max_y - min_y or 1

    parts: list[str] = []

    parts.append('<hp:run charPrIDRef="0">')
    parts.append(
        f'<hp:polygon {_shape_common_attrs(eid)}>'
    )
    parts.append(_shape_header_xml(width, height))
    parts.append(_line_shape_xml(line_color, line_width))
    parts.append(_fill_brush_xml(fill_color))
    parts.append(_shadow_xml())

    # Polygon points
    for x, y in points:
        parts.append(f'<hc:pt x="{x}" y="{y}"/>')

    # sz, pos, outMargin at the END
    parts.append(_sz_xml(width, height))
    parts.append(_pos_xml())
    parts.append(_out_margin_xml())

    parts.append('</hp:polygon>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# CURVE (bezier)
# ======================================================================

def build_curve_xml(
    segments: List[dict],
    line_color: str = "#000000",
    line_width: int = 283,
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:curve>`` element.

    Each segment dict has keys: ``type`` (``"LINE"`` or ``"CURVE"``),
    ``x1``, ``y1``, ``x2``, ``y2``.
    """
    eid = _id()
    # Compute bounding box from all segment coordinates
    all_x: list[int] = []
    all_y: list[int] = []
    for seg in segments:
        all_x.extend([seg["x1"], seg["x2"]])
        all_y.extend([seg["y1"], seg["y2"]])
    width = (max(all_x) - min(all_x)) or 1
    height = (max(all_y) - min(all_y)) or 1

    parts: list[str] = []

    parts.append('<hp:run charPrIDRef="0">')
    parts.append(
        f'<hp:curve {_shape_common_attrs(eid)}>'
    )
    parts.append(_shape_header_xml(width, height))
    parts.append(_line_shape_xml(line_color, line_width))
    parts.append(_shadow_xml())

    # Curve segments
    for seg in segments:
        parts.append(
            f'<hp:seg type="{seg["type"]}"'
            f' x1="{seg["x1"]}" y1="{seg["y1"]}"'
            f' x2="{seg["x2"]}" y2="{seg["y2"]}"/>'
        )

    # sz, pos, outMargin at the END
    parts.append(_sz_xml(width, height))
    parts.append(_pos_xml())
    parts.append(_out_margin_xml())

    parts.append('</hp:curve>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# CONNECT LINE
# ======================================================================

def build_connect_line_xml(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    line_color: str = "#000000",
    line_width: int = 283,
    connect_type: str = "STROKE_NOARROW",
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:connectLine>`` element.

    *connect_type*: ``STROKE_NOARROW``, ``STROKE_ARROW``, etc.
    """
    eid = _id()
    w = abs(end_x - start_x) or 1
    h = abs(end_y - start_y) or 1
    # Control point at midpoint
    ctrl_x = (start_x + end_x) // 2
    ctrl_y = (start_y + end_y) // 2

    parts: list[str] = []

    parts.append('<hp:run charPrIDRef="0">')
    parts.append(
        f'<hp:connectLine type="{connect_type}"'
        f' {_shape_common_attrs(eid)}>'
    )
    parts.append(_shape_header_xml(w, h))
    parts.append(_line_shape_xml(line_color, line_width))
    parts.append(_shadow_xml())

    # Start, end, control points
    parts.append(f'<hc:startPt x="{start_x}" y="{start_y}"/>')
    parts.append(f'<hc:endPt x="{end_x}" y="{end_y}"/>')
    parts.append(f'<hc:controlPt x="{ctrl_x}" y="{ctrl_y}"/>')

    # sz, pos, outMargin at the END
    parts.append(_sz_xml(w, h))
    parts.append(_pos_xml())
    parts.append(_out_margin_xml())

    parts.append('</hp:connectLine>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# BULLET PARAGRAPH
# ======================================================================

def build_bullet_paragraph_xml(
    text: str,
    bullet_char: str = "\u25cf",
    char_pr_id_ref: str = "0",
) -> str:
    """Build a ``<hp:run>`` for a single bullet item.

    The bullet character is prepended to the text as ``"● text"``.
    Returns raw XML to be stored in ``Para.raw_xml_content``.
    """
    display = f"{bullet_char} {_escape(text)}"
    return (
        f'<hp:run charPrIDRef="{char_pr_id_ref}">'
        f'<hp:t>{display}</hp:t>'
        f'</hp:run>'
    )


# ======================================================================
# NUMBERED PARAGRAPH
# ======================================================================

def build_numbered_paragraph_xml(
    text: str,
    number: int,
    format_string: str = "{n}. ",
    char_pr_id_ref: str = "0",
) -> str:
    """Build a ``<hp:run>`` for a single numbered list item.

    *format_string* should contain ``{n}`` which will be replaced with
    the item number.  Returns raw XML for ``Para.raw_xml_content``.
    """
    prefix = format_string.replace("{n}", str(number))
    display = f"{prefix}{_escape(text)}"
    return (
        f'<hp:run charPrIDRef="{char_pr_id_ref}">'
        f'<hp:t>{display}</hp:t>'
        f'</hp:run>'
    )


# ======================================================================
# HYPERLINK
# ======================================================================

def _escape_hyperlink_command(url: str) -> str:
    """Escape URL for the hyperlink Command parameter.

    Colons are escaped as ``\\:`` and ``;1;0;0;`` is appended.
    """
    return url.replace(":", "\\:") + ";1;0;0;"


def build_hyperlink_xml(
    text: str,
    url: str,
    char_pr_id_ref: str = "0",
) -> str:
    """Build three ``<hp:run>`` elements for a hyperlink.

    Uses the RULEBOOK 6-param structure required by Whale/Hancom Office:
      - Prop (integer): 0
      - Command (string): URL with escaped colons + ;1;0;0;
      - Path (string): original URL
      - Category: HWPHYPERLINK_TYPE_URL
      - TargetType: HWPHYPERLINK_TARGET_BOOKMARK
      - DocOpenType: HWPHYPERLINK_JUMP_CURRENTTAB

    Returns raw XML for ``Para.raw_xml_content``.
    """
    field_id = _id()
    field_id2 = _id()
    escaped_url = _escape(url)
    escaped_text = _escape(text)
    command_val = _escape(_escape_hyperlink_command(url))

    parts: list[str] = []

    # Run 1: fieldBegin with 6 parameters
    parts.append(f'<hp:run charPrIDRef="{char_pr_id_ref}">')
    parts.append('<hp:ctrl>')
    parts.append(
        f'<hp:fieldBegin id="{field_id}" type="HYPERLINK"'
        f' name="" editable="0" dirty="0" zorder="-1" fieldid="{field_id2}">'
    )
    parts.append('<hp:parameters cnt="6" name="">')
    parts.append('<hp:integerParam name="Prop">0</hp:integerParam>')
    parts.append(f'<hp:stringParam name="Command">{command_val}</hp:stringParam>')
    parts.append(f'<hp:stringParam name="Path">{escaped_url}</hp:stringParam>')
    parts.append('<hp:stringParam name="Category">HWPHYPERLINK_TYPE_URL</hp:stringParam>')
    parts.append('<hp:stringParam name="TargetType">HWPHYPERLINK_TARGET_BOOKMARK</hp:stringParam>')
    parts.append('<hp:stringParam name="DocOpenType">HWPHYPERLINK_JUMP_CURRENTTAB</hp:stringParam>')
    parts.append('</hp:parameters>')
    parts.append('</hp:fieldBegin>')
    parts.append('</hp:ctrl>')
    parts.append('</hp:run>')

    # Run 2: visible text
    parts.append(f'<hp:run charPrIDRef="{char_pr_id_ref}">')
    parts.append(f'<hp:t>{escaped_text}</hp:t>')
    parts.append('</hp:run>')

    # Run 3: fieldEnd
    parts.append(f'<hp:run charPrIDRef="{char_pr_id_ref}">')
    parts.append('<hp:ctrl>')
    parts.append(f'<hp:fieldEnd beginIDRef="{field_id}"/>')
    parts.append('</hp:ctrl>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# EQUATION
# ======================================================================

def build_equation_xml(
    script: str,
    width: int = 3750,
    height: int = 3375,
    base_unit: int = 1000,
    base_line: int = 61,
    font: str = "HancomEQN",
) -> str:
    """Build a ``<hp:run>`` containing an ``<hp:equation>`` element.

    The equation *script* uses Hancom equation syntax (e.g. ``x^2 + y^2 = r^2``).
    Returns raw XML for ``Para.raw_xml_content``.
    """
    eid = _id()
    escaped_script = _escape(script)

    parts: list[str] = []
    parts.append('<hp:run charPrIDRef="0">')
    parts.append(
        f'<hp:equation id="{eid}" zOrder="0" numberingType="EQUATION"'
        f' textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES"'
        f' lock="0" dropcapstyle="None"'
        f' version="Equation Version 60"'
        f' baseLine="{base_line}" textColor="#000000"'
        f' baseUnit="{base_unit}" lineMode="CHAR" font="{font}">'
    )

    # sz, pos, outMargin
    parts.append(
        f'<hp:sz width="{width}" widthRelTo="ABSOLUTE"'
        f' height="{height}" heightRelTo="ABSOLUTE" protect="0"/>'
    )
    parts.append(
        '<hp:pos treatAsChar="1" affectLSpacing="0"'
        ' flowWithText="1" allowOverlap="0" holdAnchorAndSO="0"'
        ' vertRelTo="PARA" horzRelTo="PARA"'
        ' vertAlign="TOP" horzAlign="LEFT"'
        ' vertOffset="0" horzOffset="0"/>'
    )
    parts.append('<hp:outMargin left="56" right="56" top="0" bottom="0"/>')

    # shapeComment and script
    parts.append('<hp:shapeComment>\uc218\uc2dd\uc785\ub2c8\ub2e4.</hp:shapeComment>')
    parts.append(f'<hp:script>{escaped_script}</hp:script>')

    parts.append('</hp:equation>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# IMAGE (hp:pic)
# ======================================================================

def build_image_xml(
    binary_item_id: str,
    width: int,
    height: int,
    org_width: int,
    org_height: int,
) -> str:
    """Build a ``<hp:run>`` containing an ``<hp:pic>`` element.

    *binary_item_id* is the manifest item id (e.g. ``"image1"``) that
    references the embedded image in the HWPX ZIP ``BinData/`` folder.

    *width* / *height* are display dimensions in hwpunit.
    *org_width* / *org_height* are the original image dimensions in hwpunit.

    Returns raw XML for ``Para.raw_xml_content``.
    """
    pic_id = _id()
    inst_id = _id()
    cx = width // 2
    cy = height // 2

    # Compute scale matrix values
    sx = f"{width / org_width:.6f}" if org_width > 0 else "1"
    sy = f"{height / org_height:.6f}" if org_height > 0 else "1"

    parts: list[str] = []
    parts.append('<hp:run charPrIDRef="0">')

    # <hp:pic> opening
    parts.append(
        f'<hp:pic id="{pic_id}" zOrder="0" numberingType="PICTURE"'
        f' textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES"'
        f' lock="0" dropcapstyle="None" href=""'
        f' groupLevel="0" instid="{inst_id}" reverse="0">'
    )

    # AbstractShapeComponentType children (FIRST)
    parts.append(f'<hp:offset x="0" y="0"/>')
    parts.append(f'<hp:orgSz width="{org_width}" height="{org_height}"/>')
    parts.append(f'<hp:curSz width="{width}" height="{height}"/>')
    parts.append('<hp:flip horizontal="0" vertical="0"/>')
    parts.append(
        f'<hp:rotationInfo angle="0" centerX="{cx}" centerY="{cy}" rotateimage="1"/>'
    )

    # renderingInfo
    parts.append('<hp:renderingInfo>')
    parts.append('<hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>')
    parts.append(f'<hc:scaMatrix e1="{sx}" e2="0" e3="0" e4="0" e5="{sy}" e6="0"/>')
    parts.append('<hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>')
    parts.append('</hp:renderingInfo>')

    # PictureType children
    # imgRect
    parts.append('<hp:imgRect>')
    parts.append(f'<hc:pt0 x="0" y="0"/>')
    parts.append(f'<hc:pt1 x="{org_width}" y="0"/>')
    parts.append(f'<hc:pt2 x="{org_width}" y="{org_height}"/>')
    parts.append(f'<hc:pt3 x="0" y="{org_height}"/>')
    parts.append('</hp:imgRect>')

    # imgClip, inMargin, imgDim
    parts.append('<hp:imgClip left="0" top="0" right="0" bottom="0"/>')
    parts.append('<hp:inMargin left="0" right="0" top="0" bottom="0"/>')
    parts.append(f'<hp:imgDim dimwidth="{org_width}" dimheight="{org_height}"/>')

    # hc:img referencing the binary item
    parts.append(
        f'<hc:img binaryItemIDRef="{binary_item_id}"'
        f' bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>'
    )

    # AbstractShapeObjectType children (LAST)
    parts.append(
        f'<hp:sz width="{width}" height="{height}"'
        f' widthRelTo="ABSOLUTE" heightRelTo="ABSOLUTE" protect="0"/>'
    )
    parts.append(
        '<hp:pos treatAsChar="1" affectLSpacing="0"'
        ' flowWithText="1" allowOverlap="1" holdAnchorAndSO="0"'
        ' vertRelTo="PARA" horzRelTo="PARA"'
        ' vertAlign="TOP" horzAlign="LEFT"'
        ' vertOffset="0" horzOffset="0"/>'
    )
    parts.append('<hp:outMargin left="0" right="0" top="0" bottom="0"/>')

    parts.append('</hp:pic>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# HEADER / FOOTER (section header/footer ctrl)
# ======================================================================

def _build_header_footer_sublist_xml(
    text: str,
    char_pr_id_ref: str = "0",
    vert_align: str = "TOP",
    text_width: int = 42520,
    text_height: int = 4252,
) -> str:
    """Build the inner subList XML for header or footer text."""
    p_id = _id()
    escaped_text = _escape(text)
    return (
        f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK"'
        f' vertAlign="{vert_align}" linkListIDRef="0" linkListNextIDRef="0"'
        f' textWidth="{text_width}" textHeight="{text_height}"'
        f' hasTextRef="0" hasNumRef="0">'
        f'<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0"'
        f' columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_pr_id_ref}">'
        f'<hp:t>{escaped_text}</hp:t>'
        f'</hp:run>'
        f'</hp:p>'
        f'</hp:subList>'
    )


def build_header_xml(
    text: str,
    char_pr_id_ref: str = "0",
) -> str:
    """Build a ``<hp:run>`` containing a header ctrl element.

    Produces the correct OWPML structure where the header is wrapped in
    ``<hp:ctrl><hp:header>`` with a subList containing the header text.
    The header element has ``applyPageType="BOTH"`` and ``vertAlign="TOP"``.

    Returns raw XML for ``Para.raw_xml_content``.
    """
    header_id = _id()
    parts: list[str] = []
    parts.append(f'<hp:run charPrIDRef="{char_pr_id_ref}">')
    parts.append('<hp:ctrl>')
    parts.append(
        f'<hp:header id="{header_id}" applyPageType="BOTH">'
    )
    parts.append(_build_header_footer_sublist_xml(
        text, char_pr_id_ref, vert_align="TOP",
    ))
    parts.append('</hp:header>')
    parts.append('</hp:ctrl>')
    parts.append('</hp:run>')
    return "".join(parts)


def build_footer_xml(
    text: str,
    char_pr_id_ref: str = "0",
) -> str:
    """Build a ``<hp:run>`` containing a footer ctrl element.

    Produces the correct OWPML structure where the footer is wrapped in
    ``<hp:ctrl><hp:footer>`` with a subList containing the footer text.
    The footer element has ``applyPageType="BOTH"`` and ``vertAlign="BOTTOM"``.

    Returns raw XML for ``Para.raw_xml_content``.
    """
    footer_id = _id()
    parts: list[str] = []
    parts.append(f'<hp:run charPrIDRef="{char_pr_id_ref}">')
    parts.append('<hp:ctrl>')
    parts.append(
        f'<hp:footer id="{footer_id}" applyPageType="BOTH">'
    )
    parts.append(_build_header_footer_sublist_xml(
        text, char_pr_id_ref, vert_align="BOTTOM",
    ))
    parts.append('</hp:footer>')
    parts.append('</hp:ctrl>')
    parts.append('</hp:run>')
    return "".join(parts)


# ======================================================================
# PAGE NUMBER
# ======================================================================

def build_page_number_xml(
    pos: str = "BOTTOM_CENTER",
    format_type: str = "DIGIT",
    side_char: str = "-",
    char_pr_id_ref: str = "0",
) -> str:
    """Build a ``<hp:run>`` containing a page number ctrl element.

    *pos* values: ``BOTTOM_CENTER``, ``BOTTOM_LEFT``, ``BOTTOM_RIGHT``,
    ``TOP_CENTER``, ``TOP_LEFT``, ``TOP_RIGHT``.
    *format_type* values: ``DIGIT``, ``CIRCLE``, ``ROMAN_CAPITAL``,
    ``ROMAN_SMALL``, ``LATIN_CAPITAL``, ``LATIN_SMALL``.

    Returns raw XML for ``Para.raw_xml_content``.
    """
    parts: list[str] = []
    parts.append(f'<hp:run charPrIDRef="{char_pr_id_ref}">')
    parts.append('<hp:ctrl>')
    parts.append(
        f'<hp:pageNum pos="{pos}" formatType="{format_type}"'
        f' sideChar="{_escape(side_char)}"/>'
    )
    parts.append('</hp:ctrl>')
    parts.append('</hp:run>')
    return "".join(parts)


# ======================================================================
# FOOTNOTE
# ======================================================================

def build_footnote_xml(
    text: str,
    number: int = 1,
    char_pr_id_ref: str = "0",
) -> str:
    """Build a ``<hp:run>`` containing a footNote ctrl element.

    Produces the correct OWPML structure:
    ``<hp:run><hp:ctrl><hp:footNote>`` with a subList that contains the
    footnote text preceded by an autoNum control for numbering.

    *number* is the footnote sequence number (1-based).

    Returns raw XML to be **appended** to an existing paragraph's
    ``raw_xml_content`` (the anchor paragraph).
    """
    inst_id = _id()
    escaped_text = _escape(text)
    suffix_char = str(40 + number)  # ASCII code for closing paren area

    parts: list[str] = []
    parts.append(f'<hp:run charPrIDRef="{char_pr_id_ref}">')
    parts.append('<hp:ctrl>')
    parts.append(
        f'<hp:footNote number="{number}" suffixChar="{suffix_char}"'
        f' instId="{inst_id}">'
    )
    parts.append(
        '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK"'
        ' vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0"'
        ' textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
    )
    parts.append(
        '<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0"'
        ' columnBreak="0" merged="0">'
    )
    # autoNum run
    parts.append('<hp:run charPrIDRef="0">')
    parts.append('<hp:ctrl>')
    parts.append(
        f'<hp:autoNum num="{number}" numType="FOOTNOTE">'
        f'<hp:autoNumFormat type="DIGIT" userChar="" prefixChar=""'
        f' suffixChar=")" supscript="0"/>'
        f'</hp:autoNum>'
    )
    parts.append('</hp:ctrl>')
    parts.append('</hp:run>')
    # text run
    parts.append(f'<hp:run charPrIDRef="{char_pr_id_ref}">')
    parts.append(f'<hp:t> {escaped_text}</hp:t>')
    parts.append('</hp:run>')
    parts.append('</hp:p>')
    parts.append('</hp:subList>')
    parts.append('</hp:footNote>')
    parts.append('</hp:ctrl>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# BOOKMARK
# ======================================================================

def build_bookmark_xml(
    name: str,
    char_pr_id_ref: str = "0",
) -> str:
    """Build ``<hp:run>`` elements for a bookmark.

    A bookmark is a pair of ``fieldBegin`` / ``fieldEnd`` with type
    ``BOOKMARK``.  It marks a position in the document that can be
    referenced by hyperlinks.

    Returns raw XML for ``Para.raw_xml_content``.
    """
    field_id = _id()
    escaped_name = _escape(name)

    parts: list[str] = []

    # Run 1: fieldBegin
    parts.append(f'<hp:run charPrIDRef="{char_pr_id_ref}">')
    parts.append('<hp:ctrl>')
    parts.append(
        f'<hp:fieldBegin id="{field_id}" type="BOOKMARK"'
        f' name="{escaped_name}" editable="0" dirty="0"/>'
    )
    parts.append('</hp:ctrl>')
    parts.append('</hp:run>')

    # Run 2: fieldEnd
    parts.append(f'<hp:run charPrIDRef="{char_pr_id_ref}">')
    parts.append('<hp:ctrl>')
    parts.append(f'<hp:fieldEnd beginIDRef="{field_id}"/>')
    parts.append('</hp:ctrl>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# CODE BLOCK (monospace paragraph)
# ======================================================================

def build_code_block_xml(
    code: str,
    language: Optional[str] = None,
    char_pr_id_ref: str = "0",
) -> str:
    """Build ``<hp:run>`` elements for a code block.

    Since dynamically adding charPr entries to the header is not supported,
    this renders code as a bordered paragraph with optional language prefix.
    Each line of the code becomes a separate ``<hp:run>`` with a line break
    between them.

    Returns raw XML for ``Para.raw_xml_content``.
    """
    prefix = f"[{_escape(language)}] " if language else ""
    lines = code.split("\n")

    parts: list[str] = []
    for i, line in enumerate(lines):
        escaped_line = _escape(line)
        if i == 0 and prefix:
            escaped_line = prefix + escaped_line
        parts.append(
            f'<hp:run charPrIDRef="{char_pr_id_ref}">'
            f'<hp:t>{escaped_line}</hp:t>'
            f'</hp:run>'
        )
        # Add line break between lines (not after the last one)
        if i < len(lines) - 1:
            parts.append(
                f'<hp:run charPrIDRef="{char_pr_id_ref}">'
                f'<hp:t>&#xA;</hp:t>'
                f'</hp:run>'
            )

    return "".join(parts)


# ======================================================================
# COLUMNS (colPr)
# ======================================================================

def build_columns_xml(
    col_count: int = 2,
    col_type: str = "NEWSPAPER",
    layout: str = "LEFT",
    same_gap: int = 1200,
    separator_type: Optional[str] = None,
    separator_width: str = "0.12 mm",
    separator_color: str = "#000000",
) -> str:
    """Build a complete ``<hp:run>`` containing a ``<hp:colPr>`` control.

    The colPr element sets column layout for the current section.
    It is wrapped in ``<hp:ctrl>`` inside ``<hp:run>``.

    Parameters
    ----------
    col_count : int
        Number of columns (1 to reset to single column).
    col_type : str
        Column type: ``"NEWSPAPER"``, ``"BALANCED_NEWSPAPER"``, ``"PARALLEL"``.
    layout : str
        Layout direction: ``"LEFT"``, ``"RIGHT"``.
    same_gap : int
        Gap between columns in HWPX units.
    separator_type : str or None
        Column separator line type (e.g. ``"SOLID"``). None = no separator.
    separator_width : str
        Separator line width (e.g. ``"0.12 mm"``).
    separator_color : str
        Separator line color (e.g. ``"#000000"``).

    Returns raw XML for ``Para.raw_xml_content``.
    """
    col_id = _id()
    same_sz = "true" if col_count > 1 else "false"

    parts: list[str] = []
    parts.append('<hp:run charPrIDRef="0">')
    parts.append('<hp:ctrl>')
    parts.append(
        f'<hp:colPr id="{col_id}" type="{col_type}" layout="{layout}"'
        f' colCount="{col_count}" sameSz="{same_sz}" sameGap="{same_gap}">'
    )

    if separator_type is not None and col_count > 1:
        parts.append(
            f'<hp:colLine type="{separator_type}"'
            f' width="{separator_width}" color="{separator_color}"/>'
        )

    parts.append('</hp:colPr>')
    parts.append('</hp:ctrl>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# TEXTART
# ======================================================================

def build_textart_xml(
    text: str,
    width: int = 14000,
    height: int = 7000,
    font_name: str = "\ud568\ucd08\ub86c\ubc14\ud0d5",
    font_style: str = "\uc9c4\ud558\uac8c",
    text_shape: str = "WAVE1",
    fill_color: str = "#0000FF",
    line_color: str = "#000000",
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:textart>`` element.

    *text_shape* values: ``"WAVE1"``, ``"WAVE2"``, ``"THIN_CURVE_DOWN1"``,
    ``"THIN_CURVE_UP1"``, ``"TRIANGLE_UP"``, etc.

    Returns raw XML for ``Para.raw_xml_content``.
    """
    eid = _id()
    cx = width // 2
    cy = height // 2
    escaped_text = _escape(text)

    parts: list[str] = []

    parts.append('<hp:run charPrIDRef="0">')
    parts.append(
        f'<hp:textart {_shape_common_attrs(eid)}'
        f' textWrap="SQUARE" textFlow="BOTH_SIDES"'
        f' text="{escaped_text}">'
    )
    parts.append(_shape_header_xml(width, height))
    parts.append(_line_shape_xml(line_color, 0))
    parts.append(
        '<hc:fillBrush>'
        f'<hc:winBrush faceColor="{fill_color}" hatchColor="#000000" alpha="0"/>'
        '</hc:fillBrush>'
    )
    parts.append(_shadow_xml())

    # Corner points
    parts.append(f'<hc:pt0 x="0" y="0"/>')
    parts.append(f'<hc:pt1 x="{width}" y="0"/>')
    parts.append(f'<hc:pt2 x="{width}" y="{height}"/>')
    parts.append(f'<hc:pt3 x="0" y="{height}"/>')

    # textartPr
    parts.append(
        f'<hp:textartPr fontName="{_escape(font_name)}"'
        f' fontStyle="{_escape(font_style)}" fontType="TTF"'
        f' textShape="{text_shape}" lineSpacing="120"'
        f' charSpacing="100" align="LEFT"/>'
    )

    # sz, pos, outMargin at the END
    parts.append(_sz_xml(width, height))
    parts.append(_pos_xml())
    parts.append(_out_margin_xml())

    parts.append('</hp:textart>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# GROUP CONTAINER
# ======================================================================

def build_container_xml(
    children_xml: List[str],
    width: int = 20000,
    height: int = 20000,
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:container>`` element.

    *children_xml* is a list of pre-built shape XML strings.  Each child
    is the **inner** content of a shape element (i.e. a complete
    ``<hp:rect ...>...</hp:rect>`` or ``<hp:ellipse ...>...</hp:ellipse>``
    without the outer ``<hp:run>`` wrapper).

    Returns raw XML for ``Para.raw_xml_content``.
    """
    eid = _id()

    parts: list[str] = []

    parts.append('<hp:run charPrIDRef="0">')
    parts.append(
        f'<hp:container {_shape_common_attrs(eid)}'
        f' textWrap="IN_FRONT_OF_TEXT" textFlow="BOTH_SIDES">'
    )
    parts.append(_shape_header_xml(width, height))
    parts.append(_rendering_info_xml())

    # Child shapes
    for child in children_xml:
        parts.append(child)

    # sz, pos, outMargin at the END
    parts.append(_sz_xml(width, height))
    parts.append(_pos_xml())
    parts.append(_out_margin_xml())

    parts.append('</hp:container>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# IMAGE FILL BRUSH (imgBrush)
# ======================================================================

def _img_fill_brush_xml(image_item_id: str, mode: str = "STRETCH") -> str:
    """Build ``<hc:fillBrush>`` with ``<hc:imgBrush>`` for image fills.

    *image_item_id* is the manifest item id (e.g. ``"image1"``).
    *mode*: ``"TILE"``, ``"CENTER"``, ``"FIT"``, ``"STRETCH"``.
    """
    return (
        '<hc:fillBrush>'
        f'<hc:imgBrush mode="{mode}">'
        f'<hc:img binaryItemIDRef="{image_item_id}"'
        f' bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>'
        '</hc:imgBrush>'
        '</hc:fillBrush>'
    )


def build_rectangle_with_image_fill_xml(
    image_item_id: str,
    width: int = 14400,
    height: int = 7200,
    mode: str = "STRETCH",
    line_color: str = "#000000",
    line_width: int = 283,
    text: Optional[str] = None,
) -> str:
    """Build a ``<hp:run>`` containing a ``<hp:rect>`` with image fill.

    *image_item_id* is the manifest item id for the fill image.
    *mode*: ``"TILE"``, ``"CENTER"``, ``"FIT"``, ``"STRETCH"``.

    Returns raw XML for ``Para.raw_xml_content``.
    """
    eid = _id()
    parts: list[str] = []

    parts.append('<hp:run charPrIDRef="0">')
    parts.append(
        f'<hp:rect ratio="0" {_shape_common_attrs(eid)}>'
    )
    parts.append(_shape_header_xml(width, height))
    parts.append(_line_shape_xml(line_color, line_width))
    parts.append(_img_fill_brush_xml(image_item_id, mode))
    parts.append(_shadow_xml())

    # pt0-pt3 (corner points)
    parts.append(f'<hc:pt0 x="0" y="0"/>')
    parts.append(f'<hc:pt1 x="{width}" y="0"/>')
    parts.append(f'<hc:pt2 x="{width}" y="{height}"/>')
    parts.append(f'<hc:pt3 x="0" y="{height}"/>')

    # drawText (text inside shape)
    if text is not None:
        parts.append(_draw_text_xml(text, width))

    # sz, pos, outMargin at the END
    parts.append(_sz_xml(width, height))
    parts.append(_pos_xml())
    parts.append(_out_margin_xml())

    parts.append('</hp:rect>')
    parts.append('</hp:run>')

    return "".join(parts)


# ======================================================================
# FORM CONTROLS  (Phase 4)
# ======================================================================

def _form_common_attrs(
    name: str,
    foreColor: str = "#000000",
    backColor: str = "#FFFFFF",
    groupName: str = "",
    tabStop: str = "1",
    editable: str = "1",
    tabOrder: str = "1",
    enabled: str = "1",
    borderTypeIDRef: str = "0",
    drawFrame: str = "1",
    printable: str = "1",
    command: str = "",
) -> str:
    return (
        f' name="{_escape(name)}" foreColor="{foreColor}" backColor="{backColor}"'
        f' groupName="{_escape(groupName)}" tabStop="{tabStop}" editable="{editable}"'
        f' tabOrder="{tabOrder}" enabled="{enabled}" borderTypeIDRef="{borderTypeIDRef}"'
        f' drawFrame="{drawFrame}" printable="{printable}" command="{_escape(command)}"'
    )


def _form_char_pr_xml() -> str:
    return '<hp:formCharPr charPrIDRef="0" followContext="0" autoSz="0" wordWrap="0"/>'


def _form_control_xml(
    tag: str,
    attrs: str,
    width: int,
    height: int,
    extra_children: str = "",
) -> str:
    """Wrap a form control element inside ``<hp:run>``."""
    return (
        '<hp:run charPrIDRef="0">'
        f'<hp:{tag}{attrs}>'
        f'{_form_char_pr_xml()}'
        f'{extra_children}'
        f'{_sz_xml(width, height)}'
        f'{_pos_xml()}'
        f'{_out_margin_xml()}'
        f'</hp:{tag}>'
        '</hp:run>'
    )


def build_checkbox_xml(
    caption: str = "체크박스",
    name: str = "CheckBox1",
    checked: bool = False,
    width: int = 9921,
    height: int = 1984,
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:checkBtn>`` element."""
    value = "CHECKED" if checked else "UNCHECKED"
    attrs = (
        f' caption="{_escape(caption)}" value="{value}"'
        f' radioGroupName="" triState="0" backStyle="OPAQUE"'
        f'{_form_common_attrs(name)}'
    )
    return _form_control_xml("checkBtn", attrs, width, height)


def build_radio_button_xml(
    caption: str = "라디오",
    name: str = "Radio1",
    group: str = "",
    checked: bool = False,
    width: int = 8504,
    height: int = 1984,
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:radioBtn>`` element."""
    value = "CHECKED" if checked else "UNCHECKED"
    attrs = (
        f' caption="{_escape(caption)}" value="{value}"'
        f' radioGroupName="{_escape(group)}" triState="0" backStyle="OPAQUE"'
        f'{_form_common_attrs(name, groupName=group)}'
    )
    return _form_control_xml("radioBtn", attrs, width, height)


def build_button_xml(
    caption: str = "버튼",
    name: str = "Button1",
    value: str = "",
    width: int = 7087,
    height: int = 1984,
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:btn>`` element."""
    attrs = (
        f' caption="{_escape(caption)}" value="{_escape(value)}"'
        f'{_form_common_attrs(name)}'
    )
    return _form_control_xml("btn", attrs, width, height)


def build_combobox_xml(
    name: str = "ComboBox1",
    items: list[tuple[str, str]] | None = None,
    list_box_rows: int = 10,
    list_box_width: int = 0,
    edit_enable: bool = True,
    width: int = 9921,
    height: int = 1984,
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:comboBox>`` element.

    *items* is a list of ``(display_text, value)`` tuples.
    """
    items = items or []
    attrs = (
        f' listBoxRows="{list_box_rows}" listBoxWidth="{list_box_width}"'
        f' editEnable="{1 if edit_enable else 0}" selectedValue=""'
        f'{_form_common_attrs(name, backColor="#F0F0F0")}'
    )
    children = "".join(
        f'<hp:listItem displayText="{_escape(dt)}" value="{_escape(v)}"/>'
        for dt, v in items
    )
    return _form_control_xml("comboBox", attrs, width, height, extra_children=children)


def build_listbox_xml(
    name: str = "ListBox1",
    items: list[tuple[str, str]] | None = None,
    width: int = 9921,
    height: int = 3968,
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:listBox>`` element.

    *items* is a list of ``(display_text, value)`` tuples.
    """
    items = items or []
    attrs = (
        f' selectedValue=""'
        f'{_form_common_attrs(name)}'
    )
    children = "".join(
        f'<hp:listItem displayText="{_escape(dt)}" value="{_escape(v)}"/>'
        for dt, v in items
    )
    return _form_control_xml("listBox", attrs, width, height, extra_children=children)


def build_edit_xml(
    name: str = "Edit1",
    text: str = "",
    multi_line: bool = False,
    max_length: int = 2147483647,
    read_only: bool = False,
    align_text: str = "LEFT",
    width: int = 7087,
    height: int = 1984,
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:edit>`` element."""
    attrs = (
        f' multiLine="{1 if multi_line else 0}" passwordChar=""'
        f' maxLength="{max_length}" scrollBars="NONE"'
        f' tabKeyBehavior="NEXT_OBJECT" numOnly="0"'
        f' readOnly="{1 if read_only else 0}" alignText="{align_text}"'
        f'{_form_common_attrs(name)}'
    )
    children = f'<hp:text>{_escape(text)}</hp:text>' if text else '<hp:text/>'
    return _form_control_xml("edit", attrs, width, height, extra_children=children)


def build_scrollbar_xml(
    name: str = "ScrollBar1",
    orientation: str = "HORIZONTAL",
    min_val: int = 0,
    max_val: int = 32767,
    value: int = 0,
    small_change: int = 1,
    large_change: int = 3,
    width: int = 14400,
    height: int = 1984,
) -> str:
    """Build a complete ``<hp:run>`` containing an ``<hp:scrollBar>`` element."""
    attrs = (
        f' delay="50" smallChange="{small_change}" largeChange="{large_change}"'
        f' min="{min_val}" max="{max_val}" page="3" value="{value}"'
        f' type="{orientation}"'
        f'{_form_common_attrs(name)}'
    )
    return _form_control_xml("scrollBar", attrs, width, height)


# ======================================================================
# INLINE / SPECIAL CHARACTERS  (Phase 4)
# ======================================================================

def build_highlight_xml(
    text: str,
    color: str = "#FFFF00",
    char_pr_id_ref: str = "0",
) -> str:
    """Build multi-run XML for highlighted (markpen) text.

    Returns three ``<hp:run>`` elements: markpenBegin, text, markpenEnd.
    """
    escaped = _escape(text)
    return (
        f'<hp:run charPrIDRef="{char_pr_id_ref}">'
        f'<hp:markpenBegin color="{color}"/>'
        '</hp:run>'
        f'<hp:run charPrIDRef="{char_pr_id_ref}">'
        f'<hp:t>{escaped}</hp:t>'
        '</hp:run>'
        f'<hp:run charPrIDRef="{char_pr_id_ref}">'
        '<hp:markpenEnd/>'
        '</hp:run>'
    )


def build_dutmal_xml(
    main_text: str,
    sub_text: str,
    pos: str = "TOP",
    sz_ratio: int = 50,
    align: str = "CENTER",
    char_pr_id_ref: str = "0",
) -> str:
    """Build a ``<hp:run>`` containing a ``<hp:dutmal>`` (ruby text) element."""
    return (
        f'<hp:run charPrIDRef="{char_pr_id_ref}">'
        f'<hp:dutmal posType="{pos}" szRatio="{sz_ratio}"'
        f' option="0" styleIDRef="0" align="{align}">'
        f'<hp:mainText>{_escape(main_text)}</hp:mainText>'
        f'<hp:subText>{_escape(sub_text)}</hp:subText>'
        '</hp:dutmal>'
        '</hp:run>'
    )


def build_hidden_comment_xml(
    text: str,
    char_pr_id_ref: str = "0",
) -> str:
    """Build a ``<hp:run>`` containing an ``<hp:ctrl><hp:hiddenComment>``."""
    p_id = _id()
    escaped = _escape(text)
    return (
        f'<hp:run charPrIDRef="{char_pr_id_ref}">'
        '<hp:ctrl>'
        '<hp:hiddenComment>'
        '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK"'
        ' vertAlign="TOP" linkListIDRef="0" linkListNextIDRef="0"'
        ' textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
        f'<hp:p id="{p_id}" paraPrIDRef="0" styleIDRef="0" pageBreak="0"'
        ' columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_pr_id_ref}">'
        f'<hp:t>{escaped}</hp:t>'
        '</hp:run>'
        '</hp:p>'
        '</hp:subList>'
        '</hp:hiddenComment>'
        '</hp:ctrl>'
        '</hp:run>'
    )


def build_indexmark_xml(
    key: str,
    second_key: str | None = None,
    char_pr_id_ref: str = "0",
) -> str:
    """Build a ``<hp:run>`` containing an ``<hp:ctrl><hp:indexmark>``."""
    second = (
        f'<hp:secondKey>{_escape(second_key)}</hp:secondKey>'
        if second_key else ''
    )
    return (
        f'<hp:run charPrIDRef="{char_pr_id_ref}">'
        '<hp:ctrl>'
        '<hp:indexmark>'
        f'<hp:firstKey>{_escape(key)}</hp:firstKey>'
        f'{second}'
        '</hp:indexmark>'
        '</hp:ctrl>'
        '</hp:run>'
    )


def build_tab_xml(char_pr_id_ref: str = "0") -> str:
    """Build a ``<hp:run>`` containing a tab character."""
    return (
        f'<hp:run charPrIDRef="{char_pr_id_ref}">'
        '<hp:t><hp:tab/></hp:t>'
        '</hp:run>'
    )


def build_special_char_xml(
    char_type: str = "nbspace",
    char_pr_id_ref: str = "0",
) -> str:
    """Build a ``<hp:run>`` containing a special character.

    *char_type*: ``"nbspace"`` | ``"fwspace"`` | ``"hyphen"``.
    """
    tag_map = {
        "nbspace": "nbSpace",
        "fwspace": "fwSpace",
        "hyphen": "hyphen",
    }
    tag = tag_map.get(char_type.lower(), "nbSpace")
    return (
        f'<hp:run charPrIDRef="{char_pr_id_ref}">'
        f'<hp:t><hp:{tag}/></hp:t>'
        '</hp:run>'
    )
