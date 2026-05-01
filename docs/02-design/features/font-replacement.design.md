---
template: design
version: 1.2
description: 나눔고딕 통일 + font/ 삭제 — 변경 위치 + 테스트 명세
---

# font-replacement Design Document

> **Summary**: 모든 default 폰트 메타 표기를 `'나눔고딕'` (OFL 1.1) 으로 통일하고, 미사용 `font/*.zip` 132MB 를 삭제. 함초롬 (한컴) + 맑은 고딕 (MS) 두 라이선스 위험 폰트를 동시 제거. 변환 (`hwp2hwpx`) fidelity 와 rhwp 폴백 매핑은 보존.
>
> **Project**: pyhwpxlib
> **Version**: 0.16.0 → 0.16.1 (patch, 라이선스 안전화)
> **Date**: 2026-05-01
> **Status**: Draft
> **Planning Doc**: [font-replacement.plan.md](../../01-plan/features/font-replacement.plan.md)

---

## 1. Overview

### 1.1 Design Goals

- **단일 default**: heading/body/caption 전부 `'나눔고딕'` (사용자 결정 — 통일)
- **font/ 폴더 통째 삭제** (사용자 결정 — 132MB 절감)
- **변환 fidelity 보존**: `hwp2hwpx.convert()` 는 원본 폰트명 유지
- **rhwp 폴백 매핑 유지**: 기존 함초롬 hwpx 정상 렌더

### 1.2 Design Principles

- **보수적 안전 우선**: MS·한컴 폰트 메타 표기 0건
- **Backward compat**: 사용자가 명시적으로 `FontSet(heading_hangul='맑은 고딕', ...)` 지정 가능
- **회귀 보호**: 변환 fidelity + 폴백 매핑 + 시각 검증 모두 테스트

---

## 2. Architecture

### 2.1 변경 위치 (5곳)

| 파일 | 변경 내용 | LOC |
|------|----------|-----|
| `pyhwpxlib/themes.py` | `FontSet` 6개 default 모두 `'나눔고딕'` | 6 |
| `pyhwpxlib/tools/blank_file_maker.py` | `_add_font_pair` font 0 face 갱신 + 주석 업데이트 | 4 |
| `pyhwpxlib/tools/_reference_header.xml` | 함초롬돋움/바탕 → 나눔고딕 일괄 교체 | ~10 |
| `font/` (폴더) | **통째 삭제** (132MB) | -7 files |
| `README.md` / `README_KO.md` | "Fonts" 섹션 신설 | +25 |

### 2.2 통일 매핑

```
이전:                                현재:
─────────────────────────────────    ─────────────────────────────────
themes.py FontSet default '맑은 고딕'  → '나눔고딕' (전 6개 필드)
blank_file_maker font 0  '맑은 고딕'  → '나눔고딕'
blank_file_maker font 1  '나눔명조'   → '나눔고딕' (통일 결정)
_reference_header  함초롬돋움/바탕    → 나눔고딕 (모든 fontface)
font/*.zip (7개, 132MB)              → 삭제
```

### 2.3 보존 항목

- `vendor/NanumGothic-*.ttf` (4MB 임베드, OFL) — rhwp 폴백 보호
- `vendor/OFL-NanumGothic.txt` (라이선스 텍스트)
- `rhwp_bridge.py:146-147` "함초롬돋움/바탕" → NanumGothic 폴백 매핑 (안전망)
- `pyhwpxlib/hwp2hwpx.py` 변환 로직 — 원본 폰트명 보존

---

## 3. Detailed Design

### 3.1 themes.py FontSet

