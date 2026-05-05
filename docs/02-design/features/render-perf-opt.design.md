---
template: design
version: 1.3
feature: render-perf-opt
date: 2026-05-05
author: ratiertm
project: hwpx-skill / pyhwpxlib
version_at_design: 0.17.3
target_version: 0.18.0
status: Draft
---

# render-perf-opt Design Document

> **Summary**: 렌더링 정확도 무손실로 fill-and-verify 컴퓨트·토큰을 동시에 줄이는 캐싱 + XML-level 검증 + 워크플로 게이팅의 세부 설계.
>
> **Project**: hwpx-skill / pyhwpxlib
> **Version**: 0.17.3 → 0.18.0
> **Author**: ratiertm
> **Date**: 2026-05-05
> **Status**: Draft
> **Planning Doc**: [render-perf-opt.plan.md](../../01-plan/features/render-perf-opt.plan.md)

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | 양식 채우기 cycle이 비싸서 사용자가 재시도 망설이는 단계 — 단가 절감이 사용 빈도를 늘림 |
| **WHO** | pyhwpxlib MCP/CLI 사용자, 특히 양식 다중 채우기 시나리오 |
| **RISK** | 캐시 무효화 실수로 PNG sha256 회귀 — 모든 양식 사용자에 영향 |
| **SUCCESS** | (1) sha256 동일 (2) 5회 mean ≤200ms (3) tools-list ≤12K (4) 175 PASS |
| **SCOPE** | Tier 1 (T1.1~T1.5) + T2.2 + T2.3 + INF + REL 0.18.0. T3 전부 보류 |

---

## 1. Overview

### 1.1 Design Goals

1. wasmtime Engine instantiate 의 851ms 비용을 첫 호출 1회로 amortize
2. 동일 `(font, size, text)` 텍스트 측정의 결과 캐시
3. fontconfig 폰트 등록을 프로세스당 1회로 게이트
4. 외부 엔진 주입(DI)으로 N장 렌더링 시 init 1회만
5. MCP 도구 docstring 슬림화로 tools-list 응답 토큰 ≥50% 감축
6. 중간 검증을 PNG 대신 XML-level check-fill 로 대체 (~10ms)
7. 워크플로 [3] Step D를 "중간 check-fill / 최종 PNG" 게이트로 갱신

### 1.2 Design Principles

- **Pure memoization only** — 입력이 같으면 출력이 byte-identical. eviction 정책도 결정성 무손상.
- **Local state, local change** — 캐시 상태는 사용처 옆에 둔다 (rhwp_bridge / api 인라인). 신규 모듈은 신규 기능(check_fill)에만.
- **Backward compatible** — 0.17.x 코드 무수정 동작. 신규 인자는 keyword-only optional.
- **Fail fast on cache invariants** — 외부에서 fork() / multiprocess 진입 시 lazy re-create. 더티 캐시 사용 금지.
- **Observable** — 캐시 hit/miss는 `__cache_info__` 등 stdlib 패턴 노출 (디버깅 용이).

---

## 2. Architecture Options

### 2.0 Architecture Comparison

3개 옵션 평가 후 사용자 선택 → **Option C (Pragmatic)** 채택.

| Criteria | A: Minimal | B: Clean | C: Pragmatic |
|----------|:-:|:-:|:-:|
| 신규 파일 | 3 | 6 | 4 |
| 수정 파일 | 7 | 8 | 7 |
| 복잡도 | Low | High | Medium |
| 유지보수 | Med | High | High |
| 회귀 위험 | Low | Medium | Low |
| 추천 | hotfix | 장기 | **이 사이클** |

**Selected**: **Option C** — Plan §7.3 폴더 구조와 일치. 캐시는 사용처와 동거(읽기 단순), check-fill은 재사용 가능한 단일 모듈로 분리.

### 2.1 Component Diagram

