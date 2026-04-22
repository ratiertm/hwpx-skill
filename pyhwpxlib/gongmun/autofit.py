"""Autofit: rhwp RenderTree 기반 공문 1페이지 자동 맞춤.

Design: docs/02-design/features/compact-autofit.design.md (v0.2)

Shrink steps (0~2):
    0) spacer pt  (6 → 4)         step size -2pt,  하한 4pt
    1) lineSpacing × ratio×0.90    하한 120
    2) 상/하 여백 (-2mm)           하한 12mm

step 3 (compact 강제) 는 Q3 결정으로 제거 — 사용자 설정 존중.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .builder import GongmunBuilder

logger = logging.getLogger(__name__)

_TOLERANCE_PX = 2.0
_MAX_ITERATIONS = 3
_MIN_MARGINS_TB_MM = 12
_LINE_SPACING_MIN = 120
_LINE_SPACING_RATIO = 0.90
_SPACER_FONT_SIZE_MIN = 4

_BODY_DEFAULT_LINE_SPACING = 160           # 본문 기본 (Q2 실측) — ratio 하한 판정 기준


# ---------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------

def fit_to_one_page(
    hwpx_path: str,
    builder: "GongmunBuilder",
    *,
    max_iters: int = _MAX_ITERATIONS,
    tolerance_px: float = _TOLERANCE_PX,
) -> bool:
    """Overflow를 감지해 shrink step을 순차 적용한다.

    Returns
    -------
    bool
        모든 content가 1페이지 Body bbox 안에 들어가면 True.
        하한 도달 또는 max_iters 초과로 실패하면 False (WARN 로그).
    """
    overflow = _measure_overflow(hwpx_path)
    logger.debug("autofit start overflow=%.1fpx", overflow)
    if overflow <= tolerance_px:
        return True

    for step in range(max_iters):
        if not _apply_shrink_step(builder, step):
            logger.warning(
                "autofit: step %d lower bound reached (overflow=%.1fpx). "
                "compact=True 또는 본문 축소를 검토하세요.",
                step, overflow,
            )
            return False
        try:
            builder._build_and_save_once(hwpx_path)
        except Exception:
            logger.exception("autofit rebuild failed at step %d", step)
            return False
        overflow = _measure_overflow(hwpx_path)
        logger.debug("autofit step=%d -> overflow=%.1fpx", step, overflow)
        if overflow <= tolerance_px:
            return True

    logger.warning(
        "autofit failed after %d steps (overflow=%.1fpx). "
        "compact=True 또는 본문 축소를 검토하세요.",
        max_iters, overflow,
    )
    return False


# ---------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------

def _measure_overflow(hwpx_path: str) -> float:
    """Page 1 을 넘어간 만큼의 overflow(px). 측정 실패 시 0.0.

    rhwp 는 auto-paginator라 page 0 내부에서는 overflow가 발생하지 않는다.
    대신 page_count > 1 이면 초과분이 있는 것으로 판정하고,
    마지막 페이지 content y+h + (page_count-2) * body_h 로 총 초과량을 근사한다.
    """
    try:
        from ..rhwp_bridge import RhwpEngine   # noqa: F401 — 존재 여부 확인용
    except Exception:
        logger.debug("rhwp_bridge import failed — autofit skipped", exc_info=True)
        return 0.0
    try:
        engine = _get_engine()
        doc = engine.load(hwpx_path)
        try:
            pc = doc.page_count
            if pc <= 1:
                return 0.0
            last_tree = doc.get_page_render_tree(pc - 1)
        finally:
            doc.close()
        body = _find_body(last_tree)
        if body is None:
            return float(pc - 1) * 1000.0   # fallback
        body_h = body["bbox"]["h"]
        extents = _all_extents(body, exclude={"Header", "Footer", "PageBg", "Page"})
        last_content = max(extents) - body["bbox"]["y"] if extents else 0.0
        # (마지막 페이지 초과분) + (중간 페이지들 전체 body_h 만큼)
        return last_content + (pc - 2) * body_h
    except Exception:
        logger.debug("overflow measure failed", exc_info=True)
        return 0.0


def _find_body(tree: dict) -> Optional[dict]:
    # Q1 실증: Body 는 root의 직접 자식
    for c in tree.get("children", []):
        if c.get("type") == "Body":
            return c
    return None


def _all_extents(node: dict, *, exclude: set[str]) -> list[float]:
    out: list[float] = []
    b = node.get("bbox") or {}
    if node.get("type") not in exclude and (b.get("h", 0) > 0):
        out.append(b["y"] + b["h"])
    for c in node.get("children") or []:
        out.extend(_all_extents(c, exclude=exclude))
    return out


# ---------------------------------------------------------------
# Engine cache (singleton — WASM 재초기화 비용 회피)
# ---------------------------------------------------------------

_ENGINE_CACHE: list = []   # type: ignore[type-arg]


def _get_engine():
    if _ENGINE_CACHE:
        return _ENGINE_CACHE[0]
    from ..rhwp_bridge import RhwpEngine   # lazy
    eng = RhwpEngine()
    _ENGINE_CACHE.append(eng)
    return eng


# ---------------------------------------------------------------
# Shrink steps
# ---------------------------------------------------------------

def _apply_shrink_step(builder: "GongmunBuilder", step: int) -> bool:
    """step에 해당하는 1회 조정. 하한 도달 시 False."""
    if step == 0:
        new_pt = builder._spacer_pt - 2
        if new_pt < _SPACER_FONT_SIZE_MIN:
            return False
        builder._spacer_pt = new_pt
        return True
    if step == 1:
        new_ratio = builder._line_spacing_ratio * _LINE_SPACING_RATIO
        # 본문 기본 160%가 하한 미만이 되는지 판정 (표·제목 등 작은 값은 post-save 에서 120 클램프)
        if _BODY_DEFAULT_LINE_SPACING * new_ratio < _LINE_SPACING_MIN:
            return False
        builder._line_spacing_ratio = new_ratio
        return True
    if step == 2:
        t, b, l, r, h, f = builder.margins_mm
        if t <= _MIN_MARGINS_TB_MM and b <= _MIN_MARGINS_TB_MM:
            return False
        builder.margins_mm = (
            max(t - 2, _MIN_MARGINS_TB_MM),
            max(b - 2, _MIN_MARGINS_TB_MM),
            l, r, h, f,
        )
        return True
    return False
