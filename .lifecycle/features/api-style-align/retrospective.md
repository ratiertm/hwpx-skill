# Retrospective: api-style-align

**Feature:** API Style Alignment for Upstream PR
**Date:** 2026-03-28
**Mode:** feature
**Commit:** ratiertm/python-hwpx 37c698c

## What Went Well

- **_append_child가 근본 해결책** — `LET.SubElement` vs `ET.SubElement` 문제를 `parent.makeelement()` 기반의 `_append_child`로 통일. stdlib ET도 lxml도 모두 동작
- **공식 테스트 238개 전부 통과** — 이전에 3개 실패하던 것이 0개로. 하위 호환 완전 유지
- **명시적 시그니처가 IDE 지원 향상** — `**kwargs`에서 60+ 명시적 파라미터로 변경하여 자동완성, type check 가능
- **공식 API 분석이 방향을 잡아줌** — WebFetch로 API 레퍼런스를 확인하여 중복 구현, 네이밍 차이를 사전에 파악

## What Went Wrong

- **처음에 `LET.SubElement`로 수정했다가 공식 테스트에서 실패** — stdlib ET element를 받는 경로를 고려 안 함. `_append_child`로 다시 수정
- **ensure_para_style의 modifier 내부도 같은 문제** — charPr만 고치고 paraPr을 빠뜨릴 뻔했지만 sed로 일괄 변경하여 해결

## Key Decisions

| 결정 | 이유 |
|------|------|
| `**kwargs` → 명시적 파라미터 | IDE 자동완성 + type safety + docstring 일관성 |
| `LET.SubElement` → `_append_child` | stdlib/lxml 양쪽 호환. 공식 코드의 기존 패턴 |
| docstring을 Args/Returns/Raises로 | 공식 python-hwpx와 동일 스타일 |

## Lessons for Next Phase

1. **`_append_child`를 기본으로 사용** — 새 코드에서 `ET.SubElement`나 `LET.SubElement` 직접 사용 금지
2. **공식 테스트를 매번 실행** — 우리 테스트만 통과해서는 안 됨
3. **명시적 시그니처 > kwargs** — 파라미터가 많아도 명시적이 낫다
