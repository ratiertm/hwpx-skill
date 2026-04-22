---
template: design
version: 1.2
feature: compact-autofit
date: 2026-04-23
author: Mindbuild
project: pyhwpxlib
version_proj: 0.11.0
status: Draft
planning_doc: ../01-plan/features/compact-autofit.plan.md
---

# compact-autofit Design Document

> **Summary**: `GongmunBuilder.save()` 직후 rhwp RenderTree로 overflow를 측정하고, 우선순위 기반 shrink step을 반복 적용해 공문을 1페이지에 맞춘다.
>
> **Project**: pyhwpxlib
> **Version**: 0.11.0 → 0.12.0
> **Author**: Mindbuild
> **Date**: 2026-04-23
> **Status**: Draft
> **Planning Doc**: [compact-autofit.plan.md](../01-plan/features/compact-autofit.plan.md)

### Pipeline References

| Phase | Document | Status |
|-------|----------|--------|
| Phase 1 Schema | — | N/A |
| Phase 2 Convention | memory/feedback_version_sync.md | ✅ (existing) |

---

## 1. Overview

### 1.1 Design Goals

- Plan의 FR-01~06을 순수 Python·옵트인 방식으로 구현한다.
- autofit=False 경로의 코드 패스는 **불변** (golden 호환 유지).
- 단일 책임 파일 1개(`autofit.py`) + 최소 침습 옵션 1개(`GongmunBuilder.autofit`).
- rhwp 실패(WASM 로드 에러 등) 시 기능을 **조용히 스킵** — 편집 파이프라인 중단 금지.

### 1.2 Design Principles

- **YAGNI**: 여러 페이지 공문·첨부물 autofit은 미래 과제 (Out of Scope).
- **Observable**: 각 시도의 Y좌표/적용 파라미터를 DEBUG 로그로 남겨 재현성 확보.
- **Fail-soft**: 측정 실패 시 0을 반환해 원본 그대로 보존.
- **Idempotent**: autofit이 이미 1페이지이면 추가 빌드 없이 즉시 종료.

---

## 2. Architecture

### 2.1 Component Diagram

```
┌──────────────────────┐
│ GongmunBuilder.save() │
│  (기존 로직)           │
└──────────┬───────────┘
           │ out 경로
           ▼
┌──────────────────────┐   autofit=True 시에만
│  autofit.fit_to_one_page()    │
│  - measure (RhwpEngine)       │
│  - decide shrink step         │
│  - mutate builder config      │
│  - re-save                    │
└──────────┬───────────┘
           │ 성공/실패
           ▼
     반환 (out 경로)
```

### 2.2 Data Flow

```
  1. save(path)  — 첫 저장
  2. RhwpEngine.load(path) → doc.get_page_render_tree(0)
  3. body_bbox = 첫 depth-1 child of type=Body
  4. content_y_end = max(child.y + child.h)
  5. overflow = max(0, content_y_end - (body.y + body.h))
  6. overflow <= tolerance → done
  7. else → apply shrink step N → goto 1
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| `gongmun.autofit` | `rhwp_bridge.RhwpEngine` | RenderTree 취득 |
| `gongmun.autofit` | `gongmun.builder.GongmunBuilder` (self) | shrink 파라미터 mutate |
| `GongmunBuilder.save` | `gongmun.autofit.fit_to_one_page` | 옵션 활성 시 위임 |
| Test | `pytest`, `wasmtime` (importorskip) | smoke + regression |

> RhwpEngine 은 싱글톤 캐시(`_ENGINE_CACHE`)로 재사용해 WASM 재초기화 비용 회피.

---

## 3. Data Model

### 3.1 신규 상수

```python
# autofit.py
_TOLERANCE_PX = 2.0              # rhwp linesegarray 오차 허용
_MAX_ITERATIONS = 3              # 스텝 0·1·2 → 최대 3회 재빌드
_MIN_MARGINS_TB_MM = 12          # 상/하 여백 하한 (Q3)
_LINE_SPACING_MIN = 120          # lineSpacing value 하한 (Q2)
_LINE_SPACING_RATIO = 0.90       # 비례 축소 계수 (Q2)
_SPACER_FONT_SIZE_MIN = 4        # 빈 줄 pt 하한
```

### 3.2 Shrink Step 정의 (Q1~Q3 실증 반영)

| Step | 조작 대상 | 1회 감소량 | 하한 |
|:----:|-----------|-----------|------|
| 0 | `self._spacer_pt` | −2pt | `_SPACER_FONT_SIZE_MIN` (=4) |
| 1 | 전역 `lineSpacing value` **×0.90 비례 축소** (Q2) | × 0.90 | 모든 값 ≥ 120 |
| 2 | `self.margins_mm` 의 상/하 | −2mm 씩 | **12mm** (Q3에 따라 완화) |

> step 3 (compact 강제)은 **제거**. 사용자의 `compact=False` 를 autofit이 뒤집지 않음 (Q3 결정).
> 실패 시 WARN 로그에 **구체 제안** 포함:
> `"autofit 실패 (overflow=XX px). compact=True 또는 본문 축소를 검토하세요."`

### 3.3 Builder Config Hooks

`GongmunBuilder`에 다음 속성을 신설 (기본값은 현행 동작과 동일):

```python
# builder.py __init__ 에 추가
self.autofit: bool = autofit
self._spacer_pt: int = 6          # 본문 사이 빈 줄 pt
self._line_spacing_pct: int = 160 # 기본 줄간격 %
```

기존 `add_paragraph("", font_size=6)` 호출부를 `add_paragraph("", font_size=self._spacer_pt)`로 치환.
`_line_spacing_pct`는 paraPr의 linespacing 속성으로 post-save XML 치환(기존 `_apply_margins` 패턴 재사용).

---

## 4. API Specification

### 4.1 신규 API

```python
# 사용자 가시 API
GongmunBuilder(
    data,
    *,
    theme="default",
    항목간_공백=True,
    compact=False,
    margins_mm=(20, 15, 20, 20, 0, 10),
    autofit=False,          # ← 신규 (기본 False)
)
```

### 4.2 내부 API

```python
# pyhwpxlib/gongmun/autofit.py (신규)

