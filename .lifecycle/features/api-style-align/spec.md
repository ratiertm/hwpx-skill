---
feature: api-style-align
title: API Style Alignment — Match Official python-hwpx Patterns for Upstream PR
created: 2026-03-28
updated: 2026-03-28
status: agreed
depends_on: [owpml-phase2-bugfix]
steps: 15
tags: [api, refactor, upstream, pr-ready]
---

# E2E Spec: API Style Alignment

Refactor our fork's custom APIs to match the official python-hwpx coding patterns,
so the changes are PR-ready for upstream (airmang/python-hwpx).

**원칙:**
1. 기존 공식 API 시그니처를 깨지 않는다 (하위 호환)
2. 새 파라미터는 기존 시그니처 뒤에 keyword-only로 추가
3. 공식 패턴(section.properties, run.bold=True)을 따른다
4. 중복 구현은 내부에서 공식 API를 호출하도록 위임

---

## Interaction 1: ensure_run_style 하위 호환 확장

### e2e-api-style-001: 시그니처 하위 호환 Screen

**Chain:** Screen
**Status:** pending

#### What
공식 `ensure_run_style(bold, italic, underline)` 시그니처를 유지하면서 우리 파라미터를 keyword-only로 추가.

#### Verification Criteria
- [ ] `ensure_run_style(bold=True)` — 기존대로 동작 (하위 호환)
- [ ] `ensure_run_style(bold=True, height=2000, font_hangul="맑은 고딕")` — 확장 동작
- [ ] `ensure_run_style(height=2000)` — 새 파라미터만으로도 동작
- [ ] 공식 테스트 209개 통과

#### Details
- **Element:** `src/hwpx/oxml/document.py` ensure_run_style()
- **User Action:** 기존 코드가 깨지지 않는지 확인
- **Initial State:** 우리 fork는 이미 확장되어 있으나, `**kwargs` 래퍼로 되어 있음

---

### e2e-api-style-002: document.py 래퍼 정리 Connection

**Chain:** Connection
**Status:** pending

#### What
`HwpxDocument.ensure_run_style(**kwargs)` → 명시적 파라미터 시그니처로 변경. docstring에 모든 파라미터 문서화.

#### Verification Criteria
- [ ] `document.py`의 ensure_run_style이 명시적 파라미터를 가짐 (kwargs 아님)
- [ ] docstring이 공식 스타일 (Args: 섹션) 따름
- [ ] type hint가 모든 파라미터에 있음

#### Details
- **Method:** `src/hwpx/document.py` HwpxDocument.ensure_run_style()
- **Endpoint:** 명시적 시그니처 + docstring
- **Request:** N/A
- **Auth:** None

---

### e2e-api-style-003: ensure_run_style 테스트 Processing

**Chain:** Processing
**Status:** pending

#### What
공식 테스트 + 우리 확장 테스트 모두 통과.

#### Verification Criteria
- [ ] 기존 공식 테스트 (bold/italic/underline만 사용) 통과
- [ ] 확장 파라미터 테스트 (height, font, strikeout 등) 통과
- [ ] 하위 호환: 기존 코드에서 에러 없음

#### Details
- **Storage:** src/hwpx/oxml/document.py — WRITE

---

### e2e-api-style-004: ensure_run_style Response

**Chain:** Response
**Status:** pending

#### What
확장된 ensure_run_style이 Whale에서 렌더링 확인.

#### Verification Criteria
- [ ] height + font_hangul + bold 조합 문서 → Whale에서 정상 표시
- [ ] 공식 API (bold만) 문서 → 기존대로 동작

---

### e2e-api-style-005: ensure_run_style Error

**Chain:** Error
**Status:** pending

#### What
잘못된 파라미터에 대한 에러 처리.

#### Verification Criteria
- [ ] `height=-1` → ValueError
- [ ] `text_color="red"` → ValueError
- [ ] 기존 공식 호출 패턴에서 새 에러 안 남

---

## Interaction 2: ensure_para_style → 공식 패턴 적용

### e2e-api-style-006: ensure_para_style 네이밍 Screen

**Chain:** Screen
**Status:** pending

#### What
`ensure_para_style` 을 공식의 `ensure_char_property` / `ensure_run_style` 네이밍 패턴에 맞춰 정리.

