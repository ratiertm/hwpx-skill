# TODO — hwpx-skill / python-hwpx OWPML 구현

---

## 다음 세션: render-perf-opt (PDCA, 0.18.0 목표)

> 시작: `/pdca plan render-perf-opt`
> 컨텍스트: 2026-05-05 세션에서 Tier 1 + T2.2 + T2.3 합의, 컨텍스트 한계로 Plan 직전 중단.
> 제약: **문서 정확도 유지 (byte-identical PNG)** — 캐시는 순수 메모이제이션만.

### Baseline (2026-05-05 측정)

- `RhwpEngine()` instantiate: **851 ms** — WASM compile
- `render_to_png` cold: **1,291 ms**
- `render_to_png` 5회 평균: **879 ms/회** (매번 새 엔진)
- 테스트 167 PASS in 13.8s
- 회귀 검증 anchor: PNG `sha256 = d4501eeed09bc3d4d6c45a887523fdec913f428bdfee18f3e8c2570a793f2c05`
  - 입력: `Test/output/template_fill_makers.hwpx`, page=0, scale=1.0, register_fonts=False
  - 크기: 85,966 bytes

### 변경 항목 (8개 + 2 인프라 + 1 릴리스)

| Tier | # | 변경 | 위치 | 주의 |
|---|---|---|---|---|
| 1 | T1.1 | wasmtime Engine + Module 모듈-레벨 캐시 | `pyhwpxlib/rhwp_bridge.py` | Store/Linker/Instance 는 인스턴스별 (thread-safe 패턴) |
| 1 | T1.2 | `_TextMeasurer` LRU on `(font_path, size, text)` → width | `pyhwpxlib/rhwp_bridge.py` | functools.lru_cache, 키 정확해야 회귀 없음 |
| 1 | T1.3 | `_register_bundled_fonts` 모듈-레벨 가드 (1회만) | `pyhwpxlib/api.py` | — |
| 1 | T1.4 | `render_to_png(engine=None)` DI | `pyhwpxlib/api.py` | 외부 엔진 주입 시 N장 렌더 1회 init |
| 1 | T1.5 | MCP docstrings 압축 (다단락 → 2-3 문장) | `pyhwpxlib/mcp_server/server.py` | `hwpx_template_*`, `hwpx_render_png`, `hwpx_guide` |
| 2 | T2.2 | 신규 CLI `pyhwpxlib check-fill <name> -d data.json` + MCP `hwpx_check_fill` | `pyhwpxlib/cli.py` + api.py + mcp_server | XML-level 빈칸 검증, ~10ms (PNG 안 만듦) |
| 2 | T2.3 | Workflow [3] Step D 게이팅 — 중간엔 check-fill, 최종에만 PNG | `skill/hwpx-form/WORKFLOW.md` | 안티 패턴 예시 추가 |
| - | INF | 회귀 테스트 — 변경 전/후 byte-identical PNG (3개 문서) | `tests/test_render_consistency.py` | sha256 anchor 사용 |
| - | INF | 벤치마크 스크립트 — 5회 sequential, mean/p50/p95 보고 | `scripts/bench_render.py` | 변경 전/후 비교 자동화 |
| - | REL | 0.18.0 minor 릴리스 (신규 CLI 라서 patch 부족) | pyproject + __init__ + CHANGELOG + skill zip + llm_guide | **CLAUDE.md "Release checklist" 8단계 따라야 함** |

### 예상 효과 (5장 fill-and-verify 시나리오)

- 컴퓨트: 6초 → **1초** (-83%)
- 응답 토큰: 25K → **10K** (-60%)
- 코드 변경: ~250 줄 (LRU + CLI + MCP + workflow doc + tests)
- 테스트: 167 → ~175 (회귀 + check-fill 7-8 케이스)

### 보류 항목 (이번 묶음 제외)

- T3.1 wasmtime AOT 디스크 캐시 — 별도 PDCA cycle
- T3.2 병렬 렌더 — 1-2 페이지 양식이 대부분이라 회귀 위험
- T3.3 SKILL.md 슬림 20-30% — 라우팅 영향 검증 필요
- T3.4 Anthropic `cache_control` 마커 문서화

### Pre-task 등록 상태 (2026-05-05 세션)

Tasks #19~#26 등록되어 있음 (in TaskList). 새 세션 시작 시 정리하고 PDCA Plan 부터 정식 진행.

---

## 현재 상태 (2026-03-28)

- **구현 완료 + Whale 검증**: ~38개 기능 (텍스트, charPr, paraPr, 표, 페이지 설정, 기본 도형)
- **구현 완료 + 렌더링 미확인**: ~7개 (pageNum, autoNum, footer, arc, polygon, equation, create_style)
- **미구현**: ~65개

## Phase 2 남은 작업 (버그 수정 + 안정화)

- [ ] 한컴오피스 설치 후 pageNum/autoNum/footer 렌더링 검증
- [ ] create_style로 만든 스타일이 한컴오피스에서 적용되는지 확인
- [ ] charPr 전수 Whale 검증 (취소선, 그림자, 양각/음각이 보이는지)
- [ ] paraPr 전수 Whale 검증 (줄간격, 문단간격이 적용되는지)
- [ ] 표 병합 Whale 검증 (merge_cells가 보이는지)
- [ ] insert_image Whale 검증 (실제 이미지가 보이는지)

## Phase 3: 도형/수식 완성 (~15개)

