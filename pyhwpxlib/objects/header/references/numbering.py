"""Numbering and bullet objects: Numbering, ParaHead, Bullet.

Ported from kr.dogfoot.hwpxlib.object.content.header_xml.references.Numbering,
Bullet, and numbering.ParaHead.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from ....base import HWPXObject, SwitchableObject
from ....object_type import ObjectType
from ..enum_types import HorizontalAlign1, NumberType1, ValueUnit1
from .border_fill import Image


# ---------------------------------------------------------------------------
# ParaHead
# ---------------------------------------------------------------------------

@dataclass
class ParaHead(HWPXObject):
    """Paragraph head for each numbering level."""

    level: Optional[int] = None
    start: Optional[int] = None
    align: Optional[HorizontalAlign1] = None
    useInstWidth: Optional[bool] = None
    autoIndent: Optional[bool] = None
    widthAdjust: Optional[int] = None
    textOffsetType: Optional[ValueUnit1] = None
    textOffset: Optional[int] = None
    numFormat: Optional[NumberType1] = None
    charPrIDRef: Optional[str] = None
    checkable: Optional[bool] = None
    text: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_paraHead

    def clone(self) -> ParaHead:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Numbering
# ---------------------------------------------------------------------------

@dataclass
class Numbering(SwitchableObject):
    """Numbered paragraph style definition."""

    id: Optional[str] = None
    start: Optional[int] = None
    _para_head_list: List[ParaHead] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_numbering

    def count_of_para_head(self) -> int:
        return len(self._para_head_list)

    def get_para_head(self, index: int) -> ParaHead:
        return self._para_head_list[index]

    def get_para_head_index(self, para_head: ParaHead) -> int:
        for i, ph in enumerate(self._para_head_list):
            if ph is para_head:
                return i
        return -1

    def add_para_head(self, para_head: ParaHead) -> None:
        self._para_head_list.append(para_head)

    def add_new_para_head(self) -> ParaHead:
        ph = ParaHead()
        self._para_head_list.append(ph)
        return ph

    def insert_para_head(self, para_head: ParaHead, position: int) -> None:
        self._para_head_list.insert(position, para_head)

    def remove_para_head(self, position_or_item) -> None:
        if isinstance(position_or_item, int):
            del self._para_head_list[position_or_item]
        else:
            self._para_head_list.remove(position_or_item)

    def remove_all_para_heads(self) -> None:
        self._para_head_list.clear()

    def para_heads(self) -> List[ParaHead]:
        return self._para_head_list

    def __iter__(self) -> Iterator[ParaHead]:
        return iter(self._para_head_list)

    def clone(self) -> Numbering:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Bullet
# ---------------------------------------------------------------------------

@dataclass
class Bullet(SwitchableObject):
    """Bullet paragraph style definition."""

    id: Optional[str] = None
    _char: Optional[str] = None
    checkedChar: Optional[str] = None
    useImage: Optional[bool] = None
    img: Optional[Image] = None
    paraHead: Optional[ParaHead] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_bullet

    def create_img(self) -> Image:
        self.img = Image()
        return self.img

    def remove_img(self) -> None:
        self.img = None

    def create_para_head(self) -> ParaHead:
        self.paraHead = ParaHead()
        return self.paraHead

    def remove_para_head(self) -> None:
        self.paraHead = None

    def clone(self) -> Bullet:
        return copy.deepcopy(self)
