# PDCA Design: hwpx-skill-upgrade

> Plan 기반 상세 설계. 각 Phase별 구현 명세, 파일 구조, 인터페이스, 검증 방법 정의.

---

## Phase 2: HWPX_RULEBOOK 확장

### 대상 파일
- `skill/references/HWPX_RULEBOOK.md` (현재 §1~§28)
- `~/.claude/skills/hwpx/references/HWPX_RULEBOOK.md` (동기화)

### §29 Color BGR 규칙

```markdown
## 29. HWP/HWPX Color는 BGR (2026-04-14 검증)

HWP 바이너리의 색상값은 **BGR** 바이트 오더 (Blue-Green-Red).
`0xFF0000`은 빨간색이 아니라 **파란색**.

### 올바른 변환
| HWP (BGR) | RGB | 의미 |
|-----------|-----|------|
| 0x0000FF | #FF0000 | 빨간색 |
| 0xFF0000 | #0000FF | 파란색 |
| 0x00FF00 | #00FF00 | 초록색 (동일) |

### hwp2hwpx.py에서 처리
```python
# BGR → RGB 변환
bgr = 0x0000FF
r = bgr & 0xFF
g = (bgr >> 8) & 0xFF
b = (bgr >> 16) & 0xFF
rgb_hex = f"#{r:02X}{g:02X}{b:02X}"  # "#FF0000"
```

### 체크리스트
- [ ] hwp2hwpx.py의 색상 변환 코드가 BGR→RGB를 하는지 확인
- [ ] charPr의 textColor, borderFill의 색상 등 모든 경로
```

### §30 landscape 반전

```markdown
## 30. landscape 값 반전 (WIDELY=세로, NARROWLY=가로)

HWPX 스펙에서 pagePr[@landscape] 값이 **직관과 반대**:
- `WIDELY` = 세로 (portrait) — 넓게 펼친 게 아니라 세로
- `NARROWLY` = 가로 (landscape) — 좁게가 아니라 가로

### 코드에서
```python
if landscape:
    page_pr.landscape = "NARROWLY"   # 가로
else:
    page_pr.landscape = "WIDELY"     # 세로
```
혼동하기 쉬우니 반드시 주석으로 명시.
```

### §31 TextBox 구조

```markdown
## 31. TextBox = hp:rect + hp:drawText (control 아님)

HWPX에서 텍스트 박스는 독립 control이 아니라 `<hp:rect>` 안에 `<hp:drawText>`를 넣는 구조.

### 필수 요소
1. `<hp:rect>` — 외곽 도형
2. `<hp:shapeComment>` — 필수 (빈 문자열이라도)
3. `<hp:drawText>` — 텍스트 내용 (subList 포함)

### 요소 순서
shapeComment → drawText 순서 필수. 역순이면 한/글 parse error.
```

### §32 Polygon 닫힘

```markdown
## 32. Polygon 첫 꼭짓점 반복 필수

`<hp:polygon>` 또는 `<hc:polygon>`의 꼭짓점 목록에서
**마지막 점 = 첫 번째 점**이어야 닫힌 도형.

예: 삼각형 → pt1, pt2, pt3, pt1 (4점)
```

### §33 breakNonLatinWord

```markdown
## 33. breakNonLatinWord = KEEP_WORD

breakSetting에서 `breakNonLatinWord`는 `KEEP_WORD` 사용.
`BREAK_WORD` 설정 시 한글 글자가 퍼져 보임 (글자 간격 이상).
```

### 검증 방법
- 각 규칙에 코드 예시 포함
- §29는 hwp2hwpx.py 코드 검증 (BGR→RGB 변환 확인)
- 동기화: project `skill/references/` → installed `~/.claude/skills/hwpx/references/`

---

## Phase 3: Warning-first 원칙

### 대상 파일
- `pyhwpxlib/hwp2hwpx.py`

### 3-1. unknown char 경고

**현재 코드** (4곳의 `else: pass`):
```python
# 라인 ~2490
else:
    # Other control chars - skip
    pass
```

**변경**:
```python
import logging
logger = logging.getLogger(__name__)

# 라인 ~2490
else:
    logger.warning("hwp2hwpx: unknown control char %#06x at pos %d", ch, char_pos)
```

`logging` 모듈 사용 (warnings 대신). pyhwpxlib의 `__init__.py`에 이미 `logging.getLogger(__name__).addHandler(logging.NullHandler())` 있으므로 호환.

### 3-2. 변환 검증 (verify 옵션)

