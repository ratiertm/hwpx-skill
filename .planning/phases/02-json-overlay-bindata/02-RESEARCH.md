# Phase 2: JSON Overlay 정밀화 + BinData 에러 핸들링 - Research

**Researched:** 2026-04-15
**Domain:** HWPX XML text replacement, HWP binary data handling, overlay JSON schema
**Confidence:** HIGH

## Summary

Phase 2 addresses four requirements: precise `<hp:t>` text replacement (TS-3), BinData crash prevention (TS-4), image replacement via overlay (CF-2), and nested table overlay support (CF-3). The core challenge is that `overlay.py`'s `apply_overlay` uses naive raw string replacement (`xml.replace(">original<", ">new<")`) which fails when text is split across multiple `<hp:t>` XML elements -- a common pattern in HWPX documents where a single logical string like "울산중부소방서" is stored as `<hp:t>울산중부</hp:t><hp:t>소방서</hp:t>`.

The BinData fix is straightforward: wrap `_decompress()` calls in `_attach_binary_data()` with try/except. The image replacement and nested table features have skeletal implementations but need testing and validation.

**Primary recommendation:** Use regex-based multi-`<hp:t>` pattern matching for text replacement (avoids ET namespace rewriting), store individual `<hp:t>` parts in extract, and add comprehensive tests as this module has zero test coverage.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TS-3 | JSON Overlay `<hp:t>` 단위 교체 | Regex-based multi-hp:t replacement pattern verified; extract must preserve individual `<hp:t>` parts |
| TS-4 | BinData 에러 핸들링 | try/except in `_attach_binary_data` + warning log + empty bytes fallback |
| CF-2 | JSON Overlay 이미지 교체 | `apply_overlay` already has `image_replacements` param; needs BinData path matching fix + tests |
| CF-3 | Overlay 중첩 표 지원 | `_extract_table` recursion exists; `apply_overlay` cell replacement needs nested-aware targeting |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| xml.etree.ElementTree | stdlib | XML parsing for extract phase | Already used; no additional dependency |
| re | stdlib | Regex-based `<hp:t>` pattern replacement in apply phase | Avoids ET namespace rewriting problem |
| zipfile | stdlib | Direct ZIP manipulation (replace subprocess unpack/repack) | Already imported; faster than subprocess |
| zlib | stdlib | BinData decompression error handling | Already used in hwp2hwpx.py |
| hashlib | stdlib | SHA256 verification | Already used |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| logging | stdlib | Warning output for BinData skip | Replace silent failures with logged warnings |
| pytest | 9.0.2 | Test framework | All new code needs tests |

**No new dependencies required.** This phase works entirely with stdlib.

## Architecture Patterns

### Recommended Change Structure
```
pyhwpxlib/
├── json_io/
│   ├── overlay.py        # PRIMARY: extract + apply improvements
│   └── encoder.py        # MINOR: no changes needed for this phase
├── hwp2hwpx.py           # TS-4: try/except in _attach_binary_data
tests/
├── test_overlay.py       # NEW: golden-file tests for overlay
├── golden/
│   └── overlay/          # NEW: test fixtures
```

### Pattern 1: Multi-`<hp:t>` Extraction with Parts Preservation

**What:** During `extract_overlay`, store individual `<hp:t>` text segments alongside the joined value.
**When to use:** Every text extraction -- both free-standing paragraphs and table cells.

```python
# In _extract_from_paragraph, for each run's <hp:t> elements:
t_elements = run_el.findall(f"{_HP}t")
parts = [_collect_t_text(t) for t in t_elements]
joined = "".join(parts)  # NOT " ".join -- no artificial space

text_entry = {
    "id": f"t{_text_id[0]}",
    "location": f"{prefix}/run{ri}",
    "value": joined,
    "original": joined,
    "original_parts": parts,  # NEW: preserve individual <hp:t> contents
    "style_hint": hint,
}
```

For cells, similarly:
```python
# In _extract_cell_full_text, return parts list alongside joined text
def _extract_cell_parts(tc_el) -> tuple[str, list[str]]:
    """Return (joined_text, individual_hp_t_parts)."""
    parts = []
    for t_el in tc_el.findall(f".//{_HP}t"):
        parts.append(_collect_t_text(t_el))
    return "".join(parts), parts  # join without space for matching
```

### Pattern 2: Regex-Based Precise Replacement

