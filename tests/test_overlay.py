"""Tests for pyhwpxlib.json_io.overlay — extract and apply with hp:t parts."""
from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

# Module under test
from pyhwpxlib.json_io.overlay import (
    FORMAT_VERSION,
    _HP,
    _HH,
    _extract_cell_full_text,
    _extract_from_paragraph,
    _replace_text_in_xml,
    _xml_escape,
    apply_overlay,
    extract_overlay,
)


# ─── Helpers ───────────────────────────────────


def _make_section_xml(body_content: str) -> str:
    """Wrap paragraph content in a minimal OWPML section XML."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
        ' xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"'
        ' xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core">'
        f"{body_content}"
        "</hp:sec>"
    )


def _make_header_xml() -> str:
    """Minimal header.xml for extract_overlay."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head">'
        '<hh:charProperties>'
        '<hh:charPr id="0" height="1000" bold="0" italic="0"/>'
        '</hh:charProperties>'
        '</hh:head>'
    )


def _create_hwpx_zip(tmp_path: Path, section_xml: str, header_xml: str | None = None) -> Path:
    """Create a minimal HWPX ZIP for testing."""
    hwpx_path = tmp_path / "test.hwpx"
    if header_xml is None:
        header_xml = _make_header_xml()
    with zipfile.ZipFile(hwpx_path, "w") as zf:
        # mimetype must be first and stored uncompressed
        zf.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/hwp+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        zf.writestr("Contents/header.xml", header_xml)
        zf.writestr("Contents/section0.xml", section_xml)
    return hwpx_path


# ─── _xml_escape ───────────────────────────────


class TestXmlEscape:
    def test_amp(self):
        assert _xml_escape("A&B") == "A&amp;B"

    def test_lt_gt(self):
        assert _xml_escape("a<b>c") == "a&lt;b&gt;c"

    def test_plain(self):
        assert _xml_escape("hello") == "hello"

    def test_korean(self):
        assert _xml_escape("한글텍스트") == "한글텍스트"


# ─── _replace_text_in_xml ─────────────────────


class TestReplaceTextInXml:
    def test_single_part(self):
        xml = '<hp:run><hp:t>안녕하세요</hp:t></hp:run>'
        result = _replace_text_in_xml(xml, ["안녕하세요"], "반갑습니다")
        assert "<hp:t>반갑습니다</hp:t>" in result

    def test_multi_part(self):
        xml = '<hp:run><hp:t>울산중부</hp:t><hp:t>소방서</hp:t></hp:run>'
        result = _replace_text_in_xml(xml, ["울산중부", "소방서"], "울산중부 구청")
        assert "<hp:t>울산중부 구청</hp:t>" in result
        # The two original <hp:t> elements should be merged into one
        assert "소방서" not in result

    def test_multi_part_with_whitespace(self):
        xml = '<hp:run><hp:t>울산중부</hp:t>  \n  <hp:t>소방서</hp:t></hp:run>'
        result = _replace_text_in_xml(xml, ["울산중부", "소방서"], "울산중부 구청")
        assert "<hp:t>울산중부 구청</hp:t>" in result

    def test_xml_special_chars_in_original(self):
        xml = '<hp:run><hp:t>A&amp;B</hp:t></hp:run>'
        result = _replace_text_in_xml(xml, ["A&B"], "C&D")
        assert "<hp:t>C&amp;D</hp:t>" in result

    def test_xml_special_chars_lt_gt(self):
        xml = '<hp:run><hp:t>x&lt;y</hp:t></hp:run>'
        result = _replace_text_in_xml(xml, ["x<y"], "a>b")
        assert "<hp:t>a&gt;b</hp:t>" in result

    def test_no_match_returns_unchanged(self):
        xml = '<hp:run><hp:t>hello</hp:t></hp:run>'
        result = _replace_text_in_xml(xml, ["world"], "replaced")
        assert result == xml

    def test_replaces_only_first_occurrence(self):
        xml = '<hp:t>hello</hp:t><hp:t>hello</hp:t>'
        result = _replace_text_in_xml(xml, ["hello"], "world")
        assert result.count("world") == 1
        assert result.count("hello") == 1


