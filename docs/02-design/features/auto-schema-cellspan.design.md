---
template: design
version: 1.2
description: auto_schema 반복 그리드 감지 + 행/열 라벨 결합 (0.13.4)
---

# auto-schema-cellspan Design Document

> **Summary**: makers 양식 셀 덤프 진단 결과, 진짜 병목은 cellSpan 미적용이 아니라 `_detect_repeated_grid` 의 over-strict 동작과 행 그룹 라벨 미사용. 본 설계는 두 문제를 함께 해결하면서 cellSpan-aware lookup 도 보조 개선으로 포함.
>
> **Project**: pyhwpxlib
> **Version**: 0.13.3 → 0.13.4
> **Date**: 2026-04-29
> **Status**: Draft
> **Planning Doc**: [auto-schema-cellspan.plan.md](../../01-plan/features/auto-schema-cellspan.plan.md)

---

## 1. Overview

### 1.1 Design Goals

makers 표[0] (11×7) 의 16개 참여자 value 셀을 `member_N_{name|dept|id|sign}` 형태로 자동 매핑하여 수동 schema 와 ≥70% overlap 달성. 단일 필드 (team_name, project_name, period, report_date) 는 100% 유지.

### 1.2 Design Principles

- **진단 우선**: 가설 검증 후 설계 (Phase 0 셀 덤프로 실제 구조 파악)
- **최소 변경**: 기존 0.13.3 휴리스틱 회귀 없이 추가 로직 도입
- **명시적 fallback**: 자동 추론 실패 시 generic key 로 안전 분기 (사용자 schema.json 직접 편집 가능)

### 1.3 진단 결과 (Phase 0 완료)

makers 표[0] 실제 cellAddr/Span:

```
r=0  (0..6, cs=7)   "전정Makers프로젝트 ... 결과보고"        ← title
r=1  c=0            "팀 명"                                  ← label
     c=1 cs=6       (empty)                                  ← team_name
r=2  c=0            "구  분"
     c=1            "성  명"        ← header                  ← name
     c=2 cs=2       "학  과(부)"    ← header                  ← dept
     c=4 cs=2       "학  번"        ← header                  ← id
     c=6            "서  명"        ← header                  ← sign
r=3  c=0 rs=4       "참 여 자"      ← row group (rs=4!)
     c=1            (empty)         ← member_1_name
     c=2 cs=2       (empty)         ← member_1_dept
     c=4 cs=2       (empty)         ← member_1_id
     c=6            (empty)         ← member_1_sign
r=4  ... (member_2)
r=5  ... (member_3)
r=6  ... (member_4)
r=7  c=0  "프로젝트명" + c=1 cs=6 (empty)
r=8  c=0  "활동기간" + c=1 cs=2 (placeholder) + c=3 cs=2 "최종보고서류 작성일" + c=5 cs=2 (placeholder)
r=9, r=10  notice text spans (cs=7)
```

### 1.4 진짜 병목 (가설 수정)

**가설 (Plan 시점)**: cellSpan 무시로 헤더 라벨이 above_candidates 진입 못 함.

**진단 후 정정**: 실제로는 strict `col ==` 비교에서도 헤더가 매칭됨. 진짜 문제는:

1. **`_detect_repeated_grid` over-strict**: 표 전체 rows 의 common 컬럼 교집합으로 판정.
   - 행 1, 7, 8 (단일 col 또는 cs 큰 row) 이 grid 행과 섞여 있어 common = {1} 만 남음 → grid 미감지
   - 결과: `prefer_header=False` → left_candidates 우선 → row group "참 여 자" 매칭 → 모든 4행이 같은 라벨 → name/name_2/name_3/name_4 (참고로 "참 여 자"는 mapping 없어 generic field_N으로 떨어질 수도)

2. **row group label 무활용**: `rs=4` 인 (3, 0) "참 여 자" 같은 행 그룹 라벨이 4행을 묶는 문맥인데 단일 라벨로만 사용됨.
   - 수동 schema는 `member_1_name`, `member_2_name` 처럼 row index 를 key 에 포함
   - 자동 schema는 그런 결합 로직 없음

3. **(보조) cellSpan-aware lookup 부재**: makers 에서는 영향 적지만, 다른 양식에서 헤더 cs > 매칭 미스 가능. 안전망으로 추가.

---

## 2. Architecture

### 2.1 Module Layout (변경 없음)

