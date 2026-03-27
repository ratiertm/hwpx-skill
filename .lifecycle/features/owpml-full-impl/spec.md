---
feature: owpml-full-impl
title: OWPML Core Implementation — charPr, paraPr, table, image, page (Phase 1)
created: 2026-03-28
updated: 2026-03-28
status: agreed
depends_on: [hwpx-skill-v1]
steps: 25
tags: [owpml, python-hwpx, charPr, paraPr, table, image, pagePr]
---

# E2E Spec: OWPML Full Implementation

User calls python-hwpx API to set font/paragraph/table/image/page properties per OWPML spec -> properties stored in header.xml/section0.xml -> Hancom Office renders document with all formatting applied.

---

## Interaction 1: Character Properties (charPr) — 14 missing attributes

### e2e-owpml-full-impl-001: Font Reference Screen

**Chain:** Screen
**Status:** implemented

#### What
User calls `ensure_run_style(font_hangul="맑은 고딕", font_latin="Arial")` to set per-language font references.

#### Verification Criteria
- [ ] `ensure_run_style()` accepts `font_hangul`, `font_latin`, `font_hanja`, `font_japanese`, `font_other`, `font_symbol`, `font_user` parameters
- [ ] Generated `<hh:charPr>` contains `<hh:fontRef>` with correct per-language font IDs
- [ ] Font names are registered in `<hh:fontfaces>` if not already present

#### Details
- **Element:** Python API call
- **User Action:** `doc.ensure_run_style(font_hangul="맑은 고딕", height=1200)`
- **Initial State:** Default font (함초롬돋움)

---

### e2e-owpml-full-impl-002: Character Decoration Connection

**Chain:** Connection
**Status:** implemented

#### What
API writes strikeout, outline, shadow, emboss, engrave, superscript, subscript attributes to charPr XML.

#### Verification Criteria
- [ ] `ensure_run_style(strikeout=True)` adds `<hh:strikeout shape="SOLID" color="#000000"/>`
- [ ] `ensure_run_style(outline="SOLID")` adds `<hh:outline type="SOLID"/>`
- [ ] `ensure_run_style(shadow=True)` adds `<hh:shadow type="DROP" color="#C0C0C0" offsetX="10" offsetY="10"/>`
- [ ] `ensure_run_style(superscript=True)` / `subscript=True` sets appropriate attribute
- [ ] `ensure_run_style(emboss=True)` / `engrave=True` adds corresponding element

#### Details
- **Method:** `ensure_run_style()` extended parameters → `modifier()` in `oxml/document.py`
- **Endpoint:** `HwpxDocument.ensure_run_style(**kwargs) -> str (charPrIDRef)`
- **Request:** keyword arguments for each decoration type
- **Auth:** None

---

### e2e-owpml-full-impl-003: Character Spacing Processing

**Chain:** Processing
**Status:** implemented

#### What
Sets per-language spacing, ratio, relative size, and offset in charPr XML.

#### Verification Criteria
- [ ] `ensure_run_style(spacing_hangul=10)` sets `<hh:spacing hangul="10" .../>`
- [ ] `ensure_run_style(ratio_hangul=95)` sets `<hh:ratio hangul="95" .../>`
- [ ] `ensure_run_style(rel_size_latin=110)` sets `<hh:relSz latin="110" .../>`
- [ ] `ensure_run_style(offset_hangul=5)` sets `<hh:offset hangul="5" .../>`
- [ ] Per-language attributes (hangul, latin, hanja, japanese, other, symbol, user) all supported

#### Details
- **Steps:**
  1. Parse kwargs for spacing/ratio/relSz/offset per language
  2. Find or create charPr via `ensure_char_property()`
  3. Set child element attributes
- **Storage:** header.xml `<hh:charProperties>` — WRITE

---

### e2e-owpml-full-impl-004: Character Properties Response

**Chain:** Response
**Status:** implemented

#### What
Returns charPr ID that can be used with `add_paragraph(char_pr_id_ref=)`.

