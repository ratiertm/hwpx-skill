"""Template path resolver — workspace folder structure (v0.17.0+).

v0.17.0 폴더 구조 (옵션 D):
    ~/.local/share/pyhwpxlib/templates/
    └── <name>/
        ├── source.hwpx
        ├── schema.json
        ├── decisions.md
        ├── history.json
        └── outputs/

Backward compat: v0.13.3 flat 구조 (`<name>.hwpx` + `<name>.schema.json`) 도
인식하여 폴더 구조로 자동 인식. 마이그레이션은 ``pyhwpxlib template migrate``
참고.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

WorkspaceFile = Literal["source", "schema", "decisions", "history", "outputs"]

_FILE_NAMES: dict[str, str] = {
    "source": "source.hwpx",
    "schema": "schema.json",
    "decisions": "decisions.md",
    "history": "history.json",
    "outputs": "outputs",  # 디렉토리
}


# ── 디렉토리 경로 ──────────────────────────────────────────────────


def user_workspaces_dir() -> Path:
    """사용자 워크스페이스 root (XDG / Windows: LOCALAPPDATA).

    macOS / Linux: $XDG_DATA_HOME/pyhwpxlib/templates  (default ~/.local/share/...)
    Windows:       %LOCALAPPDATA%/pyhwpxlib/templates
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or str(
            Path.home() / "AppData" / "Local")
        return Path(base) / "pyhwpxlib" / "templates"
    base = os.environ.get("XDG_DATA_HOME") or str(
        Path.home() / ".local" / "share")
    return Path(base) / "pyhwpxlib" / "templates"


# Legacy alias (v0.13.3 호환)
def user_templates_dir() -> Path:
    """Deprecated alias for :func:`user_workspaces_dir`."""
    return user_workspaces_dir()


def skill_templates_dir() -> Path:
    """Bundled skill templates dir (project root 기준)."""
    here = Path(__file__).resolve()
    project_root = here.parent.parent.parent
    return project_root / "skill" / "templates"


# ── 워크스페이스 경로 해결 ─────────────────────────────────────────


def workspace_path(name: str) -> Path:
    """양식 워크스페이스 폴더 경로 (존재 여부 무관)."""
    return user_workspaces_dir() / name


def resolve_workspace(name: str) -> Path | None:
    """양식 워크스페이스 폴더가 존재하면 반환.

    우선순위:
      1. user 워크스페이스 (``<root>/<name>/source.hwpx`` 존재 시)
      2. skill bundle (legacy flat: ``<skill>/<name>.hwpx``)
    """
    user_ws = workspace_path(name)
    if (user_ws / "source.hwpx").exists():
        return user_ws

    # Skill bundle 은 여전히 flat (개발자 번들)
    skill_flat = skill_templates_dir() / f"{name}.hwpx"
    if skill_flat.exists():
        return skill_templates_dir()  # flat 폴더 자체 반환 (호환 모드)

    return None


def resolve_template_file(
    name: str, kind: WorkspaceFile = "source",
) -> Path | None:
    """워크스페이스 안의 파일 경로 해결.

    kind: ``"source"`` ``"schema"`` ``"decisions"`` ``"history"`` ``"outputs"``

    user 워크스페이스 (폴더) 우선, skill bundle (flat) 폴백.
    """
    if kind not in _FILE_NAMES:
        raise ValueError(f"unknown kind: {kind}")
    fname = _FILE_NAMES[kind]

    # 1. user workspace (폴더 구조)
    user_ws = workspace_path(name)
    user_file = user_ws / fname
    if user_file.exists() or kind == "outputs":
        # outputs 는 폴더라 exists() 가 빈 폴더에서도 True. fall through OK.
        if user_file.exists():
            return user_file

    # 2. skill bundle (flat — schema/source 만 존재)
    skill_dir = skill_templates_dir()
    if kind == "source":
        flat = skill_dir / f"{name}.hwpx"
        if flat.exists():
            return flat
    elif kind == "schema":
        flat = skill_dir / f"{name}.schema.json"
        if flat.exists():
            return flat

    return None


