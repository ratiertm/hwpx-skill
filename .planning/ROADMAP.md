# Roadmap — pyhwpxlib v0.5

## Milestone 1: 테마 시스템 + JSON Overlay + 기술 부채 해소

### Phase 1: 테마 시스템 코어
**Goal**: `HwpxBuilder(theme='forest')` 한 줄로 팔레트+폰트+사이즈+여백 통합 적용

**Requirements**: TS-1, TS-2

**Plans:** 2 plans

Plans:
- [x] 01-01-PLAN.md — Theme 데이터 모델 + 10종 내장 테마 + 테스트 스캐폴드
- [x] 01-02-PLAN.md — Builder/BlankFileMaker/api.py 테마 통합 + 통합 테스트

**Deliverables**:
- `pyhwpxlib/themes.py` — 테마 데이터 모델 + 10종 내장 테마
- `builder.py` 리팩토링 — `DS` dict → 테마 시스템 통합
- header.xml 동적 fontfaces 생성 (복수 폰트 등록)
- charPr/paraPr 테마 연동 (fontRef, height, color)
- `TABLE_PRESETS` → 테마에서 파생
- 기존 `theme='default'` 하위 호환 유지
- 테스트: 10종 테마 각각 문서 생성 + validate + rhwp 프리뷰

**Success**: 10종 테마로 생성한 문서가 각각 다른 색상/폰트/사이즈를 가짐

---

### Phase 2: JSON Overlay 정밀화 + BinData 에러 핸들링
**Goal**: 원본 서식 100% 보존하면서 텍스트 정밀 교체 + HWP 변환 안정화

**Requirements**: TS-3, TS-4, CF-2, CF-3

**Plans:** 1/3 plans executed

Plans:
- [x] 02-01-PLAN.md — overlay.py extract/apply 정밀화: original_parts + regex replacement + zipfile 리팩토링
- [x] 02-02-PLAN.md — hwp2hwpx.py BinData 에러 핸들링 (try/except + warning)
- [x] 02-03-PLAN.md — 이미지 교체 + 중첩 표 double-extraction 버그 수정

**Deliverables**:
- `overlay.py` 개선 — `<hp:t>` 단위 원본 보존 + 정밀 매칭
- 분리된 텍스트 (`울산중부` + `소방서`) 교체 동작
- 중첩 표 셀 텍스트 overlay 지원
- 이미지 교체 (`new_data_b64` 필드)
- `hwp2hwpx.py` — `_attach_binary_data` try/except + warning
- 테스트: 소방서 안내문 → 구청 안내문 변환 (원본 레이아웃 100% 보존)

**Success**: `ibgopongdang.hwpx` overlay 적용 → 모든 텍스트 교체됨 + 서식 동일

---

### Phase 3: 동적 테마 추출 + 통합
**Goal**: 사용자 양식에서 테마 자동 추출 → 저장 → 재사용

**Requirements**: CF-1

**Deliverables**:
- `extract_theme(hwpx_path)` — header.xml 분석 → 테마 JSON 생성
  - charPr → 폰트명, 크기, 색상, 볼드/이탤릭 추출
  - paraPr → 정렬, 줄간격, 들여쓰기 추출
  - 표 스타일 → 헤더 배경색, 셀 패딩 추출
- 테마 저장/로드 (`~/.pyhwpxlib/themes/` 또는 프로젝트 내)
- `HwpxBuilder(theme='custom/my-form')` 커스텀 테마 사용
- SKILL.md 워크플로우 업데이트 — "양식 업로드 → 테마 추출 → 새 문서 생성"
- MCP 서버에 `hwpx_extract_theme` 도구 추가
- 테스트: 3개 양식에서 테마 추출 → 해당 테마로 새 문서 생성

**Success**: 양식 업로드 → 테마 추출 → 같은 스타일로 다른 내용의 문서 생성

---

### Phase 4: 정비 + 릴리스
**Goal**: 문서/테스트 정비 + PyPI v0.5.0 배포

**Deliverables**:
- 기존 테스트 전체 통과 확인
- 새 기능 테스트 추가 (테마, overlay, extract_theme)
- SKILL.md 업데이트 — 테마 시스템 반영
- design_guide.md → 코드와 동기화
- README.md 업데이트
- PyPI 0.5.0 배포
- Oracle MCP 서버 업데이트 (`git pull && systemctl restart`)

**Success**: PyPI 0.5.0 배포 + 모든 테스트 통과

---

## Phase Summary

| Phase | Goal | Requirements | Estimate |
|-------|------|-------------|----------|
| 1 | 테마 시스템 코어 | TS-1, TS-2 | 3-4일 |
| 2 | 1/3 | In Progress|  |
| 3 | 동적 테마 추출 | CF-1 | 2-3일 |
| 4 | 정비 + 릴리스 | — | 1-2일 |
