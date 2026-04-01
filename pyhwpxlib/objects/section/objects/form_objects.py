"""Form objects - FormObject, ButtonCore, Button, RadioButton, CheckButton,
ComboBox, ListBox, Edit, ScrollBar, and supporting types.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from ....base import HWPXObject
from ....object_type import ObjectType
from ....objects.common.base_objects import HasOnlyText
from ...section.enum_types import (
    BackStyle,
    ButtonCheckValue,
    DisplayScrollBar,
    ScrollBarType,
    TabKeyBehavior,
)
from .drawing_object import ShapeObject


# ============================================================
# FormCharPr
# ============================================================

@dataclass
class FormCharPr(HWPXObject):
    """Form character properties (hp:formCharPr)."""

    char_pr_id_ref: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_formCharPr


# ============================================================
# ListItem (for ComboBox and ListBox)
# ============================================================

@dataclass
class ListItem(HWPXObject):
    """List item for combo/list box (hp:listItem)."""

    display_text: Optional[str] = None
    value: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_listItem


# ============================================================
# FormObject (abstract base)
# ============================================================

@dataclass
class FormObject(ShapeObject):
    """Abstract base for form objects."""

    name: Optional[str] = None
    fore_color: Optional[str] = None
    back_color: Optional[str] = None
    group_name: Optional[str] = None
    tab_stop: Optional[bool] = None
    tab_order: Optional[int] = None
    enabled: Optional[bool] = None
    border_type_id_ref: Optional[str] = None
    draw_frame: Optional[bool] = None
    printable: Optional[bool] = None
    form_editable: Optional[bool] = None
    command: Optional[str] = None
    form_char_pr: Optional[FormCharPr] = None

    def _object_type(self) -> ObjectType:
        raise NotImplementedError

    def create_form_char_pr(self) -> FormCharPr:
        self.form_char_pr = FormCharPr()
        return self.form_char_pr

    def remove_form_char_pr(self) -> None:
        self.form_char_pr = None


# ============================================================
# ButtonCore (abstract base for button-like form objects)
# ============================================================

@dataclass
class ButtonCore(FormObject):
    """Abstract base for button-like form objects."""

    caption_text: Optional[str] = None
    btn_value: Optional[ButtonCheckValue] = None
    radio_group_name: Optional[str] = None
    tri_state: Optional[bool] = None
    back_style: Optional[BackStyle] = None

    def _object_type(self) -> ObjectType:
        raise NotImplementedError


# ============================================================
# Concrete form objects
# ============================================================

@dataclass
class Button(ButtonCore):
    """Button form object (hp:btn)."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_btn


@dataclass
class RadioButton(ButtonCore):
    """Radio button form object (hp:radioBtn)."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_radioBtn


@dataclass
class CheckButton(ButtonCore):
    """Check button form object (hp:checkBtn)."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_checkBtn


@dataclass
class ComboBox(FormObject):
    """Combo box form object (hp:comboBox)."""

    list_box_rows: Optional[int] = None
    list_box_width: Optional[int] = None
    edit_enable: Optional[bool] = None
    selected_value: Optional[str] = None
    _list_item_list: List[ListItem] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_comboBox

    def count_of_list_item(self) -> int:
        return len(self._list_item_list)

    def get_list_item(self, index: int) -> ListItem:
        return self._list_item_list[index]

    def add_list_item(self, item: ListItem) -> None:
        self._list_item_list.append(item)

    def add_new_list_item(self) -> ListItem:
        li = ListItem()
        self._list_item_list.append(li)
        return li

    def list_items(self) -> List[ListItem]:
        return self._list_item_list


@dataclass
class ListBox(FormObject):
    """List box form object (hp:listBox)."""

    item_height: Optional[int] = None
    top_idx: Optional[int] = None
    selected_value: Optional[str] = None
    _list_item_list: List[ListItem] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_listBox

    def count_of_list_item(self) -> int:
        return len(self._list_item_list)

    def get_list_item(self, index: int) -> ListItem:
        return self._list_item_list[index]

    def add_list_item(self, item: ListItem) -> None:
        self._list_item_list.append(item)

    def add_new_list_item(self) -> ListItem:
        li = ListItem()
        self._list_item_list.append(li)
        return li

    def list_items(self) -> List[ListItem]:
        return self._list_item_list


@dataclass
class Edit(FormObject):
    """Edit box form object (hp:edit)."""

    multi_line: Optional[bool] = None
    password_char: Optional[str] = None
    max_length: Optional[int] = None
    scroll_bars: Optional[DisplayScrollBar] = None
    tab_key_behavior: Optional[TabKeyBehavior] = None
    num_only: Optional[bool] = None
    read_only: Optional[bool] = None
    align_text: Optional[str] = None  # HorizontalAlign1 from header enums
    edit_text: Optional[HasOnlyText] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_edit

    def create_text(self) -> HasOnlyText:
        self.edit_text = HasOnlyText(ObjectType.hp_text)
        return self.edit_text

    def remove_text(self) -> None:
        self.edit_text = None


@dataclass
class ScrollBar(FormObject):
    """Scroll bar form object (hp:scrollBar)."""

    delay: Optional[int] = None
    large_change: Optional[int] = None
    small_change: Optional[int] = None
    min_val: Optional[int] = None
    max_val: Optional[int] = None
    page: Optional[int] = None
    value: Optional[int] = None
    sb_type: Optional[ScrollBarType] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_scrollBar
