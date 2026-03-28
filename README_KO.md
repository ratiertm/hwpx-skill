# hwpx-skill

AI에게 말로 설명하면 한글 문서(HWPX)가 만들어집니다. 한컴오피스 설치가 필요 없습니다.

[**English**](README.md)

## 핵심 기능

AI(Claude Code, Cursor, ChatGPT 등)에게 원하는 문서를 자연어로 설명하면, AI가 CLI 명령어를 조합해서 `.hwpx` 파일을 생성합니다:

```
나: "3분기 매출 보고서 만들어줘. 제목, 개요, 월별 매출 표,
     핵심 성과 3개를 글머리표로, 마지막에 요약."

AI → CLI 명령어 실행 → 보고서.hwpx (한컴오피스에서 바로 열기)
```

AI 에이전트가 CLI 스킬 메타데이터를 읽고, 적절한 명령어(`document new`, `style add`, `table add`, `structure bullet-list`, ...)를 골라서 문서를 조립합니다. 코드를 작성하거나 한컴오피스를 열 필요 없이 서식이 적용된 `.hwpx` 파일을 받습니다.

**웹 UI**에서도 가능합니다 -- LLM 탭에서 지시문을 입력하면 문서가 생성됩니다.

## 다른 방법들

**마크다운에서 변환** -- 명령어 하나로 자동 서식 적용:

```bash
cli-anything-hwpx convert 보고서.md -o 보고서.hwpx
```

