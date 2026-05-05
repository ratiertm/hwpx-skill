"""Module 2 (check-fill) tests.

Design Ref: render-perf-opt.design.md §8.2 + §8.3 — U-06,07 + I-04..08.
Plan SC: FR-06 (CLI), FR-07 (MCP).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


# --- Unit tests on CheckResult dataclass --------------------------------

def test_check_result_is_complete():
    from pyhwpxlib.templates.check_fill import CheckResult
    r = CheckResult(template="x", filled=["a", "b"], empty=[], placeholders=[])
    assert r.is_complete is True
    r2 = CheckResult(template="x", filled=["a"], empty=["b"], placeholders=[])
    assert r2.is_complete is False
    r3 = CheckResult(template="x", filled=["a", "b"], empty=[], placeholders=["{{c}}"])
    assert r3.is_complete is False


def test_check_result_to_dict_includes_is_complete():
    from pyhwpxlib.templates.check_fill import CheckResult
    r = CheckResult(template="x", filled=["a"], empty=[], placeholders=[])
    d = r.to_dict()
    assert d["is_complete"] is True
    assert d["template"] == "x"
    assert d["filled"] == ["a"]


# --- Schema-driven path -------------------------------------------------

@pytest.fixture
def fake_template(tmp_path: Path) -> dict:
    """Create a minimal HWPX-like fake + schema in tmp_path."""
    # We don't need a real HWPX for schema-driven check_fill — just a file
    # whose section0.xml is readable. But check_fill scans XML for
    # placeholders, so we provide a real (tiny) zip.
    import zipfile

    tpl_dir = tmp_path / "fake_tpl"
    tpl_dir.mkdir()
    hwpx_path = tpl_dir / "source.hwpx"
    section_xml = (
        '<?xml version="1.0"?>'
        '<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
        'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section">'
        '<hp:p><hp:run><hp:t>{{name}}</hp:t></hp:run></hp:p>'
        '<hp:p><hp:run><hp:t>학번: ____________</hp:t></hp:run></hp:p>'
        '<hp:p><hp:run><hp:t>concrete value</hp:t></hp:run></hp:p>'
        '</hs:sec>'
    ).encode("utf-8")
    with zipfile.ZipFile(hwpx_path, "w") as z:
        z.writestr("Contents/section0.xml", section_xml)

    schema = {
        "name": "fake_tpl",
        "tables": [{
            "index": 0,
            "fields": [
                {"key": "name", "cell": [0, 0]},
                {"key": "student_id", "cell": [1, 0]},
                {"key": "phone", "cell": [2, 0]},
            ],
        }],
    }
    schema_path = tpl_dir / "schema.json"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
    return {"hwpx": str(hwpx_path), "schema": str(schema_path)}


def test_check_fill_schema_path(fake_template):
    from pyhwpxlib.templates.check_fill import check_fill
    r = check_fill(fake_template["hwpx"],
                   {"name": "홍길동", "student_id": "20260001"})
    assert r.schema_used is True
    assert r.total_fields == 3
    assert "name" in r.filled
    assert "student_id" in r.filled
    assert "phone" in r.empty
    assert r.is_complete is False


def test_check_fill_complete_when_all_filled(fake_template):
    """Schema is complete, but the source.hwpx still has {{name}} / underscores."""
    from pyhwpxlib.templates.check_fill import check_fill
    r = check_fill(fake_template["hwpx"],
                   {"name": "A", "student_id": "B", "phone": "C"})
    # All schema fields filled, but the *source* template still has
    # placeholders in its XML — check_fill exposes them honestly.
    assert r.empty == []
    assert "{{name}}" in r.placeholders
    assert "<underscores>" in r.placeholders
    assert r.is_complete is False  # placeholders still present


def test_check_fill_partial_field(fake_template):
    """Empty string treated same as missing."""
    from pyhwpxlib.templates.check_fill import check_fill
    r = check_fill(fake_template["hwpx"],
                   {"name": "홍", "student_id": "  ", "phone": ""})
    assert "name" in r.filled
    assert "student_id" in r.empty  # whitespace-only counts as empty
    assert "phone" in r.empty


# --- Pattern fallback (no schema) ---------------------------------------

def test_check_fill_pattern_fallback(tmp_path):
    """When no schema is present, schema_used=False; fall back to placeholder scan."""
    import zipfile
    from pyhwpxlib.templates.check_fill import check_fill

    hwpx_path = tmp_path / "noschema.hwpx"
    section_xml = (
        '<?xml version="1.0"?>'
        '<hs:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
        'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section">'
        '<hp:p><hp:run><hp:t>{{title}}</hp:t></hp:run></hp:p>'
        '</hs:sec>'
    ).encode("utf-8")
    with zipfile.ZipFile(hwpx_path, "w") as z:
        z.writestr("Contents/section0.xml", section_xml)

    r = check_fill(str(hwpx_path), {"some": "value"})
    assert r.schema_used is False
    assert "{{title}}" in r.placeholders
    assert "some" in r.filled


# --- Resolved-name path (real registered template) ----------------------

def test_check_fill_via_registered_name():
    """End-to-end against the project's bundled makers_project_report template."""
    from pyhwpxlib.templates.check_fill import check_fill
    from pyhwpxlib.templates.resolver import resolve_template_path

    if resolve_template_path("makers_project_report", suffix=".hwpx") is None:
        pytest.skip("makers_project_report template not registered")

    r = check_fill("makers_project_report", {"team_name": "테스트팀"})
    assert r.schema_used is True
    assert r.total_fields > 1
    assert "team_name" in r.filled
    # Other schema fields unspecified → in empty
    assert len(r.empty) >= 1


