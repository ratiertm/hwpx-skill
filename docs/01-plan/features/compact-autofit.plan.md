---
template: plan
version: 1.2
feature: compact-autofit
date: 2026-04-23
author: Mindbuild
project: pyhwpxlib
version_proj: 0.11.0
status: Draft
---

# compact-autofit Planning Document

> **Summary**: `GongmunBuilder(compact=True, 항목간_공백=True)`로 공문을 생성했을 때 결문이 2페이지로 넘어가는 문제를, rhwp RenderTree 기반으로 자동 감지·보정하여 1페이지에 맞추는 기능.
>
> **Project**: pyhwpxlib
> **Version**: 0.11.0 → 0.12.0
> **Author**: Mindbuild
> **Date**: 2026-04-23
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

공문(1장 원칙)을 `compact` 모드로 밀도 있게 배치하면서도 항목 간 가독성을 위해 `항목간_공백=True` 를 주면, 본문 길이에 따라 결문("끝." / 발신명의 / 협조자 / 결재란)이 두 번째 페이지로 밀리는 경우가 발생한다. 현재는 사람이 눈으로 확인한 뒤 줄간격·여백을 수동으로 재조정해야 한다.

이 기능은 생성 직후 `rhwp` RenderTree를 조회하여 오버플로우 여부를 판정하고, 정해진 우선순위에 따라 spacer 크기·줄간격·여백을 자동 축소해 1페이지 안에 맞도록 재저장한다.

### 1.2 Background

- **기존 TODO**: Task #12 (project_next_todo.md) — "compact 모드 1페이지 보장". 지금까지는 시각 피드백 루프(Whale/PNG 확인 → 코드 수정)로 해결.
- **신규 가용성**: 2026-04-23 `rhwp_bridge.get_page_render_tree()` 추가 — 페이지별 bbox/children을 JSON으로 취득 가능. 자동 감지의 재료가 갖춰짐.
- **비즈니스**: 공문은 "1장이 표준" 이라는 행정 관례가 강해, 1.1 페이지로 넘치는 결과물은 실무 사용자에게 즉시 불합격 판정.

### 1.3 Related Documents

- 선행 커밋: `7b54bae feat(rhwp_bridge): HTML / RenderTree / Canvas-count 메서드 추가`
- 룰 출처: `docs/.pdca-snapshots/…` 없음 (신규 기능)
- 참조 코드: `pyhwpxlib/gongmun/builder.py`, `pyhwpxlib/rhwp_bridge.py`
- TODO 기록: `memory/project_next_todo.md` Task #12

---

## 2. Scope

### 2.1 In Scope

- [ ] `GongmunBuilder` 에 `autofit: bool = False` 옵션 추가
- [ ] 저장 직후 RenderTree로 본문 + 결문의 최대 y+h 계산
- [ ] body bbox 바깥으로 넘친 경우 자동 재조정 루프 (max 3회)
- [ ] 조정 우선순위: ① spacer 높이 축소 → ② 줄간격 축소 → ③ 상/하 여백 -2mm → ④ `compact` 강제
- [ ] 실패 시 경고 로그 + 원본 보존
- [ ] smoke test: 긴 본문 샘플이 autofit 후 1페이지로 수렴하는지 검증
- [ ] Task #12 종결 조건 충족

### 2.2 Out of Scope

