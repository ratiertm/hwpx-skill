---
feature: hwpx-skill-v1
title: HWPX Document Generation via CLI
created: 2026-03-27
updated: 2026-03-27
status: verified
depends_on: []
steps: 25
tags: [hwpx, cli, python, document-generation]
---

# E2E Spec: HWPX Document Generation via CLI

User creates a new HWPX document via CLI -> content stored in .hwpx file (ZIP+XML) -> user opens in Hancom Office and sees the content.

---

## Interaction 1: Create Document and Add Text

### e2e-hwpx-skill-v1-001: CLI New Document Screen

**Chain:** Screen
**Status:** implemented

#### What
User runs `cli-anything-hwpx document new --output report.hwpx` in terminal.

#### Verification Criteria
- [ ] `cli-anything-hwpx document new --output <path>` command exists and is executable
- [ ] Output shows document info (sections, paragraphs, images count)
- [ ] .hwpx file is created at the specified path

#### Details
- **Element:** Terminal CLI command
- **User Action:** Execute `document new --output <filename>`
- **Initial State:** No .hwpx file exists at the target path

---

### e2e-hwpx-skill-v1-002: CLI Text Add Connection

**Chain:** Connection
**Status:** implemented

#### What
User runs `cli-anything-hwpx --file report.hwpx text add "content"` to add a paragraph.

#### Verification Criteria
- [ ] `--file <path> text add <content>` command parses correctly
- [ ] Command opens the existing .hwpx file via python-hwpx API

#### Details
- **Method:** CLI command -> `doc_mod.open_document(path)` -> `text_mod.add_paragraph(doc, content)`
- **Endpoint:** `cli-anything-hwpx --file <path> text add <content>`
- **Request:** file_path (str), content (str)
- **Auth:** None (local file system)

---

### e2e-hwpx-skill-v1-003: Text Add Processing

**Chain:** Processing
**Status:** implemented

#### What
python-hwpx adds a paragraph element to section0.xml inside the HWPX ZIP, then auto-saves.

#### Verification Criteria
- [ ] `HwpxDocument.add_paragraph(text)` inserts `<hp:p><hp:run><hp:t>text</hp:t></hp:run></hp:p>` into section0.xml
- [ ] `_auto_save_if_needed()` writes the modified document back to the original file path

#### Details
- **Steps:**
  1. Open .hwpx file -> HwpxDocument object in memory
  2. `add_paragraph(content)` appends `<hp:p>` element to section XML
  3. `_auto_save_if_needed()` calls `sess.save(path)` -> `doc.save_to_path(path)`
  4. ZIP file is rewritten with updated section0.xml
- **Storage:** .hwpx file (ZIP+XML on local filesystem) -- WRITE

---

### e2e-hwpx-skill-v1-004: Text Add Response

**Chain:** Response
**Status:** implemented

#### What
CLI outputs confirmation message and the added text is persisted in the file.

#### Verification Criteria
- [ ] CLI prints "Added paragraph: {content}..." with text, section, status fields
- [ ] Running `text extract` on the same file returns the added content

#### Details
- **Success Status:** Exit code 0
- **Response Shape:** `{text: str, section: int, status: "added"}`
- **UI Updates:**
  - Terminal shows "Added paragraph: ..." confirmation
  - Subsequent `text extract` returns all accumulated paragraphs

---

### e2e-hwpx-skill-v1-005: Text Add Errors

**Chain:** Error
**Status:** implemented

#### What
Failure modes when adding text to a document.

#### Verification Criteria
- [ ] Missing file shows "File not found" error and exits with code 1
- [ ] Invalid .hwpx file (corrupted ZIP) shows parse error
- [ ] Missing --file flag shows Click usage error

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| File path does not exist | "Error: File not found: {path}" on stderr, exit 1 | null (client-side) |
| File is not valid .hwpx (corrupted ZIP/XML) | "Error: {parse error}" on stderr, exit 1 | null (server-side) |
| No --file flag and no document open | "Error: No document open" on stderr, exit 1 | null (client-side) |

---

## Interaction 2: Extract and Verify Content

### e2e-hwpx-skill-v1-006: Text Extract Screen

**Chain:** Screen
**Status:** implemented

#### What
User runs `cli-anything-hwpx --file report.hwpx text extract` to read document content.

#### Verification Criteria
- [ ] `text extract` command exists and accepts --file and --format options
- [ ] Output displays all paragraphs in the document as plain text

