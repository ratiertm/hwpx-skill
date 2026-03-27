# Retrospective: owpml-full-impl

**Feature:** OWPML Full Implementation — python-hwpx 100% Coverage
**Date:** 2026-03-28
**Mode:** release (Stages 1→2→3→4→5→6→7→8)
**Commits:** ratiertm/python-hwpx a6b402e, 165db5a / ratiertm/hwpx-skill dcff10e, e086768

## What Went Well

- **비용효율성 분석이 올바른 방향을 잡아줌** — 신규 개발(4.5x) 대신 fork 업그레이드(1x) 선택이 정확했음. 실제로 ~900줄 추가로 70+ 기능 구현
- **ensure_run_style 패턴 확장이 매우 효율적** — 기존 predicate/modifier 패턴에 파라미터만 추가하는 방식으로 charPr 14개 속성을 한 번에 구현
- **ensure_para_property를 ensure_char_property와 동일 패턴으로 구현** — 코드 일관성 유지
- **이전 retrospective 교훈 적용** — per-step 마킹, SPEC 코멘트 동시 작성, 테스트 즉시 실행
- **Whale 브라우저로 시각적 검증** — 한컴오피스 없이도 hwpx 렌더링 확인 가능

## What Went Wrong

- **`\t` 버그를 DO Stage에서 못 잡음** — `_sanitize_text()`가 `Section.add_paragraph()` 경로에서 호출 안 되는 것을 TEST가 아닌 개별 요소 테스트에서 발견
- **add_control의 lxml/ET 충돌** — `add_page_number()` 등 control 기반 기능이 동작 안 함. 기존 코드의 깊은 문제로 이번에 해결 못 함 (DEV-001)
- **arc/equation이 Whale에서 도형으로 안 보임** — add_shape 기반 stub이 OWPML 필수 하위 요소를 완전히 만들지 않아서. 파일은 열리지만 시각적 렌더링 안 됨
- **owpml_full_test.hwpx (모든 요소 포함)가 한글에서 안 열림** — 불완전한 도형 요소 때문. 텍스트/서식만 있는 파일은 정상

## Surprises

- `_sanitize_text()`가 이미 `\t` 제거 로직을 갖고 있었지만, `add_paragraph`의 주요 경로에서 호출되지 않았음
- Naver Whale이 hwpx 뷰어를 내장하고 있어서 한컴오피스 없이 검증 가능
- OWPML XSD에 모든 속성이 명확히 정의되어 있어 구현 난이도가 예상보다 낮았음

## Key Decisions

| 결정 | 이유 |
|------|------|
| fork 업그레이드 vs 신규 개발 | 비용효율성 4.5배 — OPC/XML 레이어 14,000줄 재사용 |
| ensure_para_style 신규 API | ensure_run_style과 대칭적 패턴 — 학습 비용 최소화 |
| insert_image 편의 API | add_image(bytes) + add_shape("pic") 조합이 너무 복잡해서 래퍼 필요 |
| `\t`를 제거(strip)하는 방식 | OWPML에서 tab은 `<hp:ctrl>` 요소인데, 이를 자동 변환하면 부작용 우려. 일단 제거로 안전하게 처리 |

## Technical Debt

- [ ] add_control lxml/ET 호환 — `_make_paragraph`와 `Section.add_paragraph` 경로에서 ET vs lxml 일관성 필요
- [ ] arc/polygon/equation의 OWPML 필수 하위 요소 — shapeObject/sz/pos 등 완전한 구조
- [ ] create_style()이 stub — header.xml `<hh:styles>` 조작 필요
- [ ] checkbox, radio 등 폼 컨트롤 — add_control 수정 후 구현 가능
- [ ] `\t`를 `<hp:ctrl type="tab"/>` 요소로 변환하는 것이 정확한 OWPML 방식

## Lessons for Next Phase

1. **XML 텍스트에 제어문자가 들어가는 모든 경로를 체크** — `_sanitize_text()` 호출 누락은 어디서든 발생 가능
2. **Whale 브라우저가 hwpx 검증 도구로 유용** — 한컴오피스 없이 빠른 시각적 확인
3. **lxml/ET 혼용은 근본적 리팩토링 필요** — 부분 수정으로는 계속 새로운 곳에서 터짐
4. **도형 요소는 텍스트보다 훨씬 복잡** — shapeObject 구조를 완전히 만들어야 렌더링됨
