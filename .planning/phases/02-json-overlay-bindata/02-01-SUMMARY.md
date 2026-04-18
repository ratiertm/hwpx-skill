---
phase: 02-json-overlay-bindata
plan: 01
subsystem: json-io
tags: [overlay, hwpx, xml, regex, zipfile, hp-t]

requires:
  - phase: 01-theme-system-core
    provides: project structure and test scaffold
provides:
  - "original_parts field in overlay JSON for precise hp:t-level text tracking"
  - "_replace_text_in_xml function for single and multi hp:t regex replacement"
  - "zipfile-based apply_overlay (no subprocess)"
  - "_xml_escape using xml.sax.saxutils.escape"
  - "_extract_cell_parts returning (joined_text, parts_list)"
affects: [02-json-overlay-bindata, overlay-consumers, form-pipeline]

tech-stack:
  added: [xml.sax.saxutils]
  patterns: [regex-based-xml-replacement, original-parts-tracking, zipfile-direct-manipulation]

key-files:
  created:
    - tests/test_overlay.py
  modified:
    - pyhwpxlib/json_io/overlay.py

key-decisions:
  - "Regex-based multi-hp:t replacement instead of ET serialization (avoids namespace rewriting)"
  - "Cell text join changed from ' ' to '' for matching accuracy"
  - "zipfile direct manipulation replaces subprocess unpack/repack"

patterns-established:
  - "original_parts: every text/cell entry carries individual <hp:t> parts list for precise replacement"
  - "_replace_text_in_xml: single-part uses str.replace, multi-part uses regex with </hp:t>\\s*<hp:t> pattern"

requirements-completed: [TS-3]

duration: 3min
completed: 2026-04-18
---

# Phase 2 Plan 1: Overlay original_parts + regex replacement + zipfile refactor Summary

**Precise hp:t-level text extraction with original_parts tracking, regex-based multi-hp:t replacement, and zipfile-direct apply (removes subprocess dependency)**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-18T02:02:53Z
- **Completed:** 2026-04-18T02:05:51Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- extract_overlay now tracks individual `<hp:t>` parts per run as `original_parts` list
- apply_overlay correctly replaces split text like "울산중부"+"소방서" via regex pattern matching
- apply_overlay rewritten to use zipfile directly, removing subprocess/tempfile/shutil dependencies
- Cell text extraction changed from space-join to empty-join for matching accuracy
- XML special characters handled via `xml.sax.saxutils.escape`
- 20 comprehensive tests covering all new functionality

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests** - `43e1904` (test)
2. **Task 1 (GREEN): Implementation** - `dba816f` (feat)

## Files Created/Modified
- `tests/test_overlay.py` - 20 unit/integration tests for overlay extract and apply
- `pyhwpxlib/json_io/overlay.py` - original_parts extraction, regex replacement, zipfile refactor

## Decisions Made
- Used regex-based replacement instead of ElementTree serialization to avoid namespace prefix rewriting (`hp:` -> `ns0:`)
- Changed cell text join from `" "` to `""` for accurate XML matching (breaking change for `original` field but necessary for correctness)
- Removed `subprocess`, `sys`, `shutil`, `tempfile` imports from overlay.py -- apply_overlay now uses zipfile directly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in `test_form_pipeline.py::TestGenerateForm` due to missing `ratiertm-hwpx` dependency -- unrelated to this plan's changes, not fixed (out of scope).

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functionality is fully wired.

## Next Phase Readiness
- overlay extract/apply now supports split `<hp:t>` patterns
- Ready for Plan 02 (BinData error handling) and Plan 03 (nested table/image overlay)
- `original_parts` field available for all downstream overlay consumers

---
*Phase: 02-json-overlay-bindata*
*Completed: 2026-04-18*

## Self-Check: PASSED
