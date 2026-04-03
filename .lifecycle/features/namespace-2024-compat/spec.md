---
feature: namespace-2024-compat
title: OWPML 2024 네임스페이스 호환 지원
created: 2026-03-28
updated: 2026-03-28
status: verified
depends_on: [char-property-dataclass]
steps: 10
tags: [python-hwpx, namespace, owpml-2024, upstream-pr]
---

# E2E Spec: OWPML 2024 네임스페이스 호환

개발자가 2024 네임스페이스(owpml.org) HWPX 파일을 열면 -> 2011로 자동 정규화 -> 기존 코드로 정상 처리 -> 저장 시 원본 네임스페이스 보존 옵션

## Interaction 1: 2024→2011 정규화 (읽기)

## e2e-namespace-2024-compat-001: 2024 네임스페이스 매핑 추가

**Chain:** Screen
**Status:** verified (attempt 1)

### What
xml_utils.py의 정규화 테이블에 2024→2011 매핑 7개를 추가한다.

### Verification Criteria
- [ ] `_HWPML_NS_TO_2011` (리네임)에 2024→2011 매핑 7개 존재
- [ ] owpml.org/owpml/2024/core → hancom.co.kr/hwpml/2011/core
- [ ] owpml.org/owpml/2024/head → hancom.co.kr/hwpml/2011/head
- [ ] owpml.org/owpml/2024/paragraph → hancom.co.kr/hwpml/2011/paragraph
- [ ] owpml.org/owpml/2024/section → hancom.co.kr/hwpml/2011/section
- [ ] owpml.org/owpml/2024/master-page → hancom.co.kr/hwpml/2011/master-page
- [ ] owpml.org/owpml/2024/history → hancom.co.kr/hwpml/2011/history
- [ ] owpml.org/owpml/2024/version → hancom.co.kr/hwpml/2011/app (또는 별도 매핑)

### Details
- **Element:** xml_utils.py line 14-22 확장
- **User Action:** 2024 네임스페이스 HWPX 파일을 open()
- **Initial State:** 2016→2011 매핑만 존재 (7개)

## e2e-namespace-2024-compat-002: normalize 함수 업데이트

**Chain:** Connection
**Status:** verified (attempt 1)

### What
normalize_hwpml_namespaces() 함수명/docstring을 2024 포함으로 업데이트.

### Verification Criteria
- [ ] 함수 docstring에 "2016 and 2024" 명시
- [ ] 변수명이 2016 전용이 아닌 범용으로 변경 (또는 기존 유지 + 주석)
- [ ] document.py의 namespace registration에 2024 방어 등록 추가

### Details
- **Method:** normalize_hwpml_namespaces(data: bytes) -> bytes
- **Endpoint:** xml_utils.py line 25-37
- **Request:** bytes (2024 네임스페이스 XML)
- **Auth:** None

## e2e-namespace-2024-compat-003: 2024 HWPX 파일 파싱 검증

**Chain:** Processing
**Status:** verified (attempt 1)

### What
2024 네임스페이스를 사용하는 테스트 XML이 정상 파싱된다.

### Verification Criteria
- [ ] 2024 네임스페이스 charPr XML → CharProperty 정상 파싱
- [ ] 2024 네임스페이스 paraPr XML → ParagraphProperty 정상 파싱
- [ ] header.xml 전체가 2024 네임스페이스일 때 정상 파싱

### Details
- **Steps:**
  1. 2024 네임스페이스 XML 테스트 데이터 생성
  2. parse_xml() 호출
  3. 정규화 후 2011 기반 코드가 정상 처리 확인
- **Storage:** 테스트 XML bytes -- READ

## e2e-namespace-2024-compat-004: 정규화 결과 확인

**Chain:** Response
**Status:** verified (attempt 1)

### What
정규화 후 모든 기존 API가 동일하게 동작한다.

### Verification Criteria
- [ ] 정규화된 XML에서 2024 URI가 완전히 제거됨
- [ ] 기존 코드의 `{_HH}charPr` 패턴이 정상 매칭
- [ ] ensure_run_style 등 모든 기존 API 정상 동작

