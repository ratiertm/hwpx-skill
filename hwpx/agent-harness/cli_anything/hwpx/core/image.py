"""Image operations — add, list, remove images."""

from __future__ import annotations

from pathlib import Path

from hwpx import HwpxDocument


def add_image(doc: HwpxDocument, path: str,
              width: float | None = None,
              height: float | None = None) -> dict:
    """Add an image to the document.

    Args:
        doc: The HWPX document.
        path: Path to the image file.
        width: Optional width in mm.
        height: Optional height in mm.

    Returns:
        Summary dict.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    kwargs = {}
    if width is not None:
        kwargs["width"] = width
    if height is not None:
        kwargs["height"] = height

    doc.add_image(str(p), **kwargs)
    return {
        "path": str(p),
        "width": width,
        "height": height,
        "status": "added",
    }


def list_images(doc: HwpxDocument) -> list[dict]:
    """List all images in the document."""
    images = doc.list_images() if hasattr(doc, "list_images") else []
    return [{"index": i, "info": str(img)} for i, img in enumerate(images)]


def remove_image(doc: HwpxDocument, index: int) -> dict:
    """Remove an image by index."""
    images = doc.list_images() if hasattr(doc, "list_images") else []
    if index < 0 or index >= len(images):
        raise IndexError(f"Image index {index} out of range (0-{len(images)-1})")
    doc.remove_image(index)
    return {"index": index, "status": "removed"}
