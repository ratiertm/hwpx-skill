---
phase: 01-theme-system-core
plan: 02
subsystem: theming
tags: [builder-integration, font-registration, backward-compat, table-presets]

requires:
  - phase: 01-theme-system-core
    plan: 01
    provides: "Theme/Palette/FontSet/SizeSet/Margins + BUILTIN_THEMES + _make_table_presets"
provides:
  - "HwpxBuilder(theme='forest') creates themed documents"
  - "BlankFileMaker.make(font_set=) registers multiple fonts"
  - "api.add_heading(height=, font_name=, text_color=) overrides"
  - "Theme/BUILTIN_THEMES in public __init__.py exports"
affects: [future-preset-integration, form-pipeline-theming]

tech-stack:
  added: []
  patterns: [per-instance-preset-derivation, backward-compat-guard]

key-files:
  created: []
  modified:
    - pyhwpxlib/builder.py
    - pyhwpxlib/api.py
    - pyhwpxlib/tools/blank_file_maker.py
    - pyhwpxlib/__init__.py
    - tests/test_themes.py

key-decisions:
  - "Default theme uses _is_default_theme flag to skip font_name/text_color injection for backward compat"
  - "font_set=None passed to create_document for default theme (preserves original fontface pair)"
  - "Per-instance _table_presets_dict derived from theme palette, module-level TABLE_PRESETS untouched"
  - "Paragraph IDs are random per-run, so backward compat test compares header.xml (deterministic)"

patterns-established:
  - "_heading_style_kwargs() centralizes theme-to-charPr mapping"
  - "_add_theme_fonts() deduplicates FontSet entries for fontface registration"

requirements-completed: [TS-1, TS-2]

duration: 7min
completed: 2026-04-17
---

# Phase 1 Plan 02: Theme Integration into Builder Summary

**Wire Theme system into HwpxBuilder, BlankFileMaker, and api.py with per-instance table presets and multi-font registration**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-17T22:15:16Z
- **Completed:** 2026-04-17T22:22:16Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- HwpxBuilder(theme='forest') creates documents with forest-colored headings and table presets
- HwpxBuilder() (no args) produces identical header.xml to pre-change behavior
- BlankFileMaker.make(font_set=) registers all unique fonts from FontSet with deduplication
- api.add_heading() accepts height/font_name/text_color overrides for theme injection
- api.create_document(font_set=) threads FontSet to BlankFileMaker
- Per-instance _table_presets_dict derived from active theme palette
- Module-level DS and TABLE_PRESETS remain unchanged (backward compat constants)
- Theme and BUILTIN_THEMES exported in pyhwpxlib.__init__.py
- All 10 built-in themes produce valid HWPX files

## Task Commits

1. **Task 1: Wire theme into BlankFileMaker and api.py** - `3b06778` (feat)
2. **Task 2: Wire theme into HwpxBuilder + integration tests** - `f2120bf` (feat)

## Files Created/Modified

- `pyhwpxlib/builder.py` - Added theme= parameter, _heading_style_kwargs(), per-instance _table_presets_dict
- `pyhwpxlib/api.py` - create_document(font_set=), add_heading(height=, font_name=, text_color=)
- `pyhwpxlib/tools/blank_file_maker.py` - make(font_set=), _add_theme_fonts(), _fontfaces(font_set=)
- `pyhwpxlib/__init__.py` - Added Theme, BUILTIN_THEMES exports
- `tests/test_themes.py` - 7 integration tests replacing 7 skip placeholders (36 total pass)

## Decisions Made

- Default theme backward compat uses `_is_default_theme` flag to avoid injecting font_name/text_color into headings (which would change charPr from the original behavior)
- font_set=None for default theme preserves the original fontface pair (함초롬돋움/함초롬바탕)
- Paragraph IDs are randomly generated per run, so backward compat test compares header.xml (deterministic) rather than section XML

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Paragraph ID randomness in backward compat test**
- **Found during:** Task 2
- **Issue:** Plan specified "compare byte output" but paragraph IDs are random per-run, making byte comparison impossible for section XML
- **Fix:** Changed test to compare header.xml (deterministic) and verify fontface structure
- **Files modified:** tests/test_themes.py
- **Commit:** f2120bf

## Issues Encountered
None

## Known Stubs
None - all theme integration is fully wired.

## User Setup Required
None

## Next Phase Readiness
- Theme system fully integrated into builder pipeline
- All 10 themes produce valid HWPX with correct colors and fonts
- Ready for Phase 2 (preset system or form pipeline theming)

---
*Phase: 01-theme-system-core*
*Completed: 2026-04-17*
