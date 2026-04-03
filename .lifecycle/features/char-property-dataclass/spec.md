---
feature: char-property-dataclass
title: CharProperty 데이터클래스 확장 (공식 아키텍처 패턴)
created: 2026-03-28
updated: 2026-03-28
status: verified
depends_on: [api-style-align]
steps: 15
tags: [python-hwpx, dataclass, upstream-pr, owpml]
---

# E2E Spec: CharProperty 데이터클래스 확장

개발자가 python-hwpx로 HWPX 파일을 열면 -> charPr XML이 전용 데이터클래스로 파싱됨 -> ensure_run_style이 데이터클래스를 통해 XML 생성 -> 저장 후 재오픈 시 동일 데이터 보존

## Interaction 1: charPr XML 파싱 → 전용 데이터클래스

## e2e-char-property-dataclass-001: CharProperty 데이터클래스 정의

**Chain:** Screen
**Status:** verified (attempt 1)

### What
header.py에 CharProperty 전용 하위 데이터클래스 10개를 정의한다. ParagraphProperty가 ParagraphAlignment, ParagraphMargin 등 7개 하위 클래스를 갖는 것과 동일한 패턴.

### Verification Criteria
- [ ] CharFontRef 데이터클래스 존재 (hangul, latin, hanja, japanese, other, symbol, user 필드)
- [ ] CharSpacing 데이터클래스 존재 (7개 언어별 필드)
- [ ] CharRatio 데이터클래스 존재 (7개 언어별 필드)
- [ ] CharRelSize 데이터클래스 존재 (7개 언어별 필드)
- [ ] CharOffset 데이터클래스 존재 (7개 언어별 필드)
- [ ] CharUnderline 데이터클래스 존재 (type, shape, color 필드)
- [ ] CharStrikeout 데이터클래스 존재 (shape, color 필드)
- [ ] CharOutline 데이터클래스 존재 (type 필드)
- [ ] CharShadow 데이터클래스 존재 (type, color, offset_x, offset_y 필드)
- [ ] CharProperty에 height, text_color, shade_color, use_font_space, use_kerning, sym_mark, border_fill_id_ref 명시적 필드 추가
- [ ] CharProperty에 bold, italic, emboss, engrave, supscript, subscript Optional[bool] 필드 추가
- [ ] CharProperty에 font_ref, spacing, ratio, rel_size, offset, underline, strikeout, outline, shadow Optional 필드 추가
- [ ] 기존 attributes/child_attributes/child_elements Dict 필드를 other_attributes/other_children으로 유지 (미지원 요소 fallback)

### Details
- **Element:** header.py 데이터클래스 정의 (line 122~141 영역 확장)
- **User Action:** 개발자가 `from hwpx.oxml.header import CharProperty, CharFontRef, CharSpacing` 등으로 임포트
- **Initial State:** CharProperty는 id + 3개 Dict 필드만 있는 generic 구조

## e2e-char-property-dataclass-002: parse_char_property 파서 확장

**Chain:** Connection
**Status:** verified (attempt 1)

### What
parse_char_property()를 확장하여 charPr XML의 각 자식 요소를 전용 데이터클래스로 파싱한다. ParagraphProperty의 parse_paragraph_alignment, parse_paragraph_margin 등과 동일 패턴.

### Verification Criteria
- [ ] parse_char_font_ref() 함수 존재 — fontRef 요소 → CharFontRef
- [ ] parse_char_spacing() 함수 존재 — spacing 요소 → CharSpacing
- [ ] parse_char_ratio() 함수 존재 — ratio 요소 → CharRatio
- [ ] parse_char_rel_size() 함수 존재 — relSz 요소 → CharRelSize
- [ ] parse_char_offset() 함수 존재 — offset 요소 → CharOffset
- [ ] parse_char_underline() 함수 존재 — underline 요소 → CharUnderline
- [ ] parse_char_strikeout() 함수 존재 — strikeout 요소 → CharStrikeout
- [ ] parse_char_outline() 함수 존재 — outline 요소 → CharOutline
- [ ] parse_char_shadow() 함수 존재 — shadow 요소 → CharShadow
- [ ] parse_char_property()가 위 파서들을 호출하여 CharProperty 필드를 채움
- [ ] 미인식 자식 요소는 other_children Dict로 fallback

