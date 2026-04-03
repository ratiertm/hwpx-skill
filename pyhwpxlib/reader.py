"""HWPX file reader — parse .hwpx files for text extraction and analysis.

Opens a .hwpx file (ZIP), normalizes namespaces, and parses the XML into
lightweight dataclasses suitable for text extraction and content analysis.
"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Namespace constants (canonical 2011 URIs)
# ---------------------------------------------------------------------------

_HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
_HS_NS = "http://www.hancom.co.kr/hwpml/2011/section"
_HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
_HC_NS = "http://www.hancom.co.kr/hwpml/2011/core"

HP = f"{{{_HP_NS}}}"
HS = f"{{{_HS_NS}}}"
HH = f"{{{_HH_NS}}}"
HC = f"{{{_HC_NS}}}"

_SECTION_RE = re.compile(r"^Contents/section\d+\.xml$", re.IGNORECASE)

# Namespace normalization: map 2016/2024 variants back to canonical 2011
_NS_REPLACEMENTS = [
    (b"http://www.hancom.co.kr/hwpml/2016/paragraph", b"http://www.hancom.co.kr/hwpml/2011/paragraph"),
    (b"http://www.hancom.co.kr/hwpml/2024/paragraph", b"http://www.hancom.co.kr/hwpml/2011/paragraph"),
    (b"http://www.hancom.co.kr/hwpml/2016/section", b"http://www.hancom.co.kr/hwpml/2011/section"),
    (b"http://www.hancom.co.kr/hwpml/2024/section", b"http://www.hancom.co.kr/hwpml/2011/section"),
    (b"http://www.hancom.co.kr/hwpml/2016/head", b"http://www.hancom.co.kr/hwpml/2011/head"),
    (b"http://www.hancom.co.kr/hwpml/2024/head", b"http://www.hancom.co.kr/hwpml/2011/head"),
    (b"http://www.hancom.co.kr/hwpml/2016/core", b"http://www.hancom.co.kr/hwpml/2011/core"),
    (b"http://www.hancom.co.kr/hwpml/2024/core", b"http://www.hancom.co.kr/hwpml/2011/core"),
]


def _normalize_ns(raw: bytes) -> bytes:
    """Replace 2016/2024 namespace URIs with their 2011 equivalents."""
    for old, new in _NS_REPLACEMENTS:
        if old in raw:
            raw = raw.replace(old, new)
    return raw


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class HwpxRun:
    """A text run within a paragraph."""
    char_pr_id_ref: str = "0"
    text: str = ""
    is_table: bool = False
    is_shape: bool = False


@dataclass
class HwpxParagraph:
    """A paragraph in the document."""
    id: str = ""
    para_pr_id_ref: str = "0"
    style_id_ref: str = "0"
    runs: List[HwpxRun] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs if not r.is_table and not r.is_shape)


@dataclass
class HwpxTableCell:
    """A table cell."""
    row: int = 0
    col: int = 0
    col_span: int = 1
    row_span: int = 1
    text: str = ""
    paragraphs: List[HwpxParagraph] = field(default_factory=list)


@dataclass
class HwpxTable:
    """A table in the document."""
    rows: int = 0
    cols: int = 0
    cells: List[HwpxTableCell] = field(default_factory=list)

    def to_2d(self) -> List[List[str]]:
        """Return row-major 2D list of cell text values."""
        if not self.cells:
            return []
        grid: List[List[str]] = [[""] * self.cols for _ in range(self.rows)]
        for cell in self.cells:
            if 0 <= cell.row < self.rows and 0 <= cell.col < self.cols:
                grid[cell.row][cell.col] = cell.text
        return grid


@dataclass
class HwpxSection:
    """A section in the document."""
    paragraphs: List[HwpxParagraph] = field(default_factory=list)
    tables: List[HwpxTable] = field(default_factory=list)


@dataclass
class HwpxDocument:
    """Parsed HWPX document for reading."""
    sections: List[HwpxSection] = field(default_factory=list)
    images: List[str] = field(default_factory=list)  # BinData paths

    @classmethod
    def open(cls, filepath: str) -> "HwpxDocument":
        """Open and parse a .hwpx file."""
        doc = cls()
        with zipfile.ZipFile(filepath, "r") as zf:
            # Discover section files
            section_names = sorted(
                n for n in zf.namelist() if _SECTION_RE.match(n)
            )
            if not section_names:
                # Fallback: look in content.hpf manifest
                section_names = _find_sections_from_manifest(zf)

            for sec_name in section_names:
                raw = _normalize_ns(zf.read(sec_name))
                root = ET.fromstring(raw)
                section = _parse_section(root)
                doc.sections.append(section)

            # Collect BinData image paths
            doc.images = [
                n for n in zf.namelist()
                if n.startswith("BinData/") and not n.endswith("/")
            ]

        return doc

    @property
    def text(self) -> str:
        """Extract all text from the document."""
        parts: list[str] = []
        for section in self.sections:
            for para in section.paragraphs:
                t = para.text
                if t:
                    parts.append(t)
            for table in section.tables:
                for row in table.to_2d():
                    parts.append("\t".join(row))
        return "\n".join(parts)

    @property
    def paragraphs(self) -> List[HwpxParagraph]:
        """All paragraphs across all sections."""
        result: list[HwpxParagraph] = []
        for section in self.sections:
            result.extend(section.paragraphs)
        return result


# ---------------------------------------------------------------------------
# Internal parsing helpers
# ---------------------------------------------------------------------------

def _find_sections_from_manifest(zf: zipfile.ZipFile) -> List[str]:
    """Parse Contents/content.hpf to find section file paths."""
    try:
        raw = _normalize_ns(zf.read("Contents/content.hpf"))
    except KeyError:
        return []

    root = ET.fromstring(raw)
    section_names: list[str] = []
    # Walk all elements looking for item entries with section hrefs
    for elem in root.iter():
        href = elem.get("href", "")
        if not href:
            continue
        # Normalize path: manifest uses relative "section0.xml" or full "Contents/section0.xml"
        if re.match(r"section\d+\.xml$", href, re.IGNORECASE):
            section_names.append(f"Contents/{href}")
        elif _SECTION_RE.match(href):
            section_names.append(href)

    return sorted(section_names)


def _parse_section(root: ET.Element) -> HwpxSection:
    """Parse a section XML root element into HwpxSection."""
    section = HwpxSection()

    for p_elem in root.findall(f"{HP}p"):
        para = _parse_paragraph(p_elem)
        section.paragraphs.append(para)

        # Find tables inside this paragraph
        for tbl_elem in p_elem.findall(f".//{HP}tbl"):
            table = _parse_table(tbl_elem)
            section.tables.append(table)

    return section


def _parse_paragraph(p_elem: ET.Element) -> HwpxParagraph:
    """Parse an <hp:p> element into HwpxParagraph."""
    para = HwpxParagraph(
        id=p_elem.get("id", ""),
        para_pr_id_ref=p_elem.get("paraPrIDRef", "0"),
        style_id_ref=p_elem.get("styleIDRef", "0"),
    )

    for run_elem in p_elem.findall(f"{HP}run"):
        run = HwpxRun(
            char_pr_id_ref=run_elem.get("charPrIDRef", "0"),
        )

        # Collect text from <hp:t> children of the run
        text_parts: list[str] = []
        for child in run_elem:
            if child.tag == f"{HP}t":
                # Collect all text content within <hp:t>, including tail text
                # from sub-elements (tabs, line breaks, etc.)
                t_text = _collect_t_text(child)
                if t_text:
                    text_parts.append(t_text)

        run.text = "".join(text_parts)

        # Check if this run contains a table or shape object
        if run_elem.find(f".//{HP}tbl") is not None:
            run.is_table = True
        if run_elem.find(f".//{HP}pic") is not None or \
           run_elem.find(f".//{HP}rect") is not None or \
           run_elem.find(f".//{HP}ellipse") is not None or \
           run_elem.find(f".//{HP}line") is not None:
            run.is_shape = True

        para.runs.append(run)

    return para


def _collect_t_text(t_elem: ET.Element) -> str:
    """Collect all text from a <hp:t> element, including child tail text."""
    parts: list[str] = []
    if t_elem.text:
        parts.append(t_elem.text)
    for child in t_elem:
        # Tab, lineBreak etc. may have tail text
        tag_local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag_local == "tab":
            parts.append("\t")
        elif tag_local in ("lineBreak", "hypenBreak"):
            parts.append("\n")
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _parse_table(tbl_elem: ET.Element) -> HwpxTable:
    """Parse an <hp:tbl> element into HwpxTable."""
    table = HwpxTable()

    all_cells: list[HwpxTableCell] = []
    row_idx = 0
    max_col = 0

    for tr_elem in tbl_elem.findall(f"{HP}tr"):
        col_idx = 0
        for tc_elem in tr_elem.findall(f"{HP}tc"):
            cell = HwpxTableCell(row=row_idx, col=col_idx)

            # Parse col/row span
            cell.col_span = int(tc_elem.get("colSpan", "1"))
            cell.row_span = int(tc_elem.get("rowSpan", "1"))

            # Cell address (if present, prefer it)
            addr = tc_elem.find(f"{HP}cellAddr")
            if addr is not None:
                cell.col = int(addr.get("colAddr", str(col_idx)))
                cell.row = int(addr.get("rowAddr", str(row_idx)))

            # Collect text from all <hp:t> descendants of this cell
            cell_texts: list[str] = []
            for t_elem in tc_elem.findall(f".//{HP}t"):
                t_text = _collect_t_text(t_elem)
                if t_text:
                    cell_texts.append(t_text)
            cell.text = "".join(cell_texts).strip()

            # Parse cell paragraphs
            for cp_elem in tc_elem.findall(f".//{HP}p"):
                cell.paragraphs.append(_parse_paragraph(cp_elem))

            all_cells.append(cell)
            col_idx += cell.col_span
            if col_idx > max_col:
                max_col = col_idx

        row_idx += 1

    table.rows = row_idx
    table.cols = max_col
    table.cells = all_cells
    return table


# ---------------------------------------------------------------------------
# Text extraction functions
# ---------------------------------------------------------------------------

def extract_text(filepath: str, separator: str = "\n") -> str:
    """Extract plain text from HWPX file.

    Walks all paragraphs and tables, returning concatenated text.
    Tables are rendered as tab-separated rows.
    """
    doc = HwpxDocument.open(filepath)
    parts: list[str] = []

    for section in doc.sections:
        for para in section.paragraphs:
            t = para.text
            if t:
                parts.append(t)
        for table in section.tables:
            for row in table.to_2d():
                line = "\t".join(row)
                if line.strip():
                    parts.append(line)

    return separator.join(parts)


def extract_markdown(filepath: str) -> str:
    """Extract content from HWPX file as Markdown.

    Paragraphs become plain text lines; tables become Markdown tables.
    """
    doc = HwpxDocument.open(filepath)
    lines: list[str] = []

    for sec_idx, section in enumerate(doc.sections):
        if sec_idx > 0:
            lines.append("---")
            lines.append("")

        table_idx = 0

        for para in section.paragraphs:
            t = para.text
            if t:
                lines.append(t)
                lines.append("")

        for table in section.tables:
            grid = table.to_2d()
            if grid:
                # Header row
                header = grid[0]
                lines.append("| " + " | ".join(header) + " |")
                lines.append("| " + " | ".join("---" for _ in header) + " |")
                # Data rows
                for row in grid[1:]:
                    padded = row + [""] * max(0, len(header) - len(row))
                    lines.append("| " + " | ".join(padded[:len(header)]) + " |")
                lines.append("")

    return "\n".join(lines).rstrip()


def extract_html(filepath: str) -> str:
    """Extract content from HWPX file as HTML.

    Paragraphs become <p> elements; tables become <table> elements.
    Returns a complete HTML5 document.
    """
    doc = HwpxDocument.open(filepath)

    def _esc(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    body_parts: list[str] = []

    for sec_idx, section in enumerate(doc.sections):
        if sec_idx > 0:
            body_parts.append("<hr />")

        for para in section.paragraphs:
            t = para.text
            if t:
                body_parts.append(f"<p>{_esc(t)}</p>")

        for table in section.tables:
            grid = table.to_2d()
            if grid:
                body_parts.append('<table border="1">')
                for row in grid:
                    body_parts.append("  <tr>")
                    for cell in row:
                        body_parts.append(f"    <td>{_esc(cell)}</td>")
                    body_parts.append("  </tr>")
                body_parts.append("</table>")

    body = "\n".join(body_parts)

    return (
        "<!DOCTYPE html>\n"
        '<html lang="ko">\n'
        "<head>\n"
        '  <meta charset="utf-8" />\n'
        "  <title>HWPX Document</title>\n"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>"
    )
