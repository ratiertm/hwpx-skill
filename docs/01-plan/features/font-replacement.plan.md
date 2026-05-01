---
template: plan
version: 1.2
description: 함초롬/맑은 고딕 라이선스 이슈 회피 — 나눔 시리즈 + KoPub 으로 default 교체
---

# font-replacement Planning Document

> **Summary**: pyhwpxlib 의 default 폰트 메타 표기를 **OFL 라이선스 폰트 (나눔고딕/나눔명조)** 로 통일한다. 함초롬돋움/바탕 (한컴 라이선스), 맑은 고딕 (MS 라이선스) 모두 재배포 위험 있는 폰트. 코드 default 는 이미 일부 안전하지만 `_reference_header.xml` 등 일부 위치에 함초롬 잔존 + 맑은 고딕도 MS 라이선스라 동반 교체 필요.
>
> **Project**: pyhwpxlib
> **Version**: 0.16.0 → 0.16.1 (patch — additive 안전 교체)
> **Date**: 2026-05-01
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

PyPI 에 배포된 라이브러리가 사용자에게 **재배포 라이선스 위반 가능성** 을 전이하지 않도록 default 폰트를 안전한 OFL 폰트로 통일.

### 1.2 Background

**라이선스 분석**:

| 폰트 | 라이선스 | 재배포 | pyhwpxlib 사용처 |
|------|---------|-------|------------------|
| 함초롬돋움/바탕 (HCR-) | 한컴 오피스 라이선스 | ❌ 불가 | `_reference_header.xml`, rhwp 매핑 |
| 맑은 고딕 (Malgun Gothic) | Microsoft 라이선스 | ❌ 불가 | `themes.py` default, `blank_file_maker.py:262` |
| **나눔고딕/명조** | **OFL 1.1** | ✅ **가능** | `vendor/` (4MB 임베드), 일부 default |
| KoPub Batang/Dotum | KoPub 무료 (상업 OK) | ✅ 가능 | `font/` zip (미사용) |

**현재 코드 상태 (감사 완료)**:
- ✅ `vendor/NanumGothic-{Bold,Regular}.ttf` — 임베드, OFL 1.1 라이선스 명시
- ✅ `rhwp_bridge.py:146-147` — 함초롬 → NanumGothic 폴백 매핑 안전
- ⚠ `themes.py:49,51,53` — `FontSet` default 가 `'맑은 고딕'` (MS)
- ⚠ `blank_file_maker.py:262,278` — fontfaces font 0=맑은 고딕, 1=나눔명조
- ⚠ `_reference_header.xml` — 함초롬돋움/바탕 메타 (분석 reference 용)
- ⚠ `font/` 폴더 7 zip (132MB) — 미사용, 검토 필요

**위협 모델**:
- pyhwpxlib 사용자가 신규 hwpx 생성 → 메타에 "맑은 고딕" 표기됨
- 사용자가 그 hwpx 를 한컴 오피스 (Windows 외 환경) 또는 라이선스 없는 사용자에게 배포 → 폰트 메타 표기 자체가 라이선스 분쟁 소지
- 임베드 안 했어도 **상표/제품명 사용** 의미로 해석 가능 (보수적)
- 우리는 안전 폰트 (OFL) 만 default 표기하면 사용자에게 위험 전이 안 됨

### 1.3 Related

- 한국 공문서 표준 (행안부 「2025 행정업무운영 편람」) — 휴먼명조/휴먼바탕 권장이지만 일반 명조/고딕 모두 허용
- OFL 1.1 (SIL Open Font License) — 임베드/재배포/수정 모두 허용
- 기존 `vendor/OFL-NanumGothic.txt` — 라이선스 텍스트 이미 포함
- v0.13.0 에서 "한국 공문서 표준 적용 — 폰트/크기/여백/줄간격" 기존 작업

---

## 2. Goals

### 2.1 Primary Goals

1. **default 폰트 메타 표기 → OFL 폰트** — `themes.py` `FontSet` + `blank_file_maker.py` `_add_font_pair` + `_reference_header.xml`
2. **font/ 폴더 정리** — 미사용 zip 7개 (132MB) 삭제 또는 별도 명시
3. **README/LICENSE 폰트 출처 명시** — OFL 1.1 라이선스 + NOTICE 갱신
4. **사용자 변환물 (`hwp2hwpx`) 은 원본 폰트명 보존** — 사용자 책임 영역 명시

