---
template: plan
version: 1.2
description: HwpxJsonDocument 에 16개 풍부 필드 추가 + decoder.from_json 매핑 (옵션 A, 정공법)
---

# json-schema-expansion Planning Document

> **Summary**: graphify 분석으로 드러난 JSON 경로 단조성 (`from_json` 이 builder 19개 add_* 중 3개만 사용 = 16%) 을 해소한다. `HwpxJsonDocument` 스키마에 heading/image/header-footer/list/footnote 등 풍부 필드를 추가하고 `decoder.from_json` 이 16개 builder 메서드를 호출하도록 매핑한다. JSON/MCP 사용자가 builder 직접 호출 수준의 풍부한 HWPX 를 만들 수 있게 된다.
>
> **Project**: pyhwpxlib
> **Version**: 0.14.0 → 0.15.0 (additive, non-breaking)
> **Date**: 2026-04-29
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

graphify 분석 결과 (`pyhwpxlib_improvement_directions.md` § "두 경로의 표현력이 극과 극"):

| 경로 | 표현력 | 사용 메서드 |
|------|:------:|-------------|
| HwpxBuilder 직접 호출 (Python) | 풍부 (19/19) | heading/image/list/footnote/header/footer/등 |
| JSON → from_json (MCP, 외부 LLM) | **단조 (3/19)** | paragraph/table/page_break |
| overlay (기존 양식 채우기) | 양식 자체의 풍부함 | 텍스트/이미지/표 셀 patch |

옵션 A 정공법: JSON 경로의 단조성을 근본 해소. MCP/Claude/GPT 등 외부 도구가 풍부한 HWPX 를 JSON 한 덩어리로 생성 가능.

### 1.2 Background

- 사용자 분석 (`개선방향.md` line 49-52): "옵션 A — JSON schema 확장 (정공법, 큰 작업)"
- v0.13.3 옵션 B (template workflow) 는 **기존 양식 재사용** 패턴. 새 양식을 LLM 이 0부터 만드는 시나리오는 미커버
- v0.14.0 rhwp-strict-mode 는 **출력 정직성** 정책. 표현력 자체와는 직교
- 옵션 A 는 두 정책과 호환되며 누락된 표현력 갭만 메움

### 1.3 Related

- 메모리: `project_template_workflow_0_13_3.md` (옵션 B 결과)
- 메모리: `reference_hwpx_ecosystem_position.md` (rhwp 노선)
- graphify 분석: `graphify-out/`
- 코드: `pyhwpxlib/json_io/{schema,decoder,encoder}.py` + `pyhwpxlib/builder.py`

---

## 2. Scope

### 2.1 In Scope (v0.15.0)

- [ ] `HwpxJsonDocument` / `Section` / `Paragraph` 스키마 확장 — 풍부 요소 표현
- [ ] 신규 dataclass: `Heading`, `Image`, `HeaderFooter`, `Footnote`, `BulletList`, `NumberedList`, `Equation`, `Highlight`, `Shape` (rectangle/line/draw_line)
- [ ] `decoder.from_json` 이 16개 builder 메서드 매핑하여 호출:
   - heading, image, image_from_url, header, footer, footnote, page_number,
     highlight, draw_line, line, rectangle, equation,
     bullet_list, numbered_list, nested_bullet_list, nested_numbered_list
- [ ] `encoder.to_json` 도 round-trip 지원 (HWPX → JSON 시 풍부 요소 식별 → 적절한 타입으로 재현)
- [ ] **deferred 처리**: header/footer/page_number 는 builder 가 마지막 재생 (Whale SecPr 버그 회피 — `feedback_hwpx_whale_bug.md` 메모리 적용)
- [ ] 신규 테스트 ≥ 16 (each builder method round-trip)
- [ ] CHANGELOG 0.15.0
- [ ] SKILL.md / mcp_server 업데이트 (JSON 예시 추가)

### 2.2 Out of Scope

- 기존 단순 paragraphs/tables JSON 호환 깨기 — 모든 추가 필드는 optional, 기존 input 그대로 동작
- 양식 form-fill 통합 (별도 trajectory)
- 복잡한 차트/SmartArt (builder 자체가 미지원)
- v0.15.0 에서 schema 가 모든 OWPML 292 클래스 표현 — 19개 builder 메서드 한정

---

## 3. Requirements