- [ ] arc — 완전한 OWPML shapeObject 구조 (현재 add_shape stub)
- [ ] polygon — 완전한 OWPML 구조 + 꼭짓점 좌표
- [ ] curve — seg 배열 (LINE/CURVE)
- [ ] connectLine — 연결선
- [ ] group container — 도형 그룹
- [ ] textart — 글맵시
- [ ] drawText — 도형 내 텍스트
- [ ] equation — 완전한 수식 구조 (script → 렌더링)
- [ ] 도형 채우기 — gradient, image pattern (현재 단색만)
- [ ] 선 화살표/끝모양 — headStyle, tailStyle, headSz, tailSz
- [ ] 도형 그림자 — ShadowType
- [ ] 좌표계/회전/뒤집기 — offset, flip, rotationInfo
- [ ] 캡션 — caption/subList

## Phase 4: 필드/폼/특수 요소 (~20개)

- [ ] checkbox (checkBtn)
- [ ] radio button (radioBtn)
- [ ] combo box (comboBox)
- [ ] list box (listBox)
- [ ] edit field (edit)
- [ ] scroll bar (scrollBar)
- [ ] date field (fieldBegin type=DATE)
- [ ] formula field (fieldBegin type=FORMULA)
- [ ] cross reference (fieldBegin type=CROSSREF)
- [ ] mail merge (fieldBegin type=MAILMERGE)
- [ ] click-here field (fieldBegin type=CLICK_HERE)
- [ ] 형광펜 (markpenBegin/End)
- [ ] 루비/덧말 (dutmal)
- [ ] 색인 표시 (indexmark)
- [ ] 숨은 설명 (hiddenComment)
- [ ] tab을 `<hp:ctrl>` 요소로 변환 (현재는 제거)
- [ ] nbSpace, fwSpace, hyphen 특수 문자
- [ ] 자동 번호 서식 (autoNumFormat 세부 옵션)
- [ ] 페이지 번호 위치 제어 (pageNumCtrl + pageHiding)

## Phase 5: OLE/차트/기타 (~25개)

- [ ] OLE 객체 (ole — objectType, binaryItemIDRef)
- [ ] 비디오 (video — videotype, fileIDRef)
- [ ] 차트 (chart)
- [ ] 스타일 수정/삭제 API
- [ ] 번호 문단 모양 (numberings/numbering/paraHead)
- [ ] 글머리표 모양 생성 (bullets/bullet)
- [ ] 탭 정의 생성 (tabProperties/tabPr)
- [ ] 금칙어 (forbiddenWordList)
- [ ] 호환 문서 (compatibleDocument)
- [ ] 변경 추적 생성/수정/수락/거절
- [ ] 변경 추적 설정 (trackchangeConfig)
- [ ] 변경 추적 태그 (insertBegin/End, deleteBegin/End)
- [ ] 각주 번호 모양 (footNotePr/autoNumFormat)
- [ ] 각주 구분선 (footNotePr/noteLine)
- [ ] 각주 간격 (footNotePr/noteSpacing)
- [ ] 각주 번호 매기기 (footNotePr/numbering)
- [ ] 미주 모양/번호/위치 (endNotePr)
- [ ] 페이지 설정 고급 (grid, visibility, lineNumberShape, pageBorderFill)
- [ ] 바탕쪽 생성/수정 (masterPage)
- [ ] 텍스트 방향 (secPr/@textDirection)
- [ ] 기본 탭 간격 (secPr/@tabStopVal)
- [ ] 프레젠테이션 설정 (presentation)
- [x] merge_cells 수정 — 피병합 셀을 물리적으로 제거 (2026-03-29 완료)
- [x] set_cell_text 줄바꿈 — \n을 별도 `<hp:p>`로 분리 (2026-03-29 완료)
- [x] set_margin hasMargin="1" — 셀 패딩 인식 수정 (2026-03-29 완료)
- [x] set_row_heights / set_col_widths API 추가 (2026-03-29 완료)
- [ ] 폰트 임베딩 (isEmbedded=1 + binaryItemIDRef로 .ttf를 BinData/에 포함, add_image 패턴 활용)
- [ ] lxml/ET 전체 통합 (근본적 리팩토링 — stdlib ET 의존 제거)

## Phase 6: 양식 템플릿 시스템

- [ ] YAML → HWPX 변환기 (YAML로 양식 정의 → template.hwpx 자동 생성)
- [ ] grid_detector 정확도 개선 (내부 짧은 선 감지, OCR 한국어 정확도)
- [ ] Web UI에서 감지 결과 시각적 확인/수정 화면
- [ ] 고객 캡처/PDF → 자동 감지 → YAML → 검토 → template.hwpx 파이프라인
- [ ] template.hwpx에서 입력칸 위치를 메타데이터로 관리 (어느 셀에 데이터를 넣을지)
- [ ] 기존 HWP/HWPX 파일에서 내용 비우고 template으로 변환
- [ ] Image → HWPX 전체 파이프라인 (현재 UI disabled):
  - [ ] Anthropic API (base64 이미지) 연동으로 셀 텍스트 자동 인식 (API 키 필요)
  - [ ] 감지된 그리드를 HTML 테이블로 표시 + 각 셀 텍스트 입력 UI
  - [ ] 수정 후 HWPX 생성/다운로드

## Whale 뷰어 한계 (한컴오피스 필요)

Whale이 렌더링하지 못하는 기능 (XML은 정상):
- 페이지 번호 (`<hp:pageNum>`)
- 자동 번호 (`<hp:autoNum>`)
- 머리말/꼬리말 (`header/footer`)
- 도형 (arc, polygon, equation)
- 이미지 (insert_image — 미확인)
- 하이퍼링크 (`<hp:fieldBegin type="HYPERLINK">`) — 2026-03-28 확인, XML은 한컴 실제 파일과 동일한 6-param 구조

이 기능들은 한컴오피스에서 검증 필요.
