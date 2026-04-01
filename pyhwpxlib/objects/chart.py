"""Port of chart/ChartXMLFile.java."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional

from pyhwpxlib.base import SwitchableObject
from pyhwpxlib.object_type import ObjectType


@dataclass
class ChartXMLFile(SwitchableObject):
    """Binary chart container."""

    path: Optional[str] = None
    data: Optional[bytes] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.c_chartSpace

    def clone(self) -> ChartXMLFile:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: ChartXMLFile) -> None:
        self.path = from_obj.path
        self.data = from_obj.data
        self._copy_switches_from(from_obj)
