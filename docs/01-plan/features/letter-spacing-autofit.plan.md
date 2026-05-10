---
template: plan
version: 1.3
feature: letter-spacing-autofit
date: 2026-05-07
author: ratiertm
project: hwpx-skill / pyhwpxlib
version_at_plan: 0.18.1
target_version: 0.19.0
status: Draft
---

# letter-spacing-autofit Planning Document

> **Summary**: 한국어 양식·보고서에서 라인 끝 단어 분할(예: "정산기" → "정산"|"기")을 자간 ±1% 자동 조정으로 해소. 한컴/Windows 의존 없이 lineseg 기반 탐지 + rhwp WASM fallback + per-line run splitting + 자체 simulator 반복 보정으로 구현.
>
> **Project**: hwpx-skill / pyhwpxlib
> **Version**: 0.18.1 → 0.19.0
> **Author**: ratiertm
> **Date**: 2026-05-07
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 한글 문서 라인 끝에서 단어가 두 줄로 잘리는 가독성 저하. 수작업 자간 조정은 노동집약적이고, 받은 COM 스크립트는 한컴오피스 + Windows 필수라 크로스플랫폼 라이브러리에 직접 사용 불가. |
| **Solution** | OWPML `<hp:lineseg textpos="N"/>` 로 단어 분할 탐지 (lineseg 부재 시 rhwp WASM 으로 동적 생성) → per-line run splitting + charPr letterSpacing ±1% 반복 보정 (자체 simulator 기반) → 본문/표/글상자 전체 영역 순회. 한컴 없이 동작. |
| **Function/UX Effect** | 사용자가 1 CLI 호출로 문서 전체 자간 자동 조정 → 단어 분할 0건 (또는 보정 한계 초과 문단은 수동 권고). LLM 자동화 파이프라인에서도 MCP 도구로 호출 가능. |
| **Core Value** | 받은 COM 스크립트를 한컴 없이 재현해 macOS/Linux/Windows 모두에서 동일 결과. pyhwpxlib 가 가지는 "한컴 없이 동작" 가치명제의 자연스러운 확장. |

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | 라인 끝 단어 분할이 한국어 문서 가독성을 깨뜨리고, 수작업 자간 조정은 양식 수십 장 시 비현실적. 받은 COM 스크립트는 한컴+Windows 필수라 본 프로젝트 가치명제와 충돌. |
| **WHO** | pyhwpxlib CLI/MCP 사용자, 특히 보고서·계약서·양식을 다량 처리하는 사용자. 운영체제 무관. |
| **RISK** | (1) per-line run splitting 후 lineseg 동기화 불일치 → 한컴 보안경고. (2) 자체 simulator 의 layout 정확도가 한컴과 달라 시각 결과 미스매치. (3) 무한 반복 (수렴 안 함). |
| **SUCCESS** | (1) 받은 스크립트가 처리하는 샘플 문서에서 word-split 0건 달성 (or undo+skip 처리). (2) sample 4-page 문서 처리 시간 ≤ 30초. (3) 기존 회귀 0건. (4) 한컴오피스 1건 이상 시각 검증. |
| **SCOPE** | 0.19.0: lineseg 탐지 + per-line run split + 자체 simulator iteration + 본문/표/글상자. 보류: COM 브리지 (0.21.0+). |

---

## 1. Overview

### 1.1 Purpose

한국어 HWPX 문서에서 라인 끝 단어 분할을 자간 ±1% 조정으로 자동 해소한다. 한컴오피스 의존 없이.

### 1.2 Background

**받은 COM 스크립트 분석 (2026-05-06 검토)**:
- `hwp.Run("MoveLineEnd")` + `MoveSelWordBegin/End` 로 잘린 단어 앞/뒤 길이 측정
- `앞부분길이 >= 뒷부분길이` → `CharShapeSpacingDecrease` (자간 -1%, 단어 끌어당김)
- 그 외 → `CharShapeSpacingIncrease` (자간 +1%, 단어 통째 다음 줄로 밀어냄)
- 종료: 잘린 단어 없음 / 한 줄 문단 / 15% 누적 (undo all, 스크립트 버그로 break 누락)
- 영역: 본문 + `area` 인덱스 순회로 표·각주·글상자