```
┌────────────── render-perf-opt ───────────────┐
│                                              │
│  ┌─ pyhwpxlib/rhwp_bridge.py ───────────┐    │
│  │  module globals:                     │    │
│  │    _ENGINE: wasmtime.Engine          │    │
│  │    _MODULE: wasmtime.Module          │    │
│  │  functools.lru_cache:                │    │
│  │    _measure_text_cached(font,size,t) │    │
│  │  RhwpEngine.__init__():              │    │
│  │    Store/Linker/Instance per call    │    │
│  └──────────────────────────────────────┘    │
│              ↑ uses                          │
│  ┌─ pyhwpxlib/api.py ────────────────────┐   │
│  │  module globals:                      │   │
│  │    _FONTS_REGISTERED: bool            │   │
│  │  render_to_png(*, engine=None):       │   │
│  │    if engine is None: engine = Rhwp() │   │
│  │    _register_bundled_fonts() once     │   │
│  └───────────────────────────────────────┘   │
│              ↑ wraps                         │
│  ┌─ pyhwpxlib/templates/check_fill.py ───┐   │
│  │  check_fill(name, data) → CheckResult │   │
│  │    schema 있으면 schema vs filled     │   │
│  │    없으면 hp:t pattern fallback       │   │
│  │    {filled:[], empty:[], placeholders}│   │
│  └───────────────────────────────────────┘   │
│              ↑ thin wrappers                 │
│  ┌─ cli.py ──┐  ┌─ mcp_server/server.py ──┐  │
│  │check-fill │  │ hwpx_check_fill          │  │
│  │ handler   │  │ (compressed docstring)   │  │
│  └───────────┘  └──────────────────────────┘  │
└──────────────────────────────────────────────┘
```

### 2.2 Data Flow

#### 2.2.1 Render path (with caching)
```
render_to_png(path)
  → _register_bundled_fonts() [first call: fontconfig add; rest: noop]
  → engine = engine or RhwpEngine()
       └─ wasmtime.Engine: module-singleton hit (1ms instead of 851ms)
       └─ wasmtime.Module: cached
       └─ Store/Linker/Instance: fresh per call
  → engine.load(path)
  → doc.render_page_svg(0)
       └─ _measure_text_cached(font, size, text) [LRU hit on repeated text]
  → cairosvg.svg2png(svg, ...) [unchanged]
  → write PNG bytes (sha256 identical to baseline)
```

#### 2.2.2 Verify path (NEW: check-fill)
```
check_fill(name, data_dict)
  → load template via templates.list_templates() resolver
  → if template has schema:
       expected_keys = schema.fields
       filled_keys = data.keys()
       empty = expected_keys - filled_keys
       placeholders = scan filled HWPX for {{...}}, ____, hp:t-empty cells
  → else:
       parse HWPX section XML
       collect <hp:t> nodes
       classify each: filled / empty / placeholder
  → return CheckResult(filled=[...], empty=[...], placeholders=[...])
  ~10ms total (no cairosvg, no wasmtime)
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| `_ENGINE` / `_MODULE` globals | wasmtime | WASM Engine cache |
| `_measure_text_cached` | functools | LRU |
| `_FONTS_REGISTERED` flag | fontconfig (via cairosvg) | Idempotent registration |
| `render_to_png(engine=)` | RhwpEngine | DI for batch |
| `check_fill` | pyhwpxlib.templates, OWPML XML parser | XML-level introspection |
| `hwpx_check_fill` MCP | check_fill | Thin wrapper |
| WORKFLOW.md Step D | (docs only) | Gating policy |

---

## 3. Data Model

### 3.1 Module-level Cache State

```python
# pyhwpxlib/rhwp_bridge.py
from typing import Optional
import wasmtime, functools

_ENGINE: Optional["wasmtime.Engine"] = None       # module singleton
_MODULE: Optional["wasmtime.Module"] = None       # compiled WASM, paired with _ENGINE
_ENGINE_PID: Optional[int] = None                 # detect fork()

def _get_engine_and_module() -> tuple["wasmtime.Engine", "wasmtime.Module"]:
    """Lazy init. Re-create on fork (PID change)."""
    global _ENGINE, _MODULE, _ENGINE_PID
    import os
    pid = os.getpid()
    if _ENGINE is None or _ENGINE_PID != pid:
        _ENGINE = wasmtime.Engine()
        _MODULE = wasmtime.Module(_ENGINE, _WASM_BYTES)
        _ENGINE_PID = pid
    return _ENGINE, _MODULE

@functools.lru_cache(maxsize=4096)
def _measure_text_cached(font_path: str, size: int, text: str) -> int:
    """Pure: same inputs → same width. No mutation."""
    return _measure_text_uncached(font_path, size, text)
