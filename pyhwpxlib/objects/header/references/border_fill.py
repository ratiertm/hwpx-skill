"""BorderFill-related objects: BorderFill, SlashCore, Border, FillBrush,
WinBrush, Gradation, Color, ImgBrush, Image.

Ported from kr.dogfoot.hwpxlib.object.content.header_xml.references.BorderFill
and kr.dogfoot.hwpxlib.object.content.header_xml.references.borderfill.*
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from ....base import HWPXObject, SwitchableObject
from ....object_type import ObjectType
from ..enum_types import (
    CenterLineSort,
    GradationType,
    HatchStyle,
    ImageBrushMode,
    ImageEffect,
    LineType2,
    LineWidth,
    SlashType,
)


# ---------------------------------------------------------------------------
# Color  (gradation stop color)
# ---------------------------------------------------------------------------

@dataclass
class Color(HWPXObject):
    """Color value for gradation stops."""

    value: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hc_color

    def clone(self) -> Color:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# SlashCore  (diagonal line info)
# ---------------------------------------------------------------------------

@dataclass
class SlashCore(HWPXObject):
    """Diagonal slash/backslash info."""

    _object_type_value: ObjectType = field(default=ObjectType.hh_slash)
    type: Optional[SlashType] = None
    Crooked: Optional[bool] = None
    isCounter: Optional[bool] = None

    def __init__(self, object_type: ObjectType = ObjectType.hh_slash):
        self._object_type_value = object_type
        self.type = None
        self.Crooked = None
        self.isCounter = None

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def clone(self) -> SlashCore:
        cloned = SlashCore(self._object_type_value)
        cloned.type = self.type
        cloned.Crooked = self.Crooked
        cloned.isCounter = self.isCounter
        return cloned


# ---------------------------------------------------------------------------
# Border  (single border edge)
# ---------------------------------------------------------------------------

@dataclass
class Border(HWPXObject):
    """Border line definition (left/right/top/bottom/diagonal)."""

    _object_type_value: ObjectType = field(default=ObjectType.hh_leftBorder)
    type: Optional[LineType2] = None
    width: Optional[LineWidth] = None
    color: Optional[str] = None

    def __init__(self, object_type: ObjectType = ObjectType.hh_leftBorder):
        self._object_type_value = object_type
        self.type = None
        self.width = None
        self.color = None

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def clone(self) -> Border:
        cloned = Border(self._object_type_value)
        cloned.type = self.type
        cloned.width = self.width
        cloned.color = self.color
        return cloned


# ---------------------------------------------------------------------------
# WinBrush  (basic fill)
# ---------------------------------------------------------------------------

@dataclass
class WinBrush(HWPXObject):
    """Basic fill brush (face color, hatch pattern)."""

    faceColor: Optional[str] = None
    hatchColor: Optional[str] = None
    hatchStyle: Optional[HatchStyle] = None
    alpha: Optional[float] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hc_winBrush

    def clone(self) -> WinBrush:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Image  (image info for fills and bullets)
# ---------------------------------------------------------------------------

@dataclass
class Image(HWPXObject):
    """Image info (binary reference, brightness, contrast, effect)."""

    binaryItemIDRef: Optional[str] = None
    bright: Optional[int] = None
    contrast: Optional[int] = None
    effect: Optional[ImageEffect] = None
    alpha: Optional[float] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hc_img

    def clone(self) -> Image:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# ImgBrush  (image fill)
# ---------------------------------------------------------------------------

@dataclass
class ImgBrush(SwitchableObject):
    """Image fill brush."""

    mode: Optional[ImageBrushMode] = None
    img: Optional[Image] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hc_imgBrush

    def create_img(self) -> Image:
        self.img = Image()
        return self.img

    def remove_img(self) -> None:
        self.img = None

    def clone(self) -> ImgBrush:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Gradation  (gradient fill)
# ---------------------------------------------------------------------------

@dataclass
class Gradation(SwitchableObject):
    """Gradient fill definition."""

    type: Optional[GradationType] = None
    angle: Optional[int] = None
    centerX: Optional[int] = None
    centerY: Optional[int] = None
    step: Optional[int] = None
    stepCenter: Optional[int] = None
    alpha: Optional[float] = None
    _color_list: List[Color] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hc_gradation

    def count_of_color(self) -> int:
        return len(self._color_list)

    def get_color(self, index: int) -> Color:
        return self._color_list[index]

    def add_color(self, color: Color) -> None:
        self._color_list.append(color)

    def add_new_color(self) -> Color:
        color = Color()
        self._color_list.append(color)
        return color

    def insert_color(self, color: Color, position: int) -> None:
        self._color_list.insert(position, color)

    def remove_color(self, position_or_color) -> None:
        if isinstance(position_or_color, int):
            del self._color_list[position_or_color]
        else:
            self._color_list.remove(position_or_color)

    def remove_all_colors(self) -> None:
        self._color_list.clear()

    def colors(self) -> List[Color]:
        return self._color_list

    def __iter__(self) -> Iterator[Color]:
        return iter(self._color_list)

    def clone(self) -> Gradation:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# FillBrush  (container for fill types)
# ---------------------------------------------------------------------------

@dataclass
class FillBrush(SwitchableObject):
    """Fill brush container (winBrush, gradation, imgBrush)."""

    winBrush: Optional[WinBrush] = None
    gradation: Optional[Gradation] = None
    imgBrush: Optional[ImgBrush] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hc_fillBrush

    def create_win_brush(self) -> WinBrush:
        self.winBrush = WinBrush()
        return self.winBrush

    def remove_win_brush(self) -> None:
        self.winBrush = None

    def create_gradation(self) -> Gradation:
        self.gradation = Gradation()
        return self.gradation

    def remove_gradation(self) -> None:
        self.gradation = None

    def create_img_brush(self) -> ImgBrush:
        self.imgBrush = ImgBrush()
        return self.imgBrush

    def remove_img_brush(self) -> None:
        self.imgBrush = None

    def clone(self) -> FillBrush:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# BorderFill
# ---------------------------------------------------------------------------

@dataclass
class BorderFill(SwitchableObject):
    """Border and fill properties."""

    id: Optional[str] = None
    threeD: Optional[bool] = None
    shadow: Optional[bool] = None
    centerLine: Optional[CenterLineSort] = None
    breakCellSeparateLine: Optional[bool] = None

    slash: Optional[SlashCore] = None
    backSlash: Optional[SlashCore] = None
    leftBorder: Optional[Border] = None
    rightBorder: Optional[Border] = None
    topBorder: Optional[Border] = None
    bottomBorder: Optional[Border] = None
    diagonal: Optional[Border] = None
    fillBrush: Optional[FillBrush] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_borderFill

    # -- factory helpers --

    def create_slash(self) -> SlashCore:
        self.slash = SlashCore(ObjectType.hh_slash)
        return self.slash

    def remove_slash(self) -> None:
        self.slash = None

    def create_back_slash(self) -> SlashCore:
        self.backSlash = SlashCore(ObjectType.hh_backSlash)
        return self.backSlash

    def remove_back_slash(self) -> None:
        self.backSlash = None

    def create_left_border(self) -> Border:
        self.leftBorder = Border(ObjectType.hh_leftBorder)
        return self.leftBorder

    def remove_left_border(self) -> None:
        self.leftBorder = None

    def create_right_border(self) -> Border:
        self.rightBorder = Border(ObjectType.hh_rightBorder)
        return self.rightBorder

    def remove_right_border(self) -> None:
        self.rightBorder = None

    def create_top_border(self) -> Border:
        self.topBorder = Border(ObjectType.hh_topBorder)
        return self.topBorder

    def remove_top_border(self) -> None:
        self.topBorder = None

    def create_bottom_border(self) -> Border:
        self.bottomBorder = Border(ObjectType.hh_bottomBorder)
        return self.bottomBorder

    def remove_bottom_border(self) -> None:
        self.bottomBorder = None

    def create_diagonal(self) -> Border:
        self.diagonal = Border(ObjectType.hh_diagonal)
        return self.diagonal

    def remove_diagonal(self) -> None:
        self.diagonal = None

    def create_fill_brush(self) -> FillBrush:
        self.fillBrush = FillBrush()
        return self.fillBrush

    def remove_fill_brush(self) -> None:
        self.fillBrush = None

    def clone(self) -> BorderFill:
        return copy.deepcopy(self)
