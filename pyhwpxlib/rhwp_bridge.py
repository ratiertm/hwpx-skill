"""HWP/HWPX → SVG renderer via rhwp WASM.

Loads the rhwp WebAssembly binary (built from the `rhwp` Rust project by
Edward Kim, MIT licensed) and exposes a minimal Python API for rendering
HWP/HWPX documents to SVG strings.

This module is intended for **preview** use cases — e.g., letting an LLM
inspect a generated HWPX without having to ship a full native renderer.

The renderer keeps one WASM instance per engine; the instance is not
thread-safe and should be used from a single thread.

Dependencies
------------
- wasmtime: required (``pip install wasmtime``)
- Pillow:    optional. Enables accurate text advance-width measurement.
             Without Pillow a simple em-based heuristic is used.

WASM binary resolution order
----------------------------
1. ``RHWP_WASM_PATH`` environment variable (explicit override).
2. Bundled package resource (``pyhwpxlib/vendor/rhwp_bg.wasm``).
3. Installed VS Code extension ``edwardkim.rhwp-vscode-*`` (development fallback).
4. Raises ``RhwpWasmNotFoundError`` with an install hint.
"""
from __future__ import annotations

import ctypes
import os
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import wasmtime
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "pyhwpxlib.rhwp_bridge requires `wasmtime`. "
        "Install with `pip install pyhwpxlib[preview]`."
    ) from e

# importlib.resources.files() is standard on 3.9+; on 3.8 use the backport if present.
if sys.version_info >= (3, 9):
    from importlib.resources import files as _resource_files, as_file as _resource_as_file
else:  # pragma: no cover
    try:
        from importlib_resources import files as _resource_files, as_file as _resource_as_file  # type: ignore
    except ImportError:
        _resource_files = None  # type: ignore
        _resource_as_file = None  # type: ignore

try:
    from PIL import ImageFont
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

try:
    from fontTools.ttLib import TTFont
    from fontTools.subset import Subsetter, Options as SubsetOptions
    _HAS_FONTTOOLS = True
except ImportError:
    _HAS_FONTTOOLS = False


class RhwpWasmNotFoundError(RuntimeError):
    """Raised when the rhwp WASM binary cannot be located."""


class RhwpError(RuntimeError):
    """Generic rhwp WASM error (load, render, etc.)."""


# ---------------------------------------------------------------------------
# WASM binary resolution
# ---------------------------------------------------------------------------

def _find_wasm() -> Path:
    """Resolve the rhwp WASM binary path.

    Resolution order:
    1. ``RHWP_WASM_PATH`` environment variable (explicit override).
    2. Bundled package resource (``pyhwpxlib/vendor/rhwp_bg.wasm``).
    3. VS Code extension installation (development fallback).
    4. Raise :class:`RhwpWasmNotFoundError` with an install hint.
    """
    # Step 1: explicit env var
    env = os.environ.get("RHWP_WASM_PATH")
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p
        raise RhwpWasmNotFoundError(
            f"RHWP_WASM_PATH is set but not a file: {p}"
        )

    # Step 2: bundled package resource (normal case for PyPI installs)
    if _resource_files is not None and _resource_as_file is not None:
        try:
            resource = _resource_files("pyhwpxlib.vendor") / "rhwp_bg.wasm"
            with _resource_as_file(resource) as real_path:
                if Path(real_path).is_file():
                    return Path(real_path)
        except (ModuleNotFoundError, FileNotFoundError):
            pass

    # Step 3: VS Code extension fallback (development)
    ext_root = Path.home() / ".vscode/extensions"
    if ext_root.is_dir():
        candidates = sorted(
            ext_root.glob("edwardkim.rhwp-vscode-*/dist/media/rhwp_bg.wasm")
        )
        if candidates:
            return candidates[-1]  # latest version by sort

    raise RhwpWasmNotFoundError(
        "rhwp WASM binary not found. "
        "Install with: pip install pyhwpxlib[preview]\n"
        "Or set RHWP_WASM_PATH to a valid rhwp_bg.wasm file."
    )


# ---------------------------------------------------------------------------
# Text measurement
# ---------------------------------------------------------------------------

