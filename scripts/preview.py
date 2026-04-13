"""HWPX visual preview via rhwp WASM + resvg-py.

Usage:
    python scripts/preview.py <file.hwpx> [out_dir]

Outputs PNG per page to out_dir (default: /tmp) and returns fill ratio info.
Used by Claude's autonomous layout optimization loop.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from pyhwpxlib.rhwp_bridge import RhwpEngine
import resvg_py


_engine: RhwpEngine | None = None


def _get_engine() -> RhwpEngine:
    global _engine
    if _engine is None:
        _engine = RhwpEngine()
    return _engine


def _svg_fill_ratio(svg: str) -> float:
    """Estimate content fill ratio by finding max y-coordinate of any element."""
    m = re.search(r'<svg[^>]*height="([\d.]+)"', svg)
    if not m:
        return 0.0
    page_h = float(m.group(1))
    ys: list[float] = []
    for mm in re.finditer(r'\by="([\d.]+)"', svg):
        ys.append(float(mm.group(1)))
    for mm in re.finditer(r'\by2="([\d.]+)"', svg):
        ys.append(float(mm.group(1)))
    if not ys:
        return 0.0
    return max(ys) / page_h


def render_pages(hwpx_path: str | Path, out_dir: str | Path = "/tmp") -> list[dict]:
    """Render each page to PNG. Returns [{page, png, fill_ratio, svg_size}, ...]."""
    hwpx_path = Path(hwpx_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    engine = _get_engine()
    doc = engine.load(hwpx_path)
    stem = hwpx_path.stem
    results = []
    for i in range(doc.page_count):
        svg = doc.render_page_svg(i)
        png = resvg_py.svg_to_bytes(svg_string=svg)
        out_png = out_dir / f"{stem}_p{i}.png"
        out_png.write_bytes(bytes(png))
        results.append({
            "page": i,
            "png": str(out_png),
            "fill_ratio": _svg_fill_ratio(svg),
            "svg_chars": len(svg),
        })
    doc.close()
    return results


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    hwpx = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp"
    results = render_pages(hwpx, out_dir)
    for r in results:
        print(f"  page {r['page']}: {r['png']}  fill={r['fill_ratio']:.2f}")
    avg = sum(r["fill_ratio"] for r in results) / len(results) if results else 0.0
    print(f"avg fill ratio: {avg:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