```
pyhwpxlib/templates/
├── auto_schema.py     ← 본 작업 핵심
│   ├── _find_balanced_tables           (변경 없음)
│   ├── _extract_cells                  (변경 없음)
│   ├── _is_label                       (변경 없음)
│   ├── _is_placeholder                 (변경 없음)
│   ├── _detect_repeated_grid           (재설계 ← § 3.1)
│   ├── _find_grid_subregion            (신규 ← § 3.2)
│   ├── _find_label_for                 (cellSpan-aware ← § 3.3)
│   ├── _find_row_group_label           (신규 ← § 3.4)
│   └── generate_schema                 (호출 흐름 갱신 ← § 3.5)
├── slugify.py
│   └── _LABEL_MAP                      (member_N 결합 시 추가 mapping)
└── diagnose.py                         (신규: CLI 진단 도구 ← § 6)
```

### 2.2 Data Flow

```
section_xml
  └─ for each table:
      ├─ cells = _extract_cells(tbl)
      ├─ grid_region = _find_grid_subregion(cells)        ← 신규
      │     ├─ value-only contiguous rows ≥ 3
      │     └─ same col-set across them
      │
      ├─ for each value cell c:
      │     ├─ if c in grid_region:
      │     │     ├─ row_group = _find_row_group_label(c, cells)   ← 신규
      │     │     ├─ col_header = _find_label_for(c, ..., prefer_header=True)
      │     │     ├─ row_idx = (c.row - grid_region.start) + 1
      │     │     └─ key = slug(row_group) + "_" + str(row_idx) + "_" + slug(col_header)
      │     │           예: member + _1 + _name = "member_1_name"
      │     └─ else:
      │           label = _find_label_for(c, ..., prefer_header=False)
      │           key = slug(label)            (기존 동작)
      │
      └─ schema["tables"].append(...)
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| `_find_grid_subregion` | `_extract_cells`, `_is_placeholder` | 표 안의 그리드 sub-region (start_row, end_row, cols) 반환 |
| `_find_row_group_label` | `_extract_cells`, rs 정보 | rs > 1 인 col=0 라벨에서 그룹명 추출 |
| `_find_label_for` (개정) | cellSpan 정보 (cs, rs) | colSpan/rowSpan 범위 안 매칭 |
| `slugify._LABEL_MAP` | (없음) | "참 여 자" → "member" 등 row group 매핑 추가 |

---

## 3. Detailed Design

### 3.1 `_detect_repeated_grid` 재설계 → `_find_grid_subregion`

**현재 (0.13.3)**:
```python
def _detect_repeated_grid(cells):
    by_row = {row: {col,col,...} for value cells}
    common = intersection(all)
    return len(by_row) >= 3 and len(common) >= 2
```

**문제**: 모든 행을 한 그릇에 넣어 교집합 → 1/7/8 행이 grid 깨뜨림.

**개정**:
```python
def _find_grid_subregion(cells) -> Optional[GridRegion]:
    """
    표 안에서 다음 조건을 만족하는 최대 contiguous row 구간을 찾는다:
      1. 연속된 ≥ 3 개 행
      2. 모두 value 셀 (empty 또는 placeholder)
      3. 같은 col 집합 (정확히 같은 cols)
      4. col 집합 크기 ≥ 2
    여러 후보 중 가장 긴 것 반환. 없으면 None.

    예 (makers): rows 3,4,5,6 (모두 cols={1,2,4,6}, 4 rows) → GridRegion(3, 6, {1,2,4,6})
    """
    by_row = {}
    for c in cells:
        if not c["text"] or _is_placeholder(c["text"]):
            by_row.setdefault(c["row"], set()).add(c["col"])
    rows = sorted(by_row)
    best = None
    i = 0
    while i < len(rows):
        j = i
        cols = by_row[rows[i]]
        if len(cols) < 2:
            i += 1; continue
        while j + 1 < len(rows) and rows[j+1] == rows[j] + 1 and by_row[rows[j+1]] == cols:
            j += 1
        run = j - i + 1
        if run >= 3 and (best is None or run > best.length):
            best = GridRegion(start=rows[i], end=rows[j], cols=cols)
        i = j + 1
    return best
