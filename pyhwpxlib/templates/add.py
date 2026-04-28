"""Register a new template — convert HWP if needed, precise fix, auto-schema, save.

Usage::

    from pyhwpxlib.templates import add
    info = add("./samples/my_form.hwp", name="my_form")
    # info = {"name": ..., "hwpx_path": ..., "schema_path": ..., "fields": N, ...}
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Optional


def add(
    input_path: str | Path,
    name: Optional[str] = None,
    *,
    shared: bool = False,
    output_dir: Optional[Path] = None,
    fix_linesegs: bool = False,
) -> dict:
    """Convert + auto-schema + save under user (default) or shared dir.

    Parameters
    ----------
    input_path : .hwp or .hwpx file
    name : ASCII template name. If None, derived from input filename via slugify.
    shared : if True, store in skill/templates/ (commit-intended). Default user dir.
    output_dir : explicit override (advanced).
    fix_linesegs : when True, apply the precise textpos-overflow fix on save.
        Default False per v0.14.0 rhwp-aligned policy — register the form
        as-is, run ``pyhwpxlib doctor`` separately if it triggers Hancom's
        security warning at fill time.
    """
    from pyhwpxlib.templates.resolver import (
        user_templates_dir,
        skill_templates_dir,
    )
    from pyhwpxlib.templates.slugify import slugify
    from pyhwpxlib.templates.auto_schema import generate_schema_from_hwpx
    from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(input_path)

    # Resolve template name (ASCII)
    if name is None:
        name = slugify(src.stem) or "template"
    name = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_") or "template"

    # Resolve target dir
    if output_dir is not None:
        target_dir = Path(output_dir)
    elif shared:
        target_dir = skill_templates_dir()
    else:
        target_dir = user_templates_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    target_hwpx = target_dir / f"{name}.hwpx"
    target_schema = target_dir / f"{name}.schema.json"

    # Convert HWP→HWPX if needed
    if src.suffix.lower() == ".hwp":
        from pyhwpxlib.hwp2hwpx import convert
        tmp_hwpx = target_dir / f"{name}._tmp.hwpx"
        convert(str(src), str(tmp_hwpx))
        intermediate = tmp_hwpx
    elif src.suffix.lower() == ".hwpx":
        intermediate = src
    else:
        raise ValueError(f"unsupported input: {src.suffix} (need .hwp or .hwpx)")

    # Write to final location. v0.14.0: do not silent-fix unless caller
    # explicitly requests it via fix_linesegs=True.
    archive = read_zip_archive(str(intermediate))
    strip_mode = "precise" if fix_linesegs else False
    write_zip_archive(str(target_hwpx), archive, strip_linesegs=strip_mode)

    # Auto-schema
    schema = generate_schema_from_hwpx(target_hwpx, name=name)
    schema["title"] = src.stem  # keep human-readable title (Korean OK)
    schema["name_kr"] = src.stem
    schema["source"] = str(src)
    target_schema.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Cleanup intermediate
    if src.suffix.lower() == ".hwp":
        try:
            (target_dir / f"{name}._tmp.hwpx").unlink()
        except FileNotFoundError:
            pass

    field_count = sum(len(t.get("fields", [])) for t in schema.get("tables", []))
    return {
        "name": name,
        "hwpx_path": str(target_hwpx),
        "schema_path": str(target_schema),
        "fields": field_count,
        "tables": len(schema.get("tables", [])),
        "source": "skill" if shared else "user",
        "title_kr": schema.get("name_kr"),
    }
