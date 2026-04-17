# Phase 1: 테마 시스템 코어 - Research

**Researched:** 2026-04-15
**Domain:** HWPX document theming — color palettes, font registration, size/margin presets
**Confidence:** HIGH

## Summary

Phase 1 requires building a `Theme` dataclass that unifies the currently scattered design tokens (DS dict, TABLE_PRESETS, _HEADING_STYLES, hardcoded fontfaces) into a single coherent system. The codebase already has all the low-level machinery needed: `style_manager.py` has `_ensure_font_registered()` for multi-font registration, `ensure_char_style()` accepts `font_name` parameter, and the object model supports per-language fontRef via `ValuesByLanguage.set()` (hangul vs latin). The design guide (`design_guide.md`) defines 10 named palettes with Primary/Secondary/Accent/Surface colors. The gap is purely at the orchestration level — no code connects palettes to the builder, and fonts are hardcoded to 함초롬돋움 in two places (`blank_file_maker.py:258-278` and the legacy `_build_header_legacy` dead code).

The key architectural insight is that `HwpxBuilder.save()` replays actions through `pyhwpxlib.api` functions, which call `style_manager.ensure_*()` on an `HWPXFile` created by `create_document()` (which delegates to `BlankFileMaker`). The theme must be threaded through this entire chain: `HwpxBuilder.__init__(theme=)` → `save()` → `create_document(fonts=)` → `BlankFileMaker.make(fonts=)` for fontface setup, and `ensure_char_style(font_name=, height=, text_color=)` for per-element styling.

**Primary recommendation:** Create `pyhwpxlib/themes.py` with a `Theme` dataclass containing `palette`, `fonts`, `sizes`, and `margins` sub-structures. Provide 10 built-in themes from design_guide.md palettes. Wire into `HwpxBuilder.__init__(theme='forest')` and propagate through `save()` to the object model API. Keep `theme='default'` producing identical output to current behavior for backward compatibility.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TS-1 | 테마 시스템 기본 구조 — `HwpxBuilder(theme='name')` API, 팔레트+폰트+사이즈+여백 통합, DS/TABLE_PRESETS 통합, 10종 내장 테마, 하위 호환 | Theme dataclass design, palette data from design_guide.md, TABLE_PRESETS derivation pattern, backward compat via `theme='default'` |
| TS-2 | 폰트 시스템 — header.xml fontfaces 복수 폰트 등록, 제목/본문/캡션 폰트 분리, charPr fontRef 참조, 한글/라틴 폰트 분리 | `_ensure_font_registered()` in style_manager.py, `ValuesByLanguage.set()` for per-lang fontRef, `BlankFileMaker._add_font_pair()` pattern |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dataclasses | stdlib | Theme/Palette/FontSet/SizeSet data model | Already used throughout codebase (objects/ tree) |
| copy.deepcopy | stdlib | Clone base charPr/paraPr for new styles | Already used in style_manager.py |

### Supporting
No new dependencies needed. This phase is purely internal refactoring of existing code structures.

## Architecture Patterns

### Recommended Project Structure
```
pyhwpxlib/
├── themes.py          # NEW: Theme, Palette, FontSet, SizeSet, Margins dataclasses + BUILTIN_THEMES
├── builder.py         # MODIFIED: theme= parameter, DS/TABLE_PRESETS derived from theme
├── style_manager.py   # UNCHANGED: already supports font_name, height, text_color
├── tools/
│   └── blank_file_maker.py  # MODIFIED: accept font list from theme
└── api.py             # MODIFIED: _HEADING_STYLES → accept overrides from theme
```

