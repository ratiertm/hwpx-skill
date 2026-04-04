# OWPML 표 사이즈 구조 (리버스 엔지니어링)

서식(Template) HWPX 문서의 표 크기/그리드 시스템.
서식SAMPLE1.owpml(세액면제 신청서)과 서식SAMPLE2.owpml(영업신고서)에서 역산.

## 단위 체계

```
1 HWP Unit = 1/7200 inch = 0.003528mm
283.46 HWP Units ≈ 1mm
7200 HWP Units = 1 inch
100 HWP Units = 1pt (charPr height 기준)
```

| 실물 | HWP Unit | 비고 |
|------|----------|------|
| A4 가로 | 59528 | 210mm |
| A4 세로 | 84188 | 297mm |
| 1mm | 283.46 | |
| 1cm | 2834.6 | |
| 10pt 글자 | 1000 | charPr height |

## 사이즈 계층 구조

```
pagePr                              ← 용지 크기
├── width="59528" height="84188"    ← A4
├── landscape="WIDELY"              ← 세로(WIDELY) / 가로(NARROWLY)
└── margin
    ├── left="5104" right="5104"    ← 약 18mm
    ├── top="4252" bottom="4252"    ← 약 15mm
    └── header="2836" footer="2836"
    → 본문영역 width = pagePr.width - margin.left - margin.right

tbl                                 ← 표
├── sz
│   ├── width="49040"               ← 표 전체 너비
│   ├── height="67044"              ← 표 전체 높이
│   ├── widthRelTo="ABSOLUTE"       ← 항상 절대값
│   └── heightRelTo="ABSOLUTE"
├── pos
│   ├── treatAsChar="1"             ← 본문 흐름에 포함
│   ├── horzRelTo="COLUMN"          ← 컬럼 기준 배치
│   └── vertRelTo="PARA"            ← 문단 기준 배치
├── outMargin                       ← 표↔본문 간격
│   └── left="140" right="140" top="140" bottom="140"
├── inMargin                        ← 표↔셀 간격
│   └── left="140" right="140" top="140" bottom="140"
├── cellSpacing="0"                 ← 셀 간 간격
│
├── tr (행, 속성 없음)
│   └── tc (셀)
│       ├── cellAddr colAddr="3" rowAddr="1"     ← 좌표
│       ├── cellSpan colSpan="2" rowSpan="1"     ← 병합
│       ├── cellSz   width="11036" height="4320" ← ⭐ 셀 크기
│       └── cellMargin left="141" right="141" top="141" bottom="141"
│
└── 표 너비 ≈ 본문영역 - outMargin.left - outMargin.right
```

## 핵심 규칙: 숨겨진 그리드

### 규칙 1: 별도 컬럼/행 정의 없음, cellSz가 전부

OWPML에는 HTML `<colgroup>`이나 DOCX `<w:gridCol>` 같은 컬럼 너비 선언이 **없다**.
모든 크기 정보는 각 `<hp:tc>`의 `<hp:cellSz>`에 저장된다.

### 규칙 2: 숨겨진 컬럼 그리드가 존재한다

모든 표에는 암묵적 컬럼 그리드가 있고, 각 컬럼의 너비 합 = 표 전체 너비:

```
SAMPLE1 (14×9): col[0..8] = [2140, 3976, 8388, 11044, 9916, 1120, 5404, 284, 6768]
                SUM = 49040 = tbl.sz.width ✅

SAMPLE2 (17×14): col[0..13] = [2392, 2108, 2024, 1408, 4524, 13180, 1926, 4490, 744, 1756, 1912, 532, 452, 6208]
                 SUM = 43656 = tbl.sz.width ✅
```

### 규칙 3: cellSz.width = span 범위 컬럼 합

```
셀 (row=3, col=1) colSpan=2:
  width = col[1] + col[2] = 3976 + 8388 = 12364 ✅

셀 (row=7, col=0) colSpan=3:
  width = col[0] + col[1] + col[2] = 2140 + 3976 + 8388 = 14504 ✅

셀 (row=0, col=0) colSpan=7:
  width = col[0] + ... + col[6] = 41988 ✅
```

