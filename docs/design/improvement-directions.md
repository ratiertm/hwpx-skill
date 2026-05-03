# pyhwpxlib 개선 방향 상세 설계 메모

대상 항목:
- 3. validate vs lint 분리
- 4. font-check 강화
- 10. CLI `--json` 출력

---

## 3. validate vs lint 분리

### 목표
현재 `validate`는 이름상 “정상 파일인지”를 뜻하지만, 실제로는 ZIP 구조·필수 XML 존재·파싱 가능 여부 같은 **구조적 최소 유효성 검사**에 더 가깝다. 반면 사용자가 실제로 알고 싶은 것은 “Whale/한글에서 안 깨지나?”에 가까우므로, 둘의 역할을 분리하는 것이 바람직하다.

### 역할 정의

#### validate
구조적 최소 유효성 검사에 집중한다.

검사 항목 예시:
- ZIP 열림 여부
- `mimetype` 존재 여부
- `Contents/header.xml`, `Contents/section0.xml` 등 필수 파일 존재 여부
- XML 파싱 가능 여부
- 손상된 압축, 누락된 파일, 파싱 오류를 실패로 처리

#### lint
렌더링/호환성 위험 패턴을 탐지한다.

검사 항목 예시:
- 문단 텍스트 안의 `\n` 탐지
- 첫 content paragraph 이전의 빈 문단 탐지
- 표 셀 내부 텍스트의 위험 패턴 탐지
- 문서 선언 폰트와 실제 해상 가능 폰트의 불일치 탐지
- 너무 긴 단일 run / paragraph 경고

### 권장 CLI 구조

```bash
python -m pyhwpxlib validate file.hwpx
python -m pyhwpxlib lint file.hwpx
python -m pyhwpxlib lint file.hwpx --strict
python -m pyhwpxlib lint file.hwpx --format json
```

### 출력 정책
- `validate`: pass/fail 중심
- `lint`: warning/error/code/path 중심

### 예시 JSON 출력

```json
{
  "command": "lint",
  "ok": true,
  "file": "output.hwpx",
  "issues": [
    {
      "code": "TEXT_NEWLINE_IN_RUN",
      "severity": "warning",
      "message": "Paragraph text contains newline characters.",
      "path": "Contents/section0.xml",
      "hint": "Split into separate paragraphs instead of '\\n'."
    }
  ]
}
```

### 구현 우선순위
1. 기존 `validate` 유지
2. `lint` 신설
3. guide에서 이미 금지한 규칙을 우선 룰로 코드화
4. 이후 Whale/Hancom 실사용 이슈를 룰셋에 점진적으로 추가

---

## 4. font-check 강화

### 목표
현재 font-check는 “문서에 적힌 폰트 이름 확인” 수준에 머무르기 쉽다. 그러나 실제 문제는 **어떤 폰트 파일로 최종 해상되는지**에 있다. 따라서 선언 폰트, 해상 폰트, fallback 여부, preview 일치성 위험까지 보여주는 방향으로 확장하는 것이 좋다.

### 현재 한계
- 문서 내부 선언 폰트명 추출에 가까움
- 실제 preview 렌더링의 최종 fallback 결과와 다를 수 있음
- 사용자 지정 `font_map`이 반영되지 않음
- “문서에 선언된 폰트”와 “실제로 렌더된 폰트 파일”은 다를 수 있음

### 강화 방향

#### 1) 선언 폰트 / 해상 폰트 분리 출력
예시:

```json
{
  "declared_font": "Malgun Gothic",
  "resolved_font": "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
  "source": "font_map_alias",
  "fallback_used": true
}
```

#### 2) `--font-map` 옵션 추가
사용자가 JSON 파일로 별칭 맵을 줄 수 있게 한다.

```bash
python -m pyhwpxlib font-check file.hwpx --font-map fonts.json
```

#### 3) 위험도 등급 추가
상태 예시:
- `ok`: 선언 폰트와 해상 폰트가 동일 계열
- `alias`: 별칭 매핑으로 해상됨
- `fallback`: 기본 fallback 사용
- `missing`: 해상 실패 가능성 높음

#### 4) 프리뷰 연계 검사
가능하면 `font-check --preview` 모드 추가:
- 문서 폰트 추출
- `RhwpEngine(font_map=...)`로 실제 해상
- SVG의 `font-family` 목록까지 확인
- 문서/HWPX/RHWP/SVG 간 mismatch 리포트 제공

### 권장 출력 예시

사람용:

```text
[OK]       Noto Sans CJK KR -> /fonts/NotoSansCJKkr-Regular.otf
[ALIAS]    Malgun Gothic -> /fonts/NotoSansCJKkr-Regular.otf
[FALLBACK] Helvetica -> /fonts/DejaVuSans.ttf
[WARN]     Apple SD Gothic Neo declared in document, but SVG resolved to sans-serif
```

자동화용:

```json
{
  "command": "font-check",
  "ok": false,
  "file": "a.hwpx",
  "fonts": [
    {
      "declared": "Malgun Gothic",
      "resolved": "/fonts/NotoSansCJK-Regular.ttc",
      "status": "alias"
    }
  ],
  "summary": {
    "declared": 6,
    "resolved": 6,
    "fallback_used": 2,
    "svg_mismatch": 1
  }
}
```

### 구현 우선순위
1. `font-check --json` 추가
2. `--font-map` 지원
3. resolved/fallback 상태 추가
4. preview-aware mismatch 검사 추가

---

## 10. CLI --json 출력

### 목표
`pyhwpxlib`는 사람이 쓰는 CLI를 넘어서, LLM / MCP / 자동화 파이프라인에도 맞는 구조로 가고 있다. 따라서 구조화 출력이 필요하다.

### 적용 우선순위
먼저 붙일 명령:
- `validate`
- `lint`
- `font-check`
- `themes list`
- `info`

### 구현 원칙

#### 1) 사람용 출력과 JSON 출력을 완전히 분리
- 기본: 사람이 읽기 좋은 콘솔 출력
- `--json`: 오직 JSON만 출력
- stderr에는 진짜 에러만 출력

#### 2) 공통 응답 스키마 고정

```json
{
  "command": "validate",
  "version": "0.7.0",
  "ok": true,
  "file": "output.hwpx",
  "data": {},
  "warnings": [],
  "errors": []
}
```

#### 3) 종료 코드 일관성 유지
- `ok=true` → exit code 0
- fatal error → exit code 1
- lint warning만 있음 → exit code 0
- `--strict`에서 warning을 실패로 볼 경우 → 별도 종료 코드 사용 가능

### 명령별 예시 스키마

#### validate --json

```json
{
  "command": "validate",
  "ok": true,
  "file": "a.hwpx",
  "checks": [
    {"name": "zip_open", "ok": true},
    {"name": "mimetype_exists", "ok": true},
    {"name": "header_xml_parse", "ok": true}
  ]
}
```

#### lint --json

```json
{
  "command": "lint",
  "ok": true,
  "file": "a.hwpx",
  "issues": [
    {
      "code": "TEXT_NEWLINE_IN_RUN",
      "severity": "warning",
      "message": "Paragraph contains newline characters.",
      "path": "Contents/section0.xml"
    }
  ]
}
```

#### font-check --json

```json
{
  "command": "font-check",
  "ok": false,
  "file": "a.hwpx",
  "fonts": [
    {
      "declared": "Malgun Gothic",
      "resolved": "/fonts/NotoSansCJK-Regular.ttc",
      "status": "alias"
    }
  ]
}
```

#### themes list --json

```json
{
  "command": "themes list",
  "ok": true,
  "themes": [
    {"name": "default", "source": "builtin"},
    {"name": "forest", "source": "builtin"},
    {"name": "custom/my_style", "source": "user"}
  ]
}
```

### 구현 팁
공통 헬퍼를 두면 유지보수가 편하다.

```python
def emit(result: dict, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        render_human(result)
```

---

## 추천 추진 순서

### 1단계
- `validate` 유지
- `lint` 신설
- `validate --json`, `font-check --json` 추가

### 2단계
- `font-check --font-map`
- `font-check`에 resolved/fallback 상태 추가

### 3단계
- `lint --strict`
- SVG mismatch까지 보는 preview-aware font-check

---

## 한 줄 정리
- `validate/lint`는 **구조 검사 vs 렌더 위험 검사**로 분리
- `font-check`는 **폰트 이름 확인기 → 실제 해상 결과 분석기**로 확장
- `--json`은 **사람용 CLI를 자동화용 CLI로 확장하는 기반**

---

## 참고 근거
- Python `argparse`는 하위 명령(subcommands) 기반 CLI 구성에 적합하며, `add_subparsers()`를 통해 명령별 파서를 둘 수 있다.
- Python `json` 모듈은 `json.dumps(..., ensure_ascii=False)`를 통해 한글을 이스케이프하지 않고 출력할 수 있다.
