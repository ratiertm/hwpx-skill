---
gsd_state_version: 1.0
milestone: v0.5
milestone_name: milestone
current_plan: Phase 4 next
---

# Project State

## Current Phase
Phase 4: 정비 + 릴리스 — **Not started**

## Completed Phases
- Phase 1: 테마 시스템 코어 ✅
- Phase 2: JSON Overlay + BinData ✅
- Phase 2.1: hwp2hwpx 양식 표 + 이모지 ✅
- Phase 2.2: BinData 이미지 복구 ✅
- Phase 2.3: 폰트 파이프라인 정비 ✅
- Phase 3: 동적 테마 추출 ✅

## PyPI Status
- **현재 배포**: 0.6.0 (2026-04-18)

## 남은 TODO

### Phase 4 — 정비 + 릴리스
- README.md + design_guide.md 동기화
- SKILL.md 업데이트 (테마 추출, 폰트 파이프라인 반영)
- SKILL.md claude.ai 재업로드
- Oracle MCP 서버 업데이트
- PyPI 0.7.0 배포

## 미해결 이슈
- overlay 40-run 셀 비례 분배 가끔 부정확
- linesegarray 불일치 → rhwp 프리뷰 뭉침 (Whale 정상)

## Key Decisions
- Overlay 방식 (JSON 전체 재구성 X)
- heading textColor = primary
- body 기본 12pt
- 체크박스 4패턴 (□/☐/[  ]/[ ])
- Oracle MCP 유지 ($0/월)

## Last Session
- **Timestamp**: 2026-04-18T15:30:00Z
