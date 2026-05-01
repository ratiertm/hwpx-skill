---
template: design
version: 1.2
description: 워크스페이스 폴더 구조 + CLI/MCP/Hook 통합 설계 + 마이그레이션 알고리즘
---

# hwpx-context-persistence Design Document

> **Summary**: v0.13.3 flat 구조를 양식별 폴더 (옵션 D) 로 마이그레이션 + 신규 CLI 5종 + SKILL.md 3곳 갱신 + MCP 3 tools + SessionStart hook. resolver.py 재작성 (subdirectory glob), 신규 모듈 3개 (`context.py`, `migration.py`, `workspace.py`). 자동 백업 + `--dry-run` 으로 마이그레이션 안전성 확보.
>
> **Project**: pyhwpxlib
> **Version**: 0.16.1 → 0.17.0 (major)
> **Date**: 2026-05-01
> **Status**: Draft
> **Planning Doc**: [hwpx-context-persistence.plan.md](../../01-plan/features/hwpx-context-persistence.plan.md)

---

## 1. Overview

### 1.1 Design Goals

- **Stage 1 코어**: workspace 폴더 + 5 신규 명령 + 자동 outputs + 마이그레이션
- **Stage 2 SKILL.md**: On Load + Step 0 + Step F 갱신
- **Stage 3 MCP/Hook**: 3 tools + SessionStart hook (옵트인)
- **마이그레이션 안전성**: 자동 백업 + dry-run + 회귀 테스트
- **Backward compat**: 기존 `template add/fill/show/list/diagnose` 시그니처 유지

### 1.2 모듈/명령 매핑

| 영역 | 신규 모듈 | CLI 명령 | MCP tool |
|------|----------|---------|----------|
| 워크스페이스 | `templates/workspace.py` | `template open` | `template_workspace_list` |
| 컨텍스트 | `templates/context.py` | `template context`, `template annotate` | `template_context` |
| 이력 | (history.json 직접) | `template log-fill` | `template_log_fill` |
| 마이그레이션 | `templates/migration.py` | `template migrate`, `install-hook` | — |
| 갱신 | `templates/resolver.py` `add.py` `fill.py` `__init__.py` | 기존 명령 자동 갱신 | — |
| Hook | `scripts/session_start_hook.sh` | `pyhwpxlib install-hook` | — |

---

## 2. Architecture

### 2.1 워크스페이스 폴더 구조 (Stage 1)

```
~/.local/share/pyhwpxlib/templates/                (XDG / Windows: %LOCALAPPDATA%)
├── 검수확인서/                                     ← <slug> 폴더
│   ├── source.hwpx                                ← 원본 양식
│   ├── schema.json                                ← auto_schema + _meta
│   ├── decisions.md                               ← 결정 누적
│   ├── history.json                               ← 채우기 이력 10건
│   └── outputs/
│       ├── 2026-05-01_홍길동.hwpx
│       └── 2026-04-28_김철수.hwpx
└── 의견제출서/
    └── ...
```

slug 규칙: `pyhwpxlib.templates.slugify` 그대로 (한글 → 영문). 한글명은 `schema.json._meta.name_kr`.

### 2.2 schema.json `_meta` 확장

```json
{
  "name": "geomsu_hwaginso",
  "tables": [...],
  "_meta": {
    "name_kr": "검수확인서",
    "description": "사내 검수확인서 1매 표준",
    "page_standard": "1page",      // "1page" | "free"
    "structure_type": "B",          // "A" | "B" | "unknown"
    "added_at": "2026-04-25",
    "last_used": "2026-05-01",
    "usage_count": 5,
    "notes": "검수자 서명은 이미지 삽입"
  }
}
```

### 2.3 decisions.md / history.json 포맷

**decisions.md** (최신 위):
```markdown
# 결정사항: 검수확인서

## 2026-05-01
- 구조 B 재확인
- 서명란 이미지 삽입

## 2026-04-25
- 최초 등록. 1매 표준.
```

**history.json** (최근 10건, FIFO):
```json
[
  {
    "filled_at": "2026-05-01T14:23:00",
    "data": {"검수자": "홍길동", "검수일": "2026-05-01"},
    "output_path": "~/.local/share/.../검수확인서/outputs/2026-05-01_홍길동.hwpx"
  }
]
```

