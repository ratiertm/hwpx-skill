# Architecture

**Analysis Date:** 2026-04-15

## Pattern Overview

**Overall:** Dual-track document manipulation library — a high-level fluent Builder API that generates XML directly, and a lower-level object-model API ported from the Java hwpxlib reference implementation.

**Key Characteristics:**
- HWPX documents are ZIP archives containing OWPML-namespaced XML files
- Two parallel code paths exist: `HwpxBuilder` (XML string generation) and `api.py` (object model manipulation)
- JSON round-trip layer (`json_io`) enables LLM-friendly editing without touching XML
- WASM-based preview renderer (`rhwp_bridge.py`) closes the verification loop for generated documents
- MCP server (`mcp_server/server.py`) exposes all capabilities as tools for AI agents

## Layers

**Public API Layer:**
- Purpose: Stable entry points for users and AI agents
- Location: `pyhwpxlib/__init__.py`, `pyhwpxlib/builder.py`, `pyhwpxlib/api.py`, `pyhwpxlib/cli.py`
- Contains: `HwpxBuilder` class, standalone `api.py` functions, CLI command dispatch
- Depends on: Object model layer, writer layer, style manager
- Used by: Tests, MCP server, scripts, external consumers

**MCP Server Layer:**
- Purpose: Expose library as Claude-consumable tools via FastMCP
- Location: `pyhwpxlib/mcp_server/server.py`
- Contains: 8 registered tools — `hwpx_to_json`, `hwpx_from_json`, `hwpx_patch`, `hwpx_inspect`, `hwpx_preview`, `hwpx_build_step`, `hwpx_fill_form`, `hwpx_analyze_form`, `hwpx_validate`
- Depends on: `json_io`, `builder.HwpxBuilder`, `templates.form_pipeline`, `scripts.preview`
- Used by: Claude Desktop via `claude mcp add pyhwpxlib`

**JSON Round-Trip Layer:**
- Purpose: LLM-friendly HWPX ↔ JSON conversion without raw XML exposure
- Location: `pyhwpxlib/json_io/`
- Contains:
  - `encoder.py` — HWPX ZIP → `HwpxJsonDocument` dict (`to_json`)
  - `decoder.py` — JSON dict → new HWPX via `HwpxBuilder` (`from_json`)
  - `overlay.py` — Surgical per-field extraction and post-save replacement (`extract_overlay`, `apply_overlay`)
  - `schema.py` — Dataclasses: `HwpxJsonDocument`, `Section`, `Paragraph`, `Run`, `RunContent`, `Table`, `Preservation`
- Depends on: `builder.HwpxBuilder` (via decoder), direct ZIP/XML access (via encoder)
- Schema version string: `pyhwpxlib-json/1`

**Form Pipeline Layer:**
- Purpose: Reverse-engineer existing HWPX forms and clone/fill them exactly
- Location: `templates/form_pipeline.py`
- Contains: `extract_form`, `generate_form`, `clone_form`, `fill_by_labels`, `find_cell_by_label`
- Strategy: Extract raw XML blocks from `header.xml` (fontfaces, charProperties, borderFills), reconstruct ZIP with post-save string patching to bypass namespace rewriting
- Depends on: Direct ZIP/XML operations, `pyhwpxlib.api` for generation
- Used by: `mcp_server/server.py` (`hwpx_fill_form`, `hwpx_analyze_form`), `tests/test_form_pipeline.py`

**Object Model Layer:**
- Purpose: Typed Python dataclass tree mirroring the OWPML Java reference implementation
- Location: `pyhwpxlib/objects/`, `pyhwpxlib/hwpx_file.py`, `pyhwpxlib/base.py`
- Contains:
  - `HWPXFile` — root container holding all sub-files as typed attributes
  - `pyhwpxlib/objects/header/` — `HeaderXMLFile`, `RefList`, `CharPr`, `ParaPr`, `BorderFill`, `Fontfaces`, `Style`, `Numbering`, `TabPr`
  - `pyhwpxlib/objects/section/` — `SectionXMLFile`, `Para`, `Run`, `T`, `SecPr`, section-level control objects
  - `pyhwpxlib/base.py` — `HWPXObject` (abstract base), `ObjectList[T]` (generic typed container), `SwitchableObject`
- Depends on: `pyhwpxlib/constants/` (namespaces, element names, attribute names)
- Used by: `api.py`, `writer/`, `style_manager.py`, `tools/blank_file_maker.py`

**Writer Layer:**
- Purpose: Serialize object model tree to XML strings and assemble the final HWPX ZIP
- Location: `pyhwpxlib/writer/`
- Contains:
  - `hwpx_writer.py` — Top-level `HWPXWriter` that assembles skeleton + overrides into ZIP
  - `xml_builder.py` — Fluent `XMLStringBuilder` (port of Java original)
  - `shape_writer.py` — `build_table_xml` and shape XML builders (direct string generation)
  - `header/header_writer.py` — Serialize `HeaderXMLFile` to XML
  - `section/section_writer.py` — Serialize `SectionXMLFile` to XML
  - `content_hpf_writer.py`, `manifest_writer.py`, `masterpage_writer.py`, `settings_writer.py`, `version_writer.py`
