"""pyhwpxlib — Python library for Korean HWPX/HWP document creation and editing.

No Hancom Office required. Works with Claude, ChatGPT, Gemini, and any LLM.

Quick Start::

    from pyhwpxlib import HwpxBuilder
    doc = HwpxBuilder(theme='forest')  # 10 built-in themes
    doc.add_heading("제목", level=1)
    doc.add_paragraph("본문 텍스트")
    doc.add_table([["항목", "값"], ["A", "1"]])
    doc.save("output.hwpx")

Themes: default, forest, warm_executive, ocean_analytics, coral_energy,
        charcoal_minimal, teal_trust, berry_cream, sage_calm, cherry_bold

For full LLM guide::

    python -m pyhwpxlib guide

CRITICAL RULES (violating these breaks Whale/Hancom rendering):
- Never put newlines inside text strings. Use separate add_paragraph() calls.
- Never use ET.tostring() to rewrite XML. Use string replacement only.
- HwpxBuilder handles secPr placement automatically. Do not add empty paragraphs before content.
"""
import logging

__version__ = "0.18.1"

logging.getLogger(__name__).addHandler(logging.NullHandler())

from pyhwpxlib.builder import HwpxBuilder, DS, TABLE_PRESETS
from pyhwpxlib.themes import Theme, BUILTIN_THEMES, extract_theme, save_theme, load_theme
from pyhwpxlib.api import insert_image_to_existing

__all__ = [
    "HwpxBuilder", "DS", "TABLE_PRESETS",
    "Theme", "BUILTIN_THEMES",
    "extract_theme", "save_theme", "load_theme",
    "insert_image_to_existing",
]
