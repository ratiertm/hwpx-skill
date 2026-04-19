"""Table adapter — stable interface for python-hwpx table operations.

Wraps table/cell objects and routes calls through available methods
or XML fallback. Callers never need to know the python-hwpx version.

Usage::

    from pyhwpxlib.runtime_adapter import TableAdapter

    adapter = TableAdapter(table_obj)
    adapter.set_in_margin(left=510, right=510, top=141, bottom=141)
    adapter.set_cell_margin(cell_obj, left=141, right=141, top=141, bottom=141)
    adapter.set_cell_size(cell_obj, width=10000, height=2000)
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"


class TableAdapter:
    """Adapter for python-hwpx table operations with version-agnostic interface."""

    def __init__(self, table):
        self._table = table

    def set_in_margin(self, left: int = 0, right: int = 0,
                      top: int = 0, bottom: int = 0) -> None:
        """Set table inner margin (inMargin).

        Uses native method if available, falls back to XML manipulation.
        """
        if hasattr(self._table, 'set_in_margin'):
            self._table.set_in_margin(left=left, right=right, top=top, bottom=bottom)
        else:
            self._set_in_margin_xml(left, right, top, bottom)

    def _set_in_margin_xml(self, left: int, right: int, top: int, bottom: int) -> None:
        """XML fallback for set_in_margin."""
        el = self._table.element.find(f"{_HP}inMargin")
        if el is None:
            try:
                from lxml import etree
                el = etree.SubElement(self._table.element, f"{_HP}inMargin")
            except ImportError:
                import xml.etree.ElementTree as ET
                el = ET.SubElement(self._table.element, f"{_HP}inMargin")
        el.set("left", str(left))
        el.set("right", str(right))
        el.set("top", str(top))
        el.set("bottom", str(bottom))

    def set_out_margin(self, left: int = 0, right: int = 0,
                       top: int = 0, bottom: int = 0) -> None:
        """Set table outer margin (outMargin)."""
        el = self._table.element.find(f"{_HP}outMargin")
        if el is not None:
            el.set("left", str(left))
            el.set("right", str(right))
            el.set("top", str(top))
            el.set("bottom", str(bottom))

    @staticmethod
    def set_cell_margin(cell, left: int = 0, right: int = 0,
                        top: int = 0, bottom: int = 0) -> None:
        """Set cell margin (cellMargin).

        Uses native method if available, falls back to XML.
        """
        if hasattr(cell, 'set_margin'):
            cell.set_margin(left=left, right=right, top=top, bottom=bottom)
        else:
            el = cell.element.find(f"{_HP}cellMargin")
            if el is None:
                try:
                    from lxml import etree
                    el = etree.SubElement(cell.element, f"{_HP}cellMargin")
                except ImportError:
                    import xml.etree.ElementTree as ET
                    el = ET.SubElement(cell.element, f"{_HP}cellMargin")
            el.set("left", str(left))
            el.set("right", str(right))
            el.set("top", str(top))
            el.set("bottom", str(bottom))

    @staticmethod
    def set_cell_size(cell, width: int = 0, height: int = 0) -> None:
        """Set cell size (cellSz + sz).

        Updates both hp:cellSz and hp:sz for rendering consistency.
        """
        if hasattr(cell, 'set_size'):
            cell.set_size(width=width, height=height)
        else:
            for tag in (f"{_HP}cellSz", f"{_HP}sz"):
                el = cell.element.find(tag)
                if el is not None:
                    el.set("width", str(width))
                    el.set("height", str(height))

    @staticmethod
    def set_cell_border_fill_id(cell, border_fill_id: int | str) -> None:
        """Set cell borderFillIDRef.

        Uses native method if available, falls back to XML attribute.
        """
        if hasattr(cell, 'set_border_fill_id'):
            cell.set_border_fill_id(border_fill_id)
        else:
            cell.element.set("borderFillIDRef", str(border_fill_id))