### Details
- **Method:** parse_char_property(node: etree._Element) -> CharProperty
- **Endpoint:** header.py line 851~867 확장
- **Request:** lxml Element (charPr 노드)
- **Auth:** None (internal parser)

## e2e-char-property-dataclass-003: 기존 HWPX 파일 파싱 검증

**Chain:** Processing
**Status:** verified (attempt 1)

### What
실제 HWPX 파일을 열었을 때 charPr 요소들이 전용 데이터클래스로 정확히 파싱되는지 검증한다.

### Verification Criteria
- [ ] HwpxDocument.open() → header.char_properties에 CharProperty 리스트 존재
- [ ] CharProperty.font_ref가 CharFontRef 인스턴스 (None이 아닌 경우)
- [ ] CharProperty.height가 int 타입 (기존 attributes["height"] 대신)
- [ ] CharProperty.text_color가 str 타입 (#RRGGBB)
- [ ] bold/italic 등 boolean 플래그가 올바르게 파싱됨

### Details
- **Steps:**
  1. 테스트용 HWPX 파일 로드 (tests/fixtures/ 내 기존 파일)
  2. header.char_properties.properties[0] 접근
  3. 각 필드가 올바른 타입과 값인지 assert
- **Storage:** HWPX ZIP 내 header.xml -- READ

## e2e-char-property-dataclass-004: 파싱 결과 접근성

**Chain:** Response
**Status:** verified (attempt 1)

### What
파싱된 CharProperty 데이터클래스의 필드에 IDE 자동완성으로 접근할 수 있다.

### Verification Criteria
- [ ] `char_prop.font_ref.hangul` 같은 점 표기법으로 접근 가능
- [ ] `char_prop.height` 직접 접근 가능 (기존: `char_prop.attributes.get("height")`)
- [ ] `char_prop.underline.type` 접근 가능 (기존: `char_prop.child_attributes.get("underline", {}).get("type")`)
- [ ] mypy/pyright 타입 체크 통과

### Details
- **Success Status:** 모든 필드가 typing annotation과 일치
- **Response Shape:** CharProperty 인스턴스의 각 필드가 Optional[SubClass] 또는 primitive
- **UI Updates:**
  - IDE에서 CharProperty. 입력 시 font_ref, height, text_color 등 자동완성 표시
  - 기존 attributes Dict 접근 코드 없이도 동작

## e2e-char-property-dataclass-005: 파싱 에러 처리

**Chain:** Error
**Status:** verified (attempt 1)

### What
잘못된 charPr XML이나 누락된 필수 요소 처리.

### Verification Criteria
- [ ] fontRef 없는 charPr → CharProperty.font_ref = None (에러 아님)
- [ ] 알 수 없는 자식 요소 → other_children에 GenericElement로 저장
- [ ] 잘못된 속성값 (height="abc") → parse_int가 None 반환, 에러 미발생

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| fontRef 자식 없음 | font_ref=None, 나머지 정상 파싱 | OK |
| 알 수 없는 자식 요소 (예: customTag) | other_children에 저장 | OK |
| 속성값 타입 오류 | parse_int/parse_bool이 None 반환 | OK |

---

## Interaction 2: ensure_run_style 데이터클래스 기반 재작성

## e2e-char-property-dataclass-006: CharProperty → XML 직렬화

**Chain:** Screen
**Status:** verified (attempt 1)

### What
CharProperty 데이터클래스를 charPr XML 요소로 직렬화하는 함수를 구현한다.

### Verification Criteria
- [ ] serialize_char_property(prop: CharProperty) -> etree._Element 함수 존재
- [ ] serialize_char_font_ref(ref: CharFontRef) -> etree._Element 존재
- [ ] serialize_char_underline, serialize_char_strikeout 등 하위 직렬화 함수 존재
- [ ] bold/italic은 존재 여부가 True → 빈 요소 `<hh:bold/>` 생성
- [ ] height, textColor 등은 charPr 속성으로 직렬화
- [ ] _append_child 패턴 사용 (LET.SubElement 직접 사용 금지)

### Details
- **Element:** header.py에 serialize_* 함수 추가
- **User Action:** 내부적으로 ensure_run_style에서 호출
- **Initial State:** 현재는 document.py에서 XML 직접 조작

## e2e-char-property-dataclass-007: ensure_run_style 데이터클래스 연동

**Chain:** Connection
**Status:** verified (attempt 1)

### What
document.py의 ensure_run_style이 CharProperty 데이터클래스를 통해 동작하도록 재작성한다.

### Verification Criteria
- [ ] ensure_run_style의 predicate가 CharProperty 필드를 비교 (XML attribute 직접 비교 아님)
- [ ] ensure_run_style의 modifier가 serialize_char_property()를 통해 XML 생성
- [ ] 기존 40+ 파라미터 시그니처 유지 (하위 호환)
- [ ] ensure_char_property()가 CharProperty 데이터클래스 기반으로 동작

### Details
- **Method:** ensure_run_style(bold, italic, ...) → CharProperty 생성/수정 → XML 직렬화
- **Endpoint:** document.py ensure_run_style / ensure_char_property
- **Request:** 기존과 동일한 파라미터
- **Auth:** None

## e2e-char-property-dataclass-008: 기능 동작 검증

**Chain:** Processing
**Status:** verified (attempt 1)

### What
ensure_run_style로 설정한 스타일이 HWPX 파일에 올바르게 저장되고, 다시 열었을 때 동일한 CharProperty로 파싱된다.

### Verification Criteria
- [ ] ensure_run_style(bold=True) → charPr에 `<hh:bold/>` 요소 생성
- [ ] ensure_run_style(height=2000) → charPr에 height="2000" 속성
- [ ] ensure_run_style(text_color="#FF0000") → charPr에 textColor="#FF0000"
- [ ] ensure_run_style(font_hangul=1) → charPr에 `<hh:fontRef hangul="1" .../>` 요소
- [ ] ensure_run_style(underline_type="BOTTOM") → charPr에 `<hh:underline type="BOTTOM" .../>` 요소

### Details
- **Steps:**
  1. 새 문서 생성 또는 기존 문서 열기
  2. ensure_run_style() 호출로 속성 설정
  3. 저장
  4. 다시 열어서 CharProperty 필드 확인
- **Storage:** HWPX ZIP 내 header.xml -- READ+WRITE

## e2e-char-property-dataclass-009: 기존 API 호환

**Chain:** Response
**Status:** verified (attempt 1)

### What
기존 ensure_run_style API를 사용하는 코드가 변경 없이 동작한다.

### Verification Criteria
- [ ] 기존 테스트 238개 (공식) 전부 통과
- [ ] 기존 테스트 64개 (hwpx-skill) 전부 통과
- [ ] ensure_run_style(bold=True, italic=True, underline=True) — 공식 3파라미터 호출 정상
- [ ] ensure_run_style 60+ 파라미터 호출 정상

### Details
- **Success Status:** 전체 테스트 통과 (302개)
- **Response Shape:** 기존과 동일한 반환값
- **UI Updates:**
  - 한컴오피스/Whale에서 동일한 렌더링 결과

## e2e-char-property-dataclass-010: ensure_run_style 에러 처리

**Chain:** Error
**Status:** verified (attempt 1)

### What
잘못된 파라미터, charPr 없는 문서 등의 에러 처리.

### Verification Criteria
- [ ] height=0 또는 음수 → ValueError 또는 기본값 사용 (1000)
- [ ] 잘못된 underline_type → ValueError
- [ ] charPr가 없는 문서에서 ensure_run_style → 새 charPr 생성

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| height=0 (범위 밖) | ValueError 또는 기본값 1000 | 400 |
| underline_type="INVALID" | ValueError: Invalid underline type | 400 |
| charPr 없는 문서 | 새 CharProperty 생성하여 추가 | OK |

---

## Interaction 3: 라운드트립 보존 및 공식 테스트

## e2e-char-property-dataclass-011: 라운드트립 테스트

**Chain:** Screen
**Status:** verified (attempt 1)

### What
HWPX 파일을 열고 저장했을 때 charPr 데이터가 손실 없이 보존된다.

### Verification Criteria
- [ ] 열기 → 저장 → 재열기 시 CharProperty 필드 값이 동일
- [ ] fontRef의 7개 언어별 값 보존
- [ ] underline, strikeout 등 선택적 요소 보존
- [ ] other_children에 저장된 미지원 요소도 보존

### Details
- **Element:** 테스트 파일 (fixture HWPX)
- **User Action:** open → save → reopen → assert equal
- **Initial State:** 다양한 charPr 조합이 포함된 테스트 파일

## e2e-char-property-dataclass-012: XML 직렬화 정합성

**Chain:** Connection
**Status:** verified (attempt 1)

### What
serialize_char_property()가 생성한 XML이 OWPML 스키마와 일치한다.

### Verification Criteria
- [ ] 자식 요소 순서: fontRef → ratio → spacing → relSz → offset → italic → bold → underline → strikeout → outline → shadow → emboss → engrave → supscript → subscript
- [ ] 네임스페이스: `hh:` 접두사 (2011 기준)
- [ ] 빈 요소 (bold, italic 등)는 self-closing tag

### Details
- **Method:** XML 요소 순서가 스키마 sequence와 일치하는지 검증
- **Endpoint:** serialize_char_property()
- **Request:** CharProperty 인스턴스
- **Auth:** None

## e2e-char-property-dataclass-013: 공식 테스트 통과

**Chain:** Processing
**Status:** verified (attempt 1)

### What
공식 python-hwpx 테스트 238개가 모두 통과한다.

### Verification Criteria
- [ ] `pytest tests/` (공식 테스트) 238/238 통과
- [ ] 기존 hwpx-skill 테스트 64/64 통과
- [ ] 새 CharProperty 테스트 10+개 추가 및 통과

### Details
- **Steps:**
  1. `cd ratiertm-hwpx && pytest tests/` 실행
  2. `cd hwpx/agent-harness && pytest tests/` 실행
  3. 새 테스트 `tests/test_char_property.py` 실행
- **Storage:** test fixture HWPX 파일 -- READ

## e2e-char-property-dataclass-014: __all__ 및 임포트 업데이트

**Chain:** Response
**Status:** verified (attempt 1)

### What
새 데이터클래스와 파서 함수가 모듈 __all__에 등록되고 임포트 가능하다.

### Verification Criteria
- [ ] header.py __all__에 CharFontRef, CharSpacing, CharRatio 등 9개 클래스 추가
- [ ] header.py __all__에 parse_char_font_ref 등 9개 파서 함수 추가
- [ ] header.py __all__에 serialize_char_property 등 직렬화 함수 추가
- [ ] `from hwpx.oxml.header import CharFontRef` 정상 동작

### Details
- **Success Status:** 모든 새 심볼이 임포트 가능
- **Response Shape:** 기존 __all__ 리스트에 추가
- **UI Updates:**
  - IDE에서 hwpx.oxml.header 임포트 시 새 클래스 자동완성

## e2e-char-property-dataclass-015: 호환성 에러 처리

**Chain:** Error
**Status:** verified (attempt 1)

### What
데이터클래스 변경이 기존 코드를 깨뜨리지 않는지 확인.

### Verification Criteria
- [ ] CharProperty.attributes 접근하는 기존 코드 → other_attributes로 마이그레이션 또는 호환 프로퍼티 제공
- [ ] child_attributes 접근하는 기존 코드 → 호환 유지
- [ ] child_elements 접근하는 기존 코드 → 호환 유지

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| 기존 코드가 CharProperty.attributes 접근 | DeprecationWarning + 동작 유지 또는 other_attributes 리다이렉트 | OK |
| 기존 코드가 child_attributes["fontRef"] 접근 | 호환 Dict 반환 또는 font_ref 필드로 안내 | OK |
| slots=True와 새 필드 충돌 | dataclass 정의에 모든 필드 명시 | OK |

## Deviations

_No deviations recorded yet._
