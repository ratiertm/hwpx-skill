"""Test configuration for pyhwpxlib."""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest


@pytest.fixture
def doc():
    """Return a fresh HWPX document."""
    from pyhwpxlib.api import create_document
    return create_document()


@pytest.fixture
def tmp_hwpx(tmp_path):
    """Return a path for a temporary HWPX file."""
    return str(tmp_path / "output.hwpx")


@pytest.fixture
def sample_form():
    """Return path to the sample 의견제출서 form."""
    path = PROJECT_ROOT / "templates" / "sources" / "sample_의견제출서.hwpx"
    if not path.exists():
        pytest.skip(f"Sample form not found: {path}")
    return str(path)
