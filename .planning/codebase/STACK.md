# Technology Stack

**Analysis Date:** 2026-04-15

## Languages

**Primary:**
- Python 3.x — All library, CLI, MCP server, and API server code. `requires-python = ">=3.8"` in `pyproject.toml`; runtime tested on Python 3.14.3

**Secondary:**
- WebAssembly (WASM) — Bundled binary `pyhwpxlib/vendor/rhwp_bg.wasm` (compiled from Rust, MIT-licensed `rhwp` project by Edward Kim); invoked at runtime through Python `wasmtime`
- XML — Native format for OWPML/HWPX document internals; parsed via `xml.etree.ElementTree` (stdlib) and optionally `lxml`

## Runtime

**Environment:**
- CPython 3.8+ (stdlib-only core; optional deps unlock full feature set)
- macOS is the primary development platform (font fallback paths in `pyhwpxlib/rhwp_bridge.py` reference `/System/Library/Fonts/`)

**Package Manager:**
- pip / setuptools 77+
- Lockfile: not present (library project; no lockfile committed)

## Frameworks

**Core:**
- None (zero mandatory runtime dependencies; all features are opt-in via extras)

**MCP Server:**
- `fastmcp` 3.2.3 — MCP protocol server powering `pyhwpxlib/mcp_server/server.py`; installed via `pip install pyhwpxlib[mcp]`

**REST API:**
- `fastapi` 0.135.2 — FastAPI REST server in `api_server/main.py`; run via `uvicorn api_server.main:app`
- `uvicorn` — ASGI server (used for `api_server/`, not declared in `pyproject.toml`; dev dependency)

**Build/Dev:**
- `setuptools>=77` + `wheel` — Build backend declared in `pyproject.toml`
- No linting config detected (no `.eslintrc`, `ruff.toml`, `pyproject.toml` linting section, or `Makefile`)

## Key Dependencies

**All dependencies are optional** — installed via extras in `pyproject.toml`.

**`[images]`:**
- `Pillow>=9.0` (installed: 12.1.1) — Accurate text advance-width measurement in `pyhwpxlib/rhwp_bridge.py`; also used for PNG output validation

**`[lxml]`:**
- `lxml>=4.9` (installed: 5.4.0) — Optional faster XML parsing; stdlib `xml.etree.ElementTree` used when absent

**`[mcp]`:**
- `fastmcp>=0.1` (installed: 3.2.3) — MCP server framework (`pyhwpxlib/mcp_server/server.py`)

**`[preview]`:**
- `wasmtime>=20.0` (installed: 43.0.0) — Python bindings for the WebAssembly runtime that loads `rhwp_bg.wasm`
- `resvg-py>=0.1` (installed: 0.3.0) — Renders SVG output from rhwp to PNG bytes (`scripts/preview.py`)
- `fonttools>=4.0` (installed: 4.62.1) — TTF subsetting and base64 embedding of fonts into SVG (`pyhwpxlib/rhwp_bridge.py`)

**`[all]`:** meta-extra that installs all of the above

## Configuration

**Environment:**
- `RHWP_WASM_PATH` — Optional env var to override WASM binary location (see `pyhwpxlib/rhwp_bridge.py` `_find_wasm()`)
- No `.env` file or secrets required for core functionality

**Build:**
- `pyproject.toml` — single source of truth for build system, metadata, extras, entry points, and package-data globs
- Package data includes `pyhwpxlib/tools/*.hwpx`, `pyhwpxlib/tools/*.xml`, `pyhwpxlib/vendor/*.wasm`, vendor license files

## Platform Requirements

**Development:**
- Python 3.8+
- Optional extras: `pip install -e ".[all]"` for full feature set including WASM preview

**Production:**
- Distributable as a PyPI package (`name = "pyhwpxlib"`, `version = "0.4.0"`)
- CLI entry point: `pyhwpxlib` → `pyhwpxlib.cli:main`
- MCP server: `python -m pyhwpxlib.mcp_server.server`
- REST API: `uvicorn api_server.main:app`

---

*Stack analysis: 2026-04-15*
