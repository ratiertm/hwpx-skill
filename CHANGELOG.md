# Changelog

All notable changes to pyhwpxlib are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## 0.17.0 — 2026-05-01

> **Cross-session memory.** When the chat context resets, pyhwpxlib no
> longer forgets your form. Each registered template now owns a
> workspace folder under `~/.local/share/pyhwpxlib/templates/<name>/`
> that holds the original document, decisions, fill history, and saved
> outputs — all auto-loaded on the next session.

### Added

- **Per-template workspace folders.** `template add <file>` creates
  `~/.local/share/pyhwpxlib/templates/<name>/` containing
  `original.hwpx`, `decisions.md` (free-form notes), `history.json`
  (last fill payloads), and `outputs/` (auto-named results).
- **Auto-named outputs.** `template fill --name <key>` with no
  `--output` writes to `outputs/YYYY-MM-DD_<key>.hwpx` and appends the
  payload to `history.json`. Re-runs preserve the prior file (suffixed
  `_2`, `_3`, …).
- **CLI commands.**
  - `template context <name>` — print decisions, recent fills,
    structural summary
  - `template annotate <name>` — append a note to `decisions.md`
  - `template log-fill <name> --data <json>` — manual history entry
  - `template open <name>` — open the workspace folder in Finder/Explorer
  - `template migrate` — relocate templates from legacy registry to the
    new layout (creates a `tar.gz` backup before moving)
  - `template install-hook` — install a Claude Code SessionStart hook
    that calls `list_templates` + `load_context` automatically
- **MCP tools.** `hwpx_template_context`, `hwpx_template_workspace_list`,
  `hwpx_template_log_fill` exposed via `pyhwpxlib.mcp_server`.
- **New modules.**
  - `pyhwpxlib/templates/workspace.py` — `auto_output_path`,
    `install_session_hook`
  - `pyhwpxlib/templates/context.py` — `TemplateContext`,
    `load_context`, `annotate`, `log_fill`
  - `pyhwpxlib/templates/migration.py` — `plan_migration`,
    `execute_migration` (`tar.gz` backup before mutate)

### Changed

- `pyhwpxlib.templates.fill.fill` accepts `output_path=None` and
  resolves to the workspace `outputs/` folder when the template has
  one. Existing callers that pass an explicit path are unaffected.
- `LICENSE.md` — Rolling Change Date advanced to 2030-05-01.

### Tests

- `tests/test_workspace_persistence.py` — 18 cases (T-WS / T-MIG /
  T-MCP / T-HOOK), incl. cross-session restoration scenario.
- Total regression: 130 → **148 PASS**.

### Compatibility

- Fully backward compatible. Templates registered under the legacy
  registry continue to work; `template migrate` is opt-in.

---

## 0.16.1 — 2026-05-01

> **License safety patch.** Default font metadata switched from
> 함초롬 / 맑은 고딕 (closed redistribution licenses) to 나눔고딕 (SIL
> OFL 1.1). PyPI users no longer inherit redistribution risk from
> Hancom / Microsoft fonts in the default code path.

### Changed

- `pyhwpxlib/themes.py` — `FontSet` six fields all default to
  `'나눔고딕'` (previously `'맑은 고딕'`).
- `pyhwpxlib/tools/blank_file_maker.py::_add_font_pair` — font slots
  0 and 1 unified to `'나눔고딕'`.
- `pyhwpxlib/tools/_reference_header.xml` — 함초롬돋움 / 바탕
  references rewritten to 나눔고딕.
- `README.md` / `README_KO.md` — new **Fonts** section explains the
  license comparison table and how to override.

### Removed

- `pyhwpxlib/font/` — 148 MB of unused font zip bundles (7 archives)
  pruned from the package. Significant PyPI wheel size reduction.

### Preserved

- `vendor/NanumGothic-*.ttf` (4 MB OFL embed) still ships for the
  rhwp fallback path.
- `rhwp_bridge.py` 함초롬 → NanumGothic mapping is unchanged
  (existing HWPX files render unchanged).
- `hwp2hwpx.convert()` preserves original font names for fidelity.
- `FontSet(heading_hangul='맑은 고딕')` override remains supported
  — the user takes on the redistribution responsibility.

### Tests

- `tests/test_font_defaults.py` — 7 new cases (T-FR-01…06 +
  backward-compat bonus).
