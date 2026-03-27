# Retrospective: hwpx-skill-v1

**Feature:** hwpx-skill-v1 — AI agent CLI for HWPX document generation
**Date:** 2026-03-27
**Mode:** feature (Stages 1→2→3→4→8)
**Commits:** 3 (7c51483, 58f3287, 8610dc0)

## What Went Well

- **python-hwpx 라이브러리가 안정적** — `HwpxDocument` API가 잘 설계되어 있어서 CLI 래핑이 수월했음
- **auto-save 버그 수정이 깔끔** — global 변수 + 헬퍼 함수 패턴으로 1개 파일만 수정, 10개 mutation 명령에 1줄씩 추가
- **convert 기능 구현이 빠름** — HTML/MD/TXT 파싱 → HWPX 변환이 50줄 이내로 완성
- **PDCA + dev-lifecycle 병행** — PDCA로 auto-save 버그를 먼저 수정하고, dev-lifecycle로 전체 feature를 관리

## What Went Wrong

- **DO Stage에서 일괄 처리한 것이 가장 큰 실수**
  - `sed`로 25개 스텝을 한꺼번에 `implemented`로 마킹
  - per-step 검증을 건너뛰고 "이미 구현되어 있다"고 판단
  - 테스트 코드 없이 수동 확인만으로 통과시킴
  - 사용자가 "UI 관련 코드나 테스트는 왜 없지?"로 발견

- **SPEC 코멘트를 나중에 추가**
  - DO Stage에서 구현하면서 바로 추가해야 하는데, redo 때 일괄 추가
  - 추적성(traceability)이 사후적으로 만들어짐

- **`--file` 에러 핸들링 버그를 테스트 작성 중 발견**
  - 존재하지 않는 파일에 대해 에러 없이 진행되는 문제
  - 테스트를 먼저 작성했다면 DO Stage에서 잡았을 것

## Surprises

- `HwpxDocument.open()`에 존재하지 않는 경로를 넣어도 에러 없이 새 문서를 반환함 — python-hwpx의 예상치 못한 동작
- HWPX `<hp:pic>` 이미지 삽입이 예상보다 복잡 — `shapeObject`, `shapeRect`, `imgRect`, `imgDim`, `img` 5개 하위 요소 필요
- CliRunner가 글로벌 상태를 공유하여 테스트 간 오염 발생

## Key Decisions

| 결정 | 이유 |
|------|------|
| Click Context 대신 global 변수 사용 | 기존 코드 패턴(`_json_output`, `_repl_mode`)과 일관성 |
| convert 명령을 CLI 서브커맨드로 추가 | 기존 CLI 구조에 자연스럽게 통합 |
| DO Stage redo | per-step 검증 누락을 사용자가 발견, 테스트 + SPEC 코멘트 추가 |

## Technical Debt

- [ ] HWPX 이미지 삽입 — `<hp:pic>` 규격 준수 코드가 아직 `hwpx_cli.py`에 통합 안 됨 (python-hwpx API 직접 사용 필요)
- [ ] Interaction 4 (LLM) — AI 에이전트 워크플로이므로 코드 없음, 하지만 SKILL.md 기반 자동화 테스트 가능
- [ ] CliRunner 글로벌 상태 오염 — 테스트에서 `_session = None` 리셋이 필요

## Lessons for Next Phase

1. **DO Stage에서 절대 일괄 마킹하지 말 것** — 각 스텝을 구현하고, 검증하고, 마킹하는 순서를 지킬 것
2. **테스트를 구현과 동시에 작성할 것** — 나중에 추가하면 버그를 놓침
3. **SPEC 코멘트를 구현 시점에 추가할 것** — 사후 추가는 추적성을 해침
4. **python-hwpx API의 예외 동작을 신뢰하지 말 것** — wrapper 레이어에서 검증 추가 필요
