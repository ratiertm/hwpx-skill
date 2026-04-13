"""Golden tests: rhwp visual rendering produces valid output."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

PROJECT = os.path.dirname(os.path.dirname(__file__))
TEST_DIR = os.path.join(PROJECT, 'Test')

# Find all HWPX files in Test/
HWPX_SAMPLES = [
    os.path.join(TEST_DIR, f)
    for f in os.listdir(TEST_DIR)
    if f.endswith('.hwpx') and os.path.isfile(os.path.join(TEST_DIR, f))
] if os.path.isdir(TEST_DIR) else []


@pytest.mark.parametrize("hwpx", HWPX_SAMPLES, ids=[os.path.basename(p) for p in HWPX_SAMPLES])
def test_renders_without_error(hwpx, tmp_path):
    """rhwp 렌더링이 에러 없이 PNG 생성."""
    from scripts.preview import render_pages
    results = render_pages(hwpx, str(tmp_path))
    assert len(results) > 0, "No pages rendered"
    for r in results:
        assert r["fill_ratio"] >= 0.0
        assert r["svg_chars"] > 100, "SVG too small — likely empty render"
        assert os.path.exists(r["png"]), f"PNG not created: {r['png']}"


@pytest.mark.parametrize("hwpx", HWPX_SAMPLES, ids=[os.path.basename(p) for p in HWPX_SAMPLES])
def test_png_not_empty(hwpx, tmp_path):
    """생성된 PNG가 빈 파일이 아닌지 검증."""
    from scripts.preview import render_pages
    results = render_pages(hwpx, str(tmp_path))
    for r in results:
        size = os.path.getsize(r["png"])
        assert size > 1000, f"PNG too small ({size} bytes) — likely blank"
