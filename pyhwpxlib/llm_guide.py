"""LLM Quick Reference Guide for pyhwpxlib.

Usage: python -m pyhwpxlib guide
"""

GUIDE = r"""
# pyhwpxlib v0.10.0 — LLM Quick Reference Guide

## Installation
```
pip install pyhwpxlib
```

## 1. Create a New Document
```python
from pyhwpxlib import HwpxBuilder

doc = HwpxBuilder(theme='forest')  # Choose from 10 themes
doc.add_heading("Title", level=1)
doc.add_paragraph("")  # spacing after heading (REQUIRED)
doc.add_paragraph("Body text.")
doc.add_paragraph("")  # spacing before table
doc.add_table([["Col A", "Col B"], ["1", "2"]])
doc.add_paragraph("")  # spacing after table

# Images — ALWAYS add empty paragraphs before/after (prevents overlap)
doc.add_paragraph("")
doc.add_image("photo.png", width=42520, height=23918)  # full A4 width, 16:9
doc.add_paragraph("")
doc.add_image_from_url("https://example.com/img.png",
    filename="img.png", width=42520, height=23918)
doc.add_paragraph("")

doc.save("output.hwpx")
```

### Image Size Rule
Default width is ALWAYS **42520** (full A4 width). Calculate height to preserve ratio:
```python
from PIL import Image
img = Image.open("photo.png")
w, h = img.size
width = 42520  # ALWAYS use full width for photos/charts
height = int(42520 * h / w)  # preserve aspect ratio
doc.add_image("photo.png", width=width, height=height)
```
Only use smaller width (8000-12000) for logos/icons.

## 2. Available Themes (10)
| Theme | Color | Best For |
|-------|-------|----------|
| default | Blue #395da2 | Corporate, government |
| forest | Green #2C5F2D | Environment, ESG |
| warm_executive | Brown #B85042 | Proposals, branding |
| ocean_analytics | Teal #065A82 | Data, research |
| coral_energy | Coral #F96167 | Marketing |
| charcoal_minimal | Gray #36454F | Minimal, technical |
| teal_trust | Teal #028090 | Medical, finance |
| berry_cream | Wine #6D2E46 | Education, culture |
| sage_calm | Sage #84B59F | Wellness |
| cherry_bold | Red #990011 | Warning, strong claims |

## 3. Extract & Reuse Theme from Existing Document
```python
from pyhwpxlib import extract_theme, save_theme, HwpxBuilder

theme = extract_theme("reference.hwpx", name="my_style")
save_theme(theme)  # ~/.pyhwpxlib/themes/my_style.json
doc = HwpxBuilder(theme='custom/my_style')
```

## 4. HwpxBuilder API
| Method | Purpose |
|--------|---------|
| add_heading(text, level=1) | Heading (1-4) |
| add_paragraph(text, bold, italic, font_size, text_color, alignment) | Paragraph |
| add_paragraph("") | **Spacing between elements (REQUIRED)** |
| add_table(data, header_bg, cell_colors, col_widths, row_heights) | Table |
| add_bullet_list(items) | Bullet list |
| add_numbered_list(items) | Numbered list |
| add_image(path, width, height) | Local image |
| add_image_from_url(url, filename, width, height) | Download + insert image |
| add_page_break() | Page break |
| add_line() | Horizontal line |
| add_header(text) / add_footer(text) | Header / Footer |
| add_page_number() | Page number |
| save(path) | Save to .hwpx |

## 5. Read Existing Documents
```python
from pyhwpxlib.api import extract_text
text = extract_text("document.hwpx")

# Structured extraction (text + tables + images)
from pyhwpxlib.json_io.overlay import extract_overlay
overlay = extract_overlay("document.hwpx")
# overlay['texts'], overlay['tables'], overlay['images']
```

## 6. Convert HWP to HWPX
```python
from pyhwpxlib.hwp2hwpx import convert
convert("old.hwp", "new.hwpx")
```

## 7. Edit Existing Documents (Overlay)
```python
from pyhwpxlib.json_io.overlay import extract_overlay, apply_overlay

overlay = extract_overlay("template.hwpx")
for t in overlay['texts']:
    t['value'] = t['value'].replace('old_text', 'new_text')
apply_overlay("template.hwpx", overlay, "output.hwpx")
```

## 8. Fill Form Templates
```python
from pyhwpxlib.api import fill_template_checkbox

fill_template_checkbox("form.hwpx",
    data={"old_label": "new_value"},
    checks=["agree"],
    output_path="filled.hwpx")
```

## 9. Image Operations
```python
# Insert image into EXISTING document
from pyhwpxlib.api import insert_image_to_existing
insert_image_to_existing("doc.hwpx", "photo.png", "output.hwpx",
    width=21260, height=15000, position='end')

# Replace image in existing document
import base64
from pyhwpxlib.json_io.overlay import extract_overlay, apply_overlay
overlay = extract_overlay("doc.hwpx")
for img in overlay['images']:
    with open("new.png", "rb") as f:
        img['new_data_b64'] = base64.b64encode(f.read()).decode()
apply_overlay("doc.hwpx", overlay, "output.hwpx")
```

## 10. Validate, Lint, Font Check
```bash
python -m pyhwpxlib validate output.hwpx        # Structure check
python -m pyhwpxlib lint output.hwpx             # Rendering risk check
python -m pyhwpxlib font-check output.hwpx       # Font resolution check
python -m pyhwpxlib themes list                  # List all themes

# JSON output for automation
python -m pyhwpxlib validate output.hwpx --json
python -m pyhwpxlib lint output.hwpx --json
```

## 11. Korean Official Documents (공문/기안문) — v0.10.0+

Auto-generates 공문 compliant with 행정안전부 「2025 행정업무운영 편람」.

```python
from pyhwpxlib.gongmun import Gongmun, GongmunBuilder, signer, validate_file

doc = Gongmun(
    기관명="행정안전부",
    수신="수신자 참조",              # or "내부결재"
    제목="2024년 정보공개 종합평가 계획 안내",
    본문=[
        "「공공기관의 정보공개에 관한 법률」 ...",
        ("계약 개요", [                    # nested: level-2 가./나./다.
            "계약명: ...",
            "계약 금액: ...",
        ]),
    ],
    붙임=["계획서 1부."],                # auto "끝." marker
    발신명의="행정안전부장관",
    기안자=signer("행정사무관", "김OO"),
    결재권자=signer("과장", "박OO", 전결=True, 서명일자="2025. 9. 30."),
    시행_처리과명="정보공개과", 시행_일련번호="000", 시행일="2025. 9. 30.",
    우편번호="30112", 도로명주소="세종특별자치시 도움6로 42",
    전화="(044)205-0000", 공개구분="대국민공개",
)
GongmunBuilder(doc).save("output.hwpx")      # 공문 표준 여백 자동 적용
                                              # (상30/하15/좌우20/머꼬10 mm)

# 규정 검증 (10종 체크)
from pyhwpxlib.gongmun import format_report
print(format_report(validate_file("output.hwpx")))
# ERROR: DATE_FORMAT, DISCRIMINATORY_TERM, DUEUM_ERROR
# WARNING: AUTHORITATIVE_TONE, LOANWORD_ERROR, END_MARKER_MISSING
# INFO: HANGUL_COMPAT_CHAR, ENGLISH_ABBREV
```

**Auto-applied (편람 준수)**:
- 날짜 `2025. 9. 20.` / 금액 `금113,560원(금일십일만삼천오백육십원)`
- 항목기호 8단계 `1.→가.→1)→가)→(1)→(가)→①→㉮` + 2타 들여쓰기
- 끝표시 `VV끝.` / '기안자·결재권자' 용어 생략 / 회색 구분선
- 내부결재 시 **발신명의 자동 생략** (영 §13③)

**Options**:
- `GongmunBuilder(doc, compact=True)` — 1페이지 맞춤 (§4 p68 "1건 1매")
- `GongmunBuilder(doc, margins_mm=(30,15,20,20,10,10))` — 여백 커스텀
- `GongmunSimple(...)` — 간이기안문 (내부결재 전용, 시행문 변환 불가)

**Rules file**: `pyhwpxlib/gongmun/rules.yaml` (270줄, 편람 기계판독 YAML)

## 12. Preview (SVG)
```python
from pyhwpxlib.rhwp_bridge import RhwpEngine  # requires pip install pyhwpxlib[preview]
engine = RhwpEngine()
doc = engine.load("output.hwpx")
svg = doc.render_page_svg(0, embed_fonts=True)
```

## CRITICAL RULES

1. **No \n in text** — Use separate add_paragraph() calls
2. **No ET.tostring()** — Breaks namespace prefixes. Use string replacement
3. **Spacing required** — add_paragraph("") before/after headings, tables, images
4. **Tables only when needed** — Don't force tables into narrative content
5. **Always validate + lint** after creation
6. **Use themes** — Never hardcode blue (#395da2) for everything

## Common Mistakes by LLMs

- Creating XML directly → Use HwpxBuilder
- \n in text → Whale error
- No spacing between elements → Text sticks together
- Tables everywhere → Only use when data/comparison exists
- `from hwpx import ...` → Wrong. Use `from pyhwpxlib import ...`
- Ignoring validate/lint → Broken files delivered to user
- 공문 생성 시 '기안자:' 등 용어 붙임 → 편람 p71 위반, GongmunBuilder 사용
- 공문 날짜 `2025.9.20` (공백 없음) → GongmunBuilder의 format_date() 사용
"""


def print_guide():
    print(GUIDE)
