"""Picture object model and supporting types (LineShape, ImageRect,
ImageDim, Effects).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from ....base import HWPXObject
from ....object_type import ObjectType
from ....objects.common.base_objects import LeftRightTopBottom, Point
from ...section.enum_types import (
    ArrowSize,
    ArrowType,
    ColorEffectType,
    ColorType,
    LineCap,
    OutlineStyle,
    ShadowStyle,
)
from .drawing_object import ShapeComponent


# ============================================================
# LineShape (used by Picture, OLE, and DrawingObject)
# ============================================================

@dataclass
class LineShape(HWPXObject):
    """Line/border shape (hp:lineShape)."""

    color: Optional[str] = None
    width: Optional[int] = None
    type: Optional[str] = None  # LineType2
    style: Optional[OutlineStyle] = None
    end_cap: Optional[LineCap] = None
    head_style: Optional[ArrowType] = None
    tail_style: Optional[ArrowType] = None
    head_sz: Optional[ArrowSize] = None
    tail_sz: Optional[ArrowSize] = None
    head_fill: Optional[bool] = None
    tail_fill: Optional[bool] = None
    alpha: Optional[float] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_lineShape


# ============================================================
# ImageRect, ImageDim
# ============================================================

@dataclass
class ImageRect(HWPXObject):
    """Image coordinate rect (hp:imgRect)."""

    pt0: Optional[Point] = None
    pt1: Optional[Point] = None
    pt2: Optional[Point] = None
    pt3: Optional[Point] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_imgRect

    def create_pt0(self) -> Point:
        self.pt0 = Point(ObjectType.hc_pt0)
        return self.pt0

    def create_pt1(self) -> Point:
        self.pt1 = Point(ObjectType.hc_pt1)
        return self.pt1

    def create_pt2(self) -> Point:
        self.pt2 = Point(ObjectType.hc_pt2)
        return self.pt2

    def create_pt3(self) -> Point:
        self.pt3 = Point(ObjectType.hc_pt3)
        return self.pt3


@dataclass
class ImageDim(HWPXObject):
    """Image dimension (hp:imgDim)."""

    width: Optional[int] = None
    height: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_imgDim


# ============================================================
# Effects and sub-types
# ============================================================

@dataclass
class EffectsColor(HWPXObject):
    """Effects color (hp:effectsColor)."""

    type: Optional[ColorType] = None
    schema_color: Optional[str] = None
    system_color: Optional[str] = None
    r: Optional[int] = None
    g: Optional[int] = None
    b: Optional[int] = None
    c: Optional[int] = None
    m: Optional[int] = None
    y: Optional[int] = None
    k: Optional[int] = None
    _effects: List[Any] = field(default_factory=list)  # ColorEffect entries

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_effectsColor


@dataclass
class ColorEffect(HWPXObject):
    """Color effect entry (hp:effect)."""

    type: Optional[ColorEffectType] = None
    value: Optional[float] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_effect


@dataclass
class EffectShadow(HWPXObject):
    """Shadow effect (hp:shadow for effects)."""

    alignment: Optional[str] = None
    radius: Optional[float] = None
    direction: Optional[int] = None
    distance: Optional[int] = None
    rotation_with_shape: Optional[bool] = None
    color: Optional[EffectsColor] = None
    alpha: Optional[float] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_shadow_for_effects


@dataclass
class Glow(HWPXObject):
    """Glow effect (hp:glow)."""

    radius: Optional[float] = None
    color: Optional[EffectsColor] = None
    alpha: Optional[float] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_glow


@dataclass
class SoftEdge(HWPXObject):
    """Soft edge effect (hp:softEdge)."""

    radius: Optional[float] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_softEdge


@dataclass
class Reflection(HWPXObject):
    """Reflection effect (hp:reflection)."""

    alignment: Optional[str] = None
    radius: Optional[float] = None
    direction: Optional[int] = None
    distance: Optional[int] = None
    skew_x: Optional[float] = None
    skew_y: Optional[float] = None
    scale_x: Optional[float] = None
    scale_y: Optional[float] = None
    rotation_with_shape: Optional[bool] = None
    fade_direction: Optional[int] = None
    start_position: Optional[float] = None
    start_transparency: Optional[float] = None
    end_position: Optional[float] = None
    end_transparency: Optional[float] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_reflection


@dataclass
class Effects(HWPXObject):
    """Image effects container (hp:effects)."""

    shadow: Optional[EffectShadow] = None
    glow: Optional[Glow] = None
    soft_edge: Optional[SoftEdge] = None
    reflection: Optional[Reflection] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_effects

    def create_shadow(self) -> EffectShadow:
        self.shadow = EffectShadow()
        return self.shadow

    def remove_shadow(self) -> None:
        self.shadow = None

    def create_glow(self) -> Glow:
        self.glow = Glow()
        return self.glow

    def remove_glow(self) -> None:
        self.glow = None

    def create_soft_edge(self) -> SoftEdge:
        self.soft_edge = SoftEdge()
        return self.soft_edge

    def remove_soft_edge(self) -> None:
        self.soft_edge = None

    def create_reflection(self) -> Reflection:
        self.reflection = Reflection()
        return self.reflection

    def remove_reflection(self) -> None:
        self.reflection = None


# ============================================================
# Picture
# ============================================================

@dataclass
class Picture(ShapeComponent):
    """Picture object (hp:pic)."""

    reverse: Optional[bool] = None
    pic_line_shape: Optional[LineShape] = None
    img_rect: Optional[ImageRect] = None
    img_clip: Optional[LeftRightTopBottom] = None
    in_margin: Optional[LeftRightTopBottom] = None
    img_dim: Optional[ImageDim] = None
    img: Optional[Any] = None  # Image from header_xml
    effects: Optional[Effects] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_pic

    def create_line_shape(self) -> LineShape:
        self.pic_line_shape = LineShape()
        return self.pic_line_shape

    def remove_line_shape(self) -> None:
        self.pic_line_shape = None

    def create_img_rect(self) -> ImageRect:
        self.img_rect = ImageRect()
        return self.img_rect

    def remove_img_rect(self) -> None:
        self.img_rect = None

    def create_img_clip(self) -> LeftRightTopBottom:
        self.img_clip = LeftRightTopBottom(ObjectType.hp_imgClip)
        return self.img_clip

    def remove_img_clip(self) -> None:
        self.img_clip = None

    def create_in_margin(self) -> LeftRightTopBottom:
        self.in_margin = LeftRightTopBottom(ObjectType.hp_inMargin)
        return self.in_margin

    def remove_in_margin(self) -> None:
        self.in_margin = None

    def create_img_dim(self) -> ImageDim:
        self.img_dim = ImageDim()
        return self.img_dim

    def remove_img_dim(self) -> None:
        self.img_dim = None

    def create_effects(self) -> Effects:
        self.effects = Effects()
        return self.effects

    def remove_effects(self) -> None:
        self.effects = None
