# pyhwpxlib

파이썬으로 .hwpx 파일을 생성하는 오픈소스 도구입니다. 한컴오피스 설치가 필요 없습니다.

[**English**](README.md)

## 어떤 상황에 쓰나요

- 서버에서 HWPX 문서를 자동 생성해야 할 때
- 마크다운/HTML을 HWPX로 변환해야 할 때
- AI 에이전트가 한글 문서를 출력해야 할 때
- 정부 양식/계약서를 데이터로 자동 채워야 할 때
- HWP 5.x 파일을 HWPX로 변환해야 할 때

## 설치

```bash
pip install pyhwpxlib
```

Python 3.10 이상 필요.

## 빠른 시작

### Python API로 문서 생성

```python
from pyhwpxlib import HwpxBuilder

doc = HwpxBuilder()
doc.add_heading("프로젝트 보고서", level=1)
doc.add_paragraph("2026년 4월 작성")
doc.add_table([
    ["항목", "수량", "금액"],
    ["서버", "3", "9,000,000"],
    ["라이선스", "10", "5,000,000"],
])
doc.add_paragraph("")
doc.add_heading("1. 개요", level=2)
doc.add_paragraph("본 보고서는...")
doc.save("보고서.hwpx")
```

### 마크다운에서 변환

```bash
pyhwpxlib md2hwpx 보고서.md -o 보고서.hwpx
```

변환 시 자동 인식: 제목(#), **볼드**, *이탈릭*, 글머리표, 번호 목록, 코드 블록, 표, 수평선

### HWP → HWPX 변환

```python
from pyhwpxlib.hwp2hwpx import convert

convert("기존문서.hwp", "변환결과.hwpx")
```

### 양식 자동 채우기

```python
from pyhwpxlib.api import fill_template_checkbox

fill_template_checkbox(
    "근로계약서_양식.hwpx",
    data={
        ">성 명<": ">성 명  홍길동<",
        ">사업체명<": ">사업체명  (주)블루오션<",
    },
    checks=["민간기업"],
    output_path="근로계약서_홍길동.hwpx",
)
```

### AI 에이전트 연동

AI(Claude Code, Cursor 등)에게 자연어로 문서를 설명하면 CLI 명령어를 조합해서 `.hwpx`를 생성합니다:

```
나: "3분기 매출 보고서 만들어줘. 제목, 개요, 월별 매출 표,
     핵심 성과 3개를 글머리표로, 마지막에 요약."

AI → pyhwpxlib 호출 → 보고서.hwpx
```

## 전체 기능

### 문서 생성 (HwpxBuilder)

| 메서드 | 설명 |
|--------|------|
| `add_heading(text, level)` | 제목 (1~4) |
| `add_paragraph(text, bold, font_size, text_color)` | 단락 |
| `add_table(data, header_bg, col_widths, ...)` | 표 (프리셋 자동) |
| `add_bullet_list(items)` | 글머리 기호 목록 |
| `add_numbered_list(items)` | 번호 목록 |
| `add_image(path, width, height)` | 이미지 삽입 |
| `add_page_break()` | 페이지 나누기 |
| `add_header(text)` / `add_footer(text)` | 머리말 / 꼬리말 |
| `add_page_number()` | 페이지 번호 |
| `add_footnote(text)` | 각주 |
| `add_equation(script)` | 수식 |
| `save(path)` | 저장 |

### 변환

| 기능 | 코드 |
|------|------|
| MD → HWPX | `pyhwpxlib md2hwpx input.md -o output.hwpx` |
| HTML → HWPX | `convert_html_file_to_hwpx("in.html", "out.hwpx")` |
| HWPX → HTML | `convert_hwpx_to_html("in.hwpx", "out.html")` |
| HWP → HWPX | `from pyhwpxlib.hwp2hwpx import convert` |
| 텍스트 추출 | `extract_text("document.hwpx")` |

### 양식 자동화

| 기능 | 설명 |
|------|------|
| `fill_template_checkbox()` | 양식에 데이터 채우기 (서식 100% 보존) |
| `fill_template_batch()` | 동일 양식으로 다건 생성 |
| `extract_schema()` | 양식 필드 자동 탐지 |

### 문서 편집

```bash
# 1. 압축 풀기
python -m pyhwpxlib unpack document.hwpx unpacked/

# 2. XML 직접 편집 (원본 문자열 교체 방식)

# 3. 다시 묶기
python -m pyhwpxlib pack unpacked/ output.hwpx

# 4. 검증
python -m pyhwpxlib validate output.hwpx
```

## CLI 명령어

CLI로도 단계별 문서 생성이 가능합니다:

```bash
# 빈 문서 만들기
pyhwpxlib document new -o 보고서.hwpx

# 스타일 텍스트 추가
pyhwpxlib --file 보고서.hwpx style add "프로젝트 보고서" --bold --font-size 16

# 표 추가
pyhwpxlib --file 보고서.hwpx table add -r 3 -c 2 \
  -h "이름,역할" -d "김철수,개발자" -d "이영희,디자이너"

# 텍스트 추출
pyhwpxlib --file 보고서.hwpx text extract
```

## HWPX 포맷이란?

HWPX는 한컴오피스의 차세대 문서 포맷입니다. ZIP 안에 XML 파일이 들어있는 구조로, Microsoft Word의 `.docx`와 비슷한 개념입니다. 한국 공공기관과 기업에서 표준으로 사용됩니다.

## 참고

- [python-hwpx](https://github.com/airmang/python-hwpx) -- 고규현 (MIT)

## 알려진 한계

- 복잡한 셀 병합 레이아웃은 수동 검토 필요
- HWPX 렌더링 미리보기 미지원 (한컴오피스에서 직접 확인)
- CSS→HWPX 매핑은 주요 속성 46개만 지원
- 이미지 내 텍스트 인식(OCR)은 별도 API 키 필요

## 라이선스

[BSL 1.1 (Business Source License)](LICENSE.md)

- 개인/비상업/교육/오픈소스 → **무료**
- 사내 5인 이하 → **무료**
- 상업적 사용/6인 이상 → **유료 라이선스 필요**
- 2030-04-07 이후 → Apache 2.0으로 자동 전환
