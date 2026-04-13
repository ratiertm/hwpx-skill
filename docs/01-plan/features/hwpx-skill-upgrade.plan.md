# PDCA Plan: hwpx-skill-upgrade

> 이번 세션(2026-04-10~13)에서 발견된 기능/개선사항을 hwpx skill에 체계적으로 반영

## 배경

이번 세션에서 다음 작업을 수행하며 다수의 개선 필요사항을 발견:
- pyhwpxlib v0.2.1 sync (rhwp WASM 프리뷰, 폰트 임베딩)
- 시각 QA 자동화 루프 구축 (preview.py)
- AI반도체_시장분석.hwpx 버그 수정 (dual-height, charPr 불일치)
- Excel→HWPX 보고서 생성 (AFC 정기점검 결과)
- HWP→HWPX 변환 버그 수정 (fwSpace/nbSpace/hyphen 텍스트 누락)
- 외부 프로젝트 비교 분석 (hwp-extension, airmang/python-hwpx, HwpForge)
- 파일 정리 (samples/, Test/, 불필요 fork 제거)

## 목표

hwpx skill의 안정성, 기능 범위, 엔지니어링 품질을 한 단계 올린다.

---

## Phase 1: 즉시 반영 (완료/진행 중)

### 1-1. SKILL.md 업데이트 ✅
- [x] Step F: rhwp WASM 프리뷰로 교체
- [x] 워크플로우 [5] Excel→HWPX 추가
- [x] Quick Reference에 Preview, Excel 추가
- [x] Critical Rules #13 (셀 hard-wrap), #14 (표 청킹), #15 (dual-height) 추가

### 1-2. HWPX_RULEBOOK.md ✅
- [x] §28 표 dual-height 동기화 규칙

### 1-3. scripts 동기화 ✅
- [x] preview.py → skill에 복사
- [x] create.py 업데이트

### 1-4. pyhwpxlib 버그 수정 ✅
- [x] hwp2hwpx.py: fwSpace/nbSpace/hyphen extended control 잘못 분류 (4곳)
- [x] upstream push 완료 (commit 3e1ed48)

### 1-5. 프로젝트 정리 ✅
- [x] samples/, Test/ 폴더 분리
- [x] ratiertm-hwpx, python-hwpx-fork, hwpxlib 제거 (47MB 절감)
- [x] .gitignore 업데이트

---

## Phase 2: HWPX_RULEBOOK 확장 (1-2일)

HwpForge의 Gotchas 22개 중 우리에게 적용되는 항목 추가.

### 2-1. Color BGR 규칙 추가
- HWP는 BGR 바이트 오더 (0xFF0000 = 파란색!)
- hwp2hwpx.py의 색상 처리가 올바른지 검증
- 룰북 §29로 추가

### 2-2. landscape 반전 명시
- WIDELY = 세로, NARROWLY = 가로 (직관과 반대)
- 룰북 §30으로 추가

### 2-3. TextBox 규칙
- TextBox = `hp:rect` + `hp:drawText` (control 아님)
- 요소 순서/shapeComment 필수
- 룰북 §31로 추가

### 2-4. Polygon 닫힘 규칙
- 첫 꼭짓점을 마지막에 반복 필수
- 룰북 §32로 추가

### 2-5. breakNonLatinWord 규칙
- `KEEP_WORD` 사용 (BREAK_WORD 시 글자 퍼짐)
- 룰북 §33으로 추가

---

## Phase 3: Warning-first 원칙 적용 (2-3일)

HwpForge의 핵심 설계 원칙을 hwp2hwpx.py에 적용.

### 3-1. unknown char 경고 추가
- 현재: `else: pass` (조용히 무시)
- 변경: `warnings.warn(f"Unknown control char {ch:#x} at pos {pos}")` 로 경고
- fwSpace 버그 같은 문제를 조기 발견 가능

