# pyhwpxlib 하네스 엔지니어링 적용 가이드
> "Thin Harness, Fat Skills" 원칙을 pyhwpxlib 생태계에 적용한 설계 기준

---

## 현재 구조 진단

```
┌─────────────────────────────────────┐
│  SKILL.md (Fat Skills)               │
│  워크플로우 [1][2][3][4][5] 전부 있음  │  ← 백과사전 문제
│  On Load에 Python 코드 inline         │  ← 하네스 로직 혼재
└─────────────────────────────────────┘
           ↑
┌─────────────────────────────────────┐
│  MCP server / Claude Code           │  ← Thin Harness (잘 됨)
│  template_workspace / context / save │
└─────────────────────────────────────┘
           ↑
┌─────────────────────────────────────┐
│  pyhwpxlib CLI + Python API         │  ← Deterministic Layer (잘 됨)
│  fill_template / page-guard / autofit│
└─────────────────────────────────────┘
```

하네스와 결정론 레이어는 잘 설계되어 있음.
**스킬 파일이 Fat해지지 못한 것이 핵심 문제.**

---

## 원칙별 적용

---

### ① 스킬 파일 — SKILL.md를 함수로 쪼갠다

#### 현재 문제
```
SKILL.md 하나에 5개 워크플로우 전부
→ 모든 세션에서 전체 파일을 LLM이 읽음
→ "양식 채우기"를 할 때도 "새 문서 만들기" 절차가 컨텍스트를 차지
```

#### 목표 구조
```
SKILL.md                     ← 200줄 이하 포인터 (리졸버)
  ├── 절대 규칙 (10줄)
  ├── 워크플로우 목록 + 파일 포인터
  └── Quick Reference 테이블

skills/hwpx-new-doc.md       ← 워크플로우 [1] 전용
skills/hwpx-edit.md          ← 워크플로우 [2] 전용
skills/hwpx-form.md          ← 워크플로우 [3] 전용 ★ 가장 중요
skills/hwpx-convert.md       ← 워크플로우 [4] 전용
skills/hwpx-analyze.md       ← 워크플로우 [5] 전용
```

#### 스킬이 함수처럼 동작하는 예시
```
hwpx-form.md(FORM_NAME, STRUCTURE_TYPE, PAGE_STANDARD, FILL_DATA)

→ FORM_NAME=검수확인서, STRUCTURE_TYPE=B, PAGE_STANDARD=1page
  → B형 patch 방식으로 1매 고정 채우기 전문가

→ FORM_NAME=의견제출서, STRUCTURE_TYPE=A, PAGE_STANDARD=free
  → fill_by_labels 방식으로 자유 양식 채우기 전문가
```
같은 스킬, 다른 파라미터 = 다른 전문가. 파라미터는 `template context`가 공급.

---

### ② 하네스 — On Load에서 코드를 제거한다

#### 현재 문제 (On Load)
```python
# ❌ 이건 하네스가 할 일 — 스킬에 있으면 안 됨
from pyhwpxlib.templates import list_templates
items = list_templates()
```

#### 올바른 기술 방식
```markdown
## On Load

**Step 1**: MCP `template_workspace()` 결과를 읽는다.
- 등록 양식이 있으면 → 사용자 언급과 매칭
- 매칭되면 → `template_context(name)` 결과를 흡수하고 바로 워크플로우 [3]으로

**Step 2**: 등록 양식 없거나 새 작업이면 → AskUserQuestion
```

Python 코드는 없음. "MCP가 이미 실행해서 결과를 줬을 것이다 — 그걸 어떻게 해석하라"만 기술.

#### MCP 도구별 역할 (하네스의 책임)

| MCP Tool | 하는 일 | 스킬에서의 역할 |
|----------|---------|--------------|
| `template_workspace()` | 등록 양식 목록 반환 | On Load 트리거 |
| `template_context(name)` | 결정사항·이전값 마크다운 반환 | 컨텍스트 주입 |
| `template_save_session(name, data, decision)` | log-fill + annotate 한 번에 | 세션 종료 트리거 |

하네스(MCP)는 실행하고, 스킬은 결과를 해석하는 방법만 기술한다.

---

### ③ 리졸버 — description과 Versions 테이블을 정비한다

#### description 정비 원칙
```
현재: 키워드 나열 (길고 탐지 기준 불명확)
목표: "이 작업이 들어오면 이 스킬" 기준 명확화
```

description은 **라우팅 테이블**이다. 워크플로우별 스킬로 분리 후에는
각 스킬의 description이 더 좁고 정확해진다.

```yaml
# hwpx-form.md description 예시
description: "기존 HWPX 양식 파일에 데이터를 채울 때. 
  '양식 채우기', '빈칸 채워줘', 등록된 양식 이름 언급 시 트리거.
  새 문서 생성(hwpx-new-doc)이나 문서 편집(hwpx-edit)과 구별."
```

#### Versions 테이블 즉시 수정 필요

현재 SKILL.md Versions 테이블은 **0.16.0** 까지만 있음.
On Load 본문에는 **0.17.0+** 기능(`list_templates`, `load_context`)이 이미 쓰임.
→ 리졸버(description + 버전 정보)와 본문이 불일치.

```markdown
## Versions (추가 필요)
| 0.17.0 | 컨텍스트 지속성 — template context/annotate/log-fill/workspace |
```

