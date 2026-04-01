"""Paragraph property objects: ParaPr, Align, Heading, BreakSetting,
ParaMargin, LineSpacing, ParaBorder, AutoSpacing.

Ported from kr.dogfoot.hwpxlib.object.content.header_xml.references.ParaPr
and kr.dogfoot.hwpxlib.object.content.header_xml.references.parapr.*
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional

from ....base import HWPXObject, SwitchableObject
from ....object_type import ObjectType
from ...common.base_objects import ValueAndUnit
from ..enum_types import (
    HorizontalAlign2,
    LineBreakForLatin,
    LineBreakForNonLatin,
    LineSpacingType,
    LineWrap,
    ParaHeadingType,
    ValueUnit2,
    VerticalAlign1,
)


# ---------------------------------------------------------------------------
# Align
# ---------------------------------------------------------------------------

@dataclass
class Align(HWPXObject):
    """Paragraph alignment."""

    horizontal: Optional[HorizontalAlign2] = None
    vertical: Optional[VerticalAlign1] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_align

    def clone(self) -> Align:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# Heading
# ---------------------------------------------------------------------------

@dataclass
class Heading(HWPXObject):
    """Paragraph heading (numbering/bullet reference)."""

    type: Optional[ParaHeadingType] = None
    idRef: Optional[str] = None
    level: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_heading

    def clone(self) -> Heading:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# BreakSetting
# ---------------------------------------------------------------------------

@dataclass
class BreakSetting(HWPXObject):
    """Line/page break settings for a paragraph."""

    breakLatinWord: Optional[LineBreakForLatin] = None
    breakNonLatinWord: Optional[LineBreakForNonLatin] = None
    widowOrphan: Optional[bool] = None
    keepWithNext: Optional[bool] = None
    keepLines: Optional[bool] = None
    pageBreakBefore: Optional[bool] = None
    lineWrap: Optional[LineWrap] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_breakSetting

    def clone(self) -> BreakSetting:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# ParaMargin
# ---------------------------------------------------------------------------

@dataclass
class ParaMargin(SwitchableObject):
    """Paragraph margins (indent, left, right, prev, next)."""

    intent: Optional[ValueAndUnit] = None
    left: Optional[ValueAndUnit] = None
    right: Optional[ValueAndUnit] = None
    prev: Optional[ValueAndUnit] = None
    next: Optional[ValueAndUnit] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_margin

    def create_intent(self) -> ValueAndUnit:
        self.intent = ValueAndUnit(ObjectType.hc_intent)
        return self.intent

    def remove_intent(self) -> None:
        self.intent = None

    def create_left(self) -> ValueAndUnit:
        self.left = ValueAndUnit(ObjectType.hc_left)
        return self.left

    def remove_left(self) -> None:
        self.left = None

    def create_right(self) -> ValueAndUnit:
        self.right = ValueAndUnit(ObjectType.hc_right)
        return self.right

    def remove_right(self) -> None:
        self.right = None

    def create_prev(self) -> ValueAndUnit:
        self.prev = ValueAndUnit(ObjectType.hc_prev)
        return self.prev

    def remove_prev(self) -> None:
        self.prev = None

    def create_next(self) -> ValueAndUnit:
        self.next = ValueAndUnit(ObjectType.hc_next)
        return self.next

    def remove_next(self) -> None:
        self.next = None

    def clone(self) -> ParaMargin:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# LineSpacing
# ---------------------------------------------------------------------------

@dataclass
class LineSpacing(HWPXObject):
    """Line spacing settings."""

    type: Optional[LineSpacingType] = None
    value: Optional[int] = None
    unit: Optional[ValueUnit2] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_lineSpacing

    def clone(self) -> LineSpacing:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# ParaBorder
# ---------------------------------------------------------------------------

@dataclass
class ParaBorder(HWPXObject):
    """Paragraph border settings."""

    borderFillIDRef: Optional[str] = None
    offsetLeft: Optional[int] = None
    offsetRight: Optional[int] = None
    offsetTop: Optional[int] = None
    offsetBottom: Optional[int] = None
    connect: Optional[bool] = None
    ignoreMargin: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_border

    def clone(self) -> ParaBorder:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# AutoSpacing
# ---------------------------------------------------------------------------

@dataclass
class AutoSpacing(HWPXObject):
    """Auto-spacing between East Asian and other scripts."""

    eAsianEng: Optional[bool] = None
    eAsianNum: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_autoSpacing

    def clone(self) -> AutoSpacing:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# ParaPr
# ---------------------------------------------------------------------------

@dataclass
class ParaPr(SwitchableObject):
    """Paragraph properties."""

    id: Optional[str] = None
    tabPrIDRef: Optional[str] = None
    condense: Optional[int] = None
    fontLineHeight: Optional[bool] = None
    snapToGrid: Optional[bool] = None
    suppressLineNumbers: Optional[bool] = None
    checked: Optional[bool] = None

    align: Optional[Align] = None
    heading: Optional[Heading] = None
    breakSetting: Optional[BreakSetting] = None
    margin: Optional[ParaMargin] = None
    lineSpacing: Optional[LineSpacing] = None
    border: Optional[ParaBorder] = None
    autoSpacing: Optional[AutoSpacing] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_paraPr

    # -- factory helpers --

    def create_align(self) -> Align:
        self.align = Align()
        return self.align

    def remove_align(self) -> None:
        self.align = None

    def create_heading(self) -> Heading:
        self.heading = Heading()
        return self.heading

    def remove_heading(self) -> None:
        self.heading = None

    def create_break_setting(self) -> BreakSetting:
        self.breakSetting = BreakSetting()
        return self.breakSetting

    def remove_break_setting(self) -> None:
        self.breakSetting = None

    def create_margin(self) -> ParaMargin:
        self.margin = ParaMargin()
        return self.margin

    def remove_margin(self) -> None:
        self.margin = None

    def create_line_spacing(self) -> LineSpacing:
        self.lineSpacing = LineSpacing()
        return self.lineSpacing

    def remove_line_spacing(self) -> None:
        self.lineSpacing = None

    def create_border(self) -> ParaBorder:
        self.border = ParaBorder()
        return self.border

    def remove_border(self) -> None:
        self.border = None

    def create_auto_spacing(self) -> AutoSpacing:
        self.autoSpacing = AutoSpacing()
        return self.autoSpacing

    def remove_auto_spacing(self) -> None:
        self.autoSpacing = None

    def clone(self) -> ParaPr:
        return copy.deepcopy(self)
