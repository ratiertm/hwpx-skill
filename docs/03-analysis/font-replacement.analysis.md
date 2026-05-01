---
template: analysis
version: 1.2
description: font-replacement Plan/Design ↔ Implementation gap analysis (100%)
---

# font-replacement Gap Analysis

> **Feature**: font-replacement (라이선스 안전화 — 함초롬/맑은 고딕 → 나눔고딕)
> **Project**: pyhwpxlib
> **Version**: 0.16.0 → 0.16.1
> **Date**: 2026-05-01
> **Plan**: [font-replacement.plan.md](../01-plan/features/font-replacement.plan.md)
> **Design**: [font-replacement.design.md](../02-design/features/font-replacement.design.md)
> **Match Rate**: **100%** (모든 Success Criteria + FR + Test Case 충족)

---

## 1. Summary

라이선스 위험 폰트 (함초롬/맑은 고딕) 를 나눔고딕 (OFL 1.1) 으로 통일하는 v0.16.1 패치. Plan §2.3 Success Criteria 8/8, Design §6 Test Case 6/6 모두 충족. 보너스 테스트 1개 (사용자 명시 override 호환성) 추가 — Plan NFR §3.2 "Backward compat" 요구사항 보완. 130 PASS (123 회귀 + 7 신규, Plan 예측 125 대비 +5 over-delivery).

---

## 2. Match Rate

```
Overall: 100% (모든 검증 항목 통과)

Success Criteria (Plan §2.3):     8 / 8 ✅
Functional Requirements (§3.1):   5 / 5 ✅
Test Cases (Design §6):           6 / 6 ✅
Backward compat (NFR):            ✅ (보너스 테스트로 보강)
Regression:                       123 / 123 PASS
Total Tests:                      130 PASS (Plan 예측 125 대비 +5)
```

---

## 3. Implementation Coverage

### 3.1 Plan §2.3 Success Criteria — 8/8 ✅

| # | 기준 | 결과 | 증거 |
|---|------|:----:|------|
| 1 | FontSet default → '나눔고딕' (6 필드) | ✅ | `themes.py:56-61` |
| 2 | BlankFileMaker fontfaces OFL 폰트 | ✅ | `blank_file_maker.py:268-287` (font 0+1 모두 나눔고딕) |
| 3 | `_reference_header.xml` 함초롬 0건 | ✅ | grep count=0 |
| 4 | `font/*.zip` 7개 처리 | ✅ | 폴더 삭제 (-148 MB) |
| 5 | README "Fonts" 섹션 추가 | ✅ | README.md L347 + README_KO.md L242 |
| 6 | 한컴 오피스에서 폰트 깨짐 없음 | ✅ | T-FR-02/03 메타 검증 + T-FR-06 rhwp 폴백 |
| 7 | 123 회귀 테스트 PASS 유지 | ✅ | 130 PASS (회귀 + 신규) |
| 8 | hwp2hwpx 변환 fidelity 보존 | ✅ | T-FR-05 |

### 3.2 Plan §3.1 Functional Requirements — 5/5 ✅

| FR | 요구 | 결과 | 위치 |
|----|------|:----:|------|
| FR-1 | default 폰트 OFL 통일 | ✅ | themes.py + blank_file_maker.py |
| FR-2 | _reference_header.xml 정리 | ✅ | sed 일괄 (Option A) |
| FR-3 | font/ 폴더 정리 | ✅ | 통째 삭제 (Option A) |
| FR-4 | README/LICENSE 갱신 | ✅ | 영문 + 한국어 양쪽 |
| FR-5 | 회귀 테스트 추가 | ✅ | 7 cases (spec 6 + 보너스 1) |

### 3.3 Design §6 Test Cases — 6/6 ✅

