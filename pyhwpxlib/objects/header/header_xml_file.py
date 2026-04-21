"""Header XML file object model.

Ported from kr.dogfoot.hwpxlib.object.content.header_xml:
HeaderXMLFile, RefList, BeginNum, DocOption, CompatibleDocument,
TrackChangeConfig, ForbiddenWord, LinkInfo, LayoutCompatibilityItem.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import List, Optional

from ...base import HWPXObject, ObjectList, SwitchableObject
from ...object_type import ObjectType
from ..common.base_objects import HasOnlyText
from .enum_types import TargetProgramSort
from ..section.enum_types import LicenseType


# ---------------------------------------------------------------------------
# NoAttributeNoChild  (marker object with no attributes/children)
# ---------------------------------------------------------------------------

@dataclass
class NoAttributeNoChild(HWPXObject):
    """Object with no attributes and no children (e.g. bold, italic markers)."""

    _object_type_value: ObjectType = field(default=ObjectType.Unknown)

    def __init__(self, object_type: ObjectType = ObjectType.Unknown):
        self._object_type_value = object_type

    def _object_type(self) -> ObjectType:
        return self._object_type_value

    def clone(self) -> NoAttributeNoChild:
        return NoAttributeNoChild(self._object_type_value)


# ---------------------------------------------------------------------------
# BeginNum
# ---------------------------------------------------------------------------

@dataclass
class BeginNum(HWPXObject):
    """Start number info for pages, footnotes, etc."""

    page: Optional[int] = None
    footnote: Optional[int] = None
    endnote: Optional[int] = None
    pic: Optional[int] = None
    tbl: Optional[int] = None
    equation: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_beginNum

    def clone(self) -> BeginNum:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# LinkInfo
# ---------------------------------------------------------------------------

@dataclass
class LinkInfo(HWPXObject):
    """Link information in DocOption."""

    path: Optional[str] = None
    pageInherit: Optional[bool] = None
    footnoteInherit: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_linkinfo

    def clone(self) -> LinkInfo:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# LicenseMark
# ---------------------------------------------------------------------------

@dataclass
class LicenseMark(HWPXObject):
    """License mark info (CCL, KOGL)."""

    type: Optional[LicenseType] = None
    flag: Optional[int] = None
    lang: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_licensemark

    def clone(self) -> LicenseMark:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# DocOption
# ---------------------------------------------------------------------------

@dataclass
class DocOption(SwitchableObject):
    """Document option containing link info."""

    linkinfo: Optional[LinkInfo] = None
    licensemark: Optional[LicenseMark] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_docOption

    def create_linkinfo(self) -> LinkInfo:
        self.linkinfo = LinkInfo()
        return self.linkinfo

    def remove_linkinfo(self) -> None:
        self.linkinfo = None

    def create_licensemark(self) -> LicenseMark:
        self.licensemark = LicenseMark()
        return self.licensemark

    def remove_licensemark(self) -> None:
        self.licensemark = None

    def clone(self) -> DocOption:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# LayoutCompatibilityItem
# ---------------------------------------------------------------------------

@dataclass
class LayoutCompatibilityItem(HWPXObject):
    """Single layout compatibility item."""

    name: Optional[str] = None
    text: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.each_layoutCompatibilityItem

    def clone(self) -> LayoutCompatibilityItem:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# CompatibleDocument
# ---------------------------------------------------------------------------

@dataclass
class CompatibleDocument(SwitchableObject):
    """Compatible document settings."""

    targetProgram: Optional[TargetProgramSort] = None
    layoutCompatibility: Optional[ObjectList[LayoutCompatibilityItem]] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_compatibleDocument

    def create_layout_compatibility(self) -> ObjectList[LayoutCompatibilityItem]:
        self.layoutCompatibility = ObjectList(
            _object_type_value=ObjectType.hh_layoutCompatibility,
            _item_class=LayoutCompatibilityItem,
        )
        return self.layoutCompatibility

    def remove_layout_compatibility(self) -> None:
        self.layoutCompatibility = None

    def clone(self) -> CompatibleDocument:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# TrackChangeConfig
# ---------------------------------------------------------------------------

@dataclass
class TrackChangeConfig(SwitchableObject):
    """Track change configuration."""

    flags: Optional[int] = None
    # configItemSet is from root module; use generic Optional for now
    configItemSet: Optional[object] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_trackchageConfig

    def clone(self) -> TrackChangeConfig:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# ForbiddenWord
# ---------------------------------------------------------------------------

@dataclass
class ForbiddenWord(HWPXObject):
    """Forbidden word entry (contains only text)."""

    _buffer: str = field(default="", repr=False)

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_forbiddenWord

    def text(self) -> str:
        return self._buffer

    def add_text(self, text: str) -> None:
        self._buffer += text

    def clone(self) -> ForbiddenWord:
        cloned = ForbiddenWord()
        cloned.add_text(self._buffer)
        return cloned


# ---------------------------------------------------------------------------
# RefList  (forward-declared, needs reference types)
# ---------------------------------------------------------------------------

@dataclass
class RefList(SwitchableObject):
    """Reference list container -- holds all style/property collections.

    Import the concrete reference types lazily or set them after construction
    to avoid circular imports. The fields use Optional[ObjectList[...]] where
    the item type is imported from the references sub-package.
    """

    fontfaces: Optional[object] = None  # Fontfaces
    borderFills: Optional[ObjectList] = None
    charProperties: Optional[ObjectList] = None
    tabProperties: Optional[ObjectList] = None
    numberings: Optional[ObjectList] = None
    bullets: Optional[ObjectList] = None
    paraProperties: Optional[ObjectList] = None
    styles: Optional[ObjectList] = None
    memoProperties: Optional[ObjectList] = None
    trackChanges: Optional[ObjectList] = None
    trackChangeAuthors: Optional[ObjectList] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_refList

    # -- factory helpers (import reference types at call time) --

    def create_fontfaces(self) -> object:
        from .references.fontface import Fontfaces
        self.fontfaces = Fontfaces()
        return self.fontfaces

    def remove_fontfaces(self) -> None:
        self.fontfaces = None

    def create_border_fills(self) -> ObjectList:
        from .references.border_fill import BorderFill
        self.borderFills = ObjectList(
            _object_type_value=ObjectType.hh_borderFills,
            _item_class=BorderFill,
        )
        return self.borderFills

    def remove_border_fills(self) -> None:
        self.borderFills = None

    def create_char_properties(self) -> ObjectList:
        from .references.char_pr import CharPr
        self.charProperties = ObjectList(
            _object_type_value=ObjectType.hh_charProperties,
            _item_class=CharPr,
        )
        return self.charProperties

    def remove_char_properties(self) -> None:
        self.charProperties = None

    def create_tab_properties(self) -> ObjectList:
        from .references.tab_pr import TabPr
        self.tabProperties = ObjectList(
            _object_type_value=ObjectType.hh_tabProperties,
            _item_class=TabPr,
        )
        return self.tabProperties

    def remove_tab_properties(self) -> None:
        self.tabProperties = None

    def create_numberings(self) -> ObjectList:
        from .references.numbering import Numbering
        self.numberings = ObjectList(
            _object_type_value=ObjectType.hh_numberings,
            _item_class=Numbering,
        )
        return self.numberings

    def remove_numberings(self) -> None:
        self.numberings = None

    def create_bullets(self) -> ObjectList:
        from .references.numbering import Bullet
        self.bullets = ObjectList(
            _object_type_value=ObjectType.hh_bullets,
            _item_class=Bullet,
        )
        return self.bullets

    def remove_bullets(self) -> None:
        self.bullets = None

    def create_para_properties(self) -> ObjectList:
        from .references.para_pr import ParaPr
        self.paraProperties = ObjectList(
            _object_type_value=ObjectType.hh_paraProperties,
            _item_class=ParaPr,
        )
        return self.paraProperties

    def remove_para_properties(self) -> None:
        self.paraProperties = None

    def create_styles(self) -> ObjectList:
        from .references.style import Style
        self.styles = ObjectList(
            _object_type_value=ObjectType.hh_styles,
            _item_class=Style,
        )
        return self.styles

    def remove_styles(self) -> None:
        self.styles = None

    def create_memo_properties(self) -> ObjectList:
        from .references.memo_pr import MemoPr
        self.memoProperties = ObjectList(
            _object_type_value=ObjectType.hh_memoProperties,
            _item_class=MemoPr,
        )
        return self.memoProperties

    def remove_memo_properties(self) -> None:
        self.memoProperties = None

    def create_track_changes(self) -> ObjectList:
        from .references.track_change import TrackChange
        self.trackChanges = ObjectList(
            _object_type_value=ObjectType.hh_trackChanges,
            _item_class=TrackChange,
        )
        return self.trackChanges

    def remove_track_changes(self) -> None:
        self.trackChanges = None

    def create_track_change_authors(self) -> ObjectList:
        from .references.track_change import TrackChangeAuthor
        self.trackChangeAuthors = ObjectList(
            _object_type_value=ObjectType.hh_trackChangeAuthors,
            _item_class=TrackChangeAuthor,
        )
        return self.trackChangeAuthors

    def remove_track_change_authors(self) -> None:
        self.trackChangeAuthors = None

    def clone(self) -> RefList:
        return copy.deepcopy(self)


# ---------------------------------------------------------------------------
# HeaderXMLFile  (root object)
# ---------------------------------------------------------------------------

@dataclass
class HeaderXMLFile(SwitchableObject):
    """Root object for Contents/header.xml."""

    version: Optional[str] = None
    secCnt: Optional[int] = None
    beginNum: Optional[BeginNum] = None
    refList: Optional[RefList] = None
    forbiddenWordList: Optional[ObjectList[ForbiddenWord]] = None
    compatibleDocument: Optional[CompatibleDocument] = None
    docOption: Optional[DocOption] = None
    metaTag: Optional[HasOnlyText] = None
    trackChangeConfig: Optional[TrackChangeConfig] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hh_head

    # -- factory helpers --

    def create_begin_num(self) -> BeginNum:
        self.beginNum = BeginNum()
        return self.beginNum

    def remove_begin_num(self) -> None:
        self.beginNum = None

    def create_ref_list(self) -> RefList:
        self.refList = RefList()
        return self.refList

    def remove_ref_list(self) -> None:
        self.refList = None

    def create_forbidden_word_list(self) -> ObjectList[ForbiddenWord]:
        self.forbiddenWordList = ObjectList(
            _object_type_value=ObjectType.hh_forbiddenWordList,
            _item_class=ForbiddenWord,
        )
        return self.forbiddenWordList

    def remove_forbidden_word_list(self) -> None:
        self.forbiddenWordList = None

    def create_compatible_document(self) -> CompatibleDocument:
        self.compatibleDocument = CompatibleDocument()
        return self.compatibleDocument

    def remove_compatible_document(self) -> None:
        self.compatibleDocument = None

    def create_doc_option(self) -> DocOption:
        self.docOption = DocOption()
        return self.docOption

    def remove_doc_option(self) -> None:
        self.docOption = None

    def create_meta_tag(self) -> HasOnlyText:
        self.metaTag = HasOnlyText(ObjectType.hh_metaTag)
        return self.metaTag

    def remove_meta_tag(self) -> None:
        self.metaTag = None

    def create_track_change_config(self) -> TrackChangeConfig:
        self.trackChangeConfig = TrackChangeConfig()
        return self.trackChangeConfig

    def remove_track_change_config(self) -> None:
        self.trackChangeConfig = None

    def clone(self) -> HeaderXMLFile:
        return copy.deepcopy(self)
