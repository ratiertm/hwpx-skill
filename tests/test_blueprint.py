"""blueprint 테스트 — 3 케이스 (T-BP-01 ~ T-BP-03) + 추가 회귀."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pyhwpxlib import HwpxBuilder
from pyhwpxlib.blueprint import analyze_blueprint, format_text, main


@pytest.fixture
def rich_doc(tmp_path: Path) -> Path:
    """표 3개 + 다양한 paragraph fixture."""
    p = tmp_path / "rich.hwpx"
    b = HwpxBuilder(theme="warm_executive")
    b.add_heading("Rich Doc", level=1)
    for i in range(20):
        b.add_paragraph(f"본문 {i}")
    # 표 3개
    b.add_table([["A", "B"], ["1", "2"]])
    b.add_paragraph("")
    b.add_table([["C", "D", "E"], ["3", "4", "5"]])
    b.add_paragraph("")
    b.add_table([["F"], ["6"]])
    b.save(str(p))
    return p


@pytest.fixture
def empty_doc(tmp_path: Path) -> Path:
    """빈 HwpxBuilder (heading 1개만)."""
    p = tmp_path / "empty.hwpx"
    b = HwpxBuilder(theme="default")
    b.add_paragraph("")
    b.save(str(p))
    return p


# ── T-BP-01: 표 3개 + 본문 → text 포맷 ─────────────────────────


def test_bp_01_text_output_includes_tables(rich_doc: Path):
    """text 출력에 'Tables (3)', paragraphs 포함."""
    bp = analyze_blueprint(rich_doc, depth=2)
    assert len(bp.tables) == 3
    assert bp.paragraph_count >= 20
    assert bp.image_count == 0

    text = format_text(bp)
    assert "Tables (3)" in text
    assert "T1" in text and "T2" in text and "T3" in text
    assert "Body" in text
    assert "Page" in text


# ── T-BP-02: --json 출력 ─────────────────────────────────────


def test_bp_02_json_output(rich_doc: Path, capsys: pytest.CaptureFixture):
    """--json 출력이 유효 JSON, page/styles/tables 키 모두 존재."""
    rc = main([str(rich_doc), "--blueprint", "--depth", "2", "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert "page" in data
    assert "styles" in data
    assert "tables" in data
    assert "paragraph_count" in data
    assert data["page"]["pages"] >= 1
    assert data["page"]["body_width"] > 0
    assert len(data["tables"]) == 3
    assert isinstance(data["styles"]["char_props"], list)


# ── T-BP-03: 빈 문서 ────────────────────────────────────────


def test_bp_03_empty_doc(empty_doc: Path):
    """빈 HWPX → tables=[], paragraph_count >= 1, page=1."""
    bp = analyze_blueprint(empty_doc, depth=2)
    assert bp.tables == []
    assert bp.paragraph_count >= 1
    assert bp.page.pages == 1
    assert bp.image_count == 0


# ── 추가: depth=1 가벼움, depth=3 히스토그램 ────────────────────


def test_bp_depth_1_minimal(rich_doc: Path):
    """depth=1 → col_widths/has_span 비움, char_total=0."""
    bp = analyze_blueprint(rich_doc, depth=1)
    assert len(bp.tables) == 3
    for t in bp.tables:
        assert t.col_widths == []
        assert t.has_span is False
    assert bp.styles.char_total == 0  # depth=1 은 styles 미수집


def test_bp_depth_3_histogram(rich_doc: Path):
    """depth=3 → char_histogram, para_histogram 채워짐."""
    bp = analyze_blueprint(rich_doc, depth=3)
    assert len(bp.char_histogram) > 0
    assert len(bp.para_histogram) > 0
    # 가장 많이 쓴 paraPr 가 0(default) 또는 본문 스타일
    most = max(bp.para_histogram.values())
    assert most >= 5


# ── 추가: invalid depth ─────────────────────────────────────


def test_bp_invalid_depth_raises(rich_doc: Path):
    """depth=0 → ValueError."""
    with pytest.raises(ValueError, match="depth"):
        analyze_blueprint(rich_doc, depth=0)


def test_bp_missing_file_raises(tmp_path: Path):
    """없는 파일 → FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        analyze_blueprint(tmp_path / "missing.hwpx")


# ── CLI subprocess 통합 ─────────────────────────────────────


def test_bp_cli_integration(rich_doc: Path):
    """python -m pyhwpxlib analyze 통합 동작."""
    result = subprocess.run(
        [sys.executable, "-m", "pyhwpxlib", "analyze",
         str(rich_doc), "--blueprint"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Tables (3)" in result.stdout
    assert "Page" in result.stdout
