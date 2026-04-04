# Plan: form-pipeline-refactor (v2)

## 개요
form_pipeline.py 서식 클론 파이프라인의 기능 완성 + 코드 품질 개선.
코드 리뷰 보고서(2026-04-05) 기반 리팩토링 + 미해결 기능 구현.
**각 Phase별 테스트 필수.**

## 배경
- 22커밋으로 단일/다중 페이지 서식 클론 달성
- 코드 리뷰: HIGH 6건, MEDIUM 10건, LOW 8건
- 미해결: 줄바꿈, textColor, 부분 스타일 (body 텍스트 run 단위)
- 이미 완료 확인: 코드 블록 ✅, 중첩 목록 ✅, MD→HWPX ✅

---

## Phase 1: 기능 완성 + 테스트 (최우선)

### 1-1. body 텍스트 multi-run 구성
- **문제**: `add_paragraph(text)` → p당 1 run만 생성, 원본은 다중 run
- **원인**: `_generate_from_paragraphs`의 텍스트 p 생성 (line 827~847)
- **해결**: 셀과 동일하게 직접 p/run XML 구성
- **효과**: textColor + 부분 스타일 + 줄바꿈 3가지 동시 해결

### 1-T. 테스트 (tests/test_form_pipeline_multirun.py)
- 녹색환경 서식: 줄바꿈 정확 + 폰트 색깔 + 부분 스타일
- 별지11호/SAMPLE/20250224 regression
- 단일 run / 다중 run / 빈 텍스트 edge case

**완료 조건**: 구현 + 테스트 전체 통과

---

## Phase 2: 안정성 개선 + 테스트

### 2-1. except Exception: pass → 구체적 예외 + logging
- form_pipeline.py 14건 (10 Exception + 4 bare except)
- html_to_hwpx.py 11건
- html_converter.py 3건

### 2-2. .find() 후 None 체크 (12건 재확인)
### 2-3. tempfile.mktemp → TemporaryDirectory (form_pipeline.py:712)

### 2-T. 테스트 (tests/test_stability.py)
- 잘못된 입력 시 구체적 예외 발생 확인
- None 반환 시 graceful 처리 확인
- TemporaryDirectory 정리 확인
- 기존 329개 테스트 regression 없음

**완료 조건**: except Exception 0건 + 테스트 전체 통과

---

## Phase 3: 구조 개선 + 테스트

### 3-1. _init_para() 헬퍼 추출 (api.py 18곳 → 1곳)
### 3-2. 매직 넘버 → Defaults 상수 클래스
### 3-3. 구 데이터 모델 제거 (paragraphs로 통합)
### 3-4. _generate_table() 220줄 → 5개 서브 함수 분리

### 3-T. 테스트 (tests/test_refactor.py)
- _init_para() 단위 테스트 (필드 값 검증)
- Defaults 상수 사용 확인
- _reverse_grid() colspan/rowspan edge case
- 분리된 함수별 단위 테스트
- 전체 regression (기존 서식 클론 동작)

**완료 조건**: 리팩토링 + 테스트 전체 통과

---

## 제외 (scope 밖)
- CLI clone 통합, upstream PR → Phase 1~3 완료 후 별도 PDCA
- HWP 5.x → scope 밖
- XML regex→ElementTree, 타입 힌트 → 후순위

## 실행 순서
```
Phase 1 (기능+테스트) → Phase 2 (안정성+테스트) → Phase 3 (구조+테스트)
         │                      │                       │
         └── PDCA analyze ──────└── PDCA analyze ───────└── PDCA analyze → report
```

## 핵심 파일
- templates/form_pipeline.py (1,307줄) — Phase 1~3 모두
- pyhwpxlib/api.py (2,112줄) — Phase 3
- pyhwpxlib/html_to_hwpx.py (941줄) — Phase 2
- pyhwpxlib/html_converter.py (797줄) — Phase 2

## 성공 기준
- [ ] 녹색환경 서식 클론: 줄바꿈 정확, 폰트 색깔 보존, 부분 스타일 보존
- [ ] 기존 서식 regression 없음
- [ ] except Exception: pass 0건
- [ ] .find() 후 None 체크 100%
- [ ] 각 Phase 테스트 전체 통과
