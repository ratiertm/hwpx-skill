"""HWP <-> HWPX 값 변환 유틸리티

Ported from hwp2hwpx ValueConvertor.java by neolord0
(https://github.com/neolord0/hwp2hwpx)
Original work Copyright (c) neolord0, licensed under Apache License 2.0.
This file: Copyright (c) 2026 Eunmi Lee (ratiertm), licensed under Apache License 2.0.
"""


def color_from_int(value: int) -> str:
    """Color4Byte (int) -> '#RRGGBB' string.
    HWP stores as BGR (blue in low byte, red in high byte).
    4294967295 (0xFFFFFFFF) -> 'none'"""
    if value == 0xFFFFFFFF or value == 4294967295:
        return "none"
    r = value & 0xFF
    g = (value >> 8) & 0xFF
    b = (value >> 16) & 0xFF
    return f"#{r:02X}{g:02X}{b:02X}"


def color_with_none(value: int, none_value: int) -> str:
    """color but returns 'none' if value == none_value"""
    if value == none_value:
        return "none"
    return color_from_int(value)


def ref_id(value: int) -> str:
    """Reference ID: -1 -> '4294967295', else str(value)"""
    if value == -1 or value == 0xFFFFFFFF:
        return "4294967295"
    return str(value)


def line_type2(border_type: int) -> str:
    """HWP BorderType/LineType -> HWPX line type string
    Maps: 0=NONE, 1=SOLID, 2=DASH, 3=DOT, 4=DASH_DOT, 5=DASH_DOT_DOT,
    6=LONG_DASH, 7=CIRCLE, 8=DOUBLE_SLIM, 9=SLIM_THICK, 10=THICK_SLIM,
    11=SLIM_THICK_SLIM
    """
    mapping = {
        0: "NONE", 1: "SOLID", 2: "DASH", 3: "DOT",
        4: "DASH_DOT", 5: "DASH_DOT_DOT", 6: "LONG_DASH",
        7: "CIRCLE", 8: "DOUBLE_SLIM", 9: "SLIM_THICK",
        10: "THICK_SLIM", 11: "SLIM_THICK_SLIM"
    }
    return mapping.get(border_type, "NONE")


def line_type2_gso(line_type: int) -> str:
    """GSO LineType -> HWPX (note: Dash/Dot are SWAPPED in HWP GSO)
    0=SOLID, 1=DOT(maps to DASH), 2=DASH(maps to DOT), 3=DASH_DOT,
    4=DASH_DOT_DOT, 5=LONG_DASH, 6=CIRCLE, 7=DOUBLE_SLIM,
    8=SLIM_THICK, 9=THICK_SLIM, 10=SLIM_THICK_SLIM, 11=NONE
    """
    mapping = {
        0: "SOLID", 1: "DOT", 2: "DASH", 3: "DASH_DOT",
        4: "DASH_DOT_DOT", 5: "LONG_DASH", 6: "CIRCLE",
        7: "DOUBLE_SLIM", 8: "SLIM_THICK", 9: "THICK_SLIM",
        10: "SLIM_THICK_SLIM", 11: "NONE"
    }
    return mapping.get(line_type, "SOLID")


def line_type3(border_type2: int) -> str:
    """BorderType2 -> HWPX (adds WAVE, DOUBLEWAVE)
    Same as line_type2 but with 12=WAVE, 13=DOUBLEWAVE"""
    mapping = {
        0: "NONE", 1: "SOLID", 2: "DASH", 3: "DOT",
        4: "DASH_DOT", 5: "DASH_DOT_DOT", 6: "LONG_DASH",
        7: "CIRCLE", 8: "DOUBLE_SLIM", 9: "SLIM_THICK",
        10: "THICK_SLIM", 11: "SLIM_THICK_SLIM",
        12: "WAVE", 13: "DOUBLEWAVE"
    }
    return mapping.get(border_type2, "NONE")


