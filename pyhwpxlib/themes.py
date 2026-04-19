"""Theme system for pyhwpxlib — color palettes, fonts, sizes, margins.

Provides frozen dataclasses (Theme, Palette, FontSet, SizeSet, Margins)
and 10 built-in themes. The 'default' theme produces values identical to
the current DS dict in builder.py for backward compatibility.

Usage::

    from pyhwpxlib.themes import BUILTIN_THEMES, _make_table_presets

    theme = BUILTIN_THEMES['forest']
    presets = _make_table_presets(theme.palette)
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ======================================================================
# Dataclass hierarchy
# ======================================================================

@dataclass(frozen=True)
class Palette:
    """Color palette for a theme. All values are hex color strings (#RRGGBB)."""
    primary: str
    on_primary: str
    secondary: str
    accent: str
    surface: str
    on_surface: str
    on_surface_var: str
    surface_low: str
    surface_high: str
    primary_container: str
    outline_var: str
    error: str
    tertiary_container: str
    primary_dim: str


@dataclass(frozen=True)
class FontSet:
    """Font names for heading, body, and caption text.

    Default is '맑은 고딕' (Malgun Gothic) — 2022년 6월 이후 공문서 표준.
    Fallback: 번들된 NanumGothic (vendor/).
    """
    heading_hangul: str = '맑은 고딕'
    heading_latin: str = '맑은 고딕'
    body_hangul: str = '맑은 고딕'
    body_latin: str = '맑은 고딕'
    caption_hangul: str = '맑은 고딕'
    caption_latin: str = '맑은 고딕'


@dataclass(frozen=True)
class SizeSet:
    """Font sizes in pt (한국 공문서 표준 기준).

    공문서: 제목 20pt, 작은제목 17pt, 내부제목 15pt, 본문 15pt, 표 11pt.
    """
    h1: int = 20
    h2: int = 17
    h3: int = 15
    h4: int = 15
    body: int = 15
    caption: int = 11


@dataclass(frozen=True)
class Margins:
    """Page margins in HWPX units (1mm ~ 283).

    공문서 표준: 위 15mm, 아래 15mm, 좌 20mm, 우 20mm, 머리말 10mm, 꼬리말 10mm.
    """
    left: int = 5660     # 20mm
    right: int = 5660    # 20mm
    top: int = 4245      # 15mm
    bottom: int = 4245   # 15mm
    header: int = 2830   # 10mm
    footer: int = 2830   # 10mm


@dataclass(frozen=True)
class Density:
    """Document density — line spacing, alignment, cell padding.

    공문서 표준: 줄간격 160%, 자간 -5~-10%, 정렬 JUSTIFY.
    """
    line_spacing: int = 160
    align: str = 'JUSTIFY'
    cell_padding: int = 283
    char_spacing: int = -5  # 자간 (%, 음수=촘촘)


@dataclass(frozen=True)
class Theme:
    """Complete visual theme for HWPX document generation."""
    name: str
    palette: Palette
    fonts: FontSet = field(default_factory=FontSet)
    sizes: SizeSet = field(default_factory=SizeSet)
    margins: Margins = field(default_factory=Margins)
    density: Density = field(default_factory=Density)


# ======================================================================
# _make_table_presets
# ======================================================================

def _make_table_presets(palette: Palette) -> dict:
    """Derive TABLE_PRESETS from a palette.

    Returns a dict with keys: corporate, government, academic, default.
    Each value has: header_bg, header_text, cell_margin, header_height,
    row_height, header_align, data_align, stripe_color.
    """
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
            'header_height': 2400,
            'row_height': 2000,
            'header_align': 'CENTER',
            'data_align': 'CENTER',
            'stripe_color': palette.surface_low,
        },
        'academic': {
            'header_bg': '',
            'header_text': '',
            'cell_margin': (200, 200, 141, 141),
            'header_height': 2000,
            'row_height': 1800,
            'header_align': 'CENTER',
            'data_align': 'CENTER',
            'stripe_color': '',
        },
        'default': {
            'header_bg': palette.primary,
            'header_text': palette.on_primary,
            'cell_margin': (283, 283, 200, 200),
            'header_height': 2400,
            'row_height': 2000,
            'header_align': 'CENTER',
            'data_align': 'CENTER',
            'stripe_color': palette.surface_low,
        },
    }


