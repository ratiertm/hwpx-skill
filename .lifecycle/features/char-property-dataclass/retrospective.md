# Retrospective: char-property-dataclass

**Feature:** CharProperty 데이터클래스 확장 (공식 아키텍처 패턴)
**Date:** 2026-03-28
**Mode:** feature
**Commit:** ratiertm/python-hwpx 0bcd72e

## What Went Well

- **ParagraphProperty 패턴 참조가 효과적** — 7개 하위 클래스 + 7개 parse_* 패턴이 이미 있어서, CharProperty도 같은 구조로 9개 하위 클래스 + 9개 parse_*/serialize_* 를 빠르게 작성
- **_compat_local_name이 stdlib/lxml 호환 문제를 예방** — `_append_child` 교훈을 적용하여, parser에도 `_compat_local_name` 추가. 첫 시도에서 stdlib ET 오류 발생 → 즉시 수정
- **parse→modify→serialize 패턴이 깔끔** — ensure_run_style의 modifier가 XML 직접 조작 (~100줄)에서 데이터클래스 수정 (~70줄)으로 변경. 가독성과 유지보수성 향상
- **전체 테스트 317개 통과** — 공식 253 + hwpx-skill 64 전부 통과. 하위 호환 완전 유지
- **_CHAR_CHILD_PARSERS Dict 패턴** — if/elif 체인 대신 Dict 기반 디스패치로 파서 확장이 쉬움

## What Went Wrong

- **stdlib ET 호환을 처음에 놓침** — `local_name(child)` (lxml 전용)를 parse_char_property에서 사용하여 ensure_run_style 테스트 실패. `_compat_local_name` 추가로 수정. 교훈: header.py의 함수도 document.py에서 호출될 수 있음
- **GenericElement 생성 시 stdlib 호환** — `parse_generic_element`가 lxml 전용이라 fallback try/except 추가 필요

## Key Decisions

| 결정 | 이유 |
|------|------|
| `_compat_local_name` 추가 (lxml `local_name` 대신) | document.py에서 호출 시 stdlib ET element 전달 가능. 양쪽 호환 필수 |
| `_CHAR_CHILD_PARSERS` Dict 기반 디스패치 | if/elif 체인 대비 확장 용이, 새 요소 추가 시 Dict에 한 줄 추가 |
| `_char_make_child` (header.py 전용) | document.py의 `_append_child` import 시 순환참조 위험. 동일 패턴의 독립 함수 |
| predicate는 XML 직접 비교 유지 | predicate를 데이터클래스로 전환하면 매번 parse 비용 발생. modifier만 dataclass화 |
| `other_attributes` + `other_children` 필드 유지 | 미지원 요소/속성이 라운드트립 시 손실되지 않도록 fallback Dict 보존 |

## Metrics

- **변경량:** header.py +473줄, document.py +54/-88줄, test_char_property.py +271줄 (신규)
- **테스트:** 317/317 통과 (15개 신규)
- **Spec steps:** 15/15 verified (attempt 1)
- **Deviations:** 0
- **Rework:** 1회 (stdlib ET compat fix)

## Lessons for Next Phase

1. **header.py 함수는 반드시 stdlib/lxml 양쪽 호환으로 작성** — `local_name` 대신 `_compat_local_name` 사용. document.py에서 호출되는 모든 함수에 적용
2. **Dict 디스패치 패턴을 serialize에도 확장 가능** — `_CHAR_SERIALIZE_MAP`으로 직렬화도 같은 패턴 적용 가능
3. **predicate 최적화는 별도 이슈** — 현재 predicate는 XML 직접 비교, 향후 필요시 dataclass 기반으로 전환 가능하지만 성능 trade-off 고려 필요
4. **Phase B (ensure_run_style 완전 재작성) 시 predicate도 dataclass화 검토** — 현재 modifier만 전환. predicate는 간단한 비교만 하므로 XML 직접 비교가 더 빠름
5. **네임스페이스 2024 작업 시 `_HH_NS` 상수를 config로 분리 필요** — 현재 하드코딩된 2011 네임스페이스
