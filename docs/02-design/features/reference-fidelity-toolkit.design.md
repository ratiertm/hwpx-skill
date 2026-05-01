---
template: design
version: 1.2
description: page-guard CLI + analyze blueprint + 의도 룰 4개 — 모듈 시그니처와 통합 지점 설계
---

# reference-fidelity-toolkit Design Document

> **Summary**: 신규 모듈 2개 (`pyhwpxlib/page_guard.py`, `pyhwpxlib/blueprint.py`) + cli.py 명령 2개 (`page-guard`, `analyze`) + SKILL.md/RULEBOOK 의도 룰 4개. 페이지 카운트는 rhwp 1차 + OWPML static 폴백 이중 경로. blueprint 는 OWPML 만으로 인간 가독 청사진 생성. v0.15.0 → v0.16.0 (additive).
>
> **Project**: pyhwpxlib
> **Version**: 0.15.0 → 0.16.0
> **Date**: 2026-05-01
> **Status**: Draft
> **Planning Doc**: [reference-fidelity-toolkit.plan.md](../../01-plan/features/reference-fidelity-toolkit.plan.md)

---

## 1. Overview

### 1.1 Design Goals

- **A. page-guard**: 레퍼런스/결과 페이지 카운트 비교 강제 게이트. exit code 로 fail/pass 신호. CI/스크립트 통합 가능.
- **B. 의도 룰 4개**: SKILL.md + HWPX_RULEBOOK.md 양쪽에 명시. LLM 동작에 메타 가이드 주입.
- **C. analyze blueprint**: 한 명령으로 charPr/paraPr/borderFill/표/페이지 청사진 출력. 새 사용자 onboarding + LLM 컨텍스트 생성.

### 1.2 Design Principles

- **Additive only**: 기존 CLI/API 시그니처 무변경. 신규 명령·모듈만 추가.
- **이중 경로 (page-guard)**: rhwp WASM 1차 + OWPML static 폴백 — rhwp 로딩 실패 시도 동작.
- **No new deps**: lxml + 기존 rhwp_bridge 만 사용.
- **LLM 친화 JSON 출력**: text + json 양 모드 모두 지원.

### 1.3 모듈/명령 매핑

| 영역 | 신규 모듈 | CLI 명령 | 진입점 함수 |
|------|----------|---------|------------|
| A. page-guard | `pyhwpxlib/page_guard.py` | `pyhwpxlib page-guard` | `count_pages()` `compare()` `main()` |
| C. blueprint | `pyhwpxlib/blueprint.py` | `pyhwpxlib analyze --blueprint` | `analyze_blueprint()` `format_text()` `main()` |
| B. 의도 룰 | (코드 변경 없음) | — | `skill/SKILL.md` + `references/HWPX_RULEBOOK.md` 텍스트 추가 |

---

## 2. Architecture

### 2.1 page_guard.py 시그니처

