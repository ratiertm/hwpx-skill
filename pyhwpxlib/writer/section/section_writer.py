"""Write section*.xml - Port of all section writers.

This module handles:
- SectionXMLFile root with namespaces
- Para, Run, T writing
- Table, Picture, Shape object writing
- SubList writing
- SecPr (section properties) writing
- LineSeg array writing
- Drawing object / shape component common attributes
"""
from __future__ import annotations

from typing import Any, Optional

from pyhwpxlib.constants import attribute_names as AN
from pyhwpxlib.constants import element_names as EN
from pyhwpxlib.constants.namespaces import Namespaces
from pyhwpxlib.object_type import ObjectType
from pyhwpxlib.objects.section.section_xml_file import SectionXMLFile, SubList
from pyhwpxlib.writer.xml_builder import XMLStringBuilder

# Full namespaces matching Java hwpxlib output
_SECTION_NAMESPACES = [
    Namespaces.ha, Namespaces.hp, Namespaces.hp10,
    Namespaces.hs, Namespaces.hc, Namespaces.hh,
    Namespaces.hhs, Namespaces.hm, Namespaces.hpf,
    Namespaces.dc, Namespaces.opf, Namespaces.ooxmlchart,
    Namespaces.hwpunitchar, Namespaces.epub, Namespaces.config,
]


def write_section(xsb: XMLStringBuilder, section: SectionXMLFile) -> None:
    """Serialize a SectionXMLFile into *xsb*."""
    xsb.clear()
    xsb.open_element(EN.hs_sec)
    for ns in _SECTION_NAMESPACES:
        xsb.namespace(ns)

    for para in section.paras():
        _write_para(xsb, para)

    xsb.close_element()


# ======================================================================
# Para
# ======================================================================

def _write_para(xsb: XMLStringBuilder, para: Any) -> None:
    xsb.open_element(EN.hp_p)
    xsb.attribute(AN.id, para.id)
    xsb.attribute(AN.paraPrIDRef, para.paraPrIDRef if hasattr(para, "paraPrIDRef") else getattr(para, "para_pr_id_ref", None))
    xsb.attribute(AN.styleIDRef, para.styleIDRef if hasattr(para, "styleIDRef") else getattr(para, "style_id_ref", None))
    xsb.attribute(AN.pageBreak, para.pageBreak if hasattr(para, "pageBreak") else getattr(para, "page_break", None))
    xsb.attribute(AN.columnBreak, para.columnBreak if hasattr(para, "columnBreak") else getattr(para, "column_break", None))
    xsb.attribute(AN.merged, para.merged)
    xsb.attribute(AN.paraTcId, para.paraTcId if hasattr(para, "paraTcId") else getattr(para, "para_tc_id", None))

    # Raw XML content (injected by add_table / add_rectangle / etc.)
    raw_xml = getattr(para, "raw_xml_content", None)
    if raw_xml:
        xsb.raw(raw_xml)
    else:
        # Runs
        runs = getattr(para, "runs", None)
        if runs is not None:
            run_list = runs() if callable(runs) else runs
            for run in run_list:
                _write_run(xsb, run)

    # LineSegArray
    lsa = getattr(para, "lineSegArray", getattr(para, "line_seg_array", None))
    if lsa is not None:
        _write_line_seg_array(xsb, lsa)

    xsb.close_element()


# ======================================================================
# Run
# ======================================================================

def _write_run(xsb: XMLStringBuilder, run: Any) -> None:
    xsb.open_element(EN.hp_run)
    xsb.attribute(AN.charPrIDRef, run.charPrIDRef if hasattr(run, "charPrIDRef") else getattr(run, "char_pr_id_ref", None))
    xsb.attribute(AN.charTcId, run.charTcId if hasattr(run, "charTcId") else getattr(run, "char_tc_id", None))

    # SecPr (section properties inside a run)
    sec_pr = getattr(run, "secPr", getattr(run, "sec_pr", None))
    if sec_pr is not None:
        _write_sec_pr(xsb, sec_pr)

    # Run items
    run_items = getattr(run, "runItems", getattr(run, "run_items", None))
    if run_items is not None:
        items = run_items() if callable(run_items) else run_items
        for item in items:
            _write_run_item(xsb, item)

    xsb.close_element()


def _write_run_item(xsb: XMLStringBuilder, item: Any) -> None:
    """Dispatch to the right writer based on object type."""
    ot = item._object_type()

    if ot == ObjectType.hp_ctrl:
        _write_ctrl(xsb, item)
    elif ot == ObjectType.hp_t:
        _write_t(xsb, item)
    elif ot == ObjectType.hp_tbl:
        _write_table(xsb, item)
    elif ot == ObjectType.hp_pic:
        _write_picture(xsb, item)
    elif ot == ObjectType.hp_line:
        _write_drawing_object(xsb, EN.hp_line, item)
    elif ot == ObjectType.hp_rect:
        _write_drawing_object(xsb, EN.hp_rect, item)
    elif ot == ObjectType.hp_ellipse:
        _write_drawing_object(xsb, EN.hp_ellipse, item)
    elif ot == ObjectType.hp_arc:
        _write_drawing_object(xsb, EN.hp_arc, item)
    elif ot == ObjectType.hp_polygon:
        _write_drawing_object(xsb, EN.hp_polygon, item)
    elif ot == ObjectType.hp_curve:
        _write_drawing_object(xsb, EN.hp_curve, item)
    elif ot == ObjectType.hp_connectLine:
        _write_drawing_object(xsb, EN.hp_connectLine, item)
    elif ot == ObjectType.hp_textart:
        _write_drawing_object(xsb, EN.hp_textart, item)
    elif ot == ObjectType.hp_container:
        _write_drawing_object(xsb, EN.hp_container, item)
    elif ot == ObjectType.hp_ole:
        _write_drawing_object(xsb, EN.hp_ole, item)
    elif ot == ObjectType.hp_equation:
        _write_equation(xsb, item)
    elif ot == ObjectType.hp_chart:
        _write_chart(xsb, item)
    elif ot == ObjectType.hp_compose:
        _write_compose(xsb, item)
    elif ot == ObjectType.hp_dutmal:
        _write_dutmal(xsb, item)
    elif ot == ObjectType.hp_video:
        _write_drawing_object(xsb, EN.hp_video, item)
    elif ot == ObjectType.hp_markpenBegin:
        xsb.open_element(EN.hp_markpenBegin)
        xsb.attribute(AN.beginColor, getattr(item, "begin_color", getattr(item, "beginColor", None)))
        xsb.close_element()
    elif ot in (ObjectType.hp_btn, ObjectType.hp_radioBtn, ObjectType.hp_checkBtn):
        _write_form_object(xsb, item, ot)
    elif ot == ObjectType.hp_comboBox:
        _write_form_object(xsb, item, ot)
    elif ot == ObjectType.hp_edit:
        _write_form_object(xsb, item, ot)
    elif ot == ObjectType.hp_listBox:
        _write_form_object(xsb, item, ot)
    elif ot == ObjectType.hp_scrollBar:
        _write_form_object(xsb, item, ot)
    else:
        # Unknown run item - try to write as generic element
        pass


# ======================================================================
# T (text element)
# ======================================================================

def _write_t(xsb: XMLStringBuilder, t: Any) -> None:
    xsb.open_element(EN.hp_t)
    xsb.attribute(AN.charPrIDRef, t.charPrIDRef if hasattr(t, "charPrIDRef") else getattr(t, "char_pr_id_ref", None))

    # Fast path: only text
    is_empty = getattr(t, "isEmpty", getattr(t, "is_empty", None))
    is_only_text = getattr(t, "isOnlyText", getattr(t, "is_only_text", None))

    if is_empty is not None and callable(is_empty) and is_empty():
        pass  # empty T
    elif is_only_text is not None and callable(is_only_text) and is_only_text():
        only_text = getattr(t, "onlyText", getattr(t, "only_text", None))
        if only_text is not None:
            text = only_text() if callable(only_text) else only_text
            xsb.text(text)
    else:
        # Iterate items
        items = getattr(t, "items", None)
        if items is not None:
            item_list = items() if callable(items) else items
            for ti in item_list:
                _write_t_item(xsb, ti)

    xsb.close_element()