# ======================================================================
# Built-in themes (10 themes)
# ======================================================================

# 'default' = Administrative Slate — MUST match DS dict in builder.py exactly
_DEFAULT_PALETTE = Palette(
    primary='#395da2',
    on_primary='#f7f7ff',
    secondary='#cbe7f5',
    accent='#9f403d',
    surface='#f8f9fa',
    on_surface='#2b3437',
    on_surface_var='#586064',
    surface_low='#f1f4f6',
    surface_high='#e3e9ec',
    primary_container='#d8e2ff',
    outline_var='#abb3b7',
    error='#9f403d',
    tertiary_container='#e2dbfd',
    primary_dim='#2b5195',
)

_FOREST_PALETTE = Palette(
    primary='#2C5F2D',
    on_primary='#f7f7ff',
    secondary='#97BC62',
    accent='#F5F5F5',
    surface='#F9FBF7',
    on_surface='#2b3437',
    on_surface_var='#586064',
    surface_low='#f3f6f0',
    surface_high='#e5eade',
    primary_container='#c8e6c9',
    outline_var='#abb3b7',
    error='#9f403d',
    tertiary_container='#e8e8e8',
    primary_dim='#1e4d1f',
)

_WARM_EXECUTIVE_PALETTE = Palette(
    primary='#B85042',
    on_primary='#f7f7ff',
    secondary='#E7E8D1',
    accent='#A7BEAE',
    surface='#FBF9F7',
    on_surface='#2b3437',
    on_surface_var='#586064',
    surface_low='#f5f2ee',
    surface_high='#ebe5df',
    primary_container='#f5d0cb',
    outline_var='#abb3b7',
    error='#9f403d',
    tertiary_container='#d6e5dc',
    primary_dim='#a03e30',
)

_OCEAN_ANALYTICS_PALETTE = Palette(
    primary='#065A82',
    on_primary='#f7f7ff',
    secondary='#1C7293',
    accent='#21295C',
    surface='#F5F9FB',
    on_surface='#2b3437',
    on_surface_var='#586064',
    surface_low='#edf4f7',
    surface_high='#dde9ef',
    primary_container='#b3d9ec',
    outline_var='#abb3b7',
    error='#9f403d',
    tertiary_container='#c9cce0',
    primary_dim='#044a6e',
)

_CORAL_ENERGY_PALETTE = Palette(
    primary='#F96167',
    on_primary='#2b3437',
    secondary='#F9E795',
    accent='#2F3C7E',
    surface='#FFFDF7',
    on_surface='#2b3437',
    on_surface_var='#586064',
    surface_low='#faf8f0',
    surface_high='#f2ede2',
    primary_container='#fdc8ca',
    outline_var='#abb3b7',
    error='#9f403d',
    tertiary_container='#c5cae8',
    primary_dim='#e04e54',
)

_CHARCOAL_MINIMAL_PALETTE = Palette(
    primary='#36454F',
    on_primary='#f7f7ff',
    secondary='#F2F2F2',
    accent='#212121',
    surface='#FFFFFF',
    on_surface='#2b3437',
    on_surface_var='#586064',
    surface_low='#f7f7f7',
    surface_high='#ebebeb',
    primary_container='#c4cdd3',
    outline_var='#abb3b7',
    error='#9f403d',
    tertiary_container='#e0e0e0',
    primary_dim='#2a3940',
)

_TEAL_TRUST_PALETTE = Palette(
    primary='#028090',
    on_primary='#f7f7ff',
    secondary='#00A896',
    accent='#02C39A',
    surface='#F5FBFA',
    on_surface='#2b3437',
    on_surface_var='#586064',
    surface_low='#eef7f5',
    surface_high='#ddf0ec',
    primary_container='#b0e0e6',
    outline_var='#abb3b7',
    error='#9f403d',
    tertiary_container='#c2f0e4',
    primary_dim='#016a78',
)

_BERRY_CREAM_PALETTE = Palette(
    primary='#6D2E46',
    on_primary='#f7f7ff',
    secondary='#A26769',
    accent='#ECE2D0',
    surface='#FDF9F5',
    on_surface='#2b3437',
    on_surface_var='#586064',
    surface_low='#f7f2ec',
    surface_high='#ede4da',
    primary_container='#e0b8c6',
    outline_var='#abb3b7',
    error='#9f403d',
    tertiary_container='#f0e8d8',
    primary_dim='#5a2239',
)

