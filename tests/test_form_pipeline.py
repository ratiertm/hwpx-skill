"""Tests for templates/form_pipeline.py — form extraction and generation."""
import os
import sys
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "templates"))

from form_pipeline import extract_form, generate_form


FORMS = [
    ("sample_의견제출서",   "templates/sources/sample_의견제출서.hwpx"),
    ("근로지원인서비스신청서",  "templates/sources/근로지원인서비스신청서.hwpx"),
    ("별지 제11호 서식",    "templates/sources/별지 제11호 서식.hwpx"),
    ("서식SAMPLE1",        "templates/sources/서식SAMPLE1.owpml"),
    ("서식SAMPLE2",        "templates/sources/서식SAMPLE2.owpml"),
    ("SimpleTable",        "templates/sources/SimpleTable.hwpx"),
]


@pytest.fixture(params=FORMS, ids=[f[0] for f in FORMS])
def form_path(request):
    name, rel_path = request.param
    abs_path = str(PROJECT_ROOT / rel_path)
    if not os.path.exists(abs_path):
        pytest.skip(f"Form not found: {abs_path}")
    return abs_path


class TestExtractForm:
    def test_returns_dict(self, form_path):
        data = extract_form(form_path)
        assert isinstance(data, dict)

    def test_has_tables_key(self, form_path):
        data = extract_form(form_path)
        assert "tables" in data

    def test_tables_is_list(self, form_path):
        data = extract_form(form_path)
        assert isinstance(data["tables"], list)

    def test_table_has_required_keys(self, form_path):
        data = extract_form(form_path)
        for table in data["tables"]:
            assert "rows" in table
            assert "cols" in table
            assert "cells" in table
            assert "merges" in table

    def test_table_dimensions_positive(self, form_path):
        data = extract_form(form_path)
        for table in data["tables"]:
            assert table["rows"] > 0
            assert table["cols"] > 0


class TestGenerateForm:
    def test_generates_hwpx_file(self, form_path, tmp_path):
        output_path = str(tmp_path / "generated.hwpx")
        data = extract_form(form_path)
        generate_form(data, output_path)
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 1000

    def test_output_is_valid_zip(self, form_path, tmp_path):
        import zipfile
        output_path = str(tmp_path / "generated.hwpx")
        data = extract_form(form_path)
        generate_form(data, output_path)
        assert zipfile.is_zipfile(output_path)


class TestRoundTrip:
    """Extract → generate → extract round-trip preserves structure."""

    def test_table_count_preserved(self, form_path, tmp_path):
        output_path = str(tmp_path / "clone.hwpx")
        orig = extract_form(form_path)
        generate_form(orig, output_path)
        clone = extract_form(output_path)
        assert len(orig["tables"]) == len(clone["tables"])

    def test_rows_cols_preserved(self, form_path, tmp_path):
        output_path = str(tmp_path / "clone.hwpx")
        orig = extract_form(form_path)
        generate_form(orig, output_path)
        clone = extract_form(output_path)
        for ot, ct in zip(orig["tables"], clone["tables"]):
            assert ot["rows"] == ct["rows"]
            assert ot["cols"] == ct["cols"]

    def test_cell_count_preserved(self, form_path, tmp_path):
        output_path = str(tmp_path / "clone.hwpx")
        orig = extract_form(form_path)
        generate_form(orig, output_path)
        clone = extract_form(output_path)
        for ot, ct in zip(orig["tables"], clone["tables"]):
            assert len(ot["cells"]) == len(ct["cells"])