### 3-2. 변환 결과 검증 리포트
- 변환 후 원본 HWP text vs HWPX text 비교
- 글자 수 차이, 누락 문자 자동 감지
- `convert()` 함수에 `verify=True` 옵션 추가

---

## Phase 4: Golden Tests 도입 (2-3일)

### 4-1. 기본 round-trip 테스트
- samples/ 폴더의 실제 파일 10개로 HWP→HWPX→extract_text 검증
- 변환 전후 텍스트 일치 확인
- `tests/test_hwp2hwpx_golden.py`

### 4-2. 시각 round-trip 테스트
- HWPX→rhwp SVG→PNG 비교
- 기준 PNG 저장 → 이후 변경 시 pixel diff
- `tests/test_visual_golden.py`

### 4-3. form fill round-trip 테스트
- 의견제출서 등 양식 → 데이터 채우기 → 추출 → 일치 검증
- `tests/test_form_fill_golden.py`

---

## Phase 5: JSON 라운드트립 + MCP 서버 (MVP 3-5일) — Task #7

### 5-1. JSON 스키마 설계
- Hybrid 방식: semantic top layer + _preservation
- form_pipeline의 dict 추출 로직을 일반화

### 5-2. to_json / from_json 구현
- `pyhwpxlib/json_io/encoder.py` — HWPX → JSON
- `pyhwpxlib/json_io/decoder.py` — JSON → HWPX
- `pyhwpxlib/json_io/preservation.py` — byte-preserving patch

### 5-3. MCP 서버
- fastmcp 기반 6 tools
- `hwpx_to_json`, `hwpx_from_json`, `hwpx_patch`, `hwpx_inspect`, `hwpx_preview`, `hwpx_validate`
- Claude Code 등록: `claude mcp add pyhwpxlib -- python -m pyhwpxlib.mcp_server.server`

---

## Phase 6: upstream 동기화 검토 — Task #6

### 6-1. airmang/python-hwpx v2.9.0 table_navigation 평가
- 라벨 기반 셀 탐색 + 배치 채우기
- form_pipeline과의 통합 가능성

### 6-2. HwpForge CLI/MCP 활용 검토
- `@hwpforge/mcp` 설치 실험
- JSON round-trip 워크플로우 비교 (우리 구현 vs HwpForge)
- 병행 사용 여부 결정

---

## 우선순위 및 일정

| Phase | 작업 | 기간 | 의존성 |
|-------|------|------|--------|
| 1 | 즉시 반영 | ✅ 완료 | - |
| 2 | 룰북 확장 | 1-2일 | - |
| 3 | Warning-first | 2-3일 | Phase 2 |
| 4 | Golden Tests | 2-3일 | Phase 3 |
| 5 | JSON + MCP (MVP) | 3-5일 | Phase 4 |
| 6 | upstream 동기화 | 1-2일 | - |

**총 예상: 9-15일** (Phase 1 제외)

## 성공 기준

- [ ] HWPX_RULEBOOK §28~§33 완성 (6개 규칙 추가)
- [ ] hwp2hwpx.py에 warning 로깅 + 변환 검증
- [ ] Golden test 15개 이상, 전부 통과
- [ ] JSON round-trip으로 기존 Test/*.hwpx 5개 이상 무손실 변환
- [ ] MCP 서버 6 tools 동작, Claude Code에서 `hwpx_to_json` 호출 성공
- [ ] samples/ 파일 중 HWP→HWPX 변환 시 텍스트 누락 0건

## 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| JSON 스키마 설계 복잡 | Phase 5 지연 | form_pipeline dict를 시작점으로 MVP 범위 축소 |
| Golden test 실패 다수 | Phase 4 지연 | 실패 테스트를 TODO로 기록하고 점진 수정 |
| HwpForge MCP와 기능 중복 | Phase 6 결정 지연 | 병행 전략 (각자 강점 영역 분리) |
| hwp2hwpx 추가 버그 발견 | 전체 일정 영향 | warning-first로 조기 감지, 발견 즉시 수정 |
