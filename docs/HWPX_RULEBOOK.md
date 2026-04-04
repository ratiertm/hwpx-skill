# HWPX 생성 룰북

python-hwpx로 HWPX 문서를 만들 때 반드시 지켜야 하는 규칙.
이 규칙을 어기면 Whale/한컴오피스에서 파일이 열리지 않음.

## 1. 셀 텍스트에 줄바꿈 금지 (직접 \n)

```python
# ❌ 에러 발생
tbl.set_cell_text(0, 0, "첫줄\n둘째줄")

# ✅ 정상 (set_cell_text 내부에서 \n → 별도 <hp:p>로 분리)
# 2026-03-29 수정 완료 — 이제 \n 사용 가능
tbl.set_cell_text(0, 0, "첫줄\n둘째줄")
```

**원인**: HWPX에서 셀 내 줄바꿈은 `<hp:t>` 안의 `\n` 문자가 아니라, `<hp:subList>` 안에 별도 `<hp:p>` 요소로 표현해야 함.

**수정**: `text.setter`에서 `\n` 감지 시 자동으로 `<hp:p>` 분리 처리.

## 1-1. linesegarray 규칙 (글자 겹침 방지)

```xml
<!-- ✅ secPr 포함 첫 문단에만 linesegarray 1개 -->
<hp:p>
  <hp:run charPrIDRef="0"><secPr .../></hp:run>
  <hp:linesegarray>
    <hp:lineseg textpos="0" vertpos="0" vertsize="1000" textheight="1000"
                baseline="850" spacing="600" horzpos="0" horzsize="42520" flags="393216"/>
  </hp:linesegarray>
</hp:p>

<!-- ✅ 나머지 문단에는 linesegarray 없음 — 한컴이 자동 계산 -->
<hp:p paraPrIDRef="0">
  <hp:run charPrIDRef="0"><hp:t>텍스트</hp:t></hp:run>
</hp:p>
```

**규칙**:
- `linesegarray`는 **secPr 포함 첫 문단에만** 1개
- 나머지 모든 `<hp:p>` (본문, 셀 내부)에는 **넣지 않음**
- 한컴오피스가 열 때 자동으로 레이아웃 재계산

**❌ 잘못 넣으면**: 모든 줄이 겹쳐서 렌더링됨 (vertpos 충돌)

## 1-2. secPr 문단에 텍스트 금지

```xml
<!-- ❌ secPr과 텍스트를 같은 p에 넣으면 겹침 발생 -->
<hp:p>
  <hp:run><secPr .../></hp:run>
  <hp:run><hp:t>제목 텍스트</hp:t></hp:run>
</hp:p>

<!-- ✅ secPr은 빈 문단, 텍스트는 다음 p -->
<hp:p>
  <hp:run><secPr .../></hp:run>
  <hp:linesegarray>...</hp:linesegarray>
</hp:p>
<hp:p>
  <hp:run><hp:t>제목 텍스트</hp:t></hp:run>
</hp:p>
```

**원인**: secPr 문단에 텍스트를 합치면 표/텍스트 위치가 겹침. python-hwpx(공식)도 secPr을 빈 문단으로 분리.

## 1-3. paraPr에 lineSpacing 필수

```xml
<!-- ❌ lineSpacing 없으면 글자 겹침 -->
<hh:paraPr id="20" tabPrIDRef="0" condense="0">
  <hh:align horizontal="CENTER" vertical="BASELINE"/>
</hh:paraPr>

<!-- ✅ lineSpacing 필수 -->
<hh:paraPr id="20" tabPrIDRef="0" condense="0">
  <hh:align horizontal="CENTER" vertical="BASELINE"/>
  <hh:lineSpacing type="PERCENT" value="150" unit="HWPUNIT"/>
</hh:paraPr>
```

**원인**: paraPr에 `<hh:lineSpacing>`이 없으면 한컴오피스가 줄 간격을 0으로 처리하여 모든 줄이 같은 위치에 겹침.

**규칙**: 새로 만드는 paraPr에는 반드시 `lineSpacing` 포함. 원본 서식 기본값: `type="PERCENT" value="150"`.

| value | 의미 |
|-------|------|
| 100 | 1줄 (빽빽) |
| 120 | 1.2줄 (구비서류 등 좁은 간격) |
| 150 | 1.5줄 (표준, 가장 흔함) |
| 160 | 1.6줄 (hwpxlib 기본) |

