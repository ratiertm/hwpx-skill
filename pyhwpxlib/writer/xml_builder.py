"""Port of XMLStringBuilder.java - fluent XML string builder.

Faithful port of the Java original with:
- Fluent API returning self
- Element stack with ElementInfo tracking
- Lazy tag closing (don't write > until first child or text)
- XML escape for attributes and text content
- attribute() skips None values
- Boolean as "0"/"1"
- Float formatted without trailing zeros
- namespace() adds xmlns:prefix="uri"
- clear() resets for reuse
- to_string() closes all open elements
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Union


_PREFIX = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'


class _ElementInfo:
    """Tracks state for a single open XML element."""

    __slots__ = ("name", "_has_child", "_child_index")

    def __init__(self, name: str) -> None:
        self.name = name
        self._has_child = False
        self._child_index = 0

    def has_child(self) -> bool:
        return self._has_child

    def had_child(self) -> None:
        self._has_child = True

    def child_index(self) -> int:
        return self._child_index

    def increase_child_index(self) -> None:
        self._child_index += 1


class XMLStringBuilder:
    """Builds an XML string incrementally using a fluent API."""

    def __init__(self) -> None:
        self._parts: List[str] = [_PREFIX]
        self._stack: List[_ElementInfo] = []

    # ------------------------------------------------------------------
    # Element lifecycle
    # ------------------------------------------------------------------

    def raw(self, xml_string: str) -> XMLStringBuilder:
        """Append raw XML string without escaping."""
        if self._stack:
            current = self._stack[-1]
            if not current.has_child():
                self._parts.append(">")
            current.had_child()
            current.increase_child_index()
        self._parts.append(xml_string)
        return self

    def open_element(self, name: str) -> XMLStringBuilder:
        if self._stack:
            current = self._stack[-1]
            if not current.has_child():
                self._parts.append(">")
            current.had_child()
            current.increase_child_index()

        self._parts.append("<")
        self._parts.append(name)
        self._stack.append(_ElementInfo(name))
        return self

    def close_element(self) -> XMLStringBuilder:
        if not self._stack:
            return self

        info = self._stack.pop()
        if info.has_child():
            self._parts.append("</")
            self._parts.append(info.name)
            self._parts.append(">")
        else:
            self._parts.append("/>")
        return self

    # ------------------------------------------------------------------
    # Namespace
    # ------------------------------------------------------------------

    def namespace(self, ns: Optional[Enum]) -> XMLStringBuilder:
        """Add xmlns:prefix="uri" declaration.

        *ns* is expected to be a member of :class:`~pyhwpxlib.constants.namespaces.Namespaces`
        whose ``.name`` is the prefix (e.g. ``ha``) and ``.value`` is the URI.
        """
        if not self._stack or self._stack[-1].has_child() or ns is None:
            return self

        self._parts.append(" xmlns:")
        self._parts.append(ns.name)
        self._parts.append('="')
        self._parts.append(ns.value)
        self._parts.append('"')
        return self

    # ------------------------------------------------------------------
    # Attributes
    # ------------------------------------------------------------------

    def attribute(
        self,
        name: str,
        value: Union[str, int, float, bool, Enum, None],
    ) -> XMLStringBuilder:
        """Write an attribute.  Skips silently when *value* is ``None``."""
        if value is None:
            return self
        if not self._stack or self._stack[-1].has_child():
            return self

        # Dispatch by type
        if isinstance(value, bool):
            str_val = "1" if value else "0"
        elif isinstance(value, float):
            str_val = _format_float(value)
        elif isinstance(value, int):
            str_val = str(value)
        elif isinstance(value, Enum):
            # Some enums have tuple values like ('NONE', 0) with a .str property
            if hasattr(value, 'str'):
                str_val = value.str
            elif isinstance(value.value, tuple):
                str_val = str(value.value[0])
            else:
                str_val = str(value.value)
        else:
            str_val = str(value)

        self._parts.append(" ")
        self._parts.append(name)
        self._parts.append('="')
        self._parts.append(_escape_xml_attr(str_val))
        self._parts.append('"')
        return self

    def attribute_index(
        self,
        name: str,
        value: Union[Enum, None],
    ) -> XMLStringBuilder:
        """Write an attribute whose value is the enum's index (ordinal)."""
        if value is None:
            return self
        if not self._stack or self._stack[-1].has_child():
            return self

        # For Python enums that expose an index via .index() or we derive from list position
        if hasattr(value, "index"):
            idx = value.index()
        else:
            # Fallback: use list position in the enum class
            idx = list(type(value)).index(value)

        return self.attribute(name, str(idx))

    # ------------------------------------------------------------------
    # Text content
    # ------------------------------------------------------------------

    def text(self, text: Optional[str]) -> XMLStringBuilder:
        """Write escaped text content inside the current element."""
        if not text:
            return self

        if self._stack:
            if not self._stack[-1].has_child():
                self._parts.append(">")
            self._stack[-1].had_child()

        escaped = text.replace("&", "&amp;")
        escaped = escaped.replace(">", "&gt;")
        escaped = escaped.replace("<", "&lt;")
        escaped = escaped.replace("\n", "\r\n")
        self._parts.append(escaped)
        return self

    # ------------------------------------------------------------------
    # Raw content
    # ------------------------------------------------------------------

    def raw(self, text: str) -> XMLStringBuilder:
        """Write raw XML content without escaping."""
        if self._stack:
            if not self._stack[-1].has_child():
                self._parts.append(">")
            self._stack[-1].had_child()
        self._parts.append(text)
        return self

    # ------------------------------------------------------------------
    # Finalization
    # ------------------------------------------------------------------

    def to_string(self) -> str:
        """Close all remaining open elements and return the XML string."""
        while self._stack:
            self.close_element()
        return "".join(self._parts)

    def __str__(self) -> str:
        return self.to_string()

    def clear(self) -> XMLStringBuilder:
        """Reset the builder for reuse (starts fresh with XML declaration)."""
        self._parts.clear()
        self._parts.append(_PREFIX)
        self._stack.clear()
        return self


# ======================================================================
# Private helpers
# ======================================================================

def _escape_xml_attr(s: str) -> str:
    """Escape a string for use in an XML attribute value."""
    # & must be first!
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _format_float(value: float) -> str:
    """Format a float without unnecessary trailing zeros (like Java DecimalFormat #.######)."""
    formatted = f"{value:.6f}"
    # Strip trailing zeros but keep at least one digit after decimal if needed
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted
