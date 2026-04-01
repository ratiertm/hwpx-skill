"""Base classes for pyhwpxlib: HWPXObject, SwitchableObject, ObjectList, AttachedFile."""
from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, Iterator, List, Optional, Type, TypeVar

from .object_type import ObjectType

T = TypeVar("T")


@dataclass
class HWPXObject(ABC):
    """Base class for all HWPX objects."""

    @abstractmethod
    def _object_type(self) -> ObjectType:
        ...

    def clone(self) -> HWPXObject:
        return copy.deepcopy(self)


@dataclass
class SwitchableObject(HWPXObject):
    """HWPXObject that can contain hp:switch compatibility elements."""

    _switch_list: Optional[List["Switch"]] = field(default=None, repr=False)

    def switch_list(self) -> Optional[List["Switch"]]:
        return self._switch_list

    def remove_switch_list(self) -> None:
        self._switch_list = None

    def add_new_switch(self) -> "Switch":
        from .objects.common.compatibility import Switch

        if self._switch_list is None:
            self._switch_list = []
        sw = Switch()
        self._switch_list.append(sw)
        return sw

    def _copy_switches_from(self, from_obj: SwitchableObject) -> None:
        if from_obj._switch_list is not None:
            self._switch_list = []
            for sw in from_obj._switch_list:
                new_sw = self.add_new_switch()
                new_sw.copy_from(sw)
        else:
            self._switch_list = None


@dataclass
class ObjectList(SwitchableObject, Generic[T]):
    """Generic typed list wrapper (port of Java ObjectList<ItemType>)."""

    _object_type_value: Optional[ObjectType] = field(default=None, repr=False)
    _item_class: Optional[Type[T]] = field(default=None, repr=False)
    _list: List[T] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def count(self) -> int:
        return len(self._list)

    def get(self, index: int) -> T:
        return self._list[index]

    def get_index(self, item: T) -> int:
        for i, v in enumerate(self._list):
            if v is item:
                return i
        return -1

    def add(self, item: T) -> None:
        self._list.append(item)

    def add_new(self) -> Optional[T]:
        if self._item_class is None:
            return None
        instance = self._item_class()
        self._list.append(instance)
        return instance

    def insert(self, item: T, position: int) -> None:
        self._list.insert(position, item)

    def remove(self, position_or_item) -> None:
        if isinstance(position_or_item, int):
            del self._list[position_or_item]
        else:
            self._list.remove(position_or_item)

    def remove_all(self) -> None:
        self._list.clear()

    def items(self) -> List[T]:
        return self._list

    def empty(self) -> bool:
        return len(self._list) == 0

    def __iter__(self) -> Iterator[T]:
        return iter(self._list)

    def __len__(self) -> int:
        return len(self._list)


@dataclass
class AttachedFile:
    """Binary file attachment."""

    data: Optional[bytes] = None

    def clone(self) -> AttachedFile:
        cloned = AttachedFile()
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: AttachedFile) -> None:
        self.data = from_obj.data
