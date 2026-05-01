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

## 공문(기안문) 생성 — v0.10.0+

행정안전부 「2025 행정업무운영 편람」 규정을 자동 준수하는 공문/기안문 생성기.

```python
from pyhwpxlib.gongmun import Gongmun, GongmunBuilder, signer, validate_file

doc = Gongmun(
    기관명="OO 주식회사",
    수신="내부결재",                     # 또는 "OOO장관"
    제목="용역 계약 체결(안)",
    본문=[
        "계약을 아래와 같이 체결하고자 ...",
        ("계약 개요", [                   # 자동 2단계: 가./나./다./라.
            "계약명: ...",
            "계약 금액: ...",
            "계약 기간: 2026. 5. 1. ~ 2027. 4. 30.",
        ]),
    ],
    붙임=["계약서(안) 1부."],              # 자동 "끝." 표시
    기안자=signer("팀장", "김OO"),
    결재권자=signer("본부장", "박OO"),
    시행_처리과명="OO본부", 시행_일련번호="2026-001",
    시행일="2026. 4. 21.", 공개구분="비공개",
)
GongmunBuilder(doc).save("output.hwpx")

# 규정 검증 (10종 체크)
print(validate_file("output.hwpx"))
```

**자동 적용 (편람 준수)**:
- 날짜 `2025. 9. 20.` · 금액 `금113,560원(금일십일만삼천오백육십원)`
- 8단계 항목기호 `1.→가.→1)→가)→(1)→(가)→①→㉮` + 2타 들여쓰기
- "끝." 표시 (2타 + 끝.)
- 내부결재 시 발신명의 자동 생략 (영 §13③)
- 공문 표준 여백: 상 30 / 하 15 / 좌·우 20 / 머리말·꼬리말 10 mm
- '기안자·검토자·결재권자' 용어 생략 (편람 p71)

**자동 검사 (10종 룰)**:
- ERROR: 날짜 포맷(`2024.9.20`), 차별 표현(결손가정·학부형), 두음법칙(년간→연간)
- WARNING: 위압적 어투("할 것", "~바람"), 권위적 표현(치하했다), 외래어 오표기(컨퍼런스→콘퍼런스), 끝 표시 누락
- INFO: 한글 호환 영역 특수문자(㉮), 영문 약어 한글 설명 누락(AI→인공지능)

**지원 문서 유형 4종**: 일반기안문 (대외) / 간이기안문 (내부결재) / 일괄기안 / 공동기안

전체 규칙 YAML: [`pyhwpxlib/gongmun/rules.yaml`](pyhwpxlib/gongmun/rules.yaml) (270줄, 편람 기계판독 버전)

## HWPX 포맷이란?

HWPX는 한컴오피스의 차세대 문서 포맷입니다. ZIP 안에 XML 파일이 들어있는 구조로, Microsoft Word의 `.docx`와 비슷한 개념입니다. 한국 공공기관과 기업에서 표준으로 사용됩니다.

## 크레딧

이 프로젝트는 다음 오픈소스를 기반으로 합니다:

| 프로젝트 | 저작자 | 라이선스 | 사용 내용 |
|---------|--------|---------|----------|
| [hwp2hwpx](https://github.com/neolord0/hwp2hwpx) | neolord0 | Apache 2.0 | HWP→HWPX 변환 로직 (Python 포팅) |
| [hwplib](https://github.com/neolord0/hwplib) | neolord0 | Apache 2.0 | HWP 바이너리 파서 (Python 포팅) |
| [python-hwpx](https://github.com/airmang/python-hwpx) | 고규현 | MIT | HWPX 데이터클래스 모델 |

## 알려진 한계

- 복잡한 셀 병합 레이아웃은 수동 검토 필요
- HWPX 렌더링 미리보기 미지원 (한컴오피스에서 직접 확인)
- CSS→HWPX 매핑은 주요 속성 46개만 지원
- 이미지 내 텍스트 인식(OCR)은 별도 API 키 필요

## 라이선스

파일별로 다른 라이선스가 적용됩니다. 자세한 내용은 [LICENSE.md](LICENSE.md)를 참조하세요.

| 대상 | 라이선스 |
|------|---------|
| `hwp2hwpx.py`, `hwp_reader.py`, `value_convertor.py` | Apache 2.0 (원본 파생물) |
| **나머지 전체** | **BSL 1.1** |

**BSL 1.1 요약:**
- 개인/비상업/교육/오픈소스 → **무료**
- 사내 5인 이하 → **무료**
- 상업적 사용/6인 이상 → **유료 라이선스 필요**
- Rolling Change Date: 각 릴리스는 릴리스일 + 4년 후 Apache 2.0으로 자동 전환 (최신 0.17.0 → 2030-05-01). 자세한 내용은 [LICENSE.md](LICENSE.md).

## 폰트

pyhwpxlib 는 **나눔고딕** (네이버, SIL OFL 1.1) 을 신규 문서 메타 표기 default 로
사용하며, rhwp 렌더링 폴백용으로 ttf 를 임베드 (`vendor/`) 합니다.

### 함초롬돋움/바탕 · 맑은 고딕을 안 쓰는 이유

| 폰트 | 라이선스 | 이슈 |
|------|---------|------|
| 함초롬돋움/바탕 (HCR-) | 한컴 오피스 라이선스 | 한컴 오피스 사용자만 배포 허용 |
| 맑은 고딕 (Malgun Gothic) | Microsoft 라이선스 | Windows/Office 사용자만 배포 허용 |
| **나눔고딕/나눔명조** | **SIL OFL 1.1** | **재배포·임베드·수정 모두 자유** |

한컴·Microsoft 폰트는 재배포 제약이 있어, v0.16.1+ 부터 사용자에게
라이선스 위험이 전이되지 않도록 나눔고딕을 default 로 사용합니다.

### Default 변경

```python
from pyhwpxlib.themes import FontSet

# 명시적으로 맑은 고딕 지정 가능 (라이선스는 사용자 책임)
fonts = FontSet(heading_hangul='맑은 고딕', body_hangul='맑은 고딕',
                caption_hangul='맑은 고딕')
```

### HWP→HWPX 변환

`hwp2hwpx.convert()` 는 **원본 .hwp 의 폰트명을 그대로 보존** 합니다.
변환물의 폰트 라이선스 준수는 사용자 책임입니다.