def fit_to_one_page(
    hwpx_path: str,
    builder: "GongmunBuilder",
    *,
    max_iters: int = 3,
    tolerance_px: float = 2.0,
) -> bool:
    """overflow를 감지해 shrink step을 순차 적용. 성공 시 True, 실패 시 False."""


def _measure_overflow(hwpx_path: str) -> float:
    """첫 페이지 body bbox 기준 overflow(px). 측정 실패 시 0.0."""


def _apply_shrink_step(builder, step_idx: int) -> bool:
    """step_idx에 해당하는 조정 1회 적용. 하한 도달 시 False."""


def _rebuild_and_save(builder, hwpx_path: str) -> None:
    """builder 상태를 초기화하고 재저장. _builder도 새로 만든다."""
```

### 4.3 Return Contract

- `fit_to_one_page` 성공: `True` + 최종 hwpx 파일에 조정 반영됨
- 모든 스텝 소진 후에도 overflow: `False` + `logger.warning(...)` + 마지막 산출물 유지
- RhwpEngine 예외: `False` + `logger.debug("autofit skipped", exc_info=True)` + 원본 유지

---

## 5. Algorithm Detail

### 5.1 Overflow 측정 함수

```python
def _measure_overflow(hwpx_path: str) -> float:
    try:
        engine = _get_engine()            # 싱글톤
        doc = engine.load(hwpx_path)
        try:
            tree = doc.get_page_render_tree(0)
            body = _find_body_node(tree)
            if body is None:
                return 0.0
            content_end = _max_y_extent(tree, exclude={"Header", "Footer", "PageBg"})
            limit = body["bbox"]["y"] + body["bbox"]["h"]
            return max(0.0, content_end - limit)
        finally:
            doc.close()
    except Exception:
        logger.debug("overflow measure failed", exc_info=True)
        return 0.0
```

`_find_body_node` 는 DFS로 `type == "Body"` 탐색.
`_max_y_extent` 는 자식 중 type이 exclude 셋에 포함되지 않는 것들의 `y + h` 최댓값.

### 5.2 메인 루프

```python
def fit_to_one_page(hwpx_path, builder, *, max_iters=3, tolerance_px=2.0):
    for step in range(max_iters + 1):
        overflow = _measure_overflow(hwpx_path)
        logger.debug("autofit step=%d overflow=%.1fpx", step, overflow)
        if overflow <= tolerance_px:
            return True
        if step == max_iters:
            break
        if not _apply_shrink_step(builder, step):
            logger.warning("autofit gave up at step %d (lower bound)", step)
            return False
        _rebuild_and_save(builder, hwpx_path)
    logger.warning("autofit failed: overflow=%.1fpx after %d steps",
                   overflow, max_iters)
    return False
