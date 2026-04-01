"""Enum types for header.xml objects.

Ported from kr.dogfoot.hwpxlib.object.content.header_xml.enumtype.*
Each enum stores a string value (str) matching the HWPX XML attribute values.
"""
from __future__ import annotations

from enum import Enum


class CenterLineSort(Enum):
    NONE = "NONE"
    VERTICAL = "VERTICAL"
    HORIZONTAL = "HORIZONTAL"
    CROSS = "CROSS"

    @classmethod
    def from_string(cls, s: str | None) -> CenterLineSort | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class CharShadowType(Enum):
    NONE = "NONE"
    DROP = "DROP"
    CONTINUOUS = "CONTINUOUS"

    @classmethod
    def from_string(cls, s: str | None) -> CharShadowType | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class FontFamilyType(Enum):
    FCAT_UNKNOWN = "FCAT_UNKNOWN"
    FCAT_MYUNGJO = "FCAT_MYUNGJO"
    FCAT_GOTHIC = "FCAT_GOTHIC"
    FCAT_SSERIF = "FCAT_SSERIF"
    FCAT_BRUSHSCRIPT = "FCAT_BRUSHSCRIPT"
    FCAT_DECORATIVE = "FCAT_DECORATIVE"
    FCAT_NONRECTMJ = "FCAT_NONRECTMJ"
    FCAT_NONRECTGT = "FCAT_NONRECTGT"

    @classmethod
    def from_string(cls, s: str | None) -> FontFamilyType | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class FontLanguage(Enum):
    HANGUL = "HANGUL"
    LATIN = "LATIN"
    HANJA = "HANJA"
    JAPANESE = "JAPANESE"
    OTHER = "OTHER"
    SYMBOL = "SYMBOL"
    USER = "USER"