### Pattern 1: Theme Dataclass Hierarchy
**What:** A frozen dataclass tree that fully specifies visual appearance.
**When to use:** Every time a document is created.
**Example:**
```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class Palette:
    primary: str          # 헤더, 표 헤더 배경, 섹션 제목
    on_primary: str       # primary 위 텍스트 (흰색 계열)
    secondary: str        # 하이라이트 박스, 보조 영역
    accent: str           # 콜아웃, 경고
    surface: str          # 배경
    on_surface: str       # 본문 텍스트
    on_surface_var: str   # 메타데이터, 캡션
    surface_low: str      # 줄무늬 행
    error: str = '#9f403d'

@dataclass(frozen=True)
class FontSet:
    heading_hangul: str = '함초롬돋움'
    heading_latin: str = '함초롬돋움'
    body_hangul: str = '함초롬돋움'
    body_latin: str = '함초롬돋움'
    caption_hangul: str = '함초롬돋움'
    caption_latin: str = '함초롬돋움'

@dataclass(frozen=True)
class SizeSet:
    """Font sizes in pt."""
    h1: int = 24
    h2: int = 18
    h3: int = 16
    h4: int = 14
    body: int = 11
    caption: int = 10

@dataclass(frozen=True)
class Margins:
    """Page margins in HWPX units (1mm ~ 283)."""
    left: int = 8504
    right: int = 8504
    top: int = 5668
    bottom: int = 4252
    header: int = 4252
    footer: int = 4252

@dataclass(frozen=True)
class Theme:
    name: str
    palette: Palette
    fonts: FontSet = field(default_factory=FontSet)
    sizes: SizeSet = field(default_factory=SizeSet)
    margins: Margins = field(default_factory=Margins)
```

### Pattern 2: TABLE_PRESETS Derived from Theme
**What:** TABLE_PRESETS becomes a function, not a module-level dict, deriving colors from the active theme's palette.
**When to use:** In `HwpxBuilder.add_table()` when `use_preset=True`.
**Example:**
```python
def _make_table_presets(palette: Palette) -> dict:
    return {
        'corporate': {
            'header_bg': palette.primary,
            'header_text': palette.on_primary,
            'cell_margin': (283, 283, 200, 200),
            'header_height': 2400,
            'row_height': 2000,
            'header_align': 'CENTER',
            'data_align': 'CENTER',
            'stripe_color': palette.surface_low,
        },
        'government': {
            'header_bg': palette.primary,
            'header_text': palette.on_primary,
            'cell_margin': (425, 425, 283, 283),
            # ...same pattern...
        },
        'academic': {
            'header_bg': '',
            'header_text': '',
            # ...no colors...
        },
        'default': {
            'header_bg': palette.primary,
            'header_text': palette.on_primary,
            # ...
        },
    }
```

### Pattern 3: Font Registration at Document Creation
**What:** Register all theme fonts in `BlankFileMaker` instead of only 함초롬돋움/함초롬바탕.
**When to use:** During `create_document()`, before any paragraph/heading is added.
**Example:**
```python
# In blank_file_maker.py, replace _add_font_pair with:
def _add_theme_fonts(fontface, font_set: FontSet) -> None:
    unique_fonts = []
    seen = set()
    for font_name in [
        font_set.heading_hangul, font_set.heading_latin,
        font_set.body_hangul, font_set.body_latin,
        font_set.caption_hangul, font_set.caption_latin,
    ]:
        if font_name not in seen:
            seen.add(font_name)
            unique_fonts.append(font_name)
    
    for i, font_name in enumerate(unique_fonts):
        f = fontface.add_new_font()
        f.id = str(i)
        f.face = font_name
        f.type = FontType.TTF
        f.isEmbedded = False
```

### Pattern 4: Heading Styles from Theme
**What:** `_HEADING_STYLES` becomes a method that reads from the active theme's SizeSet.
**When to use:** In `HwpxBuilder.save()` when replaying heading actions.
**Example:**
```python
# In HwpxBuilder.save(), replace direct _HEADING_STYLES access:
def _heading_height(self, level: int) -> int:
    sizes = self._theme.sizes
    return {1: sizes.h1, 2: sizes.h2, 3: sizes.h3, 4: sizes.h4}.get(level, 12) * 100
```

