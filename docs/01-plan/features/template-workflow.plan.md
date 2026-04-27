---
template: plan
version: 1.2
description: 사용자 양식 등록·자동 schema·fill·재사용 워크플로 (옵션 B)
---

# template-workflow Planning Document

> **Summary**: 사용자가 올린 .hwp/.hwpx 양식을 자동 분석 → schema 생성 → 표준 위치(skill 또는 user dir)에 저장 → schema 기반 fill 재사용. 옵션 B 범위 (중간).
>
> **Project**: pyhwpxlib
> **Version**: 0.13.2 → 0.13.3 (마무리 시)
> **Date**: 2026-04-28
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

옵션 B의 가설(graphify로 검증): JSON→from_json 경로는 단조 (16% 메서드만 사용).
풍부한 HWPX 만들려면 **기존 양식 재사용** 패턴이 필요. makers_project_report 가 prototype.

### 1.2 Background

- HwpxBuilder 19개 add_* 메서드 vs decoder.from_json 3개만 사용 (graphify 분석)
- 사용자가 올린 양식을 매번 수동으로 정리 (변환·precise fix·schema 작성·skill 추가)는 비효율
- 자동화 70%면 사용자가 30%만 검토/조정으로 끝낼 수 있음

### 1.3 Related

- 선례: `skill/templates/makers_project_report.{hwpx,schema.json}` (수동 작성)
- graphify 분석: 단조함 검증 결과 (이 세션)

---

## 2. Scope

### 2.1 In Scope (B)

- [ ] `pyhwpxlib/templates/` 모듈 (resolver / slugify / auto_schema / fill / public API)
- [ ] CLI `pyhwpxlib template {add,fill,show,list}` 4개 서브명령
- [ ] User dir 계층 (XDG, `~/.local/share/pyhwpxlib/templates/`)
- [ ] HWP→HWPX 자동 변환 + precise fix + ASCII 파일명
- [ ] auto_schema 휴리스틱 (빈 셀 + 인접 라벨 매칭, placeholder 감지)
- [ ] makers fixture 검증 (자동 schema vs 수동 schema 비교)
- [ ] 회귀 테스트
- [ ] skill 가이드 갱신 (templates/README.md)

### 2.2 Out of Scope (C로 미룸)

- `template edit` (사용자가 텍스트 에디터로 schema.json 직접 편집)
- `template share` (skill commit 자동화)
- 반복 항목 자동 감지 (참여자 1~N 패턴) — 사용자가 명시
- 음역 라이브러리 (단순 한글→영어 mapping table 사용)
- 새 PyPI 출시 (이번 옵션 B는 dev 후 별도 결정)

---

## 3. Requirements

### 3.1 Functional

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | `template add <hwp_or_hwpx> [--name N] [--shared]` — 변환·fix·schema 자동·저장 | High |
| FR-02 | auto_schema: 빈 셀에 인접 라벨 매핑하여 fields 생성 (정확도 ≥ 70%) | High |
| FR-03 | `template fill <name> -d data.json -o out.hwpx` — schema 기반 셀 채우기 | High |
| FR-04 | `template show <name>` — schema + 셀 위치 미리보기 | Medium |
| FR-05 | `template list` — user + shared 양식 목록 | Medium |
| FR-06 | XDG 계층: user dir 우선, 없으면 skill 양식 fallback | Medium |
| FR-07 | makers schema 자동 생성 결과가 수동 schema와 ≥ 70% 일치 | High |

### 3.2 Non-Functional

| Category | Criteria |
|----------|----------|
| 한컴 호환 | precise fix 자동 적용 (write_zip_archive default) |
| 파일명 | 모두 ASCII (zip 호환) |
| 회귀 | 기존 31개 테스트 + 새 templates 테스트 PASS |
| 의존성 | 추가 외부 패키지 없음 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] makers 양식: `pyhwpxlib template add ./samples/3.\ 전정\ Makers...hwp --name makers` → 자동 생성 schema 가 수동 schema 의 fields 70%+ 매칭
- [ ] `template fill makers -d data.json -o out.hwpx` 가 한컴에서 정상 (보안 경고 없음)
- [ ] User dir + skill dir 모두 list 에 표시
- [ ] 회귀 31 + 신규 ≥ 8 테스트 PASS

### 4.2 Quality

- [ ] auto_schema 정확도 측정 (precision/recall) makers 기준
- [ ] CLI 사용성: 한 줄로 add → fill 가능

---

## 5. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| 한글 라벨 → ASCII key 충돌 (예: 두 다른 라벨이 같은 slug) | Medium | 충돌 시 _2 _3 suffix |
| auto_schema 휴리스틱이 사용자 양식에서 빗나감 | High | show 명령으로 검토 → 수동 .json 편집 권장 |
| 반복 항목 (참여자 N명) auto-detect 못 함 | Medium | 사용자가 schema.json에서 직접 인덱스 지정 (우선) |
| user dir 위치 OS별 차이 (mac/linux/win) | Low | XDG 표준 + Windows fallback (`%LOCALAPPDATA%`) |

---

## 6. Architecture

### 6.1 모듈 구조

```
pyhwpxlib/
├── templates/                         (신규 모듈)
│   ├── __init__.py                    public API: add, fill, show, list_templates
│   ├── resolver.py                    user dir + skill dir 경로 resolver
│   ├── slugify.py                     한글/특수문자 → ASCII key
│   ├── auto_schema.py                 자동 분석 (빈 셀 + 인접 라벨)
│   └── fill.py                        schema 기반 cell 채움
└── cli.py                              `template` 서브명령 추가
```

### 6.2 Data Flow

```
[add]
hwp/hwpx 입력
  ├─ HWP면 hwp2hwpx.convert
  ├─ slug 정규화 (한글 파일명 → ASCII)
  ├─ precise fix (write_zip_archive default)
  ├─ auto_schema 분석 → schema.json
  └─ 저장 (user dir or --shared로 skill dir)

[fill]
template name + data.json
  ├─ resolver: user dir 우선 → skill dir fallback
  ├─ schema.json 로드 → fields 매핑
  ├─ 각 field cell 위치에 data[key] 텍스트 교체 (정규식)
  ├─ write_zip_archive (precise default)
  └─ 출력 hwpx
```

### 6.3 Auto Schema 휴리스틱

```
1. 표 모두 추출 (depth-aware)
2. 각 cell:
   a. 텍스트 있고 짧음(<20자) + col=0 또는 행/열 헤더 패턴 → 라벨
   b. 빈 셀 → value (인접 라벨에서 key 도출)
   c. placeholder 패턴 (xx.xx, 0회차, ----, (예시)) → value (텍스트가 placeholder)
3. 라벨 → slug:
   - mapping table (팀명→team_name, 성명→name, 학번→id, 등)
   - mapping 없으면 한글 그대로 (key_kr) + auto_NN 보조 key
4. spans 보존 (span [rs, cs])
```

---

## 7. Conventions

- 파일명: ASCII만 (한글은 `name_kr` 필드)
- key naming: snake_case
- schema 버전: `"version": "1.0"` (auto_schema가 갱신할 때 bump)

---

## 8. Next Steps

1. [x] Plan 작성
2. [ ] resolver + slugify (의존성 없음)
3. [ ] auto_schema (table 분석)
4. [ ] fill (cell 정규식 교체)
5. [ ] __init__.py (public API)
6. [ ] CLI 4개 명령
7. [ ] makers 자동 schema 비교 검증
8. [ ] 회귀 테스트
9. [ ] skill 가이드 + 메모리 갱신

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-28 | Initial draft | Mindbuild + Claude |
