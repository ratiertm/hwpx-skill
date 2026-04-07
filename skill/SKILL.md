---
name: hwpx
description: "Use this skill whenever the user wants to create, read, edit, or manipulate Hangul/Korean word processor documents (.hwpx, .hwp, .owpml files). Triggers include: any mention of 'hwpx', 'hwp', '한글 파일', '한글 문서', '한컴', 'OWPML', or requests to produce Korean government forms, fill templates, clone forms, or convert documents. Also use when converting HWP to HWPX (hwp2hwpx), extracting text from .hwpx files, filling form fields, checking/unchecking boxes, generating multiple filled documents, or converting HTML/Markdown to .hwpx format. If the user asks for a Korean document, government form, template automation, or HWP file conversion, use this skill. Do NOT use for .docx Word documents, PDFs, or spreadsheets."
---

# HWPX creation, editing, and form automation

## 절대 규칙 — 이 스킬의 모든 작업에 적용

1. **pyhwpxlib만 사용한다.** 자체 코드를 작성하거나 다른 라이브러리로 우회하지 않는다.
2. `.hwp` 파일이 들어오면 **반드시 `pyhwpxlib.hwp2hwpx.convert()`로 HWPX 변환부터** 한다. olefile 직접 읽기, 바이너리 파싱 등 다른 방법을 시도하지 않는다.
3. `.hwpx` 파일이 들어오면 **반드시 `pyhwpxlib.api.extract_text()`로 읽는다.** zipfile로 직접 열거나 xml.etree로 직접 파싱하지 않는다.
4. 새 문서 생성은 **반드시 `from pyhwpxlib import HwpxBuilder`를 사용한다.** XML을 직접 작성하지 않는다.
5. 문서 편집은 **반드시 `pyhwpxlib unpack → 문자열 교체 → pyhwpxlib pack` 순서**를 따른다.

위 규칙을 어기면 Whale/한컴오피스에서 파일이 열리지 않거나 서식이 깨진다.

## 디자인 규칙 — 새 문서 생성 시 반드시 적용

지루한 문서를 만들지 마라. 자세한 가이드: [references/design_guide.md](references/design_guide.md)

1. **주제에 맞는 색상을 선택한다** — 파란색 디폴트 금지. design_guide.md에 10종 팔레트 있음
2. **매 섹션마다 시각 요소** — 텍스트만 있는 섹션 금지. 표/박스/목록/수치 중 최소 1개
3. **같은 레이아웃 반복 금지** — 표→목록→박스→인용문 순환
4. **AI 생성 패턴 피하기** — 제목 아래 악센트 라인, 매번 같은 표지, 모든 섹션 동일 구조
5. **QA 필수** — 생성 후 validate + 사용자에게 Whale 확인 요청. 문제가 있다고 가정하고 찾는다

---

## On Load — 스킬 로드 시 즉시 실행

이 스킬이 로드되면 **반드시** 아래 흐름을 따른다. 이 단계를 건너뛰지 않는다.

사용자의 메시지에 구체적인 작업이 포함되어 있지 않은 경우, **반드시 AskUserQuestion을 호출**하여 작업을 물어본다:

```
"어떤 작업을 하시겠어요?"

1. 새 문서 만들기 — HwpxBuilder로 보고서, 공문서, 양식 등 생성
2. 기존 문서 편집 — hwpx 파일의 텍스트/서식 수정 (unpack → edit → pack)
3. 양식 자동화 — 서식 템플릿에 데이터 채우기, 다건 생성, 스키마 추출
4. 문서 변환 — MD→HWPX, HTML→HWPX, HWPX→HTML, HWP 5.x 읽기
```

사용자가 이미 구체적인 요청을 했으면 (예: "이 hwp 파일 읽어줘", "보고서 만들어줘") 질문 없이 바로 해당 작업을 진행한다. 단, 해당 워크플로우의 각 단계는 **반드시 AskUserQuestion으로 진행**한다 — 단계를 건너뛰고 혼자 판단하지 않는다.

**자동 감지 규칙** — 파일 확장자에 따라 자동 판단:
- 사용자가 `.hwp` 파일을 주면 → **먼저 hwp2hwpx로 HWPX 변환** 후 작업 진행
- 사용자가 `.hwpx` 파일을 주면 → 바로 읽기/편집/양식 채우기 진행
- 사용자가 `.md` 파일을 주면 → md2hwpx 또는 LLM+HwpxBuilder로 변환
- 사용자가 `.html` 파일을 주면 → convert_html_file_to_hwpx로 변환
- 사용자가 텍스트만 주면 → HwpxBuilder로 새 문서 생성

