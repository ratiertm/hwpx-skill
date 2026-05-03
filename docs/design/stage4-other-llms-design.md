# Stage 4 설계 — Other LLMs 통합

> ChatGPT · Gemini · Cursor · Windsurf · Aider · Ollama 등  
> MCP·filesystem·메모리가 없는 환경에서의 컨텍스트 지속 패턴.

---

## 환경 분석

| LLM | 파일시스템 | 지속 메모리 | 주입 위치 | 난이도 |
|-----|-----------|------------|----------|--------|
| ChatGPT (UI) | ❌ | Custom Instructions (1500자) | 첫 메시지 or Knowledge | ★★ |
| ChatGPT GPT Builder | ❌ | Instructions + Knowledge 파일 | Knowledge 업로드 | ★ |
| Gemini (UI) | ❌ | ❌ | 첫 메시지 | ★★★ |
| Gemini API | ❌ | system_instruction | API 호출 시 | ★★ |
| Cursor | ✅ `.cursor/rules/` | `.cursorrules` 파일 | 프로젝트 영구 | ★ |
| Windsurf | ✅ | `.windsurfrules` | 프로젝트 영구 | ★ |
| Aider | ✅ | `--system-prompt` | CLI 플래그 | ★★ |
| Ollama | ❌ | Modelfile | 모델 설정 | ★★★ |

**핵심 제약**: 이 환경들은 사용자 로컬 파일시스템에 접근할 수 없음.  
→ `template context` 출력을 **텍스트로 주입**하는 것이 유일한 방법.

---

## 구성 5개

```
Stage 4
  ├── 4-A: template context 출력 형식 최적화 (--brief 플래그)
  ├── 4-B: 수동 주입 패턴 (universal)
  ├── 4-C: Cursor / Windsurf 전용 파일 생성
  ├── 4-D: API 자동화 패턴 (개발자용)
  └── 4-E: chatgpt_hwpx_guide.md 업데이트
```

---

## Stage 4-A: `template context` 출력 형식 최적화

Other LLMs는 토큰 비용과 컨텍스트 한계가 있음.  
`--brief` / `--full` 플래그로 출력량을 제어.

### 기본값 (`--full`, 기존 동작 유지)

```markdown
# 양식: 검수확인서
> 사내 검수확인서 1매 표준

- 파일: ~/.local/share/pyhwpxlib/templates/geomsu_hwaginso.hwpx
- 구조: B형 (patch 방식)
- 페이지: 1매 고정

## 필드 목록
| 키 | 레이블 | 위치 |
|geomsu_ja | 검수자 | 표0-행2-열1 |
...

## 결정사항
- [2026-05-01] 서명란은 이미지(sign.png) 삽입
- [2026-04-25] 구조 B 확인

## 최근 채우기 값
{"geomsu_ja": "홍길동", ...}
```

**≈ 400~600 토큰**

### `--brief` (Other LLMs 주입용)

```markdown
# hwpx 양식: 검수확인서 (B형·1매)
필드: geomsu_ja(검수자), geomsu_il(검수일자), geomsu_hang(검수항목)
주의: 서명란은 이미지 삽입. 구조 B → patch 방식 사용.
최근값: {"geomsu_ja":"홍길동","geomsu_il":"2026. 5. 1."}
```

**≈ 80~120 토큰**

### CLI 명세 추가 (Stage 1 범위)

```bash
pyhwpxlib template context <이름>          # full (기본)
pyhwpxlib template context <이름> --brief  # 토큰 절약형
pyhwpxlib template context <이름> --no-history  # 이력 제외
```

---

## Stage 4-B: 수동 주입 패턴 (universal)

### 기본 패턴

```bash
# 1. 터미널에서 컨텍스트 출력
pyhwpxlib template context 검수확인서

# 2. 출력을 LLM 시스템 프롬프트 or 첫 메시지에 붙여넣기
```

### Shell alias (macOS/Linux, `~/.zshrc`)

```bash
# 컨텍스트를 클립보드로 복사
hwpx-ctx() {
  if [ -z "$1" ]; then
    pyhwpxlib template list
  else
    pyhwpxlib template context "$@" | pbcopy   # macOS
    # pyhwpxlib template context "$@" | xclip  # Linux
    echo "[hwpx] '$1' 컨텍스트 복사됨 → 시스템 프롬프트에 붙여넣기"
  fi
}

# Brief 버전 (ChatGPT Custom Instructions용)
hwpx-ctx-brief() {
  pyhwpxlib template context "$1" --brief | pbcopy
  echo "[hwpx] '$1' brief 컨텍스트 복사됨"
}

# 전체 목록 표시
alias hwpx-ls='pyhwpxlib template list'
```

**사용:**
```bash
hwpx-ctx 검수확인서           # full → 클립보드
hwpx-ctx-brief 검수확인서     # brief → 클립보드 (ChatGPT용)
hwpx-ls                      # 등록 양식 목록
```