def _write_t_item(xsb: XMLStringBuilder, item: Any) -> None:
    """Write a single TItem."""
    ot = item._object_type()

    if ot == ObjectType.NormalText:
        xsb.text(item.text)
    elif ot == ObjectType.hp_markpenBegin:
        xsb.open_element(EN.hp_markpenBegin)
        xsb.attribute(AN.beginColor, getattr(item, "begin_color", getattr(item, "beginColor", None)))
        xsb.close_element()
    elif ot == ObjectType.hp_markpenEnd:
        xsb.open_element(EN.hp_markpenEnd)
        xsb.close_element()
    elif ot == ObjectType.hp_titleMark:
        xsb.open_element(EN.hp_titleMark)
        xsb.attribute(AN.ignore, getattr(item, "ignore", None))
        xsb.close_element()
    elif ot == ObjectType.hp_tab:
        xsb.open_element(EN.hp_tab)
        if item.width is not None:
            xsb.attribute(AN.width, item.width)
        leader = getattr(item, "leader", None)
        if leader is not None:
            if isinstance(leader, int):
                xsb.attribute(AN.leader, leader)
            elif isinstance(leader, str):
                xsb.attribute(AN.leader, leader)
            elif hasattr(leader, "index") and not callable(leader.index):
                xsb.attribute(AN.leader, str(leader.index))
            else:
                xsb.attribute_index(AN.leader, leader)
        tab_type = getattr(item, "type", None)
        if tab_type is not None:
            if isinstance(tab_type, int):
                xsb.attribute(AN.type, tab_type)
            else:
                xsb.attribute_index(AN.type, tab_type)
        xsb.close_element()
    elif ot == ObjectType.hp_lineBreak:
        xsb.open_element(EN.hp_lineBreak)
        xsb.close_element()
    elif ot == ObjectType.hp_hyphen:
        xsb.open_element(EN.hp_hyphen)
        xsb.close_element()
    elif ot == ObjectType.hp_nbSpace:
        xsb.open_element(EN.hp_nbSpace)
        xsb.close_element()
    elif ot == ObjectType.hp_fwSpace:
        xsb.open_element(EN.hp_fwSpace)
        xsb.close_element()
    elif ot in (ObjectType.hp_insertBegin, ObjectType.hp_insertEnd,
                ObjectType.hp_deleteBegin, ObjectType.hp_deleteEnd):
        _TRACK_CHANGE_ELEM = {
            ObjectType.hp_insertBegin: EN.hp_insertBegin,
            ObjectType.hp_insertEnd: EN.hp_insertEnd,
            ObjectType.hp_deleteBegin: EN.hp_deleteBegin,
            ObjectType.hp_deleteEnd: EN.hp_deleteEnd,
        }
        elem = _TRACK_CHANGE_ELEM[ot]
        xsb.open_element(elem)
        xsb.attribute(AN.Id, getattr(item, "tc_id_attr", getattr(item, "Id", None)))
        xsb.attribute(AN.TcId, getattr(item, "tc_id", getattr(item, "TcId", None)))
        xsb.attribute(AN.paraend, item.paraend)
        xsb.close_element()


# ======================================================================
# Ctrl (control characters)
# ======================================================================

def _write_ctrl(xsb: XMLStringBuilder, ctrl: Any) -> None:
    """Write hp:ctrl and its child control items."""
    xsb.open_element(EN.hp_ctrl)

    # Ctrl contains a list of CtrlItem objects
    items_fn = getattr(ctrl, "ctrl_items", None)
    if items_fn is not None:
        items = items_fn() if callable(items_fn) else items_fn
        for ctrl_item in items:
            _write_ctrl_item(xsb, ctrl_item)

    xsb.close_element()


def _write_ctrl_item(xsb: XMLStringBuilder, item: Any) -> None:
    """Dispatch control item by object type."""
    ot = item._object_type()

    if ot == ObjectType.hp_colPr:
        _write_col_pr(xsb, item)
    elif ot == ObjectType.hp_fieldBegin:
        _write_field_begin(xsb, item)
    elif ot == ObjectType.hp_fieldEnd:
        xsb.open_element(EN.hp_fieldEnd)
        xsb.close_element()
    elif ot == ObjectType.hp_bookmark:
        xsb.open_element(EN.hp_bookmark)
        xsb.attribute(AN.name, item.name)
        xsb.close_element()
    elif ot in (ObjectType.hp_header, ObjectType.hp_footer):
        _write_header_footer(xsb, item, ot)
    elif ot in (ObjectType.hp_footNote, ObjectType.hp_endNote):
        _write_footnote_endnote(xsb, item, ot)
    elif ot == ObjectType.hp_autoNum:
        _write_auto_num(xsb, item)
    elif ot == ObjectType.hp_newNum:
        _write_new_num(xsb, item)
    elif ot == ObjectType.hp_pageNumCtrl:
        _write_page_num_ctrl(xsb, item)
    elif ot == ObjectType.hp_pageHiding:
        _write_page_hiding(xsb, item)
    elif ot == ObjectType.hp_pageNum:
        _write_page_num(xsb, item)
    elif ot == ObjectType.hp_indexmark:
        _write_indexmark(xsb, item)
    elif ot == ObjectType.hp_hiddenComment:
        _write_hidden_comment(xsb, item)
    else:
        # Unknown ctrl item
        pass


# ------------------------------------------------------------------
# Control item writers
# ------------------------------------------------------------------

def _write_col_pr(xsb: XMLStringBuilder, cp: Any) -> None:
    xsb.open_element(EN.hp_colPr)
    xsb.attribute(AN.id, cp.id)
    xsb.attribute(AN.type, cp.type)
    xsb.attribute(AN.layout, cp.layout)
    xsb.attribute(AN.colCount, cp.colCount if hasattr(cp, "colCount") else getattr(cp, "col_count", None))
    xsb.attribute(AN.sameSz, cp.sameSz if hasattr(cp, "sameSz") else getattr(cp, "same_sz", None))
    xsb.attribute(AN.sameGap, cp.sameGap if hasattr(cp, "sameGap") else getattr(cp, "same_gap", None))

    # colSz children
    col_sizes = getattr(cp, "colSizes", getattr(cp, "col_sizes", None))
    if col_sizes is not None:
        sizes = col_sizes() if callable(col_sizes) else col_sizes
        for cs in sizes:
            xsb.open_element(EN.hp_colSz)
            xsb.attribute(AN.width, cs.width)
            xsb.attribute(AN.gap, cs.gap)
            xsb.close_element()

    # colLine children
    col_lines = getattr(cp, "colLines", getattr(cp, "col_lines", None))
    if col_lines is not None:
        lines = col_lines() if callable(col_lines) else col_lines
        for cl in lines:
            xsb.open_element(EN.hp_colLine)
            xsb.attribute(AN.type, cl.type)
            xsb.attribute(AN.width, cl.width)
            xsb.attribute(AN.color, cl.color)
            xsb.close_element()

    xsb.close_element()


def _write_field_begin(xsb: XMLStringBuilder, fb: Any) -> None:
    xsb.open_element(EN.hp_fieldBegin)
    xsb.attribute(AN.type, fb.type)
    xsb.attribute(AN.name, fb.name)
    xsb.attribute(AN.id, fb.id)
    xsb.attribute(AN.editable, fb.editable)
    xsb.attribute(AN.dirty, fb.dirty)
    xsb.attribute(AN.zorder, fb.zorder)

    # fieldid
    xsb.attribute(AN.fieldid, fb.fieldid if hasattr(fb, "fieldid") else getattr(fb, "field_id", None))

    # parameter set
    ps = getattr(fb, "parameterSet", getattr(fb, "parameter_set", None))
    if ps is not None:
        _write_parameter_set(xsb, ps)

    xsb.close_element()


def _write_parameter_set(xsb: XMLStringBuilder, ps: Any) -> None:
    """Write hp:parameterset and its children."""
    xsb.open_element(EN.hp_parameterset)
    xsb.attribute(AN.cnt, ps.cnt if hasattr(ps, "cnt") else getattr(ps, "count", None))

    params = getattr(ps, "parameters", None)
    if params is not None:
        items = params() if callable(params) else params
        for p in items:
            _write_parameter(xsb, p)

    xsb.close_element()


def _write_parameter(xsb: XMLStringBuilder, p: Any) -> None:
    """Write a single parameter element."""
    ot = p._object_type()
    _PARAM_ELEMS = {
        ObjectType.hp_booleanParam: EN.hp_booleanParam,
        ObjectType.hp_integerParam: EN.hp_integerParam,
        ObjectType.hp_unsignedintegerParam: EN.hp_unsignedintegerParam,
        ObjectType.hp_floatParam: EN.hp_floatParam,
        ObjectType.hp_stringParam: EN.hp_stringParam,
        ObjectType.hp_listParam: EN.hp_listParam,
    }
    elem = _PARAM_ELEMS.get(ot)
    if elem is None:
        return

    xsb.open_element(elem)
    xsb.attribute(AN.name, p.name)
    val = getattr(p, "value", None)
    if val is not None:
        xsb.text(str(val) if not isinstance(val, str) else val)
    xsb.close_element()


def _write_header_footer(xsb: XMLStringBuilder, hf: Any, ot: ObjectType) -> None:
    elem = EN.hp_header if ot == ObjectType.hp_header else EN.hp_footer
    xsb.open_element(elem)
    xsb.attribute(AN.id, getattr(hf, "id", None))
    xsb.attribute(AN.applyPageType, hf.applyPageType if hasattr(hf, "applyPageType") else getattr(hf, "apply_page_type", None))

    sub_list = getattr(hf, "subList", getattr(hf, "sub_list", None))
    if sub_list is not None:
        _write_sub_list(xsb, sub_list)

    xsb.close_element()


def _write_footnote_endnote(xsb: XMLStringBuilder, fn: Any, ot: ObjectType) -> None:
    elem = EN.hp_footNote if ot == ObjectType.hp_footNote else EN.hp_endNote
    xsb.open_element(elem)

    sub_list = getattr(fn, "subList", getattr(fn, "sub_list", None))
    if sub_list is not None:
        _write_sub_list(xsb, sub_list)

    xsb.close_element()