```python
def convert(hwp_path: str, hwpx_path: str, *, verify: bool = False) -> str:
    """..."""
    # 기존 변환 로직
    ...
    
    if verify:
        _verify_conversion(hwp_path, hwpx_path)
    return hwpx_path

def _verify_conversion(hwp_path: str, hwpx_path: str) -> None:
    """변환 전후 텍스트 비교, 누락 감지."""
    from .hwp_reader import read_hwp
    from .api import extract_text
    
    hwp_doc = read_hwp(hwp_path)
    hwp_texts = hwp_doc.texts
    hwpx_text = extract_text(hwpx_path)
    
    hwp_combined = ''.join(t.replace(' ', '') for t in hwp_texts)
    hwpx_clean = hwpx_text.replace(' ', '').replace('\n', '').replace('\t', '')
    
    if len(hwp_combined) != len(hwpx_clean):
        logger.warning(
            "hwp2hwpx verify: text length mismatch — HWP %d chars, HWPX %d chars (diff %d)",
            len(hwp_combined), len(hwpx_clean),
            len(hwp_combined) - len(hwpx_clean)
        )
    
    # 문자별 diff (누락 문자 찾기)
    missing = set(hwp_combined) - set(hwpx_clean)
    if missing:
        logger.warning("hwp2hwpx verify: chars in HWP but not in HWPX: %s", missing)
```

### 인터페이스 변경
- `convert()` 함수 시그니처에 `verify: bool = False` 추가 (하위 호환)
- CLI에서 `--verify` 플래그 추가

---

## Phase 4: Golden Tests

### 디렉터리 구조
```
tests/
  golden/
    baselines/           # 기준 텍스트/PNG 저장
      doc_sample.txt
      doc_sample_p0.png
      ...
  test_hwp2hwpx_golden.py
  test_visual_golden.py
  test_form_fill_golden.py
```

### 4-1. HWP→HWPX Golden Test

```python
# tests/test_hwp2hwpx_golden.py
import pytest
from pyhwpxlib.hwp2hwpx import convert
from pyhwpxlib.api import extract_text

GOLDEN_SAMPLES = [
    ("samples/20250224112049_9119844.hwpx", "HWP5"),  # .hwpx이지만 실제 HWP
    ("samples/ibgopongdang_230710.hwpx", "HWP5"),
    ("samples/녹색환경지원센터 설립ㆍ운영에 관한 규정(안).hwpx", "HWP5"),
    ("samples/doc_41e4v297d...v4801.hwpx", "HWP5"),
    ("samples/doc_41e4v297d...v4801 (1).hwpx", "HWP5"),
]

@pytest.mark.parametrize("src,fmt", GOLDEN_SAMPLES)
def test_hwp_to_hwpx_no_text_loss(src, fmt, tmp_path):
    """변환 후 원본 텍스트가 누락되지 않는지 검증."""
    from pyhwpxlib.hwp_reader import read_hwp
    hwp_doc = read_hwp(src)
    hwp_chars = set(''.join(hwp_doc.texts))
    
    dst = str(tmp_path / "out.hwpx")
    convert(src, dst)
    hwpx_text = extract_text(dst)
    hwpx_chars = set(hwpx_text)
    
    missing = hwp_chars - hwpx_chars - {'\r', '\x00'}
    assert not missing, f"Missing chars: {missing}"
```

### 4-2. Visual Golden Test

```python
# tests/test_visual_golden.py
import pytest
from scripts.preview import render_pages

VISUAL_SAMPLES = [
    "Test/doc_sample_fixed.hwpx",
    "Test/demo_report.hwpx",
    "Test/2020년_AFC설비_2분기_정기점검_결과.hwpx",
]

@pytest.mark.parametrize("hwpx", VISUAL_SAMPLES)
def test_visual_renders_without_error(hwpx):
    """rhwp 렌더링이 에러 없이 완료되고 PNG 생성."""
    results = render_pages(hwpx, "/tmp/golden_test")
    assert len(results) > 0
    for r in results:
        assert r["fill_ratio"] > 0.1  # 최소한 뭔가 그려짐
        assert r["svg_chars"] > 100
```

### 4-3. Form Fill Golden Test

```python
# tests/test_form_fill_golden.py
def test_opinion_form_fill_preserves_structure(tmp_path):
    """의견제출서 채우기 후 원본 구조 보존 확인."""
    # fill → extract → 채운 데이터가 포함되어 있는지
    ...
```

### 실행
```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/test_hwp2hwpx_golden.py -v
PYTHONPATH=. .venv/bin/python -m pytest tests/test_visual_golden.py -v
```

---

## Phase 5: JSON 라운드트립 + MCP 서버

### 디렉터리 구조
```
pyhwpxlib/
  json_io/
    __init__.py
    schema.py          # dataclass 정의
    encoder.py         # HWPX → JSON
    decoder.py         # JSON → HWPX
    preservation.py    # byte-preserving patch
  mcp_server/
    __init__.py
    server.py          # fastmcp 진입점
```

### 5-1. JSON 스키마 (`schema.py`)

```python
@dataclass
class HwpxJsonDocument:
    _format: str = "pyhwpxlib-json/1"
    _source_sha256: str = ""
    sections: list[HwpxJsonSection] = field(default_factory=list)
    _preservation: Optional[dict] = None

@dataclass
class HwpxJsonSection:
    page: HwpxJsonPage
    blocks: list[HwpxJsonBlock]

@dataclass
class HwpxJsonBlock:
    type: Literal["paragraph", "table", "image", "page_break"]
    # paragraph
    text: Optional[str] = None
    style: Optional[dict] = None
    # table
    rows: Optional[list] = None
    size: Optional[dict] = None
    col_widths: Optional[list] = None
```

