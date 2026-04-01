"""Table object model - Table, Tr (row), Tc (cell), and supporting types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from ....base import HWPXObject, ObjectList, SwitchableObject
from ....object_type import ObjectType
from ....objects.common.base_objects import LeftRightTopBottom, WidthAndHeight
from ...section.enum_types import TablePageBreak
from .drawing_object import ShapeObject


# ============================================================
# Table sub-objects
# ============================================================

@dataclass
class CellAddr(HWPXObject):
    """Cell address (hp:cellAddr)."""

    col_addr: Optional[int] = None
    row_addr: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_cellAddr


@dataclass
class CellSpan(HWPXObject):
    """Cell span (hp:cellSpan)."""

    col_span: Optional[int] = None
    row_span: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_cellSpan


@dataclass
class CellZone(HWPXObject):
    """Cell zone for merged-cell-like border/fill (hp:cellzone)."""

    start_col_addr: Optional[int] = None
    start_row_addr: Optional[int] = None
    end_col_addr: Optional[int] = None
    end_row_addr: Optional[int] = None
    border_fill_id_ref: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_cellzone


@dataclass
class Label(HWPXObject):
    """Label for label-page table (hp:label)."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_label


@dataclass
class ParameterSet(HWPXObject):
    """Parameter set for special table properties."""

    def _object_type(self) -> ObjectType:
        # Uses the hp_parameters type from ParameterListCore lineage
        return ObjectType.hp_parameters


# ============================================================
# Tc (table cell)
# ============================================================

@dataclass
class Tc(SwitchableObject):
    """Table cell (hp:tc)."""

    name: Optional[str] = None
    header: Optional[bool] = None
    has_margin: Optional[bool] = None
    protect: Optional[bool] = None
    editable: Optional[bool] = None
    dirty: Optional[bool] = None
    border_fill_id_ref: Optional[str] = None
    cell_addr: Optional[CellAddr] = None
    cell_span: Optional[CellSpan] = None
    cell_sz: Optional[WidthAndHeight] = None
    cell_margin: Optional[LeftRightTopBottom] = None
    sub_list: Optional[Any] = None  # SubList

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_tc

    def create_cell_addr(self) -> CellAddr:
        self.cell_addr = CellAddr()
        return self.cell_addr

    def remove_cell_addr(self) -> None:
        self.cell_addr = None

    def create_cell_span(self) -> CellSpan:
        self.cell_span = CellSpan()
        return self.cell_span

    def remove_cell_span(self) -> None:
        self.cell_span = None

    def create_cell_sz(self) -> WidthAndHeight:
        self.cell_sz = WidthAndHeight(ObjectType.hp_cellSz)
        return self.cell_sz

    def remove_cell_sz(self) -> None:
        self.cell_sz = None

    def create_cell_margin(self) -> LeftRightTopBottom:
        self.cell_margin = LeftRightTopBottom(ObjectType.hp_cellMargin)
        return self.cell_margin

    def remove_cell_margin(self) -> None:
        self.cell_margin = None

    def create_sub_list(self) -> Any:
        from ...section.section_xml_file import SubList
        self.sub_list = SubList()
        return self.sub_list

    def remove_sub_list(self) -> None:
        self.sub_list = None


# ============================================================
# Tr (table row)
# ============================================================

@dataclass
class Tr(SwitchableObject):
    """Table row (hp:tr)."""

    _tc_list: List[Tc] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_tr

    def count_of_tc(self) -> int:
        return len(self._tc_list)

    def get_tc(self, index: int) -> Tc:
        return self._tc_list[index]

    def add_tc(self, tc: Tc) -> None:
        self._tc_list.append(tc)

    def add_new_tc(self) -> Tc:
        tc = Tc()
        self._tc_list.append(tc)
        return tc

    def insert_tc(self, tc: Tc, position: int) -> None:
        self._tc_list.insert(position, tc)

    def remove_tc(self, position_or_tc) -> None:
        if isinstance(position_or_tc, int):
            del self._tc_list[position_or_tc]
        else:
            self._tc_list.remove(position_or_tc)

    def remove_all_tcs(self) -> None:
        self._tc_list.clear()

    def tcs(self) -> List[Tc]:
        return self._tc_list


# ============================================================
# Table
# ============================================================

@dataclass
class Table(ShapeObject):
    """Table object (hp:tbl)."""

    page_break: Optional[TablePageBreak] = None
    repeat_header: Optional[bool] = None
    row_cnt: Optional[int] = None
    col_cnt: Optional[int] = None
    cell_spacing: Optional[int] = None
    border_fill_id_ref: Optional[str] = None
    no_adjust: Optional[bool] = None
    in_margin: Optional[LeftRightTopBottom] = None
    cellzone_list: Optional[ObjectList[CellZone]] = None
    _tr_list: List[Tr] = field(default_factory=list)
    parameter_set: Optional[ParameterSet] = None
    label: Optional[Label] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_tbl

    def create_in_margin(self) -> LeftRightTopBottom:
        self.in_margin = LeftRightTopBottom(ObjectType.hp_inMargin)
        return self.in_margin

    def remove_in_margin(self) -> None:
        self.in_margin = None

    def create_cellzone_list(self) -> ObjectList[CellZone]:
        self.cellzone_list = ObjectList(
            _object_type_value=ObjectType.hp_cellzoneList,
            _item_class=CellZone,
        )
        return self.cellzone_list

    def remove_cellzone_list(self) -> None:
        self.cellzone_list = None

    # --- Tr list ---

    def count_of_tr(self) -> int:
        return len(self._tr_list)

    def get_tr(self, index: int) -> Tr:
        return self._tr_list[index]

    def add_tr(self, tr: Tr) -> None:
        self._tr_list.append(tr)

    def add_new_tr(self) -> Tr:
        tr = Tr()
        self._tr_list.append(tr)
        return tr

    def insert_tr(self, tr: Tr, position: int) -> None:
        self._tr_list.insert(position, tr)

    def remove_tr(self, position_or_tr) -> None:
        if isinstance(position_or_tr, int):
            del self._tr_list[position_or_tr]
        else:
            self._tr_list.remove(position_or_tr)

    def remove_all_trs(self) -> None:
        self._tr_list.clear()

    def trs(self) -> List[Tr]:
        return self._tr_list

    def create_parameter_set(self) -> ParameterSet:
        self.parameter_set = ParameterSet()
        return self.parameter_set

    def remove_parameter_set(self) -> None:
        self.parameter_set = None

    def create_label(self) -> Label:
        self.label = Label()
        return self.label

    def remove_label(self) -> None:
        self.label = None