### 규칙 4: cellSz.height = span 범위 행 합

```
셀 (row=0, col=0) rowSpan=2:
  height = row[0] + row[1] = 2900 + 2900 = 5800 ✅

셀 (row=8, col=0) rowSpan=3:
  height = row[8] + row[9] + row[10] = 4320 + 4320 + 4320 = 12960 ✅
```

### 규칙 5: 표 너비와 본문영역 관계

```
표 width = 본문영역 - outMargin.left - outMargin.right
SAMPLE1: 49040 = 49320 - 140 - 140 ✅
```

### 규칙 6: 행 높이 합 ≈ 표 높이

```
SAMPLE1: SUM(row_heights) = 66444, tbl.height = 67044 (diff=600)
SAMPLE2: SUM(row_heights) = 62984, tbl.height = 62984 (diff=0) ✅
```

약간의 오차는 cellMargin 또는 border 누적 가능.

## 컬럼 그리드 역산 방법

cellSz에서 개별 컬럼 너비를 추출하는 연립방정식 풀이:

```python
def reverse_column_grid(cells, col_count):
    """셀 리스트에서 개별 컬럼 너비 역산"""
    col_widths = [None] * col_count
    equations = [(c['col'], c['col'] + c['colSpan'], c['width']) for c in cells]
    
    # 1단계: colSpan=1 셀에서 직접 확정
    for start, end, w in equations:
        if end - start == 1:
            col_widths[start] = w
    
    # 2단계: 반복적으로 미확정 컬럼 추론
    changed = True
    while changed:
        changed = False
        for start, end, w in equations:
            unknowns = [i for i in range(start, end) if col_widths[i] is None]
            knowns_sum = sum(col_widths[i] for i in range(start, end) if col_widths[i] is not None)
            if len(unknowns) == 1:
                col_widths[unknowns[0]] = w - knowns_sum
                changed = True
    
    return col_widths
```

## 서식 생성에 필요한 최소 정보

```python
template = {
    # 용지
    "page": {"width": 59528, "height": 84188, "landscape": "WIDELY"},
    "margin": {"left": 5104, "right": 5104, "top": 4252, "bottom": 4252},
    
    # 그리드 (핵심) — 이것만 정의하면 모든 cellSz 자동 계산
    "col_widths": [2140, 3976, 8388, 11044, 9916, 1120, 5404, 284, 6768],
    "row_heights": [2900, 2900, 780, 4320, 4320, 4320, 4604, 4440, 4320, 4320, 4320, 18816, 2900, 3184],
    
    # 셀 정의 (좌표 + span + 역할만, 크기는 그리드에서 계산)
    "cells": [
        {"row": 0, "col": 0, "cs": 7, "rs": 2, "role": "TITLE", "text": "세액면제 신청서(갑)"},
        {"row": 3, "col": 1, "cs": 2, "rs": 1, "role": "LABEL", "text": "①성명또는법인명"},
        {"row": 3, "col": 3, "cs": 1, "rs": 1, "role": "INPUT", "field": "name"},
        # ...
    ]
}

# cellSz 자동 계산:
def calc_cell_size(cell, col_widths, row_heights):
    width = sum(col_widths[cell['col'] : cell['col'] + cell['cs']])
    height = sum(row_heights[cell['row'] : cell['row'] + cell['rs']])
    return width, height
```

## tr 구조 규칙

### span된 셀은 시작 tr에만 존재

```
row=0에서 rowSpan=2인 셀 → tr[0]에만 <hp:tc> 존재
row=1의 tr에는 해당 위치 tc 없음 (물리적 부재)
```

### 각 tr의 tc 출현 규칙

```
tr[i]에 나타나는 tc = {
    해당 행에서 시작하는 셀 (rowAddr == i)
    단, rowSpan으로 상위 행에서 시작된 셀은 제외
}
```

### 예시: SAMPLE1 tr 구성

