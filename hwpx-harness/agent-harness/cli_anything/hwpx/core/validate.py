"""Validation operations — schema and package validation."""

from __future__ import annotations

from pathlib import Path

from hwpx import HwpxDocument


def validate_document(doc_or_path) -> dict:
    """Validate HWPX document against XSD schema.

    Args:
        doc_or_path: HwpxDocument instance or path string.

    Returns:
        Dict with is_valid flag and any errors.
    """
    if isinstance(doc_or_path, (str, Path)):
        doc = HwpxDocument.open(str(doc_or_path))
    else:
        doc = doc_or_path

    try:
        result = doc.validate()
        if result is None or result is True:
            return {"is_valid": True, "errors": []}
        if isinstance(result, list):
            return {"is_valid": len(result) == 0, "errors": [str(e) for e in result]}
        return {"is_valid": bool(result), "errors": []}
    except Exception as e:
        return {"is_valid": False, "errors": [str(e)]}


def validate_package(path: str) -> dict:
    """Validate HWPX ZIP/OPC package structure.

    Args:
        path: Path to .hwpx file.

    Returns:
        Dict with validation results.
    """
    from hwpx.tools import validate_package as _validate_pkg

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        result = _validate_pkg(str(p))
        if result is None or result is True:
            return {"is_valid": True, "errors": []}
        if isinstance(result, list):
            return {"is_valid": len(result) == 0, "errors": [str(e) for e in result]}
        return {"is_valid": bool(result), "errors": []}
    except Exception as e:
        return {"is_valid": False, "errors": [str(e)]}
