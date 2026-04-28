# Changelog

All notable changes to pyhwpxlib are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## 0.14.0 — 2026-04-29

> **Breaking change.** pyhwpxlib adopts the rhwp-aligned position on
> non-standard HWPX structures: detect, notify, never silently rewrite.
> See [`reference_hwpx_ecosystem_position.md`](docs/) for the rationale.

### Changed (breaking)

- **`write_zip_archive(strip_linesegs=...)` default flipped from
  `"precise"` → `False`.** Existing callers that depended on the silent
  textpos-overflow fix must opt in:
  ```python
  # before (≤ 0.13.x)
  write_zip_archive(path, archive)                       # silent fix

  # after (0.14.0+)
  write_zip_archive(path, archive, strip_linesegs="precise")  # explicit
  ```
- `write_zip_archive` now **returns `int`** — the count of linesegs
  actually fixed (0 when no fix was attempted). Existing callers that
  ignore the return value continue to work.
- `pyhwpxlib.api.fill_template` and `fill_template_checkbox`:
  added keyword-only `fix_linesegs: bool = False` parameter.
- `pyhwpxlib.json_io.overlay.apply_overlay`: same.
- `pyhwpxlib.templates.add` and `pyhwpxlib.templates.fill_template_file`:
  same.

### Added

- **`pyhwpxlib doctor <file>`** — diagnose non-standard HWPX structures.
  Pass `--fix` to apply the precise textpos-overflow correction (writes
  `<file>.fixed.hwpx` by default; `--inplace` to overwrite, `-o` for an
  explicit output path).
- **`pyhwpxlib validate --mode {strict|compat|both}`** — `compat`
  preserves the historical zip + parse + required-files check; `strict`
  performs OWPML-spec-aligned checks (lineseg textpos consistency,
  namespace declarations, first-paragraph ordering, hp:t form report);
  `both` (default) reports side-by-side. Exit code follows compat;
  strict failures are advisory.
- **`pyhwpxlib template add/fill --fix`** — explicit flag to opt back
  into the precise fix. Without `--fix`, the CLI emits an stderr
  advisory (`[pyhwpxlib] 비표준 lineseg N건 ...`) when the output
  would trigger Hancom's security warning.
- `pyhwpxlib.doctor` Python module exposing `diagnose(path)` and
  `fix(input, output, mode="precise")`.

### Fixed

- `pyhwpxlib template fill` previously claimed to fill empty cells
  (`team_name`, `member_*`, `project_name`) but silently skipped them.
  Root cause: `_replace_first_paragraph_text` regex only matched the
  paired `<hp:t>...</hp:t>` form; pristine empty cells in HWPX use the
  legal self-closing `<hp:t/>` form. The regex now handles both forms,
  and `tests/test_templates.py::test_add_hwp_then_fill_round_trip`
  asserts the values actually land in the section XML.

### Migration notes

If you upgrade from 0.13.x and need the previous silent precise-fix
behaviour:

| Use case | What to add |
|----------|-------------|
| `pyhwpxlib template fill ...` | `--fix` |
| `pyhwpxlib.api.fill_template(...)` | `fix_linesegs=True` |
| `pyhwpxlib.json_io.overlay.apply_overlay(...)` | `fix_linesegs=True` |
| Direct `write_zip_archive(...)` | `strip_linesegs="precise"` |

Or run `pyhwpxlib doctor <file> --fix --inplace` after the fact for any
file that triggers Hancom's security warning.

### Why this change

The HWPX spec defines `<hp:lineseg>` coordinates as accurate, pre-computed
values. Some Hancom versions emit inaccurate values; Hancom's reader
silently reflows on load and hides the discrepancy. External renderers
(rhwp, custom previewers) that respect the spec render the inaccurate
values literally and break.

When pyhwpxlib silently applied the same kind of "fix" on every save it
hid the same technical debt from users. v0.14.0 reverses that: the
default is honest preservation; corrections are explicit; users see what
their files actually contain.

---

## 0.13.4 — 2026-04-29

### Added

- `pyhwpxlib.templates.auto_schema._find_grid_subregion` — detects
  contiguous repeated-grid rows so participant cells are slugged
  `member_1_name`, `member_2_dept`, ... instead of `field_2`/`field_3`.
- `pyhwpxlib.templates.auto_schema._find_row_group_label` — picks up
  rowSpan-based group labels like `참 여 자` (rs=4).
- `pyhwpxlib.templates.auto_schema._find_label_for` is now cellSpan-aware
  (header colSpan covers all columns it spans; row-label rowSpan covers
  all rows).
- `pyhwpxlib.templates.diagnose` (CLI + API) — per-table grid diagnostic
  + optional manual schema overlap precision/recall.
- 15 new tests (9 cellSpan + 6 diagnose).

### Changed

- `skill/templates/makers_project_report.schema.json` — manual schema
  realigned with auto naming: `member_N_id` → `member_N_student_id`,
  `member_N_sign` → `member_N_signature`.

### Metrics

- makers form table[0] auto vs manual schema overlap: 34% → **100%**
  (target was 70%).

---

## 0.13.3 — 2026-04-28

### Added

- `pyhwpxlib.templates` module — register, fill, show, list user-uploaded
  HWP/HWPX forms with auto-generated schemas. XDG-compliant user dir
  + skill bundle dir. CLI `pyhwpxlib template {add,fill,show,list}`.

### Fixed

- `precise` lineseg fix now applied on every `write_zip_archive` save by
  default (Hancom security warning workaround). _(Reverted to opt-in in
  0.14.0; see above.)_
