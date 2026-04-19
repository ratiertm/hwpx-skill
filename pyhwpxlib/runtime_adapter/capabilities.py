"""Runtime capability detection for python-hwpx."""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RuntimeCapabilities:
    """Detected capabilities of the current python-hwpx runtime."""
    table_set_in_margin: bool = False
    cell_set_margin: bool = False
    cell_set_size: bool = False
    hwpx_version: str = "unknown"


def detect_capabilities() -> RuntimeCapabilities:
    """Probe the installed python-hwpx to determine available methods.

    Returns a RuntimeCapabilities with flags for each detected feature.
    Logs a summary at DEBUG level.
    """
    caps = RuntimeCapabilities()

    try:
        import hwpx
        caps.hwpx_version = getattr(hwpx, '__version__', 'unknown')
    except ImportError:
        logger.debug("python-hwpx not installed")
        return caps

    try:
        from hwpx.oxml.table import HwpxOxmlTable
        caps.table_set_in_margin = hasattr(HwpxOxmlTable, 'set_in_margin')
    except ImportError:
        pass

    try:
        from hwpx.oxml.table import HwpxOxmlCell
        caps.cell_set_margin = hasattr(HwpxOxmlCell, 'set_margin')
        caps.cell_set_size = hasattr(HwpxOxmlCell, 'set_size')
    except ImportError:
        pass

    logger.debug(
        "python-hwpx %s capabilities: set_in_margin=%s, cell_set_margin=%s, cell_set_size=%s",
        caps.hwpx_version, caps.table_set_in_margin,
        caps.cell_set_margin, caps.cell_set_size,
    )
    return caps


# Module-level singleton — detected once at import time
_CAPS: RuntimeCapabilities | None = None


def get_capabilities() -> RuntimeCapabilities:
    """Get cached runtime capabilities (detected once)."""
    global _CAPS
    if _CAPS is None:
        _CAPS = detect_capabilities()
    return _CAPS