```python
# .hwp 파일 감지 시 자동 실행
from pyhwpxlib.hwp_reader import detect_format
fmt = detect_format(file_path)  # "HWP" or "HWPX"
if fmt == "HWP":
    from pyhwpxlib.hwp2hwpx import convert
    hwpx_path = file_path.replace('.hwp', '.hwpx')
    convert(file_path, hwpx_path)
    # 이후 hwpx_path로 작업 진행
```

**워크플로우 [1] 새 문서 만들기**:

Step A: AskUserQuestion — "어떤 유형?" → 정부양식/공문서/보고서/세무법무/논문/자유
Step B: 디자인 결정 — [references/design_guide.md](references/design_guide.md) 읽고 주제에 맞는 팔레트 선택
Step C: AskUserQuestion — "내용을 알려주세요"
Step D: 실행
```python
from pyhwpxlib import HwpxBuilder, DS
doc = HwpxBuilder(table_preset='corporate')
# 주제에 맞는 팔레트 적용, 매 섹션 시각 요소 포함, 같은 레이아웃 반복 금지
doc.add_paragraph(제목, bold=True, font_size=18, text_color=PALETTE['primary'], alignment='CENTER')
# ... 본문, 표, 박스, 목록 조합 ...
doc.save(파일명)
```
Step E: `pyhwpxlib validate 파일명`
Step F: 자동 시각 검토 — HWPX → HTML → 스크린샷 → Claude가 직접 확인
```python
from pyhwpxlib.api import convert_hwpx_to_html
convert_hwpx_to_html(파일명, '/tmp/hwpx_preview.html')
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 800, 'height': 1200})
    page.goto('file:///tmp/hwpx_preview.html')
    page.wait_for_timeout(1000)
    page.screenshot(path='/tmp/hwpx_preview.png', full_page=True)
    browser.close()
# Read tool로 /tmp/hwpx_preview.png 확인 → 문제 발견 시 자동 수정
```
Step G: AskUserQuestion — "Whale에서도 열어 확인해주세요. 수정할 부분 있나요?" → 있으면 Step C로

**워크플로우 [2] 기존 문서 편집**:

Step A: AskUserQuestion — "파일 경로?"
Step B: 자동 감지 + 텍스트 추출
```python
from pyhwpxlib.hwp_reader import detect_format
if detect_format(path) == "HWP":
    from pyhwpxlib.hwp2hwpx import convert
    convert(path, hwpx_path)
from pyhwpxlib.api import extract_text
print(extract_text(hwpx_path))  # 사용자에게 내용 보여주기
```
Step C: AskUserQuestion — "어떤 편집?" → 텍스트 교체/구조 수정/양식 채우기
Step D: 실행
```bash
pyhwpxlib unpack doc.hwpx -o unpacked/
# 원본 문자열 교체 (ET.tostring 금지!)
pyhwpxlib pack unpacked/ -o output.hwpx
pyhwpxlib validate output.hwpx
```
Step E: AskUserQuestion — "수정할 부분 있나요?"

**워크플로우 [3] 양식 자동화**:

Step A: AskUserQuestion — "템플릿 파일 경로?"
Step B: 스키마 추출 → 필드 목록 보여주기
```python
from pyhwpxlib.api import extract_schema
schema = extract_schema(template_path)
```
Step C: AskUserQuestion — "데이터 입력 방식?" → 대화형/JSON/CSV파일
Step D: 데이터 입력 받기 → 확인 보여주기 → AskUserQuestion "맞나요?"
Step E: 실행
```python
from pyhwpxlib.api import fill_template_checkbox
fill_template_checkbox(template_path, data=data, checks=checks, output_path=output)
```
Step F: `pyhwpxlib validate output` → AskUserQuestion "추가 생성?"

**워크플로우 [4] 문서 변환**:

Step A: AskUserQuestion — "변환 유형?" → HWP→HWPX / MD→HWPX / HTML→HWPX / HWPX→HTML
Step B: AskUserQuestion — "파일 경로?"
Step C: 실행
```python
# HWP→HWPX
from pyhwpxlib.hwp2hwpx import convert
convert(hwp_path, hwpx_path)

# MD→HWPX
# pyhwpxlib md2hwpx input.md -o output.hwpx

# HTML→HWPX
from pyhwpxlib.api import convert_html_file_to_hwpx
convert_html_file_to_hwpx(html_path, hwpx_path)
```
Step D: `pyhwpxlib validate output` → 결과 요약
Step E: AskUserQuestion — "다음 작업?" → 편집/추가 변환/완료

모든 흐름의 마지막은 **"수정할 부분이 있으면 알려주세요"**로 끝나고, 사용자가 만족할 때까지 반복한다.

---

## Quick Reference

| Task | Approach |
|------|----------|
| Read/extract text | `pyhwpxlib.api.extract_text()` or unpack for raw XML |
| Create new document | Use `HwpxBuilder` — see Creating New Documents below |
| Edit existing document | Unpack → edit XML → repack — see Editing Existing Documents below |
| Fill form template | `fill_template_checkbox()` — see [references/form_automation.md](references/form_automation.md) |
| Batch generate | `fill_template_batch()` — multiple files from one template |
| Convert MD → HWPX | `pyhwpxlib md2hwpx input.md -o output.hwpx` |
| Convert HTML → HWPX | `convert_html_file_to_hwpx(html_path, hwpx_path)` |
| **Convert HWP → HWPX** | `pyhwpxlib.hwp2hwpx.convert(hwp_path, hwpx_path)` |
| Read HWP 5.x binary | `pyhwpxlib.hwp_reader.read_hwp()` |
| Analyze form fields | `extract_schema()` + `analyze_schema_with_llm()` |

---

## Creating New Documents

Generate .hwpx files with `HwpxBuilder`, then validate.

### Setup
```python
from pyhwpxlib import HwpxBuilder, DS, TABLE_PRESETS

doc = HwpxBuilder(table_preset='corporate')
doc.add_heading("제목", level=1)
doc.add_paragraph("본문 텍스트")
doc.add_table([["A", "B"], ["1", "2"]])
doc.save("output.hwpx")
```

### Validation
```bash
pyhwpxlib validate output.hwpx
```

### HwpxBuilder Method Table

| 메서드 | 용도 |
|--------|------|
| `add_heading(text, level, alignment)` | 제목 (1~4) |
| `add_paragraph(text, bold, italic, font_size, text_color, alignment)` | 단락 |
| `add_table(data, header_bg, cell_colors, cell_margin, ...)` | 표 (프리셋 자동) |
| `add_bullet_list(items, bullet_char)` | 글머리 기호 목록 |
| `add_numbered_list(items, format_string)` | 번호 목록 |
| `add_nested_bullet_list(items)` | 중첩 글머리 [(level, text), ...] |
| `add_nested_numbered_list(items)` | 중첩 번호 [(level, text), ...] |
| `add_image(path, width, height)` | 로컬 이미지 |
| `add_image_from_url(url, filename, width, height)` | URL 이미지 다운로드 |
| `add_page_break()` | 페이지 나누기 |
| `add_line()` | 구분선 |
| `add_header(text)` | 머리말 |
| `add_footer(text)` | 꼬리말 |
| `add_page_number(pos)` | 페이지 번호 |
| `add_footnote(text, number)` | 각주 |
| `add_equation(script)` | 수식 |
| `add_highlight(text, color)` | 텍스트 하이라이트 |
| `add_rectangle(width, height, line_color)` | 사각형 도형 |
| `add_draw_line(x1, y1, x2, y2, line_color)` | 직선 도형 |
| `save(path)` | 저장 |

### Key API Examples

**생성자**:
```python
doc = HwpxBuilder(table_preset='corporate')
# table_preset: 'corporate' | 'government' | 'academic' | 'default'
# 프리셋이 표의 헤더색, 패딩, 행높이, 정렬, 줄무늬를 자동 적용
```