def line_width(thickness: int) -> str:
    """HWP BorderThickness -> HWPX width string (MM_0_1 etc.)"""
    mapping = {
        0: "MM_0_1", 1: "MM_0_12", 2: "MM_0_15", 3: "MM_0_2",
        4: "MM_0_25", 5: "MM_0_3", 6: "MM_0_4", 7: "MM_0_5",
        8: "MM_0_6", 9: "MM_0_7", 10: "MM_1_0", 11: "MM_1_5",
        12: "MM_2_0", 13: "MM_3_0", 14: "MM_4_0", 15: "MM_5_0"
    }
    return mapping.get(thickness, "MM_0_1")


def horizontal_align(value: int) -> str:
    """Paragraph horizontal alignment
    0=JUSTIFY, 1=LEFT, 2=RIGHT, 3=CENTER, 4=DISTRIBUTE, 5=DISTRIBUTE_SPACE"""
    mapping = {
        0: "JUSTIFY", 1: "LEFT", 2: "RIGHT", 3: "CENTER",
        4: "DISTRIBUTE", 5: "DISTRIBUTE_SPACE"
    }
    return mapping.get(value, "JUSTIFY")


def vertical_align1(value: int) -> str:
    """Vertical alignment type 1: 0=BASELINE, 1=TOP, 2=CENTER, 3=BOTTOM"""
    mapping = {0: "BASELINE", 1: "TOP", 2: "CENTER", 3: "BOTTOM"}
    return mapping.get(value, "BASELINE")


def vertical_align2(value: int) -> str:
    """Vertical alignment type 2: 0=TOP, 1=CENTER, 2=BOTTOM"""
    mapping = {0: "TOP", 1: "CENTER", 2: "BOTTOM"}
    return mapping.get(value, "TOP")


def number_type1(para_num_format: int) -> str:
    """ParagraphNumberFormat -> HWPX"""
    mapping = {
        0: "DIGIT", 1: "CIRCLED_DIGIT", 2: "ROMAN_CAPITAL",
        3: "ROMAN_SMALL", 4: "LATIN_CAPITAL", 5: "LATIN_SMALL",
        6: "CIRCLED_LATIN_CAPITAL", 7: "CIRCLED_LATIN_SMALL",
        8: "HANGUL_SYLLABLE", 9: "CIRCLED_HANGUL_SYLLABLE",
        10: "HANGUL_JAMO", 11: "CIRCLED_HANGUL_JAMO",
        12: "HANGUL_PHONETIC", 13: "IDEOGRAPH",
        14: "CIRCLED_IDEOGRAPH"
    }
    return mapping.get(para_num_format, "DIGIT")


def number_type2(number_shape: int) -> str:
    """NumberShape -> HWPX (same as number_type1 + extras)"""
    mapping = {
        0: "DIGIT", 1: "CIRCLED_DIGIT", 2: "ROMAN_CAPITAL",
        3: "ROMAN_SMALL", 4: "LATIN_CAPITAL", 5: "LATIN_SMALL",
        6: "CIRCLED_LATIN_CAPITAL", 7: "CIRCLED_LATIN_SMALL",
        8: "HANGUL_SYLLABLE", 9: "CIRCLED_HANGUL_SYLLABLE",
        10: "HANGUL_JAMO", 11: "CIRCLED_HANGUL_JAMO",
        12: "HANGUL_PHONETIC", 13: "IDEOGRAPH",
        14: "CIRCLED_IDEOGRAPH",
        15: "DECAGON_CIRCLE", 16: "DECAGON_CIRCLE_HANJA",
        17: "SYMBOL", 18: "USER_CHAR"
    }
    return mapping.get(number_shape, "DIGIT")


def text_wrap(value: int) -> str:
    """TextWrap: 0=SQUARE, 1=TOP_AND_BOTTOM, 2=BEHIND_TEXT, 3=IN_FRONT_OF_TEXT"""
    mapping = {
        0: "SQUARE", 1: "TOP_AND_BOTTOM",
        2: "BEHIND_TEXT", 3: "IN_FRONT_OF_TEXT"
    }
    return mapping.get(value, "SQUARE")


def text_flow(value: int) -> str:
    """TextFlow: 0=BOTH_SIDES, 1=LEFT_ONLY, 2=RIGHT_ONLY, 3=LARGEST_ONLY"""
    mapping = {
        0: "BOTH_SIDES", 1: "LEFT_ONLY",
        2: "RIGHT_ONLY", 3: "LARGEST_ONLY"
    }
    return mapping.get(value, "BOTH_SIDES")