---

## 3. Module Signatures

### 3.1 `templates/resolver.py` (재작성)

```python
def user_workspaces_dir() -> Path:
    """사용자 워크스페이스 root (XDG / LOCALAPPDATA)."""
    # 기존 user_templates_dir() 와 동일 경로


def workspace_path(name: str) -> Path:
    """양식 워크스페이스 폴더 경로."""
    return user_workspaces_dir() / name


def resolve_template_file(name: str, kind: str = "source") -> Path | None:
    """워크스페이스 안의 파일 해결.

    kind: "source" → source.hwpx
          "schema" → schema.json
          "decisions" → decisions.md
          "history" → history.json
    user 워크스페이스 우선, skill bundle 폴백.
    """


def list_all_templates() -> list[dict]:
    """모든 양식 메타 (폴더 단위 스캔).

    Returns:
        [{"name", "name_kr", "source", "_meta": {...},
          "outputs_count": N, "decisions_count": N}, ...]
    """
```

### 3.2 `templates/context.py` (신규)

```python
@dataclass
class TemplateContext:
    """LLM 주입용 컨텍스트 데이터."""
    name: str
    name_kr: str
    description: str
    structure_type: Literal["A", "B", "unknown"]
    page_standard: Literal["1page", "free"]
    last_used: Optional[str]
    usage_count: int
    notes: str
    fields: list[dict]                # schema.json fields
    decisions: list[tuple[str, str]]  # [(date, text), ...] 최신 순
    recent_data: Optional[dict]       # history.json[0].data

    def to_markdown(self) -> str:
        """LLM paste 용 마크다운 출력."""

    def to_dict(self) -> dict:
        """JSON 직렬화."""


def load_context(name: str) -> TemplateContext:
    """워크스페이스에서 컨텍스트 로드. FileNotFoundError 가능."""


def annotate(
    name: str, *,
    description: Optional[str] = None,
    page_standard: Optional[str] = None,
    structure_type: Optional[str] = None,
    notes: Optional[str] = None,
    add_decision: Optional[str] = None,
) -> None:
    """schema.json._meta 갱신 + decisions.md 추기."""


def log_fill(
    name: str, data: dict,
    output_path: Optional[Path] = None,
) -> None:
    """history.json 갱신 (FIFO 10건) + usage_count 증가."""


def open_workspace(name: str) -> int:
    """Finder/Explorer 에서 폴더 열기 (subprocess)."""
```

### 3.3 `templates/migration.py` (신규)

```python
@dataclass
class MigrationPlan:
    """마이그레이션 사전 계획."""
    flat_files: list[Path]            # v0.13.3 flat .hwpx 파일들
    target_workspaces: list[Path]     # v0.17.0 폴더 경로
    backup_path: Path                 # tar.gz 백업 위치
    conflicts: list[str]              # 이미 폴더 존재 등 충돌

    def report(self) -> str:
        """dry-run 출력용."""


def plan_migration(root: Optional[Path] = None) -> MigrationPlan:
    """v0.13.3 flat 구조 감지 → 마이그레이션 계획 생성."""


def execute_migration(
    plan: MigrationPlan, *,
    backup: bool = True,
) -> dict:
    """실제 마이그레이션 실행. backup=True 면 tar.gz 자동 생성.

    Returns: {"migrated": N, "skipped": M, "backup": path}
    """
```

### 3.4 `templates/workspace.py` (신규)

```python
def create_workspace(
    name: str, source_hwpx: Path, *,
    name_kr: Optional[str] = None,
    overwrite: bool = False,
) -> Path:
    """양식 워크스페이스 폴더 + 초기 파일들 생성.

    1. <root>/<name>/ 디렉토리 생성
    2. source.hwpx 복사
    3. schema.json (auto_schema 결과)
    4. decisions.md (헤더만)
    5. history.json ([])
    6. outputs/ 빈 디렉토리
    """


def auto_output_path(name: str, data: dict) -> Path:
    """자동 outputs/ 파일명 생성.

    포맷: outputs/YYYY-MM-DD_<주요필드값>.hwpx
    주요 필드: data 의 첫 한글 값 (예: "홍길동")
    중복 시 _2, _3 suffix
    """


def install_session_hook(force: bool = False) -> Path:
    """~/.claude/hooks/session-start.sh 설치."""


def uninstall_session_hook() -> None:
    """hook 제거."""
```

