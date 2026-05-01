---
template: plan
version: 1.2
description: 레퍼런스 충실도 보장 — page-guard 게이트 + 의도 룰 + analyze 청사진 (A+B+C 통합)
---

# reference-fidelity-toolkit Planning Document

> **Summary**: 다른 hwpx-skill 개발자의 XML-first 접근에서 학습 — "레퍼런스 99% 복원 + 쪽수 동일 강제" 패턴을 우리 API-first 시스템에 흡수한다. 양식 채우기·공문·기존 문서 편집 시 결과물의 충실도를 강제 게이트로 보장하여 사용자 신뢰도를 한 단계 끌어올린다.
>
> **Project**: pyhwpxlib
> **Version**: 0.15.0 → 0.16.0 (additive, non-breaking)
> **Date**: 2026-05-01
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

다른 hwpx-skill 의 XML-first 접근에서 다음 3가지 자산을 학습:

| 자산 | 우리 현재 상태 | 흡수 후 |
|------|---------------|---------|
| **page_guard 강제 게이트** | autofit 시도만 하고 강제 아님 | **fail-fast 게이트** — threshold 초과 시 빌드 실패 |
| **Critical Rules 의도 룰** | 9개 기술 룰 위주 | + 4개 의도 룰 (치환 우선·구조 변경 제한·페이지 동일·게이트 통과) |
| **analyze 청사진 출력** | unpack/diagnose 분산 | 한 명령으로 인간 가독 구조 요약 (charPr/paraPr/borderFill/표/페이지) |

### 1.2 Background

- **사용자 피드백 (2026-05-01)**: 다른 개발자의 XML-first SKILL.md 검토 후 "page_guard 강제 게이트 + 의도 룰 흡수" 결정
- **현재 충실도 도구의 한계**:
  - `pyhwpxlib validate` → XML 무결성만 검증 (페이지 변동 감지 못함)
  - `GongmunBuilder(autofit=True)` → 자동 조정만, 실패 시 WARN 로그 후 통과
  - `pyhwpxlib doctor` → lineseg 비표준만 진단
  - 결과물이 "validate 통과 ≠ 사용자 의도 일치"
- **다른 개발자의 강점**:
  - `page_guard.py` 미통과 시 완료 처리 금지 — 강제 게이트
  - "치환 우선 편집", "무단 페이지 증가 금지" 명시 의도 룰
- **상호 보완**: 우리 광범위 자동화 + 다른 개발자의 보존 게이트 = 양 진영 강점 흡수

### 1.3 Related

- 다른 개발자 SKILL.md (사용자 공유, 2026-05-01)
- `pyhwpxlib/gongmun/autofit.py` — 자동 조정 로직 (강제화 베이스)
- `pyhwpxlib/rhwp_bridge.py` — `get_page_render_tree` 페이지 카운트 추출 가능
- `pyhwpxlib/doctor.py` — diagnose CLI 패턴 참고
- `references/HWPX_RULEBOOK.md` — Critical Rules 9개 (확장 대상)

---

## 2. Goals

### 2.1 Primary Goals

1. **A. `pyhwpxlib page-guard` CLI** — 레퍼런스 HWPX 와 결과 HWPX 의 페이지 카운트 비교, threshold 초과 시 exit 1
2. **B. Critical Rules 의도 룰 4개 추가** — SKILL.md 와 references/HWPX_RULEBOOK.md 양쪽
3. **C. `pyhwpxlib analyze` 청사진 모드** — `--blueprint` 플래그로 인간 가독 구조 요약 출력

### 2.2 Non-Goals

- XML-first 워크플로 전면 도입 (우리는 API-first 유지)
- 다른 개발자의 templates/ 5종 (gonmun/report/minutes/proposal) 재구현 (우리는 10 테마 + 양식 등록 시스템으로 대체)
- 기존 `validate`/`doctor`/`lint` CLI 동작 변경 (page-guard 는 별개 명령)
- pyhwpxlib API 시그니처 변경 (additive 만)

### 2.3 Success Criteria

