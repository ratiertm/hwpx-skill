# Coding Conventions

**Analysis Date:** 2026-04-15

## Overview

This codebase is a Python library (`pyhwpxlib`) for creating and editing HWPX (Hancom Office XML) documents. Most conventions are enforced via `skill/SKILL.md` (the LLM-facing skill doc) and the critical rules baked into `skill/references/HWPX_RULEBOOK.md`. Violations cause Whale/한컴오피스 to fail to open the file — not just test failures.

---

## Naming Patterns

**Files:**
- Module files use `snake_case`: `api.py`, `style_manager.py`, `hwp_reader.py`, `html_to_hwpx.py`
- Writer modules are grouped: `pyhwpxlib/writer/manifest_writer.py`, `pyhwpxlib/writer/shape_writer.py`
- Object model files mirror OWPML structure: `pyhwpxlib/objects/section/objects/shapes.py`
- Test files: `test_<area>.py` — all flat in `tests/`

**Classes:**
- PascalCase: `HwpxBuilder`, `HWPXFile`, `HWPXObject`, `BlankFileMaker`
- Object model classes match OWPML names: `Rectangle`, `Ellipse`, `DrawingObject`, `ConnectLine`
- Writer classes use PascalCase: `XMLStringBuilder`, `HWPXWriter`

**Functions:**
- Public API: `snake_case` — `create_document()`, `add_paragraph()`, `extract_text()`, `fill_template()`
- Private helpers: leading underscore — `_init_para()`, `_patch_empty_cell()`, `_generate_table()`, `_apply_merges()`
- Internal pyhwpxlib helpers: `_colorref_to_hex()`, `_hard_wrap()`

**Variables:**
- `snake_case` throughout
- Constants: `UPPER_SNAKE_CASE` — `PAGE_HEIGHT`, `CELL_MARGIN`, `ROW_HEIGHT`, `NESTED_OUT_MARGIN`, `PAGE_WIDTH`

**Types:**
- Dataclasses from `abc`: `HWPXObject(ABC)`, `SwitchableObject(HWPXObject)`
- Namespaces as `Enum`: `class Namespaces(Enum)` in `pyhwpxlib/constants/namespaces.py`
- ObjectType: `pyhwpxlib/object_type.py` — enum mapping to OWPML element names (`hp_rect`, `hp_tbl`, etc.)

---

## XML Handling — Critical Rules

These rules exist because HWPX is a ZIP of XML files with strict Hancom namespace requirements.

### Rule 1: ET.tostring is PROHIBITED for re-serialization

```python
# WRONG — destroys namespace prefixes, Whale fails to open
import xml.etree.ElementTree as ET
root = ET.fromstring(xml)
new_xml = ET.tostring(root, encoding='unicode')  # ns0: prefix leaks

# CORRECT — string replacement preserves original namespace declarations
with open('unpacked/Contents/section0.xml', 'r') as f:
    xml = f.read()
xml = xml.replace('>원래 텍스트<', '>새 텍스트<', 1)
with open('unpacked/Contents/section0.xml', 'w') as f:
    f.write(xml)
```

