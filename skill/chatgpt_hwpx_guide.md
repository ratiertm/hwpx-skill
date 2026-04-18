# pyhwpxlib — 한글(HWPX) 문서 생성·편집·분석 완전 가이드

> 이 파일은 LLM(ChatGPT/Gemini/Claude 등)에서 pyhwpxlib를 사용하기 위한 통합 가이드입니다.
> GPT Builder의 Instructions 또는 Knowledge에 업로드하세요.
> 이 가이드의 모든 기능은 Code Interpreter 환경에서 동작합니다.

---

## 설치

```python
!pip install pyhwpxlib
```

설치 확인:
```python
import pyhwpxlib
print(pyhwpxlib.__version__)  # 0.7.0+
```

---

## 절대 규칙 — 반드시 지켜야 함

1. **pyhwpxlib만 사용** — XML을 직접 작성하거나 다른 라이브러리로 우회하지 않는다
2. `.hwp` 파일이 들어오면 **반드시 `pyhwpxlib.hwp2hwpx.convert()`로 HWPX 변환부터**
3. `.hwpx` 파일 읽기는 **`pyhwpxlib.api.extract_text()`** 사용
4. 새 문서 생성은 **`from pyhwpxlib import HwpxBuilder`** 사용
5. 문서 편집은 **`unpack → 문자열 교체 → pack`** 순서
6. 생성/편집 후 **반드시 validate + lint 실행**
7. **생성/편집 후 반드시 SVG 프리뷰를 생성하고 직접 확인** — 이 단계를 건너뛰지 않는다. 문제가 발견되면 자동으로 수정하고 다시 프리뷰한다.
8. `<hp:t>` 안에 `\n` 넣으면 Whale 에러 — 별도 paragraph로 분리
8. `ET.tostring()` 재직렬화 금지 — 네임스페이스 깨짐
9. 텍스트에 `&`, `<`, `>` 포함 시 자동 이스케이프됨 (xml.sax.saxutils.escape)

---

## 1. 새 문서 만들기

```python
from pyhwpxlib import HwpxBuilder

doc = HwpxBuilder(theme='forest')  # 10종 테마 중 선택
doc.add_heading("제목", level=1)
doc.add_paragraph("본문 텍스트")
doc.add_table([["항목", "내용"], ["A", "100"], ["B", "200"]])

# 이미지 삽입
doc.add_image("logo.png", width=10000, height=5000)

doc.save("output.hwpx")
```

### 테마 목록 (10종)

| 테마명 | Primary | 용도 |
|--------|---------|------|
| `default` | `#395da2` 파랑 | 공문서, 기업 보고서 |
| `forest` | `#2C5F2D` 초록 | 환경, ESG |
| `warm_executive` | `#B85042` 적갈 | 제안서 |
| `ocean_analytics` | `#065A82` 청록 | 데이터 분석 |
| `coral_energy` | `#F96167` 코랄 | 마케팅 |
| `charcoal_minimal` | `#36454F` 차콜 | 기술 문서 |
| `teal_trust` | `#028090` 청록 | 의료, 금융 |
| `berry_cream` | `#6D2E46` 와인 | 교육 |
| `sage_calm` | `#84B59F` 연초록 | 웰빙 |
| `cherry_bold` | `#990011` 빨강 | 경고 |

### 커스텀 테마 (기존 문서에서 추출)

```python
from pyhwpxlib import extract_theme, save_theme, HwpxBuilder

# 기존 문서의 스타일 추출
theme = extract_theme("reference.hwpx", name="우리회사양식")
save_theme(theme)  # ~/.pyhwpxlib/themes/ 에 저장

# 추출한 스타일로 새 문서 생성
doc = HwpxBuilder(theme='custom/우리회사양식')
```

---

## 2. HwpxBuilder 메서드 전체 목록

