---
template: report
version: 1.1
description: PDCA completion report for font-replacement (v0.16.1)
---

# font-replacement Completion Report

> **Status**: Complete (Match Rate 100%, no iteration needed)
>
> **Project**: pyhwpxlib
> **Version**: 0.16.0 → 0.16.1 (patch — 라이선스 안전화)
> **Author**: Mindbuild + Claude
> **Completion Date**: 2026-05-01
> **PDCA Cycle**: font-replacement (Plan → Design → Do → Check → Report, Act 생략)

---

## 1. Executive Summary

PyPI 배포된 pyhwpxlib 사용자에게 **재배포 라이선스 위반 위험을 전이하지 않도록** default 폰트 메타 표기를 OFL 1.1 폰트 (나눔고딕) 로 통일. 함초롬돋움/바탕 (한컴 라이선스) 과 맑은 고딕 (Microsoft 라이선스) 두 라이선스 위험 폰트를 동시 제거. 미사용 `font/` 폴더 148MB 삭제로 PyPI 패키지 크기도 대폭 절감. PDCA 4단계 (Plan → Design → Do → Check) 1회 완료, Match Rate 100% 즉시 도달로 Act 단계 생략. 회귀 테스트 130 PASS (123 회귀 + 7 신규, Plan 예측 +5 over-delivery).

---

## 2. Related Documents

| Phase | Document | Status |
|-------|----------|--------|
| Plan | [font-replacement.plan.md](../../01-plan/features/font-replacement.plan.md) | ✅ Finalized |
| Design | [font-replacement.design.md](../../02-design/features/font-replacement.design.md) | ✅ Finalized |
| Check | [font-replacement.analysis.md](../../03-analysis/font-replacement.analysis.md) | ✅ 100% |
| Act | (생략 — 100% 도달) | — |
| Report | Current document | ✅ This report |

---

## 3. Completion Status

### 3.1 Functional Requirements — 5/5 ✅

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR-1 | default 폰트 OFL 통일 | ✅ | themes.py FontSet (6 필드) + blank_file_maker (font 0+1) |
| FR-2 | _reference_header.xml 정리 | ✅ | sed 일괄, 함초롬 0건 |
| FR-3 | font/ 폴더 정리 | ✅ | 통째 삭제 (-148 MB) |
| FR-4 | README/LICENSE 갱신 | ✅ | 영문 + 한국어 양쪽 Fonts 섹션 |
| FR-5 | 회귀 테스트 | ✅ | 7 cases (T-FR-01~06 + 보너스) |

### 3.2 Plan Success Criteria — 8/8 (100%)

모든 기준 통과 (자세한 내용은 analysis.md §3.1).

### 3.3 Test Coverage

```
신규 테스트:
  tests/test_font_defaults.py    7 cases  (T-FR-01~06 + backward compat)

회귀 (기존 v0.16.0):
  test_diagnose, test_gongmun_autofit, test_json_schema_expansion,
  test_lineseg_reflow, test_page_guard, test_blueprint,
  test_rhwp_bridge_extensions, test_rhwp_strict_mode, test_templates
─────────────────────────────────────────────────────────────────────
                                123 cases (전부 PASS 유지)

총합: 130 PASS (4.21s)
```

---

## 4. Implementation Highlights

### 4.1 변경 위치 5곳

| 파일 | 변경 |
|------|------|
| `pyhwpxlib/themes.py` | FontSet 6 필드 → '나눔고딕' 통일 |
| `pyhwpxlib/tools/blank_file_maker.py` | _add_font_pair font 0/1 모두 '나눔고딕' |
| `pyhwpxlib/tools/_reference_header.xml` | sed 함초롬→나눔고딕 일괄 |
| `pyhwpxlib/font/` | **삭제** (-148 MB, 7 zip) |
| `README.md` / `README_KO.md` | "Fonts" 섹션 신설 (영문+한국어) |

### 4.2 보존 항목 (회귀 안전망)

- `vendor/NanumGothic-{Bold,Regular}.ttf` (4MB OFL 임베드) — rhwp 폴백
- `vendor/OFL-NanumGothic.txt` (라이선스 텍스트)
- `rhwp_bridge.py:146-147` 함초롬 → NanumGothic 폴백 매핑 — 기존 hwpx 호환
- `pyhwpxlib/hwp2hwpx.py` 변환 로직 — 원본 폰트명 보존 (fidelity)
- 사용자 명시 override (`FontSet(heading_hangul='맑은 고딕')`) — 호환성 유지

### 4.3 핵심 알고리즘

폰트 메타 표기 단순 교체. 알고리즘 변경 없음. 핵심은:
1. **default 통일**: 한컴/MS 폰트 메타 0건 보장
2. **fidelity 보존**: hwp2hwpx 변환 시 원본 폰트명 유지 (사용자 책임)
3. **폴백 안전망**: 기존 hwpx (함초롬 표기) 도 NanumGothic 으로 정상 렌더

