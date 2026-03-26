"""Structure operations — sections, headers, footers, shapes."""

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
    """Set header text for a section."""
    doc.set_header_text(text)
    return {"text": text, "section": section_idx, "status": "set"}


def set_footer(doc: HwpxDocument, text: str, section_idx: int = 0) -> dict:
    """Set footer text for a section."""
    doc.set_footer_text(text)
    return {"text": text, "section": section_idx, "status": "set"}


def add_bookmark(doc: HwpxDocument, name: str) -> dict:
    """Add a bookmark at the current position."""
    doc.add_bookmark(name)
    return {"name": name, "status": "added"}


def add_hyperlink(doc: HwpxDocument, url: str, text: str | None = None) -> dict:
    """Add a hyperlink."""
    doc.add_hyperlink(url, text or url)
    return {"url": url, "text": text or url, "status": "added"}
