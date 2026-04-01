"""SectionXMLFile and ParaListCore - top-level section containers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Optional

from ...base import SwitchableObject
from ...object_type import ObjectType
from .enum_types import LineWrapMethod, TextDirection, VerticalAlign2


# Forward reference resolved at runtime
# from .paragraph import Para


@dataclass
class ParaListCore(SwitchableObject):
    """Abstract base for objects containing a list of paragraphs."""

    _para_list: List["Para"] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        raise NotImplementedError

    # --- para list management ---

    def count_of_para(self) -> int:
        return len(self._para_list)

    def get_para(self, index: int) -> "Para":
        return self._para_list[index]

    def get_para_index(self, para: "Para") -> int:
        for i, p in enumerate(self._para_list):
            if p is para:
                return i
        return -1

    def add_para(self, para: "Para") -> None:
        self._para_list.append(para)

    def add_new_para(self) -> "Para":
        from .paragraph import Para

        para = Para()
        self._para_list.append(para)
        return para

    def insert_para(self, para: "Para", position: int) -> None:
        self._para_list.insert(position, para)

    def remove_para(self, position_or_para) -> None:
        if isinstance(position_or_para, int):
            del self._para_list[position_or_para]
        else:
            self._para_list.remove(position_or_para)

    def remove_all_paras(self) -> None:
        self._para_list.clear()

    def paras(self) -> List["Para"]:
        return self._para_list

    def __iter__(self) -> Iterator["Para"]:
        return iter(self._para_list)

    def __len__(self) -> int:
        return len(self._para_list)


@dataclass
class SubList(ParaListCore):
    """Internal paragraph list (hp:subList) with layout attributes."""

    id: Optional[str] = None
    text_direction: Optional[TextDirection] = None
    line_wrap: Optional[LineWrapMethod] = None
    vert_align: Optional[VerticalAlign2] = None
    link_list_id_ref: Optional[str] = None
    link_list_next_id_ref: Optional[str] = None
    text_width: Optional[int] = None
    text_height: Optional[int] = None
    has_text_ref: Optional[bool] = None
    has_num_ref: Optional[bool] = None
    meta_tag: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_subList


@dataclass
class SectionXMLFile(ParaListCore):
    """Root element of a section XML file (hs:sec)."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hs_sec
