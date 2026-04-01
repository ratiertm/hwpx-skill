"""Dynamic style management for pyhwpxlib.

Provides ensure_* functions that find or create style entries in the
header's reference lists.  This enables runtime style creation for
bold text, custom colors, code blocks, cell backgrounds, etc.

Usage::

    from pyhwpxlib.style_manager import ensure_char_style, ensure_border_fill

    doc = create_document()
    char_id = ensure_char_style(doc, bold=True, height=1200)
    bf_id = ensure_border_fill(doc, face_color="#F5F5F5")
"""
from __future__ import annotations

import copy
from typing import Optional

from .hwpx_file import HWPXFile
from .objects.header.enum_types import (
    CenterLineSort,
    HorizontalAlign1,
    HorizontalAlign2,
    LanguageType,
    LineBreakForLatin,
    LineBreakForNonLatin,
    LineSpacingType,
    LineType2,
    LineWidth,
    LineWrap,
    NumberType1,
    ParaHeadingType,
    SlashType,
    SymMarkSort,
    UnderlineType,
    LineType3,
    ValueUnit1,
    ValueUnit2,
    VerticalAlign1,
    FontType,
)
from .objects.header.header_xml_file import NoAttributeNoChild
from .object_type import ObjectType


# ======================================================================
# Internal helpers
# ======================================================================

def _next_id(items_list) -> str:
    """Get next available numeric ID from a list of items with .id attributes."""
    max_id = -1
    for item in items_list.items():
        try:
            val = int(item.id)
            if val > max_id:
                max_id = val
        except (TypeError, ValueError):
            continue
    return str(max_id + 1)


def _get_ref_list(hwpx_file: HWPXFile):
    """Return the header refList, raising if missing."""
    header = hwpx_file.header_xml_file
    if header is None or header.refList is None:
        raise RuntimeError(
            "HWPXFile has no header or refList. "
            "Create a document with create_document() first."
        )
    return header.refList


# ======================================================================
# ensure_char_style
# ======================================================================

def ensure_char_style(
    hwpx_file: HWPXFile,
    *,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    height: Optional[int] = None,
    text_color: Optional[str] = None,
    font_name: Optional[str] = None,
) -> str:
    """Find or create a charPr matching the given style and return its ID.

    Parameters
    ----------
    bold, italic, underline : bool
        Text decoration flags.
    height : int or None
        Font size in HWPX units (100 = 1pt, so 1000 = 10pt).
        None means "use the base charPr's height (1000)".
    text_color : str or None
        Hex color string (e.g. ``"#FF0000"``).
        None means "use the base charPr's color (#000000)".
    font_name : str or None
        Font face name. When provided, the font is registered in all
        fontface language lists and the new charPr's fontRef is set to
        the font's index.

    Returns
    -------
    str
        The charPr ID suitable for use as ``char_pr_id_ref``.
    """
    ref_list = _get_ref_list(hwpx_file)
    char_props = ref_list.charProperties
    if char_props is None:
        raise RuntimeError("No charProperties in refList.")

    # Resolve defaults from base charPr (id=0)
    effective_height = height if height is not None else 1000
    effective_color = text_color if text_color is not None else "#000000"

    # Resolve font_name -> fontRef ID
    font_ref_id: Optional[str] = None
    if font_name is not None:
        font_ref_id = _ensure_font_registered(hwpx_file, font_name)

    # Search existing charPr entries for a match
    for cp in char_props.items():
        if _char_pr_matches(cp, effective_height, effective_color,
                            bold, italic, underline, font_ref_id):
            return cp.id

    # Not found -- clone base charPr (id=0) and modify
    base_cp = None
    for cp in char_props.items():
        if cp.id == "0":
            base_cp = cp
            break
    if base_cp is None:
        raise RuntimeError("Base charPr (id=0) not found.")

    new_cp = copy.deepcopy(base_cp)
    new_cp.id = _next_id(char_props)
    new_cp.height = effective_height
    new_cp.textColor = effective_color

    # Bold
    if bold:
        new_cp.create_bold()
    else:
        new_cp.bold = None

    # Italic
    if italic:
        new_cp.create_italic()
    else:
        new_cp.italic = None

    # Underline
    if underline:
        ul = new_cp.create_underline()
        ul.type = UnderlineType.BOTTOM
        ul.shape = LineType3.SOLID
        ul.color = effective_color
    else:
        new_cp.underline = None

    # Font reference
    if font_ref_id is not None and new_cp.fontRef is not None:
        new_cp.fontRef.set_all(font_ref_id)

    char_props.add(new_cp)
    return new_cp.id


