#!/usr/bin/env python3
"""hwpx skill updater — sync between project and installed skill.

Usage:
    # Push: project → installed skill
    python scripts/update_skill.py push

    # Pull: installed skill → project
    python scripts/update_skill.py pull

    # Status: show diff between project and installed
    python scripts/update_skill.py status

    # Backup: snapshot current installed skill
    python scripts/update_skill.py backup
"""
import sys
import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

# Paths
INSTALLED = Path.home() / ".claude" / "skills" / "hwpx"
PROJECT = Path(__file__).resolve().parent.parent  # skill/ directory in project

# If running from installed skill, find project skill/ via cwd
def find_project_skill():
    """Find project's skill/ directory."""
    cwd = Path.cwd()
    # Check common locations
    candidates = [
        cwd / "skill",
        cwd,
        PROJECT,
    ]
    for p in candidates:
        if (p / "SKILL.md").exists() and p != INSTALLED:
            return p
    return None


SYNC_FILES = [
    "SKILL.md",
    "chatgpt_hwpx_guide.md",
    "references/HWPX_RULEBOOK.md",
    "references/api_reference.md",
    "references/api_full.md",
    "references/document_types.md",
    "references/design_guide.md",
    "references/editing.md",
    "references/form_automation.md",
    "references/gongmun.md",
    "scripts/hwpx_helper.py",
    "scripts/update_skill.py",
    "evals/evals.json",
]


def file_hash(path):
    """Get MD5 hash of file."""
    if not path.exists():
        return None
    return hashlib.md5(path.read_bytes()).hexdigest()


def status(src, dst, direction="→"):
    """Show diff status between two directories."""
    print(f"\n{'File':<45} {'Status'}")
    print("─" * 60)
    changes = 0
    for rel in SYNC_FILES:
        s = src / rel
        d = dst / rel
        sh = file_hash(s)
        dh = file_hash(d)

        if sh is None and dh is None:
            continue
        elif sh is None:
            print(f"  {rel:<43} ✗ missing in source")
            changes += 1
        elif dh is None:
            print(f"  {rel:<43} + new (not in dest)")
            changes += 1
        elif sh != dh:
            # Show size diff
            ss = s.stat().st_size
            ds = d.stat().st_size
            diff = ss - ds
            sign = "+" if diff > 0 else ""
            print(f"  {rel:<43} ≠ changed ({sign}{diff} bytes)")
            changes += 1
        else:
            print(f"  {rel:<43} ✓ same")

    print(f"\n{'─' * 60}")
    if changes == 0:
        print("✅ All files in sync.")
    else:
        print(f"⚠️  {changes} file(s) differ.")
    return changes


def sync(src, dst, label):
    """Copy files from src to dst."""
    copied = 0
    skipped = 0
    for rel in SYNC_FILES:
        s = src / rel
        d = dst / rel
        if not s.exists():
            continue
        if file_hash(s) == file_hash(d):
            skipped += 1
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
        copied += 1
        print(f"  {label}: {rel}")

    print(f"\n✅ {copied} file(s) copied, {skipped} unchanged.")
    return copied


def backup():
    """Create timestamped backup of installed skill."""
    if not INSTALLED.exists():
        print("❌ No installed skill to backup.")
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = INSTALLED.parent / f"hwpx_backup_{ts}"
    shutil.copytree(INSTALLED, backup_dir)
    print(f"✅ Backup created: {backup_dir}")
    return backup_dir


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower()
    project = find_project_skill()

    if cmd == "status":
        if project:
            print(f"Project:   {project}")
            print(f"Installed: {INSTALLED}")
            status(project, INSTALLED)
        else:
            print("❌ Project skill/ directory not found.")

    elif cmd == "push":
        if not project:
            print("❌ Project skill/ directory not found.")
            sys.exit(1)
        print(f"Push: {project} → {INSTALLED}")
        sync(project, INSTALLED, "→")

    elif cmd == "pull":
        if not project:
            print("❌ Project skill/ directory not found.")
            sys.exit(1)
        print(f"Pull: {INSTALLED} → {project}")
        sync(INSTALLED, project, "←")

    elif cmd == "backup":
        backup()

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
