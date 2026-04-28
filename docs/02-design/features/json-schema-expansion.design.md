---
template: design
version: 1.2
description: HwpxJsonDocument 16개 풍부 type + decoder dispatch 매핑 설계
---

# json-schema-expansion Design Document

> **Summary**: `RunContent.type` 을 13개 신규 type 으로 확장하고 top-level 에 deferred 3종(header/footer/page_number) 을 둔다. `decoder.from_json` 은 dispatch table 로 16개 builder 메서드를 매핑한다. 모든 추가는 optional, v0.14.0 JSON 입력 그대로 동작 (back-compat).
>
> **Project**: pyhwpxlib
> **Version**: 0.14.0 → 0.15.0
> **Date**: 2026-04-29
> **Status**: Draft
> **Planning Doc**: [json-schema-expansion.plan.md](../../01-plan/features/json-schema-expansion.plan.md)

---

## 1. Overview

### 1.1 Design Goals

- builder 19개 add_* 메서드 모두 JSON 한 덩어리로 도달 가능
- v0.14.0 input back-compat (paragraphs/tables-only JSON 그대로 동작)
- rhwp-strict-mode 일관 — 알 수 없는 type 은 silent skip 금지, ValueError
- Whale SecPr 버그 회피 — header/footer/page_number 는 deferred (builder 패턴 동일)

### 1.2 Design Principles

- **Discriminated union**: `RunContent.type` 문자열 enum + 각 type 별 nested dataclass
- **Optional 필드 우선**: 모든 신규 필드 default — 외부 LLM 이 minimal JSON 작성 가능
- **1:1 매핑**: dataclass → builder kwargs 변환 최소화 (LLM 친화)

### 1.3 builder 메서드 ↔ JSON type 대응 (전체 19개)

| # | builder | JSON type | 위치 |
|---|---------|-----------|------|
| 1 | `add_paragraph` | `text` (기존) | RunContent |
| 2 | `add_table` | `table` (기존) | RunContent |
| 3 | `add_page_break` | `page_break: bool` (기존) | Paragraph |
| 4 | `add_heading` | `heading` | RunContent (신규) |
| 5 | `add_image` | `image` (path) | RunContent (신규) |
| 6 | `add_image_from_url` | `image` (url) | RunContent (신규) |
| 7 | `add_line` | `shape_line` | RunContent (신규) |
| 8 | `add_bullet_list` | `bullet_list` | RunContent (신규) |
| 9 | `add_numbered_list` | `numbered_list` | RunContent (신규) |
| 10 | `add_nested_bullet_list` | `nested_bullet_list` | RunContent (신규) |
| 11 | `add_nested_numbered_list` | `nested_numbered_list` | RunContent (신규) |
| 12 | `add_header` | `header` | top-level deferred (신규) |
| 13 | `add_footer` | `footer` | top-level deferred (신규) |
| 14 | `add_page_number` | `page_number` | top-level deferred (신규) |
| 15 | `add_footnote` | `footnote` | RunContent (신규) |
| 16 | `add_equation` | `equation` | RunContent (신규) |
| 17 | `add_highlight` | `highlight` | RunContent (신규) |
| 18 | `add_rectangle` | `shape_rect` | RunContent (신규) |
| 19 | `add_draw_line` | `shape_draw_line` | RunContent (신규) |

---

## 2. Architecture

### 2.1 Module Layout

```
pyhwpxlib/json_io/
├── schema.py
│   ├── (기존) HwpxJsonDocument, Section, Paragraph, Run, RunContent, Table, ...
│   └── (신규) Heading, Image, BulletList, NumberedList, NestedListItem,
│              Footnote, Equation, Highlight, Shape, HeaderFooter, PageNumber
├── decoder.py
│   ├── from_json(data, output_path)             ← 변경: dispatch + deferred
│   └── (신규) _apply_run, _apply_image, _apply_shape, _apply_list ...
└── encoder.py
    └── to_json(hwpx_path)                       ← 변경 (best-effort 식별)
```

### 2.2 Component Diagram

