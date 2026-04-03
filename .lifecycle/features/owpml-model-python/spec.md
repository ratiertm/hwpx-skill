---
feature: owpml-model-python
title: hancom-io/hwpx-owpml-model C++ → Python 전체 전환
created: 2026-03-28
updated: 2026-03-28
status: draft
depends_on: [char-property-dataclass, namespace-2024-compat]
steps: 25
tags: [python-hwpx, owpml-model, reverse-engineering, dataclass, upstream-pr]
---

# E2E Spec: OWPML Model C++ → Python 전환

hancom-io/hwpx-owpml-model의 292개 C++ 클래스를 Python dataclass로 전환.
소스: https://github.com/hancom-io/hwpx-owpml-model (Apache 2.0)
목표: python-hwpx에 공식 OWPML 데이터 모델 완전 구현

## 현황: 59/292 Python 클래스 (20%)

| 카테고리 | C++ | Python 완료 | 비고 |
|----------|-----|-------------|------|
| Core | 10 | 0 | 기반 타입 (color, margin, fill 등) |
| Head | 107 | ~45 | CharProperty 9, ParagraphProperty 7 완료 |
| Para | 134 | ~12 | Table/Ctrl/Run 대부분 generic |
| Etc | 36 | ~2 | history, version 등 |
| RDF | 1 | 0 | metadata |
| Root | 4 | 0 | ClassID, enum 등 |
| **합계** | **292** | **~59** | **20%** |

---

## Phase 1: Core 기반 타입 (10개 클래스)

모든 카테고리가 참조하는 기반 타입. 먼저 구현해야 나머지가 상속/참조 가능.

## e2e-owpml-model-python-001: Core 데이터클래스 정의

**Chain:** Screen
**Status:** pending

### What
C++ Core 클래스 10개를 Python dataclass로 전환. `oxml/core.py` 신규 파일.

### Verification Criteria
- [ ] MarginAttribute (left, right, top, bottom) — CMarginAttrubute
- [ ] Color (red, green, blue, alpha) — Ccolor
- [ ] Gradation — CGradation
- [ ] ImageBrush (binaryItemIDRef, alpha 등) — CImgBrush
- [ ] WindowBrush (face_color, hatch_color, hatch_style, alpha) — CWinBrush
- [ ] FillBrushType (gradation, imgBrush, winBrush 등) — CFillBrushType
- [ ] ImageType — CImageType
- [ ] PointType (x, y) — CPointType
- [ ] MatrixType — CMatrixType
- [ ] HWPValue (unit, value) — CHWPValue

### Details
- **Element:** `oxml/core.py` 신규 파일 생성
- **User Action:** `from hwpx.oxml.core import MarginAttribute, Color, FillBrushType`
- **Initial State:** Core 타입이 없어서 Head/Para에서 generic Dict 사용

## e2e-owpml-model-python-002: Core 파서 함수

**Chain:** Connection
**Status:** pending

### What
Core 데이터클래스용 parse_* 함수 10개.

### Verification Criteria
- [ ] parse_margin_attribute() — MarginAttributeGroup XML → MarginAttribute
- [ ] parse_color() — color XML → Color
- [ ] parse_fill_brush() — fillBrush XML → FillBrushType
- [ ] 나머지 7개 parse_* 함수 존재
- [ ] C++ 소스의 ReadAttribute/InitMap 로직과 1:1 대응

### Details
- **Method:** 각 parse_*(node) -> CoreDataclass
- **Endpoint:** oxml/core.py
- **Request:** lxml Element
- **Auth:** None

## e2e-owpml-model-python-003: Core 테스트 및 검증

**Chain:** Processing
**Status:** pending

### What
Core 데이터클래스 파싱/생성 테스트.

### Verification Criteria
- [ ] test_core_margin.py — MarginAttribute 파싱/접근
- [ ] test_core_color.py — Color 파싱
- [ ] test_core_fill.py — FillBrushType 파싱
- [ ] 기존 공식 테스트 265/265 통과 (하위 호환)
- [ ] C++ .cpp 소스의 InitMap과 Python parse_*가 동일한 XML 구조를 처리