## 2. 셀 병합: 빈 행 금지

```python
# ❌ 에러 — 행4,5가 셀 0개 (빈 행)
tbl.merge_cells(3, 0, 5, 0)   # 라벨 세로 병합
tbl.merge_cells(3, 1, 5, 3)   # 내용 블록 병합 → 행4,5 모든 셀 제거됨

# ✅ 정상 — 모든 행에 최소 1개 셀
tbl.merge_cells(3, 0, 5, 0)   # 라벨 세로 병합
tbl.merge_cells(3, 1, 3, 3)   # 행3 가로 병합
tbl.merge_cells(4, 1, 4, 3)   # 행4 가로 병합
tbl.merge_cells(5, 1, 5, 3)   # 행5 가로 병합
```

**원인**: 세로 병합으로 col0 셀 제거 + 블록 병합으로 col1~3 셀 제거 = 빈 행. HWPX는 빈 `<hp:tr>` 허용 안 함.

**규칙**: 병합 후 **모든 `<hp:tr>`에 최소 1개의 `<hp:tc>`** 가 있어야 함.

## 3. 셀 병합: 피병합 셀은 물리적 제거

```xml
<!-- ❌ 잘못된 구조 (이전 방식) -->
<hp:tr>
  <hp:tc>주 셀 colSpan=2</hp:tc>
  <hp:tc>피병합 셀 (span=1, size=0으로만 변경)</hp:tc>  <!-- 남아있으면 안됨 -->
</hp:tr>

<!-- ✅ 올바른 구조 (한컴 실제 파일) -->
<hp:tr>
  <hp:tc>주 셀 colSpan=2</hp:tc>
  <!-- 피병합 셀 물리적으로 없음 -->
</hp:tr>
```

**수정**: `merge_cells`에서 피병합 셀을 `row_element.remove(element)` 로 제거.

## 4. 셀 패딩: hasMargin="1" 필수

```python
# ❌ 패딩 무시됨
cell.set_margin(left=400, right=400, top=250, bottom=250)
# hasMargin="0" 이면 한컴오피스가 cellMargin을 무시

# ✅ 패딩 적용됨 (수정 완료)
cell.set_margin(left=400, right=400, top=250, bottom=250)
# 내부에서 자동으로 hasMargin="1" 설정
```

## 5. 하이퍼링크: 6-param 구조

```xml
<!-- 한컴 실제 파일과 동일한 구조 -->
<hp:fieldBegin id="..." type="HYPERLINK" name="" editable="0" dirty="0" zorder="-1" fieldid="...">
  <hp:parameters cnt="6" name="">
    <hp:integerParam name="Prop">0</hp:integerParam>
    <hp:stringParam name="Command">https\://example.com;1;0;0;</hp:stringParam>
    <hp:stringParam name="Path">https://example.com</hp:stringParam>
    <hp:stringParam name="Category">HWPHYPERLINK_TYPE_URL</hp:stringParam>
    <hp:stringParam name="TargetType">HWPHYPERLINK_TARGET_BOOKMARK</hp:stringParam>
    <hp:stringParam name="DocOpenType">HWPHYPERLINK_JUMP_CURRENTTAB</hp:stringParam>
  </hp:parameters>
</hp:fieldBegin>
```

- Command: 콜론을 `\:` 로 이스케이프, 뒤에 `;1;0;0;` 접미사
- cnt="6" (3개만 넣으면 Whale에서 안 보임)

## 6. 단 구분선: 3개 속성 모두 필요

```xml
<!-- ❌ type만 넣으면 렌더링 안됨 -->
<hp:colLine type="SOLID"/>

<!-- ✅ 3개 다 필요 -->
<hp:colLine type="SOLID" width="0.12 mm" color="#000000"/>
```

`set_columns(separator_type="SOLID")` 호출 시 자동으로 기본값 채움.

## 7. HTML 태그 금지

HWPX에는 HTML 대응이 없음. LLM이 `<iframe>`, `<div>`, `<style>` 등을 생성하면 에러.

- LLM 프롬프트에 "NEVER use HTML tags" 명시
- 변환기에서 `re.sub(r'<[^>]+>', '', content)` 로 자동 제거

## 8. CSS→HWPX 매핑 규칙

