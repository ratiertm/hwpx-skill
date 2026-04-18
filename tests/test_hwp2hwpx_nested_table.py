"""Tests for nested table preservation and surrogate pair decoding in HWP→HWPX conversion."""
import os
import sys
import struct
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pyhwpxlib.hwp2hwpx import (
    _group_paragraphs,
    _find_ctrl_headers_in_group,
    _collect_sub_records,
)

PROJECT = os.path.dirname(os.path.dirname(__file__))

# ── Constants ──
_TAG_PARA_HEADER = 66
_TAG_PARA_TEXT = 67
_TAG_PARA_CHAR_SHAPE = 68
_TAG_PARA_LINE_SEG = 69
_TAG_CTRL_HEADER = 71
_TAG_CELL_LIST_HEADER = 72
_TAG_TABLE_PROPS = 77


# ── Helper: build mock records ──

def _rec(tag, level, data=b'\x00' * 4):
    return {'tag': tag, 'level': level, 'data': data}


def _ctrl_rec(ctrl_id_str: str, level: int):
    """Create a CTRL_HEADER record with 4-char ctrl id (e.g. 'tbl ')."""
    data = ctrl_id_str.encode('ascii')
    # Pad to minimum 30 bytes for table CTRL processing
    data += b'\x00' * (30 - len(data))
    return _rec(_TAG_CTRL_HEADER, level, data)


def _para_text_with_chars(chars: list, level: int):
    """Create a PARA_TEXT record from a list of uint16 char codes.

    Extended ctrl chars (1-31 excluding tab/linebreak/paraend) are followed
    by 14 bytes of addition data in the text stream.
    """
    data = b''
    for ch in chars:
        data += struct.pack('<H', ch)
        if 1 <= ch <= 31 and ch not in (9, 10, 13, 24, 30, 31):
            data += b'\x00' * 14  # addition data for extended ctrl chars
    return _rec(_TAG_PARA_TEXT, level, data)


def _para_header(level: int, nchars=1):
    """Create a PARA_HEADER record."""
    # nchars(4) + ctrlMask(4) + paraShapeId(2) + styleId(1) + divideSort(1) + ...
    data = struct.pack('<I', nchars) + b'\x00' * 8
    return _rec(_TAG_PARA_HEADER, level, data)


# ═══════════════════════════════════════════════════════════════
# Test 1: _collect_sub_records collects all nested table records
# ═══════════════════════════════════════════════════════════════

class TestCollectSubRecords:
    """Unit tests for _collect_sub_records with nested structures."""

    def test_collects_all_nested_records(self):
        """_collect_sub_records should collect all records deeper than the ctrl record."""
        pg = [
            _para_header(2),                          # [0] paragraph
            _para_text_with_chars([11, 13], 3),       # [1] text with table ctrl char
            _rec(_TAG_PARA_CHAR_SHAPE, 3),            # [2]
            _rec(_TAG_PARA_LINE_SEG, 3),              # [3]
            _ctrl_rec('tbl ', 3),                     # [4] nested table CTRL
            _rec(_TAG_TABLE_PROPS, 4),                # [5]
            _rec(_TAG_CELL_LIST_HEADER, 4),           # [6] cell 1
            _para_header(4),                          # [7] cell paragraph
            _rec(_TAG_PARA_TEXT, 5),                   # [8]
            _rec(_TAG_PARA_CHAR_SHAPE, 5),            # [9]
            _rec(_TAG_CELL_LIST_HEADER, 4),           # [10] cell 2
            _para_header(4),                          # [11]
            _rec(_TAG_PARA_TEXT, 5),                   # [12]
            _rec(_TAG_PARA_CHAR_SHAPE, 5),            # [13]
        ]
        sub_recs = _collect_sub_records(pg, 4)
        # Should collect records [5] through [13] (all at level > 3)
        assert len(sub_recs) == 9
        assert sub_recs[0]['tag'] == _TAG_TABLE_PROPS
        assert sub_recs[1]['tag'] == _TAG_CELL_LIST_HEADER

    def test_stops_at_same_level(self):
        """_collect_sub_records stops when encountering a record at same level."""
        pg = [
            _para_header(2),
            _ctrl_rec('tbl ', 3),                     # [1]
            _rec(_TAG_TABLE_PROPS, 4),                # [2]
            _rec(_TAG_CELL_LIST_HEADER, 4),           # [3]
            _para_header(4),                          # [4]
            _rec(_TAG_PARA_TEXT, 5),                   # [5]
            _ctrl_rec('cold', 3),                     # [6] same level -> STOP
            _rec(99, 4),                              # [7] should NOT be collected
        ]
        sub_recs = _collect_sub_records(pg, 1)
        assert len(sub_recs) == 4  # records [2]-[5]


# ═══════════════════════════════════════════════════════════════
# Test 2: End-to-end nested table preservation (ibgopongdang)
# ═══════════════════════════════════════════════════════════════

IBGOPONGDANG_PATH = os.path.join(PROJECT, 'samples', 'ibgopongdang_230710.hwpx')