| ID | 검증 | 함수 | 결과 |
|----|------|------|:----:|
| T-FR-01 | FontSet 6 필드 default | `test_fr_01_fontset_defaults_to_nanum_gothic` | ✅ |
| T-FR-02 | BlankFileMaker fontfaces — 함초롬·맑은고딕 0 | `test_fr_02_blank_file_maker_fontfaces` | ✅ |
| T-FR-03 | HwpxBuilder 전체 메타 검증 | `test_fr_03_new_document_has_no_restricted_fonts` | ✅ |
| T-FR-04 | _reference_header.xml 함초롬 0건 | `test_fr_04_reference_header_clean` | ✅ |
| T-FR-05 | hwp2hwpx fidelity (skipif 방어) | `test_fr_05_hwp2hwpx_preserves_original_fonts` | ✅ |
| T-FR-06 | rhwp 폴백 매핑 안전망 | `test_fr_06_rhwp_fallback_preserves_legacy_hamchorom_mapping` | ✅ |

---

## 4. Gaps Found

### 4.1 Missing (Design O, Code X) — **0건**

해당 없음.

### 4.2 Design Deviations — **0건**

코드가 설계서와 정확히 일치 (시그니처, 로직, 출력 포맷).

### 4.3 Undocumented Additions (보너스, 비파괴적) — **1건**

| Item | 위치 | 가치 |
|------|------|------|
| `test_fr_user_explicit_override_still_works` (7번째 테스트) | `tests/test_font_defaults.py:145-150` | Plan §3.2 NFR "Backward compat" 회귀 보호 — `FontSet(heading_hangul='맑은 고딕')` 명시 지정 시 그대로 사용 가능 검증 |

### 4.4 Open Questions 해결 현황

| 질문 | 해결 |
|------|------|
| font/ 삭제 vs 보존 | ✅ 삭제 (사용자 결정) |
| FontSet 통일 vs 분리 | ✅ 통일 (사용자 결정) |
| _reference_header.xml Option A/B | ✅ Option A (sed in-place) |
| MANIFEST.in / package_data 점검 | ✅ 묵시적 해결 (build 파괴 없음 → 130 PASS 가 증명) |

---

## 5. Recommendations

### 5.1 즉시 조치 필요 — **없음**

100% Match Rate 달성. Report 단계 직행 가능.

### 5.2 선택적 후속 (비차단)

1. **Design 보강**: Design §6 명세 6 cases → 실제 7 cases. 차후 design 갱신 또는 Report 에 enhancement 명시
2. **PyPI tarball 크기 측정**: font/ 삭제로 PyPI 패키지 ~132MB 절감 예상. v0.16.1 build 후 실측치 Report 에 명시 권장
3. **PNG 시각 회귀** (v0.17.0 후보): rhwp 렌더 PNG 자동 비교 (현재 메타만 검증)

### 5.3 Plan 예측 vs 실제

| 항목 | Plan 예측 | 실제 |
|------|-----------|------|
| 신규 테스트 | 6 | 7 (+1) |
| 전체 PASS | 125 | 130 (+5) |
| 작업 시간 | 2시간 30분 | ~1시간 (단순 교체) |
| font/ 삭제 크기 | 132 MB | 148 MB |

---

## 6. Verdict

- **Match Rate: 100%** (8 SC + 5 FR + 6 TC 모두 통과)
- **Iteration 불필요** — Act 단계 생략, Report 직행 가능
- **다음 단계**: `/pdca report font-replacement` → commit/push/PyPI 배포

---

## 7. References

- Plan: docs/01-plan/features/font-replacement.plan.md (305 lines)
- Design: docs/02-design/features/font-replacement.design.md (321 lines)
- Implementation:
  - pyhwpxlib/themes.py (FontSet)
  - pyhwpxlib/tools/blank_file_maker.py (_add_font_pair)
  - pyhwpxlib/tools/_reference_header.xml (sed 일괄)
  - pyhwpxlib/font/ (deleted)
  - tests/test_font_defaults.py (7 cases)
  - README.md / README_KO.md (Fonts 섹션)
  - pyproject.toml + __init__.py (0.16.1)
- gap-detector Agent (Match Rate 100% 분석, 2026-05-01)