def _write_auto_num(xsb: XMLStringBuilder, an: Any) -> None:
    xsb.open_element(EN.hp_autoNum)
    xsb.attribute(AN.numType, an.numType if hasattr(an, "numType") else getattr(an, "num_type", None))
    xsb.attribute(AN.num, an.num)
    anf = getattr(an, "autoNumFormat", getattr(an, "auto_num_format", None))
    if anf is not None:
        xsb.open_element(EN.hp_autoNumFormat)
        xsb.attribute(AN.type, anf.type)
        xsb.attribute(AN.userChar, anf.userChar if hasattr(anf, "userChar") else getattr(anf, "user_char", None))
        xsb.attribute(AN.prefixChar, anf.prefixChar if hasattr(anf, "prefixChar") else getattr(anf, "prefix_char", None))
        xsb.attribute(AN.suffixChar, anf.suffixChar if hasattr(anf, "suffixChar") else getattr(anf, "suffix_char", None))
        xsb.attribute(AN.supscript, anf.supscript)
        xsb.close_element()
    xsb.close_element()


def _write_new_num(xsb: XMLStringBuilder, nn: Any) -> None:
    xsb.open_element(EN.hp_newNum)
    xsb.attribute(AN.numType, nn.numType if hasattr(nn, "numType") else getattr(nn, "num_type", None))
    xsb.attribute(AN.num, nn.num)
    xsb.close_element()


def _write_page_num_ctrl(xsb: XMLStringBuilder, pnc: Any) -> None:
    xsb.open_element(EN.hp_pageNumCtrl)
    xsb.attribute(AN.pageStartsOn, pnc.pageStartsOn if hasattr(pnc, "pageStartsOn") else getattr(pnc, "page_starts_on", None))
    xsb.close_element()


def _write_page_hiding(xsb: XMLStringBuilder, ph: Any) -> None:
    xsb.open_element(EN.hp_pageHiding)
    xsb.attribute(AN.hideHeader, ph.hideHeader if hasattr(ph, "hideHeader") else getattr(ph, "hide_header", None))
    xsb.attribute(AN.hideFooter, ph.hideFooter if hasattr(ph, "hideFooter") else getattr(ph, "hide_footer", None))
    xsb.attribute(AN.hideMasterPage, ph.hideMasterPage if hasattr(ph, "hideMasterPage") else getattr(ph, "hide_master_page", None))
    xsb.attribute(AN.hideBorder, ph.hideBorder if hasattr(ph, "hideBorder") else getattr(ph, "hide_border", None))
    xsb.attribute(AN.hideFill, ph.hideFill if hasattr(ph, "hideFill") else getattr(ph, "hide_fill", None))
    xsb.attribute(AN.hidePageNum, ph.hidePageNum if hasattr(ph, "hidePageNum") else getattr(ph, "hide_page_num", None))
    xsb.close_element()


def _write_page_num(xsb: XMLStringBuilder, pn: Any) -> None:
    xsb.open_element(EN.hp_pageNum)
    xsb.attribute(AN.pos, pn.pos if hasattr(pn, "pos") else None)
    xsb.attribute(AN.formatType, pn.formatType if hasattr(pn, "formatType") else getattr(pn, "format_type", None))
    xsb.attribute(AN.sideChar, pn.sideChar if hasattr(pn, "sideChar") else getattr(pn, "side_char", None))
    xsb.close_element()


def _write_indexmark(xsb: XMLStringBuilder, im: Any) -> None:
    xsb.open_element(EN.hp_indexmark)

    fk = getattr(im, "firstKey", getattr(im, "first_key", None))
    if fk is not None:
        xsb.open_element(EN.hp_firstKey)
        xsb.text(fk.text() if callable(getattr(fk, "text", None)) else fk.text)
        xsb.close_element()

    sk = getattr(im, "secondKey", getattr(im, "second_key", None))
    if sk is not None:
        xsb.open_element(EN.hp_secondKey)
        xsb.text(sk.text() if callable(getattr(sk, "text", None)) else sk.text)
        xsb.close_element()

    xsb.close_element()


def _write_hidden_comment(xsb: XMLStringBuilder, hc: Any) -> None:
    xsb.open_element(EN.hp_hiddenComment)

    sub_list = getattr(hc, "subList", getattr(hc, "sub_list", None))
    if sub_list is not None:
        _write_sub_list(xsb, sub_list)

    xsb.close_element()


# ======================================================================
# SubList
# ======================================================================

def _write_sub_list(xsb: XMLStringBuilder, sl: Any) -> None:
    xsb.open_element(EN.hp_subList)
    xsb.attribute(AN.id, sl.id)
    xsb.attribute(AN.textDirection, sl.text_direction if hasattr(sl, "text_direction") else getattr(sl, "textDirection", None))
    xsb.attribute(AN.lineWrap, sl.line_wrap if hasattr(sl, "line_wrap") else getattr(sl, "lineWrap", None))
    xsb.attribute(AN.vertAlign, sl.vert_align if hasattr(sl, "vert_align") else getattr(sl, "vertAlign", None))
    xsb.attribute(AN.linkListIDRef, sl.link_list_id_ref if hasattr(sl, "link_list_id_ref") else getattr(sl, "linkListIDRef", None))
    xsb.attribute(AN.linkListNextIDRef, sl.link_list_next_id_ref if hasattr(sl, "link_list_next_id_ref") else getattr(sl, "linkListNextIDRef", None))
    xsb.attribute(AN.textWidth, sl.text_width if hasattr(sl, "text_width") else getattr(sl, "textWidth", None))
    xsb.attribute(AN.textHeight, sl.text_height if hasattr(sl, "text_height") else getattr(sl, "textHeight", None))
    xsb.attribute(AN.hasTextRef, sl.has_text_ref if hasattr(sl, "has_text_ref") else getattr(sl, "hasTextRef", None))
    xsb.attribute(AN.hasNumRef, sl.has_num_ref if hasattr(sl, "has_num_ref") else getattr(sl, "hasNumRef", None))

    # metaTag - encode " as &quot;
    meta_tag = sl.meta_tag if hasattr(sl, "meta_tag") else getattr(sl, "metaTag", None)
    if meta_tag is not None:
        meta_tag = meta_tag.replace('"', "&quot;")
    xsb.attribute(AN.metaTag, meta_tag)

    for para in sl.paras():
        _write_para(xsb, para)

    xsb.close_element()


# ======================================================================
# LineSegArray
# ======================================================================

def _write_line_seg_array(xsb: XMLStringBuilder, lsa: Any) -> None:
    xsb.open_element(EN.hp_linesegarray)

    items = lsa.items() if hasattr(lsa, "items") else lsa
    for ls in (items() if callable(items) else items):
        xsb.open_element(EN.hp_lineseg)
        xsb.attribute(AN.textpos, ls.textpos)
        xsb.attribute(AN.vertpos, ls.vertpos)
        xsb.attribute(AN.vertsize, ls.vertsize)
        xsb.attribute(AN.textheight, ls.textheight)
        xsb.attribute(AN.baseline, ls.baseline)
        xsb.attribute(AN.spacing, ls.spacing)
        xsb.attribute(AN.horzpos, ls.horzpos)
        xsb.attribute(AN.horzsize, ls.horzsize)
        xsb.attribute(AN.flags, ls.flags)
        xsb.close_element()

    xsb.close_element()


# ======================================================================
# Shape Object common attributes & children
# ======================================================================

def _write_shape_object_attrs(xsb: XMLStringBuilder, so: Any) -> None:
    """Write common ShapeObject attributes."""
    xsb.attribute(AN.id, getattr(so, "id", getattr(so, "so_id", None)))
    xsb.attribute(AN.zOrder, so.zOrder if hasattr(so, "zOrder") else getattr(so, "z_order", None))
    xsb.attribute(AN.numberingType, so.numberingType if hasattr(so, "numberingType") else getattr(so, "numbering_type", None))
    xsb.attribute(AN.textWrap, so.textWrap if hasattr(so, "textWrap") else getattr(so, "text_wrap", None))
    xsb.attribute(AN.textFlow, so.textFlow if hasattr(so, "textFlow") else getattr(so, "text_flow", None))
    xsb.attribute(AN.lock, so.lock)
    xsb.attribute(AN.dropcapstyle, so.dropcapstyle if hasattr(so, "dropcapstyle") else getattr(so, "dropcap_style", None))