---

## 4. CLI Spec (Stage 1)

### 4.1 신규 명령 5종

```bash
# 컨텍스트 로드
pyhwpxlib template context <name> [--json]

# 메타·결정 갱신
pyhwpxlib template annotate <name> \
  [--description TEXT] \
  [--page-standard {1page|free}] \
  [--structure-type {A|B|unknown}] \
  [--notes TEXT] \
  [--add-decision TEXT]

# 채우기 이력 기록
pyhwpxlib template log-fill <name> --data <json|file> [--output PATH]

# 워크스페이스 폴더 열기
pyhwpxlib template open <name>

# v0.13.3 → v0.17.0 마이그레이션
pyhwpxlib template migrate [--dry-run] [--no-backup]

# SessionStart hook 설치/제거
pyhwpxlib install-hook [--force]
pyhwpxlib uninstall-hook
```

### 4.2 기존 명령 갱신

```bash
# template add — 폴더 구조 생성
pyhwpxlib template add <hwpx> --name <name> [--name-kr <kr>]

# template fill — 자동 outputs/ 저장 (--output 미지정 시)
pyhwpxlib template fill <name> -d <data>           # 자동 저장
pyhwpxlib template fill <name> -d <data> -o <path> # 사용자 지정 + history 기록

# template list — 강화 출력
pyhwpxlib template list                # 표 (한글명·횟수·outputs 개수)
pyhwpxlib template list --json
pyhwpxlib template list --count        # 숫자만 (hook 용)
```

---

## 5. SKILL.md Changes (Stage 2)

### 5.1 On Load 섹션 갱신

기존:
```markdown
사용자 메시지에 구체적 작업이 없으면 AskUserQuestion:
  1. 새 문서 만들기
  2. 기존 문서 편집
  ...
```

신규 (앞에 등록 양식 자동 표시 추가):
```markdown
## On Load

1. 등록된 양식 자동 감지:
   pyhwpxlib template list --json
   → 결과 있으면 사용자에게 "기존 양식 작업 이어가기?" 옵션 표시
   → "예" 선택 시 → template context <이름> 자동 로드

2. 신규 작업이면 기존 5 옵션 표시
```

### 5.2 Workflow [3] Step 0 보강

```markdown
**Step 0: 메타 인지 (양식 감지 우선)**

A. pyhwpxlib template list 로 등록된 양식 확인
   → 사용자 양식과 일치하면:
      pyhwpxlib template context <이름>
      → 컨텍스트 로드 (5질문 스킵 가능)
   → 없으면 → B

B. 기존 메타 인지 5질문 진행
```

### 5.3 Workflow [3] Step F 신설

```markdown
**Step F: 컨텍스트 보존 (생략 금지)**

최초 등록 (template list 에 없을 때):
  pyhwpxlib template add <source.hwpx> --name <slug> --name-kr <한글명>
  pyhwpxlib template annotate <name> \
    --description "..." \
    --page-standard 1page|free \
    --structure-type A|B \
    --notes "..."

매 세션 종료 (항상):
  pyhwpxlib template log-fill <name> -d <채운_데이터>
  (이번 결정사항 있으면) pyhwpxlib template annotate <name> --add-decision "..."
```

---

## 6. MCP Tools (Stage 3)

### 6.1 신규 3 tools

```python
# pyhwpxlib/mcp_server/server.py 추가

@mcp.tool()
def template_context(name: str) -> dict:
    """양식 워크스페이스 컨텍스트 로드 (LLM 자동 복원용).

    Returns: {"markdown": "...", "fields": [...], "recent_data": {...}}
    """
    from pyhwpxlib.templates.context import load_context
    ctx = load_context(name)
    return {"markdown": ctx.to_markdown(), **ctx.to_dict()}


@mcp.tool()
def template_workspace_list() -> list[dict]:
    """등록된 모든 양식 목록.

    Returns: [{"name", "name_kr", "last_used", "usage_count",
               "structure_type", "page_standard", "outputs_count"}, ...]
    """


@mcp.tool()
def template_log_fill(
    name: str, data: dict,
    output_path: Optional[str] = None,
) -> dict:
    """채우기 이력 기록 (history.json + usage_count).

    Returns: {"ok": True, "history_count": N}
    """
```

