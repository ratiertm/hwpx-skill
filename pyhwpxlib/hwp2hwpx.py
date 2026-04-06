"""HWP 5.x -> HWPX converter

Ported from hwp2hwpx by neolord0 (https://github.com/neolord0/hwp2hwpx)
Original work Copyright (c) neolord0, licensed under Apache License 2.0.
This Python port: Copyright (c) 2026 Eunmi Lee (ratiertm), licensed under BSL 1.1.
Changes: Rewritten in Python; adapted to pyhwpxlib object model and HWPXWriter.

Usage:
    from pyhwpxlib.hwp2hwpx import convert
    convert("input.hwp", "output.hwpx")
"""
from __future__ import annotations

import logging
import struct
import zlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ============================================================
# HWP record tag IDs (HWPTAG_BEGIN = 16)
# ============================================================
_TAG_DOCUMENT_PROPERTIES = 16
_TAG_ID_MAPPINGS = 17
_TAG_BIN_DATA = 18
_TAG_FACE_NAME = 19
_TAG_BORDER_FILL = 20
_TAG_CHAR_SHAPE = 21
_TAG_TAB_DEF = 22
_TAG_NUMBERING = 23
_TAG_BULLET = 24
_TAG_PARA_SHAPE = 25
_TAG_STYLE = 26
_TAG_DOC_DATA = 27
_TAG_MEMO_SHAPE = 92  # HWPTAG_BEGIN + 76

# HWPTAG_BEGIN = 16.  Tag = HWPTAG_BEGIN + offset
_TAG_PARA_HEADER = 66       # 16 + 50
_TAG_PARA_TEXT = 67         # 16 + 51
_TAG_PARA_CHAR_SHAPE = 68  # 16 + 52
_TAG_PARA_LINE_SEG = 69    # 16 + 53
_TAG_CTRL_HEADER = 71      # 16 + 55
_TAG_LIST_HEADER = 72      # 16 + 56
_TAG_PAGE_DEF = 73         # 16 + 57
_TAG_FOOTNOTE_SHAPE = 74   # 16 + 58
_TAG_PAGE_BORDER_FILL = 75 # 16 + 59
_TAG_SHAPE_COMPONENT = 76  # 16 + 60
_TAG_TABLE = 77            # 16 + 61

# HWP control character codes (in PARA_TEXT as uint16)
_CH_SECTION_DEF = 2
_CH_COLUMN_DEF = 3
_CH_FIELD_END = 4
_CH_FIELD_BEGIN = 5
_CH_TABLE = 11     # also GSO, button, etc.
_CH_TAB = 9
_CH_LINE_BREAK = 10
_CH_PARA_END = 13
_CH_NBSPACE = 30
_CH_FWSPACE = 31
_CH_HYPHEN = 24

# Extended control char codes (occupy 8 wchars total)
_EXTENDED_CHARS = set(range(1, 32)) - {_CH_TAB, _CH_LINE_BREAK, _CH_PARA_END}


# ============================================================
# Public API
# ============================================================

def convert(hwp_path: str, hwpx_path: str) -> str:
    """Convert HWP file to HWPX file.

    Parameters
    ----------
    hwp_path : str
        Input HWP 5.x binary file path
    hwpx_path : str
        Output HWPX file path

    Returns
    -------
    str
        The output hwpx_path
    """
    hwp = _HWPDocument(hwp_path)
    hwpx_file = _build_hwpx(hwp)
    _write_hwpx_file(hwpx_file, hwpx_path, hwp)
    logger.info("HWP -> HWPX conversion complete: %s -> %s", hwp_path, hwpx_path)
    return hwpx_path


def _write_hwpx_file(hwpx_file, hwpx_path: str, hwp: '_HWPDocument'):
    """Write HWPXFile to .hwpx ZIP without needing Skeleton.hwpx."""
    import io
    import zipfile
    from .writer.header.header_writer import write_header
    from .writer.section.section_writer import write_section
    from .writer.content_hpf_writer import write_content_hpf
    from .writer.xml_builder import XMLStringBuilder

    xsb = XMLStringBuilder()

    # Generate XML content
    xml_files = {}

    # header.xml
    if hwpx_file.header_xml_file is not None:
        write_header(xsb, hwpx_file.header_xml_file)
        xml_files["Contents/header.xml"] = xsb.to_string().encode("utf-8")

    # content.hpf
    if hwpx_file.content_hpf_file is not None:
        write_content_hpf(xsb, hwpx_file.content_hpf_file)
        xml_files["Contents/content.hpf"] = xsb.to_string().encode("utf-8")

    # section files
    for i in range(hwpx_file.section_xml_file_list.count()):
        sec = hwpx_file.section_xml_file_list.get(i)
        write_section(xsb, sec)
        xml_files[f"Contents/section{i}.xml"] = xsb.to_string().encode("utf-8")

    # version.xml (exact match to Java hwpxlib output)
    v = hwpx_file.version_xml_file
    version_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        f'<hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version"'
        f' tagetApplication="WORDPROCESSOR"'
        f' major="{v.version.major}" minor="{v.version.minor}"'
        f' micro="{v.version.micro}" buildNumber="{v.version.build_number}"'
        f' os="1" xmlVersion="1.4"'
        f' application="Hancom Office Hangul"'
        f' appVersion="9, 1, 1, 5656 WIN32LEWindows_Unknown_Version"/>'
    )
    xml_files["version.xml"] = version_xml.encode("utf-8")

    # settings.xml (exact match to Java hwpxlib output)
    settings_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        '<ha:HWPApplicationSetting'
        ' xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app"'
        ' xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0">'
        '<ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/>'
        '</ha:HWPApplicationSetting>'
    )
    xml_files["settings.xml"] = settings_xml.encode("utf-8")

    # container.xml (exact match to Java hwpxlib output)
    container_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        '<ocf:container xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container"'
        ' xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf">'
        '<ocf:rootfiles>'
        '<ocf:rootfile full-path="Contents/content.hpf"'
        ' media-type="application/hwpml-package+xml"/>'
        '<ocf:rootfile full-path="Preview/PrvText.txt"'
        ' media-type="text/plain"/>'
        '</ocf:rootfiles>'
        '</ocf:container>'
    )
    xml_files["META-INF/container.xml"] = container_xml.encode("utf-8")

    # manifest.xml (exact match to Java hwpxlib output)
    manifest_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
        '<odf:manifest xmlns:odf="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"/>'
    )
    xml_files["META-INF/manifest.xml"] = manifest_xml.encode("utf-8")

    # Write ZIP (order must match Java: mimetype, version, META-INF, Contents, settings)
    write_order = [
        "version.xml",
        "META-INF/manifest.xml",
        "META-INF/container.xml",
        "Contents/content.hpf",
        "Contents/header.xml",
    ]
    # Add section files in order
    for i in range(hwpx_file.section_xml_file_list.count()):
        write_order.append(f"Contents/section{i}.xml")
    write_order.append("settings.xml")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # mimetype must be first, uncompressed
        info = zipfile.ZipInfo("mimetype")
        info.compress_type = zipfile.ZIP_STORED
        zf.writestr(info, "application/hwp+zip")

        # Write XML files in correct order
        for name in write_order:
            if name in xml_files:
                zf.writestr(name, xml_files[name])

        # Write binary data (images, OLE)
        bin_attachments = getattr(hwpx_file, "_binary_attachments", {})
        for bin_path, bin_data in bin_attachments.items():
            zf.writestr(bin_path, bin_data)

        # PrvText.txt (empty placeholder)
        zf.writestr("Preview/PrvText.txt", "")

    with open(hwpx_path, "wb") as f:
        f.write(buf.getvalue())


# ============================================================
# HWP Document Reader (enhanced for conversion)
# ============================================================