def _write_shape_object_children(xsb: XMLStringBuilder, so: Any) -> None:
    """Write common ShapeObject child elements (sz, pos, outMargin, caption, shapeComment)."""
    sz = getattr(so, "sz", None)
    if sz is not None:
        xsb.open_element(EN.hp_sz)
        xsb.attribute(AN.width, sz.width)
        xsb.attribute(AN.widthRelTo, sz.widthRelTo if hasattr(sz, "widthRelTo") else getattr(sz, "width_rel_to", None))
        xsb.attribute(AN.height, sz.height)
        xsb.attribute(AN.heightRelTo, sz.heightRelTo if hasattr(sz, "heightRelTo") else getattr(sz, "height_rel_to", None))
        xsb.attribute(AN.protect, sz.protect)
        xsb.close_element()

    pos = getattr(so, "pos", None)
    if pos is not None:
        xsb.open_element(EN.hp_pos)
        xsb.attribute(AN.treatAsChar, pos.treatAsChar if hasattr(pos, "treatAsChar") else getattr(pos, "treat_as_char", None))
        xsb.attribute(AN.affectLSpacing, pos.affectLSpacing if hasattr(pos, "affectLSpacing") else getattr(pos, "affect_l_spacing", None))
        xsb.attribute(AN.flowWithText, pos.flowWithText if hasattr(pos, "flowWithText") else getattr(pos, "flow_with_text", None))
        xsb.attribute(AN.allowOverlap, pos.allowOverlap if hasattr(pos, "allowOverlap") else getattr(pos, "allow_overlap", None))
        xsb.attribute(AN.holdAnchorAndSO, pos.holdAnchorAndSO if hasattr(pos, "holdAnchorAndSO") else getattr(pos, "hold_anchor_and_so", None))
        xsb.attribute(AN.vertRelTo, pos.vertRelTo if hasattr(pos, "vertRelTo") else getattr(pos, "vert_rel_to", None))
        xsb.attribute(AN.horzRelTo, pos.horzRelTo if hasattr(pos, "horzRelTo") else getattr(pos, "horz_rel_to", None))
        xsb.attribute(AN.vertAlign, pos.vertAlign if hasattr(pos, "vertAlign") else getattr(pos, "vert_align", None))
        xsb.attribute(AN.horzAlign, pos.horzAlign if hasattr(pos, "horzAlign") else getattr(pos, "horz_align", None))
        xsb.attribute(AN.vertOffset, pos.vertOffset if hasattr(pos, "vertOffset") else getattr(pos, "vert_offset", None))
        xsb.attribute(AN.horzOffset, pos.horzOffset if hasattr(pos, "horzOffset") else getattr(pos, "horz_offset", None))
        xsb.close_element()

    out_margin = getattr(so, "outMargin", getattr(so, "out_margin", None))
    if out_margin is not None:
        _write_left_right_top_bottom(xsb, EN.hp_outMargin, out_margin)

    caption = getattr(so, "caption", None)
    if caption is not None:
        _write_caption(xsb, caption)

    shape_comment = getattr(so, "shapeComment", getattr(so, "shape_comment", None))
    if shape_comment is not None:
        xsb.open_element(EN.hp_shapeComment)
        text = shape_comment.text() if callable(getattr(shape_comment, "text", None)) else shape_comment.text
        xsb.text(text)
        xsb.close_element()

    parameterset = getattr(so, "parameterset", getattr(so, "parameter_set", None))
    if parameterset is not None:
        _write_parameter_set(xsb, parameterset)


def _write_caption(xsb: XMLStringBuilder, cap: Any) -> None:
    """Write hp:caption element."""
    xsb.open_element(EN.hp_caption)
    xsb.attribute(AN.side, cap.side)
    xsb.attribute(AN.fullSz, cap.fullSz if hasattr(cap, "fullSz") else getattr(cap, "full_sz", None))
    xsb.attribute(AN.width, cap.width)
    xsb.attribute(AN.gap, cap.gap)
    xsb.attribute(AN.lastWidth, cap.lastWidth if hasattr(cap, "lastWidth") else getattr(cap, "last_width", None))

    sub_list = getattr(cap, "subList", getattr(cap, "sub_list", None))
    if sub_list is not None:
        _write_sub_list(xsb, sub_list)

    xsb.close_element()


def _write_left_right_top_bottom(xsb: XMLStringBuilder, elem_name: str, lrtb: Any) -> None:
    xsb.open_element(elem_name)
    xsb.attribute(AN.left, lrtb.left)
    xsb.attribute(AN.right, lrtb.right)
    xsb.attribute(AN.top, lrtb.top)
    xsb.attribute(AN.bottom, lrtb.bottom)
    xsb.close_element()


def _write_width_and_height(xsb: XMLStringBuilder, elem_name: str, wh: Any) -> None:
    xsb.open_element(elem_name)
    xsb.attribute(AN.width, wh.width)
    xsb.attribute(AN.height, wh.height)
    xsb.close_element()


def _write_x_and_y(xsb: XMLStringBuilder, elem_name: str, xy: Any) -> None:
    xsb.open_element(elem_name)
    xsb.attribute(AN.x, xy.x)
    xsb.attribute(AN.y, xy.y)
    xsb.close_element()


# ======================================================================
# Table
# ======================================================================

def _write_table(xsb: XMLStringBuilder, tbl: Any) -> None:
    xsb.open_element(EN.hp_tbl)
    # Table may or may not inherit ShapeObject attrs - write them only if present
    if hasattr(tbl, 'id') or hasattr(tbl, 'z_order'):
        _write_shape_object_attrs(xsb, tbl)
    xsb.attribute(AN.pageBreak, tbl.pageBreak if hasattr(tbl, "pageBreak") else getattr(tbl, "page_break", None))
    xsb.attribute(AN.repeatHeader, tbl.repeatHeader if hasattr(tbl, "repeatHeader") else getattr(tbl, "repeat_header", None))
    xsb.attribute(AN.rowCnt, tbl.rowCnt if hasattr(tbl, "rowCnt") else getattr(tbl, "row_cnt", None))
    xsb.attribute(AN.colCnt, tbl.colCnt if hasattr(tbl, "colCnt") else getattr(tbl, "col_cnt", None))
    xsb.attribute(AN.cellSpacing, tbl.cellSpacing if hasattr(tbl, "cellSpacing") else getattr(tbl, "cell_spacing", None))
    xsb.attribute(AN.borderFillIDRef, tbl.borderFillIDRef if hasattr(tbl, "borderFillIDRef") else getattr(tbl, "border_fill_id_ref", None))
    xsb.attribute(AN.noAdjust, tbl.noAdjust if hasattr(tbl, "noAdjust") else getattr(tbl, "no_adjust", None))

    if hasattr(tbl, 'sz') or hasattr(tbl, 'pos'):
        _write_shape_object_children(xsb, tbl)

    # inMargin
    in_margin = getattr(tbl, "inMargin", getattr(tbl, "in_margin", None))
    if in_margin is not None:
        _write_left_right_top_bottom(xsb, EN.hp_inMargin, in_margin)

    # cellzoneList
    czl = getattr(tbl, "cellzoneList", getattr(tbl, "cellzone_list", None))
    if czl is not None:
        items = czl.items() if hasattr(czl, "items") else czl
        cz_items = items() if callable(items) else items
        if len(list(cz_items)) > 0:
            xsb.open_element(EN.hp_cellzoneList)
            cz_items2 = czl.items() if hasattr(czl, "items") else czl
            for cz in (cz_items2() if callable(cz_items2) else cz_items2):
                xsb.open_element(EN.hp_cellzone)
                xsb.attribute(AN.startRowAddr, cz.startRowAddr if hasattr(cz, "startRowAddr") else getattr(cz, "start_row_addr", None))
                xsb.attribute(AN.startColAddr, cz.startColAddr if hasattr(cz, "startColAddr") else getattr(cz, "start_col_addr", None))
                xsb.attribute(AN.endRowAddr, cz.endRowAddr if hasattr(cz, "endRowAddr") else getattr(cz, "end_row_addr", None))
                xsb.attribute(AN.endColAddr, cz.endColAddr if hasattr(cz, "endColAddr") else getattr(cz, "end_col_addr", None))
                xsb.close_element()
            xsb.close_element()

    # Tr rows
    trs = getattr(tbl, "trs", None)
    if trs is not None:
        tr_list = trs() if callable(trs) else trs
        for tr in tr_list:
            _write_tr(xsb, tr)

    # parameterSet
    ps = getattr(tbl, "parameterSet", getattr(tbl, "parameter_set", None))
    if ps is not None:
        _write_parameter_set(xsb, ps)

    # label
    label = getattr(tbl, "label", None)
    if label is not None:
        xsb.open_element(EN.hp_label)
        xsb.attribute(AN.topmargin, label.topMargin if hasattr(label, "topMargin") else getattr(label, "top_margin", None))
        xsb.attribute(AN.leftmargin, label.leftMargin if hasattr(label, "leftMargin") else getattr(label, "left_margin", None))
        xsb.attribute(AN.boxwidth, label.boxWidth if hasattr(label, "boxWidth") else getattr(label, "box_width", None))
        xsb.attribute(AN.boxlength, label.boxLength if hasattr(label, "boxLength") else getattr(label, "box_length", None))
        xsb.attribute(AN.boxmarginhor, label.boxMarginHor if hasattr(label, "boxMarginHor") else getattr(label, "box_margin_hor", None))
        xsb.attribute(AN.boxmarginver, label.boxMarginVer if hasattr(label, "boxMarginVer") else getattr(label, "box_margin_ver", None))
        xsb.attribute(AN.labelcols, label.labelCols if hasattr(label, "labelCols") else getattr(label, "label_cols", None))
        xsb.attribute(AN.labelrows, label.labelRows if hasattr(label, "labelRows") else getattr(label, "label_rows", None))
        xsb.attribute(AN.landscape, label.landscape)
        xsb.attribute(AN.pagewidth, label.pageWidth if hasattr(label, "pageWidth") else getattr(label, "page_width", None))
        xsb.attribute(AN.pageheight, label.pageHeight if hasattr(label, "pageHeight") else getattr(label, "page_height", None))
        xsb.close_element()

    xsb.close_element()


