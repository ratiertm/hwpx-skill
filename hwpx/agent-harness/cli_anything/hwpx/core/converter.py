"""Markdown → HWPX converter with CSS-driven styling.

This module is shared by both the CLI (hwpx_cli.py) and the Web UI
(server.py), avoiding global state conflicts.
"""

from __future__ import annotations

import re
import uuid as _uuid
import xml.etree.ElementTree as ET

_HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
_PAGE_WIDTH = 42520  # A4 body width in hwpunit

# ── MD→HWPX Style Presets ─────────────────────────────────────────────

MD_STYLES: dict[str, dict] = {
    "github": {
        "name": "GitHub",
        "description": "GitHub Flavored Markdown (github-markdown-css)",
        "body_height": 1000, "body_color": "#1F2328", "body_font": None,
        "line_spacing": 150,
        "h1_height": 2000, "h2_height": 1500, "h3_height": 1300,
        "h4_height": 1000, "h5_height": 900, "h6_height": 850,
        "h1_h2_border": True, "heading_border_color": "#D1D9E0",
        "heading_color": None, "heading_spacing": True,
        "code_height": 850, "code_bg": "#F6F8FA", "code_text": "#1F2328",
        "code_border": "#D1D9E0", "code_font": "D2Coding",
        "inline_code_text": "#1F2328",
        "link_color": "#0969DA",
        "quote_color": "#59636E", "quote_border_width": "283",
        "quote_border_color": "#D1D9E0",
        "hr_color": "#D1D9E0", "hr_width": "283",
        "table_header_bg": "#F0F0F0", "table_border_color": "#D1D9E0",
        "table_cell_padding": (450, 975),
        "bullet_chars": ["•", "◦", "▪", "‣", "⁃"],
    },
    "vscode": {
        "name": "VS Code",
        "description": "VS Code Markdown Preview (markdown.css)",
        "body_height": 1000, "body_color": "#333333", "body_font": None,
        "line_spacing": 157,
        "h1_height": 2000, "h2_height": 1500, "h3_height": 1300,
        "h4_height": 1000, "h5_height": 900, "h6_height": 850,
        "h1_h2_border": True, "heading_border_color": "#C8C8C8",
        "heading_color": None, "heading_spacing": True,
        "code_height": 1000, "code_bg": "#F0F0F0", "code_text": "#333333",
        "code_border": "#C8C8C8", "code_font": "D2Coding",
        "inline_code_text": "#333333",
        "link_color": "#4080D0",
        "quote_color": "#6A737D", "quote_border_width": "375",
        "quote_border_color": "#C8C8C8",
        "hr_color": "#C8C8C8", "hr_width": "71",
        "table_header_bg": "#E8E8E8", "table_border_color": "#C8C8C8",
        "table_cell_padding": (375, 750),
        "bullet_chars": ["•", "◦", "▪", "‣", "⁃"],
    },
    "minimal": {
        "name": "Minimal",
        "description": "Clean, no decorations, tight spacing",
        "body_height": 1000, "body_color": "#333333", "body_font": None,
        "line_spacing": 160,
        "h1_height": 1600, "h2_height": 1300, "h3_height": 1100,
        "h4_height": 1000, "h5_height": 900, "h6_height": 850,
        "h1_h2_border": False, "heading_border_color": "#CCCCCC",
        "heading_color": None, "heading_spacing": True,
        "code_height": 900, "code_bg": "#F5F5F5", "code_text": "#333333",
        "code_border": "#DDDDDD", "code_font": "D2Coding",
        "inline_code_text": "#C7254E",
        "link_color": "#0563C1",
        "quote_color": "#555555", "quote_border_width": "71",
        "quote_border_color": "#CCCCCC",
        "hr_color": "#CCCCCC", "hr_width": "71",
        "table_header_bg": "#D0D0D0", "table_border_color": "#CCCCCC",
        "table_cell_padding": (450, 975),
        "bullet_chars": ["•", "◦", "▪", "‣", "⁃"],
    },
    "academic": {
        "name": "Academic",
        "description": "Formal document style, larger headings, serif feel",
        "body_height": 1100, "body_color": "#000000", "body_font": None,
        "line_spacing": 180,
        "h1_height": 2200, "h2_height": 1800, "h3_height": 1400,
        "h4_height": 1100, "h5_height": 1000, "h6_height": 900,
        "h1_h2_border": True, "heading_border_color": "#000000",
        "heading_color": None, "heading_spacing": True,
        "code_height": 950, "code_bg": "#F8F8F8", "code_text": "#000000",
        "code_border": "#CCCCCC", "code_font": "D2Coding",
        "inline_code_text": "#000000",
        "link_color": "#000080",
        "quote_color": "#444444", "quote_border_width": "142",
        "quote_border_color": "#000000",
        "hr_color": "#000000", "hr_width": "142",
        "table_header_bg": "#D8D8D8", "table_border_color": "#000000",
        "table_cell_padding": (450, 975),
        "bullet_chars": ["•", "–", "·", "‣", "⁃"],
    },
}

