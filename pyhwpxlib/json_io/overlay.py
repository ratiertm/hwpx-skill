"""Overlay 방식 JSON 편집 — 원본 서식 100% 보존.

extract_overlay: HWPX → 편집 가능한 필드만 추출 (텍스트, 표 셀, 이미지 참조)
apply_overlay:   수정된 overlay JSON → 원본 XML에 적용 → 새 HWPX
"""
from __future__ import annotations

import base64
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional

_HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
_HH = "{http://www.hancom.co.kr/hwpml/2011/head}"
_HC = "{http://www.hancom.co.kr/hwpml/2011/core}"

FORMAT_VERSION = "pyhwpxlib-overlay/1"


# ─────────────────────────────────────────────
# extract_overlay
# ─────────────────────────────────────────────

def extract_overlay(
    hwpx_path: str,
    section_idx: int = 0,
    *,
    include_images: bool = True,
    include_style_hints: bool = True,
) -> dict:
    """HWPX에서 편집 가능한 필드를 overlay JSON으로 추출.

    Parameters
    ----------
    hwpx_path : str
        입력 HWPX 파일 경로
    section_idx : int
        추출할 섹션 인덱스 (기본 0)
    include_images : bool
        이미지 참조 포함 여부
    include_style_hints : bool
        스타일 힌트(폰트 크기, 볼드 등) 포함 여부

    Returns
    -------
    dict
        overlay JSON 구조
    """
    path = Path(hwpx_path)
    file_bytes = path.read_bytes()
    sha256 = hashlib.sha256(file_bytes).hexdigest()

    with zipfile.ZipFile(hwpx_path) as z:
        section_files = sorted(
            n for n in z.namelist()
            if re.match(r"Contents/section\d+\.xml", n)
        )
        if section_idx >= len(section_files):
            raise ValueError(f"Section {section_idx} not found (total: {len(section_files)})")

        sec_xml = z.read(section_files[section_idx]).decode("utf-8")

        # 스타일 힌트용 header 파싱
        style_map = {}
        if include_style_hints:
            header_xml = z.read("Contents/header.xml").decode("utf-8")
            style_map = _build_style_map(header_xml)

        # BinData 목록
        bin_files = [n for n in z.namelist() if n.startswith("BinData/")]

    root = ET.fromstring(sec_xml)

    texts = []
    tables = []
    images = []

    # 최상위 paragraph 순회 (중첩된 것은 표 내부에서 재귀 처리)
    top_paras = root.findall(f"./{_HP}p")
    _text_id = [0]
    _tbl_id = [0]
    _img_id = [0]

    for pi, p_el in enumerate(top_paras):
        _extract_from_paragraph(
            p_el, pi, texts, tables, images,
            _text_id, _tbl_id, _img_id,
            style_map, include_images, prefix=f"p{pi}",
        )

    overlay = {
        "format": FORMAT_VERSION,
        "source": path.name,
        "source_sha256": sha256,
        "section_idx": section_idx,
        "section_path": section_files[section_idx],
        "summary": {
            "texts": len(texts),
            "tables": len(tables),
            "images": len(images),
        },
        "texts": texts,
        "tables": tables,
    }
    if include_images:
        overlay["images"] = images

    return overlay


def _extract_from_paragraph(
    p_el, p_idx, texts, tables, images,
    _text_id, _tbl_id, _img_id,
    style_map, include_images, prefix,
):
    """단일 <hp:p>에서 텍스트, 표, 이미지 추출."""
    for ri, run_el in enumerate(p_el.findall(f"{_HP}run")):
        char_id = int(run_el.get("charPrIDRef", "0"))
        hint = style_map.get(char_id, "") if style_map else ""

        # 텍스트
        for t_el in run_el.findall(f"{_HP}t"):
            text = _collect_t_text(t_el)
            if text.strip():
                texts.append({
                    "id": f"t{_text_id[0]}",
                    "location": f"{prefix}/run{ri}",
                    "value": text,
                    "original": text,
                    "style_hint": hint,
                })
                _text_id[0] += 1

        # 표
        tbl_el = run_el.find(f"{_HP}tbl")
        if tbl_el is not None:
            tbl_data = _extract_table(
                tbl_el, _tbl_id[0], texts, tables, images,
                _text_id, _tbl_id, _img_id,
                style_map, include_images,
            )
            tables.append(tbl_data)
            _tbl_id[0] += 1

        # 이미지
        if include_images:
            pic_el = run_el.find(f"{_HP}pic")
            if pic_el is not None:
                img_info = _extract_image(pic_el, _img_id[0])
                if img_info:
                    images.append(img_info)
                    _img_id[0] += 1


