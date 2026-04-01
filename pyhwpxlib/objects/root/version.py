"""Port of root/VersionXMLFile.java and root/Version.java."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from pyhwpxlib.base import SwitchableObject
from pyhwpxlib.object_type import ObjectType


# --- Enum: TargetApplicationSort (from header_xml/enumtype) ---

class TargetApplicationSort(Enum):
    WordProcessor = "WORDPROCESSOR"
    Presentation = "PRESENTATION"
    SpreadSheet = "SPREADSHEET"

    @classmethod
    def from_string(cls, s: Optional[str]) -> Optional[TargetApplicationSort]:
        if s is None:
            return None
        upper = s.upper()
        for member in cls:
            if member.value == upper:
                return member
        return None


# --- Version ---

@dataclass
class Version:
    """Version information (major.minor.micro.buildNumber)."""

    major: Optional[int] = None
    minor: Optional[int] = None
    micro: Optional[int] = None
    build_number: Optional[int] = None
    os: Optional[str] = None
    xml_version: Optional[str] = None

    def clone(self) -> Version:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: Version) -> None:
        self.major = from_obj.major
        self.minor = from_obj.minor
        self.micro = from_obj.micro
        self.build_number = from_obj.build_number


# --- VersionXMLFile ---

@dataclass
class VersionXMLFile(SwitchableObject):
    """Port of /version.xml file object."""

    target_application: TargetApplicationSort = field(
        default=TargetApplicationSort.WordProcessor
    )
    version: Version = field(default_factory=Version)
    os: Optional[str] = None
    application: Optional[str] = None
    app_version: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hv_HCFVersion

    def clone(self) -> VersionXMLFile:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: VersionXMLFile) -> None:
        self.target_application = from_obj.target_application
        self.version.copy_from(from_obj.version)
        self.os = from_obj.os
        self.application = from_obj.application
        self.app_version = from_obj.app_version
        self._copy_switches_from(from_obj)