```
JSON (LLM/MCP)
    │
    ▼
HwpxJsonDocument.from_dict
    ├── sections: Section[]
    │   └── paragraphs: Paragraph[]
    │       └── runs: Run[]
    │           └── content: RunContent { type, text?, table?, image?, heading?,
    │                                     bullet_list?, numbered_list?, footnote?,
    │                                     equation?, highlight?, shape? }
    ├── header: Optional[HeaderFooter]      ← 신규 (deferred)
    ├── footer: Optional[HeaderFooter]      ← 신규 (deferred)
    └── page_number: Optional[PageNumber]   ← 신규 (deferred)
    │
    ▼
decoder.from_json
    ├── normal pass: for each run → _apply_run() → b.add_*()
    └── deferred pass: header → footer → page_number (마지막)
    │
    ▼
HwpxBuilder.save()
    │
    ▼
output.hwpx (rhwp-strict-mode 호환, lineseg 정확값)
```

---

## 3. Data Model

### 3.1 신규 dataclass 정의 (schema.py 추가)

```python
@dataclass
class Heading:
    text: str
    level: int = 1                           # 1, 2, 3, 4
    alignment: str = "JUSTIFY"               # JUSTIFY|LEFT|RIGHT|CENTER

@dataclass
class Image:
    image_path: Optional[str] = None         # 로컬 경로 (path 모드)
    image_url: Optional[str] = None          # URL (url 모드, 둘 중 하나)
    filename: Optional[str] = None           # url 모드 전용
    width: Optional[int] = None              # HWPX 단위 (None이면 원본)
    height: Optional[int] = None

@dataclass
class HeaderFooter:
    text: str

@dataclass
class PageNumber:
    pos: str = "BOTTOM_CENTER"               # BOTTOM_CENTER|BOTTOM_RIGHT|TOP_CENTER|TOP_RIGHT

@dataclass
class Footnote:
    text: str
    number: int = 1

@dataclass
class Equation:
    script: str

@dataclass
class Highlight:
    text: str
    color: str = "#FFFF00"

@dataclass
class NestedListItem:
    depth: int = 0                           # 0~6
    text: str = ""

@dataclass
class BulletList:
    items: list[str] = field(default_factory=list)
    bullet_char: str = "-"                   # '-' | '•' | '◦'
    indent: int = 2000
    native: bool = False                     # True: HWPX native bullet, False: text bullet

@dataclass
class NumberedList:
    items: list[str] = field(default_factory=list)
    format_string: str = "^1."               # '^1.' | '^1)' | '(^1)'

@dataclass
class NestedBulletList:
    items: list[NestedListItem] = field(default_factory=list)

@dataclass
class NestedNumberedList:
    items: list[NestedListItem] = field(default_factory=list)

@dataclass
class Shape:
    """Rectangle / line / draw_line 통합 표현 (kind 로 구분)."""
    kind: str = "rectangle"                  # "rectangle" | "line" | "draw_line"
    # rectangle:
    width: int = 14400
    height: int = 7200
    # draw_line:
    x1: int = 0
    y1: int = 0
    x2: int = 42520
    y2: int = 0
    # 공용:
    line_color: str = "#000000"
    line_width: int = 283
```

### 3.2 RunContent 확장

```python
@dataclass
class RunContent:
    type: str = "text"
    # 기존:
    text: Optional[str] = None
    table: Optional[int] = None              # index into section.tables
    image: Optional[Image] = None            # (기존 Image 와 통합)
    # 신규:
    heading: Optional[Heading] = None
    bullet_list: Optional[BulletList] = None
    numbered_list: Optional[NumberedList] = None
    nested_bullet_list: Optional[NestedBulletList] = None
    nested_numbered_list: Optional[NestedNumberedList] = None
    footnote: Optional[Footnote] = None
    equation: Optional[Equation] = None
    highlight: Optional[Highlight] = None
    shape: Optional[Shape] = None            # shape_rect/shape_line/shape_draw_line
```

`type` 가 결정자 (discriminator). 외부 LLM 은 type 만 정확히 쓰고 해당 nested 객체에 값 채움.