**검증 (2026-05-06 실측)**:
- `Test/2021년_AFC설비_1분기_정기점검_계획서.hwpx` 에서 다중 lineseg paragraph 26건, 그 중 word-split 1건 정확 탐지 (`'산'|'기'` = "정산기" 분할)
- HWPX `<hp:lineseg textpos="N"/>` 가 권위 있는 source

### 1.3 Related Documents

- 받은 COM 스크립트 — `자간자동조정` 함수 (이 문서의 §1.2)
- TODO.md backlog — "letter-spacing-autofit (0.19.0)"
- `feedback_hancom_security_trigger.md` — lineseg.textpos > UTF-16(text) 변경 후 보안경고 트리거. **이 사이클의 가장 큰 리스크**.
- `feedback_hwpx_ecosystem_position.md` — rhwp 노선 (감지+고지+동의 후 보정). 본 사이클은 자간 조정이 명시 사용자 동의 하의 보정이라 정책 일치.

---

## 2. Scope

### 2.1 In Scope

- [ ] **D-LINESEG**: HWPX `<hp:lineseg textpos="N"/>` 파서. 다중 lineseg paragraph에서 word-split 위치 탐지 알고리즘
- [ ] **D-RHWP**: lineseg 누락 시 rhwp WASM으로 임시 렌더 → lineseg-equivalent 추출 (fallback)
- [ ] **D-SCOPE**: section 본문 + `<hp:tbl>` 셀 + 글상자(`<hp:rect>` `<hp:gso>`) 모든 paragraph 순회
- [ ] **A-RUN-SPLIT**: lineseg.textpos 경계로 `<hp:run>` split + 각 line-run 에 charPr 별도 부여 (run splitting 알고리즘)
- [ ] **A-CHARPR**: charPr `letterSpacing` 속성 값 변경 (±N%, default 1% step)
- [ ] **I-SIMULATE**: 자체 simulator (`_measure_text_cached` + paragraph width) 로 보정 후 line break 재계산 → re-detect → iterate
- [ ] **I-LIMIT**: 15% 누적 도달 시 **그 문단만 undo + skip** (스크립트 버그 수정), 사용자 보고
- [ ] **I-HEURISTIC**: 받은 스크립트의 `앞부분 vs 뒷부분` 휴리스틱 그대로 (-1% / +1%)
- [ ] **CLI**: `pyhwpxlib autofit-spacing INPUT [-o OUT] [--report] [--max-percent N] [--inplace]`
- [ ] **MCP**: `hwpx_autofit_spacing(file, ...) -> dict {applied, skipped, manual_fix_needed[]}`
- [ ] **TEST**: AFC설비 문서 회귀 (현재 word-split 1건 → 0건), 한 줄 문단 무영향, 빈 문단 무영향, no-lineseg 파일 rhwp fallback
- [ ] **DOC**: SKILL.md / GUIDE / WORKFLOW Step 추가 + Critical Rule 1건 (rhwp 노선 적용 명시)

### 2.2 Out of Scope

