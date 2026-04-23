---
template: analysis
feature: compact-autofit
date: 2026-04-23
author: gap-detector (bkit)
design_doc: ../02-design/features/compact-autofit.design.md
match_rate: 88
---

# compact-autofit — Gap Analysis (PDCA Check)

**Match Rate: 88%** (⚠️ Minor revisions recommended — 90% 기준 미달, 단 구현 수정 없이 Design bump로 해소 가능)

| Category | Score |
|----------|:-----:|
| Functional Requirements (FR-01~06) | 100% |
| Design §3 Data Model / Constants | 95% |
| Design §4 API Contract | 90% |
| Design §5 Algorithm | **75%** |
| Design §6 Error Handling | 95% |
| Design §7 Test Plan (T-01~T-06) | **67%** |
| Design §8 Implementation Strategy | 100% |
| Design §9 Open Questions | 100% |

---

## 1. FR Verification — 6/6 완전 구현

| ID | Requirement | Evidence | ✓ |
|----|-------------|----------|:-:|
| FR-01 | autofit 옵션 (기본 False) | `builder.py:70, 90` | ✅ |
| FR-02 | save 직후 RenderTree 판정 | `builder.py:101-103 → autofit.py:86-118` | ✅ |
| FR-03 | spacer/줄간격/여백 순, 최대 3회 | `autofit.py:56-79` | ✅ |
| FR-04 | 시도별 DEBUG 로그 | `autofit.py:52, 70` | ✅ |
| FR-05 | 실패 시 WARN + 산출물 유지 | `autofit.py:58-63, 74-78` | ✅ |
| FR-06 | autofit=False 성능 영향 0 | `builder.py:101` (`if self.autofit:` 가드) | ✅ |

## 2. Open Questions 반영 — 4/4 완전 반영

| Q | 결정 | 구현 | ✓ |
|:-:|------|------|:-:|
| Q1 | Body = root 직접 자식 | `autofit.py:121-126` | ✅ |
| Q2 | lineSpacing 비례 축소 + 120 하한 | `builder.py:141-149` | ✅ |
| Q3 | step 3 제거 | `_apply_shrink_step` 0~2만 | ✅ |
| Q4 | XML id 정규화 해시 | `tests:_canonical_hash` | ✅ |

---

## 3. Top 3 Gaps (심각도 순)

### Gap #1 [H] — overflow 측정 알고리즘 Design §5.1 미반영

**Design §5.1**:
```python
tree = doc.get_page_render_tree(0)                 # page 0만
return max(0, content_end - (body.y + body.h))
```

**실제 구현** (`autofit.py:86-118`):
```python
pc = doc.page_count
if pc <= 1: return 0.0
last_tree = doc.get_page_render_tree(pc - 1)       # 마지막 페이지
return last_content + (pc - 2) * body_h
```

**사유**: rhwp는 auto-paginator. page 0 내 좌표는 항상 body bbox 안에 맞춰진다. Design §5.1의 "단일 페이지에서 넘친 좌표를 그대로 반환"은 **잘못된 전제**.

**권고**: Design v0.3으로 §5.1 재작성 + Q5 신설 (실증 결과 문서화). 구현 수정 **불요**.

### Gap #2 [M] — step 1 하한 판정 기준 불일치

**Design §3.2**: "모든 값 ≥ 120"
**실제 구현** (`autofit.py:29, 170`): `_BODY_DEFAULT_LINE_SPACING(=160) * new_ratio < 120` 고정 비교

**영향**:
- Design 문구대로라면 최소값(130) 기준 → `130 × 0.90 = 117 < 120` → **1회에 하한 도달, step 1 거의 무용**
- 구현: 160 기준 → 2회까지 축소, post-save `max(120, …)` 클램프가 안전망

**권고**: Design §3.2 step 1 조건을 다음으로 수정:
> "본문 기본 (160%) × 누적 ratio ≥ 120. 표·제목 등 작은 값은 post-save 단계에서 120 클램프로 보호."

