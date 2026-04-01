"""Base object dataclasses: Point, XAndY, XAndYFloat, WidthAndHeight,
LeftRightTopBottom, StartAndEndFloat, ValueAndUnit, HasOnlyText."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ...base import HWPXObject
from ...object_type import ObjectType


@dataclass
class HasOnlyText(HWPXObject):
    """Object that contains only text content."""

    _object_type_value: ObjectType = field(default=ObjectType.Unknown)
    _buffer: str = field(default="", repr=False)

    def __init__(self, object_type: ObjectType = ObjectType.Unknown):
        self._object_type_value = object_type
        self._buffer = ""

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def text(self) -> str:
        return self._buffer

    def add_text(self, text: str) -> None:
        self._buffer += text

    def add_text_and(self, text: str) -> HasOnlyText:
        self._buffer += text
        return self

    def clone(self) -> HasOnlyText:
        cloned = HasOnlyText(self._object_type_value)
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: HasOnlyText) -> None:
        self.add_text(from_obj.text())


@dataclass
class Point(HWPXObject):
    """Point with x, y coordinates (Long)."""

    _object_type_value: ObjectType = field(default=ObjectType.hc_pt)
    x: Optional[int] = None
    y: Optional[int] = None

    def __init__(self, object_type: ObjectType = ObjectType.hc_pt):
        self._object_type_value = object_type
        self.x = None
        self.y = None

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def set(self, x: Optional[int], y: Optional[int]) -> None:
        self.x = x
        self.y = y

    def x_and(self, x: Optional[int]) -> Point:
        self.x = x
        return self

    def y_and(self, y: Optional[int]) -> Point:
        self.y = y
        return self

    def clone(self) -> Point:
        cloned = Point(self._object_type_value)
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: Point) -> None:
        self.x = from_obj.x
        self.y = from_obj.y


@dataclass
class XAndY(HWPXObject):
    """X and Y coordinates (Long)."""

    _object_type_value: ObjectType = field(default=ObjectType.Unknown)
    x: Optional[int] = None
    y: Optional[int] = None

    def __init__(self, object_type: ObjectType = ObjectType.Unknown):
        self._object_type_value = object_type
        self.x = None
        self.y = None

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def set(self, x: Optional[int], y: Optional[int]) -> None:
        self.x = x
        self.y = y

    def x_and(self, x: Optional[int]) -> XAndY:
        self.x = x
        return self

    def y_and(self, y: Optional[int]) -> XAndY:
        self.y = y
        return self

    def clone(self) -> XAndY:
        cloned = XAndY(self._object_type_value)
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: XAndY) -> None:
        self.x = from_obj.x
        self.y = from_obj.y


@dataclass
class XAndYFloat(HWPXObject):
    """X and Y coordinates (Float)."""

    _object_type_value: ObjectType = field(default=ObjectType.Unknown)
    x: Optional[float] = None
    y: Optional[float] = None

    def __init__(self, object_type: ObjectType = ObjectType.Unknown):
        self._object_type_value = object_type
        self.x = None
        self.y = None

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def set(self, x: Optional[float], y: Optional[float]) -> None:
        self.x = x
        self.y = y

    def x_and(self, x: Optional[float]) -> XAndYFloat:
        self.x = x
        return self

    def y_and(self, y: Optional[float]) -> XAndYFloat:
        self.y = y
        return self

    def clone(self) -> XAndYFloat:
        cloned = XAndYFloat(self._object_type_value)
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: XAndYFloat) -> None:
        self.x = from_obj.x
        self.y = from_obj.y


@dataclass
class WidthAndHeight(HWPXObject):
    """Width and height dimensions (Long)."""

    _object_type_value: ObjectType = field(default=ObjectType.Unknown)
    width: Optional[int] = None
    height: Optional[int] = None

    def __init__(self, object_type: ObjectType = ObjectType.Unknown):
        self._object_type_value = object_type
        self.width = None
        self.height = None

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def set(self, width: Optional[int], height: Optional[int]) -> None:
        self.width = width
        self.height = height

    def width_and(self, width: Optional[int]) -> WidthAndHeight:
        self.width = width
        return self

    def height_and(self, height: Optional[int]) -> WidthAndHeight:
        self.height = height
        return self

    def clone(self) -> WidthAndHeight:
        cloned = WidthAndHeight(self._object_type_value)
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: WidthAndHeight) -> None:
        self.width = from_obj.width
        self.height = from_obj.height


@dataclass
class LeftRightTopBottom(HWPXObject):
    """Left, right, top, bottom margins/borders (Long)."""

    _object_type_value: ObjectType = field(default=ObjectType.Unknown)
    left: Optional[int] = None
    right: Optional[int] = None
    top: Optional[int] = None
    bottom: Optional[int] = None

    def __init__(self, object_type: ObjectType = ObjectType.Unknown):
        self._object_type_value = object_type
        self.left = None
        self.right = None
        self.top = None
        self.bottom = None

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def set(
        self,
        left: Optional[int],
        right: Optional[int],
        top: Optional[int],
        bottom: Optional[int],
    ) -> None:
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom

    def left_and(self, left: Optional[int]) -> LeftRightTopBottom:
        self.left = left
        return self

    def right_and(self, right: Optional[int]) -> LeftRightTopBottom:
        self.right = right
        return self

    def top_and(self, top: Optional[int]) -> LeftRightTopBottom:
        self.top = top
        return self

    def bottom_and(self, bottom: Optional[int]) -> LeftRightTopBottom:
        self.bottom = bottom
        return self

    def clone(self) -> LeftRightTopBottom:
        cloned = LeftRightTopBottom(self._object_type_value)
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: LeftRightTopBottom) -> None:
        self.left = from_obj.left
        self.right = from_obj.right
        self.top = from_obj.top
        self.bottom = from_obj.bottom


@dataclass
class StartAndEndFloat(HWPXObject):
    """Start and end values (Float)."""

    _object_type_value: ObjectType = field(default=ObjectType.Unknown)
    start: Optional[float] = None
    end: Optional[float] = None

    def __init__(self, object_type: ObjectType = ObjectType.Unknown):
        self._object_type_value = object_type
        self.start = None
        self.end = None

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def set(self, start: Optional[float], end: Optional[float]) -> None:
        self.start = start
        self.end = end

    def start_and(self, start: Optional[float]) -> StartAndEndFloat:
        self.start = start
        return self

    def end_and(self, end: Optional[float]) -> StartAndEndFloat:
        self.end = end
        return self

    def clone(self) -> StartAndEndFloat:
        cloned = StartAndEndFloat(self._object_type_value)
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: StartAndEndFloat) -> None:
        self.start = from_obj.start
        self.end = from_obj.end


@dataclass
class ValueAndUnit(HWPXObject):
    """Value with unit (Integer value, string unit).

    Note: Java uses ValueUnit2 enum for unit. Here we use Optional[str]
    as a placeholder until the enum is ported.
    """

    _object_type_value: ObjectType = field(default=ObjectType.Unknown)
    value: Optional[int] = None
    unit: Optional[str] = None

    def __init__(self, object_type: ObjectType = ObjectType.Unknown):
        self._object_type_value = object_type
        self.value = None
        self.unit = None

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def set(self, value: Optional[int], unit: Optional[str]) -> None:
        self.value = value
        self.unit = unit

    def value_and(self, value: Optional[int]) -> ValueAndUnit:
        self.value = value
        return self

    def unit_and(self, unit: Optional[str]) -> ValueAndUnit:
        self.unit = unit
        return self

    def clone(self) -> ValueAndUnit:
        cloned = ValueAndUnit(self._object_type_value)
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: ValueAndUnit) -> None:
        self.value = from_obj.value
        self.unit = from_obj.unit
