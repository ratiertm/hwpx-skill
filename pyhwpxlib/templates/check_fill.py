"""XML-level fill verification — fast alternative to PNG visual check.

Design Ref: render-perf-opt.design.md §3.2 + §4.1.2 — Plan SC FR-06/FR-07.

Why this exists: rendering a PNG to verify "is the form filled correctly?"
costs ~1s per page (RhwpEngine + cairosvg + font subset). For mid-cycle
iteration this is overkill. ``check_fill`` answers the same question by
inspecting the schema and the source HWPX directly — no rendering — in
~10ms.

Two strategies, in order of preference:

1. **Schema-driven** (when ``schema.json`` exists): compare keys present
   in the user's ``data`` dict against the schema's expected field keys.
   ``filled`` = keys with non-empty values. ``empty`` = expected keys
   missing or whose value is the empty string.

2. **Pattern fallback** (no schema): scan the template's
   ``Contents/section0.xml`` for placeholder shapes — ``{{key}}`` markers
   and runs of three or more underscores within an ``<hp:t>`` text node.
   Each detected placeholder becomes a ``placeholder`` entry that hasn't
   been replaced yet by the caller's data.

Both strategies also surface placeholders in the source HWPX (residual
``{{...}}`` or ``___``) so the caller knows whether the original template
itself still has guide text not covered by the schema.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Union


# Patterns for placeholder detection inside ``<hp:t>`` text nodes.
_RE_HP_T = re.compile(r"<hp:t(?:\s[^>]*)?>([^<]*)</hp:t>", re.DOTALL)
_RE_BRACE_PLACEHOLDER = re.compile(r"\{\{\s*([^}\s]+)\s*\}\}")
# Three or more underscores anywhere in the text node.
_RE_UNDERSCORE_RUN = re.compile(r"_{3,}")


@dataclass
class CheckResult:
    """Outcome of ``check_fill``.

    Attributes
    ----------
    template : str
        Template name as supplied to ``check_fill``.
    total_fields : int
        Number of fields known to the schema (or distinct placeholders
        detected when in pattern-fallback mode).
    filled : list[str]
        Field keys whose value in ``data`` is non-empty.
    empty : list[str]
        Field keys present in the schema but missing or empty in ``data``.
    placeholders : list[str]
        Residual ``{{key}}`` or underscore runs still present in the
        template's ``section0.xml`` — i.e. cells the caller hasn't filled.
    schema_used : bool
        ``True`` when schema-driven; ``False`` when pattern-fallback.
    """

    template: str
    total_fields: int = 0
    filled: List[str] = field(default_factory=list)
    empty: List[str] = field(default_factory=list)
    placeholders: List[str] = field(default_factory=list)
    schema_used: bool = False

    @property
    def is_complete(self) -> bool:
        """True iff no field is empty and no placeholder remains."""
        return not self.empty and not self.placeholders

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_complete"] = self.is_complete
        return d


def _extract_schema_keys(schema: dict) -> List[str]:
    """Pull every ``field.key`` from the schema's ``tables`` list."""
    keys: List[str] = []
    for tbl in schema.get("tables", []):
        for fld in tbl.get("fields", []):
            key = fld.get("key")
            if key:
                keys.append(key)
    return keys


def _scan_placeholders(section_xml: str) -> List[str]:
    """Return distinct placeholder markers still present in section XML.

    Scans only ``<hp:t>`` text nodes (not attribute values or other XML
    structure) so we don't false-positive on field IDs or comments.
    """
    found: list[str] = []
    seen: set[str] = set()
    for m in _RE_HP_T.finditer(section_xml):
        text = m.group(1)
        for bm in _RE_BRACE_PLACEHOLDER.finditer(text):
            marker = "{{" + bm.group(1) + "}}"
            if marker not in seen:
                seen.add(marker)
                found.append(marker)
        if _RE_UNDERSCORE_RUN.search(text):
            marker = "<underscores>"
            if marker not in seen:
                seen.add(marker)
                found.append(marker)
    return found


def _read_section_xml(hwpx_path: Path) -> Optional[str]:
    """Best-effort read of ``Contents/section0.xml`` from the HWPX zip."""
    try:
        from pyhwpxlib.package_ops import read_zip_archive
        archive = read_zip_archive(str(hwpx_path))
        raw = archive.files.get("Contents/section0.xml")
        if raw is None:
            return None
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


def check_fill(
    template_name: str,
    data: Union[dict, str, Path],
    *,
    schema_path: Optional[Union[str, Path]] = None,
    hwpx_path: Optional[Union[str, Path]] = None,
) -> CheckResult:
    """Verify whether ``data`` covers all fields of a registered template.

    Parameters
    ----------
    template_name : str
        Registered template name (resolved via XDG/skill workspace) or a
        direct path to a ``.hwpx`` file.
    data : dict | str | Path
        User data. ``dict`` directly, or a path to a JSON file.
    schema_path : str | Path, optional
        Override the auto-resolved schema location.
    hwpx_path : str | Path, optional
        Override the auto-resolved HWPX location (used for placeholder
        scanning when no schema is found).

    Returns
    -------
    CheckResult
        Field-coverage report. ``CheckResult.is_complete`` is the
        single boolean answer to "does the data fill this template?".

    Notes
    -----
    No rendering is performed — runs in ~10ms even for large templates.
    Use ``render_to_png`` only for the final visual confirmation step.
    """
    from pyhwpxlib.templates.resolver import (
        resolve_template_path,
        resolve_template_file,
    )

    # --- Normalise data input ----------------------------------------
    if isinstance(data, (str, Path)) and Path(data).exists():
        data = json.loads(Path(data).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("data must be a dict or a path to a JSON file")

    result = CheckResult(template=template_name)

    # --- Resolve schema ----------------------------------------------
    p = Path(template_name)
    if p.exists() and p.suffix == ".hwpx":
        if hwpx_path is None:
            hwpx_path = p
        if schema_path is None:
            ws_schema = p.parent / "schema.json"
            cand_legacy = p.with_suffix(".schema.json")
            if ws_schema.exists() and p.name == "source.hwpx":
                schema_path = ws_schema
            elif cand_legacy.exists():
                schema_path = cand_legacy
    else:
        if hwpx_path is None:
            hwpx_path = resolve_template_path(template_name, suffix=".hwpx")
        if schema_path is None:
            schema_path = resolve_template_file(template_name, "schema")

    if schema_path is not None and Path(schema_path).exists():
        # ----------------- Schema-driven path ------------------------
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        keys = _extract_schema_keys(schema)
        result.schema_used = True
        result.total_fields = len(keys)
        for k in keys:
            v = data.get(k)
            if v is None or (isinstance(v, str) and v.strip() == ""):
                result.empty.append(k)
            else:
                result.filled.append(k)
    else:
        # ----------------- Pattern-fallback path ---------------------
        # Without a schema we can't say which keys "should" be present, but
        # we can still flag any user-provided keys whose values are empty
        # and rely on placeholder scanning for the rest.
        result.schema_used = False
        for k, v in data.items():
            if v is None or (isinstance(v, str) and v.strip() == ""):
                result.empty.append(k)
            else:
                result.filled.append(k)
        result.total_fields = len(result.filled) + len(result.empty)

    # --- Placeholder scan (both paths) -------------------------------
    if hwpx_path is not None and Path(hwpx_path).exists():
        xml = _read_section_xml(Path(hwpx_path))
        if xml is not None:
            result.placeholders = _scan_placeholders(xml)

    return result


__all__ = ["CheckResult", "check_fill"]