변환 시 자동 인식: 제목(#), **볼드**, *이탈릭*, 글머리표, 번호 목록, 코드 블록, 표, 하이퍼링크, 수평선

**CLI로 단계별 생성:**

```bash
# 빈 문서 만들기
cli-anything-hwpx document new -o 보고서.hwpx

# 스타일 텍스트 추가
cli-anything-hwpx --file 보고서.hwpx style add "프로젝트 보고서" --bold --font-size 16

# 표 추가 (헤더 + 데이터)
cli-anything-hwpx --file 보고서.hwpx table add -r 3 -c 2 \
  -h "이름,역할" -d "김철수,개발자" -d "이영희,디자이너"

# 코드 블록 추가
cli-anything-hwpx --file 보고서.hwpx structure code-block \
  "def hello():\n    print('안녕')" --lang python

# 2단 레이아웃 설정
cli-anything-hwpx --file 보고서.hwpx structure set-columns -n 2

# 텍스트 추출
cli-anything-hwpx --file 보고서.hwpx text extract
```

## 설치

```bash
git clone https://github.com/ratiertm/hwpx-skill.git
cd hwpx-skill/hwpx/agent-harness
pip install -e .
```

Python 3.10 이상 필요.

## 전체 명령어

### 문서 관리

| 명령어 | 예시 | 설명 |
|--------|------|------|
| `document new` | `document new -o my.hwpx` | 빈 문서 생성 |
| `document open` | `document open my.hwpx` | 기존 파일 열기 |
| `document save` | `document save output.hwpx` | 저장 |
| `document info` | `document info` | 섹션, 문단, 이미지 수 표시 |

### 텍스트

| 명령어 | 예시 | 설명 |
|--------|------|------|
| `text add` | `text add "안녕하세요"` | 문단 추가 |
| `text extract` | `text extract` | 전체 텍스트 출력 |
| `text find` | `text find "키워드"` | 텍스트 검색 |
| `text replace` | `text replace --old "초안" --new "최종"` | 찾아 바꾸기 |

### 스타일

| 명령어 | 예시 | 설명 |
|--------|------|------|
| `style add` | `style add "제목" -b -s 16 -c "#0000FF"` | 볼드, 16pt, 파란색 |

### 표

| 명령어 | 예시 | 설명 |
|--------|------|------|
| `table add` | `table add -r 3 -c 2 -h "A,B" -d "1,2"` | 데이터 포함 표 생성 |
| `table list` | `table list` | 모든 표 목록 |
| `table set-bgcolor` | `table set-bgcolor -r 0 -c 0 --color "#FFD700"` | 셀 배경색 |
| `table set-gradient` | `table set-gradient -r 0 -c 0 --start "#FF0000" --end "#0000FF"` | 그라데이션 배경 |

### 구조

| 명령어 | 예시 | 설명 |
|--------|------|------|
| `structure set-header` | `structure set-header "회사명"` | 머리말 |
| `structure set-footer` | `structure set-footer "꼬리말"` | 꼬리말 |
| `structure page-number` | `structure page-number` | 페이지 번호 |
| `structure bookmark` | `structure bookmark "1장"` | 책갈피 |
| `structure hyperlink` | `structure hyperlink "https://..." -t "링크"` | 하이퍼링크 |
| `structure code-block` | `structure code-block "print(1)" --lang python` | 코드 블록 (고정폭 + 배경) |
| `structure set-columns` | `structure set-columns -n 2 --separator SOLID` | 다단 레이아웃 |
| `structure bullet-list` | `structure bullet-list "항목1,항목2"` | 글머리표 목록 |
| `structure numbered-list` | `structure numbered-list "첫째,둘째"` | 번호 목록 |
| `structure nested-bullet-list` | `structure nested-bullet-list "0:상위,1:하위"` | 중첩 글머리표 |
| `structure footnote` | `structure footnote "각주 내용"` | 각주 |
| `structure rectangle` | `structure rectangle -w 14400 -h 7200` | 사각형 도형 |
| `structure ellipse` | `structure ellipse` | 타원 도형 |
| `structure line` | `structure line` | 수평선 |
| `structure equation` | `structure equation "E=mc^2"` | 수식 |

### 변환

| 명령어 | 예시 | 설명 |
|--------|------|------|
| `convert` | `convert 보고서.md -o 보고서.hwpx` | MD/HTML/TXT를 HWPX로 |

마크다운 변환 시 처리하는 요소: `# 제목`, `**볼드**`, `*이탈릭*`, `` `코드` ``, `[링크](url)`, `- 글머리표`, `1. 번호`, ` ``` 코드 블록 ``` `, `| 표 |`, `> 인용문`, `---` 구분선

### 내보내기

| 명령어 | 예시 | 설명 |
|--------|------|------|
| `export text` | `export text -o out.txt` | 텍스트로 내보내기 |
| `export markdown` | `export markdown -o out.md` | 마크다운으로 내보내기 |
| `export html` | `export html -o out.html` | HTML로 내보내기 |

### 기타

| 명령어 | 설명 |
|--------|------|
| `undo` / `redo` | 실행 취소 / 다시 실행 (최대 50단계) |
| `validate schema` | OWPML 스키마 검증 |
| `validate package` | ZIP/OPC 구조 검증 |
| `repl` | 대화형 편집 모드 |

## 웹 UI

브라우저에서 문서를 만드는 3가지 모드:

```bash
cd hwpx/agent-harness
pip install fastapi uvicorn python-multipart
python -m uvicorn web.server:app --port 8080
```

- **Direct Input** -- 텍스트 입력 + 폰트 크기 선택 → `.hwpx` 다운로드
- **LLM Instruction** -- 자연어로 설명하면 AI가 문서 생성
- **File Upload** -- MD/HTML/TXT 파일 업로드 → `.hwpx` 변환

## Python API

CLI 없이 코드에서 직접 사용:

```python
from hwpx import HwpxDocument

doc = HwpxDocument.new()

# 제목
title = doc.ensure_run_style(bold=True, height=1600)
doc.add_paragraph("프로젝트 보고서", char_pr_id_ref=title)

# 글머리표 목록
doc.add_bullet_list(["1단계", "2단계", "3단계"])

# 코드 블록
doc.add_code_block('print("안녕")', language="python")

# 표 + 그라데이션 헤더
tbl = doc.add_table(3, 2)
tbl.set_cell_text(0, 0, "항목")
tbl.set_cell_text(0, 1, "값")
doc.set_cell_gradient(0, 0, 0,
    start_color="#4A90D9", end_color="#1A5276")

# 2단 레이아웃
doc.set_columns(2, separator_type="SOLID")

# 하이퍼링크
doc.add_hyperlink("여기를 클릭", "https://example.com")

# 저장
doc.save_to_path("보고서.hwpx")
```

## HWPX 포맷이란?

HWPX는 한컴오피스의 차세대 문서 포맷입니다. ZIP 안에 XML 파일이 들어있는 구조로, Microsoft Word의 `.docx`와 비슷한 개념입니다. 한국 공공기관과 기업에서 표준으로 사용됩니다.

이 프로젝트는 순수 Python으로 HWPX 파일을 만들고 편집합니다. 한컴오피스 설치가 필요 없습니다.

## 참고

- [python-hwpx](https://github.com/airmang/python-hwpx) -- 고규현 (MIT)
- [CLI-Anything](https://github.com/HKUDS/CLI-Anything) (MIT)

## 라이선스

MIT
