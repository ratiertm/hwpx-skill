"""Overlay 방식 JSON 편집 — 원본 서식 100% 보존.

extract_overlay: HWPX → 편집 가능한 필드만 추출 (텍스트, 표 셀, 이미지 참조)
apply_overlay:   수정된 overlay JSON → 원본 XML에 적용 → 새 HWPX
"""
from __future__ import annotations

import base64
import hashlib
import re
import xml.etree.ElementTree as ET
import xml.sax.saxutils
import zipfile
from pathlib import Path
from typing import Optional

from ..package_ops import read_zip_archive, write_zip_archive

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

    # 공문 라이선스 메타데이터 (공공누리/CCL) — 있으면 summary에 노출
    try:
        from ..gongmun.reader import license_summary
        _license = license_summary(path)
    except Exception:
        _license = None

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
            "license": _license,   # "KOGL-1" / "CCL-BY-SA" / None
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

        # 텍스트 — run 내 모든 <hp:t>를 하나의 엔트리로 수집
        t_elements = run_el.findall(f"{_HP}t")
        if t_elements:
            parts = [_collect_t_text(t) for t in t_elements]
            joined = "".join(parts)
            if joined.strip():
                texts.append({
                    "id": f"t{_text_id[0]}",
                    "location": f"{prefix}/run{ri}",
                    "value": joined,
                    "original": joined,
                    "original_parts": parts,
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
            # 셀 텍스트 + 파트 + run 경계
            cell_text, cell_parts, cell_runs = _extract_cell_parts(tc_el)

            # 셀 역할 추정
            role = _guess_cell_role(cell_text, ri, ci)

            cell_entry = {
                "row": ri,
                "col": ci,
                "value": cell_text,
                "original": cell_text,
                "original_parts": cell_parts,
                "original_runs": cell_runs,
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

            # 셀 내부 중첩 표 재귀 — 직속 자식 표만 탐색 (깊은 자손 제외)
            # 구조: <hp:tc> -> <hp:subList> -> <hp:p> -> <hp:run> -> <hp:tbl>
            # .//{_HP}tbl 은 모든 자손을 매칭하여 중복 추출 발생
            direct_tables = []
            for sub_list in tc_el.findall(f"{_HP}subList"):
                for p_el in sub_list.findall(f"{_HP}p"):
                    for run_el in p_el.findall(f"{_HP}run"):
                        tbl = run_el.find(f"{_HP}tbl")
                        if tbl is not None:
                            direct_tables.append(tbl)

            for inner_tbl in direct_tables:
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
    """셀 내부 모든 <hp:t> 텍스트를 결합 (공백 없이)."""
    parts = []
    for t_el in tc_el.findall(f".//{_HP}t"):
        parts.append(_collect_t_text(t_el))
    return "".join(parts).strip()


def _extract_cell_parts(tc_el) -> tuple[str, list[str], list[dict]]:
    """셀 내부 모든 <hp:t> 텍스트, 파트, run 경계 정보를 반환.

    Returns
    -------
    tuple[str, list[str], list[dict]]
        (joined_text, individual_hp_t_parts, run_boundaries)
        run_boundaries: [{"charPr": "18", "parts": ["텍스트"], "offset": 0, "length": 7}, ...]
    """
    parts = []
    runs = []
    offset = 0
    for p_el in tc_el.findall(f".//{_HP}p"):
        for run_el in p_el.findall(f"{_HP}run"):
            char_pr = run_el.get("charPrIDRef", "0")
            run_parts = []
            for t_el in run_el.findall(f"{_HP}t"):
                t_text = _collect_t_text(t_el)
                run_parts.append(t_text)
                parts.append(t_text)
            if run_parts:
                run_text = "".join(run_parts)
                runs.append({
                    "charPr": char_pr,
                    "parts": run_parts,
                    "offset": offset,
                    "length": len(run_text),
                })
                offset += len(run_text)
    return "".join(parts).strip(), parts, runs


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
# XML text replacement helpers
# ─────────────────────────────────────────────


def _xml_escape(text: str) -> str:
    """XML 특수 문자 이스케이프."""
    return xml.sax.saxutils.escape(text)


def _replace_text_in_xml(xml_str: str, original_parts: list[str], new_value: str) -> str:
    """원본 <hp:t> 파트를 새 값으로 교체.

    Single part: 단순 문자열 교체.
    Multi part: regex로 <hp:t>part1</hp:t>...<hp:t>partN</hp:t> 패턴 매칭 후
                <hp:t>new_value</hp:t>로 교체.
    """
    if len(original_parts) == 1:
        old = f">{_xml_escape(original_parts[0])}<"
        new = f">{_xml_escape(new_value)}<"
        return xml_str.replace(old, new, 1)

    # Multi-<hp:t> case: build regex pattern
    escaped_parts = [re.escape(_xml_escape(p)) for p in original_parts]
    parts_pattern = r"</hp:t>\s*<hp:t>".join(escaped_parts)
    full_pattern = f"<hp:t>{parts_pattern}</hp:t>"
    replacement = f"<hp:t>{_xml_escape(new_value)}</hp:t>"
    return re.sub(full_pattern, replacement, xml_str, count=1)


def _replace_cell_parts_individually(
    xml_str: str,
    original_parts: list[str],
    original_joined: str,
    new_value: str,
    original_runs: list[dict] | None = None,
) -> str:
    """셀의 파트가 다른 <hp:run>에 걸칠 때 run 단위로 교체.

    original_runs가 있으면 run 경계 정보를 사용하여
    new_value를 각 run에 정확히 분배합니다.
    """
    if original_runs:
        return _replace_by_runs(xml_str, original_runs, original_joined, new_value)

    # fallback — run 정보 없으면 파트별 단순 교체
    for part in original_parts:
        part_stripped = part.strip()
        if not part_stripped:
            continue
        old_fragment = f">{_xml_escape(part)}<"
        if old_fragment in xml_str and part_stripped not in new_value:
            # 변경된 파트 — 빈 문자열로 교체 (첫 run에 전체 텍스트를 넣는 방식)
            xml_str = xml_str.replace(old_fragment, f"><", 1)
    return xml_str


def _replace_by_runs(
    xml_str: str,
    original_runs: list[dict],
    original_joined: str,
    new_value: str,
) -> str:
    """run 경계 정보를 사용하여 각 run의 텍스트를 개별 교체.

    각 run의 원본 텍스트에서 해당 run에 적용해야 할 교체를
    원본→수정 매핑에서 개별 추출하여 적용합니다.
    """
    # 각 run에 대해 개별 diff 계산
    # original_joined에서 이 run이 차지하는 범위의 텍스트와
    # new_value에서 대응하는 범위를 비교

    # 1단계: 각 run의 원본 텍스트 → new_value에서 대응하는 텍스트 계산
    #         방법: run별 개별 교체값 = apply_same_replacements(run_text)
    #         이를 위해 원본→수정 diff를 run 단위로 분해

    # 원본과 수정 값을 run offset으로 정렬
    # new_value에서 각 run에 대응하는 부분을 역산
    run_new_texts = _distribute_new_value_to_runs(original_runs, original_joined, new_value)

    for i, run in enumerate(original_runs):
        run_text = "".join(run["parts"])
        if not run_text.strip():
            continue

        new_run_text = run_new_texts.get(i, run_text)

        # 보호: 원본 run 텍스트가 new_value에 그대로 포함되면 변경하지 않음
        # (변경되지 않은 run을 비례 분배가 깨뜨리는 것 방지)
        if run_text.strip() in new_value and new_run_text != run_text:
            # 원본이 그대로 있으니 건드리지 않음
            continue

        if new_run_text != run_text:
            for part in run["parts"]:
                old_fragment = f">{_xml_escape(part)}<"
                if old_fragment in xml_str:
                    new_fragment = f">{_xml_escape(new_run_text)}<"
                    xml_str = xml_str.replace(old_fragment, new_fragment, 1)
                    new_run_text = ""

    return xml_str


def _distribute_new_value_to_runs(
    original_runs: list[dict],
    original_joined: str,
    new_value: str,
) -> dict[int, str]:
    """각 run에 대응하는 new_value 부분을 계산.

    difflib.SequenceMatcher로 original_joined과 new_value의
    문자 매핑을 구하고, 각 run의 offset 범위에 해당하는
    new_value 문자들을 추출합니다.
    """
    import difflib

    # character-level 매핑: original[i] → new_value[j]
    sm = difflib.SequenceMatcher(None, original_joined, new_value)
    opcodes = sm.get_opcodes()

    # original의 각 문자 위치 → new_value에서의 대응 범위
    # char_map[orig_pos] = (new_start, new_end)
    orig_to_new: dict[int, tuple[int, int]] = {}
    for op, i1, i2, j1, j2 in opcodes:
        if op == 'equal':
            for k in range(i2 - i1):
                orig_to_new[i1 + k] = (j1 + k, j1 + k + 1)
        elif op == 'replace':
            # 비례 배분
            old_len = i2 - i1
            new_len = j2 - j1
            for k in range(old_len):
                ns = j1 + int(k * new_len / old_len)
                ne = j1 + int((k + 1) * new_len / old_len)
                orig_to_new[i1 + k] = (ns, ne)
        elif op == 'delete':
            for k in range(i2 - i1):
                orig_to_new[i1 + k] = (j1, j1)  # 삭제됨
        # insert는 original에 대응 없음

    # 각 run의 offset → new_value 범위 추출
    result = {}
    for idx, run in enumerate(original_runs):
        offset = run["offset"]
        length = run["length"]
        if length == 0:
            continue

        # 이 run이 매핑되는 new_value 범위
        new_positions = set()
        for k in range(offset, offset + length):
            if k in orig_to_new:
                ns, ne = orig_to_new[k]
                for p in range(ns, ne):
                    new_positions.add(p)

        if new_positions:
            new_start = min(new_positions)
            new_end = max(new_positions) + 1
            result[idx] = new_value[new_start:new_end]
        else:
            result[idx] = ""  # 이 run은 삭제됨

    return result


def _build_diff_map(original: str, new_value: str) -> list[tuple[str, str]]:
    """단어 단위 diff로 변경 부분을 (old, new) 쌍 리스트로 추출.

    한글/영문/숫자를 토큰 단위로 비교하여 정확한 교체 쌍을 생성합니다.
    예: "울산중부소방서 119재난대응과 ☎ 052) 210-4462"
      → [("울산중부소방서", "강남구청"), ("119재난대응과", "생활안전과"), ...]
    """
    import difflib

    def _tokenize(s: str) -> list[str]:
        return re.findall(r'[\w]+|[^\w\s]|\s+', s)

    old_tokens = _tokenize(original)
    new_tokens = _tokenize(new_value)

    sm = difflib.SequenceMatcher(None, old_tokens, new_tokens)
    diffs = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ('replace', 'delete', 'insert'):
            old_chunk = ''.join(old_tokens[i1:i2])
            new_chunk = ''.join(new_tokens[j1:j2])
            if old_chunk or new_chunk:
                diffs.append((old_chunk, new_chunk))
    return diffs


# ─────────────────────────────────────────────
# apply_overlay
# ─────────────────────────────────────────────

def apply_overlay(
    source_hwpx: str,
    overlay: dict,
    output_path: str,
    *,
    image_replacements: Optional[dict[str, bytes]] = None,
    fix_linesegs: bool = False,
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

    sec_path = overlay.get("section_path", f"Contents/section{overlay.get('section_idx', 0)}.xml")

    archive = read_zip_archive(source_hwpx)
    xml_str = archive.files[sec_path].decode("utf-8")

    # 텍스트 교체
    for field in overlay.get("texts", []):
        original = field.get("original", "")
        new_value = field.get("value", "")
        if original and original != new_value:
            parts = field.get("original_parts", [original])
            xml_str = _replace_text_in_xml(xml_str, parts, new_value)

    # 표 셀 교체 — 셀은 여러 <hp:run>에 걸치므로 파트별 개별 교체
    for tbl in overlay.get("tables", []):
        for cell in tbl.get("cells", []):
            original = cell.get("original", "")
            new_value = cell.get("value", "")
            if original and original != new_value:
                parts = cell.get("original_parts", [original])
                # 먼저 multi-part regex 시도
                before = xml_str
                xml_str = _replace_text_in_xml(xml_str, parts, new_value)
                if xml_str == before and len(parts) > 1:
                    # regex 실패 — 파트가 다른 <hp:run>에 걸침
                    # run 경계 정보로 정밀 교체
                    xml_str = _replace_cell_parts_individually(
                        xml_str, parts, original, new_value,
                        original_runs=cell.get("original_runs"),
                    )

    archive.files[sec_path] = xml_str.encode("utf-8")

    if image_replacements:
        for info in archive.infos:
            if not info.filename.startswith("BinData/"):
                continue
            bin_stem = Path(info.filename).stem
            if bin_stem in image_replacements:
                archive.files[info.filename] = image_replacements[bin_stem]

    out = Path(output_path)
    if out.exists():
        out.unlink()
    write_zip_archive(output_path, archive, strip_linesegs=("precise" if fix_linesegs else False))

    return output_path
