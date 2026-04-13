"""Write Contents/header.xml - Port of all header writers.

This single module handles:
- HeaderXMLFile root with namespaces
- BeginNum
- RefList with all sub-writers (fontfaces, charpr, parapr, borderfill,
  numbering, bullet, style, tabpr, memopr, trackchanges)
- DocOption, CompatibleDocument, ForbiddenWordList, TrackChangeConfig
"""
from __future__ import annotations

from typing import Any, Optional

from pyhwpxlib.constants import attribute_names as AN
from pyhwpxlib.constants import element_names as EN
from pyhwpxlib.constants.namespaces import Namespaces
from pyhwpxlib.objects.header.header_xml_file import (
    BeginNum,
    CompatibleDocument,
    DocOption,
    ForbiddenWord,
    HeaderXMLFile,
    LayoutCompatibilityItem,
    LinkInfo,
    RefList,
    TrackChangeConfig,
)
from pyhwpxlib.writer.xml_builder import XMLStringBuilder

# All namespaces on header.xml root (same order as Java)
_HEADER_NAMESPACES = [
    Namespaces.ha, Namespaces.hp, Namespaces.hp10, Namespaces.hs,
    Namespaces.hc, Namespaces.hh, Namespaces.hhs, Namespaces.hm,
    Namespaces.hpf, Namespaces.dc, Namespaces.opf, Namespaces.ooxmlchart,
    Namespaces.epub, Namespaces.config,
]


def write_header(xsb: XMLStringBuilder, header: HeaderXMLFile) -> None:
    """Serialize a HeaderXMLFile into *xsb*."""
    xsb.clear()
    xsb.open_element(EN.hh_head)
    for ns in _HEADER_NAMESPACES:
        xsb.namespace(ns)
    xsb.attribute(AN.version, header.version)
    xsb.attribute(AN.secCnt, header.secCnt)

    if header.beginNum is not None:
        _write_begin_num(xsb, header.beginNum)

    if header.refList is not None:
        _write_ref_list(xsb, header.refList)

    if header.forbiddenWordList is not None:
        _write_forbidden_word_list(xsb, header.forbiddenWordList)

    if header.compatibleDocument is not None:
        _write_compatible_document(xsb, header.compatibleDocument)

    if header.docOption is not None:
        _write_doc_option(xsb, header.docOption)

    if header.metaTag is not None:
        xsb.open_element(EN.hh_metaTag)
        xsb.text(header.metaTag.text())
        xsb.close_element()

    if header.trackChangeConfig is not None:
        _write_track_change_config(xsb, header.trackChangeConfig)

    xsb.close_element()


# ======================================================================
# BeginNum
# ======================================================================

def _write_begin_num(xsb: XMLStringBuilder, bn: BeginNum) -> None:
    xsb.open_element(EN.hh_beginNum)
    xsb.attribute(AN.page, bn.page)
    xsb.attribute(AN.footnote, bn.footnote)
    xsb.attribute(AN.endnote, bn.endnote)
    xsb.attribute(AN.pic, bn.pic)
    xsb.attribute(AN.tbl, bn.tbl)
    xsb.attribute(AN.equation, bn.equation)
    xsb.close_element()


# ======================================================================
# RefList and all sub-writers
# ======================================================================

def _write_ref_list(xsb: XMLStringBuilder, ref_list: RefList) -> None:
    xsb.open_element(EN.hh_refList)

    if ref_list.fontfaces is not None:
        _write_fontfaces(xsb, ref_list.fontfaces)

    if ref_list.borderFills is not None:
        _write_collection(xsb, EN.hh_borderFills, ref_list.borderFills, _write_border_fill)

    if ref_list.charProperties is not None:
        _write_collection(xsb, EN.hh_charProperties, ref_list.charProperties, _write_char_pr)

    if ref_list.tabProperties is not None:
        _write_collection(xsb, EN.hh_tabProperties, ref_list.tabProperties, _write_tab_pr)

    if ref_list.numberings is not None:
        _write_collection(xsb, EN.hh_numberings, ref_list.numberings, _write_numbering)

    if ref_list.bullets is not None:
        _write_collection(xsb, EN.hh_bullets, ref_list.bullets, _write_bullet)

    if ref_list.paraProperties is not None:
        _write_collection(xsb, EN.hh_paraProperties, ref_list.paraProperties, _write_para_pr)

    if ref_list.styles is not None:
        _write_collection(xsb, EN.hh_styles, ref_list.styles, _write_style)

    if ref_list.memoProperties is not None:
        _write_collection(xsb, EN.hh_memoProperties, ref_list.memoProperties, _write_memo_pr)

    if ref_list.trackChanges is not None:
        _write_collection(xsb, EN.hh_trackChanges, ref_list.trackChanges, _write_track_change)

    if ref_list.trackChangeAuthors is not None:
        _write_collection(xsb, EN.hh_trackChangeAuthors, ref_list.trackChangeAuthors, _write_track_change_author)

    xsb.close_element()


