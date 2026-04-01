"""Character property objects: CharPr, ValuesByLanguage, Underline, Strikeout,
Outline, CharShadow.

Ported from kr.dogfoot.hwpxlib.object.content.header_xml.references.CharPr
and kr.dogfoot.hwpxlib.object.content.header_xml.references.charpr.*
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Generic, Optional, TypeVar

from ....base import HWPXObject, SwitchableObject
from ....object_type import ObjectType
from ..enum_types import (
    CharShadowType,
    LineType1,
    LineType2,
    LineType3,
    SymMarkSort,
    UnderlineType,
)
from ..header_xml_file import NoAttributeNoChild

T = TypeVar("T")


# ---------------------------------------------------------------------------
# ValuesByLanguage
# ---------------------------------------------------------------------------

@dataclass
class ValuesByLanguage(HWPXObject, Generic[T]):
    """Per-language values (hangul, latin, hanja, japanese, other, symbol, user)."""

    _object_type_value: ObjectType = field(default=ObjectType.Unknown)
    hangul: Optional[T] = None
    latin: Optional[T] = None
    hanja: Optional[T] = None
    japanese: Optional[T] = None
    other: Optional[T] = None
    symbol: Optional[T] = None
    user: Optional[T] = None

    def __init__(self, object_type: ObjectType = ObjectType.Unknown):
        self._object_type_value = object_type
        self.hangul = None
        self.latin = None
        self.hanja = None
        self.japanese = None
        self.other = None
        self.symbol = None
        self.user = None

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def set(
        self,
        hangul: Optional[T],
        latin: Optional[T],
        hanja: Optional[T],
        japanese: Optional[T],
        other: Optional[T],
        symbol: Optional[T],
        user: Optional[T],
    ) -> None:
        self.hangul = hangul
        self.latin = latin
        self.hanja = hanja
        self.japanese = japanese
        self.other = other
        self.symbol = symbol
        self.user = user

    def set_all(self, value: T) -> None:
        self.hangul = value
        self.latin = value
        self.hanja = value
        self.japanese = value
        self.other = value
        self.symbol = value
        self.user = value

    def clone(self) -> ValuesByLanguage[T]:
        cloned = ValuesByLanguage[T](self._object_type_value)
        cloned.hangul = self.hangul
        cloned.latin = self.latin
        cloned.hanja = self.hanja
        cloned.japanese = self.japanese
        cloned.other = self.other
        cloned.symbol = self.symbol
        cloned.user = self.user
        return cloned


# ---------------------------------------------------------------------------
# Underline
# ---------------------------------------------------------------------------

@dataclass
class Underline(HWPXObject):
    """Character underline settings."""

    type: Optional[UnderlineType] = None
    shape: Optional[LineType3] = None
    color: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_underline

    def clone(self) -> Underline:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Strikeout
# ---------------------------------------------------------------------------

@dataclass
class Strikeout(HWPXObject):
    """Character strikeout settings."""

    shape: Optional[LineType2] = None
    color: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_strikeout

    def clone(self) -> Strikeout:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Outline
# ---------------------------------------------------------------------------

@dataclass
class Outline(HWPXObject):
    """Character outline settings."""

    type: Optional[LineType1] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_outline

    def clone(self) -> Outline:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# CharShadow
# ---------------------------------------------------------------------------

@dataclass
class CharShadow(HWPXObject):
    """Character shadow settings."""

    type: Optional[CharShadowType] = None
    color: Optional[str] = None
    offsetX: Optional[int] = None
    offsetY: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_shadow

    def clone(self) -> CharShadow:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# CharPr
# ---------------------------------------------------------------------------

@dataclass
class CharPr(SwitchableObject):
    """Character properties (font, size, color, decorations, etc.)."""

    id: Optional[str] = None
    height: Optional[int] = None
    textColor: Optional[str] = None
    shadeColor: Optional[str] = None
    useFontSpace: Optional[bool] = None
    useKerning: Optional[bool] = None
    symMark: Optional[SymMarkSort] = None
    borderFillIDRef: Optional[str] = None

    fontRef: Optional[ValuesByLanguage[str]] = None
    ratio: Optional[ValuesByLanguage[int]] = None
    spacing: Optional[ValuesByLanguage[int]] = None
    relSz: Optional[ValuesByLanguage[int]] = None
    offset: Optional[ValuesByLanguage[int]] = None

    italic: Optional[NoAttributeNoChild] = None
    bold: Optional[NoAttributeNoChild] = None
    underline: Optional[Underline] = None
    strikeout: Optional[Strikeout] = None
    outline: Optional[Outline] = None
    shadow: Optional[CharShadow] = None
    emboss: Optional[NoAttributeNoChild] = None
    engrave: Optional[NoAttributeNoChild] = None
    supscript: Optional[NoAttributeNoChild] = None
    subscript: Optional[NoAttributeNoChild] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_charPr

    # -- factory helpers --

    def create_font_ref(self) -> ValuesByLanguage[str]:
        self.fontRef = ValuesByLanguage[str](ObjectType.hh_fontRef)
        return self.fontRef

    def remove_font_ref(self) -> None:
        self.fontRef = None

    def create_ratio(self) -> ValuesByLanguage[int]:
        self.ratio = ValuesByLanguage[int](ObjectType.hh_ratio)
        return self.ratio

    def remove_ratio(self) -> None:
        self.ratio = None

    def create_spacing(self) -> ValuesByLanguage[int]:
        self.spacing = ValuesByLanguage[int](ObjectType.hh_spacing)
        return self.spacing

    def remove_spacing(self) -> None:
        self.spacing = None

    def create_rel_sz(self) -> ValuesByLanguage[int]:
        self.relSz = ValuesByLanguage[int](ObjectType.hh_relSz)
        return self.relSz

    def remove_rel_sz(self) -> None:
        self.relSz = None

    def create_offset(self) -> ValuesByLanguage[int]:
        self.offset = ValuesByLanguage[int](ObjectType.hh_offset)
        return self.offset

    def remove_offset(self) -> None:
        self.offset = None

    def create_italic(self) -> NoAttributeNoChild:
        self.italic = NoAttributeNoChild(ObjectType.hh_italic)
        return self.italic

    def remove_italic(self) -> None:
        self.italic = None

    def create_bold(self) -> NoAttributeNoChild:
        self.bold = NoAttributeNoChild(ObjectType.hh_bold)
        return self.bold

    def remove_bold(self) -> None:
        self.bold = None

    def create_underline(self) -> Underline:
        self.underline = Underline()
        return self.underline

    def remove_underline(self) -> None:
        self.underline = None

    def create_strikeout(self) -> Strikeout:
        self.strikeout = Strikeout()
        return self.strikeout

    def remove_strikeout(self) -> None:
        self.strikeout = None

    def create_outline(self) -> Outline:
        self.outline = Outline()
        return self.outline

    def remove_outline(self) -> None:
        self.outline = None

    def create_shadow(self) -> CharShadow:
        self.shadow = CharShadow()
        return self.shadow

    def remove_shadow(self) -> None:
        self.shadow = None

    def create_emboss(self) -> NoAttributeNoChild:
        self.emboss = NoAttributeNoChild(ObjectType.hh_emboss)
        return self.emboss

    def remove_emboss(self) -> None:
        self.emboss = None

    def create_engrave(self) -> NoAttributeNoChild:
        self.engrave = NoAttributeNoChild(ObjectType.hh_engrave)
        return self.engrave

    def remove_engrave(self) -> None:
        self.engrave = None

    def create_supscript(self) -> NoAttributeNoChild:
        self.supscript = NoAttributeNoChild(ObjectType.hh_supscript)
        return self.supscript

    def remove_supscript(self) -> None:
        self.supscript = None

    def create_subscript(self) -> NoAttributeNoChild:
        self.subscript = NoAttributeNoChild(ObjectType.hh_subscript)
        return self.subscript

    def remove_subscript(self) -> None:
        self.subscript = None

    def clone(self) -> CharPr:
        return copy.deepcopy(self)