### 6.2 기존 tools 와 충돌 회피

- prefix `template_*` 일관 (기존 `hwpx_*` 와 분리)
- description 에 "양식 워크스페이스 (workspace)" 명시
- argument 명시 schema (FastMCP 자동 검증)

---

## 7. SessionStart Hook (Stage 3)

### 7.1 스크립트 (`scripts/session_start_hook.sh`)

```bash
#!/usr/bin/env bash
# hwpx 등록 양식 세션 시작 시 표시 (옵트인)

set -e

if ! command -v pyhwpxlib &>/dev/null; then
  exit 0
fi

count=$(pyhwpxlib template list --count 2>/dev/null || echo 0)
if [ "$count" -gt 0 ] 2>/dev/null; then
  echo ""
  echo "=== hwpx 등록 양식 ($count 개) ==="
  pyhwpxlib template list 2>/dev/null
  echo ""
  echo "컨텍스트 로드: pyhwpxlib template context <이름>"
  echo "워크스페이스 열기: pyhwpxlib template open <이름>"
  echo ""
fi
```

### 7.2 설치 명령

```bash
pyhwpxlib install-hook
# → ~/.claude/hooks/session-start.sh 복사 (없으면 생성)
# → 기존 hook 있으면 append 모드 (--force 로 덮어쓰기)
# → chmod +x

pyhwpxlib uninstall-hook
# → hook 제거 또는 hwpx 관련 라인만 제거
```

---

## 8. Migration Algorithm

### 8.1 v0.13.3 → v0.17.0 변환 로직

```python
def execute_migration(plan: MigrationPlan, backup: bool = True) -> dict:
    # 1. 자동 백업
    if backup:
        with tarfile.open(plan.backup_path, "w:gz") as tar:
            tar.add(user_workspaces_dir(), arcname="templates_v0.13.3")

    migrated = 0
    skipped = 0

    # 2. 각 .hwpx 파일을 폴더로
    for hwpx_path in plan.flat_files:
        name = hwpx_path.stem
        target_dir = user_workspaces_dir() / name
        if target_dir.exists() and not overwrite:
            skipped += 1
            continue

        target_dir.mkdir(parents=True)

        # source.hwpx
        shutil.copy2(hwpx_path, target_dir / "source.hwpx")

        # schema.json (기존 <name>.schema.json → schema.json)
        old_schema = hwpx_path.parent / f"{name}.schema.json"
        if old_schema.exists():
            shutil.copy2(old_schema, target_dir / "schema.json")

        # 신규 파일 초기화
        (target_dir / "decisions.md").write_text(f"# 결정사항: {name}\n")
        (target_dir / "history.json").write_text("[]")
        (target_dir / "outputs").mkdir()

        # 3. 기존 flat 파일 삭제 (백업 후라 안전)
        hwpx_path.unlink()
        if old_schema.exists():
            old_schema.unlink()

        migrated += 1

    return {"migrated": migrated, "skipped": skipped,
            "backup": str(plan.backup_path) if backup else None}
```

### 8.2 안전장치

- **백업 우선**: 모든 변환 전 tar.gz 자동 생성 (`templates_backup_v0.16.x_YYYYMMDD.tar.gz`)
- **dry-run**: `--dry-run` 으로 변환 미리보기 (실제 변환 zero)
- **conflict 처리**: 이미 폴더 존재 시 skip + 보고
- **롤백**: 백업 tar.gz 으로 수동 복원 가능 (가이드 문서)

---

## 9. Test Cases

### 9.1 핵심 15+ 케이스

