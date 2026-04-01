"""Port of root/SettingsXMLFile.java, ConfigItemSet.java, ConfigItem.java, CaretPosition.java."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import List, Optional

from pyhwpxlib.base import HWPXObject, SwitchableObject
from pyhwpxlib.object_type import ObjectType


# --- CaretPosition ---

@dataclass
class CaretPosition(HWPXObject):
    """Caret position in a paragraph."""

    list_id_ref: Optional[int] = None
    para_id_ref: Optional[int] = None
    pos: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.ha_CaretPosition

    def clone(self) -> CaretPosition:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: CaretPosition) -> None:
        self.list_id_ref = from_obj.list_id_ref
        self.para_id_ref = from_obj.para_id_ref
        self.pos = from_obj.pos


# --- ConfigItem ---

@dataclass
class ConfigItem(HWPXObject):
    """A single config-item element."""

    name: Optional[str] = None
    type: Optional[str] = None
    value: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.config_item

    def clone(self) -> ConfigItem:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: ConfigItem) -> None:
        self.name = from_obj.name
        self.type = from_obj.type
        self.value = from_obj.value


# --- ConfigItemSet ---

@dataclass
class ConfigItemSet(SwitchableObject):
    """A set of config items (<config-item-set/>)."""

    name: Optional[str] = None
    config_item_list: List[ConfigItem] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.config_item_set

    def count_of_config_item(self) -> int:
        return len(self.config_item_list)

    def get_config_item(self, index: int) -> ConfigItem:
        return self.config_item_list[index]

    def get_config_item_index(self, config_item: ConfigItem) -> int:
        for i, v in enumerate(self.config_item_list):
            if v is config_item:
                return i
        return -1

    def add_config_item(self, config_item: ConfigItem) -> None:
        self.config_item_list.append(config_item)

    def add_new_config_item(self) -> ConfigItem:
        item = ConfigItem()
        self.config_item_list.append(item)
        return item

    def insert_config_item(self, config_item: ConfigItem, position: int) -> None:
        self.config_item_list.insert(position, config_item)

    def remove_config_item(self, position_or_item) -> None:
        if isinstance(position_or_item, int):
            del self.config_item_list[position_or_item]
        else:
            self.config_item_list.remove(position_or_item)

    def remove_all_config_items(self) -> None:
        self.config_item_list.clear()

    def clone(self) -> ConfigItemSet:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: ConfigItemSet) -> None:
        self.name = from_obj.name
        self.config_item_list = [item.clone() for item in from_obj.config_item_list]
        self._copy_switches_from(from_obj)


# --- SettingsXMLFile ---

@dataclass
class SettingsXMLFile(SwitchableObject):
    """Port of /settings.xml file object."""

    caret_position: Optional[CaretPosition] = None
    config_item_set: Optional[ConfigItemSet] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.ha_HWPApplicationSetting

    def create_caret_position(self) -> CaretPosition:
        self.caret_position = CaretPosition()
        return self.caret_position

    def remove_caret_position(self) -> None:
        self.caret_position = None

    def create_config_item_set(self) -> ConfigItemSet:
        self.config_item_set = ConfigItemSet()
        return self.config_item_set

    def remove_config_item_set(self) -> None:
        self.config_item_set = None

    def clone(self) -> SettingsXMLFile:
        return copy.deepcopy(self)

    def copy_from(self, from_obj: SettingsXMLFile) -> None:
        self.caret_position = (
            from_obj.caret_position.clone() if from_obj.caret_position else None
        )
        self.config_item_set = (
            from_obj.config_item_set.clone() if from_obj.config_item_set else None
        )
        self._copy_switches_from(from_obj)