**표** — 프리셋 자동 적용:
```python
doc.add_table(
    data,                          # list[list[str]] — 필수
    header_bg='#395da2',           # 헤더 배경색. None=프리셋, ''=없음
    cell_colors={(1,0): '#d8e2ff'},# {(row,col): '#hex'} 셀별 배경색
    cell_margin=(283,283,200,200), # (L,R,T,B) 셀 패딩. None=프리셋
    col_widths=[12000, 30520],     # 컬럼별 너비. None=균등분할
    row_heights=[2400, 2000],      # 행별 높이. None=프리셋
    merge_info=[(0,0,0,2)],        # [(r1,c1,r2,c2)] 병합
    cell_aligns={(1,2): 'RIGHT'},  # {(row,col): 'CENTER'|'LEFT'|'RIGHT'}
    cell_styles={(0,0): {'text_color':'#f7f7ff','bold':True,'font_size':12}},
    cell_gradients={(0,0): {'start':'#FF0000','end':'#0000FF'}},
    width=42520,                   # 표 전체 너비 (기본 A4 content width)
    use_preset=False,              # False면 프리셋 자동 적용 안 함
)
```

**col_widths — LLM이 내용에 맞게 조정**:
- `col_widths`: 내용이 긴 컬럼은 넓게, 짧은 컬럼은 좁게 (합계 = 42520)
  - 텍스트 길이 기반 비율 계산: `내용 평균 글자수 × CJK 가중치(2)` 비율로 분배
  - 예: ['항목'(2글자), '설명'(20글자)] → col_widths=[8000, 34520]
- `row_heights`: 셀 내 텍스트가 한 줄이면 2000, 여러 줄이면 3000~4000

**키-값 표** (라벨+값, 헤더 없음):
```python
doc.add_table([
    ['설립', '1969년'],
    ['본사', '수원시'],
], col_widths=[10000, 32520], header_bg='',
    cell_styles={(r,0): {'bold': True, 'text_color': '#395da2'} for r in range(2)})
```

**이미지** — `add_image(path, width, height)` / `add_image_from_url(url, ...)`:
```python
doc.add_image("photo.png", width=21260, height=15000)
doc.add_image_from_url("https://example.com/image.png",
    filename="my_image.png", width=42520, height=21260)
```

**디자인 컴포넌트 — 표를 활용한 박스**:
```python
# 하이라이트 박스 (연한 라벤더블루)
doc.add_table([['핵심 요약 내용']],
    cell_colors={(0,0): '#d8e2ff'}, row_heights=[2400],
    cell_margin=(400,400,300,300), header_bg='',
    cell_styles={(0,0): {'text_color': '#2a5094'}}, use_preset=False)

# 콜아웃 박스 (연보라 — 인용, 주의)
doc.add_table([['인용문 또는 경고']],
    cell_colors={(0,0): '#e2dbfd'}, row_heights=[2000],
    cell_margin=(400,400,300,300), header_bg='',
    cell_styles={(0,0): {'text_color': '#514d68'}}, use_preset=False)

# 정보 박스 (연시안 — 참고)
doc.add_table([['참고 정보']],
    cell_colors={(0,0): '#cbe7f5'}, row_heights=[2000],
    cell_margin=(400,400,300,300), header_bg='',
    cell_styles={(0,0): {'text_color': '#3c5561'}}, use_preset=False)
```

**디자인 시스템 색상 상수** (`DS` dict):
```python
from pyhwpxlib import DS
DS['primary']           # '#395da2' — 헤더, 소제목
DS['on_primary']        # '#f7f7ff' — primary 위 텍스트
DS['on_surface']        # '#2b3437' — 본문 (순검정 금지)
DS['on_surface_var']    # '#586064' — 메타, 캡션
DS['primary_container'] # '#d8e2ff' — 하이라이트 박스
DS['tertiary_container']# '#e2dbfd' — 콜아웃 박스
DS['surface_low']       # '#f1f4f6' — 줄무늬, 2차 배경
DS['outline_var']       # '#abb3b7' — 구분선
DS['error']             # '#9f403d' — 경고
```

### Critical Rules for HwpxBuilder

- **pyhwpxlib 기반** — header.xml은 pyhwpxlib가 생성, section만 HwpxBuilder가 구성
- **줄바꿈 금지** — `<hp:t>` 안에 `\n` 넣으면 Whale 에러. 별도 `<hp:p>`로 분리
- **mimetype STORED** — ZIP의 mimetype 엔트리는 압축 없이(STORED) 첫 번째로
- **ET.tostring 금지** — XML 재직렬화 시 네임스페이스 변경으로 Whale 에러. 원본 문자열 직접 교체