### Details
- **Steps:**
  1. C++ .cpp에서 InitMap 로직 확인
  2. 동일한 XML 구조를 Python에서 파싱
  3. assert
- **Storage:** 테스트 XML -- READ

## e2e-owpml-model-python-004: Core 에러 처리

**Chain:** Response
**Status:** pending

### What
Core 접근성 및 기존 코드 호환.

### Verification Criteria
- [ ] 기존 header.py의 ParagraphMargin이 MarginAttribute를 참조하거나 호환
- [ ] 기존 header.py의 ParagraphBorder.border_fill_id_ref가 Core와 연결 가능
- [ ] 순환 import 없음

### Details
- **Success Status:** Core → Head → Para 의존성 단방향
- **Response Shape:** import 정상 동작

## e2e-owpml-model-python-005: Core 에러 처리

**Chain:** Error
**Status:** pending

### What
속성 누락, 잘못된 값 처리.

### Verification Criteria
- [ ] 필수 속성 누락 → None (에러 아님, OWPML 관용적)
- [ ] 알 수 없는 자식 요소 → other_children
- [ ] stdlib/lxml 호환 (_compat_local_name 패턴)

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| left/right 누락 | None | OK |
| 알 수 없는 자식 | other_children | OK |
| stdlib ET | _compat_local_name | OK |

---

## Phase 2: Head 카테고리 확장 (107개 → ~62개 추가)

현재 ~45개 Python 클래스. 나머지 ~62개 추가. CharProperty/ParagraphProperty 기반 위에 BorderFill, Style, Font, TabDef, LayoutCompatibility 등.

## e2e-owpml-model-python-006: Head 핵심 타입 (BorderFill, Style, TabDef)

**Chain:** Screen
**Status:** pending

### What
Head 카테고리의 핵심 named 타입을 전환.

### Verification Criteria
- [ ] BorderFillType (borderType children, fillBrush 등) — CBorderFillType
- [ ] BorderType (type, width, color) — CBorderType
- [ ] StyleType (확장) — CStyleType
- [ ] TabDefType (tabItem children) — CTabDefType
- [ ] NumberingType — CNumberingType
- [ ] ParaHeadType — CParaHeadType
- [ ] BulletType (확장) — CBulletType
- [ ] FontfaceType (확장) — CFontfaceType

### Details
- **Element:** `oxml/header.py` 확장
- **User Action:** `from hwpx.oxml.header import BorderFillType, TabDefType`
- **Initial State:** BorderFillList가 List[GenericElement], TabProperties가 List[GenericElement]

## e2e-owpml-model-python-007: Head CharProperty 하위 요소 (완료 확인)

**Chain:** Connection
**Status:** pending

### What
Phase A에서 구현한 CharProperty 9개 하위 클래스가 C++ CCharShapeType과 일치하는지 검증.

### Verification Criteria
- [ ] C++ fontRef/ratio/spacing/relSz/offset/underline/strikeout/outline/shadow 와 Python CharFontRef 등 1:1 대응
- [ ] C++ bold/italic/emboss/engrave/supscript/subscript bool 플래그 일치
- [ ] C++ height/textColor/shadeColor/useFontSpace/useKerning/symMark/borderFillIDRef 일치
- [ ] C++ CCharShapeType.cpp의 InitMap과 Python parse_char_property가 동일 구조 처리

### Details
- **Method:** C++ .cpp 파일과 Python 파서 비교
- **Endpoint:** header.py CharProperty 계열
- **Request:** CCharShapeType.h/cpp vs CharProperty/CharFontRef 등
- **Auth:** None

## e2e-owpml-model-python-008: Head LayoutCompatibility (40+ 옵션)

**Chain:** Processing
**Status:** pending

### What
C++의 layoutCompatibility 관련 40+ bool 옵션 클래스를 Python으로 전환.

