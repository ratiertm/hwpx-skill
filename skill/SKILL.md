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

**Step 1: 등록된 양식 자동 인식 (v0.17.0+, 채팅 간 컨텍스트 유지의 핵심)**
```python
from pyhwpxlib.templates import list_templates
items = list_templates()  # workspace 우선 + skill bundle 폴백
# items[i]: {name, name_kr, source, _meta:{description,...}, decisions_count, ...}
```
- 사용자가 양식명·한글명·기능 키워드를 언급하면 매칭되는 양식이 있는지 먼저 확인.
- 매칭되면 곧장 **Step 2: 컨텍스트 로드**.
- "양식이 등록돼 있다 / 새로 등록 / 검색" 중에 능동 안내.

**Step 2: 등록 양식 매칭 시 컨텍스트 자동 주입**
```python
from pyhwpxlib.templates.context import load_context
ctx = load_context(name)            # schema/_meta + decisions.md + history.json
print(ctx.to_markdown())            # 채팅에 그대로 포스트 — 모델이 즉시 흡수
```
이전 채팅의 결정사항 (`structure_type`/`page_standard`/`notes`/decisions) 과
최근 채우기 값 (`recent_data`) 이 자동 복원된다 → 사용자가 양식 다시 업로드하거나
설명 다시 할 필요 없음.

**Step 3: 사용자 메시지에 구체적 작업이 없으면 AskUserQuestion**
```
"어떤 작업을 하시겠어요?"
1. 새 문서 만들기
2. 기존 문서 편집
3. 양식 자동화 (등록된 양식 N개 — 이름 말씀하시면 컨텍스트 즉시 로드)
4. 문서 변환
5. 문서 분석 — 텍스트·표·이미지 추출 + Vision
```

**자동 감지**: `.hwp` → 변환 후 진행, `.hwpx` → 바로 진행, `.md` → md2hwpx

**SessionStart hook (선택)**: `pyhwpxlib install-hook` 한 번 실행하면 Claude Code 가
새 채팅 시작 시 등록 양식 목록을 자동으로 sessionContext 에 주입한다 → 매번
list_templates() 호출 없이도 모델이 바로 인식.

---

## 워크플로우 [1] 새 문서 만들기

Step A: 테마 선택
```python
from pyhwpxlib.themes import _THEMES_DIR, BUILTIN_THEMES, load_theme
customs = sorted(_THEMES_DIR.glob('*.json')) if _THEMES_DIR.exists() else []
```
저장된 양식이 있으면 먼저 제안. 없으면 주제에 맞는 내장 테마 선택 (10종).

Step B: 내용 확인 → AskUserQuestion

**Rich Mode 체크리스트** — "최대한 기능 활용", "풍부하게", 보고서/제안서 요청 시 점검:

| 분류 | Builder 메서드 | 언제 |
|------|---------------|------|
| 구조 | `add_heading` `add_paragraph` `add_page_break` `add_line` | 항상 |
| 강조 | `add_highlight` `add_footnote` `add_equation` | 핵심 메시지·각주·수식 |
| 리스트 | `add_bullet_list` `add_numbered_list` `add_nested_bullet_list` `add_nested_numbered_list` | 단계·항목·계층 |
| 시각 | `add_image` `add_image_from_url` `add_table` `add_rectangle` `add_draw_line` | 그래프·표·도형 |
| 결문 | `add_header` `add_footer` `add_page_number` | 보고서·공식 문서 |

→ 내용에 자연스러운 것만 선택. 디자인 규칙 #2 (억지 삽입 금지) 유지. 골든 샘플: [references/rich_document_example.md](references/rich_document_example.md).

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

**보조 렌더 API** (용도별 선택):
```python
html = doc.render_page_html(0)               # HTML fragment — SVG/PNG보다 훨씬 가벼움(수십 KB)
tree = doc.get_page_render_tree(0)           # {type, bbox, children} — 좌표 기반 레이아웃 검증용
n    = doc.render_page_canvas_count(0)       # Canvas 명령 수 (sanity check)
# tree로 "결문이 page 1 body bbox 안에 있나" 프로그래매틱 판정 가능
# → 공문 autofit, 양식 fill 후 빈 셀 검증 등에 활용
```
브라우저 비트맵 렌더(`renderPageToCanvas`)는 `HtmlCanvasElement` 필요라 Python 불가.