def _write_collection(xsb, wrapper_elem, obj_list, item_writer_fn) -> None:
    """Write a collection wrapper element with itemCnt and per-item writer."""
    count = len(obj_list) if hasattr(obj_list, "__len__") else obj_list.count()
    if count == 0:
        return
    xsb.open_element(wrapper_elem)
    xsb.attribute(AN.itemCnt, count)
    for item in obj_list.items():
        item_writer_fn(xsb, item)
    xsb.close_element()


# ------------------------------------------------------------------
# Fontfaces
# ------------------------------------------------------------------

def _write_fontfaces(xsb: XMLStringBuilder, fontfaces: Any) -> None:
    """Write hh:fontfaces element.

    fontfaces is a Fontfaces object with .fontfaces() returning a list of Fontface.
    """
    xsb.open_element(EN.hh_fontfaces)
    xsb.attribute(AN.itemCnt, 7)  # Java hardcodes 7

    for fontface in fontfaces.fontfaces():
        _write_fontface(xsb, fontface)

    xsb.close_element()


def _write_fontface(xsb: XMLStringBuilder, fontface: Any) -> None:
    xsb.open_element(EN.hh_fontface)
    xsb.attribute(AN.lang, fontface.lang)
    xsb.attribute(AN.fontCnt, fontface.count_of_font() if hasattr(fontface, "count_of_font") else None)

    for font in fontface.fonts():
        _write_font(xsb, font)

    xsb.close_element()


def _write_font(xsb: XMLStringBuilder, font: Any) -> None:
    xsb.open_element(EN.hh_font)
    xsb.attribute(AN.id, font.id)
    xsb.attribute(AN.face, font.face)
    xsb.attribute(AN.type, font.type)
    xsb.attribute(AN.isEmbedded, getattr(font, "isEmbedded", getattr(font, "is_embedded", None)))
    xsb.attribute(AN.binaryItemIDRef, getattr(font, "binaryItemIDRef", getattr(font, "binary_item_id_ref", None)))

    sf = getattr(font, "substFont", None) or getattr(font, "subst_font", None)
    if sf is not None:
        xsb.open_element(EN.hh_substFont)
        xsb.attribute(AN.face, sf.face)
        xsb.attribute(AN.type, sf.type)
        xsb.attribute(AN.isEmbedded, getattr(sf, "isEmbedded", getattr(sf, "is_embedded", None)))
        xsb.attribute(AN.binaryItemIDRef, getattr(sf, "binaryItemIDRef", getattr(sf, "binary_item_id_ref", None)))
        xsb.close_element()

    ti = getattr(font, "typeInfo", None) or getattr(font, "type_info", None)
    if ti is not None:
        xsb.open_element(EN.hh_typeInfo)
        xsb.attribute(AN.familyType, ti.family_type if hasattr(ti, "family_type") else getattr(ti, "familyType", None))
        xsb.attribute(AN.serifStyle, ti.serif_style if hasattr(ti, "serif_style") else getattr(ti, "serifStyle", None))
        xsb.attribute(AN.weight, ti.weight)
        xsb.attribute(AN.proportion, ti.proportion)
        xsb.attribute(AN.contrast, ti.contrast)
        xsb.attribute(AN.strokeVariation, ti.stroke_variation if hasattr(ti, "stroke_variation") else getattr(ti, "strokeVariation", None))
        xsb.attribute(AN.armStyle, ti.arm_style if hasattr(ti, "arm_style") else getattr(ti, "armStyle", None))
        xsb.attribute(AN.letterform, ti.letterform)
        xsb.attribute(AN.midline, ti.midline)
        xsb.attribute(AN.xHeight, ti.x_height if hasattr(ti, "x_height") else getattr(ti, "xHeight", None))
        xsb.close_element()

    xsb.close_element()


# ------------------------------------------------------------------
# CharPr
# ------------------------------------------------------------------