```

```python
# pyhwpxlib/api.py
_FONTS_REGISTERED: bool = False

def _register_bundled_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    # ... fontconfig add bundled NanumGothic ...
    _FONTS_REGISTERED = True
```

### 3.2 CheckResult Dataclass

```python
# pyhwpxlib/templates/check_fill.py
from dataclasses import dataclass, field, asdict
from typing import List

@dataclass
class CheckResult:
    template: str                               # template name
    total_fields: int                           # known fields (from schema or detected)
    filled: List[str]      = field(default_factory=list)  # field keys that have non-empty values
    empty: List[str]       = field(default_factory=list)  # field keys with no value
    placeholders: List[str] = field(default_factory=list) # cells still showing {{key}} or ___ patterns
    schema_used: bool      = False              # True iff resolved via schema, else pattern fallback

    @property
    def is_complete(self) -> bool:
        return not self.empty and not self.placeholders

    def to_dict(self) -> dict:
        return asdict(self) | {"is_complete": self.is_complete}
```

### 3.3 Cache Invariants

| Invariant | Mechanism |
|-----------|-----------|
| `_ENGINE` valid in current process | `_ENGINE_PID == os.getpid()` 가드 |
| `_measure_text_cached` 결정성 | 입력 tuple hashable, 폰트 파일 변경은 path 변경으로 키 분리 |
| `_FONTS_REGISTERED` 단조 | True 로 한 번 set 후 unset 없음 (process lifetime) |
| Engine ≠ shared mutable state | wasmtime Engine 자체는 thread-safe, Store/Linker/Instance는 per call |

---

## 4. API Specification

### 4.1 Public API Changes

#### 4.1.1 `render_to_png` (modified)
```python
def render_to_png(
    hwpx_path: str,
    output_path: Optional[str] = None,
    *,
    page: int = 0,
    scale: float = 1.0,
    register_fonts: bool = True,
    engine: Optional["RhwpEngine"] = None,   # NEW (keyword-only)
) -> str:
    """
    Render HWPX page to PNG.

    NEW: Pass `engine=` to reuse a single RhwpEngine across many calls.
    Without it, the module-singleton WASM Engine cache still amortizes the
    851ms instantiate cost across calls.
    """
```

**Backward compat**: 기존 호출자(`engine` 미지정) 동작 동일. 첫 호출 cold time 만 변동(851ms → ~5ms after first).

#### 4.1.2 `check_fill` (NEW)
```python
# pyhwpxlib.templates.check_fill
def check_fill(template_name: str, data: dict) -> CheckResult: ...
```

#### 4.1.3 CLI `check-fill` (NEW)
```bash
pyhwpxlib check-fill <template_name> -d data.json [-o report.json]
# stdout: JSON of CheckResult
# exit 0 if is_complete, exit 1 if any empty/placeholder
```

#### 4.1.4 MCP `hwpx_check_fill` (NEW)
```
hwpx_check_fill(name: str, data: dict) -> dict
  Returns CheckResult.to_dict()
  Docstring: 2-3 sentences + 1 example
