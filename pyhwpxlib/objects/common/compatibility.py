"""Compatibility classes: InSwitchObject, Switch, Case, Default."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ...base import HWPXObject
from ...object_type import ObjectType


@dataclass
class InSwitchObject(HWPXObject):
    """Abstract base for objects inside a Switch (Case, Default)."""

    _child_list: List[HWPXObject] = field(default_factory=list)

    def count_of_child(self) -> int:
        return len(self._child_list)

    def get_child(self, index: int) -> HWPXObject:
        return self._child_list[index]

    def add_child(self, child: HWPXObject) -> None:
        self._child_list.append(child)

    def insert_child(self, child: HWPXObject, position: int) -> None:
        self._child_list.insert(position, child)

    def remove_child(self, position_or_child) -> None:
        if isinstance(position_or_child, int):
            del self._child_list[position_or_child]
        else:
            self._child_list.remove(position_or_child)

    def remove_all_children(self) -> None:
        self._child_list.clear()

    def children(self) -> List[HWPXObject]:
        return self._child_list

    def _copy_children_from(self, from_obj: InSwitchObject) -> None:
        for child in from_obj._child_list:
            self.add_child(child.clone())


@dataclass
class Case(InSwitchObject):
    """hp:case element inside a Switch."""

    required_namespace: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_case

    def required_namespace_and(self, required_namespace: str) -> Case:
        self.required_namespace = required_namespace
        return self

    def clone(self) -> Case:
        cloned = Case()
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: Case) -> None:
        self.required_namespace = from_obj.required_namespace
        self._copy_children_from(from_obj)


@dataclass
class Default(InSwitchObject):
    """hp:default element inside a Switch."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_default

    def clone(self) -> Default:
        cloned = Default()
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: Default) -> None:
        self._copy_children_from(from_obj)


@dataclass
class Switch(HWPXObject):
    """hp:switch compatibility element containing Case and Default objects."""

    _case_object_list: List[Case] = field(default_factory=list)
    _default_object: Optional[Default] = None
    position: int = -1

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_switch

    def count_of_case_object(self) -> int:
        return len(self._case_object_list)

    def get_case_object(self, index: int) -> Case:
        return self._case_object_list[index]

    def add_case_object(self, case_object: Case) -> None:
        self._case_object_list.append(case_object)

    def add_new_case_object(self) -> Case:
        case_object = Case()
        self._case_object_list.append(case_object)
        return case_object

    def insert_case_object(self, case_object: Case, position: int) -> None:
        self._case_object_list.insert(position, case_object)

    def remove_case_object(self, position_or_case) -> None:
        if isinstance(position_or_case, int):
            del self._case_object_list[position_or_case]
        else:
            self._case_object_list.remove(position_or_case)

    def remove_all_case_objects(self) -> None:
        self._case_object_list.clear()

    def case_objects(self) -> List[Case]:
        return self._case_object_list

    def default_object(self) -> Optional[Default]:
        return self._default_object

    def create_default_object(self) -> None:
        self._default_object = Default()

    def remove_default_object(self) -> None:
        self._default_object = None

    def clone(self) -> Switch:
        cloned = Switch()
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: Switch) -> None:
        for case_object in from_obj._case_object_list:
            self._case_object_list.append(case_object.clone())
        if from_obj._default_object is not None:
            self._default_object = from_obj._default_object.clone()
        else:
            self._default_object = None
        self.position = from_obj.position
