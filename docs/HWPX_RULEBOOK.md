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

```xml
<!-- ✅ 올바른 구조 (pyhwpxlib 검증 완료) -->
<hs:sec>
  <!-- p[0]: secPr만 포함, 텍스트 없음, linesegarray 1개 -->
  <hp:p>
    <hp:run charPrIDRef="0">
      <hp:secPr ...>페이지설정</hp:secPr>
    </hp:run>
    <hp:linesegarray><hp:lineseg .../></hp:linesegarray>
  </hp:p>

  <!-- p[1~N]: 본문 텍스트, linesegarray 없음 -->
  <hp:p><hp:run charPrIDRef="0"><hp:t>텍스트</hp:t></hp:run></hp:p>

  <!-- 표: 별도 p 안에 -->
  <hp:p>
    <hp:run charPrIDRef="0">
      <hp:tbl ...>표 XML</hp:tbl>
      <hp:t/>
    </hp:run>
  </hp:p>

  <!-- 표 뒤 텍스트 -->
  <hp:p><hp:run charPrIDRef="0"><hp:t>표 뒤 텍스트</hp:t></hp:run></hp:p>
</hs:sec>
```

**핵심 3원칙**:
1. **secPr 문단 분리**: secPr은 빈 문단에 단독 배치, 텍스트와 합치면 겹침 발생
2. **linesegarray 최소화**: secPr 문단에만 1개, 나머지는 한컴이 자동 계산
3. **셀 내 줄바꿈**: `<hp:subList>` 안에 별도 `<hp:p>`로 분리, linesegarray 불필요

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