- Depends on: Object model layer, `tools/Skeleton.hwpx` (bundled template)
- Key pattern: `HWPXWriter.to_bytes()` loads `Skeleton.hwpx` (cached via `lru_cache`), generates XML for header + sections, merges as ZIP overrides

**Style Manager Layer:**
- Purpose: Idempotent "ensure_*" functions that find or create header reference entries at runtime
- Location: `pyhwpxlib/style_manager.py`
- Contains: `ensure_char_style`, `ensure_para_style`, `ensure_border_fill`, `ensure_gradient_border_fill`, `font_size_to_height`
- Pattern: Each `ensure_*` scans existing IDs, returns existing if match found, creates new entry if not
- Depends on: `HWPXFile`, `objects/header/` enum types
- Used by: `api.py` (add_table, add_styled_paragraph), `builder.py` (via save())

**Preview / Rendering Layer:**
- Purpose: Render HWPX pages to PNG for visual verification
- Location: `pyhwpxlib/rhwp_bridge.py`, `scripts/preview.py`, `pyhwpxlib/vendor/rhwp_bg.wasm`
- Contains:
  - `RhwpEngine` — loads `rhwp_bg.wasm` via `wasmtime`, renders pages to SVG strings
  - `render_pages()` — converts SVG to PNG via `resvg_py`, writes PNG files, returns `[{page, png, fill_ratio}]`
- Depends on: `wasmtime`, `resvg_py`, optionally `Pillow` (text advance width), `fonttools`
- WASM resolution order: `RHWP_WASM_PATH` env var → bundled `vendor/rhwp_bg.wasm` → VS Code extension fallback

**Conversion Layer:**
- Purpose: Import/export between HWPX and other formats
- Location: `pyhwpxlib/converter.py`, `pyhwpxlib/html_converter.py`, `pyhwpxlib/html_to_hwpx.py`
- Contains: HTML↔HWPX converters, Markdown→HWPX pipeline (in `api.py`)
- Separate: `pyhwpxlib/hwp2hwpx.py` (164 KB) — binary HWP 5.x → HWPX conversion; `pyhwpxlib/hwp_reader.py` — HWP binary format detection and parsing

**REST API Layer:**
- Purpose: HTTP server exposing library functions
- Location: `api_server/main.py`
- Contains: FastAPI app with `POST /convert/md-to-hwpx`, `POST /form/clone`, `POST /form/fill`
- Depends on: `pyhwpxlib.api`, `templates.form_pipeline`

## Data Flow

**New Document Creation (HwpxBuilder path):**

1. `HwpxBuilder()` initialized with `table_preset`, accumulates `_actions: list[dict]`
2. `add_heading()`, `add_paragraph()`, `add_table()`, `add_image()` etc. append action dicts
3. `save(output_path)` called → replays actions via `pyhwpxlib.api` functions
4. `api.create_document()` → `tools/blank_file_maker.BlankFileMaker.make()` → `HWPXFile` with default styles
5. Each action calls `api.add_paragraph()` / `api.add_table()` etc., which call `style_manager.ensure_*()` and `writer/shape_writer.build_table_xml()`
6. `api.save()` → `writer/hwpx_writer.HWPXWriter.to_bytes()` → loads `Skeleton.hwpx`, overrides header + sections, writes ZIP
7. (Optional) `scripts.preview.render_pages()` → `rhwp_bridge.RhwpEngine` → SVG → PNG

**HWPX Editing via JSON (json_io path):**

1. `json_io.to_json(hwpx_path)` → opens ZIP, parses section XML, returns `HwpxJsonDocument` dict
2. LLM or caller edits the JSON dict (text replacement, cell updates)
3. `json_io.patch(hwpx_path, section, edits, output)` → copies ZIP, replaces text in section XML bytes directly (no object model round-trip)
4. MCP server wraps result with `_with_preview()` → auto-renders PNG and returns base64

**Form Filling (form_pipeline path):**

