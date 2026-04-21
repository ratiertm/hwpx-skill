"""Paragraph object model - Para, Run, RunItem, T, TItem, NormalText,
Compose, LineSeg, Dutmal, and text-level control characters.

This is the core content model for HWPX documents.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from ...base import HWPXObject, ObjectList, SwitchableObject
from ...object_type import ObjectType
from ...objects.common.base_objects import HasOnlyText
from .enum_types import ComposeCircleType, ComposeType, DutmalPosType


# ============================================================
# Abstract base classes
# ============================================================

@dataclass
class RunItem(SwitchableObject):
    """Abstract base for items inside a Run (text, ctrl, table, picture...)."""

    def _object_type(self) -> ObjectType:
        raise NotImplementedError


@dataclass
class TItem(HWPXObject):
    """Abstract base for items inside a T element (text chars, markpen, tabs...)."""

    def _object_type(self) -> ObjectType:
        raise NotImplementedError


@dataclass
class CtrlItem(SwitchableObject):
    """Abstract base for control items inside a Ctrl element."""

    def _object_type(self) -> ObjectType:
        raise NotImplementedError


# ============================================================
# TItem concrete types (text-level inline elements)
# ============================================================

@dataclass
class NormalText(TItem):
    """Plain text content inside a T element."""

    text: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.NormalText


@dataclass
class MarkpenBegin(TItem):
    """Highlight pen start marker."""

    begin_color: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_markpenBegin


@dataclass
class MarkpenEnd(TItem):
    """Highlight pen end marker."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_markpenEnd


@dataclass
class TitleMark(TItem):
    """Title mark."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_titleMark


@dataclass
class Tab(TItem):
    """Tab character."""

    width: Optional[int] = None
    leader: Optional[str] = None  # LineType2 from header enums
    type: Optional[str] = None  # TabItemType from header enums

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_tab


@dataclass
class LineBreak(TItem):
    """Forced line break."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_lineBreak


@dataclass
class Hyphen(TItem):
    """Hyphen."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_hyphen


@dataclass
class NBSpace(TItem):
    """Non-breaking space."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_nbSpace


@dataclass
class FWSpace(TItem):
    """Fixed-width space."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_fwSpace


@dataclass
class MetaTag(RunItem):
    """Meta tag inside a run or paragraph (hp:metaTag)."""

    name: Optional[str] = None
    _buffer: str = field(default="", repr=False)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_metaTag

    def text(self) -> str:
        return self._buffer

    def add_text(self, text: str) -> None:
        self._buffer += text

    def clone(self) -> MetaTag:
        cloned = MetaTag(name=self.name)
        cloned.add_text(self._buffer)
        return cloned


# --- Track change markers ---

@dataclass
class TrackChangeCore(TItem):
    """Base for track-change begin/end markers."""

    tc_id_attr: Optional[str] = None  # Id attribute
    tc_id: Optional[str] = None  # TcId
    paraend: Optional[bool] = None

    def _object_type(self) -> ObjectType:
        raise NotImplementedError


@dataclass
class InsertBegin(TrackChangeCore):
    """Track change insert begin marker."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_insertBegin


@dataclass
class InsertEnd(TrackChangeCore):
    """Track change insert end marker."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_insertEnd


@dataclass
class DeleteBegin(TrackChangeCore):
    """Track change delete begin marker."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_deleteBegin


@dataclass
class DeleteEnd(TrackChangeCore):
    """Track change delete end marker."""

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_deleteEnd


# ============================================================
# MarkpenBeginForRun - markpen at Run level (different ObjectType)
# ============================================================

@dataclass
class MarkpenBeginForRun(RunItem):
    """Highlight pen begin marker at Run level."""

    begin_color: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_markpenBegin


# ============================================================
# ComposeCharPr
# ============================================================

@dataclass
class ComposeCharPr(HWPXObject):
    """Character property reference for Compose element."""

    char_pr_id_ref: Optional[str] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_charPr


# ============================================================
# T (text element containing TItems or plain text)
# ============================================================