### 3.3 HwpxJsonDocument 확장

```python
@dataclass
class HwpxJsonDocument:
    format: str = FORMAT_VERSION
    source: str = ""
    source_sha256: str = ""
    sections: list[Section] = field(default_factory=list)
    preservation: Optional[Preservation] = None
    # 신규 deferred (top-level — Whale SecPr 버그 회피):
    header: Optional[HeaderFooter] = None
    footer: Optional[HeaderFooter] = None
    page_number: Optional[PageNumber] = None
```

---

## 4. Decoder Dispatch (핵심)

### 4.1 from_json 흐름

```python
def from_json(data: dict, output_path: str) -> str:
    doc = HwpxJsonDocument.from_dict(data)
    b = HwpxBuilder()

    # Normal pass — 일반 paragraph/table/run
    for section in doc.sections:
        for para in section.paragraphs:
            if para.page_break:
                b.add_page_break()
            for run in para.runs:
                _apply_run(b, run, section)

    # Deferred pass — Whale SecPr 버그 회피 (HwpxBuilder 와 같은 패턴)
    if doc.header:
        b.add_header(doc.header.text)
    if doc.footer:
        b.add_footer(doc.footer.text)
    if doc.page_number:
        b.add_page_number(doc.page_number.pos)

    return b.save(output_path)
```

### 4.2 _apply_run dispatch table

```python
def _apply_run(b: HwpxBuilder, run: Run, section: Section) -> None:
    c = run.content
    t = c.type

    if t == "text":
        if c.text is None:
            raise ValueError("RunContent.type='text' requires 'text' field")
        b.add_paragraph(c.text)

    elif t == "heading":
        if c.heading is None:
            raise ValueError("RunContent.type='heading' requires 'heading' object")
        b.add_heading(c.heading.text, level=c.heading.level, alignment=c.heading.alignment)

    elif t == "image":
        _apply_image(b, c.image)

    elif t == "table":
        _apply_table(b, c.table, section)

    elif t == "bullet_list":
        bl = c.bullet_list
        if bl is None:
            raise ValueError("RunContent.type='bullet_list' requires 'bullet_list' object")
        b.add_bullet_list(bl.items, bullet_char=bl.bullet_char,
                          indent=bl.indent, native=bl.native)

    elif t == "numbered_list":
        nl = c.numbered_list
        if nl is None:
            raise ValueError("RunContent.type='numbered_list' requires 'numbered_list' object")
        b.add_numbered_list(nl.items, format_string=nl.format_string)

    elif t == "nested_bullet_list":
        nbl = c.nested_bullet_list
        if nbl is None:
            raise ValueError("RunContent.type='nested_bullet_list' requires 'nested_bullet_list' object")
        b.add_nested_bullet_list([(it.depth, it.text) for it in nbl.items])

    elif t == "nested_numbered_list":
        nnl = c.nested_numbered_list
        if nnl is None:
            raise ValueError("RunContent.type='nested_numbered_list' requires 'nested_numbered_list' object")
        b.add_nested_numbered_list([(it.depth, it.text) for it in nnl.items])

    elif t == "footnote":
        fn = c.footnote
        if fn is None:
            raise ValueError("RunContent.type='footnote' requires 'footnote' object")
        b.add_footnote(fn.text, number=fn.number)

    elif t == "equation":
        eq = c.equation
        if eq is None:
            raise ValueError("RunContent.type='equation' requires 'equation' object")
        b.add_equation(eq.script)

    elif t == "highlight":
        hl = c.highlight
        if hl is None:
            raise ValueError("RunContent.type='highlight' requires 'highlight' object")
        b.add_highlight(hl.text, color=hl.color)

    elif t == "shape_line":
        b.add_line()

    elif t in ("shape_rect", "shape_draw_line"):
        _apply_shape(b, c.shape, t)

    else:
        raise ValueError(f"Unknown RunContent.type: {t!r}")


def _apply_image(b: HwpxBuilder, img: Optional[Image]) -> None:
    if img is None:
        raise ValueError("RunContent.type='image' requires 'image' object")
    if img.image_path and img.image_url:
        raise ValueError("Image: provide image_path OR image_url, not both")
    if img.image_path:
        b.add_image(img.image_path, width=img.width, height=img.height)
    elif img.image_url:
        b.add_image_from_url(img.image_url, filename=img.filename or "",
                             width=img.width, height=img.height)
    else:
        raise ValueError("Image: image_path or image_url required")


def _apply_shape(b: HwpxBuilder, shape: Optional[Shape], type_: str) -> None:
    if shape is None:
        raise ValueError(f"RunContent.type={type_!r} requires 'shape' object")
    if type_ == "shape_rect":
        b.add_rectangle(width=shape.width, height=shape.height,
                        line_color=shape.line_color, line_width=shape.line_width)
    elif type_ == "shape_draw_line":
        b.add_draw_line(x1=shape.x1, y1=shape.y1, x2=shape.x2, y2=shape.y2,
                        line_color=shape.line_color, line_width=shape.line_width)


def _apply_table(b: HwpxBuilder, table_idx: Optional[int], section: Section) -> None:
    if not isinstance(table_idx, int):
        return
    if table_idx >= len(section.tables):
        raise ValueError(f"table index {table_idx} out of range")
    tbl = section.tables[table_idx]
    table_data = [[cell.text for cell in row.cells] for row in tbl.rows]
    col_widths = tbl.col_widths or None
    row_heights = [row.height for row in tbl.rows] if tbl.rows else None
    b.add_table(table_data, col_widths=col_widths, row_heights=row_heights)
```