### 2.2 Non-Goals

- 한컴 오피스 사용자에게 함초롬 표기 강제 변경 요구 (불가)
- 폰트 ttf 임베드 확장 (현재 NanumGothic 만 임베드, 나머지는 시스템 폰트 의존 유지)
- 변환 (`hwp2hwpx.convert`) 시 폰트 자동 치환 (원본 fidelity 깨짐)
- rhwp_bridge 의 함초롬 → NanumGothic 폴백 제거 (안전망 유지)

### 2.3 Success Criteria

- [ ] `pyhwpxlib.themes.FontSet` default 가 `'나눔고딕'` / `'나눔명조'` 로 변경
- [ ] `BlankFileMaker.make()` 가 fontfaces 에 OFL 폰트 메타 출력
- [ ] `_reference_header.xml` 에 함초롬 표기 0건 (또는 별도 sample 폴더로 분리)
- [ ] `font/*.zip` 7개 — 삭제 또는 `font/README.md` 로 미사용 명시
- [ ] `README.md` / `README_KO.md` "Fonts" 섹션 추가 — OFL 출처 + 한컴/MS 폰트 회피 사유
- [ ] 신규 HwpxBuilder 문서 한컴 오피스에서 열 때 폰트 깨짐 (□) 없음 (시스템 폰트 매핑)
- [ ] 기존 123 회귀 테스트 PASS 유지
- [ ] 변환 (`hwp2hwpx`) 결과는 원본 폰트명 보존 (회귀 테스트 추가)

---

## 3. Requirements

### 3.1 Functional Requirements

#### FR-1: default 폰트 OFL 통일

**themes.py**:
```python
@dataclass(frozen=True)
class FontSet:
    heading_hangul: str = '나눔고딕'   # was '맑은 고딕'
    heading_latin: str = '나눔고딕'
    body_hangul: str = '나눔고딕'
    body_latin: str = '나눔고딕'
    caption_hangul: str = '나눔고딕'
    caption_latin: str = '나눔고딕'
```

**blank_file_maker.py `_add_font_pair`**:
```python
f1.face = "나눔고딕"      # was "맑은 고딕"
f2.face = "나눔명조"       # 유지
```

#### FR-2: `_reference_header.xml` 정리

옵션 A (권장): face="함초롬돋움/바탕" → "나눔고딕/나눔명조" 일괄 교체
옵션 B: 파일을 `tools/_legacy_reference_header.xml` 로 이름 변경 + `_reference_header.xml` 신규 생성 (OFL 폰트)

#### FR-3: font/ 폴더 정리

옵션 A (권장 — 가장 안전): `font/` 폴더 통째로 삭제. PyPI 재배포에서 132MB 절감. 향후 폰트 추가 시 별도 release.
옵션 B: `font/README.md` 추가 + 각 zip 라이선스 명시 + `.gitignore` 에 `font/*.zip` 추가 (저장소 보존, 패키지 제외)

#### FR-4: README/LICENSE 갱신

```markdown
## Fonts

pyhwpxlib bundles **NanumGothic** (SIL OFL 1.1) and uses
**나눔고딕/나눔명조** as default font metadata in generated documents.

**Why not 함초롬돋움/바탕 or 맑은 고딕?**
- 함초롬돋움/바탕 (HCR): 한컴 오피스 라이선스 (재배포 불가)
- 맑은 고딕 (Malgun Gothic): Microsoft 라이선스 (재배포 불가)
- NanumGothic/나눔명조: SIL OFL 1.1 (재배포 자유)

**HWP→HWPX 변환 시 원본 폰트명은 보존됩니다** (`hwp2hwpx.convert()`).
변환물의 폰트 라이선스는 사용자 책임입니다.
```

#### FR-5: 회귀 테스트 추가

- 신규 HwpxBuilder 문서 fontfaces 검증 — face 가 OFL 폰트인지
- `hwp2hwpx.convert()` 결과는 원본 폰트명 보존 검증 (변환 fidelity)