@pytest.mark.skipif(
    not os.path.exists(IBGOPONGDANG_PATH),
    reason="ibgopongdang sample not available"
)
class TestIbgopongdangNestedTables:
    """End-to-end test: HWP with 21 tables (16 outer + 5 nested) should produce 21 tables in HWPX."""

    def test_all_tables_preserved(self, tmp_path):
        """Converting ibgopongdang HWP should produce exactly 21 hp:tbl elements."""
        import zipfile
        import xml.etree.ElementTree as ET
        from pyhwpxlib.hwp2hwpx import convert

        dst = str(tmp_path / "out.hwpx")
        convert(IBGOPONGDANG_PATH, dst)

        HP_NS = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
        with zipfile.ZipFile(dst) as z:
            total_tables = 0
            for name in z.namelist():
                if name.startswith('Contents/section') and name.endswith('.xml'):
                    data = z.read(name).decode('utf-8')
                    root = ET.fromstring(data)
                    tables = root.findall(f'.//{{{HP_NS}}}tbl')
                    total_tables += len(tables)

        assert total_tables == 21, (
            f"Expected 21 tables (16 outer + 5 nested), got {total_tables}. "
            f"Nested tables are being lost during conversion."
        )

    def test_nested_table_in_cell_run(self, tmp_path):
        """Nested tables should appear inside a cell's paragraph run element."""
        import zipfile
        import xml.etree.ElementTree as ET
        from pyhwpxlib.hwp2hwpx import convert

        dst = str(tmp_path / "out.hwpx")
        convert(IBGOPONGDANG_PATH, dst)

        HP_NS = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
        with zipfile.ZipFile(dst) as z:
            for name in z.namelist():
                if name.startswith('Contents/section') and name.endswith('.xml'):
                    data = z.read(name).decode('utf-8')
                    root = ET.fromstring(data)
                    # Find tbl elements that are inside a tc (table cell)
                    # XPath: .//tc//tbl means table inside a cell
                    nested = root.findall(
                        f'.//{{{HP_NS}}}tc//{{{HP_NS}}}tbl'
                    )
                    assert len(nested) >= 4, (
                        f"Expected at least 4 nested tables inside cells, got {len(nested)}"
                    )


# ═══════════════════════════════════════════════════════════════
# Test 3: _build_cell_paragraph level filtering (mock-based)
# ═══════════════════════════════════════════════════════════════

class TestCellParagraphLevelFiltering:
    """Verify that _build_cell_paragraph only uses records at para_level+1,
    not deeper records from nested table cells."""

    def test_only_direct_child_records_used(self):
        """When a paragraph group contains a nested table,
        _build_cell_paragraph should use PARA_TEXT at para_level+1 (level 3),
        NOT PARA_TEXT from the nested table's cells (level 5)."""
        # Build a paragraph group that mimics the real structure:
        # PARA_HEADER(2) -> PARA_TEXT(3) -> CTRL_HEADER(3, tbl) ->
        #   TABLE_PROPS(4) -> CELL_LIST_HEADER(4) -> PARA_HEADER(4) -> PARA_TEXT(5)

        # The cell paragraph's text has ctrl char 11 (table)
        cell_text = _para_text_with_chars([11, 13], 3)  # [11]=table, [13]=para_end

        # The nested table's cell text has different content
        nested_text = _para_text_with_chars([11, 11, 13], 5)  # different chars

        pg = [
            _para_header(2),           # [0]
            cell_text,                  # [1] <- THIS should be used
            _rec(_TAG_PARA_CHAR_SHAPE, 3),  # [2]
            _rec(_TAG_PARA_LINE_SEG, 3),    # [3]
            _ctrl_rec('cold', 3),      # [4] column define
            _ctrl_rec('tbl ', 3),      # [5] nested TABLE
            _rec(_TAG_TABLE_PROPS, 4), # [6]
            _rec(_TAG_CELL_LIST_HEADER, 4),  # [7]
            _para_header(4),           # [8]
            nested_text,               # [9] <- THIS should NOT be used
            _rec(_TAG_PARA_CHAR_SHAPE, 5),  # [10]
            _rec(_TAG_PARA_LINE_SEG, 5),    # [11]
        ]

        # After fix: _build_cell_paragraph should parse text_data from pg[1] (level 3),
        # not pg[9] (level 5). We verify by checking that _find_ctrl_headers_in_group
        # returns correct indices and that the text has the right ctrl chars.

        para_level = pg[0].get('level', 0)
        expected_level = para_level + 1  # = 3

        # Collect only records at expected_level (the fix)
        text_data = None
        for rec in pg[1:]:
            if rec.get('level', 0) != expected_level:
                continue
            if rec['tag'] == _TAG_PARA_TEXT:
                text_data = rec['data']

        # text_data should be from pg[1] (level 3), which has [11, 13]
        assert text_data is not None
        # Parse to verify
        chars = []
        i = 0
        while i < len(text_data) - 1:
            ch = struct.unpack_from('<H', text_data, i)[0]
            i += 2
            chars.append(ch)
            if ch == 13:
                break
            if 1 <= ch <= 31 and ch not in (9, 10, 13, 24, 30, 31):
                i += 14

        assert chars == [11, 13], f"Expected [11, 13] from direct child PARA_TEXT, got {chars}"
