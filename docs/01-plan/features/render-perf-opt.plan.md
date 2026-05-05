---
template: plan
version: 1.3
feature: render-perf-opt
date: 2026-05-05
author: ratiertm
project: hwpx-skill / pyhwpxlib
version_at_plan: 0.17.3
target_version: 0.18.0
status: Draft
---

# render-perf-opt Planning Document

> **Summary**: 양식 채우기·검증 시나리오의 컴퓨트와 응답 토큰을 동시에 줄이는 캐싱 + 검증 분리 + docstring 압축 묶음. byte-identical PNG 회귀 0건이 절대 제약.
>
> **Project**: hwpx-skill / pyhwpxlib
> **Version**: 0.17.3 → 0.18.0
> **Author**: ratiertm
> **Date**: 2026-05-05
> **Status**: Draft

---

## Executive Summary

| Perspective | Content |
|-------------|---------|
| **Problem** | 5장 fill-and-verify 시나리오에서 매번 RhwpEngine 신규 생성(851ms) + cairosvg 폰트 재등록 + 동일 텍스트 재측정으로 ~6초 소요. MCP 도구 docstring이 다단락이라 tools-list 응답이 ~25K 토큰. |
| **Solution** | Tier 1 메모이제이션 5종(엔진·텍스트 측정·폰트 가드·DI·docstring 압축) + 신규 XML-level `check-fill`(~10ms) + 워크플로 [3] Step D 게이팅으로 중간 PNG 생성 제거. 렌더링 로직 자체는 무변경. |
| **Function/UX Effect** | 컴퓨트 6초 → 1초(-83%), 응답 토큰 25K → 10K(-60%). LLM 라우팅에서는 docstring 슬림화로 도구 선택 정확도 ↑, 사용자에서는 fill-cycle 응답 지연 체감 감소. |
| **Core Value** | 정확도(byte-identical PNG) 무손실로 비용/지연 동시 절감 — 후발주자 BaaS 라이브러리에서 가장 자주 트리거되는 경로(양식 채우기)의 단가가 1/6로 떨어진다. |

---

## Context Anchor

| Key | Value |
|-----|-------|
| **WHY** | 양식 채우기 cycle이 비싸고 느려서 사용자가 "한 번 더 채워볼까" 망설이는 단계 — 단가 절감이 사용 빈도를 늘린다. |
| **WHO** | pyhwpxlib MCP/CLI 사용자 (Claude Code, ChatGPT 등 LLM 오케스트레이션 + 직접 CLI). 특히 양식 다중 채우기 시나리오. |
| **RISK** | 캐시 무효화 실수 → byte-identical PNG 회귀. 한 번이라도 sha256 어긋나면 모든 양식 사용자에게 영향. |
| **SUCCESS** | (1) 회귀 PNG sha256 동일 (2) 5장 fill 컴퓨트 ≤ 1.5초 (3) tools-list 응답 ≤ 12K 토큰 (4) 테스트 PASS ≥ 175. |
| **SCOPE** | Tier 1 (T1.1~T1.5) + T2.2(check-fill) + T2.3(워크플로 게이팅) + INF(회귀/벤치) + REL(0.18.0). T3 항목 전부 보류. |

---

## 1. Overview

### 1.1 Purpose

5장 양식 fill-and-verify 시나리오의 컴퓨트와 응답 토큰을 동시에 줄인다. 정확도 영역 무변경.

### 1.2 Background

2026-05-05 프로파일링에서 다음 병목 식별:

- `RhwpEngine()` instantiate: **851 ms** (WASM compile 단계)
- `render_to_png` cold: **1,291 ms**
- `render_to_png` 5회 평균: **879 ms/회** (매번 새 엔진)
- 양식 채우기 워크플로[3]가 매 중간 step마다 `render_to_png` 호출 → 5장이면 PNG 5번 생성
- MCP `hwpx_template_*`/`hwpx_render_png`/`hwpx_guide` docstring이 4-7 단락 → tools-list 응답이 모델 컨텍스트의 25K 토큰을 점유
- 실제로 fill 결과 검증에 필요한 정보는 "빈칸 남았는지 + 어떤 셀이 비었는지" 두 가지뿐 (PNG 수준이 필요한 건 최종 단계 1회)

