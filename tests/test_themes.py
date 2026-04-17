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
# TS-2: Font System Tests
# ======================================================================

class TestFontSystem:
    """Tests for TS-2: font registration, heading/body separation, hangul/latin split."""

    def test_multi_font_registration(self):
        """Multiple distinct fonts in FontSet are all registered in header.xml fontfaces."""
        import tempfile
        import zipfile
        import xml.etree.ElementTree as ET
        from pyhwpxlib.themes import Theme, Palette, FontSet, BUILTIN_THEMES
        from pyhwpxlib.builder import HwpxBuilder

        fs = FontSet(
            heading_hangul='맑은 고딕', heading_latin='맑은 고딕',
            body_hangul='함초롬돋움', body_latin='함초롬돋움',
        )
        theme = Theme(name='test_multi_font',
                       palette=BUILTIN_THEMES['forest'].palette,
                       fonts=fs)
        doc = HwpxBuilder(theme=theme)
        doc.add_heading("Test", level=1)
        doc.add_paragraph("Body text")

        with tempfile.NamedTemporaryFile(suffix='.hwpx', delete=False) as tmp:
            doc.save(tmp.name)
            with zipfile.ZipFile(tmp.name) as zf:
                header_xml = zf.read('Contents/header.xml')

        root = ET.fromstring(header_xml)
        ns = {'hh': 'http://www.hancom.co.kr/hwpml/2011/head'}
        hangul_ff = root.find('.//hh:fontface[@lang="HANGUL"]', ns)
        fonts = [f.get('face') for f in hangul_ff.findall('hh:font', ns)]
        assert '맑은 고딕' in fonts, f"Expected '맑은 고딕' in fontfaces, got {fonts}"
        assert '함초롬돋움' in fonts, f"Expected '함초롬돋움' in fontfaces, got {fonts}"

    def test_heading_body_font_separation(self):
        """Heading charPr references heading font, body uses body font (or default)."""
        import tempfile
        import zipfile
        import xml.etree.ElementTree as ET
        from pyhwpxlib.themes import Theme, FontSet, BUILTIN_THEMES
        from pyhwpxlib.builder import HwpxBuilder

        fs = FontSet(
            heading_hangul='맑은 고딕', heading_latin='맑은 고딕',
            body_hangul='함초롬돋움', body_latin='함초롬돋움',
        )
        theme = Theme(name='test_font_sep',
                       palette=BUILTIN_THEMES['forest'].palette,
                       fonts=fs)
        doc = HwpxBuilder(theme=theme)
        doc.add_heading("Heading Text", level=1)
        doc.add_paragraph("Body text", bold=True)

        with tempfile.NamedTemporaryFile(suffix='.hwpx', delete=False) as tmp:
            doc.save(tmp.name)
            with zipfile.ZipFile(tmp.name) as zf:
                header_xml = zf.read('Contents/header.xml')

        root = ET.fromstring(header_xml)
        ns = {'hh': 'http://www.hancom.co.kr/hwpml/2011/head'}

        # Find fontfaces to determine IDs
        hangul_ff = root.find('.//hh:fontface[@lang="HANGUL"]', ns)
        font_map = {}
        for f in hangul_ff.findall('hh:font', ns):
            font_map[f.get('id')] = f.get('face')

        # Heading charPr should reference the heading font
        char_prs = root.findall('.//hh:charPr', ns)
        # Find the heading charPr (height=2400, has bold)
        heading_cp = None
        for cp in char_prs:
            if cp.get('height') == '2400' and cp.find('hh:bold', ns) is not None:
                heading_cp = cp
                break
        assert heading_cp is not None, "Heading charPr not found"
        font_ref = heading_cp.find('hh:fontRef', ns)
        heading_font_id = font_ref.get('hangul')
        assert font_map.get(heading_font_id) == '맑은 고딕', \
            f"Heading font should be '맑은 고딕', got '{font_map.get(heading_font_id)}'"

    def test_hangul_latin_font_split(self):
        """FontSet with different hangul/latin fonts registers both in fontfaces."""
        import tempfile
        import zipfile
        import xml.etree.ElementTree as ET
        from pyhwpxlib.themes import Theme, FontSet, BUILTIN_THEMES
        from pyhwpxlib.builder import HwpxBuilder

        fs = FontSet(
            heading_hangul='나눔명조', heading_latin='Arial',
            body_hangul='함초롬돋움', body_latin='함초롬돋움',
        )
        theme = Theme(name='test_split',
                       palette=BUILTIN_THEMES['default'].palette,
                       fonts=fs)
        doc = HwpxBuilder(theme=theme)
        doc.add_heading("Test", level=1)

        with tempfile.NamedTemporaryFile(suffix='.hwpx', delete=False) as tmp:
            doc.save(tmp.name)
            with zipfile.ZipFile(tmp.name) as zf:
                header_xml = zf.read('Contents/header.xml')

        root = ET.fromstring(header_xml)
        ns = {'hh': 'http://www.hancom.co.kr/hwpml/2011/head'}
        hangul_ff = root.find('.//hh:fontface[@lang="HANGUL"]', ns)
        fonts = [f.get('face') for f in hangul_ff.findall('hh:font', ns)]
        assert '나눔명조' in fonts, f"Expected '나눔명조' in fontfaces, got {fonts}"
        assert 'Arial' in fonts, f"Expected 'Arial' in fontfaces, got {fonts}"
        assert '함초롬돋움' in fonts, f"Expected '함초롬돋움' in fontfaces, got {fonts}"