def numbering_type(value: int) -> str:
    """Numbering type for shapes: 0=NONE, 1=PICTURE, 2=TABLE, 3=EQUATION"""
    mapping = {0: "NONE", 1: "PICTURE", 2: "TABLE", 3: "EQUATION"}
    return mapping.get(value, "NONE")


def size_rel_to_h(value: int) -> str:
    """Horizontal size relative to: 0=PAPER, 1=PAGE, 2=COLUMN, 3=PARA, 4=ABSOLUTE"""
    mapping = {0: "PAPER", 1: "PAGE", 2: "COLUMN", 3: "PARA", 4: "ABSOLUTE"}
    return mapping.get(value, "ABSOLUTE")


def size_rel_to_v(value: int) -> str:
    """Vertical size relative to: 0=PAPER, 1=PAGE, 2=ABSOLUTE"""
    mapping = {0: "PAPER", 1: "PAGE", 2: "ABSOLUTE"}
    return mapping.get(value, "ABSOLUTE")


def pos_rel_to_v(value: int) -> str:
    """Vertical position relative to: 0=PAPER, 1=PAGE, 2=PARA"""
    mapping = {0: "PAPER", 1: "PAGE", 2: "PARA"}
    return mapping.get(value, "PARA")


def pos_rel_to_h(value: int) -> str:
    """Horizontal position relative to: 0=PAPER, 1=PAGE, 2=COLUMN, 3=PARA"""
    mapping = {0: "PAPER", 1: "PAGE", 2: "COLUMN", 3: "PARA"}
    return mapping.get(value, "PARA")


def pos_align_v(value: int) -> str:
    """Vertical align: 0=TOP, 1=CENTER, 2=BOTTOM, 3=INSIDE, 4=OUTSIDE"""
    mapping = {0: "TOP", 1: "CENTER", 2: "BOTTOM", 3: "INSIDE", 4: "OUTSIDE"}
    return mapping.get(value, "TOP")


def pos_align_h(value: int) -> str:
    """Horizontal align: 0=LEFT, 1=CENTER, 2=RIGHT, 3=INSIDE, 4=OUTSIDE"""
    mapping = {0: "LEFT", 1: "CENTER", 2: "RIGHT", 3: "INSIDE", 4: "OUTSIDE"}
    return mapping.get(value, "LEFT")


def caption_side(value: int) -> str:
    """Caption side: 0=LEFT, 1=RIGHT, 2=TOP, 3=BOTTOM"""
    mapping = {0: "LEFT", 1: "RIGHT", 2: "TOP", 3: "BOTTOM"}
    return mapping.get(value, "BOTTOM")


def emphasis_sort(value: int) -> str:
    """Emphasis mark: 0=NONE, 1=DOT_ABOVE, 2=RING_ABOVE, 3=TILDE, 4=CARON,
    5=SIDE, 6=COLON, 7=GRAVE_ACCENT, 8=ACUTE_ACCENT, 9=CIRCUMFLEX,
    10=MACRON, 11=HOOK_ABOVE, 12=DOT_BELOW"""
    mapping = {
        0: "NONE", 1: "DOT_ABOVE", 2: "RING_ABOVE", 3: "TILDE",
        4: "CARON", 5: "SIDE", 6: "COLON", 7: "GRAVE_ACCENT",
        8: "ACUTE_ACCENT", 9: "CIRCUMFLEX", 10: "MACRON",
        11: "HOOK_ABOVE", 12: "DOT_BELOW"
    }
    return mapping.get(value, "NONE")


def underline_type(value: int) -> str:
    """Underline type: 0=NONE, 1=BOTTOM, 2=TOP"""
    mapping = {0: "NONE", 1: "BOTTOM", 2: "TOP"}
    return mapping.get(value, "NONE")


def outline_type(value: int) -> str:
    """Outline: 0=NONE, 1=SOLID, 2=DOT, 3=THICK, 4=DASH, 5=DASH_DOT,
    6=DASH_DOT_DOT"""
    mapping = {
        0: "NONE", 1: "SOLID", 2: "DOT", 3: "THICK",
        4: "DASH", 5: "DASH_DOT", 6: "DASH_DOT_DOT"
    }
    return mapping.get(value, "NONE")


