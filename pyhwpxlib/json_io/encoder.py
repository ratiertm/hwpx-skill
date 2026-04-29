"""HWPX → JSON encoder.

Parses HWPX file and produces a JSON-serializable HwpxJsonDocument.
Leverages form_pipeline's XML extraction patterns.
"""
from __future__ import annotations

import hashlib
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from .schema import (
    HwpxJsonDocument, Section, Paragraph, Run, RunContent,
    Table, TableRow, TableCell, PageSettings, Preservation,
    Image, Footnote, Equation, Shape, HeaderFooter, PageNumber,
)

_HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
_HH = "{http://www.hancom.co.kr/hwpml/2011/head}"


def to_json(hwpx_path: str, section_idx: Optional[int] = None) -> dict:
    """Export HWPX to JSON dict.

    Parameters
    ----------
    hwpx_path : str
        Path to .hwpx file
    section_idx : int, optional
        If given, export only this section (0-based). Includes preservation
        metadata for later patching.

    Returns
    -------
    dict
        JSON-serializable document structure
    """
    path = Path(hwpx_path)
    file_bytes = path.read_bytes()
    sha256 = hashlib.sha256(file_bytes).hexdigest()

    top_level: dict = {"header": None, "footer": None, "page_number": None}

    with zipfile.ZipFile(hwpx_path) as z:
        # Find section files
        section_files = sorted(
            n for n in z.namelist()
            if re.match(r'Contents/section\d+\.xml', n)
        )
        header_xml = z.read('Contents/header.xml').decode('utf-8')

        sections = []
        for si, sec_name in enumerate(section_files):
            if section_idx is not None and si != section_idx:
                continue
            sec_xml = z.read(sec_name).decode('utf-8')
            sec = _parse_section(sec_xml, top_level=top_level)
            sections.append(sec)

    preservation = None
    if section_idx is not None and section_idx < len(section_files):
        sec_bytes = zipfile.ZipFile(hwpx_path).read(section_files[section_idx])
        preservation = Preservation(
            source_sha256=sha256,
            section_path=section_files[section_idx],
            raw_header_xml=header_xml,
        )

    doc = HwpxJsonDocument(
        source=path.name,
        source_sha256=sha256,
        sections=sections,
        preservation=preservation,
        header=top_level["header"],
        footer=top_level["footer"],
        page_number=top_level["page_number"],
    )
    return doc.to_dict()


def _parse_section(xml_str: str, *, top_level: dict | None = None) -> Section:
    """Parse section XML into Section dataclass.

    When ``top_level`` is provided (a mutable dict with keys ``header``,
    ``footer``, ``page_number``), this function will detect the matching
    section-level constructs (``<hp:header>``, ``<hp:footer>``,
    ``<hp:autoNum>`` / ``<hp:pageNum>``) and populate the dict so the
    caller can attach them to the top-level ``HwpxJsonDocument``. This
    mirrors HwpxBuilder's deferred-actions pattern on the encode side.
    """
    root = ET.fromstring(xml_str)

    # Page settings
    page = _parse_page_settings(root)

    # Top-level rich elements (best-effort, first occurrence wins)
    if top_level is not None:
        if top_level.get("header") is None:
            hdr = root.find(f'.//{_HP}header')
            if hdr is not None:
                txt = "".join(t.text or "" for t in hdr.findall(f'.//{_HP}t'))
                if txt:
                    top_level["header"] = HeaderFooter(text=txt)
        if top_level.get("footer") is None:
            ftr = root.find(f'.//{_HP}footer')
            if ftr is not None:
                txt = "".join(t.text or "" for t in ftr.findall(f'.//{_HP}t'))
                if txt:
                    top_level["footer"] = HeaderFooter(text=txt)
        if top_level.get("page_number") is None:
            pn = root.find(f'.//{_HP}autoNum')
            if pn is None:
                pn = root.find(f'.//{_HP}pageNum')
            if pn is not None:
                pos = pn.get("pos") or pn.get("position") or "BOTTOM_CENTER"
                top_level["page_number"] = PageNumber(pos=pos)

    # Paragraphs + inline tables
    paragraphs = []
    tables = []
    for p_el in root.findall(f'.//{_HP}p'):
        para, inline_tables = _parse_paragraph(p_el)
        paragraphs.append(para)
        tables.extend(inline_tables)

    return Section(paragraphs=paragraphs, page_settings=page, tables=tables)


