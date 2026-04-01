"""Equation object model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ....object_type import ObjectType
from ....objects.common.base_objects import HasOnlyText
from ...section.enum_types import EquationLineMode
from .drawing_object import ShapeObject


@dataclass
class Equation(ShapeObject):
    """Equation object (hp:equation)."""

    version: Optional[str] = None
    base_line: Optional[int] = None
    text_color: Optional[str] = None
    base_unit: Optional[int] = None
    line_mode: Optional[EquationLineMode] = None
    font: Optional[str] = None
    script: Optional[HasOnlyText] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_equation

    def create_script(self) -> HasOnlyText:
        self.script = HasOnlyText(ObjectType.hp_script)
        return self.script

    def remove_script(self) -> None:
        self.script = None
