"""Tests for pyhwpxlib.themes — Theme dataclass hierarchy and built-in themes.

Covers TS-1 (theme system core) and TS-2 (font system) requirements.
"""
import pytest


# ======================================================================
# TS-1: Theme System Core Tests
# ======================================================================

class TestDefaultPalette:
    """Default theme palette must exactly match the current DS dict values."""

    def test_default_palette_matches_ds(self):
        from pyhwpxlib.themes import BUILTIN_THEMES

        p = BUILTIN_THEMES['default'].palette
        assert p.primary == '#395da2'
        assert p.primary_dim == '#2b5195'
        assert p.on_primary == '#f7f7ff'
        assert p.on_surface == '#2b3437'
        assert p.on_surface_var == '#586064'
        assert p.surface == '#f8f9fa'
        assert p.surface_low == '#f1f4f6'
        assert p.surface_high == '#e3e9ec'
        assert p.primary_container == '#d8e2ff'
        assert p.outline_var == '#abb3b7'
        assert p.error == '#9f403d'
        assert p.tertiary_container == '#e2dbfd'


class TestAllThemesExist:
    """BUILTIN_THEMES must have exactly 10 entries with specific keys."""

    EXPECTED_KEYS = {
        'default', 'forest', 'warm_executive', 'ocean_analytics',
        'coral_energy', 'charcoal_minimal', 'teal_trust',
        'berry_cream', 'sage_calm', 'cherry_bold',
    }

    def test_all_themes_exist(self):
        from pyhwpxlib.themes import BUILTIN_THEMES

        assert set(BUILTIN_THEMES.keys()) == self.EXPECTED_KEYS
        assert len(BUILTIN_THEMES) == 10


class TestThemeIsFrozen:
    """Theme and its sub-structures must be frozen (immutable)."""

    def test_theme_is_frozen(self):
        from pyhwpxlib.themes import BUILTIN_THEMES

        theme = BUILTIN_THEMES['default']
        with pytest.raises(AttributeError):
            theme.palette = None  # type: ignore[misc]

    def test_palette_is_frozen(self):
        from pyhwpxlib.themes import BUILTIN_THEMES

        palette = BUILTIN_THEMES['default'].palette
        with pytest.raises(AttributeError):
            palette.primary = '#000000'  # type: ignore[misc]


class TestPaletteNoNoneValues:
    """Every palette field in every theme must be a non-empty string starting with '#'."""

    def test_palette_no_none_values(self):
        from pyhwpxlib.themes import BUILTIN_THEMES, Palette
        import dataclasses

        palette_fields = [f.name for f in dataclasses.fields(Palette)]
        for name, theme in BUILTIN_THEMES.items():
            for field_name in palette_fields:
                val = getattr(theme.palette, field_name)
                assert isinstance(val, str), f"{name}.{field_name} is not str: {val!r}"
                assert val.startswith('#'), f"{name}.{field_name} doesn't start with '#': {val!r}"
                assert len(val) >= 4, f"{name}.{field_name} is too short: {val!r}"


class TestDefaultFontSet:
    """FontSet() defaults all fields to a consistent hangul font."""

    def test_default_font_set(self):
        from pyhwpxlib.themes import FontSet
        import dataclasses

        fs = FontSet()
        for f in dataclasses.fields(fs):
            assert getattr(fs, f.name) == '\ud568\ucd08\ub86c\ub3cb\uc6c0', \
                f"FontSet().{f.name} != '\ud568\ucd08\ub86c\ub3cb\uc6c0'"


class TestDefaultSizeSet:
    """SizeSet() has expected default font sizes."""

    def test_default_size_set(self):
        from pyhwpxlib.themes import SizeSet

        ss = SizeSet()
        assert ss.h1 == 24
        assert ss.h2 == 18
        assert ss.h3 == 16
        assert ss.h4 == 14
        assert ss.body == 11
        assert ss.caption == 10


class TestMakeTablePresets:
    """_make_table_presets must produce correct shape and values."""

    def test_make_table_presets_corporate(self):
        from pyhwpxlib.themes import BUILTIN_THEMES, _make_table_presets

        palette = BUILTIN_THEMES['default'].palette
        presets = _make_table_presets(palette)
        assert presets['corporate']['header_bg'] == '#395da2'
        assert presets['corporate']['header_text'] == '#f7f7ff'
        assert presets['corporate']['stripe_color'] == '#f1f4f6'

    def test_make_table_presets_academic(self):
        from pyhwpxlib.themes import BUILTIN_THEMES, _make_table_presets

        palette = BUILTIN_THEMES['forest'].palette
        presets = _make_table_presets(palette)
        assert presets['academic']['header_bg'] == ''
        assert presets['academic']['header_text'] == ''
        assert presets['academic']['stripe_color'] == ''

    def test_make_table_presets_shape(self):
        from pyhwpxlib.themes import BUILTIN_THEMES, _make_table_presets

        palette = BUILTIN_THEMES['default'].palette
        presets = _make_table_presets(palette)

        expected_preset_keys = {'corporate', 'government', 'academic', 'default'}
        assert set(presets.keys()) == expected_preset_keys

        expected_fields = {
            'header_bg', 'header_text', 'cell_margin', 'header_height',
            'row_height', 'header_align', 'data_align', 'stripe_color',
        }
        for preset_name, preset in presets.items():
            assert set(preset.keys()) == expected_fields, \
                f"Preset '{preset_name}' has wrong keys: {set(preset.keys())}"

    def test_make_table_presets_default_matches_builder(self):
        """_make_table_presets(default palette) must match the existing TABLE_PRESETS in builder.py."""
        from pyhwpxlib.themes import BUILTIN_THEMES, _make_table_presets
        from pyhwpxlib.builder import TABLE_PRESETS

        palette = BUILTIN_THEMES['default'].palette
        derived = _make_table_presets(palette)

        for preset_name in TABLE_PRESETS:
            for field_name in TABLE_PRESETS[preset_name]:
                assert derived[preset_name][field_name] == TABLE_PRESETS[preset_name][field_name], \
                    f"Mismatch in {preset_name}.{field_name}: " \
                    f"derived={derived[preset_name][field_name]!r} vs " \
                    f"builder={TABLE_PRESETS[preset_name][field_name]!r}"


# ======================================================================
# TS-2: Font System Tests (placeholder — implemented in Plan 02/03)
# ======================================================================

class TestFontSystemPlaceholders:
    """Placeholder tests for TS-2 requirements. Will be implemented in Plan 02/03."""

    def test_multi_font_registration(self):
        pytest.skip("Implemented in Plan 02/03")

    def test_heading_body_font_separation(self):
        pytest.skip("Implemented in Plan 02/03")

    def test_hangul_latin_font_split(self):
        pytest.skip("Implemented in Plan 02/03")


# ======================================================================
# Integration Tests (placeholder — implemented in Plan 02/03)
# ======================================================================

class TestIntegrationPlaceholders:
    """Placeholder integration tests. Will be implemented in Plan 02/03."""

    def test_theme_forest_colors(self):
        pytest.skip("Implemented in Plan 02/03")

    def test_all_themes_generate_valid_hwpx(self):
        pytest.skip("Implemented in Plan 02/03")

    def test_table_presets_from_theme(self):
        pytest.skip("Implemented in Plan 02/03")

    def test_default_theme_backward_compat(self):
        pytest.skip("Implemented in Plan 02/03")
