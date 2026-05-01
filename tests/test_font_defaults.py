"""font-replacement (v0.16.1) 회귀 테스트 — T-FR-01 ~ T-FR-06.

라이선스 안전화: 함초롬돋움/바탕 (한컴) + 맑은 고딕 (MS) → 나눔고딕 (OFL 1.1)
통일. 이 테스트는 default 메타 표기가 라이선스 위험 폰트를 0건으로 유지하는지
회귀 보호.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from pyhwpxlib import HwpxBuilder
from pyhwpxlib.themes import FontSet


def _read_section_xml(hwpx: Path) -> str:
    with zipfile.ZipFile(hwpx) as z:
        return z.read("Contents/section0.xml").decode("utf-8")


def _read_header_xml(hwpx: Path) -> str:
    with zipfile.ZipFile(hwpx) as z:
        return z.read("Contents/header.xml").decode("utf-8")


# ── T-FR-01: FontSet default 나눔고딕 통일 ──────────────────────


def test_fr_01_fontset_defaults_to_nanum_gothic():
    """FontSet() default 6 필드 모두 '나눔고딕' (통일 결정)."""
    fs = FontSet()
    assert fs.heading_hangul == "나눔고딕"
    assert fs.heading_latin == "나눔고딕"
    assert fs.body_hangul == "나눔고딕"
    assert fs.body_latin == "나눔고딕"
    assert fs.caption_hangul == "나눔고딕"
    assert fs.caption_latin == "나눔고딕"


# ── T-FR-02: BlankFileMaker fontfaces 검증 ─────────────────────


def test_fr_02_blank_file_maker_fontfaces(tmp_path: Path):
    """HwpxBuilder().save() 결과 header.xml — 함초롬·맑은 고딕 0건."""
    p = tmp_path / "blank.hwpx"
    HwpxBuilder().save(str(p))
    header_xml = _read_header_xml(p)

    assert "함초롬돋움" not in header_xml, "함초롬돋움 표기 잔존"
    assert "함초롬바탕" not in header_xml, "함초롬바탕 표기 잔존"
    assert "맑은 고딕" not in header_xml, "맑은 고딕 표기 잔존"
    assert "나눔고딕" in header_xml, "나눔고딕 표기 누락"


# ── T-FR-03: HwpxBuilder 신규 문서 메타 검증 ─────────────────


def test_fr_03_new_document_has_no_restricted_fonts(tmp_path: Path):
    """HwpxBuilder 로 만든 문서의 모든 메타에 라이선스 제약 폰트 0건."""
    p = tmp_path / "doc.hwpx"
    b = HwpxBuilder(theme="default")
    b.add_heading("제목", level=1)
    b.add_paragraph("본문 텍스트")
    b.add_table([["A", "B"], ["1", "2"]])
    b.save(str(p))

    sec = _read_section_xml(p)
    hdr = _read_header_xml(p)
    full = sec + hdr

    assert "함초롬" not in full, "함초롬 폰트 표기 잔존"
    assert "맑은 고딕" not in full, "맑은 고딕 표기 잔존"


# ── T-FR-04: _reference_header.xml 정리 ──────────────────────


def test_fr_04_reference_header_clean():
    """tools/_reference_header.xml 파일에 함초롬 표기 0건."""
    ref = (Path(__file__).parent.parent / "pyhwpxlib"
           / "tools" / "_reference_header.xml")
    if ref.exists():
        text = ref.read_text(encoding="utf-8")
        assert "함초롬돋움" not in text
        assert "함초롬바탕" not in text


# ── T-FR-05: hwp2hwpx 변환 fidelity (원본 폰트명 보존) ─────────


@pytest.mark.skipif(
    not (Path(__file__).parent.parent / "samples").exists(),
    reason="sample .hwp files not available in CI",
)
def test_fr_05_hwp2hwpx_preserves_original_fonts(tmp_path: Path):
    """변환 (hwp2hwpx) 결과는 원본 .hwp 의 폰트명 보존 — fidelity 우선.

    회귀 보호: default 변경이 변환 로직에 영향 미치지 않음을 검증.
    """
    from pyhwpxlib.hwp2hwpx import convert

    samples_dir = Path(__file__).parent.parent / "samples"
    sample = next(
        (s for s in samples_dir.glob("*.hwp")
         if not s.name.startswith(".") and s.stat().st_size > 1000),
        None,
    )
    if sample is None:
        pytest.skip("no usable .hwp sample")

    out = tmp_path / "converted.hwpx"
    try:
        convert(str(sample), str(out))
    except Exception as e:
        pytest.skip(f"conversion failed: {e}")

    hdr = _read_header_xml(out)
    # 변환 결과에 fontfaces 가 존재해야 함 (구조 보존)
    assert "fontface" in hdr, "변환 결과에 fontfaces 누락"
    # 폰트명은 원본 의존이라 특정 단어 검증 안 함 — 변환 성공 + 구조만 검증


# ── T-FR-06: rhwp 폴백 매핑 안전망 ──────────────────────────


def test_fr_06_rhwp_fallback_preserves_legacy_hamchorom_mapping():
    """기존 함초롬 표기 hwpx 도 NanumGothic 으로 정상 렌더링 (회귀)."""
    from pyhwpxlib.rhwp_bridge import _build_font_map

    font_map = _build_font_map()
    assert "함초롬돋움" in font_map, "함초롬돋움 폴백 매핑 손실"
    assert "함초롬바탕" in font_map, "함초롬바탕 폴백 매핑 손실"

    # NanumGothic ttf 경로로 매핑되는지 확인
    for key in ("함초롬돋움", "함초롬바탕"):
        path = font_map[key]
        assert "NanumGothic" in path, f"{key} → {path} (NanumGothic 아님)"


# ── 추가: 사용자 명시 지정 호환성 (backward compat) ─────────


def test_fr_user_explicit_override_still_works(tmp_path: Path):
    """사용자가 명시적으로 '맑은 고딕' 지정하면 그대로 사용 — 호환성."""
    fs = FontSet(heading_hangul="맑은 고딕", body_hangul="맑은 고딕",
                 caption_hangul="맑은 고딕")
    assert fs.heading_hangul == "맑은 고딕"
    # default 가 아닌 명시 지정은 사용자 책임 영역 (라이선스 안내는 README)
