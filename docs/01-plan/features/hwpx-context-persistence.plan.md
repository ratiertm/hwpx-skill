---
template: plan
version: 1.2
description: 양식 워크스페이스 통합 — Stage 1 (옵션 D 폴더 구조) + Stage 2 (SKILL.md) + Stage 3 (MCP/Hook)
---

# hwpx-context-persistence Planning Document

> **Summary**: 사용자 피드백 "채팅창 바뀌면 기억 못 해서 다시 양식 업로드하고 다시 설명하고..." 의 근본 해결. 양식별 폴더 워크스페이스 (옵션 D) + SKILL.md 자동 컨텍스트 로드 + MCP/SessionStart hook 통합으로 새 채팅에서도 등록 양식의 모든 정보 (구조·결정·이력·결과물) 100% 자동 복원.
>
> **Project**: pyhwpxlib
> **Version**: 0.16.1 → 0.17.0 (major — breaking change: 폴더 구조 마이그레이션)
> **Date**: 2026-05-01
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

**기존 문제**: pyhwpxlib v0.13.3+ 의 template 시스템은 양식 파일과 schema 만 저장. 사용자가 한 번 채팅에서 결정한 사항 (구조 B / 1매 표준 / 서명은 이미지) 과 채운 값들이 새 채팅에서 모두 사라짐. 매번 양식 재업로드 + 재설명 반복.

**해결**: 양식별 폴더 워크스페이스에 **모든 컨텍스트 (양식 + 메타 + 결정 + 이력 + 결과물) 영구 저장** + LLM 이 양식명 들으면 자동 로드.

### 1.2 Background

- 사용자 피드백 (2026-05-01): "사용자에게 너무 불편한 일 아니야?"
- 기존 설계 (5개 design doc, 1794줄) 이미 작성됨 — Stage 1~4 분리 형태
- 사용자 결정: Stage 1+2+3 통합 일괄 진행 (Stage 4 Other LLMs 는 v0.18.0 후보)
- 사용자 결정: 옵션 D (폴더 단위 워크스페이스) 채택 — 폴더 클릭하면 양식의 모든 것이 보임

### 1.3 Related

- 기존 design docs (검토 완료):
  - `docs/design/hwpx-context-persistence-design.md` (메인, 397줄)
  - `docs/design/stage2-skill-design.md` (261줄)
  - `docs/design/stage3-platform-design-enhanced.md` (383줄)
  - `docs/design/stage4-other-llms-design.md` (Stage 4 — 본 사이클 외)
  - `docs/design/stage4-sandbox-workflow.md` (Stage 4 — 본 사이클 외)
- v0.13.3 옵션 B template workflow (`pyhwpxlib template add/fill/show/list/diagnose`)
- v0.16.0 reference-fidelity-toolkit (page-guard 강제 게이트)

---

## 2. Goals

### 2.1 Primary Goals

**Stage 1 — 워크스페이스 폴더 구조 (옵션 D)**
1. 양식별 폴더로 마이그레이션 — `<이름>/` 안에 source.hwpx + schema + decisions + history + outputs
2. 신규 CLI 명령 — `template context/annotate/log-fill/migrate/open`
3. 자동 outputs/ 저장 (사용자 `--output` 미지정 시)
4. `template list` 강화 (한글명·마지막 사용·횟수·구조·페이지·outputs 개수)
5. 기존 v0.13.3 사용자 자동 마이그레이션 스크립트

**Stage 2 — SKILL.md 통합**
6. On Load 섹션에 등록 양식 자동 표시
7. Workflow [3] Step 0 보강 (양식 감지 → 자동 컨텍스트 로드)
8. Workflow [3] Step F 신설 (세션 종료 시 컨텍스트 보존)
9. SKILL.md → 사용자 동기화

**Stage 3 — MCP / Hook 통합**
10. MCP 서버에 신규 tools — `template_context`, `template_workspace_list`, `template_log_fill`
11. SessionStart hook 스크립트 (`~/.claude/hooks/session-start.sh`)
12. Claude Desktop / Code 양쪽에서 자동 컨텍스트 로드 동작 검증

### 2.2 Non-Goals

