"""XML text node operations for HWPX documents.

Centralizes all XML text replacement logic so that api.py and other modules
don't manipulate raw XML strings directly. Escape responsibility lives here.

Usage::

    from pyhwpxlib.xml_ops import replace_text_nodes, iter_section_entries

    xml_out = replace_text_nodes(xml_str, {"name": "홍길동", "company": "A&B"})
"""
from __future__ import annotations

import re
import zipfile
from xml.sax.saxutils import escape as _sax_escape


def safe_xml_escape(text: str) -> str:
    """Escape text for safe insertion into XML text nodes.

    Handles &, <, >, ", ' — the five XML special characters.
    Use this only for raw XML string manipulation (e.g., fill_template).
    For object-model insertion (e.g., T.add_text), do NOT escape —
    the serialization layer handles it automatically.
    """
    return _sax_escape(text, {"'": "&apos;", '"': "&quot;"})


def iter_section_entries(hwpx_path: str) -> list[str]:
    """List section XML entry names in a HWPX ZIP, sorted."""
    with zipfile.ZipFile(hwpx_path) as z:
        return sorted(
            n for n in z.namelist()
            if n.startswith('Contents/section') and n.endswith('.xml')
        )


_T_NODE_RE = re.compile(r'<hp:t>([^<]*)</hp:t>')


def replace_text_nodes(
    xml_text: str,
    replacements: dict[str, str],
    *,
    support_braced_keys: bool = True,
) -> str:
    """Replace placeholder text only inside ``<hp:t>...</hp:t>`` nodes.

    This is the single source of truth for text replacement in raw XML.
    It never touches XML attributes or tag names.

    Parameters
    ----------
    xml_text : str
        Raw XML string (e.g., section0.xml content).
    replacements : dict
        Mapping of placeholder → replacement value.
        Values are automatically XML-escaped.
    support_braced_keys : bool
        If True (default), for each key ``k`` also match ``{{k}}``.
        The braced pattern is tried first (longer match wins).

    Returns
    -------
    str
        Modified XML string with replacements applied inside <hp:t> nodes.

    Examples
    --------
    >>> replace_text_nodes('<hp:t>{{name}}</hp:t>', {"name": "홍길동"})
    '<hp:t>홍길동</hp:t>'

    >>> replace_text_nodes('<hp:t>A&amp;B</hp:t>', {"A&B": "X&Y"})
    '<hp:t>X&amp;Y</hp:t>'
    """
    # Build replacement list
    expanded: list[tuple[str, str]] = []
    for placeholder, value in replacements.items():
        if support_braced_keys and '{{' not in placeholder:
            # In braced mode: match {{key}} only, not bare "key"
            # This prevents short keys like "이름" from matching "이름:" in text
            expanded.append((f'{{{{{placeholder}}}}}', value))
        else:
            # Literal mode or key already contains braces
            expanded.append((placeholder, value))

    # Sort by escaped-placeholder length descending so longer patterns match first
    expanded.sort(key=lambda pair: len(safe_xml_escape(pair[0])), reverse=True)

    def _replacer(match: re.Match) -> str:
        content = match.group(1)
        for placeholder, value in expanded:
            xml_placeholder = safe_xml_escape(placeholder)
            xml_value = safe_xml_escape(value)
            content = content.replace(xml_placeholder, xml_value)
        return f'<hp:t>{content}</hp:t>'

    return _T_NODE_RE.sub(_replacer, xml_text)