---

## 5. Lessons Learned

### 5.1 잘된 점

- **사용자 결정 사전 확보**: Plan §9 Open Question 2개 (font/ 삭제 vs 보존, FontSet 통일 vs 분리) 를 Design 진입 전 사용자에게 확인 → 의사결정 지연 없이 직진
- **회귀 안전망 명시**: rhwp 폴백 + hwp2hwpx fidelity 를 처음부터 보존 항목으로 명시 → backward-compat 유지
- **단일 PDCA 사이클로 closure**: 단순 교체 작업의 적정 scope. 100% 즉시 도달로 Act 생략
- **Plan 예측 over-delivery**: 7 tests / 130 PASS / 148MB 삭제 (예측 6 / 125 / 132MB)

### 5.2 개선 필요

- **Design §6 명세 미스매치**: 6 cases 명시 vs 실제 7 (보너스 1) — 차후 design phase 에서 backward-compat 테스트도 spec 에 포함
- **시각 회귀 부재**: 메타 검증만, 실제 한컴 오피스/Whale 시각 차이는 수동 검증 필요. v0.17.0 후보로 PNG diff 자동화 검토

### 5.3 재사용 가능 패턴

- **라이선스 패치 패턴**: 라이브러리에 잠재적 라이선스 위험 식별 → 안전 대체재 OFL 폰트 default 변경 + override 호환성 + fidelity 보존 → 패치 릴리스. 이 3박자 (default/override/fidelity) 가 라이선스 안전화 표준 절차로 자리잡음

---

## 6. Architectural Impact

### 6.1 Public API 무변경

기존 import / 호출 시그니처 모두 그대로:
```python
from pyhwpxlib import HwpxBuilder
from pyhwpxlib.themes import FontSet

# Default — 이제 나눔고딕
b = HwpxBuilder()  # 동작 동일

# 명시 override — 이전과 동일
fs = FontSet(heading_hangul='맑은 고딕')
```

### 6.2 메타 출력 변경 (사용자 가시 변화)

- 신규 HwpxBuilder 문서 → fontfaces 메타 `face="나눔고딕"` (이전 "맑은 고딕")
- 한컴 오피스에서 열 때 시스템 폰트 매핑 (한글 fontface lang="HANGUL") 자동 작동

### 6.3 Backward Compat

- 기존 v0.16.0 사용자 코드 — 100% 호환
- v0.14.0 / v0.15.0 / v0.16.0 입력 모두 그대로 동작
- `FontSet(heading_hangul='맑은 고딕', ...)` 명시 지정도 그대로 작동

---

## 7. Sustainability — Future Work

### 7.1 v0.17.0 후보

- PNG 시각 회귀 (rhwp 렌더 자동 diff)
- `pyhwpxlib lint --fonts` — 사용자 hwpx 의 폰트 메타 분석 (한컴/MS 폰트 사용 여부 보고)
- 추가 OFL 폰트 옵션 (KoPub Batang/Dotum 임베드 옵션, --extra-fonts 플래그)

### 7.2 v0.18.0+ 후보

- 사용자 폰트 임베드 워크플로 (`pyhwpxlib font register --ttf path/to/font.ttf`)
- 한국 정부 표준 폰트 패키지 (행안부 편람 권장 폰트 사전 매핑)

---

## 8. Acknowledgments

- **사용자 (Mindbuild)** — 라이선스 우려 명시 (2026-05-01) + Open Question 2개 사전 결정
- **Naver NanumGothic** — SIL OFL 1.1 폰트, 한국 OSS 폰트의 대표
- **gap-detector Agent** — Match Rate 100% 자동 분석

---

## 9. Release Checklist

- [x] PDCA 4단계 (Plan/Design/Do/Check) 완료
- [x] 130 PASS (123 회귀 + 7 신규)
- [x] pyproject.toml + __init__.py 0.16.1 동기화
- [x] LICENSE.md / README.md / README_KO.md Rolling Change Date 갱신 (2030-05-01)
- [x] README/README_KO Fonts 섹션 추가
- [ ] git commit + tag v0.16.1
- [ ] git push origin main + tag
- [ ] PyPI build + upload
- [ ] work-log 기록
- [ ] (선택) skill bundle 0.16.1.zip

---

## 10. Final Verdict

**Status: ✅ COMPLETE — Match Rate 100%, Single PDCA Cycle**

`font-replacement` v0.16.1 패치는 라이선스 안전화 단일 목표를 100% 달성. Plan/Design 명세 그대로 구현 + backward-compat 보너스 테스트 추가. 다음: 배포 시퀀스.
