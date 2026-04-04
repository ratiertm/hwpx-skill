"""Example 07: Read an existing HWPX file and extract content."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyhwpxlib.api import extract_text, extract_markdown, extract_html

sample = os.path.join(os.path.dirname(__file__), "..", "docs", "sample_의견제출서.hwpx")
if not os.path.exists(sample):
    print("Sample file not found — set 'sample' to any .hwpx file path")
    sys.exit(0)

# Extract as plain text
text = extract_text(sample)
print("=== Plain Text ===")
print(text[:300])

# Extract as Markdown
md = extract_markdown(sample)
print("\n=== Markdown ===")
print(md[:300])

# Extract as HTML (saved to file)
from pyhwpxlib.html_converter import convert_hwpx_to_html
convert_hwpx_to_html(sample, output_path="extracted.html")
print("\nHTML saved to: extracted.html")