### Anti-Patterns to Avoid
- **Modifying global DS/TABLE_PRESETS at runtime:** These are module-level dicts imported by other code. Making them mutable per-instance would cause cross-contamination between builders. Instead, derive per-instance presets from the theme.
- **Breaking `__init__.py` exports:** `DS` and `TABLE_PRESETS` are public API (exported in `__init__.py`). Keep them as module-level constants representing the default theme, even though internally the builder uses theme-derived values.
- **Using `_build_header_legacy()` as a reference:** This is dead code (confirmed in CONCERNS.md). The real font registration path is `BlankFileMaker` → object model → `HWPXWriter`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Font registration | Manual XML string building for fontfaces | `style_manager._ensure_font_registered()` | Already handles all 7 language slots, ID management, dedup |
| charPr creation | Manually building charPr XML | `style_manager.ensure_char_style(font_name=, height=, text_color=)` | Handles matching, cloning, bold/italic/underline, fontRef |
| paraPr creation | Manual alignment/spacing XML | `style_manager.ensure_para_style(align=, line_spacing_value=)` | Handles all paragraph properties, idempotent |
| Color validation | Custom hex color parser | None needed (pass-through) | HWPX accepts standard #RRGGBB strings directly |

**Key insight:** The `style_manager.py` already solves the hard problems (font registration, style dedup, ID management). The theme system is an orchestration layer on top, not a replacement.

## Common Pitfalls

### Pitfall 1: fontRef ID Mismatch
**What goes wrong:** charPr references font ID "2" but only fonts 0 and 1 exist in fontfaces. Document renders with fallback font or crashes.
**Why it happens:** Fonts registered in `BlankFileMaker` have IDs 0,1. If `ensure_char_style(font_name=X)` creates ID 2 but only in HANGUL fontface, other language slots are missing.
**How to avoid:** `_ensure_font_registered()` already registers in ALL language fontfaces. Use it exclusively. Never manually set fontRef IDs.
**Warning signs:** Text renders in wrong font in Whale/한컴 오피스.

### Pitfall 2: Breaking Backward Compatibility
**What goes wrong:** Existing code using `HwpxBuilder()` (no theme argument) produces different output.
**Why it happens:** Default palette colors differ from current DS dict values.
**How to avoid:** `theme='default'` must produce EXACTLY the same DS dict values: `primary='#395da2'`, fonts=함초롬돋움, sizes=24/18/16/14pt headings, same margins. Use the current DS dict values as the `default` theme definition. Test by comparing output of `HwpxBuilder()` before and after.
**Warning signs:** `test_hwpx_builder.py` assertions on `#395da2` fail.

### Pitfall 3: Module-Level DS/TABLE_PRESETS Mutation
**What goes wrong:** Setting `DS['primary'] = theme.palette.primary` at module level affects all HwpxBuilder instances.
**Why it happens:** DS and TABLE_PRESETS are mutable dicts at module scope, imported by tests and __init__.py.
**How to avoid:** Keep module-level DS and TABLE_PRESETS frozen (representing default theme). Each HwpxBuilder instance creates its own derived `_table_presets` dict from the theme. The module-level constants remain for backward compatibility with direct importers.
**Warning signs:** Tests that run in sequence produce different colors than tests run individually.

### Pitfall 4: Missing surface_low in Design Guide Palettes
**What goes wrong:** Design guide defines Primary/Secondary/Accent/Surface but NOT surface_low, on_primary, on_surface, on_surface_var. TABLE_PRESETS need these for stripe_color, header text, body text.
**Why it happens:** Design guide palettes are minimal (4 colors each). Full theme needs ~10 color slots.
**How to avoid:** Derive missing colors algorithmically or define them manually for each theme. For example: `surface_low` = lighter shade of surface, `on_primary` = white or near-white (determined by primary darkness), `on_surface` = dark gray `#2b3437`, `on_surface_var` = medium gray `#586064`.
**Warning signs:** Some themes have missing/None color values causing empty strings in XML attributes.