# macOS system font fallback. Extend this mapping to taste.
_DEFAULT_FONT_MAP: dict[str, str] = {
    "apple sd gothic neo": "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "helvetica": "/System/Library/Fonts/Helvetica.ttc",
    "arial": "/System/Library/Fonts/Supplemental/Arial.ttf",
    "times new roman": "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "courier new": "/System/Library/Fonts/Supplemental/Courier New.ttf",
}
_KOREAN_FALLBACK = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
_LATIN_FALLBACK = "/System/Library/Fonts/Helvetica.ttc"


class _TextMeasurer:
    """Measures text width given a CSS-style font string like
    ``bold 1000px "HY견고딕", 'Malgun Gothic', sans-serif``.
    Uses Pillow if available, otherwise returns a char-count heuristic.
    """

    def __init__(self, font_map: Optional[dict[str, str]] = None):
        self._map = dict(_DEFAULT_FONT_MAP)
        if font_map:
            self._map.update({k.lower(): v for k, v in font_map.items()})
        self._cache: dict[tuple[str, int], object] = {}  # (path, size_int) -> ImageFont

    @staticmethod
    def _parse_css_font(css: str) -> tuple[list[str], float, bool]:
        s = css.strip()
        is_bold = bool(re.search(r"\bbold\b", s, re.IGNORECASE))
        s2 = re.sub(r"\b(bold|italic|oblique|normal)\b", "", s, flags=re.IGNORECASE).strip()
        m = re.search(r"([\d.]+)\s*px", s2)
        size = float(m.group(1)) if m else 16.0
        if m:
            s2 = s2[m.end():].lstrip(" ,")
        fams = [f.strip().strip("\"'").lower() for f in s2.split(",") if f.strip()]
        return fams, size, is_bold

    def _resolve_path(self, families: list[str]) -> str:
        for fam in families:
            path = self._map.get(fam)
            if path and os.path.exists(path):
                return path
        # Korean fallback if any Korean keyword in family list
        for fam in families:
            if any(k in fam for k in ("gothic", "myung", "batang", "nanum",
                                       "noto", "pretendard", "hy", "한", "맑",
                                       "굴", "바탕", "함초")):
                if os.path.exists(_KOREAN_FALLBACK):
                    return _KOREAN_FALLBACK
        if os.path.exists(_LATIN_FALLBACK):
            return _LATIN_FALLBACK
        return _KOREAN_FALLBACK  # final resort

    def measure(self, css_font: str, text: str) -> float:
        if not text:
            return 0.0
        fams, size, _bold = self._parse_css_font(css_font)

        if not _HAS_PIL:
            # Heuristic: 1.0em for CJK, 0.5em for ASCII/punctuation
            w = 0.0
            for ch in text:
                cp = ord(ch)
                if cp > 0x2E80 or cp == 0x3000:
                    w += size
                else:
                    w += size * 0.5
            return w

        path = self._resolve_path(fams)
        isize = max(1, int(round(size)))
        key = (path, isize)
        ft = self._cache.get(key)
        if ft is None:
            try:
                ft = ImageFont.truetype(path, isize)
            except Exception:
                ft = ImageFont.truetype(_KOREAN_FALLBACK, isize)
            self._cache[key] = ft
        try:
            w = ft.getlength(text)  # type: ignore[attr-defined]
        except AttributeError:  # very old Pillow
            bbox = ft.getbbox(text)  # type: ignore[attr-defined]
            w = bbox[2] - bbox[0]
        if ft.size and ft.size != size:
            w *= size / ft.size
        return float(w)


# ---------------------------------------------------------------------------
# Font embedding
# ---------------------------------------------------------------------------

