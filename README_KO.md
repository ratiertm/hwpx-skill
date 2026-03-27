# hwpx-skill

AI 에이전트가 한글 문서(HWPX)를 자동으로 생성, 편집, 검증할 수 있게 하는 CLI 스킬. 한컴오피스 설치가 필요 없습니다.

[CLI-Anything](https://github.com/HKUDS/CLI-Anything) 프레임워크로 [python-hwpx](https://github.com/airmang/python-hwpx) 라이브러리를 래핑하여, Claude Code, Cursor, OpenClaw 같은 AI 에이전트가 CLI 명령어만으로 `.hwpx` 문서를 조작할 수 있습니다.

[**English**](README.md)

## 아키텍처

```
AI Agent (Claude Code, Cursor, OpenClaw, ...)
    │  CLI 명령어
    ▼
cli-anything-hwpx (agent-harness)
    │  Python API 호출
    ▼
python-hwpx (HwpxDocument)
    │  XML 조작
    ▼
.hwpx 파일 (ZIP + XML, OWPML 규격)
```

| 계층 | 역할 | 디렉토리 |
|------|------|----------|
| **CLI-Anything** | 모든 소프트웨어를 에이전트용 CLI로 래핑하는 프레임워크 | `cli-anything-original/` |
| **python-hwpx** | HWPX 포맷을 순수 Python으로 읽고/쓰고/편집하는 라이브러리 | `python-hwpx-fork/`, `ratiertm-hwpx/` |
| **agent-harness** | 위 두 개를 결합한 CLI 스킬 (이 프로젝트의 핵심) | `hwpx/agent-harness/` |
| **Web UI** | FastAPI 서버 + 브라우저 기반 문서 생성 | `hwpx/agent-harness/web/` |

## 설치

```bash
cd hwpx/agent-harness
pip install -e .
```

요구 사항: Python >= 3.10, python-hwpx >= 2.8.0, click >= 8.0.0

## 빠른 시작

```bash
# 새 문서 만들기
cli-anything-hwpx document new --output report.hwpx

# 텍스트 추가 (자동 저장)
cli-anything-hwpx --file report.hwpx text add "프로그램 구조 설계서"

# 헤더와 데이터가 있는 표 추가
cli-anything-hwpx --file report.hwpx table add -r 3 -c 2 \
  -h "이름,역할" \
  -d "CLI-Anything,프레임워크" \
  -d "python-hwpx,라이브러리"

# 마크다운을 HWPX로 변환
cli-anything-hwpx convert README.md -o readme.hwpx

# 텍스트 추출
cli-anything-hwpx --file report.hwpx text extract
```

## 웹 UI

브라우저에서 문서 생성, LLM 지시, 파일 변환을 할 수 있는 웹 인터페이스입니다.

```bash
cd hwpx/agent-harness
pip install fastapi uvicorn python-multipart
python -m uvicorn web.server:app --port 8080
# http://localhost:8080 접속
```

3개 탭:
- **Direct Input** — 직접 텍스트 입력 + 제목 폰트 크기 선택 → HWPX 생성 + 다운로드
- **LLM Instruction** — 자연어 지시문 입력 → AI가 문서 내용 생성 → HWPX 다운로드
- **File Upload** — HTML/MD/TXT 파일 업로드 → HWPX로 변환 + 다운로드

## 명령어 목록

| 그룹 | 명령어 | 설명 |
|------|--------|------|
| `document` | new, open, save, info | 문서 생성/열기/저장/정보 |
| `text` | extract, find, replace, add | 텍스트 추출/검색/치환/추가 |
| `table` | add (--header, --data), list | 헤더+데이터 표 추가/목록 |
| `image` | add, list, remove | 이미지 추가/목록/삭제 |
| `export` | text, markdown, html | 텍스트/마크다운/HTML 변환 |
| `convert` | (소스파일) -o output.hwpx | HTML/MD/TXT → HWPX 변환 |
| `validate` | schema, package | 스키마/패키지 검증 |
| `structure` | sections, add-section, set-header, set-footer, bookmark, hyperlink | 구조 조작 |
| `undo` / `redo` | — | 실행 취소/다시 실행 (최대 50단계) |
| `repl` | — | 대화형 편집 모드 |

## 주요 기능

- **one-shot 자동 저장** — `--file` 모드에서 변경 명령 실행 후 파일에 자동 저장
- **표에 데이터 입력** — `table add -h "A,B" -d "1,2" -d "3,4"` 로 셀 값 채우기
- **파일 변환** — `convert source.md -o output.hwpx` (HTML, Markdown, 텍스트 지원)
- **폰트 크기** — `ensure_run_style(height=2000)` 으로 20pt 텍스트 (OWPML 규격: 100 hwpunit = 1pt)
- **글자 색상** — `ensure_run_style(text_color="#FF0000")` 으로 빨간 글자
- **JSON 출력** — `--json` 플래그로 AI 에이전트용 구조화된 출력
- **크로스 플랫폼** — Windows, macOS, Linux, CI/CD 어디서든 동작 (순수 Python)

## 폰트 크기 (OWPML 규격)

python-hwpx fork (`ratiertm-hwpx/`)에 폰트 크기와 글자 색상 기능을 추가했습니다:

```python
from hwpx import HwpxDocument

doc = HwpxDocument.new()

# 20pt 굵은 제목
title = doc.ensure_run_style(bold=True, height=2000)
doc.add_paragraph("제목", char_pr_id_ref=title)

# 12pt 파란 글씨
blue = doc.ensure_run_style(height=1200, text_color="#0000FF")
doc.add_paragraph("파란 텍스트", char_pr_id_ref=blue)

doc.save_to_path("styled.hwpx")
```

Height 단위: 1 hwpunit = 1/100 pt (OWPML `<hh:charPr height="1000">` = 10pt)

## HWPX 포맷이란?

HWPX는 한컴오피스의 차세대 문서 포맷으로, 기존 바이너리 `.hwp`를 대체합니다.

- **구조**: ZIP 아카이브 안에 XML 문서 (OWPML/OPC 규격)
- **구성**: `mimetype`, `META-INF/container.xml`, `Contents/` (본문), `BinData/` (이미지/폰트), `header.xml` (메타데이터)
- **크로스 플랫폼**: Windows, macOS, Linux, CI/CD 어디서든 동작

## 프로젝트 구조

```
hwpx-skill/
├── hwpx/agent-harness/          # 핵심 — CLI 스킬 + 웹 UI
│   ├── cli_anything/hwpx/
│   │   ├── hwpx_cli.py          # Click 기반 CLI + REPL
│   │   ├── core/                 # document, text, table, image, export, validate, structure, session
│   │   ├── utils/repl_skin.py   # REPL 인터페이스
│   │   └── skills/SKILL.md      # AI 에이전트 탐색용 메타데이터
│   ├── web/
│   │   ├── server.py            # FastAPI 서버
│   │   └── index.html           # 웹 UI
│   ├── tests/                   # 64개 테스트 (core + autosave + convert)
│   └── setup.py
├── ratiertm-hwpx/               # python-hwpx fork (폰트 크기 + 색상 + lxml 수정)
├── cli-anything-original/       # CLI-Anything 프레임워크
└── docs/                        # PDCA 문서
```

## 테스트

```bash
cd hwpx/agent-harness
pip install -e ".[dev]"
pytest tests/ -v
# 64개 테스트 통과
```

## 참고

- **python-hwpx**: [github.com/airmang/python-hwpx](https://github.com/airmang/python-hwpx) (고규현, MIT)
- **CLI-Anything**: [github.com/HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything) (MIT)

## 라이선스

MIT