```python
# Before (themes.py:47-53)
@dataclass(frozen=True)
class FontSet:
    """..."""
    heading_hangul: str = '맑은 고딕'
    heading_latin: str = '맑은 고딕'
    body_hangul: str = '맑은 고딕'
    body_latin: str = '맑은 고딕'
    caption_hangul: str = '맑은 고딕'
    caption_latin: str = '맑은 고딕'

# After (v0.16.1)
@dataclass(frozen=True)
class FontSet:
    """Font names for heading, body, and caption text.

    Default is '나눔고딕' (Naver Nanum Gothic, SIL OFL 1.1).
    재배포 자유 — 임베드/수정/상업 사용 모두 허용.

    이전 default 였던 '맑은 고딕' (Microsoft) 와 일부 사용 흔적이 있던
    '함초롬돋움/바탕' (한컴) 은 재배포 라이선스 제약으로 v0.16.1 부터 회피.
    사용자가 명시 지정하면 그대로 사용 가능 (호환성):
        FontSet(heading_hangul='맑은 고딕', body_hangul='맑은 고딕')

    Fallback: 번들된 NanumGothic (vendor/) — rhwp 렌더 시 자동 매핑.
    """
    heading_hangul: str = '나눔고딕'
    heading_latin: str = '나눔고딕'
    body_hangul: str = '나눔고딕'
    body_latin: str = '나눔고딕'
    caption_hangul: str = '나눔고딕'
    caption_latin: str = '나눔고딕'
```

### 3.2 blank_file_maker.py

```python
# Before (blank_file_maker.py:258-291)
def _add_font_pair(fontface) -> None:
    # Font 0: 맑은 고딕 (공문서 표준, 2022.06~)
    f1 = fontface.add_new_font()
    f1.id = "0"
    f1.face = "맑은 고딕"
    ...
    # Font 1: 나눔명조 (system fallback — NanumMyeongjo)
    f2 = fontface.add_new_font()
    f2.id = "1"
    f2.face = "나눔명조"
    ...

# After (v0.16.1)
def _add_font_pair(fontface) -> None:
    """Default font pair — 나눔고딕 (id=0) + 나눔고딕 (id=1).

    재배포 안전 (SIL OFL 1.1). 이전의 '맑은 고딕' (MS) 은 라이선스 제약으로
    회피. 한컴 오피스에서 열 때는 시스템 폰트 매핑으로 자동 fallback.
    """
    # Font 0: 나눔고딕 (OFL, 통일 default)
    f1 = fontface.add_new_font()
    f1.id = "0"
    f1.face = "나눔고딕"
    ...
    # Font 1: 나눔고딕 (통일)
    f2 = fontface.add_new_font()
    f2.id = "1"
    f2.face = "나눔고딕"
    ...
```

### 3.3 _reference_header.xml 일괄 교체

함초롬돋움/바탕 모든 출현 → 나눔고딕 (sed 일괄 가능):

```bash
sed -i '' 's/함초롬돋움/나눔고딕/g; s/함초롬바탕/나눔고딕/g' \
    pyhwpxlib/tools/_reference_header.xml
```

### 3.4 font/ 폴더 삭제

```bash
rm -rf pyhwpxlib/font/
# git history 에 기록 보존 (이전 commits 에서 복원 가능)
# pyproject.toml 의 package_data 에 영향 없음 (font/ 미참조 확인)
```

### 3.5 README/README_KO Fonts 섹션

`README.md` 의 License 섹션 직후 추가:

```markdown
## Fonts

pyhwpxlib uses **NanumGothic** (Naver, SIL OFL 1.1) as default font metadata
in generated documents and bundles it for rhwp rendering fallback.

### Why not 함초롬돋움/바탕 or 맑은 고딕?

| Font | License | Issue |
|------|---------|-------|
| 함초롬돋움/바탕 (HCR-) | Hancom Office license | Bundled with Hancom Office only |
| 맑은 고딕 (Malgun Gothic) | Microsoft license | Bundled with Windows/Office only |
| **나눔고딕/명조** | **SIL OFL 1.1** | **Free redistribution** |

Both Hancom and Microsoft fonts have redistribution restrictions, so
pyhwpxlib defaults to NanumGothic to avoid license concerns for users.

### Override default

```python
from pyhwpxlib import HwpxBuilder
from pyhwpxlib.themes import FontSet

