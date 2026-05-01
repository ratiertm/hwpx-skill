"""page-guard 테스트 — 5 케이스 (T-PG-01 ~ T-PG-05)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pyhwpxlib import HwpxBuilder
from pyhwpxlib.page_guard import compare, count_pages, main


@pytest.fixture
def ref_1page(tmp_path: Path) -> Path:
    """1페이지 레퍼런스 fixture."""
    p = tmp_path / "ref_1p.hwpx"
    b = HwpxBuilder(theme="default")
    b.add_heading("Test Reference", level=1)
    b.add_paragraph("내용 한 줄")
    b.save(str(p))
    return p


@pytest.fixture
def out_1page(tmp_path: Path) -> Path:
    """1페이지 결과 — pass 시나리오."""
    p = tmp_path / "out_1p.hwpx"
    b = HwpxBuilder(theme="default")
    b.add_heading("Test Output", level=1)
    b.add_paragraph("다른 내용")
    b.save(str(p))
    return p


@pytest.fixture
def out_2page(tmp_path: Path) -> Path:
    """2페이지 결과 — fail 시나리오 (page_break 추가)."""
    p = tmp_path / "out_2p.hwpx"
    b = HwpxBuilder(theme="default")
    b.add_heading("Test Output", level=1)
    b.add_paragraph("page 1")
    b.add_page_break()
    b.add_paragraph("page 2")
    b.save(str(p))
    return p


# ── T-PG-01: 같은 페이지, threshold 0 → pass ─────────────────────


def test_pg_01_same_page_passes(ref_1page: Path, out_1page: Path):
    """ref 1p / out 1p / threshold 0 → exit 0, passed=True, diff=0."""
    result = compare(ref_1page, out_1page, threshold=0, mode="static")
    assert result.passed is True
    assert result.diff == 0
    assert result.reference.pages == 1
    assert result.output.pages == 1


# ── T-PG-02: +1 페이지, threshold 0 → fail ───────────────────────


def test_pg_02_extra_page_fails(ref_1page: Path, out_2page: Path):
    """ref 1p / out 2p / threshold 0 → exit 1, passed=False, diff=+1."""
    result = compare(ref_1page, out_2page, threshold=0, mode="static")
    assert result.passed is False
    assert result.diff == 1
    assert result.reference.pages == 1
    assert result.output.pages == 2


# ── T-PG-03: +1 페이지, threshold 1 → pass (허용 오차 내) ─────────


def test_pg_03_threshold_allows_diff(ref_1page: Path, out_2page: Path):
    """ref 1p / out 2p / threshold 1 → exit 0, passed=True, diff=+1."""
    result = compare(ref_1page, out_2page, threshold=1, mode="static")
    assert result.passed is True
    assert result.diff == 1


# ── T-PG-04: static 모드 직접 사용 ──────────────────────────────


def test_pg_04_static_mode(ref_1page: Path):
    """mode='static' 시 method='static', warnings 없음."""
    result = count_pages(ref_1page, mode="static")
    assert result.pages == 1
    assert result.method == "static"
    assert result.warnings == []


# ── T-PG-05: --json 출력 형식 ────────────────────────────────────


def test_pg_05_json_output(
    ref_1page: Path, out_2page: Path, capsys: pytest.CaptureFixture
):
    """--json 출력이 유효 JSON, 모든 필드 존재."""
    rc = main([
        "--reference", str(ref_1page),
        "--output", str(out_2page),
        "--mode", "static",
        "--json",
    ])
    assert rc == 1  # fail
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["passed"] is False
    assert data["diff"] == 1
    assert data["threshold"] == 0
    assert data["reference"]["pages"] == 1
    assert data["output"]["pages"] == 2
    assert data["reference"]["method"] == "static"


# ── 추가: FileNotFoundError 처리 ─────────────────────────────────


def test_pg_missing_file_returns_exit_2(
    tmp_path: Path, capsys: pytest.CaptureFixture
):
    """없는 파일 → exit 2, stderr 메시지."""
    rc = main([
        "--reference", str(tmp_path / "nonexistent.hwpx"),
        "--output", str(tmp_path / "also_missing.hwpx"),
        "--mode", "static",
    ])
    assert rc == 2


# ── CLI subprocess 통합 (선택) ───────────────────────────────────


def test_pg_cli_integration_pass(ref_1page: Path, out_1page: Path):
    """python -m pyhwpxlib page-guard 가 exit 0 반환."""
    result = subprocess.run(
        [sys.executable, "-m", "pyhwpxlib", "page-guard",
         "--reference", str(ref_1page),
         "--output", str(out_1page),
         "--mode", "static"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "PASS" in result.stdout


# ── T-PG-06: 양식 셀 fill overflow 회귀 (실제 사용자 시나리오) ──────


def _build_form(path: Path, extra_lines: int = 0) -> None:
    """양식 시뮬레이션 — 표 + 본문, 추가 라인 수 가변."""
    b = HwpxBuilder(theme="default")
    b.add_heading("전문가 활용 내역서", level=1)
    b.add_paragraph("")
    b.add_table([
        ["프로그램명", "테스트 프로그램"],
        ["전문가", "홍길동"],
        ["경력 사항", "○ 경력 시작"],
        ["용역 내역", "○ 활용 시작"],
    ])
    b.add_paragraph("")
    b.add_paragraph("○ 경력 사항 상세")
    for i in range(extra_lines):
        b.add_paragraph(
            f"  - 추가 경력 {i:03d}: 회사X 정보화 사업 자문 위원 "
            f"(2024.0{(i % 9) + 1}.01 ~ 2024.0{(i % 9) + 1}.30)"
        )
    b.add_paragraph("")
    b.add_paragraph("본문 마무리")
    b.save(str(path))


@pytest.fixture
def ref_form_1page(tmp_path: Path) -> Path:
    """1페이지 양식 baseline — 표 + 짧은 본문."""
    p = tmp_path / "form_ref.hwpx"
    _build_form(p, extra_lines=0)
    return p


def test_pg_06_cell_fill_triggers_page_overflow(
    ref_form_1page: Path, tmp_path: Path,
):
    """실제 양식 fill 시나리오 — 본문 라인 폭증 → page-guard FAIL.

    회귀 보호: 양식 채우기 워크플로에서 사용자가 무심코 텍스트를 너무 많이
    넣었을 때 page-guard 가 페이지 폭증을 잡아내는지 검증. Rule #12 (페이지
    동일 필수) 의 핵심 안전장치.

    구현 단순화: HwpxBuilder 의 add_paragraph 만으로 본문 라인 50개 추가하여
    페이지 폭증 시뮬레이션. 실제 양식의 표 셀 fill 도 동일 효과 — 셀이 세로로
    늘어나거나 본문이 길어지거나 page-guard 의 감지 로직은 동일.
    """
    overflow = tmp_path / "form_overflow.hwpx"
    _build_form(overflow, extra_lines=50)

    ref_pages = count_pages(ref_form_1page, mode="rhwp").pages
    out_pages = count_pages(overflow, mode="rhwp").pages

    assert ref_pages == 1, f"baseline 양식 1페이지여야 함, 실제: {ref_pages}"
    assert out_pages > 1, (
        f"본문 50줄 추가 후 페이지 늘어야 함, 실제: {out_pages}")

    rc = main([
        "--reference", str(ref_form_1page),
        "--output", str(overflow),
        "--threshold", "0",
        "--mode", "rhwp",
    ])
    assert rc == 1, "fill overflow 시 exit 1 (FAIL) 반환해야 함"