- 복수 페이지 공문의 자동 분할 (결재란만 2페이지)
- 표가 포함된 첨부문서 레이아웃 (별도 이슈)
- Whale/Hancom 실제 렌더 기준 fit (rhwp 기준만 신뢰)
- 폰트 크기 자동 축소 — 공문 표준 15pt 규정 위반

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | `GongmunBuilder(autofit=True)` 옵션 도입 (기본 False) | High | Pending |
| FR-02 | `save()` 직후 rhwp RenderTree 로 overflow 판정 | High | Pending |
| FR-03 | overflow 시 spacer/줄간격/여백 순서로 최대 3회 재시도 | High | Pending |
| FR-04 | 각 시도별 적용 파라미터와 결과 y+h 를 로그(DEBUG) | Medium | Pending |
| FR-05 | 최종 1페이지 fit 실패 시 WARN 로그 + 마지막 산출물 유지 | Medium | Pending |
| FR-06 | autofit 비활성 시 성능 영향 0 (렌더 안 함) | High | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|--------------------|
| Performance | autofit 활성 시 추가 시간 < 2초/문서 (WASM 로드 1회 재사용) | `time.perf_counter()` 측정 |
| Accuracy | 현재 수동 성공 사례 5건 중 5건 autofit으로도 1페이지 유지 | 회귀 테스트 |
| Safety | autofit=False 동작 완전 동일 (바이트 단위 일치) | golden file 비교 |
| Reliability | rhwp 로드 실패 시 autofit 스킵 + 경고 (예외 전파 X) | try/except + 원본 반환 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] `GongmunBuilder.autofit` 옵션 구현 + 단위 테스트 통과
- [ ] smoke test: 짧은 문서(autofit 불필요) / 긴 문서(autofit 필요) 둘 다 1페이지 수렴
- [ ] 기존 `tests/test_rhwp_bridge_extensions.py` 4건 그대로 통과
- [ ] Task #12 TaskUpdate completed
- [ ] CHANGELOG에 "0.12.0 (예상): gongmun autofit" 기재

### 4.2 Quality Criteria

- [ ] autofit=True 경로 코드 커버리지 ≥ 80%
- [ ] autofit=False 경로 golden 비교 통과 (바이트 동일)
- [ ] 회귀: 기존 `롯데이노베이트_*.hwpx` 재생성 결과 동일 렌더

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|:------:|:----------:|------------|
| rhwp RenderTree가 Whale 실제 레이아웃과 어긋나 오판 | High | Medium | autofit=False 를 기본값 유지, 옵트인 전용. 문서에 "rhwp 추정치" 명시 |
| 재조정 루프가 수렴하지 않아 무한반복 | High | Low | 반복 횟수 하드 상한 3, 실패 시 WARN |
| 공문 표준 여백(20/20mm) 을 autofit이 깎아 실무 반려 | Medium | Medium | 최소 여백 가드 (상 ≥ 15mm, 하 ≥ 15mm, 좌우 ≥ 18mm) |
| autofit 활성 시 WASM 초기화 비용으로 배치 생성 속도 저하 | Medium | High | RhwpEngine 싱글톤 재사용, 옵션 OFF 기본값 |
| linesegarray 불일치로 rhwp 가 false-positive overflow 판정 | Medium | Medium | 2px 여유 허용 (tolerance=2px) |

---

## 6. Architecture Considerations

### 6.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | 단일 모듈, 순수 Python 라이브러리 | 자립형 라이브러리 기능 추가 | ☑ |
| **Dynamic** | feature-based 모듈 구조 | 백엔드 연동, SaaS | ☐ |
| **Enterprise** | 계층 분리, DI | 대규모 시스템 | ☐ |

> `pyhwpxlib` 은 순수 Python 라이브러리. 기존 `gongmun/` 모듈에 기능만 추가.

### 6.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| 감지 방식 | (A) y+h 단순 비교 / (B) body_area 엄격 비교 / (C) 페이지 수 > 1 | **B** | body_area (margin 제외) 대비로 해야 footer/header 제외. 페이지 수 비교는 신뢰 불가 (rhwp 부정확) |
| 조정 순위 | ① spacer → ② 줄간격 → ③ 여백 | **①→②→③** | 시각 영향 적은 순서. spacer는 "가독성을 위한 덤"이므로 먼저 제거 |
| 여백 하한 | (A) 법규 없음 / (B) 행정편람 권장 15/15/18/18 | **B** | 편람 준수 유지 |
| API 노출 | (A) 옵션 추가 / (B) 별도 메서드 | **A** | 기존 save() 호출 사이트 변경 불필요 |
| rhwp 실패 시 | (A) 예외 / (B) warn + 원본 반환 | **B** | 편집 파이프라인 중단 회피 |
| 테스트 기준 | (A) golden bytes / (B) "1페이지 이하" 판정 | **B** | golden은 의존성(rhwp 버전 등) 때문에 깨지기 쉬움 |