근본 원인: 후발주자 라이브러리이지만 양식 채우기는 현재 가장 자주 트리거되는 경로 — 이 경로의 단위 비용이 BaaS의 매력도를 직접 결정.

### 1.3 Related Documents

- TODO 항목: `TODO.md` 최상단 "다음 세션: render-perf-opt"
- 회귀 anchor: `Test/output/template_fill_makers.hwpx`, page=0, scale=1.0, register_fonts=False → sha256 `d4501eeed09bc3d4d6c45a887523fdec913f428bdfee18f3e8c2570a793f2c05`, 85,966 bytes
- 관련 워크플로: `skill/hwpx-form/WORKFLOW.md` Step D
- 메모리: `feedback_version_sync.md`, `feedback_hancom_security_trigger.md`

---

## 2. Scope

### 2.1 In Scope

- [ ] **T1.1** wasmtime `Engine` + `Module` 모듈-레벨 싱글턴 캐시 (`pyhwpxlib/rhwp_bridge.py`)
- [ ] **T1.2** `_TextMeasurer` `functools.lru_cache` on `(font_path, size, text)` → width
- [ ] **T1.3** `_register_bundled_fonts` 모듈-레벨 가드 (프로세스당 1회)
- [ ] **T1.4** `render_to_png(..., engine: Optional[RhwpEngine] = None)` DI 파라미터 추가
- [ ] **T1.5** MCP 도구 docstring 압축 (2-3문장 + 예시 1개) — `hwpx_template_*`, `hwpx_render_png`, `hwpx_guide`
- [ ] **T2.2** 신규 CLI `pyhwpxlib check-fill <name> -d data.json` + MCP `hwpx_check_fill` (부분 메타 + 빈칸 리스트 JSON, ~10ms)
- [ ] **T2.3** `skill/hwpx-form/WORKFLOW.md` Step D 갱신 — 중간 검증은 `check-fill`, 최종에만 `render_to_png` (안티 패턴 예시 추가)
- [ ] **INF-1** `tests/test_render_consistency.py` — 변경 전/후 byte-identical PNG (3개 문서, sha256 anchor)
- [ ] **INF-2** `scripts/bench_render.py` — 5회 sequential, mean/p50/p95 보고
- [ ] **REL** 0.18.0 minor 릴리스 — pyproject + `__init__.py` + CHANGELOG + skill zip + `llm_guide.GUIDE` (CLAUDE.md "Release checklist" 8단계 준수)

### 2.2 Out of Scope

