"""HWP 5.x binary file reader — full format parser based on hwplib Java structure.

Parses the complete HWP 5.x binary format (OLE2 Compound File) including:
- FileHeader (version, flags)
- DocInfo stream (document properties, ID mappings, fonts, char/para shapes, etc.)
- BodyText sections (paragraphs, text, controls, tables, shapes)
- BinData storage (embedded binary data)

Usage:
    from pyhwpxlib.hwp_reader import read_hwp, hwp_to_hwpx, detect_format

    doc = read_hwp("input.hwp")  # returns HWPDocument
    hwp_to_hwpx("input.hwp", "output.hwpx")
"""
from __future__ import annotations

import struct
import zlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

try:
    import olefile
except ImportError:
    olefile = None
    logger.warning("olefile not installed. HWP 5.x reading disabled. pip install olefile")


# ---------------------------------------------------------------------------
# HWP Record Tag IDs (HWPTAG_BEGIN = 16)
# ---------------------------------------------------------------------------
TAG_DOCUMENT_PROPERTIES = 16
TAG_ID_MAPPINGS = 17
TAG_BIN_DATA = 18
TAG_FACE_NAME = 19
TAG_BORDER_FILL = 20
TAG_CHAR_SHAPE = 21
TAG_TAB_DEF = 22
TAG_NUMBERING = 23
TAG_BULLET = 24
TAG_PARA_SHAPE = 25
TAG_STYLE = 26
TAG_MEMO_SHAPE = 92

TAG_PARA_HEADER = 66
TAG_PARA_TEXT = 67
TAG_PARA_CHAR_SHAPE = 68
TAG_PARA_LINE_SEG = 69
TAG_CTRL_HEADER = 71
TAG_LIST_HEADER = 72
TAG_PAGE_DEF = 73
TAG_FOOTNOTE_SHAPE = 74
TAG_PAGE_BORDER_FILL = 75
TAG_SHAPE_COMPONENT = 76
TAG_TABLE = 77
TAG_SHAPE_COMPONENT_LINE = 78
TAG_SHAPE_COMPONENT_RECTANGLE = 79
TAG_SHAPE_COMPONENT_ELLIPSE = 80
TAG_SHAPE_COMPONENT_ARC = 81
TAG_SHAPE_COMPONENT_POLYGON = 82
TAG_SHAPE_COMPONENT_CURVE = 83
TAG_SHAPE_COMPONENT_OLE = 84
TAG_SHAPE_COMPONENT_PICTURE = 85
TAG_SHAPE_COMPONENT_CONTAINER = 86
TAG_CTRL_DATA = 87
TAG_SHAPE_COMPONENT_EQUATION = 88
TAG_SHAPE_COMPONENT_TEXTART = 90
TAG_FORM_OBJECT = 91

# Control character classifications
CONTROL_EXTEND_CODES = {1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23}
CONTROL_INLINE_CODES = {4, 5, 6, 7, 8, 9, 19, 20}
CONTROL_CHAR_CODES = {0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31}

# Alignment names
ALIGN_NAMES = {
    0: 'JUSTIFY', 1: 'LEFT', 2: 'RIGHT', 3: 'CENTER',
    4: 'DISTRIBUTE', 5: 'DISTRIBUTE_SPACE',
}

# Language indices for 7-language arrays
LANG_HANGUL = 0
LANG_LATIN = 1
LANG_HANJA = 2
LANG_JAPANESE = 3
LANG_OTHER = 4
LANG_SYMBOL = 5
LANG_USER = 6
LANG_NAMES = ['HANGUL', 'LATIN', 'HANJA', 'JAPANESE', 'OTHER', 'SYMBOL', 'USER']


# ---------------------------------------------------------------------------
# Data classes — rich HWPDocument hierarchy
# ---------------------------------------------------------------------------

@dataclass
class FileHeaderInfo:
    """Parsed file header information."""
    signature: bytes
    version_raw: int
    version_str: str
    properties: int
    compressed: bool
    encrypted: bool
    distribution: bool
    script: bool
    drm: bool
    has_xml_template: bool
    has_history: bool
    has_sign: bool
    certificate_encrypt: bool
    prepare_signature: bool
    certificate_drm: bool
    ccl: bool


@dataclass
class DocumentProperties:
    """DOCUMENT_PROPERTIES (tag 16) data."""
    section_count: int = 1
    begin_number_page: int = 1
    begin_number_footnote: int = 1
    begin_number_endnote: int = 1
    begin_number_picture: int = 1
    begin_number_table: int = 1
    begin_number_equation: int = 1
    caret_section: int = 0
    caret_paragraph: int = 0
    caret_position: int = 0


@dataclass
class BinDataInfo:
    """BIN_DATA (tag 18) info."""
    bin_data_type: int = 0  # LINK=0, EMBEDDING=1, STORAGE=2
    abs_path: str = ''
    rel_path: str = ''
    bin_data_id: int = 0
    extension: str = ''


@dataclass
class FaceNameInfo:
    """FACE_NAME (tag 19) font definition."""
    property_flag: int = 0
    name: str = ''
    alternative_name: str = ''
    font_type_info: Optional[bytes] = None
    default_name: str = ''
    lang_index: int = -1  # which language group this font belongs to


@dataclass
class BorderInfo:
    """Single border edge."""
    border_type: int = 0
    width: int = 0
    color: int = 0


@dataclass
class FillInfo:
    """Fill information for BorderFill."""
    fill_type: int = 0
    # Pattern fill
    pattern_color: int = 0
    pattern_bg_color: int = 0
    pattern_type: int = 0
    # Gradient fill
    gradient_type: int = 0
    gradient_angle: int = 0
    gradient_cx: int = 0
    gradient_cy: int = 0
    gradient_step: int = 0
    gradient_colors: List[int] = field(default_factory=list)
    # Image fill
    image_fill_type: int = 0
    image_bin_item: int = 0
    image_brightness: int = 0
    image_contrast: int = 0
    image_effect: int = 0


@dataclass
class BorderFillInfo:
    """BORDER_FILL (tag 20) definition."""
    property: int = 0
    left_border: BorderInfo = field(default_factory=BorderInfo)
    right_border: BorderInfo = field(default_factory=BorderInfo)
    top_border: BorderInfo = field(default_factory=BorderInfo)
    bottom_border: BorderInfo = field(default_factory=BorderInfo)
    diagonal_border: BorderInfo = field(default_factory=BorderInfo)
    fill: FillInfo = field(default_factory=FillInfo)


@dataclass
class CharShapeInfo:
    """CHAR_SHAPE (tag 21) — full 7-language character shape."""
    font_ids: List[int] = field(default_factory=lambda: [0] * 7)
    ratios: List[int] = field(default_factory=lambda: [100] * 7)
    spacings: List[int] = field(default_factory=lambda: [0] * 7)
    relative_sizes: List[int] = field(default_factory=lambda: [100] * 7)
    offsets: List[int] = field(default_factory=lambda: [0] * 7)
    base_size: int = 1000  # in hundredths of a point
    prop_bits: int = 0  # bit flags: bold, italic, underline, etc.
    shadow_gap1: int = 0
    shadow_gap2: int = 0
    char_color: int = 0
    underline_color: int = 0
    shade_color: int = 0xFFFFFFFF
    shadow_color: int = 0x00B2B2B2
    border_fill_id: int = 0
    strikeout_color: int = 0

    @property
    def is_bold(self) -> bool:
        return bool(self.prop_bits & 0x01)

    @property
    def is_italic(self) -> bool:
        return bool(self.prop_bits & 0x02)

    @property
    def underline_type(self) -> int:
        return (self.prop_bits >> 2) & 0x07

    @property
    def has_underline(self) -> bool:
        return self.underline_type != 0

    @property
    def outline_type(self) -> int:
        return (self.prop_bits >> 5) & 0x07

    @property
    def shadow_type(self) -> int:
        return (self.prop_bits >> 8) & 0x03

    @property
    def is_superscript(self) -> bool:
        return ((self.prop_bits >> 15) & 0x03) == 1

    @property
    def is_subscript(self) -> bool:
        return ((self.prop_bits >> 15) & 0x03) == 2

    @property
    def strikeout_type(self) -> int:
        return (self.prop_bits >> 18) & 0x07

    @property
    def has_strikeout(self) -> bool:
        return self.strikeout_type != 0

    @property
    def char_color_rgb(self) -> str:
        r = self.char_color & 0xFF
        g = (self.char_color >> 8) & 0xFF
        b = (self.char_color >> 16) & 0xFF
        return f'#{r:02X}{g:02X}{b:02X}'

    @property
    def height_pt(self) -> float:
        """Font size in points."""
        return self.base_size / 100.0


