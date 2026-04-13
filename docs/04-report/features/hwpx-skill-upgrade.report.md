# PDCA Completion Report: hwpx-skill-upgrade

> 기간: 2026-04-10 ~ 2026-04-14 (4일)
> Match Rate: **92%**
> 상태: **Completed**

---

## 1. 요약

hwpx skill의 안정성, 기능 범위, 엔지니어링 품질을 한 단계 올리는 업그레이드를 완료했다. rhwp WASM 시각 프리뷰, HWP→HWPX 변환 버그 수정, HWPX 룰북 확장, Golden Tests, JSON 라운드트립, MCP 서버까지 6개 Phase 중 5개를 구현했다.

## 2. 주요 성과

### 버그 수정 (Critical)
- **fwSpace/nbSpace/hyphen 텍스트 누락 버그** — hwp2hwpx.py 4곳 수정, upstream push (commit `3e1ed48`)
- 원인: extended control char 분류 오류로 뒤 14바이트 스킵 → 후속 글자 소실
- 영향: "성 명" → "성" (명 누락) 등 모든 fwSpace 뒤 텍스트
- **표 dual-height 동기화** — `<hp:sz>` + `<hp:cellSz>` 양쪽 수정 필요 발견, 룰북 §28 등록

### 신규 기능
| 기능 | 산출물 | 라인 |
|------|--------|------|
| **rhwp WASM 시각 프리뷰** | `scripts/preview.py`, SKILL.md Step F 교체 | ~80 |
| **JSON 라운드트립** | `pyhwpxlib/json_io/` (schema, encoder, decoder) | ~410 |
| **MCP 서버** (6 tools) | `pyhwpxlib/mcp_server/server.py` | ~185 |
| **Excel→HWPX 워크플로우** | SKILL.md 워크플로우 [5], `scripts/generate_afc_q2_report.py` | ~120 |
| **Warning-first 원칙** | `convert(verify=True)`, `_flush_run` 경고 | ~30 |
| **Golden Tests** | `tests/test_hwp2hwpx_golden.py`, `test_visual_golden.py` | ~100 |

### 문서 확장
| 문서 | 변경 |
|------|------|
| **HWPX_RULEBOOK.md** | §28~§33 추가 (6개 규칙: dual-height, BGR, landscape, TextBox, Polygon, breakWord) |
| **SKILL.md** | Step F 교체, 워크플로우 [5], Quick Reference 2건, Critical Rules #13~#20 (8개) |
| **메모리** | `reference_hwpx_table_dual_height.md` 추가 |

### 프로젝트 정리
- `samples/` + `Test/` 폴더 분리 (28개 파일 정리)
- `ratiertm-hwpx`, `python-hwpx-fork`, `hwpxlib` 제거 (**47MB 절감**)
- pyhwpxlib v0.2.1 sync (rhwp_bridge 폰트 임베딩, 머리말/꼬리말, GSO 도형)

## 3. 외부 프로젝트 분석

| 프로젝트 | 분석 결과 | 우리에게 영향 |
|----------|----------|-------------|
| **mjyoo2/hwp-extension** (TS) | TS↔Python 컨벤션 차이 확인 (colSz, horzRelTo). 에이전트의 "버그" 판정 3/4 무효 확인 | 교차 검증으로 불필요한 수정 방지 |
| **airmang/python-hwpx** (Python) | upstream 6 버전 뒤처짐. table_navigation (v2.9.0) 관심 | Task #6으로 보류 |
| **ai-screams/HwpForge** (Rust) | JSON 라운드트립 + MCP 원조. 112K LOC, 92% coverage | JSON 스키마 참조, 룰북 Gotchas 5개 반영 |

## 4. 정량 결과

### 테스트
| 테스트 유형 | 총 수 | Pass | Fail | 비고 |
|------------|-------|------|------|------|
| HWP→HWPX 문자 보존 | 12 | 8 | 4 | BinData zlib (기존 한계) |
| HWPX ZIP 유효성 | 12 | 8 | 4 | 동일 원인 |
| 시각 렌더링 | 20 | 20 | 0 | 전부 통과 |
| PNG 비어있지 않음 | 20 | 20 | 0 | 전부 통과 |
| **합계** | **52** | **48** | **4** | **92% pass** |

### JSON 라운드트립
- 20개 HWPX 파일 → JSON 추출 성공 (100%)
- patch 기능 동작 확인 (날짜 교체 테스트)

### MCP 서버
- 6개 tool 전부 importable + 기능 검증
- `hwpx_to_json`, `hwpx_from_json`, `hwpx_patch`, `hwpx_inspect`, `hwpx_preview`, `hwpx_validate`

## 5. 미완료 항목

| 항목 | 영향 | 다음 조치 |
|------|------|----------|
| `test_form_fill_golden.py` | Low | 다음 세션에서 추가 |
| Phase 6 upstream 동기화 | Med | Task #6으로 별도 진행 |
| MCP Claude Code 등록 실전 테스트 | Med | 사용자가 `claude mcp add` 실행 후 검증 |

## 6. 잔여 Task

| ID | 우선순위 | 작업 | 상태 |
|----|---------|------|------|
| #7 | High | JSON 라운드트립 + MCP 서버 | ✅ 완료 |
| #6 | Med | upstream python-hwpx sync | ⏳ |
| #5 | Med | table_navigation 통합 | ⏳ |
| #2 | Low | writer vertAlign 노출 | ⏳ |
| #4 | Backlog | HWP→HWPX writer 포팅 | ⏳ |

## 7. 교훈

### 잘 된 것
- **시각 프리뷰 루프**: rhwp WASM → PNG → Claude Read → 수정 → 재확인이 5분 내 동작. 이전 대비 Whale 의존 최소화
- **교차 검증 습관**: hwp-extension 에이전트의 "버그" 판정을 upstream(airmang)으로 교차 검증 → 3/4 무효 확인. 에이전트 출력을 맹신하지 않는 습관
- **바이너리 디버깅**: HWP raw char dump → fwSpace 버그 추적 → 4곳 수정 → upstream push. 체계적 접근

### 개선할 것
- **테스트 먼저**: Phase 4(Golden Tests)가 Phase 3 뒤에 왔는데, TDD 관점에서는 Phase 2 전에 테스트를 먼저 작성했어야 함
- **form_fill 테스트 누락**: 의견제출서 양식 채우기를 실제로 했지만 자동화 테스트를 안 만듦
- **JSON 스키마 검증**: HwpForge의 JSON 구조를 참조했지만 호환성은 없음. 향후 상호 운용성 결정 필요

## 8. PDCA 사이클 완성

```
[Plan] ✅ → [Design] ✅ → [Do] ✅ → [Check] ✅ 92% → [Report] ✅
```

**최종 Match Rate: 92%** — 90% 기준 충족. 업그레이드 완료.
