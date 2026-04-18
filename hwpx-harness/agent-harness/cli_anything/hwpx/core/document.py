"""Document operations — create, open, save, info."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from hwpx import HwpxDocument


def new_document() -> HwpxDocument:
    """Create a new blank HWPX document."""
    return HwpxDocument.new()


def open_document(path: str) -> HwpxDocument:
    """Open an existing HWPX file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not p.suffix.lower() == ".hwpx":
        raise ValueError(f"Not a .hwpx file: {path}")
    return HwpxDocument.open(str(p))


def save_document(doc: HwpxDocument, path: str) -> str:
    """Save document to path. Returns saved path."""
    doc.save_to_path(path)
    return path


def get_document_info(doc: HwpxDocument) -> dict:
    """Get document metadata and structure summary."""
    sections = doc.sections
    paragraphs = doc.paragraphs
    images = doc.list_images() if hasattr(doc, "list_images") else []

    total_text_len = 0
    for p in paragraphs:
        for r in getattr(p, "runs", []):
            total_text_len += len(getattr(r, "text", "") or "")

    return {
        "sections": len(sections),
        "paragraphs": len(paragraphs),
        "images": len(images),
        "text_length": total_text_len,
        "styles": len(doc.styles) if hasattr(doc, "styles") else 0,
    }