_SAGE_CALM_PALETTE = Palette(
    primary='#84B59F',
    on_primary='#2b3437',
    secondary='#69A297',
    accent='#50808E',
    surface='#F7FAF9',
    on_surface='#2b3437',
    on_surface_var='#586064',
    surface_low='#f0f5f3',
    surface_high='#e2eae6',
    primary_container='#cce4d9',
    outline_var='#abb3b7',
    error='#9f403d',
    tertiary_container='#c8d9de',
    primary_dim='#6da389',
)

_CHERRY_BOLD_PALETTE = Palette(
    primary='#990011',
    on_primary='#f7f7ff',
    secondary='#FCF6F5',
    accent='#2F3C7E',
    surface='#FFFCFC',
    on_surface='#2b3437',
    on_surface_var='#586064',
    surface_low='#f9f5f5',
    surface_high='#f0e8e8',
    primary_container='#f5b3b9',
    outline_var='#abb3b7',
    error='#9f403d',
    tertiary_container='#c5cae8',
    primary_dim='#800010',
)


BUILTIN_THEMES: dict[str, Theme] = {
    'default': Theme(name='default', palette=_DEFAULT_PALETTE),
    'forest': Theme(name='forest', palette=_FOREST_PALETTE),
    'warm_executive': Theme(name='warm_executive', palette=_WARM_EXECUTIVE_PALETTE),
    'ocean_analytics': Theme(name='ocean_analytics', palette=_OCEAN_ANALYTICS_PALETTE),
    'coral_energy': Theme(name='coral_energy', palette=_CORAL_ENERGY_PALETTE),
    'charcoal_minimal': Theme(name='charcoal_minimal', palette=_CHARCOAL_MINIMAL_PALETTE),
    'teal_trust': Theme(name='teal_trust', palette=_TEAL_TRUST_PALETTE),
    'berry_cream': Theme(name='berry_cream', palette=_BERRY_CREAM_PALETTE),
    'sage_calm': Theme(name='sage_calm', palette=_SAGE_CALM_PALETTE),
    'cherry_bold': Theme(name='cherry_bold', palette=_CHERRY_BOLD_PALETTE),
}


# ======================================================================
# Theme extraction from HWPX files
# ======================================================================

import json
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

_HEAD_NS = 'http://www.hancom.co.kr/hwpml/2011/head'
_PARA_NS = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
_SEC_NS = 'http://www.hancom.co.kr/hwpml/2011/section'

_THEMES_DIR = Path.home() / '.pyhwpxlib' / 'themes'