- **Stage 4 (Other LLMs)** — ChatGPT/Gemini/Cursor 텍스트 paste 패턴은 v0.18.0 별도 사이클
- **HTTP/SSE 서버 배포** — Stage 3 보강 설계의 BearerAuth + FastMCP 는 v0.18.0+ (play.mcp 배포 트랙)
- **양식 공유 기능** — 워크스페이스를 다른 사용자와 공유 (export/import) 는 v0.18.0+
- **자동 결정사항 추출 (LLM 자동 학습)** — 사용자가 명시적으로 `template annotate` 호출하는 패턴 유지

### 2.3 Success Criteria

- [ ] **새 채팅 시나리오**: 양식 등록 후 새 채팅에서 양식명 언급 → Claude 가 자동으로 컨텍스트 (구조·결정·이전 값) 복원
- [ ] 기존 v0.13.3 사용자 자동 마이그레이션 — `pyhwpxlib template migrate` 한 명령
- [ ] `template list` 강화 출력에 한글명·마지막 사용·횟수·구조·페이지·outputs 개수 표시
- [ ] `template fill` 무옵션 호출 시 `<이름>/outputs/YYYY-MM-DD_<auto>.hwpx` 자동 저장
- [ ] `template context <이름>` 마크다운 출력 — LLM 이 paste 가능
- [ ] `template open <이름>` — Finder/Explorer 에서 워크스페이스 폴더 열기
- [ ] MCP server `template_context` tool 동작 (Claude Desktop/Code)
- [ ] SessionStart hook — 세션 시작 시 등록 양식 목록 자동 표시
- [ ] SKILL.md 갱신 — On Load + Workflow [3] Step 0/F
- [ ] 기존 130 회귀 테스트 PASS 유지 + 신규 ≥ 15 케이스

---

## 3. Requirements

### 3.1 Functional Requirements

#### FR-1: 워크스페이스 폴더 구조 (Stage 1)

```
~/.local/share/pyhwpxlib/templates/   ← 사용자 워크스페이스 root (XDG)
└── <name>/                            ← 양식별 폴더
    ├── source.hwpx                    ← 원본 양식
    ├── schema.json                    ← auto_schema + _meta
    ├── decisions.md                   ← 결정사항 누적
    ├── history.json                   ← 채우기 이력 (최근 10건)
    └── outputs/                       ← 채운 결과물 자동 저장
        └── YYYY-MM-DD_<auto>.hwpx
```

`<name>` 은 slug (영문 키). 한글명은 `schema.json._meta.name_kr` 에 보관.

#### FR-2: 신규 CLI 명령 (Stage 1)

| 명령 | 동작 |
|------|------|
| `template context <name>` | LLM 주입용 마크다운 출력 (양식+필드+결정+최근값) |
| `template annotate <name>` | `--description --page-standard --structure-type --notes --add-decision` |
| `template log-fill <name> -d <data.json>` | history.json 갱신 + usage_count 증가 |
| `template open <name>` | Finder/Explorer 에서 워크스페이스 폴더 열기 |
| `template migrate` | v0.13.3 flat 구조 → v0.17.0 폴더 구조 자동 마이그레이션 (백업 포함) |
| `template list` 강화 | 한글명·마지막 사용·횟수·구조·페이지·outputs 개수 표 |

#### FR-3: `template fill` 자동 저장 (Stage 1)

```bash
# --output 없으면 자동 outputs/ 저장
pyhwpxlib template fill 검수확인서 -d data.json
# → ~/.local/share/.../검수확인서/outputs/2026-05-01_홍길동.hwpx 자동 저장
# + history.json 자동 기록 (output_path 포함)

# --output 있으면 사용자 지정 위치 + history.json 에 경로 기록
pyhwpxlib template fill 검수확인서 -d data.json -o ~/Desktop/result.hwpx
```

#### FR-4: SKILL.md 통합 (Stage 2)

**On Load 섹션 갱신**:
- 스킬 로드 시 `pyhwpxlib template list --json` 자동 호출
- 등록 양식 있으면 사용자에게 "기존 양식 작업 이어가기?" 옵션 표시

**Workflow [3] Step 0 보강 (양식 감지)**:
```
양식 작업 시작 전:
1. 사용자가 양식명 언급 → pyhwpxlib template list 로 등록 확인
2. 일치하면 → pyhwpxlib template context <이름> 자동 호출
3. 없으면 → 기존 Step 0 (메타 인지 5질문) 진행 후 Step F 에서 신규 등록
```

