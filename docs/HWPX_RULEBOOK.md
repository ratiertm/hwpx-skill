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