#### Details
- **Element:** Terminal CLI command
- **User Action:** Execute `--file <path> text extract`
- **Initial State:** .hwpx file contains previously added paragraphs

---

### e2e-hwpx-skill-v1-007: Text Extract Connection

**Chain:** Connection
**Status:** implemented

#### What
CLI opens the .hwpx file and calls python-hwpx export API.

#### Verification Criteria
- [ ] File is opened via `doc_mod.open_document(path)`
- [ ] `text_mod.extract_text(doc)` or `doc.export_text()` is called

#### Details
- **Method:** CLI command -> `doc_mod.open_document(path)` -> `text_mod.extract_text(doc)`
- **Endpoint:** `cli-anything-hwpx --file <path> text extract`
- **Request:** file_path (str), format (text|markdown|html, default: text)
- **Auth:** None

---

### e2e-hwpx-skill-v1-008: Text Extract Processing

**Chain:** Processing
**Status:** implemented

#### What
python-hwpx iterates sections/paragraphs/runs and concatenates text content.

#### Verification Criteria
- [ ] All `<hp:t>` text nodes are extracted from all `<hp:p>` paragraphs
- [ ] Multiple paragraphs are separated by newlines

#### Details
- **Steps:**
  1. Open .hwpx ZIP -> parse section0.xml
  2. Iterate `doc.sections[].paragraphs[].runs[].text`
  3. Concatenate with newline separators
- **Storage:** .hwpx file (ZIP+XML on local filesystem) -- READ

---

### e2e-hwpx-skill-v1-009: Text Extract Response

**Chain:** Response
**Status:** implemented

#### What
CLI outputs the extracted text to stdout.

#### Verification Criteria
- [ ] Plain text output contains all previously added paragraphs
- [ ] With `--json` flag, output is `{"content": "...", "format": "text"}`

#### Details
- **Success Status:** Exit code 0
- **Response Shape:** Plain text (default) or JSON with --json flag
- **UI Updates:**
  - Terminal displays document text content
  - No file modification occurs (read-only operation)

---

### e2e-hwpx-skill-v1-010: Text Extract Errors

**Chain:** Error
**Status:** implemented

#### What
Failure modes when extracting text.

#### Verification Criteria
- [ ] Missing file shows "File not found" error
- [ ] Empty document returns empty string (not error)
- [ ] Corrupted file shows parse error

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| File does not exist | "Error: File not found: {path}" on stderr, exit 1 | null (client-side) |
| Corrupted .hwpx file | "Error: {XML parse error}" on stderr, exit 1 | null (server-side) |
| Network filesystem timeout | "Error: {OSError}" on stderr, exit 1 | null (network) |

---

## Interaction 3: Open in Hancom Office

### e2e-hwpx-skill-v1-011: Hancom Office Open Screen

**Chain:** Screen
**Status:** implemented

#### What
User double-clicks the .hwpx file or opens it via Hancom Office.

#### Verification Criteria
- [ ] .hwpx file opens without error in Hancom Office (2020+)
- [ ] Document displays all added text paragraphs with Korean characters rendered correctly

#### Details
- **Element:** Hancom Office document viewer
- **User Action:** Double-click .hwpx file or File > Open
- **Initial State:** Hancom Office is installed on user's machine

---

### e2e-hwpx-skill-v1-012: Hancom Office File Parse Connection

**Chain:** Connection
**Status:** implemented

#### What
Hancom Office reads the ZIP structure, parses XML, and renders the document.

#### Verification Criteria
- [ ] ZIP structure is valid (mimetype, META-INF/, Contents/, header.xml)
- [ ] section0.xml follows OWPML namespace conventions

#### Details
- **Method:** Hancom Office internal ZIP+XML parser
- **Endpoint:** Local file system read
- **Request:** .hwpx file path
- **Auth:** None

---

### e2e-hwpx-skill-v1-013: Hancom Office Render Processing

**Chain:** Processing
**Status:** implemented

#### What
Hancom Office renders paragraphs, applies styles from header.xml, displays content.

#### Verification Criteria
- [ ] All paragraphs from section0.xml are rendered in document view
- [ ] Default font (함초롬돋움) is applied correctly
- [ ] Page layout matches pagePr settings (A4, margins)

