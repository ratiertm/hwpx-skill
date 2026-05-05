"""Regression tests for render_to_png byte-identical output (PNG sha256).

Design Ref: render-perf-opt.design.md §8.4 — R-01 anchor + bonus parallel
SVG byte-equality guard. The anchor is the contract that caching changes
must never break.
"""
from __future__ import annotations

import hashlib
import os

import pytest


pytest.importorskip("wasmtime")
pytest.importorskip("cairosvg")


ANCHOR_INPUT = "Test/output/template_fill_makers.hwpx"
# Captured 2026-05-05 from pyhwpxlib 0.17.3 baseline (TODO.md and design doc).
ANCHOR_SHA256 = "d4501eeed09bc3d4d6c45a887523fdec913f428bdfee18f3e8c2570a793f2c05"
ANCHOR_BYTES = 85966


@pytest.fixture(scope="module")
def _anchor_input():
    if not os.path.exists(ANCHOR_INPUT):
        pytest.skip(f"regression sample missing: {ANCHOR_INPUT}")
    return ANCHOR_INPUT


# --- R-01: byte-identical PNG against the captured anchor ------------------

def test_render_anchor_sha256(tmp_path, _anchor_input):
    from pyhwpxlib.api import render_to_png
    out = render_to_png(_anchor_input, str(tmp_path / "anchor.png"),
                        page=0, scale=1.0, register_fonts=False)
    data = open(out, "rb").read()
    assert hashlib.sha256(data).hexdigest() == ANCHOR_SHA256, (
        "PNG sha256 anchor regression — caching layer must produce byte-identical output"
    )
    assert len(data) == ANCHOR_BYTES


# --- R-02: render twice in same process → identical bytes ------------------

def test_render_consecutive_byte_identical(tmp_path, _anchor_input):
    from pyhwpxlib.api import render_to_png
    out1 = render_to_png(_anchor_input, str(tmp_path / "a.png"),
                         page=0, scale=1.0, register_fonts=False)
    out2 = render_to_png(_anchor_input, str(tmp_path / "b.png"),
                         page=0, scale=1.0, register_fonts=False)
    assert open(out1, "rb").read() == open(out2, "rb").read()


# --- R-03: render with external engine → identical bytes ------------------

def test_render_with_engine_di_byte_identical(tmp_path, _anchor_input):
    from pyhwpxlib.api import render_to_png
    from pyhwpxlib.rhwp_bridge import RhwpEngine, NANUM_GOTHIC_REGULAR

    font_map = {k: NANUM_GOTHIC_REGULAR for k in
                ("함초롬바탕", "함초롬돋움", "휴먼명조", "바탕", "Batang",
                 "NanumGothic", "나눔고딕", "serif", "sans-serif")}

    out_default = render_to_png(_anchor_input, str(tmp_path / "d.png"),
                                page=0, scale=1.0, register_fonts=False)
    out_di = render_to_png(_anchor_input, str(tmp_path / "e.png"),
                           page=0, scale=1.0, register_fonts=False,
                           engine=RhwpEngine(font_map=font_map))
    assert hashlib.sha256(open(out_default, "rb").read()).hexdigest() == ANCHOR_SHA256
    assert hashlib.sha256(open(out_di, "rb").read()).hexdigest() == ANCHOR_SHA256


# --- T-PARALLEL: render_all_svgs_parallel byte-equals serial ---------------

def test_render_pages_to_png_byte_identical(tmp_path, _anchor_input):
    """Bonus: render_pages_to_png (parallel SVG + parallel cairosvg) must
    produce PNGs byte-identical to a sequential render_to_png loop. The
    function exists as a user-contributed performance helper; we lock in
    its accuracy contract here. Out of the original Plan scope but in the
    public API surface, so a regression here would silently break batch
    callers."""
    from pyhwpxlib.api import render_to_png, render_pages_to_png

    seq_dir = tmp_path / "seq"
    par_dir = tmp_path / "par"
    seq_dir.mkdir()
    par_dir.mkdir()

    # Sequential — same parameters render_pages_to_png will use.
    seq = render_to_png(_anchor_input, str(seq_dir / "p0.png"),
                        page=0, scale=1.0, register_fonts=False)
    par_paths = render_pages_to_png(_anchor_input, str(par_dir),
                                    scale=1.0, register_fonts=False)
    assert len(par_paths) >= 1
    seq_sha = hashlib.sha256(open(seq, "rb").read()).hexdigest()
    par_sha = hashlib.sha256(open(par_paths[0], "rb").read()).hexdigest()
    assert seq_sha == par_sha, (
        f"render_pages_to_png produced different bytes than render_to_png "
        f"(seq={seq_sha[:12]} par={par_sha[:12]})"
    )
    # Anchor still holds.
    assert seq_sha == ANCHOR_SHA256


def test_parallel_svg_equals_serial(_anchor_input):
    """Bonus: the new render_all_svgs_parallel method must produce the same
    SVG strings as the serial render_all_svgs. This is out-of-scope for the
    Plan but the method already exists, so we guard it from regression."""
    from pyhwpxlib.rhwp_bridge import RhwpEngine

    engine = RhwpEngine()
    doc = engine.load(_anchor_input)
    serial = doc.render_all_svgs(embed_fonts=True)
    parallel = doc.render_all_svgs_parallel(embed_fonts=True)
    assert serial == parallel, "parallel SVG batch must byte-match serial output"