### Pitfall 5: header/footer SecPr Order Bug
**What goes wrong:** Refactoring save() to thread theme through disrupts the deferred action ordering for header/footer.
**Why it happens:** The deferred ordering (`normal_actions + deferred_actions` in `save()` lines 491-494) is a critical invariant for Whale rendering. Any refactor that changes action replay order breaks this.
**How to avoid:** Do not change the deferred action separation logic. Theme threading should only affect how each action produces its charPr/paraPr/fontRef, not the order of actions.
**Warning signs:** Documents with header/footer crash in Whale or show corrupted layout.

## Code Examples

### Current DS Dict (default theme palette source of truth)
```python
# Source: pyhwpxlib/builder.py:44-57
DS = {
    'primary': '#395da2',
    'primary_dim': '#2b5195',
    'on_primary': '#f7f7ff',
    'on_surface': '#2b3437',
    'on_surface_var': '#586064',
    'surface': '#f8f9fa',
    'surface_low': '#f1f4f6',
    'surface_high': '#e3e9ec',
    'primary_container': '#d8e2ff',
    'outline_var': '#abb3b7',
    'error': '#9f403d',
    'tertiary_container': '#e2dbfd',
}
```

### 10 Design Guide Palettes (need expansion to full Palette)
```python
# Source: skill/references/design_guide.md — 10 palettes
# Each has 4 base colors; need to expand to full Palette with on_primary, on_surface, etc.
PALETTE_BASES = {
    'administrative_slate': ('#395da2', '#cbe7f5', '#9f403d', '#f8f9fa'),
    'forest':               ('#2C5F2D', '#97BC62', '#F5F5F5', '#F9FBF7'),
    'warm_executive':       ('#B85042', '#E7E8D1', '#A7BEAE', '#FBF9F7'),
    'ocean_analytics':      ('#065A82', '#1C7293', '#21295C', '#F5F9FB'),
    'coral_energy':         ('#F96167', '#F9E795', '#2F3C7E', '#FFFDF7'),
    'charcoal_minimal':     ('#36454F', '#F2F2F2', '#212121', '#FFFFFF'),
    'teal_trust':           ('#028090', '#00A896', '#02C39A', '#F5FBFA'),
    'berry_cream':          ('#6D2E46', '#A26769', '#ECE2D0', '#FDF9F5'),
    'sage_calm':            ('#84B59F', '#69A297', '#50808E', '#F7FAF9'),
    'cherry_bold':          ('#990011', '#FCF6F5', '#2F3C7E', '#FFFCFC'),
}
```

### Font Registration (existing working code)
```python
# Source: pyhwpxlib/style_manager.py:207-245
def _ensure_font_registered(hwpx_file, font_name: str) -> str:
    # Checks HANGUL fontface for existing font
    # If not found, adds to ALL language fontfaces with same ID
    # Returns font ID as string
```

### charPr with Custom Font (existing working code)
```python
# Source: pyhwpxlib/style_manager.py:79-171
char_pr_id = ensure_char_style(
    doc,
    bold=True,
    height=2400,         # 24pt
    text_color='#2C5F2D',
    font_name='맑은 고딕',  # registers font if needed, sets fontRef
)
```