| ID | 시나리오 | 기대 |
|----|---------|------|
| T-WS-01 | `template add my.hwpx --name my_form` | 폴더 + source/schema/decisions/history/outputs 생성 |
| T-WS-02 | `template fill` 무옵션 → 자동 outputs/ | `outputs/YYYY-MM-DD_*.hwpx` |
| T-WS-03 | `template fill -o /tmp/x.hwpx` | 사용자 위치 + history.json output_path 기록 |
| T-WS-04 | `template context my_form` | 마크다운에 양식·필드·결정·최근값 |
| T-WS-05 | `template annotate --add-decision "..."` | decisions.md 최상단 날짜 블록 |
| T-WS-06 | `template list --json` | 폴더 단위 스캔, 한글명·횟수·outputs |
| T-WS-07 | `template open my_form` | 플랫폼별 file manager 호출 (CalledProcessError 없음) |
| T-WS-08 | `template log-fill --data` | history.json 10건 FIFO |
| T-MIG-01 | flat fixture → migrate | 폴더 구조 변환, 백업 tar.gz |
| T-MIG-02 | `migrate --dry-run` | 미리보기, 실제 변환 없음 |
| T-MIG-03 | migrate 후 기존 `template fill` | 정상 동작 (호환성) |
| T-MIG-04 | conflict (이미 폴더 존재) | skip + 보고 |
| T-MIG-05 | 백업 tar.gz 검증 | 압축 해제 가능, 원본 복원 가능 |
| T-MCP-01 | MCP `template_context` tool | markdown 반환 |
| T-MCP-02 | MCP `template_workspace_list` | JSON 반환 |
| T-MCP-03 | MCP `template_log_fill` | history.json 갱신 |
| T-HOOK-01 | hook 설치 + 실행 | 등록 양식 목록 출력 |
| T-HOOK-02 | hook 제거 | hwpx 라인만 제거 |

### 9.2 회귀

기존 130 PASS 유지. 마이그레이션 회귀 5 케이스 (T-MIG-01~05) 가 핵심.

---

## 10. File Plan

### 10.1 신규 파일

```
pyhwpxlib/templates/context.py        ~250 LOC
pyhwpxlib/templates/migration.py      ~200 LOC
pyhwpxlib/templates/workspace.py      ~180 LOC
scripts/session_start_hook.sh          ~25 LOC
tests/test_workspace.py               ~250 LOC (T-WS-01~08)
tests/test_migration.py               ~200 LOC (T-MIG-01~05)
tests/test_template_context.py        ~150 LOC (context 단위)
tests/test_mcp_template_tools.py      ~150 LOC (T-MCP-01~03)
docs/migrations/v0.13.3-to-v0.17.0.md ~100 LOC
```

### 10.2 수정 파일

```
pyhwpxlib/templates/resolver.py       전면 재작성 (subdirectory)
pyhwpxlib/templates/__init__.py       신규 모듈 re-export
pyhwpxlib/templates/add.py            폴더 구조 생성
pyhwpxlib/templates/fill.py           자동 outputs/ + history 기록
pyhwpxlib/cli.py                      신규 5 명령 + 갱신 1 명령
pyhwpxlib/mcp_server/server.py        신규 3 tools
pyhwpxlib/__init__.py                 0.16.1 → 0.17.0
pyproject.toml                        version bump
skill/SKILL.md                        On Load + Step 0 + Step F
README.md / README_KO.md              Workspace 섹션 추가
```

---

## 11. Implementation Order

> Plan §7.1 그대로. 14 Step 순차 진행. Critical Path:
> P1 resolver → P2 add/fill → P3 신규 명령 → P4 마이그레이션 → P5 SKILL → P6 MCP → P7 Hook → P8 테스트 → P10 릴리스.

---

## 12. Open Questions

- [ ] outputs/ 자동 파일명 — 한글 사용자값 추출 가능? Fallback 은 timestamp only? **결정 권장**: data 의 첫 한글 string field 추출, 없으면 timestamp
- [ ] migration 후 사용자가 수동으로 결정사항 추가하려면? **결정 권장**: `template annotate --add-decision` 명시 사용
- [ ] hook 이 다른 프로젝트 (hwpx 외) 세션에서도 출력? **결정 권장**: count > 0 일 때만 출력 (비활성 환경 noise zero)

---

## 13. References

- Plan: [hwpx-context-persistence.plan.md](../../01-plan/features/hwpx-context-persistence.plan.md)
- 기존 design: `docs/design/{hwpx-context-persistence-design,stage2-skill-design,stage3-platform-design-enhanced}.md`
- v0.13.3 옵션 B: `pyhwpxlib/templates/{add,fill,resolver}.py`
- 사용자 결정 (2026-05-01): Stage 1+2+3 통합 + 옵션 D + 옵트인 hook

---

## 14. Approval

- [ ] Design reviewed
- [ ] Architecture approved (모듈 시그니처 + 마이그레이션 알고리즘 확정)
- [ ] Ready for Do Phase