| CSS | HWPX | 단위 변환 |
|-----|------|----------|
| `font-size: 16px` | `charPr height="1000"` | 1px ≈ 75 hwpunit |
| `font-size: 2em` | `height = em * body_pt * 100` | body 기준 상대값 |
| `font-size: 11pt` | `height = pt * 100` | 직접 변환 |
| `line-height: 1.5` | `lineSpacing value="150"` | × 100 |
| `padding: 6px 13px` | `cellMargin left="975" top="450"` | px × 75 |
| `border-bottom: 1px` | `line_width="71"` | 1mm = 283 |

## 9. 표 열 너비: 콘텐츠 기반

```python
# 페이지 폭에 맞추고, 내용 길이에 비례 배분
page_width = 42520  # A4 body
col_max_len = [최대 텍스트 길이 per column]  # CJK는 2배
col_widths = [page_width * len / total for each column]
tbl = doc.add_table(rows, cols, width=page_width)
# cellSz width를 col_widths로 개별 설정
```

## 10. 양식 + 데이터 분리 패턴

```python
# Step 1: 양식 생성 (한 번)
doc = HwpxDocument.new()
tbl = doc.add_table(8, 4)
tbl.merge_cells(...)
tbl.set_cell_background(...)
doc.save_to_path("template.hwpx")

# Step 2: 데이터 채우기 (반복)
doc = HwpxDocument.open("template.hwpx")
tbl = doc.sections[0].paragraphs[?].tables[0]
tbl.set_cell_text(0, 1, "홍길동")
doc.save_to_path("filled_홍길동.hwpx")
```

## 11. Whale 뷰어 한계

Whale이 렌더링하지 못하는 기능 (XML은 정상, 한컴오피스에서만 확인 가능):

- 페이지 번호 (`<hp:pageNum>`)
- 자동 번호 (`<hp:autoNum>`)
- 머리말/꼬리말 (`header/footer`)
- 도형 (arc, polygon, equation)
- 하이퍼링크 (`<hp:fieldBegin type="HYPERLINK">`)
- 이미지 (insert_image)

## 12. 병합 순서 가이드

```
의견제출서 8행 4열 예시:

         col0          col1        col2        col3
row0  │ 1.명칭      │  (입력)  │ 소속기관  │  (입력)  │
row1  │ 2.직위      │  (입력)  │ 전화번호  │  (입력)  │
row2  │ 3.의견취지  │  (입력 ← col1+2+3 가로병합)     │
row3  │            ↕│  (입력 ← col1+2+3 가로병합)     │
row4  │ 4.의견내용  ↕│  (입력 ← col1+2+3 가로병합)     │
row5  │            ↕│  (입력 ← col1+2+3 가로병합)     │
row6  │ 5.첨부서류  │  (입력 ← col1+2+3 가로병합)     │
row7  │ 6.비고      │  (입력 ← col1+2+3 가로병합)     │

병합 호출 순서:
1. merge_cells(2, 1, 2, 3)   # 가로
2. merge_cells(3, 0, 5, 0)   # 세로 (라벨)
3. merge_cells(3, 1, 3, 3)   # 행3 가로
4. merge_cells(4, 1, 4, 3)   # 행4 가로
5. merge_cells(5, 1, 5, 3)   # 행5 가로
6. merge_cells(6, 1, 6, 3)   # 가로
7. merge_cells(7, 1, 7, 3)   # 가로

핵심: 세로 병합 후 각 행의 나머지 열을 개별 가로 병합
      → 모든 행에 최소 1개 셀 유지
```

## 13. HWPX 파일 생성 시 필수 구조

```
HWPX (ZIP)
├── mimetype                    → "application/hwp+zip" (고정)
├── version.xml                 → 버전 정보
├── Contents/
│   ├── header.xml              → 폰트, charPr, paraPr, borderFill, style 정의
│   ├── section0.xml            → 본문 (페이지 설정 + 문단/표)
│   └── content.hpf             → 파일 매니페스트
├── settings.xml                → 커서 위치 등
├── Preview/PrvText.txt         → 미리보기 텍스트
└── META-INF/
    ├── container.xml           → OPC 루트
    └── manifest.xml            → ODF 매니페스트
```

## 14. section0.xml 문단 구조 규칙 (2026-04-04 검증)

### 14-1. p 수 최소화 — 1페이지 배치 핵심

