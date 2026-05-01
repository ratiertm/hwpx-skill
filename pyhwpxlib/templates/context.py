"""Template context — workspace 폴더에서 LLM 주입용 컨텍스트 로드 (v0.17.0+).

핵심 시나리오: 새 채팅 세션에서 양식명 언급 → ``load_context(name)`` 또는
``pyhwpxlib template context <name>`` → 결정사항·이전 채우기 값 자동 복원.

데이터 소스:
- schema.json._meta — name_kr / description / structure_type / page_standard / 등
- decisions.md — 사용자 누적 결정사항 (최신 위)
- history.json — 채우기 이력 (최근 10건, FIFO)

Output:
- ``TemplateContext.to_markdown()`` — LLM paste 친화 마크다운
- ``TemplateContext.to_dict()`` — JSON 직렬화 (MCP tool 응답용)
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from pyhwpxlib.templates.resolver import (
    workspace_path,
    resolve_template_file,
)

StructureType = Literal["A", "B", "unknown"]
PageStandard = Literal["1page", "free"]


# ── dataclass ─────────────────────────────────────────────────────


@dataclass
class TemplateContext:
    """LLM 주입용 컨텍스트 데이터."""
    name: str
    name_kr: str
    description: str
    structure_type: str               # "A" | "B" | "unknown"
    page_standard: str                # "1page" | "free"
    last_used: Optional[str]
    usage_count: int
    notes: str
    workspace_path: str
    source_path: str
    fields: list[dict] = field(default_factory=list)
    decisions: list[tuple[str, str]] = field(default_factory=list)
    recent_data: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "name_kr": self.name_kr,
            "description": self.description,
            "structure_type": self.structure_type,
            "page_standard": self.page_standard,
            "last_used": self.last_used,
            "usage_count": self.usage_count,
            "notes": self.notes,
            "workspace_path": self.workspace_path,
            "source_path": self.source_path,
            "fields": self.fields,
            "decisions": [{"date": d, "text": t} for d, t in self.decisions],
            "recent_data": self.recent_data,
        }

    def to_markdown(self) -> str:
        lines = [
            f"# 양식: {self.name_kr}",
        ]
        if self.description:
            lines.append(f"> {self.description}")
        lines.append("")
        lines.append(f"- 파일: `{self.source_path}`")
        lines.append(
            f"- 구조: {self._structure_label()}"
        )
        lines.append(f"- 페이지: {self._page_label()}")
        if self.last_used:
            lines.append(
                f"- 마지막 사용: {self.last_used} (총 {self.usage_count}회)")
        else:
            lines.append("- 마지막 사용: 없음 (신규 등록)")
        if self.notes:
            lines.append(f"- 비고: {self.notes}")
        lines.append("")

        # 필드 목록
        if self.fields:
            lines.append("## 필드 목록")
            lines.append("| 키 | 레이블 | 위치 |")
            lines.append("|----|--------|------|")
            for f in self.fields[:20]:  # 최대 20개 표시
                key = f.get("key", "")
                label = f.get("label", "")
                row = f.get("row", "?")
                col = f.get("col", "?")
                tbl = f.get("table_index", "?")
                lines.append(f"| `{key}` | {label} | 표{tbl}-행{row}-열{col} |")
            if len(self.fields) > 20:
                lines.append(f"| … | (총 {len(self.fields)}개) | |")
            lines.append("")

        # 결정사항
        if self.decisions:
            lines.append("## 결정사항")
            for date, text in self.decisions[:10]:
                lines.append(f"- [{date}] {text}")
            lines.append("")

        # 최근 채우기 값
        if self.recent_data:
            lines.append("## 최근 채우기 값 (재사용 가능)")
            lines.append("```json")
            lines.append(json.dumps(self.recent_data,
                                    ensure_ascii=False, indent=2))
            lines.append("```")

        return "\n".join(lines)

    def _structure_label(self) -> str:
        return {
            "A": "A형 (인접 셀 — fill_by_labels)",
            "B": "B형 (같은 셀 patch 방식)",
            "unknown": "미판정",
        }.get(self.structure_type, "미판정")

    def _page_label(self) -> str:
        return {
            "1page": "1매 고정 (autofit 권장)",
            "free": "자유",
        }.get(self.page_standard, "자유")


# ── load ──────────────────────────────────────────────────────────


def load_context(name: str) -> TemplateContext:
    """워크스페이스에서 컨텍스트 로드.

    Raises:
        FileNotFoundError — 양식 미등록 또는 source.hwpx 없음
    """
    ws = workspace_path(name)
    source = ws / "source.hwpx"
    if not source.exists():
        # skill bundle (flat) 폴백
        source = resolve_template_file(name, "source")
        if source is None:
            raise FileNotFoundError(f"template not registered: {name}")

    # schema 로드
    schema_path = resolve_template_file(name, "schema")
    schema: dict = {}
    if schema_path and schema_path.exists():
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            schema = {}

    meta = schema.get("_meta", {}) if isinstance(schema, dict) else {}

    # 필드 평탄화 (테이블별 → 단일 list)
    fields: list[dict] = []
    for tidx, tbl in enumerate(schema.get("tables", [])):
        for f in tbl.get("fields", []):
            fields.append({**f, "table_index": tidx})

    # decisions.md 파싱
    decisions: list[tuple[str, str]] = []
    decisions_path = ws / "decisions.md"
    if decisions_path.exists():
        decisions = _parse_decisions(decisions_path.read_text(encoding="utf-8"))

    # history.json — 최근 1건 만 recent_data 로
    recent_data: Optional[dict] = None
    history_path = ws / "history.json"
    if history_path.exists():
        try:
            hist = json.loads(history_path.read_text(encoding="utf-8"))
            if hist:
                recent_data = hist[0].get("data")
        except (json.JSONDecodeError, OSError):
            pass

    return TemplateContext(
        name=name,
        name_kr=meta.get("name_kr") or schema.get("name_kr") or name,
        description=meta.get("description", ""),
        structure_type=meta.get("structure_type", "unknown"),
        page_standard=meta.get("page_standard", "free"),
        last_used=meta.get("last_used"),
        usage_count=int(meta.get("usage_count", 0) or 0),
        notes=meta.get("notes", ""),
        workspace_path=str(ws),
        source_path=str(source),
        fields=fields,
        decisions=decisions,
        recent_data=recent_data,
    )


def _parse_decisions(md: str) -> list[tuple[str, str]]:
    """decisions.md 에서 (date, text) 쌍 목록 추출 (최신 위)."""
    out: list[tuple[str, str]] = []
    current_date: Optional[str] = None
    for line in md.splitlines():
        m = re.match(r"##\s+(\d{4}-\d{2}-\d{2})\s*$", line)
        if m:
            current_date = m.group(1)
            continue
        if current_date and line.startswith("- "):
            out.append((current_date, line[2:].strip()))
    return out


# ── annotate ──────────────────────────────────────────────────────


def annotate(
    name: str, *,
    description: Optional[str] = None,
    page_standard: Optional[str] = None,
    structure_type: Optional[str] = None,
    notes: Optional[str] = None,
    add_decision: Optional[str] = None,
) -> dict:
    """schema.json._meta 갱신 + decisions.md 추기.

    Returns: {"meta_updated": [...], "decision_added": bool}
    """
    ws = workspace_path(name)
    if not ws.exists():
        raise FileNotFoundError(f"workspace not found: {name}")

    schema_path = ws / "schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8")) \
        if schema_path.exists() else {"name": name, "tables": []}

    if "_meta" not in schema:
        schema["_meta"] = {
            "name_kr": name,
            "description": "",
            "page_standard": "free",
            "structure_type": "unknown",
            "added_at": datetime.now().date().isoformat(),
            "last_used": None,
            "usage_count": 0,
            "notes": "",
        }

    meta = schema["_meta"]
    updated: list[str] = []

    if description is not None:
        meta["description"] = description
        updated.append("description")
    if page_standard is not None:
        if page_standard not in ("1page", "free"):
            raise ValueError(f"page_standard must be 1page|free")
        meta["page_standard"] = page_standard
        updated.append("page_standard")
    if structure_type is not None:
        if structure_type not in ("A", "B", "unknown"):
            raise ValueError(f"structure_type must be A|B|unknown")
        meta["structure_type"] = structure_type
        updated.append("structure_type")
    if notes is not None:
        meta["notes"] = notes
        updated.append("notes")

    if updated:
        schema_path.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    decision_added = False
    if add_decision is not None and add_decision.strip():
        _append_decision(ws, add_decision.strip())
        decision_added = True

    return {"meta_updated": updated, "decision_added": decision_added}


def _append_decision(ws: Path, text: str) -> None:
    """decisions.md 최상단에 오늘 날짜 블록으로 추기."""
    decisions_path = ws / "decisions.md"
    today = datetime.now().date().isoformat()

    if decisions_path.exists():
        existing = decisions_path.read_text(encoding="utf-8")
    else:
        existing = f"# 결정사항: {ws.name}\n\n<!-- 최신 항목을 위에 추가 -->\n"

    # 같은 날짜 블록 있으면 append, 없으면 신규 블록
    pat_today = re.compile(rf"^##\s+{re.escape(today)}\s*$", re.MULTILINE)
    m = pat_today.search(existing)

    if m:
        # 같은 날짜 블록 끝에 추가
        block_end = existing.find("\n## ", m.end())
        if block_end == -1:
            block_end = len(existing)
        new_text = (
            existing[:block_end].rstrip() + f"\n- {text}\n"
            + existing[block_end:]
        )
    else:
        # 헤더 직후 (## 첫 등장 직전 또는 파일 끝) 신규 블록 삽입
        first_h2 = existing.find("\n## ")
        if first_h2 == -1:
            # 헤더 직후
            insert_pos = existing.rfind("\n") + 1 if existing else 0
            block = f"\n## {today}\n- {text}\n"
            new_text = existing.rstrip() + block
        else:
            block = f"\n## {today}\n- {text}\n"
            new_text = existing[:first_h2] + block + existing[first_h2:]

    decisions_path.write_text(new_text, encoding="utf-8")


# ── log_fill ──────────────────────────────────────────────────────


def log_fill(
    name: str,
    data: dict[str, Any], *,
    output_path: Optional[Path | str] = None,
    max_history: int = 10,
) -> dict:
    """history.json 갱신 (FIFO max_history 건) + usage_count 증가.

    Returns: {"history_count": N, "usage_count": N}
    """
    ws = workspace_path(name)
    if not ws.exists():
        raise FileNotFoundError(f"workspace not found: {name}")

    history_path = ws / "history.json"
    if history_path.exists():
        try:
            hist = json.loads(history_path.read_text(encoding="utf-8"))
            if not isinstance(hist, list):
                hist = []
        except json.JSONDecodeError:
            hist = []
    else:
        hist = []

    entry = {
        "filled_at": datetime.now().isoformat(timespec="seconds"),
        "data": data,
    }
    if output_path is not None:
        entry["output_path"] = str(output_path)

    # 최신 위
    hist.insert(0, entry)
    hist = hist[:max_history]

    history_path.write_text(
        json.dumps(hist, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # usage_count 증가
    schema_path = ws / "schema.json"
    if schema_path.exists():
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            meta = schema.setdefault("_meta", {})
            meta["usage_count"] = int(meta.get("usage_count", 0) or 0) + 1
            meta["last_used"] = datetime.now().date().isoformat()
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            usage = meta["usage_count"]
        except (json.JSONDecodeError, OSError):
            usage = 0
    else:
        usage = 0

    return {"history_count": len(hist), "usage_count": usage}


# ── open ──────────────────────────────────────────────────────────


def open_workspace(name: str) -> int:
    """워크스페이스 폴더를 OS file manager 로 열기.

    Returns: subprocess return code (0 = success)
    Raises: FileNotFoundError
    """
    ws = workspace_path(name)
    if not ws.exists():
        raise FileNotFoundError(f"workspace not found: {name}")

    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["open", str(ws)], check=True)
        elif system == "Windows":
            os.startfile(str(ws))  # type: ignore[attr-defined]
        else:  # Linux / 기타
            subprocess.run(["xdg-open", str(ws)], check=True)
        return 0
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        return 1