def _write_char_pr(xsb: XMLStringBuilder, cp: Any) -> None:
    xsb.open_element(EN.hh_charPr)
    xsb.attribute(AN.id, cp.id)
    xsb.attribute(AN.height, cp.height)
    xsb.attribute(AN.textColor, cp.textColor if hasattr(cp, "textColor") else getattr(cp, "text_color", None))
    xsb.attribute(AN.shadeColor, cp.shadeColor if hasattr(cp, "shadeColor") else getattr(cp, "shade_color", None))
    xsb.attribute(AN.useFontSpace, cp.useFontSpace if hasattr(cp, "useFontSpace") else getattr(cp, "use_font_space", None))
    xsb.attribute(AN.useKerning, cp.useKerning if hasattr(cp, "useKerning") else getattr(cp, "use_kerning", None))
    xsb.attribute(AN.symMark, cp.symMark if hasattr(cp, "symMark") else getattr(cp, "sym_mark", None))
    xsb.attribute(AN.borderFillIDRef, cp.borderFillIDRef if hasattr(cp, "borderFillIDRef") else getattr(cp, "border_fill_id_ref", None))

    # ValuesByLanguage children
    for elem_name, attr_name in [
        (EN.hh_fontRef, "fontRef"),
        (EN.hh_ratio, "ratio"),
        (EN.hh_spacing, "spacing"),
        (EN.hh_relSz, "relSz"),
        (EN.hh_offset, "offset"),
    ]:
        val = getattr(cp, attr_name, None)
        if val is not None:
            _write_values_by_language(xsb, elem_name, val)

    # No-attribute children (bold, italic, emboss, engrave, supscript, subscript)
    for attr_name, elem_name in [
        ("bold", EN.hh_bold), ("italic", EN.hh_italic),
        ("emboss", EN.hh_emboss), ("engrave", EN.hh_engrave),
        ("supscript", EN.hh_supscript), ("subscript", EN.hh_subscript),
    ]:
        if getattr(cp, attr_name, None) is not None:
            xsb.open_element(elem_name)
            xsb.close_element()

    # Underline
    ul = getattr(cp, "underline", None)
    if ul is not None:
        xsb.open_element(EN.hh_underline)
        xsb.attribute(AN.type, ul.type)
        xsb.attribute(AN.shape, ul.shape)
        xsb.attribute(AN.color, ul.color)
        xsb.close_element()

    # Strikeout
    so = getattr(cp, "strikeout", None)
    if so is not None:
        xsb.open_element(EN.hh_strikeout)
        xsb.attribute(AN.shape, so.shape)
        xsb.attribute(AN.color, so.color)
        xsb.close_element()

    # Outline
    ol = getattr(cp, "outline", None)
    if ol is not None:
        xsb.open_element(EN.hh_outline)
        xsb.attribute(AN.type, ol.type)
        xsb.close_element()

    # Shadow
    sh = getattr(cp, "shadow", None)
    if sh is not None:
        xsb.open_element(EN.hh_shadow)
        xsb.attribute(AN.type, sh.type)
        xsb.attribute(AN.color, sh.color)
        xsb.attribute(AN.offsetX, sh.offsetX if hasattr(sh, "offsetX") else getattr(sh, "offset_x", None))
        xsb.attribute(AN.offsetY, sh.offsetY if hasattr(sh, "offsetY") else getattr(sh, "offset_y", None))
        xsb.close_element()

    xsb.close_element()


def _write_values_by_language(xsb: XMLStringBuilder, elem_name: str, vbl: Any) -> None:
    """Write a ValuesByLanguage element with hangul/latin/hanja/japanese/other/symbol/user."""
    xsb.open_element(elem_name)
    xsb.attribute(AN.hangul, vbl.hangul)
    xsb.attribute(AN.latin, vbl.latin)
    xsb.attribute(AN.hanja, vbl.hanja)
    xsb.attribute(AN.japanese, vbl.japanese)
    xsb.attribute(AN.other, vbl.other)
    xsb.attribute(AN.symbol, vbl.symbol)
    xsb.attribute(AN.user, vbl.user)
    xsb.close_element()


# ------------------------------------------------------------------
# ParaPr
# ------------------------------------------------------------------