> For full pyhwpxlib API (lists, shapes, equations, headers/footers, etc.) → see [references/api_full.md](references/api_full.md)

---

## Editing Existing Documents

**Read [references/editing.md](references/editing.md) for full details.** 요약:

### Step 1: Unpack
```bash
pyhwpxlib unpack document.hwpx -o unpacked/
```
Extracts all XML files to a folder.

### Step 2: Edit XML

Edit files in `unpacked/Contents/`. See [references/api_full.md](references/api_full.md) for XML Reference patterns.

**CRITICAL: Use original XML string replacement. Do NOT use ET.tostring() for re-serialization — it changes namespace prefixes and breaks Whale rendering.**

```python
# CORRECT — 원본 문자열 직접 교체
with open('unpacked/Contents/section0.xml', 'r') as f:
    xml = f.read()
xml = xml.replace('>성 명<', '>성 명  홍길동<', 1)
with open('unpacked/Contents/section0.xml', 'w') as f:
    f.write(xml)
```

```python
# WRONG — ET.tostring 재직렬화 (네임스페이스 깨짐)
root = ET.fromstring(xml)
new_xml = ET.tostring(root, encoding='unicode')  # Whale 에러!
```

### Advanced Operations

For complex edits (section extraction, paragraph insert/delete, table insertion, multi-run field filling), see [references/form_automation.md — Advanced XML Editing](references/form_automation.md).

### Step 3: Pack
```bash
pyhwpxlib pack unpacked/ -o output.hwpx
```
Creates HWPX with mimetype STORED as first entry.

### Validation
```bash
pyhwpxlib validate output.hwpx
```
Checks: ZIP validity, required files, mimetype, XML parsing, namespaces.

---

## Converting Documents

### HWP → HWPX (한글 5.x 바이너리 변환)
```python
from pyhwpxlib.hwp2hwpx import convert

convert("input.hwp", "output.hwpx")
# HWP 5.x 바이너리 → HWPX(ZIP/XML) 변환
# 표, 스타일, 병합, 머리말/꼬리말, 각주, 이미지 등 지원
```

```python
# 폴더 내 전체 HWP 파일 일괄 변환
import os
from pyhwpxlib.hwp2hwpx import convert

src_dir = "hwp_samples"
dst_dir = "hwpx_converted"
os.makedirs(dst_dir, exist_ok=True)

for f in os.listdir(src_dir):
    if f.endswith(".hwp"):
        convert(os.path.join(src_dir, f),
                os.path.join(dst_dir, f.replace(".hwp", ".hwpx")))
```

### Markdown → HWPX
```bash
python -m pyhwpxlib.cli md2hwpx input.md -o output.hwpx -s github
```
Styles: `github`, `vscode`, `minimal`, `academic`

**md 파일 → HWPX 변환 방법 2가지**:

| 방법 | 장점 | 단점 | 사용 시점 |
|------|------|------|----------|
| `md2hwpx` CLI | 빠름, 일관됨 | 단순 규칙 변환, 디자인 제한 | 단순 변환, 대량 처리 |
| LLM + HwpxBuilder | 문맥 이해, 디자인 적용 가능 | 느림 | 디자인 중요한 문서 |

**LLM이 md를 HwpxBuilder로 변환할 때 원칙**:
- 원문 텍스트를 그대로 사용한다 — 요약·재작성·생략 금지
- md의 구조(제목 계층, 표, 인용 등)를 보존한다
- 스타일링은 LLM이 주도적으로 판단하여 적용한다

### HTML → HWPX
```python
from pyhwpxlib.api import convert_html_file_to_hwpx
convert_html_file_to_hwpx("input.html", "output.hwpx")
# strip_links=True (기본값) — <a> 태그 자동 제거 (Whale fieldBegin 에러 방지)
```

### HWPX → HTML
```python
from pyhwpxlib.api import convert_hwpx_to_html
convert_hwpx_to_html("input.hwpx", "output.html")
```

### Text Extraction
```python
from pyhwpxlib.api import extract_text
text = extract_text("document.hwpx")
```

### HWP 5.x Binary Reading
```python
from pyhwpxlib.hwp_reader import read_hwp, detect_format

fmt = detect_format("file.hwp")  # "HWP" or "HWPX"
doc = read_hwp("file.hwp")
# doc['texts'], doc['paragraphs'], doc['tables'], doc['face_names']
```

---

## Critical Rules Summary

