"""Smoke tests for rhwp_bridge HTML / render tree / canvas-count extensions."""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.smoke

wasmtime = pytest.importorskip("wasmtime")
from pyhwpxlib.rhwp_bridge import RhwpDocument, RhwpEngine  # noqa: E402

SAMPLE = Path(__file__).parent / "output" / "롯데이노베이트_신규계약체결_내부결재.hwpx"


@pytest.fixture(scope="module")
def doc() -> RhwpDocument:
    if not SAMPLE.exists():
        pytest.skip(f"sample not found: {SAMPLE}")
    engine = RhwpEngine()
    return engine.load(str(SAMPLE))


def test_render_page_html_returns_string(doc: RhwpDocument) -> None:
    html = doc.render_page_html(0)
    assert isinstance(html, str)
    assert len(html) > 100
    assert "<" in html and ">" in html


def test_get_page_render_tree_has_bbox(doc: RhwpDocument) -> None:
    tree = doc.get_page_render_tree(0)
    assert isinstance(tree, dict)
    assert "bbox" in tree and "children" in tree
    bbox = tree["bbox"]
    assert bbox["w"] > 0 and bbox["h"] > 0


def test_render_page_canvas_count_positive(doc: RhwpDocument) -> None:
    count = doc.render_page_canvas_count(0)
    assert isinstance(count, int)
    assert count > 0


def test_render_tree_detects_one_page_fit(doc: RhwpDocument) -> None:
    """Task #12 precursor: verify all content fits within page bbox."""
    tree = doc.get_page_render_tree(0)
    page_h = tree["bbox"]["h"]

    def max_y_extent(node: dict) -> float:
        b = node.get("bbox", {})
        y, h = b.get("y", 0), b.get("h", 0)
        return max([y + h] + [max_y_extent(c) for c in node.get("children", [])])

    content_end = max_y_extent(tree)
    assert content_end <= page_h + 1.0, f"content overflow: {content_end} > {page_h}"
