---
name: hwpx
description: "Use this skill whenever the user wants to create, read, edit, or manipulate Hangul/Korean word processor documents (.hwpx, .hwp, .owpml files). Triggers include: any mention of 'hwpx', 'hwp', '한글 파일', '한글 문서', '한컴', 'OWPML', or requests to produce Korean government forms, fill templates, clone forms, or convert documents. Also use when extracting text from .hwpx files, filling form fields, checking/unchecking boxes, generating multiple filled documents, or converting HTML/Markdown to .hwpx format. If the user asks for a Korean document, government form, or template automation, use this skill. Do NOT use for .docx Word documents, PDFs, or spreadsheets."
---

# HWPX creation, editing, and form automation

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
