"""DrawingObject base, ShapeComponent base, ShapeObject base, and
supporting types (ShapeSize, ShapePosition, Caption, Flip, RotationInfo,
RenderingInfo, DrawText, DrawingShadow).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from ....base import HWPXObject, SwitchableObject
from ....object_type import ObjectType
from ....objects.common.base_objects import (
    HasOnlyText,
    LeftRightTopBottom,
    Point,
    WidthAndHeight,
    XAndY,
)
from ...section.enum_types import (
    CaptionSide,
    DrawingShadowType,
    DropCapStyle,
    HeightRelTo,
    HorzAlign,
    HorzRelTo,
    NumberingType,
    TextDirection,
    TextFlowSide,
    TextWrapMethod,
    VertAlign,
    VertRelTo,
    VerticalAlign2,
    WidthRelTo,
)
from ...section.paragraph import RunItem


# ============================================================
# ShapeSize, ShapePosition
# ============================================================

@dataclass
class ShapeSize(HWPXObject):
    """Shape size (hp:sz)."""

    width: Optional[int] = None
    height: Optional[int] = None
    width_rel_to: Optional[WidthRelTo] = None
    height_rel_to: Optional[HeightRelTo] = None
    protect: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_sz


@dataclass
class ShapePosition(HWPXObject):
    """Shape position (hp:pos)."""

    treat_as_char: Optional[bool] = None
    affect_line_spacing: Optional[bool] = None
    flow_with_text: Optional[bool] = None
    allow_overlap: Optional[bool] = None
    hold_anchor_and_so: Optional[bool] = None
    vert_rel_to: Optional[VertRelTo] = None
    vert_align: Optional[VertAlign] = None
    horz_rel_to: Optional[HorzRelTo] = None
    horz_align: Optional[HorzAlign] = None
    vert_offset: Optional[int] = None
    horz_offset: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_pos_for_shapeObject


# ============================================================
# Caption
# ============================================================

@dataclass
class Caption(SwitchableObject):
    """Caption for a shape object (hp:caption)."""

    side: Optional[CaptionSide] = None
    full_sz: Optional[bool] = None
    width: Optional[int] = None
    gap: Optional[int] = None
    last_width: Optional[int] = None
    sub_list: Optional[Any] = None  # SubList

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_caption

    def create_sub_list(self) -> Any:
        from ...section.section_xml_file import SubList
        self.sub_list = SubList()
        return self.sub_list

    def remove_sub_list(self) -> None:
        self.sub_list = None


# ============================================================
# Flip, RotationInfo, RenderingInfo (ShapeComponent sub-objects)
# ============================================================

@dataclass
class Flip(HWPXObject):
    """Flip state (hp:flip)."""

    horizontal: Optional[bool] = None
    vertical: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_flip


@dataclass
class RotationInfo(HWPXObject):
    """Rotation info (hp:rotationInfo)."""

    angle: Optional[int] = None
    center_x: Optional[int] = None
    center_y: Optional[int] = None
    rotate_image: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_rotationInfo


@dataclass
class Matrix(HWPXObject):
    """Transformation matrix."""

    _object_type_value: ObjectType = field(default=ObjectType.hc_transMatrix)
    e1: Optional[float] = None
    e2: Optional[float] = None
    e3: Optional[float] = None
    e4: Optional[float] = None
    e5: Optional[float] = None
    e6: Optional[float] = None

    def _object_type(self) -> ObjectType:
        return self._object_type_value


@dataclass
class RenderingInfo(HWPXObject):
    """Rendering/transformation info (hp:renderingInfo)."""

    trans_matrix: Optional[Matrix] = None
    sca_matrix: Optional[Matrix] = None
    rot_matrix: Optional[Matrix] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_renderingInfo

    def create_trans_matrix(self) -> Matrix:
        self.trans_matrix = Matrix(_object_type_value=ObjectType.hc_transMatrix)
        return self.trans_matrix

    def create_sca_matrix(self) -> Matrix:
        self.sca_matrix = Matrix(_object_type_value=ObjectType.hc_scaMatrix)
        return self.sca_matrix

    def create_rot_matrix(self) -> Matrix:
        self.rot_matrix = Matrix(_object_type_value=ObjectType.hc_rotMatrix)
        return self.rot_matrix


# ============================================================
# DrawText, DrawingShadow (DrawingObject sub-objects)
# ============================================================

@dataclass
class DrawText(SwitchableObject):
    """Text box inside a drawing object (hp:drawText)."""

    last_width: Optional[int] = None
    name: Optional[str] = None
    editable: Optional[bool] = None
    text_direction: Optional[TextDirection] = None
    text_margin: Optional[LeftRightTopBottom] = None
    sub_list: Optional[Any] = None  # SubList

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_drawText

    def create_text_margin(self) -> LeftRightTopBottom:
        self.text_margin = LeftRightTopBottom(ObjectType.hp_textMargin)
        return self.text_margin

    def remove_text_margin(self) -> None:
        self.text_margin = None

    def create_sub_list(self) -> Any:
        from ...section.section_xml_file import SubList
        self.sub_list = SubList()
        return self.sub_list

    def remove_sub_list(self) -> None:
        self.sub_list = None


@dataclass
class DrawingShadow(HWPXObject):
    """Drawing shadow (hp:shadow for drawingObject)."""

    type: Optional[DrawingShadowType] = None
    color: Optional[str] = None
    offset_x: Optional[int] = None
    offset_y: Optional[int] = None
    alpha: Optional[float] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_shadow_for_drawingObject


# ============================================================
# ShapeObject (abstract base for all shape objects)
# ============================================================

@dataclass
class ShapeObject(RunItem):
    """Abstract base for shape objects (table, picture, equation, etc.)."""

    so_id: Optional[str] = None
    z_order: Optional[int] = None
    numbering_type: Optional[NumberingType] = None
    text_wrap: Optional[TextWrapMethod] = None
    text_flow: Optional[TextFlowSide] = None
    lock: Optional[bool] = None
    dropcapstyle: Optional[DropCapStyle] = None
    sz: Optional[ShapeSize] = None
    pos: Optional[ShapePosition] = None
    out_margin: Optional[LeftRightTopBottom] = None
    caption: Optional[Caption] = None
    shape_comment: Optional[HasOnlyText] = None

    def _object_type(self) -> ObjectType:
        raise NotImplementedError

    def create_sz(self) -> ShapeSize:
        self.sz = ShapeSize()
        return self.sz

    def remove_sz(self) -> None:
        self.sz = None

    def create_pos(self) -> ShapePosition:
        self.pos = ShapePosition()
        return self.pos

    def remove_pos(self) -> None:
        self.pos = None

    def create_out_margin(self) -> LeftRightTopBottom:
        self.out_margin = LeftRightTopBottom(ObjectType.hp_outMargin)
        return self.out_margin

    def remove_out_margin(self) -> None:
        self.out_margin = None

    def create_caption(self) -> Caption:
        self.caption = Caption()
        return self.caption

    def remove_caption(self) -> None:
        self.caption = None

    def create_shape_comment(self) -> HasOnlyText:
        self.shape_comment = HasOnlyText(ObjectType.hp_shapeComment)
        return self.shape_comment

    def remove_shape_comment(self) -> None:
        self.shape_comment = None


# ============================================================
# ShapeComponent (abstract - extends ShapeObject with transform data)
# ============================================================

@dataclass
class ShapeComponent(ShapeObject):
    """Abstract base for shape components with transformation data."""

    href: Optional[str] = None
    group_level: Optional[int] = None
    instid: Optional[str] = None
    offset: Optional[XAndY] = None
    org_sz: Optional[WidthAndHeight] = None
    cur_sz: Optional[WidthAndHeight] = None
    flip: Optional[Flip] = None
    rotation_info: Optional[RotationInfo] = None
    rendering_info: Optional[RenderingInfo] = None

    def _object_type(self) -> ObjectType:
        raise NotImplementedError

    def create_offset(self) -> XAndY:
        self.offset = XAndY(ObjectType.hp_offset_for_shapeComponent)
        return self.offset

    def remove_offset(self) -> None:
        self.offset = None

    def create_org_sz(self) -> WidthAndHeight:
        self.org_sz = WidthAndHeight(ObjectType.hp_orgSz)
        return self.org_sz

    def remove_org_sz(self) -> None:
        self.org_sz = None

    def create_cur_sz(self) -> WidthAndHeight:
        self.cur_sz = WidthAndHeight(ObjectType.hp_curSz)
        return self.cur_sz

    def remove_cur_sz(self) -> None:
        self.cur_sz = None

    def create_flip(self) -> Flip:
        self.flip = Flip()
        return self.flip

    def remove_flip(self) -> None:
        self.flip = None

    def create_rotation_info(self) -> RotationInfo:
        self.rotation_info = RotationInfo()
        return self.rotation_info

    def remove_rotation_info(self) -> None:
        self.rotation_info = None

    def create_rendering_info(self) -> RenderingInfo:
        self.rendering_info = RenderingInfo()
        return self.rendering_info

    def remove_rendering_info(self) -> None:
        self.rendering_info = None


# ============================================================
# DrawingObject (abstract - extends ShapeComponent with line/fill/text/shadow)
# ============================================================

@dataclass
class DrawingObject(ShapeComponent):
    """Abstract base for drawing objects (rect, ellipse, line, etc.)."""

    line_shape: Optional[Any] = None  # LineShape from picture module
    fill_brush: Optional[Any] = None  # FillBrush from header
    draw_text: Optional[DrawText] = None
    shadow: Optional[DrawingShadow] = None

    def _object_type(self) -> ObjectType:
        raise NotImplementedError

    def create_draw_text(self) -> DrawText:
        self.draw_text = DrawText()
        return self.draw_text

    def remove_draw_text(self) -> None:
        self.draw_text = None

    def create_shadow(self) -> DrawingShadow:
        self.shadow = DrawingShadow()
        return self.shadow

    def remove_shadow(self) -> None:
        self.shadow = None