```
tr[0]:  tc(0,0)[7×2], tc(0,7)[2×1]           ← 2개
tr[1]:  tc(1,7)[2×1]                          ← 1개 (col0~6은 위에서 rowSpan)
tr[2]:  tc(2,0)[7×1], tc(2,7)[2×1]           ← 2개
tr[3]:  tc(3,0)[1×3], tc(3,1)[2×1], tc(3,3)[1×1], tc(3,4)[2×1], tc(3,6)[3×1]  ← 5개 (최다)
tr[4]:  tc(4,1)[2×1], tc(4,3)[1×1], tc(4,4)[2×1], tc(4,6)[3×1]  ← 4개 (col0은 위에서 rowSpan)
...
```

## 셀 내부 구조

```xml
<hp:tc name="" header="0" hasMargin="0" protect="0" editable="0"
       dirty="0" borderFillIDRef="14">
  <hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK"
              vertAlign="CENTER">
    <hp:p paraPrIDRef="0" styleIDRef="0">
      <hp:run charPrIDRef="5">
        <hp:t>세 액 면 제 (감 면) 신 청 서(갑)</hp:t>
      </hp:run>
    </hp:p>
  </hp:subList>
  <hp:cellAddr colAddr="0" rowAddr="0"/>
  <hp:cellSpan colSpan="7" rowSpan="2"/>
  <hp:cellSz width="41988" height="5800"/>
  <hp:cellMargin left="141" right="141" top="141" bottom="141"/>
</hp:tc>
```

### 주요 속성

| 속성 | 위치 | 설명 |
|------|------|------|
| `borderFillIDRef` | tc | header.xml의 borderFill 참조 (테두리+배경) |
| `vertAlign` | subList | 세로 정렬: CENTER, TOP, BOTTOM |
| `paraPrIDRef` | p | header.xml의 paraPr 참조 (가로 정렬, 들여쓰기) |
| `charPrIDRef` | run | header.xml의 charPr 참조 (글자 크기, 볼드) |
| `hasMargin` | tc | "1"이면 cellMargin 적용, "0"이면 무시 |
| `header` | tc | "1"이면 반복 헤더 행 |

## 서식 셀 역할 구분

| 역할 | 판별 기준 | 특징 |
|------|----------|------|
| TITLE | 전체 열 span, 큰 charPr height (1500+) | 서식 이름 |
| LABEL | ①~⑨ 번호 포함, 고정 텍스트 | 항목명 |
| INPUT | 빈 텍스트 (`<hp:run>` 없거나 텍스트 없음) | 사용자 입력 필드 |
| STATIC | 고정 텍스트 ("즉시", "없음", 날짜 형식) | 변경 불가 값 |

## 글자 스타일 (charPr) 구조

```
section0.xml                         header.xml
────────────                         ──────────
<hp:run charPrIDRef="5">    ──→     <hh:charPr id="5"
  <hp:t>제목</hp:t>                       height="1800"        ← 글자 크기
</hp:run>                                 textColor="#000000"  ← 글자 색상
                                          shadeColor="none"    ← 글자 배경색
                                          borderFillIDRef="1">
                                      <bold/>                  ← 볼드 (태그 유무)
                                      <italic/>                ← 이탤릭 (태그 유무)
                                      <fontRef hangul="0" latin="0" .../>  ← 폰트 ID
                                      <ratio hangul="100"/>    ← 장평 (%)
                                      <spacing hangul="30"/>   ← 자간 (%)
                                      <relSz hangul="100"/>    ← 상대 크기
                                      <offset hangul="0"/>     ← 위치 오프셋
                                    </hh:charPr>
```

### charPr 속성 맵

| 속성 | 위치 | 의미 | 단위/값 |
|------|------|------|---------|
| `height` | charPr 속성 | **글자 크기** | 100 = 1pt (1000=10pt, 1800=18pt) |
| `textColor` | charPr 속성 | **글자 색상** | `#RRGGBB` |
| `shadeColor` | charPr 속성 | 글자 배경색 | `#RRGGBB` 또는 `none` |
| `<bold/>` | charPr 하위 태그 | **볼드** | 태그 있으면 bold |
| `<italic/>` | charPr 하위 태그 | 이탤릭 | 태그 있으면 italic |
| `<fontRef hangul="0">` | charPr 하위 | 폰트 참조 | fontface[lang].font[id] |
| `<spacing hangul="30">` | charPr 하위 | **자간** | 0=기본, 양수=넓게, 음수=좁게 |
| `<ratio hangul="95">` | charPr 하위 | **장평** | 100=기본, 95=약간 좁게 |