def _lighten(hex_color: str, factor: float = 0.85) -> str:
    """Lighten a hex color by mixing with white."""
    c = hex_color.lstrip('#')
    r, g, b = int(c[:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f'#{r:02x}{g:02x}{b:02x}'


def _darken(hex_color: str, factor: float = 0.2) -> str:
    """Darken a hex color."""
    c = hex_color.lstrip('#')
    r, g, b = int(c[:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return f'#{r:02x}{g:02x}{b:02x}'


def extract_theme(hwpx_path: str | Path, name: str | None = None) -> Theme:
    """Extract a Theme from an existing HWPX file.

    Analyzes header.xml (charPr, fontface, borderFill) and section0.xml
    (secPr/pageMg) to infer palette, fonts, sizes, and margins.

    Parameters
    ----------
    hwpx_path : path to .hwpx file
    name : optional theme name (defaults to filename stem)

    Returns
    -------
    Theme dataclass instance
    """
    hwpx_path = Path(hwpx_path)
    if name is None:
        name = hwpx_path.stem

    with zipfile.ZipFile(hwpx_path) as z:
        header_xml = z.read('Contents/header.xml').decode('utf-8')
        try:
            sec_xml = z.read('Contents/section0.xml').decode('utf-8')
        except KeyError:
            sec_xml = None

    root = ET.fromstring(header_xml)

    # --- Fonts ---
    hangul_fonts = []
    for ff in root.iter(f'{{{_HEAD_NS}}}fontface'):
        if ff.get('lang') == 'HANGUL':
            for font_el in ff.iter(f'{{{_HEAD_NS}}}font'):
                face = font_el.get('face')
                if face:
                    hangul_fonts.append(face)
    primary_font = hangul_fonts[0] if hangul_fonts else '나눔고딕'
    fonts = FontSet(
        heading_hangul=primary_font, heading_latin=primary_font,
        body_hangul=primary_font, body_latin=primary_font,
        caption_hangul=primary_font, caption_latin=primary_font,
    )

    # --- Sizes (from charPr height, in hwpx units: 100 = 1pt) ---
    heights = []
    for cp in root.iter(f'{{{_HEAD_NS}}}charPr'):
        h = int(cp.get('height', '0'))
        if h > 0:
            heights.append(h)
    if heights:
        sorted_h = sorted(set(heights), reverse=True)
        h1 = sorted_h[0] // 100 if len(sorted_h) > 0 else 24
        h2 = sorted_h[1] // 100 if len(sorted_h) > 1 else 18
        h3 = sorted_h[2] // 100 if len(sorted_h) > 2 else 16
        h4 = sorted_h[3] // 100 if len(sorted_h) > 3 else 14
        # Body = most common height
        body_h = Counter(heights).most_common(1)[0][0] // 100
        sizes = SizeSet(h1=h1, h2=h2, h3=h3, h4=h4, body=body_h, caption=max(body_h - 2, 8))
    else:
        sizes = SizeSet()

    # --- Colors (from charPr textColor + borderFill faceColor) ---
    text_colors = []
    for cp in root.iter(f'{{{_HEAD_NS}}}charPr'):
        c = cp.get('textColor', '#000000')
        if c not in ('#000000', 'none', '#FFFFFF', '#ffffff'):
            text_colors.append(c.upper())

    fill_colors = []
    for bf in root.iter(f'{{{_HEAD_NS}}}borderFill'):
        for wb in bf.iter():
            tag = wb.tag.split('}')[-1] if '}' in wb.tag else wb.tag
            if tag == 'winBrush':
                fc = wb.get('faceColor', 'none')
                if fc not in ('none', '#FFFFFF', '#ffffff', '#000000'):
                    fill_colors.append(fc.upper())

    # Primary = most common non-black text color, or darkest fill color
    if text_colors:
        primary = Counter(text_colors).most_common(1)[0][0]
    elif fill_colors:
        # Pick the darkest fill as primary
        def _brightness(c):
            c = c.lstrip('#')
            return int(c[:2], 16) + int(c[2:4], 16) + int(c[4:6], 16)
        primary = min(fill_colors, key=_brightness)
    else:
        primary = '#395da2'

    # Table header = darkest fill, surface_low = lightest fill
    if fill_colors:
        def _brightness(c):
            c = c.lstrip('#')
            return int(c[:2], 16) + int(c[2:4], 16) + int(c[4:6], 16)
        sorted_fills = sorted(set(fill_colors), key=_brightness)
        table_header = sorted_fills[0]  # darkest
        surface_low = sorted_fills[-1]  # lightest
    else:
        table_header = primary
        surface_low = '#f1f4f6'

    palette = Palette(
        primary=primary,
        on_primary='#f7f7ff',
        secondary=_lighten(primary, 0.6),
        accent=table_header if table_header != primary else _darken(primary, 0.3),
        surface='#f8f9fa',
        on_surface='#2b3437',
        on_surface_var='#586064',
        surface_low=surface_low,
        surface_high=_lighten(primary, 0.75),
        primary_container=_lighten(primary, 0.8),
        outline_var='#abb3b7',
        error='#9f403d',
        tertiary_container=_lighten(table_header, 0.8) if table_header != primary else '#e2dbfd',
        primary_dim=_darken(primary, 0.2),
    )

    # --- Margins (from secPr/pageMg) ---
    margins = Margins()
    if sec_xml:
        sec_root = ET.fromstring(sec_xml)
        for el in sec_root.iter():
            tag = el.tag.split('}')[-1] if '}' in el.tag else el.tag
            if tag == 'pageMg':
                try:
                    margins = Margins(
                        left=int(el.get('left', margins.left)),
                        right=int(el.get('right', margins.right)),
                        top=int(el.get('top', margins.top)),
                        bottom=int(el.get('bottom', margins.bottom)),
                        header=int(el.get('header', margins.header)),
                        footer=int(el.get('footer', margins.footer)),
                    )
                except (ValueError, TypeError):
                    pass
                break

    # --- Density (line spacing, alignment, cell padding) ---
    line_spacings = []
    aligns = []
    for pp in root.iter(f'{{{_HEAD_NS}}}paraPr'):
        for child in pp:
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            if tag == 'lineSpacing':
                v = child.get('value')
                if v and child.get('type') == 'PERCENT':
                    line_spacings.append(int(v))
            if tag == 'align':
                h = child.get('horizontal')
                if h:
                    aligns.append(h)

    cell_paddings = []
    if sec_xml:
        if not sec_root:
            sec_root = ET.fromstring(sec_xml)
        for el in sec_root.iter():
            tag = el.tag.split('}')[-1] if '}' in el.tag else el.tag
            if tag == 'cellMargin':
                vals = [int(el.get(k, '0')) for k in ('left', 'right', 'top', 'bottom')]
                if any(v > 0 for v in vals):
                    cell_paddings.append(sum(vals) // 4)  # average

    density = Density(
        line_spacing=Counter(line_spacings).most_common(1)[0][0] if line_spacings else 160,
        align=Counter(aligns).most_common(1)[0][0] if aligns else 'JUSTIFY',
        cell_padding=Counter(cell_paddings).most_common(1)[0][0] if cell_paddings else 283,
    )

    return Theme(name=name, palette=palette, fonts=fonts, sizes=sizes, margins=margins, density=density)


def save_theme(theme: Theme, path: str | Path | None = None) -> Path:
    """Save a Theme to JSON file.

    Parameters
    ----------
    theme : Theme instance
    path : file path. If None, saves to ~/.pyhwpxlib/themes/{name}.json

    Returns
    -------
    Path to saved file
    """
    if path is None:
        _THEMES_DIR.mkdir(parents=True, exist_ok=True)
        path = _THEMES_DIR / f'{theme.name}.json'
    else:
        path = Path(path)

    data = {
        'name': theme.name,
        'palette': {f.name: getattr(theme.palette, f.name) for f in theme.palette.__dataclass_fields__.values()},
        'fonts': {f.name: getattr(theme.fonts, f.name) for f in theme.fonts.__dataclass_fields__.values()},
        'sizes': {f.name: getattr(theme.sizes, f.name) for f in theme.sizes.__dataclass_fields__.values()},
        'margins': {f.name: getattr(theme.margins, f.name) for f in theme.margins.__dataclass_fields__.values()},
        'density': {f.name: getattr(theme.density, f.name) for f in theme.density.__dataclass_fields__.values()},
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def load_theme(path: str | Path) -> Theme:
    """Load a Theme from JSON file.

    Parameters
    ----------
    path : file path, or theme name (looked up in ~/.pyhwpxlib/themes/)

    Returns
    -------
    Theme instance
    """
    path = Path(path)
    if not path.exists() and not path.suffix:
        # Try themes directory
        path = _THEMES_DIR / f'{path}.json'
    if not path.exists():
        raise FileNotFoundError(f'Theme file not found: {path}')

    data = json.loads(path.read_text(encoding='utf-8'))
    return Theme(
        name=data['name'],
        palette=Palette(**data['palette']),
        fonts=FontSet(**data['fonts']),
        sizes=SizeSet(**data['sizes']),
        margins=Margins(**data['margins']),
        density=Density(**data['density']) if 'density' in data else Density(),
    )


def resolve_theme(theme: str | Theme | None) -> Theme:
    """Resolve a theme argument to a Theme instance.

    Accepts:
    - None / 'default' → built-in default
    - Built-in name ('forest', 'ocean_analytics', ...)
    - 'custom/{name}' → load from ~/.pyhwpxlib/themes/{name}.json
    - Path to .json file
    - Theme instance (pass-through)
    """
    if theme is None or theme == 'default':
        return BUILTIN_THEMES['default']
    if isinstance(theme, Theme):
        return theme
    if theme in BUILTIN_THEMES:
        return BUILTIN_THEMES[theme]
    # custom/ prefix
    if isinstance(theme, str) and theme.startswith('custom/'):
        name = theme[7:]  # strip 'custom/'
        return load_theme(name)
    # Try as file path
    p = Path(theme)
    if p.exists() and p.suffix == '.json':
        return load_theme(p)
    raise ValueError(f"Unknown theme: {theme!r}. Use a built-in name, 'custom/name', or a .json path.")
