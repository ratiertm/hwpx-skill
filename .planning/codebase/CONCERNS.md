# Codebase Concerns

**Analysis Date:** 2026-04-15

---

## Tech Debt

### Single-Palette Design System (DS dict)
- **Severity:** High
- Issue: `DS` dict in `pyhwpxlib/builder.py` (lines 44–57) is hardcoded to a single "Administrative Slate" blue palette (`primary: '#395da2'`). `TABLE_PRESETS` `corporate`, `government`, and `default` all reference this same palette, so 3 of 4 presets produce identical blue headers. There is no mechanism for callers to swap palettes at build time.
- Files: `pyhwpxlib/builder.py:44–100`
- Impact: All generated documents default to the same blue color scheme regardless of document type or subject matter. The design guide (`skill/references/design_guide.md`) defines 10 palettes (Forest & Growth, Warm Executive, Ocean Analytics, etc.) but none are instantiable through the API without manually overriding every cell color.
- Fix approach: Add a `palette: dict | str = 'administrative_slate'` parameter to `HwpxBuilder.__init__`. Move palettes to `pyhwpxlib/presets.py` alongside the existing `PRESETS` dict. Replace `DS` references in `TABLE_PRESETS` with `palette['primary']` etc.

### Heading Sizes Hardcoded in api.py
- **Severity:** Medium
- Issue: `_HEADING_STYLES` in `pyhwpxlib/api.py:975–980` hardcodes heading font sizes as HWPX height values (24pt=2400, 18pt=1800, 16pt=1600, 14pt=1400). There is no way to supply custom heading sizes through the `add_heading()` API without directly calling `ensure_char_style()`.
- Files: `pyhwpxlib/api.py:975–1005`
- Impact: All documents have identical heading sizes. Document-type presets in `pyhwpxlib/presets.py` define different heading sizes (`official: 16pt h1`, `report: 18pt h1`) but these are never applied via `add_heading()`.
- Fix approach: Accept optional `height: int | None` parameter in `add_heading()`, defaulting to `_HEADING_STYLES`. Wire `HwpxBuilder.add_heading()` to pass the level-based height from an active preset.

### Font Hardcoded to 함초롬돋움
- **Severity:** Medium
- Issue: `pyhwpxlib/tools/blank_file_maker.py:258–278` hardcodes fonts 0 and 1 as `함초롬돋움` and `함초롬바탕`. The legacy `_build_header_legacy()` method in `pyhwpxlib/builder.py:388–398` also hardcodes all 7 language slots to `함초롬돋움`. HTML converter (`pyhwpxlib/html_converter.py:69`) uses the same font in CSS.
- Files: `pyhwpxlib/tools/blank_file_maker.py:258–278`, `pyhwpxlib/builder.py:391–397`
- Impact: Documents cannot use system-independent fonts (Noto Sans KR, Malgun Gothic) even if the target environment lacks Hancom bundled fonts. Low risk on Windows/macOS with Hancom installed; breaks rendering on Linux servers without the font.
- Fix approach: Add `font_hangul: str = '함초롬돋움'` / `font_latin: str = '함초롬돋움'` parameters to `BlankFileMaker.make()`. Propagate from `HwpxBuilder.__init__`.

### Legacy `_build_header_legacy` Dead Code
- **Severity:** Low
- Issue: `pyhwpxlib/builder.py:388–454` contains `_build_header_legacy()` and `_build_section()` methods that are never called — the docstring on line 386 says "(legacy … removed)". These methods reference `self._char_styles` and `self._paragraphs` which do not exist on `HwpxBuilder`.
- Files: `pyhwpxlib/builder.py:388–471`
- Impact: Dead code adds confusion; if called, would raise `AttributeError`.
- Fix approach: Delete `_build_header_legacy()` and `_build_section()` from `builder.py`.

---

## Known Bugs