### Verification Criteria
- [ ] LayoutCompatibility 데이터클래스 (40+ Optional[bool] 필드)
- [ ] C++ 각 doNotAdjust*/doNotApply*/apply*/adjust* 클래스가 LayoutCompatibility 필드로 매핑
- [ ] parse_layout_compatibility() 함수 존재

### Details
- **Steps:**
  1. C++ Head 폴더의 doNotAdjust*, doNotApply*, apply*, adjust* 헤더 40+개 분석
  2. 각각이 단일 bool 속성 → Python에서는 하나의 LayoutCompatibility 데이터클래스 필드로 통합
- **Storage:** header.xml -- READ

## e2e-owpml-model-python-009: Head MappingTableType/HWPMLHeadType

**Chain:** Response
**Status:** pending

### What
문서 헤더의 최상위 구조 타입 전환.

### Verification Criteria
- [ ] MappingTableType (fontfaces, borderFills, charProperties, paraProperties, styles 등 집합)
- [ ] HWPMLHeadType (beginNum, mappingTable, layoutCompatibility 등)
- [ ] 기존 Header 데이터클래스와 통합 또는 확장

### Details
- **Success Status:** Header 파싱 시 모든 하위 구조가 typed
- **Response Shape:** Header.mapping_table.border_fills → List[BorderFillType]

## e2e-owpml-model-python-010: Head 테스트

**Chain:** Error
**Status:** pending

### What
Head 확장 후 전체 테스트 통과.

### Verification Criteria
- [ ] 기존 공식 테스트 전체 통과
- [ ] 신규 Head 테스트 20+개
- [ ] C++ InitMap ↔ Python parse_* 1:1 검증

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| 기존 Header 파싱 호환 | 하위 호환 유지 | OK |
| 새 typed 필드 접근 | IDE 자동완성 | OK |
| GenericElement fallback | 미전환 요소 보존 | OK |

---

## Phase 3: Para 카테고리 — 구조 타입 (Table, Ctrl, Run, Section 등)

가장 큰 카테고리. Abstract 계층 + 구체 타입으로 분리.

## e2e-owpml-model-python-011: Para Abstract 타입 계층

**Chain:** Screen
**Status:** pending

### What
C++ Abstract 계층을 Python으로 전환.

### Verification Criteria
- [ ] AbstractShapeObjectType (id, zOrder, numberingType, textWrap, textFlow 등)
- [ ] AbstractShapeComponentType (extends AbstractShapeObjectType)
- [ ] AbstractDrawingObjectType
- [ ] AbstractFormObjectType (extends AbstractDrawingObjectType)
- [ ] AbstractButtonObjectType (extends AbstractFormObjectType)

### Details
- **Element:** `oxml/para_types.py` 신규 파일 (또는 body.py 확장)
- **User Action:** `from hwpx.oxml.para_types import AbstractShapeObjectType`
- **Initial State:** Abstract 계층 없음, Table이 직접 generic

## e2e-owpml-model-python-012: Para Table 계층 (공식 모델 기준)

**Chain:** Connection
**Status:** pending

### What
C++ CTableType/CTr/CTc/CCellAddr/CCellSpan/CCellSz/CCellMargin/CInsideMarginType/CCellzone/CCellzoneList/CLabel을 Python으로 전환.

### Verification Criteria
- [ ] TableType (extends AbstractShapeObjectType) — pageBreak, repeatHeader, noAdjust, rowCnt, colCnt, cellSpacing, borderFillIDRef
- [ ] InsideMarginType (extends MarginAttribute) — left, right, top, bottom
- [ ] Tr — cells: List[Tc]
- [ ] Tc — name, header, hasMargin, protect, editable, dirty, borderFillIDRef + subList, cellAddr, cellSpan, cellSz, cellMargin
- [ ] CellAddr — colAddr, rowAddr
- [ ] CellSpan — colSpan, rowSpan
- [ ] CellSz — width, height
- [ ] CellMargin (extends MarginAttribute)
- [ ] CellzoneList, Cellzone — startRowAddr, startColAddr, endRowAddr, endColAddr, borderFillIDRef
- [ ] Label — topmargin, leftmargin, boxwidth 등