```

### 5.3 Shrink Step 구현

```python
def _apply_shrink_step(builder, step_idx: int) -> bool:
    if step_idx == 0:
        new_pt = builder._spacer_pt - 2
        if new_pt < _SPACER_FONT_SIZE_MIN: return False
        builder._spacer_pt = new_pt
        return True
    if step_idx == 1:
        # Q2: lineSpacing 3종 혼재 (160/150/130) → 비례 축소
        # 실제 치환은 _rebuild_and_save 이후 post-save XML 단계에서 수행
        new_ratio = builder._line_spacing_ratio * _LINE_SPACING_RATIO
        if builder._line_spacing_effective_min(new_ratio) < _LINE_SPACING_MIN:
            return False
        builder._line_spacing_ratio = new_ratio
        return True
    if step_idx == 2:
        t, b, l, r, h, f = builder.margins_mm
        if t <= _MIN_MARGINS_TB_MM and b <= _MIN_MARGINS_TB_MM:
            return False
        builder.margins_mm = (max(t - 2, _MIN_MARGINS_TB_MM),
                              max(b - 2, _MIN_MARGINS_TB_MM),
                              l, r, h, f)
        return True
    return False
```

---

## 6. Error Handling

### 6.1 Error 경로

| 상황 | 동작 | 로그 레벨 |
|------|------|-----------|
| WASM 로드 실패 | autofit 스킵, 원본 유지 | DEBUG |
| RenderTree JSON 파싱 실패 | autofit 스킵 | DEBUG |
| 하한 도달 후에도 overflow | 마지막 산출물 유지 + WARN | WARNING |
| `GongmunBuilder.save()` 내부 예외 | 전파 (사용자 에러) | — |

### 6.2 autofit=False 경로 보장

`GongmunBuilder.save()` 에 한 줄 분기만 추가:

```python
def save(self, output_path):
    # ... 기존 로직 그대로 ...
    out = self._builder.save(str(output_path))
    self._apply_margins(out)
    if isinstance(self.data, Gongmun):
        self._apply_license(out)
    if self.autofit:                       # ← 추가 한 줄
        from .autofit import fit_to_one_page
        fit_to_one_page(out, self)
    return out
```

`autofit=False`면 기존 golden 파일과 **바이트 단위 동일** 해야 한다 (회귀 테스트로 보장).

---

## 7. Test Plan

### 7.1 Test Scope

- 단위: `_measure_overflow`, `_apply_shrink_step` 경계값
- 통합: `GongmunBuilder(autofit=True).save()` 왕복
- 회귀: 기존 `gongmun_sample.hwpx` / `롯데이노베이트_*.hwpx` 재생성 바이트 일치 (autofit=False)

### 7.2 Key Test Cases (Q4 반영)

| ID | 시나리오 | 기대 결과 |
|----|---------|----------|
| T-01 | 짧은 본문 2항목, autofit=True | 0 스텝에 fit, overflow=0, 재빌드 없음 |
| T-02 | 긴 본문 8항목 + 결문, autofit=True | ≤3 스텝 내 1페이지 수렴 |
| T-03 | autofit=False 기본 동작 | `extract_text()` 동일 + XML id 정규화 해시 일치 (Q4: 바이트 일치 불가 — `<hp:p id>`가 전역 카운터) |
| T-04 | WASM 없음 (wasmtime 없는 환경 시뮬레이션) | 원본 유지, WARN 없음 (DEBUG 로그만) |
| T-05 | 스텝 하한 도달해도 fit 안 됨 | `fit=False` 반환, WARN 로그 1건 (compact=True 제안 포함), 파일은 마지막 조정본 유지 |
| T-06 | 사용자 `compact=True` 명시 + 긴 본문 | autofit은 step 0~2만 시도, compact 설정은 유지 |

**T-03 구현 메모** (Q4):
```python
def _normalize_xml(xml: str) -> str:
    return re.sub(r' id="\d+"', ' id="X"', xml)

def _canonical_hash(hwpx_path: str) -> str:
    with zipfile.ZipFile(hwpx_path) as z:
        parts = [_normalize_xml(z.read(n).decode('utf-8'))
                 for n in sorted(z.namelist()) if n.endswith('.xml')]
    return hashlib.sha256('\n---\n'.join(parts).encode()).hexdigest()