```

`GridRegion` 은 `dataclass(start: int, end: int, cols: set[int])` + `length` 프로퍼티.

### 3.2 `_find_row_group_label`

```python
def _find_row_group_label(value_cell, cells) -> Optional[str]:
    """
    value_cell 의 row 가 어느 rowSpan 셀의 범위 안에 들어오는지 검사.
    조건: c.col < value_col, c.row ≤ value_row < c.row + c.rs, is_label.
    가장 col 이 작은 (왼쪽) 후보 반환.

    makers 예: value=(3,1), 후보 (3, 0, rs=4) → "참 여 자"
              value=(5,2), 후보 (3, 0, rs=4) (3 ≤ 5 < 7) → "참 여 자"
    """
    row, col = value_cell["row"], value_cell["col"]
    candidates = [
        c for c in cells
        if c["col"] < col
        and c["row"] <= row < c["row"] + c["rs"]
        and _is_label(c["text"])
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda c: c["col"])["text"]
```

### 3.3 `_find_label_for` cellSpan-aware

**개정**:
```python
def _find_label_for(value_cell, cells, *, prefer_header=True):
    row, col = value_cell["row"], value_cell["col"]
    above = [
        c for c in cells
        if c["row"] < row
        and c["col"] <= col < c["col"] + c["cs"]   # ← span-aware
        and _is_label(c["text"])
    ]
    left = [
        c for c in cells
        if c["col"] < col
        and c["row"] <= row < c["row"] + c["rs"]   # ← span-aware
        and _is_label(c["text"])
    ]
    if prefer_header and above:
        return max(above, key=lambda c: c["row"])["text"]
    if left:
        return max(left, key=lambda c: c["col"])["text"]
    if above:
        return max(above, key=lambda c: c["row"])["text"]
    return None
```

makers 표[0] r=3 c=4 (member_1_id) 의 경우:
- 기존: above col==4 → (2, 4) "학 번" ✓ (uchanged)
- 개정: above c.col≤4 < c.col+c.cs → (2, 4, cs=2) "학 번" ✓ (동일)

다른 양식에서 헤더가 col=3 cs=2 (cols 3-4 cover) 이고 value 가 col=4 인 경우 새로 매칭됨.

### 3.4 grid 안 셀 처리 (generate_schema 안)

```python
grid = _find_grid_subregion(cells)
for cell in cells:
    text = cell["text"]
    if text and not _is_placeholder(text):
        continue  # label, skip

    if grid and grid.start <= cell["row"] <= grid.end and cell["col"] in grid.cols:
        col_header = _find_label_for(cell, cells, prefer_header=True)
        row_group = _find_row_group_label(cell, cells)
        row_idx = cell["row"] - grid.start + 1     # 1-based

        if row_group and col_header:
            base = label_to_key(row_group, _empty_set)   # e.g. "member"
            field_part = label_to_key(col_header, _empty_set)  # e.g. "name"
            key = f"{base}_{row_idx}_{field_part}"
        elif col_header:
            key = label_to_key(f"{col_header}_{row_idx}", used_keys, fallback_index=...)
        else:
            key = f"field_{cell['row']}_{cell['col']}"
    else:
        # 기존 로직 (단일 필드)
        label = _find_label_for(cell, cells, prefer_header=False)
        key = label_to_key(label or text or f"cell_{r}_{c}", used_keys, fallback_index=...)

    fields.append({"key": key, "cell": [cell.row, cell.col], "label": col_header or label or "", ...})
```

**주의**:
- `label_to_key(row_group, _empty_set)` 의 _empty_set 은 row_group 자체를 단독 슬러그화 (충돌 검사 별개)
- row_group 의 한국어 → ASCII 매핑은 slugify._LABEL_MAP 에 추가:

```python
_LABEL_MAP["참여자"] = "member"
_LABEL_MAP["참 여 자"] = "member"
_LABEL_MAP["참여 자"] = "member"
```

### 3.5 호출 흐름 정리 (`generate_schema`)

```python
def generate_schema(section_xml, *, name, ...):
    schema = {...}
    used_keys = set()
    fallback_index = [0]

    for t_idx, (ts, te) in enumerate(_find_balanced_tables(section_xml)):
        cells = _extract_cells(section_xml[ts:te])
        if not cells:
            continue

        grid = _find_grid_subregion(cells)         # ← 신규
        fields = []
        for cell in cells:
            if has label text → continue
            field = _build_field(cell, cells, grid, used_keys, fallback_index)  # ← 신규 helper
            fields.append(field)

        schema["tables"].append({...})
    return schema
