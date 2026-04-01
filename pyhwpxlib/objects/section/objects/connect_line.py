"""ConnectLine object model."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ....base import HWPXObject, ObjectList
from ....object_type import ObjectType
from ...section.enum_types import ConnectLineType
from .drawing_object import DrawingObject


@dataclass
class ConnectLinePoint(HWPXObject):
    """ConnectLine endpoint (hp:startPt / hp:endPt)."""

    _object_type_value: ObjectType = field(default=ObjectType.hp_startPt)
    x: Optional[int] = None
    y: Optional[int] = None
    sub_idx: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return self._object_type_value


@dataclass
class ConnectLineControlPoint(HWPXObject):
    """ConnectLine control point (hp:point)."""

    x: Optional[int] = None
    y: Optional[int] = None
    type: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_point


@dataclass
class ConnectLine(DrawingObject):
    """Connect line object (hp:connectLine)."""

    connect_type: Optional[ConnectLineType] = None
    start_pt: Optional[ConnectLinePoint] = None
    end_pt: Optional[ConnectLinePoint] = None
    control_points: Optional[ObjectList[ConnectLineControlPoint]] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_connectLine

    def create_start_pt(self) -> ConnectLinePoint:
        self.start_pt = ConnectLinePoint(_object_type_value=ObjectType.hp_startPt)
        return self.start_pt

    def remove_start_pt(self) -> None:
        self.start_pt = None

    def create_end_pt(self) -> ConnectLinePoint:
        self.end_pt = ConnectLinePoint(_object_type_value=ObjectType.hp_endPt)
        return self.end_pt

    def remove_end_pt(self) -> None:
        self.end_pt = None

    def create_control_points(self) -> ObjectList[ConnectLineControlPoint]:
        self.control_points = ObjectList(
            _object_type_value=ObjectType.hp_controlPoints,
            _item_class=ConnectLineControlPoint,
        )
        return self.control_points

    def remove_control_points(self) -> None:
        self.control_points = None
