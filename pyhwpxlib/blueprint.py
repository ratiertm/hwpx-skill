"""HWPX 인간 가독 청사진 생성기 — 새 사용자 onboarding + LLM 컨텍스트 생성.

OWPML 정적 분석만으로 charPr / paraPr / borderFill / 표 / 페이지 인벤토리 출력.
rhwp 의존 없음 — 빠르고 가벼움.

CLI:
  pyhwpxlib analyze FILE --blueprint [--depth {1,2,3}] [--json]

depth:
  1 — 페이지 + 표 카운트만 (가장 가벼움)
  2 (default) — + 스타일 인벤토리 + 표 상세
  3 — + paragraph 별 스타일 분포 히스토그램
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from lxml import etree

_HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
_HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
_NS = {"hp": _HP_NS, "hh": _HH_NS}


# ── dataclasses ───────────────────────────────────────────────────


@dataclass
class PageInfo:
    """페이지 설정."""
    width: int          # HWPUNIT
    height: int
    margin_left: int
    margin_right: int
    margin_top: int
    margin_bottom: int
    body_width: int     # = width - margin_left - margin_right
    pages: int          # static count

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class StyleInventory:
    """header.xml 의 스타일 ID 인벤토리."""
    char_props: list[int]      # 사용된 charPr ID
    para_props: list[int]      # 사용된 paraPr ID
    border_fills: list[int]    # 사용된 borderFill ID
    char_total: int            # 정의된 총 개수 (itemCnt)
    para_total: int
    border_total: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class TableInfo:
    """표 1개의 요약."""
    index: int                 # 문서 내 순번 (0-based)
    rows: int
    cols: int
    col_widths: list[int]      # HWPUNIT
    has_header: bool           # repeatHeader="1" 여부
    has_span: bool             # rowSpan/colSpan>1 사용 여부
    border_fill_id: int

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Blueprint:
    """전체 청사진."""
    path: Path
    page: PageInfo
    styles: StyleInventory
    tables: list[TableInfo]
    paragraph_count: int
    image_count: int
    page_break_count: int
    section_count: int
    char_histogram: dict[int, int] = field(default_factory=dict)  # depth=3
    para_histogram: dict[int, int] = field(default_factory=dict)  # depth=3

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "page": self.page.to_dict(),
            "styles": self.styles.to_dict(),
            "tables": [t.to_dict() for t in self.tables],
            "paragraph_count": self.paragraph_count,
            "image_count": self.image_count,
            "page_break_count": self.page_break_count,
            "section_count": self.section_count,
            "char_histogram": self.char_histogram,
            "para_histogram": self.para_histogram,
        }


# ── analyze ────────────────────────────────────────────────────────


def _read_hwpx_xmls(hwpx_path: Path) -> tuple[Optional[bytes], list[bytes]]:
    """HWPX 에서 header.xml 과 모든 section*.xml 바이트 반환."""
    header_bytes: Optional[bytes] = None
    section_bytes: list[bytes] = []
    with zipfile.ZipFile(hwpx_path) as z:
        for name in sorted(z.namelist()):
            if name == "Contents/header.xml":
                header_bytes = z.read(name)
            elif (name.startswith("Contents/section")
                  and name.endswith(".xml")):
                section_bytes.append(z.read(name))
    return header_bytes, section_bytes


def _parse_page_info(header_root: etree._Element, pages: int) -> PageInfo:
    """header.xml 의 beginNum 또는 첫 secPr 후보에서 페이지 정보 추출."""
    # secPr 는 header 에 없고 section0.xml 첫 문단에 있음 — 여기서는 default.
    # 정확 추출은 _parse_secpr_from_section 에서.
    # 이 함수는 fallback 용 placeholder.
    return PageInfo(
        width=59528, height=84186,
        margin_left=8504, margin_right=8504,
        margin_top=5667, margin_bottom=4252,
        body_width=42520,
        pages=pages,
    )


def _parse_secpr(section_root: etree._Element, pages: int) -> PageInfo:
    """section*.xml 의 첫 secPr 에서 페이지/여백 추출."""
    sec = section_root.find(".//hp:secPr", _NS)
    if sec is None:
        return _parse_page_info(section_root, pages)

    page_el = sec.find("hp:pagePr", _NS)
    if page_el is None:
        return _parse_page_info(section_root, pages)

    width = int(page_el.get("width", "59528"))
    height = int(page_el.get("height", "84186"))
    margin = page_el.find("hp:margin", _NS)
    if margin is not None:
        ml = int(margin.get("left", "8504"))
        mr = int(margin.get("right", "8504"))
        mt = int(margin.get("top", "5667"))
        mb = int(margin.get("bottom", "4252"))
    else:
        ml = mr = 8504
        mt = 5667
        mb = 4252
    return PageInfo(
        width=width, height=height,
        margin_left=ml, margin_right=mr,
        margin_top=mt, margin_bottom=mb,
        body_width=width - ml - mr,
        pages=pages,
    )


def _parse_styles(header_bytes: Optional[bytes],
                  used_char: set[int], used_para: set[int],
                  used_border: set[int]) -> StyleInventory:
    """header.xml itemCnt + 사용된 ID 셋."""
    char_total = para_total = border_total = 0

    if header_bytes is not None:
        root = etree.fromstring(header_bytes)
        cp = root.find(".//hh:charProperties", _NS)
        pp = root.find(".//hh:paraProperties", _NS)
        bf = root.find(".//hh:borderFills", _NS)
        if cp is not None:
            char_total = int(cp.get("itemCnt", "0"))
        if pp is not None:
            para_total = int(pp.get("itemCnt", "0"))
        if bf is not None:
            border_total = int(bf.get("itemCnt", "0"))

    return StyleInventory(
        char_props=sorted(used_char),
        para_props=sorted(used_para),
        border_fills=sorted(used_border),
        char_total=char_total,
        para_total=para_total,
        border_total=border_total,
    )


def _parse_table(tbl: etree._Element, idx: int) -> TableInfo:
    """<hp:tbl> 1개를 TableInfo 로 요약."""
    rows = int(tbl.get("rowCnt", "0"))
    cols = int(tbl.get("colCnt", "0"))
    repeat_header = tbl.get("repeatHeader", "0") == "1"
    border_fill_id = int(tbl.get("borderFillIDRef", "0"))

    # 첫 행의 cellSz/width 모음으로 col widths 추정
    col_widths: list[int] = []
    first_tr = tbl.find("hp:tr", _NS)
    if first_tr is not None:
        for tc in first_tr.findall("hp:tc", _NS):
            cell_sz = tc.find("hp:cellSz", _NS)
            if cell_sz is not None:
                col_widths.append(int(cell_sz.get("width", "0")))
            else:
                col_widths.append(0)

    # span 검사
    has_span = False
    for tc in tbl.iter(f"{{{_HP_NS}}}tc"):
        span = tc.find("hp:cellSpan", _NS)
        if span is not None:
            if (int(span.get("colSpan", "1")) > 1
                    or int(span.get("rowSpan", "1")) > 1):
                has_span = True
                break

    return TableInfo(
        index=idx,
        rows=rows,
        cols=cols,
        col_widths=col_widths,
        has_header=repeat_header,
        has_span=has_span,
        border_fill_id=border_fill_id,
    )


def analyze_blueprint(hwpx_path: Path | str, depth: int = 2) -> Blueprint:
    """HWPX 의 OWPML 파싱 → Blueprint dataclass.

    depth:
      1 — 페이지 + 표 카운트만
      2 (default) — + 스타일 인벤토리 + 표 상세
      3 — + paragraph 별 charPr/paraPr 분포 히스토그램

    Raises:
      FileNotFoundError, lxml.etree.XMLSyntaxError, zipfile.BadZipFile
    """
    if depth not in (1, 2, 3):
        raise ValueError("depth must be 1, 2, or 3")

    path = Path(hwpx_path)
    if not path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    header_bytes, section_bytes_list = _read_hwpx_xmls(path)

    used_char: set[int] = set()
    used_para: set[int] = set()
    used_border: set[int] = set()
    char_hist: Counter = Counter()
    para_hist: Counter = Counter()
    paragraph_count = 0
    image_count = 0
    page_break_count = 0
    tables: list[TableInfo] = []
    page_info: Optional[PageInfo] = None

    pages = 1  # static count
    table_idx = 0

    for sec_bytes in section_bytes_list:
        sec_root = etree.fromstring(sec_bytes)

        if page_info is None:
            page_info = _parse_secpr(sec_root, pages)

        # paragraph + 사용된 스타일 ID 모음
        for p in sec_root.iter(f"{{{_HP_NS}}}p"):
            paragraph_count += 1
            if p.get("pageBreak") == "1":
                page_break_count += 1
                pages += 1
            if p.get("columnBreak") == "1":
                pages += 1
            ppref = p.get("paraPrIDRef")
            if ppref is not None and ppref.isdigit():
                pid = int(ppref)
                used_para.add(pid)
                if depth == 3:
                    para_hist[pid] += 1

        # run 의 charPrIDRef
        for run in sec_root.iter(f"{{{_HP_NS}}}run"):
            cpref = run.get("charPrIDRef")
            if cpref is not None and cpref.isdigit():
                cid = int(cpref)
                used_char.add(cid)
                if depth == 3:
                    char_hist[cid] += 1

        # tables
        for tbl in sec_root.iter(f"{{{_HP_NS}}}tbl"):
            if depth >= 1:
                ti = _parse_table(tbl, table_idx)
                # depth=1: rows/cols 만, col_widths/span 정보 비움
                if depth == 1:
                    ti.col_widths = []
                    ti.has_span = False
                tables.append(ti)
                table_idx += 1
                if ti.border_fill_id:
                    used_border.add(ti.border_fill_id)

        # tc/borderFillIDRef 도 모음
        for tc in sec_root.iter(f"{{{_HP_NS}}}tc"):
            bfref = tc.get("borderFillIDRef")
            if bfref is not None and bfref.isdigit():
                used_border.add(int(bfref))

        # 이미지
        image_count += len(sec_root.xpath(".//hp:pic", namespaces=_NS))

    # 정확한 pages 갱신
    if page_info is None:
        page_info = _parse_page_info(etree.fromstring(b"<root/>"), pages)
    page_info.pages = pages

    # 스타일 인벤토리
    if depth >= 2:
        styles = _parse_styles(header_bytes, used_char, used_para, used_border)
    else:
        styles = StyleInventory(
            char_props=[], para_props=[], border_fills=[],
            char_total=0, para_total=0, border_total=0,
        )

    return Blueprint(
        path=path,
        page=page_info,
        styles=styles,
        tables=tables,
        paragraph_count=paragraph_count,
        image_count=image_count,
        page_break_count=page_break_count,
        section_count=len(section_bytes_list),
        char_histogram=dict(char_hist) if depth == 3 else {},
        para_histogram=dict(para_hist) if depth == 3 else {},
    )


# ── 텍스트 포맷 ────────────────────────────────────────────────────


def _hwpunit_to_mm(hwpunit: int) -> float:
    return hwpunit / 283.5


def format_text(blueprint: Blueprint) -> str:
    """인간 가독 텍스트 포맷."""
    bp = blueprint
    lines = [
        f"═══ HWPX Blueprint: {bp.path.name} ═══",
        "",
        "Page",
        f"  size:    {bp.page.width} × {bp.page.height} HWPUNIT "
        f"({_hwpunit_to_mm(bp.page.width):.0f} × {_hwpunit_to_mm(bp.page.height):.0f} mm)",
        f"  margins: L/R {bp.page.margin_left}/{bp.page.margin_right}, "
        f"T/B {bp.page.margin_top}/{bp.page.margin_bottom}",
        f"  body:    {bp.page.body_width} ({_hwpunit_to_mm(bp.page.body_width):.0f} mm)",
        f"  pages:   {bp.page.pages} (static count)",
        "",
    ]

    if bp.styles.char_total or bp.styles.para_total or bp.styles.border_total:
        lines.append("Styles")
        lines.append(
            f"  charPr      defined {bp.styles.char_total} · "
            f"used {bp.styles.char_props}")
        lines.append(
            f"  paraPr      defined {bp.styles.para_total} · "
            f"used {bp.styles.para_props}")
        lines.append(
            f"  borderFill  defined {bp.styles.border_total} · "
            f"used {bp.styles.border_fills}")
        lines.append("")

    lines.append(f"Tables ({len(bp.tables)})")
    for t in bp.tables:
        flags = []
        if t.has_header:
            flags.append("repeatHeader")
        if t.has_span:
            flags.append("span")
        flag_str = f"  [{', '.join(flags)}]" if flags else ""
        cw = f"cols={t.col_widths}" if t.col_widths else ""
        lines.append(f"  T{t.index + 1}  {t.rows}×{t.cols}  {cw}{flag_str}")
    if not bp.tables:
        lines.append("  (none)")
    lines.append("")

    lines.append("Body")
    lines.append(
        f"  {bp.paragraph_count} paragraphs · {len(bp.tables)} tables · "
        f"{bp.image_count} images")
    lines.append(
        f"  page_break: {bp.page_break_count} · sections: {bp.section_count}")

    if bp.char_histogram or bp.para_histogram:
        lines.append("")
        lines.append("Style usage histogram (depth=3)")
        if bp.char_histogram:
            top_char = sorted(bp.char_histogram.items(),
                              key=lambda x: -x[1])[:5]
            lines.append(
                f"  charPr top: {[(k, v) for k, v in top_char]}")
        if bp.para_histogram:
            top_para = sorted(bp.para_histogram.items(),
                              key=lambda x: -x[1])[:5]
            lines.append(
                f"  paraPr top: {[(k, v) for k, v in top_para]}")

    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리. exit 0 (정상) / 2 (오류)."""
    parser = argparse.ArgumentParser(
        prog="pyhwpxlib analyze",
        description="HWPX 구조 청사진 (charPr/paraPr/borderFill/표/페이지)",
    )
    parser.add_argument("file", help="분석할 HWPX 경로")
    parser.add_argument("--blueprint", action="store_true",
                        help="청사진 모드 (현재 유일한 모드)")
    parser.add_argument("--depth", type=int, choices=[1, 2, 3], default=2,
                        help="분석 깊이 (default 2)")
    parser.add_argument("--json", action="store_true", help="JSON 출력")

    args = parser.parse_args(argv)

    if not args.blueprint:
        # 현재는 blueprint 만 지원. 향후 다른 모드 추가 시 default 처리 분기
        print("error: --blueprint 옵션이 필요합니다 "
              "(현재 analyze 의 유일한 모드)", file=sys.stderr)
        return 2

    try:
        bp = analyze_blueprint(args.file, depth=args.depth)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except (zipfile.BadZipFile, etree.XMLSyntaxError) as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(bp.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_text(bp))

    return 0


if __name__ == "__main__":
    sys.exit(main())