def _char_pr_matches(
    cp,
    height: int,
    text_color: str,
    bold: bool,
    italic: bool,
    underline: bool,
    font_ref_id: Optional[str],
) -> bool:
    """Check if an existing charPr matches the requested style."""
    if cp.height != height:
        return False
    if cp.textColor != text_color:
        return False
    if bool(cp.bold) != bold:
        return False
    if bool(cp.italic) != italic:
        return False
    if bool(cp.underline) != underline:
        return False
    if font_ref_id is not None:
        if cp.fontRef is None:
            return False
        # Check hangul as representative (all langs should be same)
        if str(cp.fontRef.hangul) != str(font_ref_id):
            return False
    return True


# ======================================================================
# Font registration
# ======================================================================

def _ensure_font_registered(hwpx_file: HWPXFile, font_name: str) -> str:
    """Register a font in all fontface language lists if not present.

    Returns the font ID (index) as a string.
    """
    ref_list = _get_ref_list(hwpx_file)
    fontfaces = ref_list.fontfaces
    if fontfaces is None:
        raise RuntimeError("No fontfaces in refList.")

    # Check if the font already exists (check HANGUL fontface as canonical)
    hangul_ff = fontfaces.hangul_fontface()
    if hangul_ff is not None:
        for font in hangul_ff.fonts():
            if font.face == font_name:
                return font.id

    # Font not found -- add to all language fontface lists
    # Determine next font ID from the first fontface
    next_font_id = "0"
    if hangul_ff is not None and hangul_ff.count_of_font() > 0:
        max_id = -1
        for f in hangul_ff.fonts():
            try:
                val = int(f.id)
                if val > max_id:
                    max_id = val
            except (TypeError, ValueError):
                continue
        next_font_id = str(max_id + 1)

    for ff in fontfaces.fontfaces():
        new_font = ff.add_new_font()
        new_font.id = next_font_id
        new_font.face = font_name
        new_font.type = FontType.TTF
        new_font.isEmbedded = False

    return next_font_id


# ======================================================================
# ensure_border_fill
# ======================================================================

