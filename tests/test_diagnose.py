"""Tests for pyhwpxlib.templates.diagnose CLI/API."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAKERS_HWPX = PROJECT_ROOT / "skill" / "templates" / "makers_project_report.hwpx"
MAKERS_SCHEMA = PROJECT_ROOT / "skill" / "templates" / "makers_project_report.schema.json"


def _has(p): return p.exists()


@pytest.mark.skipif(not _has(MAKERS_HWPX), reason="makers HWPX missing")
def test_diagnose_api_returns_grid_info():
    """Programmatic API returns per-table grid sub-region detection."""
    from pyhwpxlib.templates.diagnose import diagnose
    result = diagnose(MAKERS_HWPX)
    assert "schema" in result
    assert "tables" in result

    t0 = next(t for t in result["tables"] if t["index"] == 0)
    assert t0["grid"] is not None
    assert t0["grid"]["start_row"] == 3
    assert t0["grid"]["end_row"] == 6
    assert set(t0["grid"]["cols"]) == {1, 2, 4, 6}
    assert t0["row_group_label"] is not None  # "참 여 자"


@pytest.mark.skipif(not _has(MAKERS_HWPX) or not _has(MAKERS_SCHEMA),
                    reason="makers fixtures missing")
def test_diagnose_with_manual_schema_reports_overlap():
    from pyhwpxlib.templates.diagnose import diagnose
    result = diagnose(MAKERS_HWPX, manual_schema_path=MAKERS_SCHEMA)
    assert "comparison" in result
    cmp = result["comparison"]
    assert cmp["manual_keys_count"] == 44
    # table 0 is 100% — total overlap is 20/44 = 45% (table 1 활동사진 out of scope)
    assert cmp["overlap_count"] >= 20
    assert cmp["overlap_ratio"] >= 0.40


@pytest.mark.skipif(not _has(MAKERS_HWPX), reason="makers HWPX missing")
def test_diagnose_cli_text_output(capsys):
    from pyhwpxlib.templates.diagnose import main
    code = main([str(MAKERS_HWPX)])
    assert code == 0
    out = capsys.readouterr().out
    assert "Table 0" in out
    assert "Grid sub-region" in out
    assert "Auto fields" in out


@pytest.mark.skipif(not _has(MAKERS_HWPX) or not _has(MAKERS_SCHEMA),
                    reason="makers fixtures missing")
def test_diagnose_cli_json_with_schema(capsys):
    from pyhwpxlib.templates.diagnose import main
    code = main([str(MAKERS_HWPX), "--schema", str(MAKERS_SCHEMA), "--json"])
    assert code == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "comparison" in parsed
    assert parsed["comparison"]["overlap_ratio"] >= 0.40


def test_diagnose_cli_missing_file_returns_2(capsys, tmp_path):
    from pyhwpxlib.templates.diagnose import main
    code = main([str(tmp_path / "does_not_exist.hwpx")])
    assert code == 2


def test_diagnose_cli_wrong_extension_returns_2(tmp_path):
    from pyhwpxlib.templates.diagnose import main
    f = tmp_path / "x.docx"
    f.write_bytes(b"x")
    code = main([str(f)])
    assert code == 2
