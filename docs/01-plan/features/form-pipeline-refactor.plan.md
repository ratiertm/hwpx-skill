# Plan: form-pipeline-refactor

## 개요
form_pipeline.py 서식 클론 파이프라인의 기능 완성 + 코드 품질 개선.
코드 리뷰 보고서(2026-04-05) 기반 리팩토링 + 미해결 3가지 기능 구현.

## 배경
- 22커밋으로 단일/다중 페이지 서식 클론 달성
- 코드 리뷰: HIGH 6건, MEDIUM 10건, LOW 8건
- 미해결: 줄바꿈, textColor, 부분 스타일 (body 텍스트 run 단위)

## Phase 1: 기능 완성 (body 텍스트 multi-run) — 우선순위 최고

### 1-1. body 텍스트 run 단위 charPr 보존
- **문제**: `add_paragraph(text)` → p당 1 run만 생성, 원본은 다중 run
- **원인**: `_generate_from_paragraphs`의 텍스트 p 생성 (line 827~847)
- **해결**: 셀과 동일하게 직접 p/run XML 구성
- **효과**: textColor + 부분 스타일 + 줄바꿈 3가지 동시 해결

### 1-2. 구현 상세
```python
# 현재 (body 텍스트)
doc.add_paragraph(text, char_pr_id_ref=default_cpr)  # 1 run만

# 변경 → 직접 p/run 구성
new_p = SubElement(section_el, "hp:p")
for run_data in para_data['runs']:
    for content in run_data['contents']:
        if content['type'] == 'text':
            new_run = SubElement(new_p, "hp:run")
            new_run.set("charPrIDRef", str(cpr_map[run_data['charPrIDRef']]))
            t = SubElement(new_run, "hp:t")
            t.text = content['text']
```

### 1-3. 검증
- 녹색환경지원센터 서식: 줄바꿈 없음 + 폰트 색깔 + 부분 스타일
- 별지11호: 기존 정상 동작 유지 (regression)
- 20250224 다중 페이지: 기존 정상 동작 유지

## Phase 2: 안정성 개선 — HIGH 이슈 해결

### 2-1. except Exception: pass → 구체적 예외 + 로깅 (21건)
- form_pipeline.py 7건
- html_to_hwpx.py 11건
- html_converter.py 3건

### 2-2. .find() 후 None 체크 (12건)
- form_pipeline.py에서 `.find()` → `.set()` 패턴

### 2-3. 임시 파일 → TemporaryDirectory
- form_pipeline.py의 `tempfile.mktemp` → `tempfile.TemporaryDirectory`

## Phase 3: 구조 개선

### 3-1. api.py _init_para() 헬퍼 추출
- 12곳 반복 → 1곳, 78줄 감소

### 3-2. form_pipeline.py 함수 분리
- `_generate_table()` 220줄 → 5개 함수로 분리
  - `_setup_table_structure()`
  - `_populate_cells()`
  - `_apply_merges()`
  - `_apply_styles()`
  - `_generate_nested_tables()`

### 3-3. 구 데이터 모델 제거
- `tables` + `before_table_text` (구) → `paragraphs` (신)으로 통합

### 3-4. 매직 넘버 → 명명 상수
```python
class Defaults:
    PAGE_WIDTH = 59528      # A4 가로 (1/7200 inch)
    PAGE_HEIGHT = 84188     # A4 세로
    CELL_MARGIN = 141       # 셀 기본 마진
    ROW_HEIGHT = 3600       # 행 기본 높이
    NESTED_OUT_MARGIN = 283 # 중첩 표 바깥 마진
    NESTED_IN_MARGIN = 510  # 중첩 표 안쪽 마진
```

## Phase 4: 테스트

### 4-1. _reverse_grid() 단위 테스트
### 4-2. form_pipeline 라운드트립 통합 테스트
### 4-3. 서식 클론 시각 검증 자동화

## 우선순위

| Phase | 예상 시간 | 우선순위 |
|-------|----------|---------|
| Phase 1 (기능 완성) | 2~3시간 | ⭐ 최우선 |
| Phase 2 (안정성) | 1~2일 | 높음 |
| Phase 3 (구조) | 2~3일 | 중간 |
| Phase 4 (테스트) | 2일 | 낮음 |

## 성공 기준
- [ ] 녹색환경 서식 클론: 줄바꿈 정확, 폰트 색깔 보존, 부분 스타일 보존
- [ ] 기존 서식 (별지11호, SAMPLE1/2, 20250224) regression 없음
- [ ] except Exception: pass 0건
- [ ] .find() 후 None 체크 100%
- [ ] 장함수 50줄 이하