def ensure_border_fill(
    hwpx_file: HWPXFile,
    *,
    face_color: Optional[str] = None,
    hatch_color: Optional[str] = None,
    border_type: str = "NONE",
    border_width: str = "0.12 mm",
    border_color: str = "#000000",
) -> str:
    """Find or create a borderFill and return its ID.

    Parameters
    ----------
    face_color : str or None
        Background fill color (e.g. ``"#F5F5F5"``).
    hatch_color : str or None
        Hatch pattern color.
    border_type : str
        Border line type (default ``"NONE"``).
    border_width : str
        Border width string (default ``"0.12 mm"``).
    border_color : str
        Border color (default ``"#000000"``).

    Returns
    -------
    str
        The borderFill ID.
    """
    ref_list = _get_ref_list(hwpx_file)
    border_fills = ref_list.borderFills
    if border_fills is None:
        raise RuntimeError("No borderFills in refList.")

    # Search for an existing match
    for bf in border_fills.items():
        if _border_fill_matches(bf, face_color, hatch_color):
            return bf.id

    # Not found -- create new
    from .objects.header.references.border_fill import (
        BorderFill, Border, FillBrush, WinBrush, SlashCore,
    )

    new_bf = BorderFill()
    new_bf.id = _next_id(border_fills)
    new_bf.threeD = False
    new_bf.shadow = False
    new_bf.centerLine = CenterLineSort.NONE
    new_bf.breakCellSeparateLine = False

    # Slash / BackSlash
    slash = new_bf.create_slash()
    slash.type = SlashType.NONE
    slash.Crooked = False
    slash.isCounter = False

    back_slash = new_bf.create_back_slash()
    back_slash.type = SlashType.NONE
    back_slash.Crooked = False
    back_slash.isCounter = False

    # Borders
    bt = LineType2.from_string(border_type)
    bw = LineWidth.from_string(border_width)

    for create_fn in [new_bf.create_left_border, new_bf.create_right_border,
                      new_bf.create_top_border, new_bf.create_bottom_border]:
        b = create_fn()
        b.type = bt
        b.width = bw
        b.color = border_color

    diag = new_bf.create_diagonal()
    diag.type = LineType2.SOLID
    diag.width = LineWidth.MM_0_1
    diag.color = "#000000"

    # Fill brush
    if face_color is not None or hatch_color is not None:
        fb = new_bf.create_fill_brush()
        wb = fb.create_win_brush()
        wb.faceColor = face_color
        wb.hatchColor = hatch_color
        wb.alpha = 0.0

    border_fills.add(new_bf)
    return new_bf.id


def ensure_gradient_border_fill(
    hwpx_file: HWPXFile,
    *,
    start_color: str = "#FFFFFF",
    end_color: str = "#000000",
    gradient_type: str = "LINEAR",
    angle: int = 0,
    center_x: int = 50,
    center_y: int = 50,
    step: int = 50,
) -> str:
    """Find or create a borderFill with gradient fill and return its ID.

    Parameters
    ----------
    start_color, end_color : str
        Gradient stop colors (hex, e.g. ``"#FFFFFF"``).
    gradient_type : str
        Gradient type: ``"LINEAR"``, ``"RADIAL"``, ``"CONICAL"``, ``"SQUARE"``.
    angle : int
        Gradient angle in degrees (0-360).
    center_x, center_y : int
        Center point for radial/conical gradients (0-100).
    step : int
        Gradient step count.

    Returns
    -------
    str
        The borderFill ID.
    """
    from .objects.header.references.border_fill import (
        BorderFill, FillBrush, Gradation, Color, SlashCore, Border,
    )
    from .objects.header.enum_types import GradationType

    ref_list = _get_ref_list(hwpx_file)
    border_fills = ref_list.borderFills
    if border_fills is None:
        raise RuntimeError("No borderFills in refList.")

    # Search for an existing gradient match
    for bf in border_fills.items():
        if _gradient_fill_matches(bf, start_color, end_color, gradient_type, angle):
            return bf.id

    # Not found -- create new borderFill with gradient
    new_bf = BorderFill()
    new_bf.id = _next_id(border_fills)
    new_bf.threeD = False
    new_bf.shadow = False
    new_bf.centerLine = CenterLineSort.NONE
    new_bf.breakCellSeparateLine = False

    # Slash / BackSlash
    slash = new_bf.create_slash()
    slash.type = SlashType.NONE
    slash.Crooked = False
    slash.isCounter = False

    back_slash = new_bf.create_back_slash()
    back_slash.type = SlashType.NONE
    back_slash.Crooked = False
    back_slash.isCounter = False

    # Borders (all NONE)
    for create_fn in [new_bf.create_left_border, new_bf.create_right_border,
                      new_bf.create_top_border, new_bf.create_bottom_border]:
        b = create_fn()
        b.type = LineType2.NONE
        b.width = LineWidth.MM_0_1
        b.color = "#000000"

    diag = new_bf.create_diagonal()
    diag.type = LineType2.SOLID
    diag.width = LineWidth.MM_0_1
    diag.color = "#000000"

    # Fill brush with gradation
    fb = new_bf.create_fill_brush()
    grad = fb.create_gradation()
    grad.type = GradationType.from_string(gradient_type)
    grad.angle = angle
    grad.centerX = center_x
    grad.centerY = center_y
    grad.step = step

    c1 = grad.add_new_color()
    c1.value = start_color
    c2 = grad.add_new_color()
    c2.value = end_color

    border_fills.add(new_bf)
    return new_bf.id