| 메서드 | 용도 |
|--------|------|
| `add_heading(text, level=1, alignment='LEFT')` | 제목 (1~4) |
| `add_paragraph(text, bold, italic, font_size, text_color, alignment)` | 단락 |
| `add_table(data, header_bg, cell_colors, col_widths, row_heights, merge_info, cell_styles)` | 표 |
| `add_bullet_list(items, bullet_char='•')` | 글머리 기호 목록 |
| `add_numbered_list(items, format_string='{}.'))` | 번호 목록 |
| `add_nested_bullet_list(items)` | 중첩 글머리 `[(level, text), ...]` |
| `add_nested_numbered_list(items)` | 중첩 번호 `[(level, text), ...]` |
| `add_image(path, width, height)` | 로컬 이미지 삽입 |
| `add_image_from_url(url, filename, width, height)` | URL 이미지 다운로드+삽입 |
| `add_page_break()` | 페이지 나누기 |
| `add_line()` | 구분선 |
| `add_header(text)` | 머리말 |
| `add_footer(text)` | 꼬리말 |
| `add_page_number(pos='BOTTOM_CENTER')` | 페이지 번호 |
| `add_footnote(text, number)` | 각주 |
| `add_highlight(text, color='#FFFF00')` | 하이라이트 |
| `save(path)` | 저장 |

---

## 3. 표 상세 사용법

```python
doc.add_table(
    data=[["이름", "나이", "부서"], ["홍길동", "30", "개발팀"]],
    header_bg='#395da2',           # 헤더 배경색 (None=테마 자동)
    cell_colors={(1,0): '#d8e2ff'},# 셀별 배경색
    col_widths=[12000, 8000, 22520], # 컬럼 너비 (합계=42520)
    row_heights=[2400, 2000],      # 행 높이
    merge_info=[(0,0,0,2)],        # 병합 [(r1,c1,r2,c2)]
    cell_aligns={(1,2): 'RIGHT'},  # 셀별 정렬
    cell_styles={(0,0): {'text_color':'#ffffff','bold':True,'font_size':12}},
)
```

**col_widths 계산법**: A4 content width = 42520. 내용 길이 비율로 분배.
- 예: ['항목'(2글자), '설명'(20글자)] → col_widths=[8000, 34520]

**디자인 박스** (표를 활용한 하이라이트/콜아웃):

```python
# 하이라이트 박스
doc.add_table([['핵심 요약 내용']],
    cell_colors={(0,0): '#d8e2ff'}, header_bg='',
    cell_margin=(400,400,300,300), use_preset=False)

# 경고 박스
doc.add_table([['주의사항']],
    cell_colors={(0,0): '#f5d0cb'}, header_bg='',
    cell_margin=(400,400,300,300), use_preset=False)
```

---

## 4. 기존 문서 읽기

```python
from pyhwpxlib.api import extract_text
text = extract_text("document.hwpx")
print(text)
```

### JSON으로 구조화 추출 (텍스트 + 표 + 이미지)

```python
from pyhwpxlib.json_io.overlay import extract_overlay
overlay = extract_overlay("document.hwpx")

# overlay['texts']  — 본문 텍스트 목록
# overlay['tables'] — 표 목록 (id, context, rows, cols)
# overlay['images'] — 이미지 메타데이터
```

---

## 5. 기존 문서 편집 (Overlay 방식)

원본 서식 100% 보존하면서 텍스트만 교체:

```python
from pyhwpxlib.json_io.overlay import extract_overlay, apply_overlay

overlay = extract_overlay("template.hwpx")

# 텍스트 교체
for t in overlay['texts']:
    t['value'] = t['value'].replace('울산중부소방서', '강남구청')

# 적용 (원본 서식 보존)
apply_overlay("template.hwpx", overlay, "output.hwpx")
```

### Unpack/Pack 방식 (직접 XML 편집)

```python
import subprocess
subprocess.run(["pyhwpxlib", "unpack", "doc.hwpx", "-o", "unpacked/"])

# unpacked/Contents/section0.xml 수정 (문자열 교체만!)
with open('unpacked/Contents/section0.xml', 'r') as f:
    xml = f.read()
xml = xml.replace('>기존 텍스트<', '>새 텍스트<', 1)
with open('unpacked/Contents/section0.xml', 'w') as f:
    f.write(xml)

subprocess.run(["pyhwpxlib", "pack", "unpacked/", "-o", "output.hwpx"])
```

---

## 6. 문서 변환