#### Details
- **Steps:**
  1. Parse header.xml for font/style definitions
  2. Parse section0.xml for paragraph content
  3. Apply charPrIDRef styles to text runs
  4. Render in WYSIWYG view
- **Storage:** .hwpx file (ZIP+XML on local filesystem) -- READ

---

### e2e-hwpx-skill-v1-014: Hancom Office Display Response

**Chain:** Response
**Status:** implemented

#### What
User sees the document content rendered correctly in Hancom Office.

#### Verification Criteria
- [ ] All text paragraphs are visible and readable
- [ ] Korean text is displayed without mojibake (encoding issues)
- [ ] Document structure (sections, page breaks) is correct

#### Details
- **Success Status:** Document opens without error dialog
- **Response Shape:** Rendered WYSIWYG document view
- **UI Updates:**
  - Document title bar shows filename
  - Content area displays all paragraphs
  - Status bar shows page count

---

### e2e-hwpx-skill-v1-015: Hancom Office Open Errors

**Chain:** Error
**Status:** implemented

#### What
Failure modes when opening generated .hwpx in Hancom Office.

#### Verification Criteria
- [ ] Missing required XML elements show "file corrupted" dialog
- [ ] Invalid namespace declarations cause parse error with message
- [ ] Incomplete ZIP structure (missing mimetype) shows format error

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| Invalid/missing XML structure in section0.xml | "파일이 손상되었습니다" error dialog | null (client-side) |
| Missing required namespace in header.xml | Document opens partially or shows warning | null (server-side) |
| Incomplete ZIP (missing mimetype or META-INF) | "지원하지 않는 형식" error dialog | null (network) |

---

## Interaction 4: LLM Instruction-Based Document Generation

### e2e-hwpx-skill-v1-016: LLM Instruction Screen

**Chain:** Screen
**Status:** implemented

#### What
User writes a natural language instruction for the AI agent (e.g., "이 프로그램의 특징을 한글로 적어줘").

#### Verification Criteria
- [ ] Instruction text area accepts multi-line natural language input
- [ ] Output filename field specifies the target .hwpx file
- [ ] User can see the instruction will be sent to the AI agent, not directly to the CLI

#### Details
- **Element:** Instruction form with textarea + filename input
- **User Action:** Type instruction in natural language, specify output filename
- **Initial State:** Empty instruction textarea, default filename

---

### e2e-hwpx-skill-v1-017: LLM Instruction Connection

**Chain:** Connection
**Status:** implemented

#### What
AI agent receives the instruction, reads SKILL.md to understand available CLI commands, and generates a sequence of CLI calls.

#### Verification Criteria
- [ ] AI agent reads `cli_anything/hwpx/skills/SKILL.md` for available commands
- [ ] Agent generates `document new` followed by multiple `text add` commands

#### Details
- **Method:** Natural language -> AI agent -> CLI command sequence
- **Endpoint:** AI agent context (Claude Code, Cursor, etc.)
- **Request:** instruction (str), output_filename (str)
- **Auth:** None (AI agent session)

---

### e2e-hwpx-skill-v1-018: LLM Instruction Processing

**Chain:** Processing
**Status:** implemented

#### What
AI agent executes the generated CLI commands sequentially: create document, then add paragraphs based on the instruction content.

#### Verification Criteria
- [ ] `document new --output <file>` creates the base file
- [ ] Multiple `--file <file> text add <content>` calls add generated paragraphs
- [ ] Each `text add` triggers `_auto_save_if_needed()` to persist changes

#### Details
- **Steps:**
  1. AI agent interprets instruction and generates content
  2. Execute `cli-anything-hwpx document new --output <file>`
  3. For each paragraph: `cli-anything-hwpx --file <file> text add "<paragraph>"`
  4. Each call auto-saves to the .hwpx file
- **Storage:** .hwpx file (ZIP+XML on local filesystem) -- WRITE

---

### e2e-hwpx-skill-v1-019: LLM Instruction Response

**Chain:** Response
**Status:** implemented

#### What
AI agent reports completion with the list of added paragraphs and the output file path.

#### Verification Criteria
- [ ] Agent confirms the number of paragraphs added
- [ ] `text extract` shows the AI-generated content matches the instruction intent
- [ ] Output file is a valid .hwpx openable in Hancom Office

#### Details
- **Success Status:** All CLI commands exit with code 0
- **Response Shape:** Agent message summarizing what was created
- **UI Updates:**
  - Agent shows "N paragraphs added to <file>"
  - User can run `text extract` to verify content

