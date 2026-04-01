"""OLE, Container, Video, Chart object models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from ....object_type import ObjectType
from ....objects.common.base_objects import XAndY
from ...section.enum_types import OLEDrawAspect, OLEObjectType, VideoType
from .drawing_object import ShapeComponent, ShapeObject
from .picture import LineShape


# ============================================================
# OLE
# ============================================================

@dataclass
class OLE(ShapeComponent):
    """OLE object (hp:ole)."""

    ole_object_type: Optional[OLEObjectType] = None
    binary_item_id_ref: Optional[str] = None
    has_moniker: Optional[bool] = None
    draw_aspect: Optional[OLEDrawAspect] = None
    eq_base_line: Optional[int] = None
    extent: Optional[XAndY] = None
    ole_line_shape: Optional[LineShape] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_ole

    def create_extent(self) -> XAndY:
        self.extent = XAndY(ObjectType.hc_extent)
        return self.extent

    def remove_extent(self) -> None:
        self.extent = None

    def create_line_shape(self) -> LineShape:
        self.ole_line_shape = LineShape()
        return self.ole_line_shape

    def remove_line_shape(self) -> None:
        self.ole_line_shape = None


# ============================================================
# Container (group of ShapeComponents)
# ============================================================

@dataclass
class Container(ShapeComponent):
    """Container / group object (hp:container)."""

    _child_list: List[ShapeComponent] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_container

    def count_of_child(self) -> int:
        return len(self._child_list)

    def get_child(self, index: int) -> ShapeComponent:
        return self._child_list[index]

    def add_child(self, child: ShapeComponent) -> None:
        self._child_list.append(child)

    def children(self) -> List[ShapeComponent]:
        return self._child_list

    def add_new_container(self) -> Container:
        c = Container()
        self._child_list.append(c)
        return c

    def add_new_line(self) -> Any:
        from .shapes import Line
        ln = Line()
        self._child_list.append(ln)
        return ln

    def add_new_rectangle(self) -> Any:
        from .shapes import Rectangle
        r = Rectangle()
        self._child_list.append(r)
        return r

    def add_new_ellipse(self) -> Any:
        from .shapes import Ellipse
        e = Ellipse()
        self._child_list.append(e)
        return e

    def add_new_arc(self) -> Any:
        from .shapes import Arc
        a = Arc()
        self._child_list.append(a)
        return a

    def add_new_polygon(self) -> Any:
        from .shapes import Polygon
        p = Polygon()
        self._child_list.append(p)
        return p

    def add_new_curve(self) -> Any:
        from .shapes import Curve
        c = Curve()
        self._child_list.append(c)
        return c

    def add_new_connect_line(self) -> Any:
        from .connect_line import ConnectLine
        cl = ConnectLine()
        self._child_list.append(cl)
        return cl

    def add_new_picture(self) -> Any:
        from .picture import Picture
        p = Picture()
        self._child_list.append(p)
        return p

    def add_new_ole(self) -> OLE:
        o = OLE()
        self._child_list.append(o)
        return o

    def add_new_text_art(self) -> Any:
        from .text_art import TextArt
        ta = TextArt()
        self._child_list.append(ta)
        return ta


# ============================================================
# Video
# ============================================================

@dataclass
class Video(ShapeComponent):
    """Video object (hp:video)."""

    videotype: Optional[VideoType] = None
    file_id_ref: Optional[str] = None
    image_id_ref: Optional[str] = None
    tag: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_video


# ============================================================
# Chart
# ============================================================

@dataclass
class Chart(ShapeObject):
    """Chart object (hp:chart)."""

    version: Optional[float] = None
    chart_id_ref: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_chart
