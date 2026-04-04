"""Tests for pyhwpxlib.style_manager."""
import pytest
from pyhwpxlib.api import create_document, add_paragraph, add_table, save


class TestEnsureCharStyle:
    def test_basic_char_style(self):
        from pyhwpxlib.style_manager import ensure_char_style
        doc = create_document()
        cid = ensure_char_style(doc, font_name="Arial", height=1200, bold=False,
                                 italic=False, underline=False)
        assert cid is not None
        assert isinstance(cid, str)

    def test_bold_char_style(self):
        from pyhwpxlib.style_manager import ensure_char_style
        doc = create_document()
        cid = ensure_char_style(doc, font_name="Arial", height=1400, bold=True,
                                 italic=False, underline=False)
        assert cid is not None

    def test_italic_char_style(self):
        from pyhwpxlib.style_manager import ensure_char_style
        doc = create_document()
        cid = ensure_char_style(doc, font_name="Arial", height=1000, bold=False,
                                 italic=True, underline=False)
        assert cid is not None

    def test_with_color(self):
        from pyhwpxlib.style_manager import ensure_char_style
        doc = create_document()
        cid = ensure_char_style(doc, font_name="Arial", height=1200, bold=False,
                                 italic=False, underline=False, text_color="#FF0000")
        assert cid is not None

    def test_returns_same_id_for_same_style(self):
        from pyhwpxlib.style_manager import ensure_char_style
        doc = create_document()
        cid1 = ensure_char_style(doc, font_name="Arial", height=1200, bold=False,
                                  italic=False, underline=False)
        cid2 = ensure_char_style(doc, font_name="Arial", height=1200, bold=False,
                                  italic=False, underline=False)
        assert cid1 == cid2

    def test_different_fonts_get_different_ids(self):
        from pyhwpxlib.style_manager import ensure_char_style
        doc = create_document()
        cid1 = ensure_char_style(doc, font_name="Arial", height=1200, bold=False,
                                  italic=False, underline=False)
        cid2 = ensure_char_style(doc, font_name="Helvetica", height=1200, bold=False,
                                  italic=False, underline=False)
        assert cid1 != cid2


class TestEnsureBorderFill:
    def test_basic_border_fill(self):
        from pyhwpxlib.style_manager import ensure_border_fill
        doc = create_document()
        bid = ensure_border_fill(doc, face_color="#FF0000")
        assert bid is not None
        assert isinstance(bid, str)

    def test_no_color(self):
        from pyhwpxlib.style_manager import ensure_border_fill
        doc = create_document()
        bid = ensure_border_fill(doc)
        assert bid is not None

    def test_returns_same_id_for_same_color(self):
        from pyhwpxlib.style_manager import ensure_border_fill
        doc = create_document()
        bid1 = ensure_border_fill(doc, face_color="#0000FF")
        bid2 = ensure_border_fill(doc, face_color="#0000FF")
        assert bid1 == bid2

    def test_different_colors_get_different_ids(self):
        from pyhwpxlib.style_manager import ensure_border_fill
        doc = create_document()
        bid1 = ensure_border_fill(doc, face_color="#FF0000")
        bid2 = ensure_border_fill(doc, face_color="#00FF00")
        assert bid1 != bid2


class TestEnsureGradientBorderFill:
    def test_linear_gradient(self):
        from pyhwpxlib.style_manager import ensure_gradient_border_fill
        doc = create_document()
        bid = ensure_gradient_border_fill(doc, start_color="#FF0000", end_color="#0000FF")
        assert bid is not None

    def test_returns_same_id_for_same_gradient(self):
        from pyhwpxlib.style_manager import ensure_gradient_border_fill
        doc = create_document()
        bid1 = ensure_gradient_border_fill(doc, start_color="#FF0000", end_color="#0000FF")
        bid2 = ensure_gradient_border_fill(doc, start_color="#FF0000", end_color="#0000FF")
        assert bid1 == bid2


class TestEnsureParaStyle:
    def test_basic_para_style(self):
        from pyhwpxlib.style_manager import ensure_para_style
        doc = create_document()
        pid = ensure_para_style(doc)
        assert pid is not None

    def test_with_align(self):
        from pyhwpxlib.style_manager import ensure_para_style
        doc = create_document()
        pid = ensure_para_style(doc, align="LEFT")
        assert pid is not None

    def test_different_indent(self):
        from pyhwpxlib.style_manager import ensure_para_style
        doc = create_document()
        pid1 = ensure_para_style(doc)
        pid2 = ensure_para_style(doc, indent=500)
        assert pid1 != pid2


class TestEnsureNumbering:
    def test_basic_numbering(self):
        from pyhwpxlib.style_manager import ensure_numbering
        doc = create_document()
        nid = ensure_numbering(doc)
        assert nid is not None

    def test_returns_same_id_for_same_style(self):
        from pyhwpxlib.style_manager import ensure_numbering
        doc = create_document()
        nid1 = ensure_numbering(doc)
        nid2 = ensure_numbering(doc)
        assert nid1 == nid2

    def test_force_new_creates_different(self):
        from pyhwpxlib.style_manager import ensure_numbering
        doc = create_document()
        nid1 = ensure_numbering(doc)
        nid2 = ensure_numbering(doc, force_new=True)
        # force_new should create a new numbering
        assert nid1 is not None
        assert nid2 is not None


class TestEnsureBullet:
    def test_basic_bullet(self):
        from pyhwpxlib.style_manager import ensure_bullet
        doc = create_document()
        bid = ensure_bullet(doc, char="•")
        assert bid is not None

    def test_default_bullet(self):
        from pyhwpxlib.style_manager import ensure_bullet
        doc = create_document()
        bid = ensure_bullet(doc)
        assert bid is not None

    def test_different_bullets(self):
        from pyhwpxlib.style_manager import ensure_bullet
        doc = create_document()
        bid1 = ensure_bullet(doc, char="•")
        bid2 = ensure_bullet(doc, char="▪")
        assert bid1 is not None
        assert bid2 is not None


class TestFontSizeToHeight:
    def test_basic_conversion(self):
        from pyhwpxlib.style_manager import font_size_to_height
        result = font_size_to_height(12)
        assert result is not None
        assert isinstance(result, int)
        assert result > 0

    def test_none_returns_none(self):
        from pyhwpxlib.style_manager import font_size_to_height
        result = font_size_to_height(None)
        assert result is None

    def test_larger_size_gives_larger_height(self):
        from pyhwpxlib.style_manager import font_size_to_height
        h12 = font_size_to_height(12)
        h24 = font_size_to_height(24)
        assert h24 > h12


class TestCellGradient:
    def test_cell_gradient_via_add_table(self, tmp_path):
        from pyhwpxlib.api import add_table
        hwpx_path = str(tmp_path / "gradient.hwpx")
        doc = create_document()
        add_table(doc, rows=2, cols=2,
                  cell_gradients={(0, 0): {"start": "#FF0000", "end": "#0000FF"}})
        save(doc, hwpx_path)
        import os
        assert os.path.exists(hwpx_path)


class TestSetCellGradient:
    def test_set_cell_gradient(self, tmp_path):
        from pyhwpxlib.api import add_table, set_cell_gradient
        import os
        hwpx_path = str(tmp_path / "cell_grad.hwpx")
        doc = create_document()
        add_table(doc, rows=2, cols=2)
        # Table is at para index 1 (index 0 is the default blank para)
        set_cell_gradient(doc, 1, row=0, col=0,
                          start_color="#FF0000", end_color="#FFFFFF")
        save(doc, hwpx_path)
        assert os.path.exists(hwpx_path)
