"""Register a new template — workspace folder structure (v0.17.0+).

v0.17.0: 양식별 폴더 (옵션 D) — `<root>/<name>/source.hwpx + schema + ...`
v0.13.3 호환: ``shared=True`` 는 skill bundle (flat) 그대로.

Usage::

    from pyhwpxlib.templates import add
    info = add("./samples/my_form.hwp", name="my_form", name_kr="내 양식")
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
    name_kr: Optional[str] = None,
    shared: bool = False,
    output_dir: Optional[Path] = None,
    fix_linesegs: bool = False,
) -> dict:
    """Register a template as a workspace folder (v0.17.0+).

    Parameters
    ----------
    input_path : .hwp or .hwpx file
    name : ASCII slug (None → derived from filename)
    name_kr : 한글 이름 (None → 원본 파일명 유지)
    shared : True 면 skill bundle (flat, commit-intended). 기본 user workspace.
    output_dir : 명시 override (advanced — 폴더가 아니라 root 만 지정).
    fix_linesegs : True 면 precise textpos-overflow fix 적용 (v0.14.0 rhwp 노선
        에서는 default False — caller 가 명시 동의 시에만).
    """
    from pyhwpxlib.templates.resolver import (
        user_workspaces_dir,
        skill_templates_dir,
    )
    from pyhwpxlib.templates.slugify import slugify
    from pyhwpxlib.templates.auto_schema import generate_schema_from_hwpx
    from pyhwpxlib.package_ops import read_zip_archive, write_zip_archive

    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(input_path)

    # 1. Slug name
    if name is None:
        name = slugify(src.stem) or "template"
    name = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_") or "template"

    if name_kr is None:
        name_kr = src.stem

    # 2. Target — workspace folder vs flat (skill bundle)
    if shared:
        # Legacy flat (개발자 번들 — skill/templates/<name>.hwpx)
        target_dir = (Path(output_dir) if output_dir is not None
                      else skill_templates_dir())
        target_dir.mkdir(parents=True, exist_ok=True)
        target_hwpx = target_dir / f"{name}.hwpx"
        target_schema = target_dir / f"{name}.schema.json"
        is_workspace = False
    else:
        # v0.17.0+ workspace folder
        root = (Path(output_dir) if output_dir is not None
                else user_workspaces_dir())
        ws_dir = root / name
        ws_dir.mkdir(parents=True, exist_ok=True)
        (ws_dir / "outputs").mkdir(exist_ok=True)
        target_hwpx = ws_dir / "source.hwpx"
        target_schema = ws_dir / "schema.json"
        is_workspace = True

    # 3. Convert HWP→HWPX if needed (intermediate file in target dir)
    if src.suffix.lower() == ".hwp":
        from pyhwpxlib.hwp2hwpx import convert
        tmp_hwpx = target_hwpx.parent / f"{name}._tmp.hwpx"
        convert(str(src), str(tmp_hwpx))
        intermediate = tmp_hwpx
    elif src.suffix.lower() == ".hwpx":
        intermediate = src
    else:
        raise ValueError(
            f"unsupported input: {src.suffix} (need .hwp or .hwpx)")

    # 4. Write final source.hwpx
    archive = read_zip_archive(str(intermediate))
    strip_mode = "precise" if fix_linesegs else False
    write_zip_archive(str(target_hwpx), archive, strip_linesegs=strip_mode)

    # 5. Auto-schema with _meta extension
    schema = generate_schema_from_hwpx(target_hwpx, name=name)
    schema["title"] = src.stem
    schema["name_kr"] = name_kr
    schema["source"] = str(src)

    if is_workspace:
        # v0.17.0+ _meta block
        from datetime import date
        schema["_meta"] = {
            "name_kr": name_kr,
            "description": "",
            "page_standard": "free",      # default; user can annotate
            "structure_type": "unknown",   # default; user can annotate
            "added_at": date.today().isoformat(),
            "last_used": None,
            "usage_count": 0,
            "notes": "",
        }

    target_schema.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 6. Workspace 초기 파일들 (decisions.md / history.json)
    if is_workspace:
        ws_dir = target_hwpx.parent
        decisions_path = ws_dir / "decisions.md"
        if not decisions_path.exists():
            decisions_path.write_text(
                f"# 결정사항: {name_kr}\n\n"
                f"<!-- 최신 항목을 위에 추가 -->\n",
                encoding="utf-8",
            )
        history_path = ws_dir / "history.json"
        if not history_path.exists():
            history_path.write_text("[]", encoding="utf-8")

    # 7. Cleanup tmp
    if src.suffix.lower() == ".hwp":
        try:
            (target_hwpx.parent / f"{name}._tmp.hwpx").unlink()
        except FileNotFoundError:
            pass

    field_count = sum(len(t.get("fields", [])) for t in schema.get("tables", []))
    return {
        "name": name,
        "name_kr": name_kr,
        "hwpx_path": str(target_hwpx),
        "schema_path": str(target_schema),
        "workspace_path": str(target_hwpx.parent) if is_workspace else None,
        "fields": field_count,
        "tables": len(schema.get("tables", [])),
        "source": "user" if is_workspace else "skill",
        "title_kr": name_kr,
    }
