---
gsd_state_version: 1.0
milestone: v0.5
milestone_name: milestone
current_plan: Phase 2.2 next
---

# Project State

## Current Phase
Phase 2.2: BinData 이미지 복구 — **Not started**

## Completed Phases
- Phase 1: 테마 시스템 코어 ✅
- Phase 2: JSON Overlay + BinData ✅
- Phase 2.1: hwp2hwpx 양식 표 + 이모지 ✅

## PyPI Status
- **현재 배포**: 0.6.0 (2026-04-18)

## 남은 TODO (순서대로)

### TODO 1: Phase 2.2 — BinData 이미지 복구
- **파일**: `hwp2hwpx.py` `_decompress()` line 419-425
- **문제**: ibgopongdang BIN0001~0004.png zlib 실패 → 이미지 스킵
- **시도**: raw passthrough, deflate window size 변형
- **테스트**: 변환 후 Whale에서 이미지 표시

### TODO 2: Phase 2.3 — 폰트 파이프라인
- NanumGothic TTF vendor/ 번들
- embed_fonts=True 기본값
- font_map 번들 폰트 고정
- `python -m pyhwpxlib font-check` CLI
- SKILL.md Rule 25 (폰트 민감하지 않은 레이아웃)

### TODO 3: Phase 3 — 동적 테마 추출
- `extract_theme(hwpx_path)` → 테마 JSON
- 테마 저장/로드 (`~/.pyhwpxlib/themes/`)
- `HwpxBuilder(theme='custom/my-form')`
- MCP 서버 `hwpx_extract_theme` 도구

### TODO 4: Phase 4 — 정비 + 릴리스
- README.md + design_guide.md 동기화
- Oracle MCP 서버 업데이트
- SKILL.md claude.ai 재업로드
- PyPI 최종 배포

## 미해결 이슈
- overlay 40-run 셀 비례 분배 가끔 부정확
- linesegarray 불일치 → rhwp 프리뷰 뭉침 (Whale 정상)
- Linux 한글 폰트 fallback 개선 필요 (Phase 2.3)

## Key Decisions
- Overlay 방식 (JSON 전체 재구성 X)
- heading textColor = primary
- body 기본 12pt
- 체크박스 4패턴 (□/☐/[  ]/[ ])
- Oracle MCP 유지 ($0/월)

## Last Session
- **Timestamp**: 2026-04-18T15:30:00Z