### hwp2hwpx.py BinData Decompression Silently Corrupts Data
- **Severity:** High
- Issue: `_HWPDocument._decompress()` in `pyhwpxlib/hwp2hwpx.py:419–425` catches `zlib.error` from the raw-deflate path and falls back to `zlib.decompress(raw)` (zlib-wrapped). If both fail, the exception propagates uncaught from `_decompress()`. At the call sites in `_attach_binary_data()` (line 987) and `_parse_stream()` (line 429), there is no per-stream try/except, so a single corrupt BinData stream in a HWP file causes the entire conversion to abort with a traceback rather than skipping the attachment and logging a warning.
- Files: `pyhwpxlib/hwp2hwpx.py:419–425`, `pyhwpxlib/hwp2hwpx.py:979–991`
- Trigger: Any HWP file whose embedded binary streams (images, OLE objects) use an unexpected compression format or are truncated.
- Fix approach: Wrap individual stream reads in `_attach_binary_data()` with `try/except Exception`: log a warning and set `attachments[key] = b''` on failure. This matches the existing `logger.warning` pattern at line 990.

### header/footer SecPr Order Bug (Whale)
- **Severity:** High
- Issue: `HwpxBuilder.save()` defers `header`, `footer`, and `page_number` actions to the end of the action list (lines 491–493 in `pyhwpxlib/builder.py`) to work around a Whale rendering bug where inserting header/footer before `SecPr` causes a corrupted document. The deferred order is documented as intentional but there is no test verifying that this ordering is preserved across refactors.
- Files: `pyhwpxlib/builder.py:491–494`
- Impact: If the deferred separation is removed or changed in a refactor, header/footer insertion will silently revert to the broken order. No test catches this regression.
- Fix approach: Add a unit test in `tests/test_hwpx_builder.py` asserting that `add_header()` / `add_footer()` calls always appear after body content in the serialized XML.

### `from_json` decoder drops all text formatting
- **Severity:** High
- Issue: `pyhwpxlib/json_io/decoder.py:from_json()` (lines 40–62) reconstructs documents by calling `b.add_paragraph(c.text)` for every run, ignoring `char_shape_id`. Bold, italic, font size, text color, and alignment encoded in the JSON are all silently discarded. The schema stores `char_shape_id` as an integer ID referencing the source document's header, but the decoder never resolves it.
- Files: `pyhwpxlib/json_io/decoder.py:40–62`
- Impact: Round-tripping a document through `to_json → from_json` strips all character-level formatting. Using `from_json` for document reconstruction produces a plain-text-only output.
- Fix approach: Encode resolved style hints (bold, height, color) into the JSON at export time in `encoder.py`, then apply them in `from_json`. The `style_hint` field in `overlay.py` shows a working pattern for this.

### `apply_overlay` text replacement is fragile (substring collision)
- **Severity:** Medium
- Issue: `pyhwpxlib/json_io/overlay.py:apply_overlay()` (lines 406–426) replaces text by constructing raw XML fragments `>original<` and `>new_value<` and calling `xml.replace(old_fragment, new_fragment, 1)`. If the original text appears in an attribute value, comment, or other context, it may match incorrectly. Multi-line text values (containing `\n`) will never match because XML element text is always on a single line. The replacement does not handle XML-escaped characters (`&amp;`, `&lt;`, `&gt;`).
- Files: `pyhwpxlib/json_io/overlay.py:406–426`
- Impact: Edits silently fail when: (a) the original text contains special XML characters, (b) the text spans multiple `<hp:t>` elements (whitespace normalization in `_extract_cell_full_text` joins them with spaces but the original XML may not have a space), or (c) duplicate strings appear in the document.
- Fix approach: Use `xml.etree.ElementTree` to locate the exact `<hp:t>` element by paragraph index and run index (the `location` field in the overlay) rather than doing raw string replacement.

---

## Security Considerations

### MCP server project path hardcoded to local dev machine
- **Severity:** Medium
- Risk: `pyhwpxlib/mcp_server/server.py:27` computes `_PROJECT_ROOT` relative to `__file__`, and the MCP instructions (lines 59–60) hardcode `/Users/leeeunmi/Projects/active/hwpx-skill` as the project root path, including as the default output directory for generated files.
- Files: `pyhwpxlib/mcp_server/server.py:27, 59`
- Current mitigation: The `_abs()` helper converts relative paths using `_PROJECT_ROOT`, so absolute paths work. But the hardcoded path in the instruction string causes incorrect guidance when the server runs on Oracle Cloud or any other machine.
- Recommendations: Replace the hardcoded path in the instruction string with a dynamic `{_PROJECT_ROOT}` substitution at server startup.