class _HWPDocument:
    """Reads an HWP 5.x binary file into structured data for conversion."""

    def __init__(self, filepath: str):
        try:
            import olefile
        except ImportError:
            raise ImportError("olefile not installed. pip install olefile")

        self.ole = olefile.OleFileIO(filepath)

        # FileHeader
        fh = self.ole.openstream('FileHeader').read()
        version_raw = struct.unpack_from('<I', fh, 32)[0]
        self.version_mm = (version_raw >> 24) & 0xFF
        self.version_nn = (version_raw >> 16) & 0xFF
        self.version_pp = (version_raw >> 8) & 0xFF
        self.version_rr = version_raw & 0xFF
        props = struct.unpack_from('<I', fh, 36)[0]
        self.compressed = bool(props & 0x01)
        self.encrypted = bool(props & 0x02)

        if self.encrypted:
            raise ValueError("Encrypted HWP files cannot be converted")

        # Parse DocInfo
        self.docinfo_records = self._parse_stream('DocInfo')
        self.id_mappings = self._read_id_mappings()
        self.face_names = self._read_face_names()
        self.border_fills = self._read_border_fills()
        self.char_shapes = self._read_char_shapes()
        self.tab_defs = self._read_tab_defs()
        self.numberings = self._read_numberings()
        self.bullets = self._read_bullets()
        self.para_shapes = self._read_para_shapes()
        self.styles = self._read_styles()

        # Count sections
        self.section_count = 0
        while self.ole.exists(f'BodyText/Section{self.section_count}'):
            self.section_count += 1

        # Section data (raw records)
        self.section_records: List[List[dict]] = []
        for i in range(self.section_count):
            records = self._parse_stream(f'BodyText/Section{i}')
            self.section_records.append(records)

        # BinData
        self.bin_data_ids = self._read_bin_data_entries()

        # Summary Information
        self.summary = self._read_summary()

        # Streams list
        self.streams = ['/'.join(s) for s in self.ole.listdir()]

    def close(self):
        self.ole.close()

    def _decompress(self, raw: bytes) -> bytes:
        if not self.compressed:
            return raw
        try:
            return zlib.decompress(raw, -15)
        except zlib.error:
            return zlib.decompress(raw)

    def _parse_stream(self, name: str) -> List[dict]:
        raw = self.ole.openstream(name).read()
        data = self._decompress(raw)
        return _parse_records(data)

    def _read_id_mappings(self) -> dict:
        """Read HWPTAG_ID_MAPPINGS -> counts of each type."""
        counts = {}
        count_names = [
            'binData', 'hangulFont', 'englishFont', 'hanjaFont',
            'japaneseFont', 'etcFont', 'symbolFont', 'userFont',
            'borderFill', 'charShape', 'tabDef', 'numbering',
            'bullet', 'paraShape', 'style', 'memoShape'
        ]
        for rec in self.docinfo_records:
            if rec['tag'] == _TAG_ID_MAPPINGS:
                d = rec['data']
                for i, name in enumerate(count_names):
                    if i * 4 + 4 <= len(d):
                        counts[name] = struct.unpack_from('<I', d, i * 4)[0]
                break
        return counts

    def _read_face_names(self) -> List[dict]:
        """Read all HWPTAG_FACE_NAME records, grouped by language."""
        results = []
        for rec in self.docinfo_records:
            if rec['tag'] == _TAG_FACE_NAME and len(rec['data']) >= 3:
                d = rec['data']
                props = d[0]
                name_len = struct.unpack_from('<H', d, 1)[0]
                if 3 + name_len * 2 <= len(d):
                    face = d[3:3 + name_len * 2].decode('utf-16-le', errors='replace')
                else:
                    face = "Unknown"
                # Font type info
                font_type_val = (props >> 5) & 0x03 if len(d) > 0 else 0
                results.append({
                    'face': face,
                    'type': font_type_val,
                    'raw': d,
                })
        return results

    def _read_border_fills(self) -> List[dict]:
        """Read all HWPTAG_BORDER_FILL records."""
        results = []
        for rec in self.docinfo_records:
            if rec['tag'] == _TAG_BORDER_FILL and len(rec['data']) >= 14:
                d = rec['data']
                prop = struct.unpack_from('<H', d, 0)[0]
                # 4 borders: left, right, top, bottom (each: type 1B, width 1B, color 4B = 6B)
                borders = []
                pos = 2
                for _ in range(4):
                    if pos + 6 <= len(d):
                        btype = d[pos]
                        bwidth = d[pos + 1]
                        bcolor = struct.unpack_from('<I', d, pos + 2)[0]
                        borders.append({'type': btype, 'width': bwidth, 'color': bcolor})
                        pos += 6
                    else:
                        borders.append({'type': 0, 'width': 0, 'color': 0})
                        pos += 6
                # diagonal
                diag = {'type': 0, 'width': 0, 'color': 0}
                if pos + 6 <= len(d):
                    diag = {
                        'type': d[pos], 'width': d[pos + 1],
                        'color': struct.unpack_from('<I', d, pos + 2)[0]
                    }
                    pos += 6

                # Fill type flags (4 bytes)
                fill_type = 0
                fill_face_color = None
                fill_hatch_color = 0
                if pos + 4 <= len(d):
                    fill_type = struct.unpack_from('<I', d, pos)[0]
                    pos += 4

                    # If fill has pattern fill (bit 0), read winBrush data
                    if fill_type & 0x01:
                        if pos + 8 <= len(d):
                            back_color = struct.unpack_from('<I', d, pos)[0]
                            pattern_color = struct.unpack_from('<I', d, pos + 4)[0]
                            fill_face_color = back_color
                            fill_hatch_color = pattern_color

                results.append({
                    'prop': prop,
                    'borders': borders,  # [left, right, top, bottom]
                    'diagonal': diag,
                    'fill_type': fill_type,
                    'fill_face_color': fill_face_color,
                    'fill_hatch_color': fill_hatch_color,
                    'raw': d,
                })
        return results

    def _read_char_shapes(self) -> List[dict]:
        """Read all HWPTAG_CHAR_SHAPE records."""
        results = []
        for rec in self.docinfo_records:
            if rec['tag'] == _TAG_CHAR_SHAPE and len(rec['data']) >= 54:
                d = rec['data']
                # Font ID references per language (7 languages, 2 bytes each)
                font_ids = []
                for i in range(7):
                    font_ids.append(struct.unpack_from('<H', d, i * 2)[0])
                # Ratios (7 x 1 byte at offset 14)
                ratios = []
                for i in range(7):
                    if 14 + i < len(d):
                        ratios.append(d[14 + i])
                    else:
                        ratios.append(100)
                # Spacings (7 x 1 signed byte at offset 21)
                spacings = []
                for i in range(7):
                    if 21 + i < len(d):
                        spacings.append(struct.unpack_from('<b', d, 21 + i)[0])
                    else:
                        spacings.append(0)
                # RelSz (7 x 1 byte at offset 28)
                rel_sizes = []
                for i in range(7):
                    if 28 + i < len(d):
                        rel_sizes.append(d[28 + i])
                    else:
                        rel_sizes.append(100)
                # Offset (7 x 1 signed byte at offset 35)
                offsets = []
                for i in range(7):
                    if 35 + i < len(d):
                        offsets.append(struct.unpack_from('<b', d, 35 + i)[0])
                    else:
                        offsets.append(0)

                # HWP CharShape binary layout (verified from hex dump):
                # [0-13]  7 x uint16 fontIDs = 14 bytes
                # [14-20] 7 x uint8 ratios = 7 bytes
                # [21-27] 7 x int8 spacings = 7 bytes
                # [28-34] 7 x uint8 relSizes = 7 bytes
                # [35-41] 7 x int8 offsets = 7 bytes
                # [42-45] uint32 baseSize
                # [46-49] uint32 property
                # [50]    int8 shadowGap1
                # [51]    int8 shadowGap2
                # [52-55] uint32 charColor
                # [56-59] uint32 underlineColor
                # [60-63] uint32 shadeColor
                # [64-67] uint32 shadowColor
                # [68-69] uint16 borderFillId
                # [70-73] uint32 strikeoutColor
                base_size = struct.unpack_from('<I', d, 42)[0] if len(d) >= 46 else 1000
                prop = struct.unpack_from('<I', d, 46)[0] if len(d) >= 50 else 0
                text_color = struct.unpack_from('<I', d, 52)[0] if len(d) >= 56 else 0
                underline_color = struct.unpack_from('<I', d, 56)[0] if len(d) >= 60 else 0
                shade_color = struct.unpack_from('<I', d, 60)[0] if len(d) >= 64 else 0xFFFFFFFF
                shadow_color = struct.unpack_from('<I', d, 64)[0] if len(d) >= 68 else 0xB2B2B2

                # Extract property bits
                italic = bool(prop & 0x01)
                bold = bool(prop & 0x02)
                underline_type_val = (prop >> 2) & 0x03
                underline_shape = (prop >> 4) & 0x0F
                outline_type_val = (prop >> 8) & 0x07
                shadow_type_val = (prop >> 11) & 0x03
                emboss = bool(prop & (1 << 13))
                engrave = bool(prop & (1 << 14))
                superscript = bool(prop & (1 << 15))
                subscript = bool(prop & (1 << 16))
                strikeout_shape = (prop >> 18) & 0x07
                emphasis = (prop >> 21) & 0x0F

                # Shadow offset
                shadow_offset_x = struct.unpack_from('<b', d, 50)[0] if len(d) >= 51 else 0
                shadow_offset_y = struct.unpack_from('<b', d, 51)[0] if len(d) >= 52 else 0

                # borderFillId
                border_fill_id = struct.unpack_from('<H', d, 68)[0] if len(d) >= 70 else 0

                results.append({
                    'font_ids': font_ids,
                    'ratios': ratios,
                    'spacings': spacings,
                    'rel_sizes': rel_sizes,
                    'offsets': offsets,
                    'height': base_size,
                    'prop': prop,
                    'text_color': text_color,
                    'underline_color': underline_color,
                    'shade_color': shade_color,
                    'shadow_color': shadow_color,
                    'italic': italic,
                    'bold': bold,
                    'underline_type': underline_type_val,
                    'underline_shape': underline_shape,
                    'outline_type': outline_type_val,
                    'shadow_type': shadow_type_val,
                    'shadow_offset_x': shadow_offset_x,
                    'shadow_offset_y': shadow_offset_y,
                    'emboss': emboss,
                    'engrave': engrave,
                    'superscript': superscript,
                    'subscript': subscript,
                    'strikeout_shape': strikeout_shape,
                    'emphasis': emphasis,
                    'border_fill_id': border_fill_id,
                })
        return results

    def _read_tab_defs(self) -> List[dict]:
        """Read HWPTAG_TAB_DEF records."""
        results = []
        for rec in self.docinfo_records:
            if rec['tag'] == _TAG_TAB_DEF:
                d = rec['data']
                auto_tab_left = False
                auto_tab_right = False
                if len(d) >= 4:
                    prop = struct.unpack_from('<I', d, 0)[0]
                    auto_tab_left = bool(prop & 0x01)
                    auto_tab_right = bool(prop & 0x02)
                results.append({
                    'auto_tab_left': auto_tab_left,
                    'auto_tab_right': auto_tab_right,
                    'raw': d,
                })
        return results

    def _read_numberings(self) -> List[dict]:
        """Read HWPTAG_NUMBERING records."""
        results = []
        for rec in self.docinfo_records:
            if rec['tag'] == _TAG_NUMBERING:
                d = rec['data']
                heads = []
                pos = 0
                for level in range(7):
                    if pos + 12 <= len(d):
                        align = struct.unpack_from('<I', d, pos)[0]
                        width_adjust = struct.unpack_from('<I', d, pos + 4)[0]
                        text_offset = struct.unpack_from('<H', d, pos + 8)[0]
                        num_format = struct.unpack_from('<H', d, pos + 10)[0]
                        heads.append({
                            'level': level + 1,
                            'align': align,
                            'num_format': num_format,
                            'text_offset': text_offset,
                        })
                        pos += 12
                start = 0
                if pos + 2 <= len(d):
                    start = struct.unpack_from('<H', d, pos)[0]
                results.append({'heads': heads, 'start': start})
        return results

    def _read_bullets(self) -> List[dict]:
        """Read HWPTAG_BULLET records."""
        results = []
        for rec in self.docinfo_records:
            if rec['tag'] == _TAG_BULLET:
                results.append({'raw': rec['data']})
        return results

    def _read_para_shapes(self) -> List[dict]:
        """Read all HWPTAG_PARA_SHAPE records."""
        results = []
        for rec in self.docinfo_records:
            if rec['tag'] == _TAG_PARA_SHAPE and len(rec['data']) >= 8:
                d = rec['data']
                prop1 = struct.unpack_from('<I', d, 0)[0]
                alignment = (prop1 >> 2) & 0x07  # bits 2-4
                break_latin = (prop1 >> 5) & 0x03
                break_nonlatin = (prop1 >> 7) & 0x01
                heading_type_val = (prop1 >> 16) & 0x03
                heading_level = (prop1 >> 18) & 0x07
                widow_orphan = bool(prop1 & (1 << 13))
                keep_with_next = bool(prop1 & (1 << 14))
                keep_lines = bool(prop1 & (1 << 15))
                page_break_before = bool(prop1 & (1 << 24))
                snap_to_grid = bool(prop1 & (1 << 26))

                left_margin = struct.unpack_from('<i', d, 4)[0] if len(d) >= 8 else 0
                right_margin = struct.unpack_from('<i', d, 8)[0] if len(d) >= 12 else 0
                indent = struct.unpack_from('<i', d, 12)[0] if len(d) >= 16 else 0
                prev_spacing = struct.unpack_from('<i', d, 16)[0] if len(d) >= 20 else 0
                next_spacing = struct.unpack_from('<i', d, 20)[0] if len(d) >= 24 else 0
                line_spacing = struct.unpack_from('<i', d, 24)[0] if len(d) >= 28 else 160

                tab_def_id = struct.unpack_from('<H', d, 28)[0] if len(d) >= 30 else 0
                numbering_id = struct.unpack_from('<H', d, 30)[0] if len(d) >= 32 else 0
                border_fill_id = struct.unpack_from('<H', d, 32)[0] if len(d) >= 34 else 0
                border_offset_left = struct.unpack_from('<H', d, 34)[0] if len(d) >= 36 else 0
                border_offset_right = struct.unpack_from('<H', d, 36)[0] if len(d) >= 38 else 0
                border_offset_top = struct.unpack_from('<H', d, 38)[0] if len(d) >= 40 else 0
                border_offset_bottom = struct.unpack_from('<H', d, 40)[0] if len(d) >= 42 else 0

                prop3 = struct.unpack_from('<I', d, 42)[0] if len(d) >= 46 else 0
                line_spacing_type_val = prop3 & 0x03
                e_asian_eng = bool(prop3 & (1 << 4))
                e_asian_num = bool(prop3 & (1 << 5))
                line_wrap_val = (prop3 >> 2) & 0x03

                results.append({
                    'alignment': alignment,
                    'break_latin': break_latin,
                    'break_nonlatin': break_nonlatin,
                    'heading_type': heading_type_val,
                    'heading_level': heading_level,
                    'widow_orphan': widow_orphan,
                    'keep_with_next': keep_with_next,
                    'keep_lines': keep_lines,
                    'page_break_before': page_break_before,
                    'snap_to_grid': snap_to_grid,
                    'left_margin': left_margin,
                    'right_margin': right_margin,
                    'indent': indent,
                    'prev_spacing': prev_spacing,
                    'next_spacing': next_spacing,
                    'line_spacing': line_spacing,
                    'tab_def_id': tab_def_id,
                    'numbering_id': numbering_id,
                    'border_fill_id': border_fill_id,
                    'border_offset_left': border_offset_left,
                    'border_offset_right': border_offset_right,
                    'border_offset_top': border_offset_top,
                    'border_offset_bottom': border_offset_bottom,
                    'line_spacing_type': line_spacing_type_val,
                    'e_asian_eng': e_asian_eng,
                    'e_asian_num': e_asian_num,
                    'line_wrap': line_wrap_val,
                })
        return results

    def _read_styles(self) -> List[dict]:
        """Read HWPTAG_STYLE records."""
        results = []
        for rec in self.docinfo_records:
            if rec['tag'] == _TAG_STYLE and len(rec['data']) >= 8:
                d = rec['data']
                pos = 0
                # Name (wchar string: 2-byte length + chars)
                if pos + 2 > len(d):
                    continue
                name_len = struct.unpack_from('<H', d, pos)[0]
                pos += 2
                name = ''
                if pos + name_len * 2 <= len(d):
                    name = d[pos:pos + name_len * 2].decode('utf-16-le', errors='replace')
                pos += name_len * 2

                # English name
                if pos + 2 > len(d):
                    results.append({'name': name, 'eng_name': '', 'type': 0,
                                    'next_style': 0, 'lang_id': 0,
                                    'para_pr_id': 0, 'char_pr_id': 0})
                    continue
                eng_name_len = struct.unpack_from('<H', d, pos)[0]
                pos += 2
                eng_name = ''
                if pos + eng_name_len * 2 <= len(d):
                    eng_name = d[pos:pos + eng_name_len * 2].decode('utf-16-le', errors='replace')
                pos += eng_name_len * 2

                # Properties
                style_type = 0
                next_style = 0
                lang_id = 0
                para_pr_id = 0
                char_pr_id = 0
                if pos + 1 <= len(d):
                    style_type = d[pos]
                    pos += 1
                if pos + 2 <= len(d):
                    next_style = struct.unpack_from('<H', d, pos)[0]
                    pos += 2
                if pos + 2 <= len(d):
                    lang_id = struct.unpack_from('<h', d, pos)[0]
                    pos += 2
                if pos + 2 <= len(d):
                    para_pr_id = struct.unpack_from('<H', d, pos)[0]
                    pos += 2
                if pos + 2 <= len(d):
                    char_pr_id = struct.unpack_from('<H', d, pos)[0]
                    pos += 2

                results.append({
                    'name': name,
                    'eng_name': eng_name,
                    'type': style_type,  # 0=PARA, 1=CHAR
                    'next_style': next_style,
                    'lang_id': lang_id,
                    'para_pr_id': para_pr_id,
                    'char_pr_id': char_pr_id,
                })
        return results

    def _read_bin_data_entries(self) -> Dict[int, str]:
        """Read HWPTAG_BIN_DATA entries, map ID -> extension."""
        result = {}
        idx = 0
        for rec in self.docinfo_records:
            if rec['tag'] == _TAG_BIN_DATA:
                d = rec['data']
                if len(d) >= 2:
                    prop = struct.unpack_from('<H', d, 0)[0]
                    data_type = prop & 0x0F
                    # For embedded: prop has extension info
                    ext = 'png'  # default
                    if data_type == 0:  # LINK
                        # absolute path follows
                        pass
                    elif data_type == 1:  # EMBEDDING
                        if len(d) >= 4:
                            ext_len = struct.unpack_from('<H', d, 2)[0]
                            if 4 + ext_len * 2 <= len(d):
                                ext = d[4:4 + ext_len * 2].decode('utf-16-le', errors='replace').lower()
                idx += 1
                result[idx] = ext
        return result

    def _read_summary(self) -> dict:
        """Read SummaryInformation (OLE property set)."""
        summary = {}
        try:
            if self.ole.exists('\x05SummaryInformation'):
                # Use olefile's get_metadata
                meta = self.ole.get_metadata()
                summary['title'] = getattr(meta, 'title', None) or ''
                summary['subject'] = getattr(meta, 'subject', None) or ''
                summary['author'] = getattr(meta, 'author', None) or ''
                summary['keywords'] = getattr(meta, 'keywords', None) or ''
                summary['comments'] = getattr(meta, 'comments', None) or ''
                summary['last_saved_by'] = getattr(meta, 'last_saved_by', None) or ''
                # Dates
                cd = getattr(meta, 'create_time', None)
                md = getattr(meta, 'last_saved_time', None)
                summary['created'] = cd.strftime('%Y-%m-%dT%H:%M:%S') if cd else ''
                summary['modified'] = md.strftime('%Y-%m-%dT%H:%M:%S') if md else ''
        except Exception:
            pass
        return summary

    def get_font_by_lang_and_id(self, lang_index: int, font_id: int) -> Optional[str]:
        """Get font face name by language index (0-6) and font ID within that language."""
        counts = self.id_mappings
        lang_keys = ['hangulFont', 'englishFont', 'hanjaFont', 'japaneseFont',
                     'etcFont', 'symbolFont', 'userFont']
        offset = 0
        for i, key in enumerate(lang_keys):
            cnt = counts.get(key, 0)
            if i == lang_index:
                idx = offset + font_id
                if 0 <= idx < len(self.face_names):
                    return self.face_names[idx]['face']
                return None
            offset += cnt
        return None


