---
template: plan
version: 1.2
description: auto_schema cellSpan-aware lookup — makers overlap 34→70%
---

# auto-schema-cellspan Planning Document

> **Summary**: v0.13.3 auto_schema 가 cellSpan 을 무시하여 makers 양식의 반복 그리드(참여자 1~N) 헤더 라벨을 찾지 못하는 문제 해결. 0.13.4 patch.
>
> **Project**: pyhwpxlib
> **Version**: 0.13.3 → 0.13.4
> **Date**: 2026-04-29
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

v0.13.3 출시한 auto_schema 휴리스틱이 단일 필드(team_name/period/report_date)는
정확하지만 makers 의 **반복 그리드(참여자 4명 × 4필드 = 16개)** 에서 헤더 라벨
("성명/학과(부)/학번/서명")을 찾지 못해 `field_N` fallback 으로 떨어진다.

증상:
- 수동 schema: `member_1_name`, `member_1_dept`, `member_1_id`, `member_1_sign`, ...
- 자동 schema: `field_2`, `field_3`, ... (인덱스 fallback)
- **현재 overlap: 34%** (목표 70%)

### 1.2 Background

makers 표[0] 구조 (수동 schema 기준):
```
row=2 (header): | (1,0)? | 성명 | 학과(부)cs=2 | 학번cs=2 | 서명 |
row=3 (참여자1):| 참여자1 | (빈) | (빈)cs=2     | (빈)cs=2 | (빈) |
row=4 (참여자2):| 참여자2 | (빈) | (빈)cs=2     | (빈)cs=2 | (빈) |
```

`_find_label_for(value_cell=(3, 2))` 의 above_candidates lookup:
- 현재: `c["col"] == 2 and c["row"] < 3 and is_label`
- 헤더 "학과(부)" 의 cellAddr 이 col=2 이고 cellSpan colSpan=2 라면 col==2 매칭 OK
- 그러나 (3, 3) 또는 (3, 4) value 의 경우, 헤더 col 과 정확히 일치하지 않으면 미스

**가설**: 값 셀이 헤더의 cellSpan 범위 안에 있어도 strict col== 비교라 매칭 실패.

### 1.3 Related

- `pyhwpxlib/templates/auto_schema.py` (현재 구현)
- `skill/templates/makers_project_report.schema.json` (수동 ground truth)
- 직전 세션 기록: `memory/project_template_workflow_0_13_3.md`

---

## 2. Scope

### 2.1 In Scope

- [ ] makers 양식 진단: 실제 cell addr/span 덤프 → 어디서 lookup 깨지는지 확인
- [ ] `_find_label_for` cellSpan-aware: 헤더 col ≤ value col < header col + colSpan
- [ ] 반복 그리드 row label 결합: row label("참여자1") + col header("성명") → `member_1_name`
- [ ] makers overlap 측정 스크립트 (precision/recall vs 수동 schema)
- [ ] 회귀 12 + 신규 cellSpan-specific 테스트 ≥ 4
- [ ] PyPI 0.13.4 출시 + skill zip

### 2.2 Out of Scope

- 새 mapping table 추가 (현재 slugify mapping 으로 충분)
- 활동사진 12쌍 (표[1]) — placeholder 패턴은 별도 issue, 이번엔 표[0] 만
- AI 기반 schema 생성 (미래)
- HWP→HWPX 변환 자체 개선

---

## 3. Requirements

### 3.1 Functional

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | `_find_label_for` 가 헤더 cellSpan 범위 안에 들어가는 value 도 매칭 | High |
| FR-02 | 반복 그리드 감지 시 row label + col header 조합 key 생성 (`member_1_name`) | High |
| FR-03 | makers 자동 schema 의 표[0] field key 가 수동과 ≥ 70% 일치 (overlap) | High |
| FR-04 | 기존 단일 필드 정확도 회귀 없음 (team_name, period 등 100% 유지) | High |
| FR-05 | 진단 도구: `python -m pyhwpxlib.templates.diagnose <hwpx>` — 셀 덤프 + 자동 schema 비교 | Medium |

### 3.2 Non-Functional