**7가지 비주얼 체크포인트**:

**1. 시각적 계층 (Visual Hierarchy)**
- 제목/소제목/본문 크기 구분이 되는가? (공문서 기준: 본문 15pt, 소제목 16pt, 제목 18~20pt)
- 표지가 있으면: 제목이 충분히 크게 보이나? (22pt+)

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

**Step 0: 메타 인지 (생략 금지)** — 편집 전 반드시 시각 확인 + 5질문 답하기.
- 모든 페이지 PNG 렌더링 → Read tool로 직접 확인
- ① 이 문서는 무엇인가? (양식·보고서·공문·계약·증빙·교재…)
- ② 누가 작성·수신하는가?
- ③ 페이지 표준이 있는가? ("1건 1매" / "1페이지 원칙" / 자유)
- ④ 보존할 부분 vs 변경할 부분? (예시·서명란·기관명·도장은 보존)
- ⑤ 결과물의 사용처? (제출·저장·인쇄·전자결재)
- → AskUserQuestion으로 분석 결과 확인 후 진행. 메타 인지 건너뛰면 단순 텍스트 치환에 머물러 사용자 의도와 어긋남.

Step A: 파일 경로 → HWP면 HWPX 변환
Step B: `extract_text()` → 내용 보여주기
Step C: 편집 유형 확인 → 텍스트 교체/양식 채우기
Step D: `unpack → 원본 문자열 교체 → pack → validate`

---

## 워크플로우 [3] 양식 채우기

**Step 0: 컨텍스트 자동 로드 (v0.17.0+, 새 채팅에서 우선 시도)**
```python
from pyhwpxlib.templates.context import load_context
ctx = load_context(name)  # 등록 양식 → 결정사항·이전 채우기 값 자동 복원
print(ctx.to_markdown())
```
또는 CLI: `pyhwpxlib template context <name>`. **이전 채팅의 합의가 살아 있다 →
사용자가 양식 다시 업로드/설명할 필요 없음.** 미등록이면 Step 0' 메타 인지로.

**Step 0': 메타 인지 (미등록 양식만)** — 워크플로우 [2]와 동일. 양식은 특히 페이지 표준이 강하므로 필수.
- "1매 표준" 양식 (지급조서·증빙·검수확인서)은 결과도 1페이지여야 함
- 양식에 포함된 **(예시) 페이지는 가이드** — 결과물에선 보통 제거
- 미리 인쇄된 항목 (사업명·기관명)은 보존, 빈 칸만 채움
- → 사용자에게 "이 양식의 결과물은 1페이지로 만드는 게 맞나요?" 확인 후
  `pyhwpxlib template add` + `template annotate --page-standard 1page --structure A/B`
  로 결과를 워크스페이스에 박제 (다음 채팅에서 자동 복원).

Step A: 프리뷰 렌더링 → Claude가 PNG 보고 양식 분석
Step B: 사용자에게 필드 입력 요청 (ctx.recent_data 가 있으면 보여주고 재사용 제안)
Step C: **구조 판정** — 인접 셀(A) vs 같은 셀(B)
- 구조 A → `fill_by_labels` 사용
- 구조 B → `unpack → 문자열 교체 → pack`
Step D: 프리뷰 검증 → Whale 확인 요청
Step E: **1페이지 fit 검증** — page_count == 1 이어야 함 (1매 표준 양식)
- 넘치면: `GongmunBuilder(autofit=True)` 로 코드에 위임 (폰트/줄간격/셀 높이 조정 알고리즘은 결정론 영역)
- autofit 후에도 실패 → 사용자에게 보고하고 수동 조정 요청 (LLM이 mm 단위로 임의 결정 금지)

