"""LineSeg handling for cross-renderer compatibility.

Background
----------
HWPX spec expects one <hp:lineseg> per visual line. Some Hancom versions
emit a single lineseg per paragraph because Hancom re-flows linesegs at
load time regardless of stored values. External viewers like rhwp trust
the stored linesegs literally and end up rendering all text on one line
when there's only one lineseg, causing visible overlap.

rhwp's validator flags this with three rules
(rhwp/src/document_core/validation.rs):

    R1 (LinesegArrayEmpty)        - text present but no linesegs
    R2 (LinesegUncomputed)        - len==1 && line_height==0
    R3 (LinesegTextRunReflow)     - len==1 && text > 40 chars && no '\\n'

R3 is a *renderer correctness* heuristic — it does NOT trigger Hancom's
"외부 수정" security warning. Hancom opens R3-violating files normally.
This module exists to keep external tooling (rhwp, custom previewers,
PDF exporters) rendering the document correctly after we replace text.

Two strategies
--------------
1. ``fix_r3_violations(section_xml, header_xml=None)``
   Split the lineseg into N entries using a width heuristic
   (Korean ≈ font_size, ASCII ≈ 0.5 * font_size, capped at 39 chars/line
   to guarantee R3 disappears). Useful when the consumer trusts stored
   linesegs and won't reflow.

2. ``strip_linesegarrays(section_xml, mode='remove'|'empty')``
   Remove the linesegarray entirely (``remove``) or leave a self-closing
   ``<hp:linesegarray/>`` (``empty``). Forces both Hancom and rhwp to
   re-flow from scratch — no width heuristic needed. Recommended when
   stored geometry is unreliable after edits.

References
----------
- rhwp/src/renderer/composer/line_breaking.rs:621 (reflow_line_segs)
- rhwp/src/document_core/commands/document.rs (reflow_linesegs_on_demand)
- rhwp/src/document_core/validation.rs (R1/R2/R3)
"""
from __future__ import annotations

import math
import re
from typing import Optional

# rhwp 호환: 1 inch = 7200 HWPUNIT, 1 inch = 25.4 mm
# 실증: 12pt -> line_height = 1200 HWPUNIT (font_size_to_line_height)
# 한글(전각) 평균 폭 ≈ line_height * 1.0
# ASCII(반각) 평균 폭 ≈ line_height * 0.5
_HANGUL_WIDTH_RATIO = 1.0
_ASCII_WIDTH_RATIO = 0.5

# R3 임계값 (rhwp validation.rs:179와 동일)
R3_MIN_TEXT_LEN = 40

# 기본 폰트 크기 (HWPUNIT). char_shape에서 못 찾을 때 fallback.
_DEFAULT_FONT_SIZE_HWP = 1000  # 10pt = 1000 HWPUNIT (한컴 기본)


def _avg_char_width_hwp(text: str, font_size_hwp: int) -> float:
    """텍스트의 평균 글자폭(HWPUNIT) 추정.

    한글/CJK는 font_size 그대로, ASCII는 0.5 * font_size로 가중평균.
    """
    if not text:
        return float(font_size_hwp)
    hangul = sum(1 for c in text if '\uac00' <= c <= '\ud7a3' or '\u3131' <= c <= '\u318e')
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u30ff')
    wide = hangul + cjk
    narrow = len(text) - wide
    total_w = wide * font_size_hwp * _HANGUL_WIDTH_RATIO + narrow * font_size_hwp * _ASCII_WIDTH_RATIO
    return total_w / len(text)


def _utf16_len(text: str) -> int:
    """UTF-16 code unit count (BMP=1, supplementary=2)."""
    return sum(1 if ord(c) <= 0xFFFF else 2 for c in text)


def count_r3_violations(section_xml: str) -> int:
    """R3 조건에 해당하는 paragraph 개수만 센다 (보고/lint 용)."""
    count = 0
    for p_match in re.finditer(r'<hp:p[\s>].*?</hp:p>', section_xml, re.DOTALL):
        p = p_match.group(0)
        ts = re.findall(r'<hp:t[^>]*>([^<]*)</hp:t>', p)
        full_text = ''.join(ts)
        if len(full_text) <= R3_MIN_TEXT_LEN or '\n' in full_text:
            continue
        lsa = re.search(r'<hp:linesegarray[^>]*>(.*?)</hp:linesegarray>', p, re.DOTALL)
        if not lsa:
            continue
        if len(re.findall(r'<hp:lineseg ', lsa.group(1))) == 1:
            count += 1
    return count