**Workflow [3] Step F 신설 (컨텍스트 보존)**:
```
세션 종료 직전:
1. (최초 등록 시) template add → annotate (description, page_standard, structure_type)
2. (매 세션) template log-fill <이름> -d <채운_데이터>
3. (이번 세션 결정사항 있으면) template annotate <이름> --add-decision "<결정>"
```

#### FR-5: MCP / Hook 통합 (Stage 3)

**MCP server 신규 tools** (`pyhwpxlib/mcp_server/server.py`):
- `template_context(name)` — 마크다운 컨텍스트 반환
- `template_workspace_list()` — 등록 양식 메타 JSON
- `template_log_fill(name, data, output_path?)` — 채우기 이력 기록

**SessionStart hook** (`~/.claude/hooks/session-start.sh`):
```bash
#!/bin/bash
if command -v pyhwpxlib &>/dev/null; then
  count=$(pyhwpxlib template list --count 2>/dev/null || echo 0)
  if [ "$count" -gt 0 ]; then
    echo "=== hwpx 등록 양식 ($count 개) ==="
    pyhwpxlib template list
    echo "컨텍스트 로드: pyhwpxlib template context <이름>"
  fi
fi
```

### 3.2 Non-Functional Requirements

- **Migration 자동화**: 기존 v0.13.3 사용자 데이터 0% 손실. `template migrate` 한 명령. 자동 백업.
- **Backward compat**: 마이그레이션 후 모든 기존 명령 (`template add/fill/show/list/diagnose`) 동작 유지
- **하위 호환 모드** (선택): `--legacy-flat` 플래그로 옛 구조 유지 가능 (deprecated 경로)
- **PII 안전**: `history.json` 의 채우기 값은 사용자 로컬 디스크에만 저장 (네트워크 전송 zero)
- **Cross-platform**: macOS / Linux / Windows 모두 동작 (XDG / LOCALAPPDATA)

---

## 4. Constraints

### 4.1 Technical Constraints

- **resolver.py 재작성**: 기존 `*.hwpx` flat glob → `*/source.hwpx` subdirectory glob
- **list_all_templates() 재작성**: 폴더 단위 스캔으로 변경
- **schema.json `_meta` 확장**: 기존 schema 와 호환되는 옵셔널 키만 추가
- **MCP tools 시그니처**: 기존 `hwpx_*` tools 와 충돌 없는 prefix (`template_*`)

### 4.2 Resource Constraints

- 1인 개발 — **6~7일** 예상 (Stage 1: 3일 + Stage 2: 1일 + Stage 3: 2일 + 테스트/문서: 1일)
- 신규 외부 의존성 0건
- v0.17.0 major 버전 (마이그레이션 breaking change)

### 4.3 Other Constraints

- skill bundle (hwpx-skill-0.17.0.zip) 동시 갱신
- README/README_KO Workspace 섹션 신설
- 마이그레이션 가이드 문서 (`docs/migrations/v0.13.3-to-v0.17.0.md`)

---

## 5. Risks

### 5.1 Identified Risks

| Risk | Probability | Impact | Mitigation |
|------|:-----------:|:------:|------------|
| 마이그레이션 실패 → 기존 사용자 데이터 손실 | M | **H** | (1) 자동 백업 (`templates_backup_v0.16.x.tar.gz`) (2) dry-run 모드 (`--dry-run` 미리보기) (3) 마이그레이션 회귀 테스트 5+ 케이스 |
| MCP tool 충돌 — Claude Desktop 이 기존 `hwpx_*` 와 혼동 | L | M | `template_*` prefix 명확화. 도구 description 에 "template (양식 워크스페이스)" 명시 |
| SessionStart hook 글로벌 적용 — 다른 프로젝트에도 영향 | M | L | hook 옵트인 패턴 (`pyhwpxlib install-hook` 명령으로 사용자가 명시 설치). 기본 비활성 |
| 폴더 구조 변경 — 사용자 코드의 하드코딩 경로 깨짐 | L | M | `--legacy-flat` 호환 모드 + 마이그레이션 가이드 문서 |
| outputs/ 누적 디스크 압박 (수년 후) | L | L | `template clean <name> --older-than 90d` 정리 명령 (v0.18.0 후보) |
| MCP server 가 새 tools 노출 후 외부 LLM 이 잘못 호출 | L | L | tool description 명확. unit test |

