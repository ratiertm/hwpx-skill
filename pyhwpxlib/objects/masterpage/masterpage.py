"""Port of content/masterpage_xml/MasterPageXMLFile.java and MasterPageType enum."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pyhwpxlib.base import SwitchableObject
from pyhwpxlib.object_type import ObjectType


# --- MasterPageType enum ---

class MasterPageType(Enum):
    BOTH = "BOTH"
    EVEN = "EVEN"
    ODD = "ODD"
    LAST_PAGE = "LAST_PAGE"
    OPTIONAL_PAGE = "OPTIONAL_PAGE"

    @classmethod
    def from_string(cls, s: Optional[str]) -> Optional[MasterPageType]:
        if s is None:
            return None
        upper = s.upper()
        for member in cls:
            if member.value == upper:
                return member
        return None


# --- MasterPageXMLFile ---

@dataclass
class MasterPageXMLFile(SwitchableObject):
    """Port of masterpage XML file object.

    Note: sub_list is typed as Any because SubList lives in the section module,
    which may not be created yet. Use forward reference once available.
    """

    id: Optional[str] = None
    type: Optional[MasterPageType] = None
    page_number: Optional[int] = None
    page_duplicate: Optional[bool] = None
    page_front: Optional[bool] = None
    sub_list: Optional[Any] = None  # SubList from section module

    def _object_type(self) -> ObjectType:
        return ObjectType.masterPage

    def create_sub_list(self) -> Any:
        """Create a SubList. Import deferred to avoid circular dependency."""
        try:
            from pyhwpxlib.objects.section.objects.sub_list import SubList
            self.sub_list = SubList()
        except ImportError:
            self.sub_list = None
        return self.sub_list

    def remove_sub_list(self) -> None:
        self.sub_list = None

    def clone(self) -> MasterPageXMLFile:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: MasterPageXMLFile) -> None:
        self.id = from_obj.id
        self.type = from_obj.type
        self.page_number = from_obj.page_number
        self.page_duplicate = from_obj.page_duplicate
        self.page_front = from_obj.page_front
        self.sub_list = (
            from_obj.sub_list.clone() if from_obj.sub_list else None
        )
        self._copy_switches_from(from_obj)