### 3.1 Functional

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | `HwpxJsonDocument` 스키마에 신규 RunContent.type 추가: `heading`, `image`, `bullet_list`, `numbered_list`, `nested_bullet_list`, `nested_numbered_list`, `equation`, `highlight`, `footnote`, `shape_rect`, `shape_line`, `shape_draw_line`, `page_number` | High |
| FR-02 | `Section` 또는 top-level 에 `header: Optional[HeaderFooter]`, `footer: Optional[HeaderFooter]` (deferred) | High |
| FR-03 | `decoder.from_json` 이 위 13개 type + 기존 paragraph/table/page_break = 16개 builder 메서드 호출 | High |
| FR-04 | header/footer/page_number 는 deferred actions 로 마지막 처리 (HwpxBuilder 패턴 동일) | High |
| FR-05 | Image: `image_path` (로컬) 또는 `image_url` (URL) 둘 중 하나 + width/height optional | High |
| FR-06 | List: items 배열 + nested 의 경우 `[depth, text]` tuple 표현 | High |
| FR-07 | 기존 0.14.0 JSON (paragraphs/tables only) 그대로 동작 (back-compat) | High |
| FR-08 | 모든 신규 type 에 대한 단위 테스트 + 통합 round-trip 테스트 | High |
| FR-09 | `encoder.to_json` 이 풍부 요소를 식별하여 적절한 type 으로 출력 (best-effort) | Medium |

### 3.2 Non-Functional

| Category | Criteria |
|----------|----------|
| 호환성 | v0.14.0 JSON input 그대로 동작 (additive only) |
| 검증 | 회귀 72 PASS 유지 + 신규 ≥ 16 |
| MCP | mcp_server.hwpx_from_json 이 새 schema 그대로 받음 (별도 변경 없이) |
| 표준 준수 | 출력 HWPX 가 v0.14.0 strict validate PASS |
| Hancom 호환 | rhwp-strict-mode default 유지 (silent fix 없음) |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] JSON 한 덩어리로 다음을 만들 수 있음: 표지(heading) + 본문(paragraph) + 불릿(bullet_list) + 표(table) + 이미지(image) + 각주(footnote) + header + footer + page_number
- [ ] mcp_server 의 `hwpx_from_json` 으로 동일한 JSON 입력 가능
- [ ] 회귀 72 + 신규 ≥ 16 = ≥ 88 PASS
- [ ] Round-trip: HwpxBuilder 로 만든 풍부 문서 → encoder.to_json → decoder.from_json 결과가 시맨틱 동일
- [ ] CHANGELOG / SKILL.md 갱신
- [ ] PyPI 0.15.0 출시

### 4.2 Quality

- [ ] dataclass 스키마 명확 — 각 type 별 필수/optional 필드 docstring
- [ ] decoder 매핑 함수 분리 (`_apply_heading`, `_apply_image`, ...) 로 가독성
- [ ] 잘못된 JSON 입력 시 명확한 ValueError (조용한 skip 금지 — rhwp 노선 일관)

---

## 5. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| schema 폭발 — 19개 type 마다 별도 dataclass | Medium | 공용 RunContent 에 union 필드로 통합, dataclass 는 type 별 nested 구조만 |
| header/footer 순서 버그 (Whale SecPr) | High | builder 의 deferred 패턴 그대로 적용 (`feedback_hwpx_whale_bug.md`) |
| nested list depth 표현 모호 | Medium | builder API 인 `[(depth, text), ...]` tuple → JSON 에선 `[{depth, text}, ...]` 로 명시 |
| encoder round-trip 100% 안 됨 | Medium | encoder 는 best-effort, FR-09 은 Medium priority. 핵심은 from_json (외부→HWPX) |
| JSON sample 파일 시간 소요 | Low | 단위 테스트 fixture 는 inline dict, 별도 파일 안 만듦 |

---

## 6. Architecture

### 6.1 스키마 변경 (additive)

```python
# pyhwpxlib/json_io/schema.py — 신규 type 들

@dataclass
class Heading:
    text: str
    level: int = 1                  # 1, 2, 3
    alignment: str = "JUSTIFY"

@dataclass
class Image:
    image_path: Optional[str] = None    # 로컬 경로
    image_url: Optional[str] = None     # URL (둘 중 하나)
    width: Optional[int] = None
    height: Optional[int] = None
    filename: Optional[str] = None      # url 모드 전용

@dataclass
class HeaderFooter:
    text: str

@dataclass
class Footnote:
    text: str
    number: int = 1

@dataclass
class ListItem:
    depth: int = 0
    text: str = ""

@dataclass
class BulletList:
    items: list[str]                # flat or list[ListItem] for nested
    bullet_char: str = "-"
    nested: bool = False

@dataclass
class NumberedList:
    items: list[str]
    format_string: str = "^1."
    nested: bool = False

@dataclass
class Highlight:
    text: str
    color: str = "#FFFF00"

@dataclass
class Equation:
    script: str

@dataclass
class Shape:
    kind: str                       # "rectangle" | "line" | "draw_line"
    width: int = 14400
    height: int = 7200
    x1: int = 0
    y1: int = 0
    x2: int = 42520
    y2: int = 0
    color: str = "#000000"

@dataclass
class PageNumber:
    pos: str = "BOTTOM_CENTER"

# RunContent.type 확장:
#   "text" | "table" | "image" | "heading" | "bullet_list" | "numbered_list"
#   | "nested_bullet_list" | "nested_numbered_list" | "footnote" | "equation"
#   | "highlight" | "shape_rect" | "shape_line" | "shape_draw_line"
#   | "page_number"

@dataclass
class HwpxJsonDocument:
    # 기존 필드 유지
    sections: list[Section] = ...
    # 신규 (deferred):
    header: Optional[HeaderFooter] = None
    footer: Optional[HeaderFooter] = None
    page_number: Optional[PageNumber] = None
```