def _extract_table(
    tbl_el, tbl_idx, texts, tables, images,
    _text_id, _tbl_id, _img_id,
    style_map, include_images,
) -> dict:
    """<hp:tbl>에서 셀 데이터 추출. 중첩 표/이미지도 재귀 처리."""
    cells = []
    for ri, tr_el in enumerate(tbl_el.findall(f"{_HP}tr")):
        for ci, tc_el in enumerate(tr_el.findall(f"{_HP}tc")):
            # 셀 텍스트
            cell_text = _extract_cell_full_text(tc_el)

            # 셀 역할 추정
            role = _guess_cell_role(cell_text, ri, ci)

            cell_entry = {
                "row": ri,
                "col": ci,
                "value": cell_text,
                "original": cell_text,
                "role": role,
                "editable": role != "header",
            }

            # span 정보
            span_el = tc_el.find(f"{_HP}cellSpan")
            if span_el is not None:
                cs = int(span_el.get("colSpan", "1"))
                rs = int(span_el.get("rowSpan", "1"))
                if cs > 1:
                    cell_entry["col_span"] = cs
                if rs > 1:
                    cell_entry["row_span"] = rs

            cells.append(cell_entry)

            # 셀 내부 중첩 표 재귀
            for inner_tbl in tc_el.findall(f".//{_HP}tbl"):
                nested = _extract_table(
                    inner_tbl, _tbl_id[0], texts, tables, images,
                    _text_id, _tbl_id, _img_id,
                    style_map, include_images,
                )
                nested["nested_in"] = f"tbl{tbl_idx}/r{ri}c{ci}"
                tables.append(nested)
                _tbl_id[0] += 1

            # 셀 내부 이미지
            if include_images:
                for pic_el in tc_el.findall(f".//{_HP}pic"):
                    img_info = _extract_image(pic_el, _img_id[0])
                    if img_info:
                        img_info["in_table"] = f"tbl{tbl_idx}/r{ri}c{ci}"
                        images.append(img_info)
                        _img_id[0] += 1

    # 표 크기
    sz_el = tbl_el.find(f"{_HP}sz")
    width = int(sz_el.get("width", "0")) if sz_el is not None else 0

    # 컨텍스트 추정 (첫 행 텍스트)
    first_row_texts = [c["value"] for c in cells if c["row"] == 0]
    context = " | ".join(first_row_texts[:4])

    return {
        "id": f"tbl{tbl_idx}",
        "context": context,
        "width": width,
        "rows": max((c["row"] for c in cells), default=-1) + 1,
        "cols": max((c["col"] for c in cells), default=-1) + 1,
        "cells": cells,
    }


def _extract_image(pic_el, img_idx) -> Optional[dict]:
    """<hp:pic>에서 이미지 참조 정보 추출."""
    img_el = pic_el.find(f"{_HC}img")
    if img_el is None:
        img_el = pic_el.find(f"{_HP}img")
    if img_el is None:
        return None

    bin_ref = img_el.get("binaryItemIDRef", "")
    sz_el = pic_el.find(f"{_HP}sz")
    width = int(sz_el.get("width", "0")) if sz_el is not None else 0
    height = int(sz_el.get("height", "0")) if sz_el is not None else 0

    return {
        "id": f"img{img_idx}",
        "bin_ref": bin_ref,
        "width": width,
        "height": height,
        "replaceable": True,
    }


def _collect_t_text(t_el) -> str:
    """<hp:t> 안의 텍스트 수집 (fwSpace, tab 등 포함)."""
    text = t_el.text or ""
    for child in t_el:
        tag = child.tag.split("}")[1] if "}" in child.tag else child.tag
        if tag in ("fwSpace", "nbSpace"):
            text += " "
        elif tag == "tab":
            text += "\t"
        elif tag == "lineBreak":
            text += "\n"
        if child.tail:
            text += child.tail
    return text


def _extract_cell_full_text(tc_el) -> str:
    """셀 내부 모든 <hp:t> 텍스트를 결합."""
    parts = []
    for t_el in tc_el.findall(f".//{_HP}t"):
        parts.append(_collect_t_text(t_el))
    return " ".join(parts).strip()


def _guess_cell_role(text: str, row: int, col: int) -> str:
    """셀 역할 추정: header / label / input / data."""
    if row == 0:
        return "header"
    stripped = text.strip()
    if not stripped:
        return "input"
    # 짧고 한글+공백만 → 라벨 가능성
    if len(stripped) <= 10 and re.match(r"^[가-힣\s·]+$", stripped):
        return "label"
    return "data"


