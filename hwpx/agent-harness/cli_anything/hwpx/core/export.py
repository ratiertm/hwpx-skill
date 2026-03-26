"""Export operations — text, markdown, HTML output."""

from __future__ import annotations

from pathlib import Path

from hwpx import HwpxDocument


def export_to_file(doc: HwpxDocument, output_path: str,
                   fmt: str = "text") -> dict:
    """Export document content to a file.

    Args:
        doc: The HWPX document.
        output_path: Destination file path.
        fmt: Export format — 'text', 'markdown', or 'html'.

    Returns:
        Summary dict with path and size.
    """
    if fmt == "text":
        content = doc.export_text()
    elif fmt in ("markdown", "md"):
        content = doc.export_markdown()
    elif fmt == "html":
        content = doc.export_html()
    else:
        raise ValueError(f"Unknown format: {fmt}. Use 'text', 'markdown', or 'html'.")

    p = Path(output_path)
    p.write_text(content, encoding="utf-8")
    return {
        "path": str(p),
        "format": fmt,
        "size_bytes": p.stat().st_size,
        "status": "exported",
    }