- **T3.1** wasmtime AOT 디스크 캐시 — 별도 PDCA cycle (디스크 권한·crash 시 무효화 정책 별도 설계 필요)
- **T3.2** 병렬 렌더링 — 1-2 페이지 양식이 대부분이라 회귀 위험 대비 효과 낮음
- **T3.3** SKILL.md 슬림화 20-30% — 라우팅 영향 검증을 별도 사이클에서
- **T3.4** Anthropic `cache_control` 마커 문서화 — 본 사이클의 docstring 압축이 우선
- 렌더링 로직 변경 (rhwp WASM 자체, SVG/PNG 변환 알고리즘) — accuracy anchor를 깰 위험
- 양식 채우기 알고리즘 변경 — 본 사이클은 "주변 메타·검증 도구"만 다룸

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | `RhwpEngine()` 두 번째 이후 instantiate 가 < 50ms (Engine·Module 모듈-레벨 캐시 hit) | High | Pending |
| FR-02 | 동일 `(font_path, size, text)` 두 번째 측정이 측정 호출 0회 (LRU hit) | High | Pending |
| FR-03 | `_register_bundled_fonts()` 두 번째 호출이 fontconfig add 호출 0회 (가드 작동) | High | Pending |
| FR-04 | `render_to_png(engine=engine)` 로 외부 엔진 주입 시 내부 신규 instantiate 0회 | High | Pending |
| FR-05 | 변경 후 `tools-list` 응답 토큰이 변경 전 대비 ≥ 50% 감소 (압축 docstring) | High | Pending |
| FR-06 | `pyhwpxlib check-fill <name> -d data.json` 가 `{filled: [...], empty: [...], placeholders: [...]}` JSON 출력 + 빈칸 0개일 때 exit 0 | High | Pending |
| FR-07 | `hwpx_check_fill` MCP 도구가 동일 결과를 dict 로 반환 | High | Pending |
| FR-08 | `skill/hwpx-form/WORKFLOW.md` Step D 가 "중간엔 check-fill, 최종에만 PNG" 게이팅 명시 + 안티 패턴 예시 1개 | Medium | Pending |
| FR-09 | 0.18.0 릴리스가 CLAUDE.md 8단계 체크리스트 100% 통과 (특히 `llm_guide.GUIDE` 본문 갱신 항목) | High | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Accuracy | 변경 전/후 PNG sha256 동일 (3개 문서) | `tests/test_render_consistency.py` (anchor sha256 비교) |
| Performance (compute) | 5회 sequential `render_to_png` mean ≤ 200ms (cold 1회 제외) | `scripts/bench_render.py` 변경 전/후 비교 |
| Performance (token) | MCP `tools-list` 응답 ≤ 12K 토큰 (현재 ~25K) | 변경 전/후 응답 길이 측정 |
| Reliability | 기존 167 tests + 신규 약 8 tests = 175 PASS | `pytest -q` |
| Compatibility | 0.17.x 사용자 코드 무수정 동작 (`render_to_png` 시그니처는 keyword-only 추가) | tests + manual smoke |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] FR-01 ~ FR-09 모두 구현·검증 완료
- [ ] `tests/test_render_consistency.py` 신규 — 3개 문서 byte-identical PNG 회귀 0건
- [ ] `scripts/bench_render.py` 신규 + 변경 전/후 결과 CHANGELOG에 첨부
- [ ] 신규 약 8 테스트 케이스 (check-fill 기능 + 캐시 hit/miss + DI)
- [ ] CLAUDE.md "Release checklist" 8단계 모두 ✅
- [ ] PyPI 0.18.0 publish + git tag + skill zip + `~/.claude/skills/hwpx/` sync

### 4.2 Quality Criteria

- [ ] Accuracy regression: PNG sha256 anchor 동일
- [ ] Compute: 5회 mean ≤ 200ms (cold 제외)
- [ ] Token: tools-list ≤ 12K
- [ ] Test: ≥ 175 PASS, 기존 167 PASS 그대로
- [ ] No new lint errors

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 모듈-레벨 Engine 캐시가 멀티프로세스/포크 시 깨짐 | High | Low | wasmtime `Engine` 은 thread-safe but fork-unsafe — `os.fork` 후 자식에서 access 시 lazy re-create. 문서화 + smoke test. |
| LRU 캐시 키 누락(예: font 변경 후 재측정 누락) | High | Medium | 키에 `(font_path, size, text)` 모두 포함. resolver가 같은 폰트를 다른 path로 리졸브하면 키 분리 — 이 케이스는 변경 전과 동일 동작 (cache miss). |
| `render_to_png(engine=)` 외부 주입 시 엔진 상태 오염 | Medium | Low | 매 호출 시 새 `Store`/`Linker`/`Instance` (T1.1 스코프 명시). 사용자 코드 영향 0. |
| docstring 과도 압축으로 LLM 도구 선택 오류 | High | Medium | 2-3문장 + 예시 1개 (1문장만은 회피). Plan에 sample docstring 첨부. CHECK 단계에서 실제 LLM 호출로 도구 선택 정확도 비교. |
| check-fill XML 파싱이 schema 미등록 양식에서 placeholder 오인식 | Medium | Medium | schema 있으면 schema 우선, 없으면 hp:t 텍스트의 `_____`/공백-only/`{{...}}` 3패턴만 placeholder 로 분류. 그 외는 filled. |
| 0.18.0 릴리스 후 GUIDE 미갱신 (0.10.0~0.16.x 재현) | High | Low | CLAUDE.md 8단계 체크리스트 도입 후 처음 적용 — Plan에 GUIDE 본문 변경 항목 명시 (FR-09). |

