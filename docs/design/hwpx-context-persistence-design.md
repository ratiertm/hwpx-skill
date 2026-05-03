# hwpx 컨텍스트 지속성 시스템 — 단계별 설계

> 목표: 채팅 세션이 바뀌어도 양식 컨텍스트(구조 판정·결정사항·이전 값)를 
> LLM이 자동으로 복원할 수 있도록 한다.  
> claude.ai · Claude Desktop · Claude Code · 타 LLM 모두 동일한 데이터를 읽는다.

---

## 현황 파악 (0.14.0 기준)

### 이미 있는 것

| 기능 | 명령 | 비고 |
|------|------|------|
| 양식 등록 | `pyhwpxlib template add` | HWP→HWPX 변환 + auto_schema |
| 스키마 조회 | `pyhwpxlib template show` | 원시 JSON 반환 (LLM-unfriendly) |
| 목록 조회 | `pyhwpxlib template list` | 이름·경로만 (메타데이터 없음) |
| 양식 채우기 | `pyhwpxlib template fill` | data.json → output.hwpx |
| 스키마 진단 | `pyhwpxlib template diagnose` | auto_schema 정확도 분석 |
| 저장 위치 | `~/.local/share/pyhwpxlib/templates/` | XDG 표준, 플랫폼 공통 |

### 없는 것 (= 이번 설계 대상)

- `template context <이름>` — LLM에 주입 가능한 마크다운 컨텍스트 출력
- `template annotate <이름>` — 결정사항·설명 갱신
- `template log-fill <이름>` — 채우기 이력 기록
- `<name>.decisions.md` — 세션 간 누적 결정사항 파일
- `<name>.history.json` — 이전 채우기 값 (재사용 소스)
- schema.json 메타데이터 확장 — description, structure_type, page_standard, usage stats
- SKILL.md Step F — 자동 컨텍스트 보존 단계
- SessionStart hook — Claude Code/Desktop 세션 시작 시 자동 목록 표시

---

## Stage 1 — `pyhwpxlib template` CLI 확장

### 1-1. 파일 구조 확장

```
~/.local/share/pyhwpxlib/templates/
  ├── geomsu_hwaginso.hwpx          # 원본 양식 (기존)
  ├── geomsu_hwaginso.schema.json   # auto_schema + 메타데이터 (기존 + 확장)
  ├── geomsu_hwaginso.decisions.md  # 결정사항 누적 로그 (신규)
  └── geomsu_hwaginso.history.json  # 채우기 이력 최근 10건 (신규)
```

> **왜 단일 디렉토리?** 기존 구조(flat)를 유지하면 resolver.py·list_all_templates() 
> 변경 없이 suffix만 추가하면 됨. 서브디렉토리 방식보다 하위 호환이 쉬움.

---

### 1-2. `schema.json` 확장 필드

기존 auto_schema 필드는 **그대로 보존**. 아래를 추가:

```json
{
  "name": "geomsu_hwaginso",
  "title": "검수확인서.hwpx",
  "name_kr": "검수확인서",
  "tables": [...],

  "_meta": {
    "description": "사내 검수확인서 1매 표준",
    "notes": "검수자 서명은 이미지(sign.png)로 삽입. 1페이지 fit 필수",
    "page_standard": "1page",
    "structure_type": "B",
    "added_at": "2026-04-25",
    "last_used": "2026-05-01",
    "usage_count": 5
  }
}
```

> **왜 `_meta` 네임스페이스?** 기존 auto_schema 최상위 키와 충돌 방지.  
> `page_standard`: `"1page"` | `"free"`  
> `structure_type`: `"A"` (인접 셀) | `"B"` (같은 셀 patch) | `"unknown"`

---

### 1-3. `decisions.md` 포맷

```markdown
# 결정사항: 검수확인서

<!-- 최신 항목을 위에 추가 -->

## 2026-05-01
- 구조 B 재확인 (레이블+값 같은 셀)
- 서명란은 이미지 삽입 — sign.png (width=8000, height=3000)

## 2026-04-25
- 최초 등록. 1매 표준 확인.
- 구조 B 판정: "성 명       " 패턴 (레이블+공백 placeholder 같은 셀)
- autofit 적용 — 폰트 10pt→9pt 1단계 조정으로 1페이지 fit 성공
```

---

### 1-4. `history.json` 포맷

```json
[
  {
    "filled_at": "2026-05-01T14:23:00",
    "data": {
      "geomsu_ja": "홍길동",
      "geomsu_il": "2026. 5. 1.",
      "geomsu_hang": "소프트웨어 모듈 A"
    }
  },
  {
    "filled_at": "2026-04-28T10:11:00",
    "data": {
      "geomsu_ja": "김철수",
      "geomsu_il": "2026. 4. 28.",
      "geomsu_hang": "하드웨어 모듈 B"
    }
  }
]
```