```

### 7.3 Fixtures

```
tests/fixtures/gongmun_long.py   # 항목 8개 + 각 서브항목 2줄 + 붙임 3건
tests/fixtures/gongmun_short.py  # 기존 gongmun_sample 내용 그대로
```

---

## 8. Implementation Guide

### 8.1 File Structure

```
pyhwpxlib/
├─ gongmun/
│  ├─ __init__.py              (no change)
│  ├─ builder.py               (MODIFY: +autofit 옵션, +self._spacer_pt 등, +save 분기)
│  ├─ autofit.py               (NEW)
│  └─ rules.yaml               (no change)
tests/
├─ test_gongmun_autofit.py     (NEW)
└─ fixtures/
   ├─ __init__.py              (NEW)
   ├─ gongmun_long.py          (NEW)
   └─ gongmun_short.py         (NEW)
```

### 8.2 Implementation Order

1. **builder.py**: `autofit`, `_spacer_pt`, `_line_spacing_pct` 속성 추가 (기본값만, 동작 불변)
2. **builder.py**: 모든 `font_size=6` spacer 호출부를 `font_size=self._spacer_pt` 로 치환
3. **회귀 테스트 선행**: autofit=False 경로가 기존 golden과 동일한지 확인
4. **autofit.py**: `_measure_overflow` 구현 + 단위 테스트
5. **autofit.py**: `_apply_shrink_step` 구현 + 경계값 테스트
6. **autofit.py**: `fit_to_one_page` 메인 루프 + 통합 테스트 T-01~T-06
7. **builder.py**: `save()` 마지막에 autofit 분기 추가
8. **문서**: README_KO에 `autofit` 옵션 예시 추가
9. **버전 bump**: 0.11.0 → 0.12.0 (pyproject + __init__.py)

### 8.3 재저장 (_rebuild_and_save) 전략

가장 큰 설계 질문 — "builder 상태를 어떻게 리셋해서 다시 save 하는가?"

옵션 A) **Fresh builder**: `self._builder = HwpxBuilder(theme=...)` 로 재생성 후 `_build_general` 재실행. 간단하지만 theme 객체 재로딩 비용.

옵션 B) **파라미터만 바꾸고 XML 후처리 재적용**: save 는 1회만 하고, `_apply_margins` / spacer 치환을 재적용. 빠르지만 spacer font_size 후처리가 복잡 (본문 XML 전체 재작성 필요).

**선택: A**. 이유:
- 코드가 명료 (mutate → save 반복)
- HwpxBuilder 초기화 비용은 수 ms 수준
- B는 "새 줄간격 적용"을 spacer가 아닌 실제 문단 linespacing에 반영해야 해서 XML 작업이 커짐

### 8.4 로깅

```python
# autofit.py 상단
import logging
logger = logging.getLogger(__name__)   # pyhwpxlib.gongmun.autofit
```

기본 로깅 핸들러는 pyhwpxlib 패키지의 NullHandler가 흡수 → 사용자가 명시적으로 DEBUG를 켜야 출력.

---

## 9. Open Questions (2026-04-23 실증 완료)

| # | 질문 | 실증 결과 / 최종 결정 |
|---|-----|----------------------|
| Q1 | Body bbox 구조 | ✅ **해결** — root children 중 `type=="Body"` 존재. 직접 자식 순회만으로 충분. Body y+h = Footer 직전 좌표와 일치 (e.g. 75.6+952.4=1028.0) |
| Q2 | lineSpacing 치환 전략 | ⚠ **해결 (보정)** — header.xml에 lineSpacing 요소 25개, **160/150/130% 3종 혼재**. 단일 값 replace 불가 → **정규식으로 모든 value를 ×0.90 비례 축소**. 하한 120 |
| Q3 | step 3 (compact 강제) 정책 | ✅ **해결 — 제거** — 사용자 명시값 존중. 대신 step 2 하한을 15→12mm로 완화. 실패 시 WARN에 compact=True 제안 |
| Q4 | 회귀 "바이트 일치" 가능성 | ⚠ **해결 (변경)** — 바이트 일치 **불가** (`<hp:p id>` 가 전역 카운터로 실행마다 증가). 대안: ① `extract_text()` 동등성 ② XML id 정규화 후 SHA256 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-23 | 초안 작성 (Plan 기반 algorithm 상세화) | Mindbuild |
| 0.2 | 2026-04-23 | Q1~Q4 실증 반영: step 3 제거, lineSpacing 비례 축소, 회귀는 XML 정규화 해시 | Mindbuild |