### Details
- **Method:** C++ .h/.cpp → Python dataclass + parse_* + serialize_*
- **Endpoint:** oxml/body.py 확장
- **Request:** C++ TableType.h, tr.h, tc.h, cellAddr.h, cellSpan.h, cellSz.h, cellMargin.h, InsideMarginType.h
- **Auth:** None

## e2e-owpml-model-python-013: Para Ctrl 및 하위 타입

**Chain:** Processing
**Status:** pending

### What
C++ CCtrl과 15개 자식 타입을 Python으로 전환.

### Verification Criteria
- [ ] Ctrl — charStyleIDRef + 15개 자식 타입 getter
- [ ] FieldBegin — id, type, name, editable, dirty, zorder, fieldid + parameters, subList, metaTag
- [ ] FieldEnd — beginIDRef, fieldid
- [ ] Bookmark — name
- [ ] HeaderFooterType — 공통 header/footer 타입
- [ ] NoteType — footNote/endNote 공통
- [ ] AutoNumNewNumType — autoNum/newNum 공통
- [ ] PageNumCtrl, PageHiding, PageNum
- [ ] Indexmark, HiddenComment
- [ ] ColumnDefType (colPr)

### Details
- **Steps:**
  1. C++ ctrl.h + 15개 하위 타입 .h 분석
  2. Python Ctrl 데이터클래스 + 15개 하위 데이터클래스
  3. parse_ctrl() 확장
- **Storage:** section XML -- READ

## e2e-owpml-model-python-014: Para 도형/개체 타입

**Chain:** Response
**Status:** pending

### What
C++ 도형/개체 타입 전환 (PictureType, ArcType, EllipseType, LineType, PolygonType, RectangleType, EquationType, OLEType, VideoType, ChartType, ContainerType 등).

### Verification Criteria
- [ ] PictureType (extends AbstractShapeObjectType) — imgDim, imgRect, imgClip 등
- [ ] ArcType, EllipseType, LineType, PolygonType, RectangleType
- [ ] EquationType, TextartType
- [ ] OLEType, VideoType, ChartType
- [ ] ConnectLineType, ContainerType, CurveType, GraphType
- [ ] 각 도형의 하위 요소: sz, pos, caption, shapeComment, renderingInfo 등

### Details
- **Success Status:** 모든 도형 타입이 typed
- **Response Shape:** PictureType.img_dim.width 등 dot 접근

## e2e-owpml-model-python-015: Para 폼 컨트롤

**Chain:** Error
**Status:** pending

### What
C++ 폼 컨트롤 타입 (EditType, ComboBoxType, ListBoxType, ScrollBarType 등).

### Verification Criteria
- [ ] EditType (extends AbstractFormObjectType)
- [ ] ComboBoxType, ListBoxType, ScrollBarType
- [ ] formCharPr — 폼 전용 글자 속성

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| 폼 컨트롤 미사용 문서 | 파싱 영향 없음 | OK |
| 폼 컨트롤 포함 문서 | typed 접근 가능 | OK |

---

## Phase 4: Para 나머지 + Etc (히스토리/버전)

## e2e-owpml-model-python-016: Para 텍스트/마크 요소

**Chain:** Screen
**Status:** pending

### What
RunType, PType, ParaListType, SectionDefinitionType, t, text, tab, lineBreak 등 텍스트 구조 타입.

### Verification Criteria
- [ ] PType (문단) — 기존 Paragraph 데이터클래스 확장/정합
- [ ] RunType (런) — 기존 Run 데이터클래스 확장/정합
- [ ] ParaListType (문단 리스트) — subList 등에서 사용
- [ ] SectionDefinitionType (구역 속성) — pagePr, startNum, grid 등
- [ ] 텍스트 마크: markpenBegin/End, titleMark, trackchangetag

### Details
- **Element:** oxml/body.py 확장
- **User Action:** C++ PType.h의 모든 속성이 Python Paragraph에 매핑
- **Initial State:** Paragraph/Run/Section은 있으나 속성이 부분적

