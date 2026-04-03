# Retrospective: namespace-2024-compat

**Feature:** OWPML 2024 네임스페이스 호환 지원
**Date:** 2026-03-28
**Mode:** feature
**Commit:** ratiertm/python-hwpx 75162c4

## What Went Well

- **기존 2016→2011 정규화 패턴이 완벽한 선례** — 동일 패턴에 7개 매핑만 추가. 코드 변경 최소
- **byte-level replace가 투명** — XML 파싱 전 처리이므로 기존 코드 변경 0. 가장 안전한 접근
- **13개 테스트가 모든 케이스 커버** — per-namespace, mixed, parsing, passthrough 전부 검증

## What Went Wrong

- 없음. 이상적으로 간단한 피처.

## Key Decisions

| 결정 | 이유 |
|------|------|
| 2024→2011 정규화 (2024 보존 아님) | 기존 코드 변경 없이 즉시 호환. 2024 저장은 향후 별도 기능 |
| version→app 매핑 | 2024 스키마의 "version"이 2011의 "app"에 해당 |
| _HWPML_2016_TO_2011 → _HWPML_NS_TO_2011 리네임 | 2024도 포함하므로 범용 이름으로 변경 |

## Metrics

- **변경량:** xml_utils.py +21, namespaces.py +15, document.py +5, test +90 (신규)
- **테스트:** 329/329 통과 (13개 신규)
- **Deviations:** 0

## Lessons for Next Phase

1. **2024 네임스페이스로 _저장_하는 기능은 별도 작업** — 현재는 읽기만 지원. 저장 시 2024로 변환하려면 역방향 매핑 + serialize 옵션 필요
2. **실제 2024 HWPX 파일로 테스트 필요** — 현재 테스트는 합성 XML. 한컴오피스가 2024 네임스페이스 파일을 생성하면 실제 파일로 검증 필요
