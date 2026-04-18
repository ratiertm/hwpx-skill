"""BlankFileMaker - creates a valid empty HWPX document.

Faithfully ported from the Java hwpxlib BlankFileMaker by kr.dogfoot.
All values (IDs, font names, sizes, margins) match the Java original exactly.
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..hwpx_file import HWPXFile
from ..objects.content_hpf.content_hpf import ContentHPFFile, Meta, MetaData
from ..objects.header.enum_types import (
    CenterLineSort,
    CharShadowType,
    FontFamilyType,
    FontType,
    HatchStyle,
    HorizontalAlign1,
    HorizontalAlign2,
    LanguageType,
    LineBreakForLatin,
    LineBreakForNonLatin,
    LineSpacingType,
    LineType1,
    LineType2,
    LineType3,
    LineWidth,
    LineWrap,
    NumberType1,
    ParaHeadingType,
    SlashType,
    StyleType,
    SymMarkSort,
    TargetProgramSort,
    UnderlineType,
    ValueUnit1,
    ValueUnit2,
    VerticalAlign1,
)
from ..objects.header.header_xml_file import HeaderXMLFile, RefList
from ..objects.header.references.border_fill import BorderFill
from ..objects.header.references.char_pr import CharPr
from ..objects.header.references.fontface import Fontfaces
from ..objects.header.references.numbering import Numbering
from ..objects.header.references.para_pr import ParaMargin, LineSpacing, ParaPr
from ..objects.header.references.style import Style
from ..objects.header.references.tab_pr import TabPr
from ..objects.metainf.container import ContainerXMLFile
from ..objects.root.settings import SettingsXMLFile
from ..objects.root.version import TargetApplicationSort, VersionXMLFile
from ..objects.section.enum_types import (
    ApplyPageType,
    ColumnDirection,
    EndNoteNumberingType,
    EndNotePlace,
    FootNoteNumberingType,
    FootNotePlace,
    GutterMethod,
    MultiColumnType,
    NumberType2,
    PageBorderPositionCriterion,
    PageDirection,
    PageFillArea,
    PageStartON,
    TextDirection,
    VisibilityOption,
)
from ..objects.section.section_xml_file import SectionXMLFile


class BlankFileMaker:
    """Creates a valid blank HWPX document matching the Java hwpxlib output."""

    @staticmethod
    def make(font_set=None) -> HWPXFile:
        hwpx_file = HWPXFile()
        _settings_xml_file(hwpx_file.settings_xml_file)
        _version_xml_file(hwpx_file.version_xml_file)
        _container_xml_file(hwpx_file.container_xml_file)
        _content_hpf_file(hwpx_file.content_hpf_file)

        header = HeaderXMLFile()
        hwpx_file.header_xml_file = header
        _header_xml_file(header, font_set=font_set)

        section = SectionXMLFile()
        hwpx_file.section_xml_file_list.add(section)
        _section0_xml_file(section)

        return hwpx_file


# ============================================================
# Settings XML
# ============================================================

def _settings_xml_file(settings: SettingsXMLFile) -> None:
    cp = settings.create_caret_position()
    cp.list_id_ref = 0
    cp.para_id_ref = 0
    cp.pos = 16


# ============================================================
# Version XML
# ============================================================

def _version_xml_file(version: VersionXMLFile) -> None:
    version.target_application = TargetApplicationSort.WordProcessor
    version.application = "Hancom Office Hangul"
    version.app_version = "13, 0, 0, 1408 WIN32LEWindows_Unknown_Version"
    version.version.major = 5
    version.version.minor = 1
    version.version.micro = 1
    version.version.build_number = 0
    version.version.os = "1"
    version.version.xml_version = "1.5"


# ============================================================
# Container XML
# ============================================================

def _container_xml_file(container: ContainerXMLFile) -> None:
    root_files = container.create_root_files()
    rf = root_files.add_new()
    rf.full_path = "Contents/content.hpf"
    rf.media_type = "application/hwpml-package+xml"


# ============================================================
# Content HPF
# ============================================================

def _content_hpf_file(hpf: ContentHPFFile) -> None:
    hpf.version = ""
    hpf.unique_identifier = ""
    hpf.id = ""

    # MetaData
    md = hpf.create_meta_data()
    md.create_title()
    lang = md.create_language()
    lang.add_text("ko")

    _add_meta(md, "creator", "text", None)
    _add_meta(md, "subject", "text", None)
    _add_meta(md, "description", "text", None)
    _add_meta(md, "lastsaveby", "text", None)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    _add_meta(md, "CreatedDate", "text", now_str)
    _add_meta(md, "ModifiedDate", "text", now_str)
    _add_meta(md, "date", "text", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    _add_meta(md, "keyword", "text", None)

    # Manifest
    manifest = hpf.create_manifest()
    item = manifest.add_new()
    item.id = "header"
    item.href = "Contents/header.xml"
    item.media_type = "application/xml"

    item = manifest.add_new()
    item.id = "section0"
    item.href = "Contents/section0.xml"
    item.media_type = "application/xml"

    item = manifest.add_new()
    item.id = "settings"
    item.href = "settings.xml"
    item.media_type = "application/xml"

    # Spine
    spine = hpf.create_spine()
    ref = spine.add_new()
    ref.idref = "header"
    ref.linear = "yes"

    ref = spine.add_new()
    ref.idref = "section0"
    ref.linear = "yes"


def _add_meta(md: MetaData, name: str, content: str, text: str | None) -> None:
    m = md.add_new_meta()
    m.name = name
    m.content = content
    if text is not None:
        m.text = text


# ============================================================
# Header XML
# ============================================================

def _header_xml_file(header: HeaderXMLFile, font_set=None) -> None:
    header.version = "1.2"
    header.secCnt = 1

    # BeginNum
    bn = header.create_begin_num()
    bn.page = 1
    bn.footnote = 1
    bn.endnote = 1
    bn.pic = 1
    bn.tbl = 1
    bn.equation = 1

    # RefList
    ref_list = header.create_ref_list()
    _fontfaces(ref_list, font_set=font_set)
    _border_fills(ref_list)
    _char_properties(ref_list)
    _tab_properties(ref_list)
    _numberings(ref_list)
    _para_properties(ref_list)
    _styles(ref_list)

    # CompatibleDocument
    cd = header.create_compatible_document()
    cd.targetProgram = TargetProgramSort.HWP201X
    cd.create_layout_compatibility()

    # DocOption
    doc_opt = header.create_doc_option()
    li = doc_opt.create_linkinfo()
    li.path = ""
    li.pageInherit = False
    li.footnoteInherit = False

    # TrackChangeConfig
    tcc = header.create_track_change_config()
    tcc.flags = 56


# ============================================================
# Fontfaces
# ============================================================

def _fontfaces(ref_list: RefList, font_set=None) -> None:
    fontfaces: Fontfaces = ref_list.create_fontfaces()
    for lang in [
        LanguageType.HANGUL,
        LanguageType.LATIN,
        LanguageType.HANJA,
        LanguageType.JAPANESE,
        LanguageType.OTHER,
        LanguageType.SYMBOL,
        LanguageType.USER,
    ]:
        ff = fontfaces.add_new_fontface()
        ff.lang = lang
        if font_set is not None:
            _add_theme_fonts(ff, font_set)
        else:
            _add_font_pair(ff)


def _add_font_pair(fontface) -> None:
    # Font 0: 나눔고딕 (bundled in vendor/)
    f1 = fontface.add_new_font()
    f1.id = "0"
    f1.face = "나눔고딕"
    f1.type = FontType.TTF
    f1.isEmbedded = False
    ti1 = f1.create_type_info()
    ti1.familyType = FontFamilyType.FCAT_GOTHIC
    ti1.weight = 6
    ti1.proportion = 4
    ti1.contrast = 0
    ti1.strokeVariation = 1
    ti1.armStyle = True
    ti1.letterform = True
    ti1.midline = 1
    ti1.xHeight = 1

    # Font 1: 나눔명조 (system fallback — NanumMyeongjo)
    f2 = fontface.add_new_font()
    f2.id = "1"
    f2.face = "나눔명조"
    f2.type = FontType.TTF
    f2.isEmbedded = False
    ti2 = f2.create_type_info()
    ti2.familyType = FontFamilyType.FCAT_GOTHIC
    ti2.weight = 6
    ti2.proportion = 4
    ti2.contrast = 0
    ti2.strokeVariation = 1
    ti2.armStyle = True
    ti2.letterform = True
    ti2.midline = 1
    ti2.xHeight = 1


def _add_theme_fonts(fontface, font_set) -> None:
    """Register all unique fonts from a FontSet with incremental IDs."""
    unique_fonts = []
    seen = set()
    for font_name in [
        font_set.heading_hangul, font_set.heading_latin,
        font_set.body_hangul, font_set.body_latin,
        font_set.caption_hangul, font_set.caption_latin,
    ]:
        if font_name not in seen:
            seen.add(font_name)
            unique_fonts.append(font_name)

    for i, font_name in enumerate(unique_fonts):
        f = fontface.add_new_font()
        f.id = str(i)
        f.face = font_name
        f.type = FontType.TTF
        f.isEmbedded = False
        ti = f.create_type_info()
        ti.familyType = FontFamilyType.FCAT_GOTHIC
        ti.weight = 6
        ti.proportion = 4
        ti.contrast = 0
        ti.strokeVariation = 1
        ti.armStyle = True
        ti.letterform = True
        ti.midline = 1
        ti.xHeight = 1


# ============================================================
# BorderFills
# ============================================================

def _border_fills(ref_list: RefList) -> None:
    bf_list = ref_list.create_border_fills()
    # borderFill 1: all NONE borders
    _make_border_fill(bf_list.add_new(), "1",
                      LineType2.NONE, LineWidth.MM_0_1,
                      None, None, None)
    # borderFill 2: all NONE borders + winBrush(none, #999999)
    _make_border_fill(bf_list.add_new(), "2",
                      LineType2.NONE, LineWidth.MM_0_1,
                      "none", "#999999", None)
    # borderFill 3: SOLID 0.12mm borders, no fill
    _make_border_fill(bf_list.add_new(), "3",
                      LineType2.SOLID, LineWidth.MM_0_12,
                      None, None, None)
    # borderFill 4: NONE borders + winBrush(none, #FF6600)
    _make_border_fill(bf_list.add_new(), "4",
                      LineType2.NONE, LineWidth.MM_0_1,
                      "none", "#FF6600", None)
    # borderFill 5: SOLID 0.12mm + winBrush(#FFFFFF, #FF6600, VERTICAL)
    _make_border_fill(bf_list.add_new(), "5",
                      LineType2.SOLID, LineWidth.MM_0_12,
                      "#FFFFFF", "#FF6600", HatchStyle.VERTICAL)
    # borderFill 6: SOLID 0.12mm + winBrush(#FFFFFF, #6182D6)
    _make_border_fill(bf_list.add_new(), "6",
                      LineType2.SOLID, LineWidth.MM_0_12,
                      "#FFFFFF", "#6182D6", None)
    # borderFill 7: NONE 0.12mm + winBrush(#FFFFFF, #FF0000, CROSS) + backSlash CENTER
    bf7 = bf_list.add_new()
    _make_border_fill(bf7, "7",
                      LineType2.NONE, LineWidth.MM_0_12,
                      "#FFFFFF", "#FF0000", HatchStyle.CROSS)
    bf7.backSlash.type = SlashType.CENTER
    # borderFill 8: SOLID 0.12mm + winBrush(#FFFFFF, #3A3C84)
    _make_border_fill(bf_list.add_new(), "8",
                      LineType2.SOLID, LineWidth.MM_0_12,
                      "#FFFFFF", "#3A3C84", None)


def _make_border_fill(
    bf: BorderFill,
    bf_id: str,
    border_type: LineType2,
    border_width: LineWidth,
    face_color: str | None,
    hatch_color: str | None,
    hatch_style: HatchStyle | None,
) -> None:
    bf.id = bf_id
    bf.threeD = False
    bf.shadow = False
    bf.centerLine = CenterLineSort.NONE
    bf.breakCellSeparateLine = False

    slash = bf.create_slash()
    slash.type = SlashType.NONE
    slash.Crooked = False
    slash.isCounter = False

    back_slash = bf.create_back_slash()
    back_slash.type = SlashType.NONE
    back_slash.Crooked = False
    back_slash.isCounter = False

    for create_fn in [bf.create_left_border, bf.create_right_border,
                      bf.create_top_border, bf.create_bottom_border]:
        b = create_fn()
        b.type = border_type
        b.width = border_width
        b.color = "#000000"

    diag = bf.create_diagonal()
    diag.type = LineType2.SOLID
    diag.width = LineWidth.MM_0_1
    diag.color = "#000000"

    if face_color is not None or hatch_color is not None:
        fb = bf.create_fill_brush()
        wb = fb.create_win_brush()
        wb.faceColor = face_color
        wb.hatchColor = hatch_color
        wb.hatchStyle = hatch_style
        wb.alpha = 0.0


# ============================================================
# CharProperties
# ============================================================

def _char_properties(ref_list: RefList) -> None:
    cp_list = ref_list.create_char_properties()

    # charPr 0: height=1000, fontRef=1, textColor=#000000
    _make_char_pr(cp_list.add_new(), "0", 1000, "#000000", "1", [0] * 7)
    # charPr 1: height=1000, fontRef=0, textColor=#000000
    _make_char_pr(cp_list.add_new(), "1", 1000, "#000000", "0", [0] * 7)
    # charPr 2: height=900, fontRef=0
    _make_char_pr(cp_list.add_new(), "2", 900, "#000000", "0", [0] * 7)
    # charPr 3: height=900, fontRef=1
    _make_char_pr(cp_list.add_new(), "3", 900, "#000000", "1", [0] * 7)
    # charPr 4: height=900, fontRef=0, spacing=-5
    _make_char_pr(cp_list.add_new(), "4", 900, "#000000", "0", [-5] * 7)
    # charPr 5: height=1600, fontRef=0, textColor=#2E74B5
    _make_char_pr(cp_list.add_new(), "5", 1600, "#2E74B5", "0", [0] * 7)
    # charPr 6: height=1100, fontRef=0
    _make_char_pr(cp_list.add_new(), "6", 1100, "#000000", "0", [0] * 7)
    # charPr 7: height=1400, fontRef=1, spacing=5, ratio=105, relSz=103, offset=5, bold, outline=SOLID
    cp7 = cp_list.add_new()
    _make_char_pr(cp7, "7", 1400, "#000000", "1", [5] * 7,
                  ratio_vals=[105] * 7, rel_sz_vals=[103] * 7, offset_vals=[5] * 7)
    cp7.create_bold()
    ol = cp7.create_outline()
    ol.type = LineType1.SOLID


def _make_char_pr(
    cp: CharPr,
    cp_id: str,
    height: int,
    text_color: str,
    font_ref_id: str,
    spacing_vals: list[int],
    ratio_vals: list[int] | None = None,
    rel_sz_vals: list[int] | None = None,
    offset_vals: list[int] | None = None,
) -> None:
    cp.id = cp_id
    cp.height = height
    cp.textColor = text_color
    cp.shadeColor = "none"
    cp.useFontSpace = False
    cp.useKerning = False
    cp.symMark = SymMarkSort.NONE
    cp.borderFillIDRef = "2"

    fr = cp.create_font_ref()
    fr.set(font_ref_id, font_ref_id, font_ref_id, font_ref_id,
           font_ref_id, font_ref_id, font_ref_id)

    rv = ratio_vals or [100] * 7
    ratio = cp.create_ratio()
    ratio.set(rv[0], rv[1], rv[2], rv[3], rv[4], rv[5], rv[6])

    s = spacing_vals
    spacing = cp.create_spacing()
    spacing.set(s[0], s[1], s[2], s[3], s[4], s[5], s[6])

    rsv = rel_sz_vals or [100] * 7
    rel_sz = cp.create_rel_sz()
    rel_sz.set(rsv[0], rsv[1], rsv[2], rsv[3], rsv[4], rsv[5], rsv[6])

    ov = offset_vals or [0] * 7
    offset = cp.create_offset()
    offset.set(ov[0], ov[1], ov[2], ov[3], ov[4], ov[5], ov[6])

    so = cp.create_strikeout()
    so.shape = "NONE"
    so.color = "#000000"


# ============================================================
# TabProperties
# ============================================================

def _tab_properties(ref_list: RefList) -> None:
    tp_list = ref_list.create_tab_properties()

    tp0: TabPr = tp_list.add_new()
    tp0.id = "0"
    tp0.autoTabLeft = False
    tp0.autoTabRight = False

    tp1: TabPr = tp_list.add_new()
    tp1.id = "1"
    tp1.autoTabLeft = True
    tp1.autoTabRight = False

    tp2: TabPr = tp_list.add_new()
    tp2.id = "2"
    tp2.autoTabLeft = False
    tp2.autoTabRight = True


# ============================================================
# Numberings
# ============================================================

def _numberings(ref_list: RefList) -> None:
    num_list = ref_list.create_numberings()

    # Level 1-10 para heads (shared between numbering 1 and 2)
    _para_head_data = [
        # (level, numFormat,                         text,    checkable)
        (1,  NumberType1.DIGIT,                       "^1.",   False),
        (2,  NumberType1.HANGUL_SYLLABLE,             "^2.",   False),
        (3,  NumberType1.DIGIT,                       "^3)",   False),
        (4,  NumberType1.HANGUL_SYLLABLE,             "^4)",   False),
        (5,  NumberType1.DIGIT,                       "(^5)",  False),
        (6,  NumberType1.HANGUL_SYLLABLE,             "(^6)",  False),
        (7,  NumberType1.CIRCLED_DIGIT,               "^7",    True),
        (8,  NumberType1.CIRCLED_HANGUL_SYLLABLE,     "^8",    True),
        (9,  NumberType1.HANGUL_JAMO,                 None,    False),
        (10, NumberType1.ROMAN_SMALL,                 None,    True),
    ]

    _para_head_data_2 = [
        # (level, numFormat,                         text,    checkable)
        (1,  NumberType1.DIGIT,                       "^1.",   False),
        (2,  NumberType1.HANGUL_SYLLABLE,             "^2.",   False),
        (3,  NumberType1.DIGIT,                       "^3)",   False),
        (4,  NumberType1.HANGUL_SYLLABLE,             "^4)",   False),
        (5,  NumberType1.DIGIT,                       "(^5)",  False),
        (6,  NumberType1.HANGUL_SYLLABLE,             "(^6)",  False),
        (7,  NumberType1.CIRCLED_DIGIT,               "^7",    True),
        (8,  NumberType1.CIRCLED_HANGUL_SYLLABLE,     "^8",    True),
        (9,  NumberType1.DIGIT,                       None,    False),
        (10, NumberType1.DIGIT,                       None,    False),
    ]

    # Numbering 1: start=0
    numbering1: Numbering = num_list.add_new()
    numbering1.id = "1"
    numbering1.start = 0
    _add_para_heads(numbering1, _para_head_data)

    # Numbering 2: start=1
    numbering2: Numbering = num_list.add_new()
    numbering2.id = "2"
    numbering2.start = 1
    _add_para_heads(numbering2, _para_head_data_2)


def _add_para_heads(numbering: Numbering, data: list) -> None:
    for level, num_fmt, text, checkable in data:
        ph = numbering.add_new_para_head()
        ph.start = 1
        ph.level = level
        ph.align = HorizontalAlign1.LEFT
        ph.useInstWidth = True
        ph.autoIndent = True
        ph.widthAdjust = 0
        ph.textOffsetType = ValueUnit1.PERCENT
        ph.textOffset = 50
        ph.numFormat = num_fmt
        ph.charPrIDRef = "4294967295"
        ph.checkable = checkable
        ph.text = text


# ============================================================
# ParaProperties
# ============================================================

def _para_properties(ref_list: RefList) -> None:
    pp_list = ref_list.create_para_properties()

    # All 24 paraPr entries from reference, with exact values.
    # Tuple: (id, tabPrIDRef, condense, h_align,
    #   heading_type, heading_idRef, heading_level,
    #   breakLatinWord, breakNonLatinWord,
    #   widowOrphan, keepWithNext, keepLines, pageBreakBefore,
    #   eAsianEng, eAsianNum,
    #   intent, left, right, prev, next, lineSpacing,
    #   borderFillIDRef, offsetLeft, offsetRight, offsetTop, offsetBottom,
    #   switch_heading_level)  -- None if no switch

    _KW = LineBreakForLatin.KEEP_WORD
    _BW = LineBreakForNonLatin.BREAK_WORD
    _KW2 = LineBreakForNonLatin.KEEP_WORD
    _J = HorizontalAlign2.JUSTIFY
    _L = HorizontalAlign2.LEFT
    _C = HorizontalAlign2.CENTER
    _N = ParaHeadingType.NONE
    _O = ParaHeadingType.OUTLINE
    _NUM = ParaHeadingType.NUMBER

    _pp_data = [
        # id  tab  cond  halign head   idRef lvl  brkLat  brkNL    wid  kwn  kl   pbb  eaE  eaN  int   left  right prev  next  ls   bfRef oL  oR  oT  oB   swLvl
        ("0",  "0", 0,   _J,    _N,    "0",  0,   _KW,    _BW,     0,   0,   0,   0,   0,   0,   0,    0,    0,    0,    0,    160, "2",  0,  0,  0,  0,   None),
        ("1",  "0", 0,   _J,    _N,    "0",  0,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    3000, 0,    0,    0,    160, "2",  0,  0,  0,  0,   None),
        ("2",  "1", 20,  _J,    _O,    "0",  0,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    2000, 0,    0,    0,    160, "2",  0,  0,  0,  0,   None),
        ("3",  "1", 20,  _J,    _O,    "0",  1,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    4000, 0,    0,    0,    160, "2",  0,  0,  0,  0,   None),
        ("4",  "1", 20,  _J,    _O,    "0",  2,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    6000, 0,    0,    0,    160, "2",  0,  0,  0,  0,   None),
        ("5",  "1", 20,  _J,    _O,    "0",  3,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    8000, 0,    0,    0,    160, "2",  0,  0,  0,  0,   None),
        ("6",  "1", 20,  _J,    _O,    "0",  4,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    10000,0,    0,    0,    160, "2",  0,  0,  0,  0,   None),
        ("7",  "1", 20,  _J,    _O,    "0",  5,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    12000,0,    0,    0,    160, "2",  0,  0,  0,  0,   None),
        ("8",  "1", 20,  _J,    _O,    "0",  6,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    14000,0,    0,    0,    160, "2",  0,  0,  0,  0,   None),
        ("9",  "0", 0,   _J,    _N,    "0",  0,   _KW,    _BW,     0,   0,   0,   0,   0,   0,   0,    0,    0,    0,    0,    150, "2",  0,  0,  0,  0,   None),
        ("10", "0", 0,   _J,    _N,    "0",  0,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   -2620,0,    0,    0,    0,    130, "2",  0,  0,  0,  0,   None),
        ("11", "0", 0,   _L,    _N,    "0",  0,   _KW,    _BW,     0,   0,   0,   0,   0,   0,   0,    0,    0,    0,    0,    130, "2",  0,  0,  0,  0,   None),
        ("12", "1", 20,  _L,    _N,    "0",  0,   _KW,    _BW,     0,   0,   0,   0,   0,   0,   0,    0,    0,    2400, 600,  160, "2",  0,  0,  0,  0,   None),
        ("13", "2", 0,   _L,    _N,    "0",  0,   _KW,    _BW,     0,   0,   0,   0,   0,   0,   0,    0,    0,    0,    1400, 160, "2",  0,  0,  0,  0,   None),
        ("14", "2", 0,   _L,    _N,    "0",  0,   _KW,    _BW,     0,   0,   0,   0,   0,   0,   0,    2200, 0,    0,    1400, 160, "2",  0,  0,  0,  0,   None),
        ("15", "2", 0,   _L,    _N,    "0",  0,   _KW,    _BW,     0,   0,   0,   0,   0,   0,   0,    4400, 0,    0,    1400, 160, "2",  0,  0,  0,  0,   None),
        ("16", "1", 0,   _J,    _N,    "0",  0,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    18000,0,    0,    0,    160, "2",  0,  0,  0,  0,   8),
        ("17", "1", 0,   _J,    _N,    "0",  0,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    20000,0,    0,    0,    160, "2",  0,  0,  0,  0,   9),
        ("18", "1", 0,   _J,    _N,    "0",  0,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    16000,0,    0,    0,    160, "2",  0,  0,  0,  0,   7),
        ("19", "0", 0,   _J,    _N,    "0",  0,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    0,    0,    0,    1600, 150, "2",  0,  0,  0,  0,   None),
        ("20", "2", 0,   _J,    _N,    "0",  0,   _KW,    _BW,     0,   0,   0,   0,   0,   0,   0,    0,    0,    0,    0,    150, "2",  283,283,283,283, None),
        ("21", "0", 0,   _J,    _N,    "0",  0,   _KW,    _KW2,    0,   0,   0,   0,   0,   0,   0,    0,    0,    0,    0,    160, "2",  0,  0,  0,  0,   None),
        ("22", "0", 0,   _C,    _N,    "0",  0,   _KW,    _BW,     0,   0,   0,   0,   0,   0,   0,    0,    0,    0,    0,    160, "4",  0,  0,  0,  0,   None),
        ("23", "0", 0,   _J,    _NUM,  "2",  0,   _KW,    _BW,     0,   0,   0,   0,   0,   0,   0,    0,    0,    0,    0,    160, "2",  0,  0,  0,  0,   None),
    ]

    for row in _pp_data:
        (pp_id, tab_ref, condense, h_align,
         heading_type, heading_id_ref, heading_level,
         break_latin, break_non_latin,
         widow_orphan, keep_with_next, keep_lines, page_break_before,
         e_asian_eng, e_asian_num,
         intent, left, right, prev, next_v, ls_val,
         bf_ref, oL, oR, oT, oB,
         switch_heading_level) = row

        pp = pp_list.add_new()
        pp.id = pp_id
        pp.tabPrIDRef = tab_ref
        pp.condense = condense
        pp.fontLineHeight = False
        pp.snapToGrid = True
        pp.suppressLineNumbers = False
        pp.checked = False

        align = pp.create_align()
        align.horizontal = h_align
        align.vertical = VerticalAlign1.BASELINE

        # For paraPr 16-18: heading is inside a switch block, NOT direct
        if switch_heading_level is not None:
            # Switch block: case has OUTLINE heading, default has NONE
            sw = pp.add_new_switch()
            sw.position = 1  # after align, before breakSetting

            case_obj = sw.add_new_case_object()
            case_obj.required_namespace = "http://www.hancom.co.kr/hwpml/2016/paragraph"

            from ..objects.header.references.para_pr import Heading as HeadingObj
            case_heading = HeadingObj()
            case_heading.type = ParaHeadingType.OUTLINE
            case_heading.idRef = heading_id_ref
            case_heading.level = switch_heading_level
            case_obj.add_child(case_heading)

            sw.create_default_object()
            default_obj = sw.default_object()
            default_heading = HeadingObj()
            default_heading.type = ParaHeadingType.NONE
            default_heading.idRef = "0"
            default_heading.level = 0
            default_obj.add_child(default_heading)
        else:
            heading = pp.create_heading()
            heading.type = heading_type
            heading.idRef = heading_id_ref
            heading.level = heading_level

        bs = pp.create_break_setting()
        bs.breakLatinWord = break_latin
        bs.breakNonLatinWord = break_non_latin
        bs.widowOrphan = bool(widow_orphan)
        bs.keepWithNext = bool(keep_with_next)
        bs.keepLines = bool(keep_lines)
        bs.pageBreakBefore = bool(page_break_before)
        bs.lineWrap = LineWrap.BREAK

        auto = pp.create_auto_spacing()
        auto.eAsianEng = bool(e_asian_eng)
        auto.eAsianNum = bool(e_asian_num)

        # Margin (direct child, not in switch)
        margin = pp.create_margin()
        m_intent = margin.create_intent()
        m_intent.value = intent
        m_intent.unit = ValueUnit2.HWPUNIT.value
        m_left = margin.create_left()
        m_left.value = left
        m_left.unit = ValueUnit2.HWPUNIT.value
        m_right = margin.create_right()
        m_right.value = right
        m_right.unit = ValueUnit2.HWPUNIT.value
        m_prev = margin.create_prev()
        m_prev.value = prev
        m_prev.unit = ValueUnit2.HWPUNIT.value
        m_next = margin.create_next()
        m_next.value = next_v
        m_next.unit = ValueUnit2.HWPUNIT.value

        # LineSpacing (direct child, not in switch)
        ls = pp.create_line_spacing()
        ls.type = LineSpacingType.PERCENT
        ls.value = ls_val
        ls.unit = ValueUnit2.HWPUNIT

        # Border
        border = pp.create_border()
        border.borderFillIDRef = bf_ref
        border.offsetLeft = oL
        border.offsetRight = oR
        border.offsetTop = oT
        border.offsetBottom = oB
        border.connect = False
        border.ignoreMargin = False


# ============================================================
# Styles
# ============================================================

def _styles(ref_list: RefList) -> None:
    st_list = ref_list.create_styles()

    _style_data = [
        # (id, type,       name,         engName,          paraPrIDRef, charPrIDRef, nextStyleIDRef)
        ("0",  StyleType.PARA, "바탕글",     "Normal",          "0",  "0", "0"),
        ("1",  StyleType.PARA, "본문",       "Body",            "1",  "0", "1"),
        ("2",  StyleType.PARA, "개요 1",     "Outline 1",       "2",  "0", "2"),
        ("3",  StyleType.PARA, "개요 2",     "Outline 2",       "3",  "0", "3"),
        ("4",  StyleType.PARA, "개요 3",     "Outline 3",       "4",  "0", "4"),
        ("5",  StyleType.PARA, "개요 4",     "Outline 4",       "5",  "0", "5"),
        ("6",  StyleType.PARA, "개요 5",     "Outline 5",       "6",  "0", "6"),
        ("7",  StyleType.PARA, "개요 6",     "Outline 6",       "7",  "0", "7"),
        ("8",  StyleType.PARA, "개요 7",     "Outline 7",       "8",  "0", "8"),
        ("9",  StyleType.PARA, "개요 8",     "Outline 8",       "18", "0", "9"),
        ("10", StyleType.PARA, "개요 9",     "Outline 9",       "16", "0", "10"),
        ("11", StyleType.PARA, "개요 10",    "Outline 10",      "17", "0", "11"),
        ("12", StyleType.CHAR, "쪽 번호",    "Page Number",     "0",  "1", "0"),
        ("13", StyleType.CHAR, "줄 번호",    "Line Number",     "0",  "0", "0"),
        ("14", StyleType.PARA, "머리말",     "Header",          "9",  "2", "14"),
        ("15", StyleType.PARA, "각주",       "Footnote",        "10", "3", "15"),
        ("16", StyleType.PARA, "미주",       "Endnote",         "10", "3", "16"),
        ("17", StyleType.PARA, "메모",       "Memo",            "11", "4", "17"),
        ("18", StyleType.PARA, "차례 제목",  "TOC Heading",     "12", "5", "18"),
        ("19", StyleType.PARA, "차례 1",     "TOC 1",           "13", "6", "19"),
        ("20", StyleType.PARA, "차례 2",     "TOC 2",           "14", "6", "20"),
        ("21", StyleType.PARA, "차례 3",     "TOC 3",           "15", "6", "21"),
        ("22", StyleType.PARA, "캡션",       "Caption",         "19", "0", "22"),
    ]
    for sid, stype, name, eng_name, pp_ref, cp_ref, next_ref in _style_data:
        s: Style = st_list.add_new()
        s.id = sid
        s.type = stype
        s.name = name
        s.engName = eng_name
        s.paraPrIDRef = pp_ref
        s.charPrIDRef = cp_ref
        s.nextStyleIDRef = next_ref
        s.langID = "1042"
        s.lockForm = False


# ============================================================
# Section 0 XML
# ============================================================

def _section0_xml_file(section: SectionXMLFile) -> None:
    para = section.add_new_para()
    para.id = "2764991984"
    para.para_pr_id_ref = "0"
    para.style_id_ref = "0"
    para.page_break = False
    para.column_break = False
    para.merged = False

    # Run 1: SecPr + Ctrl(ColPr)
    run1 = para.add_new_run()
    run1.char_pr_id_ref = "0"

    sec_pr = run1.create_sec_pr()
    _sec_pr(sec_pr)

    ctrl = run1.add_new_ctrl()
    col_pr = ctrl.add_new_col_pr()
    col_pr.id = ""
    col_pr.type = MultiColumnType.NEWSPAPER
    col_pr.layout = ColumnDirection.LEFT
    col_pr.col_count = 1
    col_pr.same_sz = True
    col_pr.same_gap = 0

    # Run 2: empty T (separate run, matching reference structure)
    run2 = para.add_new_run()
    run2.char_pr_id_ref = "0"
    run2.add_new_t()

    # LineSegArray for the blank paragraph (reference has this)
    from pyhwpxlib.base import ObjectList
    from pyhwpxlib.objects.section.paragraph import LineSeg
    para.line_seg_array = ObjectList()
    seg = LineSeg(
        textpos=0, vertpos=0, vertsize=1000, textheight=1000,
        baseline=850, spacing=600, horzpos=0, horzsize=42520, flags=393216,
    )
    para.line_seg_array.add(seg)


def _sec_pr(sec_pr) -> None:
    sec_pr.id = ""
    sec_pr.text_direction = TextDirection.HORIZONTAL
    sec_pr.space_columns = 1134
    sec_pr.tab_stop = 8000
    sec_pr.tab_stop_val = 4000
    sec_pr.tab_stop_unit = ValueUnit1.HWPUNIT.value
    sec_pr.outline_shape_id_ref = "1"
    sec_pr.memo_shape_id_ref = "0"
    sec_pr.text_vertical_width_head = False
    sec_pr.master_page_cnt = 0

    # Grid
    grid = sec_pr.create_grid()
    grid.line_grid = 0
    grid.char_grid = 0
    grid.wonggoji_format = False

    # StartNum
    sn = sec_pr.create_start_num()
    sn.page_starts_on = PageStartON.BOTH
    sn.page = 0
    sn.pic = 0
    sn.tbl = 0
    sn.equation = 0

    # Visibility
    vis = sec_pr.create_visibility()
    vis.hide_first_header = False
    vis.hide_first_footer = False
    vis.hide_first_master_page = False
    vis.border = VisibilityOption.SHOW_ALL
    vis.fill = VisibilityOption.SHOW_ALL
    vis.hide_first_page_num = False
    vis.hide_first_empty_line = False
    vis.show_line_number = False

    # LineNumberShape (Java uses Unknown restart type -- use None)
    lns = sec_pr.create_line_number_shape()
    lns.restart_type = 0
    lns.count_by = 0
    lns.distance = 0
    lns.start_number = 0

    # PagePr
    page_pr = sec_pr.create_page_pr()
    page_pr.landscape = PageDirection.WIDELY
    page_pr.width = 59528
    page_pr.height = 84186
    page_pr.gutter_type = GutterMethod.LEFT_ONLY

    margin = page_pr.create_margin()
    margin.header = 4252
    margin.footer = 4252
    margin.gutter = 0
    margin.left = 8504
    margin.right = 8504
    margin.top = 5668
    margin.bottom = 4252

    # FootNotePr
    fn_pr = sec_pr.create_foot_note_pr()
    anf = fn_pr.create_auto_num_format()
    anf.type = NumberType2.DIGIT
    anf.user_char = ""
    anf.prefix_char = ""
    anf.suffix_char = ")"
    anf.supscript = False

    nl = fn_pr.create_note_line()
    nl.length = -1
    nl.type = LineType2.SOLID.str
    nl.width = LineWidth.MM_0_12.str
    nl.color = "#000000"

    ns = fn_pr.create_note_spacing()
    ns.between_notes = 283
    ns.below_line = 567
    ns.above_line = 850

    fn_num = fn_pr.create_numbering()
    fn_num.type = FootNoteNumberingType.CONTINUOUS
    fn_num.new_num = 1

    fn_place = fn_pr.create_placement()
    fn_place.place = FootNotePlace.EACH_COLUMN
    fn_place.beneath_text = False

    # EndNotePr
    en_pr = sec_pr.create_end_note_pr()
    anf2 = en_pr.create_auto_num_format()
    anf2.type = NumberType2.DIGIT
    anf2.user_char = ""
    anf2.prefix_char = ""
    anf2.suffix_char = ")"
    anf2.supscript = False

    nl2 = en_pr.create_note_line()
    nl2.length = 14692344
    nl2.type = LineType2.SOLID.str
    nl2.width = LineWidth.MM_0_12.str
    nl2.color = "#000000"

    ns2 = en_pr.create_note_spacing()
    ns2.between_notes = 0
    ns2.below_line = 567
    ns2.above_line = 850

    en_num = en_pr.create_numbering()
    en_num.type = EndNoteNumberingType.CONTINUOUS
    en_num.new_num = 1

    en_place = en_pr.create_placement()
    en_place.place = EndNotePlace.END_OF_DOCUMENT
    en_place.beneath_text = False

    # PageBorderFill x3 (BOTH, EVEN, ODD)
    for page_type in [ApplyPageType.BOTH, ApplyPageType.EVEN, ApplyPageType.ODD]:
        pbf = sec_pr.add_new_page_border_fill()
        pbf.type = page_type
        pbf.border_fill_id_ref = "1"
        pbf.text_border = PageBorderPositionCriterion.PAPER
        pbf.header_inside = False
        pbf.footer_inside = False
        pbf.fill_area = PageFillArea.PAPER

        offset = pbf.create_offset()
        offset.left = 1417
        offset.right = 1417
        offset.top = 1417
        offset.bottom = 1417
