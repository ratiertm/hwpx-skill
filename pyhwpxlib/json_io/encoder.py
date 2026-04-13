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
            sec = _parse_section(sec_xml)
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
    )
    return doc.to_dict()


def _parse_section(xml_str: str) -> Section:
    """Parse section XML into Section dataclass."""
    root = ET.fromstring(xml_str)

    # Page settings
    page = _parse_page_settings(root)

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

        # Check for inline table
        tbl_el = run_el.find(f'{_HP}tbl')
        if tbl_el is not None:
            tbl = _parse_table(tbl_el)
            tables.append(tbl)
            runs.append(Run(
                content=RunContent(type="table", table=len(tables) - 1),
                char_shape_id=char_shape_id,
            ))
            continue

        # Text content
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