Step F: **page-guard 통과 (v0.16.0+, 필수 게이트)**
```bash
pyhwpxlib page-guard --reference original_form.hwpx --output filled.hwpx
# → exit 0 (PASS) 일 때만 완료 처리. exit 1 (FAIL) 시 텍스트 압축/autofit 재시도
```

Step G: **결정사항 박제 (v0.17.0+)** — 이번 채팅에서 새로 합의한 규칙이 있으면
```bash
pyhwpxlib template annotate <name> --decision "이번에 합의한 내용"
# 결과물도 자동으로 <workspace>/outputs/YYYY-MM-DD_<key>.hwpx 에 누적되고
# history.json 에 채우기 데이터가 FIFO 10건 보존된다 (template fill 자동 호출).
```

---

## 워크플로우 [4] 문서 변환

```python
from pyhwpxlib.hwp2hwpx import convert         # HWP→HWPX
from pyhwpxlib.api import convert_html_file_to_hwpx  # HTML→HWPX
# pyhwpxlib md2hwpx input.md -o output.hwpx    # MD→HWPX
```

---

## 워크플로우 [5] 공문(기안문) 생성 — 편람 준수

행정안전부 「2025 행정업무운영 편람」 규정 자동 준수. 일반기안문 / 간이기안문 / 일괄기안 / 공동기안 지원.

```python
from pyhwpxlib.gongmun import Gongmun, GongmunBuilder, signer, validate_file

doc = Gongmun(
    기관명="행정안전부",
    수신="수신자 참조",           # "내부결재" 가능
    제목="2024년 정보공개 종합평가 계획 안내",
    본문=["...", "..."],           # 자동 1. 2. 3. 번호
    붙임=["계획서 1부."],          # 자동 "끝." 표시
    발신명의="행정안전부장관",
    기안자=signer("행정사무관", "김OO"),
    결재권자=signer("정보공개과장", "김OO", 전결=True, 서명일자="2025. 9. 30."),
    시행_처리과명="정보공개과", 시행_일련번호="000", 시행일="2025. 9. 30.",
    우편번호="30112", 도로명주소="세종특별자치시 도움6로 42",
    전화="(044)205-0000", 공개구분="대국민공개",
)
GongmunBuilder(doc).save("output.hwpx")

# 1페이지 자동 맞춤 (공문 1건-1매 원칙) — rhwp RenderTree 기반
GongmunBuilder(doc, autofit=True).save("output.hwpx")
# overflow 감지 시 spacer(6→4pt) → lineSpacing×0.9 → 상·하여백(-2mm)
# 순서로 최대 3회 자동 조정. 실패 시 WARN 로그 + 마지막 조정본 유지.

# 규정 검증 (ERROR/WARNING/INFO)
from pyhwpxlib.gongmun import format_report
print(format_report(validate_file("output.hwpx")))
```

자동 적용: 날짜 포맷(`2025. 9. 20.`) · 2타 들여쓰기 · 항목기호 8단계 · 끝표시 · 두문/본문/결문 순서 · '기안자·결재권자' 용어 생략 · 회색 구분선.

자동 검사: 위압적 어투("할 것", "~바람") · 권위적 표현("치하했다") · 차별적 표현("결손가정") · 한글호환영역 특수문자(㉮ 등) · 두음법칙 오류 · 외래어 오표기 · 끝표시 누락.

> 상세: [references/gongmun.md](references/gongmun.md) · 편람 규칙 YAML: [pyhwpxlib/gongmun/rules.yaml](../pyhwpxlib/gongmun/rules.yaml)

---

## 워크플로우 [6] 문서 분석

```python
from pyhwpxlib.json_io.overlay import extract_overlay
overlay = extract_overlay(hwpx_path)
# overlay['texts'], overlay['tables'], overlay['images']
```
BinData에서 이미지 추출 → Read tool로 내용 파악 (Vision)

---

## 워크플로우 [7] JSON ↔ HWPX (v0.15.0+, 외부 LLM/MCP 친화)

