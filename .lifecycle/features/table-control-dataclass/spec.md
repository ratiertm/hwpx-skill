---
feature: table-control-dataclass
title: Table/Control 전용 데이터클래스 확장
created: 2026-03-28
updated: 2026-03-28
status: draft
depends_on: [char-property-dataclass, namespace-2024-compat]
steps: 15
tags: [python-hwpx, dataclass, table, control, upstream-pr]
---

# E2E Spec: Table/Control 데이터클래스 확장

개발자가 python-hwpx로 HWPX 표를 열면 -> Table/Row/Cell이 전용 데이터클래스로 파싱 -> typed 필드로 접근 -> 저장 시 구조 보존

## Interaction 1: Table 데이터클래스 (body.py)

## e2e-table-control-dataclass-001: Table 하위 데이터클래스 정의

**Chain:** Screen
**Status:** pending

### What
body.py에 Table 전용 하위 데이터클래스를 정의한다.

### Verification Criteria
- [ ] TableRow 데이터클래스 존재 (cells 필드)
- [ ] TableCell 데이터클래스 존재 (col_addr, row_addr, col_span, row_span, width, height, paragraphs 필드)
- [ ] TableCellMargin 데이터클래스 존재 (left, right, top, bottom)
- [ ] TableInMargin 데이터클래스 존재 (left, right, top, bottom)
- [ ] Table 확장: row_cnt, col_cnt, page_break, repeat_header, cell_spacing, border_fill_id_ref 명시적 필드
- [ ] Table.rows: List[TableRow] 필드 추가
- [ ] 기존 children/attributes는 other_children/other_attributes로 유지

### Details
- **Element:** body.py 데이터클래스 정의 (line 108~112 영역 확장)
- **User Action:** `from hwpx.oxml.body import Table, TableRow, TableCell`
- **Initial State:** Table은 tag + attributes Dict + children List[GenericElement]

## e2e-table-control-dataclass-002: Table 파서 확장

**Chain:** Connection
**Status:** pending

### What
parse_table_element()를 확장하여 tr/tc 구조를 전용 데이터클래스로 파싱한다.

### Verification Criteria
- [ ] parse_table_row() 함수 존재 — tr 요소 → TableRow
- [ ] parse_table_cell() 함수 존재 — tc 요소 → TableCell
- [ ] parse_table_cell_margin() 함수 존재
- [ ] parse_table_in_margin() 함수 존재
- [ ] parse_table_element()가 위 파서들을 호출하여 typed Table 반환
- [ ] 미인식 자식 요소는 other_children에 fallback

### Details
- **Method:** parse_table_element(node) -> Table
- **Endpoint:** body.py line 222~227 확장
- **Request:** lxml Element (tbl 노드)
- **Auth:** None

## e2e-table-control-dataclass-003: Table 파싱 검증

**Chain:** Processing
**Status:** pending

### What
실제 HWPX 파일의 표가 전용 데이터클래스로 정확히 파싱되는지 검증.

### Verification Criteria
- [ ] Table.rows가 List[TableRow] 인스턴스
- [ ] TableRow.cells가 List[TableCell] 인스턴스
- [ ] TableCell.col_addr, row_addr가 int 타입
- [ ] TableCell.col_span, row_span이 int 타입 (기본값 1)
- [ ] Table.row_cnt, col_cnt가 int 타입

### Details
- **Steps:**
  1. 테스트용 Table XML 생성
  2. parse_table_element() 호출
  3. typed 필드 assert
- **Storage:** 테스트 XML -- READ

## e2e-table-control-dataclass-004: Table 접근성

**Chain:** Response
**Status:** pending

### What
파싱된 Table의 필드에 dot 표기법으로 접근 가능.

### Verification Criteria
- [ ] `table.rows[0].cells[0].col_addr` 접근 가능
- [ ] `table.row_cnt` 직접 접근 (기존: `table.attributes.get("rowCnt")`)
- [ ] `table.repeat_header` bool 접근 가능
- [ ] `cell.width`, `cell.height` int 접근 가능

### Details
- **Success Status:** IDE 자동완성으로 모든 필드 접근
- **Response Shape:** typed 필드
- **UI Updates:** 없음

## e2e-table-control-dataclass-005: Table 에러 처리

**Chain:** Error
**Status:** pending

### What
빈 테이블, 속성 누락 등 에지 케이스.

### Verification Criteria
- [ ] tr 없는 table → rows = [] (에러 아님)
- [ ] tc 없는 tr → cells = [] (에러 아님)
- [ ] cellAddr 누락 → col_addr=None, row_addr=None

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| tr 없는 table | rows=[] | OK |
| cellSpan 누락 | col_span=1, row_span=1 (기본값) | OK |
| 알 수 없는 자식 | other_children에 저장 | OK |

---

## Interaction 2: Control 최소 데이터클래스

## e2e-table-control-dataclass-006: Control 핵심 필드 확장

**Chain:** Screen
**Status:** pending

### What
Control 데이터클래스에 OWPML 핵심 속성을 명시적 필드로 추가한다. 20+ 하위 타입의 완전 분류는 향후 과제로 남기고, 공통 필드만 확장.

### Verification Criteria
- [ ] Control에 id, name, editable, dirty, zorder, field_id 명시적 필드
- [ ] control_type 기존 필드 유지
- [ ] other_attributes/other_children fallback 유지

