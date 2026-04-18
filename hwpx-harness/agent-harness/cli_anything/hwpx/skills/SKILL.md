---
name: cli-anything-hwpx
description: CLI harness for reading, editing, creating, and validating Hancom Office HWPX documents. Supports text extraction, find/replace, tables, images, export to text/markdown/html, schema validation, undo/redo, and interactive REPL.
---

# cli-anything-hwpx

CLI tool for Hancom Office HWPX document manipulation. No Hancom Office installation required.

## Installation

```bash
pip install cli-anything-hwpx
# Or from source:
cd hwpx/agent-harness && pip install -e .
```

## Quick Start

```bash
# Create a new document
cli-anything-hwpx document new --output report.hwpx

# Open and extract text
cli-anything-hwpx --file report.hwpx text extract

# Export to Markdown
cli-anything-hwpx --file report.hwpx export markdown -o report.md

# Interactive mode
cli-anything-hwpx repl
```

## Command Groups

| Group | Commands | Description |
|-------|----------|-------------|
| `document` | new, open, save, info | Document lifecycle management |
| `text` | extract, find, replace, add | Text content operations |
| `table` | add, list | Table creation and inspection |
| `image` | add, list, remove | Image management |
| `export` | text, markdown, html | Export to various formats |
| `validate` | schema, package | Document and package validation |
| `structure` | sections, add-section, set-header, set-footer, bookmark, hyperlink | Document structure |
| `undo` | — | Undo last change |
| `redo` | — | Redo last undo |
| `repl` | — | Interactive REPL mode |

## Global Options

| Option | Description |
|--------|-------------|
| `--json` | Output as structured JSON (for agent consumption) |
| `--file PATH` | Open a .hwpx file before running the command |

## Usage Examples

### Document Management
```bash
cli-anything-hwpx document new --output blank.hwpx
cli-anything-hwpx document open existing.hwpx
cli-anything-hwpx document save output.hwpx
cli-anything-hwpx document info
```

### Text Operations
```bash
cli-anything-hwpx text extract
cli-anything-hwpx text extract --format markdown
cli-anything-hwpx text find "검색어"
cli-anything-hwpx text replace --old "초안" --new "최종본"
cli-anything-hwpx text add "새 문단 텍스트"
```

### Table & Image
```bash
cli-anything-hwpx table add --rows 3 --cols 4
cli-anything-hwpx table list
cli-anything-hwpx image add photo.png --width 100 --height 80
cli-anything-hwpx image list
cli-anything-hwpx image remove 0
```

### Export
```bash
cli-anything-hwpx export text -o output.txt
cli-anything-hwpx export markdown -o output.md
cli-anything-hwpx export html -o output.html
```

### Validation
```bash
cli-anything-hwpx validate schema document.hwpx
cli-anything-hwpx validate package document.hwpx
```

### Structure
```bash
cli-anything-hwpx structure sections
cli-anything-hwpx structure add-section
cli-anything-hwpx structure set-header "Page Header"
cli-anything-hwpx structure set-footer "Page Footer"
cli-anything-hwpx structure bookmark "chapter1"
cli-anything-hwpx structure hyperlink "https://example.com" --text "Link"
```

## JSON Output Mode

All commands support `--json` for structured output:

```bash
cli-anything-hwpx --json --file doc.hwpx document info
# {"sections": 2, "paragraphs": 15, "images": 3, "text_length": 4520, ...}

cli-anything-hwpx --json --file doc.hwpx text find "keyword"
# [{"section": 0, "paragraph": 3, "run": 0, "text": "...keyword..."}]
```

## Agent Guidance

- Always use `--json` flag for machine-readable output
- Open a document first with `document open` or `--file` before other operations
- Use `undo` after mistakes — up to 50 levels supported
- For batch processing, chain commands with `--file` flag
- HWPX format is ZIP + XML — no proprietary binary format
- Requires `python-hwpx>=2.8.0` library (auto-installed)