### Oracle Cloud MCP server potentially redundant / unmonitored
- **Severity:** Medium
- Risk: `docs/oracle-cloud-deployment.md` documents a live production MCP server at `https://hangul-docs.lchfkorea.com` (IP `158.180.83.142`). The server uses Bearer token auth (`HANGUL_DOCS_TOKEN` env var) but there is no indication of rate limiting, audit logging, or health monitoring beyond a `/health` endpoint. The deployment document is dated 2026-04-16 (tomorrow relative to analysis date), suggesting it was written speculatively or pre-committed.
- Files: `docs/oracle-cloud-deployment.md`
- Current mitigation: Bearer token provides basic access control.
- Recommendations: Confirm whether the remote server and local MCP server are intended to coexist. If the remote server duplicates local functionality, document the intended split. Add rate limiting and audit logging before treating it as production.

---

## Performance Bottlenecks

### hwp2hwpx.py: 4347-line monolithic file
- **Severity:** Medium
- Problem: `pyhwpxlib/hwp2hwpx.py` is 4347 lines and handles OLE parsing, record decoding, HWPX model construction, shape/table/paragraph rendering, and file writing in a single module. Build time for full conversion scales with document complexity, and debugging requires navigating deeply nested call stacks.
- Files: `pyhwpxlib/hwp2hwpx.py`
- Cause: Organic growth ported from Java/C++ reference implementations without decomposition into sub-modules.
- Improvement path: Extract `_HWPDocument` (OLE reader) → `hwp_reader.py` or `pyhwpxlib/hwp/reader.py`. Extract shape/table builders to `hwp_shape_builder.py`. No immediate performance impact but significantly reduces cognitive load.

### apply_overlay and patch both use subprocess for unpack/repack
- **Severity:** Medium
- Problem: `pyhwpxlib/json_io/overlay.py:apply_overlay()` and `pyhwpxlib/json_io/decoder.py:patch()` both spawn two subprocess calls (unpack + repack) via `sys.executable -m pyhwpxlib unpack/pack`. Each subprocess call launches a new Python interpreter.
- Files: `pyhwpxlib/json_io/overlay.py:391–447`, `pyhwpxlib/json_io/decoder.py:96–125`
- Cause: Reuse of CLI commands instead of direct API calls.
- Improvement path: Replace subprocess calls with direct `zipfile` operations: read target section XML, apply changes, write back to a new ZIP. The `zipfile` module is already imported in both files.

---

## Fragile Areas

### json_io/ — Zero Test Coverage
- **Severity:** Critical
- Files: `pyhwpxlib/json_io/encoder.py`, `pyhwpxlib/json_io/decoder.py`, `pyhwpxlib/json_io/overlay.py`, `pyhwpxlib/json_io/schema.py`
- Why fragile: The entire `json_io` package (encoder, decoder, overlay, schema) has zero test files. Searching `tests/` for `json_io`, `extract_overlay`, `apply_overlay`, `to_json`, and `from_json` returns no matches. The `overlay.py` module was introduced recently and is the most complex path, but has no golden-file tests.
- Safe modification: Any change to `encoder.py` or `overlay.py` should be accompanied by at least a smoke test that round-trips a known HWPX file through `extract_overlay → apply_overlay` and verifies text is replaced.
- Test coverage: None.

### apply_overlay SHA256 verification only at entry
- **Severity:** Medium
- Files: `pyhwpxlib/json_io/overlay.py:376–385`
- Why fragile: SHA256 check guards against using an overlay on a changed source file, but after the check passes and the subprocess unpacks the file, there is no verification that the unpacked XML matches the state at extract time. If the unpack step introduces encoding differences (BOM, line endings), the raw-string replacement silently fails.
- Safe modification: After unpacking, verify that the section XML sha256 matches the `source_sha256` stored in the overlay before applying edits.