def _write_para_pr(xsb: XMLStringBuilder, pp: Any) -> None:
    xsb.open_element(EN.hh_paraPr)
    xsb.attribute(AN.id, pp.id)
    xsb.attribute(AN.tabPrIDRef, pp.tabPrIDRef if hasattr(pp, "tabPrIDRef") else getattr(pp, "tab_pr_id_ref", None))
    xsb.attribute(AN.condense, pp.condense)
    xsb.attribute(AN.fontLineHeight, pp.fontLineHeight if hasattr(pp, "fontLineHeight") else getattr(pp, "font_line_height", None))
    xsb.attribute(AN.snapToGrid, pp.snapToGrid if hasattr(pp, "snapToGrid") else getattr(pp, "snap_to_grid", None))
    xsb.attribute(AN.suppressLineNumbers, pp.suppressLineNumbers if hasattr(pp, "suppressLineNumbers") else getattr(pp, "suppress_line_numbers", None))
    xsb.attribute(AN.checked, pp.checked)

    # Align
    a = getattr(pp, "align", None)
    if a is not None:
        xsb.open_element(EN.hh_align)
        xsb.attribute(AN.horizontal, a.horizontal)
        xsb.attribute(AN.vertical, a.vertical)
        xsb.close_element()

    # Heading (may be absent if inside a switch block)
    h = getattr(pp, "heading", None)
    if h is not None:
        _write_heading(xsb, h)

    # Switch blocks (e.g. heading overrides for outline levels 7-9)
    _write_switch_blocks(xsb, pp)

    # BreakSetting
    bs = getattr(pp, "breakSetting", getattr(pp, "break_setting", None))
    if bs is not None:
        xsb.open_element(EN.hh_breakSetting)
        xsb.attribute(AN.breakLatinWord, bs.breakLatinWord if hasattr(bs, "breakLatinWord") else getattr(bs, "break_latin_word", None))
        xsb.attribute(AN.breakNonLatinWord, bs.breakNonLatinWord if hasattr(bs, "breakNonLatinWord") else getattr(bs, "break_non_latin_word", None))
        xsb.attribute(AN.widowOrphan, bs.widowOrphan if hasattr(bs, "widowOrphan") else getattr(bs, "widow_orphan", None))
        xsb.attribute(AN.keepWithNext, bs.keepWithNext if hasattr(bs, "keepWithNext") else getattr(bs, "keep_with_next", None))
        xsb.attribute(AN.keepLines, bs.keepLines if hasattr(bs, "keepLines") else getattr(bs, "keep_lines", None))
        xsb.attribute(AN.pageBreakBefore, bs.pageBreakBefore if hasattr(bs, "pageBreakBefore") else getattr(bs, "page_break_before", None))
        xsb.attribute(AN.lineWrap, bs.lineWrap if hasattr(bs, "lineWrap") else getattr(bs, "line_wrap", None))
        xsb.close_element()

    # AutoSpacing
    asp = getattr(pp, "autoSpacing", getattr(pp, "auto_spacing", None))
    if asp is not None:
        xsb.open_element(EN.hh_autoSpacing)
        xsb.attribute(AN.eAsianEng, asp.eAsianEng if hasattr(asp, "eAsianEng") else getattr(asp, "e_asian_eng", None))
        xsb.attribute(AN.eAsianNum, asp.eAsianNum if hasattr(asp, "eAsianNum") else getattr(asp, "e_asian_num", None))
        xsb.close_element()

    mg = getattr(pp, "margin", None)
    ls = getattr(pp, "lineSpacing", getattr(pp, "line_spacing", None))
    if mg is not None:
        _write_para_margin(xsb, mg)
    if ls is not None:
        xsb.open_element(EN.hh_lineSpacing)
        xsb.attribute(AN.type, ls.type)
        xsb.attribute(AN.value, ls.value)
        xsb.attribute(AN.unit, ls.unit)
        xsb.close_element()

    # Border
    bd = getattr(pp, "border", None)
    if bd is not None:
        xsb.open_element(EN.hh_border)
        xsb.attribute(AN.borderFillIDRef, bd.borderFillIDRef if hasattr(bd, "borderFillIDRef") else getattr(bd, "border_fill_id_ref", None))
        xsb.attribute(AN.offsetLeft, bd.offsetLeft if hasattr(bd, "offsetLeft") else getattr(bd, "offset_left", None))
        xsb.attribute(AN.offsetRight, bd.offsetRight if hasattr(bd, "offsetRight") else getattr(bd, "offset_right", None))
        xsb.attribute(AN.offsetTop, bd.offsetTop if hasattr(bd, "offsetTop") else getattr(bd, "offset_top", None))
        xsb.attribute(AN.offsetBottom, bd.offsetBottom if hasattr(bd, "offsetBottom") else getattr(bd, "offset_bottom", None))
        xsb.attribute(AN.connect, bd.connect)
        xsb.attribute(AN.ignoreMargin, bd.ignoreMargin if hasattr(bd, "ignoreMargin") else getattr(bd, "ignore_margin", None))
        xsb.close_element()

    xsb.close_element()


