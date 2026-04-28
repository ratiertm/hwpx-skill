"""Canonical JSON schema for HWPX documents.

Inspired by HwpForge's Core DOM structure:
  Document → Section → Paragraph → Run → Content(Text|Table|Image|Heading|...)

Designed for LLM-friendly editing: flat JSON, no XML namespaces.

v0.15.0: extended with rich content types so the JSON path reaches the
same expressivity as direct ``HwpxBuilder`` calls (16 add_* methods).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

FORMAT_VERSION = "pyhwpxlib-json/1"


@dataclass
class PageSettings:
    width: int = 59528
    height: int = 84186
    landscape: str = "WIDELY"
    margin_left: int = 8504
    margin_right: int = 8504
    margin_top: int = 5668
    margin_bottom: int = 4252
    header_margin: int = 4252
    footer_margin: int = 4252


# ── v0.15.0: rich content nested dataclasses ────────────────────────


@dataclass
class Heading:
    text: str = ""
    level: int = 1                           # 1, 2, 3, 4
    alignment: str = "JUSTIFY"               # JUSTIFY|LEFT|RIGHT|CENTER


@dataclass
class Image:
    image_path: Optional[str] = None         # 로컬 경로 (path 모드)
    image_url: Optional[str] = None          # URL (둘 중 하나만)
    filename: Optional[str] = None           # url 모드 전용
    width: Optional[int] = None              # HWPX 단위 (None이면 원본)
    height: Optional[int] = None


@dataclass
class HeaderFooter:
    text: str = ""


@dataclass
class PageNumber:
    pos: str = "BOTTOM_CENTER"               # BOTTOM_CENTER|BOTTOM_RIGHT|TOP_CENTER|TOP_RIGHT


@dataclass
class Footnote:
    text: str = ""
    number: int = 1


@dataclass
class Equation:
    script: str = ""


@dataclass
class Highlight:
    text: str = ""
    color: str = "#FFFF00"


@dataclass
class NestedListItem:
    depth: int = 0                           # 0~6
    text: str = ""


@dataclass
class BulletList:
    items: list[str] = field(default_factory=list)
    bullet_char: str = "-"                   # '-' | '•' | '◦'
    indent: int = 2000
    native: bool = False


@dataclass
class NumberedList:
    items: list[str] = field(default_factory=list)
    format_string: str = "^1."               # '^1.' | '^1)' | '(^1)'


@dataclass
class NestedBulletList:
    items: list[NestedListItem] = field(default_factory=list)


@dataclass
class NestedNumberedList:
    items: list[NestedListItem] = field(default_factory=list)


@dataclass
class Shape:
    """Rectangle / line / draw_line — discriminated by RunContent.type."""
    width: int = 14400
    height: int = 7200
    x1: int = 0
    y1: int = 0
    x2: int = 42520
    y2: int = 0
    line_color: str = "#000000"
    line_width: int = 283


# ── RunContent (extended) ───────────────────────────────────────────


@dataclass
class RunContent:
    """A single run's content. The ``type`` field discriminates which nested
    object is meaningful.

    Recognized ``type`` values:
        Existing (back-compat):
            "text", "table", "image"
        New in v0.15.0:
            "heading", "bullet_list", "numbered_list",
            "nested_bullet_list", "nested_numbered_list",
            "footnote", "equation", "highlight",
            "shape_rect", "shape_line", "shape_draw_line"

    For each new ``type``, populate the matching nested object below.
    """
    type: str = "text"
    # Existing:
    text: Optional[str] = None
    table: Optional[int] = None              # index into Section.tables (kept as int)
    image: Optional[Image] = None
    # v0.15.0 additions:
    heading: Optional[Heading] = None
    bullet_list: Optional[BulletList] = None
    numbered_list: Optional[NumberedList] = None
    nested_bullet_list: Optional[NestedBulletList] = None
    nested_numbered_list: Optional[NestedNumberedList] = None
    footnote: Optional[Footnote] = None
    equation: Optional[Equation] = None
    highlight: Optional[Highlight] = None
    shape: Optional[Shape] = None            # used for shape_rect / shape_draw_line


@dataclass
class Run:
    content: RunContent = field(default_factory=RunContent)
    char_shape_id: int = 0


@dataclass
class Paragraph:
    runs: list[Run] = field(default_factory=list)
    para_shape_id: int = 0
    page_break: bool = False


@dataclass
class TableCell:
    text: str = ""
    col_span: int = 1
    row_span: int = 1
    width: int = 0
    height: int = 0


@dataclass
class TableRow:
    cells: list[TableCell] = field(default_factory=list)
    height: int = 0


@dataclass
class Table:
    rows: list[TableRow] = field(default_factory=list)
    width: int = 42520
    height: int = 0
    col_widths: list[int] = field(default_factory=list)


@dataclass
class Section:
    paragraphs: list[Paragraph] = field(default_factory=list)
    page_settings: PageSettings = field(default_factory=PageSettings)
    tables: list[Table] = field(default_factory=list)


@dataclass
class Preservation:
    """Metadata for byte-preserving patch operations."""
    source_sha256: str = ""
    section_path: str = ""
    raw_header_xml: str = ""


# ── from_dict helpers (v0.15.0 nested initialization) ──────────────


def _maybe(cls, d):
    """Build dataclass instance from dict, return None if d is None/empty."""
    if d is None:
        return None
    if isinstance(d, cls):
        return d
    if not isinstance(d, dict):
        return None
    return cls(**d)


def _build_image(d) -> Optional[Image]:
    """Image accepts the legacy dict form or new Image dataclass."""
    if d is None:
        return None
    if isinstance(d, Image):
        return d
    if isinstance(d, dict):
        # Legacy dicts may have arbitrary keys; only keep recognized fields.
        return Image(
            image_path=d.get("image_path") or d.get("path"),
            image_url=d.get("image_url"),
            filename=d.get("filename"),
            width=d.get("width"),
            height=d.get("height"),
        )
    return None


def _build_nested_items(d) -> list[NestedListItem]:
    if d is None:
        return []
    items_raw = d.get("items") if isinstance(d, dict) else d
    if not items_raw:
        return []
    out = []
    for it in items_raw:
        if isinstance(it, NestedListItem):
            out.append(it)
        elif isinstance(it, dict):
            out.append(NestedListItem(depth=it.get("depth", 0), text=it.get("text", "")))
        elif isinstance(it, (list, tuple)) and len(it) == 2:
            # Allow [depth, text] form
            out.append(NestedListItem(depth=int(it[0]), text=str(it[1])))
        # else: ignore malformed entry
    return out


def _build_run_content(cd: dict) -> RunContent:
    if cd is None:
        cd = {}
    nested_b = cd.get("nested_bullet_list")
    nested_n = cd.get("nested_numbered_list")
    return RunContent(
        type=cd.get("type", "text"),
        text=cd.get("text"),
        table=cd.get("table"),
        image=_build_image(cd.get("image")),
        heading=_maybe(Heading, cd.get("heading")),
        bullet_list=_maybe(BulletList, cd.get("bullet_list")),
        numbered_list=_maybe(NumberedList, cd.get("numbered_list")),
        nested_bullet_list=(
            NestedBulletList(items=_build_nested_items(nested_b))
            if nested_b is not None else None
        ),
        nested_numbered_list=(
            NestedNumberedList(items=_build_nested_items(nested_n))
            if nested_n is not None else None
        ),
        footnote=_maybe(Footnote, cd.get("footnote")),
        equation=_maybe(Equation, cd.get("equation")),
        highlight=_maybe(Highlight, cd.get("highlight")),
        shape=_maybe(Shape, cd.get("shape")),
    )


@dataclass
class HwpxJsonDocument:
    """Top-level JSON document structure."""
    format: str = FORMAT_VERSION
    source: str = ""
    source_sha256: str = ""
    sections: list[Section] = field(default_factory=list)
    preservation: Optional[Preservation] = None
    # v0.15.0: deferred top-level elements (Whale SecPr-bug-safe order — see
    # HwpxBuilder which appends these last).
    header: Optional[HeaderFooter] = None
    footer: Optional[HeaderFooter] = None
    page_number: Optional[PageNumber] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "HwpxJsonDocument":
        sections = []
        for sd in d.get("sections", []):
            ps = PageSettings(**sd["page_settings"]) if "page_settings" in sd else PageSettings()
            paragraphs = []
            for pd in sd.get("paragraphs", []):
                runs = []
                for rd in pd.get("runs", []):
                    cd = rd.get("content", {})
                    rc = _build_run_content(cd)
                    runs.append(Run(content=rc, char_shape_id=rd.get("char_shape_id", 0)))
                paragraphs.append(Paragraph(
                    runs=runs,
                    para_shape_id=pd.get("para_shape_id", 0),
                    page_break=pd.get("page_break", False),
                ))
            tables = []
            for td in sd.get("tables", []):
                trows = []
                for trd in td.get("rows", []):
                    tcells = [TableCell(**tc) for tc in trd.get("cells", [])]
                    trows.append(TableRow(cells=tcells, height=trd.get("height", 0)))
                tables.append(Table(
                    rows=trows, width=td.get("width", 42520),
                    height=td.get("height", 0),
                    col_widths=td.get("col_widths", []),
                ))
            sections.append(Section(paragraphs=paragraphs, page_settings=ps, tables=tables))

        pres = None
        if "preservation" in d and d["preservation"]:
            pres = Preservation(**d["preservation"])

        return cls(
            format=d.get("format", FORMAT_VERSION),
            source=d.get("source", ""),
            source_sha256=d.get("source_sha256", ""),
            sections=sections,
            preservation=pres,
            header=_maybe(HeaderFooter, d.get("header")),
            footer=_maybe(HeaderFooter, d.get("footer")),
            page_number=_maybe(PageNumber, d.get("page_number")),
        )
