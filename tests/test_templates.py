"""Tests for pyhwpxlib.templates module."""
from __future__ import annotations

import json
import os
import zipfile
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAKERS_SAMPLE = PROJECT_ROOT / "samples" / "전정_Makers_결과보고서_양식.hwpx"
MAKERS_HWP = PROJECT_ROOT / "samples" / "3. 전정 Makers 프로젝트 중간,최종 결과보고서 양식.hwp"


def _has(p): return p.exists()


# ─── slugify ────────────────────────────────────────────────────────


def test_slugify_known_label():
    from pyhwpxlib.templates.slugify import slugify
    assert slugify("팀명") == "team_name"
    assert slugify("팀  명") == "team_name"          # whitespace collapsed
    assert slugify("성명") == "name"
    assert slugify("프로젝트명") == "project_name"


def test_slugify_unknown_falls_back_to_field_index():
    from pyhwpxlib.templates.slugify import slugify
    assert slugify("이상한라벨", fallback_index=7).startswith("field_")


def test_slugify_ascii_input_passes_through():
    from pyhwpxlib.templates.slugify import slugify
    assert slugify("Team Name") == "team_name"


def test_label_to_key_collision_disambiguates():
    from pyhwpxlib.templates.slugify import label_to_key
    used = set()
    a = label_to_key("성명", used)
    b = label_to_key("성명", used)
    c = label_to_key("성명", used)
    assert a == "name"
    assert b == "name_2"
    assert c == "name_3"


# ─── resolver ───────────────────────────────────────────────────────


def test_user_dir_respects_xdg(tmp_path, monkeypatch):
    from pyhwpxlib.templates.resolver import user_templates_dir
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert user_templates_dir() == tmp_path / "pyhwpxlib" / "templates"


def test_skill_dir_resolves_to_repo():
    from pyhwpxlib.templates.resolver import skill_templates_dir
    p = skill_templates_dir()
    assert p.is_dir()
    assert (p / "makers_project_report.hwpx").exists()


def test_resolve_user_wins_over_skill(tmp_path, monkeypatch):
    from pyhwpxlib.templates.resolver import resolve_template_path
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    user_dir = tmp_path / "pyhwpxlib" / "templates"
    user_dir.mkdir(parents=True)
    fake_user = user_dir / "makers_project_report.hwpx"
    fake_user.write_bytes(b"x")
    found = resolve_template_path("makers_project_report")
    assert found == fake_user  # user dir wins


def test_resolve_falls_back_to_skill(tmp_path, monkeypatch):
    from pyhwpxlib.templates.resolver import resolve_template_path
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    found = resolve_template_path("makers_project_report")
    assert found is not None
    assert "skill/templates" in str(found)


# ─── auto_schema ────────────────────────────────────────────────────


@pytest.mark.skipif(not _has(MAKERS_SAMPLE), reason="makers fixture missing")
def test_auto_schema_yields_two_tables():
    from pyhwpxlib.templates.auto_schema import generate_schema_from_hwpx
    schema = generate_schema_from_hwpx(MAKERS_SAMPLE, name="makers_auto")
    assert schema["name"] == "makers_auto"
    assert schema["auto_generated"] is True
    assert len(schema["tables"]) == 2


@pytest.mark.skipif(not _has(MAKERS_SAMPLE), reason="makers fixture missing")
def test_auto_schema_extracts_known_labels():
    """Single fields keep bare slugs; participants get member_N_* via grid detection."""
    from pyhwpxlib.templates.auto_schema import generate_schema_from_hwpx
    schema = generate_schema_from_hwpx(MAKERS_SAMPLE, name="makers_auto")
    keys = {f["key"] for tbl in schema["tables"] for f in tbl["fields"]}
    # Single-row labels (not part of repeating grid) keep bare slugs.
    single_expected = {"team_name", "project_name", "period", "report_date"}
    assert single_expected <= keys, f"missing single keys: {single_expected - keys}"
    # Grid sub-region produces member_N_<col_header> for 4 participants × 4 fields.
    grid_expected = {f"member_{n}_{f}"
                     for n in (1, 2, 3, 4)
                     for f in ("name", "dept", "student_id", "signature")}
    assert grid_expected <= keys, f"missing grid keys: {grid_expected - keys}"


# ─── add + fill (end-to-end with isolated XDG) ─────────────────────


@pytest.mark.skipif(not _has(MAKERS_HWP), reason="makers HWP missing")
def test_add_hwp_then_fill_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from pyhwpxlib.templates import add as tpl_add, fill as tpl_fill, show as tpl_show

    info = tpl_add(str(MAKERS_HWP), name="makers_test")
    assert info["fields"] > 0
    assert info["tables"] == 2
    assert info["source"] == "user"
    assert Path(info["hwpx_path"]).exists()
    assert Path(info["schema_path"]).exists()

    schema = tpl_show("makers_test")
    assert schema["name"] == "makers_test"
    assert schema["auto_generated"] is True

    out = tmp_path / "filled.hwpx"
    summary = tpl_fill("makers_test", {
        "team_name": "Test Alpha",
        "project_name": "WebAR Guide",
        "period": "2026.03.01. ~ 2026.06.30.",
    }, out)
    assert "team_name" in summary["filled"]
    assert "project_name" in summary["filled"]
    assert out.exists()
    # output passes precise fix automatically (no textpos overflow)
    from pyhwpxlib.postprocess import count_textpos_overflow
    with zipfile.ZipFile(out) as z:
        xml = z.read("Contents/section0.xml").decode("utf-8")
    assert count_textpos_overflow(xml) == 0


@pytest.mark.skipif(not _has(MAKERS_SAMPLE), reason="makers HWPX missing")
def test_add_hwpx_skips_conversion(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    from pyhwpxlib.templates import add as tpl_add
    info = tpl_add(str(MAKERS_SAMPLE), name="makers_via_hwpx")
    assert info["tables"] == 2
    assert Path(info["hwpx_path"]).exists()


def test_add_invalid_extension_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    bad = tmp_path / "x.docx"
    bad.write_bytes(b"x")
    from pyhwpxlib.templates import add as tpl_add
    with pytest.raises(ValueError):
        tpl_add(bad, name="bad")


# ─── list_templates ────────────────────────────────────────────────


def test_list_templates_includes_skill_makers(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))  # empty user
    from pyhwpxlib.templates import list_templates
    items = list_templates()
    names = {it["name"] for it in items}
    assert "makers_project_report" in names
    skill_items = [it for it in items if it["name"] == "makers_project_report"]
    assert skill_items[0]["source"] == "skill"
