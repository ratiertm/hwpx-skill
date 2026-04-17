# Project State

## Current Phase
Phase 1: 테마 시스템 코어 — **All plans complete (2/2)**
Current Plan: 2 of 2 (DONE)

## Context
- 코드베이스 매핑 완료 (7개 문서, 1,555 lines)
- PROJECT.md, REQUIREMENTS.md, ROADMAP.md 생성 완료
- 기존 builder.py의 DS/TABLE_PRESETS/fontfaces 하드코딩 위치 파악 완료
- Plan 01 완료: Theme dataclass hierarchy + 10 built-in themes + test scaffold
- Plan 02 완료: Theme integration into HwpxBuilder, BlankFileMaker, api.py

## Key Decisions
- Oracle MCP 서버 유지 ($0/월)
- Overlay 방식 JSON 편집 채택 (전체 재구성 X)
- 테마 = 팔레트 + 폰트 + 사이즈 + 여백 통합 구조
- Palette 14 fields: DS dict 12개 + secondary/accent (design guide 4색 시스템)
- on_primary brightness heuristic: dark primary -> #f7f7ff, light -> #2b3437
- Cross-theme consistent values: on_surface, on_surface_var, outline_var, error
- Default theme uses _is_default_theme flag to skip font/color injection for backward compat
- Per-instance _table_presets_dict derived from theme palette, module-level constants untouched

## Last Session
- **Stopped at:** Completed 01-02-PLAN.md
- **Timestamp:** 2026-04-17T22:22:16Z

## Blockers
- 없음
