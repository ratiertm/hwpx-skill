"""Example 02: Styled text — bold, font size, color, heading."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyhwpxlib.api import create_document, add_paragraph, add_heading, add_styled_paragraph, save

doc = create_document()
add_heading(doc, "보고서 제목", level=1)
add_heading(doc, "1. 개요", level=2)
add_paragraph(doc, "이 문서는 pyhwpxlib로 생성되었습니다.")
add_styled_paragraph(doc, "볼드체 텍스트", bold=True)
add_styled_paragraph(doc, "큰 글자", font_size=20)
add_styled_paragraph(doc, "파란 글자", text_color="#0070C0")
save(doc, "styled.hwpx")
print("Created: styled.hwpx")
