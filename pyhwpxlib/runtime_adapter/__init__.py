"""Runtime adapter for python-hwpx API compatibility.

Detects available methods at runtime and provides a stable interface
regardless of python-hwpx version (2.8.x, 2.9.x, etc.).
"""
from .capabilities import RuntimeCapabilities, detect_capabilities
from .table_adapter import TableAdapter

__all__ = ["RuntimeCapabilities", "detect_capabilities", "TableAdapter"]
