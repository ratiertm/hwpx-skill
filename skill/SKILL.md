---
name: hwpx
description: "Use this skill whenever the user wants to create, read, edit, or manipulate Hangul/Korean word processor documents (.hwpx, .hwp, .owpml files). Triggers include: any mention of 'hwpx', 'hwp', '한글 파일', '한글 문서', '한컴', 'OWPML', or requests to produce Korean government forms, fill templates, clone forms, or convert documents. Also use when converting HWP to HWPX (hwp2hwpx), extracting text from .hwpx files, filling form fields, checking/unchecking boxes, generating multiple filled documents, or converting HTML/Markdown to .hwpx format. If the user asks for a Korean document, government form, template automation, or HWP file conversion, use this skill. Do NOT use for .docx Word documents, PDFs, or spreadsheets."
---

# HWPX creation, editing, and form automation

## Table of Contents

1. [Document Design Principles](#document-design-principles)
2. [Confirmed Style Rules](#confirmed-style-rules)
3. [Quick Reference](#quick-reference)
4. [Interactive Workflow](#interactive-workflow)
5. [Creating New Documents — HwpxBuilder API](#creating-new-documents)
6. [Editing Existing Documents](#editing-existing-documents)
7. [Converting Documents](#converting-documents)
8. [Critical Rules Summary](#critical-rules-summary)
9. [Dependencies](#dependencies)
10. [Reference Files](#reference-files)

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

---

## Confirmed Style Rules (확정된 스타일 규칙 — 세션 테스트 완료)

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

**색상 사용 원칙**:
- 구분선: 테두리 대신 배경색 전환으로 영역 구분 (No-Line Rule)
- 표 헤더: primary(#395da2) 배경 + on-primary(#f7f7ff) 흰색 볼드 텍스트
- 하이라이트: primary-container(#d8e2ff) 연한 라벤더블루 배경
- 콜아웃/인용: tertiary-container(#e2dbfd) 연보라 배경
- 일정/기한: error(#9f403d) 강조
- 단조로운 파란색 일색 금지 — 용도별로 primary/secondary/tertiary/error 구분 사용

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
→ 유형별 상세 규격: [references/document_types.md](references/document_types.md)

### Step 2: 양식/템플릿 선택

```
"어떤 양식을 사용하시겠어요?"

1. 기본 템플릿으로 새로 만들기 — HwpxBuilder로 생성
2. 기존 hwpx 파일 업로드 — 텍스트 교체 방식 (서식 100% 보존)
3. 샘플에서 선택 — 미리 만든 양식 중 선택
```

→ 2번 선택 시: 파일 경로 입력 → extract_schema → 필드 분류
→ 폼 자동화 상세: [references/form_automation.md](references/form_automation.md)

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
→ 다건 생성 시 배열로: `[{...}, {...}, ...]`

**방식 C: 파일 참조**
```
"데이터 파일 경로를 알려주세요:"
→ CSV: data.csv (헤더행 = 필드명)
→ JSON: data.json
→ Excel → CSV 변환 후 사용
```

### Step 4~5: 생성 및 수정

파일명 지정 → hwpx 생성 → Whale/한컴오피스로 열기 → 수정 반복.

---

## Creating New Documents

Generate .hwpx files with `HwpxBuilder`, then validate.

### Setup
```python
from scripts.create import HwpxBuilder, DS, TABLE_PRESETS

doc = HwpxBuilder(table_preset='corporate')
doc.add_heading("제목", level=1)
doc.add_paragraph("본문 텍스트")
doc.add_table([["A", "B"], ["1", "2"]])
doc.save("output.hwpx")
```

### Validation
```bash
python scripts/validate.py output.hwpx
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

### Critical Rules for HwpxBuilder

- **pyhwpxlib 기반** — header.xml은 pyhwpxlib가 생성, section만 HwpxBuilder가 구성
- **줄바꿈 금지** — `<hp:t>` 안에 `\n` 넣으면 Whale 에러. 별도 `<hp:p>`로 분리
- **mimetype STORED** — ZIP의 mimetype 엔트리는 압축 없이(STORED) 첫 번째로
- **ET.tostring 금지** — XML 재직렬화 시 네임스페이스 변경으로 Whale 에러. 원본 문자열 직접 교체

> For full pyhwpxlib API (lists, shapes, equations, headers/footers, etc.) → see [references/api_full.md](references/api_full.md)

---

## Editing Existing Documents

**Follow all 3 steps in order.**

### Step 1: Unpack
```bash
python scripts/unpack.py document.hwpx unpacked/
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
python scripts/pack.py unpacked/ output.hwpx
```
Creates HWPX with mimetype STORED as first entry.

### Validation
```bash
python scripts/validate.py output.hwpx
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

## Dependencies

- **olefile**: HWP 5.x binary reading (`pip install olefile`)
- **pyhwpxlib**: HWPX document API (bundled)

---

## Skill Update (스킬 동기화)

프로젝트 `skill/`과 설치된 `~/.claude/skills/hwpx/` 간 동기화:

```bash
# 상태 확인 — 어디가 다른지 보기
python scripts/update_skill.py status

# Push — 프로젝트 → 설치된 스킬
python scripts/update_skill.py push

# Pull — 설치된 스킬 → 프로젝트
python scripts/update_skill.py pull

# Backup — 현재 설치된 스킬 스냅샷
python scripts/update_skill.py backup
```

---

## Reference Files

| File | Contents |
|------|----------|
| [references/api_full.md](references/api_full.md) | pyhwpxlib full function reference, XML reference, page sizes, size conversion table |
| [references/document_types.md](references/document_types.md) | Document type specs (5 types), indent guide, TOC patterns, cover page patterns, document structure guide, table design guide |
| [references/form_automation.md](references/form_automation.md) | fill_template, batch generate, schema extraction, checkbox patterns, advanced XML editing |