def _write_tr(xsb: XMLStringBuilder, tr: Any) -> None:
    xsb.open_element(EN.hp_tr)

    tcs = getattr(tr, "tcs", None)
    if tcs is not None:
        tc_list = tcs() if callable(tcs) else tcs
        for tc in tc_list:
            _write_tc(xsb, tc)

    xsb.close_element()


def _write_tc(xsb: XMLStringBuilder, tc: Any) -> None:
    xsb.open_element(EN.hp_tc)
    xsb.attribute(AN.name, tc.name)
    xsb.attribute(AN.header, tc.header)
    xsb.attribute(AN.hasMargin, tc.hasMargin if hasattr(tc, "hasMargin") else getattr(tc, "has_margin", None))
    xsb.attribute(AN.borderFillIDRef, tc.borderFillIDRef if hasattr(tc, "borderFillIDRef") else getattr(tc, "border_fill_id_ref", None))
    xsb.attribute(AN.editable, tc.editable)

    # cellAddr
    ca = getattr(tc, "cellAddr", getattr(tc, "cell_addr", None))
    if ca is not None:
        xsb.open_element(EN.hp_cellAddr)
        xsb.attribute(AN.colAddr, ca.colAddr if hasattr(ca, "colAddr") else getattr(ca, "col_addr", None))
        xsb.attribute(AN.rowAddr, ca.rowAddr if hasattr(ca, "rowAddr") else getattr(ca, "row_addr", None))
        xsb.close_element()

    # cellSpan
    cs = getattr(tc, "cellSpan", getattr(tc, "cell_span", None))
    if cs is not None:
        xsb.open_element(EN.hp_cellSpan)
        xsb.attribute(AN.colSpan, cs.colSpan if hasattr(cs, "colSpan") else getattr(cs, "col_span", None))
        xsb.attribute(AN.rowSpan, cs.rowSpan if hasattr(cs, "rowSpan") else getattr(cs, "row_span", None))
        xsb.close_element()

    # cellSz
    csz = getattr(tc, "cellSz", getattr(tc, "cell_sz", None))
    if csz is not None:
        _write_width_and_height(xsb, EN.hp_cellSz, csz)

    # cellMargin
    cm = getattr(tc, "cellMargin", getattr(tc, "cell_margin", None))
    if cm is not None:
        _write_left_right_top_bottom(xsb, EN.hp_cellMargin, cm)

    # subList for cell content
    sub_list = getattr(tc, "subList", getattr(tc, "sub_list", None))
    if sub_list is not None:
        _write_sub_list(xsb, sub_list)
    else:
        # Tc might directly contain paras via ParaListCore inheritance
        paras = getattr(tc, "paras", None)
        if paras is not None:
            para_list = paras() if callable(paras) else paras
            for para in para_list:
                _write_para(xsb, para)

    xsb.close_element()


# ======================================================================
# Picture
# ======================================================================

def _write_picture(xsb: XMLStringBuilder, pic: Any) -> None:
    """Write <hp:pic> following HWPX schema order:
    AbstractShapeComponent (offset..renderingInfo) -> PictureType children
    -> AbstractShapeObject (sz, pos, outMargin, caption, shapeComment).
    """
    xsb.open_element(EN.hp_pic)
    _write_shape_object_attrs(xsb, pic)
    xsb.attribute(
        AN.href,
        getattr(pic, "href", None) if getattr(pic, "href", None) is not None else "",
    )
    xsb.attribute(
        AN.groupLevel,
        getattr(pic, "groupLevel", getattr(pic, "group_level", None)) or 0,
    )
    xsb.attribute(
        AN.instid,
        getattr(pic, "instid", getattr(pic, "inst_id", None)) or "0",
    )
    xsb.attribute(AN.reverse, pic.reverse)

    # 1) Shape component base fields FIRST
    _write_shape_component(xsb, pic)

    # 2) Picture-specific children: imgRect, imgClip, inMargin, imgDim, hc:img
    ir = getattr(pic, "imgRect", getattr(pic, "img_rect", None))
    if ir is not None:
        xsb.open_element(EN.hp_imgRect)
        for pt_name in ["pt0", "pt1", "pt2", "pt3"]:
            pt = getattr(ir, pt_name, None)
            if pt is not None:
                _write_x_and_y(xsb, getattr(EN, f"hc_{pt_name}"), pt)
        xsb.close_element()

    ic = getattr(pic, "imgClip", getattr(pic, "img_clip", None))
    if ic is not None:
        xsb.open_element(EN.hp_imgClip)
        xsb.attribute(AN.left, ic.left)
        xsb.attribute(AN.right, ic.right)
        xsb.attribute(AN.top, ic.top)
        xsb.attribute(AN.bottom, ic.bottom)
        xsb.close_element()
    else:
        # imgClip is required by schema; emit default zeros.
        xsb.open_element(EN.hp_imgClip)
        xsb.attribute(AN.left, 0)
        xsb.attribute(AN.top, 0)
        xsb.attribute(AN.right, 0)
        xsb.attribute(AN.bottom, 0)
        xsb.close_element()

    in_margin = getattr(pic, "inMargin", getattr(pic, "in_margin", None))
    if in_margin is not None:
        _write_left_right_top_bottom(xsb, EN.hp_inMargin, in_margin)
    else:
        xsb.open_element(EN.hp_inMargin)
        xsb.attribute(AN.left, 0)
        xsb.attribute(AN.right, 0)
        xsb.attribute(AN.top, 0)
        xsb.attribute(AN.bottom, 0)
        xsb.close_element()

    dim = getattr(pic, "imgDim", getattr(pic, "img_dim", None))
    if dim is not None:
        xsb.open_element(EN.hp_imgDim)
        xsb.attribute(
            AN.dimwidth,
            getattr(dim, "dimwidth", getattr(dim, "dim_width", None))
            or getattr(dim, "width", None),
        )
        xsb.attribute(
            AN.dimheight,
            getattr(dim, "dimheight", getattr(dim, "dim_height", None))
            or getattr(dim, "height", None),
        )
        xsb.close_element()

    img = getattr(pic, "img", None)
    if img is not None:
        from pyhwpxlib.writer.header.header_writer import _write_img
        _write_img(xsb, img)

    # 3) Shape object children LAST (sz, pos, outMargin, caption, shapeComment)
    _write_shape_object_children(xsb, pic)

    xsb.close_element()


# ======================================================================
# Shape Component (common for drawing objects)
# ======================================================================

def _write_shape_component(xsb: XMLStringBuilder, obj: Any) -> None:
    """Write shape component children: offset, orgSz, curSz, flip, rotationInfo, renderingInfo."""
    offset = getattr(obj, "offset", None)
    if offset is not None:
        _write_x_and_y(xsb, EN.hp_offset, offset)

    org_sz = getattr(obj, "orgSz", getattr(obj, "org_sz", None))
    if org_sz is not None:
        _write_width_and_height(xsb, EN.hp_orgSz, org_sz)

    cur_sz = getattr(obj, "curSz", getattr(obj, "cur_sz", None))
    if cur_sz is not None:
        _write_width_and_height(xsb, EN.hp_curSz, cur_sz)

    flip = getattr(obj, "flip", None)
    if flip is not None:
        xsb.open_element(EN.hp_flip)
        xsb.attribute(AN.horizontal, flip.horizontal)
        xsb.attribute(AN.vertical, flip.vertical)
        xsb.close_element()

    rot = getattr(obj, "rotationInfo", getattr(obj, "rotation_info", None))
    if rot is not None:
        xsb.open_element(EN.hp_rotationInfo)
        xsb.attribute(AN.angle, rot.angle)
        xsb.attribute(AN.centerX, rot.centerX if hasattr(rot, "centerX") else getattr(rot, "center_x", None))
        xsb.attribute(AN.centerY, rot.centerY if hasattr(rot, "centerY") else getattr(rot, "center_y", None))
        xsb.attribute(AN.rotateimage, rot.rotateimage if hasattr(rot, "rotateimage") else getattr(rot, "rotate_image", None))
        xsb.close_element()

    ri = getattr(obj, "renderingInfo", getattr(obj, "rendering_info", None))
    if ri is not None:
        xsb.open_element(EN.hp_renderingInfo)
        for mat_elem, mat_attr in [
            (EN.hc_transMatrix, "transMatrix"),
            (EN.hc_scaMatrix, "scaMatrix"),
            (EN.hc_rotMatrix, "rotMatrix"),
        ]:
            mat = getattr(ri, mat_attr, getattr(ri, _to_snake(mat_attr), None))
            if mat is not None:
                xsb.open_element(mat_elem)
                for e in ["e1", "e2", "e3", "e4", "e5", "e6"]:
                    xsb.attribute(e, getattr(mat, e, None))
                xsb.close_element()
        for extra_mat in getattr(ri, "extra_matrices", []):
            from ...object_type import ObjectType as OT
            ot = extra_mat._object_type()
            if ot == OT.hc_scaMatrix:
                mat_elem = EN.hc_scaMatrix
            elif ot == OT.hc_rotMatrix:
                mat_elem = EN.hc_rotMatrix
            else:
                mat_elem = EN.hc_transMatrix
            xsb.open_element(mat_elem)
            for e in ["e1", "e2", "e3", "e4", "e5", "e6"]:
                xsb.attribute(e, getattr(extra_mat, e, None))
            xsb.close_element()
        xsb.close_element()


