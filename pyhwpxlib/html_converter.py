"""Convert HWPX files to HTML for browser viewing.

Produces standalone HTML with inline CSS and base64-encoded images.
Handles paragraphs, runs with character styles, tables, shapes,
images, equations, and hyperlinks.
"""

from __future__ import annotations

import base64
import logging
import mimetypes
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

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
# HTML template
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
body {{ max-width: 210mm; margin: 20mm auto; font-family: '나눔고딕', 'NanumGothic', 'Malgun Gothic', sans-serif; font-size: 10pt; line-height: 1.6; color: #333; }}
table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
td, th {{ border: 1px solid #000; padding: 5px 8px; vertical-align: middle; }}
h1 {{ font-size: 24pt; }} h2 {{ font-size: 18pt; }} h3 {{ font-size: 14pt; }} h4 {{ font-size: 12pt; }}
.shape {{ display: inline-block; margin: 5px; }}
img {{ max-width: 100%; }}
code {{ background: #f5f5f5; padding: 2px 6px; font-family: 'D2Coding', monospace; }}
pre {{ background: #f5f5f5; padding: 10px; border: 1px solid #ddd; overflow-x: auto; }}
blockquote {{ border-left: 3px solid #ccc; padding-left: 10px; color: #666; font-style: italic; }}
</style>
</head>
<body>
{content}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _guess_mime(filename: str) -> str:
    """Guess MIME type from filename."""
    mt, _ = mimetypes.guess_type(filename)
    return mt or "application/octet-stream"


# ---------------------------------------------------------------------------
# Style parsing from header.xml
# ---------------------------------------------------------------------------

class _CharStyle:
    """Parsed character property from header.xml."""
    __slots__ = ("id", "height", "text_color", "bold", "italic",
                 "underline", "strikeout")

    def __init__(self) -> None:
        self.id: str = "0"
        self.height: int = 1000  # in 1/100 pt (1000 = 10pt)
        self.text_color: str = "#000000"
        self.bold: bool = False
        self.italic: bool = False
        self.underline: bool = False
        self.strikeout: bool = False

    def to_css(self, base_height: int = 1000) -> str:
        """Return inline CSS string for this character style."""
        parts: list[str] = []
        if self.height != base_height and self.height > 0:
            pt = self.height / 100.0
            parts.append(f"font-size: {pt:.1f}pt")
        if self.text_color and self.text_color != "#000000":
            parts.append(f"color: {self.text_color}")
        if self.bold:
            parts.append("font-weight: bold")
        if self.italic:
            parts.append("font-style: italic")
        if self.underline:
            parts.append("text-decoration: underline")
        if self.strikeout:
            parts.append("text-decoration: line-through")
        return "; ".join(parts)

    def heading_level(self) -> int:
        """Return heading level 1-4 based on font size, or 0 if not heading."""
        if self.bold:
            pt = self.height / 100.0
            if pt >= 22:
                return 1
            if pt >= 16:
                return 2
            if pt >= 13:
                return 3
            if pt >= 11:
                return 4
        return 0


def _parse_char_styles(header_root: ET.Element) -> dict[str, _CharStyle]:
    """Parse <hh:charPr> elements from header.xml into a style map."""
    styles: dict[str, _CharStyle] = {}

    for char_pr in header_root.iter(f"{HH}charPr"):
        cs = _CharStyle()
        cs.id = char_pr.get("id", "0")
        cs.height = int(char_pr.get("height", "1000"))
        cs.text_color = char_pr.get("textColor", "#000000")

        # Bold/italic are indicated by <hh:bold/> and <hh:italic/> sub-elements
        if char_pr.find(f"{HH}bold") is not None:
            cs.bold = True
        if char_pr.find(f"{HH}italic") is not None:
            cs.italic = True
        ul_elem = char_pr.find(f"{HH}underline")
        if ul_elem is not None:
            ul_type = ul_elem.get("type", "NONE")
            if ul_type and ul_type != "NONE":
                cs.underline = True
        so_elem = char_pr.find(f"{HH}strikeout")
        if so_elem is not None:
            so_shape = so_elem.get("shape", "NONE")
            if so_shape and so_shape != "NONE" and so_shape != "('NONE', 0)":
                cs.strikeout = True

        # Also check attribute-based bold/italic (some generators use this)
        bold_attr = char_pr.get("bold")
        if bold_attr and bold_attr not in ("0", "false"):
            cs.bold = True
        italic_attr = char_pr.get("italic")
        if italic_attr and italic_attr not in ("0", "false"):
            cs.italic = True

        styles[cs.id] = cs

    return styles


def _parse_border_fills(header_root: ET.Element) -> dict[str, dict]:
    """Parse <hh:borderFill> elements for cell background colors."""
    fills: dict[str, dict] = {}

    for bf in header_root.iter(f"{HH}borderFill"):
        bf_id = bf.get("id", "")
        info: dict = {}

        # Look for <hc:fillBrush> or <hh:fillBrush>
        for fill_brush in list(bf.iter()):
            tag = fill_brush.tag.split("}")[-1] if "}" in fill_brush.tag else fill_brush.tag
            if tag == "winBrush":
                face_color = fill_brush.get("faceColor", "")
                if face_color and face_color.lower() not in ("none", "white", "#ffffff"):
                    info["background"] = face_color
            elif tag == "gradation":
                # Gradient fill - extract start color for simple display
                for stop in fill_brush.iter():
                    stop_tag = stop.tag.split("}")[-1] if "}" in stop.tag else stop.tag
                    if stop_tag == "color" and stop.text:
                        info["background"] = stop.text
                        break

        if info:
            fills[bf_id] = info

    return fills


# ---------------------------------------------------------------------------
# Element converters
# ---------------------------------------------------------------------------

def _collect_t_text(t_elem: ET.Element) -> str:
    """Collect all text from a <hp:t> element, including child tail text."""
    parts: list[str] = []
    if t_elem.text:
        parts.append(t_elem.text)
    for child in t_elem:
        tag_local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag_local == "tab":
            parts.append("\t")
        elif tag_local in ("lineBreak", "hypenBreak"):
            parts.append("\n")
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


class _HwpxToHtmlConverter:
    """Stateful converter that walks HWPX XML and produces HTML fragments."""

    def __init__(
        self,
        char_styles: dict[str, _CharStyle],
        border_fills: dict[str, dict],
        images: dict[str, bytes],
        embed_images: bool = True,
    ) -> None:
        self.char_styles = char_styles
        self.border_fills = border_fills
        self.images = images  # BinData name -> raw bytes
        self.embed_images = embed_images
        self.parts: list[str] = []

    def convert_sections(self, section_roots: list[ET.Element]) -> str:
        """Convert all section roots to HTML body content."""
        for sec_idx, root in enumerate(section_roots):
            if sec_idx > 0:
                self.parts.append('<hr style="page-break-before: always;" />')
            self._convert_section(root)
        return "\n".join(self.parts)

    def _convert_section(self, root: ET.Element) -> None:
        """Convert a single section."""
        for p_elem in root.findall(f"{HP}p"):
            self._convert_paragraph(p_elem)

    def _convert_paragraph(self, p_elem: ET.Element) -> None:
        """Convert a single <hp:p> element."""
        runs = p_elem.findall(f"{HP}run")

        # Check for table
        for tbl in p_elem.findall(f".//{HP}tbl"):
            self._convert_table(tbl)

        # Check for shape elements
        for tag_suffix in ("rect", "ellipse", "arc", "polygon", "curve",
                           "connectLine", "textart", "container"):
            for shape in p_elem.findall(f".//{HP}{tag_suffix}"):
                self._convert_shape(shape, tag_suffix)

        # Check for line
        for line in p_elem.findall(f".//{HP}line"):
            self._convert_line(line)

        # Check for image (pic)
        for pic in p_elem.findall(f".//{HP}pic"):
            self._convert_image(pic)

        # Check for equation
        for eq in p_elem.findall(f".//{HP}equation"):
            self._convert_equation(eq)

        # Check for form controls
        for tag, html_fn in [
            ("checkBtn", self._convert_checkbox),
            ("radioBtn", self._convert_radio),
            ("btn", self._convert_button),
            ("comboBox", self._convert_combobox),
            ("edit", self._convert_edit),
            ("listBox", self._convert_listbox),
            ("scrollBar", self._convert_scrollbar),
        ]:
            for elem in p_elem.findall(f".//{HP}{tag}"):
                html_fn(elem)

        # Check for highlight (markpenBegin)
        has_markpen = p_elem.find(f".//{HP}markpenBegin") is not None

        # Check for dutmal (ruby)
        for dutmal in p_elem.findall(f".//{HP}dutmal"):
            self._convert_dutmal(dutmal)

        # Collect text runs
        text_fragments = self._collect_run_html(runs)
        if text_fragments:
            combined = "".join(text_fragments)
            if not combined.strip():
                return

            # Apply highlight if markpen found
            if has_markpen:
                color = "#FFFF00"
                mp = p_elem.find(f".//{HP}markpenBegin")
                if mp is not None:
                    color = mp.get("color", "#FFFF00")
                combined = f'<mark style="background-color: {color}">{combined}</mark>'

            # Determine if this should be a heading
            heading_level = self._detect_heading(runs)
            if heading_level > 0:
                self.parts.append(f"<h{heading_level}>{combined}</h{heading_level}>")
            else:
                self.parts.append(f"<p>{combined}</p>")

    def _collect_run_html(self, runs: list[ET.Element]) -> list[str]:
        """Collect HTML fragments from paragraph runs, skipping table/shape runs."""
        fragments: list[str] = []

        for run in runs:
            # Skip runs that contain tables or shapes (handled separately)
            if run.find(f".//{HP}tbl") is not None:
                continue
            if run.find(f".//{HP}pic") is not None:
                continue
            if run.find(f".//{HP}rect") is not None:
                continue
            if run.find(f".//{HP}ellipse") is not None:
                continue
            if run.find(f".//{HP}equation") is not None:
                continue

            char_pr_id = run.get("charPrIDRef", "0")
            style = self.char_styles.get(char_pr_id)

            # Check for hyperlink field
            href = self._extract_hyperlink(run)

            # Collect text from <hp:t> children
            text_parts: list[str] = []
            for child in run:
                if child.tag == f"{HP}t":
                    t_text = _collect_t_text(child)
                    if t_text:
                        text_parts.append(_escape_html(t_text))

            if not text_parts:
                continue

            text_html = "".join(text_parts)
            # Replace newlines with <br>
            text_html = text_html.replace("\n", "<br>")
            # Replace tabs with spaces
            text_html = text_html.replace("\t", "&emsp;")

            # Wrap with style
            if style:
                css = style.to_css()
                if style.bold and not style.italic:
                    text_html = f"<strong>{text_html}</strong>"
                elif style.italic and not style.bold:
                    text_html = f"<em>{text_html}</em>"
                elif style.bold and style.italic:
                    text_html = f"<strong><em>{text_html}</em></strong>"

                if css:
                    # Remove bold/italic from CSS if already wrapped
                    css_parts = [
                        p.strip() for p in css.split(";")
                        if p.strip()
                        and "font-weight" not in p
                        and "font-style" not in p
                    ]
                    if css_parts:
                        text_html = f'<span style="{"; ".join(css_parts)}">{text_html}</span>'

            # Wrap with hyperlink
            if href:
                text_html = f'<a href="{_escape_html(href)}">{text_html}</a>'

            fragments.append(text_html)

        return fragments

    def _detect_heading(self, runs: list[ET.Element]) -> int:
        """Detect if paragraph runs form a heading based on charPr styles."""
        if not runs:
            return 0

        # Check the first text-bearing run
        for run in runs:
            if run.find(f".//{HP}tbl") is not None:
                continue
            if run.find(f".//{HP}pic") is not None:
                continue

            char_pr_id = run.get("charPrIDRef", "0")
            style = self.char_styles.get(char_pr_id)
            if style:
                return style.heading_level()
            break
        return 0

    def _extract_hyperlink(self, run: ET.Element) -> str:
        """Extract hyperlink URL from fieldBegin element if present."""
        for child in run:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if tag == "fieldBegin":
                field_type = child.get("type", "")
                if field_type == "HYPERLINK":
                    # URL is in the command attribute or child param element
                    command = child.get("command", "")
                    if command:
                        return command
                    # Look for param
                    param = child.find(f".//{HP}param")
                    if param is not None and param.text:
                        return param.text
        return ""

    def _convert_table(self, tbl: ET.Element) -> None:
        """Convert a <hp:tbl> element to HTML table."""
        self.parts.append('<table>')

        for tr in tbl.findall(f"{HP}tr"):
            self.parts.append("  <tr>")

            for tc in tr.findall(f"{HP}tc"):
                col_span = int(tc.get("colSpan", "1"))
                row_span = int(tc.get("rowSpan", "1"))
                bf_id = tc.get("borderFillIDRef", "")

                # Build cell attributes
                attrs: list[str] = []
                if col_span > 1:
                    attrs.append(f'colspan="{col_span}"')
                if row_span > 1:
                    attrs.append(f'rowspan="{row_span}"')

                # Cell style from borderFill
                cell_style_parts: list[str] = []
                if bf_id and bf_id in self.border_fills:
                    bf_info = self.border_fills[bf_id]
                    if "background" in bf_info:
                        cell_style_parts.append(
                            f"background-color: {bf_info['background']}"
                        )

                # Check cell vertical alignment
                sub_list = tc.find(f"{HP}subList")
                if sub_list is not None:
                    vert_align = sub_list.get("vertAlign", "")
                    if vert_align == "CENTER":
                        cell_style_parts.append("vertical-align: middle")
                    elif vert_align == "BOTTOM":
                        cell_style_parts.append("vertical-align: bottom")

                if cell_style_parts:
                    attrs.append(f'style="{"; ".join(cell_style_parts)}"')

                attr_str = " " + " ".join(attrs) if attrs else ""

                # Collect cell text from paragraphs inside the cell
                cell_html_parts: list[str] = []
                # Find paragraphs inside subList or directly in tc
                p_elems = tc.findall(f".//{HP}p")
                for p_elem in p_elems:
                    p_runs = p_elem.findall(f"{HP}run")
                    frags = self._collect_run_html(p_runs)
                    if frags:
                        cell_html_parts.append("".join(frags))

                    # Also handle nested tables
                    for nested_tbl in p_elem.findall(f".//{HP}tbl"):
                        # Avoid double-processing - only immediate children
                        if nested_tbl in tbl.findall(f".//{HP}tbl"):
                            continue

                cell_html = "<br>".join(cell_html_parts) if cell_html_parts else ""
                self.parts.append(f"    <td{attr_str}>{cell_html}</td>")

            self.parts.append("  </tr>")

        self.parts.append("</table>")

    def _convert_shape(self, shape: ET.Element, shape_type: str) -> None:
        """Convert a shape (rect/ellipse) to HTML div."""
        sz = shape.find(f"{HP}sz")
        width = int(sz.get("width", "7200")) if sz is not None else 7200
        height = int(sz.get("height", "3600")) if sz is not None else 3600

        # Convert HWPX units to approximate mm (1 HWPX unit ~ 1/7200 inch ~ 0.00353mm)
        w_mm = width / 283.46
        h_mm = height / 283.46

        style_parts = [
            f"width: {w_mm:.1f}mm",
            f"height: {h_mm:.1f}mm",
            "display: inline-block",
            "margin: 5px",
            "border: 1px solid #000",
        ]

        if shape_type == "ellipse":
            style_parts.append("border-radius: 50%")

        # Check for fill color in the shape's lineShape/fillBrush
        for fill in shape.iter():
            tag = fill.tag.split("}")[-1] if "}" in fill.tag else fill.tag
            if tag == "winBrush":
                face_color = fill.get("faceColor", "")
                if face_color and face_color.lower() not in ("none",):
                    style_parts.append(f"background-color: {face_color}")
                break

        style = "; ".join(style_parts)

        # Extract text inside the shape
        inner_text = ""
        for t_elem in shape.findall(f".//{HP}t"):
            t_text = _collect_t_text(t_elem)
            if t_text:
                inner_text += _escape_html(t_text)

        self.parts.append(
            f'<div class="shape" style="{style}">{inner_text}</div>'
        )

    def _convert_image(self, pic: ET.Element) -> None:
        """Convert a <hp:pic> element to HTML img."""
        # Find the <hc:img> element with binaryItemIDRef
        img_elem = pic.find(f".//{HC}img")
        if img_elem is None:
            # Try without namespace
            for elem in pic.iter():
                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if tag == "img":
                    img_elem = elem
                    break

        if img_elem is None:
            return

        bin_ref = img_elem.get("binaryItemIDRef", "")
        if not bin_ref:
            return

        # Find matching image in BinData
        matched_data: bytes | None = None
        matched_name: str = ""
        for name, data in self.images.items():
            # Match by filename stem (e.g., "image1" matches "BinData/image1.jpeg")
            name_stem = Path(name).stem
            file_name = Path(name).name
            if name_stem == bin_ref or file_name == bin_ref or bin_ref in name:
                matched_data = data
                matched_name = name
                break

        if matched_data and self.embed_images:
            mime = _guess_mime(matched_name)
            b64 = base64.b64encode(matched_data).decode("ascii")
            self.parts.append(
                f'<img src="data:{mime};base64,{b64}" alt="{_escape_html(bin_ref)}" />'
            )
        elif matched_data:
            self.parts.append(
                f'<img src="{_escape_html(matched_name)}" alt="{_escape_html(bin_ref)}" />'
            )
        else:
            self.parts.append(
                f'<p><em>[Image: {_escape_html(bin_ref)}]</em></p>'
            )

    def _convert_equation(self, eq: ET.Element) -> None:
        """Convert a <hp:equation> element to HTML code block."""
        # Equation content is usually in a script attribute or child text
        script = eq.get("script", "")
        if not script:
            # Try child text
            for child in eq.iter():
                if child.text:
                    script = child.text
                    break

        if script:
            self.parts.append(f'<code>{_escape_html(script)}</code>')

    # -- Form controls -------------------------------------------------------

    def _convert_checkbox(self, elem: ET.Element) -> None:
        caption = elem.get("caption", "")
        value = elem.get("value", "UNCHECKED")
        checked = ' checked' if value == "CHECKED" else ''
        self.parts.append(
            f'<p><label><input type="checkbox"{checked}> '
            f'{_escape_html(caption)}</label></p>'
        )

    def _convert_radio(self, elem: ET.Element) -> None:
        caption = elem.get("caption", "")
        group = elem.get("radioGroupName", "")
        value = elem.get("value", "UNCHECKED")
        checked = ' checked' if value == "CHECKED" else ''
        self.parts.append(
            f'<p><label><input type="radio" name="{_escape_html(group)}"{checked}> '
            f'{_escape_html(caption)}</label></p>'
        )

    def _convert_button(self, elem: ET.Element) -> None:
        caption = elem.get("caption", "Button")
        self.parts.append(f'<p><button>{_escape_html(caption)}</button></p>')

    def _convert_combobox(self, elem: ET.Element) -> None:
        name = elem.get("name", "")
        self.parts.append(f'<p><select>')
        for item in elem.findall(f"{HP}listItem"):
            display = item.get("displayText", "")
            val = item.get("value", "")
            self.parts.append(f'  <option value="{_escape_html(val)}">{_escape_html(display or val)}</option>')
        if not elem.findall(f"{HP}listItem"):
            self.parts.append(f'  <option>{_escape_html(name)}</option>')
        self.parts.append('</select></p>')

    def _convert_edit(self, elem: ET.Element) -> None:
        text_elem = elem.find(f"{HP}text")
        text = text_elem.text if text_elem is not None and text_elem.text else ""
        multi = elem.get("multiLine", "0") == "1"
        if multi:
            self.parts.append(f'<p><textarea rows="3" style="width:200px">{_escape_html(text)}</textarea></p>')
        else:
            self.parts.append(f'<p><input type="text" value="{_escape_html(text)}" style="width:200px"></p>')

    def _convert_listbox(self, elem: ET.Element) -> None:
        self.parts.append('<p><select multiple size="4">')
        for item in elem.findall(f"{HP}listItem"):
            display = item.get("displayText", "")
            self.parts.append(f'  <option>{_escape_html(display)}</option>')
        self.parts.append('</select></p>')

    def _convert_scrollbar(self, elem: ET.Element) -> None:
        min_v = elem.get("min", "0")
        max_v = elem.get("max", "100")
        val = elem.get("value", "0")
        self.parts.append(f'<p><input type="range" min="{min_v}" max="{max_v}" value="{val}"></p>')

    # -- Line ----------------------------------------------------------------

    def _convert_line(self, line: ET.Element) -> None:
        ls = line.find(f"{HP}lineShape")
        color = ls.get("color", "#000000") if ls is not None else "#000000"
        width = int(ls.get("width", "283")) if ls is not None else 283
        px = max(1, width // 71)
        self.parts.append(f'<hr style="border: none; border-top: {px}px solid {color}; margin: 10px 0;">')

    # -- Dutmal (ruby) -------------------------------------------------------

    def _convert_dutmal(self, elem: ET.Element) -> None:
        main_el = elem.find(f"{HP}mainText")
        sub_el = elem.find(f"{HP}subText")
        main = main_el.text if main_el is not None and main_el.text else ""
        sub = sub_el.text if sub_el is not None and sub_el.text else ""
        self.parts.append(f'<p><ruby>{_escape_html(main)}<rp>(</rp><rt>{_escape_html(sub)}</rt><rp>)</rp></ruby></p>')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_hwpx_to_html(
    hwpx_path: str,
    output_path: str | None = None,
    embed_images: bool = True,
    title: str = "HWPX Document",
) -> str:
    """Convert HWPX file to HTML.

    If *output_path* is None, returns HTML as string.
    If *embed_images* is True, images are base64-encoded inline.

    Parameters
    ----------
    hwpx_path : str
        Path to the input .hwpx file.
    output_path : str or None
        Path to write the output .html file. If None, the HTML is
        returned as a string without writing to disk.
    embed_images : bool
        Whether to embed images as base64 data URIs (default True).
    title : str
        Title for the HTML <title> element.

    Returns
    -------
    str
        The generated HTML content.
    """
    char_styles: dict[str, _CharStyle] = {}
    border_fills: dict[str, dict] = {}
    images: dict[str, bytes] = {}
    section_roots: list[ET.Element] = []

    with zipfile.ZipFile(hwpx_path, "r") as zf:
        names = zf.namelist()

        # 1. Parse header.xml for styles
        header_candidates = [n for n in names if n.lower().endswith("header.xml")]
        for hname in header_candidates:
            try:
                raw = _normalize_ns(zf.read(hname))
                header_root = ET.fromstring(raw)
                char_styles.update(_parse_char_styles(header_root))
                border_fills.update(_parse_border_fills(header_root))
            except ET.ParseError as e:
                logger.warning("Failed to parse header XML [%s]: %s", hname, e)
            except Exception as e:
                logger.warning("Unexpected error reading header [%s]: %s", hname, e)

        # 2. Parse section files
        section_names = sorted(n for n in names if _SECTION_RE.match(n))
        if not section_names:
            # Fallback: look in content.hpf
            section_names = _find_sections_from_manifest(zf)

        for sec_name in section_names:
            try:
                raw = _normalize_ns(zf.read(sec_name))
                root = ET.fromstring(raw)
                section_roots.append(root)
            except ET.ParseError as e:
                logger.warning("Failed to parse section XML [%s]: %s", sec_name, e)
            except Exception as e:
                logger.warning("Unexpected error reading section [%s]: %s", sec_name, e)

        # 3. Load BinData images
        for name in names:
            if name.startswith("BinData/") and not name.endswith("/"):
                try:
                    images[name] = zf.read(name)
                except Exception as e:
                    logger.warning("Failed to read BinData image [%s]: %s", name, e)

    # Convert
    converter = _HwpxToHtmlConverter(
        char_styles=char_styles,
        border_fills=border_fills,
        images=images,
        embed_images=embed_images,
    )
    body_html = converter.convert_sections(section_roots)

    html = _HTML_TEMPLATE.format(title=_escape_html(title), content=body_html)

    if output_path:
        Path(output_path).write_text(html, encoding="utf-8")

    return html


def _find_sections_from_manifest(zf: zipfile.ZipFile) -> list[str]:
    """Parse Contents/content.hpf to find section file paths."""
    try:
        raw = _normalize_ns(zf.read("Contents/content.hpf"))
    except KeyError:
        return []

    root = ET.fromstring(raw)
    section_names: list[str] = []
    for elem in root.iter():
        href = elem.get("href", "")
        if not href:
            continue
        if re.match(r"section\d+\.xml$", href, re.IGNORECASE):
            section_names.append(f"Contents/{href}")
        elif _SECTION_RE.match(href):
            section_names.append(href)

    return sorted(section_names)