### ChatGPT Custom Instructions 패턴

Custom Instructions는 1,500자 제한 → `--brief` 필수.

```
[hwpx 양식 워크스페이스]
아래 양식들이 등록되어 있습니다. 양식 작업 시 이 정보를 우선 사용하세요.

# hwpx 양식: 검수확인서 (B형·1매)
필드: geomsu_ja(검수자), geomsu_il(검수일자), geomsu_hang(검수항목)
주의: 서명란은 이미지 삽입. 구조 B → patch 방식.
최근값: {"geomsu_ja":"홍길동","geomsu_il":"2026. 5. 1."}

# hwpx 양식: 의견제출서 (A형·자유)
필드: ...
```

→ `hwpx-ctx-brief 검수확인서` 출력을 Custom Instructions에 수동 갱신.

### ChatGPT GPT Builder / Knowledge 파일 패턴

Knowledge 파일은 용량 제한이 없음 → `--full` 사용 가능.

```bash
# 1. 컨텍스트를 파일로 내보내기
pyhwpxlib template context 검수확인서 > hwpx_검수확인서_context.md

# 2. GPT Builder Knowledge에 업로드
#    → 새 세션마다 LLM이 자동 참조
```

여러 양식:
```bash
pyhwpxlib template list --names | while read name; do
  pyhwpxlib template context "$name" >> hwpx_all_contexts.md
  echo "\n---\n" >> hwpx_all_contexts.md
done
# hwpx_all_contexts.md를 Knowledge에 업로드
```

---

## Stage 4-C: Cursor / Windsurf 전용 통합

Cursor·Windsurf는 `.cursor/rules/` 또는 `.windsurfrules` 파일을 통해  
프로젝트별 또는 전역 컨텍스트를 영구 주입할 수 있음.  
→ 한 번 설정하면 매 세션마다 자동 로드. **Other LLMs 중 가장 강력.**

### Cursor — 전역 규칙

파일: `~/.cursor/rules/hwpx.mdc`

```markdown
---
description: hwpx 양식 워크스페이스 컨텍스트
alwaysApply: false
---

당신은 HWPX 양식 전문가입니다. pyhwpxlib를 사용합니다.

## 등록된 양식
<!-- pyhwpxlib template context --brief 출력을 여기에 붙여넣기 -->
# hwpx 양식: 검수확인서 (B형·1매)
필드: geomsu_ja(검수자), geomsu_il(검수일자), geomsu_hang(검수항목)
주의: 서명란은 이미지 삽입. 구조 B → patch 방식.
최근값: {"geomsu_ja":"홍길동","geomsu_il":"2026. 5. 1."}

## 채우기 완료 후
변경사항이 있으면 아래 명령 실행 후 이 파일도 갱신:
pyhwpxlib template log-fill <이름> --data '<json>'
```

### `template export-cursor` 명령 (신규 — Stage 4 전용)

반복 붙여넣기를 없애기 위해 Cursor 규칙 파일을 자동 생성/갱신.

```bash
# Cursor 전역 규칙 생성/갱신
pyhwpxlib template export-cursor

# 특정 양식만
pyhwpxlib template export-cursor 검수확인서 의견제출서

# 프로젝트별 (현재 디렉터리에 .cursor/rules/hwpx.mdc 생성)
pyhwpxlib template export-cursor --local
```

내부 동작:
1. 등록 양식 전체 `--brief` 컨텍스트 수집
2. `~/.cursor/rules/hwpx.mdc` 덮어쓰기
3. 완료 메시지 출력

**출력 파일 예시** (`~/.cursor/rules/hwpx.mdc`):

```markdown
---
description: hwpx 양식 워크스페이스 (자동 생성 2026-05-01)
alwaysApply: false
---

pyhwpxlib 양식 컨텍스트. 양식 작업 시 이 정보를 우선 사용.

## 검수확인서
구조: B형·1매 고정 | 서명: 이미지 삽입
필드: geomsu_ja(검수자) / geomsu_il(검수일자) / geomsu_hang(검수항목)
최근값: {"geomsu_ja":"홍길동","geomsu_il":"2026. 5. 1."}

## 의견제출서
구조: A형·자유 | fill_by_labels 사용
필드: name(이름) / date(날짜) / content(내용)
최근값: {"name":"김철수","date":"2026. 4. 28."}

---
*갱신: pyhwpxlib template export-cursor*
```

### Windsurf

```bash
# .windsurfrules는 단순 마크다운/텍스트
pyhwpxlib template export-cursor --windsurf
# → 현재 디렉터리 .windsurfrules 생성/갱신
```

---

## Stage 4-D: API 자동화 패턴 (개발자용)

pyhwpxlib를 LLM API 호출 파이프라인에 통합.

### Python

