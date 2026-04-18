---
phase: 02-json-overlay-bindata
plan: 02
subsystem: converter
tags: [hwp2hwpx, bindata, zlib, error-handling]

requires:
  - phase: 01-theme-system-core
    provides: stable codebase with test infrastructure
provides:
  - resilient _attach_binary_data that skips corrupt BinData streams
  - warning logging for failed decompression
affects: [hwp-conversion, bindata-pipeline]

tech-stack:
  added: []
  patterns: [try-except-skip-with-warning for non-critical stream errors]

key-files:
  created:
    - tests/test_hwp2hwpx_bindata.py
  modified:
    - pyhwpxlib/hwp2hwpx.py

key-decisions:
  - "Skip corrupt BinData entirely (no empty bytes fallback) -- Whale handles missing BinData gracefully"

patterns-established:
  - "try/except around individual stream processing with warning log and skip"

requirements-completed: [TS-4]

duration: 1min
completed: 2026-04-18
---

# Phase 2 Plan 02: BinData Error Handling Summary

**try/except in _attach_binary_data skips corrupt zlib streams with warning instead of crashing HWP-to-HWPX conversion**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-18T02:03:00Z
- **Completed:** 2026-04-18T02:04:19Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Wrapped _attach_binary_data decompression in try/except with warning logging
- 5 tests covering mixed/all-corrupt/all-good streams, warning verification, no-empty-bytes
- convert() now completes successfully even when BinData streams are damaged

## Task Commits

Each task was committed atomically:

1. **Task 1: Wrap _attach_binary_data decompression in try/except + test**
   - RED: `630c731` (test) -- 5 failing tests for BinData error handling
   - GREEN: `1d685bc` (feat) -- try/except wrap, all tests pass

**Plan metadata:** [pending]

## Files Created/Modified
- `tests/test_hwp2hwpx_bindata.py` - 5 tests for BinData decompress error handling (mock OLE, corrupt/valid streams)
- `pyhwpxlib/hwp2hwpx.py` - try/except in _attach_binary_data (lines 979-991)

## Decisions Made
- Skip corrupt BinData entirely (do not set attachments[key] = b"") -- Whale handles missing BinData gracefully per Research Pitfall 4
- Log warning with stream name and exception message for debugging

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing golden test failure in test_hwp2hwpx_golden.py for 20250224112049_9119844.hwpx (character loss) -- unrelated to BinData changes, out of scope

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- BinData error handling complete
- Ready for Plan 03 (image replacement) and other Phase 2 plans

---
*Phase: 02-json-overlay-bindata*
*Completed: 2026-04-18*

## Self-Check: PASSED
- tests/test_hwp2hwpx_bindata.py: FOUND
- 02-02-SUMMARY.md: FOUND
- Commit 630c731: FOUND
- Commit 1d685bc: FOUND
