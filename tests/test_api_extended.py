"""Extended tests for pyhwpxlib.api — shapes, lists, headers, misc functions."""
import os
import pytest
from pathlib import Path

from pyhwpxlib.api import (
    create_document,
    add_paragraph,
    add_heading,
    add_bullet_list,
    add_numbered_list,
    add_nested_bullet_list,
    add_nested_numbered_list,
    add_code_block,
    add_rectangle,
    add_ellipse,
    add_line,
    add_header,
    add_footer,
    add_page_number,
    add_footnote,
    add_bookmark,
    add_hyperlink,
    add_highlight,
    add_tab,
    add_special_char,
    add_hidden_comment,
    add_textart,
    add_checkbox,
    add_radio_button,
    add_button,
    add_edit_field,
    add_combobox,
    add_listbox,
    add_scrollbar,
    add_dutmal,
    add_indexmark,
    set_columns,
    set_page_setup,
    extract_markdown,
    extract_html,
    save,
    extract_text,
)


# ============================================================
# Lists
# ============================================================

class TestBulletList:
    def test_basic_bullet_list(self, doc, tmp_hwpx):
        add_bullet_list(doc, ["Alpha", "Beta", "Gamma"])
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Alpha" in text
        assert "Beta" in text
        assert "Gamma" in text

    def test_single_item(self, doc, tmp_hwpx):
        add_bullet_list(doc, ["Only Item"])
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Only Item" in text

    def test_korean_items(self, doc, tmp_hwpx):
        add_bullet_list(doc, ["첫 번째", "두 번째"])
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "첫 번째" in text

    def test_returns_list(self, doc):
        result = add_bullet_list(doc, ["A", "B"])
        assert result is not None


class TestNumberedList:
    def test_basic_numbered_list(self, doc, tmp_hwpx):
        add_numbered_list(doc, ["First", "Second", "Third"])
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "First" in text
        assert "Third" in text

    def test_returns_list(self, doc):
        result = add_numbered_list(doc, ["X", "Y"])
        assert result is not None


class TestNestedBulletList:
    def test_basic_nested(self, doc, tmp_hwpx):
        # items is list of (level, text) tuples
        items = [(0, "Parent"), (1, "Child 1"), (1, "Child 2")]
        add_nested_bullet_list(doc, items)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Parent" in text
        assert "Child 1" in text

    def test_flat_items(self, doc, tmp_hwpx):
        items = [(0, "Item A"), (0, "Item B")]
        add_nested_bullet_list(doc, items)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Item A" in text


class TestNestedNumberedList:
    def test_basic_nested(self, doc, tmp_hwpx):
        items = [(0, "Section 1"), (1, "1.1"), (1, "1.2"), (0, "Section 2")]
        add_nested_numbered_list(doc, items)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Section 1" in text
        assert "1.1" in text


class TestCodeBlock:
    def test_basic_code_block(self, doc, tmp_hwpx):
        add_code_block(doc, "print('hello world')")
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "print" in text

    def test_multiline_code(self, doc, tmp_hwpx):
        code = "def foo():\n    return 42"
        add_code_block(doc, code)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "foo" in text

    def test_with_language(self, doc, tmp_hwpx):
        add_code_block(doc, "x = 1", language="python")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


# ============================================================
# Headings
# ============================================================

class TestHeadings:
    def test_all_heading_levels(self, doc, tmp_hwpx):
        for level in range(1, 7):
            add_heading(doc, f"Heading {level}", level=level)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        for level in range(1, 7):
            assert f"Heading {level}" in text


# ============================================================
# Shapes
# ============================================================

class TestShapes:
    def test_add_rectangle(self, doc, tmp_hwpx):
        add_rectangle(doc, width=5000, height=3000)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)
        assert os.path.getsize(tmp_hwpx) > 1000

    def test_add_ellipse(self, doc, tmp_hwpx):
        add_ellipse(doc, width=4000, height=4000)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_line(self, doc, tmp_hwpx):
        add_line(doc)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_rectangle_with_text(self, doc, tmp_hwpx):
        add_rectangle(doc, width=6000, height=2000, text="Shape Text")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)
        assert os.path.getsize(tmp_hwpx) > 1000

    def test_multiple_shapes(self, doc, tmp_hwpx):
        add_rectangle(doc, width=3000, height=2000)
        add_ellipse(doc, width=3000, height=2000)
        add_line(doc)
        save(doc, tmp_hwpx)
        assert os.path.getsize(tmp_hwpx) > 1000


# ============================================================
# Header / Footer / Page Number
# ============================================================

