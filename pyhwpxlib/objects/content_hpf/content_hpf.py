"""Port of content/context_hpf/ classes: ContentHPFFile, ManifestItem, Meta, MetaData, SpineItemRef."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import List, Optional

from pyhwpxlib.base import AttachedFile, HWPXObject, ObjectList, SwitchableObject
from pyhwpxlib.objects.common.base_objects import HasOnlyText
from pyhwpxlib.object_type import ObjectType


# --- SpineItemRef ---

@dataclass
class SpineItemRef(HWPXObject):
    """A spine item reference."""

    idref: Optional[str] = None
    linear: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.opf_itemref

    def clone(self) -> SpineItemRef:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: SpineItemRef) -> None:
        self.idref = from_obj.idref
        self.linear = from_obj.linear


# --- Meta ---

@dataclass
class Meta(HWPXObject):
    """A <meta> element inside metadata."""

    name: Optional[str] = None
    content: Optional[str] = None
    text: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.opf_meta

    def clone(self) -> Meta:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: Meta) -> None:
        self.name = from_obj.name
        self.content = from_obj.content
        self.text = from_obj.text


# --- MetaData ---

@dataclass
class MetaData(SwitchableObject):
    """Metadata section of content.hpf."""

    title: Optional[HasOnlyText] = None
    language: Optional[HasOnlyText] = None
    meta_list: List[Meta] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.opf_metadata

    def create_title(self) -> HasOnlyText:
        self.title = HasOnlyText(ObjectType.opf_title)
        return self.title

    def remove_title(self) -> None:
        self.title = None

    def create_language(self) -> HasOnlyText:
        self.language = HasOnlyText(ObjectType.opf_language)
        return self.language

    def remove_language(self) -> None:
        self.language = None

    def count_of_meta(self) -> int:
        return len(self.meta_list)

    def get_meta(self, index: int) -> Meta:
        return self.meta_list[index]

    def get_meta_index(self, meta: Meta) -> int:
        for i, v in enumerate(self.meta_list):
            if v is meta:
                return i
        return -1

    def add_meta(self, meta: Meta) -> None:
        self.meta_list.append(meta)

    def add_new_meta(self) -> Meta:
        m = Meta()
        self.meta_list.append(m)
        return m

    def insert_meta(self, meta: Meta, position: int) -> None:
        self.meta_list.insert(position, meta)

    def remove_meta(self, position_or_item) -> None:
        if isinstance(position_or_item, int):
            del self.meta_list[position_or_item]
        else:
            self.meta_list.remove(position_or_item)

    def remove_all_metas(self) -> None:
        self.meta_list.clear()

    def clone(self) -> MetaData:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: MetaData) -> None:
        self.title = from_obj.title.clone() if from_obj.title else None
        self.language = from_obj.language.clone() if from_obj.language else None
        self.meta_list = [m.clone() for m in from_obj.meta_list]
        self._copy_switches_from(from_obj)


# --- ManifestItem ---

@dataclass
class ManifestItem(HWPXObject):
    """An <item> element in the manifest section of content.hpf."""

    id: Optional[str] = None
    href: Optional[str] = None
    media_type: Optional[str] = None
    fallback: Optional[str] = None
    fallback_style: Optional[str] = None
    required_namespace: Optional[str] = None
    required_modules: Optional[str] = None
    encryption: Optional[bool] = None
    file_size: Optional[int] = None
    is_embedded: Optional[bool] = None
    sub_path: Optional[str] = None
    attached_file: Optional[AttachedFile] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.opf_item

    def has_attached_file(self) -> bool:
        """Check if this media type requires an attached file."""
        from pyhwpxlib.constants.mime_types import OLE, Image_PreFix, Script_PreFix

        if self.media_type is None:
            return False
        return (
            self.media_type == OLE
            or self.media_type.startswith(Image_PreFix)
            or self.media_type.startswith(Script_PreFix)
        )

    def create_attached_file(self) -> AttachedFile:
        self.attached_file = AttachedFile()
        return self.attached_file

    def remove_attached_file(self) -> None:
        self.attached_file = None

    def clone(self) -> ManifestItem:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: ManifestItem) -> None:
        self.id = from_obj.id
        self.href = from_obj.href
        self.media_type = from_obj.media_type
        self.fallback = from_obj.fallback
        self.fallback_style = from_obj.fallback_style
        self.required_namespace = from_obj.required_namespace
        self.required_modules = from_obj.required_modules
        self.encryption = from_obj.encryption
        self.file_size = from_obj.file_size
        self.is_embedded = from_obj.is_embedded
        self.sub_path = from_obj.sub_path
        self.attached_file = (
            from_obj.attached_file.clone() if from_obj.attached_file else None
        )


# --- ContentHPFFile ---

@dataclass
class ContentHPFFile(SwitchableObject):
    """Port of Contents/content.hpf file object."""

    version: Optional[str] = None
    unique_identifier: Optional[str] = None
    id: Optional[str] = None
    meta_data: Optional[MetaData] = None
    manifest: Optional[ObjectList[ManifestItem]] = None
    spine: Optional[ObjectList[SpineItemRef]] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.opf_package

    def create_meta_data(self) -> MetaData:
        self.meta_data = MetaData()
        return self.meta_data

    def remove_meta_data(self) -> None:
        self.meta_data = None

    def create_manifest(self) -> ObjectList[ManifestItem]:
        self.manifest = ObjectList(
            _object_type_value=ObjectType.opf_manifest,
            _item_class=ManifestItem,
        )
        return self.manifest

    def remove_manifest(self) -> None:
        self.manifest = None

    def get_manifest_item_by_id(self, item_id: str) -> Optional[ManifestItem]:
        if self.manifest is None:
            return None
        for item in self.manifest.items():
            if item.id == item_id:
                return item
        return None

    def create_spine(self) -> ObjectList[SpineItemRef]:
        self.spine = ObjectList(
            _object_type_value=ObjectType.opf_spine,
            _item_class=SpineItemRef,
        )
        return self.spine

    def remove_spine(self) -> None:
        self.spine = None

    def clone(self) -> ContentHPFFile:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: ContentHPFFile) -> None:
        self.version = from_obj.version
        self.unique_identifier = from_obj.unique_identifier
        self.id = from_obj.id
        self.meta_data = (
            from_obj.meta_data.clone() if from_obj.meta_data else None
        )
        if from_obj.manifest is not None:
            self.create_manifest()
            for item in from_obj.manifest.items():
                self.manifest.add(item.clone())
        else:
            self.remove_manifest()
        if from_obj.spine is not None:
            self.create_spine()
            for ref in from_obj.spine.items():
                self.spine.add(ref.clone())
        else:
            self.remove_spine()
        self._copy_switches_from(from_obj)
