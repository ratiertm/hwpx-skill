"""Fontface-related objects: Fontfaces, Fontface, Font, SubstFont, TypeInfo.

Ported from kr.dogfoot.hwpxlib.object.content.header_xml.references.fontface.*
and kr.dogfoot.hwpxlib.object.content.header_xml.references.Fontface(s).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from ....base import HWPXObject, SwitchableObject
from ....object_type import ObjectType
from ..enum_types import FontFamilyType, FontType, LanguageType


# ---------------------------------------------------------------------------
# TypeInfo
# ---------------------------------------------------------------------------

@dataclass
class TypeInfo(HWPXObject):
    """Font detail information (PANOSE-like)."""

    familyType: Optional[FontFamilyType] = None
    serifStyle: Optional[str] = None
    weight: Optional[int] = None
    proportion: Optional[int] = None
    contrast: Optional[int] = None
    strokeVariation: Optional[int] = None
    armStyle: Optional[bool] = None
    letterform: Optional[bool] = None
    midline: Optional[int] = None
    xHeight: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_typeInfo

    def clone(self) -> TypeInfo:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# SubstFont
# ---------------------------------------------------------------------------

@dataclass
class SubstFont(HWPXObject):
    """Substitute font information."""

    face: Optional[str] = None
    type: Optional[FontType] = None
    isEmbedded: Optional[bool] = None
    binaryItemIDRef: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_substFont

    def clone(self) -> SubstFont:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Font
# ---------------------------------------------------------------------------

@dataclass
class Font(SwitchableObject):
    """A single font definition within a fontface."""

    id: Optional[str] = None
    face: Optional[str] = None
    type: Optional[FontType] = None
    isEmbedded: Optional[bool] = None
    binaryItemIDRef: Optional[str] = None
    substFont: Optional[SubstFont] = None
    typeInfo: Optional[TypeInfo] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_font

    def create_subst_font(self) -> SubstFont:
        self.substFont = SubstFont()
        return self.substFont

    def remove_subst_font(self) -> None:
        self.substFont = None

    def create_type_info(self) -> TypeInfo:
        self.typeInfo = TypeInfo()
        return self.typeInfo

    def remove_type_info(self) -> None:
        self.typeInfo = None

    def clone(self) -> Font:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Fontface  (one per language)
# ---------------------------------------------------------------------------

@dataclass
class Fontface(SwitchableObject):
    """Font list for a specific language."""

    lang: Optional[LanguageType] = None
    _font_list: List[Font] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_fontface

    def count_of_font(self) -> int:
        return len(self._font_list)

    def get_font(self, index: int) -> Font:
        return self._font_list[index]

    def get_font_index(self, font: Font) -> int:
        for i, f in enumerate(self._font_list):
            if f is font:
                return i
        return -1

    def add_font(self, font: Font) -> None:
        self._font_list.append(font)

    def add_new_font(self) -> Font:
        font = Font()
        self._font_list.append(font)
        return font

    def insert_font(self, font: Font, position: int) -> None:
        self._font_list.insert(position, font)

    def remove_font(self, position_or_font) -> None:
        if isinstance(position_or_font, int):
            del self._font_list[position_or_font]
        else:
            self._font_list.remove(position_or_font)

    def remove_all_fonts(self) -> None:
        self._font_list.clear()

    def fonts(self) -> List[Font]:
        return self._font_list

    def __iter__(self) -> Iterator[Font]:
        return iter(self._font_list)

    def clone(self) -> Fontface:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Fontfaces  (container of Fontface per language)
# ---------------------------------------------------------------------------

@dataclass
class Fontfaces(SwitchableObject):
    """Container for all fontface lists (one per language)."""

    _fontface_list: List[Fontface] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_fontfaces

    def count_of_fontface(self) -> int:
        return len(self._fontface_list)

    def get_fontface(self, index: int) -> Fontface:
        return self._fontface_list[index]

    def add_fontface(self, fontface: Fontface) -> None:
        self._fontface_list.append(fontface)

    def add_new_fontface(self) -> Fontface:
        fontface = Fontface()
        self._fontface_list.append(fontface)
        return fontface

    def insert_fontface(self, fontface: Fontface, position: int) -> None:
        self._fontface_list.insert(position, fontface)

    def remove_fontface(self, position_or_fontface) -> None:
        if isinstance(position_or_fontface, int):
            del self._fontface_list[position_or_fontface]
        else:
            self._fontface_list.remove(position_or_fontface)

    def remove_all_fontfaces(self) -> None:
        self._fontface_list.clear()

    def fontfaces(self) -> List[Fontface]:
        return self._fontface_list

    def _get_fontface_by_lang(self, lang: LanguageType) -> Optional[Fontface]:
        for ff in self._fontface_list:
            if ff.lang == lang:
                return ff
        return None

    def hangul_fontface(self) -> Optional[Fontface]:
        return self._get_fontface_by_lang(LanguageType.HANGUL)

    def latin_fontface(self) -> Optional[Fontface]:
        return self._get_fontface_by_lang(LanguageType.LATIN)

    def hanja_fontface(self) -> Optional[Fontface]:
        return self._get_fontface_by_lang(LanguageType.HANJA)

    def japanese_fontface(self) -> Optional[Fontface]:
        return self._get_fontface_by_lang(LanguageType.JAPANESE)

    def other_fontface(self) -> Optional[Fontface]:
        return self._get_fontface_by_lang(LanguageType.OTHER)

    def symbol_fontface(self) -> Optional[Fontface]:
        return self._get_fontface_by_lang(LanguageType.SYMBOL)

    def user_fontface(self) -> Optional[Fontface]:
        return self._get_fontface_by_lang(LanguageType.USER)

    def __iter__(self) -> Iterator[Fontface]:
        return iter(self._fontface_list)

    def clone(self) -> Fontfaces:
        return copy.deepcopy(self)