DEFAULT_STYLE = "github"


# ── Converter ─────────────────────────────────────────────────────────

def convert_markdown_to_hwpx(doc, content: str, style_name: str = DEFAULT_STYLE) -> int:
    """Parse Markdown and build HWPX with selectable CSS-based styling."""
    s = MD_STYLES.get(style_name, MD_STYLES[DEFAULT_STYLE])

    # Strip HTML — HWPX has no HTML equivalent
    content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<[^>]+>", "", content)

    lines = content.split("\n")
    element_count = 0
    i = 0

    # Body paragraph style from CSS
    body_para_kw: dict = {}
    if s.get("line_spacing"):
        body_para_kw["line_spacing"] = s["line_spacing"]
    if s.get("para_align"):
        body_para_kw["align"] = s["para_align"]
    if s.get("para_indent"):
        body_para_kw["indent"] = s["para_indent"]
    if s.get("para_spacing_after"):
        body_para_kw["spacing_after"] = s["para_spacing_after"]
    if s.get("para_spacing_before"):
        body_para_kw["spacing_before"] = s["para_spacing_before"]
    body_para_id = None
    if body_para_kw:
        body_para_id = doc.ensure_para_style(**body_para_kw)

    while i < len(lines):
        line = lines[i]

        # ── Code block ──
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip() or None
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            doc.add_code_block(
                "\n".join(code_lines), language=lang,
                font=s.get("code_font", "D2Coding"),
                font_size=s["code_height"], bg_color=s["code_bg"],
                text_color=s["code_text"], border_color=s["code_border"],
            )
            element_count += len(code_lines) + (1 if lang else 0)
            doc.add_paragraph("")
            continue

        # ── Table ──
        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            element_count += _handle_table(doc, lines, i, s)
            while i < len(lines) and lines[i].strip().startswith("|"):
                i += 1
            continue

        # ── Horizontal rule ──
        stripped = line.strip()
        if _is_horizontal_rule(stripped):
            doc.add_line(_PAGE_WIDTH, 0, _PAGE_WIDTH, 0,
                         line_color=s["hr_color"], line_width=s["hr_width"])
            element_count += 1
            i += 1
            continue

        # ── Empty line ──
        if not stripped:
            i += 1
            continue

        # ── Heading ──
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            _handle_heading(doc, heading_match, element_count, s)
            element_count += 1
            i += 1
            continue

        # ── Blockquote ──
        if stripped.startswith(">"):
            count, i = _handle_blockquote(doc, lines, i, s)
            element_count += count
            continue

        # ── Bullet list ──
        if re.match(r"^(\s*)([-*+])\s+(.+)$", stripped):
            count, i = _handle_bullet_list(doc, lines, i, s)
            element_count += count
            continue

        # ── Numbered list ──
        if re.match(r"^(\s*)\d+[.)]\s+(.+)$", stripped):
            count, i = _handle_numbered_list(doc, lines, i)
            element_count += count
            continue

        # ── Regular paragraph ──
        _add_rich_paragraph(doc, stripped, style=s, para_pr_id=body_para_id)
        element_count += 1
        i += 1

    return element_count


