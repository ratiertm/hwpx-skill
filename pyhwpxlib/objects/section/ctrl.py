"""Control types - FieldBegin, FieldEnd, FootNote, EndNote, Header, Footer,
HiddenComment, AutoNum, NewNum, ColPr, Indexmark, Bookmark, PageNumCtrl,
PageHiding, PageNum, and supporting types.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from ...base import HWPXObject, SwitchableObject
from ...object_type import ObjectType
from ...objects.common.base_objects import HasOnlyText
from .enum_types import (
    ApplyPageType,
    ColumnDirection,
    FieldType,
    MultiColumnType,
    NumType,
    NumberType2,
    PageNumPosition,
)
from .paragraph import CtrlItem


# ============================================================
# ColSz, ColLine (column definition helpers)
# ============================================================

@dataclass
class ColSz(HWPXObject):
    """Column size and gap (hp:colSz)."""

    width: Optional[int] = None
    gap: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_colSz


@dataclass
class ColLine(HWPXObject):
    """Column separator line (hp:colLine)."""

    type: Optional[str] = None  # LineType2 from header enums
    width: Optional[str] = None  # LineWidth from header enums
    color: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_colLine


# ============================================================
# AutoNumFormat (for footnotes / endnotes / auto numbering)
# ============================================================

@dataclass
class AutoNumFormat(HWPXObject):
    """Auto number format (hp:autoNumFormat)."""

    type: Optional[NumberType2] = None
    user_char: Optional[str] = None
    prefix_char: Optional[str] = None
    suffix_char: Optional[str] = None
    supscript: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_autoNumFormat


# ============================================================
# FieldBegin
# ============================================================

@dataclass
class FieldBegin(CtrlItem):
    """Field begin marker (hp:fieldBegin)."""

    id: Optional[str] = None
    type: Optional[FieldType] = None
    name: Optional[str] = None
    editable: Optional[bool] = None
    dirty: Optional[bool] = None
    zorder: Optional[int] = None
    fieldid: Optional[str] = None
    parameters: Optional[Any] = None  # Parameters (ParameterListCore subclass)
    sub_list: Optional[Any] = None  # SubList
    meta_tag: Optional[HasOnlyText] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_fieldBegin

    def create_sub_list(self) -> Any:
        from .section_xml_file import SubList
        self.sub_list = SubList()
        return self.sub_list

    def remove_sub_list(self) -> None:
        self.sub_list = None

    def create_meta_tag(self) -> HasOnlyText:
        self.meta_tag = HasOnlyText(ObjectType.hp_metaTag)
        return self.meta_tag

    def remove_meta_tag(self) -> None:
        self.meta_tag = None


# ============================================================
# FieldEnd
# ============================================================

@dataclass
class FieldEnd(CtrlItem):
    """Field end marker (hp:fieldEnd)."""

    begin_id_ref: Optional[str] = None
    fieldid: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_fieldEnd


# ============================================================
# Bookmark
# ============================================================

@dataclass
class Bookmark(CtrlItem):
    """Bookmark (hp:bookmark)."""

    name: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_bookmark


# ============================================================
# Header / Footer (header/footer core)
# ============================================================

@dataclass
class Header(CtrlItem):
    """Page header (hp:header)."""

    id: Optional[str] = None
    apply_page_type: Optional[ApplyPageType] = None
    sub_list: Optional[Any] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_header

    def create_sub_list(self) -> Any:
        from .section_xml_file import SubList
        self.sub_list = SubList()
        return self.sub_list

    def remove_sub_list(self) -> None:
        self.sub_list = None


@dataclass
class Footer(CtrlItem):
    """Page footer (hp:footer)."""

    id: Optional[str] = None
    apply_page_type: Optional[ApplyPageType] = None
    sub_list: Optional[Any] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_footer

    def create_sub_list(self) -> Any:
        from .section_xml_file import SubList
        self.sub_list = SubList()
        return self.sub_list

    def remove_sub_list(self) -> None:
        self.sub_list = None


# ============================================================
# FootNote / EndNote
# ============================================================

@dataclass
class FootNote(CtrlItem):
    """Footnote (hp:footNote)."""

    number: Optional[int] = None
    suffix_char: Optional[str] = None
    inst_id: Optional[str] = None
    sub_list: Optional[Any] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_footNote

    def create_sub_list(self) -> Any:
        from .section_xml_file import SubList
        self.sub_list = SubList()
        return self.sub_list

    def remove_sub_list(self) -> None:
        self.sub_list = None


@dataclass
class EndNote(CtrlItem):
    """Endnote (hp:endNote)."""

    number: Optional[int] = None
    suffix_char: Optional[str] = None
    inst_id: Optional[str] = None
    sub_list: Optional[Any] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_endNote

    def create_sub_list(self) -> Any:
        from .section_xml_file import SubList
        self.sub_list = SubList()
        return self.sub_list

    def remove_sub_list(self) -> None:
        self.sub_list = None


# ============================================================
# AutoNum / NewNum
# ============================================================

@dataclass
class AutoNum(CtrlItem):
    """Auto number (hp:autoNum)."""

    num: Optional[int] = None
    num_type: Optional[NumType] = None
    auto_num_format: Optional[AutoNumFormat] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_autoNum

    def create_auto_num_format(self) -> AutoNumFormat:
        self.auto_num_format = AutoNumFormat()
        return self.auto_num_format

    def remove_auto_num_format(self) -> None:
        self.auto_num_format = None


@dataclass
class NewNum(CtrlItem):
    """New number (hp:newNum)."""

    num: Optional[int] = None
    num_type: Optional[NumType] = None
    auto_num_format: Optional[AutoNumFormat] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_newNum

    def create_auto_num_format(self) -> AutoNumFormat:
        self.auto_num_format = AutoNumFormat()
        return self.auto_num_format

    def remove_auto_num_format(self) -> None:
        self.auto_num_format = None


# ============================================================
# PageNumCtrl
# ============================================================

@dataclass
class PageNumCtrl(CtrlItem):
    """Page number control (hp:pageNumCtrl)."""

    page_starts_on: Optional[ApplyPageType] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_pageNumCtrl


# ============================================================
# PageHiding
# ============================================================

@dataclass
class PageHiding(CtrlItem):
    """Page hiding control (hp:pageHiding)."""

    hide_header: Optional[bool] = None
    hide_footer: Optional[bool] = None
    hide_master_page: Optional[bool] = None
    hide_border: Optional[bool] = None
    hide_fill: Optional[bool] = None
    hide_page_num: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_pageHiding


# ============================================================
# PageNum
# ============================================================

@dataclass
class PageNum(CtrlItem):
    """Page number position (hp:pageNum)."""

    pos: Optional[PageNumPosition] = None
    format_type: Optional[str] = None  # NumberType1 from header enums
    side_char: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_pageNum


# ============================================================
# Indexmark
# ============================================================

@dataclass
class Indexmark(CtrlItem):
    """Index mark (hp:indexmark)."""

    first_key: Optional[HasOnlyText] = None
    second_key: Optional[HasOnlyText] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_indexmark

    def create_first_key(self) -> HasOnlyText:
        self.first_key = HasOnlyText(ObjectType.hp_firstKey)
        return self.first_key

    def remove_first_key(self) -> None:
        self.first_key = None

    def create_second_key(self) -> HasOnlyText:
        self.second_key = HasOnlyText(ObjectType.hp_secondKey)
        return self.second_key

    def remove_second_key(self) -> None:
        self.second_key = None


# ============================================================
# HiddenComment
# ============================================================

@dataclass
class HiddenComment(CtrlItem):
    """Hidden comment (hp:hiddenComment)."""

    sub_list: Optional[Any] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_hiddenComment

    def create_sub_list(self) -> Any:
        from .section_xml_file import SubList
        self.sub_list = SubList()
        return self.sub_list

    def remove_sub_list(self) -> None:
        self.sub_list = None


# ============================================================
# ColPr (column definition)
# ============================================================

@dataclass
class ColPr(CtrlItem):
    """Column definition (hp:colPr)."""

    id: Optional[str] = None
    type: Optional[MultiColumnType] = None
    layout: Optional[ColumnDirection] = None
    col_count: Optional[int] = None
    same_sz: Optional[bool] = None
    same_gap: Optional[int] = None
    _col_sz_list: List[ColSz] = field(default_factory=list)
    col_line: Optional[ColLine] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_colPr

    def count_of_col_sz(self) -> int:
        return len(self._col_sz_list)

    def get_col_sz(self, index: int) -> ColSz:
        return self._col_sz_list[index]

    def add_col_sz(self, col_sz: ColSz) -> None:
        self._col_sz_list.append(col_sz)

    def add_new_col_sz(self) -> ColSz:
        cs = ColSz()
        self._col_sz_list.append(cs)
        return cs

    def col_szs(self) -> List[ColSz]:
        return self._col_sz_list

    def create_col_line(self) -> ColLine:
        self.col_line = ColLine()
        return self.col_line

    def remove_col_line(self) -> None:
        self.col_line = None
