"""Render performance benchmark — render-perf-opt baseline & verification.

Design Ref: render-perf-opt.design.md §8.4 — B-01.
Plan SC: 5-run mean ≤ 200ms (cold excluded), accuracy anchor sha256 unchanged.

Usage:
    python scripts/bench_render.py [--input PATH] [--runs N] [--page P]

Reports cold time, warm mean/p50/p95, and PNG sha256 to confirm byte-identity
against the reference anchor.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import statistics
import sys
import time
from pathlib import Path


DEFAULT_INPUT = "Test/output/template_fill_makers.hwpx"
ANCHOR_SHA256 = "d4501eeed09bc3d4d6c45a887523fdec913f428bdfee18f3e8c2570a793f2c05"


def _measure(input_path: str, page: int, runs: int) -> dict:
    from pyhwpxlib.api import render_to_png
    from pyhwpxlib.rhwp_bridge import _measure_text_cached, _ENGINE_CACHE

    out = "/tmp/_bench.png"
    timings: list[float] = []

    # Cold
    t0 = time.perf_counter()
    render_to_png(input_path, out, page=page, scale=1.0, register_fonts=False)
    cold = (time.perf_counter() - t0) * 1000
    sha = hashlib.sha256(open(out, "rb").read()).hexdigest()
    size = os.path.getsize(out)

    # Warm runs
    for _ in range(runs):
        t = time.perf_counter()
        render_to_png(input_path, out, page=page, scale=1.0, register_fonts=False)
        timings.append((time.perf_counter() - t) * 1000)

    cache = _measure_text_cached.cache_info()
    return {
        "input": input_path,
        "page": page,
        "cold_ms": cold,
        "warm_runs": runs,
        "warm_mean_ms": statistics.mean(timings),
        "warm_p50_ms": statistics.median(timings),
        "warm_p95_ms": (
            statistics.quantiles(timings, n=20)[18] if runs >= 5 else max(timings)
        ),
        "warm_min_ms": min(timings),
        "warm_max_ms": max(timings),
        "sha256": sha,
        "size_bytes": size,
        "anchor_match": sha == ANCHOR_SHA256,
        "lru_hits": cache.hits,
        "lru_misses": cache.misses,
        "engine_cache_entries": len(_ENGINE_CACHE),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT,
                        help=f"HWPX input file (default: {DEFAULT_INPUT})")
    parser.add_argument("--runs", type=int, default=5,
                        help="Number of warm runs (default: 5)")
    parser.add_argument("--page", type=int, default=0,
                        help="Page index (default: 0)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 2

    print(f"# render-perf-opt benchmark")
    print(f"# input:  {args.input}")
    print(f"# page:   {args.page}, runs: {args.runs}")
    print()

    r = _measure(args.input, args.page, args.runs)

    print(f"  cold:        {r['cold_ms']:8.1f} ms")
    print(f"  warm mean:   {r['warm_mean_ms']:8.1f} ms  (target ≤ 200ms)")
    print(f"  warm p50:    {r['warm_p50_ms']:8.1f} ms")
    print(f"  warm p95:    {r['warm_p95_ms']:8.1f} ms")
    print(f"  warm min:    {r['warm_min_ms']:8.1f} ms")
    print(f"  warm max:    {r['warm_max_ms']:8.1f} ms")
    print()
    print(f"  sha256:      {r['sha256']}")
    print(f"  bytes:       {r['size_bytes']}")
    print(f"  anchor:      {'MATCH' if r['anchor_match'] else 'MISMATCH ❌'}")
    print(f"  LRU:         hits={r['lru_hits']} misses={r['lru_misses']}")
    print(f"  engine cache: {r['engine_cache_entries']} entries")

    if not r["anchor_match"]:
        print("\nERROR: PNG sha256 does not match the captured anchor.", file=sys.stderr)
        print("       Caching changes broke byte-identity. Investigate.", file=sys.stderr)
        return 1

    if r["warm_mean_ms"] > 200:
        print(f"\nWARN: warm mean {r['warm_mean_ms']:.0f}ms exceeds 200ms target.",
              file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