```python
"""레퍼런스 vs 결과 페이지 카운트 비교 — 강제 게이트.

이중 경로:
  1. rhwp WASM (정확): RhwpEngine().load(path).page_count
  2. OWPML static (빠름·폴백): <hp:p pageBreak="1"> 카운트 + secPr 분석
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

CountMode = Literal["rhwp", "static", "auto"]


@dataclass
class PageCountResult:
    """페이지 카운트 결과.

    Attributes:
        path: 분석 대상 hwpx 경로
        pages: 페이지 수 (>=1)
        method: 어느 경로로 측정했는지 ("rhwp" 또는 "static")
        warnings: 경고 메시지 (예: "rhwp 실패, static 폴백")
    """
    path: Path
    pages: int
    method: Literal["rhwp", "static"]
    warnings: list[str]


@dataclass
class GuardResult:
    """page-guard 비교 결과.

    Attributes:
        passed: threshold 이내면 True
        reference: 레퍼런스 PageCountResult
        output: 결과 PageCountResult
        threshold: 허용 페이지 차이
        diff: output.pages - reference.pages (음수 가능)
    """
    passed: bool
    reference: PageCountResult
    output: PageCountResult
    threshold: int
    diff: int

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "reference": {"path": str(self.reference.path),
                          "pages": self.reference.pages,
                          "method": self.reference.method},
            "output": {"path": str(self.output.path),
                       "pages": self.output.pages,
                       "method": self.output.method},
            "threshold": self.threshold,
            "diff": self.diff,
        }


def count_pages(
    hwpx_path: Path | str,
    mode: CountMode = "auto",
) -> PageCountResult:
    """단일 HWPX 파일의 페이지 수 측정.

    mode:
      "auto" (default): rhwp 시도, 실패 시 static 폴백
      "rhwp"          : rhwp 만 (실패 시 RuntimeError)
      "static"        : OWPML 정적 분석만 (rhwp 안 씀)

    Raises:
        FileNotFoundError: hwpx_path 없음
        RuntimeError: mode="rhwp" 인데 rhwp 로딩 실패
    """
    ...


def compare(
    reference: Path | str,
    output: Path | str,
    threshold: int = 0,
    mode: CountMode = "auto",
) -> GuardResult:
    """레퍼런스/결과 페이지 카운트 비교."""
    ...


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리. exit code 0 (pass) / 1 (fail) / 2 (오류)."""
    ...
```

### 2.2 blueprint.py 시그니처

```python
"""HWPX 인간 가독 청사진 생성기.

OWPML 정적 분석만으로 charPr/paraPr/borderFill/표/페이지 요약.
rhwp 의존 없음 — 빠르고 가벼움.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional


@dataclass
class StyleInventory:
    """header.xml 의 스타일 ID 인벤토리."""
    char_props: list[int]      # [0, 7, 8, 10] — 사용된 charPr ID
    para_props: list[int]      # [0, 20, 21, 24] — 사용된 paraPr ID
    border_fills: list[int]    # [1, 4, 5] — 사용된 borderFill ID
    char_total: int            # itemCnt (정의된 총 개수)
    para_total: int
    border_total: int


@dataclass
class TableInfo:
    """표 1개의 요약."""
    index: int                 # 0, 1, 2 (문서 내 순번)
    rows: int
    cols: int
    col_widths: list[int]      # HWPUNIT
    has_header: bool
    has_span: bool             # rowSpan/colSpan 사용 여부
    border_fill_id: int


@dataclass
class PageInfo:
    """페이지 설정."""
    width: int                 # HWPUNIT (예: 59528 = A4 width)
    height: int                # 84186 = A4 height
    margin_left: int
    margin_right: int
    margin_top: int
    margin_bottom: int
    body_width: int            # = width - margin_left - margin_right
    pages: int                 # static count


@dataclass
class Blueprint:
    """전체 청사진."""
    path: Path
    page: PageInfo
    styles: StyleInventory
    tables: list[TableInfo]
    paragraph_count: int
    image_count: int
    page_break_count: int
    section_count: int

    def to_dict(self) -> dict:
        ...


def analyze_blueprint(hwpx_path: Path | str, depth: int = 2) -> Blueprint:
    """OWPML 파싱 → Blueprint dataclass.

    depth:
      1: 페이지 + 표 카운트만 (가장 가벼움)
      2 (default): + 스타일 인벤토리 + 표 상세
      3: + 사용 위치 / paragraph 별 스타일 분포 (가장 무거움)

    Raises:
        FileNotFoundError, lxml.etree.XMLSyntaxError
    """
    ...


def format_text(blueprint: Blueprint) -> str:
    """인간 가독 텍스트 포맷.

    예시:
        ═══ HWPX Blueprint: reference.hwpx ═══

        Page
          size:    A4 (59528 × 84186 HWPUNIT)
          margins: L/R 8504, T/B 5667
          body:    42520
          pages:   1
        ...
    """
    ...


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리."""
    ...
```

### 2.3 cli.py 통합

