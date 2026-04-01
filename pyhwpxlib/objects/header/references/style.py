"""Style object.

Ported from kr.dogfoot.hwpxlib.object.content.header_xml.references.Style.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional

from ....base import HWPXObject
from ....object_type import ObjectType
from ..enum_types import StyleType


@dataclass
class Style(HWPXObject):
    """Named style (paragraph or character)."""

    id: Optional[str] = None
    type: Optional[StyleType] = None
    name: Optional[str] = None
    engName: Optional[str] = None
    paraPrIDRef: Optional[str] = None
    charPrIDRef: Optional[str] = None
    nextStyleIDRef: Optional[str] = None
    langID: Optional[str] = None
    lockForm: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_style

    def clone(self) -> Style:
        return copy.deepcopy(self)
