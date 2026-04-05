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

### HwpxBuilder API

```python
doc = HwpxBuilder()

# 제목 (level 1~4)
doc.add_heading("제목", level=1)      # 20pt 볼드
doc.add_heading("소제목", level=2)    # 16pt 볼드

# 일반 단락
doc.add_paragraph("본문 텍스트")
doc.add_paragraph("")  # 빈 줄 (간격용)

# 스타일 단락
doc.add_paragraph("강조 텍스트", bold=True, text_color="#FF0000")
doc.add_paragraph("작은 텍스트", font_size=9, text_color="#888888")

# 표
doc.add_table([
    ["헤더1", "헤더2", "헤더3"],
    ["값1", "값2", "값3"],
])

# 구분선
doc.add_line()

# 저장
doc.save("output.hwpx")
```

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

**색상 팔레트 (한국 공문서 스타일)**:

| 용도 | 색상 | 코드 |
|------|------|------|
| 본문 | 검정 | #000000 |
| 부제목/날짜 | 회색 | #888888 |
| 강조 (긍정) | 녹색 | #2E7D32 |
| 강조 (경고) | 빨강 | #E74C3C |
| 링크/참조 | 파랑 | #1565C0 |
| 주석/미주 | 연회색 | #999999 |
| 표 헤더 배경 | 연파랑 | #D5E8F0 |
| 표 교차행 배경 | 연회색 | #F5F5F5 |

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

| 구분 | 폰트 크기 | 볼드 | 정렬 | 줄간격 | 상하 간격 |
|------|----------|------|------|--------|----------|
| 대제목 | 20pt | O | CENTER | 200 | 위 400, 아래 200 |
| 중제목 | 16pt | O | LEFT | 160 | 위 300, 아래 150 |
| 소제목 | 14pt | O | LEFT | 160 | 위 200, 아래 100 |
| 본문 | 10pt | X | JUSTIFY | 160 | 위 0, 아래 0 |
| 캡션 | 9pt | X | CENTER | 130 | 위 50, 아래 100 |
| 주석 | 9pt | X | LEFT | 130 | 위 0, 아래 0 |
| 꼬리말 | 8pt | X | LEFT | 130 | - |

**정렬 규칙**:

| 요소 | 정렬 | 이유 |
|------|------|------|
| 대제목 | CENTER | 문서 시각적 중심 |
| 중/소제목 | LEFT | 읽기 흐름 |
| 본문 | JUSTIFY | 한국 공문서 기본 (condense 25% 필요) |
| 표 헤더 | CENTER | 열 제목 강조 |
| 표 데이터 (텍스트) | LEFT | 가독성 |
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
| 기본 | 1200 | 일반 데이터 행 |
| 헤더 | 1500 | 표 제목 행 |
| 넓음 | 2000 | 여러 줄 텍스트 |
| 좁음 | 800 | 밀집 데이터 |

**셀 패딩 (cellMargin)**:
```xml
<hp:cellMargin left="141" right="141" top="0" bottom="0" />
```

| 패딩 | left/right | top/bottom | 사용 |
|------|-----------|------------|------|
| 기본 | 141 | 0 | 일반 셀 |
| 넓은 여백 | 283 | 141 | 제목 셀, 가독성 |
| 좁은 여백 | 70 | 0 | 밀집 표 |
| 양식 셀 | 510 | 141 | 입력 칸 (넓은 여백) |

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

```python
from pyhwpxlib.api import add_image

# 파일에서 이미지 삽입
add_image(doc, "photo.png", width=20000, height=15000)
# width/height: HWPUNIT (1/7200 inch)
# 20000 ≈ 70mm, 15000 ≈ 53mm

# 크기 변환 참고
# mm → HWPUNIT: mm * 283.46
# inch → HWPUNIT: inch * 7200
# px (96dpi) → HWPUNIT: px * 75
```

**이미지 크기 가이드**:

| 용도 | width | height | 비고 |
|------|-------|--------|------|
| 전체 너비 | 42520 | 비율 자동 | 본문 영역 전체 |
| 반 너비 | 21260 | 비율 자동 | 2단 배치용 |
| 증명사진 | 8504 | 11339 | 3×4cm |
| 썸네일 | 7087 | 7087 | 25×25mm |

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

```python
# [  ] → [√] 패턴
data = {"민간기업 [  ]": "민간기업 [√]"}

# □ → ■ 패턴 (checks 파라미터 사용)
checks = ["__ALL__"]  # 전체 □ → ■
checks = ["민간기업"]  # 해당 라벨 뒤 □만 ■로
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

---

## Dependencies

- **olefile**: HWP 5.x binary reading (`pip install olefile`)
- **pyhwpxlib**: HWPX document API (bundled)
- **python-hwpx**: HWPX dataclass library (bundled at `ratiertm-hwpx/`)