### Per-Language FontRef (for hangul/latin split)
```python
# Source: pyhwpxlib/objects/header/references/char_pr.py:58-83
# ValuesByLanguage supports individual language setting:
fontRef.hangul = "0"  # 나눔명조
fontRef.latin = "2"   # Arial
# Or set all at once:
fontRef.set_all("0")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single hardcoded DS dict | Theme dataclass (this phase) | Phase 1 | All documents can have unique palettes |
| 함초롬돋움 only (id=0) | Multiple fonts via FontSet | Phase 1 | 제목/본문/캡션 각기 다른 폰트 |
| Fixed _HEADING_STYLES | SizeSet per theme | Phase 1 | 테마별 heading 크기 조절 가능 |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None detected (uses defaults) |
| Quick run command | `python -m pytest tests/test_hwpx_builder.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TS-1-a | `HwpxBuilder(theme='forest')` creates doc with forest palette colors | unit | `pytest tests/test_themes.py::test_theme_forest_colors -x` | Wave 0 |
| TS-1-b | `theme='default'` produces identical output to current no-theme behavior | unit | `pytest tests/test_themes.py::test_default_theme_backward_compat -x` | Wave 0 |
| TS-1-c | TABLE_PRESETS derive from active theme palette | unit | `pytest tests/test_themes.py::test_table_presets_from_theme -x` | Wave 0 |
| TS-1-d | All 10 built-in themes generate valid HWPX files | integration | `pytest tests/test_themes.py::test_all_themes_generate_valid_hwpx -x` | Wave 0 |
| TS-2-a | Multiple fonts registered in header.xml fontfaces | unit | `pytest tests/test_themes.py::test_multi_font_registration -x` | Wave 0 |
| TS-2-b | Heading uses heading font, body uses body font | unit | `pytest tests/test_themes.py::test_heading_body_font_separation -x` | Wave 0 |
| TS-2-c | 한글/라틴 폰트 분리 (e.g., 나눔명조 + Arial) | unit | `pytest tests/test_themes.py::test_hangul_latin_font_split -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_themes.py tests/test_hwpx_builder.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_themes.py` -- covers all TS-1 and TS-2 requirements
- [ ] Fix import path in `tests/test_hwpx_builder.py` (line 8: imports from `scripts.create` instead of `pyhwpxlib.builder`)

## Open Questions

1. **Font availability on target systems**
   - What we know: 함초롬돋움/함초롬바탕 are bundled with Hancom Office. 맑은 고딕 is Windows-only. Noto Sans KR is cross-platform.
   - What's unclear: Which fonts are available on the Oracle Cloud MCP server. HWPX renderers may use fallback fonts if specified font is missing.
   - Recommendation: Default theme uses 함초롬돋움 (safe). Other themes can use 맑은 고딕/나눔명조 etc. Document that font availability affects rendering. No runtime font-existence check needed (HWPX just stores the name).

2. **Palette expansion from 4 to 10+ colors**
   - What we know: Design guide provides Primary/Secondary/Accent/Surface (4 colors) per palette. DS dict has 12 color slots.
   - What's unclear: Optimal derivation of on_primary, surface_low, on_surface, etc. from 4 base colors.
   - Recommendation: Manually define all 10+ color slots for each theme. Use the Administrative Slate palette as the reference pattern. For dark primaries: on_primary = near-white. For light primaries: on_primary = dark color. surface_low = slight tint of surface.

3. **presets.py vs themes.py overlap**
   - What we know: `presets.py` has PRESETS dict with page/title/heading/body/colors per document type. `themes.py` will have Theme dataclass with similar scope.
   - What's unclear: Should PRESETS be merged into themes, or remain separate?
   - Recommendation: Keep them separate for now. `presets.py` defines document structure (numbering, footer_text, etc.). `themes.py` defines visual appearance (colors, fonts, sizes). In Phase 4, consider merging if redundancy is problematic.

## Sources

### Primary (HIGH confidence)
- `pyhwpxlib/builder.py` — DS dict (lines 44-57), TABLE_PRESETS (lines 59-99), save() (lines 475-594)
- `pyhwpxlib/style_manager.py` — ensure_char_style (lines 79-171), _ensure_font_registered (lines 207-245)
- `pyhwpxlib/tools/blank_file_maker.py` — _add_font_pair (lines 257-290), fontface registration
- `pyhwpxlib/objects/header/references/char_pr.py` — ValuesByLanguage.set() (lines 58-83)
- `pyhwpxlib/api.py` — _HEADING_STYLES (lines 975-980), add_heading (lines 983-1005)
- `skill/references/design_guide.md` — 10 palettes, typography guide, font recommendations
- `pyhwpxlib/presets.py` — PRESETS dict, color definitions per document type
- `.planning/codebase/CONCERNS.md` — tech debt items for DS/fonts/heading, dead code identification
- `tests/test_hwpx_builder.py` — existing tests with hardcoded color assertions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all patterns exist in codebase
- Architecture: HIGH — clear dataclass pattern, well-understood injection points
- Pitfalls: HIGH — identified from actual code review and CONCERNS.md

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable domain, internal refactoring)