def _gradient_fill_matches(
    bf,
    start_color: str,
    end_color: str,
    gradient_type: str,
    angle: int,
) -> bool:
    """Check if an existing borderFill matches the requested gradient."""
    fb = bf.fillBrush
    if fb is None:
        return False
    grad = fb.gradation
    if grad is None:
        return False
    if grad.type is None:
        return False
    grad_type_val = grad.type.value if hasattr(grad.type, 'value') else str(grad.type)
    if grad_type_val != gradient_type:
        return False
    if grad.angle != angle:
        return False
    colors = grad.colors()
    if len(colors) != 2:
        return False
    if colors[0].value != start_color or colors[1].value != end_color:
        return False
    return True


def _border_fill_matches(bf, face_color: Optional[str], hatch_color: Optional[str]) -> bool:
    """Check if an existing borderFill matches the requested fill colors."""
    fb = bf.fillBrush
    if face_color is None and hatch_color is None:
        # Match a borderFill with no fill brush
        return fb is None
    if fb is None:
        return False
    wb = fb.winBrush
    if wb is None:
        return False
    if wb.faceColor != face_color:
        return False
    if wb.hatchColor != hatch_color:
        return False
    return True


# ======================================================================
# ensure_para_style
# ======================================================================

def ensure_para_style(
    hwpx_file: HWPXFile,
    *,
    align: Optional[str] = None,
    line_spacing_value: Optional[int] = None,
    line_spacing_type: Optional[str] = None,
    border_fill_id_ref: Optional[str] = None,
    indent: Optional[int] = None,
    margin_left: Optional[int] = None,
) -> str:
    """Find or create a paraPr matching the given style and return its ID.

    Parameters
    ----------
    align : str or None
        Horizontal alignment (e.g. ``"JUSTIFY"``, ``"LEFT"``, ``"CENTER"``).
    line_spacing_value : int or None
        Line spacing value (e.g. 160 for 160%).
    line_spacing_type : str or None
        Line spacing type (default ``"PERCENT"``).
    border_fill_id_ref : str or None
        BorderFill ID for paragraph background/border.
    indent : int or None
        Paragraph indent in HWPX units.
    margin_left : int or None
        Left margin in HWPX units.

    Returns
    -------
    str
        The paraPr ID.
    """
    ref_list = _get_ref_list(hwpx_file)
    para_props = ref_list.paraProperties
    if para_props is None:
        raise RuntimeError("No paraProperties in refList.")

    # Resolve defaults from base paraPr (id=0)
    effective_align = align or "JUSTIFY"
    effective_ls_value = line_spacing_value if line_spacing_value is not None else 160
    effective_ls_type = line_spacing_type or "PERCENT"
    effective_bf_ref = border_fill_id_ref or "2"
    effective_indent = indent if indent is not None else 0
    effective_margin_left = margin_left if margin_left is not None else 0

    # Search for existing match
    for pp in para_props.items():
        if _para_pr_matches(pp, effective_align, effective_ls_value,
                            effective_bf_ref, effective_indent,
                            effective_margin_left):
            return pp.id

    # Not found -- clone base paraPr (id=0) and modify
    base_pp = None
    for pp in para_props.items():
        if pp.id == "0":
            base_pp = pp
            break
    if base_pp is None:
        raise RuntimeError("Base paraPr (id=0) not found.")

    new_pp = copy.deepcopy(base_pp)
    new_pp.id = _next_id(para_props)

    # Alignment
    if new_pp.align is not None:
        new_pp.align.horizontal = HorizontalAlign2.from_string(effective_align)

    # Line spacing
    if new_pp.lineSpacing is not None:
        new_pp.lineSpacing.value = effective_ls_value
        ls_type = LineSpacingType.from_string(effective_ls_type)
        if ls_type is not None:
            new_pp.lineSpacing.type = ls_type

    # Border (paragraph background)
    if new_pp.border is not None:
        new_pp.border.borderFillIDRef = effective_bf_ref
    else:
        border = new_pp.create_border()
        border.borderFillIDRef = effective_bf_ref
        border.offsetLeft = 0
        border.offsetRight = 0
        border.offsetTop = 0
        border.offsetBottom = 0
        border.connect = False
        border.ignoreMargin = False

    # Indent
    if effective_indent != 0 and new_pp.margin is not None:
        if new_pp.margin.intent is not None:
            new_pp.margin.intent.value = effective_indent

    # Left margin
    if effective_margin_left != 0 and new_pp.margin is not None:
        if new_pp.margin.left is not None:
            new_pp.margin.left.value = effective_margin_left

    para_props.add(new_pp)
    return new_pp.id


