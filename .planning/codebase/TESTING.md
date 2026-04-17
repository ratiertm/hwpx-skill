# Testing Patterns

**Analysis Date:** 2026-04-15

## Test Framework

**Runner:**
- pytest (Python 3.14 inferred from `__pycache__` naming)
- Config: no `pytest.ini`; no `[tool.pytest]` in `pyproject.toml` — default pytest discovery

**Assertion Library:**
- Built-in `assert` (pytest-style)

**Run Commands:**
```bash
pytest tests/                       # Run all tests (417 total)
pytest tests/test_form_fill_golden.py    # Single file
pytest tests/ -k "TestFillByLabels"      # Filter by class
pytest tests/ -v                    # Verbose
```

**Total Tests:** 417 collected

---

## Test File Organization

**Location:** All test files are in `tests/` (flat — no subdirectories)

**Naming:** `test_<area>.py`

**Fixtures:** Shared fixtures in `tests/conftest.py`

**Output artifacts:** Tests write `.hwpx` files to `tests/output/` (committed — used as regression baselines for visual inspection)

```
tests/
├── conftest.py                    # Shared fixtures: doc, tmp_hwpx, sample_form
├── test_api_core.py               # pyhwpxlib.api public API
├── test_api_extended.py           # Extended API: headers, footers, bullets, shapes
├── test_api_server.py             # FastAPI endpoint tests (skipped if fastapi absent)
├── test_api_shapes.py             # Drawing object API
├── test_converter.py              # Markdown → HWPX conversion
├── test_form_fill_golden.py       # fill_by_labels + _patch_empty_cell golden tests
├── test_form_pipeline.py          # form extract/generate round-trip (6 real forms)
├── test_form_pipeline_multirun.py # Multi-run charPr preservation
├── test_html_converters.py        # HTML → HWPX conversion
├── test_hwp2hwpx_golden.py        # HWP 5.x binary → HWPX conversion
├── test_hwpx_builder.py           # HwpxBuilder high-level API
├── test_object_model.py           # OWPML dataclass object model
├── test_refactor.py               # Structural rules: no magic numbers, func sizes
├── test_stability.py              # Exception handling, tempfile cleanup, regression
├── test_style_manager.py          # ensure_char_style, ensure_border_fill
├── test_visual_golden.py          # rhwp visual rendering (PNG) for files in Test/
└── test_writer_utils.py           # Low-level XML writer utilities
```

---

## Shared Fixtures (`tests/conftest.py`)

```python
@pytest.fixture
def doc():
    """Return a fresh HWPX document via create_document()."""
    from pyhwpxlib.api import create_document
    return create_document()

@pytest.fixture
def tmp_hwpx(tmp_path):
    """Return a path string for a temporary output file."""
    return str(tmp_path / "output.hwpx")

@pytest.fixture
def sample_form():
    """Return path to templates/sources/sample_의견제출서.hwpx — skips if missing."""
    path = PROJECT_ROOT / "templates" / "sources" / "sample_의견제출서.hwpx"
    if not path.exists():
        pytest.skip(f"Sample form not found: {path}")
    return str(path)
```

---

## Test Structure Patterns

### Class-per-feature grouping (dominant pattern)

```python
class TestAddParagraph:
    def test_returns_para(self, doc):         # unit: return type
    def test_text_content(self, doc, tmp_hwpx):  # integration: save+extract
    def test_unicode(self, doc, tmp_hwpx):    # edge: non-ASCII
    def test_multiple_paragraphs(self, ...):  # boundary: volume
```

### Parametrize over real fixture files

```python
FORMS = [
    ("sample_의견제출서", "templates/sources/sample_의견제출서.hwpx"),
    ("근로지원인서비스신청서", "templates/sources/근로지원인서비스신청서.hwpx"),
    ("서식SAMPLE1", "templates/sources/서식SAMPLE1.owpml"),
    ("SimpleTable", "templates/sources/SimpleTable.hwpx"),
]

@pytest.fixture(params=FORMS, ids=[f[0] for f in FORMS])
def form_path(request):
    name, rel_path = request.param
    abs_path = str(PROJECT_ROOT / rel_path)
    if not os.path.exists(abs_path):
        pytest.skip(f"Form not found: {abs_path}")
    return abs_path
```