#### Verification Criteria
- [ ] Return value is valid charPr ID string
- [ ] `add_paragraph(text, char_pr_id_ref=id)` produces paragraph with correct style
- [ ] `export_text()` returns the text (style doesn't affect text content)
- [ ] Generated HWPX opens in Hancom Office with correct character formatting

#### Details
- **Success Status:** Returns str (charPr ID)
- **Response Shape:** `str` — ID reference for charPr element
- **UI Updates:** Document displays styled text when opened in Hancom Office

---

### e2e-owpml-full-impl-005: Character Properties Errors

**Chain:** Error
**Status:** implemented

#### What
Error handling for invalid character property values.

#### Verification Criteria
- [ ] Invalid font name (not in fontfaces) auto-registers the font
- [ ] `height=0` or negative raises ValueError
- [ ] Invalid color format (not #RRGGBB) raises ValueError

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| Font name not in fontfaces | Auto-register in `<hh:fontfaces>` | null (auto-fix) |
| height <= 0 | ValueError("height must be positive") | null (client) |
| Invalid color format | ValueError("color must be #RRGGBB") | null (client) |

---

## Interaction 2: Paragraph Properties (paraPr) — 11 missing attributes

### e2e-owpml-full-impl-006: Paragraph Alignment Screen

**Chain:** Screen
**Status:** implemented

#### What
User calls `ensure_para_style(align="CENTER", line_spacing=160)` to set paragraph formatting.

#### Verification Criteria
- [ ] New method `ensure_para_style()` exists on HwpxDocument
- [ ] Accepts: `align` (LEFT/CENTER/RIGHT/JUSTIFY/DISTRIBUTE), `line_spacing` (percent), `line_spacing_type` (PERCENT/FIXED/BETWEEN_LINES)
- [ ] Returns paraPr ID string

#### Details
- **Element:** Python API call
- **User Action:** `doc.ensure_para_style(align="CENTER", line_spacing=160)`
- **Initial State:** Default paragraph style (left-aligned, 160% line spacing)

---

### e2e-owpml-full-impl-007: Paragraph Margin Connection

**Chain:** Connection
**Status:** implemented

#### What
API sets indent, left/right margin, before/after paragraph spacing in paraPr XML.

#### Verification Criteria
- [ ] `ensure_para_style(indent=800)` sets `<hp:margin><hp:intent value="800" unit="HWPUNIT"/></hp:margin>`
- [ ] `ensure_para_style(margin_left=400, margin_right=400)` sets left/right values
- [ ] `ensure_para_style(spacing_before=200, spacing_after=200)` sets prev/next values
- [ ] Values are in hwpunit (7200 = 1 inch)

#### Details
- **Method:** `ensure_para_style()` → `header.ensure_para_property()` in `oxml/document.py`
- **Endpoint:** `HwpxDocument.ensure_para_style(**kwargs) -> str (paraPrIDRef)`
- **Request:** keyword arguments for margin/spacing
- **Auth:** None

---

### e2e-owpml-full-impl-008: Paragraph Advanced Processing

**Chain:** Processing
**Status:** implemented

#### What
Sets heading, break settings, border, tab reference, auto-spacing in paraPr XML.

#### Verification Criteria
- [ ] `ensure_para_style(heading_type="OUTLINE", heading_level=1)` sets heading attributes
- [ ] `ensure_para_style(keep_with_next=True, page_break_before=True)` sets break settings
- [ ] `ensure_para_style(border_fill_id=N)` sets paragraph border reference
- [ ] `ensure_para_style(tab_pr_id=N)` sets tab definition reference

#### Details
- **Steps:**
  1. Parse kwargs for all paraPr attributes
  2. Find or create paraPr via `ensure_para_property()`
  3. Set align, margin, lineSpacing, heading, breakSetting child elements
- **Storage:** header.xml `<hh:paraProperties>` — WRITE

---

### e2e-owpml-full-impl-009: Paragraph Properties Response

**Chain:** Response
**Status:** implemented

#### What
Returns paraPr ID for use with `add_paragraph(para_pr_id_ref=)`.

#### Verification Criteria
- [ ] `add_paragraph(text, para_pr_id_ref=id)` produces centered/indented paragraph
- [ ] Combined with charPr: `add_paragraph(text, char_pr_id_ref=char_id, para_pr_id_ref=para_id)` works
- [ ] Generated HWPX opens correctly in Hancom Office

#### Details
- **Success Status:** Returns str (paraPr ID)
- **Response Shape:** `str` — ID reference for paraPr element
- **UI Updates:** Document displays formatted paragraphs

---

### e2e-owpml-full-impl-010: Paragraph Properties Errors

**Chain:** Error
**Status:** implemented

#### What
Error handling for invalid paragraph property values.

#### Verification Criteria
- [ ] Invalid align value raises ValueError
- [ ] Negative margin raises ValueError
- [ ] line_spacing=0 raises ValueError

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| Invalid align value | ValueError("align must be LEFT/CENTER/RIGHT/JUSTIFY/DISTRIBUTE") | null (client) |
| Negative margin value | ValueError("margin values must be non-negative") | null (client) |
| line_spacing <= 0 | ValueError("line_spacing must be positive") | null (client) |

---

## Interaction 3: Table Advanced Features — 10 missing features

### e2e-owpml-full-impl-011: Cell Merge Screen

**Chain:** Screen
**Status:** implemented

#### What
User calls `table.merge_cells(0, 0, 0, 2)` to merge cells in a table.

#### Verification Criteria
- [ ] `HwpxOxmlTable.merge_cells(start_row, start_col, end_row, end_col)` method exists
- [ ] Merged cells produce correct `<tc>` with `colSpan`/`rowSpan` attributes
- [ ] Content of merged cells is preserved in the top-left cell

#### Details
- **Element:** Python API call on table object
- **User Action:** `tbl = doc.add_table(3, 3); tbl.merge_cells(0, 0, 0, 2)`
- **Initial State:** 3x3 table with individual cells

---

### e2e-owpml-full-impl-012: Cell Styling Connection

**Chain:** Connection
**Status:** implemented

#### What
API sets cell size, margin, border, and background for individual cells.

#### Verification Criteria
- [ ] `table.set_cell_size(row, col, width, height)` sets `<tc><cellSz width="..." height="..."/></tc>`
- [ ] `table.set_cell_margin(row, col, left, right, top, bottom)` sets cellMargin
- [ ] `table.set_cell_border_fill(row, col, border_fill_id)` sets per-cell borderFillIDRef
- [ ] `table.set_cell_background(row, col, color)` applies background via borderFill

#### Details
- **Method:** New methods on HwpxOxmlTable
- **Endpoint:** `table.set_cell_size()`, `table.set_cell_margin()`, etc.
- **Request:** row, col, values
- **Auth:** None

---

### e2e-owpml-full-impl-013: Table Properties Processing

**Chain:** Processing
**Status:** implemented

#### What
Sets table-level properties: inner margin, header repeat, page break, cell spacing.

#### Verification Criteria
- [ ] `add_table(repeat_header=True)` sets `<tbl repeatHeader="1"/>`
- [ ] `add_table(page_break="CELL")` sets `<tbl pageBreak="CELL"/>`
- [ ] `add_table(cell_spacing=100)` sets `<tbl cellSpacing="100"/>`
- [ ] `add_table(in_margin_left=100, in_margin_top=50)` sets `<tbl><inMargin .../></tbl>`

#### Details
- **Steps:**
  1. Extend `add_table()` with new kwargs
  2. Set attributes on `<tbl>` element
  3. Add `<inMargin>` child element
- **Storage:** section0.xml `<tbl>` element — WRITE

---

### e2e-owpml-full-impl-014: Table Response

**Chain:** Response
**Status:** implemented

#### What
Table with merged cells, styled cells, and properties renders correctly.

#### Verification Criteria
- [ ] `export_text()` returns cell content in reading order
- [ ] Merged cells appear as single cell in Hancom Office
- [ ] Table properties (header repeat, page break) function correctly

#### Details
- **Success Status:** Table object returned with all properties set
- **Response Shape:** `HwpxOxmlTable` with enhanced methods
- **UI Updates:** Hancom Office renders merged/styled table

---

### e2e-owpml-full-impl-015: Table Errors

**Chain:** Error
**Status:** implemented

#### What
Error handling for invalid table operations.

#### Verification Criteria
- [ ] Merging out-of-range cells raises IndexError
- [ ] Overlapping merge ranges raise ValueError
- [ ] Setting style on merged (hidden) cell raises ValueError

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| merge_cells with out-of-range indices | IndexError | null (client) |
| Overlapping merge regions | ValueError("cells already merged") | null (client) |
| Style on hidden cell in merged range | ValueError("cell is part of merged region") | null (client) |

---

## Interaction 4: Image & Page Setup — 9 + 11 missing features

### e2e-owpml-full-impl-016: Image Inline Insert Screen

**Chain:** Screen
**Status:** implemented

#### What
User calls `doc.insert_image(path, width=150, height=100)` for convenient inline image insertion.

#### Verification Criteria
- [ ] New method `insert_image(path_or_bytes, width, height)` on HwpxDocument
- [ ] Generates complete `<hp:pic>` with shapeObject/sz/pos/shapeRect/imgRect/imgDim/img
- [ ] Width/height in mm (converted to hwpunit internally)
- [ ] Returns paragraph containing the image

#### Details
- **Element:** Python API call
- **User Action:** `doc.insert_image("photo.png", width=150, height=100)`
- **Initial State:** Document without images

---

### e2e-owpml-full-impl-017: Image Properties Connection

**Chain:** Connection
**Status:** implemented

#### What
API sets image crop, effects, brightness, contrast, alpha, rotation, flip.

#### Verification Criteria
- [ ] `insert_image(..., crop_left=10, crop_top=10)` sets `<hp:imgClip left="10" top="10" .../>`
- [ ] `insert_image(..., bright=20, contrast=30)` sets attributes on `<hp:img>`
- [ ] `insert_image(..., alpha=50)` sets transparency
- [ ] `insert_image(..., rotation=90)` adds `<rotationInfo>` element
- [ ] `insert_image(..., flip_horizontal=True)` adds flip attribute

#### Details
- **Method:** `insert_image()` with optional kwargs
- **Endpoint:** `HwpxDocument.insert_image(**kwargs) -> HwpxOxmlParagraph`
- **Request:** image path/bytes + formatting kwargs
- **Auth:** None

---

### e2e-owpml-full-impl-018: Page Setup Processing

**Chain:** Processing
**Status:** implemented

#### What
Sets page size, orientation, margins, gutter, grid, visibility, line numbers, page border.

#### Verification Criteria
- [ ] New method `set_page_setup()` on HwpxDocument
- [ ] `set_page_setup(width=59528, height=84186)` sets A4 size (hwpunit)
- [ ] `set_page_setup(landscape=True)` swaps width/height and sets NARROWLY
- [ ] `set_page_setup(margin_left=8504, margin_top=5668)` sets margins
- [ ] `set_page_setup(gutter=1000, gutter_type="LEFT_ONLY")` sets gutter
- [ ] Convenience presets: `set_page_setup(paper="A4")`, `set_page_setup(paper="Letter")`

#### Details
- **Steps:**
  1. Find `<hp:secPr>` in section0.xml
  2. Set `<hp:pagePr>` attributes (landscape, width, height, gutterType)
  3. Set `<hp:pagePr><hp:margin>` child elements
  4. Optionally set grid, visibility, lineNumberShape, pageBorderFill
- **Storage:** section0.xml `<hp:secPr>/<hp:pagePr>` — WRITE

---

### e2e-owpml-full-impl-019: Image & Page Response

**Chain:** Response
**Status:** implemented

#### What
Image displays inline in document, page setup affects document layout.

#### Verification Criteria
- [ ] Image visible in Hancom Office at specified size/position
- [ ] Page orientation change reflected in Hancom Office
- [ ] Margins change visible in document layout
- [ ] Combined: image + page setup + styled text in one document

#### Details
- **Success Status:** Document renders with all properties
- **Response Shape:** Document with images and page formatting
- **UI Updates:** Hancom Office shows formatted document

---

### e2e-owpml-full-impl-020: Image & Page Errors

**Chain:** Error
**Status:** implemented

#### What
Error handling for image and page setup.

#### Verification Criteria
- [ ] Non-existent image file raises FileNotFoundError
- [ ] Invalid paper size name raises ValueError
- [ ] Negative margin raises ValueError

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| Image file not found | FileNotFoundError | null (client) |
| Unknown paper preset ("B7") | ValueError("Unknown paper size") | null (client) |
| Negative margin | ValueError("margins must be non-negative") | null (client) |

---

## Interaction 5: Remaining Features — fields, forms, shapes, misc

### e2e-owpml-full-impl-021: Advanced Shapes Screen

**Chain:** Screen
**Status:** implemented

#### What
User creates arc, polygon, curve, connector, group container, textart, and draw-text shapes.

#### Verification Criteria
- [ ] `add_arc()`, `add_polygon()`, `add_curve()` methods exist
- [ ] `add_connect_line()` for connector shapes
- [ ] `add_group()` for shape grouping
- [ ] Shapes accept fill (gradient, image pattern) and line style (arrow heads)

#### Details
- **Element:** Python API calls
- **User Action:** `doc.add_polygon(points=[(0,0),(100,0),(50,80)])` etc.
- **Initial State:** Document without shapes

---

### e2e-owpml-full-impl-022: Fields & Forms Connection

**Chain:** Connection
**Status:** implemented

#### What
API creates form controls (checkbox, radio, combo, listbox, edit) and field types (formula, date, page number, cross-reference).

#### Verification Criteria
- [ ] `add_checkbox(name, checked=False)` creates `<checkBtn>` element
- [ ] `add_page_number(format="DIGIT")` creates `<pageNum>` element
- [ ] `add_field(type="DATE", format="yyyy-MM-dd")` creates date field
- [ ] `add_auto_number(type="PAGE")` creates `<autoNum>` element

#### Details
- **Method:** New convenience methods on HwpxDocument
- **Endpoint:** `add_checkbox()`, `add_page_number()`, `add_field()`, `add_auto_number()`
- **Request:** field/form specific parameters
- **Auth:** None

---

### e2e-owpml-full-impl-023: Misc Features Processing

**Chain:** Processing
**Status:** implemented

#### What
Implements remaining OWPML features: equation convenience API, OLE stub, highlight, ruby text, index marks, hidden comments, tab/linebreak/special chars, numbering/bullet styles, style create/modify, tab definitions, forbidden words.

#### Verification Criteria
- [ ] `add_equation(script)` creates `<equation>` with script content
- [ ] `add_highlight(start, end, color)` wraps text in `<markpenBegin/End>`
- [ ] `add_ruby(base_text, ruby_text)` creates `<dutmal>` element
- [ ] `create_style(name, type, char_pr_id, para_pr_id)` creates new style
- [ ] `add_numbering(type, format)` creates numbering definition
- [ ] `add_tab()`, `add_line_break()` insert special characters

#### Details
- **Steps:**
  1. Implement each feature as a method on HwpxDocument
  2. Each method manipulates the appropriate XML elements
  3. Register new definitions in header.xml where needed
- **Storage:** header.xml + section0.xml — WRITE

---

### e2e-owpml-full-impl-024: Full Document Response

**Chain:** Response
**Status:** implemented

#### What
Complete document with all OWPML features renders in Hancom Office.

#### Verification Criteria
- [ ] Document with charPr + paraPr + table + image + page setup opens without error
- [ ] All character formatting visible (font, size, color, decorations)
- [ ] All paragraph formatting applied (alignment, spacing, indent)
- [ ] Tables with merged cells render correctly
- [ ] Images display at correct size/position
- [ ] validate() returns no errors for the generated document

#### Details
- **Success Status:** All features render in Hancom Office
- **Response Shape:** Complete HWPX document
- **UI Updates:** Full-featured document in Hancom Office

---

### e2e-owpml-full-impl-025: Full Coverage Errors

**Chain:** Error
**Status:** implemented

#### What
Comprehensive error handling across all new features.

#### Verification Criteria
- [ ] All new methods have input validation
- [ ] Invalid enum values raise ValueError with valid options listed
- [ ] Type mismatches raise TypeError
- [ ] Generated documents pass `doc.validate()`

#### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| Invalid enum value | ValueError with valid options | null (client) |
| Type mismatch | TypeError | null (client) |
| Document validation failure | ValidationReport with details | null (server) |

---

## Deviations

### DEV-001: add_page_number uses add_control which has lxml/ET incompatibility
- **Spec step:** e2e-owpml-full-impl-022
- **Original:** add_page_number() creates pageNum element
- **Actual:** add_control() fails due to lxml/stdlib ET SubElement conflict in paragraph creation
- **Reason:** Deep internal code uses stdlib ET.SubElement but ensure_char_property returns lxml elements
- **Approved:** yes (known issue, workaround: use lxml SubElement directly)