def _para_pr_matches(
    pp,
    align: str,
    ls_value: int,
    bf_ref: str,
    indent: int,
    margin_left: int,
) -> bool:
    """Check if an existing paraPr matches the requested style."""
    # Check alignment
    if pp.align is not None:
        h_align = pp.align.horizontal
        if h_align is not None:
            # HorizontalAlign2 enum stores value as string
            align_val = h_align.value if hasattr(h_align, 'value') else str(h_align)
            if align_val != align:
                return False
        elif align != "JUSTIFY":
            return False
    elif align != "JUSTIFY":
        return False

    # Check line spacing
    if pp.lineSpacing is not None:
        if pp.lineSpacing.value != ls_value:
            return False
    elif ls_value != 160:
        return False

    # Check border fill ref
    if pp.border is not None:
        if pp.border.borderFillIDRef != bf_ref:
            return False
    elif bf_ref != "2":
        return False

    # Check indent
    actual_indent = 0
    if pp.margin is not None and pp.margin.intent is not None:
        actual_indent = pp.margin.intent.value or 0
    if actual_indent != indent:
        return False

    # Check left margin
    actual_left = 0
    if pp.margin is not None and pp.margin.left is not None:
        actual_left = pp.margin.left.value or 0
    if actual_left != margin_left:
        return False

    return True


# ======================================================================
# Convenience: font_size_to_height
# ======================================================================

def font_size_to_height(font_size_pt: Optional[int]) -> Optional[int]:
    """Convert a font size in pt to HWPX height units.

    HWPX uses 100 units per point, so 10pt = 1000, 16pt = 1600.
    Returns None if font_size_pt is None.
    """
    if font_size_pt is None:
        return None
    return font_size_pt * 100


# ======================================================================
# ensure_numbering
# ======================================================================

def ensure_numbering(
    hwpx_file: HWPXFile,
    *,
    start: int = 1,
    format_string: str = "^1.",
    level: int = 1,
    force_new: bool = False,
) -> str:
    """Create or find a numbering definition in the header and return its id.

    Parameters
    ----------
    start : int
        Starting number (default 1).
    format_string : str
        ParaHead text pattern (e.g. ``"^1."`` for "1.", ``"^1.^2"`` for "1.1").
    level : int
        ParaHead level (default 1).
    force_new : bool
        If True, always create a new numbering (resets counter).

    Returns
    -------
    str
        The numbering definition id.
    """
    ref_list = _get_ref_list(hwpx_file)

    # Ensure numberings collection exists
    if ref_list.numberings is None:
        ref_list.create_numberings()

    numberings = ref_list.numberings

    # Search for existing match (skip if force_new)
    if not force_new:
        for n in numberings.items():
            if n.start == start and n.count_of_para_head() > 0:
                ph = n.get_para_head(0)
                if ph.text == format_string and ph.level == level:
                    return n.id

    # Not found -- create new
    from .objects.header.references.numbering import Numbering, ParaHead

    new_n = Numbering()
    new_n.id = _next_id(numberings)
    new_n.start = start

    ph = new_n.add_new_para_head()
    ph.start = start
    ph.level = level
    ph.align = HorizontalAlign1.LEFT
    ph.useInstWidth = True
    ph.autoIndent = True
    ph.widthAdjust = 0
    ph.textOffsetType = ValueUnit1.PERCENT
    ph.textOffset = 50
    ph.numFormat = NumberType1.DIGIT
    ph.charPrIDRef = "4294967295"
    ph.checkable = False
    ph.text = format_string

    numberings.add(new_n)
    return new_n.id