This pattern appears in `test_form_pipeline.py`, `test_stability.py`, `test_refactor.py`, and `test_form_pipeline_multirun.py`. Missing fixture files cause `pytest.skip()`, not failure.

### Static content verification pattern

The most common integration assertion is:
```python
save(doc, tmp_hwpx)
text = extract_text(tmp_hwpx)
assert "expected content" in text
```

### ZIP validity assertion

All tests that generate `.hwpx` files verify they are valid ZIPs:
```python
assert zipfile.is_zipfile(output_path)
```

Some go further and inspect ZIP contents:
```python
with zipfile.ZipFile(output) as z:
    assert 'Contents/header.xml' in z.namelist()
    assert 'Contents/section0.xml' in z.namelist()
```

---

## Test Types

### Unit Tests

**Object model construction** (`tests/test_object_model.py`):
```python
def test_rectangle_create(self):
    r = Rectangle()
    assert r._object_type() == ObjectType.hp_rect

def test_rectangle_points(self):
    r = Rectangle()
    p0 = r.create_pt0()
    assert r.pt0 is p0  # create_* methods attach and return child
```

**Low-level XML patch** (`tests/test_form_fill_golden.py::TestPatchEmptyCell`):
```python
def test_replaces_self_closing_tag(self):
    xml = '<hp:tc><hp:cellAddr colAddr="1" rowAddr="2"/>...<hp:t/></hp:tc>'
    out = _patch_empty_cell(xml, 1, 2, "hello")
    assert "<hp:t>hello</hp:t>" in out
    assert "<hp:t/>" not in out

def test_missing_addr_returns_unchanged(self):
    xml = '<hp:tc><hp:cellAddr colAddr="0" rowAddr="0"/>...</hp:tc>'
    out = _patch_empty_cell(xml, 99, 99, "x")
    assert out == xml  # no-op when address not found
```

**Style deduplication** (`tests/test_style_manager.py`):
```python
def test_returns_same_id_for_same_style(self):
    cid1 = ensure_char_style(doc, font_name="Arial", height=1200, ...)
    cid2 = ensure_char_style(doc, font_name="Arial", height=1200, ...)
    assert cid1 == cid2

def test_different_fonts_get_different_ids(self):
    cid1 = ensure_char_style(doc, font_name="Arial", ...)
    cid2 = ensure_char_style(doc, font_name="Helvetica", ...)
    assert cid1 != cid2
```

### Integration Tests

**Round-trip tests** (extract → generate → re-extract):
```python
class TestRoundTrip:
    def test_table_count_preserved(self, form_path, tmp_path):
        orig = extract_form(form_path)
        generate_form(orig, output_path)
        clone = extract_form(output_path)
        assert len(orig["tables"]) == len(clone["tables"])

    def test_rows_cols_preserved(self, form_path, tmp_path):
        for ot, ct in zip(orig["tables"], clone["tables"]):
            assert ot["rows"] == ct["rows"]
            assert ot["cols"] == ct["cols"]
```

**Full document generation** (`tests/test_hwpx_builder.py::TestCorporateReport`):
```python
def test_full_corporate_report(self):
    doc = HwpxBuilder(table_preset='corporate')
    # add headings, tables, page breaks...
    out = doc.save(str(OUTPUT_DIR / "corporate_report.hwpx"))
    assert os.path.getsize(out) > 5000
    assert zipfile.is_zipfile(out)
```

### Structural / Linting Tests

Tests that read source code as text to enforce conventions:

**No bare except** (`tests/test_stability.py::TestExceptionHandling`):
```python
def test_no_bare_except_in_form_pipeline(self):
    content = (PROJECT_ROOT / "templates" / "form_pipeline.py").read_text()
    bare = re.findall(r'^\s*except\s*:', content, re.MULTILINE)
    assert len(bare) == 0
```

**No magic numbers** (`tests/test_refactor.py::TestDefaults`):
```python
def test_no_raw_magic_numbers_in_form_pipeline(self):
    # Checks that raw 141 and 3600 literals don't appear outside constant definitions
```

**Function size limit** (`tests/test_refactor.py::TestFunctionSplit`):
```python
def test_generate_table_under_100_lines(self):
    # Finds _generate_table() start/end by scanning for 'def ' lines
    assert func_lines <= 200
```

**No duplicate init blocks** (`tests/test_refactor.py::TestInitPara`):
```python
def test_no_duplicate_init_blocks_in_api(self):
    matches = re.findall(r'para\.id = str\(_random\.randint', content)
    assert len(matches) == 1  # only inside _init_para definition
```

