"""Example 04: Convert Markdown to HWPX."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyhwpxlib.api import create_document, save
from pyhwpxlib.converter import convert_markdown_to_hwpx as convert_md_to_hwpx

markdown = """# 프로젝트 보고서

## 1. 개요

본 프로젝트는 **Python**으로 한글 문서를 자동 생성하는 라이브러리입니다.

## 2. 주요 기능

- HWPX 파일 생성/편집
- 마크다운 자동 변환
- 표, 이미지, 스타일 지원

## 3. 설치

```bash
pip install pyhwpxlib
```

| 기능 | 지원 여부 |
|------|---------|
| 텍스트 | ✅ |
| 표 | ✅ |
| 이미지 | ✅ |
"""

doc = create_document()
convert_md_to_hwpx(doc, markdown)
save(doc, "from_markdown.hwpx")
print("Created: from_markdown.hwpx")