class TestHeaderFooter:
    def test_add_header(self, doc, tmp_hwpx):
        add_header(doc, "Document Header")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_footer(self, doc, tmp_hwpx):
        add_footer(doc, "Page Footer")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_page_number(self, doc, tmp_hwpx):
        add_page_number(doc)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_header_and_footer(self, doc, tmp_hwpx):
        add_header(doc, "Header Text")
        add_footer(doc, "Footer Text")
        add_paragraph(doc, "Body content")
        save(doc, tmp_hwpx)
        assert os.path.getsize(tmp_hwpx) > 1000


# ============================================================
# Footnotes / Bookmarks / Hyperlinks
# ============================================================

class TestAnnotations:
    def test_add_footnote(self, doc, tmp_hwpx):
        add_footnote(doc, "Footnote content here")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_bookmark(self, doc, tmp_hwpx):
        add_bookmark(doc, "mybookmark")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_hyperlink(self, doc, tmp_hwpx):
        add_hyperlink(doc, "Click here", "https://example.com")
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Click here" in text

    def test_add_hidden_comment(self, doc, tmp_hwpx):
        add_hidden_comment(doc, "This is a hidden comment")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


# ============================================================
# Text Formatting
# ============================================================

class TestTextFormatting:
    def test_add_highlight(self, doc, tmp_hwpx):
        add_highlight(doc, "Highlighted text")
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Highlighted text" in text

    def test_add_tab(self, doc, tmp_hwpx):
        add_paragraph(doc, "Before tab")
        add_tab(doc)
        add_paragraph(doc, "After tab")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_special_char(self, doc, tmp_hwpx):
        add_special_char(doc, "★")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_dutmal(self, doc, tmp_hwpx):
        add_dutmal(doc, "base", "ruby")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_indexmark(self, doc, tmp_hwpx):
        add_indexmark(doc, "index term")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


# ============================================================
# Textart
# ============================================================

class TestTextart:
    def test_add_textart(self, doc, tmp_hwpx):
        add_textart(doc, "WordArt Text")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


# ============================================================
# Form Controls
# ============================================================

class TestFormControls:
    def test_add_checkbox(self, doc, tmp_hwpx):
        add_checkbox(doc, "Check me")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_radio_button(self, doc, tmp_hwpx):
        add_radio_button(doc, "Option A")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_button(self, doc, tmp_hwpx):
        add_button(doc, "Submit")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_edit_field(self, doc, tmp_hwpx):
        add_edit_field(doc, text="Default text")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_combobox(self, doc, tmp_hwpx):
        # items is list of (display_text, value) tuples
        add_combobox(doc, items=[("Option 1", "1"), ("Option 2", "2")])
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_listbox(self, doc, tmp_hwpx):
        add_listbox(doc, items=[("Item A", "a"), ("Item B", "b")])
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_add_scrollbar(self, doc, tmp_hwpx):
        add_scrollbar(doc)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


# ============================================================
# Column Layout
# ============================================================

class TestColumnLayout:
    def test_set_columns(self, doc, tmp_hwpx):
        set_columns(doc, col_count=2)
        add_paragraph(doc, "Two-column layout text")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_single_column(self, doc, tmp_hwpx):
        set_columns(doc, col_count=1)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_three_columns(self, doc, tmp_hwpx):
        set_columns(doc, col_count=3)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


# ============================================================
# Page Setup
# ============================================================

class TestPageSetup:
    def test_set_page_setup_a4(self, doc, tmp_hwpx):
        set_page_setup(doc, paper="A4")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_set_page_setup_landscape(self, doc, tmp_hwpx):
        set_page_setup(doc, landscape=True)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_set_page_setup_margins(self, doc, tmp_hwpx):
        set_page_setup(doc, margin_top=2000, margin_bottom=2000,
                       margin_left=2000, margin_right=2000)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


# ============================================================
# Extract functions
# ============================================================

class TestExtractFunctions:
    def test_extract_markdown(self, tmp_path):
        hwpx_path = str(tmp_path / "test.hwpx")
        doc = create_document()
        add_heading(doc, "Test Heading", level=1)
        add_paragraph(doc, "Test paragraph content")
        save(doc, hwpx_path)

        md = extract_markdown(hwpx_path)
        assert isinstance(md, str)
        assert len(md) > 0

    def test_extract_html(self, tmp_path):
        hwpx_path = str(tmp_path / "test.hwpx")
        doc = create_document()
        add_paragraph(doc, "HTML extraction test")
        save(doc, hwpx_path)

        html = extract_html(hwpx_path)
        assert isinstance(html, str)
        assert "HTML extraction test" in html

    def test_extract_markdown_with_table(self, tmp_path):
        from pyhwpxlib.api import add_table
        hwpx_path = str(tmp_path / "table.hwpx")
        doc = create_document()
        tbl = add_table(doc, rows=2, cols=2)
        save(doc, hwpx_path)

        md = extract_markdown(hwpx_path)
        assert isinstance(md, str)
