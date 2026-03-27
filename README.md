# hwpx-skill

AI agents create, edit, and validate Hancom Office HWPX documents via CLI — no Hancom Office installation required.

Built with the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) framework wrapping [python-hwpx](https://github.com/airmang/python-hwpx), enabling Claude Code, Cursor, OpenClaw, and other AI agents to manipulate `.hwpx` documents through command-line interfaces.

[**한국어 문서**](README_KO.md)

## Architecture

```
AI Agent (Claude Code, Cursor, OpenClaw, ...)
    │  CLI commands
    ▼
cli-anything-hwpx (agent-harness)
    │  Python API calls
    ▼
python-hwpx (HwpxDocument)
    │  XML manipulation
    ▼
.hwpx file (ZIP + XML, OWPML spec)
```

| Layer | Role | Directory |
|-------|------|-----------|
| **CLI-Anything** | Framework for wrapping any software as agent-ready CLI | `cli-anything-original/` |
| **python-hwpx** | Pure Python library for reading/writing HWPX files | `python-hwpx-fork/`, `ratiertm-hwpx/` |
| **agent-harness** | CLI skill combining the two above (core of this project) | `hwpx/agent-harness/` |
| **Web UI** | FastAPI server with browser-based document generation | `hwpx/agent-harness/web/` |

## Installation

```bash
cd hwpx/agent-harness
pip install -e .
```

Requirements: Python >= 3.10, python-hwpx >= 2.8.0, click >= 8.0.0

## Quick Start

```bash
# Create a new document
cli-anything-hwpx document new --output report.hwpx

# Add text (auto-saves to file)
cli-anything-hwpx --file report.hwpx text add "Program Structure Design"

# Add a table with header and data
cli-anything-hwpx --file report.hwpx table add -r 3 -c 2 \
  -h "Name,Role" \
  -d "CLI-Anything,Framework" \
  -d "python-hwpx,Library"

# Convert Markdown to HWPX
cli-anything-hwpx convert README.md -o readme.hwpx

# Extract text
cli-anything-hwpx --file report.hwpx text extract
```

## Web UI

A browser-based interface for document generation, LLM instruction, and file conversion.

```bash
cd hwpx/agent-harness
pip install fastapi uvicorn python-multipart
python -m uvicorn web.server:app --port 8080
# Open http://localhost:8080
```

Three tabs:
- **Direct Input** — type content, select title font size, generate HWPX
- **LLM Instruction** — write natural language instructions for AI-generated documents
- **File Upload** — upload HTML/MD/TXT files and convert to HWPX

## Commands

| Group | Commands | Description |
|-------|----------|-------------|
| `document` | new, open, save, info | Document lifecycle |
| `text` | extract, find, replace, add | Text operations |
| `table` | add (--header, --data), list | Table with data support |
| `image` | add, list, remove | Image management |
| `export` | text, markdown, html | Export to formats |
| `convert` | (source file) -o output.hwpx | HTML/MD/TXT → HWPX |
| `validate` | schema, package | Document validation |
| `structure` | sections, add-section, set-header, set-footer, bookmark, hyperlink | Document structure |
| `undo` / `redo` | — | Up to 50-level undo |
| `repl` | — | Interactive editing mode |

## Features

- **Auto-save in one-shot mode** — `--file` flag persists changes after each mutation command
- **Table with data** — `table add -h "A,B" -d "1,2" -d "3,4"` fills cells via `set_cell_text()`
- **File conversion** — `convert source.md -o output.hwpx` supports HTML, Markdown, plain text
- **Font size support** — `ensure_run_style(height=2000)` for 20pt text (OWPML spec: 100 hwpunit = 1pt)
- **Text color** — `ensure_run_style(text_color="#FF0000")` for colored text
- **JSON output** — `--json` flag for structured agent-consumable output
- **Cross-platform** — Windows, macOS, Linux, CI/CD (pure Python, no Hancom Office needed)

## Font Size (OWPML Spec)

python-hwpx fork (`ratiertm-hwpx/`) extends `ensure_run_style()` with font size and color:

```python
from hwpx import HwpxDocument

doc = HwpxDocument.new()

# 20pt bold title
title = doc.ensure_run_style(bold=True, height=2000)
doc.add_paragraph("Title", char_pr_id_ref=title)

# 12pt blue text
blue = doc.ensure_run_style(height=1200, text_color="#0000FF")
doc.add_paragraph("Blue text", char_pr_id_ref=blue)

doc.save_to_path("styled.hwpx")
```

Height unit: 1 hwpunit = 1/100 pt (OWPML `<hh:charPr height="1000">` = 10pt)

## What is HWPX?

HWPX is the modern document format for Hancom Office, the dominant office suite in South Korea.

- **Format**: ZIP archive containing XML documents (OWPML/OPC specification)
- **Structure**: `mimetype`, `META-INF/container.xml`, `Contents/` (body), `BinData/` (images/fonts), `header.xml` (metadata)
- **Replaces**: Legacy binary `.hwp` format

## Project Structure

```
hwpx-skill/
├── hwpx/agent-harness/          # Core — CLI skill + Web UI
│   ├── cli_anything/hwpx/
│   │   ├── hwpx_cli.py          # Click-based CLI + REPL
│   │   ├── core/                 # document, text, table, image, export, validate, structure, session
│   │   ├── utils/repl_skin.py   # REPL interface
│   │   └── skills/SKILL.md      # AI agent discovery metadata
│   ├── web/
│   │   ├── server.py            # FastAPI server
│   │   └── index.html           # Web UI
│   ├── tests/                   # 64 tests (core + autosave + convert)
│   └── setup.py
├── ratiertm-hwpx/               # python-hwpx fork (font size + color + lxml fix)
├── cli-anything-original/       # CLI-Anything framework
└── docs/                        # PDCA documents
```

## Testing

```bash
cd hwpx/agent-harness
pip install -e ".[dev]"
pytest tests/ -v
# 64 tests passing
```

## Credits

- **python-hwpx**: [github.com/airmang/python-hwpx](https://github.com/airmang/python-hwpx) by Kyuhyun Koh — MIT
- **CLI-Anything**: [github.com/HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything) — MIT

## License

MIT