def shadow_type(value: int) -> str:
    """Shadow type: 0=NONE, 1=DROP, 2=CONTINUOUS"""
    mapping = {0: "NONE", 1: "DROP", 2: "CONTINUOUS"}
    return mapping.get(value, "NONE")


def heading_type(value: int) -> str:
    """Heading type: 0=NONE, 1=OUTLINE, 2=NUMBER, 3=BULLET"""
    mapping = {0: "NONE", 1: "OUTLINE", 2: "NUMBER", 3: "BULLET"}
    return mapping.get(value, "NONE")


def break_latin_word(value: int) -> str:
    """Break latin word: 0=KEEP_WORD, 1=HYPHENATION, 2=BREAK_WORD"""
    mapping = {0: "KEEP_WORD", 1: "HYPHENATION", 2: "BREAK_WORD"}
    return mapping.get(value, "BREAK_WORD")


def break_non_latin_word(value: int) -> str:
    """Break non-latin word: 0=KEEP_WORD, 1=BREAK_WORD"""
    mapping = {0: "KEEP_WORD", 1: "BREAK_WORD"}
    return mapping.get(value, "KEEP_WORD")


def line_spacing_type(value: int) -> str:
    """Line spacing type: 0=PERCENT, 1=PERCENT(fixed), 2=BETWEEN_LINES, 3=AT_LEAST"""
    mapping = {0: "PERCENT", 1: "PERCENT", 2: "BETWEEN_LINES", 3: "AT_LEAST"}
    return mapping.get(value, "PERCENT")


def page_break_table(value: int) -> str:
    """Table page break: 0=NONE, 1=CELL, 2=TABLE"""
    mapping = {0: "NONE", 1: "CELL", 2: "TABLE"}
    return mapping.get(value, "NONE")


def landscape(value: int) -> str:
    """Page orientation: 0=WIDELY(portrait), 1=NARROWLY(landscape)"""
    mapping = {0: "WIDELY", 1: "NARROWLY"}
    return mapping.get(value, "WIDELY")


def gutter_type(value: int) -> str:
    """Gutter type: 0=LEFT_ONLY, 1=LEFT_RIGHT, 2=TOP_BOTTOM"""
    mapping = {0: "LEFT_ONLY", 1: "LEFT_RIGHT", 2: "TOP_BOTTOM"}
    return mapping.get(value, "LEFT_ONLY")


def text_direction(value: int) -> str:
    """Text direction: 0=HORIZONTAL, 1=VERTICAL, 2=VERTICALALL"""
    mapping = {0: "HORIZONTAL", 1: "VERTICAL", 2: "VERTICALALL"}
    return mapping.get(value, "HORIZONTAL")


def line_wrap(value: int) -> str:
    """Line wrap: 0=BREAK, 1=SQUEEZE, 2=KEEP"""
    mapping = {0: "BREAK", 1: "SQUEEZE", 2: "KEEP"}
    return mapping.get(value, "BREAK")


def sub_list_line_wrap(value: int) -> str:
    """SubList line wrap: 0=BREAK, 1=SQUEEZE, 2=KEEP"""
    mapping = {0: "BREAK", 1: "SQUEEZE", 2: "KEEP"}
    return mapping.get(value, "BREAK")


def column_type(value: int) -> str:
    """Column type: 0=NEWSPAPER, 1=BALANCED_NEWSPAPER, 2=PARALLEL"""
    mapping = {0: "NEWSPAPER", 1: "BALANCED_NEWSPAPER", 2: "PARALLEL"}
    return mapping.get(value, "NEWSPAPER")


def column_layout(value: int) -> str:
    """Column layout: 0=LEFT, 1=RIGHT, 2=MIRROR"""
    mapping = {0: "LEFT", 1: "RIGHT", 2: "MIRROR"}
    return mapping.get(value, "LEFT")


def font_type(value: int) -> str:
    """Font type: 0=Unknown->REP, 1=TTF, 2=HFT"""
    mapping = {0: "REP", 1: "TTF", 2: "HFT"}
    return mapping.get(value, "REP")


