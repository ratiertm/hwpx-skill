# Codebase Structure

**Analysis Date:** 2026-04-15

## Directory Layout

```
hwpx-skill/                         # Project root
├── pyhwpxlib/                      # Core Python library (installable package)
│   ├── __init__.py                 # Exports HwpxBuilder, DS, TABLE_PRESETS
│   ├── __main__.py                 # python -m pyhwpxlib entry point
│   ├── builder.py                  # HwpxBuilder — primary high-level API
│   ├── api.py                      # Low-level object-model API functions
│   ├── cli.py                      # CLI command dispatch (pyhwpxlib console script)
│   ├── hwpx_file.py                # HWPXFile root container dataclass
│   ├── base.py                     # HWPXObject, ObjectList[T], SwitchableObject
│   ├── object_type.py              # ObjectType enum
│   ├── reader.py                   # HWPX ZIP reader → lightweight dataclasses
│   ├── style_manager.py            # ensure_* idempotent style registry
│   ├── presets.py                  # Document type presets (official, report, etc.)
│   ├── converter.py                # Format converters (HTML↔HWPX)
│   ├── html_converter.py           # HWPX → HTML
│   ├── html_to_hwpx.py             # HTML → HWPX
│   ├── hwp_reader.py               # HWP 5.x binary reader
│   ├── hwp2hwpx.py                 # HWP → HWPX converter (164KB, standalone)
│   ├── value_convertor.py          # Unit/value conversion utilities
│   ├── rhwp_bridge.py              # WASM renderer bridge (SVG preview)
│   ├── json_io/                    # JSON round-trip layer
│   │   ├── __init__.py             # Exports: to_json, from_json, patch, extract_overlay, apply_overlay
│   │   ├── encoder.py              # HWPX → JSON (to_json)
│   │   ├── decoder.py              # JSON → HWPX (from_json, patch)
│   │   ├── overlay.py              # Surgical overlay extraction/application
│   │   └── schema.py               # Dataclasses: HwpxJsonDocument, Section, Paragraph, etc.
│   ├── mcp_server/                 # MCP server for AI agent integration
│   │   ├── __init__.py
│   │   └── server.py               # FastMCP instance with 8+ registered tools
│   ├── writer/                     # Serialization: object model → XML → ZIP
│   │   ├── hwpx_writer.py          # HWPXWriter (Skeleton.hwpx + overrides)
│   │   ├── xml_builder.py          # XMLStringBuilder (port of Java original)
│   │   ├── shape_writer.py         # build_table_xml, shape XML builders
│   │   ├── container_writer.py
│   │   ├── content_hpf_writer.py
│   │   ├── manifest_writer.py
│   │   ├── masterpage_writer.py
│   │   ├── settings_writer.py
│   │   ├── version_writer.py
│   │   ├── header/                 # Header XML serialization
│   │   └── section/                # Section XML serialization
│   ├── tools/                      # Bundled binary assets
│   │   ├── blank.hwpx              # Minimal valid HWPX (used by builder.py save())
│   │   ├── Skeleton.hwpx           # Full structural template (used by HWPXWriter)
│   │   ├── _reference_header.xml   # Reference XML for header generation
│   │   └── blank_file_maker.py     # BlankFileMaker.make() → HWPXFile
│   ├── objects/                    # Object model tree (OWPML dataclasses)
│   │   ├── header/                 # HeaderXMLFile, RefList, enum_types
│   │   │   └── references/         # CharPr, ParaPr, BorderFill, Fontfaces, Style, etc.
│   │   ├── section/                # SectionXMLFile, Para, Run, T, SecPr, ctrl.py
│   │   │   └── objects/            # Table, Picture, DrawingObject, FormObjects, etc.
│   │   ├── common/                 # Shared objects (compatibility switch)
│   │   ├── content_hpf/            # ContentHPFFile (package manifest)
│   │   ├── masterpage/
│   │   ├── metainf/                # ContainerXMLFile, ManifestXMLFile
│   │   └── root/                   # SettingsXMLFile, VersionXMLFile
│   ├── constants/                  # OWPML constants
│   │   ├── namespaces.py           # Namespaces enum + module-level URI strings
│   │   ├── element_names.py
│   │   ├── attribute_names.py
│   │   ├── mime_types.py
│   │   ├── zip_entry_names.py
│   │   └── default_values.py
│   ├── vendor/                     # Bundled third-party binaries
│   │   ├── rhwp_bg.wasm            # Rust HWPX renderer (3.3MB, MIT licensed)
│   │   ├── LICENSE.rhwp.txt
│   │   └── NOTICE.md
│   └── reader/                     # (Legacy reader directory, mostly superseded by reader.py)
├── templates/                      # Form pipeline and template sources
│   ├── form_pipeline.py            # extract_form, generate_form, clone_form, fill_by_labels
│   ├── form_accuracy_test.py
│   ├── hwpx_generator.py
│   └── sources/                    # Source HWPX/OWPML template files (reference forms)
├── skill/                          # Claude skill definitions
│   ├── SKILL.md                    # Primary skill manifest (triggers, workflows, rules)
│   ├── docx_SKILL.md               # DOCX skill (separate, read-only)
│   ├── references/                 # Skill reference documents
│   │   ├── HWPX_RULEBOOK.md
│   │   ├── api_reference.md
│   │   ├── api_full.md
│   │   ├── design_guide.md         # Color palettes and design rules
│   │   ├── document_types.md
│   │   ├── editing.md
│   │   └── form_automation.md
│   ├── evals/
│   └── stitch/                     # Packaged skill bundle
├── tests/                          # Test suite
│   ├── conftest.py
│   ├── test_api_core.py
│   ├── test_api_extended.py
│   ├── test_api_server.py
│   ├── test_api_shapes.py
│   ├── test_converter.py
│   ├── test_form_fill_golden.py    # Golden-file form fill tests
│   ├── test_form_pipeline.py
│   ├── test_form_pipeline_multirun.py
│   ├── test_html_converters.py
│   ├── test_hwp2hwpx_golden.py
│   ├── test_hwpx_builder.py
│   ├── test_object_model.py
│   ├── test_refactor.py
│   ├── test_stability.py
│   ├── test_style_manager.py
│   ├── test_visual_golden.py
│   ├── test_writer_utils.py
│   ├── golden/                     # Golden reference HWPX files
│   └── output/                     # Test output artifacts
├── scripts/                        # Developer utility scripts
│   ├── preview.py                  # render_pages() — HWPX → PNG pipeline
│   ├── create.py                   # Example document creation scripts
│   ├── fill_opinion_form.py        # Form fill example
│   ├── generate_afc_q2_report.py   # Report generation example
│   ├── fix_ai_report.py
│   ├── optimize_demo_report.py
│   ├── mcp_http_server.py          # HTTP proxy for MCP server
│   ├── pack.py                     # Repack HWPX from unpacked directory
│   ├── unpack.py                   # Unpack HWPX to directory
│   ├── validate.py                 # Standalone HWPX validator
│   └── templates/                  # Script-level templates
├── api_server/                     # FastAPI REST server
│   └── main.py                     # POST /convert/md-to-hwpx, /form/clone, /form/fill
├── samples/                        # Sample HWPX documents for testing/reference
├── references/                     # Architecture and implementation reference docs
├── examples/                       # Usage examples
├── Test/                           # Ad-hoc test output directory (gitignored)
├── hwp_samples/                    # Sample HWP 5.x files for conversion testing
├── pyproject.toml                  # Package metadata, dependencies, console scripts
├── README.md
└── .planning/codebase/             # Architecture documentation (this directory)
```

