"""JSON round-trip for HWPX documents.

Provides HWPX → JSON export, JSON → HWPX import, and section-level patching.
"""
from .encoder import to_json
from .decoder import from_json, patch
from .overlay import extract_overlay, apply_overlay

__all__ = ["to_json", "from_json", "patch", "extract_overlay", "apply_overlay"]