### 5.2 Assumptions

- 사용자는 양식별로 ~10건 이내 outputs 누적 (디스크 압박 미미)
- Claude Code/Desktop SKILL.md 호출 패턴이 안정적 (양식명 언급 → context 명령 호출)
- MCP server stdio 모드로 충분 (HTTP/SSE 는 v0.18.0)

---

## 6. Implementation Plan

### 6.1 Phases

| Phase | Description | Estimated Time |
|-------|-------------|----------------|
| **P1** | resolver.py / list_all_templates 재작성 (subdirectory) | 0.5일 |
| **P2** | template add 갱신 (폴더 생성), template fill 자동 outputs/ | 1일 |
| **P3** | 신규 명령 — `context/annotate/log-fill/open/migrate` | 1.5일 |
| **P4** | 마이그레이션 스크립트 (v0.13.3 flat → v0.17.0 folder) + 자동 백업 | 1일 |
| **P5** | SKILL.md On Load + Step 0 + Step F 갱신 + 사용자 동기화 | 0.5일 |
| **P6** | MCP server 신규 3 tools 추가 | 0.5일 |
| **P7** | SessionStart hook 스크립트 + `pyhwpxlib install-hook` 명령 | 0.5일 |
| **P8** | 회귀 테스트 (≥15 신규) + 마이그레이션 회귀 테스트 | 1일 |
| **P9** | README Workspace 섹션 + migration guide + skill bundle 갱신 | 0.5일 |
| **P10** | v0.17.0 릴리스 (commit/tag/push/PyPI) + work-log | 0.5일 |

### 6.2 Technologies/Tools

- 변경 위주 (resolver, add, fill, list 모두 갱신)
- 신규 모듈: `pyhwpxlib/templates/context.py`, `migration.py`, `workspace.py`
- MCP server 확장 (기존 FastMCP 패턴 재사용)
- pytest 회귀

### 6.3 Dependencies

- 외부 의존성 0건
- 내부: 기존 `pyhwpxlib.templates.{add,fill,resolver,slugify,auto_schema,diagnose}` 재구성

---

## 7. Implementation Order

### 7.1 Recommended Order

**Sprint 1 — 코어 (3일)**
1. Step 1: `resolver.py` subdirectory 지원 + `list_all_templates()` 재작성
2. Step 2: `template add` 폴더 구조 생성 (source.hwpx + schema + decisions.md + history.json + outputs/)
3. Step 3: `template fill` 자동 outputs/ 저장 + `--output` 호환
4. Step 4: 신규 `template context/annotate/log-fill/open` 명령
5. Step 5: 마이그레이션 스크립트 `template migrate` + 자동 백업 + `--dry-run`

**Sprint 2 — SKILL + MCP (2일)**
6. Step 6: SKILL.md On Load + Workflow [3] Step 0 보강 + Step F 신설
7. Step 7: `~/.claude/skills/hwpx/SKILL.md` 동기화
8. Step 8: MCP server `template_context/template_workspace_list/template_log_fill` 추가
9. Step 9: SessionStart hook 스크립트 + `pyhwpxlib install-hook` 명령

**Sprint 3 — QA + 릴리스 (1.5일)**
10. Step 10: 회귀 테스트 (≥15 신규) — workspace 폴더 / 마이그레이션 / 자동 outputs / context 출력
11. Step 11: README Workspace 섹션 + migration guide
12. Step 12: skill bundle 0.17.0.zip + version bump + Rolling Change Date
13. Step 13: 통합 시나리오 검증 — 새 채팅에서 양식명 언급 → 컨텍스트 자동 로드 동작 확인
14. Step 14: commit + tag v0.17.0 + push + PyPI 배포 + work-log

### 7.2 Critical Path

P1 (resolver) → P2 (add/fill) → P3 (신규 명령) → P4 (마이그레이션) → P5 (SKILL) → P6 (MCP) → P7 (Hook) → P8 (테스트) → P10 (릴리스)

P1 ~ P4 (Sprint 1) 가 가장 위험. 회귀 테스트로 보호.

---

## 8. Testing Plan

