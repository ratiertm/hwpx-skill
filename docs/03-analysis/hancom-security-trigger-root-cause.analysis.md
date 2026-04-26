# Hancom Security Trigger — Root Cause Analysis

**Date**: 2026-04-27  
**Status**: Confirmed

## 결론 (한 줄)

한컴이 외부 수정 hwpx 를 보안경고로 막는 시그니처는 **`<hp:lineseg textpos="N"/>` 에서 `N > UTF-16(paragraph 안 hp:t 텍스트 합)`** 단 한 가지.

## 검증 매트릭스 (지청운 sample, 인덱스 6 paragraph)

| 변형 | 텍스트 | textpos | 한컴 |
|------|--------|---------|------|
| 원본 | `(별도 기재)` 7자 | 61 | ❌ |
| I1 (49자) | 49자 | 61 | ❌ (49 < 61) |
| **I1 (80자)** | 80자 | 61 | ✅ (80 > 61) |
| **I2 (textpos 5)** | 7자 | 5 | ✅ (5 < 7) |
| **J (정밀 fix)** | 7자 | (61 lineseg 제거) | ✅ |

## 폐기된 가설들

| # | 가설 | 반증 실험 |
|---|------|----------|
| 1 | zip timestamp (1980 vs 실제) | B1 |
| 2 | zip compression (PrvImage STORED vs DEFLATED) | B2 |
| 3 | zip entry 순서 | B 시리즈 전체 |
| 4 | content.hpf의 `Z` 접미사 / `lastsaveby="USER"` | 정상/오류 둘 다 동일 |
| 5 | 텍스트 길이 자체 | A1 (이준구+90자 정상), A3 (이준구+130자 정상) |
| 6 | R3 위반 (lineseg=1+text>40+no\\n) | 검수확인서_채움 (R3=3) 정상 |
| 7 | 특정 셀 위치 (row=7) | C2 (지청운 row=7 R3 해제) 오류 |
| 8 | 외부 LLM 가설 1 — "이름 길이로 lineseg 초과" | 이름 셀은 R3 아님 |
| 9 | 외부 LLM 가설 2 — "본명: 키워드 개인정보 스캐너" | 비현실적 |

## 결정적 진전

**Phase 1**: 정상(이준구) vs 오류(지청운) — section0.xml 60 bytes 차이만, lineseg/paragraph/run XML 완전 동일, 차이는 텍스트 16개.

**A~B**: 텍스트 길이/zip 메타 무관 입증.

**C**: 셀 위치(row) 무관 입증.

**D**: 트리거 위치 = section0.xml 안 (확정).

**E~H**: Binary search (16 → 8 → 4 → 2 → 1) 으로 인덱스 6 (주소 셀) 까지 좁힘.

**I~J**: textpos overflow 가설 → 정밀 fix 검증 → 한컴 통과.

## 정밀 fix vs 강한 망치 (strip)

| 측면 | precise (default v0.13.2+) | remove (옛 default v0.13.0/0.13.1) |
|------|---------------------------|------------------------------------|
| 처리 | overflow lineseg 만 제거 | linesegarray 전체 제거 |
| 한컴 | ✅ 회피 | ✅ 회피 |
| rhwp | ✅ 정확 (lineseg 보존) | reflow 필요 (lineseg 없음) |
| 외부 렌더러 캐시 | ✅ 유지 | ❌ 무효화 |
| 안전 마진 | 정확한 트리거 1종 처리 | 모든 lineseg 시그니처 회피 (망치) |

`precise` 가 새 default. 미래 한컴 버전이 다른 lineseg 시그니처를 추가하면
`remove` fallback 옵트인.

## 영향

- pyhwpxlib 0.13.2: `fix_textpos_overflow`, `count_textpos_overflow` 추가
- `package_ops.write_zip_archive(strip_linesegs="precise"|"remove"|False)` 모드 옵션
- CLI: `pyhwpxlib reflow-linesegs --mode precise` (default)
- Lint: `TEXTPOS_OVERFLOW` (error) — 정확한 트리거. `RHWP_R3_RENDER_RISK` (warning) — 별개.

## 참고

- Plan: `docs/01-plan/features/hancom-security-trigger-root-cause.plan.md`
- 회귀 테스트: `tests/test_lineseg_reflow.py` (31 cases PASS)
- 메모리: `~/.claude/projects/.../memory/feedback_hancom_security_trigger.md`
