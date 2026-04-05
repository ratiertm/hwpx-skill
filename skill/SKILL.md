---
name: hwpx
description: "Use this skill whenever the user wants to create, read, edit, or manipulate Hangul/Korean word processor documents (.hwpx, .hwp, .owpml files). Triggers include: any mention of 'hwpx', 'hwp', '한글 파일', '한글 문서', '한컴', 'OWPML', or requests to produce Korean government forms, fill templates, clone forms, or convert documents. Also use when extracting text from .hwpx files, filling form fields, checking/unchecking boxes, generating multiple filled documents, or converting HTML/Markdown to .hwpx format. If the user asks for a Korean document, government form, or template automation, use this skill. Do NOT use for .docx Word documents, PDFs, or spreadsheets."
---

# HWPX creation, editing, and form automation

## Table of Contents

1. [Overview](#overview)
2. [Quick Reference](#quick-reference)
3. [Creating New Documents](#creating-new-documents)
   - HwpxBuilder API
   - Page Size
   - Document Templates & Style Guide
   - Document Structure Guide
   - Table Design Guide
   - Indent Guide
   - Critical Rules
4. [Editing Existing Documents](#editing-existing-documents)
   - Step 1: Unpack
   - Step 2: Edit XML
   - Step 3: Pack
5. [Form Automation](#form-automation)
   - Fill Template
   - Batch Generate
   - Schema Extraction
   - Template Builder UI
   - Checkbox Patterns
6. [Converting Documents](#converting-documents)
   - MD → HWPX
   - HTML → HWPX
   - HWPX → HTML
   - HWP 5.x Reading
7. [XML Reference](#xml-reference)
   - Document Structure
   - Namespaces
   - Paragraph / Table / charPr / paraPr
8. [Critical Rules Summary](#critical-rules-summary)
9. [Dependencies](#dependencies)

---

## Document Design Principles (문서 디자인 원칙)

**LLM은 템플릿 복붙 머신이 아니다. 문서 디자이너다.**

매 문서마다 동일한 레이아웃을 반복하지 않는다. 내용을 읽고, 그 문서에 가장 적합한 구성을 판단하여 컴포넌트를 조합한다.

**금지 패턴**:
- 매번 같은 표지 (빈줄 5개 → 카테고리 → 대제목 → 부제 → 하이라이트 박스 → 날짜 → 구분선)
- 모든 문서에 "EQUITY RESEARCH", "CONFIDENTIAL" 같은 라벨 붙이기
- 내용과 무관하게 7개 섹션 + 목차 + 표지를 기계적으로 생성
- 원문을 요약·재작성하여 자기 말로 바꾸기
- 모든 섹션마다 page_break를 넣어 1섹션=1페이지 강제하기

**해야 하는 것**:
- 내용을 먼저 읽고, 문서의 성격(리서치/제안서/공문/안내문/분석)을 파악
- 그 성격에 맞는 레이아웃과 컴포넌트를 선택
- 표지가 필요한 문서인지, 목차가 필요한 분량인지 판단
- 표/박스/구분선/이미지를 어디에 배치하면 효과적인지 판단
- 원문 텍스트는 그대로 사용하되, 시각적 배치와 강조는 LLM이 디자인
- page_break는 내용 흐름에 맞게 적절히 사용 (자연스럽게 넘치면 자동 넘김, 주제 전환 시만 명시적 삽입)

**페이지 나누기 판단 기준**:
- 표지 → 본문: page_break 필요
- 목차 → 본문: page_break 필요
- 같은 주제 내 소제목 전환: page_break 불필요 (자연스럽게 이어짐)
- 큰 주제 전환 (예: "분석" → "결론"): 내용량에 따라 판단
- 짧은 문서 (3~4페이지): page_break 최소화 — 내용이 자연스럽게 흐르게
- 긴 문서 (10페이지+): 장(chapter) 단위에서만 page_break

**컴포넌트 조합 판단 기준**:

| 내용 특성 | 적합한 컴포넌트 |
|----------|----------------|
| 핵심 수치/요약 | 하이라이트 박스 (#d8e2ff) |
| 인용문/참고사항 | 콜아웃 박스 (#e2dbfd) |
| 비교 데이터 | 표 (헤더 + 줄무늬) |
| 순서/절차 | 번호 목록 + 들여쓰기 |
| 강조/경고 | error 색상 (#9f403d) 텍스트 |
| 부연/메타 정보 | 정보 박스 (#cbe7f5) 또는 작은 회색 텍스트 |
| 시각적 구분 | 텍스트 구분선 (━), 페이지 나누기 |
| 장문 본문 | 소제목(primary 색상) + 들여쓰기 단락 |

**stitch 레퍼런스 (skill/stitch/ hwpx_1~5)**:
5가지 서로 다른 레이아웃 패턴이 있다. 매번 같은 걸 쓰지 말고, 내용에 맞는 패턴을 참고한다.

### 확정된 스타일 규칙 (세션 테스트 완료)

**폰트 크기 체계** — 점진적 축소 (heading API 대신 add_paragraph로 직접 제어):
```
대제목: 18pt bold CENTER (문서 타이틀)
섹션 제목: 14pt bold primary색 (1. 2. 3. 번호 포함)
본문: 11pt on-surface색 (2칸 들여쓰기)
부제/캡션: 10pt on-surface-variant색
참고/미주: 8pt outline-variant색
```
- heading API(24/18/16/14pt)는 크기 점프가 커서 균형이 안 맞음
- add_paragraph(bold, font_size, text_color)로 직접 제어 권장

**섹션 구성 패턴**:
```python
# 섹션 제목 — 번호 포함, primary 색상
doc.add_paragraph('1. 섹션 제목', bold=True, font_size=14, text_color='#395da2')
# 본문 — 바로 아래 (빈 줄 없음), 2칸 들여쓰기
doc.add_paragraph('  본문 텍스트...', font_size=11, text_color='#2b3437')
```
- 섹션 제목과 본문 사이에 빈 줄 넣지 않음 (스페이싱 최소)
- 본문 첫 줄에 `  ` (2칸) 들여쓰기

**블릿 목록** — 텍스트 방식 (네이티브 블릿은 Whale에서 문자 무시됨):
```python
doc.add_bullet_list(['항목1', '항목2', '항목3'])
# → "    - 항목1" 형태로 출력 (4칸 들여쓰기 + '-' 문자)
# 블릿 문자 순서: '-' (기본), '•', '◦'
# 본문보다 들여써서 계층 구분
```

**표 규칙**:
- 데이터 행: CENTER 정렬 (프리셋 자동)
- 헤더 행: CENTER + 볼드 + primary 배경 + 흰 텍스트 (프리셋 자동)
- 짝수 행: 줄무늬 #f1f4f6 (프리셋 자동)
- col_widths: 텍스트 길이에 맞게 LLM이 판단 (합계=42520)
  - 짧은 컬럼(라벨 2~3글자): 7000~9000
  - 긴 컬럼(설명 20글자+): 20000~30000
- row_heights: 한 줄이면 2000, 여러 줄이면 3000~4000

**페이지 나누기**: 표지→본문, 목차→본문에서만. 짧은 문서는 자연스럽게 흐르게.

---

## Interactive Workflow (대화형 문서 생성)

사용자가 "한글 문서 만들어줘"라고 요청하면, 아래 단계를 순서대로 진행합니다.
**AskUserQuestion 도구를 사용**하여 각 단계에서 사용자 선택을 받습니다.

### Step 1: 문서 유형 선택

```
"어떤 유형의 문서를 만드시겠어요?"

1. 정부 양식 — 신청서, 계약서, 허가서 (바탕 11pt, 160%)
2. 공문서 — 기관 공문, 협조전, 통보서 (바탕 12pt, 160%)
3. 기업 보고서 — 분석, 제안서, 실적 보고 (돋움 제목, 170%)
4. 세무/법무 — 소장, 세금계산서, 등기 (바탕 12pt, 200%)
5. 학술 논문 — 학위 논문, 학회 발표 (바탕 11pt, 170%)
6. 자유 형식 — 직접 지정
```

→ 선택에 따라 Document Type Specifications의 스타일 자동 적용

### Step 2: 양식/템플릿 선택

```
"어떤 양식을 사용하시겠어요?"

1. 기본 템플릿으로 새로 만들기 — HwpxBuilder로 생성
2. 기존 hwpx 파일 업로드 — 텍스트 교체 방식 (서식 100% 보존)
3. 샘플에서 선택 — 미리 만든 양식 중 선택
```

→ 2번 선택 시: 파일 경로 입력 → extract_schema → 필드 분류

### Step 3: 내용 입력

**새로 만들기 (1번)**:
```
"문서 내용을 알려주세요."
→ 제목, 본문 주제, 포함할 데이터 등을 자유롭게 입력
→ 대화를 통해 내용 구성
```

**기존 양식 편집 (2번)** — 3가지 데이터 입력 방식:

**방식 A: 대화형 (AskUserQuestion)**
```
"다음 필드에 데이터를 입력해주세요:"

[성 명]     → 홍길동
[주민등록번호] → 850101-1234567
[사업체명]   → (주)블루오션
[사업체유형]  → 민간기업 ☑ / 공공기관 ☐ / 지방자치단체 ☐
```
→ AskUserQuestion으로 각 필드를 하나씩 또는 그룹으로 질문
→ 체크박스는 options로 선택지 제공

**방식 B: JSON 일괄 입력**
```
"데이터를 JSON으로 입력해주세요:"

{
  "성 명": "홍길동",
  "주민등록번호": "850101-1234567",
  "사업체명": "(주)블루오션",
  "checks": ["민간기업"]
}
```
→ 사용자가 JSON 텍스트를 한번에 붙여넣기
→ 다건 생성 시 배열로: `[{...}, {...}, ...]`

**방식 C: 파일 참조**
```
"데이터 파일 경로를 알려주세요:"
→ CSV: data.csv (헤더행 = 필드명)
→ JSON: data.json
→ Excel → CSV 변환 후 사용
```

**데이터 입력 후 확인**:
```
"입력하신 내용을 확인합니다:"

  성 명: 홍길동
  주민등록번호: 850101-1234567
  사업체명: (주)블루오션
  체크: [√] 민간기업

"맞으면 파일을 생성합니다. 수정할 부분이 있나요?"
```

### Step 4: 파일 생성

```
"파일명을 지정해주세요. (기본: {주제}_{날짜}.hwpx)"
→ 사용자 확인 후 hwpx 생성
→ 생성 완료 메시지 + 파일 경로 안내
→ "Whale/한컴오피스로 열어볼까요?" 확인
```

### Step 5: 수정/반복 (선택)

```
"수정할 부분이 있으면 알려주세요."
→ 텍스트 수정: unpack → edit → pack
→ 추가 생성: 같은 양식으로 다건 생성 (batch)
→ 만족: 완료
```

### Workflow 구현 예시

```python
# Step 1: 유형 선택 → 스타일 결정
doc_type = ask_user("문서 유형?", options=["정부양식", "공문서", "기업보고서", "세무법무", "학술논문"])

# Step 2: 양식 선택
template = ask_user("양식?", options=["새로 만들기", "기존 파일 업로드"])

if template == "새로 만들기":
    # Step 3: 내용 수집 → HwpxBuilder로 생성
    doc = HwpxBuilder()
    # doc_type에 맞는 스타일 자동 적용
    doc.add_heading(title, level=1)
    doc.add_paragraph(body)
    doc.save(output_path)

elif template == "기존 파일 업로드":
    # Step 3: 필드 채우기
    schema = extract_schema(uploaded_file)
    analyzed = analyze_schema_with_llm(schema)
    # 사용자에게 input_fields 보여주고 값 입력받기
    fill_template_checkbox(uploaded_file, data, checks, output_path)

# Step 4: 파일 열기
open_in_whale(output_path)
```

---

## Overview

A .hwpx file is a ZIP archive (OPC format) containing XML files following the OWPML (Open Word-Processor Markup Language) standard by Hancom. The key files are `Contents/header.xml` (styles) and `Contents/section0.xml` (body content).

## Quick Reference

| Task | Approach |
|------|----------|
| Read/extract text | `pyhwpxlib.api.extract_text()` or unpack for raw XML |
| Create new document | Use `HwpxBuilder` — see Creating New Documents below |
| Edit existing document | Unpack → edit XML → repack — see Editing Existing Documents below |
| Fill form template | `fill_template_checkbox()` — see Form Automation below |
| Batch generate | `fill_template_batch()` — multiple files from one template |
| Convert MD → HWPX | `pyhwpxlib md2hwpx input.md -o output.hwpx` |
| Convert HTML → HWPX | `convert_html_file_to_hwpx(html_path, hwpx_path)` |
| Read HWP 5.x binary | `pyhwpxlib.hwp_reader.read_hwp()` |
| Analyze form fields | `extract_schema()` + `analyze_schema_with_llm()` |

---

## Creating New Documents

Generate .hwpx files with `HwpxBuilder`, then validate.

### Setup
```python
from scripts.create import HwpxBuilder

doc = HwpxBuilder()
doc.add_heading("제목", level=1)
doc.add_paragraph("본문 텍스트")
doc.add_table([["A", "B"], ["1", "2"]])
doc.save("output.hwpx")
```

### Validation
```bash
python scripts/validate.py output.hwpx
```

### HwpxBuilder API — 전체 레퍼런스

```python
from scripts.create import HwpxBuilder, DS, TABLE_PRESETS
```

**생성자**:
```python
doc = HwpxBuilder(table_preset='corporate')
# table_preset: 'corporate' | 'government' | 'academic' | 'default'
# 프리셋이 표의 헤더색, 패딩, 행높이, 정렬, 줄무늬를 자동 적용
```

**제목** — `add_heading(text, level, alignment)`:
```python
doc.add_heading("제목", level=1)                    # 24pt 볼드
doc.add_heading("중제목", level=2)                  # 18pt 볼드
doc.add_heading("소제목", level=3)                  # 16pt 볼드
doc.add_heading("소소제목", level=4)                # 14pt 볼드
doc.add_heading("가운데 제목", level=1, alignment='CENTER')
```

**단락** — `add_paragraph(text, bold, italic, font_size, text_color, alignment)`:
```python
doc.add_paragraph("본문 텍스트")
doc.add_paragraph("")                               # 빈 줄 (간격)
doc.add_paragraph("강조", bold=True, text_color="#395da2")
doc.add_paragraph("작은 글씨", font_size=9, text_color="#586064")
doc.add_paragraph("가운데 정렬", alignment='CENTER')
# alignment: 'JUSTIFY'(기본) | 'CENTER' | 'LEFT' | 'RIGHT'
```

**표** — `add_table(data, ...)` — 프리셋 자동 적용:
```python
# 기본 사용 — 프리셋이 헤더색/패딩/정렬/줄무늬 자동 적용
doc.add_table([
    ["헤더1", "헤더2", "헤더3"],
    ["값1", "값2", "값3"],
])

# 전체 파라미터
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

**프리셋 자동 적용 항목** (use_preset=True일 때):
- `header_bg`: 프리셋 색상 (corporate=#395da2)
- `cell_margin`: 프리셋 패딩
- `row_heights`: 헤더 2400 + 데이터 2000
- `cell_aligns`: 헤더 행 CENTER, **데이터 행도 CENTER** (기본)
- `cell_styles`: 헤더 행 흰색(#f7f7ff) 볼드
- `stripe_color`: 짝수행 줄무늬 (#f1f4f6)
- 명시적 파라미터는 프리셋보다 우선

**표 셀 너비/높이 — LLM이 내용에 맞게 조정해야 하는 항목**:
- `col_widths`: 내용이 긴 컬럼은 넓게, 짧은 컬럼은 좁게 (합계 = 42520)
  - 텍스트 길이 기반 비율 계산: `내용 평균 글자수 × CJK 가중치(2)` 비율로 분배
  - 예: ['항목'(2글자), '설명'(20글자)] → col_widths=[8000, 34520]
- `row_heights`: 셀 내 텍스트가 한 줄이면 2000, 여러 줄이면 3000~4000
  - 줄바꿈(\n)이 있는 셀은 높이를 늘려야 함
  - 헤더 행은 항상 데이터 행보다 크거나 같게

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
# 로컬 파일
doc.add_image("photo.png", width=21260, height=15000)

# URL에서 다운로드 후 삽입
doc.add_image_from_url(
    "https://example.com/image.png",
    filename="my_image.png",
    width=42520,        # 전체 너비
    height=21260,
)
# → /tmp/hwpx_images/ 에 자동 다운로드
```

**페이지 나누기** — `add_page_break()`:
```python
doc.add_page_break()  # 다음 내용을 새 페이지에서 시작
```

**구분선** — `add_line()`:
```python
doc.add_line()  # ─ × 40 문자
# 또는 텍스트 구분선 (더 얇고 세련됨)
doc.add_paragraph('━' * 50, font_size=6, text_color='#abb3b7')
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

**저장**:
```python
doc.save("output.hwpx")  # 파일 경로 반환
```

**디자인 시스템 색상 상수** (`DS` dict):
```python
from scripts.create import DS
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

### pyhwpxlib 전체 함수 레퍼런스

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

**들여쓰기** — `ensure_para_style` + `add_paragraph`:
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

**머리말/꼬리말/페이지번호**:
```python
add_header(doc, "문서 제목 — 대외비")
add_footer(doc, "© 2026 회사명")
add_page_number(doc)
# pos: 'BOTTOM_CENTER'(기본), 'BOTTOM_RIGHT', 'TOP_CENTER', 'TOP_RIGHT'
# format_type: 'DIGIT'(기본), 'CIRCLE', 'HANGUL'
```

**각주**:
```python
add_footnote(doc, "출처: 삼성전자 2024년 사업보고서", number=1)
```

**수식**:
```python
add_equation(doc, "x = {-b +- sqrt {b^2 - 4ac}} over {2a}")
```

**하이퍼링크** (주의: Whale 에러 가능):
```python
add_hyperlink(doc, "네이버", "https://www.naver.com")
# Whale에서 fieldBegin/fieldEnd 에러 발생 가능 — 필요시만 사용
```

**텍스트 강조 (하이라이트)**:
```python
add_highlight(doc, "강조 텍스트", color="#FFFF00")
```

**북마크**:
```python
add_bookmark(doc, "section_1")
```

**도형**:
```python
add_rectangle(doc, width=14000, height=7000, line_color="#395da2", line_width=283)
add_ellipse(doc, width=10000, height=8000)
add_line(doc, x1=0, y1=0, x2=42520, y2=0, line_color="#abb3b7", line_width=71)
```

**다단 레이아웃**:
```python
set_columns(doc, col_count=2, same_gap=1200, separator_type="SOLID")
```

**문서 병합**:
```python
merge_documents(["doc1.hwpx", "doc2.hwpx"], "merged.hwpx")
```

**텍스트 추출**:
```python
text = extract_text("document.hwpx")
```

**HwpxBuilder로 모든 기능 사용 가능** — pyhwpxlib 직접 호출 불필요:

```python
doc = HwpxBuilder(table_preset='corporate')

# 제목 + 본문 + 표 + 목록 + 머리말 + 각주를 한 객체로
doc.add_heading("제목", level=1)
doc.add_paragraph("본문")
doc.add_table([["A", "B"], ["1", "2"]])
doc.add_bullet_list(["항목1", "항목2"])
doc.add_numbered_list(["가.", "나."])
doc.add_header("문서 제목")
doc.add_footer("© 2026")
doc.add_page_number()
doc.add_footnote("출처 정보")
doc.add_image_from_url("https://...", width=21260)
doc.save("output.hwpx")
```

**HwpxBuilder 전체 메서드 목록**:

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

### Page Size (OWPML 단위: 1/7200 inch)

| 용지 | width | height |
|------|-------|--------|
| A4 | 59,528 | 84,188 |
| B5 | 51,592 | 72,848 |
| Letter | 61,200 | 79,200 |

### Document Templates & Style Guide

**기본 폰트**: 함초롬돋움 (한컴 기본), 맑은 고딕 (Windows 호환), 나눔고딕 (웹 호환)

**폰트 크기 체계 (height 단위)**:

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

**표 스타일**:

| 스타일 | 설명 | 코드 |
|--------|------|------|
| 기본 표 | 테두리만 | borderFillIDRef="1" |
| 헤더 강조 | 첫 행 배경색 | set_cell_background(row=0, color) |
| 줄무늬 | 짝수행 배경 | 행별 borderFill 교체 |

**보고서 템플릿 패턴**:
```python
doc = HwpxBuilder()
doc.add_heading("보고서 제목", level=1)
doc.add_paragraph("2026년 4월 5일", font_size=10, text_color="#888888")
doc.add_paragraph("")

doc.add_table([
    ["항목", "값", "비고"],
    ["데이터1", "100", "정상"],
])
doc.add_paragraph("")

doc.add_heading("1. 개요", level=2)
doc.add_paragraph("본문 내용...")
doc.add_paragraph("")

doc.add_heading("2. 분석", level=2)
doc.add_paragraph("분석 내용...")
doc.add_paragraph("")

doc.add_paragraph("본 문서는 정보 제공 목적으로 작성되었습니다.",
                   font_size=9, text_color="#999999")
doc.save("report.hwpx")
```

**서식(양식) 템플릿 패턴**:
```python
# 1. 원본 서식 hwpx 업로드
# 2. extract_schema()로 필드 탐지
# 3. template_builder.py로 입력 필드 지정 → schema.json 저장
# 4. fill_template_checkbox()로 데이터 채우기
# → 원본 서식의 스타일이 100% 보존됨
```

### Document Type Specifications (문서 유형별 규격)

**유형별 핵심 수치 비교표**:

| 항목 | 정부 양식 | 공문서 | 세무/법무 | 기업 보고서 | 학술 논문 |
|------|-----------|--------|-----------|-------------|-----------|
| **제목 크기** | 18~20pt | 15~16pt | 18~20pt | 22~24pt | 16~18pt |
| **본문 크기** | 11~12pt | 12pt | 12pt | 11pt | 10~11pt |
| **본문 줄간격** | 160% | 160% | 200% | 170% | 170% |
| **상단 여백** | 20mm | 30mm | 30mm | 25mm | 30mm |
| **좌측 여백** | 20mm | 20mm | 30mm | 25mm | 30mm |
| **본문 서체** | 바탕 | 바탕 | 바탕 | 바탕 | 바탕 |
| **제목 서체** | 바탕 | 바탕 | 바탕 | 돋움 | 바탕 |
| **색상 원칙** | 단색+적색 | 단색만 | 단색만 | 다색 허용 | 단색만 |
| **표 스타일** | 전체 테두리 | 전체 테두리 | 전체+강조 | 3선+컬러 | 3선 |
| **첫줄 들여쓰기** | 없음 | 없음 | 없음 | 선택 | 10pt |

**1. 정부 양식** (근로계약서, 신청서):
- 제목 18~20pt Bold 바탕, 가운데 정렬
- 본문 11~12pt, 줄간격 160%
- 여백: 상20 하15 좌20 우20mm
- 표: 실선 0.4mm 검정, 셀 패딩 상하2 좌우3mm
- 색상: 검정만, 필수표시만 적색(#CC0000)

**2. 공문서** (기관 공문, 협조전):
- 「행정업무의 운영 및 관리에 관한 규정」 준거
- 기관명 16pt Bold, 제목 15pt Bold, 본문 12pt
- 여백: 상30 하15 좌20 우15mm
- 검정만 사용, 줄간격 160%

**3. 세무/법무** (소장, 세금계산서):
- 본문 줄간격 **200%** (법원 제출 관행)
- 좌측 여백 **30mm** (편철 공간)
- 항목: `1. → 가. → (1) → (가)` 체계
- 검정만 사용

**4. 기업 보고서** (분석, 제안서):
- 표지 22~24pt Bold 돋움, 장 16~18pt
- 본문 11pt 바탕, 줄간격 170%
- 표: 3선 스타일, 헤더 남색(#2B4C7E) 배경 + 흰색 텍스트
- 다색 허용, 긍정 녹색(#27AE60), 부정 적색(#E74C3C)

**5. 학술 논문** (KCI 기준):
- 제목 16~18pt Bold 바탕, 본문 10~11pt
- 줄간격 170%, 첫줄 들여쓰기 10pt
- 여백: 상30 하25 좌30 우30mm (학위논문 좌 35mm)
- 표: 3선 표(상·헤더하단·하단만 실선), 배경색 없음
- 검정만 사용

**서체 대체 순서**: 함초롬바탕 → 바탕 → 나눔명조 / 함초롬돋움 → 돋움 → 나눔고딕

**색상 팔레트 (Administrative Slate 디자인 시스템)**:

"The Digital Archivist" — 권위적이고 세련된 에디토리얼 톤.
순검정(#000000) 사용 금지. 모든 텍스트는 on-surface(#2b3437) 사용.

| 역할 | 이름 | 코드 | 용도 |
|------|------|------|------|
| **기본** | on-surface | #2b3437 | 본문 텍스트 (순검정 금지!) |
| **보조** | on-surface-variant | #586064 | 메타데이터, 캡션, 날짜 |
| **연한보조** | outline-variant | #abb3b7 | 구분선, 미주 |
| **주 강조** | primary | #395da2 | 표 헤더, 섹션 제목, 악센트 |
| **주 강조 위** | on-primary | #f7f7ff | primary 배경 위 텍스트 |
| **하이라이트** | primary-container | #d8e2ff | 요약 박스, 핵심 정보 배경 |
| **정보** | secondary-container | #cbe7f5 | 상태 칩, 정보 박스 |
| **콜아웃** | tertiary-container | #e2dbfd | 인용, 편집자 주, 참고 |
| **경고** | error | #9f403d | 기한, 경고, 중요 표시 |
| **배경** | surface | #f8f9fa | 페이지 배경 (off-white) |
| **2차 배경** | surface-container-low | #f1f4f6 | 표 교차행, 사이드 영역 |
| **강조 배경** | surface-container-high | #e3e9ec | 강조 배경 |
| **표 헤더** | primary | #395da2 | 표 헤더 배경 + on-primary 텍스트 |
| **표 교차행** | surface-container-low | #f1f4f6 | 짝수행 줄무늬 |

**색상 사용 원칙**:
- 구분선: 테두리 대신 배경색 전환으로 영역 구분 (No-Line Rule)
- 표 헤더: primary(#395da2) 배경 + on-primary(#f7f7ff) 흰색 볼드 텍스트
- 하이라이트: primary-container(#d8e2ff) 연한 라벤더블루 배경
- 콜아웃/인용: tertiary-container(#e2dbfd) 연보라 배경
- 일정/기한: error(#9f403d) 강조
- 단조로운 파란색 일색 금지 — 용도별로 primary/secondary/tertiary/error 구분 사용

### Document Structure Guide (문서 구성 가이드)

**문서 계층 구조**:
```
대제목 (level 1) — 문서 타이틀, 1개만
├── 중제목 (level 2) — 섹션 구분 (1. 개요, 2. 분석, 3. 결론)
│   ├── 소제목 (level 3) — 하위 항목 (1.1, 1.2)
│   │   └── 본문 텍스트 — 일반 단락
│   └── 소제목 (level 3)
│       ├── 본문 텍스트
│       └── 표/그림
├── 중제목 (level 2)
│   └── ...
└── 부록/참고 — 작은 폰트, 회색
```

**제목별 스타일**:

| 구분 | 크기 | 볼드 | 색상 | 정렬 | 줄간격 |
|------|------|------|------|------|--------|
| 대제목 | 24pt | O | on-surface (#2b3437) | CENTER | 200 |
| 중제목 | 18pt | O | on-surface (#2b3437) | LEFT | 160 |
| 소제목 | 16pt | O | primary (#395da2) | LEFT | 160 |
| 본문 | 10pt | X | on-surface (#2b3437) | JUSTIFY | 160 |
| 캡션/표제목 | 10pt | O | on-surface (#2b3437) | LEFT | 130 |
| 메타/날짜 | 9pt | X | on-surface-variant (#586064) | LEFT | 130 |
| 면책/미주 | 8pt | X | outline-variant (#abb3b7) | LEFT | 130 |

**정렬 규칙**:

| 요소 | 정렬 | 이유 |
|------|------|------|
| 대제목 | CENTER | 문서 시각적 중심 |
| 중/소제목 | LEFT | 읽기 흐름 |
| 본문 | JUSTIFY | 한국 공문서 기본 (condense 25% 필요) |
| 표 헤더 | CENTER | 열 제목 강조 |
| 표 데이터 (텍스트) | CENTER | 가독성 |
| 표 데이터 (숫자) | RIGHT | 자릿수 정렬 |
| 날짜/작성자 | RIGHT | 관례 |

**문단 간격 패턴**:
```python
# 제목 뒤 — 빈 줄 1개
doc.add_heading("제목", level=1)
doc.add_paragraph("")

# 섹션 전환 — 빈 줄 1개 또는 구분선
doc.add_paragraph("")
doc.add_heading("다음 섹션", level=2)

# 표 전후 — 빈 줄 1개씩
doc.add_paragraph("")
doc.add_table([...])
doc.add_paragraph("")

# 본문 연속 — 빈 줄 없이 연결
doc.add_paragraph("첫 번째 문단")
doc.add_paragraph("두 번째 문단")

# 문서 끝 주석 — 빈 줄 2개 후
doc.add_paragraph("")
doc.add_paragraph("")
doc.add_paragraph("본 문서는...", font_size=9, text_color="#999999")
```

**구분선 패턴**:
```python
# 가벼운 구분 — 짧은 선
doc.add_paragraph("───────────────", text_color="#CCCCCC")

# 강한 구분 — 전체 너비 선
doc.add_line()

# 섹션 구분 — 빈 줄 + 제목
doc.add_paragraph("")
doc.add_heading("새 섹션", level=2)
```

**들여쓰기 패턴 (paraPr margin)**:

| 구분 | intent 값 | 사용 |
|------|----------|------|
| 기본 | 0 | 일반 본문 |
| 1단 들여쓰기 | -2800 | 조항 번호 뒤 본문 |
| 2단 들여쓰기 | -4880 | 하위 항목 |
| 3단 들여쓰기 | -7680 | 세부 항목 |
| 좌측 여백 | left 4000 | 인용문, 참고 |

**번호 매기기 패턴**:
```
제1조(목적)          ← 조 (condense 25%, intent -2800)
  1. 항목             ← 호 (intent -4880)
    가. 세부항목       ← 목 (intent -7680)
      1) 세부세부      ← 세목
```

**한국 공문서 기본 설정**:
```python
# A4 용지
page_width = 59528    # 210mm
page_height = 84188   # 297mm

# 여백 (한국 공문서 기본)
margin_left = 8504    # 30mm
margin_right = 8504   # 30mm
margin_top = 5668     # 20mm
margin_bottom = 4252  # 15mm

# 기본 폰트
font = "함초롬돋움"    # 한컴 기본
font_size = 10        # pt (height 1000)

# 줄간격
line_spacing = 160    # 160% (한국 공문서 기본)

# 정렬
alignment = "JUSTIFY" # 양쪽 정렬 + condense 25%
```

### Table Design Guide (표 만들기 가이드)

**표 너비 계산 (DXA 아닌 HWPUNIT: 1/7200 inch)**:
```
A4 용지 너비:       59,528
좌우 여백:         -8,504 × 2 = -17,008
─────────────────────────
본문 영역 너비:      42,520   ← 표 최대 너비
```

**열 너비 분배**:
```python
content_width = 42520

# 균등 분할
cols = 3
col_width = content_width // cols  # 14,173

# 비율 분할 (3:2:1)
ratios = [3, 2, 1]
total = sum(ratios)
col_widths = [content_width * r // total for r in ratios]
# → [21260, 14173, 7087]
```

**행 높이**:
| 유형 | height | 사용 |
|------|--------|------|
| 헤더 | 2400 | 표 제목 행 |
| 기본 | 2000 | 일반 데이터 행 |
| 넓음 | 3200 | 여러 줄 텍스트 |
| 좁음 | 1200 | 밀집 데이터 |

**셀 패딩 (cellMargin)**:
```xml
<hp:cellMargin left="283" right="283" top="200" bottom="200" />
```

| 패딩 | left/right | top/bottom | 사용 |
|------|-----------|------------|------|
| 기본 | 283 | 200 | 일반 셀 (여유 있는 패딩 기본) |
| 넓은 여백 | 425 | 283 | 정부 양식, 가독성 |
| 좁은 여백 | 141 | 70 | 밀집 표 |
| 양식 셀 | 510 | 200 | 입력 칸 |

**표 스타일 기본값 (Administrative Slate)**:
- 헤더 행: primary(#395da2) 배경 + on-primary(#f7f7ff) 흰색 볼드 텍스트 + CENTER 정렬
- 데이터 행 (텍스트): CENTER 정렬
- 데이터 행 (숫자): RIGHT 정렬
- 짝수 행: surface-container-low(#f1f4f6) 줄무늬 배경
- 각 표 위에 캡션: `[ 표 N ] 표 제목` (10pt 볼드)

**표에서 사용할 수 있는 강조 패턴**:
- 하이라이트 행: primary-container(#d8e2ff) 배경 — 요약, 합계
- 경고 행: error(#9f403d) 텍스트 — 기한 초과, 위험
- 정보 행: secondary-container(#cbe7f5) 배경 — 참고 정보

**표 마진 (표 바깥 여백)**:
```xml
<hp:outMargin left="0" right="0" top="0" bottom="0" />
<hp:inMargin left="141" right="141" top="141" bottom="141" />
```

| 속성 | 기본값 | 설명 |
|------|--------|------|
| outMargin | 0 | 표 바깥 여백 (본문과의 간격) |
| inMargin | 141 | 표 안쪽 여백 (셀 기본 패딩) |
| 중첩 표 outMargin | 283 | 중첩 표 바깥 여백 |
| 중첩 표 inMargin | 510 | 중첩 표 안쪽 여백 |

**표 테두리 (borderFill)**:
```xml
<!-- borderFill id="1" = 테두리 없음 (기본) -->
<!-- borderFill id="2"+ = 커스텀 테두리 -->
<hh:borderFill id="2" threeD="0" shadow="0">
  <hh:leftBorder type="SOLID" width="0.12 mm" color="#000000" />
  <hh:rightBorder type="SOLID" width="0.12 mm" color="#000000" />
  <hh:topBorder type="SOLID" width="0.12 mm" color="#000000" />
  <hh:bottomBorder type="SOLID" width="0.12 mm" color="#000000" />
</hh:borderFill>
```

| type | 설명 |
|------|------|
| NONE | 테두리 없음 |
| SOLID | 실선 |
| DASH | 점선 |
| DOT | 점 |
| DOUBLE_SLIM | 이중선 |

**셀 병합**:
```xml
<!-- 가로 병합: colSpan -->
<hp:cellSpan colSpan="3" rowSpan="1" />

<!-- 세로 병합: rowSpan -->
<hp:cellSpan colSpan="1" rowSpan="2" />

<!-- 가로+세로 동시 -->
<hp:cellSpan colSpan="2" rowSpan="3" />
```

**셀 수직 정렬 (vertAlign)**:
```xml
<hp:subList vertAlign="CENTER">  <!-- TOP, CENTER, BOTTOM -->
```

**셀 배경색**:
```python
# pyhwpxlib API
table.set_cell_background(row, col, "#D5E8F0")

# XML 직접
# borderFill에 winBrush 추가
```

**add_table 기본값과 권장값**:

| 파라미터 | 기본값 | 권장값 | 단위 |
|----------|--------|--------|------|
| `width` | 42520 | 42520 (전체너비) | HWPUNIT |
| `col_widths` | 균등분할 | 내용에 맞게 | HWPUNIT 리스트 |
| `row_heights` | 프리셋 자동 | 헤더 2400, 데이터 2000 | HWPUNIT 리스트 |
| `cell_margin` | 프리셋 자동 | (283,283,200,200) | (L,R,T,B) |
| `header_bg` | 프리셋 자동 | #395da2 (primary) | 헤더 배경색 |
| `cell_aligns` | 프리셋 자동 | 헤더 CENTER, 텍스트 CENTER, 숫자 RIGHT | 정렬 |
| `cell_styles` | 프리셋 자동 | 헤더 {text_color: #f7f7ff, bold: True} | 글자 스타일 |
| `cell_colors` | 프리셋 자동 | 짝수행 #f1f4f6 줄무늬 | 배경색 |

**프리셋**: `HwpxBuilder(table_preset='corporate')` 사용 시 위 값들이 자동 적용됨.
명시적으로 파라미터를 넘기면 프리셋보다 우선.

**표 생성 실전 예시**:
```python
# 기본 — 자동 균등 분할
doc.add_table([["A","B","C"],["1","2","3"]])
# → width=42520, 3열 균등(14173씩), 높이 3600

# 열 너비 지정 (합 = width)
add_table(doc, 2, 3, data=[...],
          col_widths=[21260, 14173, 7087])  # 5:3:2 비율

# 행 높이 지정
add_table(doc, 3, 2, data=[...],
          row_heights=[1500, 1200, 1200])  # 헤더 높고 데이터 낮게

# 셀 패딩 지정
add_table(doc, 2, 2, data=[...],
          cell_margin=(200, 200, 100, 100))  # 여유있는 패딩

# 셀 배경색
add_table(doc, 2, 2, data=[...],
          cell_colors={(0,0): "#D5E8F0", (0,1): "#D5E8F0"})  # 헤더행 배경
```

**크기 환산표**:

| 실제 크기 | HWPUNIT | 용도 |
|----------|---------|------|
| 5mm | 1417 | 최소 셀 패딩 |
| 10mm | 2835 | 일반 셀 높이 |
| 15mm | 4252 | 헤더 셀 높이 |
| 30mm | 8504 | 여백 |
| 50mm | 14173 | 좁은 열 |
| 75mm | 21260 | 반 너비 열 |
| 150mm | 42520 | 전체 너비 |

**표 유형별 템플릿**:

```python
# 1. 데이터 표 (헤더 + 데이터)
doc.add_table([
    ["항목", "수량", "금액"],     # 헤더 (볼드, 배경색)
    ["제품A", "100", "50,000"],
    ["제품B", "200", "80,000"],
    ["합계", "300", "130,000"],
])

# 2. 키-값 표 (라벨 + 입력칸)
doc.add_table([
    ["성 명", ""],
    ["주민등록번호", ""],
    ["주 소", ""],
])

# 3. 카드 레이아웃 (가로 나열)
doc.add_table([
    ["현재가", "목표가", "상승여력"],
    ["$184.86", "$250", "+35%"],
])

# 4. 비교 표
doc.add_table([
    ["구분", "항목A", "항목B", "차이"],
    ["성능", "100", "150", "+50%"],
    ["가격", "1,000", "1,200", "+20%"],
])
```

### Design Components (디자인 컴포넌트 가이드)

문서 작성 시 아래 컴포넌트를 상황에 맞게 조합합니다.
디자인 레퍼런스: `skill/stitch/` 폴더의 hwpx_1~5 스크린샷 참조.

**구분선**: 테두리 표 대신 텍스트 구분선 사용
```python
doc.add_paragraph('━' * 50, font_size=6, text_color='#abb3b7')
```

**섹션 제목**: 표/박스 없이 텍스트로
```python
doc.add_paragraph('섹션 제목', bold=True, font_size=13, text_color='#395da2')
```

**하이라이트 박스**: primary-container 배경 표
```python
doc.add_table([['핵심 요약 내용']],
    cell_colors={(0,0): '#d8e2ff'},
    cell_margin=(400,400,300,300), header_bg='',
    cell_styles={(0,0): {'text_color': '#2a5094'}},
    use_preset=False)
```

**콜아웃/인용 박스**: tertiary-container 배경
```python
doc.add_table([['인용문 또는 편집자 주']],
    cell_colors={(0,0): '#e2dbfd'},
    cell_margin=(400,400,300,300), header_bg='',
    cell_styles={(0,0): {'text_color': '#514d68'}},
    use_preset=False)
```

**정보 박스**: secondary-container 배경
```python
doc.add_table([['참고 정보']],
    cell_colors={(0,0): '#cbe7f5'},
    cell_margin=(400,400,300,300), header_bg='',
    cell_styles={(0,0): {'text_color': '#3c5561'}},
    use_preset=False)
```

**문서 유형별 컴포넌트 조합 (stitch 레퍼런스)**:

| 유형 | 핵심 컴포넌트 | stitch 참조 |
|------|-------------|------------|
| 기안서/기획안 | 번호(01,02,03) + 들여쓰기 본문 + 하이라이트 박스 | hwpx_1 |
| 회의록 | 메타 그리드(표) + 안건 테이블 + 콜아웃 박스 | hwpx_2 |
| 사업 보고서 | 표지 + 요약 표 + 섹션별 표/통계 | hwpx_3 |
| 공문서 | 수신/참조/제목(표) + 가.나. 계층 들여쓰기 + 구분선 | hwpx_4 |
| 안내문/협조문 | 히어로 박스(primary-container) + 과제 목록 + 일정 표 | hwpx_5 |

### Indent Guide (들여쓰기 상세)

**intent vs left margin 차이**:
```
intent (들여쓰기):  첫 줄만 들여쓰기 (음수 = 내어쓰기)
left (좌측 여백):   전체 단락 좌측 이동

예시: intent=-2800, left=2800
  ↓ intent (첫 줄 내어쓰기)
제1조(목적) 이 규정은 환경기술 및 환경산업
  ↓ left (2째줄부터 들여쓰기)
       지원법 제10조에 따른 센터의 설립
       및 운영에 관한 사항을 규정함을
       목적으로 한다.
```

**공문서 들여쓰기 체계**:
```python
# 단계별 intent + left 조합
styles = {
    "조": {"intent": -2800, "left": 2800},   # 제1조(목적)
    "호": {"intent": -4880, "left": 4880},   # 1. 항목
    "목": {"intent": -7680, "left": 7680},   # 가. 세부
    "세목": {"intent": -9080, "left": 9080}, # 1) 세부세부
}
```

### Table of Contents in Document (문서 내 목차)

HWPX에서 목차는 자동 생성이 아닌 **수동 구성**으로 만듭니다.
제목(heading)을 기반으로 목차 텍스트를 직접 생성합니다.

**목차 생성 패턴**:
```python
doc = HwpxBuilder()

# 목차 페이지
doc.add_heading("목 차", level=1)
doc.add_paragraph("")
doc.add_paragraph("1. 개요 ························· 2", font_size=11)
doc.add_paragraph("2. 현황 분석 ··················· 5", font_size=11)
doc.add_paragraph("  2.1 시장 동향 ··············· 5", font_size=10)
doc.add_paragraph("  2.2 경쟁사 분석 ············· 8", font_size=10)
doc.add_paragraph("3. 결론 ························· 12", font_size=11)
doc.add_paragraph("")

# 본문 시작
doc.add_heading("1. 개요", level=2)
doc.add_paragraph("본문 내용...")
```

**목차 자동 생성 헬퍼**:
```python
def generate_toc(sections, dot_char="·"):
    """섹션 목록에서 목차 텍스트 생성
    sections = [("1. 개요", 2), ("2. 분석", 5), ("  2.1 세부", 6)]
    """
    lines = []
    for title, page in sections:
        indent = len(title) - len(title.lstrip())
        dots = dot_char * (40 - len(title) - len(str(page)))
        lines.append(f"{title} {dots} {page}")
    return lines
```

**목차 스타일**:
| 요소 | 폰트 | 정렬 |
|------|------|------|
| "목 차" 제목 | 20pt 볼드 CENTER | 가운데 |
| 1단계 항목 | 11pt LEFT | 왼쪽 |
| 2단계 항목 | 10pt LEFT (들여쓰기 2칸) | 왼쪽 |
| 3단계 항목 | 9pt LEFT (들여쓰기 4칸) | 왼쪽 |
| 점선 | · 반복 | 제목과 페이지 번호 연결 |
| 페이지 번호 | 우측 정렬 | 오른쪽 끝 |

**표지 페이지 (Cover Page)**:

표지는 문서의 첫 페이지로, 제목/부제/작성자/날짜/기관명을 세로 가운데 배치.
본문과 분리하기 위해 표지 끝에 페이지 구분이 필요합니다.

```python
doc = HwpxBuilder()

# ── 표지 ──
doc.add_paragraph("")   # 상단 여백
doc.add_paragraph("")
doc.add_paragraph("")
doc.add_paragraph("")
doc.add_paragraph("")

doc.add_heading("2026년도", level=2)
doc.add_paragraph("")

doc.add_paragraph("엔비디아 투자 분석 보고서", bold=True, font_size=24,
                   alignment="CENTER")
doc.add_paragraph("")
doc.add_paragraph("")

doc.add_paragraph("NVDA (NVIDIA Corporation)", font_size=14,
                   text_color="#76b900", alignment="CENTER")
doc.add_paragraph("")
doc.add_paragraph("")
doc.add_paragraph("")

doc.add_paragraph("2026년 4월 5일", font_size=12,
                   text_color="#888888", alignment="CENTER")
doc.add_paragraph("")

doc.add_paragraph("작성자: 홍길동", font_size=11, alignment="CENTER")
doc.add_paragraph("미국주식 투자 블로그", font_size=10,
                   text_color="#888888", alignment="CENTER")

# 표지 하단 — 기관/회사 로고 위치
doc.add_paragraph("")
doc.add_paragraph("")
doc.add_paragraph("")
doc.add_line()
doc.add_paragraph("Confidential", font_size=8,
                   text_color="#CCCCCC", alignment="CENTER")
```

**표지 스타일 규칙**:

| 요소 | 폰트 크기 | 정렬 | 색상 |
|------|----------|------|------|
| 연도/카테고리 | 16pt | CENTER | #333333 |
| **대제목** | **24pt 볼드** | **CENTER** | **#000000** |
| 부제목 | 14pt | CENTER | 브랜드색 |
| 날짜 | 12pt | CENTER | #888888 |
| 작성자 | 11pt | CENTER | #333333 |
| 기관명 | 10pt | CENTER | #888888 |
| 기밀 표시 | 8pt | CENTER | #CCCCCC |

**표지 유형별 패턴**:

```python
# 1. 공문서 표지
doc.add_paragraph("대외비", font_size=14, bold=True, text_color="#E74C3C",
                   alignment="CENTER")
doc.add_paragraph("")
doc.add_heading("녹색환경지원센터 설립·운영에 관한 규정", level=1)
doc.add_paragraph("")
doc.add_paragraph("환경부", font_size=16, bold=True, alignment="CENTER")

# 2. 보고서 표지
doc.add_paragraph("[ 분석 보고서 ]", font_size=12, text_color="#888888",
                   alignment="CENTER")
doc.add_heading("AI 반도체 시장 동향", level=1)
doc.add_paragraph("2026년 1분기", font_size=14, alignment="CENTER")

# 3. 제안서 표지
doc.add_heading("제 안 요 청 서", level=1)
doc.add_paragraph("")
doc.add_table([
    ["사업명", "2026년 AI 인프라 구축 사업"],
    ["주관기관", "한국정보원"],
    ["제출일", "2026년 4월 5일"],
])
```

**전체 문서 구성 순서**:
```python
doc = HwpxBuilder()

# 1. 표지 (1페이지 전체 사용)
# ... (위 표지 코드) ...
# 페이지 넘김 (빈 줄로 채우거나 pageBreak 속성)

# 2. 목차
doc.add_heading("목 차", level=1)
doc.add_paragraph("1. 개요 ························· 2", font_size=11)
doc.add_paragraph("2. 분석 ························· 4", font_size=11)
doc.add_paragraph("3. 결론 ························· 8", font_size=11)
doc.add_paragraph("")

# 3. 본문
doc.add_heading("1. 개요", level=2)
doc.add_paragraph("본문...")
doc.add_paragraph("")

doc.add_heading("2. 분석", level=2)
doc.add_heading("2.1 시장 동향", level=3)
doc.add_paragraph("분석 내용...")
doc.add_paragraph("")

doc.add_heading("3. 결론", level=2)
doc.add_paragraph("결론 내용...")
doc.add_paragraph("")

# 4. 부록/참고
doc.add_line()
doc.add_paragraph("참고 문헌", bold=True, font_size=11)
doc.add_paragraph("1. 출처1", font_size=9, text_color="#666666")
doc.add_paragraph("2. 출처2", font_size=9, text_color="#666666")
doc.add_paragraph("")

# 5. 면책 조항
doc.add_paragraph("본 문서는 정보 제공 목적으로 작성되었습니다.",
                   font_size=8, text_color="#999999")

doc.save("report.hwpx")
```

### Lists (글머리 기호 / 번호 목록)

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

**주의**: 유니코드 bullet 문자(•, ▪) 직접 사용 금지. 반드시 `add_bullet_list` API 사용.

### Images (이미지 삽입)

**HwpxBuilder API (권장)**:
```python
doc = HwpxBuilder()

# 로컬 이미지 삽입
doc.add_image("photo.png", width=21260, height=15000)

# URL에서 다운로드 후 삽입
doc.add_image_from_url(
    "https://example.com/image.png",
    filename="my_image.png",   # 저장 파일명 (생략 시 URL에서 추출)
    width=21260,               # 표시 너비 (HWPX 단위)
    height=15000,              # 표시 높이
)
# → /tmp/hwpx_images/ 에 자동 다운로드 후 문서에 삽입
```

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

### Page Breaks (페이지 나누기)

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

### Headers and Footers (머리말 / 꼬리말)

```python
from pyhwpxlib.api import add_header, add_footer, add_page_number

# 머리말
add_header(doc, "보고서 제목 — 기밀")

# 꼬리말
add_footer(doc, "© 2026 회사명")

# 페이지 번호
add_page_number(doc)
```

### Footnotes (각주)

```python
from pyhwpxlib.api import add_footnote

# 본문에 각주 삽입
add_footnote(doc, "각주 내용: 출처 정보")
```

### Hyperlinks (하이퍼링크)

```python
from pyhwpxlib.api import add_hyperlink

add_hyperlink(doc, "네이버", "https://www.naver.com")
```

**주의**: Whale에서 fieldBegin/fieldEnd 렌더링 에러 발생 가능 (룰북 규칙 28).
HTML→HWPX 변환 시 `strip_links=True`로 링크 자동 제거 권장.

### Equations (수식)

```python
from pyhwpxlib.api import add_equation

add_equation(doc, "x = {-b +- sqrt {b^2 - 4ac}} over {2a}")
```

### Shapes (도형)

```python
from pyhwpxlib.api import add_rectangle, add_ellipse, add_line

# 사각형
add_rectangle(doc, width=14000, height=7000)

# 타원
add_ellipse(doc, width=14000, height=7000)

# 직선
add_line(doc, x1=0, y1=0, x2=42520, y2=0,
         line_color="#76b900", line_width=283)
```

### Multi-Column (다단)

```python
from pyhwpxlib.api import set_columns

# 2단 레이아웃
set_columns(doc, count=2, spacing=1134)
```

### Converting to Images (이미지 변환)

```bash
# HWPX → PDF (한컴오피스 필요)
# → PDF → 이미지 (pdftoppm)
# 현재 자동화 미지원 — 한컴오피스 수동 변환 또는 LibreOffice 사용

# LibreOffice로 PDF 변환 (실험적)
# libreoffice --headless --convert-to pdf document.hwpx
```

### Critical Rules for HwpxBuilder

- **pyhwpxlib 기반** — header.xml은 pyhwpxlib가 생성, section만 HwpxBuilder가 구성
- **줄바꿈 금지** — `<hp:t>` 안에 `\n` 넣으면 Whale 에러. 별도 `<hp:p>`로 분리
- **mimetype STORED** — ZIP의 mimetype 엔트리는 압축 없이(STORED) 첫 번째로
- **ET.tostring 금지** — XML 재직렬화 시 네임스페이스 변경으로 Whale 에러. 원본 문자열 직접 교체

---

## Editing Existing Documents

**Follow all 3 steps in order.**

### Step 1: Unpack
```bash
python scripts/unpack.py document.hwpx unpacked/
```
Extracts all XML files to a folder.

### Step 2: Edit XML

Edit files in `unpacked/Contents/`. See XML Reference below for patterns.

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

### Step 3: Pack
```bash
python scripts/pack.py unpacked/ output.hwpx
```
Creates HWPX with mimetype STORED as first entry.

### Validation
```bash
python scripts/validate.py output.hwpx
```
Checks: ZIP validity, required files, mimetype, XML parsing, namespaces.

---

## Form Automation

### Fill Template (텍스트 교체 방식 — 서식 100% 보존)

```python
from pyhwpxlib.api import fill_template_checkbox

fill_template_checkbox(
    "template.hwpx",
    data={
        ">성 명<": ">성 명  홍길동<",
        ">사업체명<": ">사업체명  (주)블루오션<",
    },
    checks=["민간기업"],    # [  ] → [√] 또는 □ → ■
    output_path="filled.hwpx",
)
```

### Batch Generate (다건 생성)

```python
from pyhwpxlib.api import fill_template_batch

records = [
    {"data": {">성 명<": ">성 명  홍길동<"}, "checks": ["민간기업"], "filename": "홍길동"},
    {"data": {">성 명<": ">성 명  김영수<"}, "checks": ["공공기관(공기업)"], "filename": "김영수"},
]
fill_template_batch("template.hwpx", records, output_dir="output/")
```

### Schema Extraction (필드 자동 탐지)

```python
from pyhwpxlib.api import extract_schema, analyze_schema_with_llm

schema = extract_schema("template.hwpx")
analyzed = analyze_schema_with_llm(schema)
# analyzed['input_fields'] — 사용자 입력 필드
# analyzed['fixed_fields'] — 고정 텍스트
# analyzed['checkboxes'] — 체크박스
```

### Template Builder UI

```bash
python template_builder.py template.hwpx --port 8081
# 브라우저에서 필드 입력/고정/제목 토글 → schema.json 저장
```

### Checkbox Patterns

**주의: 체크박스에 2가지 형태가 있음**
- `[  ]` 패턴 — data로 직접 교체 (checks 파라미터 미지원)
- `□` 패턴 — checks 파라미터 사용

```python
# [  ] → [√] 패턴 — data로 직접 교체해야 함
data = {"공공기관(공기업) [  ]": "공공기관(공기업) [√]"}

# □ → ■ 패턴 — checks 파라미터 사용
checks = ["__ALL__"]  # 전체 □ → ■
checks = ["민간기업"]  # 해당 라벨 뒤 □만 ■로

# 혼합 사용 예시
fill_template_checkbox(
    "template.hwpx",
    data={
        ">성 명<": ">성 명  홍길동<",
        "민간기업 [  ]": "민간기업 [√]",      # [  ] → [√]
    },
    checks=["동의함"],                         # □ → ■
    output_path="filled.hwpx",
)
```

### Critical Rules for Form Automation

- **원본 ZIP 복사 + XML 텍스트 교체** — pyhwpxlib 재생성 금지 (header 깨짐)
- **`.replace(old, new, 1)`** — 첫 번째만 교체 (다른 페이지 보호)
- **condense/styleIDRef/breakSetting** — 원본 paraPr을 건드리면 JUSTIFY 글자 벌어짐
- **ET.tostring 금지** — 반드시 원본 문자열 직접 교체

---

## Converting Documents

### Markdown → HWPX
```bash
python -m pyhwpxlib.cli md2hwpx input.md -o output.hwpx -s github
```
Styles: `github`, `vscode`, `minimal`, `academic`

**md2hwpx 표 스타일 (자동 적용)**:
- 헤더 행: 배경색 + 볼드 + CENTER 정렬
- 데이터 행 (텍스트): CENTER 정렬
- 데이터 행 (숫자): RIGHT 자동 판별
- 행 높이: 헤더 2400, 데이터 2000
- 셀 패딩: 스타일별 설정값 (github 기본 975/450)

**md 파일 → HWPX 변환 방법 2가지**:

| 방법 | 장점 | 단점 | 사용 시점 |
|------|------|------|----------|
| `md2hwpx` CLI | 빠름, 일관됨 | 단순 규칙 변환, 디자인 제한 | 단순 변환, 대량 처리 |
| LLM + HwpxBuilder | 문맥 이해, 디자인 적용 가능 | 느림 | 디자인 중요한 문서 |

**LLM이 md를 HwpxBuilder로 변환할 때 원칙**:
- 원문 텍스트를 그대로 사용한다 — 요약·재작성·생략 금지
- md의 구조(제목 계층, 표, 인용 등)를 보존한다
- 스타일링은 LLM이 주도적으로 판단하여 적용한다 (색상, 박스, 정렬 등)
  - 인용문 `>` → 콜아웃 박스(#e2dbfd) 가능
  - 핵심 문장 → 하이라이트 박스(#d8e2ff) 가능
  - 표 숫자 → RIGHT 정렬 자동 적용
- 문서 유형에 맞지 않는 양식을 억지로 씌우지 않는다
  - 리서치 분석문에 "EQUITY RESEARCH" 표지를 붙이지 않음
  - 원문의 성격(학술/분석/보고서/안내문)에 맞는 스타일 적용

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
| 12 | header/footer/page_number는 SecPr 뒤에 삽입 | HwpxBuilder가 자동 처리 (deferred) |
| 9 | 원문 텍스트 보존 — 요약·재작성·생략 금지 | 원문 왜곡 방지 |
| 10 | 원문 성격에 맞지 않는 양식 강제 금지 | 리서치문에 기업보고서 표지 등 |
| 11 | LLM은 스타일링은 자유롭게, 내용은 충실하게 | 디자인은 판단, 텍스트는 보존 |

---

## Dependencies

- **olefile**: HWP 5.x binary reading (`pip install olefile`)
- **pyhwpxlib**: HWPX document API (bundled)
- **python-hwpx**: HWPX dataclass library (bundled at `ratiertm-hwpx/`)