---

### e2e-hwpx-skill-v1-020: LLM Instruction Errors

**Chain:** Error
**Status:** implemented

#### What
Failure modes for LLM-based document generation.

#### Verification Criteria
- [ ] Empty instruction shows validation error
- [ ] AI agent clarifies ambiguous instructions before generating
- [ ] CLI errors during execution are reported back to the user

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| Empty instruction | "지시문을 입력해주세요" validation error | null (client-side) |
| CLI command fails mid-sequence | Agent reports error and partial result | null (server-side) |
| File system permission denied | "Error: Permission denied" from CLI | null (network) |

---

## Interaction 5: File Upload and Convert to HWPX

### e2e-hwpx-skill-v1-021: File Upload Screen

**Chain:** Screen
**Status:** implemented

#### What
User uploads an HTML, Markdown, or plain text file to convert into a .hwpx document.

#### Verification Criteria
- [ ] File input accepts .html, .md, .txt file types
- [ ] Output filename field specifies the target .hwpx path
- [ ] File preview shows the content of the uploaded file

#### Details
- **Element:** File upload input + filename input + preview area
- **User Action:** Select file via file picker, specify output filename
- **Initial State:** No file selected, empty preview

---

### e2e-hwpx-skill-v1-022: File Upload Parse Connection

**Chain:** Connection
**Status:** implemented

#### What
System reads the uploaded file content and converts it to paragraphs based on file type.

#### Verification Criteria
- [ ] HTML files: strip tags, extract text content per block element
- [ ] Markdown files: parse headings/paragraphs, convert to plain text lines
- [ ] Text files: split by newlines into paragraphs

#### Details
- **Method:** File read -> content parser -> CLI command sequence
- **Endpoint:** Local file read + `cli-anything-hwpx` commands
- **Request:** source_file (path), output_file (path), format (html|md|txt)
- **Auth:** None

---

### e2e-hwpx-skill-v1-023: File Convert Processing

**Chain:** Processing
**Status:** implemented

#### What
Parse the uploaded file content, then create a new .hwpx and add each paragraph via CLI.

#### Verification Criteria
- [ ] HTML: `<h1>`, `<h2>`, `<p>`, `<li>` elements become individual paragraphs
- [ ] Markdown: `#`, `##`, paragraphs, `- list items` become individual paragraphs
- [ ] Text: each non-empty line becomes a paragraph
- [ ] All paragraphs are saved to .hwpx via `text add` + auto-save

#### Details
- **Steps:**
  1. Read source file and detect format by extension
  2. Parse content into paragraph list based on format
  3. `cli-anything-hwpx document new --output <output_file>`
  4. For each paragraph: `cli-anything-hwpx --file <output_file> text add "<paragraph>"`
  5. Auto-save persists each addition
- **Storage:** .hwpx file (ZIP+XML on local filesystem) -- WRITE

---

### e2e-hwpx-skill-v1-024: File Convert Response

**Chain:** Response
**Status:** implemented

#### What
System confirms conversion with paragraph count and output path.

#### Verification Criteria
- [ ] Output shows source format, paragraph count, and output file path
- [ ] `text extract` on the output file returns content matching the source
- [ ] Output .hwpx opens correctly in Hancom Office

#### Details
- **Success Status:** Exit code 0 for all CLI commands
- **Response Shape:** `{source: str, format: str, paragraphs: int, output: str}`
- **UI Updates:**
  - Shows "Converted N paragraphs from <source> to <output>"
  - Preview of extracted text from the generated .hwpx

---

### e2e-hwpx-skill-v1-025: File Convert Errors

**Chain:** Error
**Status:** implemented

#### What
Failure modes for file upload and conversion.

#### Verification Criteria
- [ ] Unsupported file type shows format error
- [ ] Empty file shows "no content" warning
- [ ] Encoding errors (non-UTF8) show charset error with suggestion

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| Unsupported file extension (.pdf, .docx, etc.) | "지원하지 않는 형식입니다. html, md, txt만 가능합니다." | null (client-side) |
| Empty file (0 bytes) | "파일에 내용이 없습니다" warning | null (server-side) |
| Non-UTF8 encoding | "인코딩 오류: UTF-8 파일만 지원합니다" | null (network) |

---

## Deviations

_No deviations recorded yet._
