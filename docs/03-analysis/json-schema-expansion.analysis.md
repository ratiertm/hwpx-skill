---
template: analysis
description: Gap analysis for json-schema-expansion (v0.15.0) — Act-1 closure, 100% match
---

# json-schema-expansion Gap Analysis

> **Feature**: json-schema-expansion (옵션 A)
> **Version**: 0.15.0
> **Date**: 2026-04-29
> **Match Rate**: **100%** (55/55 verifiable items)
> **Plan**: [json-schema-expansion.plan.md](../01-plan/features/json-schema-expansion.plan.md)
> **Design**: [json-schema-expansion.design.md](../02-design/features/json-schema-expansion.design.md)
> **Iteration**: Act-1 (full closure)

---

## 1. Match Rate Breakdown

| Category | Items | Fulfilled | % |
|----------|-------|-----------|---|
| Design § 1.3 — 19 builder ↔ JSON type mapping | 19 | 19 | 100% |
| Design § 3 — 13 dataclasses | 13 | 13 | 100% |
| Design § 4 — Decoder dispatch (14 branches + 3 helpers) | 17 | 17 | 100% |
| Design § 6 — Test plan T-01..T-18 | 18 | 18 | 100% |
| Plan FR-01..FR-09 | 9 | 9 | 100% |
| Plan DoD § 4.1 (excluding PyPI release, N/A in Check) | 4 | 4 | 100% |
| Doc consistency | 2 | 2 | 100% |
| **Overall** | **55** | **55** | **100%** |

Status: **= 100% — ready for `/pdca report`.**

---

## 2. Fulfilled (Design ≡ Implementation)

### 2.1 19 builder ↔ JSON type mapping (100%)

All 19 HwpxBuilder.add_* methods reachable via JSON:
- 14 RunContent dispatch branches (decoder.py:88-162) — text, heading, image (path/url), table, bullet_list, numbered_list, nested_*, footnote, equation, highlight, shape_line/rect/draw_line + ValueError fallback
- 3 top-level deferred (header/footer/page_number) processed last
- 1 page_break (Paragraph.page_break flag) — kept from v0.14.0
- 1 image url branch (image_path XOR image_url) inside _apply_image

### 2.2 Schema dataclasses (13/13)

All present in `schema.py:35-118`. Plan § 6.1 Shape now correctly states `RunContent.type` is the discriminator (no separate `kind` field).

### 2.3 Decoder dispatch (17/17)

All branches raise `ValueError` on missing nested object — rhwp-strict-mode policy enforced consistently.

### 2.4 Tests — full coverage

| Tests | Count |
|-------|------|
| T-01..T-18 listed | **18 PASS** (T-03 added in Act-1) |
| Parametric ValueError guards | 11 PASS |
| FR-09 encoder round-trip | **6 PASS** (Act-1) |
| **New cases vs v0.14.0** | **35** |
| Total regression | **107 PASS** (was 100 in initial Do) |

### 2.5 Act-1 closures (the three previously-outstanding items)

| Item | Resolution | Evidence |
|------|------------|----------|
| **Plan § 6.1 Shape `kind` doc** | Field removed from Shape dataclass spec; docstring states `RunContent.type` is the discriminator and points to Design § 4.2 | `docs/01-plan/features/json-schema-expansion.plan.md:188-198` |
| **T-03 image url mock test** | `test_t03_image_url_mode_with_mocked_urllib` added — patches `urllib.request.urlopen` to serve a 1×1 PNG; asserts BinData entry in output zip | `tests/test_json_schema_expansion.py` (T-03 section) |
| **FR-09 encoder rich-type emission** | `_detect_rich_run` (encoder.py) detects `<hp:tbl>`/`<hp:pic>`/`<hp:footNote>`/`<hp:equation>`/`<hp:rect>`/`<hp:line>` → emits matching `RunContent.type`. `_extract_shape_from` reads geometry. `_parse_section` populates top-level header/footer/page_number from section XML | `pyhwpxlib/json_io/encoder.py` rich detect block + 6 new round-trip tests PASS |

### 2.6 Bonus features (Implementation > Design)