1. `hwpx_analyze_form(file)` → `extract_form()` parses ZIP, builds cell grid from OWPML tables
2. User provides `{"label>direction": "value"}` mappings
3. `fill_by_labels(file, mappings, output)` → `find_cell_by_label()` navigates grid → writes value into target cell XML
4. Post-save: XML string replacement restores raw header blocks (bypasses namespace rewriting by Python's ET)

**HWP → HWPX conversion:**

1. `hwp_reader.detect_format(path)` checks magic bytes
2. If HWP: `hwp2hwpx.convert(src, dst)` → binary parsing → reconstructed HWPX

**State Management:**
- `HwpxBuilder` holds stateful `_actions` list (append-only, replayed at save time)
- `HWPXFile` is an in-memory dataclass tree; no lazy loading
- `RhwpEngine` is a singleton (module-level `_engine` in `scripts/preview.py`)
- `_load_skeleton()` in `hwpx_writer.py` uses `lru_cache` to keep Skeleton.hwpx bytes in memory

## Key Abstractions

**HwpxBuilder:**
- Purpose: Declarative, LLM-friendly API for building new documents
- Examples: `pyhwpxlib/builder.py`
- Pattern: Builder accumulates action dicts; single `save()` call commits everything. Exported as `pyhwpxlib.HwpxBuilder`.

**HWPXFile:**
- Purpose: Root in-memory document tree
- Examples: `pyhwpxlib/hwpx_file.py`
- Pattern: Dataclass with typed `ObjectList[T]` fields. All sub-objects support `.clone()` and `.copy_from()`.

**ObjectList[T]:**
- Purpose: Typed list container with `add()`, `get(i)`, `items()`, `add_new()` interface
- Examples: `pyhwpxlib/base.py`
- Pattern: Port of Java `ObjectList<ItemType>`. Used throughout objects/ tree.

**HwpxJsonDocument:**
- Purpose: LLM-facing flat JSON schema
- Examples: `pyhwpxlib/json_io/schema.py`
- Pattern: Dataclasses with `to_dict()` / `from_dict()`. Format version: `pyhwpxlib-json/1`. Includes `Preservation` block for byte-accurate patching.

**ensure_* functions (style_manager):**
- Purpose: Idempotent style registry
- Examples: `pyhwpxlib/style_manager.py`
- Pattern: Each function scans header reference list for matching entry, returns existing ID or creates new one.

**TABLE_PRESETS / DS design tokens:**
- Purpose: Named visual styles for tables
- Examples: `pyhwpxlib/builder.py` lines 44–99
- Pattern: `DS` dict maps semantic names to hex colors. `TABLE_PRESETS` maps preset names to full table style configs. Preset is applied automatically in `HwpxBuilder.add_table()`.

## Entry Points

**CLI:**
- Location: `pyhwpxlib/cli.py`, installed as `pyhwpxlib` console script
- Triggers: `pyhwpxlib md2hwpx`, `hwpx2html`, `text`, `fill`, `info`, `merge`, `unpack`, `pack`, `validate`
- Responsibilities: Argument parsing, delegates to `api.py` functions

**MCP Server:**
- Location: `pyhwpxlib/mcp_server/server.py`
- Triggers: `python -m pyhwpxlib.mcp_server.server` or `claude mcp add`
- Responsibilities: Registers 8+ tools on FastMCP instance `mcp`, handles path resolution via `_abs()`, auto-attaches preview PNG to every write operation via `_with_preview()`

**Package __init__:**
- Location: `pyhwpxlib/__init__.py`
- Exports: `HwpxBuilder`, `DS`, `TABLE_PRESETS`

**REST API:**
- Location: `api_server/main.py`
- Triggers: `uvicorn api_server.main:app --reload --port 8000`
- Responsibilities: File upload/download endpoints, delegates to `api.py` and `form_pipeline`

## Error Handling

**Strategy:** Fail-fast with descriptive exceptions; no silent fallbacks in core paths.

**Patterns:**
- `RhwpWasmNotFoundError` raised with install hint when `rhwp_bg.wasm` not found
- `FileNotFoundError` raised by `HWPXWriter._load_skeleton()` if `Skeleton.hwpx` missing
- `ImportError` with pip install guidance when optional dependencies (`wasmtime`, `fastmcp`) absent
- `hwpx_validate` MCP tool provides explicit ZIP/XML integrity checks before other operations
- Namespace normalization in `reader.py` silently remaps 2016/2024 URI variants to canonical 2011 URIs

## Cross-Cutting Concerns

**Logging:** `logging.getLogger(__name__)` in all modules; library-level null handler in `__init__.py`

**Validation:** `scripts/validate.py` and `hwpx_validate` MCP tool check ZIP structure, mimetype entry order, required files (`Contents/header.xml`, `Contents/section0.xml`, `mimetype`), and XML parseability

**Namespace handling:** OWPML uses four primary namespaces — `hp` (paragraph), `hs` (section), `hh` (head/header), `hc` (core). Defined as module-level constants in each file (`_HP`, `_HH`, etc.) and as a canonical `Namespaces` enum in `pyhwpxlib/constants/namespaces.py`. Python's `xml.etree.ElementTree` rewrites namespace prefixes on serialization; the form pipeline bypasses this with raw string replacement.

**Units:** All dimensions in HWPX units (1/7200 inch). 1mm ≈ 283 HWPX units. A4 = 59528 × 84186 or 84188. Content width at standard margins = 42520.

**Preview enforcement:** The MCP server's `_with_preview()` helper is called on every write operation. The FastMCP `instructions` block encodes mandatory workflow rules for the consuming LLM.

---

*Architecture analysis: 2026-04-15*