**What:** Build a regex pattern from `original_parts` that matches the actual XML structure, then replace with single `<hp:t>`.
**When to use:** In `apply_overlay` for both text fields and table cells.

```python
import re

def _replace_text_in_xml(xml: str, original_parts: list[str], new_value: str) -> str:
    """Replace multi-<hp:t> text with new value, preserving XML structure."""
    if len(original_parts) == 1:
        # Simple case: single <hp:t>
        old = f">{_xml_escape(original_parts[0])}<"
        new = f">{_xml_escape(new_value)}<"
        return xml.replace(old, new, 1)
    
    # Multi-<hp:t> case: build regex pattern
    escaped_parts = [re.escape(_xml_escape(p)) for p in original_parts]
    # Match: <hp:t>part1</hp:t> [whitespace] <hp:t>part2</hp:t> ...
    parts_pattern = r"</hp:t>\s*<hp:t>".join(escaped_parts)
    full_pattern = f"<hp:t>{parts_pattern}</hp:t>"
    replacement = f"<hp:t>{_xml_escape(new_value)}</hp:t>"
    return re.sub(full_pattern, replacement, xml, count=1)

def _xml_escape(text: str) -> str:
    """Escape XML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
```

**Verified:** This regex approach was tested and correctly handles `<hp:t>울산중부</hp:t><hp:t>소방서</hp:t>` -> `<hp:t>울산중부 구청</hp:t>`.

### Pattern 3: BinData Error Handling

**What:** Wrap individual stream decompression in try/except, log warning, skip failed streams.
**When to use:** In `_attach_binary_data()` in `hwp2hwpx.py`.

```python
def _attach_binary_data(hwpx, hwp: '_HWPDocument'):
    attachments = {}
    for bin_id, ext in hwp.bin_data_ids.items():
        hex_id = f"BIN{bin_id:04X}"
        ole_stream = f"BinData/{hex_id}.{ext}"
        if hwp.ole.exists(ole_stream):
            try:
                raw = hwp.ole.openstream(ole_stream).read()
                data = hwp._decompress(raw)
                attachments[f"BinData/{hex_id}.{ext}"] = data
            except Exception as e:
                logger.warning("Failed to decompress BinData %s: %s — skipping", ole_stream, e)
        else:
            logger.warning("Binary stream not found in HWP OLE: %s", ole_stream)
    hwpx._binary_attachments = attachments
```

### Pattern 4: Direct ZIP Manipulation (Replace Subprocess)

**What:** Use `zipfile` module directly instead of subprocess unpack/repack.
**When to use:** In `apply_overlay` -- this is a performance improvement that also reduces fragility.

```python
def apply_overlay(source_hwpx, overlay, output_path, *, image_replacements=None):
    source_path = Path(source_hwpx)
    # ... SHA256 check ...
    
    with zipfile.ZipFile(source_path, 'r') as zin:
        sec_path = overlay.get("section_path", f"Contents/section{overlay.get('section_idx', 0)}.xml")
        xml = zin.read(sec_path).decode("utf-8")
        
        # Apply text replacements
        for field in overlay.get("texts", []):
            # ... replacement logic ...
        
        # Write output ZIP
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == sec_path:
                    zout.writestr(item, xml.encode("utf-8"))
                elif image_replacements and item.filename.startswith("BinData/"):
                    # Check if this binary should be replaced
                    bin_name = Path(item.filename).stem
                    if bin_name in image_replacements:
                        zout.writestr(item, image_replacements[bin_name])
                    else:
                        zout.writestr(item, zin.read(item.filename))
                else:
                    zout.writestr(item, zin.read(item.filename))
    
    return output_path
```

**Note on mimetype:** HWPX validation requires `mimetype` as the first entry, uncompressed. When rewriting ZIP, preserve the original entry order and compression settings.

### Anti-Patterns to Avoid
- **ET for apply phase:** Python's `xml.etree.ElementTree` rewrites namespace prefixes (`hp:` -> `ns0:`) which breaks HWPX documents. Only use ET for parsing/extraction, never for serialization back to HWPX XML.
- **Space-joining `<hp:t>` parts:** Current `_extract_cell_full_text` uses `" ".join(parts)` which introduces artificial spaces. Use `"".join(parts)` for matching accuracy.
- **Unbounded string replace:** `xml.replace(old, new)` without `count=1` could replace unintended occurrences of the same text.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ZIP manipulation | subprocess unpack/repack | `zipfile` stdlib | 2 subprocess calls = 2 Python interpreter launches; zipfile is already imported |
| XML escaping | manual character replacement | `xml.sax.saxutils.escape()` | Handles all XML special chars correctly |
| Binary format detection | custom magic bytes | existing `_decompress` fallback chain | Already handles zlib vs raw-deflate |