- [ ] `pyhwpxlib page-guard --reference ref.hwpx --output out.hwpx` 가 레퍼런스 N 페이지, 결과 N 페이지면 exit 0, 다르면 exit 1 + stderr 진단
- [ ] `--threshold 0` (default) / `--threshold 1` (1페이지 허용 오차) 옵션 동작
- [ ] `pyhwpxlib analyze --blueprint <file>` 가 charPr/paraPr/borderFill/표/페이지 요약을 stdout 에 인간 가독 형태로 출력
- [ ] `--json` 출력 모드 (LLM 친화)
- [ ] SKILL.md `Critical Rules` 표에 의도 룰 4개 추가 (#10~#13 또는 신규 섹션)
- [ ] `references/HWPX_RULEBOOK.md` 동기화
- [ ] 신규 테스트 ≥ 8 케이스 (page-guard 5 + analyze 3) 모두 PASS

---

## 3. Requirements

### 3.1 Functional Requirements

#### FR-1: `page-guard` 명령 (A)

```bash
pyhwpxlib page-guard --reference REF --output OUT [--threshold N] [--json]
```

- `--reference` (필수): 기준 HWPX
- `--output` (필수): 검증할 HWPX
- `--threshold N` (default 0): 허용 페이지 차이 (0 = 완전 동일)
- `--json`: JSON 결과 출력 (CI 통합용)
- `pyhwpxlib gongmun-validate` 처럼 exit code 로 fail/pass 신호
- 페이지 카운트는 rhwp `get_page_render_tree` 또는 OWPML `<hp:secPr>` 분석으로 계산

**출력 예 (text)**:
```
✓ page-guard PASS
  reference: 1 pages
  output:    1 pages
  threshold: 0
```
```
✗ page-guard FAIL
  reference: 1 pages
  output:    2 pages (+1)
  threshold: 0
  hint: 결과가 1페이지를 초과했습니다. autofit 또는 텍스트 압축을 시도하세요.
```

#### FR-2: 의도 룰 4개 추가 (B)

`SKILL.md` 와 `references/HWPX_RULEBOOK.md` 의 Critical Rules 표에 다음 추가:

| 룰 | 내용 | 결과 |
|----|------|------|
| 의도-1 | **치환 우선 편집** — 양식 채우기·기존 문서 편집 시 새 문단/표 추가 대신 기존 노드 텍스트 치환을 우선 | 서식 보존, 페이지 변동 최소화 |
| 의도-2 | **구조 변경 제한** — 사용자 명시 요청 없이 `<hp:p>` `<hp:tbl>` `rowCnt` `colCnt` 추가/삭제/분할/병합 금지 | 레퍼런스 충실도 |
| 의도-3 | **페이지 동일 필수** — 레퍼런스가 있으면 결과 쪽수가 레퍼런스와 동일해야 함 (1매 표준 양식 특히) | 양식·공문 신뢰도 |
| 의도-4 | **page-guard 통과 필수** — 레퍼런스 작업 시 `pyhwpxlib validate` 통과만으로 완료 처리 금지, `page-guard` 도 통과해야 함 | 강제 게이트 |

#### FR-3: `analyze --blueprint` 모드 (C)

```bash
pyhwpxlib analyze --blueprint FILE [--json]
```

기존 `analyze` 가 있으면 옵션 추가, 없으면 신규 명령.

**출력 예 (text)**:
```
═══ HWPX Blueprint: reference.hwpx ═══

Page
  size:    A4 (59528 × 84186 HWPUNIT)
  margins: L/R 8504, T/B 5667
  body:    42520 (= 150mm)
  pages:   1

Styles
  charPr  0~13  (10pt 함초롬바탕 → 22pt 볼드 등 14종)
  paraPr  0~27  (JUSTIFY/CENTER/RIGHT, 들여쓰기 4단계, 섹션 헤더)
  borderFill  1~8  (테두리 + 색상 헤더 5종)

Tables (3)
  T1  3×4  cols=[14173, 14173, 14174] · 헤더행 borderFill=4
  T2  5×2  cols=[8504, 34016] · 라벨/내용
  T3  2×3  cols=[10630, 10630, 21260] · cellSpan 2개

Body
  50 paragraphs · 3 tables · 0 images
  styles used: charPr {0,7,8,10}, paraPr {0,20,21,24}
  page_break: 0
```

**출력 예 (json)**: 같은 정보 JSON 직렬화 — LLM 이 새 문서 작성 시 청사진 그대로 사용 가능.

### 3.2 Non-Functional Requirements

- **Backward compat**: 기존 CLI 명령 동작 무변경. 신규 명령만 추가.
- **Speed**: page-guard < 2초 (rhwp WASM 로딩 포함), analyze < 1초.
- **Cross-platform**: macOS/Linux 동일 동작 (rhwp 의존성).
- **테스트 커버리지**: 신규 코드 ≥ 90%

---

## 4. Constraints

### 4.1 Technical Constraints

- 페이지 카운트 추출 방법:
  1. **rhwp WASM** (`get_page_render_tree`) — 정확하지만 무거움
  2. **OWPML 정적 분석** (`<hp:p pageBreak="1">` 카운트 + secPr 추정) — 빠르지만 부정확
  - **결정**: rhwp 1차, 실패 시 정적 폴백
- analyze --blueprint 는 OWPML 파싱만으로 충분 (rhwp 불필요)
- 신규 의존성 추가 금지 (이미 lxml + rhwp 충분)

### 4.2 Resource Constraints

- 1인 개발 — A → B → C 순서로 1~2일 내 완료 가능
- 테스트는 기존 fixture (`tests/fixtures/`) 재사용 + page-guard 전용 fixture 2개 추가

### 4.3 Other Constraints

- v0.16.0 같은 릴리스에 묶음 (3개 분리 릴리스 안 함)
- skill bundle (hwpx-skill-0.16.0.zip) 도 동시 갱신

---

## 5. Risks

### 5.1 Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|:-----------:|:------:|------------|
| rhwp 페이지 카운트 부정확 (특정 HWPX 에서 한컴과 차이) | M | M | 정적 폴백 + `--mode rhwp/static/both` 옵션 + 실측 fixture 5종 회귀 테스트 |
| 의도 룰이 너무 엄격해서 정상 워크플로 막음 | L | M | "사용자 명시 요청 없이" 단서 명시. 룰은 가이드 우선, 강제 게이트는 page-guard 만 |
| analyze 청사진이 너무 장황해서 LLM 컨텍스트 폭발 | L | L | --json 모드 + `--depth 1/2/3` 옵션으로 요약 수준 조절 |
| 다른 개발자 page_guard 와 알고리즘 차이 → 호환성 분쟁 | L | L | 이 프로젝트는 독립. 비호환 명시 (예: "다른 page_guard 와 다른 알고리즘") |

### 5.2 Assumptions

- rhwp WASM 이 페이지 카운트를 정확히 보고한다 (이미 autofit 에서 검증됨)
- 사용자가 양식·공문 작업에서 "1매 표준" 을 강제 게이트로 원함 (피드백 명시)
- 의도 룰은 SKILL.md 기재만으로도 LLM 동작 변화에 충분 (강제 메커니즘 불필요)

---

## 6. Implementation Plan

### 6.1 Phases

| Phase | Description | Estimated Time |
|-------|-------------|----------------|
| P1 | A. page-guard CLI 구현 + 5 테스트 | 0.5일 |
| P2 | C. analyze --blueprint 모드 + 3 테스트 | 0.5일 |
| P3 | B. SKILL.md + HWPX_RULEBOOK.md 의도 룰 4개 추가 | 1시간 |
| P4 | 통합 — workflows 워크플로우 [3] 양식 채우기 / [5] 공문에 page-guard 게이트 step 추가 | 1시간 |
| P5 | skill bundle (0.16.0.zip) + 동기화 + 메모리 갱신 | 30분 |

### 6.2 Technologies/Tools

- **lxml**: OWPML 정적 분석 (analyze blueprint, page-guard static fallback)
- **rhwp_bridge**: 페이지 카운트 정확 측정 (page-guard primary)
- **argparse**: 기존 cli.py 패턴 따름
- **pytest**: 신규 테스트 8개 추가

### 6.3 Dependencies

- 신규 외부 의존성 없음
- 내부: `pyhwpxlib.rhwp_bridge.RhwpEngine.load().get_page_render_tree()` 활용
- skill bundle 빌드는 기존 `make zip` 또는 수동 zip 절차

---

## 7. Implementation Order

### 7.1 Recommended Order

1. **Step 1**: `pyhwpxlib/page_guard.py` 모듈 신설 — `count_pages(hwpx_path) -> int` 함수 (rhwp + static)
2. **Step 2**: `pyhwpxlib/cli.py` 에 `_cmd_page_guard` 추가 + argparse 등록
3. **Step 3**: `tests/test_page_guard.py` — 5 케이스 (동일/+1/-1/threshold/static fallback)
4. **Step 4**: `pyhwpxlib/blueprint.py` 모듈 신설 — `analyze_blueprint(hwpx_path) -> dict` (OWPML 파싱)
5. **Step 5**: `pyhwpxlib/cli.py` `_cmd_analyze` 에 `--blueprint --json --depth` 옵션 추가 (또는 신규 `_cmd_blueprint`)
6. **Step 6**: `tests/test_blueprint.py` — 3 케이스 (text 출력 / json 출력 / 빈 문서)
7. **Step 7**: `skill/SKILL.md` Critical Rules 표 확장 (의도 룰 4개)
8. **Step 8**: `skill/references/HWPX_RULEBOOK.md` 동기화
9. **Step 9**: SKILL.md 워크플로우 [3] 양식 채우기 Step E + [5] 공문에 page-guard step 명시
10. **Step 10**: `pyproject.toml` + `__init__.py` 0.15.0 → 0.16.0 + `update_license_date.py --append`
11. **Step 11**: 통합 테스트 실행 (`pytest tests/`) + skill zip 빌드 + 사용자 동기화

### 7.2 Critical Path

Step 1 → 2 → 3 (A 완료) → Step 4 → 5 → 6 (C 완료) → Step 7 → 8 → 9 (B 완료) → Step 10 → 11 (릴리스)

A 와 C 는 독립적이라 병렬 가능. B 는 A+C 완료 후 통합 시점에.

---

## 8. Testing Plan

### 8.1 Test Strategy

- **단위**: `count_pages` (rhwp/static 경로 각각), `analyze_blueprint` (OWPML 파싱)
- **CLI**: argparse 동작, exit code, stdout/stderr 형식
- **회귀**: 기존 테스트 107 PASS 유지

### 8.2 Test Cases

#### page-guard (5)

1. T-PG-01: 레퍼런스 1p · 결과 1p · threshold 0 → exit 0
2. T-PG-02: 레퍼런스 1p · 결과 2p · threshold 0 → exit 1, stderr "+1"
3. T-PG-03: 레퍼런스 1p · 결과 2p · threshold 1 → exit 0 (허용 오차 내)
4. T-PG-04: rhwp 로딩 실패 → static fallback 동작
5. T-PG-05: `--json` 모드 — 결과 JSON 파싱 가능

#### blueprint (3)

6. T-BP-01: 표 3개 + 50 문단 문서 → text 출력에 "Tables (3)" 포함
7. T-BP-02: `--json` → 유효 JSON, charPr/paraPr/borderFill 키 존재
8. T-BP-03: 빈 HWPX (HwpxBuilder().save()) → 페이지 1 + 표 0 정상 보고

---

## 9. Open Questions

- [ ] page-guard 의 페이지 카운트 — rhwp 가 한컴 실제 렌더와 100% 일치하는가? (기존 autofit 에서 동작했으니 OK 가정)
- [ ] analyze --blueprint 와 기존 `lint`/`diagnose` 의 출력 중복 — 별개 명령 vs 통합 옵션? (별개 권장 — `analyze` 는 아직 없음)
- [ ] 의도 룰을 SKILL.md 기재만 할지, `pyhwpxlib lint --strict` 모드로 자동 검사도 추가할지? (1차 PR 은 SKILL.md 만)

---

## 10. References

- 다른 hwpx-skill SKILL.md (사용자 공유 2026-05-01) — XML-first + page_guard.py 패턴
- `pyhwpxlib/gongmun/autofit.py` — 페이지 카운트 → 조정 로직 (참조)
- `pyhwpxlib/rhwp_bridge.py:get_page_render_tree` — 페이지 카운트 소스
- `references/HWPX_RULEBOOK.md` — Critical Rules 확장 대상
- `docs/01-plan/features/json-schema-expansion.plan.md` — 최근 plan 템플릿 패턴

---

## 11. Approval

- [ ] Plan reviewed
- [ ] Stakeholders aligned (사용자 — 2026-05-01 A+B+C 동시 진행 승인)
- [ ] Ready for Design Phase