@dataclass
class T(RunItem):
    """Text element (hp:t) - contains text content and inline markers."""

    char_pr_id_ref: Optional[str] = None
    _only_text: Optional[str] = field(default=None, repr=False)
    _item_list: Optional[List[TItem]] = field(default=None, repr=False)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_t

    def add_text(self, text: str) -> None:
        if self._item_list is not None and len(self._item_list) > 0:
            self._item_list.append(NormalText(text=text))
        else:
            if self._only_text is None:
                self._only_text = text
            else:
                self._preprocess()
                self._item_list.append(NormalText(text=text))

    def clear(self) -> None:
        self._only_text = None
        self._item_list = None

    def is_empty(self) -> bool:
        return self._only_text is None and self._item_list is None

    def is_only_text(self) -> bool:
        return self._only_text is not None

    @property
    def only_text(self) -> Optional[str]:
        return self._only_text

    def count_of_items(self) -> int:
        if self._item_list is None:
            return 0
        return len(self._item_list)

    def get_item(self, index: int) -> Optional[TItem]:
        if self._item_list is None:
            return None
        return self._item_list[index]

    def add_item(self, item: TItem) -> None:
        self._preprocess()
        self._item_list.append(item)

    def add_new_text(self) -> NormalText:
        self._preprocess()
        nt = NormalText()
        self._item_list.append(nt)
        return nt

    def _preprocess(self) -> None:
        if self._item_list is None:
            self._item_list = []
        if self._only_text is not None:
            self._item_list.append(NormalText(text=self._only_text))
            self._only_text = None

    def add_new_markpen_begin(self) -> MarkpenBegin:
        self._preprocess()
        mb = MarkpenBegin()
        self._item_list.append(mb)
        return mb

    def add_new_markpen_end(self) -> MarkpenEnd:
        self._preprocess()
        me = MarkpenEnd()
        self._item_list.append(me)
        return me

    def add_new_title_mark(self) -> TitleMark:
        self._preprocess()
        tm = TitleMark()
        self._item_list.append(tm)
        return tm

    def add_new_tab(self) -> Tab:
        self._preprocess()
        t = Tab()
        self._item_list.append(t)
        return t

    def add_new_line_break(self) -> LineBreak:
        self._preprocess()
        lb = LineBreak()
        self._item_list.append(lb)
        return lb

    def add_new_hyphen(self) -> Hyphen:
        self._preprocess()
        h = Hyphen()
        self._item_list.append(h)
        return h

    def add_new_nb_space(self) -> NBSpace:
        self._preprocess()
        nb = NBSpace()
        self._item_list.append(nb)
        return nb

    def add_new_fw_space(self) -> FWSpace:
        self._preprocess()
        fw = FWSpace()
        self._item_list.append(fw)
        return fw

    def add_new_insert_begin(self) -> InsertBegin:
        self._preprocess()
        ib = InsertBegin()
        self._item_list.append(ib)
        return ib

    def add_new_insert_end(self) -> InsertEnd:
        self._preprocess()
        ie = InsertEnd()
        self._item_list.append(ie)
        return ie

    def add_new_delete_begin(self) -> DeleteBegin:
        self._preprocess()
        db = DeleteBegin()
        self._item_list.append(db)
        return db

    def add_new_delete_end(self) -> DeleteEnd:
        self._preprocess()
        de = DeleteEnd()
        self._item_list.append(de)
        return de

    def items(self) -> Optional[List[TItem]]:
        return self._item_list


# ============================================================
# Compose (character overlap)
# ============================================================

@dataclass
class Compose(RunItem):
    """Character overlap (hp:compose)."""

    circle_type: Optional[ComposeCircleType] = None
    char_sz: Optional[int] = None
    compose_type: Optional[ComposeType] = None
    compose_text: Optional[str] = None
    _char_pr_list: List[ComposeCharPr] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_compose

    def count_of_char_pr(self) -> int:
        return len(self._char_pr_list)

    def get_char_pr(self, index: int) -> ComposeCharPr:
        return self._char_pr_list[index]

    def add_char_pr(self, char_pr: ComposeCharPr) -> None:
        self._char_pr_list.append(char_pr)

    def add_new_char_pr(self) -> ComposeCharPr:
        cp = ComposeCharPr()
        self._char_pr_list.append(cp)
        return cp

    def char_prs(self) -> List[ComposeCharPr]:
        return self._char_pr_list