```python
# HWP 5.x → HWPX
from pyhwpxlib.hwp2hwpx import convert
convert("input.hwp", "output.hwpx")

# Markdown → HWPX
subprocess.run(["pyhwpxlib", "md2hwpx", "input.md", "-o", "output.hwpx"])

# HTML → HWPX
from pyhwpxlib.api import convert_html_file_to_hwpx
convert_html_file_to_hwpx("input.html", "output.hwpx")

# HWPX → HTML
from pyhwpxlib.api import convert_hwpx_to_html
convert_hwpx_to_html("input.hwpx", "output.html")
```

---

## 7. 양식 채우기

```python
from pyhwpxlib.api import fill_template_checkbox

fill_template_checkbox("form.hwpx",
    data={"성 명": "홍길동", "연락처": "010-1234-5678"},
    checks=["동의함"],  # 체크박스 체크
    output_path="filled.hwpx")
```

### 체크박스 4패턴 자동 인식
- `□` → `■`
- `☐` → `☑`
- `[  ]` → `[■]`
- `[ ]` → `[■]`

---

## 8. 이미지 처리

### 이미지 추출 (문서 → 파일)

```python
import zipfile, os
os.makedirs('/tmp/images', exist_ok=True)
with zipfile.ZipFile("document.hwpx") as z:
    for name in z.namelist():
        if name.startswith('BinData/'):
            data = z.read(name)
            fname = name.split('/')[-1]
            with open(f'/tmp/images/{fname}', 'wb') as f:
                f.write(data)
```

### 기존 문서에 이미지 추가

```python
from pyhwpxlib.api import insert_image_to_existing

insert_image_to_existing(
    hwpx_path="document.hwpx",
    image_path="photo.png",
    output_path="document_with_image.hwpx",
    width=21260,     # ~75mm
    height=15000,    # ~53mm
    position='end',  # 'end' 또는 'start'
)
```

### 기존 이미지 교체

```python
import base64
from pyhwpxlib.json_io.overlay import extract_overlay, apply_overlay

overlay = extract_overlay("doc.hwpx")
for img in overlay['images']:
    with open("new_image.png", "rb") as f:
        img['new_data_b64'] = base64.b64encode(f.read()).decode()
apply_overlay("doc.hwpx", overlay, "output.hwpx")
```

---

## 9. 검증 + 프리뷰

### 9-1. 구조/렌더링 검증

```python
import subprocess

# 구조 검증
subprocess.run(["pyhwpxlib", "validate", "output.hwpx"])

# 렌더링 위험 검사
subprocess.run(["pyhwpxlib", "lint", "output.hwpx"])

# 폰트 확인
subprocess.run(["pyhwpxlib", "font-check", "output.hwpx"])
```

### 9-2. SVG 프리뷰 생성 + 시각 검토 (생략 금지)

HWPX를 생성/편집/변환한 후에는 반드시 SVG 프리뷰를 생성하고 직접 확인한다.

```python
try:
    from pyhwpxlib.rhwp_bridge import RhwpEngine
    engine = RhwpEngine()
    doc = engine.load("output.hwpx")
    for i in range(doc.page_count):
        svg = doc.render_page_svg(i, embed_fonts=True)
        with open(f"/tmp/preview_page{i}.svg", "w") as f:
            f.write(svg)
        # SVG를 이미지로 변환하여 확인
        try:
            import cairosvg
            cairosvg.svg2png(url=f"/tmp/preview_page{i}.svg",
                           write_to=f"/tmp/preview_page{i}.png", output_width=800)
        except ImportError:
            pass  # SVG 파일 직접 확인
except ImportError:
    print("프리뷰 엔진 미설치. pip install pyhwpxlib[preview]")
    print("validate + lint로 검증합니다.")
```

프리뷰가 안 되는 환경(wasmtime 미설치)에서는 validate + lint로 대체한다.

### 9-3. 시각 검토 7가지 체크포인트

프리뷰 이미지를 보면서 반드시 아래 항목을 확인한다:

1. **시각적 계층** — 제목/소제목/본문 크기 차이가 충분한가? (2배 이상)
2. **색상 & 대비** — 테마 primary 색상이 적용됐나? 표 헤더 위 텍스트가 읽히나?
3. **타이포그래피** — 폰트 깨짐(□), 글자 겹침 없나?
4. **레이아웃** — 넘침/잘림/빈 페이지 없나? 여백 균등한가?
5. **표 스타일** — 헤더 배경색, 셀 패딩, 컬럼 너비 적절한가?
6. **원본 대조** (편집 시) — 원본과 같은 구조인가? 교체 안 된 텍스트 없나?
7. **AI 패턴 피하기** — 모든 섹션 동일 레이아웃? 텍스트만 있는 섹션?

