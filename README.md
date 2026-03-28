# hwpx-skill

Tell an AI what you want, get a formatted Hancom Office document. No Hancom Office installation required.

[**한국어 문서**](README_KO.md)

## The main idea

Describe your document in plain language to any LLM (Claude Code, Cursor, ChatGPT, ...) and it generates a `.hwpx` file using this skill's CLI commands:

```
You: "3분기 매출 보고서를 만들어줘. 제목, 개요, 월별 매출 표,
      핵심 성과 3개를 글머리표로, 마지막에 요약."

AI → runs CLI commands → report.hwpx (ready to open in Hancom Office)
```

The AI agent reads the CLI skill metadata, picks the right commands (`document new`, `style add`, `table add`, `structure bullet-list`, ...), and assembles the document. You get a formatted `.hwpx` file without writing any code or opening Hancom Office.

This also works with the **Web UI** -- type instructions in the LLM tab and download the result.

## Other ways to create documents

**Convert from Markdown** -- one command, automatic formatting:

```bash
cli-anything-hwpx convert report.md -o report.hwpx
```

The converter understands headings, bold/italic, bullet lists, numbered lists, code blocks, tables, hyperlinks, and horizontal rules.

**Build step by step** from the CLI:

```bash
# Create a blank document
cli-anything-hwpx document new -o report.hwpx

# Add styled text
cli-anything-hwpx --file report.hwpx style add "Project Report" --bold --font-size 16

# Add a table with data
cli-anything-hwpx --file report.hwpx table add -r 3 -c 2 \
  -h "Name,Role" -d "Alice,Engineer" -d "Bob,Designer"

# Add a code block
cli-anything-hwpx --file report.hwpx structure code-block \
  "def hello():\n    print('hello')" --lang python

# Set 2-column layout
cli-anything-hwpx --file report.hwpx structure set-columns -n 2

# Extract text back out
cli-anything-hwpx --file report.hwpx text extract
```

## Installation

```bash
git clone https://github.com/ratiertm/hwpx-skill.git
cd hwpx-skill/hwpx/agent-harness
pip install -e .
```

Requires Python 3.10+.

## All commands

### Document

| Command | Example | What it does |
|---------|---------|-------------|
| `document new` | `document new -o my.hwpx` | Create a blank document |
| `document open` | `document open my.hwpx` | Open an existing file |
| `document save` | `document save output.hwpx` | Save to a path |
| `document info` | `document info` | Show sections, paragraphs, images count |

### Text

| Command | Example | What it does |
|---------|---------|-------------|
| `text add` | `text add "Hello"` | Add a paragraph |
| `text extract` | `text extract` | Print all text |
| `text find` | `text find "keyword"` | Search for text |
| `text replace` | `text replace --old "draft" --new "final"` | Find and replace |

### Styling

| Command | Example | What it does |
|---------|---------|-------------|
| `style add` | `style add "Title" -b -s 16 -c "#0000FF"` | Bold, 16pt, blue text |

### Tables

| Command | Example | What it does |
|---------|---------|-------------|
| `table add` | `table add -r 3 -c 2 -h "A,B" -d "1,2"` | Create table with data |
| `table list` | `table list` | List all tables |
| `table set-bgcolor` | `table set-bgcolor -r 0 -c 0 --color "#FFD700"` | Cell background color |
| `table set-gradient` | `table set-gradient -r 0 -c 0 --start "#FF0000" --end "#0000FF"` | Gradient fill |

### Structure

| Command | Example | What it does |
|---------|---------|-------------|
| `structure set-header` | `structure set-header "Company Name"` | Page header |
| `structure set-footer` | `structure set-footer "Page Footer"` | Page footer |
| `structure page-number` | `structure page-number` | Add page numbers |
| `structure bookmark` | `structure bookmark "ch1"` | Insert bookmark |
| `structure hyperlink` | `structure hyperlink "https://..." -t "Link"` | Insert hyperlink |
| `structure code-block` | `structure code-block "print(1)" --lang python` | Code with monospace font + background |
| `structure set-columns` | `structure set-columns -n 2 --separator SOLID` | Multi-column layout |
| `structure bullet-list` | `structure bullet-list "A,B,C"` | Bullet list |
| `structure numbered-list` | `structure numbered-list "First,Second"` | Numbered list |
| `structure nested-bullet-list` | `structure nested-bullet-list "0:A,1:Sub"` | Nested bullets |
| `structure footnote` | `structure footnote "See note"` | Footnote |
| `structure rectangle` | `structure rectangle -w 14400 -h 7200` | Rectangle shape |
| `structure ellipse` | `structure ellipse` | Ellipse shape |
| `structure line` | `structure line` | Horizontal line |
| `structure equation` | `structure equation "E=mc^2"` | Math equation |

### Convert

| Command | Example | What it does |
|---------|---------|-------------|
| `convert` | `convert report.md -o report.hwpx` | MD/HTML/TXT to HWPX |

Markdown conversion handles: `# heading`, `**bold**`, `*italic*`, `` `code` ``, `[link](url)`, `- bullets`, `1. numbers`, ` ``` code blocks ``` `, `| tables |`, `> blockquote`, `---` rules.

### Export

| Command | Example | What it does |
|---------|---------|-------------|
| `export text` | `export text -o out.txt` | Export as plain text |
| `export markdown` | `export markdown -o out.md` | Export as Markdown |
| `export html` | `export html -o out.html` | Export as HTML |

### Other

| Command | What it does |
|---------|-------------|
| `undo` / `redo` | Undo/redo up to 50 levels |
| `validate schema` | Validate XML against OWPML schema |
| `validate package` | Validate ZIP/OPC structure |
| `repl` | Enter interactive editing mode |

## Web UI

A browser interface with three modes:

```bash
cd hwpx/agent-harness
pip install fastapi uvicorn python-multipart
python -m uvicorn web.server:app --port 8080
```

- **Direct Input** -- type text, pick font size, download `.hwpx`
- **LLM Instruction** -- describe what you want, AI generates the document
- **File Upload** -- drag in MD/HTML/TXT, get `.hwpx` back

## Python API

For programmatic use without the CLI:

```python
from hwpx import HwpxDocument

doc = HwpxDocument.new()

# Styled heading
title = doc.ensure_run_style(bold=True, height=1600)
doc.add_paragraph("Project Report", char_pr_id_ref=title)

# Bullet list
doc.add_bullet_list(["Phase 1", "Phase 2", "Phase 3"])

# Code block
doc.add_code_block('print("hello")', language="python")

# Table with gradient header
tbl = doc.add_table(3, 2)
tbl.set_cell_text(0, 0, "Name")
tbl.set_cell_text(0, 1, "Value")
doc.set_cell_gradient(0, 0, 0,
    start_color="#4A90D9", end_color="#1A5276")

# 2-column layout
doc.set_columns(2, separator_type="SOLID")

# Hyperlink
doc.add_hyperlink("Click here", "https://example.com")

# Save
doc.save_to_path("report.hwpx")
```

## What is HWPX?

HWPX is the modern document format for Hancom Office, the standard office suite in South Korea. It is a ZIP archive containing XML files following the OWPML specification -- similar in concept to `.docx` for Microsoft Word.

This project lets you create and edit HWPX files with pure Python, no Hancom Office installation needed.

## Credits

- [python-hwpx](https://github.com/airmang/python-hwpx) by Kyuhyun Koh (MIT)
- [CLI-Anything](https://github.com/HKUDS/CLI-Anything) (MIT)

## License

MIT