## e2e-owpml-model-python-017: Para 공통 하위 요소

**Chain:** Connection
**Status:** pending

### What
pos, sz, caption, flip, rotationInfo, renderingInfo, visibility, presentation, placement, outMargin 등 도형/개체 공통 하위 요소.

### Verification Criteria
- [ ] PositionType (pos) — treatAsChar, affectLSpacing, vertRelTo, horzRelTo 등
- [ ] SizeType (sz) — width, height, widthRelTo, heightRelTo, protect
- [ ] Caption — side, fullSz, width, gap, lastWidth
- [ ] FlipType — horizontal, vertical
- [ ] RotationInfo — angle, centerX, centerY
- [ ] RenderingInfo — effects, alpha, glow, softEdge, reflection
- [ ] Visibility, Presentation, Placement, OutMargin

### Details
- **Method:** C++ .h 분석 → Python dataclass
- **Endpoint:** oxml/para_types.py
- **Request:** C++ Para 폴더 .h 파일 30+개
- **Auth:** None

## e2e-owpml-model-python-018: Etc 카테고리

**Chain:** Processing
**Status:** pending

### What
히스토리, 버전, 매니페스트 등 문서 메타데이터 타입.

### Verification Criteria
- [ ] HWPMLHistoryType — HistoryEntryType children
- [ ] HistoryEntryType — DiffEntryType children (InsertType, DeleteType, UpdateType)
- [ ] VersionType — application, major, minor, micro, build
- [ ] ManifestType — item, itemref
- [ ] SectionType (구역 루트)
- [ ] MasterPageType
- [ ] MetadataType
- [ ] ParameterSetType, ParameterArrayType, ParameterBinary, ParameterItemtype
- [ ] HWPApplicationSetting, DocDistribute, CaretPosition

### Details
- **Steps:**
  1. C++ Etc 폴더 36개 .h 분석
  2. Python oxml/etc.py 신규 파일
- **Storage:** history.xml, version.xml -- READ

## e2e-owpml-model-python-019: RDF + Root

**Chain:** Response
**Status:** pending

### What
RDF 메타데이터와 Root 공통 타입.

### Verification Criteria
- [ ] RDF (최소 구현)
- [ ] ClassID — enum 매핑
- [ ] enumdef — OWPML enum 정의 (TABLEPAGEBREAKTYPE 등)

### Details
- **Success Status:** 모든 OWPML enum이 Python enum 또는 상수로 정의
- **Response Shape:** `from hwpx.oxml.enums import TablePageBreakType`

## e2e-owpml-model-python-020: Phase 4 에러 처리

**Chain:** Error
**Status:** pending

### What
전체 하위 호환 및 에러 처리.

### Verification Criteria
- [ ] 기존 모든 테스트 통과
- [ ] GenericElement fallback 유지 (미전환 요소)
- [ ] 순환 import 없음

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| 기존 코드 호환 | 100% 유지 | OK |
| 미전환 요소 | GenericElement | OK |
| 새 파일 import | 정상 | OK |

---

## Phase 5: 통합 검증 및 C++ ↔ Python 1:1 대응 확인

## e2e-owpml-model-python-021: C++ InitMap ↔ Python parse_* 전수 비교

**Chain:** Screen
**Status:** pending

### What
모든 C++ .cpp의 InitMap/ReadAttribute와 Python parse_* 함수가 동일한 XML 요소/속성을 처리하는지 전수 비교.

### Verification Criteria
- [ ] Core 10/10 클래스 1:1 대응
- [ ] Head 107/107 클래스 1:1 대응
- [ ] Para 134/134 클래스 1:1 대응
- [ ] Etc 36/36 클래스 1:1 대응
- [ ] 총 292/292 C++ → Python 매핑 완료

### Details
- **Element:** 비교 스크립트 또는 수동 확인
- **User Action:** 클래스별 매핑 테이블 생성
- **Initial State:** 59/292 (20%)

## e2e-owpml-model-python-022: 전체 테스트 통과

**Chain:** Connection
**Status:** pending

