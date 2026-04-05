# Form Automation Reference

## Table of Contents

1. [Fill Template (텍스트 교체 방식)](#fill-template)
2. [Batch Generate (다건 생성)](#batch-generate)
3. [Schema Extraction (필드 자동 탐지)](#schema-extraction)
4. [Template Builder UI](#template-builder-ui)
5. [Checkbox Patterns](#checkbox-patterns)
6. [Critical Rules for Form Automation](#critical-rules-for-form-automation)

---

## Fill Template

텍스트 교체 방식 — 서식 100% 보존

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

---

## Batch Generate

다건 생성

```python
from pyhwpxlib.api import fill_template_batch

records = [
    {"data": {">성 명<": ">성 명  홍길동<"}, "checks": ["민간기업"], "filename": "홍길동"},
    {"data": {">성 명<": ">성 명  김영수<"}, "checks": ["공공기관(공기업)"], "filename": "김영수"},
]
fill_template_batch("template.hwpx", records, output_dir="output/")
```

---

## Schema Extraction

필드 자동 탐지

```python
from pyhwpxlib.api import extract_schema, analyze_schema_with_llm

schema = extract_schema("template.hwpx")
analyzed = analyze_schema_with_llm(schema)
# analyzed['input_fields'] — 사용자 입력 필드
# analyzed['fixed_fields'] — 고정 텍스트
# analyzed['checkboxes'] — 체크박스
```

---

## Template Builder UI

```bash
python template_builder.py template.hwpx --port 8081
# 브라우저에서 필드 입력/고정/제목 토글 → schema.json 저장
```

---

## Checkbox Patterns

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

---

## Critical Rules for Form Automation

- **원본 ZIP 복사 + XML 텍스트 교체** — pyhwpxlib 재생성 금지 (header 깨짐)
- **`.replace(old, new, 1)`** — 첫 번째만 교체 (다른 페이지 보호)
- **condense/styleIDRef/breakSetting** — 원본 paraPr을 건드리면 JUSTIFY 글자 벌어짐
- **ET.tostring 금지** — 반드시 원본 문자열 직접 교체
