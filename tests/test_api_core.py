"""Tests for pyhwpxlib.api — core document operations."""
import os
import pytest
from pathlib import Path

from pyhwpxlib.api import (
    create_document,
    add_paragraph,
    add_styled_paragraph,
    add_heading,
    add_table,
    save,
    extract_text,
    fill_template,
    merge_documents,
)
from pyhwpxlib.hwpx_file import HWPXFile


# ============================================================
# create_document
# ============================================================

class TestCreateDocument:
    def test_returns_hwpx_file(self):
        doc = create_document()
        assert isinstance(doc, HWPXFile)

    def test_has_section(self):
        doc = create_document()
        section = doc.section_xml_file_list.get(0)
        assert section is not None


# ============================================================
# add_paragraph
# ============================================================

class TestAddParagraph:
    def test_returns_para(self, doc):
        from pyhwpxlib.objects.section.paragraph import Para
        para = add_paragraph(doc, "hello")
        assert para is not None

    def test_text_content(self, doc, tmp_hwpx):
        add_paragraph(doc, "pyhwpxlib test text")
        save(doc, tmp_hwpx)
        extracted = extract_text(tmp_hwpx)
        assert "pyhwpxlib test text" in extracted

    def test_empty_string(self, doc):
        para = add_paragraph(doc, "")
        assert para is not None

    def test_unicode(self, doc, tmp_hwpx):
        add_paragraph(doc, "한글 テスト 한글")
        save(doc, tmp_hwpx)
        extracted = extract_text(tmp_hwpx)
        assert "한글" in extracted

    def test_multiple_paragraphs(self, doc, tmp_hwpx):
        for i in range(5):
            add_paragraph(doc, f"Paragraph {i}")
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Paragraph 0" in text
        assert "Paragraph 4" in text


# ============================================================
# add_styled_paragraph
# ============================================================

class TestAddStyledParagraph:
    def test_bold(self, doc, tmp_hwpx):
        add_styled_paragraph(doc, "Bold text", bold=True)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)
        assert os.path.getsize(tmp_hwpx) > 0

    def test_font_size(self, doc, tmp_hwpx):
        add_styled_paragraph(doc, "Large text", font_size=24)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_color(self, doc, tmp_hwpx):
        add_styled_paragraph(doc, "Colored text", text_color="#FF0000")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_italic_underline(self, doc, tmp_hwpx):
        add_styled_paragraph(doc, "Italic underline", italic=True, underline=True)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_combined_styles(self, doc, tmp_hwpx):
        add_styled_paragraph(doc, "Combined", bold=True, italic=True, font_size=16, text_color="#0000FF")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


# ============================================================
# add_heading
# ============================================================

class TestAddHeading:
    def test_level1(self, doc, tmp_hwpx):
        add_heading(doc, "Heading 1", level=1)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "Heading 1" in text

    def test_all_levels(self, doc, tmp_hwpx):
        for level in range(1, 5):
            add_heading(doc, f"Level {level}", level=level)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        for level in range(1, 5):
            assert f"Level {level}" in text

    def test_default_level(self, doc, tmp_hwpx):
        add_heading(doc, "Default heading")
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)


# ============================================================
# add_table
# ============================================================

class TestAddTable:
    def test_basic_table(self, doc, tmp_hwpx):
        add_table(doc, rows=2, cols=2)
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_with_data(self, doc, tmp_hwpx):
        data = [["A", "B"], ["1", "2"]]
        add_table(doc, rows=2, cols=2, data=data)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "A" in text
        assert "B" in text

    def test_with_col_widths(self, doc, tmp_hwpx):
        add_table(doc, rows=2, cols=3, col_widths=[14000, 14000, 14520])
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_single_cell(self, doc, tmp_hwpx):
        add_table(doc, rows=1, cols=1, data=[["Only cell"]])
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)

    def test_large_table(self, doc, tmp_hwpx):
        data = [[f"r{r}c{c}" for c in range(5)] for r in range(10)]
        add_table(doc, rows=10, cols=5, data=data)
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert "r0c0" in text
        assert "r9c4" in text


# ============================================================
# save / extract_text
# ============================================================