def _embed_fonts_in_svg(svg: str, font_map: dict[str, str]) -> str:
    """Parse SVG for font usage, subset TTFs, and inject @font-face CSS.

    Scans ``<text font-family="...">`` elements, finds matching TTF files,
    subsets them to only the characters actually used, base64-encodes the
    subsets, and inserts ``@font-face`` rules into the SVG ``<defs>``.

    Requires ``fonttools``.  Returns the SVG unchanged if fonttools is missing.
    """
    if not _HAS_FONTTOOLS:
        return svg

    import base64
    import io

    # 1. Collect (font-family, characters) from SVG
    font_chars: dict[str, set[str]] = {}
    for m in re.finditer(
        r'font-family="([^"]+)"[^>]*>([^<]*)<', svg
    ):
        families_raw, text = m.group(1), m.group(2)
        if not text.strip():
            continue
        first_family = families_raw.split(",")[0].strip().strip("'\"")
        key = first_family.lower()
        if key not in font_chars:
            font_chars[key] = set()
        font_chars[key].update(text)

    if not font_chars:
        return svg

    # 2. Resolve font paths and generate @font-face
    resolver = _TextMeasurer(font_map=font_map)
    face_rules: list[str] = []

    for family_lower, chars in font_chars.items():
        path = resolver._resolve_path([family_lower])
        if not os.path.exists(path):
            continue
        try:
            font = TTFont(path, fontNumber=0)
            opts = SubsetOptions()
            opts.flavor = None  # keep as raw TTF (broadest SVG viewer support)
            opts.desubroutinize = True
            subsetter = Subsetter(options=opts)
            codepoints = {ord(c) for c in chars if ord(c) > 32}
            if not codepoints:
                continue
            subsetter.populate(unicodes=codepoints)
            subsetter.subset(font)
            buf = io.BytesIO()
            font.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            font.close()
            # Use the original family name (preserving case) for CSS
            original_family = family_lower
            for m2 in re.finditer(r'font-family="([^"]*)"', svg):
                first = m2.group(1).split(",")[0].strip().strip("'\"")
                if first.lower() == family_lower:
                    original_family = first
                    break
            face_rules.append(
                f'@font-face {{ font-family: "{original_family}"; '
                f'src: url("data:font/ttf;base64,{b64}") format("truetype"); }}'
            )
        except Exception:
            continue

    if not face_rules:
        return svg

    # 3. Inject <style> after opening <svg ...> tag
    style_block = "\n<defs><style>\n" + "\n".join(face_rules) + "\n</style></defs>\n"
    insert_pos = svg.find(">")
    if insert_pos == -1:
        return svg
    return svg[: insert_pos + 1] + style_block + svg[insert_pos + 1 :]


# ---------------------------------------------------------------------------
# Public engine
# ---------------------------------------------------------------------------

