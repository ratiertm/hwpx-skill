---
template: plan
version: 1.2
description: rhwp 노선 채택 — silent fix opt-in 전환, dual-mode validate, doctor 명령 (0.14.0)
---

# rhwp-strict-mode Planning Document

> **Summary**: 한컴 silent reflow 가 후발주자에게 비용 전가하는 구조에 동조하지 않는다. `write_zip_archive` 의 silent precise fix 를 opt-in 으로 전환하고 dual-mode validate + interactive doctor 를 추가하여 rhwp 의 3가지 행동 강령을 코드로 강제한다.
>
> **Project**: pyhwpxlib
> **Version**: 0.13.4 → **0.14.0** (breaking)
> **Date**: 2026-04-29
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

Memory `reference_hwpx_ecosystem_position.md` 의 3강령 적용:

1. 비표준 입력은 **감지 + 고지**
2. 자동 보정은 **사용자 명시적 선택 후에만**
3. pyhwpxlib 자신도 **비표준 새로 생산하지 않음**

### 1.2 Background

- 0.13.2~0.13.4 에서 `write_zip_archive(strip_linesegs="precise")` default 가 한컴 보안 트리거(textpos overflow) 를 silent fix
- 사용자 편의 명분이지만 **한컴 silent reflow 와 동일한 함정** — 비표준 파일이 silently 통과해 생태계로 유통됨
- rhwp 입장 채택: 사용자가 명시적으로 `--fix` 누르거나 `strip_linesegs="precise"` 명시한 경우에만 보정

### 1.3 Related

- 메모리: `reference_hwpx_ecosystem_position.md` (philosophy)
- 메모리: `feedback_hancom_security_trigger.md` (precise fix 기술 배경)
- rhwp Discussion #184 / validate CLI 계획 #185

---

## 2. Scope

### 2.1 In Scope (v0.14.0)

