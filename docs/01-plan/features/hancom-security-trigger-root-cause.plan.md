---
template: plan
version: 1.2
description: 한컴 hwpx 보안경고 근본 원인 식별 — 외부 수정 감지 시그니처 분리 실험
---

# hancom-security-trigger-root-cause Planning Document

> **Summary**: 한컴 hwpx 보안경고("문서 보안 설정을 낮춤") 트리거의 정확한 시그니처를 통제 실험으로 분리. 현재 strip 우회는 안전한 default이지만 어떤 lineseg 속성/조건이 결정 요인인지 미식별.
>
> **Project**: pyhwpxlib + hwpx-skill
> **Version**: 0.13.1
> **Author**: Mindbuild + Claude Opus 4.7
> **Date**: 2026-04-27
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

한컴 보안 경고를 회피하는 strip 우회는 검증됨. 그러나:

- 어떤 lineseg 속성(textpos / vertpos / vertsize / baseline / segment_width / flags)이 트리거인지 모름
- 정상/오류 파일의 진짜 차이가 식별 안 됨 (이준구 vs 지청운)
- 우리 R3fix(N개 분할)가 실패한 정확한 이유 모름 — 분할값 부정확? 갯수 자체? 다른 속성?

이 미해결 항목들을 통제 실험으로 좁힘.

### 1.2 Background

이전 가설 폐기 이력:
- ❌ R3 위반 자체 = 트리거 (반증: 검수확인서_채움 R3=3 정상 열림)
- ❌ timestamp 1980 / 파일 순서 / content.hpf Z 접미사 / lastsaveby
- ✅ 부분 정답: linesegarray 통째 strip → 회피 성공

근본 원인을 알면:
- lineseg 보존하면서 회피 가능한 정밀 fix 가능
- skill에 정확한 트리거 조건 명시 → AI가 우회만 의존하지 않음
- pyhwpxlib lint가 더 좁은 조건만 경고 가능

### 1.3 Related Documents

- 회피 구현: `pyhwpxlib/postprocess/lineseg_reflow.py`
- 메모리: `~/.claude/projects/-Users-leeeunmi-Projects-active-hwpx-skill/memory/feedback_hancom_security_trigger.md`
- rhwp 출처: `references/rhwp/src/document_core/validation.rs` (R1/R2/R3)

---

## 2. Scope

### 2.1 In Scope

- [ ] Phase 1 — 이준구(정상) vs 지청운(오류) 원본 정밀 diff (section0/header/content.hpf 구조 비교)
- [ ] Phase 2 — 정상 파일에서 lineseg 속성 1개씩 의도적 손상 후 한컴 반응 (4~6개 속성)
- [ ] Phase 3 — 정상 파일에서 lineseg 갯수만 변경 (1→3 분할, 값은 정확) 한컴 반응
- [ ] Phase 4 — 트리거 시그니처 문서화 (메모리 + skill 갱신)

### 2.2 Out of Scope

- rhwp 빌드 환경 구축 (cargo 설치)
- font_metric 정밀 포팅 (Phase 3 정확값 분할이 통과해도 별도 작업)
- 한컴 자체 알고리즘 리버스 엔지니어링 (외부 도구 검사 불가)
- 새 PyPI 출시 (조사 결과 따라 결정)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | Phase 1: 정상/오류 sample 정밀 diff 분석 결과 산출 | High | Pending |
| FR-02 | Phase 2: 4개 이상 lineseg 속성 단일 손상 실험 → 한컴 반응 매트릭스 | High | Pending |
| FR-03 | Phase 3: 정확한 reflow 후 갯수만 1→3 변경한 파일 한컴 검증 | Medium | Pending |
| FR-04 | Phase 4: 트리거 시그니처 식별 결과 메모리/skill 반영 | High | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| 검증 비용 | 한컴 수동 검증 횟수 ≤ 10회 | 사용자 검증 요청 카운트 |
| 데이터 손실 | 실험 파일은 별도 디렉터리 (`Test/output/security_probe/`) | 원본 파일 미수정 |
| 재현성 | 모든 실험 스크립트 저장 | `tests/security_probe/` |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] Phase 1~4 완료
- [ ] 트리거 시그니처가 단일 속성(또는 조합)으로 좁혀짐 OR "분리 불가"가 결론으로 문서화
- [ ] 결과가 `feedback_hancom_security_trigger.md`에 정정 반영
- [ ] 정밀 fix 가능 여부 판정 (lineseg 보존 회피 알고리즘)

### 4.2 Quality Criteria

- [ ] 각 Phase의 실험 파일/결과/사용자 한컴 반응 모두 기록
- [ ] 가설 → 실험 → 반증/지지 사이클로 진행 (가설 깜빡 금지)

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| 한컴 검증 피로도 (반복 요청) | Medium | High | Phase별 모든 변형을 한 번에 묶어서 한 차례 검증 요청 |
| 트리거가 단일 속성으로 분리 불가 (복합 조건) | High | Medium | 그 자체를 결론으로 문서화 → 정밀 fix 포기, strip 유지 |
| 정상 파일이 다른 이유로 깨질 수 있음 (한 속성 손상이 렌더링 깨버림) | Medium | Medium | 손상 폭을 작게 (예: vertpos +50, vertsize +10) |

---

## 6. Architecture Considerations

라이브러리 조사 작업이므로 6/7 섹션 대부분 N/A. 핵심만:

### 6.x 실험 구조

```
Test/output/security_probe/
├── phase1_diff/             # 정상 vs 오류 원본 비교 산출물
├── phase2_attr_probe/       # 속성별 단일 손상 변형
│   ├── orig.hwpx            # baseline (정상)
│   ├── textpos_off.hwpx
│   ├── vertpos_off.hwpx
│   ├── vertsize_off.hwpx
│   ├── baseline_off.hwpx
│   └── horzsize_off.hwpx
├── phase3_count_only/       # 값 정확 + 갯수만 변경
│   ├── orig.hwpx
│   └── split3_accurate.hwpx
└── results.md                # 한컴 반응 기록
```

---

## 7. Convention Prerequisites

N/A (조사 작업)

---

## 8. Next Steps

1. [x] Plan 작성 (이 문서)
2. [ ] Phase 1 실행 — 정상/오류 sample diff
3. [ ] Phase 2 실험 — 속성 분리
4. [ ] Phase 3 실험 — 갯수만 변경
5. [ ] Phase 4 — 결과 문서화 + 메모리 갱신

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-27 | Initial draft | Mindbuild + Claude |
