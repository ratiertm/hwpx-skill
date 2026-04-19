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


def write_zip_archive(path: str, archive: ZipArchive) -> None:
    """Write a ZIP archive back using the original ZipInfo metadata/order."""
    with zipfile.ZipFile(path, "w") as zf:
        for info in archive.infos:
            zf.writestr(info, archive.files[info.filename])


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