---

## 5. JSON 예시 (외부 LLM 친화)

### 5.1 풍부한 보고서 예시

```json
{
  "format": "1.0",
  "header": {"text": "기밀 보고서"},
  "footer": {"text": "회사 X — 2026"},
  "page_number": {"pos": "BOTTOM_CENTER"},
  "sections": [{
    "paragraphs": [
      {"runs": [{"content": {"type": "heading",
                              "heading": {"text": "1. 서론", "level": 1}}}]},
      {"runs": [{"content": {"type": "text",
                              "text": "본 보고서는..."}}]},
      {"runs": [{"content": {"type": "bullet_list",
                              "bullet_list": {
                                "items": ["배경", "목적", "범위"],
                                "bullet_char": "•"
                              }}}]},
      {"runs": [{"content": {"type": "image",
                              "image": {"image_path": "./photo.png",
                                        "width": 42520, "height": 30000}}}]},
      {"runs": [{"content": {"type": "footnote",
                              "footnote": {"text": "참고문헌 3 참조", "number": 1}}}]},
      {"runs": [{"content": {"type": "highlight",
                              "highlight": {"text": "주의 필요",
                                            "color": "#FFFF00"}}}]}
    ],
    "tables": [],
    "page_settings": {"width": 59530, "height": 84150}
  }]
}
```

### 5.2 중첩 목록 예시

```json
{"runs": [{"content": {
  "type": "nested_bullet_list",
  "nested_bullet_list": {
    "items": [
      {"depth": 0, "text": "1단계 항목"},
      {"depth": 1, "text": "  2단계 하위"},
      {"depth": 2, "text": "    3단계 하위"}
    ]
  }
}}]}
```

### 5.3 v0.14.0 호환 (paragraphs/tables only)

```json
{
  "format": "1.0",
  "sections": [{
    "paragraphs": [{"runs": [{"content": {"type": "text", "text": "Hello"}}]}],
    "tables": [],
    "page_settings": {}
  }]
}
```

→ 그대로 동작 (회귀 테스트로 보장)

---

## 6. Test Plan

### 6.1 단위 테스트 (≥ 16 개, builder 메서드별 1:1)