- **COM 브리지** — Windows + 한컴 한정 wrapper. 0.21.0+ 별도 사이클 (사용자가 옵션 E로 명시 합의)
- **자간 외 조정** — 줄간격, 글자크기, 문단 너비 변경 (스크립트도 안 건드림)
- **스크립트 버그 그대로 재현** — 15% 후 break 누락 / undo all 후 무한루프 가능성 — 우리는 명시 종료
- **Hancom 권위 layout 일치 보장** — 우리 simulator 결과가 Hancom 시각 결과와 100% 일치 보장 안 함 (rhwp 노선 정책 + Critical Rule #12 reference fidelity 정책과 일관)
- **JSON-IO 통합** — `from_json` 의 letterSpacing/autofit 키 노출 — 별도 사이클
- **운율적 조정 (mate-pair, 약자 쌍)** — 영문/일문 typography 의 kerning. 한국어는 monospace 가까워 불필요

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | `<hp:lineseg textpos="N"/>` 다중 출현 시 word-split 위치 정확 탐지 (n번째 break의 `text[pos-1]`/`text[pos]` 모두 non-whitespace alnum/CJK) | High | Pending |
| FR-02 | lineseg 부재 시 rhwp WASM 으로 임시 렌더 → lineseg-equivalent 정보 추출 (rhwp render tree의 Line bbox + 해당 line의 text 매핑) | High | Pending |
| FR-03 | 탐지된 split paragraph에 대해 lineseg.textpos 경계로 `<hp:run>` split + per-line charPr letterSpacing 부여 | High | Pending |
| FR-04 | 휴리스틱 적용: 앞부분길이 ≥ 뒷부분길이 → -1%, 그 외 → +1% (스크립트와 동일) | High | Pending |
| FR-05 | 자체 simulator로 보정 후 line break 재계산 → re-detect 반복. 수렴 또는 15%/문단 도달 시 종료 | High | Pending |
| FR-06 | 15% 누적 도달 시 그 문단의 charPr 변경 모두 되돌리고(undo) 다음 문단으로. `manual_fix_needed[]` 에 기록 | High | Pending |
| FR-07 | 본문 + `<hp:tbl>` 모든 셀 + 글상자/도형 안의 paragraph 모두 순회 | Medium | Pending |
| FR-08 | CLI `pyhwpxlib autofit-spacing INPUT [-o OUT] [--max-percent N] [--report] [--inplace]` 동작 (exit 0 = 모두 처리, 1 = manual fix 필요 문단 존재) | High | Pending |
| FR-09 | MCP `hwpx_autofit_spacing(file_path, output_path, max_percent=15) -> dict` (filled, skipped, manual_fix_needed) | Medium | Pending |
| FR-10 | 0.18.1 호출자 무영향 (자간 조정은 명시 호출 시에만 동작) | High | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | 4-page 문서 (300+ paragraphs) 처리 ≤ 30초 | `time pyhwpxlib autofit-spacing AFC설비.hwpx` |
| Accuracy | AFC설비 샘플 word-split 1건 → 0건 (or skip 보고) | 회귀 테스트 + 한컴 시각 확인 1건 |
| Reliability | 기존 197 PASS 무회귀 + 신규 약 12건 = ~209 | `pytest -q` |
| Compatibility | 0.18.x 호출자 무영향 | tests/test_render_consistency.py 등 sha256 anchor 유지 |
| Hancom safety | 보정된 lineseg.textpos 와 변경된 text 길이 일관 (precise lineseg fix 자동 적용) | doctor pass + 한컴 보안경고 없음 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] FR-01~FR-10 모두 구현·검증 완료
- [ ] AFC설비 회귀 테스트 PASS (word-split 1→0 or skip 보고)
- [ ] 1매 양식 (`Test/output/template_fill_makers.hwpx` 등) 처리 시 byte-identical 보존 (자간 조정 대상 없음)
- [ ] 한컴오피스에서 결과 1건 시각 확인 (사용자 책임 — 보고서에 명시)
- [ ] CLAUDE.md "Release checklist" 8단계 모두 ✅
- [ ] PyPI 0.19.0 publish + git tag + skill zip + ~/.claude sync

### 4.2 Quality Criteria

