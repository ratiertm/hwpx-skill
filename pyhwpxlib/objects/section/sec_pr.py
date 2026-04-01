"""Section properties - SecPr, PagePr, PageMargin, Grid, StartNum,
Visibility, LineNumberShape, FootNotePr, EndNotePr, PageBorderFill,
MasterPage, Presentation, and supporting note/page types.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from ...base import HWPXObject, SwitchableObject
from ...object_type import ObjectType
from ...objects.common.base_objects import LeftRightTopBottom
from .ctrl import AutoNumFormat
from .enum_types import (
    ApplyPageType,
    EndNoteNumberingType,
    EndNotePlace,
    FootNoteNumberingType,
    FootNotePlace,
    GutterMethod,
    LineNumberRestartType,
    NumberType2,
    PageBorderPositionCriterion,
    PageDirection,
    PageFillArea,
    PageStartON,
    PresentationEffect,
    TextDirection,
    VisibilityOption,
)


# ============================================================
# Page properties
# ============================================================

@dataclass
class PageMargin(HWPXObject):
    """Page margins (hp:margin inside hp:pagePr)."""

    left: Optional[int] = None
    right: Optional[int] = None
    top: Optional[int] = None
    bottom: Optional[int] = None
    header: Optional[int] = None
    footer: Optional[int] = None
    gutter: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_margin


@dataclass
class PagePr(SwitchableObject):
    """Page properties (hp:pagePr)."""

    landscape: Optional[PageDirection] = None
    width: Optional[int] = None
    height: Optional[int] = None
    gutter_type: Optional[GutterMethod] = None
    margin: Optional[PageMargin] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_pagePr

    def create_margin(self) -> PageMargin:
        self.margin = PageMargin()
        return self.margin

    def remove_margin(self) -> None:
        self.margin = None


# ============================================================
# Note properties
# ============================================================

@dataclass
class NoteLine(HWPXObject):
    """Note separator line (hp:noteLine)."""

    type: Optional[str] = None  # LineType2
    width: Optional[str] = None  # LineWidth
    color: Optional[str] = None
    length: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_noteLine


@dataclass
class NoteSpacing(HWPXObject):
    """Note spacing (hp:noteSpacing)."""

    above_line: Optional[int] = None
    below_line: Optional[int] = None
    between_notes: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_noteSpacing


@dataclass
class FootNoteNumbering(HWPXObject):
    """Footnote numbering settings (hp:numbering for footnote)."""

    type: Optional[FootNoteNumberingType] = None
    new_num: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_numbering_for_footnote


@dataclass
class FootNotePlacement(HWPXObject):
    """Footnote placement settings (hp:placement for footnote)."""

    place: Optional[FootNotePlace] = None
    beneath_text: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_placement_for_footnote


@dataclass
class EndNoteNumbering(HWPXObject):
    """Endnote numbering settings (hp:numbering for endnote)."""

    type: Optional[EndNoteNumberingType] = None
    new_num: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_numbering_for_endnote


@dataclass
class EndNotePlacement(HWPXObject):
    """Endnote placement settings (hp:placement for endnote)."""

    place: Optional[EndNotePlace] = None
    beneath_text: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_placement_for_endnote


@dataclass
class FootNotePr(SwitchableObject):
    """Footnote shape properties (hp:footNotePr)."""

    auto_num_format: Optional[AutoNumFormat] = None
    note_line: Optional[NoteLine] = None
    note_spacing: Optional[NoteSpacing] = None
    numbering: Optional[FootNoteNumbering] = None
    placement: Optional[FootNotePlacement] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_footNotePr

    def create_auto_num_format(self) -> AutoNumFormat:
        self.auto_num_format = AutoNumFormat()
        return self.auto_num_format

    def remove_auto_num_format(self) -> None:
        self.auto_num_format = None

    def create_note_line(self) -> NoteLine:
        self.note_line = NoteLine()
        return self.note_line

    def remove_note_line(self) -> None:
        self.note_line = None

    def create_note_spacing(self) -> NoteSpacing:
        self.note_spacing = NoteSpacing()
        return self.note_spacing

    def remove_note_spacing(self) -> None:
        self.note_spacing = None

    def create_numbering(self) -> FootNoteNumbering:
        self.numbering = FootNoteNumbering()
        return self.numbering

    def remove_numbering(self) -> None:
        self.numbering = None

    def create_placement(self) -> FootNotePlacement:
        self.placement = FootNotePlacement()
        return self.placement

    def remove_placement(self) -> None:
        self.placement = None


@dataclass
class EndNotePr(SwitchableObject):
    """Endnote shape properties (hp:endNotePr)."""

    auto_num_format: Optional[AutoNumFormat] = None
    note_line: Optional[NoteLine] = None
    note_spacing: Optional[NoteSpacing] = None
    numbering: Optional[EndNoteNumbering] = None
    placement: Optional[EndNotePlacement] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_endNotePr

    def create_auto_num_format(self) -> AutoNumFormat:
        self.auto_num_format = AutoNumFormat()
        return self.auto_num_format

    def remove_auto_num_format(self) -> None:
        self.auto_num_format = None

    def create_note_line(self) -> NoteLine:
        self.note_line = NoteLine()
        return self.note_line

    def remove_note_line(self) -> None:
        self.note_line = None

    def create_note_spacing(self) -> NoteSpacing:
        self.note_spacing = NoteSpacing()
        return self.note_spacing

    def remove_note_spacing(self) -> None:
        self.note_spacing = None

    def create_numbering(self) -> EndNoteNumbering:
        self.numbering = EndNoteNumbering()
        return self.numbering

    def remove_numbering(self) -> None:
        self.numbering = None

    def create_placement(self) -> EndNotePlacement:
        self.placement = EndNotePlacement()
        return self.placement

    def remove_placement(self) -> None:
        self.placement = None


# ============================================================
# PageBorderFill
# ============================================================

@dataclass
class PageBorderFill(SwitchableObject):
    """Page border/fill properties (hp:pageBorderFill)."""

    type: Optional[ApplyPageType] = None
    border_fill_id_ref: Optional[str] = None
    text_border: Optional[PageBorderPositionCriterion] = None
    header_inside: Optional[bool] = None
    footer_inside: Optional[bool] = None
    fill_area: Optional[PageFillArea] = None
    offset: Optional[LeftRightTopBottom] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_pageBorderFill

    def create_offset(self) -> LeftRightTopBottom:
        self.offset = LeftRightTopBottom(ObjectType.hp_offset_for_pageBorderFill)
        return self.offset

    def remove_offset(self) -> None:
        self.offset = None


# ============================================================
# Grid, StartNum, Visibility, LineNumberShape
# ============================================================

@dataclass
class Grid(HWPXObject):
    """Grid alignment info (hp:grid)."""

    line_grid: Optional[int] = None
    char_grid: Optional[int] = None
    wonggoji_format: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_grid


@dataclass
class StartNum(HWPXObject):
    """Start number info (hp:startNum)."""

    page_starts_on: Optional[PageStartON] = None
    page: Optional[int] = None
    pic: Optional[int] = None
    tbl: Optional[int] = None
    equation: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_startNum


@dataclass
class Visibility(HWPXObject):
    """Show/hide settings (hp:visibility)."""

    hide_first_header: Optional[bool] = None
    hide_first_footer: Optional[bool] = None
    hide_first_master_page: Optional[bool] = None
    border: Optional[VisibilityOption] = None
    fill: Optional[VisibilityOption] = None
    hide_first_page_num: Optional[bool] = None
    hide_first_empty_line: Optional[bool] = None
    show_line_number: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_visibility


@dataclass
class LineNumberShape(HWPXObject):
    """Line number shape settings (hp:lineNumberShape)."""

    restart_type: Optional[LineNumberRestartType] = None
    count_by: Optional[int] = None
    distance: Optional[int] = None
    start_number: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_lineNumberShape


# ============================================================
# MasterPage, Presentation
# ============================================================

@dataclass
class MasterPage(HWPXObject):
    """Master page reference (hp:masterPage)."""

    id_ref: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_masterPage


@dataclass
class Presentation(SwitchableObject):
    """Presentation settings (hp:presentation)."""

    effect: Optional[PresentationEffect] = None
    sound_id_ref: Optional[str] = None
    invent_text: Optional[bool] = None
    autoshow: Optional[bool] = None
    showtime: Optional[int] = None
    applyto: Optional[str] = None
    fill_brush: Optional[Any] = None  # FillBrush from header

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_presentation


# ============================================================
# SecPr (section properties - the main container)
# ============================================================

@dataclass
class SecPr(SwitchableObject):
    """Section properties (hp:secPr)."""

    id: Optional[str] = None
    text_direction: Optional[TextDirection] = None
    space_columns: Optional[int] = None
    tab_stop: Optional[int] = None
    tab_stop_val: Optional[int] = None
    tab_stop_unit: Optional[str] = None  # ValueUnit1 from header
    outline_shape_id_ref: Optional[str] = None
    memo_shape_id_ref: Optional[str] = None
    text_vertical_width_head: Optional[bool] = None
    master_page_cnt: Optional[int] = None
    grid: Optional[Grid] = None
    start_num: Optional[StartNum] = None
    visibility: Optional[Visibility] = None
    line_number_shape: Optional[LineNumberShape] = None
    page_pr: Optional[PagePr] = None
    foot_note_pr: Optional[FootNotePr] = None
    end_note_pr: Optional[EndNotePr] = None
    _page_border_fill_list: List[PageBorderFill] = field(default_factory=list)
    _master_page_list: List[MasterPage] = field(default_factory=list)
    presentation: Optional[Presentation] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_secPr

    # --- create/remove helpers ---

    def create_grid(self) -> Grid:
        self.grid = Grid()
        return self.grid

    def remove_grid(self) -> None:
        self.grid = None

    def create_start_num(self) -> StartNum:
        self.start_num = StartNum()
        return self.start_num

    def remove_start_num(self) -> None:
        self.start_num = None

    def create_visibility(self) -> Visibility:
        self.visibility = Visibility()
        return self.visibility

    def remove_visibility(self) -> None:
        self.visibility = None

    def create_line_number_shape(self) -> LineNumberShape:
        self.line_number_shape = LineNumberShape()
        return self.line_number_shape

    def remove_line_number_shape(self) -> None:
        self.line_number_shape = None

    def create_page_pr(self) -> PagePr:
        self.page_pr = PagePr()
        return self.page_pr

    def remove_page_pr(self) -> None:
        self.page_pr = None

    def create_foot_note_pr(self) -> FootNotePr:
        self.foot_note_pr = FootNotePr()
        return self.foot_note_pr

    def remove_foot_note_pr(self) -> None:
        self.foot_note_pr = None

    def create_end_note_pr(self) -> EndNotePr:
        self.end_note_pr = EndNotePr()
        return self.end_note_pr

    def remove_end_note_pr(self) -> None:
        self.end_note_pr = None

    def create_presentation(self) -> Presentation:
        self.presentation = Presentation()
        return self.presentation

    def remove_presentation(self) -> None:
        self.presentation = None

    # --- PageBorderFill list ---

    def count_of_page_border_fill(self) -> int:
        return len(self._page_border_fill_list)

    def get_page_border_fill(self, index: int) -> PageBorderFill:
        return self._page_border_fill_list[index]

    def add_page_border_fill(self, pbf: PageBorderFill) -> None:
        self._page_border_fill_list.append(pbf)

    def add_new_page_border_fill(self) -> PageBorderFill:
        pbf = PageBorderFill()
        self._page_border_fill_list.append(pbf)
        return pbf

    def page_border_fills(self) -> List[PageBorderFill]:
        return self._page_border_fill_list

    # --- MasterPage list ---

    def count_of_master_page(self) -> int:
        return len(self._master_page_list)

    def get_master_page(self, index: int) -> MasterPage:
        return self._master_page_list[index]

    def add_master_page(self, mp: MasterPage) -> None:
        self._master_page_list.append(mp)

    def add_new_master_page(self) -> MasterPage:
        mp = MasterPage()
        self._master_page_list.append(mp)
        return mp

    def master_pages(self) -> List[MasterPage]:
        return self._master_page_list