# ======================================================================
# Drawing object (generic writer for shapes)
# ======================================================================

def _write_container_child(xsb: XMLStringBuilder, child: Any) -> None:
    """Write a child shape inside an hp:container (omits sz/pos/outMargin)."""
    ot = child._object_type()
    _CHILD_ELEM_MAP = {
        ObjectType.hp_line:        EN.hp_line,
        ObjectType.hp_rect:        EN.hp_rect,
        ObjectType.hp_ellipse:     EN.hp_ellipse,
        ObjectType.hp_arc:         EN.hp_arc,
        ObjectType.hp_polygon:     EN.hp_polygon,
        ObjectType.hp_curve:       EN.hp_curve,
        ObjectType.hp_connectLine: EN.hp_connectLine,
        ObjectType.hp_textart:     EN.hp_textart,
        ObjectType.hp_ole:         EN.hp_ole,
        ObjectType.hp_pic:         None,  # pictures handled separately
    }
    elem_name = _CHILD_ELEM_MAP.get(ot)
    if elem_name is not None:
        _write_drawing_object(xsb, elem_name, child, is_container_child=True)
    else:
        _write_run_item(xsb, child)


def _write_drawing_object(xsb: XMLStringBuilder, elem_name: str, obj: Any, is_container_child: bool = False) -> None:
    """Generic writer for drawing objects (Line, Rect, Ellipse, etc.).

    HWPX schema order:
    ShapeComponent base (offset..renderingInfo) -> lineShape -> fillBrush
    -> shadow -> geometry (pt0..pt3 / pts / segs) -> drawText
    -> ShapeObject children (sz, pos, outMargin) LAST.

    When is_container_child=True, the trailing ShapeObject children (sz, pos,
    outMargin) are omitted — container children in HWPX do not carry these
    elements; they belong only to the top-level container element.
    """
    xsb.open_element(elem_name)
    _write_shape_object_attrs(xsb, obj)

    xsb.attribute(AN.instid, getattr(obj, "instid", getattr(obj, "inst_id", None)))
    xsb.attribute(AN.groupLevel, getattr(obj, "groupLevel", getattr(obj, "group_level", None)))

    # hp:rect-specific: rounded-corner ratio
    if elem_name == EN.hp_rect:
        xsb.attribute(AN.ratio, getattr(obj, "ratio", None))

    # 1) Shape component base (offset, orgSz, curSz, flip, rotationInfo, renderingInfo)
    _write_shape_component(xsb, obj)

    # 2) LineShape (required)
    ls = getattr(obj, "lineShape", getattr(obj, "line_shape", None))
    if ls is not None:
        xsb.open_element(EN.hp_lineShape)
        xsb.attribute(AN.color, ls.color)
        xsb.attribute(AN.width, ls.width)
        xsb.attribute(AN.type, ls.type)
        xsb.attribute(AN.style, ls.style)
        xsb.attribute(AN.endCap, getattr(ls, "endCap", getattr(ls, "end_cap", None)))
        xsb.attribute(AN.headStyle, getattr(ls, "headStyle", getattr(ls, "head_style", None)))
        xsb.attribute(AN.tailStyle, getattr(ls, "tailStyle", getattr(ls, "tail_style", None)))
        xsb.attribute(AN.headfill, getattr(ls, "headfill", getattr(ls, "head_fill", None)))
        xsb.attribute(AN.tailfill, getattr(ls, "tailfill", getattr(ls, "tail_fill", None)))
        xsb.attribute(AN.headSz, getattr(ls, "headSz", getattr(ls, "head_sz", None)))
        xsb.attribute(AN.tailSz, getattr(ls, "tailSz", getattr(ls, "tail_sz", None)))
        xsb.attribute(AN.outlineStyle, getattr(ls, "outlineStyle", getattr(ls, "outline_style", None)))
        xsb.attribute(AN.alpha, ls.alpha)
        xsb.close_element()

    # 3) FillBrush (required)
    fb = getattr(obj, "fillBrush", getattr(obj, "fill_brush", None))
    if fb is not None:
        from pyhwpxlib.writer.header.header_writer import _write_fill_brush
        _write_fill_brush(xsb, fb)

    # 4) Shadow (optional)
    shadow = getattr(obj, "shadow", None)
    if shadow is not None and hasattr(shadow, "type"):
        xsb.open_element(EN.hp_shadow)
        xsb.attribute(AN.type, shadow.type)
        xsb.attribute(AN.color, shadow.color)
        xsb.attribute(AN.offsetX, getattr(shadow, "offsetX", getattr(shadow, "offset_x", None)))
        xsb.attribute(AN.offsetY, getattr(shadow, "offsetY", getattr(shadow, "offset_y", None)))
        xsb.attribute(AN.alpha, shadow.alpha)
        xsb.close_element()

    # 5) Type-specific geometry (pts, segs, startPt/endPt, center/ax1/ax2, ...)
    _write_object_geometry(xsb, elem_name, obj)

    # 6) DrawText (optional, for shapes that contain text)
    dt = getattr(obj, "drawText", getattr(obj, "draw_text", None))
    if dt is not None:
        _write_draw_text(xsb, dt)

    # 6b) Container child shapes (hp:container only)
    child_list = getattr(obj, "_child_list", None)
    if child_list:
        for child in child_list:
            _write_container_child(xsb, child)

    # 7) Shape object children LAST (sz, pos, outMargin)
    # Skip for container children — they don't carry these elements.
    if not is_container_child:
        _write_shape_object_children(xsb, obj)

    xsb.close_element()


def _write_draw_text(xsb: XMLStringBuilder, dt: Any) -> None:
    """Write hp:drawText element."""
    xsb.open_element(EN.hp_drawText)

    # textMargin
    tm = getattr(dt, "textMargin", getattr(dt, "text_margin", None))
    if tm is not None:
        _write_left_right_top_bottom(xsb, EN.hp_textMargin, tm)

    # subList or direct paras
    sl = getattr(dt, "subList", getattr(dt, "sub_list", None))
    if sl is not None:
        _write_sub_list(xsb, sl)
    else:
        paras = getattr(dt, "paras", None)
        if paras is not None:
            for p in (paras() if callable(paras) else paras):
                _write_para(xsb, p)

    xsb.close_element()


def _write_object_geometry(xsb: XMLStringBuilder, elem_name: str, obj: Any) -> None:
    """Write type-specific geometry (line points, ellipse axes, polygon points, etc.)."""
    if elem_name == EN.hp_rect:
        for attr, elem in [
            ("pt0", EN.hc_pt0), ("pt1", EN.hc_pt1),
            ("pt2", EN.hc_pt2), ("pt3", EN.hc_pt3),
        ]:
            pt = getattr(obj, attr, None)
            if pt is not None:
                _write_x_and_y(xsb, elem, pt)

    elif elem_name == EN.hp_arc:
        for attr, elem in [
            ("center", EN.hc_center), ("ax1", EN.hc_ax1), ("ax2", EN.hc_ax2),
        ]:
            pt = getattr(obj, attr, None)
            if pt is not None:
                _write_x_and_y(xsb, elem, pt)

    elif elem_name == EN.hp_line:
        sp = getattr(obj, "startPt", getattr(obj, "start_pt", None))
        ep = getattr(obj, "endPt", getattr(obj, "end_pt", None))
        if sp is not None:
            _write_x_and_y(xsb, EN.hc_startPt, sp)
        if ep is not None:
            _write_x_and_y(xsb, EN.hc_endPt, ep)

    elif elem_name == EN.hp_ellipse:
        for attr, elem in [
            ("center", EN.hc_center), ("ax1", EN.hc_ax1), ("ax2", EN.hc_ax2),
            ("start1", EN.hc_start1), ("start2", EN.hc_start2),
            ("end1", EN.hc_end1), ("end2", EN.hc_end2),
        ]:
            pt = getattr(obj, attr, None)
            if pt is not None:
                _write_x_and_y(xsb, elem, pt)

    elif elem_name == EN.hp_polygon:
        pts = getattr(obj, "pts", getattr(obj, "points", None))
        if pts is not None:
            pt_list = pts() if callable(pts) else pts
            for pt in pt_list:
                _write_x_and_y(xsb, EN.hc_pt, pt)

    elif elem_name == EN.hp_curve:
        segs = getattr(obj, "segs", getattr(obj, "segments", None))
        if segs is not None:
            seg_list = segs() if callable(segs) else segs
            for seg in seg_list:
                xsb.open_element(EN.hp_seg)
                xsb.attribute(AN.type, seg.type)
                xsb.attribute(AN.x1, seg.x1)
                xsb.attribute(AN.y1, seg.y1)
                xsb.attribute(AN.x2, seg.x2)
                xsb.attribute(AN.y2, seg.y2)
                xsb.close_element()

    elif elem_name == EN.hp_connectLine:
        sp = getattr(obj, "startPt", getattr(obj, "start_pt", None))
        ep = getattr(obj, "endPt", getattr(obj, "end_pt", None))
        if sp is not None:
            _write_x_and_y(xsb, EN.hp_startPt, sp)
        if ep is not None:
            _write_x_and_y(xsb, EN.hp_endPt, ep)

        cps = getattr(obj, "controlPoints", getattr(obj, "control_points", None))
        if cps is not None:
            xsb.open_element(EN.hp_controlPoints)
            cp_list = cps() if callable(cps) else cps
            for pt in cp_list:
                _write_x_and_y(xsb, EN.hp_point, pt)
            xsb.close_element()


