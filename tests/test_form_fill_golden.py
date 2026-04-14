"""Golden tests for label-based form filling (fill_by_labels).

Covers:
- Empty cell patch via cellAddr anchor
- Text appears in generated document
- applied/failed counts are correct
- Unknown labels fail gracefully
- Output is a valid HWPX ZIP
"""
import os
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "templates"))

from form_pipeline import fill_by_labels, find_cell_by_label, extract_form, _patch_empty_cell
from pyhwpxlib.api import extract_text


SAMPLE = str(PROJECT_ROOT / "templates/sources/sample_의견제출서.hwpx")


@pytest.fixture(scope="module")
def sample_form():
    if not os.path.exists(SAMPLE):
        pytest.skip(f"Sample not found: {SAMPLE}")
    return SAMPLE


@pytest.fixture(scope="module")
def empty_label(sample_form):
    """Find a label whose right-adjacent cell is empty (suitable for empty-cell patch)."""
    form = extract_form(sample_form)
    for tbl in form["tables"]:
        for cell in tbl.get("cells", []):
            text = " ".join(
                r.get("text", "") for line in cell.get("lines", []) for r in line.get("runs", [])
            ).strip()
            if not text or len(text) > 12:
                continue
            r = find_cell_by_label(form, text, "right")
            if r and not r["target_cell"]["text"]:
                return text
    pytest.skip("No empty target cell found in sample")


class TestFillByLabels:
    def test_empty_cell_patch_applied(self, sample_form, empty_label, tmp_path):
        out = str(tmp_path / "filled.hwpx")
        result = fill_by_labels(sample_form, {f"{empty_label}>right": "테스트값"}, out)
        assert result["applied_count"] == 1
        assert result["failed_count"] == 0
        assert os.path.exists(out)

    def test_filled_value_appears_in_text(self, sample_form, empty_label, tmp_path):
        out = str(tmp_path / "filled.hwpx")
        fill_by_labels(sample_form, {f"{empty_label}>right": "홍길동UNIQUE"}, out)
        text = extract_text(out)
        assert "홍길동UNIQUE" in text

    def test_output_is_valid_zip(self, sample_form, empty_label, tmp_path):
        out = str(tmp_path / "filled.hwpx")
        fill_by_labels(sample_form, {f"{empty_label}>right": "값"}, out)
        assert zipfile.is_zipfile(out)

    def test_unknown_label_is_recorded_as_failed(self, sample_form, tmp_path):
        out = str(tmp_path / "filled.hwpx")
        result = fill_by_labels(
            sample_form,
            {"존재하지않는라벨XYZ>right": "v"},
            out,
        )
        assert result["failed_count"] == 1
        assert result["applied_count"] == 0
        assert result["failed"][0]["path"] == "존재하지않는라벨XYZ>right"

    def test_default_direction_is_right(self, sample_form, empty_label, tmp_path):
        out = str(tmp_path / "filled.hwpx")
        result = fill_by_labels(sample_form, {empty_label: "값"}, out)
        assert result["applied_count"] == 1

    def test_multiple_fills_in_one_call(self, sample_form, tmp_path):
        form = extract_form(sample_form)
        labels = []
        for tbl in form["tables"]:
            for cell in tbl.get("cells", []):
                text = " ".join(
                    r.get("text", "") for line in cell.get("lines", [])
                    for r in line.get("runs", [])
                ).strip()
                if not text or len(text) > 12:
                    continue
                r = find_cell_by_label(form, text, "right")
                if r and not r["target_cell"]["text"]:
                    labels.append(text)
                if len(labels) >= 2:
                    break
            if len(labels) >= 2:
                break
        if len(labels) < 2:
            pytest.skip("Need at least 2 empty target cells")

        out = str(tmp_path / "multi.hwpx")
        mappings = {f"{lbl}>right": f"VAL{i}" for i, lbl in enumerate(labels)}
        result = fill_by_labels(sample_form, mappings, out)
        assert result["applied_count"] == 2
        text = extract_text(out)
        assert "VAL0" in text
        assert "VAL1" in text


class TestPatchEmptyCell:
    """Unit tests for the low-level _patch_empty_cell XML surgery."""

    def test_replaces_self_closing_tag(self):
        xml = (
            '<hp:tc><hp:cellAddr colAddr="1" rowAddr="2"/>'
            '<hp:subList><hp:p><hp:run><hp:t/></hp:run></hp:p></hp:subList></hp:tc>'
        )
        out = _patch_empty_cell(xml, 1, 2, "hello")
        assert "<hp:t>hello</hp:t>" in out
        assert "<hp:t/>" not in out

    def test_replaces_empty_open_close_tag(self):
        xml = (
            '<hp:tc><hp:cellAddr colAddr="3" rowAddr="4"/>'
            '<hp:subList><hp:p><hp:run><hp:t></hp:t></hp:run></hp:p></hp:subList></hp:tc>'
        )
        out = _patch_empty_cell(xml, 3, 4, "world")
        assert "<hp:t>world</hp:t>" in out

    def test_missing_addr_returns_unchanged(self):
        xml = '<hp:tc><hp:cellAddr colAddr="0" rowAddr="0"/><hp:t/></hp:tc>'
        out = _patch_empty_cell(xml, 99, 99, "x")
        assert out == xml
