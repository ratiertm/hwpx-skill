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
    """Font names for heading, body, and caption text."""
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
    """Complete visual theme for HWPX document generation."""
    name: str
    palette: Palette
    fonts: FontSet = field(default_factory=FontSet)
    sizes: SizeSet = field(default_factory=SizeSet)
    margins: Margins = field(default_factory=Margins)


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
