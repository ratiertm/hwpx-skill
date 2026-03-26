# hwpx-skill

AI 에이전트가 한글 문서(HWPX)를 자동으로 생성, 편집, 검증할 수 있게 하는 CLI 스킬.

[CLI-Anything](https://github.com/HKUDS/CLI-Anything) 프레임워크로 [python-hwpx](https://github.com/airmang/python-hwpx) 라이브러리를 래핑하여, Claude Code 같은 AI 에이전트가 CLI 명령어만으로 `.hwpx` 문서를 조작할 수 있습니다. 한컴오피스 설치가 필요 없습니다.

## 아키텍처

```
AI Agent (Claude Code, OpenClaw, Cursor, ...)
    │  CLI 명령어
    ▼
cli-anything-hwpx (agent-harness)
    │  Python API 호출
    ▼
python-hwpx (HwpxDocument)
    │  XML 조작
    ▼
.hwpx 파일 (ZIP + XML)
```

| 계층 | 역할 | 디렉토리 |
|------|------|----------|
| **CLI-Anything** | 모든 소프트웨어를 에이전트용 CLI로 래핑하는 프레임워크 | `cli-anything-original/` |
| **python-hwpx** | HWPX 포맷을 순수 Python으로 읽고/쓰고/편집하는 라이브러리 | `python-hwpx-fork/`, `ratiertm-hwpx/` |
| **agent-harness** | 위 두 개를 결합한 CLI 스킬 (이 프로젝트의 핵심) | `hwpx/agent-harness/` |

## 설치

```bash
cd hwpx/agent-harness
pip install -e .
```

요구 사항: Python >= 3.10, python-hwpx >= 2.8.0, click >= 8.0.0

## 사용법

### 문서 생성 및 편집

```bash
# 새 문서 만들기
cli-anything-hwpx document new --output report.hwpx

# 텍스트 추가
cli-anything-hwpx --file report.hwpx text add "제목: 프로그램 구조 설계서"

# 표 추가
cli-anything-hwpx --file report.hwpx table add --rows 5 --cols 3

# 이미지 삽입
cli-anything-hwpx --file report.hwpx image add diagram.png --width 150 --height 100

# 저장
cli-anything-hwpx --file report.hwpx document save output.hwpx
```

### 텍스트 추출 및 변환

```bash
# 텍스트 추출
cli-anything-hwpx --file report.hwpx text extract

# 마크다운으로 변환
cli-anything-hwpx --file report.hwpx export markdown -o report.md

# HTML로 변환
cli-anything-hwpx --file report.hwpx export html -o report.html
```

### 찾기 및 바꾸기

```bash
cli-anything-hwpx --file report.hwpx text find "초안"
cli-anything-hwpx --file report.hwpx text replace --old "초안" --new "최종본"
```

### 검증

```bash
cli-anything-hwpx validate schema document.hwpx
cli-anything-hwpx validate package document.hwpx
```

### 대화형 모드 (REPL)

```bash
cli-anything-hwpx repl
```

### JSON 출력 (에이전트용)

모든 명령어에 `--json` 플래그를 붙이면 구조화된 JSON으로 출력합니다:

```bash
cli-anything-hwpx --json --file doc.hwpx document info
# {"sections": 2, "paragraphs": 15, "images": 3, "text_length": 4520}
```

## 명령어 목록

| 그룹 | 명령어 | 설명 |
|------|--------|------|
| `document` | new, open, save, info | 문서 생성/열기/저장/정보 |
| `text` | extract, find, replace, add | 텍스트 추출/검색/치환/추가 |
| `table` | add, list | 표 추가/목록 |
| `image` | add, list, remove | 이미지 추가/목록/삭제 |
| `export` | text, markdown, html | 텍스트/마크다운/HTML 변환 |
| `validate` | schema, package | 스키마/패키지 검증 |
| `structure` | sections, add-section, set-header, set-footer, bookmark, hyperlink | 구조 조작 |
| `undo` / `redo` | — | 실행 취소/다시 실행 (최대 50단계) |
| `repl` | — | 대화형 편집 모드 |

## 프로젝트 구조

```
hwpx-skill/
├── hwpx/agent-harness/          # 핵심 — CLI 스킬
│   ├── cli_anything/hwpx/
│   │   ├── hwpx_cli.py          # Click 기반 CLI + REPL
│   │   ├── core/
│   │   │   ├── session.py       # Undo/Redo 세션 관리
│   │   │   ├── document.py      # 문서 생성/열기/저장
│   │   │   ├── text.py          # 텍스트 추출/검색/치환
│   │   │   ├── table.py         # 표 조작
│   │   │   ├── image.py         # 이미지 조작
│   │   │   ├── export.py        # 텍스트/MD/HTML 변환
│   │   │   ├── validate.py      # 스키마/패키지 검증
│   │   │   └── structure.py     # 섹션/머리글/바닥글/북마크
│   │   ├── utils/
│   │   │   └── repl_skin.py     # REPL 인터페이스
│   │   └── skills/
│   │       └── SKILL.md         # AI 에이전트 탐색용 메타데이터
│   ├── setup.py
│   └── HWPX.md                  # HWPX 포맷 SOP
├── cli-anything-original/       # CLI-Anything 프레임워크 원본
├── python-hwpx-fork/            # python-hwpx 라이브러리 fork
├── ratiertm-hwpx/               # python-hwpx 수정 fork
└── docs/                        # 생성된 HWPX 문서 결과물
```

## HWPX 포맷이란?

HWPX는 한컴오피스의 차세대 문서 포맷으로, 기존 바이너리 `.hwp`를 대체합니다.

- **구조**: ZIP 아카이브 안에 XML 문서 (OWPML/OPC 규격)
- **구성**: `mimetype`, `META-INF/container.xml`, `Contents/` (본문), `BinData/` (이미지/폰트), `header.xml` (메타데이터)
- **크로스 플랫폼**: Windows, macOS, Linux, CI/CD 어디서든 동작

## python-hwpx 주요 API

| 클래스 | 용도 |
|--------|------|
| `HwpxDocument` | 문서 편집 API (79개 메서드) |
| `HwpxPackage` | OPC 컨테이너 처리 |
| `TextExtractor` | 섹션/문단 순회 및 텍스트 추출 |
| `ObjectFinder` | 태그/속성/XPath 기반 요소 검색 |

## 참고

- **python-hwpx**: [github.com/airmang/python-hwpx](https://github.com/airmang/python-hwpx) (고규현, MIT)
- **CLI-Anything**: [github.com/HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything) (MIT)

## 라이선스

MIT