```python
import subprocess

def hwpx_context(name: str, brief: bool = False) -> str:
    """양식 컨텍스트를 시스템 프롬프트에 주입."""
    cmd = ["pyhwpxlib", "template", "context", name]
    if brief:
        cmd.append("--brief")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""

def hwpx_all_contexts(brief: bool = True) -> str:
    """등록된 모든 양식 컨텍스트를 하나의 문자열로."""
    result = subprocess.run(
        ["pyhwpxlib", "template", "list", "--names"],
        capture_output=True, text=True
    )
    names = result.stdout.strip().split("\n")
    return "\n\n---\n\n".join(hwpx_context(n, brief=brief) for n in names if n)

# OpenAI API 사용 예
from openai import OpenAI
client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": f"""당신은 HWPX 양식 전문가입니다.

{hwpx_all_contexts(brief=True)}"""
        },
        {"role": "user", "content": "검수확인서 채워줘. 검수자: 홍길동, 날짜: 2026. 5. 1."}
    ]
)
```

### Node.js / TypeScript

```typescript
import { execSync } from "child_process";

function hwpxContext(name: string, brief = false): string {
  const flag = brief ? " --brief" : "";
  try {
    return execSync(`pyhwpxlib template context ${name}${flag}`, {
      encoding: "utf-8",
    });
  } catch {
    return "";
  }
}

// 사용 예
const systemPrompt = `당신은 HWPX 양식 전문가입니다.\n\n${hwpxContext("검수확인서", true)}`;
```

---

## Stage 4-E: chatgpt_hwpx_guide.md 업데이트

### 추가할 섹션 (맨 앞 "설치" 바로 뒤)

```markdown
## 0. 양식 컨텍스트 주입 (세션 간 기억 보완)

이 환경에서는 로컬 파일시스템에 접근할 수 없어 자동 컨텍스트 로드가 불가.  
대신 **대화 시작 전** 아래 단계를 거치면 매 세션 재설명이 불필요해짐.

**방법 1 — 시스템 프롬프트 or 첫 메시지에 붙여넣기 (범용)**
```bash
# 로컬 터미널에서 실행:
pyhwpxlib template context 검수확인서 --brief
# 출력을 복사 → 시스템 프롬프트 또는 대화 첫 메시지에 붙여넣기
```

**방법 2 — GPT Builder Knowledge 파일 (ChatGPT)**
```bash
pyhwpxlib template context 검수확인서 > hwpx_검수확인서.md
# 생성된 .md 파일을 GPT Builder Knowledge에 업로드
# → 이후 모든 대화에서 자동 참조
```

**방법 3 — Custom Instructions (ChatGPT, 1500자 제한)**
```bash
pyhwpxlib template context 검수확인서 --brief
# 출력을 Custom Instructions에 붙여넣기
```
```

### 업데이트할 섹션 — 워크플로우 [3] 양식 채우기

```markdown
### 워크플로우 [3] 양식 채우기

**0. 컨텍스트 확인**
- 시스템 프롬프트에 양식 컨텍스트가 주입되어 있으면 → 바로 3단계로 이동
- 없으면 → "양식 파일을 업로드해주세요"

1. 양식 파일 업로드 (컨텍스트 없을 때)
2. SVG 프리뷰 렌더링 → 양식 분석 (구조 판정 포함)
3. 필드 입력값 사용자에게 요청
4. fill_template 또는 unpack → 문자열 교체 → pack
5. SVG 프리뷰로 결과 검증
6. "Whale에서 확인해주세요"
```

---

## 변경 파일 목록

| 파일 | 변경 타입 | 내용 |
|------|-----------|------|
| `pyhwpxlib/templates/context.py` | 신규 | `--brief` / `--no-history` 출력 모드 |
| `pyhwpxlib/templates/export.py` | 신규 | `export-cursor` / `export-windsurf` 명령 |
| `pyhwpxlib/cli.py` | 수정 | `template context --brief`, `template export-cursor` 명령 등록 |
| `skill/chatgpt_hwpx_guide.md` | 수정 | 섹션 0 추가 + 워크플로우 [3] 업데이트 |

---

## 단계별 의존성

```
Stage 1 완료 필요:
  template context 명령     ← --brief 플래그 추가로 확장
  
Stage 4 신규:
  template context --brief  ← token 절약 출력
  template list --names     ← 이름 목록만 (API 자동화용)
  template export-cursor    ← Cursor 규칙 파일 자동 생성
  template export-cursor --windsurf ← Windsurf 규칙 파일
```

---

## 권장 사용 환경별 최적 경로

```
ChatGPT UI       → --brief → Custom Instructions (수동, 주기적 갱신)
ChatGPT GPT      → --full  → Knowledge 파일 업로드 (설정 1회)
Gemini UI        → --brief → 첫 메시지 붙여넣기 (매 세션)
Cursor           → export-cursor (설정 1회, 이후 자동)
Windsurf         → export-cursor --windsurf (설정 1회)
API (개발자)     → Python/Node snippet으로 자동 주입
```