def _extract_attr(tag: str, name: str, default: Optional[str] = None) -> Optional[str]:
    m = re.search(rf'\b{name}="([^"]*)"', tag)
    return m.group(1) if m else default


def _build_linesegs(
    orig_lineseg_tag: str,
    text: str,
    font_size_hwp: int,
) -> str:
    """원본 lineseg 1개 → R3 회피용 N개 lineseg로 분할.

    원본의 dimension(vertsize/textheight/baseline/spacing/horzsize/horzpos/flags)
    은 그대로 보존하고, textpos와 vertpos만 다시 계산한다.
    """
    seg_width = int(_extract_attr(orig_lineseg_tag, 'horzsize', '42520') or '42520')
    vert_size = int(_extract_attr(orig_lineseg_tag, 'vertsize', '1000') or '1000')
    spacing = int(_extract_attr(orig_lineseg_tag, 'spacing', '600') or '600')
    vert_pos_start = int(_extract_attr(orig_lineseg_tag, 'vertpos', '0') or '0')

    if seg_width <= 0:
        return orig_lineseg_tag  # 분할 불가

    avg_w = _avg_char_width_hwp(text, font_size_hwp)
    if avg_w <= 0:
        return orig_lineseg_tag

    chars_per_line = max(1, int(seg_width / avg_w))
    # 한컴은 어절 단위로 줄바꿈하므로 우리 추정보다 더 짧게 끊는다.
    # R3 위반(40자+)을 만든 케이스라면 한 줄에 R3_MIN_TEXT_LEN 이상은 들어갈 수 없다고
    # 가정하는 것이 안전 (한컴 reflow가 결과적으로 더 분할할 수 있음).
    chars_per_line = min(chars_per_line, R3_MIN_TEXT_LEN - 1)
    text_len = len(text)
    n_lines = max(2, math.ceil(text_len / chars_per_line))

    # textpos는 UTF-16 offset이지만 R3 회피만 목적이라면 char index로도 충분
    # (한컴은 textpos 단조증가만 검증)
    # 한글 위주이므로 char index ≈ UTF-16 unit 가정.
    pieces = []
    vpos = vert_pos_start
    for i in range(n_lines):
        start_char = i * chars_per_line
        # UTF-16 위치 보정
        if start_char >= text_len:
            utf16_start = _utf16_len(text)
        else:
            utf16_start = _utf16_len(text[:start_char])
        new_tag = re.sub(
            r'\btextpos="[^"]*"',
            f'textpos="{utf16_start}"',
            orig_lineseg_tag,
        )
        new_tag = re.sub(
            r'\bvertpos="[^"]*"',
            f'vertpos="{vpos}"',
            new_tag,
        )
        pieces.append(new_tag)
        vpos += vert_size + spacing
    return ''.join(pieces)


def _detect_font_size_hwp(paragraph_xml: str, header_xml: Optional[str] = None) -> int:
    """paragraph의 첫 charPr/run 의 font size 추정. 못 찾으면 기본값."""
    # paragraph 안의 첫 hp:run 의 charPrIDRef 추출
    run_m = re.search(r'<hp:run[^>]*\bcharPrIDRef="(\d+)"', paragraph_xml)
    if run_m and header_xml:
        cpid = run_m.group(1)
        # header.xml에서 해당 charPr 찾고 hh:sz 의 ratio 또는 sz 값으로 폰트 크기 추출
        # OWPML: <hh:charPr id="0" height="1000" .../>
        cp_m = re.search(
            rf'<hh:charPr[^>]*\bid="{cpid}"[^>]*\bheight="(\d+)"',
            header_xml,
        )
        if cp_m:
            return int(cp_m.group(1))
    return _DEFAULT_FONT_SIZE_HWP


