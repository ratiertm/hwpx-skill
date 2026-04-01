"""Shape objects - Rectangle, Ellipse, Line, Arc, Polygon, Curve."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ....base import HWPXObject
from ....object_type import ObjectType
from ....objects.common.base_objects import Point
from ...section.enum_types import ArcType, CurveSegmentType
from .drawing_object import DrawingObject


# ============================================================
# Rectangle
# ============================================================

@dataclass
class Rectangle(DrawingObject):
    """Rectangle shape (hp:rect)."""

    ratio: Optional[int] = None
    pt0: Optional[Point] = None
    pt1: Optional[Point] = None
    pt2: Optional[Point] = None
    pt3: Optional[Point] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_rect

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


# ============================================================
# Ellipse
# ============================================================

@dataclass
class Ellipse(DrawingObject):
    """Ellipse shape (hp:ellipse)."""

    interval_dirty: Optional[bool] = None
    has_arc_pr: Optional[bool] = None
    arc_type: Optional[ArcType] = None
    center: Optional[Point] = None
    ax1: Optional[Point] = None
    ax2: Optional[Point] = None
    start1: Optional[Point] = None
    start2: Optional[Point] = None
    end1: Optional[Point] = None
    end2: Optional[Point] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_ellipse

    def create_center(self) -> Point:
        self.center = Point(ObjectType.hc_center)
        return self.center

    def create_ax1(self) -> Point:
        self.ax1 = Point(ObjectType.hc_ax1)
        return self.ax1

    def create_ax2(self) -> Point:
        self.ax2 = Point(ObjectType.hc_ax2)
        return self.ax2

    def create_start1(self) -> Point:
        self.start1 = Point(ObjectType.hc_start1)
        return self.start1

    def create_start2(self) -> Point:
        self.start2 = Point(ObjectType.hc_start2)
        return self.start2

    def create_end1(self) -> Point:
        self.end1 = Point(ObjectType.hc_end1)
        return self.end1

    def create_end2(self) -> Point:
        self.end2 = Point(ObjectType.hc_end2)
        return self.end2


# ============================================================
# Line
# ============================================================

@dataclass
class Line(DrawingObject):
    """Line shape (hp:line)."""

    is_reverse_hv: Optional[bool] = None
    start_pt: Optional[Point] = None
    end_pt: Optional[Point] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_line

    def create_start_pt(self) -> Point:
        self.start_pt = Point(ObjectType.hc_startPt)
        return self.start_pt

    def remove_start_pt(self) -> None:
        self.start_pt = None

    def create_end_pt(self) -> Point:
        self.end_pt = Point(ObjectType.hc_endPt)
        return self.end_pt

    def remove_end_pt(self) -> None:
        self.end_pt = None


# ============================================================
# Arc
# ============================================================

@dataclass
class Arc(DrawingObject):
    """Arc shape (hp:arc)."""

    arc_type: Optional[ArcType] = None
    center: Optional[Point] = None
    ax1: Optional[Point] = None
    ax2: Optional[Point] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_arc

    def create_center(self) -> Point:
        self.center = Point(ObjectType.hc_center)
        return self.center

    def create_ax1(self) -> Point:
        self.ax1 = Point(ObjectType.hc_ax1)
        return self.ax1

    def create_ax2(self) -> Point:
        self.ax2 = Point(ObjectType.hc_ax2)
        return self.ax2


# ============================================================
# Polygon
# ============================================================

@dataclass
class Polygon(DrawingObject):
    """Polygon shape (hp:polygon)."""

    _pt_list: List[Point] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_polygon

    def count_of_pt(self) -> int:
        return len(self._pt_list)

    def get_pt(self, index: int) -> Point:
        return self._pt_list[index]

    def add_pt(self, pt: Point) -> None:
        self._pt_list.append(pt)

    def add_new_pt(self) -> Point:
        pt = Point(ObjectType.hc_pt)
        self._pt_list.append(pt)
        return pt

    def pts(self) -> List[Point]:
        return self._pt_list


# ============================================================
# Curve and CurveSegment
# ============================================================

@dataclass
class CurveSegment(HWPXObject):
    """Curve segment (hp:seg)."""

    type: Optional[CurveSegmentType] = None
    x1: Optional[int] = None
    y1: Optional[int] = None
    x2: Optional[int] = None
    y2: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_seg


@dataclass
class Curve(DrawingObject):
    """Curve shape (hp:curve)."""

    _seg_list: List[CurveSegment] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_curve

    def count_of_seg(self) -> int:
        return len(self._seg_list)

    def get_seg(self, index: int) -> CurveSegment:
        return self._seg_list[index]

    def add_seg(self, seg: CurveSegment) -> None:
        self._seg_list.append(seg)

    def add_new_seg(self) -> CurveSegment:
        seg = CurveSegment()
        self._seg_list.append(seg)
        return seg

    def segs(self) -> List[CurveSegment]:
        return self._seg_list