# ======================================================================
# Equation
# ======================================================================

def _write_equation(xsb: XMLStringBuilder, eq: Any) -> None:
    xsb.open_element(EN.hp_equation)
    _write_shape_object_attrs(xsb, eq)
    _write_shape_object_children(xsb, eq)
    _write_shape_component(xsb, eq)

    script = getattr(eq, "script", None)
    if script is not None:
        xsb.open_element(EN.hp_script)
        text = script.text() if callable(getattr(script, "text", None)) else script.text
        xsb.text(text)
        xsb.close_element()

    xsb.close_element()


# ======================================================================
# Chart
# ======================================================================

def _write_chart(xsb: XMLStringBuilder, ch: Any) -> None:
    xsb.open_element(EN.hp_chart)
    _write_shape_object_attrs(xsb, ch)
    xsb.attribute(AN.chartIDRef, ch.chartIDRef if hasattr(ch, "chartIDRef") else getattr(ch, "chart_id_ref", None))
    _write_shape_object_children(xsb, ch)
    _write_shape_component(xsb, ch)
    xsb.close_element()


# ======================================================================
# Compose / Dutmal
# ======================================================================

def _write_compose(xsb: XMLStringBuilder, comp: Any) -> None:
    xsb.open_element(EN.hp_compose)
    xsb.attribute(AN.circleType, comp.circleType if hasattr(comp, "circleType") else getattr(comp, "circle_type", None))
    xsb.attribute(AN.charSz, comp.charSz if hasattr(comp, "charSz") else getattr(comp, "char_sz", None))
    xsb.attribute(AN.composeType, comp.composeType if hasattr(comp, "composeType") else getattr(comp, "compose_type", None))
    xsb.attribute(AN.composeText, comp.composeText if hasattr(comp, "composeText") else getattr(comp, "compose_text", None))

    char_pr = getattr(comp, "charPr", getattr(comp, "char_pr", None))
    if char_pr is not None:
        xsb.open_element(EN.hp_charPr)
        xsb.attribute(AN.prIDRef, char_pr.charPrIDRef if hasattr(char_pr, "charPrIDRef") else getattr(char_pr, "char_pr_id_ref", None))
        xsb.close_element()

    xsb.close_element()


def _write_dutmal(xsb: XMLStringBuilder, dm: Any) -> None:
    xsb.open_element(EN.hp_dutmal)
    xsb.attribute(AN.posType, dm.posType if hasattr(dm, "posType") else getattr(dm, "pos_type", None))
    xsb.attribute(AN.szRatio, dm.szRatio if hasattr(dm, "szRatio") else getattr(dm, "sz_ratio", None))
    xsb.attribute(AN.option, dm.option)
    xsb.attribute(AN.charPrIDRef, dm.charPrIDRef if hasattr(dm, "charPrIDRef") else getattr(dm, "char_pr_id_ref", None))
    xsb.attribute(AN.fontName, dm.fontName if hasattr(dm, "fontName") else getattr(dm, "font_name", None))

    main_text = getattr(dm, "mainText", getattr(dm, "main_text", None))
    if main_text is not None:
        xsb.open_element(EN.hp_mainText)
        text = main_text.text() if callable(getattr(main_text, "text", None)) else main_text.text
        xsb.text(text)
        xsb.close_element()

    sub_text = getattr(dm, "subText", getattr(dm, "sub_text", None))
    if sub_text is not None:
        xsb.open_element(EN.hp_subText)
        text = sub_text.text() if callable(getattr(sub_text, "text", None)) else sub_text.text
        xsb.text(text)
        xsb.close_element()

    xsb.close_element()


# ======================================================================
# Form objects (generic)
# ======================================================================

def _write_form_object(xsb: XMLStringBuilder, obj: Any, ot: ObjectType) -> None:
    """Write form objects (button, radioBtn, checkBtn, comboBox, edit, listBox, scrollBar)."""
    _OT_TO_ELEM = {
        ObjectType.hp_btn: EN.hp_btn,
        ObjectType.hp_radioBtn: EN.hp_radioBtn,
        ObjectType.hp_checkBtn: EN.hp_checkBtn,
        ObjectType.hp_comboBox: EN.hp_comboBox,
        ObjectType.hp_edit: EN.hp_edit,
        ObjectType.hp_listBox: EN.hp_listBox,
        ObjectType.hp_scrollBar: EN.hp_scrollBar,
    }
    elem = _OT_TO_ELEM.get(ot, EN.hp_btn)
    xsb.open_element(elem)
    _write_shape_object_attrs(xsb, obj)
    _write_shape_object_children(xsb, obj)
    _write_shape_component(xsb, obj)

    # Form common attributes
    xsb.attribute(AN.name, getattr(obj, "name", None))
    xsb.attribute(AN.groupName, getattr(obj, "groupName", getattr(obj, "group_name", None)))
    xsb.attribute(AN.tabOrder, getattr(obj, "tabOrder", getattr(obj, "tab_order", None)))

    # formCharPr
    fcp = getattr(obj, "formCharPr", getattr(obj, "form_char_pr", None))
    if fcp is not None:
        xsb.open_element(EN.hp_formCharPr)
        xsb.attribute(AN.charPrIDRef, fcp.charPrIDRef if hasattr(fcp, "charPrIDRef") else getattr(fcp, "char_pr_id_ref", None))
        xsb.close_element()

    xsb.close_element()


# ======================================================================
# SecPr (Section Properties)
# ======================================================================

