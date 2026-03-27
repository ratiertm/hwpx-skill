---
feature: owpml-phase2-bugfix
title: Phase 2 — Bug Fix + Stabilization + Whale Rendering Verification
created: 2026-03-28
updated: 2026-03-28
status: agreed
depends_on: [owpml-full-impl]
steps: 15
tags: [bugfix, lxml, whale, rendering, stabilization]
---

# E2E Spec: Phase 2 — Bug Fix + Stabilization

Fix lxml/ET compatibility bugs, complete stub implementations, and verify every Phase 1 feature renders correctly in Naver Whale browser.

**검증 기준: 각 기능별 hwpx 파일 생성 → Whale에서 열기 → 스크린샷 캡쳐 → 렌더링 확인**

---

## Interaction 1: lxml/ET 호환 근본 수정

### e2e-phase2-001: add_control lxml 수정 Screen

**Chain:** Screen
**Status:** pending

#### What
`add_control()`의 `ET.SubElement` → `LET.SubElement` 수정으로 add_page_number, add_auto_number 언블록.

#### Verification Criteria
- [ ] `doc.add_control(control_type="test")` 에러 없이 실행
- [ ] `doc.add_page_number()` 에러 없이 실행
- [ ] `doc.add_auto_number()` 에러 없이 실행

#### Details
- **Element:** `oxml/document.py` HwpxOxmlParagraph.add_control() line 3166
- **User Action:** 수정 후 API 호출 테스트
- **Initial State:** TypeError: SubElement() argument 1 must be xml.etree.ElementTree.Element

---

### e2e-phase2-002: lxml/ET 전수 조사 Connection

**Chain:** Connection
**Status:** pending

#### What
`oxml/document.py` 전체에서 `ET.SubElement` 호출 중 lxml element를 받는 경로를 모두 찾아 수정.

#### Verification Criteria
- [ ] `grep "ET.SubElement" oxml/document.py`의 모든 호출이 안전한지 확인
- [ ] lxml element 경로에서 호출되는 곳은 `LET.SubElement`로 변경
- [ ] 기존 테스트 209개 모두 통과

#### Details
- **Method:** grep + 코드 분석
- **Endpoint:** `src/hwpx/oxml/document.py`
- **Request:** 전체 파일 스캔
- **Auth:** None

---

### e2e-phase2-003: lxml/ET 수정 결과 Processing

**Chain:** Processing
**Status:** pending

#### What
수정 후 전체 API가 에러 없이 동작하는지 확인.

#### Verification Criteria
- [ ] add_control, add_page_number, add_auto_number 모두 동작
- [ ] 기존 동작하던 add_paragraph, add_table, ensure_run_style 등 회귀 없음
- [ ] hwpx 파일 저장 + 재오픈 + export_text 정상

#### Details
- **Steps:**
  1. ET.SubElement → LET.SubElement 수정
  2. 전체 API 호출 테스트
  3. 기존 테스트 실행
- **Storage:** src/hwpx/oxml/document.py — WRITE

---

### e2e-phase2-004: lxml 수정 Whale 검증 Response

**Chain:** Response
**Status:** pending

#### What
add_control로 생성한 문서를 Whale에서 열어 확인.

#### Verification Criteria
- [ ] add_page_number가 포함된 hwpx 파일이 Whale에서 열림
- [ ] 스크린샷에서 파일 내용 확인 가능

#### Details
- **Success Status:** Whale에서 파일 열림 + 에러 없음
- **Response Shape:** 스크린샷 확인
- **UI Updates:** Whale 브라우저에서 문서 표시

---

### e2e-phase2-005: lxml 수정 에러 Error

**Chain:** Error
**Status:** pending

#### What
수정으로 인한 회귀 확인.

#### Verification Criteria
- [ ] 기존 python-hwpx 테스트 209개 통과
- [ ] hwpx-skill 테스트 64개 통과
- [ ] 새로운 TypeError 없음

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| 기존 테스트 실패 | 회귀 발생 — 수정 필요 | null (server) |
| 새 TypeError | 다른 ET/lxml 충돌 위치 — 추가 수정 | null (server) |
| 모든 테스트 통과 | 수정 완료 | null (client) |

---

## Interaction 2: create_style 완전 구현

### e2e-phase2-006: create_style Screen

**Chain:** Screen
**Status:** pending

#### What
`create_style(name, type, char_pr_id, para_pr_id)`가 header.xml에 실제 스타일을 생성.

#### Verification Criteria
- [ ] `doc.create_style("제목1", char_pr_id=s1, para_pr_id=p1)` 가 실제 style ID 반환
- [ ] header.xml `<hh:styles>` 에 새 style 요소 추가됨
- [ ] 반환된 style_id를 `add_paragraph(style_id_ref=)` 에 사용 가능

#### Details
- **Element:** header.xml `<hh:styles><hh:style>` 요소
- **User Action:** `create_style()` 호출
- **Initial State:** stub — `return f"style-{name}"`

---

### e2e-phase2-007: create_style Connection

**Chain:** Connection
**Status:** pending

#### What
스타일이 charPr과 paraPr을 참조하여 문단에 적용됨.

#### Verification Criteria
- [ ] `add_paragraph(text, style_id_ref=style_id)` 가 스타일 적용된 문단 생성
- [ ] 스타일의 charPr 참조가 글꼴/크기에 반영됨
- [ ] 스타일의 paraPr 참조가 정렬/줄간격에 반영됨

#### Details
- **Method:** header.xml styles 조작 → section0.xml paragraph styleIDRef
- **Endpoint:** `HwpxDocument.create_style()` → `HwpxOxmlHeader`
- **Request:** name, style_type, char_pr_id, para_pr_id
- **Auth:** None

---

### e2e-phase2-008: create_style Processing