서식 문서는 **p(문단) 수가 적을수록** 한 페이지에 들어갈 확률이 높다.
불필요한 p가 추가되면 표가 다음 페이지로 밀린다.

```xml
<!-- ❌ p가 3개 → 표가 2페이지로 밀림 -->
<hp:p>secPr</hp:p>
<hp:p>제목 텍스트</hp:p>      ← 불필요한 p
<hp:p>표</hp:p>

<!-- ✅ p가 2개 → 한 페이지에 들어감 (원본 패턴) -->
<hp:p>secPr + 제목 텍스트 + linesegarray</hp:p>
<hp:p>표</hp:p>
```

### 14-2. secPr 문단 + 표 앞 텍스트 배치

**상황별 규칙:**

| 상황 | 올바른 방식 |
|------|-----------|
| 표 앞 텍스트 있음 (서식) | secPr p에 텍스트 run 합침 |
| 표 앞 텍스트 없음 | secPr p 단독 |
| 표 없이 본문만 | secPr p 단독 + 텍스트 별도 p |

```xml
<!-- ✅ 서식: secPr p에 제목 텍스트 포함 -->
<hp:p paraPrIDRef="8">
  <hp:run charPrIDRef="4"><hp:secPr ...>페이지설정</hp:secPr></hp:run>
  <hp:run charPrIDRef="4"><hp:t>[별지 제11호 서식](97. 12. 31. 개정)</hp:t></hp:run>
  <hp:linesegarray><hp:lineseg .../></hp:linesegarray>
</hp:p>
<hp:p paraPrIDRef="1">
  <hp:run charPrIDRef="4"><hp:tbl ...>표</hp:tbl></hp:run>
</hp:p>
```

### 14-3. linesegarray 규칙

- secPr 포함 첫 문단에만 1개
- 나머지 모든 `<hp:p>` (본문, 셀 내부)에는 넣지 않음
- 한컴오피스가 열 때 자동으로 레이아웃 재계산

### 14-4. 셀 내 줄바꿈

- `<hp:subList>` 안에 별도 `<hp:p>`로 분리
- linesegarray 불필요 (한컴 자동 계산)

## 15. 서식 표 사이즈 규칙 (별지 리버스)

상세 문서: [OWPML_TABLE_SIZING.md](OWPML_TABLE_SIZING.md)

```python
# 표 너비 = 본문영역 - outMargin×2
text_area = page_width - margin_left - margin_right
table_width = text_area - 280  # outMargin 140×2

# cellSz = span 범위 컬럼/행 합
width = sum(col_widths[col : col + colSpan])
height = sum(row_heights[row : row + rowSpan])
```

| 항목 | 규칙 |
|------|------|
| cellSz.width | `sum(col_widths[col:col+colSpan])` — 별도 컬럼 정의 없음 |
| cellSz.height | `sum(row_heights[row:row+rowSpan])` |
| cellMargin | 기본 `141/141/141/141`, hasMargin="0"이면 무시 |
| charPr.height | 글자 크기 (100=1pt), 제목 1500~1800, 본문 1000~1100 |
| charPr.textColor | `#RRGGBB`, bold는 `<hh:bold/>` 태그 유무 |
| spacing (자간) | charPr 하위 `<hh:spacing hangul="30"/>` (0=기본) |

## 15-1. 중첩 표 구조 (2026-04-04 리버스)

### 컨테이너 표 패턴

복잡한 서식은 **표 안에 표**를 넣는 구조:

```
컨테이너 표 (1×1 또는 N×1)
└── 셀(0,0)
    └── <hp:subList>
        └── <hp:p>
            └── <hp:run>
                └── <hp:tbl> ← 중첩 표 1
        └── <hp:p>
            └── <hp:run>
                └── <hp:tbl> ← 중첩 표 2
```

**특징:**
- 컨테이너 표의 `rowCnt×colCnt`는 `1×1` 또는 `2×1` 등 소형
- 실제 데이터는 중첩 표들에 있음
- 중첩 표의 셀 주소(colAddr, rowAddr)는 중첩 표 기준 (컨테이너 기준 아님)
- 중첩은 3단계 이상도 가능 (표 > 셀 > 표 > 셀 > 표)

### 리버스 시 주의

