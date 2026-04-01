"""Track change objects: TrackChange, TrackChangeAuthor.

Ported from kr.dogfoot.hwpxlib.object.content.header_xml.references.TrackChange
and TrackChangeAuthor.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Optional

from ....base import HWPXObject
from ....object_type import ObjectType
from ..enum_types import TrackChangeType


@dataclass
class TrackChange(HWPXObject):
    """A single track change record."""

    id: Optional[str] = None
    type: Optional[TrackChangeType] = None
    date: Optional[str] = None
    authorID: Optional[str] = None
    hide: Optional[bool] = None
    charshapeID: Optional[str] = None
    parashapeID: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_trackChange

    def clone(self) -> TrackChange:
        return copy.deepcopy(self)


@dataclass
class TrackChangeAuthor(HWPXObject):
    """Track change author record."""

    id: Optional[str] = None
    name: Optional[str] = None
    mark: Optional[bool] = None
    color: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_trackChangeAuthor

    def clone(self) -> TrackChangeAuthor:
        return copy.deepcopy(self)
