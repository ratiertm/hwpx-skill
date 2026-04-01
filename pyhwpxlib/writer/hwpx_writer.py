"""HWPXWriter - Skeleton.hwpx template + full object model serialization.

Loads the pre-built Skeleton.hwpx template for structural files and
generates header.xml and section files from the object model.

Usage::

    from pyhwpxlib.writer.hwpx_writer import HWPXWriter

    HWPXWriter.to_filepath(hwpx_file, "output.hwpx")
    data = HWPXWriter.to_bytes(hwpx_file)
"""
from __future__ import annotations

import io
import pathlib
import zipfile
from functools import lru_cache
from typing import Dict

from pyhwpxlib.hwpx_file import HWPXFile
from pyhwpxlib.writer.content_hpf_writer import write_content_hpf
from pyhwpxlib.writer.header.header_writer import write_header
from pyhwpxlib.writer.section.section_writer import write_section
from pyhwpxlib.writer.xml_builder import XMLStringBuilder


@lru_cache(maxsize=None)
def _load_skeleton() -> Dict[str, bytes]:
    """Load all files from Skeleton.hwpx into memory (cached)."""
    skeleton_path = (
        pathlib.Path(__file__).resolve().parent.parent / "tools" / "Skeleton.hwpx"
    )
    if not skeleton_path.exists():
        raise FileNotFoundError(
            f"Skeleton.hwpx not found at {skeleton_path}. "
            "This file is required for HWPX generation."
        )
    files: Dict[str, bytes] = {}
    with zipfile.ZipFile(skeleton_path, "r") as zf:
        for info in zf.infolist():
            files[info.filename] = zf.read(info.filename)
    return files


class HWPXWriter:
    """Serialize an :class:`HWPXFile` to a ``.hwpx`` ZIP archive."""

    @staticmethod
    def to_filepath(hwpx_file: HWPXFile, filepath: str) -> None:
        data = HWPXWriter.to_bytes(hwpx_file)
        with open(filepath, "wb") as f:
            f.write(data)

    @staticmethod
    def to_stream(hwpx_file: HWPXFile, stream: io.BufferedIOBase) -> None:
        data = HWPXWriter.to_bytes(hwpx_file)
        stream.write(data)

    @staticmethod
    def to_bytes(hwpx_file: HWPXFile) -> bytes:
        skeleton = _load_skeleton()
        xsb = XMLStringBuilder()

        # Generate header.xml from object model
        overrides: Dict[str, bytes] = {}
        if hwpx_file.header_xml_file is not None:
            write_header(xsb, hwpx_file.header_xml_file)
            overrides["Contents/header.xml"] = xsb.to_string().encode("utf-8")

        # Generate content.hpf from object model
        if hwpx_file.content_hpf_file is not None:
            write_content_hpf(xsb, hwpx_file.content_hpf_file)
            overrides["Contents/content.hpf"] = xsb.to_string().encode("utf-8")

        # Generate section XML(s) from object model
        for i in range(hwpx_file.section_xml_file_list.count()):
            sec = hwpx_file.section_xml_file_list.get(i)
            write_section(xsb, sec)
            overrides[f"Contents/section{i}.xml"] = xsb.to_string().encode("utf-8")

        # Collect binary attachments (e.g. images) added via add_image()
        binary_attachments: Dict[str, bytes] = getattr(
            hwpx_file, "_binary_attachments", {}
        )

        # Assemble ZIP: skeleton files + overrides + binary attachments
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # mimetype must be first, uncompressed
            info = zipfile.ZipInfo("mimetype")
            info.compress_type = zipfile.ZIP_STORED
            zf.writestr(info, skeleton.get("mimetype", b"application/hwp+zip"))

            # Write all other files from skeleton, replacing overrides
            for name in sorted(skeleton):
                if name == "mimetype":
                    continue
                if name in overrides:
                    zf.writestr(name, overrides[name])
                else:
                    zf.writestr(name, skeleton[name])

            # Write binary attachments (images, etc.)
            for bin_path, bin_data in binary_attachments.items():
                zf.writestr(bin_path, bin_data)

        return buf.getvalue()
