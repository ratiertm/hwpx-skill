"""TextArt object model."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ....base import HWPXObject, ObjectList
from ....object_type import ObjectType
from ....objects.common.base_objects import Point
from ...section.enum_types import TextArtAlign, TextArtShape
from .drawing_object import DrawingObject


@dataclass
class TextArtPr(HWPXObject):
    """TextArt properties (hp:textartPr)."""

    font_name: Optional[str] = None
    font_style: Optional[str] = None
    font_type: Optional[str] = None  # FontType2
    text_shape: Optional[TextArtShape] = None
    line_spacing: Optional[int] = None
    char_spacing: Optional[int] = None
    align: Optional[TextArtAlign] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_textartPr


@dataclass
class TextArt(DrawingObject):
    """TextArt object (hp:textart)."""

    text: Optional[str] = None
    pt0: Optional[Point] = None
    pt1: Optional[Point] = None
    pt2: Optional[Point] = None
    pt3: Optional[Point] = None
    textart_pr: Optional[TextArtPr] = None
    outline: Optional[ObjectList[Point]] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_textart

    def create_pt0(self) -> Point:
        self.pt0 = Point(ObjectType.hc_pt0)
        return self.pt0

    def create_pt1(self) -> Point:
        self.pt1 = Point(ObjectType.hc_pt1)
        return self.pt1

    def create_pt2(self) -> Point:
        self.pt2 = Point(ObjectType.hc_pt2)
        return self.pt2

    def create_pt3(self) -> Point:
        self.pt3 = Point(ObjectType.hc_pt3)
        return self.pt3

    def create_textart_pr(self) -> TextArtPr:
        self.textart_pr = TextArtPr()
        return self.textart_pr

    def remove_textart_pr(self) -> None:
        self.textart_pr = None

    def create_outline(self) -> ObjectList[Point]:
        self.outline = ObjectList(
            _object_type_value=ObjectType.hp_outline,
            _item_class=Point,
        )
        return self.outline

    def remove_outline(self) -> None:
        self.outline = None