```

### 4.2 Compressed Docstring Examples

**Before** (`hwpx_render_png`, ~480 chars):
```
"""Render HWPX 1 page to PNG.

This tool uses cairosvg + bundled NanumGothic for Korean text. Returns
base64-encoded PNG. Note: cairosvg cannot resolve @font-face data URLs
for CJK text, so we substitute every font-family attribute to NanumGothic
after rhwp generates the SVG.

Args:
    path: Absolute path to HWPX file
    page: Page index (default 0)
    scale: Scale factor (default 1.0)
    register_fonts: Register bundled NanumGothic via fontconfig (default True)

Returns dict with png_base64, width, height.

Use this for final visual validation only. For intermediate fill
verification, prefer hwpx_check_fill (XML-level, ~10ms).
"""
```

**After** (~140 chars):
```
"""Render HWPX page to PNG (final visual check). Returns base64 PNG.
For intermediate fill verification use hwpx_check_fill instead (10× faster).

Example: hwpx_render_png("/abs/path/out.hwpx", page=0)
"""
```

**Compression target** (per tool):
| Tool | Before chars | After target | Cut |
|------|:-:|:-:|:-:|
| `hwpx_render_png` | ~480 | ≤180 | -62% |
| `hwpx_template_save_session` | ~520 | ≤200 | -62% |
| `hwpx_template_context` | ~410 | ≤170 | -59% |
| `hwpx_template_workspace_list` | ~380 | ≤160 | -58% |
| `hwpx_guide` | ~300 | ≤120 | -60% |
| `hwpx_check_fill` (NEW) | n/a | ≤180 | new |
| **Sum** | ~25K tokens | ≤12K | **-52%** |

---

## 5. UI/UX (N/A)

라이브러리/CLI/MCP 변경 — 그래픽 UI 없음.

---

## 6. Error Handling

### 6.1 Error Cases

| Case | Where | Behavior |
|------|-------|----------|
| `wasmtime` 미설치 | `_get_engine_and_module` 첫 호출 | 기존 `_HAS_WASMTIME` 플래그 + `_WASMTIME_INSTALL_HINT` 메시지 (현재 동작 유지) |
| fork 후 자식 프로세스 첫 호출 | `_get_engine_and_module` | PID 비교 후 lazy re-create. 사용자 보이지 않음 |
| LRU 캐시 메모리 압박 | `_measure_text_cached` | maxsize=4096 도달 시 LRU eviction (functools 자동) |
| `check_fill` template 미등록 | `templates.list_templates()` 폴백 | `FileNotFoundError("template not found: <name>")` |
| `check_fill` schema 손상 | schema 파싱 시 | warning 로그 + pattern fallback (silent skip 금지, 명시 reason) |
| `check-fill` CLI exit 1 | empty/placeholder 발견 | stderr 한 줄 요약 + stdout JSON. 자동화에서 grep |
| `engine=` 주입된 엔진이 잘못된 인스턴스 | `render_to_png` | `TypeError("engine must be RhwpEngine instance")` |

### 6.2 Cache Failure Mode

캐시 자체가 깨지면(예: `_measure_text_cached` exception) — 호출자에게 그대로 전파. 캐시는 결과만 저장하므로 실패 결과는 캐시 안 함 (functools 기본).

---

## 7. Security Considerations

- 신규 입력 표면 0 — 모든 변경이 내부 메모이제이션 또는 기존 입력 재해석
- `check_fill` 은 **로컬 HWPX/JSON만** 읽음. 외부 호출 없음
- `engine=` DI: instance 가 이 프로세스에서 생성된 wasmtime Store 를 가져야 함 — wrong engine 주입은 wasmtime 자체에서 실패 (additional check 불필요)

---

## 8. Test Plan

### 8.1 Test Scope

| Type | Target | Tool | Phase |
|------|--------|------|-------|
| L1: Unit | 캐시 hit/miss, fork-detect, CheckResult | pytest | Do |
| L2: Integration | render_to_png 정확도 + DI, check_fill end-to-end | pytest + fixture HWPX | Do |
| L3: Regression | byte-identical PNG (3 docs) + 5-run benchmark | pytest + scripts/bench_render.py | Do/Check |
| L4: Token | MCP tools-list 응답 길이 (변경 전/후) | manual measure (script optional) | Check |

### 8.2 L1: Unit Test Scenarios

| # | Test | Description | Expected |
|---|------|-------------|----------|
| U-01 | `test_engine_singleton_hit` | Two `RhwpEngine()` calls, same module | `_ENGINE is _ENGINE_first` |
| U-02 | `test_engine_pid_invalidate` | Mock os.getpid 변경 후 호출 | 새 Engine 생성됨 |
| U-03 | `test_measurer_lru_hit` | `_measure_text_cached` 같은 키 2회 | `cache_info().hits == 1` |
| U-04 | `test_measurer_distinct_fonts` | 다른 font_path 2회 | hits == 0 |
| U-05 | `test_fonts_registered_idempotent` | `_register_bundled_fonts` 2회 | 두 번째 호출은 noop |
| U-06 | `test_check_result_is_complete` | CheckResult 빈 empty/placeholders | `is_complete == True` |
| U-07 | `test_check_result_to_dict` | `to_dict()` 직렬화 | `is_complete` 키 포함 |

### 8.3 L2: Integration Test Scenarios

| # | Test | Description | Expected |
|---|------|-------------|----------|
| I-01 | `test_render_to_png_default_unchanged` | 0.17.3 동등 호출 | sha256 동일 (anchor) |
| I-02 | `test_render_to_png_with_engine_di` | 외부 engine 주입 | sha256 동일, 내부 RhwpEngine() 호출 0회 |
| I-03 | `test_render_to_png_n_times` | 5회 sequential | mean ≤ 200ms (cold 제외) |
| I-04 | `test_check_fill_schema_path` | schema 등록된 양식 | `schema_used == True`, empty 정확 |
| I-05 | `test_check_fill_pattern_fallback` | schema 없는 양식 | `schema_used == False`, placeholder 감지 |
| I-06 | `test_check_fill_complete` | 모든 필드 채운 결과 | `is_complete == True` |
| I-07 | `test_check_fill_partial` | 1개 필드 누락 | empty 1개, exit 1 |
| I-08 | `test_cli_check_fill_exit_codes` | CLI subprocess 호출 | complete=0, partial=1 |

### 8.4 L3: Regression / Benchmark

| # | Test | Description | Pass Criterion |
|---|------|-------------|----------------|
| R-01 | `test_render_consistency_doc1` | template_fill_makers.hwpx page=0 scale=1.0 | sha256 == `d4501ee...3f2c05` |
| R-02 | `test_render_consistency_doc2` | (선택 추가 문서) | sha256 anchor 일치 |
| R-03 | `test_render_consistency_doc3` | (선택 추가 문서) | sha256 anchor 일치 |
| B-01 | `bench_render.py` | 5회 sequential, 변경 전/후 | mean cold ≤ 1.3s, warm ≤ 200ms |

### 8.5 Seed Data

- `Test/output/template_fill_makers.hwpx` — 기존 파일, 회귀 anchor 의 입력
- 2개 추가 문서는 Do 단계에서 `Test/output/` 에서 선정 (1매 양식 / 다중 표 등 다양성)
- check_fill 테스트용 fixture: `tests/fixtures/check_fill/` 에 schema 있는/없는 양식 각 1개

---

## 9. Clean Architecture (적용 매핑)

| Layer | This Feature 컴포넌트 | Location |
|-------|----------------------|----------|
| Infrastructure | `_ENGINE`/`_MODULE` 캐시, `_register_bundled_fonts` | `pyhwpxlib/rhwp_bridge.py`, `pyhwpxlib/api.py` |
| Domain | `CheckResult` dataclass | `pyhwpxlib/templates/check_fill.py` |
| Application | `check_fill()` 함수 | `pyhwpxlib/templates/check_fill.py` |
| Presentation (CLI/MCP) | `_cmd_check_fill`, `hwpx_check_fill` | `pyhwpxlib/cli.py`, `pyhwpxlib/mcp_server/server.py` |

Dependency: Presentation → Application → Domain. Infrastructure(캐시)는 Application(api.py / rhwp_bridge.py 의 measurer) 내부에서 직접 사용 — 라이브러리이므로 layer 인입을 필수로 강제하지 않음.

---

## 10. Coding Convention Reference

### 10.1 This Feature's Conventions

| Item | Convention |
|------|-----------|
| Module-level cache 명명 | `_ENGINE`, `_MODULE`, `_FONTS_REGISTERED` (single leading underscore = module-private) |
| LRU 데코레이터 위치 | `@functools.lru_cache(maxsize=N)` 함수 정의부 직상 |
| CheckResult dataclass | `@dataclass(slots=False)` (asdict 호환) |
| Docstring 한국어 1문장 + 영어 보조 OR 영어 1문장 — MCP는 LLM 인식이 영어 ↑ → MCP는 영어 우선 |
| 신규 CLI subcommand | `pyhwpxlib/cli.py::_cmd_<name>` 핸들러 + parser 등록 |
| Exit codes | 0=성공/완전, 1=불완전, 2=사용 오류 |

### 10.2 GUIDE 갱신 규칙 (FR-09)

`pyhwpxlib/llm_guide.py::GUIDE`:
- 헤더 `# pyhwpxlib v0.18.0 — LLM Quick Reference Guide`
- 신규 섹션: "검증 분리 — check-fill (10× faster than PNG)"
- 신규 섹션: "Engine 재사용 — render_to_png(engine=)"
- 버전 히스토리 표 마지막 행 0.18.0 추가
- CLAUDE.md "Release checklist" 3번 100% 통과