```python
# pyhwpxlib/cli.py 추가 부분

def _cmd_page_guard(args: argparse.Namespace) -> int:
    from . import page_guard
    result = page_guard.compare(
        reference=args.reference,
        output=args.output,
        threshold=args.threshold,
        mode=args.mode,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _format_guard_text(result)
    return 0 if result.passed else 1


def _cmd_analyze(args: argparse.Namespace) -> int:
    from . import blueprint
    if args.blueprint:
        bp = blueprint.analyze_blueprint(args.file, depth=args.depth)
        if args.json:
            print(json.dumps(bp.to_dict(), indent=2))
        else:
            print(blueprint.format_text(bp))
        return 0
    # 미래에 다른 analyze 모드 추가 시 여기에 분기
    print("error: --blueprint 옵션이 필요합니다", file=sys.stderr)
    return 2


# argparse 등록
sub_pg = subparsers.add_parser("page-guard",
    help="레퍼런스/결과 HWPX 페이지 카운트 비교 (강제 게이트)")
sub_pg.add_argument("--reference", required=True, help="기준 HWPX 경로")
sub_pg.add_argument("--output", required=True, help="검증할 HWPX 경로")
sub_pg.add_argument("--threshold", type=int, default=0,
    help="허용 페이지 차이 (default 0)")
sub_pg.add_argument("--mode", choices=["auto", "rhwp", "static"],
    default="auto", help="페이지 카운트 측정 방법")
sub_pg.add_argument("--json", action="store_true", help="JSON 출력")
sub_pg.set_defaults(func=_cmd_page_guard)

sub_an = subparsers.add_parser("analyze",
    help="HWPX 구조 분석 (인간 가독 청사진)")
sub_an.add_argument("file", help="분석할 HWPX 경로")
sub_an.add_argument("--blueprint", action="store_true",
    help="청사진 모드 (현재 유일한 모드)")
sub_an.add_argument("--depth", type=int, choices=[1, 2, 3], default=2,
    help="분석 깊이 (default 2)")
sub_an.add_argument("--json", action="store_true", help="JSON 출력")
sub_an.set_defaults(func=_cmd_analyze)
```

---

## 3. Detailed Design

### 3.1 페이지 카운트 알고리즘

#### rhwp 경로 (정확)

```python
def _count_pages_rhwp(hwpx_path: Path) -> int:
    from .rhwp_bridge import RhwpEngine
    engine = RhwpEngine()
    doc = engine.load(str(hwpx_path))
    return doc.page_count  # rhwp 가 보고하는 정확한 값
```

문제: rhwp WASM 로딩이 첫 실행 ~2초. 환경 의존.

#### static 경로 (빠름·폴백)

```python
def _count_pages_static(hwpx_path: Path) -> int:
    """OWPML 분석으로 페이지 수 추정.

    알고리즘:
      pages = 1 + count(<hp:p pageBreak="1"> 또는 <hp:p columnBreak="1">)
              + len(secPr 변경 지점)

    한계: 텍스트 길이로 인한 자동 페이지 넘김은 감지 못함.
    autofit 후 검증용으로는 부정확. rhwp 우선.
    """
    import zipfile
    from lxml import etree
    NS = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}

    pages = 1
    with zipfile.ZipFile(hwpx_path) as z:
        for name in z.namelist():
            if name.startswith("Contents/section") and name.endswith(".xml"):
                tree = etree.fromstring(z.read(name))
                pages += len(tree.xpath('.//hp:p[@pageBreak="1"]', namespaces=NS))
                pages += len(tree.xpath('.//hp:p[@columnBreak="1"]', namespaces=NS))
    return pages
```

#### auto 경로 (default)

```python
def count_pages(hwpx_path, mode="auto"):
    if mode == "static":
        return _wrap(hwpx_path, _count_pages_static, "static", [])

    warnings = []
    if mode in ("auto", "rhwp"):
        try:
            return _wrap(hwpx_path, _count_pages_rhwp, "rhwp", warnings)
        except Exception as e:
            if mode == "rhwp":
                raise RuntimeError(f"rhwp 페이지 카운트 실패: {e}")
            warnings.append(f"rhwp 실패 ({e}), static 폴백")
            return _wrap(hwpx_path, _count_pages_static, "static", warnings)
```