### 3.2 Non-Functional Requirements

- **Backward compat**: 기존 사용자가 명시적으로 `FontSet(heading_hangul='맑은 고딕', ...)` 지정 가능 (옵션 유지)
- **Visual fidelity**: 한컴 오피스에서 열 때 폰트 깨짐 (□) 없도록 fallback 매핑 강화
- **Package size**: `font/*.zip` 132MB 제거 → PyPI tarball 크기 축소

---

## 4. Constraints

### 4.1 Technical Constraints

- **rhwp_bridge.py:146-147 폴백 매핑 유지** — 기존 함초롬 표기 hwpx (사용자 변환물) 도 계속 NanumGothic 으로 렌더링
- **변환 (`hwp2hwpx`) fidelity 우선** — 원본 폰트명 보존 (사용자 책임 영역 명시)
- **시스템 폰트 의존 최소화** — vendor/NanumGothic 임베드는 유지 (rhwp 폴백)

### 4.2 Resource Constraints

- 1인 개발 — 1일 내 완료 가능
- 신규 의존성 0건

### 4.3 Other Constraints

- v0.16.1 patch 릴리스 (additive + 라이선스 안전)
- skill bundle (hwpx-skill-0.16.1.zip) 도 동시 갱신 (메타 일관성)

---

## 5. Risks

### 5.1 Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|:-----------:|:------:|------------|
| 한컴 오피스 (Windows) 에서 나눔고딕 미설치 시 폰트 깨짐 | M | M | 한컴이 자동으로 시스템 폰트 매핑 (한글 fontface lang="HANGUL" 설정) — 시각 차이 있어도 □ 안 나옴 |
| 행안부 편람 권장 폰트 (휴먼명조 등) 와 다름 | L | L | 편람도 일반 명조/고딕 허용. 사용자가 명시 변경 가능 |
| 기존 사용자 코드가 `'맑은 고딕'` 하드코딩 | L | L | FontSet 명시 지정 가능. 마이그레이션 가이드 README 에 |
| `font/*.zip` 삭제 후 누군가가 의존 | VL | L | 미사용 검증 완료. git history 에 보존 |
| 변환 (hwp2hwpx) 회귀 — 원본 폰트명 깨짐 | L | M | 신규 회귀 테스트로 보호 |
| MS 라이선스 해석 반론 ("폰트명만 표기는 OK") | L | L | 보수적 안전 우선. 사용자가 명시 지정으로 우회 가능 |

### 5.2 Assumptions

- "함초롬 라이선스 걸린다" 출처는 한컴 오피스 라이선스 약관 기반 (사용자 정보)
- OFL 1.1 은 임베드/재배포/수정 모두 허용 (SIL 공식)
- 한국 LLM/MCP 사용자는 NanumGothic 인지/허용 가능

---

## 6. Implementation Plan

### 6.1 Phases

| Phase | Description | Estimated Time |
|-------|-------------|----------------|
| P1 | `themes.py` FontSet default → 나눔고딕 | 10분 |
| P2 | `blank_file_maker.py` `_add_font_pair` 갱신 | 10분 |
| P3 | `_reference_header.xml` 함초롬 표기 교체 | 20분 |
| P4 | `font/` 폴더 처리 (삭제 or README) | 10분 |
| P5 | `README.md` / `README_KO.md` Fonts 섹션 추가 | 30분 |
| P6 | 회귀 테스트 추가 (FR-5) | 30분 |
| P7 | 전체 회귀 (123 → 125 PASS) + 시각 검증 (rhwp 렌더 PNG) | 30분 |
| P8 | v0.16.1 패치 릴리스 (skill bundle 동기화 포함) | 30분 |

### 6.2 Technologies/Tools

- 변경 위주 (신규 모듈 없음)
- 기존 회귀 테스트 + neue `tests/test_font_defaults.py` (FR-5)
- `update_license_date.py --append` 으로 v0.16.1 Rolling Change Date 갱신

### 6.3 Dependencies

- 외부 의존성 0건
- 내부: 기존 vendor/NanumGothic 유지

---

## 7. Implementation Order

### 7.1 Recommended Order