---

## 11. Implementation Guide

### 11.1 File Structure (delta)

```
pyhwpxlib/
  rhwp_bridge.py           [MODIFY] +  ~40 lines (engine cache + measurer LRU)
  api.py                   [MODIFY] +  ~25 lines (font guard + engine= DI)
  cli.py                   [MODIFY] +  ~50 lines (check-fill handler + parser)
  llm_guide.py             [MODIFY] +  ~40 lines (v0.18.0 headers + new sections)
  __init__.py              [MODIFY] -- version bump
  templates/
    check_fill.py          [NEW]    +  ~150 lines
  mcp_server/
    server.py              [MODIFY] -- compress 6 docstrings + add hwpx_check_fill
scripts/
  bench_render.py          [NEW]    +  ~80 lines
tests/
  test_render_consistency.py  [NEW] +  ~60 lines
  test_check_fill.py          [NEW] +  ~200 lines
  test_text_measurer_cache.py [NEW] +  ~80 lines
  fixtures/check_fill/        [NEW] -- 2 small HWPX
skill/
  SKILL.md                 [MODIFY] -- Versions row 0.18.0
  hwpx-form/WORKFLOW.md    [MODIFY] -- Step D gating
pyproject.toml             [MODIFY] -- version 0.18.0
CHANGELOG.md               [MODIFY] -- 0.18.0 entry
```