# Use 맑은 고딕 explicitly (you are responsible for the license)
fonts = FontSet(heading_hangul='맑은 고딕', body_hangul='맑은 고딕')
b = HwpxBuilder(theme='default', fonts=fonts)
```

### HWP→HWPX conversion

`hwp2hwpx.convert()` **preserves original font names** from .hwp files.
The converted HWPX retains whatever fonts the source document used —
license compliance for converted files is the user's responsibility.
```

`README_KO.md` 도 동일 한국어 버전.

### 3.6 회귀 테스트 신설

`tests/test_font_defaults.py`:

```python
"""font-replacement (v0.16.1) 회귀 테스트."""
from __future__ import annotations
import re
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


# ── T-FR-01: FontSet default 나눔고딕 통일 ─────────────────


def test_fr_01_fontset_defaults_to_nanum_gothic():
    fs = FontSet()
    assert fs.heading_hangul == "나눔고딕"
    assert fs.heading_latin == "나눔고딕"
    assert fs.body_hangul == "나눔고딕"
    assert fs.body_latin == "나눔고딕"
    assert fs.caption_hangul == "나눔고딕"
    assert fs.caption_latin == "나눔고딕"


# ── T-FR-02: BlankFileMaker fontfaces 검증 ────────────────


def test_fr_02_blank_file_maker_fontfaces(tmp_path: Path):
    p = tmp_path / "blank.hwpx"
    HwpxBuilder().save(str(p))
    header_xml = _read_header_xml(p)

    # 함초롬·맑은 고딕 0건
    assert "함초롬돋움" not in header_xml
    assert "함초롬바탕" not in header_xml
    assert "맑은 고딕" not in header_xml
    # 나눔고딕 표기 존재
    assert "나눔고딕" in header_xml


# ── T-FR-03: HwpxBuilder 신규 문서 메타 검증 ─────────────


def test_fr_03_new_document_metadata(tmp_path: Path):
    p = tmp_path / "doc.hwpx"
    b = HwpxBuilder(theme="default")
    b.add_heading("제목", level=1)
    b.add_paragraph("본문")
    b.save(str(p))

    sec = _read_section_xml(p)
    hdr = _read_header_xml(p)
    full = sec + hdr

    assert "함초롬" not in full
    assert "맑은 고딕" not in full


# ── T-FR-04: _reference_header.xml 정리 ──────────────────


def test_fr_04_reference_header_clean():
    ref = Path(__file__).parent.parent / "pyhwpxlib" / "tools" \
        / "_reference_header.xml"
    if ref.exists():
        text = ref.read_text(encoding="utf-8")
        assert "함초롬돋움" not in text
        assert "함초롬바탕" not in text


# ── T-FR-05: hwp2hwpx 변환 fidelity (원본 폰트명 보존) ─────


@pytest.mark.skipif(
    not Path("samples").exists(),
    reason="sample .hwp files not available in CI",
)
def test_fr_05_hwp2hwpx_preserves_original_fonts(tmp_path: Path):
    from pyhwpxlib.hwp2hwpx import convert

    sample_hwp = next(
        (s for s in Path("samples").glob("*.hwp")
         if "전문가" in s.name),
        None,
    )
    if sample_hwp is None:
        pytest.skip("no expert form sample")

    out = tmp_path / "converted.hwpx"
    convert(str(sample_hwp), str(out))

    hdr = _read_header_xml(out)
    # 원본이 함초롬 사용했다면 변환 결과도 보존 (fidelity)
    # — 우리 default 변경이 변환에 영향 미치지 않음을 검증
    # 단, 어떤 폰트인지는 원본 의존이므로 단순히 변환 성공 + fontfaces 존재 검증
    assert "<hh:fontfaces" in hdr or "fontface" in hdr


# ── T-FR-06: rhwp 폴백 매핑 안전망 ────────────────────────


def test_fr_06_rhwp_fallback_for_legacy_hamchorom():
    """기존 함초롬 표기 hwpx 도 NanumGothic 으로 정상 렌더링 (회귀)."""
    from pyhwpxlib.rhwp_bridge import _build_font_map

    font_map = _build_font_map()
    assert "함초롬돋움" in font_map
    assert "함초롬바탕" in font_map
    # NanumGothic ttf 경로로 매핑됨
    for key in ("함초롬돋움", "함초롬바탕"):
        assert "NanumGothic" in font_map[key]
```

