---
template: analysis
version: 1.2
description: Plan/Design ↔ Implementation gap analysis (initial Check, pre-Act)
---

# reference-fidelity-toolkit Gap Analysis

> **Feature**: reference-fidelity-toolkit (A. page-guard CLI + B. Critical Rules 의도 룰 4개 + C. analyze --blueprint)
> **Project**: pyhwpxlib
> **Version**: 0.15.0 → 0.16.0
> **Date**: 2026-05-01
> **Plan**: [reference-fidelity-toolkit.plan.md](../01-plan/features/reference-fidelity-toolkit.plan.md)
> **Design**: [reference-fidelity-toolkit.design.md](../02-design/features/reference-fidelity-toolkit.design.md)
> **Match Rate**: **100%** (34 / 34 verifiable items) — Act-1 후 갱신
> **Iteration**: Act-1 완료 (HWPX_RULEBOOK.md sync)

---

## 1. Summary

세 deliverable (A. `page-guard` 강제 게이트, B. 의도 룰 4개, C. `analyze --blueprint` 청사진) 이 Plan/Design 명세대로 거의 완전히 구현됨. 모듈 시그니처(7개 dataclass), CLI 진입점 2개, 테스트 케이스 8개 모두 존재 + 122 PASS. 단 한 가지 결손: **`references/HWPX_RULEBOOK.md` 동기화 누락** (Plan §2.3 #6, Design §3.4 명시 요구). SKILL.md Critical Rules #10–#13, Quick Reference, Workflow [3] Step F, Versions 모두 갱신됨. 보너스 테스트 7건은 비파괴적 보강.

---

## 2. Match Rate

```
Overall: 97% (33 / 34 items)

By category:
  FR-1 page-guard          : 100% (10 / 10)
  FR-2 의도 룰 (docs sync) :  87% ( 7 /  8) — RULEBOOK 1건 누락
  FR-3 analyze --blueprint :  100% (11 / 11)
  Test Coverage (Design §6):  100% ( 8 /  8)
  Plan Success Criteria    :   86% ( 6 /  7)
```

---

## 3. Implementation Coverage

### 3.1 FR-1: page-guard CLI — 10/10 ✅

- `pyhwpxlib/page_guard.py` 243 LOC (Design ~150 LOC 명세 대비 풍부 보강)
- `PageCountResult` / `GuardResult` dataclass + `to_dict()` 정확 일치
- `count_pages` (rhwp/static/auto), `compare`, `_format_text`, `main` 4 함수 구현
- rhwp 1차 + static 폴백 mode=auto 정상
- CLI args (`--reference --output --threshold --mode --json`) 5종 등록
- exit 0/1/2 정확 매핑
- `cli.py:_cmd_page_guard` + dispatch 추가

### 3.2 FR-2: Critical Rules 의도 룰 — 7/8 ⚠

| 위치 | 상태 |
|------|------|
| SKILL.md Critical Rules #10–#13 (4 rows) | ✅ |
| SKILL.md Workflow [3] Step F (page-guard step) | ✅ |
| SKILL.md Quick Reference 2 행 추가 | ✅ |
| SKILL.md Versions 0.16.0 항목 | ✅ |
| **`references/HWPX_RULEBOOK.md` 동기화** | ❌ **누락** |

### 3.3 FR-3: analyze --blueprint — 11/11 ✅

- `pyhwpxlib/blueprint.py` 469 LOC
- 4개 dataclass (`PageInfo`, `StyleInventory`, `TableInfo`, `Blueprint`) 모두 일치
- `analyze_blueprint(path, depth=2)` depth 1/2/3 분기 정상
- OWPML 파싱 (header itemCnt + section charPr/paraPr/tbl/pic) 명세 정확 구현
- `format_text` Page/Styles/Tables/Body 4섹션 출력
- CLI args 4종 등록 + `cli.py:_cmd_analyze` + dispatch
- 보너스: `Blueprint.char_histogram` / `para_histogram` 필드 (depth=3 전용, Design §3.3 의도 부합)

---

## 4. Test Coverage

### 4.1 Design §6 명시 8개 — 100%

| ID | 위치 | Status |
|----|------|--------|
| T-PG-01 ~ T-PG-05 | `tests/test_page_guard.py` | ✅ 5/5 |
| T-BP-01 ~ T-BP-03 | `tests/test_blueprint.py` | ✅ 3/3 |

### 4.2 보너스 테스트 7건 (비파괴적 보강)

- `test_pg_missing_file_returns_exit_2` — exit 2 분기 검증
- `test_pg_cli_integration_pass` — subprocess 통합
- `test_bp_depth_1_minimal` / `test_bp_depth_3_histogram` — depth 분기
- `test_bp_invalid_depth_raises` / `test_bp_missing_file_raises` / `test_bp_cli_integration`

**전체 122 PASS** (15 신규 + 107 회귀).

---

## 5. Gaps Found

### 5.1 🔴 Critical (1건)

| Gap | Location | Impact | Fix |
|-----|----------|--------|-----|
| HWPX_RULEBOOK.md 의도 룰 미동기화 | `skill/references/HWPX_RULEBOOK.md` | RULEBOOK 은 SKILL.md 가 명시 참조하는 상세 문서. 사용자가 RULEBOOK 으로 갔을 때 #10–#13 상세 설명 부재. Design §3.4 + Plan §2.3 #6 요구 | 30분. "## 레퍼런스 충실도 룰" 섹션 추가 |

### 5.2 🔵 Informational (비파괴적 보강)

- `Blueprint.char_histogram` / `para_histogram` — Design §2.2 dataclass 정의 누락이지만 §3.3 의도 정확히 구현 (설계서 보강 필요)
- `_format_text` stdout/stderr 분기 — CI 통합 best practice
- 보너스 테스트 7건 — 회귀 안정성 향상

---

## 6. Plan Success Criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | page-guard exit 0/1 동작 | ✅ |
| 2 | --threshold 0/1 옵션 | ✅ |
| 3 | analyze --blueprint 인간 가독 출력 | ✅ |
| 4 | --json 출력 모드 | ✅ |
| 5 | SKILL.md Critical Rules 4개 추가 | ✅ |
| 6 | RULEBOOK 동기화 | ❌ |
| 7 | 신규 테스트 ≥ 8 PASS | ✅ |

**6/7 = 86%**

---

## 7. Recommendations

### 7.1 Act-1 (권장)

**HWPX_RULEBOOK.md 에 의도 룰 4개 상세 섹션 추가** — 30분 작업으로 Match Rate 97% → 100%.

```
## N. 레퍼런스 충실도 룰 (Critical Rules #10–#13)

### #10 치환 우선 편집
배경: ...
정상 패턴: ...
안티패턴: ...

### #11 구조 변경 제한
...

### #12 페이지 동일 필수
...

### #13 page-guard 통과 필수
...
```

### 7.2 설계서 업데이트 (선택, 차후)

- Design §2.2 `Blueprint` 에 `char_histogram` / `para_histogram` 필드 추가 (시그니처 정합성)
- Design §6 Test Plan 에 보너스 테스트 7건 항목 추가

---

## 8. Verdict

- **Initial Check: 97%** → **Act-1 완료 후: 100%**
- Act-1 작업 (2026-05-01): `skill/references/HWPX_RULEBOOK.md` 에 "## 38. 레퍼런스 충실도 룰" 섹션 신설 (#10~#13 각 룰의 배경/정상 패턴/안티패턴/예외 + 워크플로별 적용 매핑 표). 110 라인 추가.
- Plan §2.3 Success Criteria 7/7 (100%) 달성.
- 회귀 테스트 122 PASS 유지 (영향 없음).
- 다음 단계: `/pdca report reference-fidelity-toolkit` — 완료 보고서 + v0.16.0 릴리스 준비

## 9. Act-1 변경 내역

| 파일 | 변경 |
|------|------|
| `skill/references/HWPX_RULEBOOK.md` | +110 라인 — Section 38 신설 |
| `~/.claude/skills/hwpx/references/HWPX_RULEBOOK.md` | 동기화 |
| 코드 / 테스트 | 무변경 (122 PASS 유지) |