### 6.2 decoder 매핑 흐름

```python
def from_json(data, output_path):
    doc = HwpxJsonDocument.from_dict(data)
    b = HwpxBuilder()

    # Normal actions (per section/paragraph/run order)
    for section in doc.sections:
        for para in section.paragraphs:
            if para.page_break:
                b.add_page_break()
            for run in para.runs:
                _apply_run(b, run, section)

    # Deferred (Whale SecPr 회피, builder 패턴 동일)
    if doc.header:    b.add_header(doc.header.text)
    if doc.footer:    b.add_footer(doc.footer.text)
    if doc.page_number: b.add_page_number(doc.page_number.pos)

    return b.save(output_path)


def _apply_run(b, run, section):
    c = run.content
    t = c.type
    dispatch = {
        "text":             lambda: b.add_paragraph(c.text),
        "heading":          lambda: b.add_heading(c.heading.text, level=c.heading.level, alignment=c.heading.alignment),
        "image":            lambda: _apply_image(b, c.image),
        "table":            lambda: _apply_table(b, c.table, section),
        "bullet_list":      lambda: b.add_bullet_list(c.bullet_list.items, bullet_char=c.bullet_list.bullet_char),
        "numbered_list":    lambda: b.add_numbered_list(c.numbered_list.items, format_string=c.numbered_list.format_string),
        "nested_bullet_list":   lambda: b.add_nested_bullet_list([(i.depth, i.text) for i in c.bullet_list.items]),
        "nested_numbered_list": lambda: b.add_nested_numbered_list([(i.depth, i.text) for i in c.numbered_list.items]),
        "footnote":         lambda: b.add_footnote(c.footnote.text, number=c.footnote.number),
        "equation":         lambda: b.add_equation(c.equation.script),
        "highlight":        lambda: b.add_highlight(c.highlight.text, color=c.highlight.color),
        "shape_rect":       lambda: b.add_rectangle(width=c.shape.width, height=c.shape.height),
        "shape_line":       lambda: b.add_line(),
        "shape_draw_line":  lambda: b.add_draw_line(x1=c.shape.x1, y1=c.shape.y1, x2=c.shape.x2, y2=c.shape.y2, color=c.shape.color),
    }
    handler = dispatch.get(t)
    if handler is None:
        raise ValueError(f"Unknown RunContent.type: {t!r}")
    handler()
```

### 6.3 Data Flow

```
JSON (외부 LLM)
  ↓
HwpxJsonDocument.from_dict
  ├─ sections: Section[]
  │   └─ paragraphs: Paragraph[]
  │       └─ runs: Run[]
  │           └─ content: RunContent (type discriminated union)
  ├─ header: Optional[HeaderFooter]
  ├─ footer: Optional[HeaderFooter]
  └─ page_number: Optional[PageNumber]
  ↓
decoder.from_json
  ├─ for each run → _apply_run() → builder.add_*
  └─ deferred header/footer/page_number 마지막 재생
  ↓
HwpxBuilder.save() (정확값 lineseg, rhwp-strict-mode 호환)
  ↓
output.hwpx
```

---

## 7. Conventions

- 신규 dataclass: snake_case 필드명, optional 은 `Optional[T] = None`
- `RunContent.type` 문자열 enum (str 그대로) — 외부 LLM 친화
- 잘못된 type → `ValueError` (silent skip 금지, rhwp 노선)
- `image_path` vs `image_url` 동시 사용 → ValueError
- builder 인자 매칭은 1:1 (변환 최소화)

---

## 8. Next Steps

1. [ ] Design 문서 (각 type 별 필수 필드 표 + 예시 JSON)
2. [ ] schema.py 신규 dataclass 추가
3. [ ] decoder.py `_apply_run` 분리 + 16개 type 매핑
4. [ ] encoder.py round-trip 보강 (best-effort)
5. [ ] 16+ 단위 테스트 + 통합 테스트
6. [ ] mcp_server hwpx_from_json docstring 갱신 + JSON 예시
7. [ ] SKILL.md JSON 풍부 예시 추가
8. [ ] CHANGELOG 0.15.0
9. [ ] PyPI 0.15.0 출시 + skill zip

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-29 | Initial draft (옵션 A 정공법) | Mindbuild + Claude |