### Details
- **Success Status:** 2024 입력 → 2011 내부 → 기존 코드 100% 동작
- **Response Shape:** 기존과 동일
- **UI Updates:** 없음 (투명한 변환)

## e2e-namespace-2024-compat-005: 정규화 에러 처리

**Chain:** Error
**Status:** verified (attempt 1)

### What
잘못된 네임스페이스, 혼합 네임스페이스 처리.

### Verification Criteria
- [ ] 2011/2024 혼합 문서 → 정상 처리 (각각 정규화)
- [ ] 알 수 없는 네임스페이스 → 그대로 유지 (에러 아님)
- [ ] 네임스페이스 없는 요소 → 기존 동작 유지

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| 2011/2024 혼합 | 2024만 정규화, 2011은 그대로 | OK |
| 알 수 없는 네임스페이스 | 무시 (passthrough) | OK |
| 네임스페이스 없음 | 기존 동작 유지 | OK |

---

## Interaction 2: 테스트 및 하위호환

## e2e-namespace-2024-compat-006: 공식 테스트 통과

**Chain:** Screen
**Status:** verified (attempt 1)

### What
기존 공식 테스트 253개가 모두 통과한다.

### Verification Criteria
- [ ] pytest tests/ (공식) 253/253 통과
- [ ] hwpx-skill 64/64 통과
- [ ] CharProperty 15/15 통과

### Details
- **Element:** 전체 테스트 스위트
- **User Action:** pytest 실행
- **Initial State:** 317/317 통과 (변경 전)

## e2e-namespace-2024-compat-007: 2024 전용 테스트

**Chain:** Connection
**Status:** verified (attempt 1)

### What
2024 네임스페이스 정규화를 검증하는 신규 테스트.

### Verification Criteria
- [ ] test_namespace_2024_normalization() — 2024 XML bytes → 정규화 → 2011 URI로 변환 확인
- [ ] test_namespace_2024_charpr_parsing() — 2024 charPr → CharProperty 파싱 정상
- [ ] test_namespace_mixed_2011_2024() — 혼합 문서 정상 처리
- [ ] test_namespace_2016_still_works() — 기존 2016 정규화 유지 확인

### Details
- **Method:** pytest
- **Endpoint:** tests/test_namespace_compat.py
- **Request:** 각종 네임스페이스 XML 테스트 데이터
- **Auth:** None

## e2e-namespace-2024-compat-008: namespaces.py 2024 상수 추가

**Chain:** Processing
**Status:** verified (attempt 1)

### What
namespaces.py에 2024 네임스페이스 URI 상수를 추가한다 (문서화 및 향후 참조용).

### Verification Criteria
- [ ] OWPML_2024_CORE, OWPML_2024_HEAD 등 7개 상수 존재
- [ ] 기존 2011 상수와 공존

### Details
- **Steps:**
  1. namespaces.py에 2024 상수 블록 추가
  2. docstring에 2011/2016/2024 관계 설명
- **Storage:** namespaces.py -- WRITE

## e2e-namespace-2024-compat-009: document.py 방어 등록

**Chain:** Response
**Status:** verified (attempt 1)

### What
document.py의 ET.register_namespace에 2024 방어 등록을 추가한다.

### Verification Criteria
- [ ] 2024 네임스페이스에 대한 prefix 등록 (hp24, hs24, hh24, hc24 등)
- [ ] 기존 2016 등록과 동일 패턴

### Details
- **Success Status:** 2024 문서 저장 시 네임스페이스 prefix 유지
- **Response Shape:** ET.register_namespace 호출
- **UI Updates:** 없음

## e2e-namespace-2024-compat-010: __all__ 업데이트

**Chain:** Error
**Status:** verified (attempt 1)

### What
새 상수와 함수가 export 목록에 추가된다.

### Verification Criteria
- [ ] namespaces.py __all__에 2024 상수 추가
- [ ] from hwpx.oxml.namespaces import OWPML_2024_HEAD 정상 동작

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| 기존 import 유지 | 2011 상수 변경 없음 | OK |
| 새 import 가능 | 2024 상수 접근 가능 | OK |
| 순환 import | 없음 (namespaces.py는 독립) | OK |

## Deviations

_No deviations recorded yet._
