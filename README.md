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
- **JSON output** — `--json` flag for structured agent-consumable output
- **Cross-platform** — Windows, macOS, Linux, CI/CD (pure Python, no Hancom Office needed)

## OWPML Core Coverage (Phase 1) (python-hwpx fork)

Install: `pip install git+https://github.com/ratiertm/python-hwpx.git`

### Character Properties (charPr — 18 attributes)

```python
from hwpx import HwpxDocument

doc = HwpxDocument.new()

# Font + size + color + bold
title = doc.ensure_run_style(
    font_hangul="맑은 고딕", font_latin="Arial",
    bold=True, height=2000, text_color="#1a1a2e"
)
doc.add_paragraph("Title", char_pr_id_ref=title)

# Strikeout + superscript
strike = doc.ensure_run_style(strikeout=True)
sup = doc.ensure_run_style(superscript=True, height=700)

# Per-language spacing/ratio
spaced = doc.ensure_run_style(ratio_hangul=90, spacing_hangul=-5)
```

All charPr attributes: `bold`, `italic`, `underline`, `height`, `text_color`, `shade_color`, `font_hangul`~`font_user` (7 langs), `strikeout`, `outline`, `shadow`, `emboss`, `engrave`, `superscript`, `subscript`, `sym_mark`, `use_font_space`, `use_kerning`, `spacing_*`, `ratio_*`, `rel_size_*`, `offset_*` (7 langs each)

### Paragraph Properties (paraPr — 11 attributes)

```python
# Center align + 200% line spacing
p1 = doc.ensure_para_style(align="CENTER", line_spacing=200)
doc.add_paragraph("Centered", para_pr_id_ref=p1)

# Indent + paragraph spacing
p2 = doc.ensure_para_style(indent=800, spacing_before=200, spacing_after=100)

# Combined: charPr + paraPr
doc.add_paragraph("Styled", char_pr_id_ref=title, para_pr_id_ref=p1)
```

All paraPr attributes: `align` (LEFT/CENTER/RIGHT/JUSTIFY/DISTRIBUTE), `line_spacing`, `line_spacing_type`, `indent`, `margin_left`, `margin_right`, `spacing_before`, `spacing_after`, `heading_type`, `keep_with_next`, `page_break_before`

### Table Advanced

```python
tbl = doc.add_table(4, 3)
tbl.merge_cells(0, 0, 0, 2)          # Merge first row
tbl.set_cell_text(0, 0, "Header")
tbl.cell(1, 0).set_margin(left=100)  # Cell margin
tbl.set_repeat_header(True)           # Repeat header on page break
```

### Image Inline Insert

```python
doc.insert_image("photo.png", width=28000, height=14000,
    crop_left=10, bright=20, contrast=10)
```

### Page Setup

```python
doc.set_page_setup(paper="A4", landscape=False,
    margin_left=7000, margin_right=7000)
# Presets: A4, A3, A5, B4, B5, Letter, Legal
```

### Misc

```python
doc.add_line()                          # Line shape
doc.add_rectangle(fill_color="#DBEAFE") # Rectangle
doc.add_ellipse()                       # Ellipse
doc.add_arc()                           # Arc
doc.add_equation("E = mc^2")           # Equation
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
