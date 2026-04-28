---
template: analysis
description: Gap analysis between design and implementation for auto-schema-cellspan (v0.13.4) — Act iteration 1 (FR-05 closed)
---

# auto-schema-cellspan Gap Analysis

> **Feature**: auto-schema-cellspan
> **Version**: 0.13.4
> **Date**: 2026-04-29
> **Match Rate**: **96%** (was 88%; +8% from FR-05 closure)
> **Plan**: [auto-schema-cellspan.plan.md](../01-plan/features/auto-schema-cellspan.plan.md)
> **Design**: [auto-schema-cellspan.design.md](../02-design/features/auto-schema-cellspan.design.md)
> **Implementation commits**: `4f68c62` (initial) → `afff6d6` (Act iter 1: diagnose CLI)

---

## 1. Match Rate Breakdown

| Category | Items | Fulfilled | % |
|----------|-------|-----------|---|
| Design § 3 functions | 5 | 5 | 100% |
| Design § 4 test plan (T-01..T-08) | 8 | 8 | 100% |
| Design § 5 diagnose CLI | 1 | 1 | 100% |
| Plan FR-01..FR-05 | 5 | 5 | 100% |
| Plan DoD § 4.1 | 5 | 5 | 100% |
| Version bump (0.13.4) | 1 | 1 | 100% |
| Doc polish (Risk § 6 `rs ≥ 2` mention in § 3.2) | 1 | 0 | 0% |
| **Overall** | **26** | **25** | **96%** |

Status: **≥ 90% — ready for `/pdca report`.**

---

## 2. Fulfilled (Design ≡ Implementation)

| Design item | Code reference | Notes |
|-------------|----------------|-------|
| `_find_grid_subregion` (§ 3.1) | `pyhwpxlib/templates/auto_schema.py:188-221` | Contiguous run, len ≥ 3, cols ≥ 2, longest-wins. `GridRegion` dataclass at `:40-52` adds helper `.contains()`. |
| `_find_row_group_label` (§ 3.2) | `auto_schema.py:169-185` | Stricter than design: extra `c["rs"] >= 2` guard prevents adjacent rs=1 single-row labels from polluting grid keys. |
| `_find_label_for` cellSpan-aware (§ 3.3 / FR-01) | `auto_schema.py:135-166` | Both colSpan (`:151`) and rowSpan (`:157`) span-aware. |
| `_LABEL_MAP` row-group entries (§ 3.4) | `pyhwpxlib/templates/slugify.py:54-59` | 12 entries (Design asked for 5–10). |
| `generate_schema` refactor (§ 3.5 / FR-02) | `auto_schema.py:288-338` + helpers `_build_field_in_grid` (`:224-265`), `_build_field_single` (`:268-285`) | Grid-aware dispatch matches design § 3.4 flow. |
| **`diagnose` CLI / API (§ 5 / FR-05)** | **`pyhwpxlib/templates/diagnose.py` (~280 LOC)** | **NEW (afff6d6)** — see § 2.1 below. |
| **CLI subcommand wiring** | **`pyhwpxlib/cli.py` template subcommand + parser** | **NEW** — `pyhwpxlib template diagnose <hwpx> [--schema MANUAL.json] [--json]`. |
| **Module entrypoint** | **`diagnose.py` `if __name__ == "__main__"`** | **NEW** — `python -m pyhwpxlib.templates.diagnose <hwpx>`. |
| Schema migration id→student_id, sign→signature | `skill/templates/makers_project_report.schema.json`; `slugify.py:21-22` | Manual ground truth realigned with auto canonical naming. |
| T-01..T-07 unit cases | `tests/test_auto_schema_cellspan.py:25-107` | All grid sub-region + row group + cellSpan cases. |
| T-08 makers overlap ≥ 70% (FR-03) | `tests/test_auto_schema_cellspan.py:113-132` | Threshold-asserting test. table[0] overlap = **100% (20/20)**. |
| T-08b grid keys produced | `tests/test_auto_schema_cellspan.py:135-147` | All 16 expected `member_{1..4}_{name|dept|student_id|signature}`. |
| **diagnose API tests (6 cases)** | **`tests/test_diagnose.py`** | **NEW** — see § 2.1 below. |
| Existing `test_templates.py` updated | `tests/test_templates.py:91-110` | Single fields kept bare slug; grid expects member_N_*. |
| Version sync 0.13.3 → 0.13.4 | `pyhwpxlib/__init__.py:28`, `pyproject.toml:7` | Both files bumped. |

### 2.1 FR-05 closure — diagnose CLI/API verification

| Design § 5 requirement | Implementation site | Confirmed |
|------------------------|---------------------|:---------:|
| Per-table grid sub-region (rows / cols / count) | `diagnose.py` `_diagnose_one_table` + `_format_text` | ✅ |
| Row-group label sample | `diagnose.py:60-67` | ✅ |
| Per-column header detection within grid | `diagnose.py:70-77` | ✅ |
| Auto fields list with `[grid]/[single]` origin tag | `diagnose.py:125-133` | ✅ |
| Manual schema comparison (overlap %, missing/extra) | `diagnose.py:138-169` (text), `:181-192` (JSON) | ✅ |
| `--schema` flag | argparse | ✅ |
| `--json` flag | argparse | ✅ |
| Programmatic API `diagnose(hwpx_path, manual_schema_path=...)` | `diagnose.py:196-225` | ✅ (bonus, not in design) |