# ============================================================
# Record parsing utility
# ============================================================

def _parse_records(data: bytes) -> List[dict]:
    """Parse HWP binary data into record list."""
    records = []
    pos = 0
    while pos < len(data):
        if pos + 4 > len(data):
            break
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
        records.append({
            'tag': tag_id, 'level': level, 'size': size,
            'data': data[pos:pos + size]
        })
        pos += size
    return records


# ============================================================
# HWPX Builder
# ============================================================

def _build_hwpx(hwp: _HWPDocument) -> Any:
    """Build an HWPXFile from parsed HWP data."""
    from .hwpx_file import HWPXFile
    from .objects.header.header_xml_file import HeaderXMLFile
    from .objects.section.section_xml_file import SectionXMLFile
    from .tools.blank_file_maker import BlankFileMaker

    # Start from a blank file for proper structure
    hwpx = BlankFileMaker.make()

    # Overwrite with HWP data
    _build_version(hwpx, hwp)
    _build_container(hwpx, hwp)
    _build_content_hpf(hwpx, hwp)
    _build_header(hwpx, hwp)
    _build_sections(hwpx, hwp)
    _build_settings(hwpx, hwp)

    hwp.close()
    return hwpx


# ============================================================
# 1. VERSION XML
# ============================================================

def _build_version(hwpx, hwp: _HWPDocument):
    from .objects.root.version import TargetApplicationSort
    v = hwpx.version_xml_file
    v.target_application = TargetApplicationSort.WordProcessor
    v.application = "Hancom Office Hangul"
    v.app_version = "9, 1, 1, 5656 WIN32LEWindows_Unknown_Version"
    v.version.major = hwp.version_mm
    v.version.minor = hwp.version_nn
    v.version.micro = hwp.version_pp
    v.version.build_number = hwp.version_rr
    v.version.os = "1"


# ============================================================
# 2. CONTAINER XML
# ============================================================

def _build_container(hwpx, hwp: _HWPDocument):
    container = hwpx.container_xml_file
    # Already created by BlankFileMaker; add PrvText if needed
    if container.root_files is not None:
        # Check if PrvText exists
        has_prv = False
        for rf in container.root_files.items():
            if rf.full_path == "Preview/PrvText.txt":
                has_prv = True
        if not has_prv:
            rf = container.root_files.add_new()
            rf.full_path = "Preview/PrvText.txt"
            rf.media_type = "text/plain"


# ============================================================
# 3. CONTENT HPF
# ============================================================