@dataclass
class TabItem:
    """Single tab stop."""
    position: int = 0
    tab_type: int = 0
    fill_type: int = 0


@dataclass
class TabDefInfo:
    """TAB_DEF (tag 22) definition."""
    property: int = 0
    tab_items: List[TabItem] = field(default_factory=list)


@dataclass
class NumberingLevelInfo:
    """Single numbering level."""
    format_type: int = 0
    format_string: str = ''


@dataclass
class NumberingInfo:
    """NUMBERING (tag 23) definition — 7 levels."""
    levels: List[NumberingLevelInfo] = field(default_factory=list)
    start_number: int = 1


@dataclass
class BulletInfo:
    """BULLET (tag 24) definition."""
    bullet_char: str = ''
    image_bullet: bool = False
    image_id: int = 0


@dataclass
class ParaShapeInfo:
    """PARA_SHAPE (tag 25) — full paragraph shape."""
    property1: int = 0
    property2: int = 0
    left_margin: int = 0
    right_margin: int = 0
    indent: int = 0
    space_before: int = 0
    space_after: int = 0
    line_spacing_type: int = 0
    line_spacing_value: int = 160
    tab_def_id: int = 0
    heading_type: int = 0
    heading_id_ref: int = 0
    heading_level: int = 0
    border_fill_id: int = 0
    border_offset_left: int = 0
    border_offset_right: int = 0
    border_offset_top: int = 0
    border_offset_bottom: int = 0
    property3: int = 0
    line_wrap: int = 0

    @property
    def alignment(self) -> str:
        return ALIGN_NAMES.get(self.property1 & 0x07, 'JUSTIFY')

    @property
    def break_latin_word(self) -> int:
        return (self.property1 >> 4) & 0x03

    @property
    def snap_to_grid(self) -> bool:
        return bool(self.property1 & (1 << 18))

    @property
    def widow_orphan(self) -> bool:
        return bool(self.property1 & (1 << 20))

    @property
    def keep_with_next(self) -> bool:
        return bool(self.property1 & (1 << 21))

    @property
    def page_break_before(self) -> bool:
        return bool(self.property1 & (1 << 24))


@dataclass
class StyleInfo:
    """STYLE (tag 26) definition."""
    name: str = ''
    english_name: str = ''
    style_type: int = 0
    next_style_id: int = 0
    lang_id: int = 0
    para_shape_id: int = 0
    char_shape_id: int = 0
    lock_form: int = 0


@dataclass
class MemoShapeInfo:
    """MEMO_SHAPE (tag 92) definition."""
    memo_type: int = 0
    line_width: int = 0
    line_color: int = 0
    fill_color: int = 0
    active_color: int = 0
    memo_list_count: int = 0


# ---------------------------------------------------------------------------
# BodyText data classes
# ---------------------------------------------------------------------------

@dataclass
class HWPCharNormal:
    """Normal printable character."""
    char_type: str = 'normal'
    code: int = 0
    char: str = ''


@dataclass
class HWPCharControl:
    """Control character (0, 10, 13, 24-31) — 2 bytes."""
    char_type: str = 'control'
    code: int = 0


@dataclass
class HWPCharInline:
    """Inline control (4-9, 19-20) — 16 bytes total."""
    char_type: str = 'inline'
    code: int = 0
    addition: bytes = b''


@dataclass
class HWPCharExtend:
    """Extended control (1-3, 11-12, 14-18, 21-23) — 16 bytes total."""
    char_type: str = 'extend'
    code: int = 0
    addition: bytes = b''  # 12-byte addition data


@dataclass
class LineSegInfo:
    """PARA_LINE_SEG (tag 69) line segment."""
    text_start: int = 0
    line_vertical: int = 0
    line_height: int = 0
    text_height: int = 0
    baseline_distance: int = 0
    line_spacing: int = 0
    column_start: int = 0
    segment_width: int = 0
    tag: int = 0


@dataclass
class ControlInfo:
    """Parsed control from CTRL_HEADER (tag 71)."""
    ctrl_id: str = ''  # 4-char ASCII like 'tbl ', 'gso ', 'secd', etc.
    property: int = 0
    raw_data: bytes = b''
    sub_data: Dict[str, Any] = field(default_factory=dict)
    children: List[Any] = field(default_factory=list)


@dataclass
class TableInfo:
    """TABLE (tag 77) definition."""
    row_count: int = 0
    col_count: int = 0
    cell_spacing: int = 0
    margin_left: int = 0
    margin_right: int = 0
    margin_top: int = 0
    margin_bottom: int = 0
    border_fill_id: int = 0
    zone_info: List[int] = field(default_factory=list)
    cells: List['CellInfo'] = field(default_factory=list)


@dataclass
class CellInfo:
    """Cell info from LIST_HEADER in table context."""
    para_count: int = 0
    property: int = 0
    col_index: int = 0
    row_index: int = 0
    col_span: int = 1
    row_span: int = 1
    width: int = 0
    height: int = 0
    margin_left: int = 0
    margin_right: int = 0
    margin_top: int = 0
    margin_bottom: int = 0
    border_fill_id: int = 0
    paragraphs: List['ParagraphData'] = field(default_factory=list)


