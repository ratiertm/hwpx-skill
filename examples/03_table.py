"""Example 03: Table — create a table with headers and data rows."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyhwpxlib.api import create_document, add_styled_paragraph, add_table, save

doc = create_document()
add_styled_paragraph(doc, "월별 매출 현황", bold=True, font_size=14)

data = [
    ["월",  "매출액(만원)", "전월비(%)"],
    ["1월", "1,250",      "+5.2"],
    ["2월", "1,380",      "+10.4"],
    ["3월", "1,420",      "+2.9"],
]
add_table(doc, rows=4, cols=3, data=data, width=42520)

save(doc, "table.hwpx")
print("Created: table.hwpx")