---

## 6. Impact Analysis

### 6.1 Changed Resources

| Resource | Type | Change Description |
|----------|------|--------------------|
| `pyhwpxlib/rhwp_bridge.py` | Module | wasmtime `Engine`/`Module` 모듈-레벨 캐시 추가, `_TextMeasurer` LRU 추가 |
| `pyhwpxlib/api.py` | Module | `_register_bundled_fonts` 가드, `render_to_png(engine=)` DI |
| `pyhwpxlib/cli.py` | Module | 신규 `check-fill` subcommand 핸들러 + parser |
| `pyhwpxlib/mcp_server/server.py` | Module | docstring 압축 (`hwpx_template_*`, `hwpx_render_png`, `hwpx_guide`) + 신규 `hwpx_check_fill` |
| `pyhwpxlib/templates/` | Package | 신규 `check_fill.py` (XML-level 빈칸 검증 로직) — schema 있으면 schema 사용, 없으면 패턴 |
| `pyhwpxlib/llm_guide.py` | Module | v0.18.0 헤더 + check-fill 섹션 + 버전 히스토리 갱신 (FR-09) |
| `skill/hwpx-form/WORKFLOW.md` | Skill doc | Step D 게이팅 + 안티 패턴 예시 |
| `skill/SKILL.md` | Skill doc | Versions 표 0.18.0 행 추가 |
| `tests/` | Test | `test_render_consistency.py` (신규), `test_check_fill.py` (신규), `test_text_measurer_cache.py` (신규) |
| `scripts/bench_render.py` | Script | 신규 |
| `pyproject.toml`, `pyhwpxlib/__init__.py`, `CHANGELOG.md` | Release | 0.17.3 → 0.18.0 |

### 6.2 Current Consumers

| Resource | Operation | Code Path | Impact |
|----------|-----------|-----------|--------|
| `RhwpEngine()` | instantiate | `pyhwpxlib/api.py::render_to_png`, MCP `hwpx_render_png`, 사용자 코드 | None — 호출 시그니처 무변경, 캐시 hit는 투명 |
| `render_to_png(...)` | call | MCP `hwpx_render_png`, CLI `png`, skill workflow | None — 신규 keyword `engine=` 는 optional, default 무동작 동일 |
| `_register_bundled_fonts()` | call | `render_to_png` 내부, 잠재적으로 사용자 코드 | None — 두 번째 호출이 no-op 되는 게 차이의 전부 |
| `_TextMeasurer` | call | `pyhwpxlib/rhwp_bridge.py` 내부 | None — pure 캐싱, 결과 동일 |
| MCP tools (`hwpx_template_*` 등) | invoke | Claude Code, ChatGPT MCP client | docstring 길이만 변경 — 도구 시그니처/동작 무변경 |
| `pyhwpxlib check-fill` | new CLI | 신규 — 기존 호출자 0 | N/A |
| `hwpx_check_fill` | new MCP tool | 신규 | N/A |

### 6.3 Verification

- [ ] 모든 기존 호출자가 byte-identical PNG anchor 통과 (회귀 테스트)
- [ ] `engine=` 미주입 호출 (default) 가 0.17.3 동작과 동일 (cold 시간 + sha256)
- [ ] 압축된 docstring 으로도 Claude Code 도구 선택 정확도 무회귀 (CHECK 단계 실측)

---

## 7. Architecture Considerations

### 7.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | 단일 파일 | — | ☐ |
| **Dynamic** | feature 단위 모듈 | — | ☐ |
| **Library/CLI/MCP** | 본 프로젝트 (pyhwpxlib) | Python 라이브러리 + CLI + MCP 서버 | ☑ |