JSON 한 덩어리로 builder 19개 add_* 메서드 **전부** 표현 가능 (19/19, 100%).
heading, image, image_from_url, header/footer, lists, footnotes, equation,
highlight, shapes, page_number, page_break 모두 dispatch. v0.14.0
paragraphs/tables-only JSON 도 그대로 동작 (back-compat).

```python
from pyhwpxlib.json_io import from_json, to_json

# JSON → HWPX
data = {
    "header": {"text": "기밀"}, "footer": {"text": "회사 X"},
    "page_number": {"pos": "BOTTOM_CENTER"},
    "sections": [{
        "paragraphs": [
            {"runs": [{"content": {
                "type": "heading",
                "heading": {"text": "1. 서론", "level": 1}}}]},
            {"runs": [{"content": {"type": "text", "text": "본문..."}}]},
            {"runs": [{"content": {
                "type": "bullet_list",
                "bullet_list": {"items": ["배경", "목적", "범위"]}}}]},
            {"runs": [{"content": {
                "type": "footnote",
                "footnote": {"text": "참조", "number": 1}}}]},
        ],
        "tables": [], "page_settings": {}
    }]
}
from_json(data, "out.hwpx")

# HWPX → JSON (round-trip)
parsed = to_json("out.hwpx")
# parsed["sections"][0]["paragraphs"][...]["runs"][...]["content"]["type"] 에
# image/footnote/equation/shape_rect 자동 식별 (heading/list/highlight 는
# style-table 의존이라 0.15.0 에서는 best-effort 미지원)
```

**RunContent.type 14종**: text, table, heading, image, bullet_list,
numbered_list, nested_bullet_list, nested_numbered_list, footnote,
equation, highlight, shape_rect, shape_line, shape_draw_line.
**Paragraph flag**: `page_break: true` → `add_page_break()`.
**Top-level 3종 (deferred)**: header, footer, page_number.
**Unknown type → ValueError** (rhwp 노선: silent skip 금지).

MCP `hwpx_from_json` 도 새 schema 자동 지원 (signature 무변경).

---

## Quick Reference

| Task | Approach |
|------|----------|
| 새 문서 | `HwpxBuilder(theme='forest')` |
| 공문(기안문) | `GongmunBuilder(Gongmun(...)).save()` (편람 준수) |
| 공문 1페이지 자동 맞춤 | `GongmunBuilder(doc, autofit=True).save()` |
| 공문 규정 검증 | `validate_file("doc.hwpx")` (ERROR/WARNING/INFO) |
| 텍스트 읽기 | `extract_text()` |
| 편집 | `unpack → replace → pack` |
| **JSON → HWPX (v0.15.0+)** | `from_json(data, "out.hwpx")` — 19/19 builder 메서드 전부 도달 |
| **HWPX → JSON** | `to_json("doc.hwpx")` — image/footnote/equation/shape 자동 식별 |
| 양식 등록 (v0.13.3+) | `pyhwpxlib template add my_form.hwp --name my_form` |
| 양식 채우기 (schema) | `pyhwpxlib template fill <name> -d data.json -o out.hwpx` |
| 양식 자동 schema 진단 | `pyhwpxlib template diagnose <hwpx> --schema MANUAL.json` |
| 양식 채우기 ({{key}}) | `fill_template(data={"key": "val"})` — {{key}} 패턴 |
| 체크박스 | `fill_template_checkbox(checks=["동의함"])` |
| 이미지 삽입 | `add_image(path, width=42520, height=비율)` |
| 기존 문서에 이미지 | `insert_image_to_existing()` |
| 이미지 교체 | overlay `new_data_b64` |
| HWP→HWPX | `hwp2hwpx.convert()` |
| **검증 (dual-mode, v0.14.0+)** | `pyhwpxlib validate --mode {strict\|compat\|both}` |
| **비표준 진단/보정 (v0.14.0+)** | `pyhwpxlib doctor <file> [--fix]` |
| **page-guard (v0.16.0+)** | `pyhwpxlib page-guard --reference REF --output OUT [--threshold N]` — 강제 게이트 |
| **structure 청사진 (v0.16.0+)** | `pyhwpxlib analyze FILE --blueprint [--depth 1\|2\|3] [--json]` |
| Lint | `pyhwpxlib lint <file>` |
| Font check | `pyhwpxlib font-check <file>` |
| 테마 추출 | `extract_theme() → save_theme()` |
| 테마 목록 | `pyhwpxlib themes list` |
| 프리뷰 (SVG) | `RhwpEngine().load().render_page_svg()` |
| 프리뷰 (HTML, 경량) | `doc.render_page_html(0)` |
| 레이아웃 검증 | `doc.get_page_render_tree(0)` → bbox 좌표로 overflow 판정 |

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
| 8 | hwpx 편집 후 lineseg 정합성 검증 | 한컴 보안경고 회피 (v0.14.0+ opt-in) |
| 9 | 우리도 비표준 새로 생산 안 함 | rhwp 노선: 감지+고지+동의 후 보정 |
| **10** | **치환 우선 편집** — 양식·기존 문서 편집 시 새 문단/표 추가 대신 텍스트 노드 치환 우선 | 서식 보존, 페이지 변동 최소화 |
| **11** | **구조 변경 제한** — 사용자 명시 요청 없이 `<hp:p>` `<hp:tbl>` `rowCnt` `colCnt` 추가/삭제/분할/병합 금지 | 레퍼런스 충실도 |
| **12** | **페이지 동일 필수 (레퍼런스 작업)** — 레퍼런스 있으면 결과 쪽수 동일 | 양식·공문 신뢰도 |
| **13** | **page-guard 통과 필수** — `validate` 통과 ≠ 완료. `pyhwpxlib page-guard` 도 통과해야 완료 처리 | 강제 게이트 (v0.16.0+) |