---

### ④ 잠재 vs 결정론 — 경계를 명확히 한다

#### pyhwpxlib에서의 분리

| 작업 | 담당 | 이유 |
|------|------|------|
| 양식 구조 판정 (A형/B형) | LLM (잠재) | 레이블 패턴 해석 = 판단 |
| 1매 여부 판단 | LLM (잠재) | 사용자 의도 파악 = 판단 |
| fill_template 실행 | 코드 (결정론) | 같은 입력 → 같은 출력 |
| page-guard 검사 | 코드 (결정론) | 쪽수 비교 = 알고리즘 |
| autofit 실행 | 코드 (결정론) | 폰트/줄간격 조정 = 알고리즘 |
| 결정사항 해석 | LLM (잠재) | decisions.md 읽고 적용 = 판단 |

#### 현재 경계가 흐릿한 곳 — Step E

```markdown
# ❌ 현재 (LLM에게 판단을 맡김)
Step E: 넘치면: ① 폰트 한 단계 ↓ ② 줄간격 10%씩 ↓ ③ 셀 높이 비례 ↓

# ✅ 올바른 기술 (결정론으로 내림)
Step E: 1페이지 fit 검증
- page_count > 1 이면 → GongmunBuilder(autofit=True) 실행 (코드가 담당)
- autofit 후에도 실패 → 사용자에게 보고, 수동 조정 요청
```

LLM이 "폰트를 몇 pt 줄일지" 판단하는 게 아니라
코드(autofit)가 알고리즘으로 처리하고, LLM은 결과만 검증한다.

---

### ⑤ 다이어리제이션 — 세션 종료 루프를 완성한다

#### template context = pyhwpxlib의 다이어리제이션

```
결정사항 누적 (decisions.md)    ←─────────────┐
이전 채우기 값 (history.json)   ←─────────────┤
                                              │
template context 출력           ← 다이어리제이션 결과물
(한 페이지로 압축)                             │
                                              │
다음 세션에서 즉시 흡수          ─────────────→┘
```

#### 현재 누락된 것 — Step F가 SKILL.md에 없다

설계 문서(stage1/2)에는 Step F(컨텍스트 보존)가 명시되어 있음.
실제 SKILL.md 워크플로우 [3]에는 page-guard(Step F) 이후가 없음.

```markdown
# 워크플로우 [3]에 추가해야 할 Step G

Step G: **컨텍스트 보존 (생략 금지)**
> 다이어리제이션 루프의 완성 단계.

최초 등록 시:
  pyhwpxlib template add <source.hwpx>
  pyhwpxlib template annotate <이름> --description "..." --structure-type A/B --page-standard 1page/free

매 세션 종료 시 (항상):
  template_save_session(name, filled_data, decision)
  # 또는 CLI:
  # pyhwpxlib template log-fill <이름> --data '<json>'
  # pyhwpxlib template annotate <이름> --add-decision "<이번 발견>"
```

#### 학습 루프 완성 형태

```
세션 시작
  ↓ template_workspace() → 등록 양식 확인
  ↓ template_context(name) → 결정사항·이전값 흡수
  ↓ 바로 채우기 (Step 0 재판정 불필요)

세션 종료
  ↓ template_save_session() → 이력 + 결정사항 기록
  ↓ decisions.md 업데이트

다음 세션
  ↓ 이번 세션의 판단이 자동 복원됨
  ↓ 스킬이 스스로를 더 풍부하게 만들어간다
```

---

## 즉시 적용 액션 목록

### 🔴 즉시 (SKILL.md 수정)

1. **Versions 테이블에 0.17.0 추가**
   ```
   | 0.17.0 | 컨텍스트 지속성 — template context/annotate/log-fill CLI + load_context() Python API |
   ```

2. **워크플로우 [3] Step G 추가** (컨텍스트 보존 / 다이어리제이션 루프)

3. **On Load Python 코드 제거** → MCP 결과 해석 방법만 기술로 교체

### 🟡 다음 단계 (구조 개선)

4. **워크플로우별 스킬 분리** — hwpx-form.md 최우선 (가장 반복 사용)

5. **Step E autofit 결정론 명시** — LLM 판단 → 코드 위임으로 재기술

6. **각 스킬 description 정비** — 워크플로우별로 라우팅 기준 명확화

### 🟢 나중 (생태계 완성)

7. **`/improve` 패턴 도입** — 세션 후 decisions.md 자동 분석 + 스킬 개선 제안

8. **Cursor/Windsurf export** — `template export-cursor` 명령으로 규칙 파일 자동 생성

---

## 최종 목표 상태

```
사용자: "검수확인서 홍길동으로 채워줘"
  ↓
하네스(MCP): template_workspace() → template_context("검수확인서")
  ↓
스킬(hwpx-form.md): B형·1매·서명이미지 판정 이미 알고 있음 → 바로 채우기
  ↓
결정론(pyhwpxlib): fill_template() → page-guard() → pass
  ↓
하네스(MCP): template_save_session() → decisions.md + history.json 업데이트
  ↓
"완료. 다음 세션에도 이 판단이 자동 복원됩니다."
```

모델이 업그레이드될 때마다 hwpx-form.md의 판단력이 자동으로 강해진다.
decisions.md는 절대 퇴화하지 않고, 잊지 않고, 매 세션 더 풍부해진다.
