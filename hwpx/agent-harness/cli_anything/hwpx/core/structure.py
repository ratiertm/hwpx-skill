"""Structure operations — sections, headers, footers, shapes, formatting."""

from __future__ import annotations

from hwpx import HwpxDocument


def list_sections(doc: HwpxDocument) -> list[dict]:
    """List all sections with paragraph counts."""
    return [
        {
            "index": i,
            "paragraphs": len(section.paragraphs),
        }
        for i, section in enumerate(doc.sections)
    ]


def add_section(doc: HwpxDocument) -> dict:
    """Add a new section to the document."""
    doc.add_section()
    return {"sections": len(doc.sections), "status": "added"}


def set_header(doc: HwpxDocument, text: str, section_idx: int = 0) -> dict:
    """Set header text using real Hancom ctrl structure."""
    doc.add_header(text, section_index=section_idx)
    return {"text": text, "section": section_idx, "status": "set"}


def set_footer(doc: HwpxDocument, text: str, section_idx: int = 0) -> dict:
    """Set footer text using real Hancom ctrl structure."""
    doc.add_footer(text, section_index=section_idx)
    return {"text": text, "section": section_idx, "status": "set"}


def add_bookmark(doc: HwpxDocument, name: str) -> dict:
    """Add a bookmark at the current position."""
    doc.add_bookmark(name)
    return {"name": name, "status": "added"}


def add_hyperlink(doc: HwpxDocument, url: str, text: str | None = None) -> dict:
    """Add a hyperlink."""
    doc.add_hyperlink(text or url, url)
    return {"url": url, "text": text or url, "status": "added"}


def add_page_number(doc: HwpxDocument, pos: str = "BOTTOM_CENTER",
                    format_type: str = "DIGIT", side_char: str = "-") -> dict:
    """Add page number."""
    doc.add_page_number(pos=pos, format_type=format_type, side_char=side_char)
    return {"pos": pos, "format": format_type, "status": "added"}


def add_footnote(doc: HwpxDocument, text: str, anchor: str = "") -> dict:
    """Add a footnote."""
    doc.add_footnote(text, anchor_text=anchor)
    return {"text": text, "anchor": anchor, "status": "added"}


def add_endnote(doc: HwpxDocument, text: str, anchor: str = "") -> dict:
    """Add an endnote."""
    doc.add_endnote(text, anchor_text=anchor)
    return {"text": text, "anchor": anchor, "status": "added"}


def add_equation(doc: HwpxDocument, script: str) -> dict:
    """Add an equation."""
    doc.add_equation(script)
    return {"script": script, "status": "added"}


def add_rectangle(doc: HwpxDocument, width: int = 14400, height: int = 7200,
                  line_color: str = "#000000", line_width: str = "283",
                  fill_color: str | None = None) -> dict:
    """Add a rectangle shape. line_width: 283=1mm, 566=2mm, 850=3mm"""
    doc.add_rectangle(width, height, line_color=line_color, line_width=line_width, fill_color=fill_color)
    return {"width": width, "height": height, "line_width": line_width, "fill": fill_color, "status": "added"}


def add_ellipse(doc: HwpxDocument, width: int = 14400, height: int = 7200,
                line_color: str = "#000000", line_width: str = "283",
                fill_color: str | None = None) -> dict:
    """Add an ellipse shape. line_width: 283=1mm, 566=2mm, 850=3mm"""
    doc.add_ellipse(width, height, line_color=line_color, line_width=line_width, fill_color=fill_color)
    return {"width": width, "height": height, "line_width": line_width, "fill": fill_color, "status": "added"}


def add_line(doc: HwpxDocument, length: int = 20000, line_color: str = "#000000",
             line_width: str = "283") -> dict:
    """Add a horizontal line. line_width: 283=1mm, 566=2mm, 850=3mm"""
    doc.add_line(0, 0, length, 0, line_color=line_color, line_width=line_width)
    return {"length": length, "color": line_color, "line_width": line_width, "status": "added"}


def add_bullet_list(doc: HwpxDocument, items: list[str],
                    bullet_char: str = "●") -> dict:
    """Add a bullet list."""
    doc.add_bullet_list(items, bullet_char=bullet_char)
    return {"items": len(items), "char": bullet_char, "status": "added"}


def add_numbered_list(doc: HwpxDocument, items: list[str],
                      format_string: str = "^1.") -> dict:
    """Add a numbered list."""
    doc.add_numbered_list(items, format_string=format_string)
    return {"items": len(items), "format": format_string, "status": "added"}


def set_cell_background(doc: HwpxDocument, table_index: int,
                        row: int, col: int, color: str) -> dict:
    """Set table cell background color."""
    sections = doc.sections
    tables = []
    for section in sections:
        for para in section.paragraphs:
            tables.extend(para.tables)
    if table_index >= len(tables):
        raise IndexError(f"Table index {table_index} out of range (have {len(tables)})")
    tables[table_index].set_cell_background(row, col, color)
    return {"table": table_index, "row": row, "col": col, "color": color, "status": "set"}


def add_styled_text(doc: HwpxDocument, text: str, *,
                    bold: bool = False, italic: bool = False, underline: bool = False,
                    font_size: int | None = None, text_color: str | None = None) -> dict:
    """Add styled text paragraph."""
    kwargs = {"bold": bold, "italic": italic, "underline": underline}
    if font_size is not None:
        kwargs["height"] = font_size * 100  # pt to hwpunit
    if text_color is not None:
        kwargs["text_color"] = text_color
    char_id = doc.ensure_run_style(**kwargs)
    doc.add_paragraph(text, char_pr_id_ref=char_id)
    return {"text": text[:50], "bold": bold, "italic": italic, "status": "added"}


def add_code_block(doc: HwpxDocument, code: str, *,
                   language: str | None = None,
                   font: str = "D2Coding") -> dict:
    """Add a code block with monospace font and background."""
    paras = doc.add_code_block(code, language=language, font=font)
    return {"lines": len(paras), "language": language, "status": "added"}


def add_nested_bullet_list(doc: HwpxDocument, items: list[tuple[int, str]]) -> dict:
    """Add a nested bullet list. Each item is (level, text)."""
    paras = doc.add_nested_bullet_list(items)
    return {"items": len(paras), "levels": len(set(l for l, _ in items)), "status": "added"}


def add_nested_numbered_list(doc: HwpxDocument, items: list[tuple[int, str]]) -> dict:
    """Add a nested numbered list. Each item is (level, text)."""
    paras = doc.add_nested_numbered_list(items)
    return {"items": len(paras), "levels": len(set(l for l, _ in items)), "status": "added"}


def set_columns(doc: HwpxDocument, col_count: int = 2, *,
                gap: int = 1200, separator: str | None = None) -> dict:
    """Set column layout for the document."""
    kwargs: dict = {}
    if separator:
        kwargs["separator_type"] = separator
    doc.set_columns(col_count, same_gap=gap, **kwargs)
    return {"columns": col_count, "gap": gap, "separator": separator, "status": "set"}


def set_cell_gradient(doc: HwpxDocument, table_index: int,
                      row: int, col: int, *,
                      start_color: str = "#FFFFFF",
                      end_color: str = "#000000",
                      gradient_type: str = "LINEAR",
                      angle: int = 0) -> dict:
    """Set gradient fill on a table cell."""
    doc.set_cell_gradient(table_index, row, col,
                          start_color=start_color, end_color=end_color,
                          gradient_type=gradient_type, angle=angle)
    return {"table": table_index, "row": row, "col": col,
            "start": start_color, "end": end_color,
            "type": gradient_type, "status": "set"}
