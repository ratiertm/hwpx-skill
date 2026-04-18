---
phase: 02-json-overlay-bindata
plan: 03
subsystem: json-io
tags: [overlay, hwpx, image-replacement, nested-table, bindata, xpath]

requires:
  - phase: 02-json-overlay-bindata
    plan: 01
    provides: zipfile-based apply_overlay with image_replacements param, original_parts extraction
provides:
  - "Image replacement edge case coverage (nonexistent bin_ref, partial replacement, binary fidelity)"
  - "Fixed nested table extraction: direct-child XPath prevents duplication at 3+ nesting levels"
  - "Nested table cells extractable and replaceable via apply_overlay"
affects: [overlay-consumers, form-pipeline]

tech-stack:
  added: []
  patterns: [direct-child-xpath-traversal]

key-files:
  created: []
  modified:
    - pyhwpxlib/json_io/overlay.py
    - tests/test_overlay.py

key-decisions:
  - "Direct-child traversal (tc -> subList -> p -> run -> tbl) instead of .//{_HP}tbl XPath"
  - "Image replacement already fully working from Plan 01 -- Task 1 only added edge case tests"

patterns-established:
  - "Nested table traversal: always use direct-child path, never descendant XPath for recursive structures"

requirements-completed: [CF-2, CF-3]

duration: 3min
completed: 2026-04-18
---

# Phase 2 Plan 3: Image replacement tests + nested table double-extraction fix Summary

**Image replacement edge case tests confirming zipfile BinData swap, plus direct-child XPath fix eliminating nested table duplication at 3+ levels**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-18T02:13:10Z
- **Completed:** 2026-04-18T02:16:30Z
- **Tasks:** 2 (TDD)
- **Files modified:** 2

## Accomplishments
- Added 4 edge case tests for image replacement (nonexistent bin_ref skip, unreplaced preservation, exact bytes match, no-regression without image_replacements)
- Fixed nested table double-extraction bug: replaced `.//{_HP}tbl` with direct-child traversal through `subList -> p -> run -> tbl`
- Added 5 nested table tests: no-duplicate, nested_in field, original_parts, cell replacement, 3-level nesting
- Total overlay test count: 29 (all passing)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED+GREEN): Image replacement edge case tests** - `e1950bf` (test)
2. **Task 2 RED: Nested table failing tests** - `41c4860` (test)
3. **Task 2 GREEN: Fix nested table XPath** - `2f9356d` (feat)

## Files Created/Modified
- `pyhwpxlib/json_io/overlay.py` - Fixed `_extract_table` nested table XPath from `.//{_HP}tbl` to direct-child traversal
- `tests/test_overlay.py` - Added 9 new tests (4 image replacement edge cases + 5 nested table tests)

## Decisions Made
- Image replacement implementation was already complete from Plan 01's zipfile refactor -- Task 1 only needed edge case test coverage, not code changes
- Used direct-child traversal path `tc -> subList -> p -> run -> tbl` instead of a single XPath expression, because the OWPML structure nests tables inside subList/p/run containers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in `test_form_pipeline.py::TestGenerateForm` due to missing `ratiertm-hwpx` dependency -- unrelated, documented in Plan 01 summary.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functionality is fully wired.

## Next Phase Readiness
- Phase 2 (JSON Overlay + BinData) is now complete (all 3 plans done)
- Overlay extract/apply supports: split hp:t text, image replacement, nested tables
- Ready for Phase 3 or any downstream work requiring overlay features

---
*Phase: 02-json-overlay-bindata*
*Completed: 2026-04-18*

## Self-Check: PASSED