def _parse_page_settings(root) -> PageSettings:
    pp = root.find(f'.//{_HP}pagePr')
    if pp is None:
        return PageSettings()
    margin = pp.find(f'{_HP}margin')
    return PageSettings(
        width=int(pp.get('width', 59528)),
        height=int(pp.get('height', 84186)),
        landscape=pp.get('landscape', 'WIDELY'),
        margin_left=int(margin.get('left', 8504)) if margin is not None else 8504,
        margin_right=int(margin.get('right', 8504)) if margin is not None else 8504,
        margin_top=int(margin.get('top', 5668)) if margin is not None else 5668,
        margin_bottom=int(margin.get('bottom', 4252)) if margin is not None else 4252,
        header_margin=int(margin.get('header', 4252)) if margin is not None else 4252,
        footer_margin=int(margin.get('footer', 4252)) if margin is not None else 4252,
    )


def _parse_paragraph(p_el) -> tuple[Paragraph, list[Table]]:
    """Parse <hp:p> element. Returns (Paragraph, list of inline Tables)."""
    runs = []
    tables = []

    para_shape_id = int(p_el.get('paraPrIDRef', '0'))
    page_break = p_el.get('pageBreak', '0') == '1'

    for run_el in p_el.findall(f'{_HP}run'):
        char_shape_id = int(run_el.get('charPrIDRef', '0'))

        # ── Rich-type detection (v0.15.0 best-effort, FR-09) ──
        # Order matters: more specific elements first.
        rich = _detect_rich_run(run_el)
        if rich is not None:
            if rich.type == "table":
                # Resolve inline table — appended to the table list
                tbl_el = run_el.find(f'{_HP}tbl')
                if tbl_el is not None:
                    tbl = _parse_table(tbl_el)
                    tables.append(tbl)
                    rich.table = len(tables) - 1
            runs.append(Run(content=rich, char_shape_id=char_shape_id))
            continue

        # Text content (default)
        text_parts = []
        for t_el in run_el.findall(f'{_HP}t'):
            # Collect text including child elements (fwSpace, tab, etc.)
            t_text = t_el.text or ''
            for child in t_el:
                tag = child.tag.split('}')[1] if '}' in child.tag else child.tag
                if tag == 'fwSpace':
                    t_text += ' '
                elif tag == 'nbSpace':
                    t_text += ' '
                elif tag == 'tab':
                    t_text += '\t'
                elif tag == 'lineBreak':
                    t_text += '\n'
                if child.tail:
                    t_text += child.tail
            text_parts.append(t_text)

        text = ''.join(text_parts)
        runs.append(Run(
            content=RunContent(type="text", text=text),
            char_shape_id=char_shape_id,
        ))

    return Paragraph(runs=runs, para_shape_id=para_shape_id, page_break=page_break), tables


