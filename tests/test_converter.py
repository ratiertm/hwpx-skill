"""Tests for pyhwpxlib.converter — Markdown → HWPX."""
import os
import pytest

from pyhwpxlib.api import create_document, save, extract_text
from pyhwpxlib.converter import convert_markdown_to_hwpx


class TestMarkdownConverter:
    def test_headings(self, doc, tmp_hwpx):
        md = "# H1\n## H2\n### H3"
        convert_markdown_to_hwpx(doc, md)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "H1" in text
        assert "H2" in text
        assert "H3" in text

    def test_paragraph(self, doc, tmp_hwpx):
        md = "This is a paragraph.\n\nAnother paragraph."
        convert_markdown_to_hwpx(doc, md)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "This is a paragraph" in text
        assert "Another paragraph" in text

    def test_bold_italic(self, doc, tmp_hwpx):
        md = "**bold** and *italic*"
        convert_markdown_to_hwpx(doc, md)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "bold" in text
        assert "italic" in text

    def test_bullet_list(self, doc, tmp_hwpx):
        md = "- Item A\n- Item B\n- Item C"
        convert_markdown_to_hwpx(doc, md)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Item A" in text
        assert "Item B" in text
        assert "Item C" in text

    def test_numbered_list(self, doc, tmp_hwpx):
        md = "1. First\n2. Second\n3. Third"
        convert_markdown_to_hwpx(doc, md)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "First" in text
        assert "Third" in text

    def test_table(self, doc, tmp_hwpx):
        md = "| Col1 | Col2 |\n|------|------|\n| A | B |\n| C | D |"
        convert_markdown_to_hwpx(doc, md)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Col1" in text
        assert "Col2" in text

    def test_code_block(self, doc, tmp_hwpx):
        md = "```python\nprint('hello')\n```"
        convert_markdown_to_hwpx(doc, md)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "print" in text

    def test_empty_markdown(self, doc, tmp_hwpx):
        convert_markdown_to_hwpx(doc, "")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_unicode_markdown(self, doc, tmp_hwpx):
        md = "# 한국어 제목\n\n한글 텍스트입니다."
        convert_markdown_to_hwpx(doc, md)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "한국어" in text
        assert "한글" in text

    def test_returns_integer(self, doc):
        result = convert_markdown_to_hwpx(doc, "# Hello")
        # Should return number of elements or None (not raise)
        assert result is None or isinstance(result, int)
