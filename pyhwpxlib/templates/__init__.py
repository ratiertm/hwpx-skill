"""User template registry — register, fill, list HWPX form templates.

Two storage tiers (resolver order, user-dir wins):

1. **User dir** (XDG default `~/.local/share/pyhwpxlib/templates/`)
   — your personal forms, not shared
2. **Skill dir** (`<package>/../skill/templates/`)
   — bundled standard forms (makers_project_report, ...)

Public API
----------
add(input_path, name=None, *, shared=False, output_dir=None) -> dict
fill(name, data, output_path) -> str
show(name) -> dict
list_templates() -> list[dict]

CLI
---
pyhwpxlib template add <hwp_or_hwpx> [--name NAME] [--shared]
pyhwpxlib template fill <name> -d data.json -o out.hwpx
pyhwpxlib template show <name>
pyhwpxlib template list
"""
from pyhwpxlib.templates.resolver import (
    user_templates_dir,
    skill_templates_dir,
    resolve_template_path,
    list_all_templates,
)
from pyhwpxlib.templates.slugify import slugify, label_to_key
from pyhwpxlib.templates.auto_schema import generate_schema
from pyhwpxlib.templates.fill import fill_template_file as fill
from pyhwpxlib.templates.add import add

__all__ = [
    "add",
    "fill",
    "show",
    "list_templates",
    "user_templates_dir",
    "skill_templates_dir",
    "resolve_template_path",
    "slugify",
    "label_to_key",
    "generate_schema",
]


def show(name: str) -> dict:
    """Return parsed schema dict (raises FileNotFoundError if not registered)."""
    import json
    schema_path = resolve_template_path(name, suffix=".schema.json")
    if schema_path is None:
        raise FileNotFoundError(f"template not found: {name}")
    return json.loads(schema_path.read_text(encoding="utf-8"))


def list_templates() -> list[dict]:
    """Return [{name, hwpx_path, schema_path, source: 'user'|'skill'}, ...]."""
    return list_all_templates()
