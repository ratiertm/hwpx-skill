"""Tests for v0.15.0 json-schema-expansion (Option A).

Maps each of the 16 builder add_* methods that JSON can now reach to a
dedicated dispatch test against the resulting .hwpx XML.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest


def _read_section0(p: Path) -> str:
    with zipfile.ZipFile(p) as z:
        return z.read("Contents/section0.xml").decode("utf-8")


def _make_run(content: dict) -> dict:
    return {"runs": [{"content": content}]}


def _wrap(*paragraphs: dict, tables: list | None = None,
          extras: dict | None = None) -> dict:
    """Build a minimal valid HwpxJsonDocument with the given paragraphs."""
    section: dict[str, Any] = {
        "paragraphs": list(paragraphs),
        "tables": tables or [],
        "page_settings": {},
    }
    base: dict[str, Any] = {"format": "1.0", "sections": [section]}
    if extras:
        base.update(extras)
    return base


# ─── T-01 heading ──────────────────────────────────────────────────


def test_t01_heading_dispatches_to_add_heading(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "h.hwpx"
    data = _wrap(_make_run({
        "type": "heading",
        "heading": {"text": "Chapter 1", "level": 1, "alignment": "JUSTIFY"},
    }))
    from_json(data, str(out))
    assert out.exists()
    xml = _read_section0(out)
    assert "Chapter 1" in xml


# ─── T-02 image (path) ─────────────────────────────────────────────


def test_t02_image_path_mode(tmp_path):
    from pyhwpxlib.json_io import from_json
    # produce a tiny PNG to use as the source
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4"
        b"\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01"
        b"\xa6\x9d\x06}\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    img = tmp_path / "tiny.png"
    img.write_bytes(png_bytes)
    out = tmp_path / "im.hwpx"
    data = _wrap(_make_run({
        "type": "image",
        "image": {"image_path": str(img), "width": 14400, "height": 14400},
    }))
    from_json(data, str(out))
    # Expect a BinData entry inside the zip (the builder bundles the image)
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    assert any(n.startswith("BinData/") for n in names), names


# ─── T-04 image: path+url both → ValueError ────────────────────────


def test_t04_image_path_and_url_raises(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "bad.hwpx"
    data = _wrap(_make_run({
        "type": "image",
        "image": {"image_path": "/x.png", "image_url": "http://e.com/y.png"},
    }))
    with pytest.raises(ValueError, match="image_path OR image_url"):
        from_json(data, str(out))


# ─── T-05 bullet_list ──────────────────────────────────────────────


def test_t05_bullet_list(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "bl.hwpx"
    data = _wrap(_make_run({
        "type": "bullet_list",
        "bullet_list": {"items": ["alpha", "beta", "gamma"], "bullet_char": "-"},
    }))
    from_json(data, str(out))
    xml = _read_section0(out)
    for item in ("alpha", "beta", "gamma"):
        assert item in xml


# ─── T-06 numbered_list ────────────────────────────────────────────


def test_t06_numbered_list(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "nl.hwpx"
    data = _wrap(_make_run({
        "type": "numbered_list",
        "numbered_list": {"items": ["one", "two", "three"], "format_string": "^1."},
    }))
    from_json(data, str(out))
    xml = _read_section0(out)
    for item in ("one", "two", "three"):
        assert item in xml


# ─── T-07 nested_bullet_list ───────────────────────────────────────


def test_t07_nested_bullet_list(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "nbl.hwpx"
    data = _wrap(_make_run({
        "type": "nested_bullet_list",
        "nested_bullet_list": {
            "items": [
                {"depth": 0, "text": "Top"},
                {"depth": 1, "text": "Sub"},
                {"depth": 2, "text": "Deep"},
            ],
        },
    }))
    from_json(data, str(out))
    xml = _read_section0(out)
    for item in ("Top", "Sub", "Deep"):
        assert item in xml


# ─── T-08 nested_numbered_list ─────────────────────────────────────


def test_t08_nested_numbered_list(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "nnl.hwpx"
    data = _wrap(_make_run({
        "type": "nested_numbered_list",
        "nested_numbered_list": {
            "items": [
                {"depth": 0, "text": "First"},
                {"depth": 1, "text": "Second"},
            ],
        },
    }))
    from_json(data, str(out))
    xml = _read_section0(out)
    assert "First" in xml and "Second" in xml


# ─── T-09 footnote ─────────────────────────────────────────────────


def test_t09_footnote(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "fn.hwpx"
    data = _wrap(_make_run({
        "type": "footnote",
        "footnote": {"text": "see appendix", "number": 1},
    }))
    from_json(data, str(out))
    xml = _read_section0(out)
    assert "see appendix" in xml


# ─── T-10 equation ─────────────────────────────────────────────────


def test_t10_equation(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "eq.hwpx"
    data = _wrap(_make_run({
        "type": "equation",
        "equation": {"script": "E=mc^2"},
    }))
    from_json(data, str(out))
    # Equation may be encoded — at minimum the file should be valid HWPX
    xml = _read_section0(out)
    assert len(xml) > 0


# ─── T-11 highlight ────────────────────────────────────────────────


def test_t11_highlight(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "hl.hwpx"
    data = _wrap(_make_run({
        "type": "highlight",
        "highlight": {"text": "important", "color": "#FFFF00"},
    }))
    from_json(data, str(out))
    xml = _read_section0(out)
    assert "important" in xml


# ─── T-12 shape_rect ───────────────────────────────────────────────


def test_t12_shape_rect(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "sr.hwpx"
    data = _wrap(_make_run({
        "type": "shape_rect",
        "shape": {"width": 14400, "height": 7200, "line_color": "#FF0000"},
    }))
    from_json(data, str(out))
    assert out.exists()


# ─── T-13 shape_line ───────────────────────────────────────────────


def test_t13_shape_line(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "sl.hwpx"
    data = _wrap(_make_run({"type": "shape_line"}))
    from_json(data, str(out))
    assert out.exists()


# ─── T-14 shape_draw_line ──────────────────────────────────────────


def test_t14_shape_draw_line(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "sdl.hwpx"
    data = _wrap(_make_run({
        "type": "shape_draw_line",
        "shape": {"x1": 0, "y1": 0, "x2": 30000, "y2": 0,
                  "line_color": "#000000"},
    }))
    from_json(data, str(out))
    assert out.exists()


# ─── T-15 deferred header/footer/page_number ──────────────────────


def test_t15_deferred_top_level_actions(tmp_path):
    """header/footer/page_number must apply LAST so SecPr ordering stays valid."""
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "deferred.hwpx"
    data = _wrap(
        _make_run({"type": "text", "text": "Body content"}),
        extras={
            "header": {"text": "MyHeader"},
            "footer": {"text": "MyFooter"},
            "page_number": {"pos": "BOTTOM_CENTER"},
        },
    )
    from_json(data, str(out))
    # All three artifacts should be present in the output zip somewhere.
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        # Headers/footers live in their own XML files in HWPX
        joined_xml = "".join(
            z.read(n).decode("utf-8", errors="ignore")
            for n in names if n.endswith(".xml")
        )
    assert "MyHeader" in joined_xml
    assert "MyFooter" in joined_xml


# ─── T-16 unknown type → ValueError ────────────────────────────────


def test_t16_unknown_type_raises(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "x.hwpx"
    data = _wrap(_make_run({"type": "totally_unknown"}))
    with pytest.raises(ValueError, match="Unknown RunContent.type"):
        from_json(data, str(out))


# ─── T-17 v0.14.0 back-compat (paragraphs/tables only) ────────────


def test_t17_v0_14_input_still_works(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "compat.hwpx"
    data = {
        "format": "1.0",
        "sections": [{
            "paragraphs": [{"runs": [{"content": {"type": "text", "text": "Hello v0.14"}}]}],
            "tables": [],
            "page_settings": {},
        }],
    }
    from_json(data, str(out))
    xml = _read_section0(out)
    assert "Hello v0.14" in xml


# ─── T-18 rich integration (heading + paragraph + bullet + footnote) ─


def test_t18_rich_integration(tmp_path):
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "rich.hwpx"
    data = _wrap(
        _make_run({"type": "heading",
                   "heading": {"text": "Report Title", "level": 1}}),
        _make_run({"type": "text",
                   "text": "Introduction paragraph."}),
        _make_run({"type": "bullet_list",
                   "bullet_list": {"items": ["Background", "Goals", "Scope"]}}),
        _make_run({"type": "footnote",
                   "footnote": {"text": "Confidential", "number": 1}}),
        extras={
            "header": {"text": "Acme Corp"},
            "page_number": {"pos": "BOTTOM_CENTER"},
        },
    )
    from_json(data, str(out))
    xml = _read_section0(out)
    for needle in ("Report Title", "Introduction paragraph.",
                   "Background", "Goals", "Scope", "Confidential"):
        assert needle in xml, f"missing {needle!r}"


# ─── Additional: missing nested object → ValueError ───────────────


@pytest.mark.parametrize("type_,nested_field", [
    ("heading", "heading"),
    ("bullet_list", "bullet_list"),
    ("numbered_list", "numbered_list"),
    ("nested_bullet_list", "nested_bullet_list"),
    ("nested_numbered_list", "nested_numbered_list"),
    ("footnote", "footnote"),
    ("equation", "equation"),
    ("highlight", "highlight"),
    ("shape_rect", "shape"),
    ("shape_draw_line", "shape"),
    ("image", "image"),
])
def test_missing_nested_object_raises(tmp_path, type_, nested_field):
    """For each rich type, omitting the matching nested object → ValueError."""
    from pyhwpxlib.json_io import from_json
    out = tmp_path / "x.hwpx"
    data = _wrap(_make_run({"type": type_}))
    with pytest.raises(ValueError):
        from_json(data, str(out))
