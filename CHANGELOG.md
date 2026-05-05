# Changelog

All notable changes to pyhwpxlib are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## 0.18.1 — 2026-05-06

> **표 자동 페이지 넘기기.** Hancom UI의 "여러 쪽 지원" / "제목 줄 반복"
> 옵션을 builder API로 노출. 새 keyword-only 파라미터만 추가, 기존 호출자
> 무영향.

### Added

- `HwpxBuilder.add_table(..., page_break="CELL"|"TABLE"|"NONE",
  repeat_header=False)` (keyword-only). 동일 파라미터가 `pyhwpxlib.api.add_table()`
  과 `pyhwpxlib.writer.shape_writer.build_table_xml()` 에도 forward 된다.
  - `page_break="CELL"` (default) — 행 단위 분할, 다음 페이지로 흐름.
  - `page_break="TABLE"` — 표가 1페이지에 안 들어가면 통째 다음 페이지로.
  - `page_break="NONE"` — 분할 금지 (overflow 시 잘림).
  - `repeat_header=True` — 0행을 매 페이지 상단에 자동 반복.
- `tests/test_table_pagebreak.py` (8 cases) — 단위 + builder end-to-end +
  default 보존 + 잘못된 값 ValueError 검증.

### Internal

- `pyhwpxlib/writer/shape_writer.py::build_table_xml`: 하드코딩된
  `pageBreak="CELL" repeatHeader="0"` 제거, 새 keyword 파라미터에서 emit.
  잘못된 `page_break` 값은 `ValueError` 발생 (silent skip 금지 — Critical Rules 정책).

### Compatibility

- 0.18.0 호출자 무수정 동작 (default 값이 기존 하드코딩과 동일).
- 새 keyword args 는 keyword-only (positional 호출 영향 0).
- Test count: 189 → **197** (+8).

### Verification limits

