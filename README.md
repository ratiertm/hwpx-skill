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

The **Web UI** also works -- type what you want in the LLM tab, Claude generates it, and you download the `.hwpx`. Uses Claude Code's OAuth session, no API key needed.

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
- **LLM Instruction** -- describe what you want in natural language, Claude generates a formatted document
- **File Upload** -- drag in MD/HTML/TXT, get `.hwpx` back

Requires [Claude Code](https://claude.ai/claude-code) installed and authenticated (`claude auth login`).

## CSS-Driven Document Styling

HWPX documents are styled using standard CSS files. The converter reads CSS properties and maps them to HWPX XML attributes -- so you control the output by editing CSS.

### Built-in presets

4 CSS files in `hwpx/agent-harness/web/styles/`:

| File | Style | Source |
|------|-------|--------|
| `github.css` | GitHub Flavored Markdown | [github-markdown-css](https://github.com/sindresorhus/github-markdown-css) |
| `vscode.css` | VS Code Markdown Preview | VS Code built-in |
| `minimal.css` | Clean, no decorations | Custom |
| `academic.css` | Formal/academic documents | Custom |

### How it works

CSS properties are parsed and mapped to HWPX values automatically:

```css
/* Edit github.css to change the output */
h1  { font-size: 2em; border-bottom: 1px solid #d1d9e0; }  /* → charPr height=2000, bold */
h2  { font-size: 1.5em; }                                   /* → charPr height=1500 */
pre { background: #f6f8fa; font-size: 85%; }                /* → code block bg + font size */
a   { color: #0969da; }                                      /* → hyperlink color */
blockquote { color: #59636e; }                               /* → quote text color */
table th { background: #f0f0f0; padding: 6px 13px; }        /* → header bg + cell padding */
hr  { border-bottom: 1px solid #d1d9e0; }                   /* → horizontal rule */
```

### CSS → HWPX mapping

| CSS Property | HWPX Equivalent | Example |
|-------------|----------------|---------|
| `body font-size` | charPr height | `16px` → 1000 hwpunit (10pt) |
| `body color` | charPr textColor | `#1f2328` |
| `body line-height` | paraPr lineSpacing | `1.5` → 150% |
| `h1-h6 font-size` | heading charPr height | `2em` → 2000 |
| `h1 border-bottom` | line after heading | `1px solid #d1d9e0` |
| `code font-family` | code block fontRef | `monospace` → D2Coding |
| `code font-size` | code charPr height | `85%` → 850 |
| `pre background` | code block borderFill | `#f6f8fa` |
| `a color` | hyperlink textColor | `#0969da` |
| `blockquote color` | quote textColor | `#59636e` |
| `table th background` | header cell borderFill | `#f0f0f0` |
| `table td padding` | cell margin (hasMargin=1) | `6px 13px` |
| `hr` | line shape | color + width |

### Custom CSS

Add your own `.css` file to `web/styles/` or upload via the Web UI. Changes apply immediately -- no server restart needed.

```css
/* my-company.css */
body { font-size: 11pt; color: #000; }
h1   { font-size: 18pt; border-bottom: 2px solid #003366; }
h2   { font-size: 14pt; }
a    { color: #003366; }
pre  { background: #f0f4f8; }
table th { background: #003366; padding: 8px 16px; }
```

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

## Known Limitations

This project is functional but has real constraints that affect practical use:

**Form layout accuracy requires human intervention.** Complex government or corporate forms have precise grid structures (merged cells, exact row heights, column widths). Even with OpenCV-based grid detection, the automated pipeline captures only ~70-80% of the structure correctly. A human must review and correct the detected grid before generating the final template. Simple forms still take significant iteration time to match the original exactly.

**No visual feedback loop.** The system generates HWPX files but cannot see the rendered result. Every change requires manually opening the file in Whale or Hancom Office, taking a screenshot, and feeding it back for comparison. This makes the edit-verify cycle slow. Until the system can render HWPX internally or connect to a viewer API, this bottleneck remains.

**Reverse-engineering HWPX is time-consuming.** HWPX is a Hancom-proprietary XML format with undocumented behaviors. Many features (cell merging, newlines in cells, hyperlink parameters) required analyzing real Hancom Office files byte-by-byte to discover the correct XML structure. Each new feature risks breaking existing ones because the format has implicit rules not covered by any public specification.

**Even simple forms take substantial effort.** A basic opinion submission form (8 rows, 4 columns, a few merges) required multiple rounds of debugging -- cell newline handling, merge order, row height proportions, font size matching. The gap between "it looks roughly right" and "it matches the original" is wide and labor-intensive to close.

**CSS-to-HWPX mapping is incomplete.** Only 46 of hundreds of CSS properties have HWPX equivalents. Features like border-radius, box-shadow, CSS Grid layout, and syntax highlighting have no HWPX counterpart. The styling system works within these bounds but cannot reproduce arbitrary web designs.

**Image text recognition gap.** OpenCV detects grid structure (line positions, proportions, merges) with mathematical precision, but reading text inside cells is a separate problem. EasyOCR Korean accuracy is 70-80% -- not production-ready. Claude can read images within a conversation, but the server cannot independently send images to Claude via OAuth -- an Anthropic API key is required. Currently, grid structure is auto-detected but text must be entered manually.

## Roadmap

**Image→HWPX automation pipeline (in progress)**
- OpenCV grid detection → Anthropic Vision API text recognition → cell editing UI → HWPX generation
- Requires API key for cell text auto-recognition
- Detected grid shown as HTML table for user review/edit before generation

**Form template system**
- YAML-based form definition → template.hwpx auto-generation
- Customer provides capture/scan → detect → review → finalize → reuse
- Template metadata tracks which cells accept user data

**python-hwpx library expansion**
- Font embedding (ttf files inside HWPX)
- Internal HWPX rendering or viewer integration (eliminate screenshot cycle)
- ~65 unimplemented OWPML features (shapes, fields, OLE, etc.)

**HWPX generation rules (HWPX_RULEBOOK.md)**
- Cell newlines must be separate `<hp:p>` elements, not `\n` in `<hp:t>`
- Merged cells must be physically removed from `<hp:tr>`, no empty rows
- Hyperlinks require 6-parameter fieldBegin structure
- Cell padding requires `hasMargin="1"`
- CSS files control document styling, changes apply without server restart

**Form clone pipeline (`templates/form_pipeline.py`)**
- `clone <input.hwpx> -o <output.hwpx>` -- one command to clone any form
- Preserves original fonts (11+), charPr (94+), borderFill (66+) via post-save header replacement
- Multi-page support with nested tables, per-run charPr, marker-based table insertion
- pageBreak, cellMargin, lineSpacing, fillColor all preserved from original

**OWPML table sizing rules ([OWPML_TABLE_SIZING.md](docs/OWPML_TABLE_SIZING.md))**
- No explicit column definitions -- all sizing lives in `cellSz` per cell
- Hidden column grid: `SUM(col_widths) == tbl.sz.width` (exact match)
- `cellSz.width = sum(col_widths[col : col+colSpan])`, same for height
- Table width = text area - outMargin×2
- Unit: 1mm ≈ 283.46 HWP units, 7200 units = 1 inch
- Define `col_widths[]` + `row_heights[]` → all cell sizes auto-calculated

## License

MIT
