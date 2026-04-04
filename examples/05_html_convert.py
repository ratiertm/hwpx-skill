"""Example 05: Convert HTML to HWPX."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyhwpxlib.api import create_document, save
from pyhwpxlib.html_to_hwpx import convert_html_to_hwpx

html = """
<h1>회의록</h1>
<p>일시: 2026-04-05 오전 10:00</p>
<p>참석자: <strong>김철수</strong>, 이영희, 박민준</p>
<h2>안건 1: 출시 일정</h2>
<ul>
  <li>베타 출시: 4월 말</li>
  <li>정식 출시: 5월 중순</li>
</ul>
<table>
  <tr><th>담당</th><th>업무</th><th>기한</th></tr>
  <tr><td>김철수</td><td>백엔드 API</td><td>4/20</td></tr>
  <tr><td>이영희</td><td>UI 개발</td><td>4/25</td></tr>
</table>
"""

doc = create_document()
convert_html_to_hwpx(doc, html)
save(doc, "from_html.hwpx")
print("Created: from_html.hwpx")