구현은 실용적으로 더 우수하므로 유지.

### Gap #3 [M] — T-04 (WASM 부재) 테스트 생략

`pytest.importorskip("wasmtime")`으로 환경 스킵만 수행. Design이 요구한 "원본 유지 + WARN 없음 + DEBUG만" 시나리오 명시 검증 부재.

**권고**: `sys.modules` monkeypatch로 import 실패 시뮬레이션 추가 → 테스트 1건 보강.

---

## 4. Minor Findings

### 🟡 Added (Design에 없던 구현)
- `_build_and_save_once` 메서드 추출 (`builder.py:106-120`) — Design §6.2는 `save()`에 한 줄 추가만 명시. 기능 동일 [L]
- `_BODY_DEFAULT_LINE_SPACING` 상수 (`autofit.py:29`) — Design §3.1 상수 목록에 없음 [L]

### 🟣 Differences
- Design §4.3 "예외 시 False 반환" — 구현은 `_measure_overflow`가 0.0 반환 → 루프가 True로 조기 탈출. 외부 불가관이라 실질 영향 없음 [L]
- `_all_extents`는 재귀 DFS, Design 의사코드는 단층처럼 읽힘 [L]

---

## 5. Recommended Act

### A안 (권장): Design v0.3 bump — 구현 수정 없이 문서 동기화
1. §5.1 overflow 측정을 page_count 기반으로 재작성
2. §9에 Q5 추가: "rhwp auto-paginator 실증 결과"
3. §3.2 step 1 조건 완화 (본문 160 기준 + post-save 클램프)
4. §4.3 "예외 시 True + overflow=0 평가" 로 명확화
5. 테스트 T-04 보강 (monkeypatch 기반)

### B안 (선택): 구현 정렬 — Design v0.2를 진리로 취급
1. `_line_spacing_effective_min` 헬퍼 추가하여 5.3 의사코드와 1:1
2. `_measure_overflow` 예외 경로를 `-1.0` sentinel로 바꿔 False 반환 계약 준수

**A안이 더 저비용이고 실증 결과를 문서에 축적하는 가치가 있다.**

---

## 6. Act Decision

- 90% 미달이지만 **구현은 모두 실증 기반 정당한 선택**. 
- `/pdca iterate` 를 **Design 문서 수정** 작업으로 한정하여 실행 권장 (코드 변경 X).
- iterate 1회 후 재측정하면 Match Rate ≥ 95% 예상.

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-23 | gap-detector Agent 1차 분석 (Match 88%) | bkit:gap-detector |
| 0.2 | 2026-04-23 | Act-1 반영 후 재평가: **Match 97%** — Design v0.3 (Q5 추가, §5.1/§3.2/§4.3 정렬) + T-04 테스트 추가 | Mindbuild |

---

## Iteration History

### Act-1 (2026-04-23) — A안 적용

**변경사항**:
- Design v0.3 bump: §5.1 page_count 기반 재작성, §9 Q5 신설, §3.2 step 1 조건 명확화, §4.3 예외 반환 True 명시
- 테스트 추가: `test_autofit_soft_skip_when_rhwp_unavailable` (T-04) — `_get_engine` monkeypatch 기반 WASM 부재 시뮬레이션

**재측정**:
| Category | Before | After |
|----------|:-----:|:-----:|
| Design §5 Algorithm | 75% | **100%** (§5.1 재작성 완료) |
| Design §7 Test Plan | 67% | **100%** (T-04 추가) |
| Overall | **88%** | **97%** |

**잔여 Gap** (모두 Low):
- `_build_and_save_once` 메서드 추출이 Design §6.2 에 명시되지 않음 (기능 동일)
- `_line_spacing_effective_min` 헬퍼 대신 inline 상수 (§3.2 완화로 해소됨)

**결론**: 90% 기준 초과 달성. **Report 단계 진입 가능**.
