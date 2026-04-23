# pyhwpxlib Full API Reference

## Table of Contents

1. [pyhwpxlib Function Reference](#pyhwpxlib-function-reference)
   - Lists (Bullet / Numbered)
   - Nested Lists
   - Indentation (ensure_para_style)
   - 공문서 들여쓰기 체계
   - Headers / Footers / Page Numbers
   - Footnotes
   - Equations
   - Hyperlinks
   - Highlights / Bookmarks
   - Shapes (Rectangle / Ellipse / Line)
   - Multi-Column Layout
   - Document Merge
   - Text Extraction
2. [Images — pyhwpxlib Direct Usage](#images--pyhwpxlib-direct-usage)
3. [Page Breaks](#page-breaks)
4. [Converting to Images](#converting-to-images)
5. [XML Reference](#xml-reference)
   - Document Structure
   - Namespaces
   - Paragraph / Multi-run
   - Table
   - charPr / paraPr
6. [Page Size (OWPML Units)](#page-size-owpml-units)
7. [Size Conversion Table](#size-conversion-table)
8. [Font Size Height Table](#font-size-height-table)

---

## pyhwpxlib Function Reference

HwpxBuilder는 내부적으로 pyhwpxlib API를 호출합니다.
HwpxBuilder에 없는 기능은 pyhwpxlib를 직접 사용합니다.

```python
from pyhwpxlib.api import (
    create_document, save, add_paragraph, add_styled_paragraph,
    add_heading, add_table, add_image,
    add_bullet_list, add_numbered_list,
    add_nested_bullet_list, add_nested_numbered_list,
    add_header, add_footer, add_page_number,
    add_footnote, add_equation, add_hyperlink, add_highlight, add_bookmark,
    add_rectangle, add_ellipse, add_line,
    set_columns, extract_text, merge_documents,
    fill_template, fill_template_checkbox, fill_template_batch,
    convert_html_file_to_hwpx, convert_hwpx_to_html,
)
from pyhwpxlib.style_manager import ensure_para_style, ensure_char_style, font_size_to_height
```

### Lists (글머리 기호 / 번호 목록)

**글머리 기호 목록** — `add_bullet_list(doc, items, bullet_char)`:
```python
doc = create_document()
add_bullet_list(doc, ["첫 번째", "두 번째", "세 번째"])
# bullet_char: 기본 '●', 변경 가능 ('◦','▪','‣' 등)
# 주의: 유니코드 bullet(•,▪) 직접 텍스트로 쓰면 안 됨 → 반드시 이 API 사용
```

**번호 목록** — `add_numbered_list(doc, items, format_string)`:
```python
add_numbered_list(doc, ["항목 1", "항목 2", "항목 3"])
# format_string: 기본 "^1." → "1. 2. 3."
# "^1)" → "1) 2) 3)"
# "(^1)" → "(1) (2) (3)"
```

**중첩 글머리 목록** — `add_nested_bullet_list(doc, items)`:
```python
add_nested_bullet_list(doc, [
    (0, "1단계 항목"),
    (1, "2단계 하위"),
    (2, "3단계 세부"),
    (0, "다시 1단계"),
])
# level 0~6, 들여쓰기 자동 적용
```

**중첩 번호 목록** — `add_nested_numbered_list(doc, items)`:
```python
add_nested_numbered_list(doc, [
    (0, "1. 대항목"),
    (1, "1.1 중항목"),
    (1, "1.2 중항목"),
    (0, "2. 대항목"),
    (1, "2.1 중항목"),
])
```

**주의**: 유니코드 bullet 문자(•, ▪) 직접 사용 금지. 반드시 `add_bullet_list` API 사용.

### Standalone List Examples (pyhwpxlib direct)

```python
# 글머리 기호 목록
from pyhwpxlib.api import add_bullet_list
add_bullet_list(doc, ["첫 번째 항목", "두 번째 항목", "세 번째 항목"])

# 번호 목록
from pyhwpxlib.api import add_numbered_list
add_numbered_list(doc, ["항목 1", "항목 2", "항목 3"])

# 중첩 목록 (level 0~6)
from pyhwpxlib.api import add_nested_bullet_list, add_nested_numbered_list

add_nested_bullet_list(doc, [
    (0, "1단계 항목"),
    (1, "2단계 항목"),
    (2, "3단계 항목"),
    (0, "다시 1단계"),
])

add_nested_numbered_list(doc, [
    (0, "1. 항목"),
    (1, "1.1 하위"),
    (1, "1.2 하위"),
    (0, "2. 항목"),
])
```

### Indentation — `ensure_para_style` + `add_paragraph`

```python
# 들여쓰기된 단락 생성
para_id = ensure_para_style(doc, indent=-2800, margin_left=2800)
add_paragraph(doc, "들여쓰기된 텍스트", para_pr_id_ref=para_id)

# ensure_para_style 파라미터:
#   align: 'JUSTIFY'|'CENTER'|'LEFT'|'RIGHT'
#   line_spacing_value: 160 (%)
#   indent: 음수=내어쓰기 (첫 줄 왼쪽으로)
#   margin_left: 전체 단락 왼쪽 여백
```

**공문서 들여쓰기 체계**:
```python
# 조: 제1조(목적)
p1 = ensure_para_style(doc, indent=-2800, margin_left=2800)
add_paragraph(doc, "제1조(목적) 이 규정은...", para_pr_id_ref=p1)

# 호: 1. 항목
p2 = ensure_para_style(doc, indent=-4880, margin_left=4880)
add_paragraph(doc, "1. 항목 내용", para_pr_id_ref=p2)

# 목: 가. 세부
p3 = ensure_para_style(doc, indent=-7680, margin_left=7680)
add_paragraph(doc, "가. 세부 항목", para_pr_id_ref=p3)
```

### Headers / Footers / Page Numbers

```python
add_header(doc, "문서 제목 — 대외비")
add_footer(doc, "© 2026 회사명")
add_page_number(doc)
# pos: 'BOTTOM_CENTER'(기본), 'BOTTOM_RIGHT', 'TOP_CENTER', 'TOP_RIGHT'
# format_type: 'DIGIT'(기본), 'CIRCLE', 'HANGUL'
```

### Footnotes

```python
add_footnote(doc, "출처: 삼성전자 2024년 사업보고서", number=1)
```

### Equations

```python
add_equation(doc, "x = {-b +- sqrt {b^2 - 4ac}} over {2a}")
```

### Hyperlinks

```python
add_hyperlink(doc, "네이버", "https://www.naver.com")
# Whale에서 fieldBegin/fieldEnd 에러 발생 가능 — 필요시만 사용
```

**주의**: Whale에서 fieldBegin/fieldEnd 렌더링 에러 발생 가능 (룰북 규칙 28).
HTML→HWPX 변환 시 `strip_links=True`로 링크 자동 제거 권장.

### Highlights / Bookmarks

```python
add_highlight(doc, "강조 텍스트", color="#FFFF00")
add_bookmark(doc, "section_1")
```

### Shapes

```python
add_rectangle(doc, width=14000, height=7000, line_color="#395da2", line_width=283)
add_ellipse(doc, width=10000, height=8000)
add_line(doc, x1=0, y1=0, x2=42520, y2=0, line_color="#abb3b7", line_width=71)
```

### Multi-Column Layout

```python
set_columns(doc, col_count=2, same_gap=1200, separator_type="SOLID")
```

Standalone example:
```python
from pyhwpxlib.api import set_columns

# 2단 레이아웃
set_columns(doc, count=2, spacing=1134)
```

### Document Merge

```python
merge_documents(["doc1.hwpx", "doc2.hwpx"], "merged.hwpx")
```

### Text Extraction

```python
text = extract_text("document.hwpx")
```

---

## Images — pyhwpxlib Direct Usage

**pyhwpxlib 직접 사용**:
```python
from pyhwpxlib.api import add_image
add_image(doc, "photo.png", width=20000, height=15000)
```

**크기 변환**:
```
mm → HWPUNIT: mm * 283.46
inch → HWPUNIT: inch * 7200
px (96dpi) → HWPUNIT: px * 75
```

**이미지 크기 가이드**:

| 용도 | width | height | 비고 |
|------|-------|--------|------|
| 전체 너비 | 42520 | 비율 자동 | 본문 영역 전체 |
| 반 너비 | 21260 | 비율 자동 | 2단 배치용 |
| 1/3 너비 | 14173 | 비율 자동 | 3단 배치용 |
| 증명사진 | 8504 | 11339 | 3×4cm |
| 썸네일 | 7087 | 7087 | 25×25mm |

**문서 생성 시 이미지 활용 패턴**:
```python
doc = HwpxBuilder(table_preset='corporate')
doc.add_heading("보고서 제목", level=1, alignment='CENTER')
doc.add_paragraph("")

# 관련 이미지 삽입 (웹에서 다운로드)
doc.add_image_from_url("https://...", width=42520)  # 전체 너비
doc.add_paragraph("[ 그림 1 ] 이미지 캡션", font_size=9,
                   text_color='#586064', alignment='CENTER')
doc.add_paragraph("")

doc.add_heading("1. 본문", level=2)
doc.add_paragraph("내용...")
doc.save("output.hwpx")
```

---

## Page Breaks

```python
# 방법 1: 빈 단락 반복 (간단하지만 부정확)
for _ in range(30):
    doc.add_paragraph("")

# 방법 2: pageBreak 속성 (정확)
# XML 직접 수정 시:
# <hp:p pageBreak="1" ...>
```

**unpack → edit → pack 방식**:
```python
# section0.xml에서 페이지 나누기 삽입
xml = xml.replace(
    '>다음 페이지 시작 텍스트<',
    ' pageBreak="1">다음 페이지 시작 텍스트<'
)
```

---

## Converting to Images

```bash
# HWPX → PDF (한컴오피스 필요)
# → PDF → 이미지 (pdftoppm)
# 현재 자동화 미지원 — 한컴오피스 수동 변환 또는 LibreOffice 사용

# LibreOffice로 PDF 변환 (실험적)
# libreoffice --headless --convert-to pdf document.hwpx
```

---

## XML Reference

### Document Structure
```
document.hwpx (ZIP)
├── mimetype                    ← "application/hwp+zip" (STORED, 첫 번째)
├── version.xml
├── Contents/
│   ├── content.hpf             ← 매니페스트
│   ├── header.xml              ← 스타일 (fontfaces, charPr, paraPr, borderFill)
│   └── section0.xml            ← 본문 (paragraphs, tables)
├── META-INF/
│   ├── container.xml
│   ├── container.rdf
│   └── manifest.xml
├── Preview/
│   ├── PrvText.txt
│   └── PrvImage.png
└── settings.xml
```

### Namespaces
| Prefix | URI |
|--------|-----|
| hp | http://www.hancom.co.kr/hwpml/2011/paragraph |
| hs | http://www.hancom.co.kr/hwpml/2011/section |
| hh | http://www.hancom.co.kr/hwpml/2011/head |
| hc | http://www.hancom.co.kr/hwpml/2011/core |

### Paragraph
```xml
<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="0"><hp:t>텍스트</hp:t></hp:run>
</hp:p>
```

### Multi-run (run별 다른 스타일)
```xml
<hp:p id="0" paraPrIDRef="0" styleIDRef="1">
  <hp:run charPrIDRef="5"><hp:t>볼드</hp:t></hp:run>
  <hp:run charPrIDRef="3"><hp:t> 일반</hp:t></hp:run>
</hp:p>
```

### Table
```xml
<hp:tbl rowCnt="2" colCnt="3" cellSpacing="0" borderFillIDRef="1">
  <hp:tr>
    <hp:tc borderFillIDRef="1">
      <hp:cellAddr colAddr="0" rowAddr="0" />
      <hp:cellSpan colSpan="1" rowSpan="1" />
      <hp:cellSz width="14173" height="1200" />
      <hp:subList vertAlign="CENTER">
        <hp:p><hp:run charPrIDRef="0"><hp:t>셀</hp:t></hp:run></hp:p>
      </hp:subList>
    </hp:tc>
  </hp:tr>
</hp:tbl>
```

### charPr (header.xml)
```xml
<hh:charPr id="0" height="1000" textColor="#000000">
  <hh:fontRef hangul="0" latin="0" />
  <hh:bold />
</hh:charPr>
```
height: 1000=10pt, 1600=16pt, 2000=20pt

### paraPr (header.xml)
```xml
<hh:paraPr id="0" condense="25">
  <hh:align horizontal="JUSTIFY" />
  <hh:lineSpacing type="PERCENT" value="160" />
  <hh:margin><hc:intent value="-2800" /></hh:margin>
</hh:paraPr>
```

---

## Page Size (OWPML Units: 1/7200 inch)

| 용지 | width | height |
|------|-------|--------|
| A4 | 59,528 | 84,188 |
| B5 | 51,592 | 72,848 |
| Letter | 61,200 | 79,200 |

---

## Size Conversion Table

| 실제 크기 | HWPUNIT | 용도 |
|----------|---------|------|
| 5mm | 1417 | 최소 셀 패딩 |
| 10mm | 2835 | 일반 셀 높이 |
| 15mm | 4252 | 헤더 셀 높이 |
| 30mm | 8504 | 여백 |
| 50mm | 14173 | 좁은 열 |
| 75mm | 21260 | 반 너비 열 |
| 150mm | 42520 | 전체 너비 |

---

## Font Size Height Table

| 용도 | pt | height | 사용 |
|------|-----|--------|------|
| 대제목 | 20pt | 2000 | 문서 타이틀 |
| 중제목 | 16pt | 1600 | 섹션 헤딩 |
| 소제목 | 14pt | 1400 | 하위 섹션 |
| 본문 | 10pt | 1000 | 기본 텍스트 |
| 주석/캡션 | 9pt | 900 | 부가 정보, 출처 |
| 미주/각주 | 8pt | 800 | 법적 고지 |

**줄간격 (lineSpacing)**:

| 유형 | value | 사용 |
|------|-------|------|
| 넓음 | 200 | 보고서, 공문서 |
| 표준 | 160 | 일반 문서 |
| 좁음 | 130 | 표 안, 양식 |

---

## Rhwp Preview API

번들된 rhwp WASM(`pyhwpxlib/vendor/rhwp_bg.wasm`) 기반. wasmtime 필요.

```python
from pyhwpxlib.rhwp_bridge import RhwpEngine
engine = RhwpEngine()           # 싱글톤 재사용 권장 (WASM 초기화 비용)
doc = engine.load("output.hwpx")
```

| 메서드 | 반환 | 용도 |
|--------|------|------|
| `doc.page_count` | int | 페이지 수 (rhwp auto-paginate 결과) |
| `doc.render_page_svg(i, embed_fonts=False)` | str | SVG 문자열 (PNG 변환용) |
| `doc.render_page_html(i)` | str | HTML fragment (수십 KB, MCP 응답 경량화) |
| `doc.get_page_render_tree(i)` | dict | `{type, bbox, children}` — **좌표 기반 레이아웃 검증** |
| `doc.render_page_canvas_count(i)` | int | Canvas 2D 명령 개수 (sanity check) |
| `doc.close()` | — | 핸들 해제 (with 구문 권장) |

### RenderTree 구조

```
Page (root)
├─ PageBg
├─ Header     (bbox.h = 0 if 공문처럼 머리말 없음)
├─ Body       ← 본문 영역. y+h = Footer 직전
│  └─ Column/Paragraph/TextLine/TextRun ...
└─ Footer
```

**활용 예: 1페이지 overflow 감지**

```python
def body_bbox(tree):
    return next(c for c in tree["children"] if c["type"] == "Body")["bbox"]

tree = doc.get_page_render_tree(0)
if doc.page_count > 1:
    print("본문이 넘침 — spacer 줄이기 / 여백 축소 필요")
```

### 한계 (2026-04 기준)

- **`renderPageToCanvas`** (브라우저 HtmlCanvasElement 직접 그리기)는 Python에서 호출 불가 — 비트맵이 필요하면 `render_page_svg` → resvg → PNG 경로 사용
- **textWrap 미지원** — 이미지와 텍스트가 겹쳐 보일 수 있음 (Whale에서는 정상)
- **linesegarray 불일치** — 텍스트 교체 후 줄 뭉침 발생 가능