### 서식에서 발견된 글자 크기 패턴

| 용도 | height | bold | spacing | 예시 |
|------|--------|------|---------|------|
| 제목 | 1500~1800 | `<bold/>` | 0 | "신청서(갑)", "신고수리..." |
| 본문/라벨 | 1000~1100 | 없음 | 0 | "①성명", "처리기간" |
| 넓은 자간 | 1100 | 없음 | 15~36 | "성명또는법인명" |
| 좁은 자간 | 1000 | 없음 | -5~-20 | 긴 텍스트 압축 |
| 소형 주석 | 800~900 | 없음 | 0 | 하단 용지 크기 표시 |
| 투명 구분 | 100 | 없음 | 0 | 빈 공간용 극소 |

## 셀 패딩 (cellMargin) 구조

```xml
<hp:tc hasMargin="1" ...>           ← ⭐ "1"이어야 cellMargin 적용
  ...
  <hp:cellMargin left="400" right="400" top="250" bottom="250"/>
</hp:tc>
```

### hasMargin 규칙

- `hasMargin="0"`: cellMargin 값이 있어도 **무시** (한컴 기본 패딩 사용)
- `hasMargin="1"`: cellMargin 값으로 **명시적 패딩 적용**

### 파일별 비교

| 파일 유형 | hasMargin | cellMargin (L/R/T/B) | 비고 |
|----------|-----------|---------------------|------|
| 한컴 기본 (hwpxlib) | 0 | 510/510/141/141 | 패딩 무시됨 |
| 정부 서식 (SAMPLE1,2) | 0 | 141/141/141/141 | 패딩 무시 = 한컴 기본 |
| 프로그래밍 생성 (의견제출서) | 1 | 300~400/200~250 | 명시적 패딩 |
| 좁은 양식 (근로지원인) | 1 | 100/100/50/50 | 좁은 패딩 |

**발견: 정부 서식은 항상 `hasMargin="0"`** (한컴 기본 패딩에 의존)

## 검증된 실제 그리드

### 서식SAMPLE1 (세액면제 신청서, 14행×9열)

```
col[0]= 2140 ( 7.5mm)  col[1]= 3976 (14.0mm)  col[2]= 8388 (29.6mm)
col[3]=11044 (39.0mm)  col[4]= 9916 (35.0mm)  col[5]= 1120 ( 4.0mm)
col[6]= 5404 (19.1mm)  col[7]=  284 ( 1.0mm)  col[8]= 6768 (23.9mm)
SUM = 49040 ✅

row[ 0]= 2900  row[ 1]= 2900  row[ 2]=  780  row[ 3]= 4320
row[ 4]= 4320  row[ 5]= 4320  row[ 6]= 4604  row[ 7]= 4440
row[ 8]= 4320  row[ 9]= 4320  row[10]= 4320  row[11]=18816
row[12]= 2900  row[13]= 3184
SUM = 66444 (표 height=67044, diff=600)
```

### 서식SAMPLE2 (영업신고서, 17행×14열)

```
col[ 0]= 2392  col[ 1]= 2108  col[ 2]= 2024  col[ 3]= 1408
col[ 4]= 4524  col[ 5]=13180  col[ 6]= 1926  col[ 7]= 4490
col[ 8]=  744  col[ 9]= 1756  col[10]= 1912  col[11]=  532
col[12]=  452  col[13]= 6208
SUM = 43656 ✅

row[ 0]= 1848  row[ 1]= 1680  row[ 2]= 1020  row[ 3]= 1476
row[ 4]= 2984  row[ 5]= 3268  row[ 6]= 3268  row[ 7]= 3176
row[ 8]= 3900  row[ 9]= 3900  row[10]= 3836  row[11]=13236
row[12]=11700  row[13]= 1564  row[14]= 1848  row[15]= 1564
row[16]= 2716
SUM = 62984 ✅
```
