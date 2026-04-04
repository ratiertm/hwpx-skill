"""Example 01: Hello World — create a minimal HWPX document."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyhwpxlib.api import create_document, add_paragraph, save

doc = create_document()
add_paragraph(doc, "Hello, World! 안녕하세요!")
save(doc, "hello.hwpx")
print("Created: hello.hwpx")
