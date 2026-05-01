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

## Korean Official Documents (공문/기안문) — v0.10.0+

Auto-generate Korean government/corporate 공문 compliant with
the **2025 행정업무운영 편람** (Administrative Business Handbook) from
the Ministry of the Interior and Safety.

```python
from pyhwpxlib.gongmun import Gongmun, GongmunBuilder, signer, validate_file

doc = Gongmun(
    기관명="OO 주식회사",
    수신="내부결재",                       # or "OOO장관"
    제목="용역 계약 체결(안)",
    본문=[
        "계약을 아래와 같이 체결하고자 ...",
        ("계약 개요", [                     # auto level-2: 가./나./다./라.
            "계약명: ...",
            "계약 금액: ...",
            "계약 기간: 2025. 5. 1. ~ 2026. 4. 30.",
        ]),
    ],
    붙임=["계약서(안) 1부."],               # auto "끝." marker
    기안자=signer("팀장", "김OO"),
    결재권자=signer("본부장", "박OO"),
    시행_처리과명="OO본부", 시행_일련번호="2026-001",
    시행일="2026. 4. 21.", 공개구분="비공개",
)
GongmunBuilder(doc).save("output.hwpx")

# Compliance check (10 rules)
print(validate_file("output.hwpx"))
```

**Automated standards** (편람 준수):
- Date `2025. 9. 20.`, Money `금113,560원(금일십일만삼천오백육십원)`
- 8-level item markers `1.→가.→1)→가)→(1)→(가)→①→㉮` + 2-tab indent
- "끝." marker (2 spaces + 끝.)
- Sender name auto-omitted for internal decisions (영 §13③)
- Standard margins: top 30 / bottom 15 / L·R 20 / header·footer 10 mm

**Automated checks** (10 rules):
- ERROR: DATE_FORMAT, DISCRIMINATORY_TERM, DUEUM_ERROR
- WARNING: AUTHORITATIVE_TONE ("할 것", "~바람"), AUTHORITATIVE_TERM, LOANWORD_ERROR, END_MARKER_MISSING
- INFO: HANGUL_COMPAT_CHAR (㉮, ㎕), ENGLISH_ABBREV

Four document types supported: **일반기안문** (external) / **간이기안문** (internal) / **일괄기안** / **공동기안**.

See [`pyhwpxlib/gongmun/rules.yaml`](pyhwpxlib/gongmun/rules.yaml) for the full machine-readable rule set.

## What is HWPX?

HWPX is the modern document format for Hancom Office, the standard office suite in South Korea. It is a ZIP archive containing XML files following the OWPML specification -- similar in concept to `.docx` for Microsoft Word.

This project lets you create and edit HWPX files with pure Python, no Hancom Office installation needed.

## Credits

This project is built upon the following open-source projects:

| Project | Author | License | Usage |
|---------|--------|---------|-------|
| [hwp2hwpx](https://github.com/neolord0/hwp2hwpx) | neolord0 | Apache 2.0 | HWP→HWPX conversion logic (ported to Python) |
| [hwplib](https://github.com/neolord0/hwplib) | neolord0 | Apache 2.0 | HWP binary parser (ported to Python) |
| [python-hwpx](https://github.com/airmang/python-hwpx) | Kyuhyun Ko | MIT | HWPX dataclass model |

## Known Limitations

- Complex cell-merge layouts may require manual review
- No built-in HWPX preview (verify in Hancom Office or Whale)
- CSS→HWPX mapping covers 46 major properties only
- Image OCR for form text requires a separate API key

## License

This project uses a **dual license** structure. See [LICENSE.md](LICENSE.md) for full details.

| Files | License |
|-------|---------|
| `hwp2hwpx.py`, `hwp_reader.py`, `value_convertor.py` | Apache 2.0 (derivative works) |
| **All other files** | **BSL 1.1** |

**BSL 1.1 summary:**
- Personal / non-commercial / educational / open-source: **Free**
- Internal use (up to 5 users): **Free**
- Commercial use / 6+ users: **Commercial license required**
- Rolling Change Date: each release converts to Apache 2.0 four years after its release date (latest 0.16.1 → 2030-05-01). See [LICENSE.md](LICENSE.md).

## Fonts

pyhwpxlib uses **NanumGothic** (Naver, SIL OFL 1.1) as default font metadata
in generated documents and bundles it (`vendor/`) for rhwp rendering fallback.

### Why not 함초롬돋움/바탕 or 맑은 고딕?

| Font | License | Issue |
|------|---------|-------|
| 함초롬돋움/바탕 (HCR-) | Hancom Office license | Bundled with Hancom Office only |
| 맑은 고딕 (Malgun Gothic) | Microsoft license | Bundled with Windows/Office only |
| **나눔고딕/명조** | **SIL OFL 1.1** | **Free redistribution + embed** |

Both Hancom and Microsoft fonts have redistribution restrictions, so
v0.16.1+ defaults to NanumGothic to avoid license concerns for users.

### Override default

```python
from pyhwpxlib import HwpxBuilder
from pyhwpxlib.themes import FontSet

# Use 맑은 고딕 explicitly (you are responsible for the license)
fonts = FontSet(heading_hangul='맑은 고딕', body_hangul='맑은 고딕',
                caption_hangul='맑은 고딕')
b = HwpxBuilder(theme='default')  # FontSet override 는 사용자 정의 theme 통합 시
```

### HWP→HWPX conversion

`hwp2hwpx.convert()` **preserves original font names** from `.hwp` files.
Converted HWPX retains whatever fonts the source document used —
license compliance for converted files is the user's responsibility.
