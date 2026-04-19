"""Unit tests for pyhwpxlib.package_ops."""
from __future__ import annotations

import zipfile

from pyhwpxlib.package_ops import (
    read_zip_archive,
    write_zip_archive,
    iter_section_entries,
    update_entries,
)


def test_iter_section_entries_lists_only_sections(tmp_path):
    path = tmp_path / "sample.hwpx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/hwp+zip")
        zf.writestr("Contents/header.xml", "<head/>")
        zf.writestr("Contents/section1.xml", "<s1/>")
        zf.writestr("Contents/section0.xml", "<s0/>")

    assert iter_section_entries(str(path)) == [
        "Contents/section0.xml",
        "Contents/section1.xml",
    ]


def test_update_entries_and_write_preserve_other_files(tmp_path):
    src = tmp_path / "src.hwpx"
    out = tmp_path / "out.hwpx"
    with zipfile.ZipFile(src, "w") as zf:
        zf.writestr("mimetype", "application/hwp+zip")
        zf.writestr("Contents/section0.xml", "<hp:t>old</hp:t>")
        zf.writestr("BinData/image1.png", b"\x89PNG")

    archive = read_zip_archive(str(src))
    archive = update_entries(
        archive,
        ["Contents/section0.xml"],
        lambda _name, raw: raw.replace(b"old", b"new"),
    )
    write_zip_archive(str(out), archive)

    with zipfile.ZipFile(out) as zf:
        assert zf.read("Contents/section0.xml") == b"<hp:t>new</hp:t>"
        assert zf.read("BinData/image1.png") == b"\x89PNG"