- Total regression: 123 → **130 PASS**.

---

## 0.16.0 — 2026-05-01

> **Reference-fidelity toolkit.** Closes the
> "validate 통과 ≠ 사용자 의도 일치" gap by introducing a mandatory
> reference/result page-count gate plus four intent rules in the
> rulebook. Inspired by the XML-first `page_guard.py` pattern from a
> partner hwpx skill author and absorbed into our API-first stack.

### Added

- `pyhwpxlib/page_guard.py` — compares reference and result page
  counts via dual paths (rhwp engine + static heuristics) so the gate
  works whether or not rhwp is available.
- `pyhwpxlib/blueprint.py` — `analyze --blueprint` produces a human-
  readable structural blueprint at depth 1 / 2 / 3.
- CLI commands.
  - `pyhwpxlib page-guard <ref> <result>` — strict gate, exit ≠ 0
    on page-count mismatch.
  - `pyhwpxlib analyze --blueprint --depth N` — text blueprint
    output for documents.
- **Critical Rules #10–#13** in `skill/references/HWPX_RULEBOOK.md`
  Section 38:
  - #10 substitution-first edits
  - #11 structural-change restrictions
  - #12 reference / result page-count parity required
  - #13 page-guard pass required before delivery
- `skill/references/rich_document_example.md` — golden Rich-Mode
  sample + checklist.
- `scripts/update_license_date.py` — auto-bump the LICENSE Rolling
  Change Date on each release (release date + 4 years).

### Removed (legacy GUI)

- `template_builder.py`, `form_editor.py` — superseded by the v0.13.3+
  CLI workflow.

### Changed

- `LICENSE.md` / `README*.md` — Rolling Change Date pattern documented.

### Tests

- 16 new cases (`test_page_guard.py` T-PG-01..06, `test_blueprint.py`
  T-BP-01..03, plus regression-strengthening additions).
- Total regression: 107 → **123 PASS**.

---

## 0.15.0 — 2026-04-29

> JSON path now reaches the same expressivity as direct ``HwpxBuilder``
> calls. Solves the "단조" (monotonous) JSON output issue identified by
> the graphify analysis: previously ``decoder.from_json`` only used 3 of
> 19 add_* methods (16%) — it now dispatches all 16 buildable methods.

### Added

- `pyhwpxlib.json_io.schema` — 11 new dataclasses for rich content:
  `Heading`, `Image`, `HeaderFooter`, `PageNumber`, `Footnote`,
  `Equation`, `Highlight`, `BulletList`, `NumberedList`, `NestedListItem`,
  `NestedBulletList`, `NestedNumberedList`, `Shape`.
- `RunContent.type` extended with 11 new values:
  `heading`, `bullet_list`, `numbered_list`, `nested_bullet_list`,
  `nested_numbered_list`, `footnote`, `equation`, `highlight`,
  `shape_rect`, `shape_line`, `shape_draw_line`.
- `HwpxJsonDocument` gains `header`, `footer`, `page_number` (top-level,
  applied last to dodge the Whale SecPr ordering bug — same deferred
  pattern HwpxBuilder uses).
- `pyhwpxlib.json_io.decoder._apply_run` — typed dispatch table mapping
  each JSON `type` to the matching builder method. Unknown types raise
  `ValueError` (rhwp-aligned: no silent skips).

### JSON example (full pipeline available)

```json
{
  "header": {"text": "Acme Corp"},
  "page_number": {"pos": "BOTTOM_CENTER"},
  "sections": [{
    "paragraphs": [
      {"runs": [{"content": {"type": "heading",
                              "heading": {"text": "Report", "level": 1}}}]},
      {"runs": [{"content": {"type": "bullet_list",
                              "bullet_list": {"items": ["A", "B", "C"]}}}]},
      {"runs": [{"content": {"type": "footnote",
                              "footnote": {"text": "see notes"}}}]}
    ],
    "tables": [],
    "page_settings": {}
  }]
}
```

### Tests

- 28 new cases in `tests/test_json_schema_expansion.py` (T-01..T-18 +
  11 parametric "missing nested object → ValueError" guards).
- Total regression: 72 → **100 PASS**, zero break.

### Compatibility

- v0.14.0 JSON (paragraphs/tables only) continues to work unchanged —
  all new fields are additive and optional.
- rhwp-strict-mode default behaviour preserved (no silent fixes).

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
