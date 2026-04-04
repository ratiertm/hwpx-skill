"""Tests for HTML converters — html_to_hwpx and html_converter."""
import os
import pytest

from pyhwpxlib.api import create_document, save, extract_text
from pyhwpxlib.html_to_hwpx import convert_html_to_hwpx


class TestHtmlToHwpx:
    def test_simple_paragraph(self, doc, tmp_hwpx):
        n = convert_html_to_hwpx(doc, "<p>Hello World</p>")
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Hello World" in text

    def test_heading(self, doc, tmp_hwpx):
        convert_html_to_hwpx(doc, "<h1>Main Title</h1>")
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Main Title" in text

    def test_unordered_list(self, doc, tmp_hwpx):
        convert_html_to_hwpx(doc, "<ul><li>Item 1</li><li>Item 2</li></ul>")
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Item 1" in text
        assert "Item 2" in text

    def test_ordered_list(self, doc, tmp_hwpx):
        convert_html_to_hwpx(doc, "<ol><li>First</li><li>Second</li></ol>")
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "First" in text

    def test_table(self, doc, tmp_hwpx):
        html = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        convert_html_to_hwpx(doc, html)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "A" in text
        assert "B" in text

    def test_bold_italic(self, doc, tmp_hwpx):
        convert_html_to_hwpx(doc, "<p><strong>bold</strong> and <em>italic</em></p>")
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "bold" in text
        assert "italic" in text

    def test_bad_base64_image_logs_warning(self, doc, tmp_hwpx, caplog):
        """Bad base64 image should log a warning, not raise."""
        import logging
        with caplog.at_level(logging.WARNING, logger="pyhwpxlib.html_to_hwpx"):
            convert_html_to_hwpx(doc, '<img src="data:image/png;base64,INVALID"/>')
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)
        assert "Failed to decode" in caplog.text

    def test_empty_html(self, doc, tmp_hwpx):
        n = convert_html_to_hwpx(doc, "")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_returns_count(self, doc):
        n = convert_html_to_hwpx(doc, "<p>hello</p>")
        assert isinstance(n, int)
        assert n >= 0

    def test_unicode(self, doc, tmp_hwpx):
        convert_html_to_hwpx(doc, "<p>한글 テスト</p>")
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "한글" in text


class TestHwpxToHtml:
    def test_convert_round_trip(self, tmp_path):
        from pyhwpxlib.api import create_document, add_paragraph, save
        from pyhwpxlib.html_converter import convert_hwpx_to_html

        hwpx_path = str(tmp_path / "test.hwpx")
        html_path = str(tmp_path / "output.html")

        doc = create_document()
        add_paragraph(doc, "Round trip test content")
        save(doc, hwpx_path)

        convert_hwpx_to_html(hwpx_path, output_path=html_path)
        assert os.path.exists(html_path)
        with open(html_path, encoding="utf-8") as f:
            html = f.read()
        assert "Round trip test content" in html

    def test_returns_html_string(self, tmp_path):
        from pyhwpxlib.api import create_document, add_paragraph, save
        from pyhwpxlib.html_converter import convert_hwpx_to_html

        hwpx_path = str(tmp_path / "test.hwpx")
        doc = create_document()
        add_paragraph(doc, "HTML string test")
        save(doc, hwpx_path)

        html_str = convert_hwpx_to_html(hwpx_path)
        assert isinstance(html_str, str)
        assert "HTML string test" in html_str