# ============================================================
# Dutmal (annotation text / ruby)
# ============================================================

@dataclass
class Dutmal(RunItem):
    """Annotation text (hp:dutmal)."""

    pos_type: Optional[DutmalPosType] = None
    sz_ratio: Optional[int] = None
    option: Optional[int] = None
    style_id_ref: Optional[str] = None
    align: Optional[str] = None  # HorizontalAlign2 from header enums
    main_text: Optional[HasOnlyText] = None
    sub_text: Optional[HasOnlyText] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_dutmal

    def create_main_text(self) -> HasOnlyText:
        self.main_text = HasOnlyText(ObjectType.hp_mainText)
        return self.main_text

    def remove_main_text(self) -> None:
        self.main_text = None

    def create_sub_text(self) -> HasOnlyText:
        self.sub_text = HasOnlyText(ObjectType.hp_subText)
        return self.sub_text

    def remove_sub_text(self) -> None:
        self.sub_text = None


# ============================================================
# LineSeg (line segmentation info)
# ============================================================

@dataclass
class LineSeg(HWPXObject):
    """Line segmentation information (hp:lineseg)."""

    textpos: Optional[int] = None
    vertpos: Optional[int] = None
    vertsize: Optional[int] = None
    textheight: Optional[int] = None
    baseline: Optional[int] = None
    spacing: Optional[int] = None
    horzpos: Optional[int] = None
    horzsize: Optional[int] = None
    flags: Optional[int] = None

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_lineseg


# ============================================================
# Ctrl (control character container)
# ============================================================

@dataclass
class Ctrl(RunItem):
    """Control character container (hp:ctrl) - holds CtrlItems."""

    _item_list: List[CtrlItem] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_ctrl

    def count_of_ctrl_items(self) -> int:
        return len(self._item_list)

    def get_ctrl_item(self, index: int) -> CtrlItem:
        return self._item_list[index]

    def add_ctrl_item(self, item: CtrlItem) -> None:
        self._item_list.append(item)

    def ctrl_items(self) -> List[CtrlItem]:
        return self._item_list

    # Factory methods are provided in ctrl.py and imported lazily
    def add_new_col_pr(self) -> Any:
        from .ctrl import ColPr
        cp = ColPr()
        self._item_list.append(cp)
        return cp

    def add_new_field_begin(self) -> Any:
        from .ctrl import FieldBegin
        fb = FieldBegin()
        self._item_list.append(fb)
        return fb

    def add_new_field_end(self) -> Any:
        from .ctrl import FieldEnd
        fe = FieldEnd()
        self._item_list.append(fe)
        return fe

    def add_new_bookmark(self) -> Any:
        from .ctrl import Bookmark
        b = Bookmark()
        self._item_list.append(b)
        return b

    def add_new_header(self) -> Any:
        from .ctrl import Header
        h = Header()
        self._item_list.append(h)
        return h

    def add_new_footer(self) -> Any:
        from .ctrl import Footer
        f = Footer()
        self._item_list.append(f)
        return f

    def add_new_foot_note(self) -> Any:
        from .ctrl import FootNote
        fn = FootNote()
        self._item_list.append(fn)
        return fn

    def add_new_end_note(self) -> Any:
        from .ctrl import EndNote
        en = EndNote()
        self._item_list.append(en)
        return en

    def add_new_auto_num(self) -> Any:
        from .ctrl import AutoNum
        an = AutoNum()
        self._item_list.append(an)
        return an

    def add_new_new_num(self) -> Any:
        from .ctrl import NewNum
        nn = NewNum()
        self._item_list.append(nn)
        return nn

    def add_new_page_num_ctrl(self) -> Any:
        from .ctrl import PageNumCtrl
        pc = PageNumCtrl()
        self._item_list.append(pc)
        return pc

    def add_new_page_hiding(self) -> Any:
        from .ctrl import PageHiding
        ph = PageHiding()
        self._item_list.append(ph)
        return ph

    def add_new_page_num(self) -> Any:
        from .ctrl import PageNum
        pn = PageNum()
        self._item_list.append(pn)
        return pn

    def add_new_indexmark(self) -> Any:
        from .ctrl import Indexmark
        im = Indexmark()
        self._item_list.append(im)
        return im

    def add_new_hidden_comment(self) -> Any:
        from .ctrl import HiddenComment
        hc = HiddenComment()
        self._item_list.append(hc)
        return hc