# ─── extract_overlay — original_parts ──────────


class TestExtractOriginalParts:
    def test_single_hp_t_text(self, tmp_path):
        sec_xml = _make_section_xml(
            '<hp:p><hp:run charPrIDRef="0"><hp:t>전체텍스트</hp:t></hp:run></hp:p>'
        )
        hwpx = _create_hwpx_zip(tmp_path, sec_xml)
        overlay = extract_overlay(str(hwpx), include_style_hints=True)
        assert len(overlay["texts"]) == 1
        entry = overlay["texts"][0]
        assert entry["original_parts"] == ["전체텍스트"]
        assert entry["value"] == "전체텍스트"
        assert entry["original"] == "전체텍스트"

    def test_multi_hp_t_text(self, tmp_path):
        sec_xml = _make_section_xml(
            '<hp:p><hp:run charPrIDRef="0">'
            "<hp:t>울산중부</hp:t><hp:t>소방서</hp:t>"
            "</hp:run></hp:p>"
        )
        hwpx = _create_hwpx_zip(tmp_path, sec_xml)
        overlay = extract_overlay(str(hwpx), include_style_hints=True)
        assert len(overlay["texts"]) == 1
        entry = overlay["texts"][0]
        assert entry["original_parts"] == ["울산중부", "소방서"]
        assert entry["value"] == "울산중부소방서"
        assert entry["original"] == "울산중부소방서"


# ─── extract — cell text join ──────────────────


class TestCellTextJoin:
    def test_cell_text_no_space_join(self):
        """Cell text should use '' join, not ' ' join."""
        xml = (
            '<hp:tc xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
            "<hp:p><hp:run><hp:t>울산</hp:t><hp:t>중부</hp:t></hp:run></hp:p>"
            "</hp:tc>"
        )
        tc_el = ET.fromstring(xml)
        text = _extract_cell_full_text(tc_el)
        assert text == "울산중부"  # No space between parts


# ─── apply_overlay round-trip ──────────────────