## Directory Purposes

**`pyhwpxlib/`:**
- Purpose: The installable Python package. Everything a consumer needs.
- Contains: All library code, bundled assets (WASM, Skeleton.hwpx), MCP server
- Key files: `builder.py`, `api.py`, `hwpx_file.py`, `reader.py`, `style_manager.py`

**`pyhwpxlib/json_io/`:**
- Purpose: LLM-facing JSON interface. Enables document editing without XML knowledge.
- Contains: Encoder, decoder, overlay patcher, schema dataclasses
- Key files: `schema.py` (canonical types), `overlay.py` (format-preserving edits)

**`pyhwpxlib/mcp_server/`:**
- Purpose: Single-file MCP server. All AI-agent tool definitions live here.
- Contains: `server.py` only
- Key files: `server.py` — 8 `@mcp.tool()` decorated functions, workflow instructions

**`pyhwpxlib/writer/`:**
- Purpose: XML serialization. Takes object model → produces XML strings → assembles ZIP.
- Contains: Writer modules per HWPX component
- Key files: `hwpx_writer.py` (ZIP assembly), `shape_writer.py` (table XML, 57KB)

**`pyhwpxlib/tools/`:**
- Purpose: Bundled template files. Included in package via `pyproject.toml` package-data.
- Contains: `blank.hwpx` (minimal, for builder), `Skeleton.hwpx` (full structural template), reference XML
- Generated: No — these are hand-crafted and committed
- Committed: Yes