### 3.2 blueprint OWPML 파싱

```
Contents/header.xml
  → charProperties/charPr@id 모음 → StyleInventory.char_total
  → paraProperties/paraPr@id     → para_total
  → borderFills/borderFill@id    → border_total
  → headerSetting/page* 속성       → PageInfo

Contents/section*.xml
  → //hp:p 카운트                  → paragraph_count
  → //hp:p/@charPrIDRef 집합       → StyleInventory.char_props (used)
  → //hp:p/@paraPrIDRef 집합       → para_props (used)
  → //hp:tbl 분석                  → list[TableInfo]
  → //hp:pic 카운트                → image_count
  → //hp:p[@pageBreak="1"] 카운트  → page_break_count
```

### 3.3 format_text 출력 명세

```
═══ HWPX Blueprint: {path.name} ═══

Page
  size:    {width} × {height} HWPUNIT ({mm})
  margins: L/R {ml}/{mr}, T/B {mt}/{mb}
  body:    {body_width}
  pages:   {pages} (static count{*rhwp 보강 시 표기})

Styles
  charPr  defined {char_total} · used {char_props}
  paraPr  defined {para_total} · used {para_props}
  borderFill  defined {border_total} · used {border_fills}

Tables ({len(tables)})
  T{n}  {rows}×{cols}  cols={col_widths}  {flags}
  ...

Body
  {paragraph_count} paragraphs · {len(tables)} tables · {image_count} images
  page_break: {page_break_count}
```

depth=1 → Page + Tables 카운트만.
depth=2 (default) → 위 전체.
depth=3 → + 각 paragraph 의 charPr/paraPr 분포 히스토그램.

### 3.4 의도 룰 4개 (B)

`skill/SKILL.md` Critical Rules 표 확장:

```markdown
## Critical Rules

| # | Rule | Consequence |
|---|------|-------------|
| 1 | `<hp:t>` 안에 `\n` 금지 | Whale 에러 |
... (기존 1~9)
| 10 | **치환 우선 편집** — 양식·기존 문서 편집 시 새 노드 추가 대신 텍스트 노드 치환을 우선 | 서식 보존, 페이지 변동 최소화 |
| 11 | **구조 변경 제한** — 사용자 명시 요청 없이 `<hp:p>` `<hp:tbl>` `rowCnt` `colCnt` 추가/삭제/분할/병합 금지 | 레퍼런스 충실도 |
| 12 | **페이지 동일 필수 (레퍼런스 작업)** — 레퍼런스가 있으면 결과 쪽수가 동일해야 함 | 양식·공문 신뢰도 |
| 13 | **page-guard 통과 필수** — `pyhwpxlib validate` 통과 ≠ 완료. `pyhwpxlib page-guard` 도 통과해야 완료 처리 | 강제 게이트 |
```

`references/HWPX_RULEBOOK.md` 동기화 (상세 설명 포함).

`workflows`:
- 워크플로우 [3] 양식 채우기 Step E: page-guard 게이트 추가
- 워크플로우 [5] 공문 autofit 후 page-guard 검증 step 추가

---

## 4. Data Structures

dataclasses (`page_guard.py`):
- `PageCountResult` — 단일 측정
- `GuardResult` — 비교 결과 (`to_dict()` 직렬화)

dataclasses (`blueprint.py`):
- `PageInfo` — 페이지 설정
- `StyleInventory` — 스타일 ID 인벤토리
- `TableInfo` — 표 요약
- `Blueprint` — 전체 (`to_dict()` 직렬화)

---

## 5. Error Handling

| Error | 발생 위치 | 처리 |
|-------|----------|------|
| `FileNotFoundError` | count_pages, analyze_blueprint | exit 2, stderr "파일 없음: {path}" |
| `lxml.etree.XMLSyntaxError` | OWPML 파싱 | exit 2, stderr "XML 파싱 실패" |
| `rhwp 로딩 실패` | _count_pages_rhwp | mode=auto: 폴백 + warning. mode=rhwp: RuntimeError |
| `zipfile.BadZipFile` | static 분석 | exit 2, stderr "유효하지 않은 HWPX" |