def _write_para_margin(xsb: XMLStringBuilder, mg: Any) -> None:
    xsb.open_element(EN.hh_margin)

    for elem_name, attr_name in [
        (EN.hc_intent, "intent"),
        (EN.hc_left, "left"),
        (EN.hc_right, "right"),
        (EN.hc_prev, "prev"),
        (EN.hc_next, "next"),
    ]:
        val = getattr(mg, attr_name, None)
        if val is not None:
            xsb.open_element(elem_name)
            xsb.attribute(AN.value, val.value)
            xsb.attribute(AN.unit, val.unit)
            xsb.close_element()

    xsb.close_element()


def _write_heading(xsb: XMLStringBuilder, h: Any) -> None:
    """Write hh:heading element."""
    xsb.open_element(EN.hh_heading)
    xsb.attribute(AN.type, h.type)
    xsb.attribute(AN.idRef, h.idRef if hasattr(h, "idRef") else getattr(h, "id_ref", None))
    xsb.attribute(AN.level, h.level)
    xsb.close_element()


def _write_switch_blocks(xsb: XMLStringBuilder, obj: Any) -> None:
    """Write hp:switch/hp:case/hp:default blocks from a SwitchableObject."""
    switch_list = getattr(obj, "_switch_list", None)
    if not switch_list:
        return

    for sw in switch_list:
        xsb.open_element(EN.hp_switch)

        for case_obj in sw.case_objects():
            xsb.open_element(EN.hp_case)
            ns = getattr(case_obj, "required_namespace", None)
            if ns is not None:
                xsb.attribute(AN.hp_required_namespace, ns)
            for child in case_obj.children():
                _write_switch_child(xsb, child)
            xsb.close_element()

        default_obj = sw.default_object()
        if default_obj is not None:
            xsb.open_element(EN.hp_default)
            for child in default_obj.children():
                _write_switch_child(xsb, child)
            xsb.close_element()

        xsb.close_element()


def _write_switch_child(xsb: XMLStringBuilder, child: Any) -> None:
    """Write a child element inside a switch case/default block."""
    from pyhwpxlib.object_type import ObjectType

    ot = child._object_type() if hasattr(child, "_object_type") else None
    if ot == ObjectType.hh_heading:
        _write_heading(xsb, child)
    elif ot == ObjectType.hh_margin:
        _write_para_margin(xsb, child)
    elif ot == ObjectType.hh_lineSpacing:
        xsb.open_element(EN.hh_lineSpacing)
        xsb.attribute(AN.type, child.type)
        xsb.attribute(AN.value, child.value)
        xsb.attribute(AN.unit, child.unit)
        xsb.close_element()


# ------------------------------------------------------------------
# BorderFill
# ------------------------------------------------------------------

def _write_border_fill(xsb: XMLStringBuilder, bf: Any) -> None:
    xsb.open_element(EN.hh_borderFill)
    xsb.attribute(AN.id, bf.id)
    xsb.attribute(AN.threeD, bf.threeD if hasattr(bf, "threeD") else getattr(bf, "three_d", None))
    xsb.attribute(AN.shadow, bf.shadow)
    xsb.attribute(AN.centerLine, bf.centerLine if hasattr(bf, "centerLine") else getattr(bf, "center_line", None))
    xsb.attribute(AN.breakCellSeparateLine, bf.breakCellSeparateLine if hasattr(bf, "breakCellSeparateLine") else getattr(bf, "break_cell_separate_line", None))

    # Slash / BackSlash
    for elem_name, attr_name in [
        (EN.hh_slash, "slash"), (EN.hh_backSlash, "backSlash"),
    ]:
        sc = getattr(bf, attr_name, getattr(bf, attr_name.lower(), None))
        if sc is not None:
            xsb.open_element(elem_name)
            xsb.attribute(AN.type, sc.type)
            xsb.attribute(AN.Crooked, sc.Crooked if hasattr(sc, "Crooked") else getattr(sc, "crooked", None))
            xsb.attribute(AN.isCounter, sc.isCounter if hasattr(sc, "isCounter") else getattr(sc, "is_counter", None))
            xsb.close_element()

    # Borders
    for elem_name, attr_name in [
        (EN.hh_leftBorder, "leftBorder"),
        (EN.hh_rightBorder, "rightBorder"),
        (EN.hh_topBorder, "topBorder"),
        (EN.hh_bottomBorder, "bottomBorder"),
        (EN.hh_diagonal, "diagonal"),
    ]:
        border = getattr(bf, attr_name, getattr(bf, _to_snake(attr_name), None))
        if border is not None:
            xsb.open_element(elem_name)
            xsb.attribute(AN.type, border.type)
            xsb.attribute(AN.width, border.width)
            xsb.attribute(AN.color, border.color)
            xsb.close_element()

    # FillBrush
    fb = getattr(bf, "fillBrush", getattr(bf, "fill_brush", None))
    if fb is not None:
        _write_fill_brush(xsb, fb)

    xsb.close_element()


