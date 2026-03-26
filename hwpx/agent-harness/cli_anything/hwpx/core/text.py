"""Text operations — extract, find, replace."""

from __future__ import annotations

from typing import Optional

from hwpx import HwpxDocument


def extract_text(doc: HwpxDocument) -> str:
    """Extract all text from the document."""
    return doc.export_text()


def extract_markdown(doc: HwpxDocument) -> str:
    """Export document content as Markdown."""
    return doc.export_markdown()


def extract_html(doc: HwpxDocument) -> str:
    """Export document content as HTML."""
    return doc.export_html()


def find_text(doc: HwpxDocument, query: str, style: Optional[str] = None) -> list[dict]:
    """Find text occurrences in the document.

    Returns list of dicts with section_idx, paragraph_idx, run_idx, text, context.
    """
    results = []
    for sec_idx, section in enumerate(doc.sections):
        for para_idx, para in enumerate(section.paragraphs):
            for run_idx, run in enumerate(getattr(para, "runs", [])):
                run_text = getattr(run, "text", "") or ""
                if query.lower() in run_text.lower():
                    results.append({
                        "section": sec_idx,
                        "paragraph": para_idx,
                        "run": run_idx,
                        "text": run_text,
                    })
    return results


def replace_text(doc: HwpxDocument, old: str, new: str) -> int:
    """Replace all occurrences of old text with new text. Returns count."""
    count = doc.replace_text_in_runs(old, new)
    return count if isinstance(count, int) else 0


def add_paragraph(doc: HwpxDocument, text: str, section_idx: int = 0) -> dict:
    """Add a paragraph to the specified section."""
    doc.add_paragraph(text)
    return {"text": text, "section": section_idx, "status": "added"}