- [ ] 자체 simulator 와 rhwp lineseg 결과가 sample 1개에서 일치 (cross-validation)
- [ ] precise lineseg fix 자동 적용 (보정 후 textpos 동기화) — 한컴 보안경고 없음
- [ ] 신규 ~12 테스트 케이스 PASS, 197 → ~209 PASS
- [ ] No new lint errors

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **R-1: lineseg.textpos 변경 후 한컴 보안경고** (precise fix 필요) | High | High | 모든 보정 후 `package_ops.write_zip_archive(strip_linesegs="precise")` 자동. precise fix 가 0.13.2 부터 검증된 path. CHANGELOG 명시. |
| **R-2: 자체 simulator layout 가 한컴과 미스매치** → 보정 결과가 한컴에서 다르게 보임 | Medium | High | rhwp 노선 정책 (`feedback_hwpx_ecosystem_position.md`) 적용. 사용자 한컴 시각 확인 필수 명시. CLI에 `--rhwp-validate` 옵션 (별도 사이클). |
| **R-3: 무한 반복** (수렴 실패) | High | Low | 15%/문단 hard cap + 50 iter/문단 hard cap 이중 안전장치. 도달 시 undo + skip + 보고. |
| **R-4: per-line run split 실패** (이미 split 된 run, charPr ID 충돌) | Medium | Medium | 기존 run의 charPr ID 보존 + 새 charPr `extends` 패턴. 충돌 시 보정 skip + 보고. 단위 테스트로 가드. |
| **R-5: 표 안 표 (중첩 셀) 순회 누락** | Low | Medium | 재귀 walk + visited set. 단위 테스트 fixture (중첩 표) 추가. |
| **R-6: 빈 문단 / 한 줄 문단 / 헤더 등 처리 불필요 case 오인식** | Medium | Low | linesegs.length < 2 인 paragraph 모두 skip. 단위 테스트 가드. |
| **R-7: 받은 스크립트 휴리스틱이 한국어 외 (영문, 일문) 에서 부적합** | Low | Low | 한국어 우선 구현. 비-CJK paragraph는 word-split 정의가 다르므로 0.19.0 에서는 detection skip. 추후 사이클. |

---

## 6. Impact Analysis

### 6.1 Changed Resources

| Resource | Type | Change Description |
|----------|------|--------------------|
| `pyhwpxlib/autofit/` (신규 패키지) | New module | `detect.py` (lineseg 파서 + word-split 탐지) + `apply.py` (run split + charPr) + `simulator.py` (자체 layout) + `engine.py` (orchestrator) |
| `pyhwpxlib/cli.py` | Module | `autofit-spacing` subcommand 핸들러 + parser |
| `pyhwpxlib/mcp_server/server.py` | Module | `hwpx_autofit_spacing` MCP 도구 (compressed docstring) |
| `pyhwpxlib/llm_guide.py` | Module | v0.19.0 헤더 + §14 자간 자동조정 신규 + 버전 히스토리 |
| `skill/SKILL.md` | Skill doc | Versions 표 0.19.0 행 + Quick Reference + Critical Rule 추가 |
| `skill/hwpx-form/WORKFLOW.md` | Skill doc | Step E (page-fit) 직후 새 Step E.5 (자간 자동조정 옵션) |
| `tests/test_autofit_spacing.py` | New test | ~12 케이스 |
| `pyproject.toml`, `pyhwpxlib/__init__.py`, `CHANGELOG.md` | Release | 0.18.1 → 0.19.0 |

### 6.2 Current Consumers

| Resource | Operation | Code Path | Impact |
|----------|-----------|-----------|--------|
| 자간 조정 | new | 신규 호출자 0 | N/A |
| `<hp:lineseg>` 파서 | read | `pyhwpxlib/blueprint.py:203` (이미 읽기는 함) | None — 새 파서는 별도 모듈 |
| `<hp:run>` split | new | new path | 기존 run 구조 무수정 (보정 호출 안 한 paragraph는 그대로) |
| precise lineseg fix | call | 기존 `package_ops.write_zip_archive` | None — 호출 위치만 늘어남 |

### 6.3 Verification

