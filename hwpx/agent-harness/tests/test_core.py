"""Unit tests for cli-anything-hwpx core modules."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from cli_anything.hwpx.core import document as doc_mod
from cli_anything.hwpx.core import text as text_mod
from cli_anything.hwpx.core import table as table_mod
from cli_anything.hwpx.core import image as image_mod
from cli_anything.hwpx.core import export as export_mod
from cli_anything.hwpx.core import validate as validate_mod
from cli_anything.hwpx.core import structure as struct_mod
from cli_anything.hwpx.core.session import Session


# ── Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def new_doc():
    return doc_mod.new_document()


@pytest.fixture
def doc_with_text():
    doc = doc_mod.new_document()
    text_mod.add_paragraph(doc, "첫 번째 문단: 한컴오피스 HWPX 테스트")
    text_mod.add_paragraph(doc, "두 번째 문단: CLI-Anything 래퍼 검증")
    text_mod.add_paragraph(doc, "세 번째 문단: 텍스트 검색 기능 확인")
    return doc


@pytest.fixture
def saved_hwpx(doc_with_text, tmp_dir):
    path = str(tmp_dir / "test.hwpx")
    doc_mod.save_document(doc_with_text, path)
    return path


# ── document.py ────────────────────────────────────────────────────────

class TestDocument:
    def test_new_document_creates_valid_doc(self, new_doc):
        assert new_doc is not None
        assert len(new_doc.sections) >= 1

    def test_new_document_has_empty_text(self, new_doc):
        info = doc_mod.get_document_info(new_doc)
        assert info["text_length"] == 0

    def test_save_and_open(self, new_doc, tmp_dir):
        path = str(tmp_dir / "save_test.hwpx")
        doc_mod.save_document(new_doc, path)
        assert os.path.exists(path)

        reopened = doc_mod.open_document(path)
        assert len(reopened.sections) == len(new_doc.sections)

    def test_open_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            doc_mod.open_document("/tmp/does_not_exist_12345.hwpx")

    def test_open_non_hwpx_raises(self, tmp_dir):
        txt_file = tmp_dir / "test.txt"
        txt_file.write_text("not hwpx")
        with pytest.raises(ValueError, match="Not a .hwpx file"):
            doc_mod.open_document(str(txt_file))

    def test_get_document_info_keys(self, new_doc):
        info = doc_mod.get_document_info(new_doc)
        assert "sections" in info
        assert "paragraphs" in info
        assert "images" in info
        assert "text_length" in info
        assert "styles" in info

    def test_get_document_info_with_text(self, doc_with_text):
        info = doc_mod.get_document_info(doc_with_text)
        assert info["paragraphs"] >= 4  # 1 initial + 3 added
        assert info["text_length"] > 0


# ── text.py ────────────────────────────────────────────────────────────

class TestText:
    def test_extract_text(self, doc_with_text):
        text = text_mod.extract_text(doc_with_text)
        assert "첫 번째 문단" in text
        assert "CLI-Anything" in text

    def test_extract_markdown(self, doc_with_text):
        md = text_mod.extract_markdown(doc_with_text)
        assert len(md) > 0
        assert "첫 번째 문단" in md

    def test_extract_html(self, doc_with_text):
        html = text_mod.extract_html(doc_with_text)
        assert "<p>" in html or "<html" in html

    def test_find_text_found(self, doc_with_text):
        results = text_mod.find_text(doc_with_text, "CLI")
        assert len(results) >= 1
        assert any("CLI" in r["text"] for r in results)

    def test_find_text_not_found(self, doc_with_text):
        results = text_mod.find_text(doc_with_text, "NONEXISTENT_XYZ_12345")
        assert len(results) == 0

    def test_find_text_case_insensitive(self, doc_with_text):
        results = text_mod.find_text(doc_with_text, "cli")
        assert len(results) >= 1

    def test_replace_text(self, doc_with_text):
        count = text_mod.replace_text(doc_with_text, "테스트", "TEST")
        assert count >= 1
        text = text_mod.extract_text(doc_with_text)
        assert "TEST" in text
        assert "테스트" not in text

    def test_replace_text_no_match(self, doc_with_text):
        count = text_mod.replace_text(doc_with_text, "NONEXISTENT_XYZ", "replaced")
        assert count == 0

    def test_add_paragraph(self, new_doc):
        result = text_mod.add_paragraph(new_doc, "추가된 문단")
        assert result["status"] == "added"
        text = text_mod.extract_text(new_doc)
        assert "추가된 문단" in text


# ── table.py ───────────────────────────────────────────────────────────

class TestTable:
    def test_add_table(self, new_doc):
        result = table_mod.add_table(new_doc, rows=3, cols=4)
        assert result["rows"] == 3
        assert result["cols"] == 4
        assert result["status"] == "added"

    def test_list_tables_empty(self, new_doc):
        tables = table_mod.list_tables(new_doc)
        assert len(tables) == 0

    def test_list_tables_after_add(self, new_doc):
        table_mod.add_table(new_doc, rows=2, cols=3)
        tables = table_mod.list_tables(new_doc)
        assert len(tables) == 1
        assert tables[0]["rows"] == 2
        assert tables[0]["cols"] == 3

    def test_add_multiple_tables(self, new_doc):
        table_mod.add_table(new_doc, rows=2, cols=2)
        table_mod.add_table(new_doc, rows=5, cols=3)
        tables = table_mod.list_tables(new_doc)
        assert len(tables) == 2


# ── image.py ───────────────────────────────────────────────────────────

class TestImage:
    def test_add_image_nonexistent_raises(self, new_doc):
        with pytest.raises(FileNotFoundError):
            image_mod.add_image(new_doc, "/tmp/nonexistent_img_12345.png")

    def test_list_images_empty(self, new_doc):
        images = image_mod.list_images(new_doc)
        assert isinstance(images, list)

    def test_remove_image_invalid_index(self, new_doc):
        with pytest.raises(IndexError):
            image_mod.remove_image(new_doc, 99)


# ── export.py ──────────────────────────────────────────────────────────

class TestExport:
    def test_export_text(self, doc_with_text, tmp_dir):
        out = str(tmp_dir / "out.txt")
        result = export_mod.export_to_file(doc_with_text, out, "text")
        assert result["status"] == "exported"
        assert result["size_bytes"] > 0
        content = Path(out).read_text(encoding="utf-8")
        assert "첫 번째 문단" in content

    def test_export_markdown(self, doc_with_text, tmp_dir):
        out = str(tmp_dir / "out.md")
        result = export_mod.export_to_file(doc_with_text, out, "markdown")
        assert result["format"] == "markdown"
        assert Path(out).stat().st_size > 0

    def test_export_html(self, doc_with_text, tmp_dir):
        out = str(tmp_dir / "out.html")
        result = export_mod.export_to_file(doc_with_text, out, "html")
        assert result["format"] == "html"
        content = Path(out).read_text(encoding="utf-8")
        assert "<p>" in content or "<html" in content

    def test_export_unknown_format_raises(self, doc_with_text, tmp_dir):
        out = str(tmp_dir / "out.xyz")
        with pytest.raises(ValueError, match="Unknown format"):
            export_mod.export_to_file(doc_with_text, out, "xyz")


# ── validate.py ────────────────────────────────────────────────────────

class TestValidate:
    def test_validate_document_valid(self, new_doc):
        result = validate_mod.validate_document(new_doc)
        assert result["is_valid"] is True

    def test_validate_document_from_path(self, saved_hwpx):
        result = validate_mod.validate_document(saved_hwpx)
        assert "is_valid" in result

    def test_validate_package_valid(self, saved_hwpx):
        result = validate_mod.validate_package(saved_hwpx)
        assert "is_valid" in result

    def test_validate_package_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            validate_mod.validate_package("/tmp/nonexistent_12345.hwpx")


# ── structure.py ───────────────────────────────────────────────────────

class TestStructure:
    def test_list_sections(self, new_doc):
        sections = struct_mod.list_sections(new_doc)
        assert len(sections) >= 1
        assert "paragraphs" in sections[0]

    def test_add_section(self, new_doc):
        before = len(new_doc.sections)
        result = struct_mod.add_section(new_doc)
        assert result["status"] == "added"
        assert len(new_doc.sections) == before + 1

    def test_set_header(self, new_doc):
        result = struct_mod.set_header(new_doc, "Test Header")
        assert result["status"] == "set"
        assert result["text"] == "Test Header"

    def test_set_footer(self, new_doc):
        result = struct_mod.set_footer(new_doc, "Test Footer")
        assert result["status"] == "set"
        assert result["text"] == "Test Footer"

    def test_add_bookmark(self, new_doc):
        result = struct_mod.add_bookmark(new_doc, "chapter1")
        assert result["status"] == "added"
        assert result["name"] == "chapter1"

    def test_add_hyperlink(self, new_doc):
        result = struct_mod.add_hyperlink(new_doc, "https://example.com", "Example")
        assert result["status"] == "added"
        assert result["url"] == "https://example.com"


# ── session.py ─────────────────────────────────────────────────────────

class TestSession:
    def test_new_session_has_no_project(self):
        sess = Session()
        assert sess.has_project() is False

    def test_get_doc_without_project_raises(self):
        sess = Session()
        with pytest.raises(RuntimeError, match="No document open"):
            sess.get_doc()

    def test_set_and_get_doc(self, new_doc):
        sess = Session()
        sess.set_doc(new_doc, "/tmp/test.hwpx")
        assert sess.has_project() is True
        assert sess.get_doc() is new_doc
        assert sess.path == "/tmp/test.hwpx"

    def test_initial_not_modified(self, new_doc):
        sess = Session()
        sess.set_doc(new_doc)
        assert sess.modified is False

    def test_snapshot_marks_modified(self, new_doc):
        sess = Session()
        sess.set_doc(new_doc)
        sess.snapshot()
        assert sess.modified is True

    def test_undo_redo_cycle(self):
        sess = Session()
        doc = doc_mod.new_document()
        sess.set_doc(doc)

        # Add text, snapshot before
        sess.snapshot()
        text_mod.add_paragraph(doc, "paragraph 1")
        text_before = text_mod.extract_text(sess.get_doc())

        sess.snapshot()
        text_mod.add_paragraph(doc, "paragraph 2")
        text_after = text_mod.extract_text(sess.get_doc())

        assert "paragraph 2" in text_after

        # Undo -> should restore to before paragraph 2
        assert sess.undo() is True
        text_undone = text_mod.extract_text(sess.get_doc())
        assert "paragraph 2" not in text_undone
        assert "paragraph 1" in text_undone

        # Redo -> should restore paragraph 2
        assert sess.redo() is True
        text_redone = text_mod.extract_text(sess.get_doc())
        assert "paragraph 2" in text_redone

    def test_undo_empty_returns_false(self, new_doc):
        sess = Session()
        sess.set_doc(new_doc)
        assert sess.undo() is False

    def test_redo_empty_returns_false(self, new_doc):
        sess = Session()
        sess.set_doc(new_doc)
        assert sess.redo() is False

    def test_save_without_path_raises(self, new_doc):
        sess = Session()
        sess.set_doc(new_doc)
        with pytest.raises(ValueError, match="No save path"):
            sess.save()

    def test_save_with_path(self, new_doc, tmp_dir):
        sess = Session()
        sess.set_doc(new_doc)
        path = str(tmp_dir / "session_save.hwpx")
        saved = sess.save(path)
        assert saved == path
        assert sess.modified is False
        assert os.path.exists(path)

    def test_info(self, new_doc):
        sess = Session()
        sess.set_doc(new_doc, "/tmp/info_test.hwpx")
        info = sess.info()
        assert info["path"] == "/tmp/info_test.hwpx"
        assert info["modified"] is False
        assert info["undo_depth"] == 0
        assert info["redo_depth"] == 0

    def test_max_undo_depth(self, new_doc):
        sess = Session()
        sess.set_doc(new_doc)
        for _ in range(60):
            sess.snapshot()
        assert len(sess._undo_stack) == Session.MAX_UNDO