def _build_style_map(header_xml: str) -> dict[int, str]:
    """header.xml에서 charPr ID → 사람이 읽을 수 있는 스타일 힌트 매핑."""
    root = ET.fromstring(header_xml)
    style_map = {}

    # 폰트 이름 매핑
    face_names = {}
    for fn in root.findall(f".//{_HH}fontface"):
        ftype = fn.get("type", "")
        for font in fn.findall(f"{_HH}font"):
            fid = int(font.get("id", "0"))
            fname = font.get("face", "")
            face_names[(ftype, fid)] = fname

    for cp in root.findall(f".//{_HH}charPr"):
        cp_id = int(cp.get("id", "0"))
        hints = []

        # 폰트 크기
        height = int(cp.get("height", "1000"))
        size_pt = height / 100
        if size_pt != 10.0:
            hints.append(f"{size_pt:.0f}pt")

        # 볼드/이탤릭
        bold = cp.get("bold", "0")
        italic = cp.get("italic", "0")
        if bold == "1":
            hints.append("볼드")
        if italic == "1":
            hints.append("이탤릭")

        # 글자색
        color_el = cp.find(f"{_HH}color")
        if color_el is not None:
            text_color = color_el.get("value", "")
            if text_color and text_color.upper() not in ("#000000", ""):
                hints.append(f"색:{text_color}")

        # 폰트 이름
        font_ref = cp.find(f"{_HH}fontRef")
        if font_ref is not None:
            hangul_id = int(font_ref.get("hangul", "0"))
            fname = face_names.get(("HANGUL", hangul_id), "")
            if fname:
                hints.append(fname)

        style_map[cp_id] = " ".join(hints) if hints else "기본"

    return style_map


# ─────────────────────────────────────────────
# apply_overlay
# ─────────────────────────────────────────────

def apply_overlay(
    source_hwpx: str,
    overlay: dict,
    output_path: str,
    *,
    image_replacements: Optional[dict[str, bytes]] = None,
) -> str:
    """수정된 overlay JSON을 원본 HWPX에 적용.

    Parameters
    ----------
    source_hwpx : str
        원본 HWPX 파일 경로
    overlay : dict
        extract_overlay()로 추출 후 수정된 overlay JSON
    output_path : str
        출력 HWPX 파일 경로
    image_replacements : dict, optional
        {bin_ref: bytes} 매핑. 이미지 바이너리 교체용.

    Returns
    -------
    str
        출력 파일 경로
    """
    # SHA256 검증
    source_bytes = Path(source_hwpx).read_bytes()
    actual_sha = hashlib.sha256(source_bytes).hexdigest()
    expected_sha = overlay.get("source_sha256", "")
    if expected_sha and actual_sha != expected_sha:
        raise ValueError(
            f"Source file changed since overlay extraction.\n"
            f"  Expected: {expected_sha[:16]}...\n"
            f"  Actual:   {actual_sha[:16]}..."
        )

    work_dir = Path(tempfile.mkdtemp(prefix="hwpx_overlay_"))

    try:
        # 1. Unpack
        subprocess.run(
            [sys.executable, "-m", "pyhwpxlib", "unpack", source_hwpx, "-o", str(work_dir)],
            check=True, capture_output=True,
        )

        # 2. Section XML 수정
        sec_path = overlay.get("section_path", f"Contents/section{overlay.get('section_idx', 0)}.xml")
        sec_file = work_dir / sec_path
        xml = sec_file.read_text(encoding="utf-8")

        # 텍스트 교체
        changes = 0
        for field in overlay.get("texts", []):
            original = field.get("original", "")
            new_value = field.get("value", "")
            if original and original != new_value:
                # XML 내부의 텍스트를 교체
                # <hp:t>원본텍스트</hp:t> → <hp:t>새텍스트</hp:t>
                old_fragment = f">{original}<"
                new_fragment = f">{new_value}<"
                if old_fragment in xml:
                    xml = xml.replace(old_fragment, new_fragment, 1)
                    changes += 1

        # 표 셀 교체
        for tbl in overlay.get("tables", []):
            for cell in tbl.get("cells", []):
                original = cell.get("original", "")
                new_value = cell.get("value", "")
                if original and original != new_value:
                    old_fragment = f">{original}<"
                    new_fragment = f">{new_value}<"
                    if old_fragment in xml:
                        xml = xml.replace(old_fragment, new_fragment, 1)
                        changes += 1

        sec_file.write_text(xml, encoding="utf-8")

        # 3. 이미지 교체
        if image_replacements:
            for bin_ref, img_bytes in image_replacements.items():
                # bin_ref → BinData/BIN0001.png 등
                bin_dir = work_dir / "BinData"
                if bin_dir.exists():
                    for f in bin_dir.iterdir():
                        if bin_ref in f.name:
                            f.write_bytes(img_bytes)
                            changes += 1

        # 4. Repack
        out = Path(output_path)
        if out.exists():
            out.unlink()
        subprocess.run(
            [sys.executable, "-m", "pyhwpxlib", "pack", str(work_dir), "-o", output_path],
            check=True, capture_output=True,
        )

        return output_path

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
