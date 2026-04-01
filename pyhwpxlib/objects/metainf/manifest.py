"""Port of metainf/ManifestXMLFile.java, FileEntry.java, and Encryption* classes."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import List, Optional

from pyhwpxlib.base import HWPXObject, SwitchableObject
from pyhwpxlib.object_type import ObjectType


# --- EncryptionAlgorithm ---

@dataclass
class EncryptionAlgorithm(HWPXObject):
    """Encryption algorithm info."""

    algorithm_name: Optional[str] = None
    initialisation_vector: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.odf_algorithm

    def clone(self) -> EncryptionAlgorithm:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: EncryptionAlgorithm) -> None:
        self.algorithm_name = from_obj.algorithm_name
        self.initialisation_vector = from_obj.initialisation_vector


# --- EncryptionKeyDerivation ---

@dataclass
class EncryptionKeyDerivation(HWPXObject):
    """Key derivation parameters."""

    key_derivation_name: Optional[str] = None
    key_size: Optional[int] = None
    iteration_count: Optional[int] = None
    salt: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.odf_key_derivation

    def clone(self) -> EncryptionKeyDerivation:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: EncryptionKeyDerivation) -> None:
        self.key_derivation_name = from_obj.key_derivation_name
        self.key_size = from_obj.key_size
        self.iteration_count = from_obj.iteration_count
        self.salt = from_obj.salt


# --- EncryptionStartKeyGeneration ---

@dataclass
class EncryptionStartKeyGeneration(HWPXObject):
    """Start key generation parameters."""

    start_key_generation_name: Optional[str] = None
    key_size: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.odf_start_key_generation

    def clone(self) -> EncryptionStartKeyGeneration:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: EncryptionStartKeyGeneration) -> None:
        self.start_key_generation_name = from_obj.start_key_generation_name
        self.key_size = from_obj.key_size


# --- EncryptionData ---

@dataclass
class EncryptionData(SwitchableObject):
    """Encryption data attached to a FileEntry."""

    checksum_type: Optional[str] = None
    checksum: Optional[str] = None
    algorithm: Optional[EncryptionAlgorithm] = None
    key_derivation: Optional[EncryptionKeyDerivation] = None
    start_key_generation: Optional[EncryptionStartKeyGeneration] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.odf_encryption_data

    def create_algorithm(self) -> EncryptionAlgorithm:
        self.algorithm = EncryptionAlgorithm()
        return self.algorithm

    def remove_algorithm(self) -> None:
        self.algorithm = None

    def create_key_derivation(self) -> EncryptionKeyDerivation:
        self.key_derivation = EncryptionKeyDerivation()
        return self.key_derivation

    def remove_key_derivation(self) -> None:
        self.key_derivation = None

    def create_start_key_generation(self) -> EncryptionStartKeyGeneration:
        self.start_key_generation = EncryptionStartKeyGeneration()
        return self.start_key_generation

    def remove_start_key_generation(self) -> None:
        self.start_key_generation = None

    def clone(self) -> EncryptionData:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: EncryptionData) -> None:
        self.checksum_type = from_obj.checksum_type
        self.checksum = from_obj.checksum
        self.algorithm = (
            from_obj.algorithm.clone() if from_obj.algorithm else None
        )
        self.key_derivation = (
            from_obj.key_derivation.clone() if from_obj.key_derivation else None
        )
        self.start_key_generation = (
            from_obj.start_key_generation.clone()
            if from_obj.start_key_generation
            else None
        )
        self._copy_switches_from(from_obj)


# --- FileEntry ---

@dataclass
class FileEntry(SwitchableObject):
    """A file-entry element in manifest.xml."""

    full_path: Optional[str] = None
    media_type: Optional[str] = None
    size: Optional[int] = None
    encryption_data: Optional[EncryptionData] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.odf_file_entry

    def create_encryption_data(self) -> EncryptionData:
        self.encryption_data = EncryptionData()
        return self.encryption_data

    def remove_encryption_data(self) -> None:
        self.encryption_data = None

    def clone(self) -> FileEntry:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: FileEntry) -> None:
        self.full_path = from_obj.full_path
        self.media_type = from_obj.media_type
        self.size = from_obj.size
        self.encryption_data = (
            from_obj.encryption_data.clone() if from_obj.encryption_data else None
        )
        self._copy_switches_from(from_obj)


# --- ManifestXMLFile ---

@dataclass
class ManifestXMLFile(SwitchableObject):
    """Port of META-INF/manifest.xml file object."""

    file_entry_list: List[FileEntry] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.odf_manifest

    def count_of_file_entry(self) -> int:
        return len(self.file_entry_list)

    def get_file_entry(self, index: int) -> FileEntry:
        return self.file_entry_list[index]

    def get_file_entry_index(self, file_entry: FileEntry) -> int:
        for i, v in enumerate(self.file_entry_list):
            if v is file_entry:
                return i
        return -1

    def add_file_entry(self, file_entry: FileEntry) -> None:
        self.file_entry_list.append(file_entry)

    def add_new_file_entry(self) -> FileEntry:
        fe = FileEntry()
        self.file_entry_list.append(fe)
        return fe

    def insert_file_entry(self, file_entry: FileEntry, position: int) -> None:
        self.file_entry_list.insert(position, file_entry)

    def remove_file_entry(self, position_or_item) -> None:
        if isinstance(position_or_item, int):
            del self.file_entry_list[position_or_item]
        else:
            self.file_entry_list.remove(position_or_item)

    def remove_all_file_entries(self) -> None:
        self.file_entry_list.clear()

    def clone(self) -> ManifestXMLFile:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: ManifestXMLFile) -> None:
        self.file_entry_list = [fe.clone() for fe in from_obj.file_entry_list]
        self._copy_switches_from(from_obj)
