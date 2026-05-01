"""Reference vs output 페이지 카운트 비교 — 강제 게이트.

다른 hwpx-skill 의 page_guard.py 패턴을 흡수. 양식 채우기·공문·기존 문서 편집 시
"validate 통과 ≠ 사용자 의도 일치" 갭을 메우기 위한 강제 게이트.

이중 경로:
  1. rhwp WASM (정확) — RhwpEngine().load(path).page_count
  2. OWPML static (빠름·폴백) — <hp:p pageBreak="1"> 카운트 + secPr

CLI:
  pyhwpxlib page-guard --reference REF --output OUT [--threshold N] [--mode auto|rhwp|static] [--json]

Exit codes:
  0 — pass (threshold 이내)
  1 — fail (페이지 차이 초과)
  2 — error (파일 없음·XML 깨짐 등)
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from lxml import etree

CountMode = Literal["rhwp", "static", "auto"]

_HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
_NS = {"hp": _HP_NS}


@dataclass
class PageCountResult:
    """단일 HWPX 페이지 카운트 결과."""
    path: Path
    pages: int
    method: Literal["rhwp", "static"]
    warnings: list[str] = field(default_factory=list)


@dataclass
class GuardResult:
    """page-guard 비교 결과."""
    passed: bool
    reference: PageCountResult
    output: PageCountResult
    threshold: int
    diff: int  # output.pages - reference.pages

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "reference": {
                "path": str(self.reference.path),
                "pages": self.reference.pages,
                "method": self.reference.method,
                "warnings": self.reference.warnings,
            },
            "output": {
                "path": str(self.output.path),
                "pages": self.output.pages,
                "method": self.output.method,
                "warnings": self.output.warnings,
            },
            "threshold": self.threshold,
            "diff": self.diff,
        }


# ── 페이지 카운트 측정 ────────────────────────────────────────────


def _count_pages_rhwp(hwpx_path: Path) -> int:
    """rhwp WASM 으로 정확한 페이지 카운트 측정."""
    from .rhwp_bridge import RhwpEngine

    engine = RhwpEngine()
    doc = engine.load(str(hwpx_path))
    return int(doc.page_count)


def _count_pages_static(hwpx_path: Path) -> int:
    """OWPML 정적 분석으로 페이지 카운트 추정.

    알고리즘: 1 + count(pageBreak=1) + count(columnBreak=1)
    한계: 텍스트 양으로 인한 자동 페이지 넘김 미감지.
    """
    pages = 1
    with zipfile.ZipFile(hwpx_path) as z:
        for name in z.namelist():
            if not (name.startswith("Contents/section") and name.endswith(".xml")):
                continue
            tree = etree.fromstring(z.read(name))
            pages += len(tree.xpath('.//hp:p[@pageBreak="1"]', namespaces=_NS))
            pages += len(tree.xpath('.//hp:p[@columnBreak="1"]', namespaces=_NS))
    return pages


def count_pages(
    hwpx_path: Path | str,
    mode: CountMode = "auto",
) -> PageCountResult:
    """단일 HWPX 의 페이지 수 측정.

    Parameters
    ----------
    hwpx_path : Path | str
        분석 대상 파일
    mode : "auto" | "rhwp" | "static"
        - "auto" (default): rhwp 시도, 실패 시 static 폴백
        - "rhwp": rhwp 만 (실패 시 RuntimeError)
        - "static": OWPML 정적 분석만 (rhwp 안 씀)

    Raises
    ------
    FileNotFoundError, RuntimeError (mode="rhwp" + 로딩 실패)
    """
    path = Path(hwpx_path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    warnings: list[str] = []

    if mode == "static":
        return PageCountResult(path=path, pages=_count_pages_static(path),
                               method="static", warnings=warnings)

    # mode in ("auto", "rhwp")
    try:
        return PageCountResult(path=path, pages=_count_pages_rhwp(path),
                               method="rhwp", warnings=warnings)
    except Exception as e:  # noqa: BLE001
        if mode == "rhwp":
            raise RuntimeError(f"rhwp 페이지 카운트 실패: {e}") from e
        warnings.append(f"rhwp 실패 ({type(e).__name__}: {e}), static 폴백")
        return PageCountResult(path=path, pages=_count_pages_static(path),
                               method="static", warnings=warnings)


# ── 비교 ──────────────────────────────────────────────────────────


def compare(
    reference: Path | str,
    output: Path | str,
    threshold: int = 0,
    mode: CountMode = "auto",
) -> GuardResult:
    """레퍼런스/결과 페이지 카운트 비교.

    threshold:
      0 (default) — 완전 동일 강제
      N           — N 페이지 차이까지 허용

    Returns:
      passed=True 면 |diff| <= threshold
    """
    ref = count_pages(reference, mode=mode)
    out = count_pages(output, mode=mode)
    diff = out.pages - ref.pages
    passed = abs(diff) <= threshold
    return GuardResult(passed=passed, reference=ref, output=out,
                       threshold=threshold, diff=diff)


# ── CLI ───────────────────────────────────────────────────────────


def _format_text(result: GuardResult) -> str:
    """인간 가독 텍스트 출력."""
    icon = "✓" if result.passed else "✗"
    status = "PASS" if result.passed else "FAIL"
    sign = "+" if result.diff > 0 else ("" if result.diff == 0 else "")
    lines = [
        f"{icon} page-guard {status}",
        f"  reference: {result.reference.pages} pages "
        f"({result.reference.method})",
        f"  output:    {result.output.pages} pages "
        f"({result.output.method}){f' ({sign}{result.diff})' if result.diff != 0 else ''}",
        f"  threshold: {result.threshold}",
    ]
    for w in result.reference.warnings:
        lines.append(f"  ! ref: {w}")
    for w in result.output.warnings:
        lines.append(f"  ! out: {w}")
    if not result.passed:
        if result.diff > 0:
            lines.append(
                f"  hint: 결과가 레퍼런스보다 {result.diff}페이지 많습니다. "
                f"autofit 또는 텍스트 압축을 시도하세요.")
        else:
            lines.append(
                f"  hint: 결과가 레퍼런스보다 {-result.diff}페이지 적습니다. "
                f"내용 누락 가능성을 확인하세요.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리. exit code 0 (pass) / 1 (fail) / 2 (오류)."""
    parser = argparse.ArgumentParser(
        prog="pyhwpxlib page-guard",
        description="레퍼런스/결과 HWPX 페이지 카운트 비교 (강제 게이트)",
    )
    parser.add_argument("--reference", required=True, help="기준 HWPX 경로")
    parser.add_argument("--output", required=True, help="검증할 HWPX 경로")
    parser.add_argument("--threshold", type=int, default=0,
                        help="허용 페이지 차이 (default 0)")
    parser.add_argument("--mode", choices=["auto", "rhwp", "static"],
                        default="auto", help="페이지 카운트 측정 방법")
    parser.add_argument("--json", action="store_true", help="JSON 출력")

    args = parser.parse_args(argv)

    try:
        result = compare(
            reference=args.reference,
            output=args.output,
            threshold=args.threshold,
            mode=args.mode,
        )
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (RuntimeError, zipfile.BadZipFile, etree.XMLSyntaxError) as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        out_stream = sys.stdout if result.passed else sys.stderr
        print(_format_text(result), file=out_stream)

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
