"""Common ZIP package helpers for HWPX read/modify/write workflows.

Centralizes archive I/O so callers don't each reimplement:
- read all entries
- iterate section XML files
- rewrite archives while preserving ZipInfo metadata
"""
from __future__ import annotations

from dataclasses import dataclass
import zipfile
from typing import Callable, Iterable


@dataclass(frozen=True)
class ZipArchive:
    infos: list[zipfile.ZipInfo]
    files: dict[str, bytes]


def read_zip_archive(path: str) -> ZipArchive:
    """Read all entries from a ZIP archive, preserving ZipInfo metadata."""
    with zipfile.ZipFile(path, "r") as zf:
        infos = list(zf.infolist())
        files = {info.filename: zf.read(info.filename) for info in infos}
    return ZipArchive(infos=infos, files=files)


def write_zip_archive(
    path: str,
    archive: ZipArchive,
    strip_linesegs: "bool | str" = False,
) -> int:
    """Write a ZIP archive back using the original ZipInfo metadata/order.

    Returns the count of lineseg structures fixed (0 when ``strip_linesegs``
    is False/None — no fix attempted; otherwise the actual mutation count).

    The ``strip_linesegs`` argument controls Hancom's "외부 수정" security
    warning avoidance. The real trigger (verified 2026-04-27 via binary
    search across edit variants of an externally-modified hwpx) is::

        any <hp:lineseg textpos="N"/> where N > UTF-16 length of paragraph text

    Hancom interprets such a "lineseg pointing past the end of the text" as
    evidence the text was shortened by an external tool without refreshing
    the lineseg cache.

    Modes:

    * ``False`` (default, **as of v0.14.0**) — no post-processing. The
      archive is written byte-for-byte, preserving any non-standard lineseg
      values. This is the rhwp-aligned default: pyhwpxlib does not silently
      hide non-standard structures from external renderers / validators.
      Callers that want the precise security-trigger fix must opt in via
      ``strip_linesegs="precise"``.
    * ``"precise"`` — remove only the linesegs whose ``textpos`` overflows
      the paragraph's text. Keeps every other lineseg intact, so external
      renderers (rhwp, custom previewers) keep their layout cache.
    * ``"remove"`` — remove every ``<hp:linesegarray>`` block. Safer fallback
      if a future Hancom version uses a wider trigger; lossless because
      Hancom/rhwp both re-flow on load, but external renderers must reflow.
    * ``True`` — alias for ``"precise"`` (back-compat with v0.13.0/0.13.1).

    Migration note (v0.13.x → v0.14.0): if your code relied on the silent
    precise fix to avoid Hancom's security warning, pass
    ``strip_linesegs="precise"`` explicitly. See ``pyhwpxlib doctor`` for an
    interactive way to detect and fix non-standard lineseg in existing files.
    """
    if strip_linesegs is True:
        strip_linesegs = "precise"
    files = archive.files
    fixed_count = 0
    if strip_linesegs == "precise":
        from pyhwpxlib.postprocess import fix_textpos_overflow_in_section_xmls
        files, fix_total = fix_textpos_overflow_in_section_xmls(files)
        fixed_count = fix_total
    elif strip_linesegs == "remove":
        from pyhwpxlib.postprocess import strip_linesegs_in_section_xmls
        files, _ = strip_linesegs_in_section_xmls(files, mode="remove")
        # remove mode reports stripped block count, not individual fixes;
        # report 0 here to keep the precise/remove return semantics distinct.
        fixed_count = 0
    elif strip_linesegs is False or strip_linesegs is None:
        pass
    else:
        raise ValueError(
            f"strip_linesegs must be 'precise', 'remove', True, or False; got {strip_linesegs!r}"
        )
    with zipfile.ZipFile(path, "w") as zf:
        for info in archive.infos:
            zf.writestr(info, files[info.filename])
    return fixed_count


def iter_section_entries(path: str) -> list[str]:
    """List section XML entry names in a HWPX ZIP, sorted."""
    archive = read_zip_archive(path)
    return sorted(
        name for name in archive.files
        if name.startswith("Contents/section") and name.endswith(".xml")
    )


def update_entries(
    archive: ZipArchive,
    names: Iterable[str],
    updater: Callable[[str, bytes], bytes],
) -> ZipArchive:
    """Return a new archive with selected entries transformed by *updater*."""
    files = dict(archive.files)
    for name in names:
        files[name] = updater(name, files[name])
    return ZipArchive(infos=archive.infos, files=files)