def _write_fill_brush(xsb: XMLStringBuilder, fb: Any) -> None:
    """Write hc:fillBrush and its children (winBrush, gradation, imgBrush)."""
    xsb.open_element(EN.hc_fillBrush)

    wb = getattr(fb, "winBrush", getattr(fb, "win_brush", None))
    if wb is not None:
        xsb.open_element(EN.hc_winBrush)
        xsb.attribute(AN.faceColor, wb.faceColor if hasattr(wb, "faceColor") else getattr(wb, "face_color", None))
        xsb.attribute(AN.hatchColor, wb.hatchColor if hasattr(wb, "hatchColor") else getattr(wb, "hatch_color", None))
        xsb.attribute(AN.hatchStyle, wb.hatchStyle if hasattr(wb, "hatchStyle") else getattr(wb, "hatch_style", None))
        xsb.attribute(AN.alpha, wb.alpha)
        xsb.close_element()

    grad = getattr(fb, "gradation", None)
    if grad is not None:
        xsb.open_element(EN.hc_gradation)
        xsb.attribute(AN.type, grad.type)
        xsb.attribute(AN.angle, grad.angle)
        xsb.attribute(AN.centerX, grad.centerX if hasattr(grad, "centerX") else getattr(grad, "center_x", None))
        xsb.attribute(AN.centerY, grad.centerY if hasattr(grad, "centerY") else getattr(grad, "center_y", None))
        xsb.attribute(AN.step, grad.step)
        xsb.attribute(AN.colorNum, grad.colorNum if hasattr(grad, "colorNum") else getattr(grad, "color_num", None))
        xsb.attribute(AN.stepCenter, grad.stepCenter if hasattr(grad, "stepCenter") else getattr(grad, "step_center", None))
        # colors
        colors = getattr(grad, "colors", None)
        if colors is not None:
            for color in (colors() if callable(colors) else colors):
                xsb.open_element(EN.hc_color)
                xsb.attribute(AN.value, color.value if hasattr(color, "value") else color)
                xsb.close_element()
        xsb.close_element()

    ib = getattr(fb, "imgBrush", getattr(fb, "img_brush", None))
    if ib is not None:
        xsb.open_element(EN.hc_imgBrush)
        xsb.attribute(AN.mode, ib.mode)
        # img child
        img = getattr(ib, "img", None)
        if img is not None:
            _write_img(xsb, img)
        xsb.close_element()

    xsb.close_element()


def _write_img(xsb: XMLStringBuilder, img: Any) -> None:
    """Write hc:img element."""
    xsb.open_element(EN.hc_img)
    xsb.attribute(AN.binaryItemIDRef, img.binaryItemIDRef if hasattr(img, "binaryItemIDRef") else getattr(img, "binary_item_id_ref", None))
    xsb.attribute(AN.bright, img.bright)
    xsb.attribute(AN.contrast, img.contrast)
    xsb.attribute(AN.effect, img.effect)
    xsb.attribute(AN.alpha, img.alpha)
    xsb.close_element()


# ------------------------------------------------------------------
# TabPr
# ------------------------------------------------------------------

def _write_tab_pr(xsb: XMLStringBuilder, tp: Any) -> None:
    xsb.open_element(EN.hh_tabPr)
    xsb.attribute(AN.id, tp.id)
    xsb.attribute(AN.autoTabLeft, tp.autoTabLeft if hasattr(tp, "autoTabLeft") else getattr(tp, "auto_tab_left", None))
    xsb.attribute(AN.autoTabRight, tp.autoTabRight if hasattr(tp, "autoTabRight") else getattr(tp, "auto_tab_right", None))

    tab_items = getattr(tp, "tabItems", getattr(tp, "tab_items", None))
    if tab_items is not None:
        items = tab_items() if callable(tab_items) else tab_items
        items_list = list(items)
        if items_list:
            for ti in items_list:
                xsb.open_element(EN.hh_tabItem)
                xsb.attribute(AN.pos, ti.pos)
                xsb.attribute(AN.type, ti.type)
                xsb.attribute(AN.leader, ti.leader)
                xsb.close_element()

    xsb.close_element()


# ------------------------------------------------------------------
# Numbering
# ------------------------------------------------------------------

def _write_numbering(xsb: XMLStringBuilder, n: Any) -> None:
    xsb.open_element(EN.hh_numbering)
    xsb.attribute(AN.id, n.id)
    xsb.attribute(AN.start, n.start)

    para_heads = getattr(n, "paraHeads", getattr(n, "para_heads", None))
    if para_heads is not None:
        items = para_heads() if callable(para_heads) else para_heads
        for ph in items:
            _write_para_head(xsb, ph)

    xsb.close_element()


