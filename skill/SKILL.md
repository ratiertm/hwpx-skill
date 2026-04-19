---
name: hwpx
description: "Use this skill whenever the user wants to create, read, edit, analyze, or manipulate Hangul/Korean word processor documents (.hwpx, .hwp, .owpml files). Triggers include: any mention of 'hwpx', 'hwp', '한글 파일', '한글 문서', '한컴', 'OWPML', or requests to produce Korean government forms, fill templates, clone forms, or convert documents. Also use when converting HWP to HWPX (hwp2hwpx), extracting text from .hwpx files, filling form fields, checking/unchecking boxes, generating multiple filled documents, converting HTML/Markdown to .hwpx format, extracting images from HWP/HWPX documents, analyzing document contents (text, tables, images), or extracting/applying document themes and styles. If the user asks to '이미지 추출', '문서 분석', '표 데이터 추출', '이미지 내용 파악', or any Korean document operation, use this skill. Do NOT use for .docx Word documents, PDFs, or spreadsheets."
---

# HWPX creation, editing, and form automation

## 절대 규칙

1. **pyhwpxlib만 사용** — XML 직접 작성/다른 라이브러리 금지
2. `.hwp` → `pyhwpxlib.hwp2hwpx.convert()`로 HWPX 변환부터
3. `.hwpx` 읽기 → `pyhwpxlib.api.extract_text()`
4. 새 문서 → `from pyhwpxlib import HwpxBuilder`
5. 편집 → `unpack → 문자열 교체 → pack` (ET.tostring 금지)
6. 생성/편집 후 **validate + lint 필수**
7. **SVG 프리뷰 생성 → Read tool로 직접 확인** (생략 금지)

## 디자인 규칙

1. 주제에 맞는 테마 선택 — 파란색 디폴트 금지
2. **시각 요소는 내용에 맞을 때만** — 억지로 표를 만들지 않는다
3. 같은 레이아웃 반복 금지
4. 이미지 적극 활용 — 사용자가 제공하면 반드시 삽입
5. **문단 간격 필수** — `add_paragraph("")`로 헤딩/표/이미지 앞뒤에 빈 줄

---

## On Load — 스킬 로드 시 즉시 실행

사용자 메시지에 구체적 작업이 없으면 AskUserQuestion:

```
"어떤 작업을 하시겠어요?"
1. 새 문서 만들기
2. 기존 문서 편집
3. 양식 자동화
4. 문서 변환
5. 문서 분석 — 텍스트·표·이미지 추출 + Vision
```

**자동 감지**: `.hwp` → 변환 후 진행, `.hwpx` → 바로 진행, `.md` → md2hwpx

---

## 워크플로우 [1] 새 문서 만들기

Step A: 테마 선택
```python
from pyhwpxlib.themes import _THEMES_DIR, BUILTIN_THEMES, load_theme
customs = sorted(_THEMES_DIR.glob('*.json')) if _THEMES_DIR.exists() else []
```
저장된 양식이 있으면 먼저 제안. 없으면 주제에 맞는 내장 테마 선택 (10종).

Step B: 내용 확인 → AskUserQuestion

Step C: 실행
```python
from pyhwpxlib import HwpxBuilder
doc = HwpxBuilder(theme='forest')
doc.add_heading("제목", level=1)
doc.add_paragraph("")                    # 간격 필수
doc.add_paragraph("본문")
doc.add_paragraph("")
doc.add_table([["A", "B"]])              # 필요할 때만
doc.add_paragraph("")
doc.add_image("photo.png", width=42520, height=23918)  # A4 전체 너비
doc.add_paragraph("")
doc.save("output.hwpx")
```

Step D: `pyhwpxlib validate` + `pyhwpxlib lint`

Step E: **시각 검토 (생략 금지)**
```python
from pyhwpxlib.rhwp_bridge import RhwpEngine
engine = RhwpEngine()
doc = engine.load("output.hwpx")
svg = doc.render_page_svg(0, embed_fonts=True)
# Read tool로 SVG/PNG 직접 확인
```

**rhwp 프리뷰 알려진 한계** (Whale에서는 정상):
- 이미지와 텍스트 겹침 — rhwp가 textWrap 미지원
- linesegarray 불일치 — 텍스트 교체 후 줄 뭉침

**7가지 비주얼 체크포인트**:

**1. 시각적 계층 (Visual Hierarchy)**
- 제목/소제목/본문 크기 차이가 충분한가? (2배 이상)
- 표지가 있으면: 제목이 충분히 크게 보이나? (28pt+)