## Common Pitfalls

### Pitfall 1: `<hp:t>` Join Semantics
**What goes wrong:** `_extract_cell_full_text` joins parts with `" "` (space), but the actual XML has no space between `</hp:t><hp:t>`. When trying to replace the joined text, the pattern `>울산중부 소방서<` doesn't exist in the XML.
**Why it happens:** The space was added for human readability but breaks round-trip replacement.
**How to avoid:** Store `original_parts` list in extract. In `_extract_cell_full_text`, join with `""` for matching purposes. Use the parts list for regex-based replacement.
**Warning signs:** `apply_overlay` returns with `changes = 0` even though edits were requested.

### Pitfall 2: XML Special Characters in Text
**What goes wrong:** Text containing `&`, `<`, `>` is stored unescaped in overlay JSON but appears as `&amp;`, `&lt;`, `&gt;` in the actual XML.
**Why it happens:** Current code does `>original<` matching without XML-escaping `original`.
**How to avoid:** Always XML-escape text values before building the search pattern.
**Warning signs:** Replacement fails silently for text containing special characters.

### Pitfall 3: Mimetype Entry Order in ZIP
**What goes wrong:** HWPX validation requires `mimetype` as the first ZIP entry, stored uncompressed (`ZIP_STORED`). If rewriting the ZIP with `zipfile`, the entry order and compression may change.
**Why it happens:** `zipfile.ZipFile` doesn't guarantee entry order when adding files.
**How to avoid:** When rewriting ZIP, iterate `zin.infolist()` in order and preserve `compress_type` for each entry. Special-case `mimetype` to use `ZIP_STORED`.
**Warning signs:** `hwpx_validate` fails with "mimetype not first entry" error.

### Pitfall 4: BinData Reference Integrity
**What goes wrong:** After skipping a corrupt BinData stream, the section XML still references it via `binaryItemIDRef`. Whale renderer shows a broken image icon or crashes.
**Why it happens:** Only the binary data is skipped; the XML reference remains.
**How to avoid:** Log the skipped BinData ID. The XML reference is acceptable -- Whale handles missing BinData gracefully (shows placeholder). Do NOT try to remove XML references automatically.
**Warning signs:** `logger.warning` about skipped BinData should be documented for user awareness.

### Pitfall 5: Nested Table Double-Extraction
**What goes wrong:** `_extract_table` uses `tc_el.findall(f".//{_HP}tbl")` which finds ALL descendant tables, including tables nested multiple levels deep. This can cause the same nested table to be extracted multiple times.
**Why it happens:** The `.//{_HP}tbl` XPath matches all descendants, not just direct children.
**How to avoid:** Use a more targeted XPath or check if the found table is a direct child of a paragraph within the cell, not inside a deeper nested table.
**Warning signs:** Duplicate table entries in overlay JSON with same content.

## Code Examples

### Example 1: Safe Multi-`<hp:t>` Replacement
```python
# Verified by testing - regex approach handles split <hp:t> correctly
import re

xml = '<hp:run charPrIDRef="5"><hp:t>울산중부</hp:t><hp:t>소방서</hp:t></hp:run>'
original_parts = ['울산중부', '소방서']
new_text = '울산중부 구청'

escaped_parts = [re.escape(p) for p in original_parts]
parts_pattern = r"</hp:t>\s*<hp:t>".join(escaped_parts)
full_pattern = f"<hp:t>{parts_pattern}</hp:t>"
replacement = f"<hp:t>{new_text}</hp:t>"
result = re.sub(full_pattern, replacement, xml, count=1)
# Result: '<hp:run charPrIDRef="5"><hp:t>울산중부 구청</hp:t></hp:run>'
```

### Example 2: BinData Error Handling Pattern
```python
# Matches existing logger.warning pattern at line 990 of hwp2hwpx.py
try:
    raw = hwp.ole.openstream(ole_stream).read()
    data = hwp._decompress(raw)
    attachments[key] = data
except Exception as e:
    logger.warning("Failed to decompress BinData %s: %s -- skipping", ole_stream, e)
    # Do NOT set attachments[key] = b'' -- just skip entirely
    # The XML binaryItemIDRef will remain but Whale handles missing BinData
```