총 변경: ~750 줄 (Plan 추정 ~250 줄에서 회귀 테스트 + GUIDE + WORKFLOW 포함하니 750)

### 11.2 Implementation Order

1. [ ] **Module 1 (cache)**: T1.1 + T1.2 + T1.3 + T1.4 — 캐시 5종 구현 + Unit U-01~U-05 + Integration I-01~I-03
2. [ ] **Module 2 (check-fill)**: `templates/check_fill.py` + CLI handler + MCP wrapper + tests U-06,07 + I-04~08
3. [ ] **Module 3 (docs)**: T1.5 docstring 압축 + WORKFLOW.md Step D + SKILL.md Versions + GUIDE
4. [ ] **Module 4 (regression+release)**: test_render_consistency 3 docs + bench_render.py + 0.18.0 release (CLAUDE.md 8단계)

### 11.3 Session Guide

#### Module Map

| Module | Scope Key | Description | Files | Estimated Turns |
|--------|-----------|-------------|-------|:---------------:|
| Cache layer | `cache` | T1.1~T1.4 (engine + measurer + font + DI) + Unit/Integration tests | rhwp_bridge.py, api.py, test_text_measurer_cache.py | 30-40 |
| Check-fill | `check-fill` | check_fill.py + CLI + MCP + 7 tests | check_fill.py, cli.py, server.py, test_check_fill.py | 35-45 |
| Docs+Compress | `docs` | docstring 압축, WORKFLOW Step D, SKILL Versions, GUIDE v0.18.0 | server.py, WORKFLOW.md, SKILL.md, llm_guide.py | 20-30 |
| Regression+Release | `release` | regression test, bench, 0.18.0 publish (CLAUDE.md 8단계) | test_render_consistency.py, bench_render.py, pyproject, CHANGELOG, skill zip | 25-35 |

#### Recommended Session Plan

| Session | Phase | Scope | Turns |
|---------|-------|-------|:-----:|
| Session 1 (this) | Plan + Design | 전체 | ✅ done |
| Session 2 | Do | `--scope cache` | 30-40 |
| Session 3 | Do | `--scope check-fill` | 35-45 |
| Session 4 | Do | `--scope docs` | 20-30 |
| Session 5 | Do + Check | `--scope release` + `/pdca analyze` | 30-40 |
| Session 6 | QA + Report | 전체 (`/pdca qa` + `/pdca report`) | 20-30 |

게이트:
- Session 5 의 release 는 Session 2~4 모두 완료 후에만 진행
- `analyze` 단계 Match Rate ≥ 90% 까지 iterate
- 각 세션 끝에서 `tests` 전수 PASS + sha256 anchor 확인

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-05 | Initial draft — Option C 채택, Module Map 4개, Session 6개 | ratiertm |
