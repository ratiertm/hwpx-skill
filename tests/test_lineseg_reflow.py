"""Tests for postprocess.lineseg_reflow.

Covers Hancom security-trigger fix (linesegarray strip) and R3 detection.
Fixture: 지청운_전문가활용내역서_2_safe.hwpx (known to trigger Hancom warning).
"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest

from pyhwpxlib.postprocess import (
    count_r3_violations,
    fix_r3_violations,
    strip_linesegarrays,
    strip_linesegs_in_section_xmls,
    count_textpos_overflow,
    fix_textpos_overflow,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAFE_FIXTURE = (
    PROJECT_ROOT / "Test" / "output" / "지청운_전문가활용내역서_2_safe.hwpx"
)


def _read_section0(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        return z.read("Contents/section0.xml").decode("utf-8")


def _has_fixture() -> bool:
    return SAFE_FIXTURE.exists()


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_count_r3_in_known_safe_fixture():
    """지청운 fixture는 알려진 R3 위반 3건을 가진다 (한컴 보안 경고 트리거)."""
    xml = _read_section0(SAFE_FIXTURE)
    assert count_r3_violations(xml) == 3


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_strip_remove_zeros_r3():
    """remove 모드: linesegarray 통째 제거 → R3 카운트 0."""
    xml = _read_section0(SAFE_FIXTURE)
    new_xml, n = strip_linesegarrays(xml, mode="remove")
    assert n > 0
    assert count_r3_violations(new_xml) == 0
    assert "<hp:linesegarray" not in new_xml


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_strip_empty_zeros_r3():
    """empty 모드: 빈 linesegarray 유지 → R3 카운트 0 (lineseg 0개)."""
    xml = _read_section0(SAFE_FIXTURE)
    new_xml, n = strip_linesegarrays(xml, mode="empty")
    assert n > 0
    assert count_r3_violations(new_xml) == 0
    # 여는 태그는 남아있어야 함
    assert "<hp:linesegarray" in new_xml
    # 내용은 비어있어야 함 (lineseg 자식 없음)
    assert "<hp:lineseg " not in new_xml


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_strip_preserves_text_content():
    """strip 후에도 hp:t 텍스트는 보존되어야 한다."""
    xml = _read_section0(SAFE_FIXTURE)
    new_xml, _ = strip_linesegarrays(xml, mode="remove")
    # 임의 검증: 원본의 모든 hp:t 텍스트가 출력에도 존재해야 함
    import re
    orig_texts = re.findall(r"<hp:t[^>]*>([^<]*)</hp:t>", xml)
    new_texts = re.findall(r"<hp:t[^>]*>([^<]*)</hp:t>", new_xml)
    assert orig_texts == new_texts


def test_strip_invalid_mode():
    with pytest.raises(ValueError):
        strip_linesegarrays("<dummy/>", mode="bogus")


def test_strip_no_linesegarray_is_noop():
    xml = "<hp:p><hp:run><hp:t>x</hp:t></hp:run></hp:p>"
    new_xml, n = strip_linesegarrays(xml, mode="remove")
    assert n == 0
    assert new_xml == xml


def test_helper_strips_only_section_files():
    """section*.xml 만 처리, 다른 파일은 건드리지 않음."""
    files = {
        "Contents/section0.xml": (
            b"<a><hp:linesegarray><hp:lineseg /></hp:linesegarray></a>"
        ),
        "Contents/header.xml": (
            b"<h><hp:linesegarray><hp:lineseg /></hp:linesegarray></h>"
        ),
    }
    new_files, total = strip_linesegs_in_section_xmls(files, mode="remove")
    assert total == 1
    assert b"linesegarray" not in new_files["Contents/section0.xml"]
    # header.xml 은 그대로
    assert new_files["Contents/header.xml"] == files["Contents/header.xml"]


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_write_zip_archive_default_preserves_input_v0_14(tmp_path):
    """v0.14.0: default is strip_linesegs=False — non-standard input is preserved.

    rhwp-aligned default: pyhwpxlib does not silently fix non-standard
    structures so external renderers / validators see exactly what was
    saved. Callers must opt in via strip_linesegs="precise".
    """
    from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

    out = tmp_path / "default.hwpx"
    archive = read_zip_archive(str(SAFE_FIXTURE))
    fixed = write_zip_archive(str(out), archive)  # default False (no fix)

    new_xml = _read_section0(out)
    # 원본의 비표준 lineseg 보존 (R3 / textpos overflow 모두 그대로)
    assert count_r3_violations(new_xml) == 3  # 원본 그대로
    assert "<hp:linesegarray" in new_xml
    # 반환값: fix 없을 때 0
    assert fixed == 0


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_write_zip_archive_explicit_precise_fixes_overflow(tmp_path):
    """strip_linesegs="precise" (or True) — explicit opt-in keeps prior behavior."""
    from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

    out = tmp_path / "precise.hwpx"
    archive = read_zip_archive(str(SAFE_FIXTURE))
    fixed = write_zip_archive(str(out), archive, strip_linesegs="precise")

    new_xml = _read_section0(out)
    assert count_textpos_overflow(new_xml) == 0
    # R3 (rhwp 렌더 휴리스틱) 은 그대로 유지 (precise 의도)
    assert count_r3_violations(new_xml) > 0
    # linesegarray 는 보존
    assert "<hp:linesegarray" in new_xml
    # 반환값: 보정한 lineseg 개수가 보고됨
    assert fixed > 0


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_write_zip_archive_back_compat_true(tmp_path):
    """strip_linesegs=True 는 'precise' 의 alias (v0.13.0/0.13.1 호환)."""
    from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

    out = tmp_path / "back_compat.hwpx"
    archive = read_zip_archive(str(SAFE_FIXTURE))
    write_zip_archive(str(out), archive, strip_linesegs=True)

    new_xml = _read_section0(out)
    assert count_textpos_overflow(new_xml) == 0
    # True == precise -> linesegarray 보존
    assert "<hp:linesegarray" in new_xml


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_write_zip_archive_explicit_false_same_as_default(tmp_path):
    """strip_linesegs=False — 명시적 opt-out (v0.14.0 default와 동일)."""
    from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

    out = tmp_path / "preserved.hwpx"
    archive = read_zip_archive(str(SAFE_FIXTURE))
    write_zip_archive(str(out), archive, strip_linesegs=False)

    new_xml = _read_section0(out)
    assert count_r3_violations(new_xml) == 3  # 원본 그대로


# ─────────────────────────────────────────────────────────────────────
# Phase 2 verified trigger: lineseg.textpos > UTF16(text) (2026-04-27)
# ─────────────────────────────────────────────────────────────────────


def _make_paragraph(text: str, lineseg_textpos: int) -> str:
    return (
        '<hp:p paraPrIDRef="0" styleIDRef="0">'
        '<hp:run charPrIDRef="0">'
        f'<hp:t>{text}</hp:t>'
        '</hp:run>'
        '<hp:linesegarray>'
        '<hp:lineseg textpos="0" vertpos="0" vertsize="1000" textheight="1000" '
        'baseline="850" spacing="600" horzpos="0" horzsize="32864" flags="393216"/>'
        f'<hp:lineseg textpos="{lineseg_textpos}" vertpos="1600" vertsize="1000" '
        'textheight="1000" baseline="850" spacing="600" horzpos="0" horzsize="32864" '
        'flags="393216"/>'
        '</hp:linesegarray>'
        '</hp:p>'
    )


def test_count_textpos_overflow_detects_short_text_with_high_textpos():
    """text 7자, lineseg textpos=61 → overflow 1건 (지청운 케이스 재현)."""
    p = _make_paragraph("(별도 기재)", lineseg_textpos=61)
    assert count_textpos_overflow(p) == 1


def test_count_textpos_overflow_no_false_positive_when_text_is_long():
    """text 67자, lineseg textpos=61 → overflow 0건 (이준구 케이스)."""
    long_addr = "A" * 67
    p = _make_paragraph(long_addr, lineseg_textpos=61)
    assert count_textpos_overflow(p) == 0


def test_fix_textpos_overflow_removes_only_overflow_lineseg():
    """fix는 overflow한 lineseg만 제거하고 나머지는 보존."""
    p = _make_paragraph("(별도 기재)", lineseg_textpos=61)
    assert "textpos=\"61\"" in p
    assert "textpos=\"0\"" in p

    fixed, removed = fix_textpos_overflow(p)
    assert removed == 1
    # textpos=0 lineseg는 보존
    assert "textpos=\"0\"" in fixed
    # textpos=61 lineseg는 제거
    assert "textpos=\"61\"" not in fixed
    # overflow 0건
    assert count_textpos_overflow(fixed) == 0


def test_fix_textpos_overflow_keeps_one_lineseg_minimum():
    """모든 lineseg가 overflow 면 OWPML 보존용 빈 lineseg 1개 남김."""
    p = (
        '<hp:p paraPrIDRef="0" styleIDRef="0">'
        '<hp:run charPrIDRef="0"><hp:t>x</hp:t></hp:run>'
        '<hp:linesegarray>'
        '<hp:lineseg textpos="50" vertpos="0" vertsize="1000" textheight="1000" '
        'baseline="850" spacing="600" horzpos="0" horzsize="0" flags="393216"/>'
        '</hp:linesegarray>'
        '</hp:p>'
    )
    fixed, removed = fix_textpos_overflow(p)
    assert removed == 1
    assert "<hp:linesegarray>" in fixed
    assert fixed.count("<hp:lineseg ") >= 1  # OWPML 보존


def test_utf16_supplementary_text_counts_as_2_units():
    """이모지 등 BMP 외 문자는 UTF-16에서 2 unit. textpos는 UTF-16 기준."""
    # \U0001F600 (😀) = 2 UTF-16 units
    text = "ab" + "\U0001F600"  # 3 code points but 4 UTF-16 units
    # textpos=4 → overflow 아님 (정확히 끝)
    p_ok = _make_paragraph(text, lineseg_textpos=4)
    assert count_textpos_overflow(p_ok) == 0
    # textpos=5 → overflow (4 < 5)
    p_ng = _make_paragraph(text, lineseg_textpos=5)
    assert count_textpos_overflow(p_ng) == 1


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_jicheongun_fixture_has_textpos_overflow():
    """지청운 fixture는 textpos overflow 1건 (한컴 보안 트리거)."""
    xml = _read_section0(SAFE_FIXTURE)
    # 단일 alpha 케이스 (인덱스 6 paragraph)
    assert count_textpos_overflow(xml) == 1


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_jicheongun_precise_fix_eliminates_overflow(tmp_path):
    """precise fix가 지청운 한컴 트리거 1건만 제거 (lineseg 39개 보존)."""
    xml = _read_section0(SAFE_FIXTURE)
    fixed, n = fix_textpos_overflow(xml)
    assert n == 1
    assert count_textpos_overflow(fixed) == 0
    # lineseg 갯수: 40 → 39 (1개만 제거)
    assert xml.count("<hp:lineseg ") == 40
    assert fixed.count("<hp:lineseg ") == 39
    # linesegarray 39개 모두 보존 (strip 'remove' 와 다름)
    assert fixed.count("<hp:linesegarray>") == 39


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_write_zip_archive_precise_mode(tmp_path):
    """v0.14.0: precise mode is opt-in, default no-op preserves overflow."""
    from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

    out = tmp_path / "precise.hwpx"
    archive = read_zip_archive(str(SAFE_FIXTURE))
    write_zip_archive(str(out), archive, strip_linesegs="precise")  # explicit

    new_xml = _read_section0(out)
    assert count_textpos_overflow(new_xml) == 0
    # linesegarray 보존 (precise는 통째 제거 안 함)
    assert "<hp:linesegarray>" in new_xml


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_write_zip_archive_remove_mode_still_works(tmp_path):
    """기존 'remove' 모드도 호환 (강한 망치)."""
    from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

    out = tmp_path / "remove.hwpx"
    archive = read_zip_archive(str(SAFE_FIXTURE))
    write_zip_archive(str(out), archive, strip_linesegs="remove")

    new_xml = _read_section0(out)
    assert count_textpos_overflow(new_xml) == 0
    # linesegarray 통째 제거
    assert "<hp:linesegarray" not in new_xml


def test_write_zip_archive_invalid_mode_raises(tmp_path):
    from pyhwpxlib.package_ops import ZipArchive, write_zip_archive
    archive = ZipArchive(infos=[], files={})
    with pytest.raises(ValueError):
        write_zip_archive(str(tmp_path / "x.hwpx"), archive, strip_linesegs="bogus")


def test_fix_r3_does_not_eliminate_security_trigger():
    """[regression] R3 fix(분할)는 한컴 보안 트리거 회피에 부족함을 문서화.

    이 테스트는 'R3가 0이 되어도 한컴 경고는 사라지지 않는다'는 발견을
    회귀 방지로 못박는다. 실제 회피는 strip_linesegarrays가 담당.
    """
    # 인위적인 R3 위반 paragraph
    p = (
        '<hp:p paraPrIDRef="0" styleIDRef="0">'
        '<hp:run charPrIDRef="0">'
        '<hp:t>' + 'A' * 50 + '</hp:t>'
        '</hp:run>'
        '<hp:linesegarray>'
        '<hp:lineseg textpos="0" vertpos="0" vertsize="1000" textheight="1000" '
        'baseline="850" spacing="600" horzpos="0" horzsize="42520" flags="393216"/>'
        '</hp:linesegarray>'
        '</hp:p>'
    )
    assert count_r3_violations(p) == 1
    fixed, n = fix_r3_violations(p)
    assert n == 1
    assert count_r3_violations(fixed) == 0
    # NB: fixed 는 R3 검사를 통과하지만 한컴 보안 경고는 별도 — strip 권장.