class TestApplyOverlay:
    def test_roundtrip_single_text(self, tmp_path):
        sec_xml = _make_section_xml(
            '<hp:p><hp:run charPrIDRef="0"><hp:t>원본텍스트</hp:t></hp:run></hp:p>'
        )
        hwpx = _create_hwpx_zip(tmp_path, sec_xml)
        overlay = extract_overlay(str(hwpx), include_style_hints=True)

        # Modify text
        overlay["texts"][0]["value"] = "새텍스트"
        output = str(tmp_path / "out.hwpx")
        apply_overlay(str(hwpx), overlay, output)

        # Verify
        with zipfile.ZipFile(output) as zf:
            result_xml = zf.read("Contents/section0.xml").decode("utf-8")
            assert "새텍스트" in result_xml
            assert "원본텍스트" not in result_xml

    def test_roundtrip_split_hp_t(self, tmp_path):
        sec_xml = _make_section_xml(
            '<hp:p><hp:run charPrIDRef="0">'
            "<hp:t>울산중부</hp:t><hp:t>소방서</hp:t>"
            "</hp:run></hp:p>"
        )
        hwpx = _create_hwpx_zip(tmp_path, sec_xml)
        overlay = extract_overlay(str(hwpx), include_style_hints=True)

        # Modify text
        overlay["texts"][0]["value"] = "울산중부 구청"
        output = str(tmp_path / "out.hwpx")
        apply_overlay(str(hwpx), overlay, output)

        # Verify
        with zipfile.ZipFile(output) as zf:
            result_xml = zf.read("Contents/section0.xml").decode("utf-8")
            assert "울산중부 구청" in result_xml
            assert "소방서" not in result_xml

    def test_uses_zipfile_not_subprocess(self, tmp_path):
        """apply_overlay should NOT call subprocess."""
        import pyhwpxlib.json_io.overlay as overlay_mod

        assert not hasattr(overlay_mod, "subprocess") or "subprocess" not in dir(
            overlay_mod
        ), "subprocess should not be imported in overlay module"

    def test_preserves_mimetype_first(self, tmp_path):
        sec_xml = _make_section_xml(
            '<hp:p><hp:run charPrIDRef="0"><hp:t>텍스트</hp:t></hp:run></hp:p>'
        )
        hwpx = _create_hwpx_zip(tmp_path, sec_xml)
        overlay = extract_overlay(str(hwpx), include_style_hints=True)
        overlay["texts"][0]["value"] = "수정됨"
        output = str(tmp_path / "out.hwpx")
        apply_overlay(str(hwpx), overlay, output)

        with zipfile.ZipFile(output) as zf:
            entries = zf.infolist()
            assert entries[0].filename == "mimetype"
            assert entries[0].compress_type == zipfile.ZIP_STORED

    def test_image_replacement(self, tmp_path):
        sec_xml = _make_section_xml(
            '<hp:p><hp:run charPrIDRef="0"><hp:t>텍스트</hp:t></hp:run></hp:p>'
        )
        # Create HWPX with a BinData entry
        hwpx_path = tmp_path / "test_img.hwpx"
        with zipfile.ZipFile(hwpx_path, "w") as zf:
            zf.writestr(
                zipfile.ZipInfo("mimetype"),
                "application/hwp+zip",
                compress_type=zipfile.ZIP_STORED,
            )
            zf.writestr("Contents/header.xml", _make_header_xml())
            zf.writestr("Contents/section0.xml", sec_xml)
            zf.writestr("BinData/BIN0001.png", b"original_image_data")

        overlay = extract_overlay(str(hwpx_path), include_style_hints=True)
        output = str(tmp_path / "out_img.hwpx")
        new_img = b"new_image_data"
        apply_overlay(
            str(hwpx_path),
            overlay,
            output,
            image_replacements={"BIN0001": new_img},
        )

        with zipfile.ZipFile(output) as zf:
            assert zf.read("BinData/BIN0001.png") == new_img

    def test_image_replacement_nonexistent_binref_skipped(self, tmp_path):
        """Nonexistent bin_ref in image_replacements should be silently skipped."""
        sec_xml = _make_section_xml(
            '<hp:p><hp:run charPrIDRef="0"><hp:t>텍스트</hp:t></hp:run></hp:p>'
        )
        hwpx_path = tmp_path / "test_img2.hwpx"
        with zipfile.ZipFile(hwpx_path, "w") as zf:
            zf.writestr(
                zipfile.ZipInfo("mimetype"),
                "application/hwp+zip",
                compress_type=zipfile.ZIP_STORED,
            )
            zf.writestr("Contents/header.xml", _make_header_xml())
            zf.writestr("Contents/section0.xml", sec_xml)
            zf.writestr("BinData/BIN0001.png", b"original_data")

        overlay = extract_overlay(str(hwpx_path), include_style_hints=True)
        output = str(tmp_path / "out_skip.hwpx")
        # Replace a bin_ref that doesn't exist in the ZIP
        apply_overlay(
            str(hwpx_path),
            overlay,
            output,
            image_replacements={"BIN9999": b"should_be_ignored"},
        )

        # Original image should be preserved
        with zipfile.ZipFile(output) as zf:
            assert zf.read("BinData/BIN0001.png") == b"original_data"

    def test_image_replacement_preserves_unreplaced(self, tmp_path):
        """BinData files not in image_replacements dict should be preserved."""
        sec_xml = _make_section_xml(
            '<hp:p><hp:run charPrIDRef="0"><hp:t>텍스트</hp:t></hp:run></hp:p>'
        )
        hwpx_path = tmp_path / "test_img3.hwpx"
        with zipfile.ZipFile(hwpx_path, "w") as zf:
            zf.writestr(
                zipfile.ZipInfo("mimetype"),
                "application/hwp+zip",
                compress_type=zipfile.ZIP_STORED,
            )
            zf.writestr("Contents/header.xml", _make_header_xml())
            zf.writestr("Contents/section0.xml", sec_xml)
            zf.writestr("BinData/BIN0001.png", b"img1_data")
            zf.writestr("BinData/BIN0002.jpg", b"img2_data")

        overlay = extract_overlay(str(hwpx_path), include_style_hints=True)
        output = str(tmp_path / "out_partial.hwpx")
        # Only replace BIN0001, BIN0002 should be preserved
        apply_overlay(
            str(hwpx_path),
            overlay,
            output,
            image_replacements={"BIN0001": b"new_img1"},
        )

        with zipfile.ZipFile(output) as zf:
            assert zf.read("BinData/BIN0001.png") == b"new_img1"
            assert zf.read("BinData/BIN0002.jpg") == b"img2_data"

    def test_image_replacement_exact_bytes(self, tmp_path):
        """Replaced image bytes must match exactly (binary fidelity)."""
        sec_xml = _make_section_xml(
            '<hp:p><hp:run charPrIDRef="0"><hp:t>텍스트</hp:t></hp:run></hp:p>'
        )
        hwpx_path = tmp_path / "test_img4.hwpx"
        # Create a "PNG" with specific byte pattern
        png_bytes = bytes(range(256)) * 10  # 2560 bytes
        with zipfile.ZipFile(hwpx_path, "w") as zf:
            zf.writestr(
                zipfile.ZipInfo("mimetype"),
                "application/hwp+zip",
                compress_type=zipfile.ZIP_STORED,
            )
            zf.writestr("Contents/header.xml", _make_header_xml())
            zf.writestr("Contents/section0.xml", sec_xml)
            zf.writestr("BinData/BIN0001.png", b"old")

        overlay = extract_overlay(str(hwpx_path), include_style_hints=True)
        output = str(tmp_path / "out_exact.hwpx")
        apply_overlay(
            str(hwpx_path),
            overlay,
            output,
            image_replacements={"BIN0001": png_bytes},
        )

        with zipfile.ZipFile(output) as zf:
            assert zf.read("BinData/BIN0001.png") == png_bytes

    def test_no_image_replacements_no_regression(self, tmp_path):
        """apply_overlay without image_replacements should not affect BinData."""
        sec_xml = _make_section_xml(
            '<hp:p><hp:run charPrIDRef="0"><hp:t>원본</hp:t></hp:run></hp:p>'
        )
        hwpx_path = tmp_path / "test_noreg.hwpx"
        with zipfile.ZipFile(hwpx_path, "w") as zf:
            zf.writestr(
                zipfile.ZipInfo("mimetype"),
                "application/hwp+zip",
                compress_type=zipfile.ZIP_STORED,
            )
            zf.writestr("Contents/header.xml", _make_header_xml())
            zf.writestr("Contents/section0.xml", sec_xml)
            zf.writestr("BinData/BIN0001.png", b"keep_this")

        overlay = extract_overlay(str(hwpx_path), include_style_hints=True)
        overlay["texts"][0]["value"] = "수정"
        output = str(tmp_path / "out_noreg.hwpx")
        apply_overlay(str(hwpx_path), overlay, output)  # No image_replacements

        with zipfile.ZipFile(output) as zf:
            assert zf.read("BinData/BIN0001.png") == b"keep_this"

    def test_table_cell_replacement(self, tmp_path):
        sec_xml = _make_section_xml(
            "<hp:p><hp:run><hp:tbl>"
            "<hp:tr><hp:tc>"
            "<hp:p><hp:run><hp:t>셀값</hp:t></hp:run></hp:p>"
            "</hp:tc></hp:tr>"
            "</hp:tbl></hp:run></hp:p>"
        )
        hwpx = _create_hwpx_zip(tmp_path, sec_xml)
        overlay = extract_overlay(str(hwpx), include_style_hints=True, include_images=False)

        # Find table cell and modify
        assert len(overlay["tables"]) == 1
        cell = overlay["tables"][0]["cells"][0]
        assert cell["original_parts"] == ["셀값"]
        cell["value"] = "새셀값"

        output = str(tmp_path / "out.hwpx")
        apply_overlay(str(hwpx), overlay, output)

        with zipfile.ZipFile(output) as zf:
            result_xml = zf.read("Contents/section0.xml").decode("utf-8")
            assert "새셀값" in result_xml
            assert ">셀값<" not in result_xml
