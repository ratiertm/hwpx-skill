"""Module 1 (cache layer) unit tests.

Design Ref: render-perf-opt.design.md §8.2 — U-01..U-05 + parallel safety.
Plan SC: FR-01 (engine), FR-02 (measurer LRU), FR-03 (font guard), FR-04 (DI).
"""
from __future__ import annotations

import os
import threading

import pytest


# Skip the whole module if wasmtime is missing — the bridge will raise on import.
wasmtime = pytest.importorskip("wasmtime")


def _reset_caches():
    """Clear all module-level caches between tests for isolation."""
    from pyhwpxlib import rhwp_bridge as rb
    rb._ENGINE_CACHE.clear()
    rb._ENGINE_CACHE_PID = -1
    rb._measure_text_cached.cache_clear()


# --- T-CACHE-01 (U-01): Engine module-singleton hits on repeat -------------

def test_engine_singleton_hit():
    _reset_caches()
    from pyhwpxlib.rhwp_bridge import RhwpEngine, _ENGINE_CACHE

    e1 = RhwpEngine()
    e2 = RhwpEngine()
    # The engine and module objects are the same instance after the cache hit.
    assert e1._engine is e2._engine
    assert e1._module is e2._module
    # But Store/Linker/Instance are per-call (not shared mutable state).
    assert e1._store is not e2._store
    assert len(_ENGINE_CACHE) == 1


# --- T-CACHE-02 (U-02): PID change invalidates engine cache ----------------

def test_engine_pid_invalidate(monkeypatch):
    _reset_caches()
    from pyhwpxlib import rhwp_bridge as rb

    e1 = rb.RhwpEngine()
    fake_pid = os.getpid() + 1
    monkeypatch.setattr(os, "getpid", lambda: fake_pid)
    e2 = rb.RhwpEngine()
    assert e1._engine is not e2._engine, "fork detection must rebuild engine"
    assert rb._ENGINE_CACHE_PID == fake_pid


# --- T-CACHE-03 (U-03): _measure_text_cached LRU hit on repeat -------------

def test_measurer_lru_hit():
    _reset_caches()
    from pyhwpxlib.rhwp_bridge import _measure_text_cached, _KOREAN_FALLBACK

    _measure_text_cached(_KOREAN_FALLBACK, 14, "안녕", False)
    _measure_text_cached(_KOREAN_FALLBACK, 14, "안녕", False)
    info = _measure_text_cached.cache_info()
    assert info.hits == 1, f"expected 1 hit, got {info.hits}"
    assert info.misses == 1


# --- T-CACHE-04 (U-04): distinct font_path → distinct cache entries --------

def test_measurer_distinct_fonts():
    _reset_caches()
    from pyhwpxlib.rhwp_bridge import _measure_text_cached, _KOREAN_FALLBACK, _LATIN_FALLBACK

    if _KOREAN_FALLBACK == _LATIN_FALLBACK:
        pytest.skip("Korean and Latin fallback resolve to the same path on this host")
    _measure_text_cached(_KOREAN_FALLBACK, 14, "ABC", False)
    _measure_text_cached(_LATIN_FALLBACK, 14, "ABC", False)
    info = _measure_text_cached.cache_info()
    assert info.misses == 2, "different font_path must miss"
    assert info.hits == 0


# --- T-CACHE-05 (U-05): _register_bundled_fonts is idempotent --------------

def test_fonts_registered_idempotent(monkeypatch, tmp_path):
    """Second call with the same font_dir returns immediately without filesystem I/O."""
    import pyhwpxlib.api as api_mod

    # Reset flag so we can observe the transition.
    api_mod._FONTS_REGISTERED = False
    api_mod._FONTS_REGISTERED_DIR = None

    target = str(tmp_path / "fonts")
    api_mod._register_bundled_fonts(target)
    assert api_mod._FONTS_REGISTERED is True
    assert api_mod._FONTS_REGISTERED_DIR == target

    # Now patch shutil.copy to error if called — second call must NOT touch FS.
    import shutil
    called = []
    def boom(*a, **kw):
        called.append(a)
        raise AssertionError("shutil.copy must not be called on second invocation")
    monkeypatch.setattr(shutil, "copy", boom)
    result = api_mod._register_bundled_fonts(target)
    assert result == target
    assert called == [], "second call must be a no-op"


# --- T-CACHE-06: render_to_png(engine=) DI bypasses RhwpEngine() construction

def test_render_to_png_di(tmp_path, monkeypatch):
    """When engine= is provided, render_to_png must not instantiate a new RhwpEngine."""
    pytest.importorskip("cairosvg")
    from pyhwpxlib.api import render_to_png
    from pyhwpxlib.rhwp_bridge import RhwpEngine, NANUM_GOTHIC_REGULAR

    src = "Test/output/template_fill_makers.hwpx"
    if not os.path.exists(src):
        pytest.skip(f"regression sample not present: {src}")

    font_map = {k: NANUM_GOTHIC_REGULAR for k in
                ("함초롬바탕", "함초롬돋움", "휴먼명조", "바탕", "Batang",
                 "NanumGothic", "나눔고딕", "serif", "sans-serif")}
    ext_engine = RhwpEngine(font_map=font_map)

    # Sentinel: any new RhwpEngine() construction inside render_to_png must blow up.
    constructed = []
    real_init = RhwpEngine.__init__

    def tripwire(self, *a, **kw):
        constructed.append(1)
        real_init(self, *a, **kw)

    monkeypatch.setattr(RhwpEngine, "__init__", tripwire)

    out = render_to_png(src, str(tmp_path / "out.png"), page=0, scale=1.0,
                        register_fonts=False, engine=ext_engine)
    assert os.path.exists(out)
    assert constructed == [], "render_to_png must reuse the supplied engine, not construct one"


# --- T-CACHE-07: LRU is thread-safe under concurrent access ----------------

def test_measurer_lru_thread_safe():
    _reset_caches()
    from pyhwpxlib.rhwp_bridge import _measure_text_cached, _KOREAN_FALLBACK

    errors = []
    def worker():
        try:
            for _ in range(50):
                _measure_text_cached(_KOREAN_FALLBACK, 12, "테스트", False)
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert errors == []
    info = _measure_text_cached.cache_info()
    # 8 threads * 50 iterations - 1 miss = at least 399 hits
    assert info.hits >= 8 * 50 - 1