### 7.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| Engine 캐시 스코프 | thread-local / process-level / module singleton | **module singleton** | wasmtime Engine 자체가 thread-safe, RhwpEngine 인스턴스는 호출별 분리 (Store/Linker/Instance). fork-unsafe 만 lazy re-create로 해결 |
| 텍스트 측정 캐시 | functools.lru_cache / OrderedDict / 외부 캐시 | **functools.lru_cache(maxsize=4096)** | stdlib, thread-safe, 키가 hashable (tuple), 측정 자체가 결정론 |
| Font 가드 위치 | global flag / process-level lock / contextvar | **global module-level flag** | fontconfig add는 idempotent + thread-safe, single-flight 만으로 충분 |
| check-fill 검증 방법 | XML pattern match / schema-based / hybrid | **hybrid (schema 우선, 폴백 pattern)** | schema 등록 양식은 정확도 100%, 미등록 양식은 패턴으로 best-effort |
| Docstring 압축 형식 | 1문장 / 2-3문장+예시 / table | **2-3문장 + 예시 1개** | LLM 도구 선택 신호로 What/When/예시 모두 필요 |
| 릴리스 타이밍 | Tier 1 끝나면 patch / 일괄 minor | **일괄 0.18.0 minor** | 신규 CLI subcommand 라서 patch 부적합. PDCA 완료 후 1회 publish |

### 7.3 Folder Structure (delta only)

```
pyhwpxlib/
  rhwp_bridge.py        ← Engine/Module module-singleton + LRU
  api.py                ← _register_bundled_fonts guard + render_to_png(engine=)
  cli.py                ← + check-fill handler
  llm_guide.py          ← bump v0.18.0
  templates/
    check_fill.py       ← (new) XML-level 빈칸 검증
  mcp_server/
    server.py           ← compressed docstrings + hwpx_check_fill
scripts/
  bench_render.py       ← (new)
tests/
  test_render_consistency.py  ← (new) sha256 anchor
  test_check_fill.py          ← (new)
  test_text_measurer_cache.py ← (new)
skill/
  SKILL.md              ← Versions row 0.18.0
  hwpx-form/
    WORKFLOW.md         ← Step D gating
```

---

## 8. Convention Prerequisites

### 8.1 Existing Project Conventions

- [x] `CLAUDE.md` Release checklist 8단계 (이번 사이클 적용 대상)
- [x] `feedback_version_sync.md` (pyproject + `__init__.py` 동시 bump)
- [x] `feedback_hancom_security_trigger.md` (precise lineseg fix opt-in)
- [x] Critical Rules #10~#13 — 본 사이클은 렌더링 정확도 영역 무변경이라 직접 영향 없음

### 8.2 Conventions to Verify

| Category | Current | To Verify | Priority |
|----------|---------|-----------|:--------:|
| 캐시 키 결정론 | exists | `_TextMeasurer` 키가 mutable 입력 받지 않음 | High |
| MCP docstring 톤 | mixed | 압축 후에도 한국어 1줄 + 예시 1개 일관 | Medium |
| 릴리스 8단계 | exists (CLAUDE.md) | 본 사이클로 처음 풀 사이클 적용 | High |

### 8.3 Environment Variables

해당 없음 — 본 사이클은 모듈 내부 변경만.

---

## 9. Next Steps

1. [ ] `/pdca design render-perf-opt` — 3 architecture options 비교 후 선택
2. [ ] Design 단계에서 모듈 분할 결정 (특히 `templates/check_fill.py` 위치 — `pyhwpxlib/check_fill.py` vs subpackage)
3. [ ] Design 단계에서 `_TextMeasurer` 캐시 정책 (maxsize, eviction)
4. [ ] `/pdca do render-perf-opt --scope tier1` (Tier 1만 먼저 1세션) → `--scope check-fill` → `--scope release`
5. [ ] Release: CLAUDE.md 8단계 — 특히 GUIDE 본문 갱신 (FR-09) 누락 방지

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-05-05 | Initial draft — TODO.md 기반 + Checkpoint 1/2 사용자 확정 반영 | ratiertm |