### 8.1 Test Strategy

- **단위**: resolver / list / context / annotate / log-fill 각 함수
- **통합**: workspace 폴더 생성 → add → fill → list → context → migrate
- **마이그레이션 회귀**: v0.13.3 flat fixture → migrate → 기존 명령 동작 검증
- **MCP**: stdio mode 에서 신규 tool 호출 검증
- **시나리오**: 새 채팅 시뮬레이션 — context 명령 출력으로 LLM 컨텍스트 복원 가능?
- **전체**: 기존 130 PASS + 신규 ≥15

### 8.2 Test Cases (예시)

| ID | 시나리오 | 기대 |
|----|---------|------|
| T-WS-01 | `template add my.hwpx --name my_form` | `<root>/my_form/source.hwpx` 생성, schema/decisions/history/outputs 모두 |
| T-WS-02 | `template fill` 무옵션 → 자동 outputs/ 저장 | `outputs/YYYY-MM-DD_*.hwpx` 생성 |
| T-WS-03 | `template fill -o /tmp/x.hwpx` | 사용자 지정 위치 + history.json 에 경로 기록 |
| T-WS-04 | `template context my_form` | 마크다운 출력에 양식·필드·결정·최근값 모두 |
| T-WS-05 | `template annotate --add-decision "..."` | decisions.md 최상단에 날짜 블록 추가 |
| T-WS-06 | `template list --json` | 폴더 단위 스캔, 한글명·횟수·outputs 개수 |
| T-WS-07 | `template open my_form` | `open` (macOS) / `xdg-open` (Linux) / `explorer` (Win) 호출 |
| T-MIG-01 | v0.13.3 flat fixture → migrate | `<name>/source.hwpx` 폴더 구조로 변환, 백업 tar.gz 생성 |
| T-MIG-02 | migrate `--dry-run` | 변경 미리보기, 실제 변환 없음 |
| T-MIG-03 | migrate 후 기존 `template fill` | 정상 동작 (호환성 검증) |
| T-MCP-01 | MCP `template_context` tool | 마크다운 반환 |
| T-MCP-02 | MCP `template_workspace_list` | JSON 반환 |
| T-HOOK-01 | SessionStart hook 실행 | 등록 양식 목록 출력 |
| T-SKILL-01 | SKILL.md On Load — list 자동 호출 | (수동 검증) |
| T-INT-01 | 새 채팅 통합 시나리오 | (수동 검증 — Claude Code 에서) |

---

## 9. Open Questions

- [ ] 마이그레이션 시 `--legacy-flat` 모드 유지할지? **결정 권장: NO** (단순화, 호환 모드 유지 비용 큼)
- [ ] outputs/ 정리 정책 — 자동 cleanup vs 수동? **결정 권장: 수동** (`template clean --older-than 90d` 별도 명령)
- [ ] history.json 채우기 값 PII (사용자 정보) — 암호화? **결정 권장: NO** (로컬 디스크만, 네트워크 전송 없음. 암호화는 v0.18.0+)
- [ ] SessionStart hook — 옵트인 vs 자동 설치? **결정 권장: 옵트인** (`pyhwpxlib install-hook` 명시 명령)
- [ ] MCP HTTP/SSE 모드 — Stage 3 보강 설계 일부 흡수? **결정 권장: 본 사이클 외** (v0.18.0 play.mcp 트랙)

---

## 10. References

- 사용자 결정 (2026-05-01):
  1. Stage 1+2+3 일괄 진행 (Stage 4 분리)
  2. 옵션 D — 폴더 단위 워크스페이스
- 기존 design docs (5개, 1794줄)
- 사용자 피드백: "채팅창 바뀌면 기억 못 해서 다시 양식 업로드..."
- v0.13.3 template workflow (옵션 B) — 기존 시스템
- v0.16.0 reference-fidelity-toolkit — 라이선스/페이지 게이트 (선례)
- pyhwpxlib/templates/resolver.py — 핵심 변경 위치
- pyhwpxlib/mcp_server/server.py — Stage 3 확장 위치

---

## 11. Approval

- [ ] Plan reviewed
- [ ] Stakeholders aligned (사용자 — 2026-05-01 Stage 1+2+3 통합 + 옵션 D 결정)
- [ ] Ready for Design Phase
