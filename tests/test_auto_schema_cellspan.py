"""Tests for the cellSpan-aware grid heuristics in auto_schema (v0.13.4)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAKERS_HWPX = PROJECT_ROOT / "skill" / "templates" / "makers_project_report.hwpx"
MAKERS_SCHEMA = PROJECT_ROOT / "skill" / "templates" / "makers_project_report.schema.json"


def _has(p): return p.exists()


# ─── _find_grid_subregion ──────────────────────────────────────────


def _cell(r, c, *, cs=1, rs=1, text=""):
    return {"row": r, "col": c, "cs": cs, "rs": rs, "text": text}


def test_find_grid_subregion_returns_longest_run():
    """T-01/02: 4 contiguous value-only rows with same col set → GridRegion."""
    from pyhwpxlib.templates.auto_schema import _find_grid_subregion
    cells = [
        _cell(0, 0, cs=7, text="title"),
        _cell(1, 0, text="팀명"), _cell(1, 1, cs=6, text=""),    # single row, ignored
        _cell(2, 0, text="구분"), _cell(2, 1, text="성명"),
        _cell(2, 2, cs=2, text="학과"), _cell(2, 4, cs=2, text="학번"), _cell(2, 6, text="서명"),
        # grid rows
        _cell(3, 0, rs=4, text="참여자"),
        _cell(3, 1), _cell(3, 2, cs=2), _cell(3, 4, cs=2), _cell(3, 6),
        _cell(4, 1), _cell(4, 2, cs=2), _cell(4, 4, cs=2), _cell(4, 6),
        _cell(5, 1), _cell(5, 2, cs=2), _cell(5, 4, cs=2), _cell(5, 6),
        _cell(6, 1), _cell(6, 2, cs=2), _cell(6, 4, cs=2), _cell(6, 6),
        # footer rows (interrupting)
        _cell(7, 0, text="프로젝트명"), _cell(7, 1, cs=6),
    ]
    grid = _find_grid_subregion(cells)
    assert grid is not None
    assert grid.start == 3
    assert grid.end == 6
    assert grid.cols == frozenset({1, 2, 4, 6})
    assert grid.length == 4


def test_find_grid_subregion_too_short_returns_none():
    """T-03: 2 contiguous rows < 3 minimum → None."""
    from pyhwpxlib.templates.auto_schema import _find_grid_subregion
    cells = [_cell(0, 0), _cell(0, 1), _cell(1, 0), _cell(1, 1)]
    assert _find_grid_subregion(cells) is None


def test_find_grid_subregion_single_col_returns_none():
    """T-03: even with many rows, col-set size <2 → None (not a grid)."""
    from pyhwpxlib.templates.auto_schema import _find_grid_subregion
    cells = [_cell(r, 0) for r in range(5)]
    assert _find_grid_subregion(cells) is None


# ─── _find_row_group_label ─────────────────────────────────────────


def test_find_row_group_label_rs_4_covers_all_rows():
    """T-04: rs=4 cell at (3, 0) is the row-group label for rows 3..6."""
    from pyhwpxlib.templates.auto_schema import _find_row_group_label
    cells = [
        _cell(3, 0, rs=4, text="참 여 자"),
        _cell(3, 1), _cell(4, 1), _cell(5, 1), _cell(6, 1),
    ]
    for r in (3, 4, 5, 6):
        assert _find_row_group_label({"row": r, "col": 1, "cs": 1, "rs": 1}, cells) == "참 여 자"


def test_find_row_group_label_rs_1_returns_none():
    """T-05: a single-row label cell is NOT a row-group label."""
    from pyhwpxlib.templates.auto_schema import _find_row_group_label
    cells = [_cell(3, 0, rs=1, text="구분"), _cell(3, 1)]
    assert _find_row_group_label({"row": 3, "col": 1, "cs": 1, "rs": 1}, cells) is None


# ─── _find_label_for cellSpan-aware ────────────────────────────────


def test_find_label_for_header_with_colspan_covers_value():
    """T-06: header at (0, 2, cs=3) covers cols 2..4. Value (1, 4) should match."""
    from pyhwpxlib.templates.auto_schema import _find_label_for
    cells = [
        _cell(0, 2, cs=3, text="공통헤더"),
        _cell(1, 2), _cell(1, 3), _cell(1, 4),
    ]
    label = _find_label_for({"row": 1, "col": 4, "cs": 1, "rs": 1}, cells, prefer_header=True)
    assert label == "공통헤더"


def test_find_label_for_row_label_with_rowspan_covers_value():
    """T-07: row label at (0, 0, rs=3) covers rows 0..2. Value (2, 1) finds it on the left."""
    from pyhwpxlib.templates.auto_schema import _find_label_for
    cells = [
        _cell(0, 0, rs=3, text="참여자"),
        _cell(0, 1), _cell(1, 1), _cell(2, 1),
    ]
    label = _find_label_for({"row": 2, "col": 1, "cs": 1, "rs": 1}, cells, prefer_header=False)
    assert label == "참여자"


# ─── End-to-end on makers ──────────────────────────────────────────


@pytest.mark.skipif(not _has(MAKERS_HWPX), reason="makers HWPX missing")
def test_makers_table_0_overlap_meets_70_percent():
    """T-08: auto schema for makers table[0] matches manual ≥ 70%."""
    from pyhwpxlib.templates.auto_schema import generate_schema_from_hwpx

    auto = generate_schema_from_hwpx(MAKERS_HWPX, name="makers_auto")
    manual = json.loads(MAKERS_SCHEMA.read_text())

    auto_t0 = next(t for t in auto["tables"] if t["index"] == 0)
    manual_t0 = next(t for t in manual["tables"] if t["index"] == 0)

    auto_keys = {f["key"] for f in auto_t0["fields"]}
    manual_keys = {f["key"] for f in manual_t0["fields"]}
    overlap = auto_keys & manual_keys
    ratio = len(overlap) / len(manual_keys)
    assert ratio >= 0.70, (
        f"Overlap {ratio:.0%} < 70%. "
        f"missing in auto: {sorted(manual_keys - auto_keys)}, "
        f"extra in auto: {sorted(auto_keys - manual_keys)}"
    )


@pytest.mark.skipif(not _has(MAKERS_HWPX), reason="makers HWPX missing")
def test_makers_grid_produces_member_N_keys():
    """All 16 grid cells produce member_<1..4>_<name|dept|student_id|signature>."""
    from pyhwpxlib.templates.auto_schema import generate_schema_from_hwpx

    schema = generate_schema_from_hwpx(MAKERS_HWPX, name="makers_auto")
    t0 = next(t for t in schema["tables"] if t["index"] == 0)
    keys = {f["key"] for f in t0["fields"]}
    expected = {f"member_{n}_{f}"
                for n in (1, 2, 3, 4)
                for f in ("name", "dept", "student_id", "signature")}
    missing = expected - keys
    assert not missing, f"grid is missing: {missing}"
