"""Test configuration for pyhwpxlib."""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest


def pytest_collection_modifyitems(config, items):
    """Classify tests into smoke/integration/regression/slow buckets.

    This keeps CI entrypoints stable even as files move around.
    """
    regression_files = {
        "test_form_pipeline.py",
        "test_form_pipeline_multirun.py",
        "test_form_fill_golden.py",
        "test_hwp2hwpx_golden.py",
        "test_visual_golden.py",
        "test_stability.py",
    }
    slow_files = {
        "test_form_pipeline.py",
        "test_form_pipeline_multirun.py",
        "test_form_fill_golden.py",
        "test_hwp2hwpx_golden.py",
        "test_visual_golden.py",
        "test_hwp2hwpx_nested_table.py",
        "test_html_converters.py",
        "test_stability.py",
    }
    smoke_files = {
        "test_api_core.py",
        "test_api_shapes.py",
        "test_form_pipeline.py",
        "test_merge_documents.py",
        "test_xml_ops.py",
        "test_overlay.py",
        "test_api_server.py",
    }

    for item in items:
        path = Path(str(item.fspath))
        name = path.name
        parts = set(path.parts)

        if "integration" in parts:
            item.add_marker(pytest.mark.integration)
        if "regression" in parts or name in regression_files:
            item.add_marker(pytest.mark.regression)
        if name in slow_files:
            item.add_marker(pytest.mark.slow)
        if name in smoke_files and "slow" not in item.keywords:
            item.add_marker(pytest.mark.smoke)


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
