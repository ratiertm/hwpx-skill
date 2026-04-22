"""Integration tests for gongmun.autofit (Task #12, compact-autofit Design v0.2)."""
from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

pytest.importorskip("wasmtime")

from pyhwpxlib.gongmun import Gongmun, GongmunBuilder  # noqa: E402
from pyhwpxlib.gongmun import autofit as autofit_mod   # noqa: E402
from pyhwpxlib.rhwp_bridge import RhwpEngine           # noqa: E402


def _page_count(path: str) -> int:
    return RhwpEngine().load(path).page_count


def _canonical_hash(path: str) -> str:
    """Q4: <hp:p id=...> 가 전역 카운터라 바이트 일치 불가. id 정규화 후 해시."""
    parts: list[str] = []
    with zipfile.ZipFile(path) as z:
        for name in sorted(z.namelist()):
            data = z.read(name)
            if name.endswith(".xml"):
                text = re.sub(r' id="\d+"', ' id="X"', data.decode("utf-8"))
                parts.append(f"{name}::{text}")
            else:
                parts.append(f"{name}::<binary:{len(data)}>")
    return hashlib.sha256("\n---\n".join(parts).encode()).hexdigest()


def _short_doc() -> Gongmun:
    return Gongmun(
        기관명="테스트기관", 수신="귀하",
        제목="짧은 테스트",
        본문=["첫 항목", "둘째 항목"],
        공개구분="공개",
    )


def _medium_doc() -> Gongmun:
    items = [(f"추진 {i}", [f"하위 {j}" for j in range(1, 4)]) for i in range(1, 6)]
    return Gongmun(
        기관명="롯데이노베이트", 수신="롯데홈쇼핑 대표",
        제목="기간연장 요청",
        본문=items + ["회신 요망"],
        붙임=["첨부 1부"],
        공개구분="비공개", 발신명의="롯데이노베이트 대표이사",
    )


def _massive_doc() -> Gongmun:
    items = [(f"추진 {i}: 이행계획", [f"세부 {j}" for j in range(1, 5)])
             for i in range(1, 10)]
    return Gongmun(
        기관명="기관", 수신="귀하", 제목="거대 문서",
        본문=items + ["회신 요망"], 붙임=["첨부 1부"],
        공개구분="비공개", 발신명의="기관 대표",
    )


# ---- T-01 ------------------------------------------------------

def test_short_doc_autofit_no_op(tmp_path: Path) -> None:
    out = GongmunBuilder(_short_doc(), autofit=True).save(str(tmp_path / "s.hwpx"))
    assert _page_count(out) == 1


# ---- T-02 ------------------------------------------------------

def test_medium_doc_autofit_converges_to_one_page(tmp_path: Path) -> None:
    b = GongmunBuilder(_medium_doc(), 항목간_공백=True, autofit=True)
    out = b.save(str(tmp_path / "m.hwpx"))
    assert _page_count(out) == 1
    # Shrink 된 흔적이 보여야 한다 (초기값과 다름)
    assert b._spacer_pt < 6 or b._line_spacing_ratio < 1.0 or b.margins_mm[0] < 20


# ---- T-03 ------------------------------------------------------

def test_autofit_false_keeps_canonical_hash(tmp_path: Path) -> None:
    """autofit=False 경로는 실행마다 XML 정규화 해시가 동일해야 한다."""
    a = GongmunBuilder(_short_doc(), autofit=False).save(str(tmp_path / "a.hwpx"))
    b = GongmunBuilder(_short_doc(), autofit=False).save(str(tmp_path / "b.hwpx"))
    assert _canonical_hash(a) == _canonical_hash(b)


# ---- T-05 ------------------------------------------------------

def test_autofit_gives_up_gracefully(tmp_path: Path, caplog) -> None:
    """본문이 너무 많으면 WARN 1건 + 파일은 마지막 조정본 유지."""
    import logging
    with caplog.at_level(logging.WARNING, logger="pyhwpxlib.gongmun.autofit"):
        out = GongmunBuilder(_massive_doc(), 항목간_공백=True, autofit=True) \
            .save(str(tmp_path / "x.hwpx"))
    warn_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert any("compact=True" in m for m in warn_msgs)
    assert Path(out).exists()


# ---- T-06 ------------------------------------------------------

def test_autofit_respects_user_compact(tmp_path: Path) -> None:
    """사용자 compact=True 를 autofit이 뒤집지 않는다 (Q3 결정)."""
    b = GongmunBuilder(_medium_doc(), compact=True, autofit=True)
    b.save(str(tmp_path / "c.hwpx"))
    assert b.compact is True