# ── Element handlers ──────────────────────────────────────────────────

def _is_horizontal_rule(stripped: str) -> bool:
    if not stripped or len(stripped.replace(" ", "")) < 3:
        return False
    if not all(c in "-*_ " for c in stripped):
        return False
    clean = stripped.replace(" ", "")
    return len(set(clean)) == 1 and clean[0] in "-*_"


def _handle_heading(doc, match, element_count: int, s: dict) -> None:
    level = len(match.group(1))
    heading_text = strip_inline_md(match.group(2))
    if element_count > 0 and s.get("heading_spacing", True):
        doc.add_paragraph("")
    heading_sizes = {
        1: s["h1_height"], 2: s["h2_height"], 3: s["h3_height"],
        4: s["h4_height"], 5: s["h5_height"], 6: s["h6_height"],
    }
    h_size = heading_sizes.get(level, s["body_height"])
    h_color = s.get("heading_color") or s.get("body_color")
    h_kw = {}
    if h_color:
        h_kw["text_color"] = h_color
    char_id = doc.ensure_run_style(bold=True, height=h_size, **h_kw)
    doc.add_paragraph(heading_text, char_pr_id_ref=char_id)
    if s["h1_h2_border"] and level <= 2:
        doc.add_line(_PAGE_WIDTH, 0, _PAGE_WIDTH, 0,
                     line_color=s["heading_border_color"], line_width="71")


def _handle_blockquote(doc, lines: list[str], i: int, s: dict) -> tuple[int, int]:
    quote_lines = []
    while i < len(lines) and lines[i].strip().startswith(">"):
        qt = re.sub(r"^>\s?", "", lines[i].strip())
        quote_lines.append(qt)
        i += 1
    quote_text = " ".join(quote_lines)
    char_id = doc.ensure_run_style(
        italic=True, text_color=s["quote_color"], height=s["body_height"])
    doc.add_paragraph(f"  {quote_text}", char_pr_id_ref=char_id)
    doc.add_paragraph("")
    return 1, i


def _handle_bullet_list(doc, lines: list[str], i: int, s: dict) -> tuple[int, int]:
    bullet_items = []
    while i < len(lines):
        bm = re.match(r"^(\s*)([-*+])\s+(.+)$", lines[i])
        if not bm:
            break
        indent_level = len(bm.group(1).replace("\t", "    ")) // 2
        bullet_items.append((indent_level, strip_inline_md(bm.group(3))))
        i += 1
    chars = s["bullet_chars"]
    if any(level > 0 for level, _ in bullet_items):
        doc.add_nested_bullet_list(bullet_items, bullet_chars=chars)
    else:
        doc.add_bullet_list([text for _, text in bullet_items], bullet_char=chars[0])
    return len(bullet_items), i


def _handle_numbered_list(doc, lines: list[str], i: int) -> tuple[int, int]:
    num_items = []
    while i < len(lines):
        nm = re.match(r"^(\s*)\d+[.)]\s+(.+)$", lines[i])
        if not nm:
            break
        indent_level = len(nm.group(1).replace("\t", "    ")) // 2
        num_items.append((indent_level, strip_inline_md(nm.group(2))))
        i += 1
    if any(level > 0 for level, _ in num_items):
        doc.add_nested_numbered_list(num_items)
    else:
        doc.add_numbered_list([text for _, text in num_items])
    return len(num_items), i