This rule is enforced in `skill/SKILL.md` (rule #3), `skill/references/editing.md`, and `skill/references/HWPX_RULEBOOK.md` (rule 733). The comment in `templates/form_pipeline.py` at line 52 also flags this: `# ET.tostring은 ns0: 접두사로 변환하므로, 원본 XML 문자열에서 직접 추출`.

### Rule 2: No `\n` inside `<hp:t>` elements

```xml
<!-- WRONG -->
<hp:t>첫줄\n둘째줄</hp:t>

<!-- CORRECT — split into separate <hp:p> elements -->
<hp:p><hp:run><hp:t>첫줄</hp:t></hp:run></hp:p>
<hp:p><hp:run><hp:t>둘째줄</hp:t></hp:run></hp:p>
```

The `text.setter` in the library auto-splits on `\n` into separate `<hp:p>` elements.

### Rule 3: linesegarray only on the secPr paragraph

Only the first `<hp:p>` containing `<secPr>` gets a `<hp:linesegarray>`. All other paragraphs (body text, cell content) must NOT have `<hp:linesegarray>` — Hancom recomputes layout on load. Adding it to other paragraphs causes all lines to stack at the same vertical position.

### Rule 4: secPr paragraph must be empty (no text)

```xml
<!-- WRONG — text in same p as secPr causes overlap -->
<hp:p><hp:run><secPr .../></hp:run><hp:run><hp:t>Title</hp:t></hp:run></hp:p>

<!-- CORRECT -->
<hp:p><hp:run><secPr .../></hp:run><hp:linesegarray>...</hp:linesegarray></hp:p>
<hp:p><hp:run><hp:t>Title</hp:t></hp:run></hp:p>
```

### Rule 5: paraPr must include lineSpacing

Every new `<hh:paraPr>` requires `<hh:lineSpacing type="PERCENT" value="150" unit="HWPUNIT"/>`. Without it Hancom renders all lines at y=0 (overlapping). Standard value is 150 (1.5 lines).

### Rule 6: mimetype entry must be STORED (no compression)

The ZIP `mimetype` entry must be the first entry and use `ZIP_STORED` (compression=0). `pyhwpxlib pack` enforces this automatically.

### Rule 7: Table dual-height synchronization

When modifying table row heights via XML, both `<hp:sz>` and `<hp:cellSz>` must be updated to the same value. Changing only one causes the renderer to ignore the change.

### Rule 8: Empty cell patching requires `_patch_empty_cell()`

Cells with empty `<hp:t/>` cannot be filled by simple string replace (the tag has no content to anchor to). Use `_patch_empty_cell(xml, col, row, value)` from `templates/form_pipeline.py` which uses `cellAddr` as the anchor:

```python
from form_pipeline import _patch_empty_cell
new_xml = _patch_empty_cell(section_xml, col_addr, row_addr, "new value")
```

### Rule 9: HWP Color is BGR not RGB

`0xFF0000` in HWP = blue (not red). Always use `_colorref_to_hex()` when reading color values from HWP binary.

---

## Namespace Conventions

Namespaces are defined in `pyhwpxlib/constants/namespaces.py` as both an `Enum` and module-level constants:

```python
# Primary namespaces used in section XML
hp  = "http://www.hancom.co.kr/hwpml/2011/paragraph"   # paragraph/run/text
hh  = "http://www.hancom.co.kr/hwpml/2011/head"        # header: paraPr, charPr
hs  = "http://www.hancom.co.kr/hwpml/2011/section"     # section root
hm  = "http://www.hancom.co.kr/hwpml/2011/master-page"
hpf = "http://www.hancom.co.kr/schema/2011/hpf"        # content manifest
```

In test files that need namespace-aware XML parsing, the pattern is:
```python
_HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
# Usage: para.find(f"{_HP}run")
```

---

## Import Organization

**Order observed in test files:**
1. Standard library (`os`, `sys`, `re`, `zipfile`, `tempfile`, `pathlib`)
2. `pytest`
3. Project root path injection: `sys.path.insert(0, str(PROJECT_ROOT))`
4. Local project imports (`from pyhwpxlib.api import ...`, `from form_pipeline import ...`)

**Pattern for project root resolution** (consistent across all test files):
```python
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "templates"))  # when form_pipeline needed
```

**Path Aliases:**
- No `__init__` barrel files for convenience imports at test level
- `from pyhwpxlib import HwpxBuilder, DS` — `__init__.py` re-exports key symbols

---

## Error Handling

**Rules enforced by tests in `tests/test_stability.py`:**
- No bare `except:` (use `except SomeError as e:`)
- No `except Exception: pass` (silent swallowing)
- No `(IndexError, Exception)` redundant combos — `Exception` already covers `IndexError`
- Specific exceptions: `FileNotFoundError`, `KeyError`, `zipfile.BadZipFile` for file operations

**Pattern for optional dependency guards:**
```python
try:
    from fastapi.testclient import TestClient
    from api_server.main import app
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
```

---

## Magic Numbers — Use Named Constants

In `templates/form_pipeline.py`, magic numbers must be named constants (enforced by `tests/test_refactor.py`):

```python
PAGE_HEIGHT     = 84188
CELL_MARGIN     = 141
ROW_HEIGHT      = 3600
NESTED_OUT_MARGIN = 283
PAGE_WIDTH      = 59528
```

Using raw `141` or `3600` literals in `form_pipeline.py` (outside the constant definition lines) will fail `test_no_raw_magic_numbers_in_form_pipeline`.

---

## Function Design

**Size limit:** `_generate_table()` in `form_pipeline.py` must be ≤200 lines (enforced by `tests/test_refactor.py::TestFunctionSplit::test_generate_table_under_100_lines`). Functions exceeding this should be split into named helpers: `_apply_merges()`, `_apply_cell_alignment()`, `_generate_nested_tables()`.

**Paragraph initialization:** Never duplicate `para.id = str(_random.randint(...))` inline. Use `_init_para(para, ...)` from `pyhwpxlib/api.py`.

---

## Object Model Pattern

All OWPML objects extend `HWPXObject` (dataclass + ABC):
```python
@dataclass
class Rectangle(SwitchableObject):
    def _object_type(self) -> ObjectType:
        return ObjectType.hp_rect
```

Factory methods use `create_*` naming: `create_pt0()`, `create_sz()`, `create_caption()`, `create_offset()`. These create-and-attach child objects and return them for chaining.

---

## Form Structure Decision Pattern

When working with existing HWPX forms, always classify structure before filling:

- **Structure A** (adjacent cell): label cell + separate empty value cell → use `fill_by_labels()`
- **Structure B** (same cell): label + inline whitespace placeholder → use unpack → string replace → pack

```python
# Never call fill_by_labels without analyze first
form = extract_form(template_path)
# Check if label cells contain trailing whitespace (structure B indicator)
```

---

## Validation Workflow

Every HWPX created or edited must be validated before delivery:
```bash
pyhwpxlib validate output.hwpx
# Checks: ZIP validity, required files, mimetype, XML parsing, namespaces
```

After validation, a PNG preview must be rendered and visually inspected (rule #6 in SKILL.md). Reporting "complete" without viewing the preview PNG is a rule violation.

---

*Convention analysis: 2026-04-15*