### Details
- **Element:** body.py Control 클래스 (line 92~97)
- **User Action:** `ctrl.id`, `ctrl.name` 등 dot 접근
- **Initial State:** control_type만 추출, 나머지 generic

## e2e-table-control-dataclass-007: Control 파서 확장

**Chain:** Connection
**Status:** pending

### What
parse_control_element()가 핵심 속성을 명시적 필드로 추출.

### Verification Criteria
- [ ] id, name, editable, dirty, zorder, field_id 속성 추출
- [ ] 기존 control_type 추출 유지
- [ ] 미인식 속성은 other_attributes에 fallback

### Details
- **Method:** parse_control_element(node) -> Control
- **Endpoint:** body.py line 206~210 확장
- **Request:** lxml Element (ctrl 노드)
- **Auth:** None

## e2e-table-control-dataclass-008: Control 검증

**Chain:** Processing
**Status:** pending

### What
Control의 핵심 필드가 올바르게 파싱되는지 검증.

### Verification Criteria
- [ ] Control.id가 int 또는 str 타입
- [ ] Control.control_type이 str 타입
- [ ] Control.name이 Optional[str]

### Details
- **Steps:**
  1. 테스트용 ctrl XML 생성
  2. parse_control_element() 호출
  3. typed 필드 assert
- **Storage:** 테스트 XML -- READ

## e2e-table-control-dataclass-009: Control 접근성

**Chain:** Response
**Status:** pending

### What
파싱된 Control의 필드에 dot 표기법으로 접근 가능.

### Verification Criteria
- [ ] `ctrl.id` 접근 가능 (기존: `ctrl.attributes.get("id")`)
- [ ] `ctrl.control_type` 유지
- [ ] `ctrl.name` 접근 가능

### Details
- **Success Status:** IDE 자동완성
- **Response Shape:** typed 필드

## e2e-table-control-dataclass-010: Control 에러 처리

**Chain:** Error
**Status:** pending

### What
속성 누락 등 에지 케이스.

### Verification Criteria
- [ ] id 없는 ctrl → id=None
- [ ] type 없는 ctrl → control_type=None
- [ ] 알 수 없는 자식 → other_children

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| id 누락 | id=None | OK |
| 모든 속성 누락 | 기본값/None | OK |
| 알 수 없는 자식 | other_children에 저장 | OK |

---

## Interaction 3: 테스트 및 호환

## e2e-table-control-dataclass-011: __all__ 업데이트

**Chain:** Screen
**Status:** pending

### What
새 클래스와 파서 함수를 body.py __all__에 추가.

### Verification Criteria
- [ ] TableRow, TableCell, TableCellMargin, TableInMargin 추가
- [ ] parse_table_row, parse_table_cell 등 추가
- [ ] import 정상 동작

### Details
- **Element:** body.py __all__
- **User Action:** `from hwpx.oxml.body import TableRow, TableCell`
- **Initial State:** Table, Control만 export

## e2e-table-control-dataclass-012: 공식 테스트 통과

**Chain:** Connection
**Status:** pending

### What
기존 공식 테스트 전체 통과.

### Verification Criteria
- [ ] pytest tests/ (공식) 265/265 통과
- [ ] hwpx-skill 64/64 통과

### Details
- **Method:** pytest
- **Endpoint:** tests/
- **Request:** 전체 테스트 스위트
- **Auth:** None

## e2e-table-control-dataclass-013: 신규 테스트

**Chain:** Processing
**Status:** pending

### What
Table/Control 데이터클래스 전용 테스트.

### Verification Criteria
- [ ] test_table_parse_basic — 기본 테이블 파싱
- [ ] test_table_row_cells — 행/셀 구조 접근
- [ ] test_table_attributes — row_cnt, col_cnt, repeat_header 등
- [ ] test_table_empty — 빈 테이블 에지 케이스
- [ ] test_control_basic — 기본 Control 파싱
- [ ] test_control_attributes — id, name, editable 등
- [ ] test_stdlib_compat — stdlib ET 호환

### Details
- **Steps:**
  1. test_table_control.py 파일 생성
  2. 7+ 테스트 작성
- **Storage:** 테스트 XML fixtures -- READ

## e2e-table-control-dataclass-014: 하위 호환

**Chain:** Response
**Status:** pending

### What
기존 코드가 Table/Control을 사용하는 방식이 깨지지 않는다.

### Verification Criteria
- [ ] document.py의 HwpxOxmlTable이 정상 동작
- [ ] 기존 table.set_cell_text, table.merge_cells 등 정상
- [ ] 기존 Control 접근 코드 호환

### Details
- **Success Status:** 기존 API 100% 동작
- **Response Shape:** 기존과 동일

## e2e-table-control-dataclass-015: 호환 에러 처리

**Chain:** Error
**Status:** pending

### What
기존 코드가 새 필드와 충돌하지 않는다.

### Verification Criteria
- [ ] Table.children 접근하는 기존 코드 → other_children으로 리다이렉트 또는 호환 유지
- [ ] Control.attributes 접근하는 기존 코드 → other_attributes 호환
- [ ] slots=True 충돌 없음

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| 기존 코드가 Table.children 접근 | other_children fallback | OK |
| 기존 코드가 Control.attributes 접근 | other_attributes fallback | OK |
| HwpxOxmlTable 메서드들 | XML element 직접 조작이므로 무관 | OK |

## Deviations

_No deviations recorded yet._
