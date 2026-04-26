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
def test_write_zip_archive_auto_strips(tmp_path):
    """write_zip_archive(strip_linesegs=True) 기본 동작 — 자동 strip."""
    from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

    out = tmp_path / "auto_strip.hwpx"
    archive = read_zip_archive(str(SAFE_FIXTURE))
    write_zip_archive(str(out), archive)  # default True

    new_xml = _read_section0(out)
    assert count_r3_violations(new_xml) == 0
    assert "<hp:linesegarray" not in new_xml


@pytest.mark.skipif(not _has_fixture(), reason="fixture missing")
def test_write_zip_archive_opt_out(tmp_path):
    """write_zip_archive(strip_linesegs=False) — 옵트아웃 시 보존."""
    from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

    out = tmp_path / "preserved.hwpx"
    archive = read_zip_archive(str(SAFE_FIXTURE))
    write_zip_archive(str(out), archive, strip_linesegs=False)

    new_xml = _read_section0(out)
    assert count_r3_violations(new_xml) == 3  # 원본 그대로


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
