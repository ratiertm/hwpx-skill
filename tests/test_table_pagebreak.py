"""Tests for v0.18.1+ table page-break / repeat-header attributes.

Hancom UI mapping:
  page_break='CELL'     ← "여러 쪽 지원: 셀 단위로 나눔"  (default)
  page_break='TABLE'    ← "여러 쪽 지원: 표 전체를 다음 쪽으로"
  page_break='NONE'     ← "여러 쪽 지원: 나누지 않음"
  repeat_header=True    ← "제목 줄 반복"

Whale cannot render these so we verify at the XML attribute level. Hancom
visual confirmation is the user's responsibility (Critical Rule #12).
"""
from __future__ import annotations

import re

import pytest

from pyhwpxlib import HwpxBuilder
from pyhwpxlib.writer.shape_writer import build_table_xml


# --- build_table_xml unit tests ----------------------------------------------

def test_default_attributes_preserve_legacy():
    """Defaults must produce the same string as before v0.18.1."""
    xml = build_table_xml(2, 2, [["A", "B"], ["1", "2"]])
    assert 'pageBreak="CELL"' in xml
    assert 'repeatHeader="0"' in xml


def test_repeat_header_true_emits_one():
    xml = build_table_xml(3, 2, [["H1", "H2"], ["a", "b"], ["c", "d"]],
                          repeat_header=True)
    assert 'repeatHeader="1"' in xml
    # default page_break preserved
    assert 'pageBreak="CELL"' in xml


def test_page_break_table_value():
    xml = build_table_xml(2, 2, [["A", "B"], ["1", "2"]],
                          page_break="TABLE")
    assert 'pageBreak="TABLE"' in xml


def test_page_break_none_value():
    xml = build_table_xml(2, 2, [["A", "B"], ["1", "2"]],
                          page_break="NONE")
    assert 'pageBreak="NONE"' in xml


def test_page_break_invalid_raises():
    with pytest.raises(ValueError, match="page_break must be"):
        build_table_xml(2, 2, [["A", "B"], ["1", "2"]],
                        page_break="cell")  # lowercase rejected


def test_combined_repeat_header_and_table_break():
    xml = build_table_xml(3, 2, [["H1", "H2"], ["a", "b"], ["c", "d"]],
                          page_break="TABLE", repeat_header=True)
    # Both attributes must appear in the same hp:tbl element.
    m = re.search(r'<hp:tbl[^>]*>', xml)
    assert m is not None
    tag = m.group(0)
    assert 'pageBreak="TABLE"' in tag
    assert 'repeatHeader="1"' in tag


# --- HwpxBuilder integration -------------------------------------------------

def test_builder_forwards_page_break_kwargs(tmp_path):
    """End-to-end: HwpxBuilder.add_table → api.add_table → build_table_xml."""
    out = tmp_path / "out.hwpx"
    doc = HwpxBuilder()
    doc.add_paragraph("test")
    doc.add_table(
        [["헤더1", "헤더2", "헤더3"]] + [[f"r{r}c{c}" for c in range(3)]
                                       for r in range(20)],
        page_break="TABLE",
        repeat_header=True,
    )
    doc.save(str(out))

    # Inspect the generated section XML.
    import zipfile
    with zipfile.ZipFile(out) as z:
        section = z.read("Contents/section0.xml").decode("utf-8")

    # Locate the hp:tbl tag and verify both attributes are present.
    m = re.search(r'<hp:tbl[^>]*>', section)
    assert m is not None, "no <hp:tbl> generated"
    tag = m.group(0)
    assert 'pageBreak="TABLE"' in tag, tag
    assert 'repeatHeader="1"' in tag, tag


def test_builder_default_unchanged(tmp_path):
    """Calling add_table without the new kwargs must produce the legacy XML."""
    out = tmp_path / "default.hwpx"
    doc = HwpxBuilder()
    doc.add_paragraph("test")
    doc.add_table([["A", "B"], ["1", "2"]])
    doc.save(str(out))

    import zipfile
    with zipfile.ZipFile(out) as z:
        section = z.read("Contents/section0.xml").decode("utf-8")
    m = re.search(r'<hp:tbl[^>]*>', section)
    assert m is not None
    tag = m.group(0)
    assert 'pageBreak="CELL"' in tag
    assert 'repeatHeader="0"' in tag