def font_family(value: int) -> str:
    """Font family: 0=FCAT_UNKNOWN through 7=FCAT_NONRECTGT"""
    mapping = {
        0: "FCAT_UNKNOWN", 1: "FCAT_MYUNGJO", 2: "FCAT_GOTHIC",
        3: "FCAT_SSERIF", 4: "FCAT_BRUSHSCRIPT", 5: "FCAT_DECORATIVE",
        6: "FCAT_NONRECTMJ", 7: "FCAT_NONRECTGT"
    }
    return mapping.get(value, "FCAT_UNKNOWN")


def line_cap(value: int) -> str:
    """Line cap: 0=ROUND, 1=FLAT"""
    mapping = {0: "ROUND", 1: "FLAT"}
    return mapping.get(value, "ROUND")


def arrow_style(value: int) -> str:
    """Arrow style"""
    mapping = {
        0: "NORMAL", 1: "ARROW", 2: "SPEAR",
        3: "CONCAVE_ARROW", 4: "EMPTY_DIAMOND",
        5: "EMPTY_CIRCLE", 6: "EMPTY_BOX"
    }
    return mapping.get(value, "NORMAL")


def arrow_size(value: int) -> str:
    """Arrow size: 0-8 mapping"""
    mapping = {
        0: "SMALL_SMALL", 1: "SMALL_MEDIUM", 2: "SMALL_LARGE",
        3: "MEDIUM_SMALL", 4: "MEDIUM_MEDIUM", 5: "MEDIUM_LARGE",
        6: "LARGE_SMALL", 7: "LARGE_MEDIUM", 8: "LARGE_LARGE"
    }
    return mapping.get(value, "MEDIUM_MEDIUM")


def arc_type(value: int) -> str:
    """Arc type: 0=NORMAL, 1=PIE, 2=CHORD"""
    mapping = {0: "NORMAL", 1: "PIE", 2: "CHORD"}
    return mapping.get(value, "NORMAL")


def gradation_type(value: int) -> str:
    """Gradation: 1=LINEAR, 2=RADIAL, 3=CONICAL, 4=SQUARE"""
    mapping = {1: "LINEAR", 2: "RADIAL", 3: "CONICAL", 4: "SQUARE"}
    return mapping.get(value, "LINEAR")


def image_fill_mode(value: int) -> str:
    """Image fill mode"""
    mapping = {
        0: "TILE", 1: "TILE_HORZ_TOP", 2: "TILE_HORZ_BOTTOM",
        3: "TILE_VERT_LEFT", 4: "TILE_VERT_RIGHT",
        5: "TOTAL", 6: "CENTER", 7: "CENTER_TOP",
        8: "CENTER_BOTTOM", 9: "LEFT_CENTER", 10: "LEFT_TOP",
        11: "LEFT_BOTTOM", 12: "RIGHT_CENTER", 13: "RIGHT_TOP",
        14: "RIGHT_BOTTOM", 15: "ZOOM"
    }
    return mapping.get(value, "TILE")


def image_effect(value: int) -> str:
    """Picture effect: 0=REAL_PIC, 1=GRAY_SCALE, 2=BLACK_WHITE"""
    mapping = {0: "REAL_PIC", 1: "GRAY_SCALE", 2: "BLACK_WHITE"}
    return mapping.get(value, "REAL_PIC")


def hatch_style(value: int) -> str:
    """Hatch pattern style"""
    mapping = {
        0: "HORIZONTAL", 1: "VERTICAL", 2: "BACK_SLASH",
        3: "SLASH", 4: "CROSS", 5: "CROSS_DIAGONAL"
    }
    return mapping.get(value, "HORIZONTAL")


def slash_type(value: int) -> str:
    """Slash diagonal type"""
    mapping = {
        0: "NONE", 1: "CENTER", 2: "CENTER_BELOW",
        3: "CENTER_ABOVE", 4: "ALL"
    }
    return mapping.get(value, "NONE")


def center_line(value: int) -> str:
    """Center line: 0=NONE, 1=HORIZONTAL, 2=VERTICAL, 3=CROSS"""
    mapping = {0: "NONE", 1: "HORIZONTAL", 2: "VERTICAL", 3: "CROSS"}
    return mapping.get(value, "NONE")