class FontType(Enum):
    """REP=representative, TTF=TrueType, HFT=Hangul-only."""
    REP = "REP"
    TTF = "TTF"
    HFT = "HFT"

    @classmethod
    def from_string(cls, s: str | None) -> FontType | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class GradationType(Enum):
    LINEAR = "LINEAR"
    RADIAL = "RADIAL"
    CONICAL = "CONICAL"
    SQUARE = "SQUARE"

    @classmethod
    def from_string(cls, s: str | None) -> GradationType | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class HatchStyle(Enum):
    HORIZONTAL = "HORIZONTAL"
    VERTICAL = "VERTICAL"
    BACK_SLASH = "BACK_SLASH"
    SLASH = "SLASH"
    CROSS = "CROSS"
    CROSS_DIAGONAL = "CROSS_DIAGONAL"

    @classmethod
    def from_string(cls, s: str | None) -> HatchStyle | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class HorizontalAlign1(Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    CENTER = "CENTER"

    @classmethod
    def from_string(cls, s: str | None) -> HorizontalAlign1 | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class HorizontalAlign2(Enum):
    JUSTIFY = "JUSTIFY"
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    CENTER = "CENTER"
    DISTRIBUTE = "DISTRIBUTE"
    DISTRIBUTE_SPACE = "DISTRIBUTE_SPACE"

    @classmethod
    def from_string(cls, s: str | None) -> HorizontalAlign2 | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class ImageBrushMode(Enum):
    TILE = "TILE"
    TILE_HORZ_TOP = "TILE_HORZ_TOP"
    TILE_HORZ_BOTTOM = "TILE_HORZ_BOTTOM"
    TILE_VERT_LEFT = "TILE_VERT_LEFT"
    TILE_VERT_RIGHT = "TILE_VERT_RIGHT"
    TOTAL = "TOTAL"
    CENTER = "CENTER"
    CENTER_TOP = "CENTER_TOP"
    CENTER_BOTTOM = "CENTER_BOTTOM"
    LEFT_CENTER = "LEFT_CENTER"
    LEFT_TOP = "LEFT_TOP"
    LEFT_BOTTOM = "LEFT_BOTTOM"
    RIGHT_CENTER = "RIGHT_CENTER"
    RIGHT_TOP = "RIGHT_TOP"
    RIGHT_BOTTOM = "RIGHT_BOTTOM"
    ZOOM = "ZOOM"

    @classmethod
    def from_string(cls, s: str | None) -> ImageBrushMode | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class ImageEffect(Enum):
    REAL_PIC = "REAL_PIC"
    GRAY_SCALE = "GRAY_SCALE"
    BLACK_WHITE = "BLACK_WHITE"

    @classmethod
    def from_string(cls, s: str | None) -> ImageEffect | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class LanguageType(Enum):
    HANGUL = "HANGUL"
    LATIN = "LATIN"
    HANJA = "HANJA"
    JAPANESE = "JAPANESE"
    OTHER = "OTHER"
    SYMBOL = "SYMBOL"
    USER = "USER"

    @classmethod
    def from_string(cls, s: str | None) -> LanguageType | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class LineBreakForLatin(Enum):
    KEEP_WORD = "KEEP_WORD"
    HYPHENATION = "HYPHENATION"
    BREAK_WORD = "BREAK_WORD"

    @classmethod
    def from_string(cls, s: str | None) -> LineBreakForLatin | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class LineBreakForNonLatin(Enum):
    KEEP_WORD = "KEEP_WORD"
    BREAK_WORD = "BREAK_WORD"

    @classmethod
    def from_string(cls, s: str | None) -> LineBreakForNonLatin | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class LineSpacingType(Enum):
    PERCENT = "PERCENT"
    FIXED = "FIXED"
    BETWEEN_LINES = "BETWEEN_LINES"
    AT_LEAST = "AT_LEAST"

    @classmethod
    def from_string(cls, s: str | None) -> LineSpacingType | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class LineType1(Enum):
    NONE = "NONE"
    SOLID = "SOLID"
    DOT = "DOT"
    THICK = "THICK"
    DASH = "DASH"
    DASH_DOT = "DASH_DOT"
    DASH_DOT_DOT = "DASH_DOT_DOT"

    @classmethod
    def from_string(cls, s: str | None) -> LineType1 | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class LineType2(Enum):
    NONE = ("NONE", 0)
    SOLID = ("SOLID", 1)
    DOT = ("DOT", 2)
    DASH = ("DASH", 3)
    DASH_DOT = ("DASH_DOT", 4)
    DASH_DOT_DOT = ("DASH_DOT_DOT", 5)
    LONG_DASH = ("LONG_DASH", 6)
    CIRCLE = ("CIRCLE", 7)
    DOUBLE_SLIM = ("DOUBLE_SLIM", 8)
    SLIM_THICK = ("SLIM_THICK", 9)
    THICK_SLIM = ("THICK_SLIM", 10)
    SLIM_THICK_SLIM = ("SLIM_THICK_SLIM", 11)

    def __init__(self, str_val: str, index: int):
        self.str = str_val
        self.index = index

    @classmethod
    def from_string(cls, s: str | None) -> LineType2 | None:
        if s is None:
            return None
        for item in cls:
            if item.str == s.upper():
                return item
        return None

    @classmethod
    def from_index(cls, index: int) -> LineType2 | None:
        for item in cls:
            if item.index == index:
                return item
        return None


class LineType3(Enum):
    SOLID = "SOLID"
    DOT = "DOT"
    DASH = "DASH"
    DASH_DOT = "DASH_DOT"
    DASH_DOT_DOT = "DASH_DOT_DOT"
    LONG_DASH = "LONG_DASH"
    CIRCLE = "CIRCLE"
    DOUBLE_SLIM = "DOUBLE_SLIM"
    SLIM_THICK = "SLIM_THICK"
    THICK_SLIM = "THICK_SLIM"
    SLIM_THICK_SLIM = "SLIM_THICK_SLIM"
    WAVE = "WAVE"
    DOUBLEWAVE = "DOUBLEWAVE"

    @classmethod
    def from_string(cls, s: str | None) -> LineType3 | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class LineWidth(Enum):
    MM_0_1 = ("0.1 mm", 0)
    MM_0_12 = ("0.12 mm", 1)
    MM_0_15 = ("0.15 mm", 2)
    MM_0_2 = ("0.2 mm", 3)
    MM_0_25 = ("0.25 mm", 4)
    MM_0_3 = ("0.3 mm", 5)
    MM_0_4 = ("0.4 mm", 6)
    MM_0_5 = ("0.5 mm", 7)
    MM_0_6 = ("0.6 mm", 8)
    MM_0_7 = ("0.7 mm", 9)
    MM_1_0 = ("1.0 mm", 10)
    MM_1_5 = ("1.5 mm", 11)
    MM_2_0 = ("2.0 mm", 12)
    MM_3_0 = ("3.0 mm", 13)
    MM_4_0 = ("4.0 mm", 14)
    MM_5_0 = ("5.0 mm", 15)

    def __init__(self, str_val: str, index: int):
        self.str = str_val
        self.index = index

    @classmethod
    def from_string(cls, s: str | None) -> LineWidth | None:
        if s is None:
            return None
        for item in cls:
            if item.str == s:
                return item
        return None

    @classmethod
    def from_index(cls, index: int) -> LineWidth | None:
        for item in cls:
            if item.index == index:
                return item
        return None


class LineWrap(Enum):
    BREAK = "BREAK"
    SQUEEZE = "SQUEEZE"
    KEEP = "KEEP"

    @classmethod
    def from_string(cls, s: str | None) -> LineWrap | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class MemoType(Enum):
    NORMAL = "NORMAL"
    USER_INSERT = "USER_INSERT"
    USER_DELETE = "USER_DELETE"
    USER_UPDATE = "USER_UPDATE"

    @classmethod
    def from_string(cls, s: str | None) -> MemoType | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class NumberType1(Enum):
    DIGIT = "DIGIT"
    CIRCLED_DIGIT = "CIRCLED_DIGIT"
    ROMAN_CAPITAL = "ROMAN_CAPITAL"
    ROMAN_SMALL = "ROMAN_SMALL"
    LATIN_CAPITAL = "LATIN_CAPITAL"
    LATIN_SMALL = "LATIN_SMALL"
    CIRCLED_LATIN_CAPTION = "CIRCLED_LATIN_CAPTION"
    CIRCLED_LATIN_SMALL = "CIRCLED_LATIN_SMALL"
    HANGUL_SYLLABLE = "HANGUL_SYLLABLE"
    CIRCLED_HANGUL_SYLLABLE = "CIRCLED_HANGUL_SYLLABLE"
    HANGUL_JAMO = "HANGUL_JAMO"
    CIRCLED_HANGUL_JAMO = "CIRCLED_HANGUL_JAMO"
    HANGUL_PHONETIC = "HANGUL_PHONETIC"
    IDEOGRAPH = "IDEOGRAPH"
    CIRCLED_IDEOGRAPH = "CIRCLED_IDEOGRAPH"

    @classmethod
    def from_string(cls, s: str | None) -> NumberType1 | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class ParaHeadingType(Enum):
    NONE = "NONE"
    OUTLINE = "OUTLINE"
    NUMBER = "NUMBER"
    BULLET = "BULLET"

    @classmethod
    def from_string(cls, s: str | None) -> ParaHeadingType | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class SlashType(Enum):
    NONE = "NONE"
    CENTER = "CENTER"
    CENTER_BELOW = "CENTER_BELOW"
    CENTER_ABOVE = "CENTER_ABOVE"
    ALL = "ALL"

    @classmethod
    def from_string(cls, s: str | None) -> SlashType | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class StyleType(Enum):
    PARA = "PARA"
    CHAR = "CHAR"

    @classmethod
    def from_string(cls, s: str | None) -> StyleType | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class SymMarkSort(Enum):
    NONE = "NONE"
    DOT_ABOVE = "DOT_ABOVE"
    RING_ABOVE = "RING_ABOVE"
    TILDE = "TILDE"
    CARON = "CARON"
    SIDE = "SIDE"
    COLON = "COLON"
    GRAVE_ACCENT = "GRAVE_ACCENT"
    ACUTE_ACCENT = "ACUTE_ACCENT"
    CIRCUMFLEX = "CIRCUMFLEX"
    MACRON = "MACRON"
    HOOK_ABOVE = "HOOK_ABOVE"
    DOT_BELOW = "DOT_BELOW"

    @classmethod
    def from_string(cls, s: str | None) -> SymMarkSort | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class TabItemType(Enum):
    LEFT = ("LEFT", 1)
    RIGHT = ("RIGHT", 2)
    CENTER = ("CENTER", 3)
    DECIMAL = ("DECIMAL", 4)

    def __init__(self, str_val: str, index: int):
        self.str = str_val
        self.index = index

    @classmethod
    def from_string(cls, s: str | None) -> TabItemType | None:
        if s is None:
            return None
        for item in cls:
            if item.str == s.upper():
                return item
        return None

    @classmethod
    def from_index(cls, index: int) -> TabItemType | None:
        for item in cls:
            if item.index == index:
                return item
        return None


class TargetApplicationSort(Enum):
    WordProcessor = "WORDPROCESSOR"
    Presentation = "PRESENTATION"
    SpreadSheet = "SPREADSHEET"

    @classmethod
    def from_string(cls, s: str | None) -> TargetApplicationSort | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class TargetProgramSort(Enum):
    HWP201X = "HWP201X"
    HWP200X = "HWP200X"
    MS_WORD = "MS_WORD"

    @classmethod
    def from_string(cls, s: str | None) -> TargetProgramSort | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class TrackChangeType(Enum):
    Unknown = "Unknown"
    Delete = "Delete"
    Insert = "Insert"
    CharShape = "CharShape"
    ParaShape = "ParaShape"

    @classmethod
    def from_string(cls, s: str | None) -> TrackChangeType | None:
        if s is None:
            return None
        for item in cls:
            if item.value.upper() == s.upper():
                return item
        return None


class UnderlineType(Enum):
    NONE = "NONE"
    TOP = "TOP"
    BOTTOM = "BOTTOM"

    @classmethod
    def from_string(cls, s: str | None) -> UnderlineType | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class ValueUnit1(Enum):
    PERCENT = "PERCENT"
    HWPUNIT = "HWPUNIT"

    @classmethod
    def from_string(cls, s: str | None) -> ValueUnit1 | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class ValueUnit2(Enum):
    CHAR = "CHAR"
    HWPUNIT = "HWPUNIT"

    @classmethod
    def from_string(cls, s: str | None) -> ValueUnit2 | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None


class VerticalAlign1(Enum):
    BASELINE = "BASELINE"
    TOP = "TOP"
    CENTER = "CENTER"
    BOTTOM = "BOTTOM"

    @classmethod
    def from_string(cls, s: str | None) -> VerticalAlign1 | None:
        if s is None:
            return None
        for item in cls:
            if item.value == s.upper():
                return item
        return None