### What
기존 + 신규 테스트 전체 통과.

### Verification Criteria
- [ ] 공식 기존 테스트 265+개 통과
- [ ] hwpx-skill 64개 통과
- [ ] 신규 Core 테스트 10+개
- [ ] 신규 Head 테스트 20+개
- [ ] 신규 Para 테스트 30+개
- [ ] 신규 Etc 테스트 10+개

### Details
- **Method:** pytest tests/
- **Endpoint:** 전체 테스트 스위트
- **Request:** 모든 테스트
- **Auth:** None

## e2e-owpml-model-python-023: __all__ 및 모듈 구조

**Chain:** Processing
**Status:** pending

### What
새 모듈 구조 및 export 목록.

### Verification Criteria
- [ ] oxml/core.py — Core 타입 + __all__
- [ ] oxml/header.py — Head 타입 확장 + __all__ 업데이트
- [ ] oxml/body.py — Para 타입 확장 + __all__ 업데이트
- [ ] oxml/para_types.py — Abstract 계층 + 도형/폼 + __all__
- [ ] oxml/etc.py — Etc 타입 + __all__
- [ ] oxml/enums.py — OWPML enum 정의 + __all__
- [ ] oxml/__init__.py — 전체 re-export 업데이트

### Details
- **Steps:**
  1. 각 모듈의 __all__ 업데이트
  2. oxml/__init__.py에서 public API re-export
- **Storage:** 모듈 파일 -- WRITE

## e2e-owpml-model-python-024: 실제 HWPX 파일 라운드트립

**Chain:** Response
**Status:** pending

### What
실제 HWPX 파일을 열고 저장했을 때 데이터 손실 없음.

### Verification Criteria
- [ ] 표 포함 HWPX — Table/Tr/Tc 전체 typed 파싱 + 라운드트립
- [ ] 도형 포함 HWPX — Picture/Arc 등 typed 파싱 + 라운드트립
- [ ] 복잡한 서식 HWPX — BorderFill, Style, TabDef 등 전체 typed
- [ ] 히스토리 포함 HWPX — History/Version typed 파싱

### Details
- **Success Status:** open → save → reopen 시 동일
- **Response Shape:** 모든 typed 필드 보존

## e2e-owpml-model-python-025: 라이선스 및 문서화

**Chain:** Error
**Status:** pending

### What
Apache 2.0 라이선스 준수, NOTICE 파일 업데이트.

### Verification Criteria
- [ ] NOTICE.txt에 hancom-io/hwpx-owpml-model 출처 명시
- [ ] 각 신규 파일에 Apache 2.0 헤더 (원본 C++ 라이선스와 동일)
- [ ] README에 OWPML 모델 전환 내용 기재

### Details
| Condition | Behavior | Status |
|-----------|----------|--------|
| 원본 Apache 2.0 | 파생물 Apache 2.0 유지 | OK |
| NOTICE 필수 | hancom-io 크레딧 | OK |
| 상업 사용 | Apache 2.0 허용 | OK |

## Deviations

_No deviations recorded yet._

---

## 구현 순서 요약

```
Phase 1: Core (10개)     → oxml/core.py 신규
Phase 2: Head (62개 추가) → oxml/header.py 확장
Phase 3: Para (122개 추가) → oxml/body.py + oxml/para_types.py
Phase 4: Etc (36개) + RDF → oxml/etc.py + oxml/enums.py
Phase 5: 통합 검증        → 292/292 확인 + 라운드트립 + 라이선스
```

## C++ 소스 참조

```
소스: https://github.com/hancom-io/hwpx-owpml-model
라이선스: Apache License 2.0
로컬 클론: /tmp/hwpx-owpml-model/
클래스 디렉토리: /tmp/hwpx-owpml-model/OWPML/Class/
  Core/  (10개) — 기반 타입
  Head/  (107개) — 문서 헤더
  Para/  (134개) — 본문/표/컨트롤/도형
  Etc/   (36개) — 히스토리/버전
  RDF/   (1개) — 메타데이터
  Root/  (4개) — 공통
```
