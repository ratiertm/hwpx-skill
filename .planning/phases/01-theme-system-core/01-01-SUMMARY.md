---
phase: 01-theme-system-core
plan: 01
subsystem: theming
tags: [dataclass, color-palette, frozen, table-presets]

requires:
  - phase: none
    provides: standalone data layer
provides:
  - "Theme/Palette/FontSet/SizeSet/Margins frozen dataclasses"
  - "BUILTIN_THEMES dict with 10 themes"
  - "_make_table_presets(palette) function"
  - "Test scaffold for TS-1 and TS-2"
affects: [01-02-PLAN, builder-integration]

tech-stack:
  added: []
  patterns: [frozen-dataclass-hierarchy, palette-derived-presets]

key-files:
  created:
    - pyhwpxlib/themes.py
    - tests/test_themes.py
  modified: []

key-decisions:
  - "Palette has 14 fields (12 from DS dict + secondary + accent from design guide)"
  - "on_primary determined by primary brightness: dark primary -> #f7f7ff, light primary -> #2b3437"
  - "Consistent cross-theme values: on_surface=#2b3437, on_surface_var=#586064, outline_var=#abb3b7, error=#9f403d"

patterns-established:
  - "Frozen dataclass tree: Theme -> Palette/FontSet/SizeSet/Margins"
  - "_make_table_presets(palette) derives presets from any palette, academic always has empty strings"

requirements-completed: [TS-1]

duration: 3min
completed: 2026-04-15
---

# Phase 1 Plan 01: Theme Dataclass Hierarchy Summary

**Frozen dataclass hierarchy (Theme/Palette/FontSet/SizeSet/Margins) with 10 built-in palettes and palette-derived TABLE_PRESETS**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-17T22:09:32Z
- **Completed:** 2026-04-17T22:12:10Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- Frozen dataclass hierarchy with Palette (14 color fields), FontSet (6 font slots), SizeSet (6 sizes), Margins (6 dims), Theme (orchestrator)
- 10 built-in themes with fully expanded palettes derived from design_guide.md base colors
- Default theme palette is byte-for-byte identical to existing DS dict in builder.py
- _make_table_presets(palette) produces same shape as existing TABLE_PRESETS, with academic always using empty strings
- Test scaffold: 11 passing tests (TS-1), 7 skipped placeholders (TS-2, Plan 02/03)

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `6694a62` (test)
2. **Task 1 GREEN: Theme implementation** - `3514806` (feat)

_TDD task: test-first then implementation_

## Files Created/Modified
- `pyhwpxlib/themes.py` - Theme dataclass hierarchy, 10 built-in themes, _make_table_presets()
- `tests/test_themes.py` - 11 tests for TS-1, 7 placeholders for TS-2

## Decisions Made
- Palette has 14 fields total: 12 matching DS dict keys + `secondary` and `accent` from design guide's 4-base-color system
- `on_primary` uses brightness heuristic: dark primaries (Forest, Ocean, Berry, etc.) get `#f7f7ff`, light primaries (Coral Energy, Sage Calm) get `#2b3437`
- Cross-theme consistent values for on_surface, on_surface_var, outline_var, error to maintain readability across all themes

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Theme data layer complete and importable
- Ready for Plan 02 (builder integration: `HwpxBuilder(theme='forest')`)
- BUILTIN_THEMES and _make_table_presets are the integration points

---
*Phase: 01-theme-system-core*
*Completed: 2026-04-15*