| Category | Criteria |
|----------|----------|
| 회귀 | 0.13.3 의 45개 테스트 PASS 유지 |
| 한컴 호환 | 출력은 precise fix default (불변) |
| 성능 | makers 양식 분석 < 1초 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] makers 표[0] overlap precision ≥ 70% (현재 34%)
- [ ] member_1~4_name/dept/id/sign 16개 중 12개 이상 자동 매칭
- [ ] team_name, period, report_date 등 단일 필드는 100% 유지
- [ ] 회귀 45 + 신규 ≥ 4 PASS
- [ ] PyPI 0.13.4 + skill zip 0.13.4 출시

### 4.2 Quality

- [ ] cellSpan 처리 단위 테스트: header colSpan=2 가 두 값 모두 커버
- [ ] 진단 출력으로 어떤 필드가 어떤 라벨에 매칭되었는지 추적 가능

---

## 5. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| span-aware lookup이 단일 필드를 잘못 매칭 (over-match) | High | 회귀 테스트 + makers 단일 필드(team_name 등) 100% 유지 검증 |
| 반복 그리드 감지 휴리스틱이 다른 양식 깨뜨림 | Medium | makers 외 추가 fixture 1개 (예: 검수확인서) 회귀 비교 |
| row label("참여자1")이 row=N 에 같이 나오는 행이 한국어 양식마다 다름 | Medium | row label 후보를 col=0 + col<value_col 로 확장, 우선순위 명시 |

---

## 6. Architecture

### 6.1 핵심 변경 — `_find_label_for`

```python
def _find_label_for(value_cell, cells, *, prefer_header=True):
    row, col = value_cell["row"], value_cell["col"]

    # span-aware: 헤더가 colSpan으로 value col을 덮으면 매칭
    above_candidates = [
        c for c in cells
        if c["row"] < row
        and c["col"] <= col < c["col"] + c["cs"]   # ← 변경
        and _is_label(c["text"])
    ]
    left_candidates = [
        c for c in cells
        if c["col"] < col
        and c["row"] <= row < c["row"] + c["rs"]   # ← 변경 (rowSpan)
        and _is_label(c["text"])
    ]
    # 우선순위 그대로
```

### 6.2 반복 그리드 row label 결합

```python
def _row_label_for(value_cell, cells):
    """col=0 또는 col < value_col 인 라벨 셀에서 row group 라벨 추출."""
    row = value_cell["row"]
    candidates = [
        c for c in cells
        if c["col"] < value_cell["col"]
        and c["row"] <= row < c["row"] + c["rs"]
        and _is_label(c["text"])
    ]
    if candidates:
        return min(candidates, key=lambda c: c["col"])["text"]
    return None
```

repeated_grid 일 때:
```
key = slugify(row_label) + "_" + slugify(col_header)
   "참여자1" + "_" + "성명"  →  "member_1_name"
```

### 6.3 데이터 흐름

```
auto_schema.generate_schema(section_xml)
  ├─ tables 추출
  ├─ 각 table:
  │   ├─ cells 추출 (depth-aware, 변경 없음)
  │   ├─ _detect_repeated_grid → True/False
  │   ├─ if True: _find_label_for + _row_label_for 결합
  │   ├─ else: _find_label_for 단독
  │   └─ slugify (충돌 시 _2, _3)
  └─ return schema
```

---

## 7. Conventions

- `slugify` mapping에 신규 추가 시 ASCII snake_case 유지
- 진단 도구 출력은 stdout (json, text 두 모드)
- 기존 0.13.3 schema.json 호환 (필드 이름만 개선)

---

## 8. Next Steps

1. [ ] Phase 0: makers 셀 덤프 분석 (실제 row/col/cs/rs 확인)
2. [ ] Phase 1: `_find_label_for` cellSpan-aware 구현 + 단위 테스트
3. [ ] Phase 2: `_row_label_for` + repeated_grid 결합 로직
4. [ ] Phase 3: makers overlap 측정 (precision/recall)
5. [ ] Phase 4: 회귀 테스트 + diagnose CLI
6. [ ] Phase 5: PyPI 0.13.4 + skill zip 출시
7. [ ] Phase 6: 메모리 + MEMORY.md 갱신, archive plan

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-29 | Initial draft | Mindbuild + Claude |