```python
# ❌ 모든 .//hp:tbl을 같은 레벨로 취급
for tbl in root.findall('.//hp:tbl'):  # 중첩 표도 포함됨

# ✅ 직계 표만 (run 직계 자식)
for run in p.findall('hp:run'):
    for tbl in run.findall('hp:tbl'):  # 최상위 표만
        # 중첩 표는 재귀 탐색
        for tc in tbl.findall('.//hp:tc'):
            for nested_tbl in tc.findall('.//hp:tbl'):
                ...
```

### 페이지 단위 구조

```
section0.xml
├── p[0]: secPr + 1페이지 표 (또는 secPr만)
├── p[1]: 텍스트 또는 2페이지 표
├── p[2]: 컨테이너 표 (중첩 표 포함)
└── p[N]: ...
```

**페이지 구분**: secPr이 있는 p가 새 페이지 시작. 단, 한 section에 secPr은 1개이므로 표의 `pageBreak="CELL"` 속성으로 페이지가 나뉨.

## 16. 한 페이지 서식 사이즈 계산 (2026-04-04 검증)

서식을 한 페이지에 넣으려면 **콘텐츠 총 높이 < 본문 가용 높이** 여야 한다.

### 사이즈 공식

```
A4: 59528 × 84188 (210 × 297mm)

본문 가용 높이 = page.height - margin.top - margin.bottom
             예: 84188 - 4252 - 4252 = 75684 (267mm)

콘텐츠 총 높이 = 표 앞 텍스트 높이 + 표 높이 + outMargin
             예: 제목 1100 + 표 67044 + outMargin 280 = 68424

한 페이지 조건: 콘텐츠 총 높이 < 본문 가용 높이
             예: 68424 < 75684 ✅
```

### 높이 계산 요소

| 요소 | 계산 | 단위 |
|------|------|------|
| 텍스트 줄 높이 | charPr.height (예: 1100 = 11pt) | HWP Unit |
| 줄 간격 | lineSpacing value (예: 150 = 1.5배) | % |
| 표 높이 | `sum(row_heights)` 또는 `tbl.sz.height` | HWP Unit |
| 표 마진 | outMargin.top + outMargin.bottom | HWP Unit |
| 페이지 마진 | margin.top + margin.bottom | HWP Unit |

### 표 높이가 넘칠 때 대처

1. **행 높이 줄이기**: 빽빽한 서식은 행 높이 1500~2500 사용
2. **마진 줄이기**: 정부 서식은 margin 1416~5104 (기본 8504보다 좁음)
3. **폰트 크기 줄이기**: 800~900 사용 (기본 1000~1100)
4. **p 수 최소화**: secPr p에 텍스트 합치기 (규칙 14-1)

### 마진 프리셋

| 유형 | left/right | top/bottom | 본문 가용 높이 |
|------|-----------|-----------|-------------|
| 일반 문서 | 8504 (30mm) | 5668/4252 | 74266 (262mm) |
| 정부 서식 표준 | 5104 (18mm) | 4252 (15mm) | 75684 (267mm) |
| 좁은 서식 | 4000 (14mm) | 4000 (14mm) | 76188 (269mm) |
| 극소 마진 | 1416 (5mm) | 2836/1416 | 79936 (282mm) |

## 17. paraPr 생성 규칙 (2026-04-04 검증)

### 커스텀 paraPr 생성 시 필수: 기존 paraPr deep copy

```python
# ❌ align만 넣으면 글자 겹침 발생
new_pp = SubElement(container, "paraPr")
new_pp.set("id", pid)
SubElement(new_pp, "align").set("horizontal", "CENTER")
# heading, breakSetting, autoSpacing, switch(lineSpacing/margin) 전부 누락!

# ✅ 기존 paraPr[0]을 deep copy한 후 horizontal만 변경
import copy
new_pp = copy.deepcopy(base_paraPr_element)
new_pp.set("id", pid)
new_pp.find("align").set("horizontal", "CENTER")
```

### paraPr 필수 자식 요소

