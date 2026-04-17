# External Integrations

**Analysis Date:** 2026-04-15

## APIs & External Services

**Hancom OWPML/HWPX Format:**
- The library implements the OWPML 2011 XML schema (Hancom's open format) internally. No network calls to Hancom services.
- Namespaces: `http://www.hancom.co.kr/hwpml/2011/paragraph`, `.../section`, `.../head`, `.../core`
- Defined in `pyhwpxlib/constants/namespaces.py`

**No cloud APIs or external web services** are used by the library core. All operations are local.

## Data Storage

**Databases:**
- None. Documents are read/written as `.hwpx` ZIP files on the local filesystem.

**File Storage:**
- Local filesystem only. HWPX files are ZIP archives unpacked/repacked in-process.
- Temporary files written to `/tmp` during preview rendering (see `scripts/preview.py` and `pyhwpxlib/mcp_server/server.py`)
- Template source files stored in `pyhwpxlib/tools/` (bundled as package data): `blank.hwpx`, `Skeleton.hwpx`, `_reference_header.xml`

**Caching:**
- In-process WASM engine singleton cached in `scripts/preview.py` (`_engine` global)
- Font object cache in `pyhwpxlib/rhwp_bridge.py` `_TextMeasurer._cache` (keyed by `(font_path, size_int)`)

## Authentication & Identity

**Auth Provider:**
- None. No authentication on any interface.
- The MCP server (`pyhwpxlib/mcp_server/server.py`) runs as a local stdio process with no auth.
- The FastAPI server (`api_server/main.py`) has no auth middleware.

## WASM Module

**rhwp WASM binary:**
- Bundled at `pyhwpxlib/vendor/rhwp_bg.wasm`
- Source: `rhwp` Rust project by Edward Kim, MIT licensed (see `pyhwpxlib/vendor/LICENSE.rhwp.txt`)
- Runtime: loaded via `wasmtime` Python bindings in `pyhwpxlib/rhwp_bridge.py`
- Resolution order: `RHWP_WASM_PATH` env var → bundled package resource → VS Code extension `edwardkim.rhwp-vscode-*/dist/media/rhwp_bg.wasm`
- Exports used: `hwpdocument_new`, `hwpdocument_pageCount`, `hwpdocument_renderPageSvg`, `__wbindgen_malloc`, `__wbindgen_free`, `__wbg_hwpdocument_free`, `__wbindgen_start`
- Output: SVG strings per page, then converted to PNG via `resvg-py`

## MCP Server Integration

**Server:**
- File: `pyhwpxlib/mcp_server/server.py`
- Framework: `fastmcp` (server name: `"hangul-docs"`)
- Transport: stdio (run as `python -m pyhwpxlib.mcp_server.server`)
- Registration: `claude mcp add pyhwpxlib -- python -m pyhwpxlib.mcp_server.server`

**Exposed Tools (15 total):**
| Tool | Purpose |
|------|---------|
| `hwpx_to_json` | Export HWPX section to JSON |
| `hwpx_from_json` | Create HWPX from JSON structure |
| `hwpx_patch` | Replace text in HWPX section, preserving structure |
| `hwpx_inspect` | Summarize HWPX structure (sections, paragraphs, tables) |
| `hwpx_build_step` | Incrementally build HWPX with per-step PNG preview |
| `hwpx_preview` | Render HWPX pages to PNG via rhwp WASM |
| `hwpx_fill_form` | Fill form template via label-based cell navigation |
| `hwpx_analyze_form` | Discover fillable fields in a form template |
| `hwpx_validate` | Check HWPX ZIP/XML integrity |
| `hwpx_hwp_to_hwpx` | Convert legacy `.hwp` binary to HWPX |
| `hwpx_md_to_hwpx` | Convert Markdown to HWPX |
| `hwpx_html_to_hwpx` | Convert HTML to HWPX |
| `hwpx_fill_batch` | Batch-fill one template with multiple records |
| `hwpx_build` | One-shot document build from full action list |
| `hwpx_build_preset` | Build document using named style preset |

**Preview PNG flow (all tools):** HWPX file → `scripts/preview.py:render_pages()` → `RhwpEngine` (WASM) → SVG → `resvg_py.svg_to_bytes()` → PNG bytes → base64-encoded in JSON response

## REST API

**Server:**
- File: `api_server/main.py`
- Framework: FastAPI 0.135.2
- Endpoints: `POST /convert/md-to-hwpx`, `POST /form/clone`, `POST /form/fill`
- Run: `uvicorn api_server.main:app --reload --port 8000`

## Font Integration

**System fonts (macOS fallback paths):**
- `Apple SD Gothic Neo`: `/System/Library/Fonts/AppleSDGothicNeo.ttc`
- `Helvetica`: `/System/Library/Fonts/Helvetica.ttc`
- `Arial`: `/System/Library/Fonts/Supplemental/Arial.ttf`
- `Times New Roman`: `/System/Library/Fonts/Supplemental/Times New Roman.ttf`
- `Courier New`: `/System/Library/Fonts/Supplemental/Courier New.ttf`
- Defined in `pyhwpxlib/rhwp_bridge.py` `_DEFAULT_FONT_MAP`

**Font subsetting:** `fonttools` TTF subsetting used in `pyhwpxlib/rhwp_bridge.py:_embed_fonts_in_svg()` — subsets only used characters and injects base64 `@font-face` CSS into SVG output

## Format Converters

**HWP binary → HWPX:**
- `pyhwpxlib/hwp2hwpx.py` — pure Python HWP 5.x record parser; ported from `hwp2hwpx` by neolord0 (Apache 2.0)

**Markdown → HWPX:**
- `pyhwpxlib/converter.py` — internal Markdown parser using stdlib `re`; no external Markdown library

**HTML → HWPX:**
- `pyhwpxlib/html_to_hwpx.py` — uses stdlib `html.parser.HTMLParser`; no external HTML library

**HWPX → HTML:**
- `pyhwpxlib/html_converter.py`

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, Datadog, or similar.

**Logs:**
- `logging.getLogger(__name__).addHandler(logging.NullHandler())` set in `pyhwpxlib/__init__.py`
- Modules use `logging.getLogger(__name__)` throughout; callers configure handlers

## CI/CD & Deployment

**Hosting:**
- PyPI (package distribution target; `pyproject.toml` declares homepage as `https://github.com/ratiertm/hwpx-skill`)

**CI Pipeline:**
- Not detected (no `.github/workflows/`, `Makefile`, or CI config files found)

## Environment Configuration

**Required env vars:**
- None required for core functionality

**Optional env vars:**
- `RHWP_WASM_PATH` — Override bundled WASM binary path

**Secrets location:**
- No secrets required; no `.env` file in repository

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

---

*Integration audit: 2026-04-15*