1. **Step 1**: `themes.py` `FontSet` default → 나눔고딕 (모든 hangul/latin 동일)
2. **Step 2**: `blank_file_maker.py` `_add_font_pair` font 0 face → 나눔고딕 (font 1 나눔명조 유지)
3. **Step 3**: `_reference_header.xml` 함초롬 → 나눔 (sed 일괄 교체)
4. **Step 4**: `font/` 결정 — 삭제 OR README 추가
5. **Step 5**: 신규 테스트 `tests/test_font_defaults.py`
   - test_default_fontfaces_use_ofl_fonts (HwpxBuilder().save() 결과 fontfaces 검증)
   - test_hwp2hwpx_preserves_original_font_names (변환 회귀)
6. **Step 6**: `README.md` / `README_KO.md` "Fonts" 섹션 + 라이선스 표
7. **Step 7**: `pyproject.toml` + `__init__.py` 0.16.0 → 0.16.1 + license date append
8. **Step 8**: 전체 회귀 (`pytest tests/`) + 신규 hwpx 시각 검증 (rhwp 렌더)
9. **Step 9**: skill bundle 0.16.1.zip 빌드 + git commit + tag + push + PyPI 배포

### 7.2 Critical Path

Step 1~3 (default 변경) → Step 5~6 (검증·문서) → Step 7~9 (릴리스)

폰트 교체 자체는 단순. 회귀 테스트 + 시각 검증이 핵심.

---

## 8. Testing Plan

### 8.1 Test Strategy

- **단위**: FontSet default 값, blank_file_maker 출력 fontfaces 검증
- **회귀**: 기존 123 PASS 유지
- **시각**: HwpxBuilder().save() 결과를 rhwp 로 렌더 → PNG 시각 검증 (폰트 깨짐 없음)
- **fidelity**: hwp2hwpx 변환물의 폰트명 보존 검증

### 8.2 Test Cases

| ID | 시나리오 | 기대 |
|----|---------|------|
| T-FR-01 | `FontSet()` default | heading/body/caption 모두 `'나눔고딕'` |
| T-FR-02 | `BlankFileMaker.make()` fontfaces | font 0 face=`'나눔고딕'`, font 1 face=`'나눔명조'`, 함초롬 0건 |
| T-FR-03 | `HwpxBuilder().save()` 메타 검증 | section0.xml + header.xml 에 함초롬·맑은 고딕 0건 |
| T-FR-04 | `_reference_header.xml` 텍스트 검증 | 함초롬 0건 |
| T-FR-05 | `hwp2hwpx.convert(sample.hwp)` 변환 결과 | 원본 폰트명 보존 (변환 fidelity) |
| T-FR-06 | rhwp 폴백 매핑 | "함초롬돋움" 표기 hwpx → NanumGothic 으로 정상 렌더 |

---

## 9. Open Questions

- [ ] `font/` 폴더 — 삭제 vs README 보존? **권장: 삭제** (132MB 절감, git 히스토리 보존). 사용자 의사 확인 필요
- [ ] FontSet default `'나눔고딕'` vs `'나눔명조'` (heading) — 어느 쪽이 한국 공문서/보고서에 더 적합? **권장: 나눔고딕 통일** (편람도 본문 고딕 권장)
- [ ] `맑은 고딕` 강제 사용 사용자 마이그레이션 — README 에 `FontSet(heading_hangul='맑은 고딕', ...)` 명시 옵션 안내

---

## 10. References

- 사용자 정보 (2026-05-01): "함초롬 라이선스 걸린다"
- `pyhwpxlib/themes.py:49-53` — 현재 FontSet default
- `pyhwpxlib/tools/blank_file_maker.py:258-294` — _add_font_pair
- `pyhwpxlib/tools/_reference_header.xml` — 함초롬 메타 잔존 위치
- `pyhwpxlib/vendor/OFL-NanumGothic.txt` — 라이선스 텍스트
- SIL OFL 1.1 — https://scripts.sil.org/OFL
- 행안부 「2025 행정업무운영 편람」 (samples/[25.12.17]...pdf) — 권장 폰트 참고

---

## 11. Approval

- [ ] Plan reviewed
- [ ] Stakeholders aligned (사용자 — 라이선스 우려 명시 2026-05-01)
- [ ] Ready for Design Phase
