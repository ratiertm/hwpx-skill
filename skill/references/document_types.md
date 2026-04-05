# Document Types & Structure Reference

## Table of Contents

1. [Document Type Specifications (문서 유형별 규격)](#document-type-specifications)
   - 유형별 핵심 수치 비교표
   - 1. 정부 양식
   - 2. 공문서
   - 3. 세무/법무
   - 4. 기업 보고서
   - 5. 학술 논문
   - 서체 대체 순서
2. [Document Structure Guide (문서 구성 가이드)](#document-structure-guide)
   - 문서 계층 구조
   - 제목별 스타일
   - 정렬 규칙
   - 문단 간격 패턴
   - 구분선 패턴
3. [Indent Guide (들여쓰기 상세)](#indent-guide)
   - intent vs left margin 차이
   - 공문서 들여쓰기 체계
   - 들여쓰기 패턴 (paraPr margin)
   - 번호 매기기 패턴
4. [Table of Contents in Document (문서 내 목차)](#table-of-contents-in-document)
   - 목차 생성 패턴
   - 목차 자동 생성 헬퍼
   - 목차 스타일
5. [Cover Page (표지)](#cover-page)
   - 표지 스타일 규칙
   - 표지 유형별 패턴
   - 전체 문서 구성 순서
6. [Design Components (디자인 컴포넌트 가이드)](#design-components)
   - 구분선 / 섹션 제목 / 박스 패턴
   - 문서 유형별 컴포넌트 조합 (stitch 레퍼런스)
7. [Table Design Guide (표 만들기 가이드)](#table-design-guide)
   - 표 너비 계산
   - 열 너비 분배
   - 행 높이
   - 셀 패딩 (cellMargin)
   - 표 스타일 기본값
   - 표 강조 패턴
   - 표 마진
   - 표 테두리 (borderFill)
   - 셀 병합
   - 셀 수직 정렬
   - 셀 배경색
   - add_table 기본값과 권장값
   - 표 유형별 템플릿
8. [Templates & Style Guide](#templates--style-guide)
   - 기본 폰트
   - 보고서 템플릿 패턴
   - 서식(양식) 템플릿 패턴

---

## Document Type Specifications

### 유형별 핵심 수치 비교표

| 항목 | 정부 양식 | 공문서 | 세무/법무 | 기업 보고서 | 학술 논문 |
|------|-----------|--------|-----------|-------------|-----------|
| **제목 크기** | 18~20pt | 15~16pt | 18~20pt | 22~24pt | 16~18pt |
| **본문 크기** | 11~12pt | 12pt | 12pt | 11pt | 10~11pt |
| **본문 줄간격** | 160% | 160% | 200% | 170% | 170% |
| **상단 여백** | 20mm | 30mm | 30mm | 25mm | 30mm |
| **좌측 여백** | 20mm | 20mm | 30mm | 25mm | 30mm |
| **본문 서체** | 바탕 | 바탕 | 바탕 | 바탕 | 바탕 |
| **제목 서체** | 바탕 | 바탕 | 바탕 | 돋움 | 바탕 |
| **색상 원칙** | 단색+적색 | 단색만 | 단색만 | 다색 허용 | 단색만 |
| **표 스타일** | 전체 테두리 | 전체 테두리 | 전체+강조 | 3선+컬러 | 3선 |
| **첫줄 들여쓰기** | 없음 | 없음 | 없음 | 선택 | 10pt |

### 1. 정부 양식 (근로계약서, 신청서)
- 제목 18~20pt Bold 바탕, 가운데 정렬
- 본문 11~12pt, 줄간격 160%
- 여백: 상20 하15 좌20 우20mm
- 표: 실선 0.4mm 검정, 셀 패딩 상하2 좌우3mm
- 색상: 검정만, 필수표시만 적색(#CC0000)

### 2. 공문서 (기관 공문, 협조전)
- 「행정업무의 운영 및 관리에 관한 규정」 준거
- 기관명 16pt Bold, 제목 15pt Bold, 본문 12pt
- 여백: 상30 하15 좌20 우15mm
- 검정만 사용, 줄간격 160%

### 3. 세무/법무 (소장, 세금계산서)
- 본문 줄간격 **200%** (법원 제출 관행)
- 좌측 여백 **30mm** (편철 공간)
- 항목: `1. → 가. → (1) → (가)` 체계
- 검정만 사용

### 4. 기업 보고서 (분석, 제안서)
- 표지 22~24pt Bold 돋움, 장 16~18pt
- 본문 11pt 바탕, 줄간격 170%
- 표: 3선 스타일, 헤더 남색(#2B4C7E) 배경 + 흰색 텍스트
- 다색 허용, 긍정 녹색(#27AE60), 부정 적색(#E74C3C)

### 5. 학술 논문 (KCI 기준)
- 제목 16~18pt Bold 바탕, 본문 10~11pt
- 줄간격 170%, 첫줄 들여쓰기 10pt
- 여백: 상30 하25 좌30 우30mm (학위논문 좌 35mm)
- 표: 3선 표(상·헤더하단·하단만 실선), 배경색 없음
- 검정만 사용

**서체 대체 순서**: 함초롬바탕 → 바탕 → 나눔명조 / 함초롬돋움 → 돋움 → 나눔고딕

---

## Document Structure Guide

### 문서 계층 구조
```
대제목 (level 1) — 문서 타이틀, 1개만
├── 중제목 (level 2) — 섹션 구분 (1. 개요, 2. 분석, 3. 결론)
│   ├── 소제목 (level 3) — 하위 항목 (1.1, 1.2)
│   │   └── 본문 텍스트 — 일반 단락
│   └── 소제목 (level 3)
│       ├── 본문 텍스트
│       └── 표/그림
├── 중제목 (level 2)
│   └── ...
└── 부록/참고 — 작은 폰트, 회색
```

### 제목별 스타일

| 구분 | 크기 | 볼드 | 색상 | 정렬 | 줄간격 |
|------|------|------|------|------|--------|
| 대제목 | 24pt | O | on-surface (#2b3437) | CENTER | 200 |
| 중제목 | 18pt | O | on-surface (#2b3437) | LEFT | 160 |
| 소제목 | 16pt | O | primary (#395da2) | LEFT | 160 |
| 본문 | 10pt | X | on-surface (#2b3437) | JUSTIFY | 160 |
| 캡션/표제목 | 10pt | O | on-surface (#2b3437) | LEFT | 130 |
| 메타/날짜 | 9pt | X | on-surface-variant (#586064) | LEFT | 130 |
| 면책/미주 | 8pt | X | outline-variant (#abb3b7) | LEFT | 130 |

### 정렬 규칙

| 요소 | 정렬 | 이유 |
|------|------|------|
| 대제목 | CENTER | 문서 시각적 중심 |
| 중/소제목 | LEFT | 읽기 흐름 |
| 본문 | JUSTIFY | 한국 공문서 기본 (condense 25% 필요) |
| 표 헤더 | CENTER | 열 제목 강조 |
| 표 데이터 (텍스트) | CENTER | 가독성 |
| 표 데이터 (숫자) | RIGHT | 자릿수 정렬 |
| 날짜/작성자 | RIGHT | 관례 |

### 문단 간격 패턴

```python
# 제목 뒤 — 빈 줄 1개
doc.add_heading("제목", level=1)
doc.add_paragraph("")

# 섹션 전환 — 빈 줄 1개 또는 구분선
doc.add_paragraph("")
doc.add_heading("다음 섹션", level=2)

# 표 전후 — 빈 줄 1개씩
doc.add_paragraph("")
doc.add_table([...])
doc.add_paragraph("")

# 본문 연속 — 빈 줄 없이 연결
doc.add_paragraph("첫 번째 문단")
doc.add_paragraph("두 번째 문단")

# 문서 끝 주석 — 빈 줄 2개 후
doc.add_paragraph("")
doc.add_paragraph("")
doc.add_paragraph("본 문서는...", font_size=9, text_color="#999999")
```

### 구분선 패턴

```python
# 가벼운 구분 — 짧은 선
doc.add_paragraph("───────────────", text_color="#CCCCCC")

# 강한 구분 — 전체 너비 선
doc.add_line()

# 섹션 구분 — 빈 줄 + 제목
doc.add_paragraph("")
doc.add_heading("새 섹션", level=2)
```

**한국 공문서 기본 설정**:
```python
# A4 용지
page_width = 59528    # 210mm
page_height = 84188   # 297mm

# 여백 (한국 공문서 기본)
margin_left = 8504    # 30mm
margin_right = 8504   # 30mm
margin_top = 5668     # 20mm
margin_bottom = 4252  # 15mm

# 기본 폰트
font = "함초롬돋움"    # 한컴 기본
font_size = 10        # pt (height 1000)

# 줄간격
line_spacing = 160    # 160% (한국 공문서 기본)

# 정렬
alignment = "JUSTIFY" # 양쪽 정렬 + condense 25%
```

---

## Indent Guide

### intent vs left margin 차이
```
intent (들여쓰기):  첫 줄만 들여쓰기 (음수 = 내어쓰기)
left (좌측 여백):   전체 단락 좌측 이동

예시: intent=-2800, left=2800
  ↓ intent (첫 줄 내어쓰기)
제1조(목적) 이 규정은 환경기술 및 환경산업
  ↓ left (2째줄부터 들여쓰기)
       지원법 제10조에 따른 센터의 설립
       및 운영에 관한 사항을 규정함을
       목적으로 한다.
```

### 공문서 들여쓰기 체계
```python
# 단계별 intent + left 조합
styles = {
    "조": {"intent": -2800, "left": 2800},   # 제1조(목적)
    "호": {"intent": -4880, "left": 4880},   # 1. 항목
    "목": {"intent": -7680, "left": 7680},   # 가. 세부
    "세목": {"intent": -9080, "left": 9080}, # 1) 세부세부
}
```

### 들여쓰기 패턴 (paraPr margin)

| 구분 | intent 값 | 사용 |
|------|----------|------|
| 기본 | 0 | 일반 본문 |
| 1단 들여쓰기 | -2800 | 조항 번호 뒤 본문 |
| 2단 들여쓰기 | -4880 | 하위 항목 |
| 3단 들여쓰기 | -7680 | 세부 항목 |
| 좌측 여백 | left 4000 | 인용문, 참고 |

### 번호 매기기 패턴
```
제1조(목적)          ← 조 (condense 25%, intent -2800)
  1. 항목             ← 호 (intent -4880)
    가. 세부항목       ← 목 (intent -7680)
      1) 세부세부      ← 세목
```

---

## Table of Contents in Document

HWPX에서 목차는 자동 생성이 아닌 **수동 구성**으로 만듭니다.
제목(heading)을 기반으로 목차 텍스트를 직접 생성합니다.

### 목차 생성 패턴
```python
doc = HwpxBuilder()

# 목차 페이지
doc.add_heading("목 차", level=1)
doc.add_paragraph("")
doc.add_paragraph("1. 개요 ························· 2", font_size=11)
doc.add_paragraph("2. 현황 분석 ··················· 5", font_size=11)
doc.add_paragraph("  2.1 시장 동향 ··············· 5", font_size=10)
doc.add_paragraph("  2.2 경쟁사 분석 ············· 8", font_size=10)
doc.add_paragraph("3. 결론 ························· 12", font_size=11)
doc.add_paragraph("")

# 본문 시작
doc.add_heading("1. 개요", level=2)
doc.add_paragraph("본문 내용...")
```

### 목차 자동 생성 헬퍼
```python
def generate_toc(sections, dot_char="·"):
    """섹션 목록에서 목차 텍스트 생성
    sections = [("1. 개요", 2), ("2. 분석", 5), ("  2.1 세부", 6)]
    """
    lines = []
    for title, page in sections:
        indent = len(title) - len(title.lstrip())
        dots = dot_char * (40 - len(title) - len(str(page)))
        lines.append(f"{title} {dots} {page}")
    return lines
```

### 목차 스타일
| 요소 | 폰트 | 정렬 |
|------|------|------|
| "목 차" 제목 | 20pt 볼드 CENTER | 가운데 |
| 1단계 항목 | 11pt LEFT | 왼쪽 |
| 2단계 항목 | 10pt LEFT (들여쓰기 2칸) | 왼쪽 |
| 3단계 항목 | 9pt LEFT (들여쓰기 4칸) | 왼쪽 |
| 점선 | · 반복 | 제목과 페이지 번호 연결 |
| 페이지 번호 | 우측 정렬 | 오른쪽 끝 |

---

## Cover Page

표지는 문서의 첫 페이지로, 제목/부제/작성자/날짜/기관명을 세로 가운데 배치.
본문과 분리하기 위해 표지 끝에 페이지 구분이 필요합니다.

```python
doc = HwpxBuilder()

# ── 표지 ──
doc.add_paragraph("")   # 상단 여백
doc.add_paragraph("")
doc.add_paragraph("")
doc.add_paragraph("")
doc.add_paragraph("")

doc.add_heading("2026년도", level=2)
doc.add_paragraph("")

doc.add_paragraph("엔비디아 투자 분석 보고서", bold=True, font_size=24,
                   alignment="CENTER")
doc.add_paragraph("")
doc.add_paragraph("")

doc.add_paragraph("NVDA (NVIDIA Corporation)", font_size=14,
                   text_color="#76b900", alignment="CENTER")
doc.add_paragraph("")
doc.add_paragraph("")
doc.add_paragraph("")

doc.add_paragraph("2026년 4월 5일", font_size=12,
                   text_color="#888888", alignment="CENTER")
doc.add_paragraph("")

doc.add_paragraph("작성자: 홍길동", font_size=11, alignment="CENTER")
doc.add_paragraph("미국주식 투자 블로그", font_size=10,
                   text_color="#888888", alignment="CENTER")

# 표지 하단 — 기관/회사 로고 위치
doc.add_paragraph("")
doc.add_paragraph("")
doc.add_paragraph("")
doc.add_line()
doc.add_paragraph("Confidential", font_size=8,
                   text_color="#CCCCCC", alignment="CENTER")
```

### 표지 스타일 규칙

| 요소 | 폰트 크기 | 정렬 | 색상 |
|------|----------|------|------|
| 연도/카테고리 | 16pt | CENTER | #333333 |
| **대제목** | **24pt 볼드** | **CENTER** | **#000000** |
| 부제목 | 14pt | CENTER | 브랜드색 |
| 날짜 | 12pt | CENTER | #888888 |
| 작성자 | 11pt | CENTER | #333333 |
| 기관명 | 10pt | CENTER | #888888 |
| 기밀 표시 | 8pt | CENTER | #CCCCCC |

### 표지 유형별 패턴

```python
# 1. 공문서 표지
doc.add_paragraph("대외비", font_size=14, bold=True, text_color="#E74C3C",
                   alignment="CENTER")
doc.add_paragraph("")
doc.add_heading("녹색환경지원센터 설립·운영에 관한 규정", level=1)
doc.add_paragraph("")
doc.add_paragraph("환경부", font_size=16, bold=True, alignment="CENTER")

# 2. 보고서 표지
doc.add_paragraph("[ 분석 보고서 ]", font_size=12, text_color="#888888",
                   alignment="CENTER")
doc.add_heading("AI 반도체 시장 동향", level=1)
doc.add_paragraph("2026년 1분기", font_size=14, alignment="CENTER")

# 3. 제안서 표지
doc.add_heading("제 안 요 청 서", level=1)
doc.add_paragraph("")
doc.add_table([
    ["사업명", "2026년 AI 인프라 구축 사업"],
    ["주관기관", "한국정보원"],
    ["제출일", "2026년 4월 5일"],
])
```

### 전체 문서 구성 순서

```python
doc = HwpxBuilder()

# 1. 표지 (1페이지 전체 사용)
# ... (위 표지 코드) ...
# 페이지 넘김 (빈 줄로 채우거나 pageBreak 속성)

# 2. 목차
doc.add_heading("목 차", level=1)
doc.add_paragraph("1. 개요 ························· 2", font_size=11)
doc.add_paragraph("2. 분석 ························· 4", font_size=11)
doc.add_paragraph("3. 결론 ························· 8", font_size=11)
doc.add_paragraph("")

# 3. 본문
doc.add_heading("1. 개요", level=2)
doc.add_paragraph("본문...")
doc.add_paragraph("")

doc.add_heading("2. 분석", level=2)
doc.add_heading("2.1 시장 동향", level=3)
doc.add_paragraph("분석 내용...")
doc.add_paragraph("")

doc.add_heading("3. 결론", level=2)
doc.add_paragraph("결론 내용...")
doc.add_paragraph("")

# 4. 부록/참고
doc.add_line()
doc.add_paragraph("참고 문헌", bold=True, font_size=11)
doc.add_paragraph("1. 출처1", font_size=9, text_color="#666666")
doc.add_paragraph("2. 출처2", font_size=9, text_color="#666666")
doc.add_paragraph("")

# 5. 면책 조항
doc.add_paragraph("본 문서는 정보 제공 목적으로 작성되었습니다.",
                   font_size=8, text_color="#999999")

doc.save("report.hwpx")
```

---

## Design Components

문서 작성 시 아래 컴포넌트를 상황에 맞게 조합합니다.
디자인 레퍼런스: `skill/stitch/` 폴더의 hwpx_1~5 스크린샷 참조.

**구분선**: 테두리 표 대신 텍스트 구분선 사용
```python
doc.add_paragraph('━' * 50, font_size=6, text_color='#abb3b7')
```

**섹션 제목**: 표/박스 없이 텍스트로
```python
doc.add_paragraph('섹션 제목', bold=True, font_size=13, text_color='#395da2')
```

**하이라이트 박스**: primary-container 배경 표
```python
doc.add_table([['핵심 요약 내용']],
    cell_colors={(0,0): '#d8e2ff'},
    cell_margin=(400,400,300,300), header_bg='',
    cell_styles={(0,0): {'text_color': '#2a5094'}},
    use_preset=False)
```

**콜아웃/인용 박스**: tertiary-container 배경
```python
doc.add_table([['인용문 또는 편집자 주']],
    cell_colors={(0,0): '#e2dbfd'},
    cell_margin=(400,400,300,300), header_bg='',
    cell_styles={(0,0): {'text_color': '#514d68'}},
    use_preset=False)
```

**정보 박스**: secondary-container 배경
```python
doc.add_table([['참고 정보']],
    cell_colors={(0,0): '#cbe7f5'},
    cell_margin=(400,400,300,300), header_bg='',
    cell_styles={(0,0): {'text_color': '#3c5561'}},
    use_preset=False)
```

### 문서 유형별 컴포넌트 조합 (stitch 레퍼런스)

| 유형 | 핵심 컴포넌트 | stitch 참조 |
|------|-------------|------------|
| 기안서/기획안 | 번호(01,02,03) + 들여쓰기 본문 + 하이라이트 박스 | hwpx_1 |
| 회의록 | 메타 그리드(표) + 안건 테이블 + 콜아웃 박스 | hwpx_2 |
| 사업 보고서 | 표지 + 요약 표 + 섹션별 표/통계 | hwpx_3 |
| 공문서 | 수신/참조/제목(표) + 가.나. 계층 들여쓰기 + 구분선 | hwpx_4 |
| 안내문/협조문 | 히어로 박스(primary-container) + 과제 목록 + 일정 표 | hwpx_5 |

---

## Table Design Guide

### 표 너비 계산 (DXA 아닌 HWPUNIT: 1/7200 inch)
```
A4 용지 너비:       59,528
좌우 여백:         -8,504 × 2 = -17,008
─────────────────────────
본문 영역 너비:      42,520   ← 표 최대 너비
```

### 열 너비 분배
```python
content_width = 42520

# 균등 분할
cols = 3
col_width = content_width // cols  # 14,173

# 비율 분할 (3:2:1)
ratios = [3, 2, 1]
total = sum(ratios)
col_widths = [content_width * r // total for r in ratios]
# → [21260, 14173, 7087]
```

### 행 높이
| 유형 | height | 사용 |
|------|--------|------|
| 헤더 | 2400 | 표 제목 행 |
| 기본 | 2000 | 일반 데이터 행 |
| 넓음 | 3200 | 여러 줄 텍스트 |
| 좁음 | 1200 | 밀집 데이터 |

### 셀 패딩 (cellMargin)
```xml
<hp:cellMargin left="283" right="283" top="200" bottom="200" />
```

| 패딩 | left/right | top/bottom | 사용 |
|------|-----------|------------|------|
| 기본 | 283 | 200 | 일반 셀 (여유 있는 패딩 기본) |
| 넓은 여백 | 425 | 283 | 정부 양식, 가독성 |
| 좁은 여백 | 141 | 70 | 밀집 표 |
| 양식 셀 | 510 | 200 | 입력 칸 |

### 표 스타일 기본값 (Administrative Slate)
- 헤더 행: primary(#395da2) 배경 + on-primary(#f7f7ff) 흰색 볼드 텍스트 + CENTER 정렬
- 데이터 행 (텍스트): CENTER 정렬
- 데이터 행 (숫자): RIGHT 정렬
- 짝수 행: surface-container-low(#f1f4f6) 줄무늬 배경
- 각 표 위에 캡션: `[ 표 N ] 표 제목` (10pt 볼드)

### 표에서 사용할 수 있는 강조 패턴
- 하이라이트 행: primary-container(#d8e2ff) 배경 — 요약, 합계
- 경고 행: error(#9f403d) 텍스트 — 기한 초과, 위험
- 정보 행: secondary-container(#cbe7f5) 배경 — 참고 정보

### 표 마진 (표 바깥 여백)
```xml
<hp:outMargin left="0" right="0" top="0" bottom="0" />
<hp:inMargin left="141" right="141" top="141" bottom="141" />
```

| 속성 | 기본값 | 설명 |
|------|--------|------|
| outMargin | 0 | 표 바깥 여백 (본문과의 간격) |
| inMargin | 141 | 표 안쪽 여백 (셀 기본 패딩) |
| 중첩 표 outMargin | 283 | 중첩 표 바깥 여백 |
| 중첩 표 inMargin | 510 | 중첩 표 안쪽 여백 |

### 표 테두리 (borderFill)
```xml
<!-- borderFill id="1" = 테두리 없음 (기본) -->
<!-- borderFill id="2"+ = 커스텀 테두리 -->
<hh:borderFill id="2" threeD="0" shadow="0">
  <hh:leftBorder type="SOLID" width="0.12 mm" color="#000000" />
  <hh:rightBorder type="SOLID" width="0.12 mm" color="#000000" />
  <hh:topBorder type="SOLID" width="0.12 mm" color="#000000" />
  <hh:bottomBorder type="SOLID" width="0.12 mm" color="#000000" />
</hh:borderFill>
```

| type | 설명 |
|------|------|
| NONE | 테두리 없음 |
| SOLID | 실선 |
| DASH | 점선 |
| DOT | 점 |
| DOUBLE_SLIM | 이중선 |

### 셀 병합
```xml
<!-- 가로 병합: colSpan -->
<hp:cellSpan colSpan="3" rowSpan="1" />

<!-- 세로 병합: rowSpan -->
<hp:cellSpan colSpan="1" rowSpan="2" />

<!-- 가로+세로 동시 -->
<hp:cellSpan colSpan="2" rowSpan="3" />
```

### 셀 수직 정렬 (vertAlign)
```xml
<hp:subList vertAlign="CENTER">  <!-- TOP, CENTER, BOTTOM -->
```

### 셀 배경색
```python
# pyhwpxlib API
table.set_cell_background(row, col, "#D5E8F0")

# XML 직접
# borderFill에 winBrush 추가
```

### add_table 기본값과 권장값

| 파라미터 | 기본값 | 권장값 | 단위 |
|----------|--------|--------|------|
| `width` | 42520 | 42520 (전체너비) | HWPUNIT |
| `col_widths` | 균등분할 | 내용에 맞게 | HWPUNIT 리스트 |
| `row_heights` | 프리셋 자동 | 헤더 2400, 데이터 2000 | HWPUNIT 리스트 |
| `cell_margin` | 프리셋 자동 | (283,283,200,200) | (L,R,T,B) |
| `header_bg` | 프리셋 자동 | #395da2 (primary) | 헤더 배경색 |
| `cell_aligns` | 프리셋 자동 | 헤더 CENTER, 텍스트 CENTER, 숫자 RIGHT | 정렬 |
| `cell_styles` | 프리셋 자동 | 헤더 {text_color: #f7f7ff, bold: True} | 글자 스타일 |
| `cell_colors` | 프리셋 자동 | 짝수행 #f1f4f6 줄무늬 | 배경색 |

**프리셋**: `HwpxBuilder(table_preset='corporate')` 사용 시 위 값들이 자동 적용됨.
명시적으로 파라미터를 넘기면 프리셋보다 우선.

### 표 생성 실전 예시

```python
# 기본 — 자동 균등 분할
doc.add_table([["A","B","C"],["1","2","3"]])
# → width=42520, 3열 균등(14173씩), 높이 3600

# 열 너비 지정 (합 = width)
add_table(doc, 2, 3, data=[...],
          col_widths=[21260, 14173, 7087])  # 5:3:2 비율

# 행 높이 지정
add_table(doc, 3, 2, data=[...],
          row_heights=[1500, 1200, 1200])  # 헤더 높고 데이터 낮게

# 셀 패딩 지정
add_table(doc, 2, 2, data=[...],
          cell_margin=(200, 200, 100, 100))  # 여유있는 패딩

# 셀 배경색
add_table(doc, 2, 2, data=[...],
          cell_colors={(0,0): "#D5E8F0", (0,1): "#D5E8F0"})  # 헤더행 배경
```

### 표 유형별 템플릿

```python
# 1. 데이터 표 (헤더 + 데이터)
doc.add_table([
    ["항목", "수량", "금액"],     # 헤더 (볼드, 배경색)
    ["제품A", "100", "50,000"],
    ["제품B", "200", "80,000"],
    ["합계", "300", "130,000"],
])

# 2. 키-값 표 (라벨 + 입력칸)
doc.add_table([
    ["성 명", ""],
    ["주민등록번호", ""],
    ["주 소", ""],
])

# 3. 카드 레이아웃 (가로 나열)
doc.add_table([
    ["현재가", "목표가", "상승여력"],
    ["$184.86", "$250", "+35%"],
])

# 4. 비교 표
doc.add_table([
    ["구분", "항목A", "항목B", "차이"],
    ["성능", "100", "150", "+50%"],
    ["가격", "1,000", "1,200", "+20%"],
])
```

---

## Templates & Style Guide

**기본 폰트**: 함초롬돋움 (한컴 기본), 맑은 고딕 (Windows 호환), 나눔고딕 (웹 호환)

**표 스타일**:

| 스타일 | 설명 | 코드 |
|--------|------|------|
| 기본 표 | 테두리만 | borderFillIDRef="1" |
| 헤더 강조 | 첫 행 배경색 | set_cell_background(row=0, color) |
| 줄무늬 | 짝수행 배경 | 행별 borderFill 교체 |

**보고서 템플릿 패턴**:
```python
doc = HwpxBuilder()
doc.add_heading("보고서 제목", level=1)
doc.add_paragraph("2026년 4월 5일", font_size=10, text_color="#888888")
doc.add_paragraph("")

doc.add_table([
    ["항목", "값", "비고"],
    ["데이터1", "100", "정상"],
])
doc.add_paragraph("")

doc.add_heading("1. 개요", level=2)
doc.add_paragraph("본문 내용...")
doc.add_paragraph("")

doc.add_heading("2. 분석", level=2)
doc.add_paragraph("분석 내용...")
doc.add_paragraph("")

doc.add_paragraph("본 문서는 정보 제공 목적으로 작성되었습니다.",
                   font_size=9, text_color="#999999")
doc.save("report.hwpx")
```

**서식(양식) 템플릿 패턴**:
```python
# 1. 원본 서식 hwpx 업로드
# 2. extract_schema()로 필드 탐지
# 3. template_builder.py로 입력 필드 지정 → schema.json 저장
# 4. fill_template_checkbox()로 데이터 채우기
# → 원본 서식의 스타일이 100% 보존됨
```
