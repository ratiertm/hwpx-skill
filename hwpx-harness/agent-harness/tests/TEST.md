# HWPX CLI Test Plan

## Test Inventory

| File | Type | Coverage |
|------|------|----------|
| `test_core.py` | Unit | document, text, table, image, export, validate, session |
| `test_cli.py` | Integration | CLI command groups via Click testing |
| `test_e2e.py` | E2E | Full workflow: create → edit → export → validate |

## Unit Test Plan

### core/document.py
- [ ] `new_document()` creates valid HwpxDocument
- [ ] `open_document()` opens existing .hwpx file
- [ ] `open_document()` raises FileNotFoundError for missing file
- [ ] `open_document()` raises ValueError for non-.hwpx file
- [ ] `get_document_info()` returns correct section/paragraph counts

### core/text.py
- [ ] `extract_text()` returns full text content
- [ ] `find_text()` locates occurrences with position info
- [ ] `replace_text()` replaces all occurrences and returns count
- [ ] `add_paragraph()` adds text to document

### core/table.py
- [ ] `add_table()` creates table with specified dimensions
- [ ] `list_tables()` finds all tables in document

### core/image.py
- [ ] `add_image()` adds image from valid path
- [ ] `add_image()` raises FileNotFoundError for missing image
- [ ] `list_images()` returns image list
- [ ] `remove_image()` removes by index

### core/export.py
- [ ] `export_to_file()` writes text format
- [ ] `export_to_file()` writes markdown format
- [ ] `export_to_file()` writes html format
- [ ] `export_to_file()` raises ValueError for unknown format

### core/validate.py
- [ ] `validate_document()` returns valid for well-formed document
- [ ] `validate_package()` validates ZIP structure

### core/session.py
- [ ] Session creates/manages document state
- [ ] Undo/redo with snapshot stack
- [ ] Save tracks path and modified state
- [ ] Max undo depth enforced

## E2E Test Scenarios

1. **Document lifecycle**: new → add text → add table → save → reopen → verify
2. **Text extraction pipeline**: open → extract text → extract markdown → compare
3. **Find/replace workflow**: open → find → replace → verify → undo → verify original
4. **Image workflow**: new → add image → list → remove → verify
5. **Export pipeline**: open → export text → export md → export html → verify files
6. **Validation workflow**: open → validate schema → validate package → report

## Test Results

_(To be appended after test execution)_