**2. 색상 & 대비 (Color & Contrast)**
- 테마 primary 색상이 적용되었나?
- 표 헤더 위 텍스트가 읽히는가?
- 기본 파란색(#395da2)이 아닌 주제에 맞는 색상인가?

**3. 타이포그래피 (Typography)**
- 폰트 깨짐(□) 없는가?
- 글자 간격이 겹치지 않는가?

**4. 레이아웃 & 공간 (Layout & Spacing)**
- 넘침/잘림/빈 페이지 없나?
- 여백이 균등한가?

**5. 표 스타일 (Table)**
- 헤더 배경색 적용, 셀 패딩 적절, 컬럼 너비 분배

**6. 원본 대조 (편집/양식 시)**
- 원본과 같은 구조인가? 교체 안 된 텍스트 없나?

**7. AI 패턴 피하기 (Anti-Slop)**
- 모든 섹션 동일 레이아웃 아닌가?
- 텍스트만 있는 섹션에 억지로 표 넣지 않았나?

Step F: AskUserQuestion — "Whale에서도 확인해주세요"
Step G: **양식 저장 제안** — 완성 시 `extract_theme` + `save_theme`

---

## 워크플로우 [2] 기존 문서 편집

Step A: 파일 경로 → HWP면 HWPX 변환
Step B: `extract_text()` → 내용 보여주기
Step C: 편집 유형 확인 → 텍스트 교체/양식 채우기
Step D: `unpack → 원본 문자열 교체 → pack → validate`

---

## 워크플로우 [3] 양식 채우기

Step A: 프리뷰 렌더링 → Claude가 PNG 보고 양식 분석
Step B: 사용자에게 필드 입력 요청
Step C: **구조 판정** — 인접 셀(A) vs 같은 셀(B)
- 구조 A → `fill_by_labels` 사용
- 구조 B → `unpack → 문자열 교체 → pack`
Step D: 프리뷰 검증 → Whale 확인 요청

---

## 워크플로우 [4] 문서 변환

```python
from pyhwpxlib.hwp2hwpx import convert         # HWP→HWPX
from pyhwpxlib.api import convert_html_file_to_hwpx  # HTML→HWPX
# pyhwpxlib md2hwpx input.md -o output.hwpx    # MD→HWPX
```

---

## 워크플로우 [5] 문서 분석

```python
from pyhwpxlib.json_io.overlay import extract_overlay
overlay = extract_overlay(hwpx_path)
# overlay['texts'], overlay['tables'], overlay['images']
```
BinData에서 이미지 추출 → Read tool로 내용 파악 (Vision)

---

## Quick Reference

| Task | Approach |
|------|----------|
| 새 문서 | `HwpxBuilder(theme='forest')` |
| 텍스트 읽기 | `extract_text()` |
| 편집 | `unpack → replace → pack` |
| 양식 채우기 | `fill_template(data={"key": "val"})` — {{key}} 패턴 |
| 체크박스 | `fill_template_checkbox(checks=["동의함"])` |
| 이미지 삽입 | `add_image(path, width=42520, height=비율)` |
| 기존 문서에 이미지 | `insert_image_to_existing()` |
| 이미지 교체 | overlay `new_data_b64` |
| HWP→HWPX | `hwp2hwpx.convert()` |
| 검증 | `pyhwpxlib validate` + `lint` + `font-check` |
| 테마 추출 | `extract_theme() → save_theme()` |
| 테마 목록 | `pyhwpxlib themes list` |
| 프리뷰 | `RhwpEngine().load().render_page_svg()` |

---

## 테마 (10종)

| 테마명 | Primary | 용도 |
|--------|---------|------|
| `default` | `#395da2` | 공문서 |
| `forest` | `#2C5F2D` | 환경, ESG |
| `warm_executive` | `#B85042` | 제안서 |
| `ocean_analytics` | `#065A82` | 데이터 |
| `coral_energy` | `#F96167` | 마케팅 |
| `charcoal_minimal` | `#36454F` | 기술 |
| `teal_trust` | `#028090` | 의료, 금융 |
| `berry_cream` | `#6D2E46` | 교육 |
| `sage_calm` | `#84B59F` | 웰빙 |
| `cherry_bold` | `#990011` | 경고 |

커스텀: `extract_theme("ref.hwpx") → save_theme() → HwpxBuilder(theme='custom/name')`

---

## 이미지 크기 규칙

기본값은 **항상 전체 너비(42520)**. 비율 유지:
```python
from PIL import Image
img = Image.open("photo.png")
width = 42520
height = int(42520 * img.size[1] / img.size[0])
doc.add_image("photo.png", width=width, height=height)
```
로고/아이콘만 8000~12000. **이미지 앞뒤 빈 줄 필수.**

---

## Critical Rules

| # | Rule | Consequence |
|---|------|-------------|
| 1 | `<hp:t>` 안에 `\n` 금지 | Whale 에러 |
| 2 | ET.tostring 금지 | 네임스페이스 변경 |
| 3 | 원본 문자열 직접 교체 | 서식 보존 유일한 방법 |
| 4 | mimetype STORED | OPC 규격 |
| 5 | condense 보존 | JUSTIFY 벌어짐 방지 |
| 6 | 헤딩/표/이미지 앞뒤 빈 줄 | 간격 없으면 붙음 |
| 7 | 표는 필요할 때만 | 억지 삽입 금지 |

> 상세 API, 프리셋, 표 파라미터, 편집 세부사항 → [references/](references/) 참조

---

## Reference Files

| File | Contents |
|------|----------|
| [references/api_full.md](references/api_full.md) | HwpxBuilder 전체 메서드, 표 파라미터, 크기 변환 |
| [references/design_guide.md](references/design_guide.md) | 주제별 팔레트 10종, 레이아웃, QA |
| [references/editing.md](references/editing.md) | unpack/pack 상세, XML 규칙, 고급 편집 |
| [references/form_automation.md](references/form_automation.md) | fill_template, batch, schema, checkbox |
| [references/document_types.md](references/document_types.md) | 문서 유형, 프리셋, 표지, 결문 |
| [references/HWPX_RULEBOOK.md](references/HWPX_RULEBOOK.md) | Critical Rules 전체 + 상세 설명 |