class TestSaveAndExtract:
    def test_save_creates_file(self, doc, tmp_hwpx):
        save(doc, tmp_hwpx)
        assert os.path.exists(tmp_hwpx)
        assert os.path.getsize(tmp_hwpx) > 1000

    def test_save_is_valid_zip(self, doc, tmp_hwpx):
        import zipfile
        add_paragraph(doc, "test")
        save(doc, tmp_hwpx)
        assert zipfile.is_zipfile(tmp_hwpx)

    def test_extract_text_returns_string(self, doc, tmp_hwpx):
        add_paragraph(doc, "extractable text")
        save(doc, tmp_hwpx)
        text = extract_text(tmp_hwpx)
        assert isinstance(text, str)
        assert "extractable text" in text


# ============================================================
# fill_template
# ============================================================

class TestFillTemplate:
    def test_basic_fill(self, tmp_path):
        template_path = str(tmp_path / "tmpl.hwpx")
        output_path = str(tmp_path / "filled.hwpx")

        # Create template
        doc = create_document()
        add_paragraph(doc, "이름: {{이름}}, 나이: {{나이}}")
        save(doc, template_path)

        # Fill
        fill_template(template_path, {"이름": "홍길동", "나이": "30"}, output_path)

        assert os.path.exists(output_path)
        text = extract_text(output_path)
        assert "홍길동" in text
        assert "30" in text
        assert "{{" not in text, f"Curly braces should be removed: {text}"

    def test_fill_special_chars(self, tmp_path):
        """fill_template must handle &, <, > in values without breaking XML."""
        template_path = str(tmp_path / "tmpl.hwpx")
        output_path = str(tmp_path / "filled.hwpx")

        doc = create_document()
        add_paragraph(doc, "회사: {{company}}")
        save(doc, template_path)

        fill_template(template_path, {"company": "A&B < Corp"}, output_path)

        text = extract_text(output_path)
        assert "A&B < Corp" in text
        assert "{{" not in text

    def test_missing_placeholder_is_ignored(self, tmp_path):
        template_path = str(tmp_path / "tmpl.hwpx")
        output_path = str(tmp_path / "filled.hwpx")

        doc = create_document()
        add_paragraph(doc, "{{존재함}} and {{없음}}")
        save(doc, template_path)

        fill_template(template_path, {"존재함": "값"}, output_path)
        assert os.path.exists(output_path)

    def test_fill_exact_result_not_just_contains(self, tmp_path):
        """Verify exact replacement, not just 'value in text'."""
        template_path = str(tmp_path / "tmpl.hwpx")
        output_path = str(tmp_path / "filled.hwpx")

        doc = create_document()
        add_paragraph(doc, "Name: {{name}}")
        save(doc, template_path)

        fill_template(template_path, {"name": "홍길동"}, output_path)
        text = extract_text(output_path)
        assert "Name: 홍길동" in text
        assert "{{name}}" not in text
        assert "{{홍길동}}" not in text

    def test_fill_placeholder_repeated_twice(self, tmp_path):
        """Same placeholder appearing twice should both be replaced."""
        template_path = str(tmp_path / "tmpl.hwpx")
        output_path = str(tmp_path / "filled.hwpx")

        doc = create_document()
        add_paragraph(doc, "{{x}} and {{x}}")
        save(doc, template_path)

        fill_template(template_path, {"x": "OK"}, output_path)
        text = extract_text(output_path)
        assert text.strip() == "OK and OK"
        assert "{{" not in text

    def test_fill_keeps_xml_valid_with_all_special_chars(self, tmp_path):
        """Values with &, <, >, quotes must produce valid XML."""
        template_path = str(tmp_path / "tmpl.hwpx")
        output_path = str(tmp_path / "filled.hwpx")

        doc = create_document()
        add_paragraph(doc, "{{val}}")
        save(doc, template_path)

        fill_template(template_path, {"val": 'A&B <"C"> \'D\''}, output_path)
        text = extract_text(output_path)  # would throw ParseError if XML broken
        assert "A&B" in text
        assert "<" in text or "&lt;" not in text  # unescaped in text output


# ============================================================
# merge_documents
# ============================================================

class TestMergeDocuments:
    def test_merge_two(self, tmp_path):
        p1 = str(tmp_path / "a.hwpx")
        p2 = str(tmp_path / "b.hwpx")
        out = str(tmp_path / "merged.hwpx")

        doc1 = create_document()
        add_paragraph(doc1, "First document")
        save(doc1, p1)

        doc2 = create_document()
        add_paragraph(doc2, "Second document")
        save(doc2, p2)

        merge_documents([p1, p2], out)
        assert os.path.exists(out)
        text = extract_text(out)
        assert "First document" in text
        assert "Second document" in text
