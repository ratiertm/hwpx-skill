"""Canonical JSON schema for HWPX documents.

Inspired by HwpForge's Core DOM structure:
  Document → Section → Paragraph → Run → Content(Text|Table|Image|Control)

Designed for LLM-friendly editing: flat JSON, no XML namespaces.
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


@dataclass
class RunContent:
    """A single run's content. Exactly one field is set."""
    type: str = "text"  # "text" | "table" | "image" | "control"
    text: Optional[str] = None
    # For table: rows of cells
    table: Optional[list] = None
    # For image: path/dimensions
    image: Optional[dict] = None


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


@dataclass
class HwpxJsonDocument:
    """Top-level JSON document structure."""
    format: str = FORMAT_VERSION
    source: str = ""
    source_sha256: str = ""
    sections: list[Section] = field(default_factory=list)
    preservation: Optional[Preservation] = None

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
                    rc = RunContent(
                        type=cd.get("type", "text"),
                        text=cd.get("text"),
                        table=cd.get("table"),
                        image=cd.get("image"),
                    )
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
        )