### Example 3: ZIP Rewrite with Mimetype Preservation
```python
with zipfile.ZipFile(source, 'r') as zin:
    with zipfile.ZipFile(output, 'w') as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == sec_path:
                data = modified_xml.encode("utf-8")
            # Preserve original compression type
            zout.writestr(item, data)
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml (in agent-harness subdir); conftest.py in tests/ |
| Quick run command | `python -m pytest tests/test_overlay.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TS-3a | extract_overlay preserves individual hp:t parts | unit | `pytest tests/test_overlay.py::test_extract_preserves_parts -x` | Wave 0 |
| TS-3b | apply_overlay replaces split hp:t text | unit | `pytest tests/test_overlay.py::test_apply_split_hp_t -x` | Wave 0 |
| TS-3c | apply_overlay handles XML special characters | unit | `pytest tests/test_overlay.py::test_apply_xml_escape -x` | Wave 0 |
| TS-4a | _attach_binary_data skips corrupt BinData | unit | `pytest tests/test_overlay.py::test_bindata_decompress_error -x` | Wave 0 |
| TS-4b | convert() completes with corrupt BinData | integration | `pytest tests/test_overlay.py::test_hwp_convert_partial_bindata -x` | Wave 0 |
| CF-2 | apply_overlay replaces image via image_replacements | unit | `pytest tests/test_overlay.py::test_image_replacement -x` | Wave 0 |
| CF-3 | extract_overlay includes nested table cells | unit | `pytest tests/test_overlay.py::test_nested_table_extraction -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_overlay.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_overlay.py` -- new file covering TS-3, TS-4, CF-2, CF-3
- [ ] Test fixtures: sample HWPX with split `<hp:t>`, nested tables, images
- [ ] Test fixtures: sample HWP with corrupt BinData (can be mocked)

## Open Questions

1. **Sample HWPX with split `<hp:t>` pattern**
   - What we know: The 울산중부소방서 case demonstrates the bug. The `보조금_교부_신청서.hwpx` sample has simple single-`<hp:t>` patterns.
   - What's unclear: We don't have a sample file that reproduces the split pattern in the test fixtures.
   - Recommendation: Create a synthetic test fixture by programmatically building XML with split `<hp:t>` elements, or find/create a real HWPX with this pattern. Unit tests can use inline XML strings.

2. **`_extract_cell_full_text` join semantics**
   - What we know: Currently joins with `" "` (space). Changing to `""` (no space) changes the `value` and `original` fields, which is a breaking change for existing overlay JSON consumers.
   - What's unclear: Whether any downstream code depends on the space-separated format.
   - Recommendation: Keep `value` space-separated for readability, but add `original_parts` list for precise replacement. The `original` field should use `""` join for matching.

3. **Nested table double-extraction**
   - What we know: `tc_el.findall(f".//{_HP}tbl")` matches ALL descendant tables.
   - What's unclear: Whether real documents have more than one level of nesting.
   - Recommendation: Fix the XPath to only match direct-child-paragraph tables, not deeper descendants. Use `tc_el.findall(f"./{_HP}subList/{_HP}p/{_HP}run/{_HP}tbl")` or similar.

## Sources

### Primary (HIGH confidence)
- `pyhwpxlib/json_io/overlay.py` -- direct code analysis of current implementation
- `pyhwpxlib/hwp2hwpx.py:419-425, 979-991` -- BinData decompression and attachment code
- `.planning/codebase/CONCERNS.md` -- documented bugs and fragile areas
- `.planning/codebase/ARCHITECTURE.md` -- namespace handling, form pipeline patterns
- Local testing: regex-based multi-`<hp:t>` replacement verified in Python 3.14

### Secondary (MEDIUM confidence)
- HWPX ZIP structure requirements (mimetype first entry) from `scripts/validate.py` patterns
- ET namespace rewriting behavior confirmed by local test

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all stdlib, no new dependencies
- Architecture: HIGH -- patterns verified by local testing, existing codebase patterns followed
- Pitfalls: HIGH -- all derived from direct code analysis and confirmed bug reports

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable domain, no external dependency changes expected)