class RhwpEngine:
    """Single-threaded HWP/HWPX renderer backed by rhwp WASM.

    Example
    -------
    >>> engine = RhwpEngine()
    >>> doc = engine.load("sample.hwpx")
    >>> doc.page_count
    3
    >>> svg = doc.render_page_svg(0)
    """

    def __init__(self, wasm_path: Optional[str | Path] = None,
                 font_map: Optional[dict[str, str]] = None):
        self._wasm_path = Path(wasm_path) if wasm_path else _find_wasm()
        self._engine = wasmtime.Engine()
        self._store = wasmtime.Store(self._engine)
        self._module = wasmtime.Module.from_file(self._engine, str(self._wasm_path))
        self._measurer = _TextMeasurer(font_map=font_map)
        self._linker = self._build_linker()
        self._instance = self._linker.instantiate(self._store, self._module)
        self._exports = {
            e.name: self._instance.exports(self._store)[e.name]
            for e in self._module.exports
        }
        start = self._exports.get("__wbindgen_start")
        if start is not None:
            try:
                start(self._store)
            except Exception:
                pass
        self._memory = self._exports["memory"]

    # -- internal helpers -------------------------------------------------

    def _build_linker(self) -> wasmtime.Linker:
        linker = wasmtime.Linker(self._engine)
        measurer = self._measurer

        def _read_utf8(ptr: int, length: int) -> str:
            if ptr == 0 or length == 0:
                return ""
            base = self._memory.data_ptr(self._store)
            addr = ctypes.addressof(base.contents) + ptr
            return bytes((ctypes.c_ubyte * length).from_address(addr)).decode(
                "utf-8", errors="replace"
            )

        def make_stub(name: str, results):
            if "measureTextWidth" in name:
                def real(font_ptr, font_len, text_ptr, text_len):
                    font = _read_utf8(font_ptr, font_len)
                    text = _read_utf8(text_ptr, text_len)
                    return measurer.measure(font, text)
                return real

            def stub(*_args):
                out = []
                for r in results:
                    rk = str(r)
                    if "f32" in rk or "f64" in rk:
                        out.append(0.0)
                    elif "externref" in rk or "anyref" in rk:
                        out.append(None)
                    else:
                        out.append(0)
                if not out:
                    return None
                if len(out) == 1:
                    return out[0]
                return tuple(out)
            return stub

        for imp in self._module.imports:
            ft = imp.type
            if not isinstance(ft, wasmtime.FuncType):
                continue
            linker.define_func(
                imp.module, imp.name, ft,
                make_stub(imp.name, list(ft.results)),
            )
        return linker

    def _mem_addr(self, offset: int) -> int:
        base = self._memory.data_ptr(self._store)
        return ctypes.addressof(base.contents) + offset

    def _mem_write(self, offset: int, data: bytes) -> None:
        ctypes.memmove(self._mem_addr(offset), data, len(data))

    def _mem_read(self, offset: int, length: int) -> bytes:
        return bytes((ctypes.c_ubyte * length).from_address(self._mem_addr(offset)))

    def _malloc_copy(self, data: bytes) -> int:
        ptr = self._exports["__wbindgen_malloc"](self._store, len(data), 1)
        self._mem_write(ptr, data)
        return ptr

    # -- public API -------------------------------------------------------

    def load(self, path: str | Path) -> "RhwpDocument":
        """Load a HWP or HWPX file from disk."""
        p = Path(path)
        data = p.read_bytes()
        return self.load_bytes(data, name=p.name)

    def load_bytes(self, data: bytes, *, name: str = "<bytes>") -> "RhwpDocument":
        """Load a HWP or HWPX document from an in-memory byte buffer."""
        ptr = self._malloc_copy(data)
        handle, err_ptr, is_err = self._exports["hwpdocument_new"](
            self._store, ptr, len(data)
        )
        if is_err:
            raise RhwpError(f"hwpdocument_new failed for {name}")
        return RhwpDocument(self, handle, name)


class RhwpDocument:
    """A loaded HWP/HWPX document. Do not construct directly; use ``RhwpEngine.load``."""

    def __init__(self, engine: RhwpEngine, handle: int, name: str):
        self._engine = engine
        self._handle = handle
        self.name = name
        self._closed = False
        exports = engine._exports
        self._page_count_fn = exports["hwpdocument_pageCount"]
        self._render_fn = exports["hwpdocument_renderPageSvg"]
        self._free_fn = exports["__wbg_hwpdocument_free"]
        self._wb_free = exports["__wbindgen_free"]

    @property
    def page_count(self) -> int:
        self._check()
        return int(self._page_count_fn(self._engine._store, self._handle))

    def render_page_svg(self, page: int, *, embed_fonts: bool = False) -> str:
        """Render a single page to an SVG string.

        Parameters
        ----------
        page : int
            Zero-based page index.
        embed_fonts : bool
            If True, subset and base64-embed used fonts into the SVG so it
            renders identically on any machine. Requires ``fonttools``.
        """
        self._check()
        if page < 0 or page >= self.page_count:
            raise IndexError(f"page {page} out of range (0..{self.page_count - 1})")
        svg_ptr, svg_len, _err_ptr, is_err = self._render_fn(
            self._engine._store, self._handle, page
        )
        if is_err:
            raise RhwpError(f"renderPageSvg failed for page {page} of {self.name}")
        data = self._engine._mem_read(svg_ptr, svg_len)
        try:
            self._wb_free(self._engine._store, svg_ptr, svg_len, 1)
        except Exception:
            pass
        svg = data.decode("utf-8", errors="replace")
        if embed_fonts:
            svg = _embed_fonts_in_svg(svg, self._engine._measurer._map)
        return svg

    def render_all_svgs(self, *, embed_fonts: bool = False) -> list[str]:
        """Render every page to SVG strings."""
        return [self.render_page_svg(i, embed_fonts=embed_fonts)
                for i in range(self.page_count)]

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._free_fn(self._engine._store, self._handle, 0)
        except Exception:
            pass
        self._closed = True

    def _check(self):
        if self._closed:
            raise RhwpError("document is closed")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