> 최대 10건 유지 (오래된 항목 자동 삭제). 키 이름은 schema.json 필드의 `key` 값과 동일.

---

### 1-5. 신규 CLI 명령 설계

#### `template context <이름>` — 핵심 명령

LLM이 읽는 컨텍스트를 마크다운으로 출력. 세션 시작 시 `template show`를 대체.

```bash
pyhwpxlib template context 검수확인서
```

**출력 예시:**
```markdown
# 양식: 검수확인서
> 사내 검수확인서 1매 표준

- 파일: /Users/leeeunmi/.local/share/pyhwpxlib/templates/geomsu_hwaginso.hwpx
- 구조: B형 (patch 방식 — 레이블+값이 같은 셀)
- 페이지: 1매 고정 (autofit 적용)
- 마지막 사용: 2026-05-01 (총 5회)
- 비고: 검수자 서명은 이미지(sign.png)로 삽입. 1페이지 fit 필수

## 필드 목록
| 키 | 레이블 | 위치 |
|----|--------|------|
| geomsu_ja | 검수자 | 표0-행2-열1 |
| geomsu_il | 검수일자 | 표0-행3-열1 |
| geomsu_hang | 검수 항목 | 표1-행1-열0 |

## 결정사항
- [2026-05-01] 서명란은 이미지(sign.png) 삽입
- [2026-04-25] 구조 B 확인. autofit 1단계(폰트 10→9pt) 적용

## 최근 채우기 값 (재사용 가능)
{
  "geomsu_ja": "홍길동",
  "geomsu_il": "2026. 5. 1.",
  "geomsu_hang": "소프트웨어 모듈 A"
}
```

---

#### `template annotate <이름>` — 메타데이터·결정사항 갱신

```bash
# 메타데이터 갱신
pyhwpxlib template annotate 검수확인서 \
  --description "사내 검수확인서 1매 표준" \
  --page-standard 1page \
  --structure-type B \
  --notes "서명은 이미지 삽입. 1페이지 fit 필수"

# 결정사항 한 줄 추가 (날짜 자동)
pyhwpxlib template annotate 검수확인서 \
  --add-decision "구조 B 재확인 — 레이블+값 같은 셀"
```

내부 동작:
1. `schema.json`의 `_meta` 필드 갱신
2. `decisions.md` 최상단에 날짜 블록 추가

---

#### `template log-fill <이름> --data <json>` — 채우기 이력 기록

```bash
pyhwpxlib template log-fill 검수확인서 --data filled_data.json
# 또는 인라인
pyhwpxlib template log-fill 검수확인서 --data '{"geomsu_ja": "홍길동"}'
```

내부 동작:
1. `history.json` 맨 앞에 `{filled_at, data}` 추가
2. 10건 초과 시 오래된 것 제거
3. `schema.json._meta.last_used`, `usage_count` 갱신

---

#### `template list` 강화

기존 출력:
```
geomsu_hwaginso   user
```

강화 출력:
```
이름               한글명         마지막 사용    횟수  구조  페이지
geomsu_hwaginso   검수확인서     2026-05-01     5회   B형   1매
uigyeon_jechulso  의견제출서     2026-04-20     2회   A형   자유
```

플래그:
```bash
pyhwpxlib template list            # 표 형식 (기본)
pyhwpxlib template list --json     # JSON (SessionStart hook 등 파싱용)
pyhwpxlib template list --count    # 숫자만 (스크립트용)
```

---

## Stage 2 — SKILL.md Step F 추가

### 워크플로우 [3] 양식 채우기에 추가

기존 Step D (프리뷰 검증) 이후, Step E (1페이지 fit) 이후에 추가:

```
Step F: 컨텍스트 보존 (생략 금지)

─── 최초 등록 (해당 양식이 template list에 없을 때) ───
pyhwpxlib template add <source.hwpx>
# → 자동으로: HWPX 등록 + schema.json 생성

pyhwpxlib template annotate <이름> \
  --description "<한 줄 설명>" \
  --page-standard [1page|free] \
  --structure-type [A|B] \
  --notes "<특이사항>"

─── 매 세션 종료 시 (항상 실행) ───
pyhwpxlib template log-fill <이름> --data <채운_데이터.json>
pyhwpxlib template annotate <이름> --add-decision "<이번 세션 결정사항>"

─── Memory 등록 (최초 1회) ───
"<이름>(한글) 양식 등록됨.
 컨텍스트: pyhwpxlib template context <이름>
 다음 세션에서 이 명령으로 컨텍스트 복원."
```

### Step 0 (메타 인지) 보강 — 기존 양식 감지

