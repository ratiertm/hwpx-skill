"""Example 10: Merge multiple HWPX documents into one."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyhwpxlib.api import create_document, add_paragraph, add_heading, save, merge_documents

# Create two separate documents
doc1 = create_document()
add_heading(doc1, "1부: 서론", level=1)
add_paragraph(doc1, "이 문서는 첫 번째 파트입니다.")
save(doc1, "part1.hwpx")

doc2 = create_document()
add_heading(doc2, "2부: 결론", level=1)
add_paragraph(doc2, "이 문서는 두 번째 파트입니다.")
save(doc2, "part2.hwpx")

# Merge into one
merge_documents(["part1.hwpx", "part2.hwpx"], "merged.hwpx")
print("Merged: merged.hwpx")

# Cleanup
os.unlink("part1.hwpx")
os.unlink("part2.hwpx")