# ======================================================================
# ensure_bullet
# ======================================================================

def ensure_bullet(
    hwpx_file: HWPXFile,
    *,
    char: str = "\u25cf",
) -> str:
    """Create or find a bullet definition in the header and return its id.

    Parameters
    ----------
    char : str
        Bullet character (default ``"\\u25cf"`` = ``"●"``).

    Returns
    -------
    str
        The bullet definition id.
    """
    ref_list = _get_ref_list(hwpx_file)

    # Ensure bullets collection exists
    if ref_list.bullets is None:
        ref_list.create_bullets()

    bullets = ref_list.bullets

    # Search for existing match
    for b in bullets.items():
        if b._char == char:
            return b.id

    # Not found -- create new
    from .objects.header.references.numbering import Bullet, ParaHead

    new_b = Bullet()
    new_b.id = _next_id(bullets)
    new_b._char = char
    new_b.useImage = False

    ph = new_b.create_para_head()
    ph.level = 0
    ph.align = HorizontalAlign1.LEFT
    ph.useInstWidth = False
    ph.autoIndent = True
    ph.widthAdjust = 0
    ph.textOffsetType = ValueUnit1.PERCENT
    ph.textOffset = 50
    ph.numFormat = NumberType1.DIGIT
    ph.charPrIDRef = "4294967295"
    ph.checkable = False

    bullets.add(new_b)
    return new_b.id


# ======================================================================
# ensure_heading_para_style
# ======================================================================

def ensure_heading_para_style(
    hwpx_file: HWPXFile,
    *,
    heading_type: str = "NUMBER",
    heading_id_ref: str = "1",
    level: int = 0,
    margin_left: int = 0,
) -> str:
    """Create or find a paraPr with a heading reference and return its id.

    The heading element links the paragraph to a numbering or bullet
    definition so that the renderer (한컴 오피스) automatically draws
    the number or bullet character.

    Parameters
    ----------
    heading_type : str
        ``"NUMBER"`` for numbering or ``"BULLET"`` for bullets.
    heading_id_ref : str
        The id of the numbering or bullet definition.
    level : int
        Heading level (default 0).
    margin_left : int
        Left margin in HWPX units (for nested lists).

    Returns
    -------
    str
        The paraPr id.
    """
    ref_list = _get_ref_list(hwpx_file)
    para_props = ref_list.paraProperties
    if para_props is None:
        raise RuntimeError("No paraProperties in refList.")

    ht = ParaHeadingType.from_string(heading_type)

    # Search for existing match
    for pp in para_props.items():
        if _heading_para_pr_matches(pp, ht, heading_id_ref, level, margin_left):
            return pp.id

    # Not found -- clone base paraPr (id=0) and modify
    base_pp = None
    for pp in para_props.items():
        if pp.id == "0":
            base_pp = pp
            break
    if base_pp is None:
        raise RuntimeError("Base paraPr (id=0) not found.")

    new_pp = copy.deepcopy(base_pp)
    new_pp.id = _next_id(para_props)

    # Set heading reference
    from .objects.header.references.para_pr import Heading
    h = new_pp.create_heading()
    h.type = ht
    h.idRef = heading_id_ref
    h.level = level

    # Set left margin for nested lists
    if margin_left > 0 and new_pp.margin is not None:
        if new_pp.margin.left is not None:
            new_pp.margin.left.value = margin_left

    para_props.add(new_pp)
    return new_pp.id