def _write_sec_pr(xsb: XMLStringBuilder, sp: Any) -> None:
    """Write hp:secPr element."""
    xsb.open_element(EN.hp_secPr)
    xsb.attribute(AN.id, sp.id)
    xsb.attribute(AN.textDirection, sp.textDirection if hasattr(sp, "textDirection") else getattr(sp, "text_direction", None))
    xsb.attribute(AN.spaceColumns, sp.spaceColumns if hasattr(sp, "spaceColumns") else getattr(sp, "space_columns", None))
    xsb.attribute(AN.tabStop, sp.tabStop if hasattr(sp, "tabStop") else getattr(sp, "tab_stop", None))
    xsb.attribute(AN.tabStopVal, sp.tabStopVal if hasattr(sp, "tabStopVal") else getattr(sp, "tab_stop_val", None))
    xsb.attribute(AN.tabStopUnit, sp.tabStopUnit if hasattr(sp, "tabStopUnit") else getattr(sp, "tab_stop_unit", None))
    xsb.attribute(AN.outlineShapeIDRef, sp.outlineShapeIDRef if hasattr(sp, "outlineShapeIDRef") else getattr(sp, "outline_shape_id_ref", None))
    xsb.attribute(AN.memoShapeIDRef, sp.memoShapeIDRef if hasattr(sp, "memoShapeIDRef") else getattr(sp, "memo_shape_id_ref", None))
    xsb.attribute(AN.textVerticalWidthHead, sp.textVerticalWidthHead if hasattr(sp, "textVerticalWidthHead") else getattr(sp, "text_vertical_width_head", None))
    xsb.attribute(AN.masterPageCnt, sp.masterPageCnt if hasattr(sp, "masterPageCnt") else getattr(sp, "master_page_cnt", None))

    # Grid
    grid = getattr(sp, "grid", None)
    if grid is not None:
        xsb.open_element(EN.hp_grid)
        xsb.attribute(AN.lineGrid, grid.lineGrid if hasattr(grid, "lineGrid") else getattr(grid, "line_grid", None))
        xsb.attribute(AN.charGrid, grid.charGrid if hasattr(grid, "charGrid") else getattr(grid, "char_grid", None))
        xsb.attribute(AN.wonggojiFormat, grid.wonggojiFormat if hasattr(grid, "wonggojiFormat") else getattr(grid, "wonggoji_format", None))
        xsb.close_element()

    # StartNum
    sn = getattr(sp, "startNum", getattr(sp, "start_num", None))
    if sn is not None:
        xsb.open_element(EN.hp_startNum)
        xsb.attribute(AN.pageStartsOn, sn.pageStartsOn if hasattr(sn, "pageStartsOn") else getattr(sn, "page_starts_on", None))
        xsb.attribute(AN.page, sn.page)
        xsb.attribute(AN.pic, sn.pic)
        xsb.attribute(AN.tbl, sn.tbl)
        xsb.attribute(AN.equation, sn.equation)
        xsb.close_element()

    # Visibility
    vis = getattr(sp, "visibility", None)
    if vis is not None:
        xsb.open_element(EN.hp_visibility)
        xsb.attribute(AN.hideFirstHeader, vis.hideFirstHeader if hasattr(vis, "hideFirstHeader") else getattr(vis, "hide_first_header", None))
        xsb.attribute(AN.hideFirstFooter, vis.hideFirstFooter if hasattr(vis, "hideFirstFooter") else getattr(vis, "hide_first_footer", None))
        xsb.attribute(AN.hideFirstMasterPage, vis.hideFirstMasterPage if hasattr(vis, "hideFirstMasterPage") else getattr(vis, "hide_first_master_page", None))
        xsb.attribute(AN.border, vis.border)
        xsb.attribute(AN.fill, vis.fill)
        xsb.attribute(AN.hideFirstPageNum, vis.hideFirstPageNum if hasattr(vis, "hideFirstPageNum") else getattr(vis, "hide_first_page_num", None))
        xsb.attribute(AN.hideFirstEmptyLine, vis.hideFirstEmptyLine if hasattr(vis, "hideFirstEmptyLine") else getattr(vis, "hide_first_empty_line", None))
        xsb.attribute(AN.showLineNumber, vis.showLineNumber if hasattr(vis, "showLineNumber") else getattr(vis, "show_line_number", None))
        xsb.close_element()

    # LineNumberShape
    lns = getattr(sp, "lineNumberShape", getattr(sp, "line_number_shape", None))
    if lns is not None:
        xsb.open_element(EN.hp_lineNumberShape)
        xsb.attribute(AN.restartType, lns.restartType if hasattr(lns, "restartType") else getattr(lns, "restart_type", None))
        xsb.attribute(AN.countBy, lns.countBy if hasattr(lns, "countBy") else getattr(lns, "count_by", None))
        xsb.attribute(AN.distance, lns.distance)
        xsb.attribute(AN.startNumber, lns.startNumber if hasattr(lns, "startNumber") else getattr(lns, "start_number", None))
        xsb.close_element()

    # PagePr
    pp = getattr(sp, "pagePr", getattr(sp, "page_pr", None))
    if pp is not None:
        _write_page_pr(xsb, pp)

    # FootNotePr
    fnp = getattr(sp, "footNotePr", getattr(sp, "foot_note_pr", None))
    if fnp is not None:
        _write_note_pr(xsb, EN.hp_footNotePr, fnp)

    # EndNotePr
    enp = getattr(sp, "endNotePr", getattr(sp, "end_note_pr", None))
    if enp is not None:
        _write_note_pr(xsb, EN.hp_endNotePr, enp)

    # PageBorderFill
    pbfs = getattr(sp, "pageBorderFills", getattr(sp, "page_border_fills", None))
    if pbfs is not None:
        pf_list = pbfs() if callable(pbfs) else pbfs
        for pbf in pf_list:
            _write_page_border_fill(xsb, pbf)

    # MasterPage references
    mps = getattr(sp, "masterPages", getattr(sp, "master_pages", None))
    if mps is not None:
        mp_list = mps() if callable(mps) else mps
        for mp in mp_list:
            xsb.open_element(EN.hp_masterPage)
            xsb.attribute(AN.idRef, mp.idRef if hasattr(mp, "idRef") else getattr(mp, "id_ref", None))
            xsb.close_element()

    # Presentation
    pres = getattr(sp, "presentation", None)
    if pres is not None:
        xsb.open_element(EN.hp_presentation)
        xsb.attribute(AN.soundIDRef, pres.soundIDRef if hasattr(pres, "soundIDRef") else getattr(pres, "sound_id_ref", None))
        xsb.attribute(AN.inventText, pres.inventText if hasattr(pres, "inventText") else getattr(pres, "invent_text", None))
        xsb.attribute(AN.autoshow, pres.autoshow)
        xsb.attribute(AN.showtime, pres.showtime)
        xsb.attribute(AN.applyto, pres.applyto)
        xsb.close_element()

    xsb.close_element()


def _write_page_pr(xsb: XMLStringBuilder, pp: Any) -> None:
    xsb.open_element(EN.hp_pagePr)
    xsb.attribute(AN.landscape, pp.landscape)
    xsb.attribute(AN.width, pp.width)
    xsb.attribute(AN.height, pp.height)
    xsb.attribute(AN.gutterType, pp.gutterType if hasattr(pp, "gutterType") else getattr(pp, "gutter_type", None))

    mg = getattr(pp, "margin", None)
    if mg is not None:
        xsb.open_element(EN.hp_margin)
        xsb.attribute(AN.header, mg.header)
        xsb.attribute(AN.footer, mg.footer)
        xsb.attribute(AN.gutter, mg.gutter)
        xsb.attribute(AN.left, mg.left)
        xsb.attribute(AN.right, mg.right)
        xsb.attribute(AN.top, mg.top)
        xsb.attribute(AN.bottom, mg.bottom)
        xsb.close_element()

    xsb.close_element()


def _write_note_pr(xsb: XMLStringBuilder, elem_name: str, np: Any) -> None:
    """Write hp:footNotePr or hp:endNotePr."""
    xsb.open_element(elem_name)

    anf = getattr(np, "autoNumFormat", getattr(np, "auto_num_format", None))
    if anf is not None:
        xsb.open_element(EN.hp_autoNumFormat)
        xsb.attribute(AN.type, anf.type)
        xsb.attribute(AN.userChar, anf.userChar if hasattr(anf, "userChar") else getattr(anf, "user_char", None))
        xsb.attribute(AN.prefixChar, anf.prefixChar if hasattr(anf, "prefixChar") else getattr(anf, "prefix_char", None))
        xsb.attribute(AN.suffixChar, anf.suffixChar if hasattr(anf, "suffixChar") else getattr(anf, "suffix_char", None))
        xsb.attribute(AN.supscript, anf.supscript)
        xsb.close_element()

    nl = getattr(np, "noteLine", getattr(np, "note_line", None))
    if nl is not None:
        xsb.open_element(EN.hp_noteLine)
        xsb.attribute(AN.length, nl.length)
        xsb.attribute(AN.type, nl.type)
        xsb.attribute(AN.width, nl.width)
        xsb.attribute(AN.color, nl.color)
        xsb.close_element()

    ns = getattr(np, "noteSpacing", getattr(np, "note_spacing", None))
    if ns is not None:
        xsb.open_element(EN.hp_noteSpacing)
        xsb.attribute(AN.betweenNotes, ns.betweenNotes if hasattr(ns, "betweenNotes") else getattr(ns, "between_notes", None))
        xsb.attribute(AN.belowLine, ns.belowLine if hasattr(ns, "belowLine") else getattr(ns, "below_line", None))
        xsb.attribute(AN.aboveLine, ns.aboveLine if hasattr(ns, "aboveLine") else getattr(ns, "above_line", None))
        xsb.close_element()

    numbering = getattr(np, "numbering", None)
    if numbering is not None:
        xsb.open_element(EN.hp_numbering)
        xsb.attribute(AN.type, numbering.type)
        xsb.attribute(AN.newNum, numbering.newNum if hasattr(numbering, "newNum") else getattr(numbering, "new_num", None))
        xsb.close_element()

    placement = getattr(np, "placement", None)
    if placement is not None:
        xsb.open_element(EN.hp_placement)
        xsb.attribute(AN.place, placement.place)
        xsb.attribute(AN.beneathText, placement.beneathText if hasattr(placement, "beneathText") else getattr(placement, "beneath_text", None))
        xsb.close_element()

    xsb.close_element()


def _write_page_border_fill(xsb: XMLStringBuilder, pbf: Any) -> None:
    xsb.open_element(EN.hp_pageBorderFill)
    xsb.attribute(AN.type, pbf.type)
    xsb.attribute(AN.borderFillIDRef, pbf.borderFillIDRef if hasattr(pbf, "borderFillIDRef") else getattr(pbf, "border_fill_id_ref", None))
    xsb.attribute(AN.textBorder, pbf.textBorder if hasattr(pbf, "textBorder") else getattr(pbf, "text_border", None))
    xsb.attribute(AN.headerInside, pbf.headerInside if hasattr(pbf, "headerInside") else getattr(pbf, "header_inside", None))
    xsb.attribute(AN.footerInside, pbf.footerInside if hasattr(pbf, "footerInside") else getattr(pbf, "footer_inside", None))
    xsb.attribute(AN.fillArea, pbf.fillArea if hasattr(pbf, "fillArea") else getattr(pbf, "fill_area", None))

    # offset
    offset = getattr(pbf, "offset", None)
    if offset is not None:
        _write_left_right_top_bottom(xsb, EN.hp_offset, offset)

    xsb.close_element()


# ======================================================================
# Utility
# ======================================================================

def _to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    import re
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