- `_build_nested_items` accepts `[depth, text]` tuple/list form
- Image legacy `path` key alias
- `_apply_table` raises on out-of-range index (improvement over silent skip)
- Shape detection falls back gracefully when curSz/offset absent
- `_detect_rich_run` returns None on unrecognized → caller falls through to text (preserves v0.14.0 back-compat for unknown XML)

---

## 3. Gaps

### 3.1 Outstanding (Design O, Implementation X)

**None.** All FR-01..FR-09 closed.

### 3.2 Intentionally out of scope (Plan FR-09 best-effort caveat)

| Item | Rationale |
|------|-----------|
| Heading detection in encoder | Requires style-table lookup (`<hh:paraStyle>` cross-ref). Plan § 5 risk row marks as deferred. |
| List detection (bullet/numbered/nested) in encoder | Requires `<hh:numbering>` style-table reverse mapping. Plan § 5 deferred. |
| Highlight detection in encoder | Requires `<hh:charPr>` highlight-color reverse mapping. Plan § 5 deferred. |

These are explicitly scoped out of FR-09 ("best-effort") and do not count against Match Rate. Track as v0.16.0 enhancement if user demand emerges (encoder lossless round-trip).

### 3.3 Doc consistency

**None.** Plan § 6.1 ↔ Design § 4.2 ↔ implementation now aligned.

---

## 4. FR-by-FR Verdict

| FR | Priority | Status | Evidence |
|----|----------|:------:|----------|
| FR-01 (12 new RunContent.type values) | High | ✅ | schema.py:124-154 |
| FR-02 (top-level header/footer/page_number) | High | ✅ | schema.py:297-299 + encoder.py round-trip |
| FR-03 (16 builder methods callable from JSON) | High | ✅ | All 19 mapped per § 1.3 |
| FR-04 (deferred actions last) | High | ✅ | decoder.py:63-69, T-15 PASS |
| FR-05 (Image path XOR url + dimensions) | High | ✅ | decoder.py:168-179, T-03 + T-04 PASS |
| FR-06 (List items, nested as `[depth, text]`) | High | ✅ | schema.py:240-256 |
| FR-07 (v0.14.0 back-compat) | High | ✅ | T-17 PASS, additive-only |
| FR-08 (unit + integration tests) | High | ✅ | 18/18 + 11 + 6 = 35 new |
| FR-09 (encoder round-trip best-effort) | Medium | ✅ | encoder.py rich detect, 6 new tests PASS |

---

## 5. Verdict

**Code-level implementation: complete and correct for all FRs.**

- All 13 design dataclasses present
- All 14 decoder dispatch branches working
- All 19 builder methods reachable from JSON (16% → 100% vs v0.14.0)
- Encoder emits rich `RunContent.type` for image/footnote/equation/shape — round-trip semantically equivalent for these element classes
- **107 tests PASS** (initial 100 + T-03 + 6 FR-09); zero regression
- v0.14.0 input back-compat preserved (T-17)
- rhwp-strict-mode policy enforced (unknown type → ValueError)
- Whale SecPr bug avoided (deferred top-level pattern, both encode + decode sides)
- Style-table-dependent types (heading/list/highlight in encoder) intentionally scoped out per Plan § 5; documented as such

**Recommendation: proceed to `/pdca report json-schema-expansion`.** No further iteration required. Optional v0.16.0 enhancement: style-table reverse-mapping for full lossless encoder round-trip — track only if real-world blocker appears.

---

## 6. Iteration History

| Iteration | Match Rate | Trigger | Outcome |
|-----------|:----------:|---------|---------|
| Initial (Do) | 95% | First implementation pass | FR-01..FR-08 done; FR-09 + T-03 + Shape doc outstanding |
| Act-1 | **100%** | Close all three Medium/Low items | FR-09 encoder rich-type emission, T-03 url-mock test, Plan § 6.1 Shape doc clarified. Total +7 PASS (100 → 107) |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-29 | Initial gap analysis (95%, Do completion) | Mindbuild + Claude |
| 0.2 | 2026-04-29 | Act-1 re-run: 100%, all three outstanding items closed | Mindbuild + Claude |