문제 발견 시 자동 수정하고 다시 프리뷰한다.

### 9-4. JSON 출력 (자동화용)

```python
subprocess.run(["pyhwpxlib", "validate", "output.hwpx", "--json"])
subprocess.run(["pyhwpxlib", "lint", "output.hwpx", "--json"])
subprocess.run(["pyhwpxlib", "font-check", "output.hwpx", "--json"])
```

---

## 10. 문서 프리셋 (공문서/보고서/제안서)

```python
from pyhwpxlib.presets import get_preset, build_cover_page, build_official_footer

preset = get_preset('report')  # 'official' | 'report' | 'proposal'
doc = HwpxBuilder(theme='ocean_analytics')

# 표지 생성
build_cover_page(doc, preset,
    title="AI 기반 공공서비스 혁신 방안",
    subtitle="최종 보고서",
    organization="한국정보화진흥원",
    date="2026년 4월")

# 본문 ...

# 공문서 결문
build_official_footer(doc, preset,
    sender="행정안전부장관",
    drafter="사무관 홍길동",
    reviewer="서기관 김철수",
    approver="국장 이영희",
    doc_number="디지털정부국-2026-456",
    date="2026. 4. 19.")
```

| 프리셋 | 용도 | 제목 크기 | 번호 체계 |
|--------|------|----------|-----------|
| `official` | 공문서 | 16pt | 1. 가. 1) |
| `report` | 보고서 | 18pt | 제1장 제1절 |
| `proposal` | 제안서 | 22pt | 1. 1.1 |

---

## 11. 테마 관리

```python
# 테마 목록 보기
subprocess.run(["pyhwpxlib", "themes", "list"])

# 기존 문서에서 테마 추출 + 저장
subprocess.run(["pyhwpxlib", "themes", "extract", "-i", "ref.hwpx", "-n", "사내양식"])

# 저장된 테마 삭제
subprocess.run(["pyhwpxlib", "themes", "delete", "-n", "사내양식"])
```

---

## Critical Rules 전체 목록

| # | 규칙 | 위반 시 |
|---|------|---------|
| 1 | `<hp:t>` 안에 `\n` 금지 | Whale 에러 |
| 2 | ET.tostring 재직렬화 금지 | 네임스페이스 변경 → Whale 에러 |
| 3 | 원본 문자열 직접 교체만 사용 | 서식 100% 보존 유일한 방법 |
| 4 | mimetype STORED (ZIP 첫 엔트리) | OPC 규격 필수 |
| 5 | `<a href>` 제거 | fieldBegin/fieldEnd Whale 에러 |
| 6 | condense 보존 | JUSTIFY 글자 벌어짐 방지 |
| 7 | header/footer는 SecPr 뒤에 삽입 | HwpxBuilder가 자동 처리 |
| 8 | 셀 내 긴 텍스트는 30자 기준 줄바꿈 | rhwp 자동 줄바꿈 안 함 |
| 9 | 긴 표는 ~15행 단위 분할 + page_break | 표 자동 분할 안 됨 |
| 10 | 표 높이 수정 시 sz + cellSz 둘 다 변경 | 한쪽만 바꾸면 적용 안 됨 |
| 11 | HWP Color는 BGR 순서 | 0xFF0000 = 파란색 |
| 12 | breakNonLatinWord = KEEP_WORD | BREAK_WORD 시 글자 퍼짐 |
| 13 | 원문 텍스트 보존 — 요약·재작성·생략 금지 | 원문 왜곡 방지 |
| 14 | LLM은 스타일링은 자유롭게, 내용은 충실하게 | 디자인은 판단, 텍스트는 보존 |

---

## 디자인 규칙

1. **주제에 맞는 테마 선택** — 파란색 디폴트 금지
2. **매 섹션마다 시각 요소** — 텍스트만 있는 섹션 금지 (표/박스/목록 최소 1개)
3. **같은 레이아웃 반복 금지** — 표→목록→박스→인용문 순환
4. **이미지 적극 활용** — 사용자가 이미지를 제공하면 반드시 삽입
5. **검증 필수** — 생성 후 validate + lint 실행