# ============================================================
# Run (character run within a paragraph)
# ============================================================

@dataclass
class Run(SwitchableObject):
    """Character run (hp:run) - contains RunItems and optional SecPr."""

    char_pr_id_ref: Optional[str] = None
    char_tc_id: Optional[str] = None
    sec_pr: Optional[Any] = field(default=None, repr=False)  # SecPr (lazy import)
    _item_list: List[RunItem] = field(default_factory=list)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_run

    def create_sec_pr(self) -> Any:
        from .sec_pr import SecPr
        self.sec_pr = SecPr()
        return self.sec_pr

    def remove_sec_pr(self) -> None:
        self.sec_pr = None

    # --- RunItem management ---

    def count_of_run_item(self) -> int:
        return len(self._item_list)

    def get_run_item(self, index: int) -> RunItem:
        return self._item_list[index]

    def add_run_item(self, item: RunItem) -> None:
        self._item_list.append(item)

    def run_items(self) -> List[RunItem]:
        return self._item_list

    # --- Factory methods for all RunItem types ---

    def add_new_ctrl(self) -> Ctrl:
        ctrl = Ctrl()
        self._item_list.append(ctrl)
        return ctrl

    def add_new_t(self) -> T:
        t = T()
        self._item_list.append(t)
        return t

    def add_new_table(self) -> Any:
        from .objects.table import Table
        tbl = Table()
        self._item_list.append(tbl)
        return tbl

    def add_new_picture(self) -> Any:
        from .objects.picture import Picture
        pic = Picture()
        self._item_list.append(pic)
        return pic

    def add_new_container(self) -> Any:
        from .objects.ole import Container
        c = Container()
        self._item_list.append(c)
        return c

    def add_new_ole(self) -> Any:
        from .objects.ole import OLE
        o = OLE()
        self._item_list.append(o)
        return o

    def add_new_equation(self) -> Any:
        from .objects.equation import Equation
        eq = Equation()
        self._item_list.append(eq)
        return eq

    def add_new_line(self) -> Any:
        from .objects.shapes import Line
        ln = Line()
        self._item_list.append(ln)
        return ln

    def add_new_rectangle(self) -> Any:
        from .objects.shapes import Rectangle
        r = Rectangle()
        self._item_list.append(r)
        return r

    def add_new_ellipse(self) -> Any:
        from .objects.shapes import Ellipse
        e = Ellipse()
        self._item_list.append(e)
        return e

    def add_new_arc(self) -> Any:
        from .objects.shapes import Arc
        a = Arc()
        self._item_list.append(a)
        return a

    def add_new_polygon(self) -> Any:
        from .objects.shapes import Polygon
        p = Polygon()
        self._item_list.append(p)
        return p

    def add_new_curve(self) -> Any:
        from .objects.shapes import Curve
        c = Curve()
        self._item_list.append(c)
        return c

    def add_new_connect_line(self) -> Any:
        from .objects.connect_line import ConnectLine
        cl = ConnectLine()
        self._item_list.append(cl)
        return cl

    def add_new_text_art(self) -> Any:
        from .objects.text_art import TextArt
        ta = TextArt()
        self._item_list.append(ta)
        return ta

    def add_new_compose(self) -> Compose:
        c = Compose()
        self._item_list.append(c)
        return c

    def add_new_dutmal(self) -> Dutmal:
        d = Dutmal()
        self._item_list.append(d)
        return d

    def add_new_button(self) -> Any:
        from .objects.form_objects import Button
        b = Button()
        self._item_list.append(b)
        return b

    def add_new_radio_button(self) -> Any:
        from .objects.form_objects import RadioButton
        rb = RadioButton()
        self._item_list.append(rb)
        return rb

    def add_new_check_button(self) -> Any:
        from .objects.form_objects import CheckButton
        cb = CheckButton()
        self._item_list.append(cb)
        return cb

    def add_new_combo_box(self) -> Any:
        from .objects.form_objects import ComboBox
        cb = ComboBox()
        self._item_list.append(cb)
        return cb

    def add_new_list_box(self) -> Any:
        from .objects.form_objects import ListBox
        lb = ListBox()
        self._item_list.append(lb)
        return lb

    def add_new_edit(self) -> Any:
        from .objects.form_objects import Edit
        e = Edit()
        self._item_list.append(e)
        return e

    def add_new_scroll_bar(self) -> Any:
        from .objects.form_objects import ScrollBar
        sb = ScrollBar()
        self._item_list.append(sb)
        return sb

    def add_new_video(self) -> Any:
        from .objects.ole import Video
        v = Video()
        self._item_list.append(v)
        return v

    def add_new_chart(self) -> Any:
        from .objects.ole import Chart
        ch = Chart()
        self._item_list.append(ch)
        return ch

    def add_new_markpen_begin(self) -> MarkpenBeginForRun:
        mb = MarkpenBeginForRun()
        self._item_list.append(mb)
        return mb

    def add_new_meta_tag(self) -> MetaTag:
        mt = MetaTag()
        self._item_list.append(mt)
        return mt