| Test (`tests/test_diagnose.py`) | Coverage |
|---------------------------------|----------|
| `test_diagnose_api_returns_grid_info` | API returns grid info matching `(start_row=3, end_row=6, cols={1,2,4,6})` + row-group label present |
| `test_diagnose_with_manual_schema_reports_overlap` | API+manual overlap ≥ 40% (table[0] is 100%; total includes out-of-scope table[1]) |
| `test_diagnose_cli_text_output` | CLI text mode emits "Table 0", "Grid sub-region", "Auto fields" |
| `test_diagnose_cli_json_with_schema` | CLI JSON mode parses + comparison ratio ≥ 40% |
| `test_diagnose_cli_missing_file_returns_2` | Error path: nonexistent file → exit 2 |
| `test_diagnose_cli_wrong_extension_returns_2` | Error path: non-.hwpx → exit 2 |

All six PASS confirmed (`pytest tests/test_diagnose.py -v` → 6 passed). Full regression: **60 PASS** (54 + 6).

---

## 3. Gaps (Design O / Implementation X)

| Item | Design | Plan | Severity | Detail |
|------|--------|------|:--------:|--------|
| Doc cross-link: § 3.2 should mention the `rs >= 2` guard | § 6 Risks (mentioned) ↔ § 3.2 (not mentioned) | — | Low (doc only) | Implementation is stricter than spec, in the safe direction. Update Design § 3.2 in a future doc-polish pass. |

### 3.1 Indirect coverage (could be tighter — not blocking)

| FR | Status | Note |
|----|--------|------|
| FR-03 actual overlap surface | Threshold-asserted (≥ 70%); actual ratio measured 100% on table[0] | Diagnose CLI now exposes the live ratio (`pyhwpxlib template diagnose <hwpx> --schema ...`), so trend tracking is possible without test changes |
| FR-04 single-field regression | Indirectly covered by `test_auto_schema_extracts_known_labels` + 60 PASS regression | A dedicated `test_makers_single_fields_unchanged` would be belt-and-suspenders |

### 3.2 Implementation deviations (low impact, all in safe direction)

| Item | Design | Implementation | Impact |
|------|--------|----------------|--------|
| `_find_row_group_label` rs guard | `c.row ≤ row < c.row + c.rs` only | Adds `c["rs"] >= 2` filter | Low — safer, aligned with Risk § 6 |
| `GridRegion.cols` type | `set[int]` | `frozenset` | Low — strictly better |
| `GridRegion.contains()` helper | Not in design | Added at `auto_schema.py:51-52`; used by diagnose | Low — readability, reused |
| `diagnose` programmatic API | Not in design (CLI only) | `diagnose(hwpx_path, manual_schema_path=...)` exposed at `diagnose.py:196-225` | Positive — enables embedding in tests / notebooks |

---

## 4. Verdict

**Code-level implementation: complete and correct.**
- All 5 design heuristic functions present and behave as specified
- All 8 design test cases (T-01..T-08) pass
- FR-05 diagnose CLI: implemented, wired into `pyhwpxlib template diagnose`, runnable via `python -m`, plus 6 dedicated tests
- **60 tests passing** (54 + 6 new diagnose)
- makers table[0] overlap: 34% → **100%** (target was 70%)

**Match Rate 96%** — comfortably above the 90% threshold. Sole remaining item is a doc cross-link polish (Low severity).

**Recommendation: proceed to `/pdca report auto-schema-cellspan`.** The doc-polish item is non-blocking and can be rolled into 0.13.5 maintenance or addressed during report writing.

### 4.1 Pre-report checklist

- [x] FR-01..FR-05 all implemented
- [x] Match Rate ≥ 90%
- [x] Test files exist for all design test cases
- [x] Version bumped (`__init__.py` + `pyproject.toml` both at 0.13.4)
- [x] `pytest tests/test_diagnose.py -v` → 6 PASS
- [x] Full regression `pytest` → 60 PASS
- [ ] (Optional) Update Design § 3.2 with `rs >= 2` guard note

---

## 5. Iteration History

| Iteration | Commit | Match Rate | Trigger | Outcome |
|-----------|--------|:----------:|---------|---------|
| Initial (Do) | `4f68c62` | 88% | First implementation pass | FR-01..04 done, FR-05 deferred |
| Act #1 | `afff6d6` | **96%** | gap-detector flagged FR-05 as sole gap | `diagnose.py` (~280 LOC) + 6 tests + CLI wiring |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-29 | Initial gap analysis (88%) | Mindbuild + Claude |
| 0.2 | 2026-04-29 | Act iter 1: FR-05 closed via `afff6d6` (diagnose CLI), 88% → 96%, ready for report | Mindbuild + Claude |