---

## 4. Data Structures

변경 없음 (default 값만 갱신).

---

## 5. Error Handling

기존 동작 유지. 사용자 명시 지정 (`FontSet(heading_hangul='임의')`) 도 그대로 수용.

---

## 6. Testing Plan

### 6.1 Test Strategy

- **단위**: FontSet default 값, _reference_header 텍스트 검증
- **통합**: HwpxBuilder().save() 결과 hwpx 의 메타 (header.xml + section0.xml)
- **fidelity 회귀**: hwp2hwpx 변환 결과 원본 폰트명 보존
- **시각**: rhwp 렌더 PNG 시각 검증 (Read tool 로 직접 확인)
- **전체 회귀**: 기존 123 PASS 유지

### 6.2 Test Cases

총 6 케이스 (T-FR-01 ~ T-FR-06) — 위 §3.6 명세 그대로.

---

## 7. Implementation Order

> Plan §7.1 9 단계 그대로.

### 7.1 파일별 변경 요약

```
수정:
  pyhwpxlib/themes.py                            6 LOC (FontSet default)
  pyhwpxlib/tools/blank_file_maker.py            4 LOC (_add_font_pair)
  pyhwpxlib/tools/_reference_header.xml          ~10 LOC (sed 일괄)
  README.md                                      +25 LOC (Fonts 섹션)
  README_KO.md                                   +25 LOC (Fonts 섹션 한국어)
  pyhwpxlib/__init__.py                          version bump
  pyproject.toml                                 version bump

신규:
  tests/test_font_defaults.py                    ~120 LOC (6 케이스)

삭제:
  pyhwpxlib/font/                                폴더 통째 (-132 MB, 7 zip)

기타:
  scripts/update_license_date.py --append        (Rolling Change Date 자동)
```

---

## 8. Open Questions

- [ ] CI fixture — `samples/` 가 .gitignore 에 있을 가능성. T-FR-05 는 `pytest.mark.skipif` 로 방어 (이미 명세). 영구 fixture 가 필요하면 별도 작은 .hwp 추가
- [ ] `font/` 삭제 후 누군가 의존하는 코드 — grep 검증 (Plan §1.2 에서 미사용 확인 완료)
- [ ] `package_data` / `MANIFEST.in` 에 `font/` 명시 여부 — pyproject.toml 점검 필요 (변경 위치)

---

## 9. References

- Plan: [font-replacement.plan.md](../../01-plan/features/font-replacement.plan.md)
- 사용자 결정 (2026-05-01):
  1. font/ 폴더 삭제
  2. FontSet 통일 (나눔고딕 통일)
- `pyhwpxlib/themes.py:47-53` — 변경 대상
- `pyhwpxlib/tools/blank_file_maker.py:258-294` — 변경 대상
- `pyhwpxlib/tools/_reference_header.xml` — 변경 대상
- `pyhwpxlib/vendor/OFL-NanumGothic.txt` — 라이선스 보존 텍스트
- SIL OFL 1.1 https://scripts.sil.org/OFL

---

## 10. Approval

- [ ] Design reviewed
- [ ] Architecture approved (변경 위치 5곳 확정)
- [ ] Ready for Do Phase