CLI 의 모든 unexpected exception 은 `--debug` 플래그 없으면 짧은 메시지만, 있으면 traceback.

---

## 6. Testing Plan

### 6.1 page_guard tests (`tests/test_page_guard.py`)

5 테스트 케이스:

| ID | 시나리오 | 기대 |
|----|---------|------|
| T-PG-01 | ref 1p / out 1p / threshold 0 | exit 0, passed=True, diff=0 |
| T-PG-02 | ref 1p / out 2p / threshold 0 | exit 1, passed=False, diff=+1 |
| T-PG-03 | ref 1p / out 2p / threshold 1 | exit 0, passed=True, diff=+1 |
| T-PG-04 | mode=static (rhwp 안 씀) | passed 정상, method=="static" |
| T-PG-05 | --json 출력 | JSON 파싱 가능, 모든 필드 존재 |

### 6.2 blueprint tests (`tests/test_blueprint.py`)

3 테스트 케이스:

| ID | 시나리오 | 기대 |
|----|---------|------|
| T-BP-01 | 표 3개 + 50 문단 fixture | text 출력에 "Tables (3)", paragraphs=50 포함 |
| T-BP-02 | --json 출력 | JSON 파싱 가능, page/styles/tables 키 모두 존재 |
| T-BP-03 | 빈 HwpxBuilder().save() | tables=[], paragraph_count >= 1, page_count == 1 |

### 6.3 통합 회귀

기존 tests/ 107 PASS 유지 (cli.py 추가가 기존 명령에 영향 없음을 보장).

---

## 7. Implementation Order

> Plan 의 7.1 과 동일. P1(A) → P2(C) → P3(B) → P4(workflow 통합) → P5(릴리스).

### 7.1 파일별 변경

```
신규:
  pyhwpxlib/page_guard.py        ~150 LOC
  pyhwpxlib/blueprint.py         ~200 LOC
  tests/test_page_guard.py       ~120 LOC
  tests/test_blueprint.py        ~80 LOC
  tests/fixtures/ref_1page.hwpx  (HwpxBuilder 로 자동 생성)
  tests/fixtures/out_2page.hwpx  (page_break 1개 추가)

수정:
  pyhwpxlib/cli.py               +60 LOC (subparsers + dispatch)
  pyhwpxlib/__init__.py          + version bump
  pyproject.toml                 + version bump
  skill/SKILL.md                 + Critical Rules 4행 + workflow step
  skill/references/HWPX_RULEBOOK.md  + 의도 룰 상세
  scripts/update_license_date.py 호출 (0.16.0 append)
```

---

## 8. Open Questions

- [ ] `pyhwpxlib analyze` 가 향후 `--lint`, `--diagnose` 등 다른 모드를 가질 가능성 → 지금은 `--blueprint` only, 향후 확장 가능 구조로 설계 (default 가 blueprint 가 되도록)
- [ ] `page-guard` 의 `--threshold` 기본값 0 vs 1 → **0 으로 결정** (엄격 우선, 사용자가 완화 옵션)
- [ ] static fallback 의 정확도 — autofit 후 측정에서 어느 정도 차이? → rhwp 우선이라 영향 작음. T-PG-04 가 검증

---

## 9. References

- Plan: [reference-fidelity-toolkit.plan.md](../../01-plan/features/reference-fidelity-toolkit.plan.md)
- 다른 hwpx-skill SKILL.md (사용자 공유 2026-05-01) — `page_guard.py` 원형
- `pyhwpxlib/rhwp_bridge.py` — `RhwpEngine.load().page_count` 활용
- `pyhwpxlib/gongmun/autofit.py` — 페이지 카운트 → 조정 패턴
- `pyhwpxlib/doctor.py` — diagnose CLI 패턴 참조

---

## 10. Approval

- [ ] Design reviewed
- [ ] Architecture approved
- [ ] Ready for Do Phase