# ============================================================
# Para (paragraph)
# ============================================================

@dataclass
class Para(SwitchableObject):
    """Paragraph (hp:p) - the fundamental content unit."""

    id: Optional[str] = None
    para_pr_id_ref: Optional[str] = None
    style_id_ref: Optional[str] = None
    page_break: Optional[bool] = None
    column_break: Optional[bool] = None
    merged: Optional[bool] = None
    para_tc_id: Optional[str] = None
    raw_xml_content: Optional[str] = field(default=None, repr=False)
    meta_tag: Optional[MetaTag] = None
    _run_list: List[Run] = field(default_factory=list)
    line_seg_array: Optional[ObjectList[LineSeg]] = field(default=None, repr=False)

    def _object_type(self) -> ObjectType:
        return ObjectType.hp_p

    def create_meta_tag(self) -> MetaTag:
        self.meta_tag = MetaTag()
        return self.meta_tag

    def remove_meta_tag(self) -> None:
        self.meta_tag = None

    # --- Run list management ---

    def count_of_run(self) -> int:
        return len(self._run_list)

    def get_run(self, index: int) -> Run:
        return self._run_list[index]

    def get_run_index(self, run: Run) -> int:
        for i, r in enumerate(self._run_list):
            if r is run:
                return i
        return -1

    def add_run(self, run: Run) -> None:
        self._run_list.append(run)

    def add_new_run(self) -> Run:
        run = Run()
        self._run_list.append(run)
        return run

    def insert_run(self, run: Run, position: int) -> None:
        self._run_list.insert(position, run)

    def remove_run(self, position_or_run) -> None:
        if isinstance(position_or_run, int):
            del self._run_list[position_or_run]
        else:
            self._run_list.remove(position_or_run)

    def remove_all_runs(self) -> None:
        self._run_list.clear()

    def runs(self) -> List[Run]:
        return self._run_list

    # --- LineSeg array ---

    def create_line_seg_array(self) -> ObjectList[LineSeg]:
        self.line_seg_array = ObjectList(
            _object_type_value=ObjectType.hp_linesegarray,
            _item_class=LineSeg,
        )
        return self.line_seg_array

    def remove_line_seg_array(self) -> None:
        self.line_seg_array = None