### 6.3 모듈 배치

```
pyhwpxlib/
├─ gongmun/
│  ├─ builder.py            (GongmunBuilder — autofit 옵션 추가)
│  └─ autofit.py            (신규: 감지 + 조정 루프)
├─ rhwp_bridge.py           (이미 get_page_render_tree 제공)
└─ tests/
   └─ test_gongmun_autofit.py (신규)
```

---

## 7. Convention Prerequisites

### 7.1 Existing Project Conventions

- [x] `pyproject.toml` — pytest markers (smoke/integration/regression/slow)
- [x] `pyhwpxlib/__init__.py` — `__version__` 동기화 규칙 (memory: feedback_version_sync)
- [x] 2타 들여쓰기, 편람 용어 준수 (gongmun 모듈)
- [ ] autofit 로그 포맷 — `logging.getLogger("pyhwpxlib.gongmun.autofit")`

### 7.2 Conventions to Define/Verify

| Category | Current | To Define | Priority |
|----------|---------|-----------|:--------:|
| **함수 네이밍** | snake_case 통일 | `_detect_overflow`, `_shrink_spacing` 등 prefix | High |
| **폴더 구조** | 기존 gongmun/ 유지 | autofit.py 단일 파일 | High |
| **에러 처리** | RhwpError 존재 | autofit 내부 예외는 삼키고 원본 반환 | High |
| **로깅** | NullHandler 설치 | DEBUG 레벨로 시도별 y+h 출력 | Medium |

### 7.3 Environment Variables Needed

해당 없음 (순수 라이브러리).

### 7.4 Pipeline Integration

9-phase Pipeline 사용 안 함. 단일 기능 추가이므로 PDCA 사이클만 적용.

---

## 8. Implementation Sketch

```python
# pyhwpxlib/gongmun/autofit.py (신규)
from ..rhwp_bridge import RhwpEngine, RhwpError

_MIN_MARGINS_MM = (15, 15, 18, 18, 0, 10)  # 상하좌우머꼬
_TOLERANCE_PX = 2.0

def fit_to_one_page(hwpx_path: str, builder, *, max_iters: int = 3) -> bool:
    """overflow 감지 → 조정 → 재저장. 성공 시 True."""
    for attempt in range(max_iters + 1):
        overflow = _measure_overflow(hwpx_path)
        if overflow <= _TOLERANCE_PX:
            return True
        if not _apply_shrink_step(builder, attempt, overflow):
            break
        builder._rebuild_and_save(hwpx_path)  # 기존 save 재호출
    return False

def _measure_overflow(path: str) -> float:
    try:
        engine = RhwpEngine()       # 싱글톤
        doc = engine.load(path)
        tree = doc.get_page_render_tree(0)
        body = _find_body_bbox(tree)
        last = _max_content_y(tree)
        return max(0.0, last - (body["y"] + body["h"]))
    except RhwpError:
        return 0.0   # 검증 스킵 (원본 유지)
```

---

## 9. Next Steps

1. [ ] `/pdca design compact-autofit` 로 상세 설계 작성
2. [ ] autofit.py 프로토타입 + 긴 본문 픽스처 생성
3. [ ] smoke + regression 테스트 추가
4. [ ] Task #12 완료 후 `/pdca analyze compact-autofit` 로 Gap 점검
5. [ ] 0.12.0 PyPI 배포 (release 단계)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-23 | 초안 작성 (Task #12 해결용) | Mindbuild |
