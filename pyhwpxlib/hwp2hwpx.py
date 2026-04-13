"""HWP 5.x -> HWPX converter

Ported from hwp2hwpx by neolord0 (https://github.com/neolord0/hwp2hwpx)
Original work Copyright (c) neolord0, licensed under Apache License 2.0.
This file: Copyright (c) 2026 Eunmi Lee (ratiertm), licensed under Apache License 2.0.
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
_CH_HEAD_FOOT = 16  # header / footer inline control
_CH_AUTO_NUM = 18   # auto number (page, footnote, endnote, etc.)
_CH_PAGE_NUM = 21   # 쪽 번호 위치 (pgnp) inline control (0x15)
_CH_NEW_NUM = 24    # NOTE: conflicts with _CH_HYPHEN below; only in non-text context
_CH_NBSPACE = 30
_CH_FWSPACE = 31
_CH_HYPHEN = 24     # same code as _CH_NEW_NUM but context differentiates

# CTRL_HEADER ctrl-ids for header/footer/auto-num
_CTRL_ID_HEADER   = 0x68656164  # 'head'
_CTRL_ID_FOOTER   = 0x666f6f74  # 'foot'
_CTRL_ID_AUTO_NUM = 0x61746e6f  # 'atno'
_CTRL_ID_NEW_NUM  = 0x6e776e6f  # 'nwno'
_CTRL_ID_PAGE_NUM = 0x70676e70  # 'pgnp' - 쪽 번호 위치

# applyPageType mapping for header/footer (HWP prop bits 0-1)
_APPLY_PAGE_TYPE = {0: 'BOTH', 1: 'EVEN', 2: 'ODD'}

# Extended control char codes (occupy 8 wchars total)
_EXTENDED_CHARS = set(range(1, 32)) - {_CH_TAB, _CH_LINE_BREAK, _CH_PARA_END}

# HWP tab-fill sentinel value injected by _preprocess_chars() to signal that
# the following TAB element should carry a DOT leader.  The actual HWP fill
# character is a CJK ideograph (varies per paragraph) followed by U+0000.
_CH_TAB_FILL_SENTINEL = 0x0001  # a low control code safely unused elsewhere


# ============================================================
# Public API
# ============================================================

def convert(hwp_path: str, hwpx_path: str,
            ref_owpml_path: Optional[str] = None,
            *, verify: bool = False) -> str:
    """Convert HWP file to HWPX file.

    Parameters
    ----------
    hwp_path : str
        Input HWP 5.x binary file path
    hwpx_path : str
        Output HWPX file path
    ref_owpml_path : str, optional
        Reference OWPML file (same document saved by Hancom HWP).
        When provided, fill-tab widths are taken from the reference to
        produce pixel-accurate leader fills.
    verify : bool, optional
        If True, compare original HWP text vs converted HWPX text
        and log warnings on any character loss. Default False.

    Returns
    -------
    str
        The output hwpx_path
    """
    hwp = _HWPDocument(hwp_path)
    hwpx_file = _build_hwpx(hwp)
    _write_hwpx_file(hwpx_file, hwpx_path, hwp)
    if ref_owpml_path:
        _patch_tab_widths_from_owpml(hwpx_path, ref_owpml_path)
    if verify:
        _verify_conversion(hwp_path, hwpx_path)
    logger.info("HWP -> HWPX conversion complete: %s -> %s", hwp_path, hwpx_path)
    return hwpx_path


def _verify_conversion(hwp_path: str, hwpx_path: str) -> None:
    """Compare original HWP text vs converted HWPX text, warn on loss."""
    from .hwp_reader import read_hwp
    from .api import extract_text

    hwp_doc = read_hwp(hwp_path)
    hwp_chars = set()
    for t in hwp_doc.texts:
        hwp_chars.update(c for c in t if ord(c) >= 32)

    hwpx_text = extract_text(hwpx_path)
    hwpx_chars = set(c for c in hwpx_text if ord(c) >= 32)

    missing = hwp_chars - hwpx_chars
    if missing:
        sample = ''.join(sorted(missing)[:10])
        logger.warning(
            "hwp2hwpx verify: %d char(s) in HWP not found in HWPX: %s",
            len(missing), sample,
        )
    else:
        logger.info("hwp2hwpx verify: no character loss detected")


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
        _sec_str = xsb.to_string()
        # Remove surrogate characters that can't be encoded to UTF-8
        _sec_str = _sec_str.encode("utf-8", errors="surrogatepass").decode("utf-8", errors="replace")
        xml_files[f"Contents/section{i}.xml"] = _sec_str.encode("utf-8")

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
# Tab-width patch: inject widths from reference OWPML
# ============================================================

def _patch_tab_widths_from_owpml(hwpx_path: str, ref_owpml_path: str) -> None:
    """Patch fill-tab widths in *hwpx_path* using values from *ref_owpml_path*.

    The reference OWPML must be the same document saved by Hancom HWP, whose
    layout engine computes the exact per-line fill width.  Tabs are matched
    in document order per section file: the i-th fill tab in our output gets
    the i-th width from the reference.

    Also upgrades any plain ``<hp:tab/>`` that corresponds to a fill tab in
    the reference (missed by _preprocess_tab_fills) to carry the correct
    leader/type/width.
    """
    import io
    import re
    import zipfile

    _FILL_TAB_RE = re.compile(
        r'<hp:tab(?:\s+width="[^"]*")?\s+leader="3"\s+type="2"\s*/>'
    )
    _PLAIN_TAB_RE = re.compile(r'<hp:tab\s*/>')

    # Read reference OWPML widths per section
    ref_widths: Dict[str, List[int]] = {}
    with zipfile.ZipFile(ref_owpml_path, 'r') as ref_zf:
        for name in ref_zf.namelist():
            import re as _re
            if not _re.match(r'Contents/section\d+\.xml', name):
                continue
            text = ref_zf.read(name).decode('utf-8')
            # Collect fill-tab widths in document order
            widths = [
                int(m.group(1))
                for m in re.finditer(r'<hp:tab\s+width="(\d+)"\s+leader="3"\s+type="2"\s*/>', text)
            ]
            if widths:
                ref_widths[name] = widths

    if not ref_widths:
        logger.debug("_patch_tab_widths_from_owpml: no fill tabs found in reference")
        return

    # Single regex matching ALL <hp:tab .../> elements in document order
    _ANY_TAB_RE = re.compile(r'<hp:tab(?:\s[^/]*)*/>')

    # Read our hwpx, patch, write back
    buf = io.BytesIO()
    with zipfile.ZipFile(hwpx_path, 'r') as our_zf:
        entries = []
        for info in our_zf.infolist():
            data = our_zf.read(info.filename)
            sec_name = info.filename
            if sec_name in ref_widths:
                text = data.decode('utf-8')
                widths = ref_widths[sec_name]
                idx = [0]

                def _replace_any_tab(m, _widths=widths, _idx=idx):
                    if _idx[0] >= len(_widths):
                        return m.group(0)
                    w = _widths[_idx[0]]
                    _idx[0] += 1
                    return f'<hp:tab width="{w}" leader="3" type="2"/>'

                # Single pass: replace ALL tabs in document order
                text = _ANY_TAB_RE.sub(_replace_any_tab, text)
                data = text.encode('utf-8')
            entries.append((info, data))

        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as out_zf:
            for info, data in entries:
                if info.filename == 'mimetype':
                    zi = zipfile.ZipInfo('mimetype')
                    zi.compress_type = zipfile.ZIP_STORED
                    out_zf.writestr(zi, data)
                else:
                    out_zf.writestr(info.filename, data)

    with open(hwpx_path, 'wb') as f:
        f.write(buf.getvalue())

    logger.debug("_patch_tab_widths_from_owpml: patched %s", hwpx_path)


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
        """Read HWPTAG_TAB_DEF records.

        Binary layout (HWP 5.x spec):
          offset 0 : UINT32 flags  (bit0=autoTabLeft, bit1=autoTabRight)
          offset 4 : UINT32 count  (number of tab items)
          offset 8 : tab items, 8 bytes each:
            +0 INT32  position (HWPUNIT)
            +4 UINT8  type   (0=LEFT,1=RIGHT,2=CENTER,3=DECIMAL,4=BAR)
            +5 UINT8  leader (0=NONE,1=DOT,2=DOT_SPACE,3=UNDER,4=EQUAL,5=THICK)
            +6 UINT16 reserved
        """
        results = []
        for rec in self.docinfo_records:
            if rec['tag'] == _TAG_TAB_DEF:
                d = rec['data']
                auto_tab_left = False
                auto_tab_right = False
                tab_items = []
                if len(d) >= 4:
                    prop = struct.unpack_from('<I', d, 0)[0]
                    auto_tab_left = bool(prop & 0x01)
                    auto_tab_right = bool(prop & 0x02)
                if len(d) >= 8:
                    count = struct.unpack_from('<I', d, 4)[0]
                    pos = 8
                    for _ in range(count):
                        if pos + 8 > len(d):
                            break
                        item_pos = struct.unpack_from('<i', d, pos)[0]
                        item_type = d[pos + 4]
                        item_leader = d[pos + 5]
                        tab_items.append({
                            'pos': item_pos,
                            'type': item_type,
                            'leader': item_leader,
                        })
                        pos += 8
                results.append({
                    'auto_tab_left': auto_tab_left,
                    'auto_tab_right': auto_tab_right,
                    'tab_items': tab_items,
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
        """Read HWPTAG_BIN_DATA entries, map ID -> extension.

        BIN_DATA record layout:
          offset 0: prop     (2 bytes) – storage type in lower 4 bits
          offset 2: binDataID(2 bytes) – 1-based ID
          offset 4: ext_len  (2 bytes) – extension string length (chars)
          offset 6: ext      (ext_len*2 bytes) – UTF-16-LE extension
        """
        result = {}
        idx = 0
        for rec in self.docinfo_records:
            if rec['tag'] == _TAG_BIN_DATA:
                d = rec['data']
                if len(d) >= 2:
                    prop = struct.unpack_from('<H', d, 0)[0]
                    data_type = prop & 0x0F
                    if data_type == 0:  # LINK – external file, nothing to embed
                        idx += 1
                        continue
                    ext = 'png'  # default for EMBEDDING(1) / STORAGE(2)
                    if len(d) >= 6:
                        ext_len = struct.unpack_from('<H', d, 4)[0]
                        if 6 + ext_len * 2 <= len(d):
                            ext = d[6:6 + ext_len * 2].decode('utf-16-le', errors='replace').lower()
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
    _attach_binary_data(hwpx, hwp)

    hwp.close()
    return hwpx


def _attach_binary_data(hwpx, hwp: '_HWPDocument'):
    """Read embedded binary data from HWP OLE streams and attach to HWPX."""
    attachments = {}
    for bin_id, ext in hwp.bin_data_ids.items():
        hex_id = f"BIN{bin_id:04X}"
        ole_stream = f"BinData/{hex_id}.{ext}"
        if hwp.ole.exists(ole_stream):
            raw = hwp.ole.openstream(ole_stream).read()
            data = hwp._decompress(raw)
            attachments[f"BinData/{hex_id}.{ext}"] = data
        else:
            logger.warning("Binary stream not found in HWP OLE: %s", ole_stream)
    hwpx._binary_attachments = attachments


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
        item_id = f"BIN{bin_id:04X}"
        href = f"BinData/{hex_id}.{ext}"
        item = manifest.add_new()
        item.id = item_id
        item.href = href
        item.media_type = _media_type(ext)
        item.is_embedded = True
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
        ul_shape_val = cs.get('underline_shape', 0)
        # In HWP charShape, underline/strikeout shape encoding starts at 0=SOLID
        # (unlike border types where 0=NONE). Map directly.
        ul.shape = LineType3.from_string(_underline_shape_str(ul_shape_val))
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


def _underline_shape_str(val: int) -> str:
    """HWP underline/strikeout shape -> LineType3 string.

    HWP encoding for underline/strikeout shape starts at 0=SOLID (unlike
    border types where 0=NONE).  Mapping: 0=SOLID, 1=DASH, 2=DOT, 3=DASH_DOT,
    4=DASH_DOT_DOT, 5=LONG_DASH, 6=CIRCLE, 7=DOUBLE_SLIM, 8=SLIM_THICK,
    9=THICK_SLIM, 10=SLIM_THICK_SLIM, 11=WAVE, 12=DOUBLEWAVE.
    """
    _MAP = {
        0: "SOLID", 1: "DASH", 2: "DOT", 3: "DASH_DOT",
        4: "DASH_DOT_DOT", 5: "LONG_DASH", 6: "CIRCLE", 7: "DOUBLE_SLIM",
        8: "SLIM_THICK", 9: "THICK_SLIM", 10: "SLIM_THICK_SLIM",
        11: "WAVE", 12: "DOUBLEWAVE",
    }
    return _MAP.get(val, "SOLID")


# ============================================================
# 4d. TabProperties
# ============================================================

def _build_tab_properties(ref_list, hwp: _HWPDocument):
    from .objects.header.enum_types import LineType2, TabItemType, ValueUnit2

    # HWP leader byte → HWPX LineType2
    # Verified against owpml: HWP leader=3 (UNDERSCORE/DASH) → HWPX DASH (index=3)
    _LEADER_MAP = {
        0: LineType2.NONE,
        1: LineType2.DOT,
        2: LineType2.DOT,        # DOT_SPACE → DOT
        3: LineType2.DASH,       # DASH/UNDERSCORE → DASH (owpml confirmed)
        4: LineType2.DASH,       # EQUAL → DASH
        5: LineType2.SOLID,      # THICK_LINE → SOLID
    }
    # HWP type byte → HWPX TabItemType
    _TYPE_MAP = {
        0: TabItemType.LEFT,
        1: TabItemType.RIGHT,
        2: TabItemType.CENTER,
        3: TabItemType.DECIMAL,
        4: TabItemType.LEFT,     # BAR → LEFT (not in HWPX)
    }

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

        for raw_item in td.get('tab_items', []):
            ti = tp.add_new_tab_item()
            ti.pos = raw_item['pos']
            ti.type = _TYPE_MAP.get(raw_item['type'], TabItemType.LEFT)
            ti.leader = _LEADER_MAP.get(raw_item['leader'], LineType2.NONE)
            ti.unit = ValueUnit2.HWPUNIT


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
_CTRL_ID_TABLE = 0x74626C20     # 'tbl '
_CTRL_ID_GSO = 0x67736F20       # 'gso '
_CTRL_ID_EQUATION = 0x65716564  # 'eqed'
_CTRL_ID_FORM = 0x666F726D      # 'form'

# GSO shape type IDs (from ShapeComponent first 4 bytes in sub-records)
_TAG_SHAPE_COMPONENT = 76  # HWPTAG_BEGIN + 60

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


def _get_ctrl_id(rec_data: bytes) -> int:
    """Get the control type ID from the first 4 bytes of a CTRL_HEADER record."""
    if len(rec_data) < 4:
        return 0
    return struct.unpack_from('<I', rec_data, 0)[0]


def _is_table_ctrl(rec_data: bytes) -> bool:
    """Check whether an extended control record is for a table."""
    return _get_ctrl_id(rec_data) == _CTRL_ID_TABLE


def _is_gso_ctrl(rec_data: bytes) -> bool:
    """Check whether an extended control record is for a GSO (drawing object)."""
    return _get_ctrl_id(rec_data) == _CTRL_ID_GSO


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
        # Parse text into chars - handle extended ctrl chars (table, auto-num, etc.)
        chars = []
        i = 0
        pos = 0
        needs_ctrl_processing = False  # True when any ctrl char needs a ctrl record
        while i < len(text_data) - 1:
            ch = struct.unpack_from('<H', text_data, i)[0]
            i += 2
            if ch in (_CH_TABLE, _CH_AUTO_NUM, _CH_HEAD_FOOT, _CH_PAGE_NUM):
                needs_ctrl_processing = True
            chars.append((pos, ch))
            if ch == _CH_PARA_END:
                pos += 1
                break
            elif 1 <= ch <= 31 and ch not in (_CH_TAB, _CH_LINE_BREAK, _CH_PARA_END,
                                               _CH_FWSPACE, _CH_NBSPACE, _CH_HYPHEN):
                i += 14
                pos += 8
            else:
                pos += 1

        if needs_ctrl_processing:
            # Has inline ctrl objects (table/auto-num/header-footer) - use ctrl-aware builder
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


def _preprocess_tab_fills(chars: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """Preprocess HWP tab-fill sequences.

    HWP pattern: TAB + fill_char(>=0x20 or fwSpace=0x1F) + NULL(0x0000) + ... + closing_TAB
    → SENTINEL + TAB

    The SENTINEL signals _flush_run to emit leader="3" (DASH) on the TAB.
    Fill characters and the closing TAB are all dropped because the owpml
    format uses a single <hp:tab leader="3" type="2"/> with no fill chars.
    """
    result: List[Tuple[int, int]] = []
    i = 0
    while i < len(chars):
        pos_i, ch_i = chars[i]
        if (ch_i == _CH_TAB
                and i + 1 < len(chars)
                and (chars[i + 1][1] >= 0x0020 or chars[i + 1][1] == _CH_FWSPACE)
                and i + 2 < len(chars)
                and chars[i + 2][1] == 0x0000):
            # Opening fill TAB: emit SENTINEL then TAB
            result.append((pos_i, _CH_TAB_FILL_SENTINEL))
            result.append((pos_i, _CH_TAB))
            i += 1  # skip opening TAB (already emitted)
            # Skip all fill chars until closing TAB
            while i < len(chars) and chars[i][1] != _CH_TAB:
                i += 1
            if i < len(chars):
                i += 1  # skip closing TAB too
        else:
            result.append((pos_i, ch_i))
            i += 1
    return result


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

    # Pre-process tab-fill sequences across the full char list before
    # splitting by charPr, so cross-boundary patterns are handled correctly.
    chars = _preprocess_tab_fills(chars)

    ctrl_iter = iter(ctrl_indices)
    current_run_chars: List[Tuple[int, int]] = []
    current_char_pr = get_char_pr_id(chars[0][0]) if chars else "0"
    # Track current ctrl-only run so consecutive ctrl items with same charPr
    # can share one run (e.g. pgnp + head in the same run, matching Hancom output).
    _ctrl_run: Optional[Any] = None
    _ctrl_run_char_pr: Optional[str] = None

    def _get_or_new_ctrl_run(char_pr: str) -> Any:
        nonlocal _ctrl_run, _ctrl_run_char_pr
        if _ctrl_run is not None and _ctrl_run_char_pr == char_pr:
            return _ctrl_run
        _ctrl_run = para.add_new_run()
        _ctrl_run.char_pr_id_ref = char_pr
        _ctrl_run_char_pr = char_pr
        return _ctrl_run

    def _reset_ctrl_run():
        nonlocal _ctrl_run, _ctrl_run_char_pr
        _ctrl_run = None
        _ctrl_run_char_pr = None

    for char_pos, ch in chars:
        # Extended control chars (including table, field_begin, section_def, column_def, etc.)
        # each consume one control record from ctrl_iter.
        # _CH_TAB_FILL_SENTINEL is synthetic (from _preprocess_tab_fills) and must NOT
        # consume a ctrl_iter entry.
        is_extended = (1 <= ch <= 31 and ch not in
                       (_CH_TAB, _CH_LINE_BREAK, _CH_PARA_END,
                        _CH_FWSPACE, _CH_NBSPACE, _CH_HYPHEN))
        if is_extended:
            if ch == _CH_TAB_FILL_SENTINEL:
                current_run_chars.append((char_pos, ch))
                continue

            # Flush pending text run
            if current_run_chars:
                _flush_run(para, current_char_pr, current_run_chars)
                current_run_chars = []
                _reset_ctrl_run()

            # Consume the corresponding control record
            ci = next(ctrl_iter, None)

            if ci is not None:
                ctrl_rec = pg[ci]
                ctrl_id = _get_ctrl_id(ctrl_rec['data'])
                char_pr = get_char_pr_id(char_pos)
                if ctrl_id == _CTRL_ID_TABLE and ch == _CH_TABLE:
                    sub_recs = _collect_sub_records(pg, ci)
                    tbl = _build_table_object(sub_recs, ctrl_rec, hwp)
                    run = para.add_new_run()
                    run.char_pr_id_ref = char_pr
                    run._item_list.append(tbl)
                    _reset_ctrl_run()
                elif ctrl_id == _CTRL_ID_GSO and ch == _CH_TABLE:
                    sub_recs = _collect_sub_records(pg, ci)
                    gso_obj = _build_gso_object(sub_recs, ctrl_rec, hwp)
                    if gso_obj is not None:
                        run = para.add_new_run()
                        run.char_pr_id_ref = char_pr
                        run._item_list.append(gso_obj)
                    _reset_ctrl_run()
                elif ctrl_id == _CTRL_ID_FORM and ch == _CH_TABLE:
                    sub_recs = _collect_sub_records(pg, ci)
                    form_obj = _build_form_object(sub_recs, ctrl_rec, hwp)
                    if form_obj is not None:
                        run = para.add_new_run()
                        run.char_pr_id_ref = char_pr
                        run._item_list.append(form_obj)
                    _reset_ctrl_run()
                elif ctrl_id in (_CTRL_ID_HEADER, _CTRL_ID_FOOTER) and ch == _CH_HEAD_FOOT:
                    sub_recs = _collect_sub_records(pg, ci)
                    hf_obj = _build_header_footer_object(sub_recs, ctrl_rec, hwp)
                    if hf_obj is not None:
                        run = _get_or_new_ctrl_run(char_pr)
                        ctrl_wrap = run.add_new_ctrl()
                        ctrl_wrap.add_ctrl_item(hf_obj)
                elif ctrl_id == _CTRL_ID_AUTO_NUM and ch == _CH_AUTO_NUM:
                    an_obj = _build_auto_num_object(ctrl_rec)
                    if an_obj is not None:
                        run = _get_or_new_ctrl_run(char_pr)
                        ctrl_wrap = run.add_new_ctrl()
                        ctrl_wrap.add_ctrl_item(an_obj)
                elif ctrl_id == _CTRL_ID_PAGE_NUM and ch == _CH_PAGE_NUM:
                    pn_obj = _build_page_num_object(ctrl_rec)
                    if pn_obj is not None:
                        run = _get_or_new_ctrl_run(char_pr)
                        ctrl_wrap = run.add_new_ctrl()
                        ctrl_wrap.add_ctrl_item(pn_obj)

            # Reset char_pr for next segment
            current_char_pr = get_char_pr_id(char_pos)
            continue

        # Check if charPrId changed
        char_pr = get_char_pr_id(char_pos)
        if char_pr != current_char_pr:
            # Carry SENTINEL to new run if it's trailing (paired with next TAB)
            sentinel_carry = None
            if current_run_chars and current_run_chars[-1][1] == _CH_TAB_FILL_SENTINEL:
                sentinel_carry = current_run_chars.pop()
            if current_run_chars:
                _flush_run(para, current_char_pr, current_run_chars)
            current_run_chars = []
            if sentinel_carry:
                current_run_chars.append(sentinel_carry)
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

    # Build T elements from the characters.
    # Tab-fill sequences were already replaced with (SENTINEL, TAB) by
    # _preprocess_tab_fills() before the chars were split into runs.
    t = run.add_new_t()
    text_buf = []
    tab_fill_next = False

    for char_pos, ch in chars:
        if ch == _CH_TAB_FILL_SENTINEL:
            tab_fill_next = True
            continue
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
            tab = t.add_new_tab()
            if tab_fill_next:
                tab.width = 0    # width=0: viewer re-computes from tabPr at render time
                tab.leader = 3   # DASH (owpml leader="3")
                tab.type = 2     # RIGHT (owpml type="2")
                tab_fill_next = False
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
            # Unknown control char — warn instead of silent skip
            logger.warning("hwp2hwpx: unknown control char %#06x at pos %d in _flush_run", ch, char_pos)

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

        # HWPX: NARROWLY = landscape, WIDELY = portrait.
        # Paper dimensions in HWP binary are always in natural paper orientation;
        # HWPX keeps them as-is — the landscape attribute alone tells the viewer
        # the orientation.  Do NOT swap width/height.
        if landscape_val:
            page_pr.landscape = PageDirection.NARROWLY
        else:
            page_pr.landscape = PageDirection.WIDELY
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

    # Check if this paragraph has section def control or table/header/auto-num controls
    has_sec_def = False
    has_table = False
    if text_data:
        j = 0
        while j < len(text_data) - 1:
            ch = struct.unpack_from('<H', text_data, j)[0]
            j += 2
            if ch == _CH_SECTION_DEF:
                has_sec_def = True
            elif ch in (_CH_TABLE, _CH_HEAD_FOOT, _CH_AUTO_NUM, _CH_PAGE_NUM):
                has_table = True  # any ctrl object requiring ctrl record processing
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

    # Pre-process tab-fill sequences: TAB+fill+NULL → SENTINEL+TAB(leader=DOT)+TAB
    chars = _preprocess_tab_fills(chars)

    current_run_chars = []
    current_char_pr = get_char_pr_id(chars[0][0]) if chars else "0"

    for char_pos, ch in chars:
        # Sentinel: stays in current run, no charPr split
        if ch == _CH_TAB_FILL_SENTINEL:
            current_run_chars.append((char_pos, ch))
            continue
        char_pr = get_char_pr_id(char_pos)
        if char_pr != current_char_pr:
            # If SENTINEL is the last item, carry it to the new run so it
            # remains paired with its following TAB even across charPr boundaries.
            sentinel_carry = None
            if current_run_chars and current_run_chars[-1][1] == _CH_TAB_FILL_SENTINEL:
                sentinel_carry = current_run_chars.pop()
            if current_run_chars:
                _flush_run(para, current_char_pr, current_run_chars)
            current_run_chars = []
            if sentinel_carry:
                current_run_chars.append(sentinel_carry)
            current_char_pr = char_pr
        current_run_chars.append((char_pos, ch))

    if current_run_chars:
        _flush_run(para, current_char_pr, current_run_chars)

    if para.count_of_run() == 0:
        run = para.add_new_run()
        run.char_pr_id_ref = "0"
        run.add_new_t()


# ============================================================
# Header / Footer / AutoNum Builders
# ============================================================

def _build_auto_num_object(ctrl_rec: dict) -> Optional[Any]:
    """Build an AutoNum CtrlItem from an 'atno' CTRL_HEADER record."""
    from .objects.section.ctrl import AutoNum, AutoNumFormat
    from .objects.section.enum_types import NumType, NumberType2

    data = ctrl_rec['data']
    # 'atno' layout: [0-3] ctrl_id, [4-7] numType, [8-11] num
    num_type_val = struct.unpack_from('<I', data, 4)[0] if len(data) >= 8 else 0
    num_val      = struct.unpack_from('<I', data, 8)[0] if len(data) >= 12 else 1

    _NUM_TYPE_MAP = {
        0: NumType.PAGE, 1: NumType.FOOTNOTE, 2: NumType.ENDNOTE,
        3: NumType.PICTURE, 4: NumType.TABLE, 5: NumType.EQUATION,
        6: NumType.TOTAL_PAGE,
    }
    num_type = _NUM_TYPE_MAP.get(num_type_val, NumType.PAGE)

    an = AutoNum()
    an.num = num_val
    an.num_type = num_type
    anf = an.create_auto_num_format()
    anf.type = NumberType2.DIGIT
    anf.user_char = ""
    anf.prefix_char = ""
    anf.suffix_char = ""
    anf.supscript = False
    return an


def _build_page_num_object(ctrl_rec: dict) -> Optional[Any]:
    """Build a PageNum CtrlItem from a 'pgnp' CTRL_HEADER record.

    pgnp layout (16 bytes):
      [0-3]  ctrl_id  'pgnp'
      [4]    num_type (0=Arabic, 1=Roman upper, 2=Roman lower, ...)
      [5]    position (0=TOP_RIGHT, 1=BOTTOM_RIGHT, 2=TOP_LEFT, 3=BOTTOM_LEFT,
                       4=TOP_CENTER, 5=BOTTOM_CENTER, 6=INSIDE_TOP, 7=INSIDE_BOTTOM,
                       8=OUTSIDE_TOP, 9=OUTSIDE_BOTTOM)
      [6-7]  new_num  (starting page number, uint16)
      [8-13] reserved
      [14-15] side_char (UTF-16-LE separator character, e.g. '-')
    """
    from .objects.section.ctrl import PageNum
    from .objects.section.enum_types import PageNumPosition
    from .objects.header.enum_types import NumberType1

    data = ctrl_rec['data']
    if len(data) < 8:
        return None

    num_type_val = data[4] if len(data) > 4 else 0
    position_val = data[5] if len(data) > 5 else 5

    _POS_MAP = {
        0: PageNumPosition.TOP_RIGHT,
        1: PageNumPosition.BOTTOM_RIGHT,
        2: PageNumPosition.TOP_LEFT,
        3: PageNumPosition.BOTTOM_LEFT,
        4: PageNumPosition.TOP_CENTER,
        5: PageNumPosition.BOTTOM_CENTER,
        6: PageNumPosition.INSIDE_TOP,
        7: PageNumPosition.INSIDE_BOTTOM,
        8: PageNumPosition.OUTSIDE_TOP,
        9: PageNumPosition.OUTSIDE_BOTTOM,
    }
    _NUM_TYPE_MAP = {
        0: NumberType1.DIGIT,
        1: NumberType1.ROMAN_CAPITAL,
        2: NumberType1.ROMAN_SMALL,
        3: NumberType1.HANGUL_JAMO,
        4: NumberType1.HANGUL_SYLLABLE,
    }

    side_char = None
    if len(data) >= 16:
        sc = struct.unpack_from('<H', data, 14)[0]
        if sc and sc != 0xFFFF:
            try:
                side_char = chr(sc)
            except (ValueError, OverflowError):
                pass

    pn = PageNum()
    pn.pos = _POS_MAP.get(position_val, PageNumPosition.BOTTOM_CENTER)
    pn.format_type = _NUM_TYPE_MAP.get(num_type_val, NumberType1.DIGIT)
    pn.side_char = side_char
    return pn


def _build_header_footer_object(sub_records: List[dict], ctrl_rec: dict,
                                 hwp: '_HWPDocument') -> Optional[Any]:
    """Build a Header or Footer CtrlItem from HWP records.

    *sub_records* are the records immediately following the CTRL_HEADER (LIST_HEADER
    + content PARA_HEADER/PARA_TEXT/... records).
    *ctrl_rec* is the CTRL_HEADER record ('head' or 'foot').
    """
    from .objects.section.ctrl import Header, Footer, AutoNum, AutoNumFormat
    from .objects.section.enum_types import (
        ApplyPageType, NumType, NumberType2,
        TextDirection, LineWrapMethod, VerticalAlign2,
    )
    from .objects.section.section_xml_file import SubList
    from .objects.section.paragraph import Para, Run, T

    data = ctrl_rec['data']
    ctrl_id = _get_ctrl_id(data)
    # 'head'/'foot' layout: [0-3] ctrl_id, [4-7] applyPageType, [8-11] id
    prop     = struct.unpack_from('<I', data, 4)[0] if len(data) >= 8 else 0
    hf_id    = struct.unpack_from('<I', data, 8)[0] if len(data) >= 12 else 1

    apt_map = {0: ApplyPageType.BOTH, 1: ApplyPageType.EVEN, 2: ApplyPageType.ODD}
    apt = apt_map.get(prop, ApplyPageType.BOTH)

    is_header = (ctrl_id == _CTRL_ID_HEADER)
    hf = Header() if is_header else Footer()
    hf.id = str(hf_id)
    hf.apply_page_type = apt

    # Find LIST_HEADER to get textWidth/textHeight
    list_hdr = None
    for rec in sub_records:
        if rec['tag'] == _TAG_LIST_HEADER:
            list_hdr = rec
            break

    sub_list = hf.create_sub_list()
    sub_list.id = ""
    sub_list.text_direction = TextDirection.HORIZONTAL
    sub_list.line_wrap = LineWrapMethod.BREAK
    sub_list.vert_align = VerticalAlign2.TOP if is_header else VerticalAlign2.BOTTOM
    sub_list.link_list_id_ref = "0"
    sub_list.link_list_next_id_ref = "0"
    sub_list.has_text_ref = False
    sub_list.has_num_ref = False

    if list_hdr is not None and len(list_hdr['data']) >= 16:
        lhd = list_hdr['data']
        text_width  = struct.unpack_from('<I', lhd, 8)[0]
        text_height = struct.unpack_from('<I', lhd, 12)[0]
        sub_list.text_width  = text_width
        sub_list.text_height = text_height

    # Build content paragraphs from sub_records (skip the LIST_HEADER itself)
    content_recs = [r for r in sub_records if r is not list_hdr]
    _build_cell_paragraphs(sub_list, content_recs, hwp)

    return hf


# ============================================================
# GSO (Graphic Shape Object) Builders
# ============================================================

def _build_gso_object(sub_records: List[dict], ctrl_rec: dict,
                      hwp: '_HWPDocument') -> Optional[Any]:
    """Build a GSO object from CTRL_HEADER + sub-records."""
    ctrl_data = ctrl_rec['data']
    if len(ctrl_data) < 28:
        return None

    gso_prop = struct.unpack_from('<I', ctrl_data, 4)[0]
    y_offset = struct.unpack_from('<i', ctrl_data, 8)[0]
    x_offset = struct.unpack_from('<i', ctrl_data, 12)[0]
    width = struct.unpack_from('<I', ctrl_data, 16)[0]
    height = struct.unpack_from('<I', ctrl_data, 20)[0]
    z_order = struct.unpack_from('<i', ctrl_data, 24)[0]

    # CTRL_HEADER GSO outMargin fields are INT16 (2 bytes each), not INT32.
    # See hwplib CtrlHeaderGso.java: offsets 28/30/32/34 are
    # outMargin.left/right/top/bottom as INT16.
    margin_left = margin_right = margin_top = margin_bottom = 0
    if len(ctrl_data) >= 36:
        margin_left = struct.unpack_from('<h', ctrl_data, 28)[0]
        margin_right = struct.unpack_from('<h', ctrl_data, 30)[0]
        margin_top = struct.unpack_from('<h', ctrl_data, 32)[0]
        margin_bottom = struct.unpack_from('<h', ctrl_data, 34)[0]

    shape_comp_rec = None
    for rec in sub_records:
        if rec['tag'] == _TAG_SHAPE_COMPONENT:
            shape_comp_rec = rec
            break

    if shape_comp_rec is None:
        return None

    shape_info = {
        'property': gso_prop,
        'x_offset': x_offset, 'y_offset': y_offset,
        'width': width, 'height': height,
        'z_order': z_order,
        'margin_left': margin_left, 'margin_right': margin_right,
        'margin_top': margin_top, 'margin_bottom': margin_bottom,
        'sc_data': shape_comp_rec['data'],
        'sub_records': sub_records,
    }

    # Determine GSO type from ShapeComponent first 4 bytes
    sc_data = shape_comp_rec['data']
    if len(sc_data) < 4:
        return None
    sc_type_id = struct.unpack_from('<I', sc_data, 0)[0]

    # Dispatch by GSO type
    _GSO_TYPE_PICTURE   = 0x24706963  # '$pic'
    _GSO_TYPE_RECTANGLE = 0x24726563  # '$rec'
    _GSO_TYPE_ELLIPSE   = 0x24656C6C  # '$ell'
    _GSO_TYPE_LINE      = 0x246C696E  # '$lin'
    _GSO_TYPE_ARC       = 0x24617263  # '$arc'
    _GSO_TYPE_POLYGON   = 0x24706F6C  # '$pol'
    _GSO_TYPE_CURVE     = 0x24637572  # '$cur'
    _GSO_TYPE_OLE       = 0x246F6C65  # '$ole'
    _GSO_TYPE_CONTAINER = 0x24636F6E  # '$con'
    _GSO_TYPE_CONNECTLN = 0x24636C6E  # '$cln'  or 0x246C6F63 '$loc'
    _GSO_TYPE_TEXTART   = 0x24746174  # '$tat'

    if sc_type_id == _GSO_TYPE_PICTURE:
        return _try_build_picture(shape_info, hwp)
    elif sc_type_id in (_GSO_TYPE_RECTANGLE, _GSO_TYPE_ELLIPSE, _GSO_TYPE_LINE,
                        _GSO_TYPE_ARC, _GSO_TYPE_POLYGON, _GSO_TYPE_CURVE,
                        _GSO_TYPE_CONNECTLN, 0x246C6F63):
        return _build_drawing_object(shape_info, sc_type_id, hwp)
    elif sc_type_id == _GSO_TYPE_OLE:
        return _build_ole_object(shape_info, hwp)
    elif sc_type_id == _GSO_TYPE_CONTAINER:
        return _build_container_object(shape_info, hwp)
    elif sc_type_id == _GSO_TYPE_TEXTART:
        return _build_textart_object(shape_info, hwp)
    else:
        logger.debug("GSO: unsupported type 0x%08X, skipping", sc_type_id)
        return None


def _read_sc_matrices(sc_data: bytes, is_container: bool = False):
    """Read rendering matrices from ShapeComponent binary data.

    Returns list of (ObjectType, e1..e6) tuples:
      - index 0: transMatrix
      - index 1: scaMatrix
      - index 2: rotMatrix
      - index 3+: extra scaMatrix/rotMatrix pairs

    Standard GSOBASE layout offsets:
      [46:48] N_groups (UINT16)  – number of extra sca+rot matrix pairs
      [48+]   (1 + 2*N_groups) matrices × 6 doubles (48 bytes each)

    Container GSOBASE is shifted by +4 due to extra type_id at [4:8].
    """
    from .objects.section.objects.drawing_object import Matrix
    from .object_type import ObjectType

    base = 4 if is_container else 0
    # N_groups offset: 46 (standard) or 50 (container)
    n_off = base + 46
    mat_off = base + 48

    if len(sc_data) < n_off + 2:
        return []

    n_groups = struct.unpack_from('<H', sc_data, n_off)[0]
    total_mats = 1 + 2 * n_groups

    # Sanity check: need enough bytes
    needed = mat_off + total_mats * 48
    if len(sc_data) < needed:
        return []

    type_seq = (
        [ObjectType.hc_transMatrix]
        + [t for _ in range(n_groups) for t in (ObjectType.hc_scaMatrix, ObjectType.hc_rotMatrix)]
    )

    result = []
    for i, ot in enumerate(type_seq):
        off = mat_off + i * 48
        e1, e2, e3, e4, e5, e6 = struct.unpack_from('<6d', sc_data, off)
        m = Matrix(_object_type_value=ot)
        m.e1, m.e2, m.e3, m.e4, m.e5, m.e6 = e1, e2, e3, e4, e5, e6
        result.append(m)
    return result


def _populate_shape_component_base(obj: Any, w: int, h: int,
                                    x_off: int = 0, y_off: int = 0) -> None:
    """Populate required ShapeComponent base fields (offset/orgSz/curSz/flip/
    rotationInfo/renderingInfo) with sensible defaults. HWPX schema requires
    all of these for any ShapeComponent-derived element; omitting them causes
    Hancom Office to reject the file.
    """
    from .objects.section.objects.drawing_object import (
        Flip, RotationInfo, RenderingInfo, Matrix,
    )
    from .objects.common.base_objects import XAndY, WidthAndHeight
    from .object_type import ObjectType

    obj.offset = XAndY(ObjectType.hp_offset_for_shapeComponent)
    obj.offset.x = x_off
    obj.offset.y = y_off

    obj.org_sz = WidthAndHeight(ObjectType.hp_orgSz)
    obj.org_sz.width = w
    obj.org_sz.height = h

    obj.cur_sz = WidthAndHeight(ObjectType.hp_curSz)
    obj.cur_sz.width = w
    obj.cur_sz.height = h

    obj.flip = Flip()
    obj.flip.horizontal = False
    obj.flip.vertical = False

    obj.rotation_info = RotationInfo()
    obj.rotation_info.angle = 0
    obj.rotation_info.center_x = w // 2
    obj.rotation_info.center_y = h // 2
    obj.rotation_info.rotate_image = True

    ri = RenderingInfo()
    ri.trans_matrix = Matrix(_object_type_value=ObjectType.hc_transMatrix)
    ri.trans_matrix.e1 = 1.0
    ri.trans_matrix.e2 = 0.0
    ri.trans_matrix.e3 = 0.0
    ri.trans_matrix.e4 = 0.0
    ri.trans_matrix.e5 = 1.0
    ri.trans_matrix.e6 = 0.0
    ri.sca_matrix = Matrix(_object_type_value=ObjectType.hc_scaMatrix)
    ri.sca_matrix.e1 = 1.0
    ri.sca_matrix.e2 = 0.0
    ri.sca_matrix.e3 = 0.0
    ri.sca_matrix.e4 = 0.0
    ri.sca_matrix.e5 = 1.0
    ri.sca_matrix.e6 = 0.0
    ri.rot_matrix = Matrix(_object_type_value=ObjectType.hc_rotMatrix)
    ri.rot_matrix.e1 = 1.0
    ri.rot_matrix.e2 = 0.0
    ri.rot_matrix.e3 = 0.0
    ri.rot_matrix.e4 = 0.0
    ri.rot_matrix.e5 = 1.0
    ri.rot_matrix.e6 = 0.0
    obj.rendering_info = ri


def _default_line_shape() -> Any:
    """Build a minimal black solid line shape."""
    from .objects.section.objects.picture import LineShape
    ls = LineShape()
    ls.color = "#000000"
    ls.width = 100
    ls.style = "NORMAL"
    ls.end_cap = "FLAT"
    ls.head_style = "NORMAL"
    ls.tail_style = "NORMAL"
    ls.head_sz = "SMALL_SMALL"
    ls.tail_sz = "SMALL_SMALL"
    ls.head_fill = True
    ls.tail_fill = True
    ls.alpha = 0.0
    return ls


def _default_fill_brush() -> Any:
    """Build a minimal white-fill FillBrush."""
    from .objects.header.references.border_fill import FillBrush, WinBrush
    fb = FillBrush()
    wb = WinBrush()
    wb.faceColor = "#FFFFFF"
    wb.hatchColor = "#000000"
    wb.hatchStyle = "NONE"
    wb.alpha = 0.0
    fb.winBrush = wb
    return fb


def _try_build_picture(shape_info: dict, hwp: '_HWPDocument') -> Optional[Any]:
    """Try to build a Picture object if the GSO contains an image reference."""
    from .objects.section.objects.picture import Picture, ImageRect, ImageDim
    from .objects.header.references.border_fill import Image
    from .objects.section.objects.drawing_object import ShapeSize, ShapePosition
    from .objects.common.base_objects import LeftRightTopBottom, Point
    from .object_type import ObjectType

    sc_data = shape_info['sc_data']
    if len(sc_data) < 60:
        return None

    bin_item_id = _find_bin_item_id_in_sc(sc_data, hwp)
    if bin_item_id is None:
        return None

    bin_ref = hwp.bin_data_ids.get(bin_item_id)
    if bin_ref is None:
        return None

    pic = Picture()
    pic.instid = "0"
    pic.reverse = False
    pic.so_id = "0"
    pic.z_order = shape_info['z_order']
    pic.text_wrap = "TOP_AND_BOTTOM"
    pic.text_flow = "BOTH_SIDES"
    pic.lock = False

    pic.sz = ShapeSize()
    pic.sz.width = shape_info['width']
    pic.sz.height = shape_info['height']
    pic.sz.width_rel_to = "ABSOLUTE"
    pic.sz.height_rel_to = "ABSOLUTE"
    pic.sz.protect = False

    pic.pos = ShapePosition()
    pic.pos.treat_as_char = bool(shape_info['property'] & 0x01)
    pic.pos.affect_line_spacing = bool(shape_info['property'] & 0x02)
    pic.pos.vert_rel_to = "PARA"
    pic.pos.horz_rel_to = "COLUMN"
    pic.pos.vert_align = "TOP"
    pic.pos.horz_align = "LEFT"
    pic.pos.vert_offset = shape_info['y_offset']
    pic.pos.horz_offset = shape_info['x_offset']
    pic.pos.flow_with_text = False
    pic.pos.allow_overlap = True
    pic.pos.hold_anchor_and_so = False

    pic.out_margin = LeftRightTopBottom(ObjectType.hp_outMargin)
    pic.out_margin.left = shape_info['margin_left']
    pic.out_margin.right = shape_info['margin_right']
    pic.out_margin.top = shape_info['margin_top']
    pic.out_margin.bottom = shape_info['margin_bottom']

    w, h = shape_info['width'], shape_info['height']
    _populate_shape_component_base(
        pic, w, h, shape_info['x_offset'], shape_info['y_offset']
    )
    # Picture also requires a lineShape (border around the image)
    pic.line_shape = _default_line_shape()

    pic.img_dim = ImageDim()
    pic.img_dim.width = w
    pic.img_dim.height = h
    # Writer reads dim_width/dim_height attributes — set them explicitly.
    pic.img_dim.dim_width = w
    pic.img_dim.dim_height = h

    pic.img_rect = ImageRect()
    pic.img_rect.pt0 = Point(ObjectType.hc_pt0)
    pic.img_rect.pt0.x, pic.img_rect.pt0.y = 0, 0
    pic.img_rect.pt1 = Point(ObjectType.hc_pt1)
    pic.img_rect.pt1.x, pic.img_rect.pt1.y = w, 0
    pic.img_rect.pt2 = Point(ObjectType.hc_pt2)
    pic.img_rect.pt2.x, pic.img_rect.pt2.y = w, h
    pic.img_rect.pt3 = Point(ObjectType.hc_pt3)
    pic.img_rect.pt3.x, pic.img_rect.pt3.y = 0, h

    from .objects.header.enum_types import ImageEffect
    pic.img = Image()
    pic.img.binaryItemIDRef = f"BIN{bin_item_id:04X}"
    pic.img.bright = 0
    pic.img.contrast = 0
    pic.img.effect = ImageEffect.REAL_PIC
    pic.img.alpha = 0

    logger.info("GSO: built Picture with binItemID=%d", bin_item_id)
    return pic


def _find_bin_item_id_in_sc(sc_data: bytes, hwp: '_HWPDocument') -> Optional[int]:
    """Scan ShapeComponent data to find a binItemID matching known bin_data_ids."""
    known_ids = set(hwp.bin_data_ids.keys())
    if not known_ids:
        return None
    for offset in range(30, min(len(sc_data) - 1, 200), 2):
        candidate = struct.unpack_from('<H', sc_data, offset)[0]
        if candidate in known_ids:
            return candidate
    return None


def _build_drawing_object(shape_info: dict, sc_type_id: int,
                          hwp: '_HWPDocument') -> Optional[Any]:
    """Build a drawing object (Rectangle, Ellipse, Line, Arc, Polygon, Curve, ConnectLine)."""
    from .objects.section.objects.shapes import (
        Rectangle, Ellipse, Line, Arc, Polygon, Curve,
    )
    from .objects.section.objects.connect_line import ConnectLine
    from .objects.section.objects.drawing_object import (
        ShapeSize, ShapePosition, DrawingShadow,
    )
    from .objects.section.objects.picture import LineShape
    from .objects.common.base_objects import LeftRightTopBottom, Point
    from .object_type import ObjectType

    _TYPE_MAP = {
        0x24726563: ('Rectangle', Rectangle),
        0x24656C6C: ('Ellipse', Ellipse),
        0x246C696E: ('Line', Line),
        0x24617263: ('Arc', Arc),
        0x24706F6C: ('Polygon', Polygon),
        0x24637572: ('Curve', Curve),
        0x24636C6E: ('ConnectLine', ConnectLine),
        0x246C6F63: ('ConnectLine', ConnectLine),
    }

    type_info = _TYPE_MAP.get(sc_type_id)
    if type_info is None:
        return None

    type_name, cls = type_info
    obj = cls()

    # ShapeObject common properties
    obj.so_id = "0"
    obj.z_order = shape_info['z_order']
    obj.text_wrap = "TOP_AND_BOTTOM"
    obj.text_flow = "BOTH_SIDES"
    obj.lock = False

    # Size
    obj.sz = ShapeSize()
    obj.sz.width = shape_info['width']
    obj.sz.height = shape_info['height']
    obj.sz.width_rel_to = "ABSOLUTE"
    obj.sz.height_rel_to = "ABSOLUTE"
    obj.sz.protect = False

    # Position
    obj.pos = ShapePosition()
    obj.pos.treat_as_char = bool(shape_info['property'] & 0x01)
    obj.pos.affect_line_spacing = bool(shape_info['property'] & 0x02)
    obj.pos.vert_rel_to = "PARA"
    obj.pos.horz_rel_to = "COLUMN"
    obj.pos.vert_align = "TOP"
    obj.pos.horz_align = "LEFT"
    obj.pos.vert_offset = shape_info['y_offset']
    obj.pos.horz_offset = shape_info['x_offset']
    obj.pos.flow_with_text = False
    obj.pos.allow_overlap = True
    obj.pos.hold_anchor_and_so = False

    # Out margins
    obj.out_margin = LeftRightTopBottom(ObjectType.hp_outMargin)
    obj.out_margin.left = shape_info['margin_left']
    obj.out_margin.right = shape_info['margin_right']
    obj.out_margin.top = shape_info['margin_top']
    obj.out_margin.bottom = shape_info['margin_bottom']

    # Required ShapeComponent base fields (offset/orgSz/curSz/flip/
    # rotationInfo/renderingInfo). Without these HWPX schema validation fails.
    w_tmp, h_tmp = shape_info['width'], shape_info['height']
    _populate_shape_component_base(
        obj, w_tmp, h_tmp, shape_info['x_offset'], shape_info['y_offset']
    )

    # Parse ShapeComponent for lineInfo, fillInfo, shadowInfo
    sc_data = shape_info['sc_data']
    line_shape, shadow = _parse_sc_line_and_shadow(sc_data)
    obj.line_shape = line_shape if line_shape is not None else _default_line_shape()
    # Parse face fill color from SC data; fall back to white default.
    obj.fill_brush = _default_fill_brush()
    face_color = _parse_sc_fill_color(sc_data)
    if face_color and obj.fill_brush.winBrush is not None:
        obj.fill_brush.winBrush.faceColor = face_color

    if shadow is not None:
        obj.shadow = shadow

    # Rect-specific: rounded-corner ratio (from tag-79 sub-record)
    if type_name == 'Rectangle':
        _TAG_RECT_INFO = 79
        for sr in shape_info.get('sub_records', []):
            if sr['tag'] == _TAG_RECT_INFO and len(sr['data']) >= 4:
                obj.ratio = struct.unpack_from('<I', sr['data'], 0)[0]
                break

    # Type-specific geometry (corner points for rect, etc.)
    w, h = shape_info['width'], shape_info['height']
    if type_name == 'Rectangle' and hasattr(obj, 'create_pt0'):
        obj.pt0 = Point(ObjectType.hc_pt0)
        obj.pt0.x, obj.pt0.y = 0, 0
        obj.pt1 = Point(ObjectType.hc_pt1)
        obj.pt1.x, obj.pt1.y = w, 0
        obj.pt2 = Point(ObjectType.hc_pt2)
        obj.pt2.x, obj.pt2.y = w, h
        obj.pt3 = Point(ObjectType.hc_pt3)
        obj.pt3.x, obj.pt3.y = 0, h
    elif type_name == 'Line' and hasattr(obj, 'start_pt'):
        obj.start_pt = Point(ObjectType.hc_startPt)
        obj.start_pt.x, obj.start_pt.y = 0, 0
        obj.end_pt = Point(ObjectType.hc_endPt)
        obj.end_pt.x, obj.end_pt.y = w, h
    elif type_name == 'Ellipse':
        if hasattr(obj, 'create_center'):
            obj.center = Point(ObjectType.hc_center)
            obj.center.x, obj.center.y = w // 2, h // 2
            obj.ax1 = Point(ObjectType.hc_ax1)
            obj.ax1.x, obj.ax1.y = w, h // 2
            obj.ax2 = Point(ObjectType.hc_ax2)
            obj.ax2.x, obj.ax2.y = w // 2, h
    elif type_name == 'Arc':
        # hp:arc requires center + ax1 + ax2. Fall back to bounding box.
        obj.center = Point(ObjectType.hc_center)
        obj.center.x, obj.center.y = w // 2, h // 2
        obj.ax1 = Point(ObjectType.hc_ax1)
        obj.ax1.x, obj.ax1.y = w, h // 2
        obj.ax2 = Point(ObjectType.hc_ax2)
        obj.ax2.x, obj.ax2.y = w // 2, h
    elif type_name == 'Polygon':
        # hp:polygon schema requires at least 3 points. Fallback: 4 bounding-box
        # corners so the file opens even if point parsing fails.
        pts = _parse_polygon_points(sc_data)
        if not pts or len(pts) < 3:
            pts = [(0, 0), (w, 0), (w, h), (0, h)]
        for px, py in pts:
            pt = obj.add_new_pt()
            pt.x, pt.y = px, py
    elif type_name == 'Curve':
        # hp:curve requires at least 1 segment. Provide a minimal 2-point line
        # fallback so Hangul accepts the file.
        from .objects.section.objects.shapes import CurveSegment
        seg = obj.add_new_seg()
        seg.x1, seg.y1 = 0, 0
        seg.x2, seg.y2 = w, h
    elif type_name == 'ConnectLine':
        # hp:connectLine requires startPt and endPt.
        obj.start_pt = obj.create_start_pt() if hasattr(obj, 'create_start_pt') else None
        if obj.start_pt is not None:
            obj.start_pt.x, obj.start_pt.y = 0, 0
        obj.end_pt = obj.create_end_pt() if hasattr(obj, 'create_end_pt') else None
        if obj.end_pt is not None:
            obj.end_pt.x, obj.end_pt.y = w, h

    # DrawText: build from sub_records if PARA_TEXT present
    draw_text = _build_draw_text(shape_info.get('sub_records', []), w, hwp)
    if draw_text is not None:
        obj.draw_text = draw_text

    logger.info("GSO: built %s (%dx%d)", type_name, w, h)
    return obj


def _build_draw_text(sub_records: List[dict], width: int,
                     hwp: '_HWPDocument') -> Optional[Any]:
    """Build a DrawText object from LIST_HEADER + PARA_* sub-records.

    Returns None if there are no text sub-records.
    """
    _TAG_SC_TEXTBOX = 79

    list_hdr = next((r for r in sub_records if r['tag'] == _TAG_LIST_HEADER), None)
    if list_hdr is None:
        return None

    from .objects.section.objects.drawing_object import DrawText as DrawTextObj
    from .objects.section.section_xml_file import SubList
    from .objects.section.paragraph import Para

    dt = DrawTextObj()
    dt.last_width = width
    dt.editable = False

    sl = dt.create_sub_list()
    sl.id = ""
    sl.text_direction = "HORIZONTAL"
    sl.line_wrap = "BREAK"
    sl.vert_align = "CENTER"
    sl.link_list_id_ref = "0"
    sl.link_list_next_id_ref = "0"
    sl.text_width = 0
    sl.text_height = 0
    sl.has_text_ref = False
    sl.has_num_ref = False

    # Build paragraph(s) from PARA_* records
    para_text_recs = [r for r in sub_records if r['tag'] == _TAG_PARA_TEXT]
    char_shape_recs = [r for r in sub_records if r['tag'] == _TAG_PARA_CHAR_SHAPE]

    # Read paraPrIDRef / styleIDRef from PARA_HEADER if present
    para_pr_id_ref = "0"
    style_id_ref = "0"
    para_hdr_recs = [r for r in sub_records if r['tag'] == _TAG_PARA_HEADER]
    if para_hdr_recs:
        ph_data = para_hdr_recs[0]['data']
        # PARA_HEADER layout (HWP 5.x spec):
        #   [0:4]  UINT32 text_length
        #   [4:8]  UINT32 control_mask
        #   [8:10] UINT16 paraPrIDRef   (paragraph property index)
        #   [10:12] UINT16 styleIDRef   (style index)
        if len(ph_data) >= 12:
            para_pr_id_ref = str(struct.unpack_from('<H', ph_data, 8)[0])
            style_id_ref   = str(struct.unpack_from('<H', ph_data, 10)[0])

    para = sl.add_new_para()
    para.id = str(0x80000000)
    para.para_pr_id_ref = para_pr_id_ref
    para.style_id_ref = style_id_ref
    para.page_break = False
    para.column_break = False

    # Determine charPrIDRef from PARA_CHAR_SHAPE
    char_pr_id = "0"
    if char_shape_recs:
        d = char_shape_recs[0]['data']
        if len(d) >= 8:
            char_pr_id = str(struct.unpack_from('<I', d, 4)[0])

    if para_text_recs:
        # Collect characters
        chars: List[Tuple[int, int]] = []
        for rec in para_text_recs:
            raw = rec['data']
            for j in range(0, len(raw) - 1, 2):
                cp = struct.unpack_from('<H', raw, j)[0]
                if cp == 0x000D:  # PARA_END
                    break
                chars.append((j // 2, cp))
        if chars:
            _build_text_runs(para, chars, [(0, int(char_pr_id))])
        else:
            run = para.add_new_run()
            run.char_pr_id_ref = char_pr_id
            run.add_new_t()
    else:
        run = para.add_new_run()
        run.char_pr_id_ref = char_pr_id
        run.add_new_t()

    return dt


def _parse_polygon_points(sc_data: bytes) -> list:
    """Heuristically parse polygon point list from ShapeComponent bytes.

    The point count is stored as UINT32 followed by count * (INT32 x, INT32 y).
    We scan for a plausible count (3..1024) whose payload fits within sc_data.
    Returns list of (x, y) tuples or empty list on failure.
    """
    import struct as _s
    n = len(sc_data)
    # scan from offset 4 onward (skip type_id)
    for off in range(4, max(4, n - 4), 2):
        if off + 4 > n:
            break
        cnt = _s.unpack_from('<I', sc_data, off)[0]
        if 3 <= cnt <= 1024 and off + 4 + cnt * 8 <= n:
            pts = []
            for i in range(cnt):
                x, y = _s.unpack_from('<ii', sc_data, off + 4 + i * 8)
                # sanity: reject wildly out-of-range values (>100M HWPUNIT)
                if abs(x) > 100_000_000 or abs(y) > 100_000_000:
                    pts = []
                    break
                pts.append((x, y))
            if pts:
                return pts
    return []


def _colorref_to_hex(val: int) -> str:
    """Convert a Windows COLORREF (0x00BBGGRR LE uint32) to '#RRGGBB'."""
    r = val & 0xFF
    g = (val >> 8) & 0xFF
    b = (val >> 16) & 0xFF
    return "#%02X%02X%02X" % (r, g, b)


def _parse_sc_line_and_shadow(sc_data: bytes) -> tuple:
    """Parse LineInfo and ShadowInfo from ShapeComponent binary data.

    Returns (LineShape or None, DrawingShadow or None).

    Binary layout (empirically determined for HWP 5.x rect/ellipse shapes):
      header(48) + N * matrix(48) + line_color(4) + line_width(4) + line_flags(4) + ...
    Line data always starts at len(sc_data) - 56 from the end.
    Face-fill color (COLORREF) is at len(sc_data) - 39.
    """
    from .objects.section.objects.picture import LineShape

    line_shape = None

    n = len(sc_data)
    if n < 60:
        return (None, None)

    # Line data block is at a fixed distance from the END of the SC record.
    # Verified offset (from end): line_color=-56, line_width=-52, line_flags=-48.
    try:
        off_line = n - 56
        if off_line >= 0:
            color_val = struct.unpack_from('<I', sc_data, off_line)[0]
            thickness = struct.unpack_from('<I', sc_data, off_line + 4)[0]
            flags = struct.unpack_from('<I', sc_data, off_line + 8)[0]

            if color_val <= 0x00FFFFFF and thickness <= 50000:
                line_shape = LineShape()
                line_shape.color = _colorref_to_hex(color_val)
                line_shape.width = thickness
                # Bit 0-4 of flags encodes line type.
                # Matches LineType2 enum: 0=NONE, 1=SOLID, 2=DOT, 3=DASH, ...
                line_type = flags & 0x1F
                _LINE_TYPES = {
                    0: "NONE", 1: "SOLID", 2: "DOT", 3: "DASH",
                    4: "DASH_DOT", 5: "DASH_DOT_DOT", 6: "LONG_DASH",
                }
                line_shape.type = _LINE_TYPES.get(line_type, "SOLID")
    except (struct.error, IndexError):
        pass

    return (line_shape, None)


def _parse_sc_fill_color(sc_data: bytes) -> Optional[str]:
    """Return the face fill color (#RRGGBB) from ShapeComponent binary data.

    Face-fill COLORREF is at len(sc_data) - 39.
    """
    n = len(sc_data)
    off_fill = n - 39
    if off_fill < 0 or off_fill + 4 > n:
        return None
    try:
        val = struct.unpack_from('<I', sc_data, off_fill)[0]
        if val <= 0x00FFFFFF:
            return _colorref_to_hex(val)
    except (struct.error, IndexError):
        pass
    return None


def _build_ole_object(shape_info: dict, hwp: '_HWPDocument') -> Optional[Any]:
    """Build an OLE object from GSO sub-records."""
    from .objects.section.objects.ole import OLE
    from .objects.section.objects.drawing_object import ShapeSize, ShapePosition
    from .objects.common.base_objects import LeftRightTopBottom, XAndY
    from .object_type import ObjectType

    ole = OLE()
    ole.so_id = "0"
    ole.z_order = shape_info['z_order']
    ole.text_wrap = "TOP_AND_BOTTOM"
    ole.text_flow = "BOTH_SIDES"
    ole.lock = False

    ole.sz = ShapeSize()
    ole.sz.width = shape_info['width']
    ole.sz.height = shape_info['height']
    ole.sz.width_rel_to = "ABSOLUTE"
    ole.sz.height_rel_to = "ABSOLUTE"
    ole.sz.protect = False

    ole.pos = ShapePosition()
    ole.pos.treat_as_char = bool(shape_info['property'] & 0x01)
    ole.pos.affect_line_spacing = bool(shape_info['property'] & 0x02)
    ole.pos.vert_rel_to = "PARA"
    ole.pos.horz_rel_to = "COLUMN"
    ole.pos.vert_align = "TOP"
    ole.pos.horz_align = "LEFT"
    ole.pos.vert_offset = shape_info['y_offset']
    ole.pos.horz_offset = shape_info['x_offset']
    ole.pos.flow_with_text = False
    ole.pos.allow_overlap = True
    ole.pos.hold_anchor_and_so = False

    ole.out_margin = LeftRightTopBottom(ObjectType.hp_outMargin)
    ole.out_margin.left = shape_info['margin_left']
    ole.out_margin.right = shape_info['margin_right']
    ole.out_margin.top = shape_info['margin_top']
    ole.out_margin.bottom = shape_info['margin_bottom']

    _populate_shape_component_base(
        ole, shape_info['width'], shape_info['height'],
        shape_info['x_offset'], shape_info['y_offset'],
    )
    ole.ole_line_shape = _default_line_shape()

    # OLE-specific: try to find binDataId reference
    sc_data = shape_info['sc_data']
    bin_item_id = _find_bin_item_id_in_sc(sc_data, hwp)
    if bin_item_id is not None:
        ole.binary_item_id_ref = "BIN%04X" % bin_item_id
    else:
        ole.binary_item_id_ref = ""

    ole.ole_object_type = "EMBEDDED"
    ole.has_moniker = False
    ole.draw_aspect = "CONTENT"
    ole.eq_base_line = 0

    ole.extent = XAndY(ObjectType.hc_extent)
    ole.extent.x = shape_info['width']
    ole.extent.y = shape_info['height']

    logger.info("GSO: built OLE (%dx%d)", shape_info['width'], shape_info['height'])
    return ole


def _build_container_object(shape_info: dict, hwp: '_HWPDocument') -> Optional[Any]:
    """Build a Container (group) object with recursive child GSO objects."""
    from .objects.section.objects.ole import Container
    from .objects.section.objects.drawing_object import ShapeSize, ShapePosition
    from .objects.common.base_objects import LeftRightTopBottom
    from .object_type import ObjectType

    container = Container()
    container.so_id = "0"
    container.z_order = shape_info['z_order']
    container.text_wrap = "TOP_AND_BOTTOM"
    container.text_flow = "BOTH_SIDES"
    container.lock = False

    container.sz = ShapeSize()
    container.sz.width = shape_info['width']
    container.sz.height = shape_info['height']
    container.sz.width_rel_to = "ABSOLUTE"
    container.sz.height_rel_to = "ABSOLUTE"
    container.sz.protect = False

    container.pos = ShapePosition()
    container.pos.treat_as_char = bool(shape_info['property'] & 0x01)
    container.pos.affect_line_spacing = bool(shape_info['property'] & 0x02)
    container.pos.vert_rel_to = "PARA"
    container.pos.horz_rel_to = "PARA"
    container.pos.vert_align = "TOP"
    container.pos.horz_align = "LEFT"
    container.pos.vert_offset = shape_info['y_offset']
    container.pos.horz_offset = shape_info['x_offset']
    container.pos.flow_with_text = False
    container.pos.allow_overlap = True
    container.pos.hold_anchor_and_so = False

    container.out_margin = LeftRightTopBottom(ObjectType.hp_outMargin)
    container.out_margin.left = shape_info['margin_left']
    container.out_margin.right = shape_info['margin_right']
    container.out_margin.top = shape_info['margin_top']
    container.out_margin.bottom = shape_info['margin_bottom']

    # Extract sub_records and sc_data early (needed for SC binary overrides below)
    sub_records = shape_info['sub_records']
    sc_data = shape_info['sc_data']

    _populate_shape_component_base(
        container, shape_info['width'], shape_info['height'],
        shape_info['x_offset'], shape_info['y_offset'],
    )

    # Override with actual values from container's own SC binary (is_container=True,
    # all offsets shifted +4 vs standard GSOBASE).
    if len(sc_data) >= 56:
        # Container GSOBASE offsets (+4 shift):
        #   [20:24] orgW, [24:28] orgH, [28:32] curW (height always 0)
        #   [42:46] centerX, [46:50] centerY
        org_w = struct.unpack_from('<I', sc_data, 20)[0]
        org_h = struct.unpack_from('<I', sc_data, 24)[0]
        cur_w = struct.unpack_from('<I', sc_data, 28)[0]
        cx = struct.unpack_from('<I', sc_data, 42)[0]
        cy = struct.unpack_from('<I', sc_data, 46)[0]
        container.org_sz.width = org_w
        container.org_sz.height = org_h
        container.cur_sz.width = cur_w
        container.cur_sz.height = 0
        container.rotation_info.center_x = cx
        container.rotation_info.center_y = cy

    # Apply actual rendering matrices from binary
    con_matrices = _read_sc_matrices(sc_data, is_container=True)
    if con_matrices:
        from .objects.section.objects.drawing_object import RenderingInfo
        from .object_type import ObjectType as OT
        ri = RenderingInfo()
        ri.trans_matrix = con_matrices[0] if len(con_matrices) > 0 else container.rendering_info.trans_matrix
        ri.sca_matrix   = con_matrices[1] if len(con_matrices) > 1 else container.rendering_info.sca_matrix
        ri.rot_matrix   = con_matrices[2] if len(con_matrices) > 2 else container.rendering_info.rot_matrix
        ri.extra_matrices = list(con_matrices[3:])
        container.rendering_info = ri

    # Find child SHAPE_COMPONENT records (level = container SC level + 1)
    # (sub_records and sc_data already extracted above)

    # The container's own ShapeComponent is the first one (level N).
    # Child ShapeComponents are at level N+1.
    # We already have sub_records which are all records after CTRL_HEADER.
    # The container SC is the first SHAPE_COMPONENT in sub_records.
    # Children are subsequent SHAPE_COMPONENTs at a deeper level.

    container_sc_level = None
    # Group sub_records by child SC: [(child_sc_rec, [following_recs...]), ...]
    child_groups: List[Tuple[dict, List[dict]]] = []

    for rec in sub_records:
        if rec['tag'] == _TAG_SHAPE_COMPONENT:
            if container_sc_level is None:
                container_sc_level = rec.get('level', 0)
            elif rec.get('level', 0) > container_sc_level:
                child_groups.append((rec, []))
        elif child_groups and rec.get('level', 0) > container_sc_level:
            child_groups[-1][1].append(rec)

    child_count = 0
    for child_idx, (child_rec, child_sub_recs) in enumerate(child_groups):
        child_data = child_rec['data']
        if len(child_data) < 4:
            continue

        child_type_id = struct.unpack_from('<I', child_data, 0)[0]

        child_info = {
            'property': shape_info['property'],
            'x_offset': 0, 'y_offset': 0,
            'width': shape_info['width'],
            'height': shape_info['height'],
            'z_order': child_idx,
            'margin_left': 0, 'margin_right': 0,
            'margin_top': 0, 'margin_bottom': 0,
            'sc_data': child_data,
            'sub_records': child_sub_recs,
        }

        # Extract position/size from child ShapeComponent binary data.
        # Actual layout: type_id(4) + xOffset(4,signed) + yOffset(4,signed)
        #                + flags(4) + orgW(4) + orgH(4) + curW(4) + curH(4)
        # The extra flags dword at offset 12 was previously missed, causing
        # orgH/curW to be read as width/height.
        if len(child_data) >= 12:
            child_info['x_offset'] = struct.unpack_from('<i', child_data, 4)[0]
            child_info['y_offset'] = struct.unpack_from('<i', child_data, 8)[0]
        if len(child_data) >= 28:
            child_info['width']  = struct.unpack_from('<I', child_data, 16)[0]  # orgW
            child_info['height'] = struct.unpack_from('<I', child_data, 20)[0]  # orgH
            # curW from binary; curH is always 0 for child shapes inside a container
            child_info['cur_w']  = struct.unpack_from('<I', child_data, 24)[0]

        _GSO_TYPE_PICTURE   = 0x24706963
        _GSO_TYPE_OLE       = 0x246F6C65
        _DRAWING_TYPES = {0x24726563, 0x24656C6C, 0x246C696E, 0x24617263,
                          0x24706F6C, 0x24637572, 0x24636C6E, 0x246C6F63}

        child_obj = None
        if child_type_id == _GSO_TYPE_PICTURE:
            child_obj = _try_build_picture(child_info, hwp)
        elif child_type_id in _DRAWING_TYPES:
            child_obj = _build_drawing_object(child_info, child_type_id, hwp)
        elif child_type_id == _GSO_TYPE_OLE:
            child_obj = _build_ole_object(child_info, hwp)

        if child_obj is not None:
            # Override curSz and rendering matrices from binary
            if hasattr(child_obj, 'cur_sz') and child_obj.cur_sz is not None:
                child_obj.cur_sz.width  = child_info.get('cur_w', child_info['width'])
                child_obj.cur_sz.height = 0
            if len(child_data) >= 50:
                cx = struct.unpack_from('<I', child_data, 38)[0]
                cy = struct.unpack_from('<I', child_data, 42)[0]
                if hasattr(child_obj, 'rotation_info') and child_obj.rotation_info is not None:
                    child_obj.rotation_info.center_x = cx
                    child_obj.rotation_info.center_y = cy
            child_matrices = _read_sc_matrices(child_data, is_container=False)
            if child_matrices and hasattr(child_obj, 'rendering_info'):
                from .objects.section.objects.drawing_object import RenderingInfo
                ri = RenderingInfo()
                ri.trans_matrix   = child_matrices[0] if len(child_matrices) > 0 else None
                ri.sca_matrix     = child_matrices[1] if len(child_matrices) > 1 else None
                ri.rot_matrix     = child_matrices[2] if len(child_matrices) > 2 else None
                ri.extra_matrices = list(child_matrices[3:])
                child_obj.rendering_info = ri
            container.add_child(child_obj)
            child_count += 1

    logger.info("GSO: built Container with %d children", child_count)
    return container


def _build_textart_object(shape_info: dict, hwp: '_HWPDocument') -> Optional[Any]:
    """Build a TextArt object from GSO sub-records."""
    from .objects.section.objects.text_art import TextArt, TextArtPr
    from .objects.section.objects.drawing_object import ShapeSize, ShapePosition
    from .objects.common.base_objects import LeftRightTopBottom, Point
    from .object_type import ObjectType

    ta = TextArt()
    ta.so_id = "0"
    ta.z_order = shape_info['z_order']
    ta.text_wrap = "TOP_AND_BOTTOM"
    ta.text_flow = "BOTH_SIDES"
    ta.lock = False

    ta.sz = ShapeSize()
    ta.sz.width = shape_info['width']
    ta.sz.height = shape_info['height']
    ta.sz.width_rel_to = "ABSOLUTE"
    ta.sz.height_rel_to = "ABSOLUTE"
    ta.sz.protect = False

    ta.pos = ShapePosition()
    ta.pos.treat_as_char = bool(shape_info['property'] & 0x01)
    ta.pos.affect_line_spacing = bool(shape_info['property'] & 0x02)
    ta.pos.vert_rel_to = "PARA"
    ta.pos.horz_rel_to = "COLUMN"
    ta.pos.vert_align = "TOP"
    ta.pos.horz_align = "LEFT"
    ta.pos.vert_offset = shape_info['y_offset']
    ta.pos.horz_offset = shape_info['x_offset']
    ta.pos.flow_with_text = False
    ta.pos.allow_overlap = True
    ta.pos.hold_anchor_and_so = False

    ta.out_margin = LeftRightTopBottom(ObjectType.hp_outMargin)
    ta.out_margin.left = shape_info['margin_left']
    ta.out_margin.right = shape_info['margin_right']
    ta.out_margin.top = shape_info['margin_top']
    ta.out_margin.bottom = shape_info['margin_bottom']

    w, h = shape_info['width'], shape_info['height']
    _populate_shape_component_base(
        ta, w, h, shape_info['x_offset'], shape_info['y_offset']
    )

    ta.pt0 = Point(ObjectType.hc_pt0)
    ta.pt0.x, ta.pt0.y = 0, 0
    ta.pt1 = Point(ObjectType.hc_pt1)
    ta.pt1.x, ta.pt1.y = w, 0
    ta.pt2 = Point(ObjectType.hc_pt2)
    ta.pt2.x, ta.pt2.y = w, h
    ta.pt3 = Point(ObjectType.hc_pt3)
    ta.pt3.x, ta.pt3.y = 0, h

    # Try to extract text content from ShapeComponent data
    sc_data = shape_info['sc_data']
    ta.text = _extract_textart_text(sc_data)

    # TextArt properties
    ta.textart_pr = TextArtPr()
    ta.textart_pr.font_name = "바탕"
    ta.textart_pr.font_style = "Regular"
    ta.textart_pr.text_shape = "WAVE_1"
    ta.textart_pr.line_spacing = 100
    ta.textart_pr.char_spacing = 0
    ta.textart_pr.align = "LEFT"

    # Parse lineInfo/shadow from SC data
    line_shape, shadow = _parse_sc_line_and_shadow(sc_data)
    ta.line_shape = line_shape if line_shape is not None else _default_line_shape()
    ta.fill_brush = _default_fill_brush()
    if shadow is not None:
        ta.shadow = shadow

    logger.info("GSO: built TextArt '%s' (%dx%d)", (ta.text or '')[:20], w, h)
    return ta


def _extract_textart_text(sc_data: bytes) -> str:
    """Extract text content from TextArt ShapeComponent data.

    The text is stored as UTF-16LE string somewhere in the SC data,
    typically after the common fields and type-specific geometry.
    """
    # TextArt SC layout (approximate):
    # type_id(4) + type_id_repeat(4) + offset(8) + orgSz(8) + curSz(8) +
    # flip(4) + rotation(6) + renderingInfo(varies) + instid(4) +
    # lineInfo(13+) + fillInfo(varies) + shadowInfo(varies) +
    # text_len(2) + text_utf16(text_len*2) + font_name + ...

    if len(sc_data) < 50:
        return ""

    # Strategy: scan for a UTF-16LE text string by looking for a uint16 length
    # followed by printable Korean/ASCII characters
    best_text = ""
    for off in range(40, min(len(sc_data) - 4, 250), 2):
        try:
            text_len = struct.unpack_from('<H', sc_data, off)[0]
            if 1 <= text_len <= 100 and off + 2 + text_len * 2 <= len(sc_data):
                candidate = sc_data[off + 2:off + 2 + text_len * 2].decode('utf-16-le', errors='strict')
                # Check if it looks like real text (has printable chars)
                if candidate and all(c.isprintable() or c in '\r\n\t' for c in candidate):
                    if len(candidate) > len(best_text):
                        best_text = candidate
        except (UnicodeDecodeError, struct.error):
            continue

    return best_text


def _build_form_object(sub_records: List[dict], ctrl_rec: dict,
                       hwp: '_HWPDocument') -> Optional[Any]:
    """Build a form control object (Button, CheckButton, RadioButton, ComboBox, Edit)."""
    from .objects.section.objects.form_objects import (
        Button, CheckButton, RadioButton, ComboBox, Edit, FormCharPr,
    )
    from .objects.section.objects.drawing_object import ShapeSize, ShapePosition
    from .objects.common.base_objects import LeftRightTopBottom
    from .object_type import ObjectType

    ctrl_data = ctrl_rec['data']
    if len(ctrl_data) < 28:
        return None

    # Parse CTRL_HEADER common fields
    gso_prop = struct.unpack_from('<I', ctrl_data, 4)[0]
    y_offset = struct.unpack_from('<i', ctrl_data, 8)[0]
    x_offset = struct.unpack_from('<i', ctrl_data, 12)[0]
    width = struct.unpack_from('<I', ctrl_data, 16)[0]
    height = struct.unpack_from('<I', ctrl_data, 20)[0]

    # Determine form type from sub-records
    # The form type is stored in the FormObject properties within the control data.
    # We use heuristic: look for form type identifier in the data.
    # Common form types in HWP: PushButton, CheckBox, RadioButton, ComboBox, Edit
    form_type = _detect_form_type(ctrl_data, sub_records)

    _FORM_TYPE_MAP = {
        'push_button': Button,
        'check_box': CheckButton,
        'radio_button': RadioButton,
        'combo_box': ComboBox,
        'edit': Edit,
    }

    cls = _FORM_TYPE_MAP.get(form_type, Edit)  # default to Edit
    obj = cls()

    # Common form properties
    obj.name = ""
    obj.fore_color = "#000000"
    obj.back_color = "#FFFFFF"
    obj.group_name = ""
    obj.tab_stop = True
    obj.tab_order = 0
    obj.enabled = True
    obj.border_type_id_ref = ""
    obj.draw_frame = False
    obj.printable = True
    obj.form_editable = True
    obj.command = ""

    obj.so_id = "0"
    obj.z_order = 0
    obj.text_wrap = "TOP_AND_BOTTOM"
    obj.text_flow = "BOTH_SIDES"
    obj.lock = False

    obj.sz = ShapeSize()
    obj.sz.width = width
    obj.sz.height = height
    obj.sz.width_rel_to = "ABSOLUTE"
    obj.sz.height_rel_to = "ABSOLUTE"
    obj.sz.protect = False

    obj.pos = ShapePosition()
    obj.pos.treat_as_char = bool(gso_prop & 0x01)
    obj.pos.affect_line_spacing = bool(gso_prop & 0x02)
    obj.pos.vert_rel_to = "PARA"
    obj.pos.horz_rel_to = "COLUMN"
    obj.pos.vert_align = "TOP"
    obj.pos.horz_align = "LEFT"
    obj.pos.vert_offset = y_offset
    obj.pos.horz_offset = x_offset
    obj.pos.flow_with_text = False
    obj.pos.allow_overlap = True
    obj.pos.hold_anchor_and_so = False

    obj.out_margin = LeftRightTopBottom(ObjectType.hp_outMargin)

    obj.form_char_pr = FormCharPr()
    obj.form_char_pr.char_pr_id_ref = "0"

    logger.info("GSO: built Form '%s' (%dx%d)", form_type, width, height)
    return obj


def _detect_form_type(ctrl_data: bytes, sub_records: List[dict]) -> str:
    """Detect form control type from CTRL_HEADER data.

    The form type is typically stored in the FormObject's property set.
    We scan for known type identifiers.
    """
    # The form type byte is usually at a specific offset in the ctrl_data
    # or in a sub-record. HWP stores form type as a byte:
    # 0 = PushButton, 1 = RadioButton, 2 = CheckBox, 3 = ComboBox, 4 = Edit

    # Strategy: scan all data for type patterns
    all_data = ctrl_data
    for rec in sub_records:
        all_data += rec['data']

    # Look for the FormObject type byte. In HWP binary format,
    # it's typically in the LIST_HEADER sub-record.
    # Try heuristic: scan for type strings in the property set
    data_str = all_data.decode('ascii', errors='replace').lower()
    if 'checkbox' in data_str or 'check' in data_str:
        return 'check_box'
    elif 'radiobutton' in data_str or 'radio' in data_str:
        return 'radio_button'
    elif 'combobox' in data_str or 'combo' in data_str:
        return 'combo_box'
    elif 'pushbutton' in data_str or 'push' in data_str:
        return 'push_button'
    elif 'edit' in data_str:
        return 'edit'

    # Fallback: check for UTF-16LE type strings
    try:
        data_utf16 = all_data.decode('utf-16-le', errors='replace').lower()
        if 'checkbox' in data_utf16:
            return 'check_box'
        elif 'radiobutton' in data_utf16:
            return 'radio_button'
        elif 'combobox' in data_utf16:
            return 'combo_box'
        elif 'pushbutton' in data_utf16:
            return 'push_button'
        elif 'edit' in data_utf16:
            return 'edit'
    except Exception:
        pass

    return 'edit'  # default
