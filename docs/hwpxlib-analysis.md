# hwpxlib Java Library 역분석 — python-hwpx Phase 2~5 구현 참조

> 분석 대상: https://github.com/nicedoc/hwpxlib (896 파일, 74,345줄)
> 분석 일자: 2026-03-28
> 목적: python-hwpx fork의 미구현 65개 기능 구현을 위한 참조 문서

---

## 목차

1. [아키텍처 개요](#1-아키텍처-개요)
2. [Phase 3: 도형/수식 완성](#2-phase-3-도형수식-완성)
3. [Phase 4: 필드/폼/특수 요소](#3-phase-4-필드폼특수-요소)
4. [Phase 5: OLE/차트/스타일/기타](#4-phase-5-ole차트스타일기타)
5. [Reader/Writer 패턴](#5-readerwriter-패턴)
6. [네임스페이스 & 상수](#6-네임스페이스--상수)
7. [구현 우선순위 매핑](#7-구현-우선순위-매핑)

---

## 1. 아키텍처 개요

### 패키지 구조
```
hwpxlib/
├── object/          333파일  29,932줄  — 데이터 모델 (= HWPX 스펙)
├── reader/          232파일  16,874줄  — SAX 기반 XML→Object 파싱
├── writer/          112파일   8,718줄  — Object→XML 직렬화
├── tool/            134파일   8,120줄  — 빈 파일 생성, 텍스트 추출, 검색
├── commonstrings/     9파일     911줄  — 요소명, 속성명, 네임스페이스 상수
└── util/              2파일     395줄  — 유틸리티
```

### 핵심 클래스 계층
```
HWPXObject (모든 객체 베이스)
├── ShapeObject<T>           — 크기, 위치, 캡션, 텍스트 래핑
│   ├── ShapeComponent<T>    — 변환(offset, flip, rotation, matrix)
│   │   ├── DrawingObject<T> — 선, 채우기, 그림자, 텍스트박스
│   │   │   ├── Rectangle, Ellipse, Line, Polygon, Curve
│   │   │   ├── ConnectLine, TextArt
│   │   │   └── (Arc = Ellipse with hasArcPr=true)
│   │   ├── Picture          — 이미지 (lineShape 직접 소유)
│   │   └── Container        — 그룹 (ShapeComponent[] 자식)
│   ├── Equation             — 수식 (DrawingObject 아님!)
│   └── FormObject<T>        — 폼 컨트롤
│       ├── Button, CheckButton, RadioButton
│       ├── Edit, ComboBox, ListBox, ScrollBar
│       └── (ButtonCore 중간 클래스)
├── SwitchableObject         — 선택적 컨텐츠
│   ├── Caption, DrawText    — 하위 문단 포함
│   ├── FillBrush            — WinBrush | Gradation | ImgBrush
│   └── RenderingInfo        — 변환 행렬 목록
└── CtrlItem                 — 컨트롤 요소 베이스
    ├── FieldBegin, FieldEnd — 필드 (하이퍼링크, 수식, 북마크 등)
    ├── PageNum, PageNumCtrl, AutoNum, NewNum
    ├── Header, Footer       — 머리말/꼬리말
    ├── FootNote, EndNote    — 각주/미주
    ├── Bookmark, HiddenComment, Indexmark, ColPr
    └── TrackChangeCore → InsertBegin/End, DeleteBegin/End
```

---

## 2. Phase 3: 도형/수식 완성

### 2.1 도형 공통 속성

#### ShapeSize
```python
@dataclass
class ShapeSize:
    width: int           # hwpunit (1pt = 1/72 inch)
    width_rel_to: str    # "ABSOLUTE" | "PERCENT" | "AUTO"
    height: int
    height_rel_to: str
    protect: bool        # 크기 잠금
```

#### ShapePosition
```python
@dataclass
class ShapePosition:
    treat_as_char: bool      # 글자처럼 취급 (인라인)
    affect_l_spacing: bool
    flow_with_text: bool
    allow_overlap: bool
    hold_anchor_and_so: bool
    vert_rel_to: str         # "PAGE" | "MARGIN" | "PARAGRAPH"
    horz_rel_to: str         # "PAGE" | "MARGIN" | "COLUMN"
    vert_align: str          # "TOP" | "CENTER" | "BOTTOM"
    horz_align: str          # "LEFT" | "CENTER" | "RIGHT"
    vert_offset: int         # hwpunit (부호 있음)
    horz_offset: int
```

#### ShapeComponent 변환
```python
@dataclass
class Flip:
    horizontal: bool
    vertical: bool

@dataclass
class RotationInfo:
    angle: int           # 0-360 (또는 0.01도 단위)
    center_x: int        # hwpunit
    center_y: int
    rotate_image: bool

@dataclass
class Matrix:
    e1: float; e2: float; e3: float
    e4: float; e5: float; e6: float
    # [e1 e2 0] [e3 e4 0] [e5 e6 1]
    # x' = e1*x + e3*y + e5
    # y' = e2*x + e4*y + e6
```

### 2.2 DrawingObject 공통 (선, 채우기, 그림자)

#### LineShape (외곽선 + 화살표)
```python
@dataclass
class LineShape:
    color: str               # "RRGGBB"
    width: int               # hwpunit
    style: str               # "SOLID" | "DASHED" | "DOTTED" | "DASH_DOTTED" | "DASH_DOT_DOTTED" | "DOUBLE"
    end_cap: str             # "BUTT" | "ROUND" | "SQUARE"
    # 화살표
    head_style: str          # "NORMAL" | "ARROW" | "SPEAR" | "CONCAVE_ARROW" | "EMPTY_DIAMOND" | "EMPTY_CIRCLE" | "EMPTY_BOX"
    tail_style: str
    head_fill: bool
    tail_fill: bool
    head_sz: str             # "{SMALL|MEDIUM|LARGE}_{SMALL|MEDIUM|LARGE}" (너비_길이)
    tail_sz: str
    outline_style: str       # "SHADOW_FILL" | "SHADOW_OUTLINE" | "REFLECTION"
    alpha: float             # 0.0 투명 ~ 1.0 불투명
```

#### FillBrush (채우기 — 3가지 중 택1)
```python
# 단색/패턴
@dataclass
class WinBrush:
    fore_color: str          # 기본 색
    back_color: str          # 패턴 배경색
    pattern: str             # "SOLID" | "CROSS" | "DIAGONAL" 등

# 그라데이션
@dataclass
class Gradation:
    type: str                # "LINEAR" | "RADIAL" | "RECTANGULAR" | "ELLIPTICAL" | "SQUARE"
    angle: int               # 0-359
    center_x: int
    center_y: int
    step: int
    step_center: int
    alpha: float
    colors: list[str]        # 2개 이상 색상 정지점

# 이미지 채우기
@dataclass
class ImgBrush:
    mode: str                # "TILE" | "CENTER" | "FIT" | "STRETCH"
    img: Image               # binaryItemIDRef 참조
```

#### DrawingShadow
```python
@dataclass
class DrawingShadow:
    type: str                # "NONE" | "INSIDE" | "OUTSIDE"
    color: str
    offset_x: int
    offset_y: int
    alpha: float
```

### 2.3 개별 도형

#### Rectangle
```python
ratio: int       # 모서리 둥글기: 0=직각, 20=둥근, 50=반원
pt0~pt3: Point   # 네 꼭짓점 (좌상, 우상, 우하, 좌하)
```

#### Ellipse (Arc 포함)
```python
interval_dirty: bool
has_arc_pr: bool          # True면 호(arc), False면 완전 타원
arc_type: str             # "PIE" | "CHORD" | "ARC"
center: Point
ax1, ax2: Point           # 장축/단축 끝점
start1, start2: Point     # 호 시작점 (이중 표현)
end1, end2: Point         # 호 끝점
```

#### Polygon
```python
pt_list: list[Point]      # 꼭짓점 목록 (자동 닫힘)
```

#### Curve
```python
@dataclass
class CurveSegment:
    type: str              # "LINE" | "CURVE"
    x1: int; y1: int       # 첫 번째 제어점 / 끝점
    x2: int; y2: int       # 두 번째 제어점 (CURVE일 때 베지어)

seg_list: list[CurveSegment]
```

#### ConnectLine
```python
type: str                  # "STRAIGHT" | "CURVE" | "FREEFORM"
start_pt: ConnectLinePoint # shape_obj_id, connection_id, x, y
end_pt: ConnectLinePoint
control_points: list[Point]  # 경유점
```

#### TextArt
```python
text: str
pt0~pt3: Point             # 경계점
textart_pr: TextArtPr      # 글맵시 스타일
outline: list[Point]       # 커스텀 외곽선
```

#### Container (그룹)
```python
child_list: list[ShapeComponent]  # 중첩 가능 (Container 안에 Container)
```

### 2.4 수식 (Equation)

**주의: DrawingObject가 아님 — ShapeObject를 직접 상속**

```python
@dataclass
class Equation:
    # ShapeObject 속성 (sz, pos, caption 등)
    version: str
    font: str
    base_unit: int
    base_line: int
    text_color: str
    line_mode: str           # "NONE" | "BELOW" | "THROUGH"
    script: str              # 수식 스크립트 (HasOnlyText.text())
    # fill, line, shadow 없음!
```

### 2.5 캡션 & DrawText

```python
@dataclass
class Caption:
    side: str                # "TOP" | "BOTTOM" | "LEFT" | "RIGHT"
    full_sz: bool
    width: int               # LEFT/RIGHT 모드 폭
    gap: int                 # 객체↔캡션 간격
    last_width: int
    sub_list: SubList        # 문단 목록

@dataclass
class DrawText:
    last_width: int
    name: str
    editable: bool
    text_margin: LRTB        # 내부 여백
    sub_list: SubList        # 문단 목록
```

### 2.6 Picture 효과

```python
@dataclass
class Effects:
    color: EffectsColor      # brightness, contrast
    glow: EffectsGlow        # radius, color, transparency
    shadow: EffectsShadow    # color, offset, blur, transparency
    reflection: EffectsReflection
    soft_edge: EffectsSoftEdge
```

---

## 3. Phase 4: 필드/폼/특수 요소

### 3.1 FieldBegin / FieldEnd

```python
@dataclass
class FieldBegin:              # hp:fieldBegin
    id: str
    type: str                  # FieldType enum (아래 참조)
    name: str
    editable: bool
    dirty: bool
    zorder: int
    fieldid: str
    parameters: Parameters     # hp:parameters 자식
    sub_list: SubList          # hp:subList 자식
    meta_tag: str              # hp:metaTag 자식

@dataclass
class FieldEnd:                # hp:fieldEnd
    begin_id_ref: str          # 짝이 되는 FieldBegin.id 참조
    fieldid: str

# FieldType enum 값:
# CLICK_HERE, HYPERLINK, BOOKMARK, FORMULA, SUMMARY, USER_INFO,
# DATE, DOC_DATE, PATH, CROSSREF, MAILMERGE, MEMO,
# PROOFREADING_MARKS, PRIVATE_INFO, METADATA, CITATION, BIBLIOGRAPHY
```

### 3.2 형광펜 (MarkPen)

```python
@dataclass
class MarkpenBegin:            # hp:markpenBegin (TItem)
    begin_color: str           # "RRGGBB"

class MarkpenEnd:              # hp:markpenEnd (TItem)
    pass                       # 속성 없음, 마커만
```

### 3.3 덧말/루비 (Dutmal)

```python
@dataclass
class Dutmal:                  # hp:dutmal (RunItem)
    pos_type: str              # "TOP" | "BOTTOM"
    sz_ratio: int              # 크기 비율 (%)
    option: int
    style_id_ref: str          # 문자 스타일 참조
    align: str                 # HorizontalAlign2
    main_text: str             # hp:mainText
    sub_text: str              # hp:subText (루비 텍스트)
```

### 3.4 색인 표시 (Indexmark)

```python
@dataclass
class Indexmark:               # hp:indexmark (CtrlItem)
    first_key: str             # hp:firstKey
    second_key: str            # hp:secondKey (선택)
```

### 3.5 숨은 설명 (HiddenComment)

```python
@dataclass
class HiddenComment:           # hp:hiddenComment (CtrlItem)
    sub_list: SubList          # 내부 문단
```

### 3.6 북마크 (Bookmark)

```python
@dataclass
class Bookmark:                # hp:bookmark (CtrlItem)
    name: str
```

### 3.7 자동 번호 / 페이지 번호

```python
@dataclass
class AutoNum:                 # hp:autoNum (CtrlItem)
    num: int
    num_type: str              # "PAGE" | "FOOTNOTE" | "ENDNOTE" | "PICTURE" | "TABLE" | "EQUATION" | "TOTAL_PAGE"
    auto_num_format: AutoNumFormat  # 자식 요소

@dataclass
class NewNum:                  # hp:newNum
    num: int
    num_type: str
    auto_num_format: AutoNumFormat

@dataclass
class PageNum:                 # hp:pageNum
    pos: str                   # "NONE" | "TOP_LEFT" ... "INSIDE_BOTTOM" (11가지)
    format_type: str           # NumberType1 enum
    side_char: str             # 주변 문자

@dataclass
class PageNumCtrl:             # hp:pageNumCtrl
    page_starts_on: str        # "BOTH" | "EVEN" | "ODD"

@dataclass
class AutoNumFormat:           # hp:autoNumFormat
    type: str                  # NumberType2 enum
    user_char: str             # 사용자 정의 문자
    prefix_char: str
    suffix_char: str
    supscript: bool            # 위첨자 표시
```

### 3.8 단 설정 (ColPr)

```python
@dataclass
class ColPr:                   # hp:colPr (CtrlItem)
    id: str
    type: str                  # MultiColumnType enum
    layout: str                # "VERTICAL" | "HORIZONTAL"
    col_count: int
    same_sz: bool
    same_gap: int              # hwpunit
    col_sz_list: list[ColSz]   # 개별 단 크기
    col_line: ColLine          # 구분선

@dataclass
class ColSz:
    width: int
    gap: int

@dataclass
class ColLine:
    type: str                  # LineType2
    width: str                 # LineWidth enum
    color: str                 # "RRGGBB"
```

### 3.9 특수 문자 (TItem)

```python
# 모두 속성 없는 마커 요소
class NBSpace: pass            # hp:nbSpace  — 줄바꿈 방지 공백
class FWSpace: pass            # hp:fwSpace  — 전각 공백
class Hyphen: pass             # hp:hyphen   — 소프트 하이픈

@dataclass
class Tab:                     # hp:tab
    width: int                 # hwpunit
    leader: str                # LineType2 (채움선)
    type: str                  # "LEFT" | "CENTER" | "RIGHT" | "DECIMAL"
```

### 3.10 폼 컨트롤 공통 (FormObject)

```python
@dataclass
class FormObjectBase:
    name: str
    fore_color: str
    back_color: str
    group_name: str
    tab_stop: bool
    tab_order: int
    enabled: bool
    border_type_id_ref: str
    draw_frame: bool
    printable: bool
    editable: bool
    command: str
    form_char_pr: FormCharPr
```

### 3.11 개별 폼 컨트롤

```python
@dataclass
class ComboBox(FormObjectBase):   # hp:comboBox
    list_box_rows: int
    list_box_width: int
    edit_enable: bool
    selected_value: str
    list_items: list[ListItem]    # displayText + value

@dataclass
class ListBox(FormObjectBase):    # hp:listBox
    item_height: int
    top_idx: int
    selected_value: str
    list_items: list[ListItem]

@dataclass
class Edit(FormObjectBase):       # hp:edit
    multi_line: bool
    password_char: str
    max_length: int
    scroll_bars: str              # "NONE" | "VERTICAL" | "HORIZONTAL" | "BOTH"
    tab_key_behavior: str         # "NEXT_OBJECT" | "INSERT_TAB"
    num_only: bool
    read_only: bool
    align_text: str
    text: str                     # 기본값

@dataclass
class CheckButton(FormObjectBase): # hp:checkBtn
    caption_text: str
    value: str                    # "UNCHECKED" | "CHECKED" | "INDETERMINATE"
    radio_group_name: str
    tri_state: bool
    back_style: str               # "TRANSPARENT" | "OPAQUE"

@dataclass
class RadioButton(FormObjectBase): # hp:radioBtn
    caption_text: str
    value: str
    radio_group_name: str
    tri_state: bool
    back_style: str

@dataclass
class ScrollBar(FormObjectBase):  # hp:scrollBar
    delay: int                    # ms
    large_change: int
    small_change: int
    min: int
    max: int
    page: int
    value: int
    type: str                     # "HORIZONTAL" | "VERTICAL"
```

---

## 4. Phase 5: OLE/차트/스타일/기타

### 4.1 OLE

```python
@dataclass
class OLE(ShapeComponent):        # hp:ole
    object_type: str              # "UNKNOWN" | "EMBEDDED" | "LINK" | "STATIC" | "EQUATION"
    binary_item_id_ref: str       # BinData 참조 ID → ObjectBinData/BinData{N}.bin
    has_moniker: bool
    draw_aspect: str              # "CONTENT" | "THUMB_NAIL" | "ICON" | "DOC_PRINT"
    eq_base_line: int             # 0-100 (수식용)
    extent: XAndY                 # 크기
    line_shape: LineShape         # 외곽선
```

### 4.2 Video

```python
@dataclass
class Video:
    video_type: str               # "EMBEDDED" | "LINK"
    file_id_ref: str              # 로컬 바이너리 참조
    image_id_ref: str             # 미리보기 이미지 참조
    tag: str                      # 웹 비디오 URL
```

### 4.3 Chart

```python
@dataclass
class ChartXMLFile:
    path: str                     # "ObjectId/chart1.xml"
    data: bytes                   # 차트 XML 바이너리 (별도 파서 필요)
```

### 4.4 번호 매기기 / 글머리표 (Header 정의)

```python
@dataclass
class ParaHead:                   # 1개 레벨 정의
    level: int                    # 1-7
    start: int
    align: str                    # HorizontalAlign1
    use_inst_width: bool
    auto_indent: bool
    width_adjust: int
    text_offset_type: str         # ValueUnit1
    text_offset: int
    num_format: str               # NumberType1 (arabic, roman, korean 등)
    char_pr_id_ref: str           # 번호 문자 스타일 (0xffffffff = 없음)
    checkable: bool
    text: str                     # 사용자 정의 기호

@dataclass
class Numbering:                  # hh:numbering
    id: str
    start: int
    para_head_list: list[ParaHead]  # 최대 7레벨

@dataclass
class Bullet:                     # hh:bullet
    id: str
    char: str                     # 글머리 문자
    checked_char: str
    use_image: bool
    img: Image                    # binaryItemIDRef
    para_head: ParaHead
```

### 4.5 탭 정의

```python
@dataclass
class TabPr:                      # hh:tabPr
    id: str
    auto_tab_left: bool
    auto_tab_right: bool
    tab_items: list[TabItem]

@dataclass
class TabItem:
    pos: int                      # hwpunit
    type: str                     # "LEFT" | "RIGHT" | "CENTER" | "DECIMAL"
    leader: str                   # LineType2
    unit: str                     # "hwpunit" | "%" | "char"
```

### 4.6 스타일

```python
@dataclass
class Style:                      # hh:style
    id: str
    type: str                     # "PARA" | "CHAR"
    name: str                     # 현지화 이름
    eng_name: str
    para_pr_id_ref: str           # PARA 스타일 필수
    char_pr_id_ref: str           # CHAR 스타일 필수
    next_style_id_ref: str        # 다음 문단 스타일
    lang_id: str
    lock_form: bool
```

### 4.7 BorderFill

```python
@dataclass
class BorderFill:                 # hh:borderFill
    id: str
    three_d: bool
    shadow: bool
    center_line: str
    break_cell_separate_line: bool
    left_border: Border
    right_border: Border
    top_border: Border
    bottom_border: Border
    diagonal: Border
    slash: SlashCore
    back_slash: SlashCore
    fill_brush: FillBrush         # 채우기 (Phase 3 참조)
```

### 4.8 변경 추적 (Track Change)

#### Header 레벨 정의
```python
@dataclass
class TrackChange:                # hh:trackChange
    id: str
    type: str                     # "INSERT" | "DELETE" | "PROPERTY_CHANGE"
    date: str                     # ISO 8601: "yyyy-MM-ddThh:mm:ssZ"
    author_id: str
    hide: bool
    charshape_id: str             # PROPERTY_CHANGE용
    parashape_id: str
```

#### Body 레벨 마커 (텍스트 내)
```python
@dataclass
class InsertBegin:                # hp:insertBegin (TItem)
    id: str
    tc_id: str                    # → TrackChange.id 참조
    paraend: bool

class InsertEnd:                  # hp:insertEnd
    id: str
    tc_id: str
    paraend: bool

# DeleteBegin, DeleteEnd 동일 구조
```

### 4.9 MasterPage

```python
@dataclass
class MasterPageXMLFile:
    id: str
    type: str                     # "DEFAULT_PAGE" | "OPTIONAL_PAGE" | "FIRST_PAGE"
    page_number: int              # OPTIONAL_PAGE일 때
    page_duplicate: bool
    page_front: bool
    sub_list: SubList             # 문단 (머리말/꼬리말 등)
```

### 4.10 문서 이력

```python
@dataclass
class HistoryEntry:
    revision_number: int
    revision_date: str
    revision_author: str
    revision_desc: str
    revision_lock: bool
    auto_save: bool
    package_diff: FilePartDiff
    head_diff: FilePartDiff
    body_diff: FilePartDiff

@dataclass
class FilePartDiff:
    href: str
    child_diff_list: list[DiffItem]  # InsertDiff | UpdateDiff | DeleteDiff
```

### 4.11 CompatibleDocument & ForbiddenWord

```python
@dataclass
class CompatibleDocument:
    target_program: str           # TargetProgramSort enum
    layout_compatibility: list[LayoutCompatibilityItem]

@dataclass
class ForbiddenWord:
    words: str                    # 공백 구분 금지어 목록
```

---

## 5. Reader/Writer 패턴

### 5.1 Reader (SAX 기반)

```
XMLFileReader (extends SAX DefaultHandler)
  ├── elementReader 스택 관리
  ├── startElement() → 현재 reader의 childElement() 호출
  ├── endElement() → 스택 팝
  └── characters() → 텍스트 버퍼링

ElementReader (abstract)
  ├── setAttribute(name, value)     — 속성 파싱
  ├── childElement(name, attrs)     — 자식 요소 디스패치
  ├── childElementInSwitch(...)     — switch/case 내 자식
  └── text(text)                    — 텍스트 노드

ElementReaderManager
  └── Map<Sort, Queue<ElementReader>>  — 오브젝트 풀링
```

**Python 대응**: `lxml.etree.iterparse()` 또는 `xml.sax`로 동일 패턴 구현 가능.
현재 python-hwpx는 `ElementTree`/`lxml` DOM 방식 → SAX 전환 불필요, DOM으로 충분.

### 5.2 Writer (문자열 빌더)

```
XMLStringBuilder
  ├── openElement(name)       — 요소 열기 (lazy close)
  ├── attribute(name, value)  — 속성 추가 (null이면 생략)
  ├── text(text)              — 텍스트 노드
  ├── closeElement()          — 요소 닫기
  └── escapeXmlAttr(s)        — & < > " ' 이스케이프 (& 먼저!)

ElementWriter (abstract)
  ├── write(HWPXObject)       — 메인 직렬화
  ├── writeChild(sort, obj)   — 자식 위임
  └── releaseMe()             — 풀 반환

ElementWriterManager
  └── 공유 XMLStringBuilder + 오브젝트 풀링
```

**Python 대응**: `lxml.etree.SubElement()` 체인 또는 `xml.etree.ElementTree` 사용.
현재 python-hwpx의 `LET.SubElement` 패턴이 적합.

### 5.3 속성 이스케이프 (최근 커밋)

```python
def escape_xml_attr(s: str) -> str:
    # 순서 중요: & 먼저!
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))
```

---

## 6. 네임스페이스 & 상수

### 22개 네임스페이스
```python
NAMESPACES = {
    "hp":  "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hh":  "http://www.hancom.co.kr/hwpml/2011/head",
    "hc":  "http://www.hancom.co.kr/hwpml/2011/core",
    "hs":  "http://www.hancom.co.kr/hwpml/2011/section",
    "hhs": "http://www.hancom.co.kr/hwpml/2011/history",
    "hv":  "http://www.hancom.co.kr/hwpml/2011/version",
    "odf": "urn:oasis:names:tc:opendocument:xmlns:container",
    "ocf": "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0",
    "opf": "http://www.idpf.org/2007/opf",
    # ... 기타
}

# OWPML 2024 호환 (python-hwpx에서 이미 구현)
# 2024 버전은 URI 끝이 /2024/... → /2011/...로 정규화 필요
```

### 주요 요소명 접두사 규칙
| 접두사 | 의미 | 예시 |
|--------|------|------|
| `hp:` | paragraph | hp:rect, hp:tbl, hp:fieldBegin, hp:comboBox |
| `hh:` | head/header | hh:charPr, hh:paraPr, hh:style, hh:borderFill |
| `hc:` | core | hc:pt, hc:sz, hc:pos, hc:fillBrush, hc:img |
| `hs:` | section | hs:sec, hs:p |
| `hv:` | version | hv:HCFVersion |

### 단위 체계
```
1 hwpunit = 1/72 inch = 1 point
1 cm ≈ 28.35 hwpunit
A4: 595 × 842 hwpunit (210mm × 297mm)
색상: "RRGGBB" 16진수
좌표: 좌상단 원점, X→오른쪽, Y→아래쪽
```

---

## 7. 구현 우선순위 매핑

### TODO.md ↔ hwpxlib 소스 매핑

#### Phase 3: 도형/수식 (15개)
| TODO 항목 | hwpxlib 소스 | 난이도 |
|-----------|-------------|--------|
| arc (완전 구조) | `object/.../Ellipse.java` (hasArcPr=true) | 중 |
| polygon (꼭짓점) | `object/.../Polygon.java` + ptList | 하 |
| curve (seg 배열) | `object/.../Curve.java` + CurveSegment | 중 |
| connectLine | `object/.../ConnectLine.java` | 중 |
| group container | `object/.../Container.java` + childList | 중 |
| textart | `object/.../TextArt.java` + TextArtPr | 상 |
| drawText | `object/.../drawingobject/DrawText.java` + SubList | 중 |
| equation 완성 | `object/.../Equation.java` (ShapeObject 직접 상속) | 중 |
| gradient fill | `references/borderfill/Gradation.java` | 중 |
| image fill | `references/borderfill/ImgBrush.java` | 하 |
| 화살표 | `picture/LineShape.java` headStyle/tailStyle | 하 |
| 그림자 | `drawingobject/DrawingShadow.java` | 하 |
| 좌표/회전/뒤집기 | RotationInfo + Flip + RenderingInfo | 중 |
| 캡션 | `shapeobject/Caption.java` + SubList | 중 |

#### Phase 4: 필드/폼/특수 (20개)
| TODO 항목 | hwpxlib 소스 | 난이도 |
|-----------|-------------|--------|
| checkbox | `object/.../CheckButton.java` + ButtonCore | 중 |
| radio button | `object/.../RadioButton.java` | 하 (CheckButton과 동일) |
| combo box | `object/.../ComboBox.java` + ListItem | 중 |
| list box | `object/.../ListBox.java` | 하 (ComboBox 유사) |
| edit field | `object/.../Edit.java` | 중 |
| scroll bar | `object/.../ScrollBar.java` | 하 |
| date/formula/crossref | `ctrl/FieldBegin.java` (type 분기) | 중 |
| 형광펜 | `t/MarkpenBegin.java` + `t/MarkpenEnd.java` | 하 |
| 루비/덧말 | `paragraph/Dutmal.java` | 중 |
| 색인 표시 | `ctrl/Indexmark.java` | 하 |
| 숨은 설명 | `ctrl/HiddenComment.java` | 하 |
| tab → ctrl | `t/Tab.java` (width, leader, type) | 하 |
| nbSpace/fwSpace/hyphen | `t/NBSpace.java` 등 (마커 요소) | 하 |
| autoNumFormat | `secpr/notepr/AutoNumFormat.java` | 중 |
| pageNumCtrl | `ctrl/PageNumCtrl.java` + pageHiding | 하 |

#### Phase 5: OLE/차트/기타 (25개)
| TODO 항목 | hwpxlib 소스 | 난이도 |
|-----------|-------------|--------|
| OLE | `object/.../OLE.java` + binaryItemIDRef | 상 |
| video | `object/.../Video.java` | 중 |
| chart | `chart/ChartXMLFile.java` (별도 XML) | 상 |
| 스타일 수정/삭제 | `references/Style.java` | 중 |
| numbering 정의 | `references/numbering/Numbering.java` + ParaHead | 중 |
| bullet 정의 | `references/numbering/Bullet.java` | 중 |
| tabPr 정의 | `references/TabPr.java` + TabItem | 하 |
| forbiddenWord | ForbiddenWord (단순 문자열) | 하 |
| compatibleDocument | CompatibleDocument | 하 |
| 변경 추적 | `references/TrackChange.java` + InsertBegin/End | 상 |
| 각주 번호/구분선/간격 | `secpr/notepr/FootNotePr.java` | 중 |
| 미주 모양 | `secpr/notepr/EndNotePr.java` | 중 |
| 페이지 고급 | grid, lineNumberShape, pageBorderFill | 중 |
| masterPage | `masterpage_xml/MasterPageXMLFile.java` | 상 |
| lxml/ET 통합 | (python-hwpx 자체 리팩토링) | 상 |

### 추천 구현 순서 (가성비 기준)

```
1차 (하 난이도, 즉시 가능):
  - nbSpace, fwSpace, hyphen (마커만)
  - 형광펜 (markpenBegin/End)
  - polygon, 화살표, 그림자
  - bookmark, indexmark, hiddenComment
  - tab → ctrl 변환
  - scrollBar, radioButton (기존 유사)

2차 (중 난이도, 참조 필요):
  - arc (Ellipse 확장), curve, connectLine
  - drawText, caption
  - gradient/image fill
  - combo/list box, edit, checkbox
  - dutmal (루비), autoNumFormat
  - numbering/bullet 정의, tabPr, style API
  - 회전/뒤집기

3차 (상 난이도, 깊은 분석 필요):
  - container (그룹), textart
  - OLE, video, chart
  - 변경 추적 전체
  - masterPage
  - lxml/ET 근본 리팩토링
```
