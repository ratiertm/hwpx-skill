"""Tests for BinData error handling in hwp2hwpx._attach_binary_data.

Requirement: TS-4 — corrupt BinData streams should be skipped with a
warning instead of crashing the entire HWP-to-HWPX conversion.
"""

import logging
import zlib

import pytest

from pyhwpxlib.hwp2hwpx import _attach_binary_data


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class MockOleStream:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


class MockOle:
    def __init__(self, streams: dict[str, bytes]):
        self._streams = streams

    def exists(self, name: str) -> bool:
        return name in self._streams

    def openstream(self, name: str) -> MockOleStream:
        return MockOleStream(self._streams[name])


class MockHWP:
    def __init__(self, bin_data_ids: dict, streams: dict, *, compressed: bool = True):
        self.bin_data_ids = bin_data_ids
        self.ole = MockOle(streams)
        self.compressed = compressed

    def _decompress(self, raw: bytes) -> bytes:
        if not self.compressed:
            return raw
        try:
            return zlib.decompress(raw, -15)
        except zlib.error:
            return zlib.decompress(raw)


class MockHWPX:
    _binary_attachments: dict = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_valid_zlib_data(payload: bytes = b"valid image data") -> bytes:
    """Create zlib-compressed data compatible with _decompress."""
    return zlib.compress(payload)


CORRUPT_DATA = b"NOT_VALID_ZLIB_DATA_AT_ALL"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAttachBinaryDataErrorHandling:
    """TS-4: _attach_binary_data must skip corrupt streams gracefully."""

    def test_mixed_good_and_corrupt_streams(self):
        """One good stream + one corrupt stream -> only good stream attached."""
        good_data = _make_valid_zlib_data(b"good image")
        hwp = MockHWP(
            bin_data_ids={1: "png", 2: "jpg"},
            streams={
                "BinData/BIN0001.png": good_data,
                "BinData/BIN0002.jpg": CORRUPT_DATA,
            },
        )
        hwpx = MockHWPX()

        _attach_binary_data(hwpx, hwp)

        assert "BinData/BIN0001.png" in hwpx._binary_attachments
        assert hwpx._binary_attachments["BinData/BIN0001.png"] == b"good image"
        assert "BinData/BIN0002.jpg" not in hwpx._binary_attachments

    def test_all_corrupt_streams(self):
        """All corrupt streams -> empty attachments, no exception."""
        hwp = MockHWP(
            bin_data_ids={1: "png", 2: "jpg"},
            streams={
                "BinData/BIN0001.png": CORRUPT_DATA,
                "BinData/BIN0002.jpg": CORRUPT_DATA,
            },
        )
        hwpx = MockHWPX()

        _attach_binary_data(hwpx, hwp)

        assert hwpx._binary_attachments == {}

    def test_logs_warning_for_skipped_streams(self, caplog):
        """Warning is logged for each corrupt stream."""
        hwp = MockHWP(
            bin_data_ids={1: "png", 2: "jpg"},
            streams={
                "BinData/BIN0001.png": CORRUPT_DATA,
                "BinData/BIN0002.jpg": CORRUPT_DATA,
            },
        )
        hwpx = MockHWPX()

        with caplog.at_level(logging.WARNING):
            _attach_binary_data(hwpx, hwp)

        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_messages) == 2
        assert any("BIN0001" in msg for msg in warning_messages)
        assert any("BIN0002" in msg for msg in warning_messages)
        assert all("Failed to decompress BinData" in msg for msg in warning_messages)

    def test_all_good_streams_no_regression(self):
        """All good streams -> all attached normally (no regression)."""
        good1 = _make_valid_zlib_data(b"image1")
        good2 = _make_valid_zlib_data(b"image2")
        hwp = MockHWP(
            bin_data_ids={1: "png", 2: "jpg"},
            streams={
                "BinData/BIN0001.png": good1,
                "BinData/BIN0002.jpg": good2,
            },
        )
        hwpx = MockHWPX()

        _attach_binary_data(hwpx, hwp)

        assert len(hwpx._binary_attachments) == 2
        assert hwpx._binary_attachments["BinData/BIN0001.png"] == b"image1"
        assert hwpx._binary_attachments["BinData/BIN0002.jpg"] == b"image2"

    def test_no_empty_bytes_for_failed_streams(self):
        """Failed streams must NOT produce empty bytes entry."""
        hwp = MockHWP(
            bin_data_ids={1: "png"},
            streams={"BinData/BIN0001.png": CORRUPT_DATA},
        )
        hwpx = MockHWPX()

        _attach_binary_data(hwpx, hwp)

        # Must not have the key at all (not even with b"")
        assert "BinData/BIN0001.png" not in hwpx._binary_attachments
        for v in hwpx._binary_attachments.values():
            assert v != b""
