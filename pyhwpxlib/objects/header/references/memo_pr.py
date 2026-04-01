"""Memo property object.

Ported from kr.dogfoot.hwpxlib.object.content.header_xml.references.MemoPr.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional

from ....base import HWPXObject
from ....object_type import ObjectType
from ..enum_types import LineType2, LineWidth, MemoType


@dataclass
class MemoPr(HWPXObject):
    """Memo (comment) properties."""

    id: Optional[str] = None
    width: Optional[int] = None
    lineType: Optional[LineType2] = None
    lineColor: Optional[str] = None
    fillColor: Optional[str] = None
    activeColor: Optional[str] = None
    memoType: Optional[MemoType] = None
    lineWidth: Optional[LineWidth] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_memoPr

    def clone(self) -> MemoPr:
        return copy.deepcopy(self)