def _write_para_head(xsb: XMLStringBuilder, ph: Any) -> None:
    """Write hh:paraHead - shared by Numbering and Bullet."""
    xsb.open_element(EN.hh_paraHead)
    xsb.attribute(AN.start, ph.start)
    xsb.attribute(AN.level, ph.level)
    xsb.attribute(AN.align, ph.align)
    xsb.attribute(AN.useInstWidth, ph.useInstWidth if hasattr(ph, "useInstWidth") else getattr(ph, "use_inst_width", None))
    xsb.attribute(AN.autoIndent, ph.autoIndent if hasattr(ph, "autoIndent") else getattr(ph, "auto_indent", None))
    xsb.attribute(AN.widthAdjust, ph.widthAdjust if hasattr(ph, "widthAdjust") else getattr(ph, "width_adjust", None))
    xsb.attribute(AN.textOffsetType, ph.textOffsetType if hasattr(ph, "textOffsetType") else getattr(ph, "text_offset_type", None))
    xsb.attribute(AN.textOffset, ph.textOffset if hasattr(ph, "textOffset") else getattr(ph, "text_offset", None))
    xsb.attribute(AN.numFormat, ph.numFormat if hasattr(ph, "numFormat") else getattr(ph, "num_format", None))
    xsb.attribute(AN.charPrIDRef, ph.charPrIDRef if hasattr(ph, "charPrIDRef") else getattr(ph, "char_pr_id_ref", None))
    xsb.attribute(AN.checkable, ph.checkable)
    xsb.text(getattr(ph, "text", None) if isinstance(getattr(ph, "text", None), str) else (ph.text() if callable(getattr(ph, "text", None)) else None))
    xsb.close_element()


# ------------------------------------------------------------------
# Bullet
# ------------------------------------------------------------------

def _write_bullet(xsb: XMLStringBuilder, b: Any) -> None:
    xsb.open_element(EN.hh_bullet)
    xsb.attribute(AN.id, b.id)
    xsb.attribute(AN._char, b._char if hasattr(b, "_char") else getattr(b, "char", None))
    xsb.attribute(AN.checkedChar, b.checkedChar if hasattr(b, "checkedChar") else getattr(b, "checked_char", None))
    xsb.attribute(AN.useImage, b.useImage if hasattr(b, "useImage") else getattr(b, "use_image", None))

    img = getattr(b, "img", None)
    if img is not None:
        _write_img(xsb, img)

    ph = getattr(b, "paraHead", getattr(b, "para_head", None))
    if ph is not None:
        _write_para_head(xsb, ph)

    xsb.close_element()


# ------------------------------------------------------------------
# Style
# ------------------------------------------------------------------

def _write_style(xsb: XMLStringBuilder, s: Any) -> None:
    xsb.open_element(EN.hh_style)
    xsb.attribute(AN.id, s.id)
    xsb.attribute(AN.type, s.type)
    xsb.attribute(AN.name, s.name)
    xsb.attribute(AN.engName, s.engName if hasattr(s, "engName") else getattr(s, "eng_name", None))
    xsb.attribute(AN.paraPrIDRef, s.paraPrIDRef if hasattr(s, "paraPrIDRef") else getattr(s, "para_pr_id_ref", None))
    xsb.attribute(AN.charPrIDRef, s.charPrIDRef if hasattr(s, "charPrIDRef") else getattr(s, "char_pr_id_ref", None))
    xsb.attribute(AN.nextStyleIDRef, s.nextStyleIDRef if hasattr(s, "nextStyleIDRef") else getattr(s, "next_style_id_ref", None))
    xsb.attribute(AN.langID, s.langID if hasattr(s, "langID") else getattr(s, "lang_id", None))
    xsb.attribute(AN.lockForm, s.lockForm if hasattr(s, "lockForm") else getattr(s, "lock_form", None))
    xsb.close_element()


# ------------------------------------------------------------------
# MemoPr
# ------------------------------------------------------------------