def _build_content_hpf(hwpx, hwp: _HWPDocument):
    from .value_convertor import media_type as _media_type

    hpf = hwpx.content_hpf_file
    hpf.version = ""
    hpf.unique_identifier = ""
    hpf.id = ""

    # MetaData from Summary
    md = hpf.create_meta_data()
    title = md.create_title()
    if hwp.summary.get('title'):
        title.add_text(hwp.summary['title'])
    lang = md.create_language()
    lang.add_text("ko")

    _add_meta(md, "creator", "text", hwp.summary.get('author'))
    _add_meta(md, "subject", "text", hwp.summary.get('subject'))
    _add_meta(md, "description", "text", hwp.summary.get('comments'))
    _add_meta(md, "lastsaveby", "text", hwp.summary.get('last_saved_by'))

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    _add_meta(md, "CreatedDate", "text", hwp.summary.get('created') or now_str)
    _add_meta(md, "ModifiedDate", "text", hwp.summary.get('modified') or now_str)
    _add_meta(md, "date", "text", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    _add_meta(md, "keyword", "text", hwp.summary.get('keywords'))

    # Manifest
    manifest = hpf.create_manifest()
    item = manifest.add_new()
    item.id = "header"
    item.href = "Contents/header.xml"
    item.media_type = "application/xml"

    for i in range(hwp.section_count):
        item = manifest.add_new()
        item.id = f"section{i}"
        item.href = f"Contents/section{i}.xml"
        item.media_type = "application/xml"

    item = manifest.add_new()
    item.id = "settings"
    item.href = "settings.xml"
    item.media_type = "application/xml"

    # Binary data items
    bin_data_id_map = {}
    for bin_id, ext in hwp.bin_data_ids.items():
        hex_id = f"BIN{bin_id:04X}"
        item_id = f"bindata{bin_id}"
        href = f"BinData/{hex_id}.{ext}"
        item = manifest.add_new()
        item.id = item_id
        item.href = href
        item.media_type = _media_type(ext)
        bin_data_id_map[bin_id] = item_id

    # Spine
    spine = hpf.create_spine()
    ref = spine.add_new()
    ref.idref = "header"
    ref.linear = "yes"

    for i in range(hwp.section_count):
        ref = spine.add_new()
        ref.idref = f"section{i}"
        ref.linear = "yes"


def _add_meta(md, name: str, content: str, text: Optional[str]) -> None:
    m = md.add_new_meta()
    m.name = name
    m.content = content
    if text is not None:
        m.text = text


# ============================================================
# 4. HEADER XML
# ============================================================

def _build_header(hwpx, hwp: _HWPDocument):
    from .objects.header.header_xml_file import HeaderXMLFile
    from .objects.header.enum_types import TargetProgramSort

    header = HeaderXMLFile()
    hwpx.header_xml_file = header
    header.version = "1.4"
    header.secCnt = hwp.section_count

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
    _build_fontfaces(ref_list, hwp)
    _build_border_fills(ref_list, hwp)
    _build_char_properties(ref_list, hwp)
    _build_tab_properties(ref_list, hwp)
    _build_numberings(ref_list, hwp)
    _build_para_properties(ref_list, hwp)
    _build_styles(ref_list, hwp)

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
# 4a. Fontfaces
# ============================================================

def _build_fontfaces(ref_list, hwp: _HWPDocument):
    from .objects.header.enum_types import FontType, LanguageType
    from .value_convertor import font_type as _font_type

    fontfaces = ref_list.create_fontfaces()
    counts = hwp.id_mappings
    lang_keys = ['hangulFont', 'englishFont', 'hanjaFont', 'japaneseFont',
                 'etcFont', 'symbolFont', 'userFont']
    lang_types = [
        LanguageType.HANGUL, LanguageType.LATIN, LanguageType.HANJA,
        LanguageType.JAPANESE, LanguageType.OTHER, LanguageType.SYMBOL,
        LanguageType.USER,
    ]

    offset = 0
    for lang_idx, (key, lang_type) in enumerate(zip(lang_keys, lang_types)):
        cnt = counts.get(key, 0)
        ff = fontfaces.add_new_fontface()
        ff.lang = lang_type

        for i in range(cnt):
            fn_idx = offset + i
            if fn_idx < len(hwp.face_names):
                fn_data = hwp.face_names[fn_idx]
                font = ff.add_new_font()
                font.id = str(i)
                font.face = fn_data['face']
                font.type = FontType.TTF
                font.isEmbedded = False
        offset += cnt


# ============================================================
# 4b. BorderFills
# ============================================================

def _build_border_fills(ref_list, hwp: _HWPDocument):
    from .objects.header.enum_types import (
        CenterLineSort, HatchStyle, LineType2, LineWidth, SlashType,
    )
    from .value_convertor import (
        color_from_int, line_type2 as _lt2, line_width as _lw,
    )

    bf_list = ref_list.create_border_fills()

    if not hwp.border_fills:
        # Create a minimal default borderFill
        bf = bf_list.add_new()
        _make_default_border_fill(bf, "1")
        return

    for idx, bf_data in enumerate(hwp.border_fills):
        bf = bf_list.add_new()
        bf_id = str(idx + 1)
        bf.id = bf_id
        bf.threeD = bool(bf_data['prop'] & (1 << 0))
        bf.shadow = bool(bf_data['prop'] & (1 << 1))
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

        # 4 borders
        border_creators = [
            bf.create_left_border, bf.create_right_border,
            bf.create_top_border, bf.create_bottom_border,
        ]
        for i, create_fn in enumerate(border_creators):
            b = create_fn()
            bd = bf_data['borders'][i] if i < len(bf_data['borders']) else {}
            b.type = LineType2.from_string(_lt2(bd.get('type', 0)))
            b.width = LineWidth.from_index(bd.get('width', 0))
            b.color = color_from_int(bd.get('color', 0))

        # Diagonal
        diag = bf.create_diagonal()
        dd = bf_data.get('diagonal', {})
        diag.type = LineType2.from_string(_lt2(dd.get('type', 1)))
        diag.width = LineWidth.from_index(dd.get('width', 0))
        diag.color = color_from_int(dd.get('color', 0))

        # FillBrush (winBrush with faceColor for background)
        if bf_data.get('fill_face_color') is not None:
            fill_brush = bf.create_fill_brush()
            wb = fill_brush.create_win_brush()
            face_color = color_from_int(bf_data['fill_face_color'])
            hatch_color = color_from_int(bf_data.get('fill_hatch_color', 0))
            wb.faceColor = face_color
            wb.hatchColor = hatch_color
            wb.alpha = 0.0


def _make_default_border_fill(bf, bf_id: str):
    from .objects.header.enum_types import (
        CenterLineSort, LineType2, LineWidth, SlashType,
    )
    bf.id = bf_id
    bf.threeD = False
    bf.shadow = False
    bf.centerLine = CenterLineSort.NONE
    bf.breakCellSeparateLine = False
    slash = bf.create_slash()
    slash.type = SlashType.NONE
    slash.Crooked = False
    slash.isCounter = False
    bs = bf.create_back_slash()
    bs.type = SlashType.NONE
    bs.Crooked = False
    bs.isCounter = False
    for create_fn in [bf.create_left_border, bf.create_right_border,
                      bf.create_top_border, bf.create_bottom_border]:
        b = create_fn()
        b.type = LineType2.NONE
        b.width = LineWidth.MM_0_1
        b.color = "#000000"
    diag = bf.create_diagonal()
    diag.type = LineType2.SOLID
    diag.width = LineWidth.MM_0_1
    diag.color = "#000000"


# ============================================================
# 4c. CharProperties
# ============================================================

def _build_char_properties(ref_list, hwp: _HWPDocument):
    from .objects.header.enum_types import (
        CharShadowType, LineType1, LineType2, LineType3, SymMarkSort,
        UnderlineType,
    )
    from .objects.header.header_xml_file import NoAttributeNoChild
    from .object_type import ObjectType
    from .value_convertor import (
        color_from_int, emphasis_sort, outline_type, ref_id,
        shadow_type, underline_type,
    )

    cp_list = ref_list.create_char_properties()

    if not hwp.char_shapes:
        # Create a minimal default
        cp = cp_list.add_new()
        cp.id = "0"
        cp.height = 1000
        cp.textColor = "#000000"
        cp.shadeColor = "none"
        cp.useFontSpace = False
        cp.useKerning = False
        cp.symMark = SymMarkSort.NONE
        cp.borderFillIDRef = "0"
        fr = cp.create_font_ref()
        fr.set_all("0")
        cp.create_ratio().set_all(100)
        cp.create_spacing().set_all(0)
        cp.create_rel_sz().set_all(100)
        cp.create_offset().set_all(0)
        so = cp.create_strikeout()
        so.shape = "NONE"
        so.color = "#000000"
        return

    for idx, cs in enumerate(hwp.char_shapes):
        cp = cp_list.add_new()
        cp.id = str(idx)
        cp.height = cs['height']
        cp.textColor = color_from_int(cs['text_color'])
        cp.shadeColor = color_from_int(cs.get('shade_color', 0xFFFFFFFF))
        cp.useFontSpace = False
        cp.useKerning = False
        cp.symMark = SymMarkSort.from_string(emphasis_sort(cs.get('emphasis', 0)))
        cp.borderFillIDRef = ref_id(cs.get('border_fill_id', 0))

        # FontRef: map each language's font_id to its string ID
        fr = cp.create_font_ref()
        font_ids = cs.get('font_ids', [0] * 7)
        while len(font_ids) < 7:
            font_ids.append(0)
        fr.set(str(font_ids[0]), str(font_ids[1]), str(font_ids[2]),
               str(font_ids[3]), str(font_ids[4]), str(font_ids[5]),
               str(font_ids[6]))

        # Ratio
        ratios = cs.get('ratios', [100] * 7)
        while len(ratios) < 7:
            ratios.append(100)
        cp.create_ratio().set(ratios[0], ratios[1], ratios[2],
                              ratios[3], ratios[4], ratios[5], ratios[6])

        # Spacing
        spacings = cs.get('spacings', [0] * 7)
        while len(spacings) < 7:
            spacings.append(0)
        cp.create_spacing().set(spacings[0], spacings[1], spacings[2],
                                spacings[3], spacings[4], spacings[5], spacings[6])

        # RelSz
        rel_sizes = cs.get('rel_sizes', [100] * 7)
        while len(rel_sizes) < 7:
            rel_sizes.append(100)
        cp.create_rel_sz().set(rel_sizes[0], rel_sizes[1], rel_sizes[2],
                               rel_sizes[3], rel_sizes[4], rel_sizes[5], rel_sizes[6])

        # Offset
        offsets = cs.get('offsets', [0] * 7)
        while len(offsets) < 7:
            offsets.append(0)
        cp.create_offset().set(offsets[0], offsets[1], offsets[2],
                               offsets[3], offsets[4], offsets[5], offsets[6])

        # Bold / Italic
        if cs.get('bold'):
            cp.create_bold()
        if cs.get('italic'):
            cp.create_italic()

        # Underline
        ul = cp.create_underline()
        ul_type_str = underline_type(cs.get('underline_type', 0))
        ul.type = UnderlineType.from_string(ul_type_str)
        ul_shape_str = _line_type3_str(cs.get('underline_shape', 0))
        ul.shape = LineType3.from_string(ul_shape_str)
        ul.color = color_from_int(cs.get('underline_color', 0))

        # Strikeout
        so = cp.create_strikeout()
        so_shape_val = cs.get('strikeout_shape', 0)
        so.shape = _line_type2_str(so_shape_val)
        so.color = color_from_int(cs.get('text_color', 0))

        # Outline
        ol = cp.create_outline()
        ol_type_str = outline_type(cs.get('outline_type', 0))
        ol.type = LineType1.from_string(ol_type_str)

        # Shadow
        sh = cp.create_shadow()
        sh_type_str = shadow_type(cs.get('shadow_type', 0))
        sh.type = CharShadowType.from_string(sh_type_str)
        sh.color = color_from_int(cs.get('shadow_color', 0xB2B2B2))
        sh.offsetX = cs.get('shadow_offset_x', 10)
        sh.offsetY = cs.get('shadow_offset_y', 10)

        # Emboss / Engrave
        if cs.get('emboss'):
            cp.create_emboss()
        if cs.get('engrave'):
            cp.create_engrave()

        # Superscript / Subscript
        if cs.get('superscript'):
            cp.create_supscript()
        if cs.get('subscript'):
            cp.create_subscript()


def _line_type2_str(val: int) -> str:
    """Convert int to LineType2 string value for strikeout."""
    from .value_convertor import line_type2
    return line_type2(val)


def _line_type3_str(val: int) -> str:
    """Convert int to LineType3 string value for underline shape."""
    from .value_convertor import line_type3
    return line_type3(val)


# ============================================================
# 4d. TabProperties
# ============================================================

def _build_tab_properties(ref_list, hwp: _HWPDocument):
    tp_list = ref_list.create_tab_properties()

    if not hwp.tab_defs:
        # Default: one tab definition
        tp = tp_list.add_new()
        tp.id = "0"
        tp.autoTabLeft = False
        tp.autoTabRight = False
        return

    for idx, td in enumerate(hwp.tab_defs):
        tp = tp_list.add_new()
        tp.id = str(idx)
        tp.autoTabLeft = td.get('auto_tab_left', False)
        tp.autoTabRight = td.get('auto_tab_right', False)


# ============================================================
# 4e. Numberings
# ============================================================

def _build_numberings(ref_list, hwp: _HWPDocument):
    from .objects.header.enum_types import HorizontalAlign1, NumberType1, ValueUnit1
    from .value_convertor import number_type1

    num_list = ref_list.create_numberings()

    if not hwp.numberings:
        # Default numbering
        num = num_list.add_new()
        num.id = "1"
        num.start = 0
        ph = num.add_new_para_head()
        ph.level = 1
        ph.start = 1
        ph.align = HorizontalAlign1.LEFT
        ph.useInstWidth = True
        ph.autoIndent = True
        ph.widthAdjust = 0
        ph.textOffsetType = ValueUnit1.PERCENT
        ph.textOffset = 50
        ph.numFormat = NumberType1.DIGIT
        ph.charPrIDRef = "4294967295"
        ph.checkable = False
        ph.text = "^1."
        return

    for idx, nd in enumerate(hwp.numberings):
        num = num_list.add_new()
        num.id = str(idx + 1)
        num.start = nd.get('start', 0)

        for hd in nd.get('heads', []):
            ph = num.add_new_para_head()
            ph.level = hd.get('level', 1)
            ph.start = 1
            ph.align = HorizontalAlign1.LEFT
            ph.useInstWidth = True
            ph.autoIndent = True
            ph.widthAdjust = 0
            ph.textOffsetType = ValueUnit1.PERCENT
            ph.textOffset = hd.get('text_offset', 50)
            nf_str = number_type1(hd.get('num_format', 0))
            ph.numFormat = NumberType1.from_string(nf_str)
            ph.charPrIDRef = "4294967295"
            ph.checkable = False


# ============================================================
# 4f. ParaProperties
# ============================================================

def _build_para_properties(ref_list, hwp: _HWPDocument):
    from .objects.header.enum_types import (
        HorizontalAlign2, LineBreakForLatin, LineBreakForNonLatin,
        LineSpacingType, LineWrap, ParaHeadingType, ValueUnit2,
        VerticalAlign1,
    )
    from .value_convertor import (
        break_latin_word, break_non_latin_word, heading_type,
        horizontal_align, line_spacing_type, line_wrap, ref_id,
    )

    pp_list = ref_list.create_para_properties()

    if not hwp.para_shapes:
        # Create one default paraPr
        pp = pp_list.add_new()
        pp.id = "0"
        pp.tabPrIDRef = "0"
        pp.condense = 0
        pp.fontLineHeight = False
        pp.snapToGrid = True
        pp.suppressLineNumbers = False
        pp.checked = False
        a = pp.create_align()
        a.horizontal = HorizontalAlign2.JUSTIFY
        a.vertical = VerticalAlign1.BASELINE
        h = pp.create_heading()
        h.type = ParaHeadingType.NONE
        h.idRef = "0"
        h.level = 0
        bs = pp.create_break_setting()
        bs.breakLatinWord = LineBreakForLatin.KEEP_WORD
        bs.breakNonLatinWord = LineBreakForNonLatin.BREAK_WORD
        bs.widowOrphan = False
        bs.keepWithNext = False
        bs.keepLines = False
        bs.pageBreakBefore = False
        bs.lineWrap = LineWrap.BREAK
        auto = pp.create_auto_spacing()
        auto.eAsianEng = False
        auto.eAsianNum = False
        margin = pp.create_margin()
        for attr, create_fn in [('intent', margin.create_intent),
                                ('left', margin.create_left),
                                ('right', margin.create_right),
                                ('prev', margin.create_prev),
                                ('next', margin.create_next)]:
            v = create_fn()
            v.value = 0
            v.unit = ValueUnit2.HWPUNIT.value
        ls = pp.create_line_spacing()
        ls.type = LineSpacingType.PERCENT
        ls.value = 160
        ls.unit = ValueUnit2.HWPUNIT
        border = pp.create_border()
        border.borderFillIDRef = "1"
        border.offsetLeft = 0
        border.offsetRight = 0
        border.offsetTop = 0
        border.offsetBottom = 0
        border.connect = False
        border.ignoreMargin = False
        return

    for idx, ps in enumerate(hwp.para_shapes):
        pp = pp_list.add_new()
        pp.id = str(idx)
        pp.tabPrIDRef = str(ps.get('tab_def_id', 0))
        pp.condense = 0
        pp.fontLineHeight = False
        pp.snapToGrid = ps.get('snap_to_grid', True)
        pp.suppressLineNumbers = False
        pp.checked = False

        # Align
        a = pp.create_align()
        a.horizontal = HorizontalAlign2.from_string(horizontal_align(ps['alignment']))
        a.vertical = VerticalAlign1.BASELINE

        # Heading
        h = pp.create_heading()
        h.type = ParaHeadingType.from_string(heading_type(ps.get('heading_type', 0)))
        h.idRef = ref_id(ps.get('numbering_id', 0))
        h.level = ps.get('heading_level', 0)

        # BreakSetting
        bs = pp.create_break_setting()
        bs.breakLatinWord = LineBreakForLatin.from_string(
            break_latin_word(ps.get('break_latin', 0)))
        bs.breakNonLatinWord = LineBreakForNonLatin.from_string(
            break_non_latin_word(ps.get('break_nonlatin', 0)))
        bs.widowOrphan = ps.get('widow_orphan', False)
        bs.keepWithNext = ps.get('keep_with_next', False)
        bs.keepLines = ps.get('keep_lines', False)
        bs.pageBreakBefore = ps.get('page_break_before', False)
        lw_str = line_wrap(ps.get('line_wrap', 0))
        bs.lineWrap = LineWrap.from_string(lw_str)

        # AutoSpacing
        auto = pp.create_auto_spacing()
        auto.eAsianEng = ps.get('e_asian_eng', False)
        auto.eAsianNum = ps.get('e_asian_num', False)

        # Margin
        margin = pp.create_margin()
        _set_margin_value(margin.create_intent(), ps.get('indent', 0))
        _set_margin_value(margin.create_left(), ps.get('left_margin', 0))
        _set_margin_value(margin.create_right(), ps.get('right_margin', 0))
        _set_margin_value(margin.create_prev(), ps.get('prev_spacing', 0))
        _set_margin_value(margin.create_next(), ps.get('next_spacing', 0))

        # LineSpacing
        ls = pp.create_line_spacing()
        ls_type_str = line_spacing_type(ps.get('line_spacing_type', 0))
        ls.type = LineSpacingType.from_string(ls_type_str)
        ls.value = ps.get('line_spacing', 160)
        ls.unit = ValueUnit2.HWPUNIT

        # Border
        border = pp.create_border()
        border.borderFillIDRef = ref_id(ps.get('border_fill_id', 1))
        border.offsetLeft = ps.get('border_offset_left', 0)
        border.offsetRight = ps.get('border_offset_right', 0)
        border.offsetTop = ps.get('border_offset_top', 0)
        border.offsetBottom = ps.get('border_offset_bottom', 0)
        border.connect = False
        border.ignoreMargin = False


def _set_margin_value(vu, value: int):
    from .objects.header.enum_types import ValueUnit2
    vu.value = value
    vu.unit = ValueUnit2.HWPUNIT.value


# ============================================================
# 4g. Styles
# ============================================================

def _build_styles(ref_list, hwp: _HWPDocument):
    from .objects.header.enum_types import StyleType
    from .value_convertor import ref_id

    st_list = ref_list.create_styles()

    if not hwp.styles:
        # Default style
        s = st_list.add_new()
        s.id = "0"
        s.type = StyleType.PARA
        s.name = "바탕글"
        s.engName = "Normal"
        s.paraPrIDRef = "0"
        s.charPrIDRef = "0"
        s.nextStyleIDRef = "0"
        s.langID = "1042"
        s.lockForm = False
        return

    for idx, sd in enumerate(hwp.styles):
        s = st_list.add_new()
        s.id = str(idx)
        s.type = StyleType.PARA if sd.get('type', 0) == 0 else StyleType.CHAR
        s.name = sd.get('name', '')
        s.engName = sd.get('eng_name', '')
        s.paraPrIDRef = ref_id(sd.get('para_pr_id', 0))
        s.charPrIDRef = ref_id(sd.get('char_pr_id', 0))
        s.nextStyleIDRef = ref_id(sd.get('next_style', 0))
        s.langID = str(sd.get('lang_id', 1042))
        s.lockForm = False


# ============================================================
# 5. SECTIONS
# ============================================================

def _build_sections(hwpx, hwp: _HWPDocument):
    from .objects.section.section_xml_file import SectionXMLFile

    # Remove existing sections from blank file
    while hwpx.section_xml_file_list.count() > 0:
        hwpx.section_xml_file_list.remove(0)

    for sec_idx in range(hwp.section_count):
        section = SectionXMLFile()
        hwpx.section_xml_file_list.add(section)
        _build_section(section, hwp, sec_idx)


def _group_paragraphs(records: List[dict]) -> List[List[dict]]:
    """Group records into paragraph groups (PARA_HEADER starts each group).

    Only top-level PARA_HEADER records (at the minimum level found) start new
    groups.  Deeper PARA_HEADERs (e.g. inside table cells) are kept inside the
    current group so that the table builder can process them.
    """
    if not records:
        return []

    # Determine the minimum level of PARA_HEADER records in this section.
    min_level = None
    for rec in records:
        if rec['tag'] == _TAG_PARA_HEADER:
            lvl = rec.get('level', 0)
            if min_level is None or lvl < min_level:
                min_level = lvl
    if min_level is None:
        return [records]

    groups: List[List[dict]] = []
    current: List[dict] = []
    for rec in records:
        if rec['tag'] == _TAG_PARA_HEADER and rec.get('level', 0) == min_level:
            if current:
                groups.append(current)
            current = [rec]
        else:
            current.append(rec)
    if current:
        groups.append(current)
    return groups


# ============================================================
# Table builder
# ============================================================

# Control type ID for table in control records (first 4 bytes of data).
# In HWP 5.x binary, extended controls (section def, column def, table, etc.)
# use tag 71 (LIST_HEADER) with a 4-byte control ID at the start of the data.
_CTRL_ID_TABLE = 0x74626C20  # bytes ' lbt' read as uint32-LE

# Tag used for extended control records (section/column/table/etc.) in actual HWP files.
# CTRL_HEADER (tag 71) records whose first 4 bytes identify the control type.
_TAG_EXTENDED_CTRL = _TAG_CTRL_HEADER  # 71

# Tag used for TABLE properties record (row/col counts, spacing, margins)
_TAG_TABLE_PROPS = 77  # HWPTAG_BEGIN + 61

# Tag used for cell LIST_HEADER records (cell addr, span, size, margins)
_TAG_CELL_LIST_HEADER = 72  # HWPTAG_BEGIN + 56


def _find_ctrl_headers_in_group(pg: List[dict]) -> List[int]:
    """Return indices (into *pg*) of all extended control records at level == para_level+1.

    In HWP 5.x binary format, extended controls (table, section def, column def,
    etc.) are stored as tag-71 records whose first 4 bytes encode the control type.
    """
    if not pg:
        return []
    para_level = pg[0].get('level', 0)
    ctrl_level = para_level + 1
    indices = []
    for i, rec in enumerate(pg):
        if rec['tag'] == _TAG_EXTENDED_CTRL and rec.get('level', 0) == ctrl_level:
            # Verify it has a 4-byte control ID (not a plain list header)
            if len(rec['data']) >= 4:
                indices.append(i)
    return indices


def _is_table_ctrl(rec_data: bytes) -> bool:
    """Check whether an extended control record is for a table."""
    if len(rec_data) < 4:
        return False
    ctrl_id = struct.unpack_from('<I', rec_data, 0)[0]
    return ctrl_id == _CTRL_ID_TABLE


def _collect_sub_records(pg: List[dict], ctrl_idx: int) -> List[dict]:
    """Collect all records that belong to the control starting at *ctrl_idx*.

    These are the records immediately following pg[ctrl_idx] whose level is
    greater than pg[ctrl_idx]['level'].
    """
    ctrl_level = pg[ctrl_idx].get('level', 0)
    result = []
    for rec in pg[ctrl_idx + 1:]:
        if rec.get('level', 0) > ctrl_level:
            result.append(rec)
        else:
            break
    return result


def _build_table_object(sub_records: List[dict], ctrl_rec: dict,
                        hwp: '_HWPDocument') -> Any:
    """Build a Table object from the CTRL_HEADER + sub-records.

    Parameters
    ----------
    sub_records : list[dict]
        Records after the CTRL_HEADER that belong to the table (TABLE, LIST_HEADER, etc.)
    ctrl_rec : dict
        The CTRL_HEADER record itself (for position/size info)
    hwp : _HWPDocument
        The source document (for char shape lookups)

    Returns
    -------
    Table object ready to add to a Run
    """
    from .objects.section.objects.table import Table, Tr, Tc, CellAddr, CellSpan
    from .objects.section.objects.drawing_object import ShapeSize, ShapePosition
    from .objects.common.base_objects import LeftRightTopBottom, WidthAndHeight
    from .objects.section.section_xml_file import SubList
    from .objects.section.paragraph import Para, Run, T
    from .objects.section.enum_types import (
        NumberingType, TablePageBreak, TextDirection,
        TextFlowSide, TextWrapMethod, WidthRelTo, HeightRelTo,
        LineWrapMethod, VerticalAlign2,
    )
    from .object_type import ObjectType

    tbl = Table()

    # --- Parse CTRL_HEADER for position/size ---
    cd = ctrl_rec['data']
    if len(cd) >= 30:
        # ctrl_id(4) + property(4) + yOffset(4) + xOffset(4) + width(4) + height(4) + zOrder(4) = 28 min
        prop = struct.unpack_from('<I', cd, 4)[0]
        y_off = struct.unpack_from('<i', cd, 8)[0]
        x_off = struct.unpack_from('<i', cd, 12)[0]
        width = struct.unpack_from('<I', cd, 16)[0]
        height = struct.unpack_from('<I', cd, 20)[0]
        z_order = struct.unpack_from('<i', cd, 24)[0]

        # Instance ID (after zOrder + outer margins)
        instance_id = 0
        if len(cd) >= 40:
            instance_id = struct.unpack_from('<I', cd, 36)[0]
        tbl.so_id = str(instance_id) if instance_id else ""
        tbl.z_order = z_order
        tbl.numbering_type = NumberingType.TABLE
        tbl.lock = False

        # Property bit 0 = treatAsChar (isLikeWord)
        treat_as_char = bool(prop & 0x01)

        # For tables, use standard defaults matching Java output
        # (property bit layout for textWrap/textFlow/position is complex
        # and position info is read from separate fields after the property)
        tbl.text_wrap = "TOP_AND_BOTTOM"
        tbl.text_flow = "BOTH_SIDES"

        # Size
        sz = tbl.create_sz()
        sz.width = width
        sz.height = height
        sz.width_rel_to = WidthRelTo.ABSOLUTE
        sz.height_rel_to = HeightRelTo.ABSOLUTE
        sz.protect = False

        try:
            tbl.dropcap_style = "None"
        except AttributeError:
            pass
        try:
            tbl.dropcapstyle = "None"
        except AttributeError:
            pass

        # Position - use defaults for treatAsChar tables
        pos = tbl.create_pos()
        pos.treat_as_char = treat_as_char
        pos.affect_line_spacing = False
        pos.flow_with_text = treat_as_char  # typically true when treatAsChar
        pos.allow_overlap = False
        pos.hold_anchor_and_so = False
        pos.vert_rel_to = "PARA"
        pos.horz_rel_to = "PARA"
        pos.vert_align = "TOP"
        pos.horz_align = "LEFT"
        pos.vert_offset = y_off
        pos.horz_offset = x_off

        # Outer margin
        if len(cd) >= 36:
            om_left = struct.unpack_from('<H', cd, 28)[0]
            om_right = struct.unpack_from('<H', cd, 30)[0]
            om_top = struct.unpack_from('<H', cd, 32)[0]
            om_bottom = struct.unpack_from('<H', cd, 34)[0]
            om = tbl.create_out_margin()
            om.left = om_left
            om.right = om_right
            om.top = om_top
            om.bottom = om_bottom

    # --- Find TABLE properties record (tag 77) ---
    table_rec = None
    ctrl_level = ctrl_rec.get('level', 0)
    for rec in sub_records:
        if rec['tag'] == _TAG_TABLE_PROPS and rec.get('level', 0) == ctrl_level + 1:
            table_rec = rec
            break

    row_count = 0
    col_count = 0
    cell_spacing = 0
    border_fill_id = 2
    tbl_in_margin = (141, 141, 141, 141)

    if table_rec and len(table_rec['data']) >= 14:
        td = table_rec['data']
        tbl_prop = struct.unpack_from('<I', td, 0)[0]
        row_count = struct.unpack_from('<H', td, 4)[0]
        col_count = struct.unpack_from('<H', td, 6)[0]
        cell_spacing = struct.unpack_from('<H', td, 8)[0]

        # Inner margins
        if len(td) >= 18:
            im_left = struct.unpack_from('<H', td, 10)[0]
            im_right = struct.unpack_from('<H', td, 12)[0]
            im_top = struct.unpack_from('<H', td, 14)[0]
            im_bottom = struct.unpack_from('<H', td, 16)[0]
            tbl_in_margin = (im_left, im_right, im_top, im_bottom)

        # Skip rowCount x uint16 (cells per row), then borderFillId
        skip_offset = 18 + row_count * 2
        if len(td) >= skip_offset + 2:
            border_fill_id = struct.unpack_from('<H', td, skip_offset)[0]

        # Page break from tbl_prop bits 1-2
        pb_val = (tbl_prop >> 1) & 0x03
        pb_map = {0: TablePageBreak.NONE, 1: TablePageBreak.CELL, 2: TablePageBreak.TABLE}
        tbl.page_break = pb_map.get(pb_val, TablePageBreak.TABLE)

        # Repeat header from tbl_prop bit 26 (isAutoRepeatTitleRow)
        tbl.repeat_header = bool(tbl_prop & (1 << 26))

    tbl.row_cnt = row_count
    tbl.col_cnt = col_count
    tbl.cell_spacing = cell_spacing
    tbl.border_fill_id_ref = str(border_fill_id)
    tbl.no_adjust = False

    # Inner margin
    im = tbl.create_in_margin()
    im.left = tbl_in_margin[0]
    im.right = tbl_in_margin[1]
    im.top = tbl_in_margin[2]
    im.bottom = tbl_in_margin[3]

    # --- Collect cell LIST_HEADER records (tag 72) at ctrl_level+1 ---
    # First, find all cell record indices
    cell_record_indices = []
    for i, rec in enumerate(sub_records):
        if rec['tag'] == _TAG_CELL_LIST_HEADER and rec.get('level', 0) == ctrl_level + 1:
            cell_record_indices.append(i)

    # For each cell, collect sub-records from after the cell header until the
    # next cell header (or end of sub_records). Cell content records (PARA_HEADER
    # etc.) may be at the same level as the cell header itself.
    cell_infos = []  # list of (list_header_rec, cell_sub_records)
    for ci_idx, ci in enumerate(cell_record_indices):
        # End boundary: next cell record index, or end of sub_records
        if ci_idx + 1 < len(cell_record_indices):
            end_idx = cell_record_indices[ci_idx + 1]
        else:
            end_idx = len(sub_records)
        cell_subs = sub_records[ci + 1:end_idx]
        cell_infos.append((sub_records[ci], cell_subs))

    # --- Organize cells into rows and build Tr/Tc ---
    # Build a dict: row_index -> list of (col_index, list_header_data, cell_subs)
    rows_dict: Dict[int, list] = {}
    for lh_rec, cell_subs in cell_infos:
        lhd = lh_rec['data']
        if len(lhd) < 34:
            continue
        # Cell LIST_HEADER format (HWP 5.x):
        # paraCount(uint32) + property(uint32) + colAddr(uint16) + rowAddr(uint16)
        # + colSpan(uint16) + rowSpan(uint16) + width(uint32) + height(uint32)
        # + leftMargin(uint16) + rightMargin(uint16) + topMargin(uint16) + bottomMargin(uint16)
        # + borderFillId(uint16)
        para_count = struct.unpack_from('<I', lhd, 0)[0]
        cell_prop = struct.unpack_from('<I', lhd, 4)[0]
        col_idx = struct.unpack_from('<H', lhd, 8)[0]
        row_idx = struct.unpack_from('<H', lhd, 10)[0]
        col_span = struct.unpack_from('<H', lhd, 12)[0]
        row_span = struct.unpack_from('<H', lhd, 14)[0]
        cell_width = struct.unpack_from('<I', lhd, 16)[0]
        cell_height = struct.unpack_from('<I', lhd, 20)[0]

        cell_margin = (141, 141, 141, 141)
        cell_border_fill_id = 1
        cm_left = struct.unpack_from('<H', lhd, 24)[0]
        cm_right = struct.unpack_from('<H', lhd, 26)[0]
        cm_top = struct.unpack_from('<H', lhd, 28)[0]
        cm_bottom = struct.unpack_from('<H', lhd, 30)[0]
        cell_margin = (cm_left, cm_right, cm_top, cm_bottom)
        cell_border_fill_id = struct.unpack_from('<H', lhd, 32)[0]

        # Vertical alignment from cell_prop bits 5-6
        vert_align_val = (cell_prop >> 5) & 0x03
        vert_map = {0: VerticalAlign2.TOP, 1: VerticalAlign2.CENTER, 2: VerticalAlign2.BOTTOM}
        vert_align = vert_map.get(vert_align_val, VerticalAlign2.TOP)

        cell_info = {
            'col_idx': col_idx, 'row_idx': row_idx,
            'col_span': col_span, 'row_span': row_span,
            'width': cell_width, 'height': cell_height,
            'margin': cell_margin,
            'border_fill_id': cell_border_fill_id,
            'vert_align': vert_align,
            'para_count': para_count,
            'subs': cell_subs,
        }
        rows_dict.setdefault(row_idx, []).append(cell_info)

    # Build Tr/Tc for each row in order
    for r_idx in sorted(rows_dict.keys()):
        tr = tbl.add_new_tr()
        cells = sorted(rows_dict[r_idx], key=lambda c: c['col_idx'])
        for cell in cells:
            tc = tr.add_new_tc()
            tc.header = False
            tc.has_margin = True if cell['margin'] != (0, 0, 0, 0) else False
            tc.protect = False
            tc.editable = False
            tc.dirty = False
            tc.border_fill_id_ref = str(cell['border_fill_id'])

            # SubList with cell paragraphs
            sl = tc.create_sub_list()
            sl.id = ""
            sl.text_direction = TextDirection.HORIZONTAL
            sl.line_wrap = LineWrapMethod.BREAK
            sl.vert_align = cell['vert_align']
            sl.link_list_id_ref = "0"
            sl.link_list_next_id_ref = "0"
            sl.text_width = cell['width']
            sl.text_height = 0
            sl.has_text_ref = False
            sl.has_num_ref = False

            # Build paragraphs inside the cell
            _build_cell_paragraphs(sl, cell['subs'], hwp)

            # CellAddr
            ca = tc.create_cell_addr()
            ca.col_addr = cell['col_idx']
            ca.row_addr = cell['row_idx']

            # CellSpan
            cs = tc.create_cell_span()
            cs.col_span = cell['col_span']
            cs.row_span = cell['row_span']

            # CellSz
            csz = tc.create_cell_sz()
            csz.width = cell['width']
            csz.height = cell['height']

            # CellMargin
            cm = tc.create_cell_margin()
            cm.left = cell['margin'][0]
            cm.right = cell['margin'][1]
            cm.top = cell['margin'][2]
            cm.bottom = cell['margin'][3]

    return tbl


def _build_cell_paragraphs(sub_list, cell_subs: List[dict],
                           hwp: '_HWPDocument'):
    """Build paragraphs for a single table cell and add them to *sub_list*.

    *cell_subs* contains the raw records at level > list_header level.
    These are structured exactly like a section's paragraphs (PARA_HEADER +
    PARA_TEXT + PARA_CHAR_SHAPE + ...) but may also contain nested tables.
    """
    from .objects.section.paragraph import Para, Run, T, LineSeg
    from .base import ObjectList

    # Group cell sub-records into paragraph groups (by cell-level PARA_HEADER)
    para_groups = _group_paragraphs(cell_subs)

    if not para_groups:
        # Empty cell - add a minimal paragraph
        para = sub_list.add_new_para()
        para.id = "0"
        para.para_pr_id_ref = "0"
        para.style_id_ref = "0"
        para.page_break = False
        para.column_break = False
        para.merged = False
        run = para.add_new_run()
        run.char_pr_id_ref = "0"
        run.add_new_t()
        return

    for pg in para_groups:
        try:
            _build_cell_paragraph(sub_list, pg, hwp)
        except Exception as e:
            logger.debug("Error building cell paragraph: %s", e)
            para = sub_list.add_new_para()
            para.id = "0"
            para.para_pr_id_ref = "0"
            para.style_id_ref = "0"
            para.page_break = False
            para.column_break = False
            para.merged = False
            run = para.add_new_run()
            run.char_pr_id_ref = "0"
            run.add_new_t()


def _build_cell_paragraph(sub_list, pg: List[dict], hwp: '_HWPDocument'):
    """Build one paragraph inside a table cell."""
    if not pg or pg[0]['tag'] != _TAG_PARA_HEADER:
        return

    para_header = pg[0]['data']
    nchars = struct.unpack_from('<I', para_header, 0)[0] if len(para_header) >= 4 else 0
    para_shape_id = struct.unpack_from('<H', para_header, 8)[0] if len(para_header) >= 10 else 0
    style_id = para_header[10] if len(para_header) >= 11 else 0

    para = sub_list.add_new_para()
    para.id = "0"
    para.para_pr_id_ref = str(para_shape_id)
    para.style_id_ref = str(style_id)
    para.page_break = False
    para.column_break = False
    para.merged = False

    text_data = None
    char_shape_pairs = []
    line_segs = []

    for rec in pg[1:]:
        if rec['tag'] == _TAG_PARA_TEXT:
            text_data = rec['data']
        elif rec['tag'] == _TAG_PARA_CHAR_SHAPE:
            d = rec['data']
            i = 0
            while i + 8 <= len(d):
                cpos = struct.unpack_from('<I', d, i)[0]
                csid = struct.unpack_from('<I', d, i + 4)[0]
                char_shape_pairs.append((cpos, csid))
                i += 8
        elif rec['tag'] == _TAG_PARA_LINE_SEG:
            d = rec['data']
            i = 0
            while i + 36 <= len(d):
                seg = {
                    'textpos': struct.unpack_from('<I', d, i)[0],
                    'vertpos': struct.unpack_from('<i', d, i + 4)[0],
                    'vertsize': struct.unpack_from('<i', d, i + 8)[0],
                    'textheight': struct.unpack_from('<i', d, i + 12)[0],
                    'baseline': struct.unpack_from('<i', d, i + 16)[0],
                    'spacing': struct.unpack_from('<i', d, i + 20)[0],
                    'horzpos': struct.unpack_from('<i', d, i + 24)[0],
                    'horzsize': struct.unpack_from('<i', d, i + 28)[0],
                    'flags': struct.unpack_from('<I', d, i + 32)[0],
                }
                line_segs.append(seg)
                i += 36

    if text_data is not None:
        # Parse text into chars - handle table chars for nested tables
        chars = []
        i = 0
        pos = 0
        table_char_indices = []  # indices of ch=11 in chars list
        while i < len(text_data) - 1:
            ch = struct.unpack_from('<H', text_data, i)[0]
            i += 2
            if ch == _CH_TABLE:
                table_char_indices.append(len(chars))
            chars.append((pos, ch))
            if ch == _CH_PARA_END:
                pos += 1
                break
            elif 1 <= ch <= 31 and ch not in (_CH_TAB, _CH_LINE_BREAK, _CH_PARA_END):
                i += 14
                pos += 8
            else:
                pos += 1

        if table_char_indices:
            # Cell has nested tables - build runs with table handling
            ctrl_indices = _find_ctrl_headers_in_group(pg)
            _build_text_runs_with_tables(para, chars, char_shape_pairs,
                                          pg, ctrl_indices, hwp)
        else:
            _build_text_runs(para, chars, char_shape_pairs)
    else:
        run = para.add_new_run()
        run.char_pr_id_ref = "0"
        run.add_new_t()

    if line_segs:
        _build_line_seg_array(para, line_segs)


def _build_text_runs_with_tables(para, chars: List[Tuple[int, int]],
                                  char_shape_pairs: List[Tuple[int, int]],
                                  pg: List[dict],
                                  ctrl_indices: List[int],
                                  hwp: '_HWPDocument'):
    """Build text runs, inserting Table objects when ch=11 is encountered.

    Every extended control char (ch in 1-31 excluding tab/linebreak/paraend)
    corresponds to one control record in *ctrl_indices*, consumed in order.
    Only ch=11 (table) triggers table building; others are skipped.
    """
    def get_char_pr_id(char_pos: int) -> str:
        result = "0"
        for cp, csid in char_shape_pairs:
            if cp <= char_pos:
                result = str(csid)
            else:
                break
        return result

    ctrl_iter = iter(ctrl_indices)
    current_run_chars: List[Tuple[int, int]] = []
    current_char_pr = get_char_pr_id(chars[0][0]) if chars else "0"

    for char_pos, ch in chars:
        # Extended control chars (including table, field_begin, section_def, column_def, etc.)
        # each consume one control record from ctrl_iter.
        is_extended = (1 <= ch <= 31 and ch not in
                       (_CH_TAB, _CH_LINE_BREAK, _CH_PARA_END))
        if is_extended:
            # Flush pending text run
            if current_run_chars:
                _flush_run(para, current_char_pr, current_run_chars)
                current_run_chars = []

            # Consume the corresponding control record
            ci = next(ctrl_iter, None)

            if ci is not None and ch == _CH_TABLE:
                ctrl_rec = pg[ci]
                if _is_table_ctrl(ctrl_rec['data']):
                    sub_recs = _collect_sub_records(pg, ci)
                    tbl = _build_table_object(sub_recs, ctrl_rec, hwp)
                    # Add table in its own run
                    run = para.add_new_run()
                    run.char_pr_id_ref = get_char_pr_id(char_pos)
                    run._item_list.append(tbl)

            # Reset char_pr for next segment
            current_char_pr = get_char_pr_id(char_pos)
            continue

        # Check if charPrId changed
        char_pr = get_char_pr_id(char_pos)
        if char_pr != current_char_pr:
            if current_run_chars:
                _flush_run(para, current_char_pr, current_run_chars)
            current_run_chars = []
            current_char_pr = char_pr

        current_run_chars.append((char_pos, ch))

    if current_run_chars:
        _flush_run(para, current_char_pr, current_run_chars)

    if para.count_of_run() == 0:
        run = para.add_new_run()
        run.char_pr_id_ref = "0"
        run.add_new_t()


def _flush_run(para, char_pr_id: str, chars: List[Tuple[int, int]]):
    """Create a Run element from accumulated characters."""
    run = para.add_new_run()
    run.char_pr_id_ref = char_pr_id

    # Build T elements from the characters
    t = run.add_new_t()
    text_buf = []

    for char_pos, ch in chars:
        if ch >= 0x0020:
            # Normal character
            text_buf.append(chr(ch))
        elif ch == _CH_LINE_BREAK:
            # Flush text, add lineBreak
            if text_buf:
                t.add_text(''.join(text_buf))
                text_buf = []
            t.add_new_line_break()
        elif ch == _CH_TAB:
            # Flush text, add tab
            if text_buf:
                t.add_text(''.join(text_buf))
                text_buf = []
            t.add_new_tab()
        elif ch == _CH_NBSPACE:
            # Non-breaking space
            if text_buf:
                t.add_text(''.join(text_buf))
                text_buf = []
            t.add_new_nb_space()
        elif ch == _CH_FWSPACE:
            # Fixed-width space
            if text_buf:
                t.add_text(''.join(text_buf))
                text_buf = []
            t.add_new_fw_space()
        elif ch == _CH_HYPHEN:
            if text_buf:
                t.add_text(''.join(text_buf))
                text_buf = []
            t.add_new_hyphen()
        elif ch == _CH_PARA_END:
            # End of paragraph - flush and stop
            break
        elif ch == _CH_FIELD_END:
            # Field end - ignore for now (complex)
            pass
        elif ch == _CH_SECTION_DEF or ch == _CH_COLUMN_DEF:
            # Section/column definition - handled via secPr
            pass
        elif ch == _CH_TABLE or ch == _CH_FIELD_BEGIN:
            # Extended controls - skip (table/picture/etc.)
            pass
        else:
            # Other control chars - skip
            pass

    # Flush remaining text
    if text_buf:
        t.add_text(''.join(text_buf))


def _build_line_seg_array(para, line_segs: List[dict]):
    """Build line segment array for a paragraph."""
    from .base import ObjectList
    from .objects.section.paragraph import LineSeg

    para.line_seg_array = ObjectList()
    for seg in line_segs:
        ls = LineSeg(
            textpos=seg['textpos'],
            vertpos=seg['vertpos'],
            vertsize=seg['vertsize'],
            textheight=seg['textheight'],
            baseline=seg['baseline'],
            spacing=seg['spacing'],
            horzpos=seg['horzpos'],
            horzsize=seg['horzsize'],
            flags=seg['flags'],
        )
        para.line_seg_array.add(ls)


# ============================================================
# 6. SETTINGS
# ============================================================

def _build_settings(hwpx, hwp: _HWPDocument):
    settings = hwpx.settings_xml_file
    try:
        cp = settings.create_caret_position()
        cp.list_id_ref = 0
        cp.para_id_ref = 0
        cp.pos = 0
    except Exception:
        pass


# ============================================================
# Section Properties (SecPr) builder
# ============================================================

def build_sec_pr_for_section(run, hwp: _HWPDocument, records: List[dict]):
    """Build SecPr from PAGE_DEF and note shape records in section.

    Called from section building when a section definition control is found.
    """
    from .objects.section.enum_types import (
        ApplyPageType, EndNoteNumberingType, EndNotePlace,
        FootNoteNumberingType, FootNotePlace,
        GutterMethod, NumberType2, PageBorderPositionCriterion,
        PageDirection, PageFillArea, PageStartON,
        TextDirection, VisibilityOption,
    )
    from .objects.header.enum_types import (
        LineType2, LineWidth, ValueUnit1,
    )

    sec_pr = run.create_sec_pr()
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

    # LineNumberShape
    lns = sec_pr.create_line_number_shape()
    lns.restart_type = 0
    lns.count_by = 0
    lns.distance = 0
    lns.start_number = 0

    # PagePr - read from 'secd' control's PAGE_DEF child record
    # HWP PAGE_DEF tag = HWPTAG_BEGIN(16) + 57 = 73
    _TAG_PAGE_DEF_REAL = 73
    page_pr = sec_pr.create_page_pr()
    page_def = _find_record(records, _TAG_PAGE_DEF_REAL)
    if page_def and len(page_def['data']) >= 40:
        d = page_def['data']
        width = struct.unpack_from('<I', d, 0)[0]
        height = struct.unpack_from('<I', d, 4)[0]
        margin_left = struct.unpack_from('<I', d, 8)[0]
        margin_right = struct.unpack_from('<I', d, 12)[0]
        margin_top = struct.unpack_from('<I', d, 16)[0]
        margin_bottom = struct.unpack_from('<I', d, 20)[0]
        margin_header = struct.unpack_from('<I', d, 24)[0]
        margin_footer = struct.unpack_from('<I', d, 28)[0]
        margin_gutter = struct.unpack_from('<I', d, 32)[0]
        prop = struct.unpack_from('<I', d, 36)[0]
        landscape_val = prop & 0x01

        page_pr.landscape = PageDirection.NARROWLY if landscape_val else PageDirection.WIDELY
        page_pr.width = width
        page_pr.height = height
        page_pr.gutter_type = GutterMethod.LEFT_ONLY

        margin = page_pr.create_margin()
        margin.left = margin_left
        margin.right = margin_right
        margin.top = margin_top
        margin.bottom = margin_bottom
        margin.header = margin_header
        margin.footer = margin_footer
        margin.gutter = margin_gutter
    else:
        # A4 defaults (HWP unit: 1/7200 inch. A4=210x297mm)
        page_pr.landscape = PageDirection.WIDELY
        page_pr.width = 59528
        page_pr.height = 84186
        page_pr.gutter_type = GutterMethod.LEFT_ONLY
        margin = page_pr.create_margin()
        margin.left = 8504
        margin.right = 8504
        margin.top = 5668
        margin.bottom = 4252
        margin.header = 4252
        margin.footer = 4252
        margin.gutter = 0

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

    # PageBorderFill x3
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


def _find_record(records: List[dict], tag: int) -> Optional[dict]:
    """Find first record with given tag."""
    for rec in records:
        if rec['tag'] == tag:
            return rec
    return None


# ============================================================
# Enhanced section builder with SecPr
# ============================================================

def _build_section(section, hwp: _HWPDocument, sec_idx: int):
    """Build a single section from HWP records, with SecPr support."""
    records = hwp.section_records[sec_idx]

    # Group records into paragraph groups
    para_groups = _group_paragraphs(records)
    first_para = True

    for pg in para_groups:
        try:
            _build_paragraph_with_secpr(section, hwp, pg, records, first_para)
            first_para = False
        except Exception as e:
            logger.debug("Error building paragraph in section %d: %s", sec_idx, e)
            para = section.add_new_para()
            para.id = "0"
            para.para_pr_id_ref = "0"
            para.style_id_ref = "0"
            para.page_break = False
            para.column_break = False
            para.merged = False
            first_para = False


def _build_paragraph_with_secpr(section, hwp: _HWPDocument, pg: List[dict],
                                 all_records: List[dict], first_para: bool):
    """Build one paragraph, adding SecPr to the first paragraph's first run."""
    if not pg or pg[0]['tag'] != _TAG_PARA_HEADER:
        return

    para_header = pg[0]['data']
    nchars = struct.unpack_from('<I', para_header, 0)[0] if len(para_header) >= 4 else 0
    ctrl_mask = struct.unpack_from('<I', para_header, 4)[0] if len(para_header) >= 8 else 0
    para_shape_id = struct.unpack_from('<H', para_header, 8)[0] if len(para_header) >= 10 else 0
    style_id = para_header[10] if len(para_header) >= 11 else 0  # uint8, NOT uint16
    divide_sort = para_header[11] if len(para_header) >= 12 else 0

    para = section.add_new_para()
    para.id = "0"
    para.para_pr_id_ref = str(para_shape_id)
    para.style_id_ref = str(style_id)
    para.page_break = bool(divide_sort & 0x04)   # bit 2: dividePage
    para.column_break = bool(divide_sort & 0x02)  # bit 1: divideColumn
    para.merged = False

    # Find text and shape data (only at the paragraph's direct child level)
    para_level = pg[0].get('level', 0)
    child_level = para_level + 1
    text_data = None
    char_shape_pairs = []
    line_segs = []

    for rec in pg[1:]:
        if rec.get('level', 0) != child_level:
            continue
        if rec['tag'] == _TAG_PARA_TEXT:
            text_data = rec['data']
        elif rec['tag'] == _TAG_PARA_CHAR_SHAPE:
            d = rec['data']
            i = 0
            while i + 8 <= len(d):
                cpos = struct.unpack_from('<I', d, i)[0]
                csid = struct.unpack_from('<I', d, i + 4)[0]
                char_shape_pairs.append((cpos, csid))
                i += 8
        elif rec['tag'] == _TAG_PARA_LINE_SEG:
            d = rec['data']
            i = 0
            while i + 36 <= len(d):
                seg = {
                    'textpos': struct.unpack_from('<I', d, i)[0],
                    'vertpos': struct.unpack_from('<i', d, i + 4)[0],
                    'vertsize': struct.unpack_from('<i', d, i + 8)[0],
                    'textheight': struct.unpack_from('<i', d, i + 12)[0],
                    'baseline': struct.unpack_from('<i', d, i + 16)[0],
                    'spacing': struct.unpack_from('<i', d, i + 20)[0],
                    'horzpos': struct.unpack_from('<i', d, i + 24)[0],
                    'horzsize': struct.unpack_from('<i', d, i + 28)[0],
                    'flags': struct.unpack_from('<I', d, i + 32)[0],
                }
                line_segs.append(seg)
                i += 36

    # Check if this paragraph has section def control or table controls
    has_sec_def = False
    has_table = False
    if text_data:
        j = 0
        while j < len(text_data) - 1:
            ch = struct.unpack_from('<H', text_data, j)[0]
            j += 2
            if ch == _CH_SECTION_DEF:
                has_sec_def = True
            elif ch == _CH_TABLE:
                has_table = True
            elif ch == _CH_PARA_END:
                break
            if 1 <= ch <= 31 and ch not in (_CH_TAB, _CH_LINE_BREAK, _CH_PARA_END):
                j += 14

    # Build runs
    if text_data is not None:
        _build_runs_with_secpr(para, hwp, text_data, char_shape_pairs,
                                pg, all_records, has_sec_def, has_table)
    else:
        run = para.add_new_run()
        run.char_pr_id_ref = "0"
        if first_para or has_sec_def:
            build_sec_pr_for_section(run, hwp, all_records)
        run.add_new_t()

    # Build line segment array
    if line_segs:
        _build_line_seg_array(para, line_segs)


def _build_runs_with_secpr(para, hwp: _HWPDocument, text_data: bytes,
                            char_shape_pairs: List[Tuple[int, int]],
                            pg: List[dict],
                            all_records: List[dict],
                            has_sec_def: bool,
                            has_table: bool = False):
    """Build runs with SecPr and ColPr support for section-defining paragraphs."""
    # Parse text into (position, char_code) pairs
    chars = []
    i = 0
    pos = 0
    while i < len(text_data) - 1:
        ch = struct.unpack_from('<H', text_data, i)[0]
        i += 2
        chars.append((pos, ch))
        if ch == _CH_PARA_END:
            pos += 1
            break
        elif 1 <= ch <= 31 and ch not in (_CH_TAB, _CH_LINE_BREAK, _CH_PARA_END):
            i += 14
            pos += 8
        else:
            pos += 1

    if not chars:
        run = para.add_new_run()
        run.char_pr_id_ref = "0"
        if has_sec_def:
            build_sec_pr_for_section(run, hwp, all_records)
        run.add_new_t()
        return

    def get_char_pr_id(char_pos: int) -> str:
        result = "0"
        for cp, csid in char_shape_pairs:
            if cp <= char_pos:
                result = str(csid)
            else:
                break
        return result

    # Split chars into segments: before first section def, and the rest
    sec_def_found = False
    pre_sec_chars = []
    post_sec_chars = []

    for char_pos, ch in chars:
        if ch == _CH_SECTION_DEF and not sec_def_found:
            sec_def_found = True
            # SecPr goes into a separate run before text content
            continue
        elif ch == _CH_COLUMN_DEF:
            # ColPr also goes in the secPr run
            continue

        if sec_def_found:
            post_sec_chars.append((char_pos, ch))
        else:
            pre_sec_chars.append((char_pos, ch))

    if has_sec_def:
        # Run 1: SecPr + ColPr
        run1 = para.add_new_run()
        run1.char_pr_id_ref = get_char_pr_id(0)
        build_sec_pr_for_section(run1, hwp, all_records)

        # Add ColPr ctrl
        from .objects.section.enum_types import ColumnDirection, MultiColumnType
        ctrl = run1.add_new_ctrl()
        col_pr = ctrl.add_new_col_pr()
        col_pr.id = ""
        col_pr.type = MultiColumnType.NEWSPAPER
        col_pr.layout = ColumnDirection.LEFT
        col_pr.col_count = 1
        col_pr.same_sz = True
        col_pr.same_gap = 0

        if has_table:
            # When both secDef and table exist, pass ALL chars to the
            # table-aware builder so ctrl records are consumed in order.
            # The secd/cold chars will be handled as extended chars that
            # simply consume their ctrl record without producing output.
            ctrl_indices = _find_ctrl_headers_in_group(pg)
            _build_text_runs_with_tables(para, chars, char_shape_pairs,
                                          pg, ctrl_indices, hwp)
        else:
            # Run 2+: text content
            text_chars = post_sec_chars if post_sec_chars else pre_sec_chars
            if text_chars:
                _build_text_runs(para, text_chars, char_shape_pairs)
            else:
                run2 = para.add_new_run()
                run2.char_pr_id_ref = get_char_pr_id(0)
                run2.add_new_t()
    else:
        # Normal paragraph - all chars go into runs
        all_chars = pre_sec_chars + post_sec_chars if not pre_sec_chars and not post_sec_chars else chars
        if not all_chars:
            all_chars = chars
        if has_table:
            ctrl_indices = _find_ctrl_headers_in_group(pg)
            _build_text_runs_with_tables(para, all_chars, char_shape_pairs,
                                          pg, ctrl_indices, hwp)
        else:
            _build_text_runs(para, all_chars, char_shape_pairs)


def _build_text_runs(para, chars: List[Tuple[int, int]],
                     char_shape_pairs: List[Tuple[int, int]]):
    """Build text runs from character list, grouped by charPrIDRef."""

    def get_char_pr_id(char_pos: int) -> str:
        result = "0"
        for cp, csid in char_shape_pairs:
            if cp <= char_pos:
                result = str(csid)
            else:
                break
        return result

    current_run_chars = []
    current_char_pr = get_char_pr_id(chars[0][0]) if chars else "0"

    for char_pos, ch in chars:
        char_pr = get_char_pr_id(char_pos)
        if char_pr != current_char_pr:
            if current_run_chars:
                _flush_run(para, current_char_pr, current_run_chars)
            current_run_chars = []
            current_char_pr = char_pr
        current_run_chars.append((char_pos, ch))

    if current_run_chars:
        _flush_run(para, current_char_pr, current_run_chars)

    if para.count_of_run() == 0:
        run = para.add_new_run()
        run.char_pr_id_ref = "0"
        run.add_new_t()
