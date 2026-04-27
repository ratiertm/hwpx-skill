"""Template path resolver — XDG user dir overrides bundled skill dir."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def user_templates_dir() -> Path:
    """XDG-compliant user templates dir.

    macOS / Linux: $XDG_DATA_HOME/pyhwpxlib/templates  (default ~/.local/share/...)
    Windows:       %LOCALAPPDATA%/pyhwpxlib/templates
    """
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "pyhwpxlib" / "templates"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "pyhwpxlib" / "templates"


def skill_templates_dir() -> Path:
    """Bundled skill templates dir (resolved relative to project root)."""
    # pyhwpxlib/templates/resolver.py → project_root/skill/templates
    here = Path(__file__).resolve()
    project_root = here.parent.parent.parent
    return project_root / "skill" / "templates"


def resolve_template_path(name: str, suffix: str = ".hwpx") -> Path | None:
    """Find a template file by name. User dir wins, skill dir is fallback.

    suffix: ``".hwpx"`` for the document, ``".schema.json"`` for the schema.
    """
    candidates = [
        user_templates_dir() / f"{name}{suffix}",
        skill_templates_dir() / f"{name}{suffix}",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def list_all_templates() -> list[dict]:
    """List every registered template across both tiers (user wins on name collision)."""
    seen: dict[str, dict] = {}
    for source, d in [("skill", skill_templates_dir()), ("user", user_templates_dir())]:
        if not d.exists():
            continue
        for hwpx in sorted(d.glob("*.hwpx")):
            name = hwpx.stem
            schema = d / f"{name}.schema.json"
            seen[name] = {
                "name": name,
                "hwpx_path": str(hwpx),
                "schema_path": str(schema) if schema.exists() else None,
                "source": source,
            }
    return list(seen.values())
