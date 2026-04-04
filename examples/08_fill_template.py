"""Example 08: Fill a template with data (양식 데이터 채우기)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyhwpxlib.api import create_document, add_paragraph, add_styled_paragraph, save, fill_template

# Step 1: create a template with {{placeholders}}
doc = create_document()
add_styled_paragraph(doc, "수신: {{수신처}}", bold=True)
add_paragraph(doc, "발신: {{발신처}}")
add_paragraph(doc, "제목: {{제목}}")
add_paragraph(doc, "")
add_paragraph(doc, "{{본문}}")
add_paragraph(doc, "")
add_paragraph(doc, "날짜: {{날짜}}")
save(doc, "template.hwpx")
print("Template created: template.hwpx")

# Step 2: fill with actual data
data = {
    "수신처": "홍길동 귀중",
    "발신처": "김철수 (주)테스트",
    "제목": "납품 확인서",
    "본문": "아래와 같이 납품이 완료되었음을 확인합니다.",
    "날짜": "2026년 4월 5일",
}
fill_template("template.hwpx", data, "filled.hwpx")
print("Filled: filled.hwpx")