# Legacy alias (v0.13.3 호환)
def resolve_template_path(name: str, suffix: str = ".hwpx") -> Path | None:
    """Deprecated. v0.13.3 호환용. v0.17.0+ 는 :func:`resolve_template_file`.

    suffix: ``".hwpx"`` → source, ``".schema.json"`` → schema
    """
    if suffix == ".hwpx":
        return resolve_template_file(name, "source")
    if suffix == ".schema.json":
        return resolve_template_file(name, "schema")
    return None


# ── 목록 ──────────────────────────────────────────────────────────


def list_all_templates() -> list[dict]:
    """모든 등록 양식 메타 리스트.

    user 워크스페이스 (폴더 단위) + skill bundle (flat).
    user 가 같은 이름이면 우선.

    Returns
    -------
    [{"name", "name_kr", "source", "workspace_path",
      "schema_path", "outputs_count", "decisions_count",
      "_meta": {...}}, ...]
    """
    import json

    seen: dict[str, dict] = {}

    # 1. user workspaces (폴더 단위)
    user_root = user_workspaces_dir()
    if user_root.exists():
        for ws_dir in sorted(user_root.iterdir()):
            if not ws_dir.is_dir():
                continue
            source = ws_dir / "source.hwpx"
            if not source.exists():
                continue  # 빈 폴더 / 깨진 워크스페이스 skip

            schema_path = ws_dir / "schema.json"
            decisions_path = ws_dir / "decisions.md"
            outputs_dir = ws_dir / "outputs"

            meta = {}
            name_kr = ws_dir.name
            if schema_path.exists():
                try:
                    schema = json.loads(schema_path.read_text(encoding="utf-8"))
                    meta = schema.get("_meta", {})
                    name_kr = meta.get("name_kr") or schema.get(
                        "name_kr") or schema.get("title") or ws_dir.name
                except (json.JSONDecodeError, OSError):
                    pass

            outputs_count = (
                len([f for f in outputs_dir.iterdir() if f.is_file()])
                if outputs_dir.exists() else 0
            )
            decisions_count = 0
            if decisions_path.exists():
                try:
                    text = decisions_path.read_text(encoding="utf-8")
                    decisions_count = text.count("\n## ")
                except OSError:
                    pass

            seen[ws_dir.name] = {
                "name": ws_dir.name,
                "name_kr": name_kr,
                "source": "user",
                "workspace_path": str(ws_dir),
                "hwpx_path": str(source),
                "schema_path": str(schema_path) if schema_path.exists() else None,
                "outputs_count": outputs_count,
                "decisions_count": decisions_count,
                "_meta": meta,
            }

    # 2. skill bundle (flat, 개발자 번들 — user 우선)
    skill_dir = skill_templates_dir()
    if skill_dir.exists():
        for hwpx in sorted(skill_dir.glob("*.hwpx")):
            name = hwpx.stem
            if name in seen:
                continue  # user 우선
            schema = skill_dir / f"{name}.schema.json"
            seen[name] = {
                "name": name,
                "name_kr": name,
                "source": "skill",
                "workspace_path": None,
                "hwpx_path": str(hwpx),
                "schema_path": str(schema) if schema.exists() else None,
                "outputs_count": 0,
                "decisions_count": 0,
                "_meta": {},
            }

    return list(seen.values())


# ── 마이그레이션 감지 ──────────────────────────────────────────────


def detect_legacy_flat() -> list[Path]:
    """v0.13.3 flat 구조 (`<root>/<name>.hwpx`) 잔존 파일 찾기.

    v0.17.0 폴더 구조와 공존 가능. 마이그레이션 대상 식별용.
    """
    root = user_workspaces_dir()
    if not root.exists():
        return []
    return sorted(p for p in root.glob("*.hwpx") if p.is_file())