def _write_memo_pr(xsb: XMLStringBuilder, mp: Any) -> None:
    xsb.open_element(EN.hh_memoPr)
    xsb.attribute(AN.id, mp.id)
    xsb.attribute(AN.width, mp.width)
    xsb.attribute(AN.lineType, mp.lineType if hasattr(mp, "lineType") else getattr(mp, "line_type", None))
    # lineWidth uses attributeIndex in Java
    lw = getattr(mp, "lineWidth", getattr(mp, "line_width", None))
    if lw is not None:
        xsb.attribute_index(AN.lineWidth, lw)
    xsb.attribute(AN.lineColor, mp.lineColor if hasattr(mp, "lineColor") else getattr(mp, "line_color", None))
    xsb.attribute(AN.fillColor, mp.fillColor if hasattr(mp, "fillColor") else getattr(mp, "fill_color", None))
    xsb.attribute(AN.activeColor, mp.activeColor if hasattr(mp, "activeColor") else getattr(mp, "active_color", None))
    xsb.attribute(AN.memoType, mp.memoType if hasattr(mp, "memoType") else getattr(mp, "memo_type", None))
    xsb.close_element()


# ------------------------------------------------------------------
# TrackChange / TrackChangeAuthor
# ------------------------------------------------------------------

def _write_track_change(xsb: XMLStringBuilder, tc: Any) -> None:
    xsb.open_element(EN.hh_trackChange)
    xsb.attribute(AN.id, tc.id)
    xsb.attribute(AN.date, tc.date)
    xsb.attribute(AN.authorID, tc.authorID if hasattr(tc, "authorID") else getattr(tc, "author_id", None))
    xsb.attribute(AN.hide, tc.hide)
    xsb.attribute(AN.charshapeID, tc.charshapeID if hasattr(tc, "charshapeID") else getattr(tc, "charshape_id", None))
    xsb.attribute(AN.parashapeID, tc.parashapeID if hasattr(tc, "parashapeID") else getattr(tc, "parashape_id", None))
    xsb.close_element()


def _write_track_change_author(xsb: XMLStringBuilder, tca: Any) -> None:
    xsb.open_element(EN.hh_trackChangeAuthor)
    xsb.attribute(AN.id, tca.id)
    xsb.attribute(AN.name, tca.name)
    xsb.attribute(AN.mark, tca.mark)
    xsb.close_element()


# ======================================================================
# DocOption
# ======================================================================

def _write_doc_option(xsb: XMLStringBuilder, doc_opt: DocOption) -> None:
    xsb.open_element(EN.hh_docOption)

    if doc_opt.linkinfo is not None:
        _write_linkinfo(xsb, doc_opt.linkinfo)

    xsb.close_element()


def _write_linkinfo(xsb: XMLStringBuilder, li: LinkInfo) -> None:
    xsb.open_element(EN.hh_linkinfo)
    xsb.attribute(AN.path, li.path)
    xsb.attribute(AN.pageInherit, li.pageInherit)
    xsb.attribute(AN.footnoteInherit, li.footnoteInherit)
    xsb.close_element()


# ======================================================================
# ForbiddenWordList
# ======================================================================

def _write_forbidden_word_list(xsb: XMLStringBuilder, fwl) -> None:
    count = len(fwl) if hasattr(fwl, "__len__") else fwl.count()
    if count == 0:
        return

    xsb.open_element(EN.hh_forbiddenWordList)
    xsb.attribute(AN.itemCnt, count)

    for fw in fwl.items():
        xsb.open_element(EN.hh_forbiddenWord)
        xsb.text(fw.text() if callable(getattr(fw, "text", None)) else fw.text)
        xsb.close_element()

    xsb.close_element()


# ======================================================================
# CompatibleDocument
# ======================================================================

def _write_compatible_document(xsb: XMLStringBuilder, cd: CompatibleDocument) -> None:
    xsb.open_element(EN.hh_compatibleDocument)
    xsb.attribute(AN.targetProgram, cd.targetProgram)

    if cd.layoutCompatibility is not None:
        xsb.open_element(EN.hh_layoutCompatibility)
        for item in cd.layoutCompatibility.items():
            _write_layout_compat_item(xsb, item)
        xsb.close_element()

    xsb.close_element()


def _write_layout_compat_item(xsb: XMLStringBuilder, item: LayoutCompatibilityItem) -> None:
    xsb.open_element(item.name)
    xsb.text(item.text)
    xsb.close_element()


# ======================================================================
# TrackChangeConfig
# ======================================================================

def _write_track_change_config(xsb: XMLStringBuilder, tcc: TrackChangeConfig) -> None:
    xsb.open_element(EN.hh_trackchageConfig)
    xsb.attribute(AN.flags, tcc.flags)

    if tcc.configItemSet is not None:
        from pyhwpxlib.writer.settings_writer import _write_config_item_set
        _write_config_item_set(xsb, tcc.configItemSet)

    xsb.close_element()


# ======================================================================
# Utility
# ======================================================================

def _to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    import re
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