- [ ] `write_zip_archive(strip_linesegs=False)` 가 default
- [ ] CLI 파일 출력 명령에 `--fix` 플래그 (`template fill`, `md2hwpx`, `hwpx2html`, `fill`)
- [ ] `--fix` 미사용 + 비표준 감지 → stderr 에 명시 경고 (계속 진행)
- [ ] `pyhwpxlib validate --mode {strict|compat|both}` (default both)
- [ ] `pyhwpxlib doctor <file> [--fix]` interactive (감지 + 옵션 시 보정)
- [ ] HwpxBuilder.save() — silent precise fix 유지하되 (자체 생산은 표준 보장 = 강령 #3) `verify=True` default 로 사후 검증
- [ ] tests: 새 default 동작, dual-mode validate, doctor, --fix 플래그 4가지 신규 테스트
- [ ] CHANGELOG / migration note in README
- [ ] SKILL.md 업데이트 (rhwp 노선)
- [ ] 버전 0.14.0 (pyproject.toml + __init__.py)

### 2.2 Out of Scope

- 한컴에 공식 이슈 제기 (조직 외부 작업)
- OWPML 명세 본격 schema validator (현재 strict 는 휴리스틱 + namespace 검사)
- HwpxBuilder.save 가 lineseg 정확값을 처음부터 정확히 생성 (이미 그렇게 하고 있음 — 강령 #3 자가 검증)
- 0.13.x 기존 사용자 자동 마이그레이션 (CHANGELOG 명시로 갈음)

---

## 3. Requirements

### 3.1 Functional

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | `write_zip_archive` default `strip_linesegs=False` (기존 "precise"에서 변경) | High |
| FR-02 | precise fix 가 적용되었을 때 stderr 에 fix 카운트 출력 (CLI 호출 경로) | High |
| FR-03 | `template fill`, `md2hwpx`, `hwpx2html`, `fill` CLI 에 `--fix` 플래그 — 명시 시 precise 적용 | High |
| FR-04 | `pyhwpxlib validate --mode strict` — OWPML 명세 엄격 (lineseg consistency, hp:t form, namespace, secPr placement) | Medium |
| FR-05 | `pyhwpxlib validate --mode compat` — 기존 동작 (zip + parse + required files) | High |
| FR-06 | `pyhwpxlib validate --mode both` (default) — strict + compat 모두 보고 | Medium |
| FR-07 | `pyhwpxlib doctor <file>` — 감지만; `doctor --fix` 명시 시 보정 + 새 파일 출력 | Medium |
| FR-08 | HwpxBuilder.save() — `_verify_after_save` 가 비표준 출력 시 RuntimeError 발생 (강령 #3 자가 보호) | Medium |
| FR-09 | Migration note: README + CHANGELOG 에 0.13.x → 0.14.0 동작 변화 + 호환 인자 가이드 | High |

### 3.2 Non-Functional

| Category | Criteria |
|----------|----------|
| Breaking change 명확화 | CHANGELOG MAJOR 섹션 + `pyhwpxlib --version` 경고 (선택) |
| 회귀 | 0.13.4 의 60 PASS 가 default 변경 후에도 새 의도대로 동작 (적절히 인자 추가하여 PASS 유지) |
| 호환 경로 | `strip_linesegs="precise"` 명시 호출은 그대로 작동 |
| 경고 형식 | stderr 에 명시 prefix `[pyhwpxlib]` + 한국어 메시지 (사용자 80% 한국어) |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] `pyhwpxlib template fill makers ...` (no --fix) 출력 → 한컴 보안 경고 발생 (의도된 동작) + stderr 에 "비표준 lineseg 발견" 경고
- [ ] `pyhwpxlib template fill makers ... --fix` 출력 → 한컴 OK + stdout 에 "보정 N건"
- [ ] `pyhwpxlib validate file.hwpx` → strict + compat 결과 두 섹션
- [ ] `pyhwpxlib doctor broken.hwpx` → 감지 보고. `--fix` 추가 시 fixed 파일 출력
- [ ] HwpxBuilder() 새 문서 저장 → 항상 표준 출력 (no overflow)
- [ ] 회귀 60 → ≥65 PASS

### 4.2 Quality

- [ ] CHANGELOG 0.14.0 섹션 완성 + breaking change 명확
- [ ] README 마이그레이션 가이드
- [ ] SKILL.md 새 default + opt-in fix 패턴 반영

---

## 5. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| 기존 0.13.x 사용자 자동 업데이트 시 한컴 보안 경고 폭증 | High | MAJOR 버전 (0.14.0), CHANGELOG 명시, MIGRATION.md 가이드 |
| HwpxBuilder.save 의 verify 가 false positive | Medium | 회귀 테스트 + verify 끌 수 있는 옵션 (`verify=False`) |
| 사용자가 --fix 모르고 무한 반복 한컴 경고 마주침 | Medium | stderr 경고 메시지에 "--fix 또는 doctor" 안내 명시 |
| validate strict mode 가 한컴 정상 파일도 fail | Medium | strict 는 정보 제공, exit code 는 compat 기준 |

---

## 6. Architecture

### 6.1 변경 지점

```
pyhwpxlib/
├── package_ops.py
│   └── write_zip_archive(strip_linesegs=False)        ← default 변경
├── builder.py
│   └── HwpxBuilder.save(verify=True)                  ← 자가 검증 추가
├── cli.py
│   ├── _cmd_template (fill)                           ← --fix 플래그
│   ├── _cmd_md2hwpx                                   ← --fix
│   ├── _cmd_html_to_hwpx                              ← --fix
│   ├── _cmd_fill                                      ← --fix
│   ├── _cmd_validate                                  ← --mode 플래그
│   └── _cmd_doctor (신규)                              ← 신규 명령
├── validator.py (신규, 또는 cli.py 안)
│   ├── validate_compat(file) -> Result               (= 기존 _cmd_validate 본문)
│   └── validate_strict(file) -> Result               (신규)
└── doctor.py (신규)
    └── doctor(file, fix=False) -> Result
```

### 6.2 Data Flow

```
[기본 저장 (no fix)]
  archive  → write_zip_archive(strip_linesegs=False)
           → 비표준 lineseg 보존
           → if CLI: stderr "[pyhwpxlib] 비표준 lineseg N건 — 한컴에서 보안 경고 가능. doctor 또는 --fix"

[명시 fix]
  CLI --fix → strip_linesegs="precise" 전달
           → fix N건 적용
           → stdout "[pyhwpxlib] 비표준 lineseg N건 보정 (precise)"

[validate both]
  validate_compat(file) → checks: zip, parse, required
  validate_strict(file) → checks: lineseg consistency, hp:t form, namespace, secPr
  output: { compat: {...}, strict: {...} }

[doctor]
  doctor(file)        → 감지 결과 표
  doctor(file, fix=)  → 보정한 새 파일 출력 (default 같은 디렉터리, .fixed.hwpx)
```

### 6.3 strict mode 검사 항목

| 검사 | 기준 | 위반 시 |
|------|------|---------|
| Lineseg textpos consistency | textpos ≤ UTF16(text) | error |
| Lineseg textpos monotonic | 같은 paragraph 안 textpos 가 비감소 | warning |
| hp:t form | 사용된 형식 (paired vs self-closing) 일관성 | info |
| Namespace declarations | `xmlns:hp`, `xmlns:hh` 등 표준 namespace | error |
| secPr placement | 첫 paragraph 의 secPr 또는 빈 paragraph 없음 | warning |
| BinData refs | content.hpf 의 모든 binary 참조가 BinData/ 에 존재 | error |

---

## 7. Conventions

- 경고 메시지 prefix: `[pyhwpxlib]`
- exit code: compat fail → 1, strict 만 fail → 0 + warning
- `--fix` 는 모든 writer 명령에 일관 사용 (mutate-in-place 가 아님 — output 인자 그대로)
- v0.14.0 으로 MAJOR bump (breaking 명시)

---

## 8. Next Steps

1. [ ] Design 문서 작성 (자세한 strict 규칙, doctor UX)
2. [ ] write_zip_archive default 변경 + 회귀 테스트 적응
3. [ ] CLI --fix 플래그 추가 (5개 명령)
4. [ ] validator.py 신규 + strict 검사 구현
5. [ ] doctor.py 신규
6. [ ] HwpxBuilder.save verify 추가
7. [ ] 테스트 ≥ 5개 신규
8. [ ] CHANGELOG / README / SKILL.md 갱신
9. [ ] 0.14.0 commit

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-04-29 | Initial draft (rhwp 노선 채택) | Mindbuild + Claude |
