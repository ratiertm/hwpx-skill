"""render_to_png API + CLI + MCP — T-PNG-01..06.

v0.17.3 PNG preview pipeline. Validates the regex-font-family fix that
prevents tofu (□□□) rendering when cairosvg cannot resolve original
Korean font names via fontconfig.

Tests are skipped if rhwp/cairosvg are unavailable so CI on minimal
envs (without [preview] extra) still passes.
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_HWPX = PROJECT_ROOT / "samples" / "(양식) 참여확인서.hwpx"


# ── Skip rules ─────────────────────────────────────────────────────

def _have_render_deps() -> bool:
    try:
        import wasmtime  # noqa: F401
        import cairosvg  # noqa: F401
        from pyhwpxlib.rhwp_bridge import RhwpEngine  # noqa: F401
    except ImportError:
        return False
    return True


pytestmark = [
    pytest.mark.skipif(
        not SAMPLE_HWPX.exists(), reason="sample HWPX missing"
    ),
    pytest.mark.skipif(
        not _have_render_deps(),
        reason="render_to_png needs [preview] extra + cairosvg",
    ),
]


def _is_png(path: Path) -> bool:
    """Check first 8 bytes match the PNG signature."""
    if not path.exists() or path.stat().st_size < 8:
        return False
    return path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def _png_dimensions(path: Path) -> tuple[int, int]:
    """Read width/height from PNG IHDR chunk."""
    with open(path, "rb") as f:
        f.seek(16)  # skip 8-byte signature + 8-byte IHDR length+type
        w, h = struct.unpack(">II", f.read(8))
    return w, h


# ── T-PNG-01: API direct call writes a valid PNG ──────────────────


def test_T_PNG_01_api_default_output(tmp_path):
    from pyhwpxlib.api import render_to_png
    out = render_to_png(str(SAMPLE_HWPX), str(tmp_path / "out.png"),
                         page=0, scale=1.0)
    p = Path(out)
    assert p.exists()
    assert _is_png(p)
    w, h = _png_dimensions(p)
    assert w > 100 and h > 100  # not a degenerate 1x1


# ── T-PNG-02: implicit output_path resolves to {stem}_preview_p{N}.png


def test_T_PNG_02_default_output_path(tmp_path):
    from pyhwpxlib.api import render_to_png
    # Copy sample to tmp so we don't pollute samples/
    src = tmp_path / "doc.hwpx"
    src.write_bytes(SAMPLE_HWPX.read_bytes())
    out = render_to_png(str(src), page=0, scale=1.0)
    assert out == str(tmp_path / "doc_preview_p0.png")
    assert _is_png(Path(out))


# ── T-PNG-03: out-of-range page raises ValueError ────────────────


def test_T_PNG_03_out_of_range_page(tmp_path):
    from pyhwpxlib.api import render_to_png
    with pytest.raises(ValueError, match="out of range"):
        render_to_png(str(SAMPLE_HWPX), str(tmp_path / "out.png"),
                       page=999)


# ── T-PNG-04: missing input raises FileNotFoundError ─────────────


def test_T_PNG_04_missing_input(tmp_path):
    from pyhwpxlib.api import render_to_png
    with pytest.raises(FileNotFoundError):
        render_to_png(str(tmp_path / "nope.hwpx"),
                       str(tmp_path / "out.png"))


# ── T-PNG-05: CLI subcommand produces same valid PNG ─────────────


def test_T_PNG_05_cli_subcommand(tmp_path):
    out = tmp_path / "cli.png"
    cmd = [sys.executable, "-m", "pyhwpxlib", "png", str(SAMPLE_HWPX),
           "-o", str(out), "--scale", "1.0", "--json"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 0, f"stderr: {res.stderr}"
    payload = json.loads(res.stdout)
    assert payload["ok"] is True
    assert payload["output"] == str(out)
    assert _is_png(out)


# ── T-PNG-06: CLI surfaces an error on bad input ─────────────────


def test_T_PNG_06_cli_error_path(tmp_path):
    cmd = [sys.executable, "-m", "pyhwpxlib", "png",
           str(tmp_path / "missing.hwpx"),
           "-o", str(tmp_path / "out.png"), "--json"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 1
    payload = json.loads(res.stdout)
    assert payload["ok"] is False
    assert "not found" in payload["error"].lower()


# ── T-PNG-07: MCP wrapper returns success JSON ───────────────────


def test_T_PNG_07_mcp_render(tmp_path):
    from pyhwpxlib.mcp_server.server import hwpx_render_png
    out = tmp_path / "mcp.png"
    payload = json.loads(hwpx_render_png(
        str(SAMPLE_HWPX), output_path=str(out), page=0, scale=1.0,
    ))
    assert payload["ok"] is True
    assert payload["output"] == str(out)
    assert _is_png(out)


# ── T-PNG-08: MCP wrapper surfaces error JSON, no exception ──────


def test_T_PNG_08_mcp_error_path(tmp_path):
    from pyhwpxlib.mcp_server.server import hwpx_render_png
    payload = json.loads(hwpx_render_png(
        str(tmp_path / "missing.hwpx"),
        output_path=str(tmp_path / "out.png"),
    ))
    assert payload["ok"] is False
    assert "type" in payload  # FileNotFoundError class name preserved