> 상세 API, 프리셋, 표 파라미터, 편집 세부사항 → [references/](references/) 참조

### 한컴 보안경고 + rhwp 노선 (Rule 8/9 상세)

**진짜 트리거 (확정 2026-04-27)**: section*.xml 안에서 다음 조건이 단 한 번이라도
나타나면 한컴이 "문서 보안 설정을 낮춤" 경고를 띄운다:

```
<hp:lineseg textpos="N"/>  AND  N > UTF-16(paragraph 안 hp:t 텍스트 합)
```

(외부 도구가 텍스트를 짧게 바꿨는데 lineseg 캐시는 그대로 → 한컴이 외부 수정으로 판정)

**v0.14.0 정책 변경 (rhwp 노선)**: 한컴 자체가 silent reflow 로 비표준 lineseg
를 덮어 후발주자에게 비용 전가하는 구조에 동조하지 않음. `write_zip_archive` 의
silent precise fix 를 **opt-in 으로 전환**. 사용자가 명시 동의(`--fix` / `strip_linesegs="precise"`)할 때만 보정.

```python
# v0.14.0+ default — 비표준 lineseg 그대로 보존
from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive
arch = read_zip_archive(input_path)
n_fixed = write_zip_archive(output_path, arch)
# n_fixed == 0 (보정 안 함). 비표준이면 한컴 보안경고 발생 가능 → CLI는 stderr 경고

# 명시 보정 (이전 0.13.x default 동작)
n_fixed = write_zip_archive(output_path, arch, strip_linesegs="precise")
# precise = lineseg.textpos > text_len 인 lineseg 만 제거
# 다른 lineseg 는 모두 보존 → rhwp 등 외부 렌더러 캐시 유지

# 강한 망치 — linesegarray 통째 제거
write_zip_archive(output_path, arch, strip_linesegs="remove")
```

