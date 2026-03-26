# cli-anything-hwpx

CLI harness for Hancom Office HWPX document manipulation, built with the [CLI-Anything](https://github.com/HKUDS/CLI-Anything) methodology.

## What is HWPX?

HWPX is the modern document format used by Hancom Office (한컴오피스), the most popular office suite in South Korea. HWPX files are ZIP archives containing XML documents following the OWPML/OPC specification.

## Features

- **Document lifecycle**: Create, open, save HWPX files
- **Text operations**: Extract, find, replace text content
- **Tables**: Add and inspect tables
- **Images**: Add, list, remove embedded images
- **Export**: Convert to plain text, Markdown, or HTML
- **Validation**: XSD schema and OPC package validation
- **Structure**: Sections, headers, footers, bookmarks, hyperlinks
- **Undo/Redo**: Up to 50-level undo stack
- **REPL**: Interactive editing mode with styled prompts
- **JSON mode**: Structured output for AI agent consumption

## Installation

```bash
# From PyPI (when published)
pip install cli-anything-hwpx

# From source
git clone <repo>
cd hwpx/agent-harness
pip install -e .
```

## Requirements

- Python >= 3.10
- python-hwpx >= 2.8.0
- click >= 8.0.0
- prompt-toolkit >= 3.0.0

## Quick Start

```bash
# Create and edit
cli-anything-hwpx document new --output report.hwpx
cli-anything-hwpx text add "Hello, HWPX!"
cli-anything-hwpx document save

# Extract content
cli-anything-hwpx --file report.hwpx text extract --format markdown

# Interactive mode
cli-anything-hwpx repl
```

## Architecture

```
cli_anything/hwpx/
├── hwpx_cli.py          # Click-based CLI with REPL
├── core/
│   ├── session.py       # Undo/redo session management
│   ├── document.py      # Document create/open/save
│   ├── text.py          # Text extract/find/replace
│   ├── table.py         # Table operations
│   ├── image.py         # Image operations
│   ├── export.py        # Export to text/md/html
│   ├── validate.py      # Schema and package validation
│   └── structure.py     # Sections, headers, bookmarks
├── utils/
│   └── repl_skin.py     # Branded REPL interface
├── skills/
│   └── SKILL.md         # AI agent discovery
└── tests/
    └── TEST.md          # Test plan and results
```

## License

MIT
