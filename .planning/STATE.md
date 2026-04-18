---
gsd_state_version: 1.0
milestone: v0.5
milestone_name: milestone
current_plan: 1 of 1 (02.1-01 complete) -- PHASE COMPLETE
status: complete
stopped_at: Completed 02.1-01-PLAN.md (Phase 2.1 complete)
last_updated: "2026-04-18T06:47:09Z"
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 6
  completed_plans: 6
---

# Project State

## Current Phase

Phase 2.1: hwp2hwpx 양식 표 변환 개선
Current Plan: 1 of 1 (02.1-01 complete) -- PHASE COMPLETE

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
- BinData: Skip corrupt streams entirely (no empty bytes) -- Whale handles missing BinData gracefully
- Overlay: regex-based multi-hp:t replacement instead of ET serialization (avoids namespace rewriting)
- Overlay: cell text join '' not ' ' for matching accuracy
- Overlay: zipfile direct manipulation replaces subprocess unpack/repack
- Nested table XPath: direct-child traversal (tc->subList->p->run->tbl) instead of .//{_HP}tbl
- Level filtering in _build_cell_paragraph: skip records at level != para_level+1 to prevent nested table cell data overwriting parent
- Centralized _decode_hwp_text_chars for UTF-16 surrogate pair handling across all text parsing locations

## Last Session

- **Stopped at:** Completed 02.1-01-PLAN.md (Phase 2.1 complete)
- **Timestamp:** 2026-04-18T06:47:09Z

## Blockers

- 없음
