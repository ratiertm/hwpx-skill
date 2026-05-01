"""v0.13.3 flat → v0.17.0 workspace folder 마이그레이션.

전제: ``~/.local/share/pyhwpxlib/templates/`` 에 v0.13.3 형식 파일들 존재
    (`<name>.hwpx`, `<name>.schema.json`)

변환 후: 같은 root 에 ``<name>/`` 폴더로 재구성
    ``<name>/source.hwpx`` ``<name>/schema.json``
    ``<name>/decisions.md`` ``<name>/history.json`` ``<name>/outputs/``

안전장치:
1. 자동 백업 (`templates_backup_v0.16.x_YYYYMMDD.tar.gz`)
2. ``--dry-run`` 모드 (미리보기, 실제 변환 zero)
3. conflict 처리 (이미 폴더 존재 시 skip)
"""
from __future__ import annotations

import json
import shutil
import tarfile
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from pyhwpxlib.templates.resolver import (
    detect_legacy_flat,
    user_workspaces_dir,
)


@dataclass
class MigrationPlan:
    """마이그레이션 사전 계획."""
    flat_files: list[Path] = field(default_factory=list)
    target_workspaces: list[Path] = field(default_factory=list)
    backup_path: Path = field(default_factory=Path)
    conflicts: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.flat_files)

    def report(self) -> str:
        lines = [
            f"=== Migration Plan (v0.13.3 flat → v0.17.0 workspace) ===",
            f"  대상 파일: {len(self.flat_files)}",
        ]
        for src, dst in zip(self.flat_files, self.target_workspaces):
            lines.append(f"    {src.name} → {dst.name}/source.hwpx")
        if self.conflicts:
            lines.append(f"  ⚠ Conflict (skip): {len(self.conflicts)}")
            for c in self.conflicts:
                lines.append(f"    - {c}")
        if self.backup_path:
            lines.append(f"  백업: {self.backup_path}")
        return "\n".join(lines)


def plan_migration(root: Optional[Path] = None) -> MigrationPlan:
    """v0.13.3 flat 구조 감지 → 마이그레이션 계획 생성."""
    if root is None:
        root = user_workspaces_dir()
    root = Path(root)

    flat_files = detect_legacy_flat() if root == user_workspaces_dir() else (
        sorted(p for p in root.glob("*.hwpx") if p.is_file())
    )

    targets: list[Path] = []
    conflicts: list[str] = []

    for hwpx in flat_files:
        name = hwpx.stem
        target_dir = root / name
        if target_dir.exists() and target_dir.is_dir():
            existing_source = target_dir / "source.hwpx"
            if existing_source.exists():
                conflicts.append(
                    f"{name}: 이미 워크스페이스 존재 (skip)")
                targets.append(target_dir)
                continue
        targets.append(target_dir)

    backup_path = root.parent / (
        f"templates_backup_v0.16.x_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar.gz"
    )

    return MigrationPlan(
        flat_files=flat_files,
        target_workspaces=targets,
        backup_path=backup_path,
        conflicts=conflicts,
    )


def execute_migration(
    plan: MigrationPlan, *,
    backup: bool = True,
    overwrite: bool = False,
) -> dict:
    """실제 마이그레이션 실행.

    Returns: {"migrated": N, "skipped": M, "backup": str|None, "errors": [...]}
    """
    if not plan.flat_files:
        return {"migrated": 0, "skipped": 0, "backup": None, "errors": []}

    root = plan.flat_files[0].parent

    # 1. 자동 백업
    backup_path: Optional[str] = None
    if backup and root.exists():
        with tarfile.open(plan.backup_path, "w:gz") as tar:
            for item in root.iterdir():
                tar.add(item, arcname=f"templates_v0.13.3/{item.name}")
        backup_path = str(plan.backup_path)

    migrated = 0
    skipped = 0
    errors: list[str] = []

    # 2. 변환 (flat → folder)
    for hwpx_path in plan.flat_files:
        name = hwpx_path.stem
        target_dir = root / name

        # Conflict check
        if target_dir.exists() and target_dir.is_dir():
            existing_source = target_dir / "source.hwpx"
            if existing_source.exists() and not overwrite:
                skipped += 1
                continue

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "outputs").mkdir(exist_ok=True)

            # source.hwpx
            shutil.copy2(hwpx_path, target_dir / "source.hwpx")

            # schema.json (flat: <name>.schema.json → schema.json)
            old_schema = hwpx_path.parent / f"{name}.schema.json"
            new_schema_path = target_dir / "schema.json"

            if old_schema.exists():
                shutil.copy2(old_schema, new_schema_path)
                # _meta block 보강 (없으면 default 추가)
                _ensure_meta(new_schema_path, name)
            else:
                # 빈 schema 라도 _meta 만 생성
                new_schema_path.write_text(
                    json.dumps({
                        "name": name,
                        "tables": [],
                        "_meta": _default_meta(name),
                    }, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

            # decisions.md / history.json 초기화
            decisions_path = target_dir / "decisions.md"
            if not decisions_path.exists():
                decisions_path.write_text(
                    f"# 결정사항: {name}\n\n"
                    f"<!-- 최신 항목을 위에 추가 -->\n\n"
                    f"## {date.today().isoformat()}\n"
                    f"- v0.13.3 → v0.17.0 마이그레이션 자동 변환\n",
                    encoding="utf-8",
                )
            history_path = target_dir / "history.json"
            if not history_path.exists():
                history_path.write_text("[]", encoding="utf-8")

            # 3. 기존 flat 파일 삭제 (백업 후라 안전)
            try:
                hwpx_path.unlink()
            except OSError:
                pass
            if old_schema.exists():
                try:
                    old_schema.unlink()
                except OSError:
                    pass

            migrated += 1

        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {type(e).__name__}: {e}")

    return {
        "migrated": migrated,
        "skipped": skipped,
        "backup": backup_path,
        "errors": errors,
    }


# ── helpers ───────────────────────────────────────────────────────


def _default_meta(name: str) -> dict:
    return {
        "name_kr": name,
        "description": "",
        "page_standard": "free",
        "structure_type": "unknown",
        "added_at": date.today().isoformat(),
        "last_used": None,
        "usage_count": 0,
        "notes": "",
        "_migrated_from": "v0.13.3",
    }


def _ensure_meta(schema_path: Path, name: str) -> None:
    """schema.json 에 _meta 블록 보강 (없으면 default 추가)."""
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    if "_meta" not in schema:
        # 기존 schema.title / name_kr 보존
        meta = _default_meta(name)
        if "name_kr" in schema:
            meta["name_kr"] = schema["name_kr"]
        elif "title" in schema:
            meta["name_kr"] = schema["title"]
        schema["_meta"] = meta
        schema_path.write_text(
            json.dumps(schema, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