```

---

## 4. Test Plan

### 4.1 단위 테스트 (신규)

| ID | Test | Method |
|----|------|--------|
| T-01 | `_find_grid_subregion` makers 표[0] → GridRegion(3, 6, {1,2,4,6}) | 직접 호출 |
| T-02 | mixed table (header + grid + footer)에서 가장 긴 contiguous run 반환 | fixture |
| T-03 | 3개 미만 row 또는 col<2 → None | fixture |
| T-04 | `_find_row_group_label` rs=4 셀이 4행 모두 매칭 | fixture |
| T-05 | rs=1 셀은 row group label 으로 매칭 안 됨 | fixture |
| T-06 | `_find_label_for` cellSpan colSpan=2 이 col=4 매칭 (col=3, cs=2) | fixture |
| T-07 | `_find_label_for` cellSpan rowSpan=3 이 row=2 매칭 (row=0, rs=3) | fixture |
| T-08 | `generate_schema` makers → member_1_name, member_2_name, ... member_4_sign 16개 + team_name 등 4개 | makers HWPX |

### 4.2 회귀

- 기존 `tests/test_templates.py` 12개 PASS 유지
- 단일 필드 정확도: team_name, project_name, period, report_date 모두 회귀 없음

### 4.3 Overlap 측정 스크립트 (`tests/test_auto_schema_overlap.py`)

```python
def test_makers_overlap_70_percent():
    auto = generate_schema_from_hwpx("skill/templates/makers_project_report.hwpx", name="makers")
    manual = json.loads(open("skill/templates/makers_project_report.schema.json").read())
    auto_keys = {f["key"] for t in auto["tables"] for f in t["fields"]}
    manual_keys = {f["key"] for t in manual["tables"] for f in t["fields"]}
    overlap = auto_keys & manual_keys
    ratio = len(overlap) / len(manual_keys)
    assert ratio >= 0.70, f"Overlap {ratio:.0%} < 70%"
```

---

## 5. CLI / 진단 도구 (보조)

`pyhwpxlib template diagnose <hwpx>`:

```
Table 0: 11x7 (33 cells)
  Grid sub-region: rows 3..6, cols {1, 2, 4, 6} (4 rows × 4 cols = 16 cells)
  Row group label: "참 여 자" (cell (3, 0), rs=4) → "member"
  Headers: 성  명 → name, 학  과(부) → dept, 학  번 → student_id, 서  명 → signature

Auto schema fields:
  team_name        (1, 1) span=[1,6]   ← 단일
  member_1_name    (3, 1)              ← grid
  member_1_dept    (3, 2) span=[1,2]   ← grid
  ... (16 grid + 4 single = 20 fields)

Comparison vs manual schema (skill/templates/makers_project_report.schema.json):
  Auto: 20 keys, Manual: 20 keys
  Overlap: 16 / 20 = 80% (목표 70% 달성)
  Missing: { ... 차이 ... }
```

---

## 6. Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| grid sub-region 감지가 다른 양식에서 false positive | High | makers + 검수확인서 + 한 양식 추가로 fixture 회귀 |
| row_group label 매핑 사전 부족 → key 가 한글/raw 로 떨어짐 | Medium | _LABEL_MAP 에 빈도 높은 한국어 그룹 라벨 5~10개 사전 추가 (참여자, 회원, 신청인, 위원, 직원, 학생) |
| rs=4 등 wide rowSpan 셀이 단일 필드 라벨로도 사용되어 _find_label_for 가 잘못 매칭 | Medium | row group label 은 grid 안 셀에만 적용. 단일 필드는 prefer_header=False 분기에서 기존 로직 유지 |
| cellSpan-aware 변경이 단일 필드 (team_name) 회귀 | High | T-08 + 회귀 12개로 검증 |

---

## 7. Implementation Order

1. `_find_grid_subregion` 구현 + T-01,02,03 (단독 가능)
2. `_find_row_group_label` 구현 + T-04,05
3. `_find_label_for` cellSpan-aware + T-06,07
4. `_LABEL_MAP` row group entries 추가 (참여자→member 등)
5. `generate_schema` 호출 흐름 재구성 + T-08
6. overlap 측정 테스트 (≥ 70% 검증)
7. `diagnose` CLI (보조, 선택)
8. 회귀 검증 (45 PASS)
9. PyPI 0.13.4 + memory + skill zip

---

## 8. Open Questions

| Q | Resolution |
|---|------------|
| row group label 이 grid sub-region 의 첫 row 와 정렬 안 되는 경우? (예: grid r=3..6 인데 group label rs 가 r=2..6) | rs 범위 안 grid rows 가 ≥ 80% 들어가면 매칭 |
| grid 가 표 안에 2개 이상? (드물지만) | _find_grid_subregion 이 max_length 만 반환. 다른 grid 는 단일 필드처럼 처리 |
| "최종보고서류 작성일" 같은 다단어 라벨이 fallback 되는지 | _LABEL_MAP 에 직접 매핑 (이미 0.13.3 에 report_date 매핑 존재). 본 작업 범위 밖 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-29 | Initial draft + Phase 0 진단 결과 반영 | Mindbuild + Claude |