워크플로우 [3] Step 0에 추가:

```
양식 작업 시작 전:
1. pyhwpxlib template list 로 등록된 양식 확인
2. 일치하는 양식이 있으면 → pyhwpxlib template context <이름> 로 컨텍스트 로드
   → Step 0 5질문 스킵 가능 (이미 decisions.md에 답변 저장됨)
3. 없으면 → 기존 Step 0 진행 후 Step F에서 신규 등록
```

---

## Stage 3 — Claude Desktop / Claude Code

### CLAUDE.md 추가 항목

```markdown
## hwpx 양식 워크스페이스

hwpx 양식 작업 요청 시:
1. `pyhwpxlib template list` 로 등록 양식 확인
2. 일치하는 양식 있음 → `pyhwpxlib template context <이름>` 로 컨텍스트 로드
   → 바로 채우기 진행 (구조 재판정 불필요)
3. 없음 → 양식 업로드 후 SKILL.md 워크플로우 [3] + Step F 신규 등록

등록 위치: ~/.local/share/pyhwpxlib/templates/
```

### SessionStart hook

파일: `~/.claude/hooks/session-start.sh`

```bash
#!/bin/bash
# hwpx 등록 양식 세션 시작 시 표시

if command -v pyhwpxlib &>/dev/null; then
  count=$(pyhwpxlib template list --count 2>/dev/null || echo "0")
  if [ "$count" -gt 0 ]; then
    printf "\n=== hwpx 등록 양식 (%s개) ===\n" "$count"
    pyhwpxlib template list
    printf "컨텍스트 로드: pyhwpxlib template context <이름>\n\n"
  fi
fi
```

**출력 예시 (세션 시작 시):**
```
=== hwpx 등록 양식 (3개) ===
이름               한글명         마지막 사용    횟수  구조  페이지
geomsu_hwaginso   검수확인서     2026-05-01     5회   B형   1매
uigyeon_jechu...  의견제출서     2026-04-20     2회   A형   자유
lotte_ai_jeans...  롯데 AI 제안서  2026-04-29   1회   -     자유
컨텍스트 로드: pyhwpxlib template context <이름>
```

---

## Stage 4 — Other LLMs (ChatGPT, Gemini, Cursor 등)

### 수동 주입 패턴 (가장 단순)

```bash
# 터미널에서 실행 후 출력을 시스템 프롬프트에 붙여넣기
pyhwpxlib template context 검수확인서
```

### Python API 자동화 패턴

```python
import subprocess

def get_hwpx_context(name: str) -> str:
    """양식 컨텍스트를 시스템 프롬프트에 주입."""
    result = subprocess.run(
        ["pyhwpxlib", "template", "context", name],
        capture_output=True, text=True
    )
    return result.stdout

# LLM API 호출 시
system_prompt = f"""
당신은 HWPX 양식 채우기 전문가입니다.

{get_hwpx_context("검수확인서")}
"""
```

### shell alias 패턴 (빠른 주입)

`~/.zshrc` 또는 `~/.bashrc`:

```bash
hwpx-ctx() {
  pyhwpxlib template context "$1" | pbcopy  # macOS: 클립보드로 복사
  echo "컨텍스트 복사됨 → 시스템 프롬프트에 붙여넣기"
}
# 사용: hwpx-ctx 검수확인서
```

---

## 구현 순서 요약

```
Stage 1a: schema.json _meta 확장 + template annotate 명령
Stage 1b: history.json + template log-fill 명령
Stage 1c: decisions.md + template annotate --add-decision
Stage 1d: template context 명령 (1a~1c 완료 후)
Stage 1e: template list 강화

Stage 2:  SKILL.md Step F + Step 0 보강

Stage 3a: CLAUDE.md 항목 추가
Stage 3b: SessionStart hook 스크립트

Stage 4:  chatgpt_hwpx_guide.md 업데이트 (Other LLMs 패턴 문서화)
```

> **Stage 1d (`template context`)가 전체 시스템의 핵심**.  
> 이것 하나로 claude.ai(Filesystem MCP 호출) · Claude Code(hook) · 
> Other LLMs(수동 붙여넣기) 모두 동일한 컨텍스트를 얻을 수 있음.

---

## 데이터 흐름 요약

```
[양식 작업]
  ↓ template add         → .hwpx + .schema.json 생성
  ↓ template annotate    → _meta + decisions.md 기록
  ↓ 채우기 작업
  ↓ template log-fill    → history.json 기록

[다음 세션]
  ↓ template context     → 마크다운 컨텍스트 출력
  ↓ LLM 읽기            → 구조·결정·이전값 즉시 파악
  ↓ 바로 채우기 진행     → Step 0 재판정 불필요
```
