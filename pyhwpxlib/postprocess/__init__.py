"""Post-processing utilities for HWPX files.

Includes lineseg handling for cross-renderer compatibility (rhwp etc.).
NOTE: lineseg fixes are NOT a Hancom security-warning workaround;
Hancom re-flows linesegs at open time regardless of stored values.
"""
from pyhwpxlib.postprocess.lineseg_reflow import (
    fix_r3_violations,
    reflow_section_xml,
    count_r3_violations,
    strip_linesegarrays,
    strip_linesegs_in_section_xmls,
)

__all__ = [
    "fix_r3_violations",
    "reflow_section_xml",
    "count_r3_violations",
    "strip_linesegarrays",
    "strip_linesegs_in_section_xmls",
]