**검증 + 진단 + 보정 워크플로 (v0.14.0+)**:
```bash
# 1. 검증 (spec/compat 두 계층 분리)
pyhwpxlib validate <file>                     # default --mode both
pyhwpxlib validate <file> --mode strict       # OWPML 명세 엄격 (rhwp 정렬)
pyhwpxlib validate <file> --mode compat       # 한컴 받아들이는 범위

# 2. 진단 (감지만, 자동 fix 안 함)
pyhwpxlib doctor <file>                       # 비표준 항목 보고

# 3. 보정 (사용자 명시 동의 후)
pyhwpxlib doctor <file> --fix                 # → <file>.fixed.hwpx
pyhwpxlib doctor <file> --fix --inplace       # 같은 파일에 덮어쓰기
pyhwpxlib doctor <file> --fix -o out.hwpx     # 명시 출력 경로

# CLI 명령에 직접 --fix 플래그도 사용 가능
pyhwpxlib template fill <name> -d data.json -o out.hwpx --fix
pyhwpxlib reflow-linesegs <file>              # default --mode precise (legacy)
```

**우리 자신의 원칙** (Rule 9):
- HwpxBuilder 가 만드는 새 문서는 항상 정확한 lineseg 출력
- 외부 입력의 비표준 구조는 lint/doctor 로 **감지+고지** 하되 자동 보정 안 함
- 잘못된 입력 (unknown JSON type 등) 은 silent skip 금지 — 명시 ValueError

---

## Reference Files

| File | Contents |
|------|----------|
| [references/api_full.md](references/api_full.md) | HwpxBuilder 전체 메서드, 표 파라미터, 크기 변환 |
| [references/design_guide.md](references/design_guide.md) | 주제별 팔레트 10종, 레이아웃, QA |
| [references/editing.md](references/editing.md) | unpack/pack 상세, XML 규칙, 고급 편집 |
| [references/form_automation.md](references/form_automation.md) | fill_template, batch, schema, checkbox |
| [references/document_types.md](references/document_types.md) | 문서 유형, 프리셋, 표지, 결문 |
| [templates/README.md](templates/README.md) | 번들 양식 모음 (전정Makers 결과보고서 등) + schema |
| [references/gongmun.md](references/gongmun.md) | 공문 생성 (편람 준수) — 일반/간이/일괄/공동기안 + validator |
| [references/HWPX_RULEBOOK.md](references/HWPX_RULEBOOK.md) | Critical Rules 전체 + 상세 설명 |
| [references/rich_document_example.md](references/rich_document_example.md) | Rich Mode 골든 샘플 — 14/15 builder 메서드 활용 보고서 |

## Versions

| Version | Highlights |
|---------|------------|
| **0.17.0** | 컨텍스트 지속성 — 양식별 워크스페이스 폴더 (`~/.local/share/pyhwpxlib/templates/<name>/`) + `decisions.md` / `history.json` / `outputs/` 자동 누적 + `template context/annotate/log-fill/open/migrate/install-hook` CLI + MCP `hwpx_template_context / workspace_list / log_fill / save_session` |
| 0.16.1 | 라이선스 안전 — default 폰트 함초롬/맑은 고딕 → 나눔고딕 (SIL OFL 1.1), `pyhwpxlib/font/` 148 MB 제거, vendor NanumGothic 보존 |
| **0.16.0** | reference-fidelity-toolkit — `pyhwpxlib page-guard` 강제 게이트 (rhwp+static 이중 경로) + `pyhwpxlib analyze --blueprint` 청사진 + Critical Rules 의도 룰 4개 (#10~#13) |
| 0.15.0 | JSON 경로 19/19 builder 메서드 전부 도달 (옵션 A) — heading/image/image_from_url/list/footnote/equation/shape/header/footer/page_number/page_break, encoder rich-type emission |
| **0.14.0** | rhwp 노선 채택 — silent fix opt-in, `pyhwpxlib doctor`, `validate --mode strict\|compat\|both` |
| 0.13.4 | auto_schema cellSpan-aware grid + row-group label, `template diagnose` |
| 0.13.3 | template workflow (옵션 B) — add/fill/show/list/diagnose, XDG 계층 |
| 0.13.2 | precise textpos-overflow fix |
| 0.13.0 | 한국 공문서 표준 — 폰트/크기/여백/줄간격 |