def _handle_table(doc, lines: list[str], i: int, s: dict) -> int:
    table_lines = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        table_lines.append(lines[i])
        i += 1
    rows = []
    for tl in table_lines:
        cells = [c.strip() for c in tl.strip().strip("|").split("|")]
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue
        rows.append(cells)
    if not rows:
        return 0

    max_cols = max(len(r) for r in rows)

    # Content-based column widths
    col_max_len = [0] * max_cols
    for row_data in rows:
        for c_idx, cell_val in enumerate(row_data[:max_cols]):
            text_len = len(strip_inline_md(cell_val))
            cjk_count = sum(1 for ch in cell_val if ord(ch) > 0x2E80)
            col_max_len[c_idx] = max(col_max_len[c_idx], text_len + cjk_count, 1)
    total_len = sum(col_max_len)
    col_widths = [int(_PAGE_WIDTH * cl / total_len) for cl in col_max_len]
    diff = _PAGE_WIDTH - sum(col_widths)
    if diff != 0 and col_widths:
        col_widths[-1] += diff

    tbl = doc.add_table(len(rows), max_cols, width=_PAGE_WIDTH)

    # Set column widths
    for c_idx, cw in enumerate(col_widths):
        try:
            for r_idx in range(len(rows)):
                cell = tbl.cell(r_idx, c_idx)
                cell_sz = cell.element.find(f"{{{_HP_NS}}}cellSz")
                if cell_sz is not None:
                    cell_sz.set("width", str(cw))
        except (IndexError, AttributeError):
            pass

    pad = s.get("table_cell_padding", (450, 975))
    pad_v, pad_h = pad[0], pad[1]

    for r_idx, row_data in enumerate(rows):
        for c_idx, cell_val in enumerate(row_data[:max_cols]):
            tbl.set_cell_text(r_idx, c_idx, strip_inline_md(cell_val))
            try:
                h_align = "CENTER" if r_idx == 0 else "LEFT"
                tbl.set_cell_align(r_idx, c_idx, horizontal=h_align, vertical="CENTER")
            except (IndexError, AttributeError, RuntimeError):
                pass
            try:
                tbl.cell(r_idx, c_idx).set_margin(
                    left=pad_h, right=pad_h, top=pad_v, bottom=pad_v)
            except (IndexError, AttributeError, RuntimeError):
                pass

    if len(rows) > 1:
        for c_idx in range(max_cols):
            try:
                tbl.set_cell_background(0, c_idx, s["table_header_bg"])
            except (IndexError, AttributeError, RuntimeError):
                pass

    doc.add_paragraph("")
    return 1


# ── Inline formatting ─────────────────────────────────────────────────

def parse_inline_segments(text: str) -> list[tuple[str, str]]:
    """Parse inline markdown into segments of (style, text)."""
    segments: list[tuple[str, str]] = []
    pattern = re.compile(
        r"!\[([^\]]*)\]\([^)]+\)"
        r"|\[([^\]]+)\]\(([^)]+)\)"
        r"|`([^`]+)`"
        r"|\*\*\*(.+?)\*\*\*"
        r"|\*\*(.+?)\*\*"
        r"|\*(.+?)\*"
    )
    last_end = 0
    for m in pattern.finditer(text):
        if m.start() > last_end:
            segments.append(("normal", text[last_end:m.start()]))
        if m.group(1) is not None:
            segments.append(("normal", m.group(1) or ""))
        elif m.group(2) is not None:
            segments.append((f"link:{m.group(3)}", m.group(2)))
        elif m.group(4) is not None:
            segments.append(("code", m.group(4)))
        elif m.group(5) is not None:
            segments.append(("bold_italic", m.group(5)))
        elif m.group(6) is not None:
            segments.append(("bold", m.group(6)))
        elif m.group(7) is not None:
            segments.append(("italic", m.group(7)))
        last_end = m.end()
    if last_end < len(text):
        segments.append(("normal", text[last_end:]))
    if not segments:
        segments.append(("normal", text))
    return segments


