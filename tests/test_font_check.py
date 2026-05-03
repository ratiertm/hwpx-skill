"""font-check CLI enhancement (v0.18.0) — T-FC-01 ~ T-FC-05.

`--font-map <path>` user-override + status refinement
(ok / alias / fallback / missing) + RhwpEngine-aligned resolution.

These tests run on macOS/Linux/Windows — they don't assume which system
fonts are present. Each test seeds its own override map so the assertions
are deterministic.
"""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from pyhwpxlib import HwpxBuilder


def _make_doc_with_fonts(out: Path, faces: list[str]) -> Path:
    """Build a minimal HWPX file that declares the given font faces."""
    HwpxBuilder().save(str(out))
    # Patch header.xml to inject extra <hh:font face="..."/> entries so the
    # font-check parser sees them. We only need the face attribute to round-
    # trip through the zip — pyhwpxlib does not validate font registry IDs
    # on read for this code path.
    import re
    with zipfile.ZipFile(out) as z:
        header = z.read("Contents/header.xml").decode("utf-8")
        members = {n: z.read(n) for n in z.namelist()}

    extra = "".join(f'<hh:font face="{f}" type="ttf" isEmbedded="0"/>' for f in faces)
    # Insert into the first <hh:fontface> block (any lang). Use a permissive
    # injection point that works regardless of namespace prefix.
    new_header = re.sub(
        r"(<hh:fontface[^>]*>)",
        r"\1" + extra,
        header,
        count=1,
    )
    members["Contents/header.xml"] = new_header.encode("utf-8")

    out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return out


def _run_font_check(hwpx: Path, font_map: Path | None = None) -> dict:
    cmd = [sys.executable, "-m", "pyhwpxlib", "font-check", str(hwpx), "--json"]
    if font_map:
        cmd.extend(["--font-map", str(font_map)])
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode in (0, 1), f"unexpected exit: {res.returncode}\n{res.stderr}"
    # font-check exits 1 when ok=False (some font missing) — that's a valid
    # outcome we want to assert on.
    return json.loads(res.stdout)


# ── T-FC-01: declared 나눔고딕 → status ok (direct hit on bundled) ──


def test_fc_01_nanum_gothic_is_ok(tmp_path: Path):
    doc = _make_doc_with_fonts(tmp_path / "nanum.hwpx", ["나눔고딕"])
    result = _run_font_check(doc)
    nanum = next(f for f in result["fonts"] if f["declared"] == "나눔고딕")
    assert nanum["status"] == "ok"
    assert nanum["source"] == "map"
    assert "NanumGothic" in nanum["resolved"]


# ── T-FC-02: declared 함초롬 → status alias (mapped to bundled, different family) ──


def test_fc_02_hamchorom_is_alias(tmp_path: Path):
    doc = _make_doc_with_fonts(tmp_path / "ham.hwpx", ["함초롬돋움", "함초롬바탕"])
    result = _run_font_check(doc)
    for declared in ("함초롬돋움", "함초롬바탕"):
        f = next(x for x in result["fonts"] if x["declared"] == declared)
        assert f["status"] == "alias", f"{declared}: expected alias, got {f}"
        assert f["source"] == "map"
        assert "NanumGothic" in f["resolved"]


# ── T-FC-03: --font-map override resolves a previously fallback font ──


def test_fc_03_user_font_map_promotes_to_ok(tmp_path: Path):
    doc = _make_doc_with_fonts(tmp_path / "custom.hwpx", ["MyCustomFace"])
    # Without override, MyCustomFace has no entry → fallback or ok depending on
    # platform. With override pointing to a real file, it must be ok+override.
    bundled = Path(__file__).parent.parent / "pyhwpxlib" / "vendor" / "NanumGothic-Regular.ttf"
    assert bundled.exists(), "Bundled NanumGothic missing — test corpus broken"

    map_path = tmp_path / "fonts.json"
    map_path.write_text(json.dumps({"MyCustomFace": str(bundled)}), encoding="utf-8")

    result = _run_font_check(doc, font_map=map_path)
    f = next(x for x in result["fonts"] if x["declared"] == "MyCustomFace")
    # Override sends the declared name to bundled NanumGothic. Since the
    # declared name doesn't include "nanum"/"나눔", the result is alias —
    # which is the honest classification (rendered != declared family).
    assert f["status"] == "alias"
    assert f["source"] == "override"
    assert f["resolved"] == str(bundled)


# ── T-FC-04: override pointing at missing file → status missing ──


def test_fc_04_missing_path_in_override(tmp_path: Path):
    doc = _make_doc_with_fonts(tmp_path / "miss.hwpx", ["FakeFont"])
    map_path = tmp_path / "fonts.json"
    map_path.write_text(json.dumps({"FakeFont": "/no/such/path.ttf"}),
                        encoding="utf-8")
    result = _run_font_check(doc, font_map=map_path)
    f = next(x for x in result["fonts"] if x["declared"] == "FakeFont")
    assert f["status"] == "missing"
    assert f["source"] == "override"
    assert result["ok"] is False  # any missing flips the overall flag


# ── T-FC-05: invalid --font-map JSON → exit 1 with clear message ──


def test_fc_05_invalid_font_map_json(tmp_path: Path):
    doc = _make_doc_with_fonts(tmp_path / "any.hwpx", ["나눔고딕"])
    map_path = tmp_path / "broken.json"
    map_path.write_text("not-json{", encoding="utf-8")
    cmd = [sys.executable, "-m", "pyhwpxlib", "font-check", str(doc),
           "--json", "--font-map", str(map_path)]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 1
    assert "font-map" in res.stdout.lower() or "font-map" in res.stderr.lower() \
        or "json" in (res.stdout + res.stderr).lower()


# ── T-FC-06: --font-map list-type (not object) rejected ──


def test_fc_06_font_map_must_be_object(tmp_path: Path):
    doc = _make_doc_with_fonts(tmp_path / "any.hwpx", ["나눔고딕"])
    map_path = tmp_path / "list.json"
    map_path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    cmd = [sys.executable, "-m", "pyhwpxlib", "font-check", str(doc),
           "--json", "--font-map", str(map_path)]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 1
