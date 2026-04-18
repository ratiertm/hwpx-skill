"""Session management for HWPX CLI — undo/redo, project state tracking."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Optional

from hwpx import HwpxDocument


class Session:
    """Stateful session with undo/redo support for HWPX document editing."""

    MAX_UNDO = 50

    def __init__(self):
        self._doc: Optional[HwpxDocument] = None
        self._path: Optional[str] = None
        self._modified: bool = False
        self._undo_stack: list[bytes] = []
        self._redo_stack: list[bytes] = []

    # ── Project lifecycle ──────────────────────────────────────────────

    def has_project(self) -> bool:
        return self._doc is not None

    def get_doc(self) -> HwpxDocument:
        if self._doc is None:
            raise RuntimeError("No document open. Use 'document new' or 'document open' first.")
        return self._doc

    def set_doc(self, doc: HwpxDocument, path: Optional[str] = None):
        self._doc = doc
        self._path = path
        self._modified = False
        self._undo_stack.clear()
        self._redo_stack.clear()

    @property
    def path(self) -> Optional[str]:
        return self._path

    @path.setter
    def path(self, value: str):
        self._path = value

    @property
    def modified(self) -> bool:
        return self._modified

    # ── Snapshots for undo/redo ────────────────────────────────────────

    def snapshot(self):
        """Save current state for undo before a mutation."""
        if self._doc is None:
            return
        data = self._doc.to_bytes()
        self._undo_stack.append(data)
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._modified = True

    def undo(self) -> bool:
        if not self._undo_stack or self._doc is None:
            return False
        self._redo_stack.append(self._doc.to_bytes())
        prev = self._undo_stack.pop()
        self._doc = HwpxDocument.open(prev)
        return True

    def redo(self) -> bool:
        if not self._redo_stack or self._doc is None:
            return False
        self._undo_stack.append(self._doc.to_bytes())
        nxt = self._redo_stack.pop()
        self._doc = HwpxDocument.open(nxt)
        return True

    # ── Save ───────────────────────────────────────────────────────────

    def save(self, path: Optional[str] = None) -> str:
        doc = self.get_doc()
        save_path = path or self._path
        if save_path is None:
            raise ValueError("No save path specified. Provide a path argument.")
        doc.save_to_path(save_path)
        self._path = save_path
        self._modified = False
        return save_path

    # ── Info ───────────────────────────────────────────────────────────

    def info(self) -> dict:
        doc = self.get_doc()
        return {
            "path": self._path or "(unsaved)",
            "modified": self._modified,
            "sections": len(doc.sections),
            "paragraphs": len(doc.paragraphs),
            "undo_depth": len(self._undo_stack),
            "redo_depth": len(self._redo_stack),
        }
