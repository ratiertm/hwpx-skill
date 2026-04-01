"""Parameter classes: Param, ParameterListCore, IntegerParam, UnsignedIntegerParam,
FloatParam, BooleanParam, StringParam, ListParam."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ...base import SwitchableObject
from ...object_type import ObjectType


@dataclass
class Param(SwitchableObject):
    """Abstract base for all parameter types."""

    name: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.Unknown

    def name_and(self, name: str) -> Param:
        self.name = name
        return self

    def copy_from(self, from_obj: Param) -> None:
        self.name = from_obj.name
        self._copy_switches_from(from_obj)


@dataclass
class IntegerParam(Param):
    """Integer parameter (hp:integerParam)."""

    value: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_integerParam

    def value_and(self, value: Optional[int]) -> IntegerParam:
        self.value = value
        return self

    def clone(self) -> IntegerParam:
        cloned = IntegerParam()
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: IntegerParam) -> None:
        self.value = from_obj.value
        super().copy_from(from_obj)


@dataclass
class UnsignedIntegerParam(Param):
    """Unsigned integer parameter (hp:unsignedintegerParam). Uses int (Long in Java)."""

    value: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_unsignedintegerParam

    def value_and(self, value: Optional[int]) -> UnsignedIntegerParam:
        self.value = value
        return self

    def clone(self) -> UnsignedIntegerParam:
        cloned = UnsignedIntegerParam()
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: UnsignedIntegerParam) -> None:
        self.value = from_obj.value
        super().copy_from(from_obj)


@dataclass
class FloatParam(Param):
    """Float parameter (hp:floatParam)."""

    value: Optional[float] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_floatParam

    def value_and(self, value: Optional[float]) -> FloatParam:
        self.value = value
        return self

    def clone(self) -> FloatParam:
        cloned = FloatParam()
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: FloatParam) -> None:
        self.value = from_obj.value
        super().copy_from(from_obj)


@dataclass
class BooleanParam(Param):
    """Boolean parameter (hp:booleanParam)."""

    value: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_booleanParam

    def value_and(self, value: Optional[bool]) -> BooleanParam:
        self.value = value
        return self

    def clone(self) -> BooleanParam:
        cloned = BooleanParam()
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: BooleanParam) -> None:
        self.value = from_obj.value
        super().copy_from(from_obj)


@dataclass
class StringParam(Param):
    """String parameter (hp:stringParam)."""

    value: Optional[str] = None
    xml_space: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_stringParam

    def value_and(self, value: Optional[str]) -> StringParam:
        self.value = value
        return self

    def xml_space_and(self, xml_space: Optional[str]) -> StringParam:
        self.xml_space = xml_space
        return self

    def clone(self) -> StringParam:
        cloned = StringParam()
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: StringParam) -> None:
        self.value = from_obj.value
        self.xml_space = from_obj.xml_space
        super().copy_from(from_obj)


@dataclass
class ListParam(Param):
    """List parameter (hp:listParam) - contains child parameters."""

    _parameter_list: List[Param] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_listParam

    def cnt(self) -> int:
        return self.count_of_param()

    def count_of_param(self) -> int:
        return len(self._parameter_list)

    def get_param(self, index: int) -> Param:
        return self._parameter_list[index]

    def get_param_index(self, parameter: Param) -> int:
        for i, p in enumerate(self._parameter_list):
            if p is parameter:
                return i
        return -1

    def add_param(self, parameter: Param) -> None:
        self._parameter_list.append(parameter)

    def add_new_boolean_param(self) -> BooleanParam:
        p = BooleanParam()
        self._parameter_list.append(p)
        return p

    def add_new_integer_param(self) -> IntegerParam:
        p = IntegerParam()
        self._parameter_list.append(p)
        return p

    def add_new_unsigned_integer_param(self) -> UnsignedIntegerParam:
        p = UnsignedIntegerParam()
        self._parameter_list.append(p)
        return p

    def add_new_float_param(self) -> FloatParam:
        p = FloatParam()
        self._parameter_list.append(p)
        return p

    def add_new_string_param(self) -> StringParam:
        p = StringParam()
        self._parameter_list.append(p)
        return p

    def add_new_list_param(self) -> ListParam:
        p = ListParam()
        self._parameter_list.append(p)
        return p

    def insert_param(self, parameter: Param, position: int) -> None:
        self._parameter_list.insert(position, parameter)

    def remove_param(self, position_or_param) -> None:
        if isinstance(position_or_param, int):
            del self._parameter_list[position_or_param]
        else:
            self._parameter_list.remove(position_or_param)

    def remove_all_params(self) -> None:
        self._parameter_list.clear()

    def params(self) -> List[Param]:
        return self._parameter_list

    def clone(self) -> ListParam:
        cloned = ListParam()
        cloned.copy_from(self)
        return cloned

    def copy_from(self, from_obj: ListParam) -> None:
        for param in from_obj._parameter_list:
            self._parameter_list.append(param.clone())
        super().copy_from(from_obj)


@dataclass
class ParameterListCore(SwitchableObject):
    """Core parameter list container (abstract base for parameter sets)."""

    name: Optional[str] = None
    _parameter_list: List[Param] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.Unknown

    def name_and(self, name: str) -> ParameterListCore:
        self.name = name
        return self

    def cnt(self) -> int:
        return self.count_of_param()

    def count_of_param(self) -> int:
        return len(self._parameter_list)

    def get_param(self, index: int) -> Param:
        return self._parameter_list[index]

    def get_param_index(self, parameter: Param) -> int:
        for i, p in enumerate(self._parameter_list):
            if p is parameter:
                return i
        return -1

    def add_param(self, parameter: Param) -> None:
        self._parameter_list.append(parameter)

    def add_new_boolean_param(self) -> BooleanParam:
        p = BooleanParam()
        self._parameter_list.append(p)
        return p

    def add_new_integer_param(self) -> IntegerParam:
        p = IntegerParam()
        self._parameter_list.append(p)
        return p

    def add_new_unsigned_integer_param(self) -> UnsignedIntegerParam:
        p = UnsignedIntegerParam()
        self._parameter_list.append(p)
        return p

    def add_new_float_param(self) -> FloatParam:
        p = FloatParam()
        self._parameter_list.append(p)
        return p

    def add_new_string_param(self) -> StringParam:
        p = StringParam()
        self._parameter_list.append(p)
        return p

    def add_new_list_param(self) -> ListParam:
        p = ListParam()
        self._parameter_list.append(p)
        return p

    def insert_param(self, parameter: Param, position: int) -> None:
        self._parameter_list.insert(position, parameter)

    def remove_param(self, position_or_param) -> None:
        if isinstance(position_or_param, int):
            del self._parameter_list[position_or_param]
        else:
            self._parameter_list.remove(position_or_param)

    def remove_all_params(self) -> None:
        self._parameter_list.clear()

    def params(self) -> List[Param]:
        return self._parameter_list

    def copy_from(self, from_obj: ParameterListCore) -> None:
        self.name = from_obj.name
        for param in from_obj._parameter_list:
            self._parameter_list.append(param.clone())