def shadow_type_gso(value: int) -> str:
    """GSO Shadow type"""
    mapping = {
        0: "NONE", 1: "PARELLEL_LEFTTOP", 2: "PARELLEL_RIGHTTOP",
        3: "PARELLEL_LEFTBOTTOM", 4: "PARELLEL_RIGHTBOTTOM",
        5: "SHEAR_LEFTTOP", 6: "SHEAR_RIGHTTOP",
        7: "SHEAR_LEFTBOTTOM", 8: "SHEAR_RIGHTBOTTOM",
        9: "SCALE_NARROW", 10: "SCALE_ENLARGE"
    }
    return mapping.get(value, "NONE")


def outline_style(value: int) -> str:
    """Outline style: 0=NORMAL, 1=OUTER, 2=INNER"""
    mapping = {0: "NORMAL", 1: "OUTER", 2: "INNER"}
    return mapping.get(value, "NORMAL")


def connect_line_type(value: int) -> str:
    """Connect line type"""
    mapping = {
        0: "STRAIGHT_NOARROW", 1: "STRAIGHT_ONEWAY", 2: "STRAIGHT_BOTH",
        3: "STROKE_NOARROW", 4: "STROKE_ONEWAY", 5: "STROKE_BOTH",
        6: "ARC_NOARROW", 7: "ARC_ONEWAY", 8: "ARC_BOTH"
    }
    return mapping.get(value, "STRAIGHT_NOARROW")


def ole_object_type(value: int) -> str:
    """OLE object type: 0=UNKNOWN, 1=EMBEDDED, 2=LINK, 3=STATIC, 4=EQUATION"""
    mapping = {0: "UNKNOWN", 1: "EMBEDDED", 2: "LINK", 3: "STATIC", 4: "EQUATION"}
    return mapping.get(value, "UNKNOWN")


def draw_aspect(value: int) -> str:
    """OLE draw aspect: 0=CONTENT, 1=THUMBNAIL, 2=ICON, 3=DOCPRINT"""
    mapping = {0: "CONTENT", 1: "THUMBNAIL", 2: "ICON", 3: "DOCPRINT"}
    return mapping.get(value, "CONTENT")


def apply_page_type(value: int) -> str:
    """Apply page type: 0=BOTH, 1=EVEN, 2=ODD"""
    mapping = {0: "BOTH", 1: "EVEN", 2: "ODD"}
    return mapping.get(value, "BOTH")


def num_type(value: int) -> str:
    """Number sort type"""
    mapping = {
        0: "PAGE", 1: "FOOTNOTE", 2: "ENDNOTE",
        3: "PICTURE", 4: "TABLE", 5: "EQUATION"
    }
    return mapping.get(value, "PAGE")


def tab_item_type(value: int) -> str:
    """Tab type: 0=LEFT, 1=RIGHT, 2=CENTER, 3=DECIMAL"""
    mapping = {0: "LEFT", 1: "RIGHT", 2: "CENTER", 3: "DECIMAL"}
    return mapping.get(value, "LEFT")


def page_starts_on(value: int) -> str:
    """Page starts on: 0=BOTH, 1=BOTH(even), 2=EVEN, 3=null(custom)"""
    mapping = {0: "BOTH", 1: "BOTH", 2: "EVEN"}
    return mapping.get(value, "BOTH")


def visibility_border(hide: bool) -> str:
    """Border visibility"""
    return "HIDE_FIRST" if hide else "SHOW_ALL"


def visibility_fill(hide: bool) -> str:
    """Fill visibility"""
    return "HIDE_FIRST" if hide else "SHOW_ALL"


def media_type(extension: str) -> str:
    """File extension -> MIME type"""
    ext = extension.lower().strip('.')
    mapping = {
        'emf': 'image/emf', 'gif': 'image/gif', 'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg', 'png': 'image/png', 'svg': 'image/svg+xml',
        'tif': 'image/tiff', 'tiff': 'image/tiff', 'wmf': 'image/wmf',
        'bmp': 'image/bmp', 'ole': 'application/x-ole-object'
    }
    return mapping.get(ext, 'image/unknown')


def to_unsigned(value: int) -> int:
    """Convert signed 32-bit to unsigned"""
    if value < 0:
        return value + (1 << 32)
    return value