### Visual / Golden Tests

**PNG rendering** (`tests/test_visual_golden.py`) — parametrized over all `.hwpx` files in `Test/`:
```python
def test_renders_without_error(hwpx, tmp_path):
    results = render_pages(hwpx, str(tmp_path))
    assert len(results) > 0
    for r in results:
        assert r["svg_chars"] > 100       # not empty SVG
        assert os.path.exists(r["png"])   # PNG file created

def test_png_not_empty(hwpx, tmp_path):
    for r in results:
        assert os.path.getsize(r["png"]) > 1000  # not blank image
```

These tests require `wasmtime` + `resvg-py` (from `pyproject.toml [preview]` extras). They run against files in `Test/` directory (not `tests/output/`).

---

## Skip Patterns

Tests skip gracefully when fixture files are absent (common for template files not committed to repo):
```python
if not os.path.exists(abs_path):
    pytest.skip(f"Form not found: {abs_path}")
```

Optional dependencies cause entire test modules to skip:
```python
pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="fastapi not installed")
```

---

## What Is Tested

| Area | Test File | Coverage |
|------|-----------|----------|
| Public API (create, add, save, extract) | `test_api_core.py` | High — 8 classes, save/extract/fill/merge |
| HwpxBuilder high-level | `test_hwpx_builder.py` | High — presets, alignment, page breaks, corporate report |
| Form extract/generate round-trip | `test_form_pipeline.py` | High — 6 real form fixtures, table count/dim/cell preservation |
| Form fill (label-based) | `test_form_fill_golden.py` | High — empty cell, text appears, ZIP valid, unknown label, multi-fill |
| Exception handling rules | `test_stability.py` | Medium — bare except, silent swallow, tempfile cleanup |
| Structural/refactor rules | `test_refactor.py` | Medium — magic numbers, func size, no duplicate init |
| Object model (OWPML classes) | `test_object_model.py` | Medium — construction + factory methods, no serialization |
| Style deduplication | `test_style_manager.py` | Medium — char style, border fill dedup |
| Visual rendering | `test_visual_golden.py` | Medium — 25 files × 2 checks (SVG chars, PNG size) |
| Multi-run charPr preservation | `test_form_pipeline_multirun.py` | Medium — body text run count, XML namespace tags |
| HTML → HWPX | `test_html_converters.py` | Medium |
| Markdown → HWPX | `test_converter.py` | Medium |
| HWP binary conversion | `test_hwp2hwpx_golden.py` | Medium — 12 fixture-based golden tests |
| FastAPI endpoints | `test_api_server.py` | Low — skipped unless fastapi installed |
| Low-level XML writers | `test_writer_utils.py` | Low — XML builder primitives, manifest/version/settings writers |

---

## What Is NOT Tested

- **Table dual-height sync rule** (hp:sz + hp:cellSz) — no automated test, documented in `skill/references/HWPX_RULEBOOK.md` and memory `reference_hwpx_table_dual_height.md`
- **Header/footer SecPr ordering bug** — deferred, documented in memory `feedback_hwpx_whale_bug.md`
- **textColor / partial style** on text runs — noted as next TODO in memory
- **Nested table (표>셀>표) layout** — `form_pipeline.py` handles it, minimal direct test coverage
- **MCP server tools** (`pyhwpxlib/mcp_server/`) — not in test suite
- **CLI commands** (`pyhwpxlib/cli.py`) — not in test suite
- **Preview rendering** beyond PNG existence/size — no pixel-level or fill-ratio threshold tests
- **form_editor.py** — no tests (noted as next TODO)
- **checkbox fill correctness** — noted as next TODO (`feedback_test_required.md`)

---

## Regression Strategy

Each Phase of work (Phase 1, 2, 3 in `test_form_pipeline_multirun.py`, `test_stability.py`, `test_refactor.py`) ends with an explicit `TestRegression` class that re-runs the same round-trip tests from the previous phase. This pattern ensures new features don't break earlier functionality.

```python
class TestRegression:
    """Phase 2 변경이 기존 기능을 깨뜨리지 않음."""

    def test_roundtrip_still_works(self, form_path, tmp_path):
        # Same assertions as Phase 1 tests
```

---

*Testing analysis: 2026-04-15*