**`pyhwpxlib/vendor/`:**
- Purpose: Third-party binary. Rust-compiled WASM renderer for HWPX preview.
- Contains: `rhwp_bg.wasm` (3.3MB), license files
- Committed: Yes (binary, license verified)

**`pyhwpxlib/objects/`:**
- Purpose: Dataclass tree mirroring OWPML structure. Port of Java hwpxlib.
- Contains: One subdirectory per HWPX file type (header, section, masterpage, etc.)

**`templates/`:**
- Purpose: Form reverse-engineering pipeline. Not part of the installed package.
- Contains: `form_pipeline.py` (63KB main module), test scripts, source template files
- Key files: `form_pipeline.py` — extract, generate, clone, fill operations

**`skill/`:**
- Purpose: Claude skill definition. Loaded by Claude Desktop/Code to guide HWPX-related conversations.
- Contains: `SKILL.md` (workflow rules, trigger conditions), `references/` (design guides, API docs)
- Key files: `SKILL.md` — mandatory rules, step-by-step workflows for all 4 task types

**`tests/`:**
- Purpose: pytest test suite. Includes golden-file regression tests.
- Contains: 22 test files, `golden/` directory (reference HWPX files), `output/` (generated)
- Key files: `test_form_fill_golden.py`, `test_hwpx_builder.py`, `test_api_core.py`

**`scripts/`:**
- Purpose: Developer utilities and example scripts. Not part of the package.
- Contains: preview pipeline, pack/unpack helpers, form fill examples
- Key files: `preview.py` — the `render_pages()` function used by MCP server

**`api_server/`:**
- Purpose: Prototype REST API. Not part of the installed package.
- Contains: Single `main.py` FastAPI application

## Key File Locations

**Entry Points:**
- `pyhwpxlib/__init__.py`: Package public API — imports `HwpxBuilder`, `DS`, `TABLE_PRESETS`
- `pyhwpxlib/cli.py`: CLI dispatcher, installed as `pyhwpxlib` console script via `pyproject.toml`
- `pyhwpxlib/mcp_server/server.py`: MCP tool registration, run via `python -m pyhwpxlib.mcp_server.server`
- `pyhwpxlib/__main__.py`: `python -m pyhwpxlib` entry point

**Configuration:**
- `pyproject.toml`: Package version (`0.4.0`), optional dependency groups (`mcp`, `preview`, `images`), package-data inclusions
- `.gitignore`: Ignores `Test/`, `*.hwpx` in root, `__pycache__/`, `.venv/`

**Core Logic:**
- `pyhwpxlib/builder.py`: `HwpxBuilder` class, `DS` color tokens, `TABLE_PRESETS` — primary API
- `pyhwpxlib/api.py`: `create_document`, `save`, `add_table`, `add_paragraph`, `extract_text`, `add_heading`, `convert_md_file_to_hwpx` etc.
- `pyhwpxlib/style_manager.py`: `ensure_char_style`, `ensure_para_style`, `ensure_border_fill`
- `pyhwpxlib/hwpx_file.py`: `HWPXFile` root container
- `pyhwpxlib/json_io/overlay.py`: Most recently modified json_io file (2026-04-17) — overlay patching
- `templates/form_pipeline.py`: `extract_form`, `fill_by_labels`, `find_cell_by_label`
- `scripts/preview.py`: `render_pages(hwpx_path, out_dir)` — single function, used by MCP server

**Testing:**
- `tests/conftest.py`: Shared fixtures
- `tests/golden/`: Golden HWPX reference files for regression tests
- `tests/test_form_fill_golden.py`: Most recent test file (2026-04-14) — form fill golden tests

## Naming Conventions

**Files:**
- Snake case for Python modules: `blank_file_maker.py`, `html_to_hwpx.py`
- Descriptive prefix for test files: `test_api_core.py`, `test_form_pipeline_multirun.py`
- Uppercase for non-code documents: `SKILL.md`, `ARCHITECTURE.md`, `README.md`

**Directories:**
- Snake case or lower-hyphen: `json_io/`, `mcp_server/`, `api_server/`
- Short descriptive: `writer/`, `reader/`, `objects/`, `tools/`, `vendor/`

