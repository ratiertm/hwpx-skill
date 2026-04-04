"""Example 06: Clone a government form (서식 복제) using form_pipeline."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "templates"))
from form_pipeline import extract_form, generate_form

# Clone a government form — preserves exact structure, table sizes, styles
source = os.path.join(os.path.dirname(__file__), "..", "templates", "sources", "sample_의견제출서.hwpx")
if os.path.exists(source):
    form_data = extract_form(source)
    output = generate_form(form_data, "cloned_의견제출서.hwpx")
    print(f"Cloned: {output}")
else:
    print("Source form not found — adjust the path to a .hwpx form file")