- [ ] AFC설비 샘플 word-split 1건이 0건으로 (or skip 보고)
- [ ] 자간 조정 안 한 paragraph는 byte-identical 보존
- [ ] precise lineseg fix 후 한컴 보안경고 없음 (한컴 1건 검증)
- [ ] HwpxBuilder 새 파일 (lineseg 없음) 도 처리 가능 (rhwp fallback)

---

## 7. Architecture Considerations

### 7.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Library/CLI/MCP** | 본 프로젝트 (pyhwpxlib) | Python lib + CLI + MCP | ☑ |

### 7.2 Key Architectural Decisions (이미 사용자 합의)

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| Adjustment unit | per-paragraph / **per-line** | **per-line** | 받은 스크립트 충실 + 다른 라인 무영향 — 시각적 자연스러움 |
| Layout source | self-simulator / **rhwp** / Hancom only | **self-simulator + rhwp fallback** | 일관성 우선. rhwp는 lineseg 부재 시만 사용 |
| Detection scope | 본문만 / **본문+표+글상자** | **본문+표+글상자** | 받은 스크립트와 동일 |
| Limit reached | 그대로 (스크립트 버그) / **undo+skip** / report-only | **undo+skip + 보고** | 안전 + 사용자가 manual_fix_needed 목록 받아 후속 처리 가능 |
| 휴리스틱 step | ±1% (스크립트) / 적응형 | **±1% step (스크립트 충실)** | 검증된 동작. 0.20.0 에서 적응형 검토 |
| 출력 모드 | inplace / 별도 파일 | **별도 파일 default + `--inplace` 옵션** | 안전성 우선 |

### 7.3 모듈 구조 (delta only)

```
pyhwpxlib/
  autofit/
    __init__.py            ← public API: autofit_spacing(input, output, ...)
    detect.py              ← parse_linesegs, detect_word_splits
    apply.py               ← split_runs_at_lineseg, set_charpr_letter_spacing
    simulator.py           ← simulate_line_breaks(text, width, char_widths)
    engine.py              ← orchestrator: detect → apply → simulate → re-detect → loop
    rhwp_fallback.py       ← rhwp render → lineseg-equivalent extraction
  cli.py                   ← + autofit-spacing handler
  mcp_server/server.py     ← + hwpx_autofit_spacing
tests/
  test_autofit_spacing.py  ← (new) ~12 cases
```

---

## 8. Convention Prerequisites

### 8.1 Existing Project Conventions

- [x] CLAUDE.md "Release checklist" 8단계 (적용)
- [x] `feedback_version_sync.md` (pyproject + __init__.py 동시 bump)
- [x] `feedback_hancom_security_trigger.md` (precise lineseg fix 자동)
- [x] Critical Rule #12 reference fidelity (사용자 한컴 검증 명시)

### 8.2 Conventions to Verify

| Category | Current | To Verify | Priority |
|----------|---------|-----------|:--------:|
| run split 안전성 | none | 기존 charPr ID 보존, 충돌 회피 | High |
| simulator 결정성 | none | 같은 입력 → 같은 결과 | High |
| iteration 종료 보장 | none | 50 iter/문단 hard cap + 15% cap | High |

---

## 9. Next Steps

1. [ ] `/pdca design letter-spacing-autofit` — 3 architecture options 비교 (Module Map 5개 예상: detect / apply / simulate / engine / cli-mcp)
2. [ ] Design 단계에서 simulator 알고리즘 정확도 결정 (greedy line break vs Knuth-Plass)
3. [ ] Design 단계에서 run-split charPr ID 충돌 회피 전략 (extends pattern vs deep copy)
4. [ ] `/pdca do letter-spacing-autofit --scope detect` (Session 2 첫 모듈)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-07 | Initial draft — Checkpoint 1/2 사용자 합의 반영 (per-line, rhwp fallback, full scope, undo+skip), feasibility 실측 데이터 포함 | ratiertm |