### `raw_xml_content` bypass
- **Severity:** Medium
- Files: Used in 91 locations across `pyhwpxlib/`
- Why fragile: Tables, shapes, columns, and other block elements are built as raw XML strings stored in `para.raw_xml_content`. The writer emits these strings verbatim without validation. A formatting mistake in any `build_*_xml()` function produces invalid XML that Whale silently rejects or crashes on, with no Python-level error.
- Safe modification: When modifying `pyhwpxlib/writer/shape_writer.py` or any `build_*_xml()` function, validate the produced XML string with `xml.etree.ElementTree.fromstring()` in a unit test before shipping.

---

## Scaling Limits

### Temp files accumulate in api_server
- **Severity:** Low
- Files: `api_server/main.py:35–40`
- Current capacity: `_TMP_DIR` is created once at module load with `tempfile.mkdtemp()`. Every API call creates new files in this directory via `_tmp()` but nothing cleans them up after `FileResponse` is sent.
- Limit: Disk space. On a 30GB Oracle Cloud VM (47% used per `docs/oracle-cloud-deployment.md`) this will fill up over time under load.
- Scaling path: Add a background cleanup task (FastAPI `lifespan`) or use `BackgroundTasks` to delete output files after the response is sent.

---

## Dependencies at Risk

### `OleFileIO_PL.py` vendored legacy package
- **Severity:** Low
- Risk: `pyhwpxlib/vendor/` contains or references `OleFileIO_PL.py` (appeared in the file listing). This is an old vendored fork of `olefile`. The maintained package is `olefile` on PyPI.
- Impact: Security patches and Python 3.12+ compatibility fixes from upstream `olefile` are not applied.
- Migration plan: Replace `OleFileIO_PL` import in `pyhwpxlib/hwp2hwpx.py` with `import olefile` and add `olefile` to `pyproject.toml` dependencies.

---

## Missing Critical Features

### No theme/palette API
- Problem: `skill/references/design_guide.md` defines 10 named color palettes for different document types. `HwpxBuilder` exposes only the single Administrative Slate palette via `DS` and `TABLE_PRESETS`. There is no `HwpxBuilder(palette='forest_growth')` or equivalent.
- Blocks: Any document that should not look like a government-blue report (environmental reports, marketing materials, academic papers) requires the caller to manually override every cell color, heading color, and line color.

### No checkbox support in form_pipeline
- Problem: `templates/form_pipeline.py` handles table cell text fill and label matching, but there is no handling for HWPX form checkbox objects (`<hp:formObject>`). The `pyhwpxlib/objects/section/objects/form_objects.py` file exists in the model but is not wired into the form fill pipeline.
- Blocks: Government forms with checkbox fields (선택 항목) cannot be filled programmatically.

---

## Test Coverage Gaps

### overlay.py — No tests at all
- What's not tested: `extract_overlay()`, `apply_overlay()`, image replacement, nested table extraction, SHA256 mismatch rejection.
- Files: `pyhwpxlib/json_io/overlay.py`
- Risk: Silent data corruption on text replacement, image replacement, or nested table editing goes undetected until a user reports a broken document.
- Priority: **Critical**

### encoder.py / decoder.py — No tests at all
- What's not tested: `to_json()` round-trip fidelity, `from_json()` reconstruction, multi-section documents, documents with images.
- Files: `pyhwpxlib/json_io/encoder.py`, `pyhwpxlib/json_io/decoder.py`
- Risk: `from_json` already confirmed to drop all formatting; without tests this regresses undetected.
- Priority: **High**

### api_server/main.py — No integration tests
- What's not tested: `/convert/md-to-hwpx`, `/form/clone`, `/form/fill` endpoints.
- Files: `api_server/main.py`
- Risk: FastAPI endpoint regressions, temp file cleanup behavior, file upload handling.
- Priority: **Medium**

### header/footer deferred ordering
- What's not tested: The invariant that `add_header()` / `add_footer()` appear after body content in the emitted section XML.
- Files: `pyhwpxlib/builder.py:491–494`
- Risk: Refactoring the action playback loop silently reintroduces the Whale SecPr bug.
- Priority: **High**

---

*Concerns audit: 2026-04-15*
