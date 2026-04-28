"""Tests for v0.14.0 rhwp-strict-mode: validate dual-mode + doctor + opt-in fix."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAFE_FIXTURE = PROJECT_ROOT / "Test/output/지청운_전문가활용내역서_2_safe.hwpx"
MAKERS_HWPX = PROJECT_ROOT / "skill/templates/makers_project_report.hwpx"


def _has(p): return p.exists()


# ─── doctor API ────────────────────────────────────────────────────


@pytest.mark.skipif(not _has(SAFE_FIXTURE),
                    reason="known-overflow fixture missing")
def test_doctor_diagnose_detects_overflow():
    from pyhwpxlib.doctor import diagnose
    report = diagnose(SAFE_FIXTURE)
    assert report["needs_fix"] is True
    assert report["totals"]["textpos_overflow"] > 0
    codes = {it["code"] for it in report["issues"]}
    assert "TEXTPOS_OVERFLOW" in codes


@pytest.mark.skipif(not _has(MAKERS_HWPX), reason="makers fixture missing")
def test_doctor_diagnose_clean_template():
    """Clean templates should not need fix."""
    from pyhwpxlib.doctor import diagnose
    report = diagnose(MAKERS_HWPX)
    assert report["needs_fix"] is False
    assert report["totals"]["textpos_overflow"] == 0


@pytest.mark.skipif(not _has(SAFE_FIXTURE),
                    reason="known-overflow fixture missing")
def test_doctor_fix_writes_corrected_file(tmp_path):
    from pyhwpxlib.doctor import diagnose, fix
    out = tmp_path / "fixed.hwpx"
    pre = diagnose(SAFE_FIXTURE)
    assert pre["needs_fix"]
    result = fix(SAFE_FIXTURE, out)
    assert result["linesegs_fixed"] > 0
    post = diagnose(out)
    assert post["needs_fix"] is False


def test_doctor_diagnose_missing_file():
    from pyhwpxlib.doctor import diagnose
    report = diagnose("/nonexistent/file.hwpx")
    assert report["ok"] is False
    assert "not found" in report["summary"].lower()


# ─── doctor CLI ────────────────────────────────────────────────────


@pytest.mark.skipif(not _has(SAFE_FIXTURE), reason="fixture missing")
def test_doctor_cli_no_fix_returns_1_when_needs_fix(capsys):
    from pyhwpxlib.doctor import main
    code = main([str(SAFE_FIXTURE)])
    out = capsys.readouterr().out
    assert code == 1  # exit code for "needs fix and not fixed"
    assert "TEXTPOS_OVERFLOW" in out


@pytest.mark.skipif(not _has(SAFE_FIXTURE), reason="fixture missing")
def test_doctor_cli_with_fix_writes_output(tmp_path, capsys):
    from pyhwpxlib.doctor import main
    out = tmp_path / "fixed.hwpx"
    code = main([str(SAFE_FIXTURE), "--fix", "-o", str(out)])
    assert code == 0
    assert out.exists()


@pytest.mark.skipif(not _has(SAFE_FIXTURE), reason="fixture missing")
def test_doctor_cli_json_output(tmp_path, capsys):
    from pyhwpxlib.doctor import main
    code = main([str(SAFE_FIXTURE), "--json"])
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["command"] == "doctor"
    assert "report" in parsed


# ─── validate dual-mode ────────────────────────────────────────────


@pytest.mark.skipif(not _has(MAKERS_HWPX), reason="fixture missing")
def test_validate_compat_passes_for_clean_file():
    from pyhwpxlib.cli import _validate_compat
    result = _validate_compat(str(MAKERS_HWPX))
    assert result["ok"] is True


@pytest.mark.skipif(not _has(MAKERS_HWPX), reason="fixture missing")
def test_validate_strict_passes_for_clean_template():
    """Clean makers template should pass strict (no overflow, valid namespaces)."""
    from pyhwpxlib.cli import _validate_strict
    result = _validate_strict(str(MAKERS_HWPX))
    assert result["ok"] is True
    names = {c["name"] for c in result["checks"]}
    assert "lineseg_textpos_consistency" in names
    assert "namespace_hp" in names


@pytest.mark.skipif(not _has(SAFE_FIXTURE), reason="fixture missing")
def test_validate_strict_flags_overflow():
    """Files with textpos overflow should fail strict but pass compat."""
    from pyhwpxlib.cli import _validate_compat, _validate_strict
    compat = _validate_compat(str(SAFE_FIXTURE))
    strict = _validate_strict(str(SAFE_FIXTURE))
    # compat: file is structurally fine (zip + parse + required) — Hancom opens it
    assert compat["ok"] is True
    # strict: lineseg textpos > text length is a spec violation
    assert strict["ok"] is False
    overflow_check = next(c for c in strict["checks"] if c["name"] == "lineseg_textpos_consistency")
    assert overflow_check["ok"] is False


# ─── write_zip_archive default ────────────────────────────────────


def test_write_zip_archive_returns_fix_count(tmp_path):
    """v0.14.0: write_zip_archive returns the count of linesegs fixed."""
    from pyhwpxlib.package_ops import ZipArchive, write_zip_archive

    # Minimal valid HWPX-ish archive (header + section with overflow)
    overflow_section = (
        b'<?xml version="1.0"?>'
        b'<hp:sec xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        b'<hp:p paraPrIDRef="0" styleIDRef="0">'
        b'<hp:run charPrIDRef="0"><hp:t>hi</hp:t></hp:run>'
        b'<hp:linesegarray>'
        b'<hp:lineseg textpos="0" vertpos="0" vertsize="1000" textheight="1000" '
        b'baseline="850" spacing="600" horzpos="0" horzsize="32864" flags="393216"/>'
        b'<hp:lineseg textpos="50" vertpos="1600" vertsize="1000" textheight="1000" '
        b'baseline="850" spacing="600" horzpos="0" horzsize="32864" flags="393216"/>'
        b'</hp:linesegarray></hp:p></hp:sec>'
    )
    files = {
        "mimetype": b"application/hwp+zip",
        "Contents/section0.xml": overflow_section,
    }
    info_mimetype = zipfile.ZipInfo("mimetype")
    info_mimetype.compress_type = zipfile.ZIP_STORED
    info_section = zipfile.ZipInfo("Contents/section0.xml")
    info_section.compress_type = zipfile.ZIP_DEFLATED
    archive = ZipArchive(infos=[info_mimetype, info_section], files=files)

    # Default (False): no fix, returns 0
    out_default = tmp_path / "default.hwpx"
    n_default = write_zip_archive(str(out_default), archive)
    assert n_default == 0

    # precise: returns count of linesegs fixed
    out_precise = tmp_path / "precise.hwpx"
    n_precise = write_zip_archive(str(out_precise), archive, strip_linesegs="precise")
    assert n_precise == 1