### 5-2. Encoder (`encoder.py`)

```python
def to_json(hwpx_path: str, section: int | None = None) -> dict:
    """HWPX → JSON dict."""
    # 1. unpack
    # 2. header.xml → 폰트, 스타일 메타
    # 3. section0.xml → blocks 추출 (form_pipeline.extract_form 일반화)
    # 4. preservation 메타데이터 생성 (SHA-256, raw XML 보존)
    ...
```

**form_pipeline 레버리지**: `extract_form()`의 paragraph/table 추출 로직을 `_extract_blocks()`로 리팩터. form 전용 필드 (`_raw_*`) 는 `_preservation`으로 이동.

### 5-3. Decoder (`decoder.py`)

```python
def from_json(data: dict, output_path: str) -> str:
    """JSON dict → HWPX."""
    # HwpxBuilder 기반
    ...

def patch(hwpx_path: str, section_idx: int, data: dict, output_path: str) -> str:
    """기존 HWPX의 특정 section만 JSON으로 교체."""
    # 1. unpack
    # 2. _preservation.section_sha256 검증
    # 3. section XML만 재생성, 나머지 바이트 복사
    # 4. repack
    ...
```

### 5-4. MCP 서버 (`server.py`)

```python
from fastmcp import FastMCP

mcp = FastMCP("pyhwpxlib")

@mcp.tool()
def hwpx_to_json(file: str, section: int | None = None) -> dict: ...

@mcp.tool()
def hwpx_from_json(data: dict, output: str) -> str: ...

@mcp.tool()
def hwpx_patch(file: str, section: int, data: dict, output: str) -> str: ...

@mcp.tool()
def hwpx_inspect(file: str) -> dict: ...

@mcp.tool()
def hwpx_preview(file: str) -> list[str]: ...

@mcp.tool()
def hwpx_validate(file: str) -> dict: ...
```

**등록**: `claude mcp add pyhwpxlib -- .venv/bin/python -m pyhwpxlib.mcp_server.server`

### 검증
- `Test/*.hwpx` 5개 → to_json → from_json → extract_text 비교
- patch: section 편집 후 나머지 보존 확인
- MCP: Claude Code에서 tool call 성공

---

## Phase 6: upstream 동기화

### 6-1. airmang/python-hwpx 평가 기준

| 기능 | 코드 위치 | 통합 판단 기준 |
|------|----------|--------------|
| `table_navigation` | `tools/table_navigation.py` (457줄) | form_pipeline의 라벨 매칭 로직보다 안정적이면 채택 |
| `page_guard` | `tools/page_guard.py` (277줄) | 시각 QA 보완으로 가치 있으면 채택 |
| `template_analyzer` | `tools/template_analyzer.py` (234줄) | extract_schema와 비교, 더 범용적이면 참고 |

### 6-2. HwpForge 활용 결정

| 옵션 | 조건 | 선택 |
|------|------|------|
| MCP 병행 설치 | JSON round-trip 품질이 우리 구현보다 높으면 | Phase 5 결과 보고 결정 |
| CLI subprocess | Python 바인딩 나올 때까지 임시 | Phase 5 불필요 시 |
| 참고만 | 우리 구현이 충분하면 | 기본 |

---

## 구현 순서 (의존성 기반)

```
Phase 2 (룰북) ──┐
                  ├──→ Phase 3 (warning-first) ──→ Phase 4 (tests) ──→ Phase 5 (JSON+MCP)
Phase 6 (sync) ──┘
```

- Phase 2, 6은 독립 실행 가능 (병렬)
- Phase 3은 Phase 2 이후 (규칙 확인 후 코드 적용)
- Phase 4는 Phase 3 이후 (경고 로직 포함 상태에서 테스트)
- Phase 5는 Phase 4 이후 (테스트 인프라 위에 JSON round-trip 검증)

---

## 파일 변경 요약

| Phase | 변경 파일 | 유형 |
|-------|----------|------|
| 2 | `skill/references/HWPX_RULEBOOK.md` | 수정 |
| 2 | `~/.claude/skills/hwpx/references/HWPX_RULEBOOK.md` | 동기화 |
| 3 | `pyhwpxlib/hwp2hwpx.py` | 수정 |
| 4 | `tests/test_hwp2hwpx_golden.py` | 신규 |
| 4 | `tests/test_visual_golden.py` | 신규 |
| 4 | `tests/test_form_fill_golden.py` | 신규 |
| 4 | `tests/golden/baselines/` | 신규 (디렉터리) |
| 5 | `pyhwpxlib/json_io/__init__.py` | 신규 |
| 5 | `pyhwpxlib/json_io/schema.py` | 신규 |
| 5 | `pyhwpxlib/json_io/encoder.py` | 신규 |
| 5 | `pyhwpxlib/json_io/decoder.py` | 신규 |
| 5 | `pyhwpxlib/json_io/preservation.py` | 신규 |
| 5 | `pyhwpxlib/mcp_server/__init__.py` | 신규 |
| 5 | `pyhwpxlib/mcp_server/server.py` | 신규 |