def _detect_rich_run(run_el) -> Optional[RunContent]:
    """Detect a v0.15.0 rich RunContent by inspecting the run's children.

    Returns ``None`` if no rich element found (caller falls through to
    plain text extraction). Best-effort coverage matching FR-09:
      - <hp:tbl>      → type="table" (caller resolves the index)
      - <hp:pic>      → type="image" (Image with current-size dimensions)
      - <hp:footNote> → type="footnote"
      - <hp:equation> → type="equation"
      - <hp:rect>     → type="shape_rect"
      - <hp:line>     → type="shape_line"

    Heading / list / highlight detection requires style-table lookup and
    is intentionally deferred (see Plan FR-09 risk row).
    """
    # Inline table — caller resolves table index
    if run_el.find(f'{_HP}tbl') is not None:
        return RunContent(type="table")

    # Image: <hp:pic>
    pic = run_el.find(f'.//{_HP}pic')
    if pic is not None:
        cur = pic.find(f'{_HP}curSz')
        width = int(cur.get('width')) if cur is not None and cur.get('width') else None
        height = int(cur.get('height')) if cur is not None and cur.get('height') else None
        href = pic.get('href') or ''
        return RunContent(type="image",
                          image=Image(image_path=href or None,
                                       width=width, height=height))

    # Footnote: <hp:footNote>
    fn = run_el.find(f'.//{_HP}footNote')
    if fn is not None:
        txt = "".join(t.text or "" for t in fn.findall(f'.//{_HP}t'))
        try:
            number = int(fn.get('number') or 1)
        except (TypeError, ValueError):
            number = 1
        return RunContent(type="footnote",
                          footnote=Footnote(text=txt, number=number))

    # Equation: <hp:equation>
    eq = run_el.find(f'.//{_HP}equation')
    if eq is not None:
        # Equation script lives in <hp:script> child
        script_el = eq.find(f'{_HP}script')
        script = (script_el.text or '') if script_el is not None else ''
        return RunContent(type="equation", equation=Equation(script=script))

    # Rectangle: <hp:rect>
    rect = run_el.find(f'.//{_HP}rect')
    if rect is not None:
        return RunContent(type="shape_rect",
                          shape=_extract_shape_from(rect))

    # Line: <hp:line>
    line = run_el.find(f'.//{_HP}line')
    if line is not None:
        # Distinguish shape_line vs shape_draw_line — both render as a line.
        # Default to shape_line; a future enhancement could detect
        # explicit endpoint coordinates to emit shape_draw_line instead.
        return RunContent(type="shape_line")

    return None


def _extract_shape_from(el) -> Shape:
    """Pull width/height + offset coordinates from a shape element."""
    cur = el.find(f'{_HP}curSz')
    off = el.find(f'{_HP}offset')
    width = int(cur.get('width')) if cur is not None and cur.get('width') else 14400
    height = int(cur.get('height')) if cur is not None and cur.get('height') else 7200
    x1 = int(off.get('x', 0)) if off is not None else 0
    y1 = int(off.get('y', 0)) if off is not None else 0
    return Shape(width=width, height=height, x1=x1, y1=y1,
                 x2=x1 + width, y2=y1)


def _parse_table(tbl_el) -> Table:
    """Parse <hp:tbl> element into Table dataclass."""
    # Size
    sz = tbl_el.find(f'{_HP}sz')
    width = int(sz.get('width', 0)) if sz is not None else 0
    height = int(sz.get('height', 0)) if sz is not None else 0

    # Rows
    rows = []
    for tr_el in tbl_el.findall(f'{_HP}tr'):
        cells = []
        for tc_el in tr_el.findall(f'{_HP}tc'):
            cell_text = _extract_cell_text(tc_el)
            cell_sz = tc_el.find(f'{_HP}cellSz')
            cell_span = tc_el.find(f'{_HP}cellSpan')
            cells.append(TableCell(
                text=cell_text,
                col_span=int(cell_span.get('colSpan', 1)) if cell_span is not None else 1,
                row_span=int(cell_span.get('rowSpan', 1)) if cell_span is not None else 1,
                width=int(cell_sz.get('width', 0)) if cell_sz is not None else 0,
                height=int(cell_sz.get('height', 0)) if cell_sz is not None else 0,
            ))
        # Row height from first cell or 0
        rh = cells[0].height if cells else 0
        rows.append(TableRow(cells=cells, height=rh))

    return Table(rows=rows, width=width, height=height)


def _extract_cell_text(tc_el) -> str:
    """Extract all text from a table cell."""
    texts = []
    for t_el in tc_el.findall(f'.//{_HP}t'):
        if t_el.text:
            texts.append(t_el.text)
        for child in t_el:
            if child.tail:
                texts.append(child.tail)
    return ' '.join(texts).strip()