def fix_r3_violations(
    section_xml: str,
    header_xml: Optional[str] = None,
) -> tuple[str, int]:
    """section0.xml 안의 R3 위반 문단들의 linesegarray를 분할하여 R3 회피.

    Returns
    -------
    (fixed_xml, fixed_count)
    """
    fixed_count = 0
    out = []
    pos = 0

    for p_match in re.finditer(r'<hp:p[\s>].*?</hp:p>', section_xml, re.DOTALL):
        out.append(section_xml[pos:p_match.start()])
        p = p_match.group(0)
        pos = p_match.end()

        # R3 검사
        ts = re.findall(r'<hp:t[^>]*>([^<]*)</hp:t>', p)
        full_text = ''.join(ts)
        if len(full_text) <= R3_MIN_TEXT_LEN or '\n' in full_text:
            out.append(p)
            continue

        lsa_m = re.search(
            r'(<hp:linesegarray[^>]*>)(.*?)(</hp:linesegarray>)',
            p,
            re.DOTALL,
        )
        if not lsa_m:
            out.append(p)
            continue

        inner = lsa_m.group(2)
        single_segs = re.findall(r'<hp:lineseg [^/]*/>', inner)
        if len(single_segs) != 1:
            out.append(p)
            continue

        # R3 위반 확정 -> 분할
        font_size_hwp = _detect_font_size_hwp(p, header_xml)
        new_inner = _build_linesegs(single_segs[0], full_text, font_size_hwp)
        if new_inner == single_segs[0]:
            out.append(p)
            continue

        new_lsa = lsa_m.group(1) + new_inner + lsa_m.group(3)
        new_p = p[:lsa_m.start()] + new_lsa + p[lsa_m.end():]
        out.append(new_p)
        fixed_count += 1

    out.append(section_xml[pos:])
    return ''.join(out), fixed_count


def reflow_section_xml(
    section_xml: str,
    header_xml: Optional[str] = None,
) -> str:
    """fix_r3_violations의 단순 wrapper (count 무시)."""
    fixed, _ = fix_r3_violations(section_xml, header_xml)
    return fixed


def strip_linesegs_in_section_xmls(
    section_files: dict[str, bytes],
    mode: str = "remove",
) -> tuple[dict[str, bytes], int]:
    """Convenience: section*.xml dict 전체에 strip 적용.

    Returns (new_files, total_stripped).
    """
    new_files = dict(section_files)
    total = 0
    for name, raw in section_files.items():
        if not (name.startswith("Contents/section") and name.endswith(".xml")):
            continue
        try:
            xml = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        new_xml, n = strip_linesegarrays(xml, mode=mode)
        if n > 0:
            new_files[name] = new_xml.encode("utf-8")
            total += n
    return new_files, total


def strip_linesegarrays(
    section_xml: str,
    mode: str = "remove",
) -> tuple[str, int]:
    """모든 linesegarray 블록을 제거 또는 비움.

    Hancom과 rhwp 모두 빈/없는 linesegarray를 만나면 자체 reflow를 수행한다.
    텍스트 교체 후 stored geometry가 부정확할 때 가장 안전한 처리.

    Parameters
    ----------
    section_xml : str
        section0.xml 등의 원본 XML.
    mode : {'remove', 'empty'}
        'remove' — `<hp:linesegarray>...</hp:linesegarray>` 통째 삭제.
        'empty'  — 내부만 비우고 `<hp:linesegarray></hp:linesegarray>` 유지.

    Returns
    -------
    (new_xml, stripped_count)
    """
    if mode not in ("remove", "empty"):
        raise ValueError(f"mode must be 'remove' or 'empty', got {mode!r}")

    count = 0

    def _repl(m: re.Match) -> str:
        nonlocal count
        count += 1
        if mode == "remove":
            return ""
        # 'empty' — 여는 태그 보존 (속성 있을 수 있음)
        opening = re.match(r'<hp:linesegarray[^>]*>', m.group(0)).group(0)
        return f"{opening}</hp:linesegarray>"

    new_xml = re.sub(
        r'<hp:linesegarray[^>]*>.*?</hp:linesegarray>',
        _repl,
        section_xml,
        flags=re.DOTALL,
    )
    return new_xml, count