def _add_rich_paragraph(doc, md_text: str, style: dict | None = None,
                        para_pr_id: str | int | None = None) -> None:
    """Add a single paragraph with inline formatting."""
    _HP = f"{{{_HP_NS}}}"
    segments = parse_inline_segments(md_text)

    para_kw: dict = {}
    if para_pr_id is not None:
        para_kw["para_pr_id_ref"] = int(para_pr_id)

    if len(segments) == 1 and segments[0][0] == "normal":
        doc.add_paragraph(segments[0][1], **para_kw)
        return

    first_style, first_text = segments[0]
    if first_style.startswith("link:"):
        para = doc.add_paragraph("", include_run=False, **para_kw)
    else:
        char_id = _style_for_segment(doc, first_style, style=style)
        para = doc.add_paragraph(first_text, char_pr_id_ref=char_id, **para_kw)

    def _mk(parent, tag, attrib=None):
        child = parent.makeelement(tag, attrib or {})
        parent.append(child)
        return child

    start_idx = 0 if first_style.startswith("link:") else 1

    for seg_type, text in segments[start_idx:]:
        if not text:
            continue

        if seg_type.startswith("link:"):
            url = seg_type[5:]
            field_id = str(_uuid.uuid4().int % (2**31))
            begin_id = str(_uuid.uuid4().int % (2**31))

            run1 = _mk(para.element, f"{_HP}run", {"charPrIDRef": "0"})
            ctrl1 = _mk(run1, f"{_HP}ctrl")
            fb = _mk(ctrl1, f"{_HP}fieldBegin", {
                "id": begin_id, "type": "HYPERLINK", "name": "",
                "editable": "0", "dirty": "0", "zorder": "-1", "fieldid": field_id,
            })
            params = _mk(fb, f"{_HP}parameters", {"cnt": "6", "name": ""})
            _mk(params, f"{_HP}integerParam", {"name": "Prop"}).text = "0"
            _mk(params, f"{_HP}stringParam", {"name": "Command"}).text = f"{url.replace(':', chr(92) + ':')}; 1;0;0;"
            _mk(params, f"{_HP}stringParam", {"name": "Path"}).text = url
            _mk(params, f"{_HP}stringParam", {"name": "Category"}).text = "HWPHYPERLINK_TYPE_URL"
            _mk(params, f"{_HP}stringParam", {"name": "TargetType"}).text = "HWPHYPERLINK_TARGET_BOOKMARK"
            _mk(params, f"{_HP}stringParam", {"name": "DocOpenType"}).text = "HWPHYPERLINK_JUMP_CURRENTTAB"

            _s = style or MD_STYLES[DEFAULT_STYLE]
            link_char_id = doc.ensure_run_style(
                underline=True,
                text_color=_s.get("link_color", "#0969DA"),
                height=_s.get("body_height", 1000),
            )
            run2 = _mk(para.element, f"{_HP}run", {"charPrIDRef": str(link_char_id)})
            _mk(run2, f"{_HP}t").text = text

            run3 = _mk(para.element, f"{_HP}run", {"charPrIDRef": "0"})
            ctrl3 = _mk(run3, f"{_HP}ctrl")
            _mk(ctrl3, f"{_HP}fieldEnd", {"beginIDRef": begin_id, "fieldid": field_id})
        else:
            seg_char_id = _style_for_segment(doc, seg_type, style=style)
            run = para.element.makeelement(f"{_HP}run", {"charPrIDRef": str(seg_char_id)})
            t = run.makeelement(f"{_HP}t", {})
            t.text = text
            run.append(t)
            para.element.append(run)


def _style_for_segment(doc, seg_style: str, style: dict | None = None) -> str:
    """Return a charPrIDRef using the active MD style preset."""
    s = style or MD_STYLES[DEFAULT_STYLE]
    h = s["body_height"]
    color = s.get("body_color")
    font = s.get("body_font")
    font_kw = {}
    if font:
        font_kw = {"font_hangul": font, "font_latin": font}
    if seg_style == "bold":
        return doc.ensure_run_style(bold=True, height=h, text_color=color, **font_kw)
    elif seg_style == "italic":
        return doc.ensure_run_style(italic=True, height=h, text_color=color, **font_kw)
    elif seg_style == "bold_italic":
        return doc.ensure_run_style(bold=True, italic=True, height=h, text_color=color, **font_kw)
    elif seg_style == "code":
        code_font = s.get("code_font", "D2Coding")
        return doc.ensure_run_style(
            font_latin=code_font, font_hangul=code_font,
            height=s["code_height"], text_color=s["inline_code_text"])
    return "0"


def strip_inline_md(text: str) -> str:
    """Strip inline markdown formatting."""
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"___(.+?)___", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    return text