# ======================================================================
# Integration Tests
# ======================================================================

class TestThemeIntegration:
    """Integration tests for theme-builder wiring."""

    def test_theme_forest_colors(self):
        """HwpxBuilder(theme='forest') creates docs with forest palette colors in charPr."""
        import tempfile
        import zipfile
        import xml.etree.ElementTree as ET
        from pyhwpxlib.builder import HwpxBuilder

        doc = HwpxBuilder(theme='forest')
        doc.add_heading("Forest Heading", level=1)

        with tempfile.NamedTemporaryFile(suffix='.hwpx', delete=False) as tmp:
            doc.save(tmp.name)
            with zipfile.ZipFile(tmp.name) as zf:
                header_xml = zf.read('Contents/header.xml')

        root = ET.fromstring(header_xml)
        ns = {'hh': 'http://www.hancom.co.kr/hwpml/2011/head'}
        # Heading charPr should use forest on_surface color
        char_prs = root.findall('.//hh:charPr', ns)
        heading_cp = None
        for cp in char_prs:
            if cp.get('height') == '2400' and cp.find('hh:bold', ns) is not None:
                heading_cp = cp
                break
        assert heading_cp is not None, "Heading charPr not found"
        assert heading_cp.get('textColor') == '#2b3437', \
            f"Expected forest on_surface '#2b3437', got '{heading_cp.get('textColor')}'"

    def test_default_theme_backward_compat(self):
        """HwpxBuilder() and HwpxBuilder(theme='default') produce structurally identical output.

        Note: Paragraph IDs are random per-run, so we compare header.xml (deterministic)
        and verify both produce the same charPr/paraPr structures.
        """
        import tempfile
        import zipfile
        import xml.etree.ElementTree as ET
        from pyhwpxlib.builder import HwpxBuilder

        doc1 = HwpxBuilder()
        doc1.add_heading("Test", level=1)
        doc1.add_paragraph("Body")

        doc2 = HwpxBuilder(theme='default')
        doc2.add_heading("Test", level=1)
        doc2.add_paragraph("Body")

        with tempfile.NamedTemporaryFile(suffix='.hwpx', delete=False) as f1:
            doc1.save(f1.name)
            with zipfile.ZipFile(f1.name) as zf1:
                header1 = zf1.read('Contents/header.xml')

        with tempfile.NamedTemporaryFile(suffix='.hwpx', delete=False) as f2:
            doc2.save(f2.name)
            with zipfile.ZipFile(f2.name) as zf2:
                header2 = zf2.read('Contents/header.xml')

        # Header XML is deterministic and contains charPr/paraPr/fontfaces
        assert header1 == header2, "Header XML differs between HwpxBuilder() and HwpxBuilder(theme='default')"

        # Verify both use the same fontfaces (함초롬돋움/함초롬바탕)
        ns = {'hh': 'http://www.hancom.co.kr/hwpml/2011/head'}
        root = ET.fromstring(header1)
        hangul_ff = root.find('.//hh:fontface[@lang="HANGUL"]', ns)
        fonts = [f.get('face') for f in hangul_ff.findall('hh:font', ns)]
        assert fonts == ['함초롬돋움', '함초롬바탕'], \
            f"Default theme should use original font pair, got {fonts}"

    def test_all_themes_generate_valid_hwpx(self):
        """All 10 built-in themes produce valid HWPX (ZIP) files with required entries."""
        import tempfile
        import zipfile
        from pyhwpxlib.themes import BUILTIN_THEMES
        from pyhwpxlib.builder import HwpxBuilder

        for name in BUILTIN_THEMES:
            doc = HwpxBuilder(theme=name)
            doc.add_heading(f"{name} heading", level=1)
            doc.add_paragraph("Body text")

            with tempfile.NamedTemporaryFile(suffix='.hwpx', delete=False) as tmp:
                doc.save(tmp.name)
                assert zipfile.is_zipfile(tmp.name), f"Theme '{name}' produced invalid ZIP"
                with zipfile.ZipFile(tmp.name) as zf:
                    names = zf.namelist()
                    assert 'Contents/header.xml' in names, \
                        f"Theme '{name}' missing header.xml"
                    assert 'Contents/section0.xml' in names, \
                        f"Theme '{name}' missing section0.xml"

    def test_table_presets_from_theme(self):
        """HwpxBuilder(theme='forest') table uses forest primary color for header background."""
        from pyhwpxlib.builder import HwpxBuilder

        doc = HwpxBuilder(theme='forest')
        doc.add_table([["Header", "Col2"], ["Data1", "Data2"]])
        action = doc._actions[0]
        assert action['cell_colors'] is not None
        # Forest primary is #2C5F2D
        assert action['cell_colors'][(0, 0)] == '#2C5F2D', \
            f"Expected forest primary '#2C5F2D', got '{action['cell_colors'][(0, 0)]}'"\

    def test_invalid_theme_name_raises(self):
        """HwpxBuilder with unknown theme name raises ValueError."""
        from pyhwpxlib.builder import HwpxBuilder
        with pytest.raises(ValueError, match="Unknown theme"):
            HwpxBuilder(theme='nonexistent')

    def test_custom_theme_instance(self):
        """HwpxBuilder accepts a Theme instance directly."""
        from pyhwpxlib.themes import Theme, Palette, BUILTIN_THEMES
        from pyhwpxlib.builder import HwpxBuilder

        custom = Theme(
            name='custom',
            palette=BUILTIN_THEMES['forest'].palette,
        )
        doc = HwpxBuilder(theme=custom)
        assert doc._theme.name == 'custom'

    def test_module_level_ds_unchanged(self):
        """Module-level DS and TABLE_PRESETS remain unchanged after theme use."""
        from pyhwpxlib.builder import HwpxBuilder, DS, TABLE_PRESETS

        # Use a non-default theme
        doc = HwpxBuilder(theme='forest')
        doc.add_table([["A", "B"], ["1", "2"]])

        # Module-level constants should be untouched
        assert DS['primary'] == '#395da2'
        assert TABLE_PRESETS['corporate']['header_bg'] == '#395da2'