| # | Rule | Consequence |
|---|------|-------------|
| 1 | `<hp:t>` 안에 `\n` 금지 | Whale 에러 |
| 2 | secPr p에만 linesegarray | 글자 겹침 |
| 3 | ET.tostring 재직렬화 금지 | 네임스페이스 변경 → Whale 에러 |
| 4 | 원본 ZIP + 텍스트 교체 | 서식 100% 보존 유일한 방법 |
| 5 | condense 보존 | JUSTIFY 글자 벌어짐 방지 |
| 6 | styleIDRef 보존 | 들여쓰기 유지 |
| 7 | mimetype STORED | OPC 규격 필수 |
| 8 | `<a href>` 제거 | fieldBegin/fieldEnd Whale 에러 |
| 9 | 원문 텍스트 보존 — 요약·재작성·생략 금지 | 원문 왜곡 방지 |
| 10 | 원문 성격에 맞지 않는 양식 강제 금지 | 리서치문에 기업보고서 표지 등 |
| 11 | LLM은 스타일링은 자유롭게, 내용은 충실하게 | 디자인은 판단, 텍스트는 보존 |
| 12 | header/footer/page_number는 SecPr 뒤에 삽입 | HwpxBuilder가 자동 처리 (deferred) |

---

## Getting Started (시작 가이드)

### 1. 설치
```bash
pip install pyhwpxlib
```

### 2. 첫 문서 만들기
```python
from pyhwpxlib import HwpxBuilder

doc = HwpxBuilder()
doc.add_heading("첫 번째 문서", level=1)
doc.add_paragraph("pyhwpxlib으로 만든 문서입니다.")
doc.add_table([["이름", "나이"], ["홍길동", "30"]])
doc.save("my_first.hwpx")
```
→ `my_first.hwpx`를 Whale 또는 한컴오피스에서 열어 확인

### 3. 기존 HWP 파일 변환
```bash
# HWP 5.x → HWPX
python -c "from pyhwpxlib.hwp2hwpx import convert; convert('old.hwp', 'new.hwpx')"

# 마크다운 → HWPX
pyhwpxlib md2hwpx report.md -o report.hwpx
```

### 4. 기존 문서 편집
```bash
pyhwpxlib unpack document.hwpx -o unpacked/   # 풀기
# unpacked/Contents/section0.xml 편집
pyhwpxlib pack unpacked/ -o output.hwpx        # 묶기
pyhwpxlib validate output.hwpx                 # 검증
```

### 5. 양식 자동 채우기
```python
from pyhwpxlib.api import fill_template_checkbox

fill_template_checkbox("양식.hwpx",
    data={">성 명<": ">성 명  홍길동<"},
    checks=["동의함"],
    output_path="완성.hwpx")
```

---

## Dependencies

- **pyhwpxlib**: `pip install pyhwpxlib` (핵심 라이브러리)
- **olefile**: HWP 5.x 읽기용 (자동 설치됨)

---

## Skill Update (스킬 동기화)

프로젝트 `skill/`과 설치된 `~/.claude/skills/hwpx/` 간 동기화:

```bash
# 상태 확인 — 어디가 다른지 보기
python -m pyhwpxlib.update_skill status

# Push — 프로젝트 → 설치된 스킬
python -m pyhwpxlib.update_skill push

# Pull — 설치된 스킬 → 프로젝트
python -m pyhwpxlib.update_skill pull

# Backup — 현재 설치된 스킬 스냅샷
python -m pyhwpxlib.update_skill backup
```

---

## Reference Files

| File | Contents |
|------|----------|
| [references/api_full.md](references/api_full.md) | pyhwpxlib full function reference, XML reference, page sizes, size conversion table |
| [references/document_types.md](references/document_types.md) | Document type specs (5 types), indent guide, TOC patterns, cover page patterns, document structure guide, table design guide |
| [references/form_automation.md](references/form_automation.md) | fill_template, batch generate, schema extraction, checkbox patterns, advanced XML editing |
| [references/design_guide.md](references/design_guide.md) | 주제별 색상 팔레트 10종, 레이아웃 패턴, 타이포그래피, QA 프로세스 |
| [references/editing.md](references/editing.md) | 편집 워크플로우, XML 규칙, 흔한 실수, 양식 채우기, 고급 편집 (표 삽입, 섹션 추출) |