---

## 흔한 실수

| 실수 | 올바른 방법 |
|------|------------|
| XML 직접 작성 | HwpxBuilder 사용 |
| `\n`으로 줄바꿈 | 별도 `add_paragraph()` 호출 |
| 기본 파란색만 사용 | 주제에 맞는 테마 선택 |
| `from hwpx import ...` | `from pyhwpxlib import ...` |
| 이미지 없이 텍스트만 | `add_image()` 적극 활용 |
| 검증 없이 전달 | `validate` + `lint` 필수 |

---

## 대화형 워크플로우 — 사용자에게 단계별로 질문하며 진행

사용자의 요청이 구체적이지 않으면 먼저 물어본다:

```
"어떤 작업을 하시겠어요?"

1. 새 문서 만들기 — 보고서, 공문서, 양식 등
2. 기존 문서 편집 — 텍스트/서식 수정
3. 양식 자동화 — 데이터 채우기, 다건 생성
4. 문서 변환 — HWP→HWPX, MD→HWPX 등
5. 문서 분석 — 텍스트·표·이미지 추출 + 내용 파악
```

### 워크플로우 [1] 새 문서 만들기
1. "어떤 유형?" → 정부양식/공문서/보고서/제안서/자유
2. 저장된 커스텀 양식이 있으면 먼저 제안 (themes list 확인)
3. "내용을 알려주세요" → 사용자 입력
4. 주제에 맞는 테마 선택 + HwpxBuilder로 생성
   - 이미지가 필요하면 사용자에게 파일 요청
5. validate + lint 실행
6. **SVG 프리뷰 생성 → 직접 확인 → 7가지 체크포인트 점검**
7. "Whale에서도 확인해주세요. 수정할 부분 있나요?"
8. 완성되면: "이 스타일을 양식으로 저장할까요?" → extract_theme + save_theme

### 워크플로우 [2] 기존 문서 편집
1. "파일을 업로드해주세요" (HWP인 경우 자동 HWPX 변환)
2. extract_text로 내용을 보여주기
3. "어떤 편집?" → 텍스트 교체/구조 수정/양식 채우기
4. overlay 또는 unpack → 수정 → apply/pack
5. validate + lint + **SVG 프리뷰 확인**
6. "수정할 부분 있나요?"

### 워크플로우 [3] 양식 채우기
1. "양식 파일을 업로드해주세요"
2. **SVG 프리뷰 렌더링 → 이미지를 보고 양식 분석** (빈 칸 식별, 필드 이름 부여)
3. 분석 결과를 사용자에게 보여주고 입력값 요청
4. fill_template 또는 unpack → 문자열 교체 → pack
5. **SVG 프리뷰로 결과 검증**
6. "Whale에서 확인해주세요"
7. 완성되면 양식 저장 제안

### 워크플로우 [4] 문서 변환
1. "변환 유형?" → HWP→HWPX / MD→HWPX / HTML→HWPX
2. 변환 실행
3. validate + lint
4. "다음 작업?" → 편집/추가 변환/완료

### 워크플로우 [5] 문서 분석
1. "분석할 파일을 업로드해주세요"
2. HWP인 경우 자동 HWPX 변환
3. extract_overlay로 텍스트 + 표 + 이미지 메타데이터 추출
4. BinData에서 이미지 파일 추출 → 각 이미지 내용 파악:
   - 사진이면: 무엇이 찍혀 있는지 설명
   - 로고/아이콘이면: 텍스트와 의미
   - 차트/그래프면: 데이터를 표로 변환
5. 구조화된 분석 결과를 사용자에게 제공
6. "JSON으로 내보내거나 특정 표/이미지를 자세히 볼 수 있습니다"

### 모든 워크플로우의 마지막
- "수정할 부분이 있으면 알려주세요" → 만족할 때까지 반복
- 완성된 문서는 사용자에게 파일로 전달

---

*pyhwpxlib v0.7.0+ | PyPI: https://pypi.org/project/pyhwpxlib/ | GitHub: https://github.com/ratiertm/hwpx-skill*