**Chain:** Processing
**Status:** pending

#### What
header.xml에 스타일 요소를 추가하고 ID를 할당.

#### Verification Criteria
- [ ] `<hh:style id="N" type="PARA" name="제목1" .../>` 생성
- [ ] charPrIDRef, paraPrIDRef 속성 설정
- [ ] itemCnt 업데이트

#### Details
- **Steps:**
  1. header.xml `<hh:styles>` 요소 찾기 또는 생성
  2. 새 `<hh:style>` 요소 추가 (id, type, name, charPrIDRef, paraPrIDRef)
  3. itemCnt 업데이트
- **Storage:** header.xml `<hh:styles>` — WRITE

---

### e2e-phase2-009: create_style Whale 검증 Response

**Chain:** Response
**Status:** pending

#### What
스타일이 적용된 문서를 Whale에서 열어 확인.

#### Verification Criteria
- [ ] 스타일 "제목1" 이 적용된 문단이 Whale에서 해당 서식으로 보임
- [ ] 스크린샷에서 글꼴/크기/정렬 확인 가능

#### Details
- **Success Status:** Whale에서 스타일 적용 확인
- **Response Shape:** 스크린샷 확인

---

### e2e-phase2-010: create_style 에러 Error

**Chain:** Error
**Status:** pending

#### What
스타일 생성 시 에러 처리.

#### Verification Criteria
- [ ] 중복 스타일 이름은 기존 스타일 ID 반환 (덮어쓰기 안 함)
- [ ] 존재하지 않는 charPrIDRef는 ValueError

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| 중복 이름 | 기존 style ID 반환 | null (client) |
| 잘못된 charPrIDRef | ValueError | null (client) |

---

## Interaction 3: Phase 1 기능 Whale 렌더링 전수 검증

### e2e-phase2-011: charPr 렌더링 검증 Screen

**Chain:** Screen
**Status:** pending

#### What
모든 charPr 속성이 포함된 문서를 Whale에서 열어 확인.

#### Verification Criteria
- [ ] 굵은 20pt 맑은 고딕 제목이 보임
- [ ] 취소선 텍스트가 보임
- [ ] 파란색 텍스트가 보임
- [ ] 장평/자간이 적용된 텍스트가 보임 (글자 간격 변화)
- [ ] Whale 스크린샷으로 확인

#### Details
- **Element:** docs/test_phase2_charpr.hwpx
- **User Action:** Whale에서 열기 → Cmd+Shift+3 캡쳐
- **Initial State:** 한컴오피스 safe_test에서 확인됨, Whale 재확인

---

### e2e-phase2-012: paraPr 렌더링 검증 Connection

**Chain:** Connection
**Status:** pending

#### What
모든 paraPr 속성이 포함된 문서를 Whale에서 열어 확인.

#### Verification Criteria
- [ ] 가운데 정렬 텍스트가 가운데에 보임
- [ ] 오른쪽 정렬 텍스트가 오른쪽에 보임
- [ ] 들여쓰기된 문단이 들여쓰기되어 보임
- [ ] Whale 스크린샷으로 확인

#### Details
- **Method:** 파일 생성 → Whale 열기 → 스크린샷
- **Endpoint:** docs/test_phase2_parapr.hwpx
- **Request:** N/A (시각 검증)
- **Auth:** None

---

### e2e-phase2-013: Table + Image + Page 렌더링 검증 Processing

**Chain:** Processing
**Status:** pending

#### What
표 (병합 포함), 이미지, 페이지 설정이 포함된 문서를 Whale에서 확인.

#### Verification Criteria
- [ ] 3x3 표가 보임
- [ ] 셀 병합 (첫 행)이 하나의 셀로 보임
- [ ] 이미지가 표시됨 (또는 이미지 영역이 보임)
- [ ] 페이지 여백이 적용됨
- [ ] Whale 스크린샷으로 확인

#### Details
- **Steps:**
  1. 표 + 병합 + 이미지 + 페이지 설정 포함 문서 생성
  2. Whale에서 열기
  3. 스크린샷 캡쳐
- **Storage:** docs/test_phase2_table_img_page.hwpx — WRITE (생성)

---

### e2e-phase2-014: 전수 검증 결과 Response

**Chain:** Response
**Status:** pending

#### What
모든 검증 결과를 정리.

#### Verification Criteria
- [ ] charPr: 굵기/크기/색상/취소선/장평 → 렌더링 확인 or 미렌더링 기록
- [ ] paraPr: 정렬/들여쓰기/줄간격 → 렌더링 확인 or 미렌더링 기록
- [ ] table: 표/병합 → 렌더링 확인 or 미렌더링 기록
- [ ] 미렌더링 항목은 "Whale 한계" vs "OWPML 구조 문제" 구분

#### Details
- **Success Status:** 모든 항목에 대해 렌더링 여부가 기록됨
- **Response Shape:** 검증 결과 테이블
- **UI Updates:** 스크린샷 기반 확인 기록

---

### e2e-phase2-015: 검증 실패 시 Error

**Chain:** Error
**Status:** pending

#### What
렌더링 실패 시 원인 분류와 대응.

#### Verification Criteria
- [ ] "Whale 뷰어 한계" (뷰어가 지원 안 하는 기능) → 기록만, 수정 불필요
- [ ] "OWPML 구조 문제" (XML이 불완전) → Phase 3에서 수정
- [ ] "버그" (코드 오류) → 이번 Phase에서 즉시 수정

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| Whale 미지원 | 기록 (한컴오피스에서 재확인 필요) | null (client) |
| XML 구조 불완전 | Phase 3 백로그 등록 | null (server) |
| 코드 버그 | 즉시 수정 + 재검증 | null (server) |

---

## Deviations

_No deviations recorded yet._