@dataclass
class ShapeComponentInfo:
    """SHAPE_COMPONENT (tag 76) data."""
    gso_id: str = ''
    x_offset: int = 0
    y_offset: int = 0
    width: int = 0
    height: int = 0
    rotation: int = 0
    x_scale: int = 0
    y_scale: int = 0
    render_info: bytes = b''
    shape_type: str = ''
    shape_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParagraphData:
    """A single parsed paragraph."""
    instance_id: int = 0
    para_shape_id: int = 0
    style_id: int = 0
    divide_sort: int = 0
    char_count: int = 0
    control_mask: int = 0
    chars: List[Union[HWPCharNormal, HWPCharControl, HWPCharInline, HWPCharExtend]] = field(
        default_factory=list
    )
    char_shape_pairs: List[Tuple[int, int]] = field(default_factory=list)
    line_segs: List[LineSegInfo] = field(default_factory=list)
    controls: List[ControlInfo] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Extract plain text from chars."""
        parts = []
        for c in self.chars:
            if isinstance(c, HWPCharNormal):
                parts.append(c.char)
            elif isinstance(c, HWPCharControl) and c.code == 10:
                parts.append('\n')
        return ''.join(parts).strip()


@dataclass
class SectionData:
    """One section of the document body."""
    paragraphs: List[ParagraphData] = field(default_factory=list)


@dataclass
class DocInfoData:
    """All data parsed from the DocInfo stream."""
    document_properties: DocumentProperties = field(default_factory=DocumentProperties)
    id_mappings: dict = field(default_factory=dict)
    bin_data_list: List[BinDataInfo] = field(default_factory=list)
    face_names: List[FaceNameInfo] = field(default_factory=list)
    font_counts: dict = field(default_factory=dict)
    border_fills: List[BorderFillInfo] = field(default_factory=list)
    char_shapes: List[CharShapeInfo] = field(default_factory=list)
    tab_defs: List[TabDefInfo] = field(default_factory=list)
    numberings: List[NumberingInfo] = field(default_factory=list)
    bullets: List[BulletInfo] = field(default_factory=list)
    para_shapes: List[ParaShapeInfo] = field(default_factory=list)
    styles: List[StyleInfo] = field(default_factory=list)
    memo_shapes: List[MemoShapeInfo] = field(default_factory=list)


@dataclass
class HWPDocument:
    """Top-level document structure returned by read_hwp()."""
    version: str = ''
    compressed: bool = False
    encrypted: bool = False
    file_header: FileHeaderInfo = field(default_factory=lambda: FileHeaderInfo(
        signature=b'', version_raw=0, version_str='', properties=0,
        compressed=False, encrypted=False, distribution=False, script=False,
        drm=False, has_xml_template=False, has_history=False, has_sign=False,
        certificate_encrypt=False, prepare_signature=False, certificate_drm=False,
        ccl=False,
    ))
    doc_info: DocInfoData = field(default_factory=DocInfoData)
    sections: List[SectionData] = field(default_factory=list)
    bin_data_entries: Dict[int, bytes] = field(default_factory=dict)

    # Legacy compat helpers
    @property
    def texts(self) -> List[str]:
        result = []
        for sec in self.sections:
            for para in sec.paragraphs:
                t = para.text
                if t:
                    result.append(t)
        return result

    @property
    def face_names(self) -> List[str]:
        return [fn.name for fn in self.doc_info.face_names]


# ---------------------------------------------------------------------------
# Record parsing helpers
# ---------------------------------------------------------------------------

@dataclass
class HWPRecord:
    """A single HWP binary record."""
    tag_id: int
    level: int
    size: int
    data: bytes
    offset: int = 0  # byte offset in stream


def _parse_records(data: bytes) -> List[HWPRecord]:
    """Parse raw binary data into a list of HWP records."""
    records: List[HWPRecord] = []
    pos = 0
    while pos + 4 <= len(data):
        rec_offset = pos
        header = struct.unpack_from('<I', data, pos)[0]
        tag_id = header & 0x3FF
        level = (header >> 10) & 0x3FF
        size = (header >> 20) & 0xFFF
        pos += 4
        if size == 0xFFF:
            if pos + 4 > len(data):
                break
            size = struct.unpack_from('<I', data, pos)[0]
            pos += 4
        if pos + size > len(data):
            break
        records.append(HWPRecord(
            tag_id=tag_id, level=level, size=size,
            data=data[pos:pos + size], offset=rec_offset,
        ))
        pos += size
    return records


def _decompress_stream(ole, stream_name: str, compressed: bool) -> bytes:
    """Read and optionally decompress an OLE stream."""
    raw = ole.openstream(stream_name).read()
    if not compressed:
        return raw
    try:
        return zlib.decompress(raw, -15)
    except zlib.error:
        try:
            return zlib.decompress(raw)
        except zlib.error:
            logger.warning("Failed to decompress stream %s, using raw data", stream_name)
            return raw


def _read_uint8(data: bytes, pos: int) -> Tuple[int, int]:
    if pos + 1 > len(data):
        return 0, pos
    return data[pos], pos + 1


def _read_int8(data: bytes, pos: int) -> Tuple[int, int]:
    if pos + 1 > len(data):
        return 0, pos
    return struct.unpack_from('<b', data, pos)[0], pos + 1


def _read_uint16(data: bytes, pos: int) -> Tuple[int, int]:
    if pos + 2 > len(data):
        return 0, pos
    return struct.unpack_from('<H', data, pos)[0], pos + 2


def _read_int16(data: bytes, pos: int) -> Tuple[int, int]:
    if pos + 2 > len(data):
        return 0, pos
    return struct.unpack_from('<h', data, pos)[0], pos + 2


def _read_uint32(data: bytes, pos: int) -> Tuple[int, int]:
    if pos + 4 > len(data):
        return 0, pos
    return struct.unpack_from('<I', data, pos)[0], pos + 4


def _read_int32(data: bytes, pos: int) -> Tuple[int, int]:
    if pos + 4 > len(data):
        return 0, pos
    return struct.unpack_from('<i', data, pos)[0], pos + 4


def _read_hwp_string(data: bytes, pos: int) -> Tuple[str, int]:
    """Read a length-prefixed UTF-16LE string (2-byte length count of wchars)."""
    if pos + 2 > len(data):
        return '', pos
    name_len = struct.unpack_from('<H', data, pos)[0]
    pos += 2
    byte_len = name_len * 2
    if pos + byte_len > len(data):
        s = data[pos:].decode('utf-16-le', errors='replace')
        return s, len(data)
    s = data[pos:pos + byte_len].decode('utf-16-le', errors='replace')
    return s, pos + byte_len


def _read_bytes(data: bytes, pos: int, count: int) -> Tuple[bytes, int]:
    end = min(pos + count, len(data))
    return data[pos:end], end


# ---------------------------------------------------------------------------
# FileHeader parser
# ---------------------------------------------------------------------------

def _parse_file_header(ole) -> FileHeaderInfo:
    """Parse the FileHeader stream."""
    fh = ole.openstream('FileHeader').read()
    signature = fh[:32]
    version_raw = struct.unpack_from('<I', fh, 32)[0]
    props = struct.unpack_from('<I', fh, 36)[0]

    major = (version_raw >> 24) & 0xFF
    minor = (version_raw >> 16) & 0xFF
    build = (version_raw >> 8) & 0xFF
    revision = version_raw & 0xFF
    version_str = f"{major}.{minor}.{build}.{revision}"

    return FileHeaderInfo(
        signature=signature,
        version_raw=version_raw,
        version_str=version_str,
        properties=props,
        compressed=bool(props & 0x01),
        encrypted=bool(props & 0x02),
        distribution=bool(props & 0x04),
        script=bool(props & 0x08),
        drm=bool(props & 0x10),
        has_xml_template=bool(props & 0x20),
        has_history=bool(props & 0x40),
        has_sign=bool(props & 0x80),
        certificate_encrypt=bool(props & 0x100),
        prepare_signature=bool(props & 0x200),
        certificate_drm=bool(props & 0x400),
        ccl=bool(props & 0x800),
    )


# ---------------------------------------------------------------------------
# DocInfo parsers
# ---------------------------------------------------------------------------

def _parse_document_properties(data: bytes) -> DocumentProperties:
    """Parse DOCUMENT_PROPERTIES (tag 16)."""
    dp = DocumentProperties()
    pos = 0
    dp.section_count, pos = _read_uint16(data, pos)
    dp.begin_number_page, pos = _read_uint16(data, pos)
    dp.begin_number_footnote, pos = _read_uint16(data, pos)
    dp.begin_number_endnote, pos = _read_uint16(data, pos)
    dp.begin_number_picture, pos = _read_uint16(data, pos)
    dp.begin_number_table, pos = _read_uint16(data, pos)
    dp.begin_number_equation, pos = _read_uint16(data, pos)
    if pos + 4 <= len(data):
        dp.caret_section, pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        dp.caret_paragraph, pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        dp.caret_position, pos = _read_uint32(data, pos)
    return dp


def _parse_id_mappings(data: bytes) -> dict:
    """Parse ID_MAPPINGS (tag 17) — counts for all object types."""
    mapping_names = [
        'binData', 'hangulFont', 'englishFont', 'hanjaFont', 'japaneseFont',
        'etcFont', 'symbolFont', 'userFont', 'borderFill', 'charShape',
        'tabDef', 'numbering', 'bullet', 'paraShape', 'style', 'memoShape',
    ]
    result = {}
    for i, name in enumerate(mapping_names):
        off = i * 4
        if off + 4 <= len(data):
            result[name] = struct.unpack_from('<I', data, off)[0]
        else:
            result[name] = 0
    return result


def _parse_bin_data(data: bytes, bin_data_counter: int) -> BinDataInfo:
    """Parse BIN_DATA (tag 18)."""
    info = BinDataInfo()
    pos = 0
    if pos + 2 > len(data):
        return info

    prop, pos = _read_uint16(data, pos)
    info.bin_data_type = prop & 0x0F
    info.bin_data_id = bin_data_counter

    if info.bin_data_type == 0:  # LINK
        info.abs_path, pos = _read_hwp_string(data, pos)
        info.rel_path, pos = _read_hwp_string(data, pos)
    elif info.bin_data_type == 1:  # EMBEDDING
        # binDataID as stored in the stream name (BIN0001.xxx)
        if pos + 2 <= len(data):
            stored_id, pos = _read_uint16(data, pos)
            info.bin_data_id = stored_id
        info.extension, pos = _read_hwp_string(data, pos)
    elif info.bin_data_type == 2:  # STORAGE
        if pos + 2 <= len(data):
            stored_id, pos = _read_uint16(data, pos)
            info.bin_data_id = stored_id
        info.extension, pos = _read_hwp_string(data, pos)

    return info


def _parse_face_name(data: bytes) -> FaceNameInfo:
    """Parse FACE_NAME (tag 19)."""
    info = FaceNameInfo()
    pos = 0
    if len(data) < 3:
        return info

    info.property_flag, pos = _read_uint8(data, pos)
    has_alternative = bool(info.property_flag & 0x80)
    has_font_type = bool(info.property_flag & 0x40)
    has_default = bool(info.property_flag & 0x20)

    info.name, pos = _read_hwp_string(data, pos)

    if has_alternative:
        info.alternative_name, pos = _read_hwp_string(data, pos)

    if has_font_type:
        # Font type info is 10 bytes
        if pos + 10 <= len(data):
            info.font_type_info = data[pos:pos + 10]
            pos += 10

    if has_default:
        info.default_name, pos = _read_hwp_string(data, pos)

    return info


def _parse_border(data: bytes, pos: int) -> Tuple[BorderInfo, int]:
    """Parse a single border (type, width, color) = 1+1+4 = 6 bytes."""
    border = BorderInfo()
    if pos + 6 > len(data):
        return border, pos
    border.border_type, pos = _read_uint8(data, pos)
    border.width, pos = _read_uint8(data, pos)
    border.color, pos = _read_uint32(data, pos)
    return border, pos


def _parse_border_fill(data: bytes) -> BorderFillInfo:
    """Parse BORDER_FILL (tag 20)."""
    info = BorderFillInfo()
    pos = 0
    if len(data) < 2:
        return info

    info.property, pos = _read_uint16(data, pos)

    # 4 borders: left, right, top, bottom
    info.left_border, pos = _parse_border(data, pos)
    info.right_border, pos = _parse_border(data, pos)
    info.top_border, pos = _parse_border(data, pos)
    info.bottom_border, pos = _parse_border(data, pos)
    # diagonal
    info.diagonal_border, pos = _parse_border(data, pos)

    # Fill info
    if pos + 4 <= len(data):
        fill_type, pos = _read_uint32(data, pos)
        info.fill.fill_type = fill_type

        # Pattern fill (if bit 0 set)
        if fill_type & 0x01:
            if pos + 4 <= len(data):
                info.fill.pattern_color, pos = _read_uint32(data, pos)
            if pos + 4 <= len(data):
                info.fill.pattern_bg_color, pos = _read_uint32(data, pos)
            if pos + 4 <= len(data):
                info.fill.pattern_type, pos = _read_uint32(data, pos)

        # Gradient fill (if bit 2 set)
        if fill_type & 0x04:
            if pos + 1 <= len(data):
                info.fill.gradient_type, pos = _read_uint8(data, pos)
            if pos + 4 <= len(data):
                info.fill.gradient_angle, pos = _read_int32(data, pos)
            if pos + 4 <= len(data):
                info.fill.gradient_cx, pos = _read_int32(data, pos)
            if pos + 4 <= len(data):
                info.fill.gradient_cy, pos = _read_int32(data, pos)
            if pos + 4 <= len(data):
                info.fill.gradient_step, pos = _read_uint32(data, pos)
            # Color count
            if pos + 4 <= len(data):
                color_count, pos = _read_uint32(data, pos)
                for _ in range(min(color_count, 256)):
                    if pos + 4 <= len(data):
                        c, pos = _read_uint32(data, pos)
                        info.fill.gradient_colors.append(c)

        # Image fill (if bit 1 set)
        if fill_type & 0x02:
            if pos + 1 <= len(data):
                info.fill.image_fill_type, pos = _read_uint8(data, pos)
            if pos + 4 <= len(data):
                info.fill.image_bin_item, pos = _read_uint32(data, pos)
            if pos + 1 <= len(data):
                info.fill.image_brightness, pos = _read_uint8(data, pos)
            if pos + 1 <= len(data):
                info.fill.image_contrast, pos = _read_uint8(data, pos)
            if pos + 1 <= len(data):
                info.fill.image_effect, pos = _read_uint8(data, pos)

    return info


def _parse_char_shape(data: bytes) -> CharShapeInfo:
    """Parse CHAR_SHAPE (tag 21) — full 7-language arrays."""
    info = CharShapeInfo()
    pos = 0

    # 7 font IDs (WORD each = 14 bytes)
    font_ids = []
    for _ in range(7):
        v, pos = _read_uint16(data, pos)
        font_ids.append(v)
    info.font_ids = font_ids

    # 7 ratios (BYTE each = 7 bytes)
    ratios = []
    for _ in range(7):
        v, pos = _read_uint8(data, pos)
        ratios.append(v)
    info.ratios = ratios

    # 7 spacings (INT8 each = 7 bytes)
    spacings = []
    for _ in range(7):
        v, pos = _read_int8(data, pos)
        spacings.append(v)
    info.spacings = spacings

    # 7 relative sizes (BYTE each = 7 bytes)
    rel_sizes = []
    for _ in range(7):
        v, pos = _read_uint8(data, pos)
        rel_sizes.append(v)
    info.relative_sizes = rel_sizes

    # 7 offsets (INT8 each = 7 bytes)
    offsets = []
    for _ in range(7):
        v, pos = _read_int8(data, pos)
        offsets.append(v)
    info.offsets = offsets

    # base size (DWORD, 4 bytes) — at offset 42
    if pos + 4 <= len(data):
        info.base_size, pos = _read_int32(data, pos)

    # property bits (DWORD, 4 bytes) — at offset 46
    if pos + 4 <= len(data):
        info.prop_bits, pos = _read_uint32(data, pos)

    # shadow gap 1 (INT8, 1 byte)
    if pos + 1 <= len(data):
        info.shadow_gap1, pos = _read_int8(data, pos)

    # shadow gap 2 (INT8, 1 byte)
    if pos + 1 <= len(data):
        info.shadow_gap2, pos = _read_int8(data, pos)

    # char color (DWORD, 4 bytes)
    if pos + 4 <= len(data):
        info.char_color, pos = _read_uint32(data, pos)

    # underline color (DWORD, 4 bytes)
    if pos + 4 <= len(data):
        info.underline_color, pos = _read_uint32(data, pos)

    # shade color (DWORD, 4 bytes)
    if pos + 4 <= len(data):
        info.shade_color, pos = _read_uint32(data, pos)

    # shadow color (DWORD, 4 bytes)
    if pos + 4 <= len(data):
        info.shadow_color, pos = _read_uint32(data, pos)

    # border fill id (WORD, 2 bytes) — version >= 5.0.2.1
    if pos + 2 <= len(data):
        info.border_fill_id, pos = _read_uint16(data, pos)

    # strikeout color (DWORD, 4 bytes) — version >= 5.0.3.0
    if pos + 4 <= len(data):
        info.strikeout_color, pos = _read_uint32(data, pos)

    return info


def _parse_tab_def(data: bytes) -> TabDefInfo:
    """Parse TAB_DEF (tag 22)."""
    info = TabDefInfo()
    pos = 0
    if pos + 4 <= len(data):
        info.property, pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        count, pos = _read_uint32(data, pos)
        for _ in range(min(count, 1024)):
            item = TabItem()
            if pos + 4 <= len(data):
                item.position, pos = _read_uint32(data, pos)
            if pos + 1 <= len(data):
                item.tab_type, pos = _read_uint8(data, pos)
            if pos + 1 <= len(data):
                item.fill_type, pos = _read_uint8(data, pos)
            # 2 bytes reserved
            pos += 2
            info.tab_items.append(item)
    return info


def _parse_numbering(data: bytes) -> NumberingInfo:
    """Parse NUMBERING (tag 23) — 7 levels."""
    info = NumberingInfo()
    pos = 0
    for _ in range(7):
        lvl = NumberingLevelInfo()
        if pos + 4 > len(data):
            break
        lvl.format_type, pos = _read_uint32(data, pos)
        lvl.format_string, pos = _read_hwp_string(data, pos)
        info.levels.append(lvl)
    if pos + 2 <= len(data):
        info.start_number, pos = _read_uint16(data, pos)
    return info


def _parse_bullet(data: bytes) -> BulletInfo:
    """Parse BULLET (tag 24)."""
    info = BulletInfo()
    pos = 0
    if len(data) < 2:
        return info
    # bullet char
    ch, pos = _read_uint16(data, pos)
    info.bullet_char = chr(ch) if ch > 0 else ''
    # We skip additional image bullet parsing for brevity;
    # the data is rarely used and varies by version.
    return info


def _parse_para_shape(data: bytes) -> ParaShapeInfo:
    """Parse PARA_SHAPE (tag 25) — full paragraph shape."""
    info = ParaShapeInfo()
    pos = 0

    # property1 (DWORD)
    if pos + 4 <= len(data):
        info.property1, pos = _read_uint32(data, pos)

    # left margin (INT32)
    if pos + 4 <= len(data):
        info.left_margin, pos = _read_int32(data, pos)

    # right margin (INT32)
    if pos + 4 <= len(data):
        info.right_margin, pos = _read_int32(data, pos)

    # indent (INT32)
    if pos + 4 <= len(data):
        info.indent, pos = _read_int32(data, pos)

    # space before (INT32)
    if pos + 4 <= len(data):
        info.space_before, pos = _read_int32(data, pos)

    # space after (INT32)
    if pos + 4 <= len(data):
        info.space_after, pos = _read_int32(data, pos)

    # line spacing type + value: type as byte in property1 bits[25:26], value here
    if pos + 4 <= len(data):
        info.line_spacing_value, pos = _read_int32(data, pos)

    # tab def ID (WORD)
    if pos + 2 <= len(data):
        info.tab_def_id, pos = _read_uint16(data, pos)

    # heading: numbering/bullet ID ref (WORD)
    if pos + 2 <= len(data):
        info.heading_id_ref, pos = _read_uint16(data, pos)

    # border fill ID (WORD)
    if pos + 2 <= len(data):
        info.border_fill_id, pos = _read_uint16(data, pos)

    # border offsets (INT16 each)
    if pos + 2 <= len(data):
        info.border_offset_left, pos = _read_int16(data, pos)
    if pos + 2 <= len(data):
        info.border_offset_right, pos = _read_int16(data, pos)
    if pos + 2 <= len(data):
        info.border_offset_top, pos = _read_int16(data, pos)
    if pos + 2 <= len(data):
        info.border_offset_bottom, pos = _read_int16(data, pos)

    # property2 (DWORD) — version >= 5.0.1.7
    if pos + 4 <= len(data):
        info.property2, pos = _read_uint32(data, pos)

    # property3 (DWORD) — version >= 5.0.2.5
    if pos + 4 <= len(data):
        info.property3, pos = _read_uint32(data, pos)

    # line spacing type
    info.line_spacing_type = (info.property1 >> 25) & 0x03

    # heading type/level from property1
    info.heading_type = (info.property1 >> 6) & 0x03
    info.heading_level = (info.property1 >> 8) & 0x07

    return info


def _parse_style(data: bytes) -> StyleInfo:
    """Parse STYLE (tag 26)."""
    info = StyleInfo()
    pos = 0
    info.name, pos = _read_hwp_string(data, pos)
    info.english_name, pos = _read_hwp_string(data, pos)
    if pos + 1 <= len(data):
        info.style_type, pos = _read_uint8(data, pos)
    if pos + 1 <= len(data):
        info.next_style_id, pos = _read_uint8(data, pos)
    if pos + 2 <= len(data):
        info.lang_id, pos = _read_int16(data, pos)
    if pos + 2 <= len(data):
        info.para_shape_id, pos = _read_uint16(data, pos)
    if pos + 2 <= len(data):
        info.char_shape_id, pos = _read_uint16(data, pos)
    if pos + 2 <= len(data):
        info.lock_form, pos = _read_uint16(data, pos)
    return info


def _parse_memo_shape(data: bytes) -> MemoShapeInfo:
    """Parse MEMO_SHAPE (tag 92)."""
    info = MemoShapeInfo()
    pos = 0
    if pos + 4 <= len(data):
        info.memo_type, pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        info.line_width, pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        info.line_color, pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        info.fill_color, pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        info.active_color, pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        info.memo_list_count, pos = _read_uint32(data, pos)
    return info


def _parse_docinfo(ole, compressed: bool) -> DocInfoData:
    """Parse the entire DocInfo stream."""
    data = _decompress_stream(ole, 'DocInfo', compressed)
    records = _parse_records(data)

    doc_info = DocInfoData()
    bin_data_counter = 1
    current_face_name_lang = 0
    face_name_counts_per_lang = [0] * 7
    id_mappings_parsed = False

    for rec in records:
        tag = rec.tag_id
        d = rec.data

        if tag == TAG_DOCUMENT_PROPERTIES:
            doc_info.document_properties = _parse_document_properties(d)

        elif tag == TAG_ID_MAPPINGS:
            doc_info.id_mappings = _parse_id_mappings(d)
            doc_info.font_counts = {
                'binData': doc_info.id_mappings.get('binData', 0),
                'hangulFont': doc_info.id_mappings.get('hangulFont', 0),
                'englishFont': doc_info.id_mappings.get('englishFont', 0),
                'hanjaFont': doc_info.id_mappings.get('hanjaFont', 0),
                'japaneseFont': doc_info.id_mappings.get('japaneseFont', 0),
                'etcFont': doc_info.id_mappings.get('etcFont', 0),
                'symbolFont': doc_info.id_mappings.get('symbolFont', 0),
                'userFont': doc_info.id_mappings.get('userFont', 0),
            }
            id_mappings_parsed = True
            # Set up font counting to track which language each face_name belongs to
            face_name_counts_per_lang = [
                doc_info.id_mappings.get('hangulFont', 0),
                doc_info.id_mappings.get('englishFont', 0),
                doc_info.id_mappings.get('hanjaFont', 0),
                doc_info.id_mappings.get('japaneseFont', 0),
                doc_info.id_mappings.get('etcFont', 0),
                doc_info.id_mappings.get('symbolFont', 0),
                doc_info.id_mappings.get('userFont', 0),
            ]
            current_face_name_lang = 0

        elif tag == TAG_BIN_DATA:
            bd = _parse_bin_data(d, bin_data_counter)
            doc_info.bin_data_list.append(bd)
            bin_data_counter += 1

        elif tag == TAG_FACE_NAME:
            fn = _parse_face_name(d)
            # Determine which language group this font belongs to
            if id_mappings_parsed:
                while (current_face_name_lang < 7
                       and face_name_counts_per_lang[current_face_name_lang] <= 0):
                    current_face_name_lang += 1
                if current_face_name_lang < 7:
                    fn.lang_index = current_face_name_lang
                    face_name_counts_per_lang[current_face_name_lang] -= 1
            doc_info.face_names.append(fn)

        elif tag == TAG_BORDER_FILL:
            doc_info.border_fills.append(_parse_border_fill(d))

        elif tag == TAG_CHAR_SHAPE:
            doc_info.char_shapes.append(_parse_char_shape(d))

        elif tag == TAG_TAB_DEF:
            doc_info.tab_defs.append(_parse_tab_def(d))

        elif tag == TAG_NUMBERING:
            doc_info.numberings.append(_parse_numbering(d))

        elif tag == TAG_BULLET:
            doc_info.bullets.append(_parse_bullet(d))

        elif tag == TAG_PARA_SHAPE:
            doc_info.para_shapes.append(_parse_para_shape(d))

        elif tag == TAG_STYLE:
            doc_info.styles.append(_parse_style(d))

        elif tag == TAG_MEMO_SHAPE:
            doc_info.memo_shapes.append(_parse_memo_shape(d))

    return doc_info


# ---------------------------------------------------------------------------
# BodyText / Section parsers
# ---------------------------------------------------------------------------

def _parse_para_text(data: bytes) -> List[Union[HWPCharNormal, HWPCharControl, HWPCharInline, HWPCharExtend]]:
    """Parse PARA_TEXT (tag 67) character by character.

    Control code classification:
    - Normal chars (>31): 2 bytes each (UTF-16LE)
    - ControlExtend (1,2,3,11,12,14,15,16,17,18,21,22,23): 16 bytes each
      (2-byte code + 12-byte addition + 2-byte trailing)
    - ControlInline (4,5,6,7,8,9,19,20): 16 bytes each
    - ControlChar (0,10,13,24-31): 2 bytes each
    """
    chars: List[Union[HWPCharNormal, HWPCharControl, HWPCharInline, HWPCharExtend]] = []
    pos = 0
    data_len = len(data)

    while pos + 2 <= data_len:
        code = struct.unpack_from('<H', data, pos)[0]

        if code > 31:
            # Normal printable character
            chars.append(HWPCharNormal(code=code, char=chr(code)))
            pos += 2

        elif code in CONTROL_EXTEND_CODES:
            # Extended control: 2-byte code + 12-byte addition + 2-byte trailing = 16 bytes
            addition = b''
            if pos + 16 <= data_len:
                addition = data[pos + 2:pos + 14]  # 12 bytes of addition
            chars.append(HWPCharExtend(code=code, addition=addition))
            pos += 16

        elif code in CONTROL_INLINE_CODES:
            # Inline control: 16 bytes total
            addition = b''
            if pos + 16 <= data_len:
                addition = data[pos + 2:pos + 14]  # 12 bytes
            chars.append(HWPCharInline(code=code, addition=addition))
            pos += 16

        else:
            # ControlChar: 0, 10, 13, 24-31 — 2 bytes each
            chars.append(HWPCharControl(code=code))
            pos += 2

    return chars


def _parse_para_char_shape(data: bytes) -> List[Tuple[int, int]]:
    """Parse PARA_CHAR_SHAPE (tag 68): (position, charShapeID) pairs."""
    pairs: List[Tuple[int, int]] = []
    pos = 0
    while pos + 8 <= len(data):
        char_pos = struct.unpack_from('<I', data, pos)[0]
        shape_id = struct.unpack_from('<I', data, pos + 4)[0]
        pairs.append((char_pos, shape_id))
        pos += 8
    return pairs


def _parse_para_line_seg(data: bytes) -> List[LineSegInfo]:
    """Parse PARA_LINE_SEG (tag 69)."""
    segs: List[LineSegInfo] = []
    # Each segment is 36 bytes
    pos = 0
    while pos + 36 <= len(data):
        seg = LineSegInfo()
        seg.text_start = struct.unpack_from('<I', data, pos)[0]
        seg.line_vertical = struct.unpack_from('<i', data, pos + 4)[0]
        seg.line_height = struct.unpack_from('<i', data, pos + 8)[0]
        seg.text_height = struct.unpack_from('<i', data, pos + 12)[0]
        seg.baseline_distance = struct.unpack_from('<i', data, pos + 16)[0]
        seg.line_spacing = struct.unpack_from('<i', data, pos + 20)[0]
        seg.column_start = struct.unpack_from('<i', data, pos + 24)[0]
        seg.segment_width = struct.unpack_from('<i', data, pos + 28)[0]
        seg.tag = struct.unpack_from('<I', data, pos + 32)[0]
        segs.append(seg)
        pos += 36
    return segs


def _parse_ctrl_header(data: bytes) -> ControlInfo:
    """Parse CTRL_HEADER (tag 71) — read control type ID and dispatch."""
    ctrl = ControlInfo()
    if len(data) < 4:
        return ctrl

    # Control ID is 4 bytes in reverse byte order (e.g., 'lbt ' for table)
    raw_id = data[0:4]
    ctrl.ctrl_id = raw_id[::-1].decode('ascii', errors='replace')
    ctrl.raw_data = data
    pos = 4

    # Common header for positioned controls: property (DWORD)
    if pos + 4 <= len(data):
        ctrl.property, pos = _read_uint32(data, pos)

    # Dispatch based on control ID
    ctrl_id = ctrl.ctrl_id.rstrip('\x00')

    if ctrl_id == 'tbl ':
        ctrl.sub_data = _parse_ctrl_table_header(data, pos)
    elif ctrl_id == 'gso ':
        ctrl.sub_data = _parse_ctrl_gso_header(data, pos)
    elif ctrl_id == 'eqed':
        ctrl.sub_data = {'type': 'equation'}
    elif ctrl_id == 'secd':
        ctrl.sub_data = _parse_ctrl_secd(data, pos)
    elif ctrl_id == 'cold':
        ctrl.sub_data = {'type': 'column_define'}
    elif ctrl_id in ('head', 'foot'):
        ctrl.sub_data = _parse_ctrl_header_footer(data, pos, ctrl_id)
    elif ctrl_id in ('fn  ', 'en  '):
        ctrl.sub_data = _parse_ctrl_note(data, pos, ctrl_id)
    elif ctrl_id in ('atno', 'nwno'):
        ctrl.sub_data = {'type': 'auto_number' if ctrl_id == 'atno' else 'new_number'}
    elif ctrl_id in ('pghd', 'pgct'):
        ctrl.sub_data = {'type': 'page_hide'}
    elif ctrl_id == 'pgnp':
        ctrl.sub_data = {'type': 'page_number_position'}
    elif ctrl_id == 'bokm':
        ctrl.sub_data = _parse_ctrl_bookmark(data, pos)
    elif ctrl_id.startswith('%'):
        ctrl.sub_data = _parse_ctrl_field(data, pos, ctrl_id)
    elif ctrl_id == 'form':
        ctrl.sub_data = {'type': 'form_object'}
    else:
        ctrl.sub_data = {'type': 'unknown', 'ctrl_id': ctrl_id}

    return ctrl


def _parse_ctrl_table_header(data: bytes, pos: int) -> dict:
    """Parse additional table control header data."""
    result: dict = {'type': 'table'}
    # After common property: vertical offset, horizontal offset, width, height,
    # z-order, margins, object instance ID, prevent page break, description
    if pos + 4 <= len(data):
        result['y_offset'], pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        result['x_offset'], pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        result['width'], pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        result['height'], pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        result['z_order'], pos = _read_int32(data, pos)
    # margins (4 x INT16)
    for margin_name in ('margin_left', 'margin_right', 'margin_top', 'margin_bottom'):
        if pos + 2 <= len(data):
            result[margin_name], pos = _read_int16(data, pos)
    # object instance ID
    if pos + 4 <= len(data):
        result['instance_id'], pos = _read_uint32(data, pos)
    return result


def _parse_ctrl_gso_header(data: bytes, pos: int) -> dict:
    """Parse graphic shape object control header."""
    result: dict = {'type': 'gso'}
    if pos + 4 <= len(data):
        result['y_offset'], pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        result['x_offset'], pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        result['width'], pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        result['height'], pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        result['z_order'], pos = _read_int32(data, pos)
    for margin_name in ('margin_left', 'margin_right', 'margin_top', 'margin_bottom'):
        if pos + 2 <= len(data):
            result[margin_name], pos = _read_int16(data, pos)
    if pos + 4 <= len(data):
        result['instance_id'], pos = _read_uint32(data, pos)
    return result


def _parse_ctrl_secd(data: bytes, pos: int) -> dict:
    """Parse section define control."""
    result: dict = {'type': 'section_define'}
    # Section properties follow the common control header
    # Skip to the relevant fields; layout varies by version
    return result


def _parse_ctrl_header_footer(data: bytes, pos: int, ctrl_id: str) -> dict:
    """Parse header/footer control."""
    result: dict = {'type': 'header' if ctrl_id == 'head' else 'footer'}
    if pos + 4 <= len(data):
        result['property'], pos = _read_uint32(data, pos)
    return result


def _parse_ctrl_note(data: bytes, pos: int, ctrl_id: str) -> dict:
    """Parse footnote/endnote control."""
    result: dict = {'type': 'footnote' if ctrl_id == 'fn  ' else 'endnote'}
    if pos + 4 <= len(data):
        result['number'], pos = _read_uint32(data, pos)
    return result


def _parse_ctrl_bookmark(data: bytes, pos: int) -> dict:
    """Parse bookmark control."""
    result: dict = {'type': 'bookmark'}
    # Bookmark name is a HWP string after the common part
    if pos + 2 <= len(data):
        result['name'], pos = _read_hwp_string(data, pos)
    return result


def _parse_ctrl_field(data: bytes, pos: int, ctrl_id: str) -> dict:
    """Parse field control (%xxx types)."""
    result: dict = {'type': 'field', 'field_type': ctrl_id}
    # Fields have a command string and option data
    return result


def _parse_list_header(data: bytes) -> dict:
    """Parse LIST_HEADER (tag 72) — generic, then check for cell-specific data."""
    result: dict = {}
    pos = 0

    if pos + 2 <= len(data):
        result['para_count'], pos = _read_uint16(data, pos)
    if pos + 4 <= len(data):
        result['property'], pos = _read_uint32(data, pos)

    # The remaining data length hints at whether this is a cell list header.
    # Cell list header has additional: colIndex(WORD), rowIndex(WORD),
    # colSpan(WORD), rowSpan(WORD), width(DWORD), height(DWORD),
    # margins (4 x WORD), borderFillId(WORD)
    remaining = len(data) - pos
    if remaining >= 22:
        result['is_cell'] = True
        result['col_index'], pos = _read_uint16(data, pos)
        result['row_index'], pos = _read_uint16(data, pos)
        result['col_span'], pos = _read_uint16(data, pos)
        result['row_span'], pos = _read_uint16(data, pos)
        result['width'], pos = _read_uint32(data, pos)
        result['height'], pos = _read_uint32(data, pos)
        result['margin_left'], pos = _read_uint16(data, pos)
        result['margin_right'], pos = _read_uint16(data, pos)
        result['margin_top'], pos = _read_uint16(data, pos)
        result['margin_bottom'], pos = _read_uint16(data, pos)
        if pos + 2 <= len(data):
            result['border_fill_id'], pos = _read_uint16(data, pos)
    else:
        result['is_cell'] = False

    return result


def _parse_table(data: bytes) -> TableInfo:
    """Parse TABLE (tag 77)."""
    info = TableInfo()
    pos = 0

    if pos + 4 <= len(data):
        info.property, pos = _read_uint32(data, pos)  # actually stored before row/col in some versions
    # Re-read: property is DWORD, but the actual first fields are property, rowCount, colCount
    # Reset and parse properly
    pos = 0
    if pos + 4 <= len(data):
        prop, pos = _read_uint32(data, pos)
    if pos + 2 <= len(data):
        info.row_count, pos = _read_uint16(data, pos)
    if pos + 2 <= len(data):
        info.col_count, pos = _read_uint16(data, pos)
    if pos + 2 <= len(data):
        info.cell_spacing, pos = _read_uint16(data, pos)

    # margins
    if pos + 2 <= len(data):
        info.margin_left, pos = _read_uint16(data, pos)
    if pos + 2 <= len(data):
        info.margin_right, pos = _read_uint16(data, pos)
    if pos + 2 <= len(data):
        info.margin_top, pos = _read_uint16(data, pos)
    if pos + 2 <= len(data):
        info.margin_bottom, pos = _read_uint16(data, pos)

    # row sizes (WORD * rowCount)
    for _ in range(info.row_count):
        if pos + 2 <= len(data):
            val, pos = _read_uint16(data, pos)
            info.zone_info.append(val)

    # border fill ID
    if pos + 2 <= len(data):
        info.border_fill_id, pos = _read_uint16(data, pos)

    return info


def _parse_shape_component(data: bytes) -> ShapeComponentInfo:
    """Parse SHAPE_COMPONENT (tag 76)."""
    info = ShapeComponentInfo()
    pos = 0

    # gso ID (4 bytes as reversed ASCII)
    if pos + 4 <= len(data):
        raw = data[pos:pos + 4]
        info.gso_id = raw[::-1].decode('ascii', errors='replace')
        pos += 4

    # x_offset, y_offset
    if pos + 4 <= len(data):
        info.x_offset, pos = _read_int32(data, pos)
    if pos + 4 <= len(data):
        info.y_offset, pos = _read_int32(data, pos)

    # grouping level
    if pos + 2 <= len(data):
        _, pos = _read_uint16(data, pos)

    # local file version
    if pos + 2 <= len(data):
        _, pos = _read_uint16(data, pos)

    # Original size
    if pos + 4 <= len(data):
        info.width, pos = _read_uint32(data, pos)
    if pos + 4 <= len(data):
        info.height, pos = _read_uint32(data, pos)

    # Rotation
    if pos + 2 <= len(data):
        info.rotation, pos = _read_uint16(data, pos)

    # Scale
    if pos + 4 <= len(data):
        info.x_scale, pos = _read_int32(data, pos)
    if pos + 4 <= len(data):
        info.y_scale, pos = _read_int32(data, pos)

    return info


def _parse_section(ole, section_idx: int, compressed: bool) -> Optional[SectionData]:
    """Parse a single BodyText/SectionN stream into SectionData."""
    stream_name = f'BodyText/Section{section_idx}'
    if not ole.exists(stream_name):
        return None

    data = _decompress_stream(ole, stream_name, compressed)
    records = _parse_records(data)

    section = SectionData()
    current_para: Optional[ParagraphData] = None
    instance_counter = 0

    # We use index-based iteration to handle lookahead
    i = 0
    while i < len(records):
        rec = records[i]
        tag = rec.tag_id
        d = rec.data

        if tag == TAG_PARA_HEADER:
            # Flush previous paragraph
            if current_para is not None:
                section.paragraphs.append(current_para)

            current_para = ParagraphData()
            current_para.instance_id = instance_counter
            instance_counter += 1

            pos = 0
            # nChars (DWORD)
            if pos + 4 <= len(d):
                current_para.char_count = struct.unpack_from('<I', d, pos)[0]
                pos += 4
            # controlMask (DWORD)
            if pos + 4 <= len(d):
                current_para.control_mask = struct.unpack_from('<I', d, pos)[0]
                pos += 4
            # paraShapeID (WORD)
            if pos + 2 <= len(d):
                current_para.para_shape_id = struct.unpack_from('<H', d, pos)[0]
                pos += 2
            # styleID (BYTE)
            if pos + 1 <= len(d):
                current_para.style_id = d[pos]
                pos += 1
            # divideSort (BYTE)  — column/page break info
            if pos + 1 <= len(d):
                current_para.divide_sort = d[pos]
                pos += 1
            # charCount(WORD), rangeTag(WORD) — version dependent
            # instance_id (DWORD) — version >= 5.0.3.2
            if pos + 4 <= len(d):
                # skip charCount(2) + rangeTag(2)
                pos += 4
            if pos + 4 <= len(d):
                stored_instance = struct.unpack_from('<I', d, pos)[0]
                if stored_instance > 0:
                    current_para.instance_id = stored_instance

        elif tag == TAG_PARA_TEXT and current_para is not None:
            current_para.chars = _parse_para_text(d)

        elif tag == TAG_PARA_CHAR_SHAPE and current_para is not None:
            current_para.char_shape_pairs = _parse_para_char_shape(d)

        elif tag == TAG_PARA_LINE_SEG and current_para is not None:
            current_para.line_segs = _parse_para_line_seg(d)

        elif tag == TAG_CTRL_HEADER and current_para is not None:
            ctrl = _parse_ctrl_header(d)
            current_para.controls.append(ctrl)

        elif tag == TAG_TABLE and current_para is not None:
            table_info = _parse_table(d)
            # Attach to the last control if it's a table control
            for ctrl in reversed(current_para.controls):
                if ctrl.ctrl_id.rstrip('\x00') == 'tbl ':
                    ctrl.sub_data['table_info'] = table_info
                    break

        elif tag == TAG_LIST_HEADER and current_para is not None:
            lh = _parse_list_header(d)
            # Attach cell info to the last table control
            if lh.get('is_cell'):
                cell = CellInfo(
                    para_count=lh.get('para_count', 0),
                    property=lh.get('property', 0),
                    col_index=lh.get('col_index', 0),
                    row_index=lh.get('row_index', 0),
                    col_span=lh.get('col_span', 1),
                    row_span=lh.get('row_span', 1),
                    width=lh.get('width', 0),
                    height=lh.get('height', 0),
                    margin_left=lh.get('margin_left', 0),
                    margin_right=lh.get('margin_right', 0),
                    margin_top=lh.get('margin_top', 0),
                    margin_bottom=lh.get('margin_bottom', 0),
                    border_fill_id=lh.get('border_fill_id', 0),
                )
                # Find parent table control and attach
                for ctrl in reversed(current_para.controls):
                    if ctrl.ctrl_id.rstrip('\x00') == 'tbl ':
                        ti = ctrl.sub_data.get('table_info')
                        if isinstance(ti, TableInfo):
                            ti.cells.append(cell)
                        break

        elif tag == TAG_SHAPE_COMPONENT and current_para is not None:
            sc = _parse_shape_component(d)
            # Attach to the last gso control
            for ctrl in reversed(current_para.controls):
                if ctrl.ctrl_id.rstrip('\x00') == 'gso ':
                    ctrl.sub_data['shape_component'] = sc
                    break

        elif tag in (TAG_SHAPE_COMPONENT_LINE, TAG_SHAPE_COMPONENT_RECTANGLE,
                     TAG_SHAPE_COMPONENT_ELLIPSE, TAG_SHAPE_COMPONENT_ARC,
                     TAG_SHAPE_COMPONENT_POLYGON, TAG_SHAPE_COMPONENT_CURVE,
                     TAG_SHAPE_COMPONENT_OLE, TAG_SHAPE_COMPONENT_PICTURE,
                     TAG_SHAPE_COMPONENT_CONTAINER, TAG_SHAPE_COMPONENT_EQUATION,
                     TAG_SHAPE_COMPONENT_TEXTART):
            shape_type_map = {
                TAG_SHAPE_COMPONENT_LINE: 'line',
                TAG_SHAPE_COMPONENT_RECTANGLE: 'rectangle',
                TAG_SHAPE_COMPONENT_ELLIPSE: 'ellipse',
                TAG_SHAPE_COMPONENT_ARC: 'arc',
                TAG_SHAPE_COMPONENT_POLYGON: 'polygon',
                TAG_SHAPE_COMPONENT_CURVE: 'curve',
                TAG_SHAPE_COMPONENT_OLE: 'ole',
                TAG_SHAPE_COMPONENT_PICTURE: 'picture',
                TAG_SHAPE_COMPONENT_CONTAINER: 'container',
                TAG_SHAPE_COMPONENT_EQUATION: 'equation',
                TAG_SHAPE_COMPONENT_TEXTART: 'textart',
            }
            shape_type = shape_type_map.get(tag, 'unknown')
            # Attach shape-specific data to the last gso control's shape_component
            for ctrl in reversed(current_para.controls):
                if ctrl.ctrl_id.rstrip('\x00') == 'gso ':
                    sc = ctrl.sub_data.get('shape_component')
                    if isinstance(sc, ShapeComponentInfo):
                        sc.shape_type = shape_type
                        sc.shape_data['raw'] = d
                        # Parse picture-specific data
                        if tag == TAG_SHAPE_COMPONENT_PICTURE:
                            _parse_picture_shape(d, sc.shape_data)
                    break

        i += 1

    # Flush last paragraph
    if current_para is not None:
        section.paragraphs.append(current_para)

    return section


def _parse_picture_shape(data: bytes, shape_data: dict) -> None:
    """Parse picture shape specific data (tag 85)."""
    pos = 0
    # border color (DWORD)
    if pos + 4 <= len(data):
        shape_data['border_color'], pos = _read_uint32(data, pos)
    # border thickness (INT32)
    if pos + 4 <= len(data):
        shape_data['border_thickness'], pos = _read_int32(data, pos)
    # border property (DWORD)
    if pos + 4 <= len(data):
        shape_data['border_property'], pos = _read_uint32(data, pos)
    # brightness, contrast, effect
    for key in ('brightness', 'contrast', 'effect'):
        if pos + 1 <= len(data):
            shape_data[key], pos = _read_uint8(data, pos)
    # bin data ID (WORD)
    if pos + 2 <= len(data):
        shape_data['bin_data_id'], pos = _read_uint16(data, pos)


# ---------------------------------------------------------------------------
# BinData extraction
# ---------------------------------------------------------------------------

def _extract_bin_data(ole, compressed: bool) -> Dict[int, bytes]:
    """Extract binary data from BinData/ storage."""
    entries: Dict[int, bytes] = {}
    if not ole.exists('BinData'):
        return entries

    for dir_entry in ole.listdir():
        path = '/'.join(dir_entry)
        if not path.startswith('BinData/'):
            continue
        name = dir_entry[-1]
        # Extract bin data ID from name like "BIN0001.png"
        try:
            # Remove prefix 'BIN' and extension
            base = name.split('.')[0]
            if base.upper().startswith('BIN'):
                bin_id = int(base[3:])
            else:
                continue
        except (ValueError, IndexError):
            continue

        try:
            raw = ole.openstream(path).read()
            if compressed:
                try:
                    data = zlib.decompress(raw, -15)
                except zlib.error:
                    try:
                        data = zlib.decompress(raw)
                    except zlib.error:
                        data = raw
            else:
                data = raw
            entries[bin_id] = data
        except Exception as e:
            logger.warning("Failed to extract BinData/%s: %s", name, e)

    return entries


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_format(filepath: str) -> str:
    """Detect file format: HWP, HWPX, OWPML, UNKNOWN."""
    import zipfile
    try:
        with zipfile.ZipFile(filepath) as z:
            if 'Contents/section0.xml' in z.namelist():
                return 'HWPX'
    except zipfile.BadZipFile:
        pass

    with open(filepath, 'rb') as f:
        magic = f.read(8)
        if magic[:4] == b'\xd0\xcf\x11\xe0':
            return 'HWP'
        if magic[:2] == b'PK':
            return 'HWPX'
    return 'UNKNOWN'


def read_hwp(filepath: str) -> HWPDocument:
    """Read an HWP 5.x binary file and return a fully parsed HWPDocument.

    Parameters
    ----------
    filepath : str
        Path to the .hwp file.

    Returns
    -------
    HWPDocument
        Rich dataclass hierarchy with all parsed data.
    """
    if olefile is None:
        raise ImportError("olefile not installed. pip install olefile")

    ole = olefile.OleFileIO(filepath)
    try:
        # 1. FileHeader
        file_header = _parse_file_header(ole)

        doc = HWPDocument(
            version=file_header.version_str,
            compressed=file_header.compressed,
            encrypted=file_header.encrypted,
            file_header=file_header,
        )

        if file_header.encrypted:
            logger.warning("HWP file is encrypted - cannot read content")
            return doc

        # 2. DocInfo
        doc.doc_info = _parse_docinfo(ole, file_header.compressed)

        # 3. BodyText sections
        section_idx = 0
        while True:
            section = _parse_section(ole, section_idx, file_header.compressed)
            if section is None:
                break
            doc.sections.append(section)
            section_idx += 1

        # 4. BinData extraction
        doc.bin_data_entries = _extract_bin_data(ole, file_header.compressed)

        return doc

    finally:
        ole.close()


def hwp_to_hwpx(hwp_path: str, hwpx_path: str, max_paragraphs: int = 0) -> str:
    """Convert HWP 5.x to HWPX format.

    Parameters
    ----------
    hwp_path : str
        Input HWP file path.
    hwpx_path : str
        Output HWPX file path.
    max_paragraphs : int
        Maximum paragraph count (0 = unlimited). NOTE: this parameter is
        ignored by the new converter (hwp2hwpx.convert) which preserves
        the full document structure.

    Returns
    -------
    str
        Path to the output HWPX file.
    """
    # NOTE: This function now delegates to the full hwp2hwpx converter
    # (pyhwpxlib/hwp2hwpx.py) which uses the pyhwpxlib object model
    # for faithful HWP -> HWPX conversion. The previous text-based
    # approach is replaced by the complete structural conversion.
    from .hwp2hwpx import convert
    return convert(hwp_path, hwpx_path)