- Whale 뷰어는 `pageBreak`/`repeatHeader` 시각 반영 안 함 (한컴 한정 기능).
- pyhwpxlib는 XML attribute 정확성만 보장. 실제 페이지 분할/헤더 반복 시각
  확인은 한컴오피스에서 직접 열어보세요 (Critical Rule #12 reference fidelity).

### Deferred

- `from_json` 의 table action에 `page_break`/`repeat_header` 노출 — `Section.tables`
  schema 확장 필요. 별도 사이클.
- 자간 자동조정 (line-end 단어 분할 방지) — Hancom의 권위 있는 레이아웃에
  의존하는 기능. 0.19.0 PDCA cycle에서 architecture 결정 후 구현.

---

## 0.18.0 — 2026-05-05

> **render-perf-opt.** Caching layer + XML-level fill verification +
> workflow gating. Cuts 5-page fill-and-verify cycle compute by 83%
> and MCP tool-list response by 45%, all with byte-identical PNG output
> (sha256 anchor verified). PDCA-driven cycle (Plan/Design/Do/Check/Act).

### Added

- `pyhwpxlib.templates.check_fill(name, data) -> CheckResult` —
  schema-driven (when registered) or pattern-fallback fill verification
  in ~10ms. Returns `filled / empty / placeholders / schema_used /
  is_complete`. No rendering.
- CLI: `pyhwpxlib check-fill <name> -d data.json [-o report.json] [--json]`.
  Exit 0 when complete, 1 when any field empty or `{{key}}`/`___`
  placeholder remains. Use mid-cycle instead of `pyhwpxlib png`.
- MCP tool: `hwpx_check_fill(name, data)` — same payload as CLI.
- `render_to_png(*, engine=None)` keyword-only DI parameter. When the
  caller supplies a pre-built `RhwpEngine`, no new engine is constructed
  inside the call (saves Store/Linker/Instance setup in batch loops on
  top of the new Engine cache).
- `pyhwpxlib.api.render_pages_to_png(hwpx_path, out_dir=None, *, scale=1.2,
  font_name="NanumGothic", register_fonts=True, max_workers=None)` —
  multi-page batch renderer that combines (1) shared `RhwpEngine` (created
  once, reused across pages — sits on top of the module-level Engine cache),
  (2) `render_all_svgs_parallel` for SVG generation, (3) parallel
  `cairosvg.svg2png` via `ThreadPoolExecutor`. Output is byte-identical to
  a sequential `render_to_png` loop (asserted by
  `test_render_pages_to_png_byte_identical`). Speedup is workload-dependent
  (~1.3× on 4-page documents under Python's GIL); the primary win is API
  ergonomics — one call for "render all pages", no per-page loop.
- `scripts/bench_render.py` — 5-run sequential benchmark reporting cold
  / warm mean / p50 / p95 + LRU stats + sha256 anchor verification.
- `tests/test_text_measurer_cache.py`, `tests/test_render_consistency.py`,
  `tests/test_check_fill.py` — 21 new tests (engine singleton, PID
  fork-detection, LRU hits, font-register guard, DI tripwire, byte-identical
  regression for default/DI/serial-vs-parallel paths, schema/pattern
  check_fill paths, CLI exit codes).

### Performance (5 sequential `render_to_png`, byte-identical PNG)

- `RhwpEngine()` instantiate: 851ms → ~5ms warm (-99%).
- `render_to_png` warm mean: 879ms → 72ms (-92%).
- 5-cycle fill-and-verify compute estimate: ~6s → ~1s (-83%).
- MCP `tools-list` response: 7,841 → 4,300 chars (-45%) while
  preserving `Example:` lines in every retained docstring.

### Internal

- `pyhwpxlib/rhwp_bridge.py`:
  - Module-level `_ENGINE_CACHE: dict[wasm_path, (Engine, Module)]`
    with `_ENGINE_CACHE_PID` fork-safety guard. `RhwpEngine.__init__`
    now reuses the cached pair instead of compiling WASM per instance.
    Per-call `Store` / `Linker` / `Instance` remain isolated.
  - Module-level `@functools.lru_cache(maxsize=4096)
    _measure_text_cached(font_path, size_int, text, is_bold)` — pure
    function, thread-safe via stdlib. `_TextMeasurer.measure` delegates.
  - Lazy `wasmtime` import preserved from 0.17.1.
  - `RhwpDocument.render_all_svgs_parallel(*, embed_fonts=False,
    max_workers=None)` — bonus thread-pool batch SVG renderer (WASM
    serialised via lock, font embedding parallelised). Out of the
    primary scope but verified byte-equal to serial output by
    `test_parallel_svg_equals_serial`.
- `pyhwpxlib/api.py`:
  - Module-level `_FONTS_REGISTERED` / `_FONTS_REGISTERED_DIR` monotonic
    flag. Second `_register_bundled_fonts()` with the same dir is a true
    no-op (no filesystem stat).
  - `render_to_png(...)` accepts the new keyword-only `engine=`
    parameter.
- `pyhwpxlib/mcp_server/server.py`:
  - Tool docstrings compressed for `hwpx_template_save_session`,
    `hwpx_render_png`, `hwpx_template_context`,
    `hwpx_template_workspace_list`, `hwpx_template_log_fill`,
    `hwpx_check_fill`, `hwpx_build`, `hwpx_build_step`,
    `hwpx_build_preset`, `hwpx_fill_form`, `hwpx_analyze_form`,
    `hwpx_guide` — "2-3 sentences + 1 example" pattern.

### Docs

- `pyhwpxlib/llm_guide.GUIDE` v0.17.3 → **v0.18.0**: new §12.1 (engine
  reuse for batch rendering) and §13 (check-fill). Workflow router
  gains "Verify form fill is complete" and "Render N pages efficiently"
  rows. Version-history row updated. CLAUDE.md "Release checklist"
  step 3 fully satisfied (no GUIDE drift this cycle, unlike 0.10.0-0.17.1).
- `skill/SKILL.md` Versions table + Quick Reference (3 new rows for
  check-fill CLI, MCP, and `render_to_png(engine=)` DI).
- `skill/hwpx-form/WORKFLOW.md` Step D rewritten as a gating policy
  with concrete commands, rationale, and an explicit anti-pattern.

### Compatibility

- Existing 0.17.x callers (no `engine=`) see only a perf delta — output
  is byte-identical (sha256 anchor verified by
  `tests/test_render_consistency.py` against
  `Test/output/template_fill_makers.hwpx`,
  `d4501eeed09bc3d4d6c45a887523fdec913f428bdfee18f3e8c2570a793f2c05`).
- New keyword `engine=` is optional and keyword-only; positional call
  sites unaffected.
- Test count: 167 → **189** (+22 new across 3 test files).

---

## 0.17.3 — 2026-05-05

> **PNG export.** New API + CLI + MCP for rendering an HWPX page to PNG.
> Solves the long-standing Korean-tofu (□□□) problem when going through
> `cairosvg`. Triggered by a real user-reported workaround.

### Added

- `pyhwpxlib.api.render_to_png(hwpx_path, output_path=None, *, page=0,
  scale=1.2, font_name="NanumGothic", register_fonts=True)`. Pipeline:
  RhwpEngine SVG → regex-substitute every `font-family` → cairosvg.
  Idempotent fontconfig registration of bundled NanumGothic on first
  call. Returns the output PNG path.
- CLI: `pyhwpxlib png <input> [-o OUT] [--page N] [--scale N]
  [--font NAME] [--no-register-fonts] [--json]`.
- MCP tool: `hwpx_render_png(hwpx_path, output_path, page, scale,
  font_name, register_fonts)` returning `{"ok": true, "output": ...}`
  or `{"ok": false, "error": ...}`.

### Documented (no behavior change)

- `pyhwpxlib.rhwp_bridge._embed_fonts_in_svg` — docstring expanded.
  The function works correctly (subsetted TTFs include the right CJK
  glyphs); the limitation is downstream in cairosvg's `@font-face`
  data-URL handling for CJK. `embed_fonts=True` remains useful for
  browser / HTML embedding; for PNG export, `render_to_png` is the
  correct path.
- `RhwpDocument.render_page_svg` — caveat note added.

### Why this matters

- Form-fill workflow Step A (preview → analyze) and Step D (verify
  after fill) both depend on correct PNG rendering. Without this,
  Korean text rendered as tofu in headless / sandboxed PNG flows even
  though browsers showed it correctly.
- Single-call API removes the per-project workaround burden.

### Tests

- `tests/test_render_png.py` — 8 cases (T-PNG-01..08): API default
  output, default-path resolution, out-of-range page, missing input,
  CLI happy path, CLI error path, MCP happy path, MCP error path.
- All gated on `[preview]` extra + `cairosvg` availability so minimal
  CI envs skip cleanly.
- Total: 159 → **167 PASS**.

### Compatibility

Fully backward compatible. New surface only; no existing API touched.
Requires `[preview]` extra + `cairosvg` for the new path; absence
raises a clear `ImportError` with the exact `pip install` command.

---

## 0.17.2 — 2026-05-04

> **Docs patch.** No code change. Refreshes the built-in LLM
> quick-reference guide (`pyhwpxlib.llm_guide.GUIDE`) which was
> last updated for v0.10.0.

### Changed

- `pyhwpxlib.llm_guide.GUIDE` rewritten end-to-end (232 → 349 lines).
  This string is what the MCP `hwpx_guide()` tool returns, so the
  refresh propagates to every Claude Code / external orchestration
  client that calls it. Coverage now includes:
  - Template workflow (v0.13.3+) — `add` / `fill` / `show` / `list`
  - rhwp alignment (v0.14.0) — silent-fix opt-in, `doctor`,
    `validate --mode strict|compat|both`
  - JSON 19/19 builder coverage (v0.15.0)
  - `page-guard` mandatory gate + `analyze --blueprint` (v0.16.0)
  - Critical Rules #10–#13 (intent rules) elevated to top of guide
  - NanumGothic OFL default fonts (v0.16.1)
  - Workspace persistence Step 0 → Step G (v0.17.0)
  - `font-check --font-map`, ok/alias/fallback/missing taxonomy,
    `hwpx_template_save_session` MCP tool (v0.17.1)
- Added a workflow router table at the top so users with one-line
  intents ("fill this form", "convert .hwp") see the right section
  immediately.
- Added a recent-version-history table at the bottom of the guide.

### Removed

- `skill/chatgpt_hwpx_guide.md` (a ChatGPT-onboarding companion that
  also lived behind `hwpx_guide()`'s file lookup branch). Stale
  since v0.7.5; superseded by the in-process built-in. The MCP tool
  now reads `llm_guide.GUIDE` directly without a filesystem probe.

### Compatibility

Pure docs / built-in resource update. No public API change.

---

## 0.17.1 — 2026-05-04

> **Patch.** Quiet bug fix in the font-resolution path + two additive
> CLI/MCP improvements built on top.

### Fixed

- **`pyhwpxlib.rhwp_bridge` no longer hard-requires `wasmtime`.** The
  module-level `import wasmtime` was raising `ImportError` at import
  time even when callers only needed font resolution (no WASM engine).
  As a result, `pyhwpxlib font-check` returned empty resolutions on
  systems without the `[preview]` extra installed — silently wrong,
  not an error users could see. `wasmtime` is now lazy: it loads when
  `RhwpEngine()` is actually instantiated, with the same install hint
  as before. Fonts are resolved via `_TextMeasurer` regardless.

### Added

- **`pyhwpxlib font-check --font-map <path>`.** A user-supplied JSON
  file `{"font_name": "/path/to/font.ttf", ...}` merges over the
  bundled defaults (case-insensitive keys). Invalid JSON or list-type
  payloads are rejected with exit 1 + a clear message.
- **Refined font-check status taxonomy.** The four states now reflect
  what rhwp would actually pick at render time:

  | Status | Meaning |
  |--------|---------|
  | `ok` | declared font resolves to its own family file |
  | `alias` | declared resolves but to a different family (e.g. 함초롬돋움 → bundled NanumGothic) |
  | `fallback` | no entry in any map; rhwp picks a platform Korean/Latin fallback |
  | `missing` | mapped, but the target file is absent on disk |

  Each result row now also reports `source` ∈ `{map, override, fallback}`
  for traceability.
- **MCP `hwpx_template_save_session(name, data, decision, output_path)`.**
  Closes the diarization loop in one call — combines `log_fill` and
  `annotate(add_decision=...)` so the session-end "save state" step is
  a single round-trip. At least one of `data`/`decision` must be
  non-empty; both empty returns `{"saved": false}`.

### Tests

- 6 new cases for `font-check` (`tests/test_font_check.py`,
  T-FC-01..06): direct hit, alias detection, override promotion,
  missing path, invalid JSON, list-type rejection.
- 5 new cases for `save_session` (`tests/test_workspace_persistence.py`,
  T-MCP-04..08): data-only, decision-only, both, empty no-op,
  invalid-JSON.
- Total: 148 → **159 PASS**.

### Compatibility

- Fully backward compatible. No public API breakage. The lazy
  wasmtime change is invisible to users with `[preview]` already
  installed; users without it now see correct font resolution
  instead of empty rows.

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