**Classes:**
- PascalCase: `HwpxBuilder`, `HWPXFile`, `HWPXWriter`, `XMLStringBuilder`, `RhwpEngine`
- Acronyms uppercase: `HWPXFile`, `HWPXWriter` but `HwpxBuilder` (mixed convention)

**Functions:**
- Snake case: `ensure_char_style`, `build_table_xml`, `extract_form`, `render_pages`
- `ensure_*` prefix for idempotent style creation functions
- `_with_preview` prefix (underscore) for internal MCP helpers
- `_abs()` for path resolution helpers

**Constants:**
- All-caps for module-level XML namespace shortcuts: `_HP`, `_HH`, `_HC`, `_HS`
- `DS` dict (two letters) for design system color tokens
- `TABLE_PRESETS`, `PRESETS` for preset dicts

## Where to Add New Code

**New HwpxBuilder method (e.g., add_callout):**
- Primary code: `pyhwpxlib/builder.py` — add method to `HwpxBuilder`, append action dict to `self._actions`
- Renderer: `pyhwpxlib/writer/shape_writer.py` — add XML builder function
- Wiring: `pyhwpxlib/builder.py` `save()` method — handle new action kind
- Tests: `tests/test_hwpx_builder.py`

**New api.py function:**
- Implementation: `pyhwpxlib/api.py`
- Style dependencies: `pyhwpxlib/style_manager.py` if new style types needed
- Tests: `tests/test_api_core.py` or `tests/test_api_extended.py`

**New MCP tool:**
- Add `@mcp.tool()` decorated function to `pyhwpxlib/mcp_server/server.py`
- Update `server.py` module docstring tool list
- Pattern: call `_with_preview(output_path)` before returning if tool writes a file

**New json_io capability:**
- Schema changes: `pyhwpxlib/json_io/schema.py` (update dataclasses and `from_dict`)
- Encoding: `pyhwpxlib/json_io/encoder.py`
- Decoding: `pyhwpxlib/json_io/decoder.py`
- Overlay (format-preserving): `pyhwpxlib/json_io/overlay.py`

**New form template:**
- Source file: `templates/sources/` (original HWPX/OWPML)
- Pipeline integration: `templates/form_pipeline.py` if new extraction logic needed
- Golden test: `tests/golden/` (reference output), `tests/test_form_fill_golden.py`

**New object model type:**
- Implementation: appropriate subdirectory under `pyhwpxlib/objects/`
- Follow existing pattern: `@dataclass` extending `HWPXObject`, implement `_object_type()`, `clone()`, `copy_from()`
- Writer: add corresponding writer in `pyhwpxlib/writer/`

**New preset:**
- Document type presets: `pyhwpxlib/presets.py` (PRESETS dict)
- Table presets: `pyhwpxlib/builder.py` (TABLE_PRESETS dict)

**New utility script:**
- Location: `scripts/` for developer utilities, `examples/` for usage examples
- Not included in package (only `pyhwpxlib*` dirs are packaged per `pyproject.toml`)

**New test:**
- Location: `tests/test_<module_name>.py`
- Golden file output: `tests/output/` (transient), `tests/golden/` (committed reference)

## Special Directories

**`pyhwpxlib/vendor/`:**
- Purpose: Bundled Rust-compiled WASM renderer (`rhwp_bg.wasm`, 3.3MB)
- Generated: No — downloaded/built externally
- Committed: Yes
- Required by: `pyhwpxlib/rhwp_bridge.py` and `scripts/preview.py`

**`pyhwpxlib/tools/`:**
- Purpose: Template HWPX files that seed new document creation
- Generated: No — hand-crafted baseline files
- Committed: Yes — included via `pyproject.toml` package-data

**`Test/`:**
- Purpose: Ad-hoc output directory for manual testing
- Generated: Yes (by test runs and scripts)
- Committed: No (gitignored)

**`tests/output/`:**
- Purpose: Test-generated HWPX artifacts
- Generated: Yes (by test runs)
- Committed: No

**`tests/golden/`:**
- Purpose: Reference HWPX files for regression comparison
- Generated: No — committed baseline files
- Committed: Yes

**`.planning/codebase/`:**
- Purpose: Architecture documentation for GSD planning
- Generated: Yes (by map-codebase commands)
- Committed: Yes

**`pyhwpxlib.egg-info/`:**
- Purpose: Setuptools build metadata
- Generated: Yes (`pip install -e .`)
- Committed: No

---

*Structure analysis: 2026-04-15*