#### Verification Criteria
- [ ] `HwpxOxmlDocument.ensure_para_style()` 메서드 존재
- [ ] `HwpxDocument.ensure_para_style()` 래퍼 존재 (명시적 시그니처)
- [ ] `HwpxOxmlHeader.ensure_para_property()` 내부 메서드 존재
- [ ] 네이밍이 공식 패턴과 일관: `ensure_*_style()` (document), `ensure_*_property()` (header)

---

### e2e-api-style-007: ensure_para_style docstring Connection

**Chain:** Connection
**Status:** pending

#### What
공식 스타일 docstring (Args, Returns, Raises 섹션) 적용.

#### Verification Criteria
- [ ] document.py의 docstring이 공식 ensure_run_style과 동일 스타일
- [ ] oxml/document.py의 docstring이 공식 ensure_char_property와 동일 스타일
- [ ] 모든 파라미터에 type hint

---

### e2e-api-style-008: ensure_para_style 테스트 Processing

**Chain:** Processing
**Status:** pending

#### What
ensure_para_style 테스트.

#### Verification Criteria
- [ ] align, indent, line_spacing 등 모든 파라미터 테스트
- [ ] add_paragraph(para_pr_id_ref=) 조합 테스트
- [ ] charPr + paraPr 조합 테스트

---

### e2e-api-style-009: ensure_para_style Response

**Chain:** Response
**Status:** pending

#### What
Whale에서 정렬/줄간격/들여쓰기 렌더링 확인.

---

### e2e-api-style-010: ensure_para_style Error

**Chain:** Error
**Status:** pending

#### What
잘못된 파라미터 에러 처리.

#### Verification Criteria
- [ ] `align="BAD"` → ValueError
- [ ] `line_spacing=-1` → ValueError

---

## Interaction 3: 나머지 API 공식 패턴 적용 + PR 준비

### e2e-api-style-011: insert_image docstring + type hints Screen

**Chain:** Screen
**Status:** pending

#### What
insert_image, set_page_setup, create_style, set_cell_align 등에 공식 스타일 docstring + type hints.

#### Verification Criteria
- [ ] 모든 새 public 메서드에 Args/Returns/Raises docstring
- [ ] 모든 파라미터에 type hint
- [ ] 공식 코드와 동일한 들여쓰기/네이밍 컨벤션

---

### e2e-api-style-012: set_page_setup → section.properties 위임 Connection

**Chain:** Connection
**Status:** pending

#### What
set_page_setup 내부에서 section.properties.set_page_size() + set_page_margins()를 호출하도록 위임. paper 프리셋은 우리가 유지.

#### Verification Criteria
- [ ] `doc.set_page_setup(paper="A4")` 기존대로 동작
- [ ] 내부에서 `section.properties.set_page_size()` 호출
- [ ] 공식 API와 중복 코드 제거

---

### e2e-api-style-013: 전체 테스트 통과 Processing

**Chain:** Processing
**Status:** pending

#### What
공식 python-hwpx 테스트 209개 + 우리 테스트 모두 통과.

#### Verification Criteria
- [ ] `pytest tests/` — 공식 209개 통과
- [ ] hwpx-skill 64개 통과
- [ ] 새 API 스타일 테스트 추가

#### Details
- **Storage:** src/hwpx/ 전체 — WRITE

---

### e2e-api-style-014: PR용 커밋 정리 Response

**Chain:** Response
**Status:** pending

#### What
upstream PR에 포함할 커밋을 정리.

#### Verification Criteria
- [ ] 하나의 깨끗한 커밋 또는 기능별 분리된 커밋
- [ ] 커밋 메시지가 공식 저장소 스타일 따름
- [ ] CHANGELOG 또는 PR description 준비

---

### e2e-api-style-015: PR 에러 케이스 Error

**Chain:** Error
**Status:** pending

#### What
PR 거절 시나리오 대비.

#### Verification Criteria
- [ ] 하위 호환 깨짐 → 테스트로 검증 완료
- [ ] 코드 스타일 불일치 → docstring/type hint 정리 완료
- [ ] 테스트 누락 → 모든 새 기능에 테스트 포함

---

## Deviations

_No deviations recorded yet._
