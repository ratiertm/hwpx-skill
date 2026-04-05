"""Markdown -> HWPX converter with CSS-driven styling.

Ported from ratiertm-hwpx (cli_anything/hwpx/core/converter.py) to use
pyhwpxlib's functional API.
"""

from __future__ import annotations

import re
import uuid as _uuid

from .hwpx_file import HWPXFile

_PAGE_WIDTH = 42520  # A4 body width in hwpunit

# -- MD->HWPX Style Presets ------------------------------------------------

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
        "bullet_chars": ["\u2022", "\u25e6", "\u25aa", "\u2023", "\u2043"],
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
        "bullet_chars": ["\u2022", "\u25e6", "\u25aa", "\u2023", "\u2043"],
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
        "bullet_chars": ["\u2022", "\u25e6", "\u25aa", "\u2023", "\u2043"],
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
        "bullet_chars": ["\u2022", "\u2013", "\u00b7", "\u2023", "\u2043"],
    },
}

DEFAULT_STYLE = "github"


# -- Converter -------------------------------------------------------------

def convert_markdown_to_hwpx(
    hwpx_file: HWPXFile,
    content: str,
    style_name: str = DEFAULT_STYLE,
) -> int:
    """Parse Markdown and build HWPX with selectable CSS-based styling."""
    from .api import add_paragraph, add_line, add_code_block
    from .api import add_bullet_list, add_numbered_list
    from .api import add_nested_bullet_list, add_nested_numbered_list
    from .style_manager import ensure_char_style, ensure_para_style

    s = MD_STYLES.get(style_name, MD_STYLES[DEFAULT_STYLE])

    # Strip HTML -- HWPX has no HTML equivalent
    content = re.sub(r"<style[^>]*>.*?</style>", "", content,
                     flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<script[^>]*>.*?</script>", "", content,
                     flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<[^>]+>", "", content)

    lines = content.split("\n")
    element_count = 0
    i = 0

    # Body paragraph style from CSS
    body_para_kw: dict = {}
    if s.get("line_spacing"):
        body_para_kw["line_spacing_value"] = s["line_spacing"]
    body_para_id = None
    if body_para_kw:
        body_para_id = ensure_para_style(hwpx_file, **body_para_kw)

    while i < len(lines):
        line = lines[i]

        # -- Code block --
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip() or None
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            add_code_block(
                hwpx_file, "\n".join(code_lines), language=lang,
                font=s.get("code_font", "D2Coding"),
                bg_color=s["code_bg"],
            )
            element_count += len(code_lines) + (1 if lang else 0)
            add_paragraph(hwpx_file, "")
            continue

        # -- Table --
        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            element_count += _handle_table(hwpx_file, lines, i, s)
            while i < len(lines) and lines[i].strip().startswith("|"):
                i += 1
            continue

        # -- Horizontal rule --
        stripped = line.strip()
        if _is_horizontal_rule(stripped):
            add_line(hwpx_file, 0, 0, _PAGE_WIDTH, 0,
                     line_color=s["hr_color"], line_width=int(s["hr_width"]))
            element_count += 1
            i += 1
            continue

        # -- Empty line --
        if not stripped:
            i += 1
            continue

        # -- Heading --
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            _handle_heading(hwpx_file, heading_match, element_count, s)
            element_count += 1
            i += 1
            continue

        # -- Blockquote --
        if stripped.startswith(">"):
            count, i = _handle_blockquote(hwpx_file, lines, i, s)
            element_count += count
            continue

        # -- Bullet list --
        if re.match(r"^(\s*)([-*+])\s+(.+)$", stripped):
            count, i = _handle_bullet_list(hwpx_file, lines, i, s)
            element_count += count
            continue

        # -- Numbered list --
        if re.match(r"^(\s*)\d+[.)]\s+(.+)$", stripped):
            count, i = _handle_numbered_list(hwpx_file, lines, i)
            element_count += count
            continue

        # -- Regular paragraph --
        _add_rich_paragraph(hwpx_file, stripped, style=s,
                            para_pr_id=body_para_id)
        element_count += 1
        i += 1

    return element_count


# -- Element handlers -------------------------------------------------------

def _is_horizontal_rule(stripped: str) -> bool:
    if not stripped or len(stripped.replace(" ", "")) < 3:
        return False
    if not all(c in "-*_ " for c in stripped):
        return False
    clean = stripped.replace(" ", "")
    return len(set(clean)) == 1 and clean[0] in "-*_"


def _handle_heading(
    hwpx_file: HWPXFile, match, element_count: int, s: dict,
) -> None:
    from .api import add_paragraph, add_line
    from .style_manager import ensure_char_style

    level = len(match.group(1))
    heading_text = strip_inline_md(match.group(2))

    if element_count > 0 and s.get("heading_spacing", True):
        add_paragraph(hwpx_file, "")

    heading_sizes = {
        1: s["h1_height"], 2: s["h2_height"], 3: s["h3_height"],
        4: s["h4_height"], 5: s["h5_height"], 6: s["h6_height"],
    }
    h_size = heading_sizes.get(level, s["body_height"])
    h_color = s.get("heading_color") or s.get("body_color")
    h_kw: dict = {}
    if h_color:
        h_kw["text_color"] = h_color
    char_id = ensure_char_style(hwpx_file, bold=True, height=h_size, **h_kw)
    add_paragraph(hwpx_file, heading_text, char_pr_id_ref=char_id)

    if s["h1_h2_border"] and level <= 2:
        add_line(hwpx_file, 0, 0, _PAGE_WIDTH, 0,
                 line_color=s["heading_border_color"], line_width=71)


def _handle_blockquote(
    hwpx_file: HWPXFile, lines: list[str], i: int, s: dict,
) -> tuple[int, int]:
    from .api import add_paragraph
    from .style_manager import ensure_char_style

    quote_lines: list[str] = []
    while i < len(lines) and lines[i].strip().startswith(">"):
        qt = re.sub(r"^>\s?", "", lines[i].strip())
        quote_lines.append(qt)
        i += 1
    quote_text = " ".join(quote_lines)
    char_id = ensure_char_style(
        hwpx_file, italic=True, text_color=s["quote_color"],
        height=s["body_height"],
    )
    add_paragraph(hwpx_file, f"  {quote_text}", char_pr_id_ref=char_id)
    add_paragraph(hwpx_file, "")
    return 1, i


def _handle_bullet_list(
    hwpx_file: HWPXFile, lines: list[str], i: int, s: dict,
) -> tuple[int, int]:
    from .api import add_bullet_list, add_nested_bullet_list

    bullet_items: list[tuple[int, str]] = []
    while i < len(lines):
        bm = re.match(r"^(\s*)([-*+])\s+(.+)$", lines[i])
        if not bm:
            break
        indent_level = len(bm.group(1).replace("\t", "    ")) // 2
        bullet_items.append((indent_level, strip_inline_md(bm.group(3))))
        i += 1

    chars = s["bullet_chars"]
    if any(level > 0 for level, _ in bullet_items):
        add_nested_bullet_list(hwpx_file, bullet_items, bullet_chars=chars)
    else:
        add_bullet_list(
            hwpx_file,
            [text for _, text in bullet_items],
            bullet_char=chars[0],
        )
    return len(bullet_items), i


def _handle_numbered_list(
    hwpx_file: HWPXFile, lines: list[str], i: int,
) -> tuple[int, int]:
    from .api import add_numbered_list, add_nested_numbered_list

    num_items: list[tuple[int, str]] = []
    while i < len(lines):
        nm = re.match(r"^(\s*)\d+[.)]\s+(.+)$", lines[i])
        if not nm:
            break
        indent_level = len(nm.group(1).replace("\t", "    ")) // 2
        num_items.append((indent_level, strip_inline_md(nm.group(2))))
        i += 1

    if any(level > 0 for level, _ in num_items):
        add_nested_numbered_list(hwpx_file, num_items)
    else:
        add_numbered_list(hwpx_file, [text for _, text in num_items])
    return len(num_items), i


def _handle_table(
    hwpx_file: HWPXFile, lines: list[str], i: int, s: dict,
) -> int:
    from .api import add_table, add_paragraph

    table_lines: list[str] = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        table_lines.append(lines[i])
        i += 1

    rows: list[list[str]] = []
    for tl in table_lines:
        cells = [c.strip() for c in tl.strip().strip("|").split("|")]
        # Skip separator rows like |---|---|
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

    # Prepare data with inline markdown stripped
    clean_data: list[list[str]] = []
    for row_data in rows:
        cleaned_row = [strip_inline_md(cell_val) for cell_val in row_data[:max_cols]]
        # Pad to max_cols if needed
        while len(cleaned_row) < max_cols:
            cleaned_row.append("")
        clean_data.append(cleaned_row)

    # Header background colors
    cell_colors: dict[tuple[int, int], str] | None = None
    if len(rows) > 1:
        cell_colors = {}
        for c_idx in range(max_cols):
            cell_colors[(0, c_idx)] = s["table_header_bg"]

    # Cell margins
    pad = s.get("table_cell_padding", (450, 975))
    pad_v, pad_h = pad[0], pad[1]
    cell_margin = (pad_h, pad_h, pad_v, pad_v)  # left, right, top, bottom

    # Row heights: header taller than data rows
    num_rows = len(clean_data)
    row_heights = [2400] + [2000] * (num_rows - 1) if num_rows > 0 else None

    # Cell alignment: header CENTER, data CENTER (numbers detected as RIGHT by preset)
    import re as _re
    cell_aligns: dict[tuple[int, int], str] = {}
    for c_idx in range(max_cols):
        cell_aligns[(0, c_idx)] = "CENTER"  # header row
    for r_idx in range(1, num_rows):
        for c_idx in range(max_cols):
            val = clean_data[r_idx][c_idx] if c_idx < len(clean_data[r_idx]) else ""
            if _re.search(r'[\d]', val) and _re.search(r'[\d%억원만조달러배개명\+\-\.,/~]', val):
                cell_aligns[(r_idx, c_idx)] = "RIGHT"
            else:
                cell_aligns[(r_idx, c_idx)] = "CENTER"

    # Header text style: bold
    cell_styles: dict[tuple[int, int], dict] = {}
    for c_idx in range(max_cols):
        cell_styles[(0, c_idx)] = {"bold": True}

    add_table(
        hwpx_file,
        num_rows,
        max_cols,
        data=clean_data,
        width=_PAGE_WIDTH,
        col_widths=col_widths,
        cell_colors=cell_colors,
        cell_margin=cell_margin,
        row_heights=row_heights,
        cell_aligns=cell_aligns,
        cell_styles=cell_styles,
    )
    add_paragraph(hwpx_file, "")
    return 1


# -- Inline formatting ------------------------------------------------------

def parse_inline_segments(text: str) -> list[tuple[str, str]]:
    """Parse inline markdown into segments of (style, text)."""
    segments: list[tuple[str, str]] = []
    pattern = re.compile(
        r"!\[([^\]]*)\]\([^)]+\)"       # image (alt text only)
        r"|\[([^\]]+)\]\(([^)]+)\)"      # link
        r"|`([^`]+)`"                     # inline code
        r"|\*\*\*(.+?)\*\*\*"            # bold italic
        r"|\*\*(.+?)\*\*"                # bold
        r"|\*(.+?)\*"                     # italic
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


# -- Rich paragraph (mixed inline formatting) --------------------------------

def _add_rich_paragraph(
    hwpx_file: HWPXFile,
    md_text: str,
    style: dict | None = None,
    para_pr_id: str | None = None,
) -> None:
    """Add a single paragraph with inline formatting.

    For simple text, delegates to add_paragraph.  For mixed inline
    formatting (bold + normal + link in one line), builds raw XML
    with multiple <hp:run> elements.
    """
    from .api import add_paragraph, _new_raw_para

    segments = parse_inline_segments(md_text)

    # Simple case: single normal segment -> plain paragraph
    if len(segments) == 1 and segments[0][0] == "normal":
        kw: dict = {}
        if para_pr_id is not None:
            kw["para_pr_id_ref"] = para_pr_id
        add_paragraph(hwpx_file, segments[0][1], **kw)
        return

    # Complex case: build raw XML with multiple runs
    para = _new_raw_para(hwpx_file)
    if para_pr_id is not None:
        para.para_pr_id_ref = para_pr_id

    xml_parts: list[str] = []
    for seg_type, text in segments:
        if not text:
            continue
        if seg_type.startswith("link:"):
            xml_parts.append(_build_link_run_xml(hwpx_file, seg_type[5:], text, style))
        else:
            char_id = _style_for_segment(hwpx_file, seg_type, style=style)
            xml_parts.append(
                f'<hp:run charPrIDRef="{char_id}">'
                f'<hp:t>{_escape_xml(text)}</hp:t>'
                f'</hp:run>'
            )

    para.raw_xml_content = "".join(xml_parts)


def _build_link_run_xml(
    hwpx_file: HWPXFile, url: str, text: str, style: dict | None,
) -> str:
    """Build three <hp:run> elements for a hyperlink inside a rich paragraph."""
    from .style_manager import ensure_char_style
    from .writer.shape_writer import _escape, _id

    s = style or MD_STYLES[DEFAULT_STYLE]
    link_char_id = ensure_char_style(
        hwpx_file, underline=True,
        text_color=s.get("link_color", "#0969DA"),
        height=s.get("body_height", 1000),
    )

    field_id = _id()
    field_id2 = _id()
    escaped_url = _escape(url)
    escaped_text = _escape(text)
    command_val = _escape(url.replace(":", "\\:") + ";1;0;0;")

    parts: list[str] = []

    # Run 1: fieldBegin
    parts.append('<hp:run charPrIDRef="0">')
    parts.append('<hp:ctrl>')
    parts.append(
        f'<hp:fieldBegin id="{field_id}" type="HYPERLINK"'
        f' name="" editable="0" dirty="0" zorder="-1" fieldid="{field_id2}">'
    )
    parts.append('<hp:parameters cnt="6" name="">')
    parts.append('<hp:integerParam name="Prop">0</hp:integerParam>')
    parts.append(f'<hp:stringParam name="Command">{command_val}</hp:stringParam>')
    parts.append(f'<hp:stringParam name="Path">{escaped_url}</hp:stringParam>')
    parts.append('<hp:stringParam name="Category">HWPHYPERLINK_TYPE_URL</hp:stringParam>')
    parts.append('<hp:stringParam name="TargetType">HWPHYPERLINK_TARGET_BOOKMARK</hp:stringParam>')
    parts.append('<hp:stringParam name="DocOpenType">HWPHYPERLINK_JUMP_CURRENTTAB</hp:stringParam>')
    parts.append('</hp:parameters>')
    parts.append('</hp:fieldBegin>')
    parts.append('</hp:ctrl>')
    parts.append('</hp:run>')

    # Run 2: visible text
    parts.append(f'<hp:run charPrIDRef="{link_char_id}">')
    parts.append(f'<hp:t>{escaped_text}</hp:t>')
    parts.append('</hp:run>')

    # Run 3: fieldEnd
    parts.append('<hp:run charPrIDRef="0">')
    parts.append('<hp:ctrl>')
    parts.append(f'<hp:fieldEnd beginIDRef="{field_id}"/>')
    parts.append('</hp:ctrl>')
    parts.append('</hp:run>')

    return "".join(parts)


def _style_for_segment(
    hwpx_file: HWPXFile, seg_style: str, style: dict | None = None,
) -> str:
    """Return a charPrIDRef using the active MD style preset."""
    from .style_manager import ensure_char_style

    s = style or MD_STYLES[DEFAULT_STYLE]
    h = s["body_height"]
    color = s.get("body_color")
    font = s.get("body_font")
    font_kw: dict = {}
    if font:
        font_kw["font_name"] = font

    if seg_style == "bold":
        return ensure_char_style(hwpx_file, bold=True, height=h,
                                 text_color=color, **font_kw)
    elif seg_style == "italic":
        return ensure_char_style(hwpx_file, italic=True, height=h,
                                 text_color=color, **font_kw)
    elif seg_style == "bold_italic":
        return ensure_char_style(hwpx_file, bold=True, italic=True,
                                 height=h, text_color=color, **font_kw)
    elif seg_style == "code":
        code_font = s.get("code_font", "D2Coding")
        return ensure_char_style(
            hwpx_file, font_name=code_font,
            height=s["code_height"], text_color=s["inline_code_text"],
        )
    return "0"


def _escape_xml(text: str) -> str:
    """Escape XML special characters in text content."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
