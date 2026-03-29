# TODO — hwpx-skill / python-hwpx OWPML 구현

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
- [ ] 폰트 임베딩 (isEmbedded=1 + binaryItemIDRef로 .ttf를 BinData/에 포함, add_image 패턴 활용)
- [ ] lxml/ET 전체 통합 (근본적 리팩토링 — stdlib ET 의존 제거)

## Whale 뷰어 한계 (한컴오피스 필요)

Whale이 렌더링하지 못하는 기능 (XML은 정상):
- 페이지 번호 (`<hp:pageNum>`)
- 자동 번호 (`<hp:autoNum>`)
- 머리말/꼬리말 (`header/footer`)
- 도형 (arc, polygon, equation)
- 이미지 (insert_image — 미확인)
- 하이퍼링크 (`<hp:fieldBegin type="HYPERLINK">`) — 2026-03-28 확인, XML은 한컴 실제 파일과 동일한 6-param 구조

이 기능들은 한컴오피스에서 검증 필요.