| ID | Test | Method |
|----|------|--------|
| T-01 | `from_json` heading → output 에 add_heading 효과 | check XML |
| T-02 | image (path mode) | XML에 BinData |
| T-03 | image (url mode) — mock urllib | mock |
| T-04 | image: path+url 동시 → ValueError | exception |
| T-05 | bullet_list (flat) | XML 내용 |
| T-06 | numbered_list | XML 내용 |
| T-07 | nested_bullet_list ([(0,a),(1,b),(2,c)]) | depth 검증 |
| T-08 | nested_numbered_list | depth 검증 |
| T-09 | footnote | XML 내용 |
| T-10 | equation | XML 내용 |
| T-11 | highlight | XML 내용 |
| T-12 | shape_rect | XML 내용 |
| T-13 | shape_line | XML 내용 |
| T-14 | shape_draw_line | XML 내용 |
| T-15 | header/footer/page_number 모두 deferred 마지막 호출 | builder action 순서 |
| T-16 | unknown type → ValueError | exception |
| T-17 | v0.14.0 호환 — paragraphs/tables only JSON | 회귀 |
| T-18 | 풍부 통합 (heading + paragraph + bullet + image + footnote) | round-trip |

### 6.2 회귀

- 기존 72 PASS 유지
- 신규 ≥ 16 → 총 ≥ 88

### 6.3 통합 / E2E

- mcp_server.hwpx_from_json 으로 풍부 JSON 처리 (별도 변경 없이)
- output 파일이 `pyhwpxlib validate` strict + compat 모두 PASS

---

## 7. Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| from_dict 가 nested dataclass 초기화 누락 | High | 명시적 from_dict 구현 (각 nested 도 .from_dict 수동 호출) |
| 사용자가 type 만 적고 nested 객체 빠뜨림 | High | ValueError 명시 + docstring 예시 풍부 |
| dataclass 폭증 → schema.py 비대 | Medium | 하나의 RunContent 안 union 형태 유지, dataclass 는 nested만 |
| encoder round-trip 100% 안 됨 | Medium | best-effort, FR-09 Medium priority — 핵심은 from_json |
| nested list depth 직렬화 (tuple vs dict) | Low | JSON 은 dict `{depth,text}`, builder 호출 시 tuple 변환 |
| Whale SecPr 버그 재발 | High | builder 의 deferred 패턴 그대로 적용 (검증된 패턴) |

---

## 8. Implementation Order

1. [ ] `schema.py` 신규 dataclass (Heading, Image, BulletList, ...) + RunContent 확장
2. [ ] `schema.py` HwpxJsonDocument.from_dict 보강 (nested 객체 수동 초기화)
3. [ ] `decoder.py` `_apply_run` + `_apply_image` + `_apply_shape` + `_apply_table`
4. [ ] `decoder.py` `from_json` 에 deferred 처리
5. [ ] 단위 테스트 T-01 ~ T-16 (builder 메서드 별)
6. [ ] 통합 테스트 T-17, T-18
7. [ ] `encoder.py` round-trip 보강 (best-effort, FR-09)
8. [ ] mcp_server hwpx_from_json docstring 갱신
9. [ ] SKILL.md 풍부 JSON 예시
10. [ ] CHANGELOG 0.15.0 + 버전 bump
11. [ ] PyPI 0.15.0 + skill zip

---

## 9. Open Questions

| Q | Resolution |
|---|------------|
| `RunContent` 가 한 객체에 모든 nested 필드 가져 비대해지지 않나? | 모두 Optional, json 직렬화 시 None은 생략 → 실제 payload 작음. 가독성 위해 dataclass 분리는 유지 |
| heading 도 alignment 외 색상/폰트 지정해야 하나? | 0.15.0 한정: builder 시그니처 그대로 (text/level/alignment). 색상/폰트는 추후 확장 |
| nested_list 의 depth 0~6 검증을 schema 단계에서 강제? | 0.15.0 은 builder 가 검증 (그대로 위임), 0.16.0 에서 schema validator 추가 검토 |
| backwards-compat: image 가 기존엔 dict 였는데 이제 Image dataclass | from_dict 가 dict→Image 변환 — 외부 입력 호환 유지 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-29 | Initial draft (16 type dispatch + deferred top-level + 18 tests) | Mindbuild + Claude |