def ensure_image_fill_border_fill(
    hwpx_file: HWPXFile,
    *,
    image_item_id: str,
    mode: str = "STRETCH",
) -> str:
    """Find or create a borderFill with image fill and return its ID.

    Parameters
    ----------
    image_item_id : str
        Manifest item id for the image (e.g. ``"image1"``).
    mode : str
        Image fill mode: ``"TILE"``, ``"CENTER"``, ``"FIT"``, ``"STRETCH"``.

    Returns
    -------
    str
        The borderFill ID.
    """
    from .objects.header.references.border_fill import (
        BorderFill, FillBrush, SlashCore, Border,
    )

    ref_list = _get_ref_list(hwpx_file)
    border_fills = ref_list.borderFills
    if border_fills is None:
        raise RuntimeError("No borderFills in refList.")

    # Search for an existing image fill match
    for bf in border_fills.items():
        fb = bf.fillBrush
        if fb is not None and fb.imgBrush is not None:
            ib = fb.imgBrush
            if (hasattr(ib, 'img') and ib.img is not None
                    and getattr(ib.img, 'binaryItemIDRef', None) == image_item_id
                    and getattr(ib, 'mode', None) == mode):
                return bf.id

    # Not found -- create new borderFill with image fill
    new_bf = BorderFill()
    new_bf.id = _next_id(border_fills)
    new_bf.threeD = False
    new_bf.shadow = False
    new_bf.centerLine = CenterLineSort.NONE
    new_bf.breakCellSeparateLine = False

    # Slash / BackSlash
    slash = new_bf.create_slash()
    slash.type = SlashType.NONE
    slash.Crooked = False
    slash.isCounter = False

    back_slash = new_bf.create_back_slash()
    back_slash.type = SlashType.NONE
    back_slash.Crooked = False
    back_slash.isCounter = False

    # Borders (all NONE)
    for create_fn in [new_bf.create_left_border, new_bf.create_right_border,
                      new_bf.create_top_border, new_bf.create_bottom_border]:
        b = create_fn()
        b.type = LineType2.NONE
        b.width = LineWidth.MM_0_1
        b.color = "#000000"

    diag = new_bf.create_diagonal()
    diag.type = LineType2.SOLID
    diag.width = LineWidth.MM_0_1
    diag.color = "#000000"

    # Fill brush with imgBrush
    # NOTE: The object model may not have imgBrush support yet.
    # We store the raw XML attributes for the writer to handle.
    fb = new_bf.create_fill_brush()
    # Set imgBrush if the model supports it; otherwise the
    # borderFill still gets created and the shape_writer uses
    # _img_fill_brush_xml directly for shape-level image fills.
    try:
        ib = fb.create_img_brush()
        ib.mode = mode
        img = ib.create_img()
        img.binaryItemIDRef = image_item_id
        img.bright = 0
        img.contrast = 0
        img.effect = "REAL_PIC"
        img.alpha = 0
    except (AttributeError, TypeError):
        # Object model doesn't support imgBrush yet -- create winBrush
        # as placeholder so the borderFill is valid.
        wb = fb.create_win_brush()
        wb.faceColor = "#FFFFFF"
        wb.hatchColor = "#FFFFFF"
        wb.alpha = 0.0

    border_fills.add(new_bf)
    return new_bf.id


def _heading_para_pr_matches(
    pp,
    heading_type: Optional[ParaHeadingType],
    heading_id_ref: str,
    level: int,
    margin_left: int,
) -> bool:
    """Check if an existing paraPr matches the requested heading style."""
    h = getattr(pp, "heading", None)
    if h is None:
        return False
    if h.type != heading_type:
        return False
    if str(h.idRef) != str(heading_id_ref):
        return False
    if (h.level or 0) != level:
        return False

    # Check left margin
    actual_left = 0
    if pp.margin is not None and pp.margin.left is not None:
        actual_left = pp.margin.left.value or 0
    if actual_left != margin_left:
        return False

    return True