# --- CLI exit codes (FR-06) ---------------------------------------------

def test_cli_check_fill_exit_codes(fake_template, tmp_path):
    """exit 0 when complete (and no placeholders); exit 1 when incomplete."""
    data_complete = tmp_path / "complete.json"
    data_complete.write_text(json.dumps({"name": "A", "student_id": "B", "phone": "C"}),
                             encoding="utf-8")
    data_partial = tmp_path / "partial.json"
    data_partial.write_text(json.dumps({"name": "A"}), encoding="utf-8")

    # Complete data — but source still has placeholders → exit 1
    proc = subprocess.run(
        [sys.executable, "-m", "pyhwpxlib.cli", "check-fill",
         fake_template["hwpx"], "-d", str(data_complete), "--json"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1, f"placeholders should fail: {proc.stdout}"
    out_complete = json.loads(proc.stdout)
    assert out_complete["ok"] is True
    assert out_complete["empty"] == []
    assert out_complete["placeholders"]

    # Partial data → exit 1
    proc = subprocess.run(
        [sys.executable, "-m", "pyhwpxlib.cli", "check-fill",
         fake_template["hwpx"], "-d", str(data_partial), "--json"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    out_partial = json.loads(proc.stdout)
    assert "student_id" in out_partial["empty"]
    assert "phone" in out_partial["empty"]


def test_cli_check_fill_writes_output_file(fake_template, tmp_path):
    """-o writes the CheckResult JSON to a file."""
    data = tmp_path / "data.json"
    data.write_text(json.dumps({"name": "A"}), encoding="utf-8")
    out = tmp_path / "report.json"
    subprocess.run(
        [sys.executable, "-m", "pyhwpxlib.cli", "check-fill",
         fake_template["hwpx"], "-d", str(data), "-o", str(out), "--json"],
        capture_output=True, text=True,
    )
    assert out.exists()
    parsed = json.loads(out.read_text(encoding="utf-8"))
    assert parsed["template"] == fake_template["hwpx"]
    assert "name" in parsed["filled"]


# --- Performance budget (~10ms target) ----------------------------------

def test_check_fill_speed(fake_template):
    """check_fill must stay under 100ms (10× margin over the 10ms target)."""
    import time
    from pyhwpxlib.templates.check_fill import check_fill

    # Warm up.
    check_fill(fake_template["hwpx"], {"name": "A"})
    t0 = time.perf_counter()
    for _ in range(10):
        check_fill(fake_template["hwpx"], {"name": "A"})
    elapsed = (time.perf_counter() - t0) / 10
    assert elapsed < 0.1, f"check_fill too slow: {elapsed*1000:.1f}ms"
