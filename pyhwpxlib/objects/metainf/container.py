"""Port of metainf/ContainerXMLFile.java and metainf/RootFile.java."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional

from pyhwpxlib.base import AttachedFile, HWPXObject, ObjectList, SwitchableObject
from pyhwpxlib.constants.mime_types import HWPML_Package
from pyhwpxlib.object_type import ObjectType


# --- RootFile ---

@dataclass
class RootFile(HWPXObject):
    """A root-file entry inside container.xml."""

    full_path: Optional[str] = None
    media_type: Optional[str] = None
    attached_file: Optional[AttachedFile] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.ocf_rootfile

    def create_attached_file(self) -> AttachedFile:
        self.attached_file = AttachedFile()
        return self.attached_file

    def remove_attached_file(self) -> None:
        self.attached_file = None

    def clone(self) -> RootFile:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: RootFile) -> None:
        self.full_path = from_obj.full_path
        self.media_type = from_obj.media_type
        self.attached_file = (
            from_obj.attached_file.clone() if from_obj.attached_file else None
        )


# --- ContainerXMLFile ---

@dataclass
class ContainerXMLFile(SwitchableObject):
    """Port of META-INF/container.xml file object."""

    root_files: Optional[ObjectList[RootFile]] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.ocf_container

    def create_root_files(self) -> ObjectList[RootFile]:
        self.root_files = ObjectList(
            _object_type_value=ObjectType.ocf_rootfiles,
            _item_class=RootFile,
        )
        return self.root_files

    def remove_root_files(self) -> None:
        self.root_files = None

    def package_xml_file_path(self) -> Optional[str]:
        if self.root_files is None:
            return None
        for rf in self.root_files.items():
            if rf.media_type == HWPML_Package:
                return rf.full_path
        return None

    def clone(self) -> ContainerXMLFile:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: ContainerXMLFile) -> None:
        if from_obj.root_files is not None:
            self.create_root_files()
            for rf in from_obj.root_files.items():
                self.root_files.add(rf.clone())
        else:
            self.remove_root_files()
        self._copy_switches_from(from_obj)