```xml
<hh:paraPr id="0" tabPrIDRef="0" condense="0" fontLineHeight="0"
           snapToGrid="0" suppressLineNumbers="0" checked="0">
  <hh:align horizontal="CENTER" vertical="BASELINE"/>
  <hh:heading type="NONE" idRef="0" level="0"/>
  <hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="BREAK_WORD"
                   widowOrphan="0" keepWithNext="0" keepLines="0"
                   pageBreakBefore="0" lineWrap="BREAK"/>
  <hh:autoSpacing eAsianEng="0" eAsianNum="0"/>
  <hp:switch>
    <hp:case ...>
      <hh:margin>...</hh:margin>
      <hh:lineSpacing type="PERCENT" value="150" unit="HWPUNIT"/>
    </hp:case>
    <hp:default>
      <hh:margin>...</hh:margin>
      <hh:lineSpacing type="PERCENT" value="150" unit="HWPUNIT"/>
    </hp:default>
  </hp:switch>
</hh:paraPr>
```

**align만 있고 나머지가 없으면**: lineSpacing이 없어서 줄 간격 0 → 글자 겹침

### 기존 paraPr 재사용 우선

같은 horizontal 정렬이 이미 있으면 새로 만들지 말고 기존 id 재사용:
```python
# margin 변경 없는 경우 → 기존 paraPr에서 horizontal 일치하는 것 찾기
for pp in existing_paraPrs:
    if pp.align.horizontal == needed_horizontal:
        return pp.id  # 재사용
```

## 18. 셀 텍스트 정렬 체계 (줄별 독립 정렬)

### 구조

```
셀 텍스트 정렬
├── 가로 → 각 <hp:p>의 paraPrIDRef → header의 paraPr.align.horizontal
│          줄마다 다른 paraPrIDRef 가능 (같은 셀 안에서도)
│
└── 세로 → <hp:subList vertAlign="CENTER|TOP|BOTTOM">
           셀 전체에 1개 (줄별 독립 불가)
```

### 줄별 다른 정렬 예시 (별지 제11호 서식 셀(11,0))

```
p[0] JUSTIFY   | (빈줄)
p[1] JUSTIFY   | 조세감면규제법시행령... (left=2000, right=2000)
p[2] JUSTIFY   | (빈줄)
p[3] JUSTIFY   | (빈줄)
p[4] CENTER    | 년        월       일
p[5] JUSTIFY   | (빈줄)
p[6] RIGHT     | 신청인 (서명 또는 인) (right=4000)
p[7] JUSTIFY   | (빈줄)
p[8] CENTER    | 세 무 서 장 귀 하
```

각 줄의 `paraPrIDRef`가 다름 → **paraPr deep copy로 생성** (규칙 17)

### 가로 정렬 값

| 값 | 의미 | 사용처 |
|---|------|-------|
| `JUSTIFY` | 양쪽 정렬 | 본문, 라벨, 입력칸 (가장 흔함) |
| `CENTER` | 가운데 | 제목, 날짜, 섹션명 |
| `LEFT` | 왼쪽 | 주소 입력칸 |
| `RIGHT` | 오른쪽 | 서명란, 전화번호 |

### 폰트 크기 패턴 (charPr.height)

| 용도 | height | bold | spacing | 비고 |
|------|--------|------|---------|------|
| 서식 제목 | 1500~1800 | `<bold/>` | 0 | "신청서(갑)" |
| 본문/라벨 | 1000~1100 | 없음 | 0 | "①성명", "처리기간" |
| 넓은 자간 | 1100 | 없음 | 15~36 | "성명또는법인명" |
| 좁은 자간 | 1000 | 없음 | -5~-20 | 긴 텍스트 압축 |
| 소형 주석 | 800~900 | 없음 | 0 | 하단 용지 크기 |

### 셀 패딩 (cellMargin)

```xml
<!-- hasMargin="0": 값 무시, 한컴 기본 패딩 (정부 서식 패턴) -->
<hp:tc hasMargin="0">
  <hp:cellMargin left="141" right="141" top="141" bottom="141"/>
</hp:tc>

<!-- hasMargin="1": 명시적 패딩 적용 (프로그래밍 생성 패턴) -->
<hp:tc hasMargin="1">
  <hp:cellMargin left="400" right="400" top="250" bottom="250"/>
</hp:tc>
```

### 테두리 (borderFill) 패턴

| 위치 | 테두리 |
|------|--------|
| 표 외곽 | SOLID 0.4mm (THICK) |
| 표 내부 | SOLID 0.12mm (THIN) |
| 구분선 없음 | NONE 0.1mm |

셀마다 4변(left/right/top/bottom) 테두리가 독립 — 위치에 따라 17~21종 borderFill 조합
