"""Tab property objects: TabPr, TabItem.

Ported from kr.dogfoot.hwpxlib.object.content.header_xml.references.TabPr
and tabpr.TabItem.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from ....base import HWPXObject, SwitchableObject
from ....object_type import ObjectType
from ..enum_types import LineType2, TabItemType, ValueUnit2


# ---------------------------------------------------------------------------
# TabItem
# ---------------------------------------------------------------------------

@dataclass
class TabItem(HWPXObject):
    """A single tab stop."""

    pos: Optional[int] = None
    type: Optional[TabItemType] = None
    leader: Optional[LineType2] = None
    unit: Optional[ValueUnit2] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_tabItem

    def clone(self) -> TabItem:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# TabPr
# ---------------------------------------------------------------------------

@dataclass
class TabPr(SwitchableObject):
    """Tab properties definition."""

    id: Optional[str] = None
    autoTabLeft: Optional[bool] = None
    autoTabRight: Optional[bool] = None
    _tab_item_list: List[TabItem] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_tabPr

    def count_of_tab_item(self) -> int:
        return len(self._tab_item_list)

    def get_tab_item(self, index: int) -> TabItem:
        return self._tab_item_list[index]

    def get_tab_item_index(self, tab_item: TabItem) -> int:
        for i, ti in enumerate(self._tab_item_list):
            if ti is tab_item:
                return i
        return -1

    def add_tab_item(self, tab_item: TabItem) -> None:
        self._tab_item_list.append(tab_item)

    def add_new_tab_item(self) -> TabItem:
        ti = TabItem()
        self._tab_item_list.append(ti)
        return ti

    def insert_tab_item(self, tab_item: TabItem, position: int) -> None:
        self._tab_item_list.insert(position, tab_item)

    def remove_tab_item(self, position_or_item) -> None:
        if isinstance(position_or_item, int):
            del self._tab_item_list[position_or_item]
        else:
            self._tab_item_list.remove(position_or_item)

    def remove_all_tab_items(self) -> None:
        self._tab_item_list.clear()

    def tab_items(self) -> List[TabItem]:
        return self._tab_item_list

    def __iter__(self) -> Iterator[TabItem]:
        return iter(self._tab_item_list)

    def clone(self) -> TabPr:
        return copy.deepcopy(self)
