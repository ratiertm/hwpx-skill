#!/usr/bin/env python3
"""hwpx skill updater — sync between project, installed skill, and GitHub.

Usage:
    # Upgrade: GitHub → installed skill (no project clone needed)
    python scripts/update_skill.py upgrade
    python scripts/update_skill.py upgrade --ref v0.10.0
    python scripts/update_skill.py upgrade --repo user/fork
    python scripts/update_skill.py upgrade --yes         # no prompt

    # Push: local project → installed skill
    python scripts/update_skill.py push

    # Pull: installed skill → local project
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
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# Paths
INSTALLED = Path.home() / ".claude" / "skills" / "hwpx"
PROJECT = Path(__file__).resolve().parent.parent  # skill/ directory in project
COMMANDS_DIR = Path.home() / ".claude" / "commands"   # slash commands location

# GitHub config
DEFAULT_REPO = "ratiertm/hwpx-skill"
DEFAULT_REF = "main"
RAW_URL_TMPL = "https://raw.githubusercontent.com/{repo}/{ref}/skill/{path}"


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

# 슬래시 커맨드 — ~/.claude/commands/ 로 배포 (skill 밖)
# upgrade 시: 프로젝트 skill/commands/{name}.md → ~/.claude/commands/{name}.md
COMMAND_FILES = [
    "hwpx-update.md",
]


def file_hash(path):
    """Get MD5 hash of file."""
    if not path.exists():
        return None
    return hashlib.md5(path.read_bytes()).hexdigest()


def bytes_hash(buf: bytes) -> str:
    return hashlib.md5(buf).hexdigest()


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

    # 슬래시 커맨드: src/commands/{name}.md vs ~/.claude/commands/{name}.md
    for name in COMMAND_FILES:
        s = src / "commands" / name
        d = COMMANDS_DIR / name
        sh = file_hash(s)
        dh = file_hash(d)
        label = f"commands/{name}"
        if sh is None and dh is None:
            continue
        elif sh is None:
            print(f"  {label:<43} ✗ missing in project")
            changes += 1
        elif dh is None:
            print(f"  {label:<43} + new (not in ~/.claude/commands/)")
            changes += 1
        elif sh != dh:
            diff = s.stat().st_size - d.stat().st_size
            sign = "+" if diff > 0 else ""
            print(f"  {label:<43} ≠ changed ({sign}{diff} bytes)")
            changes += 1
        else:
            print(f"  {label:<43} ✓ same")

    print(f"\n{'─' * 60}")
    if changes == 0:
        print("✅ All files in sync.")
    else:
        print(f"⚠️  {changes} file(s) differ.")
    return changes


def sync(src, dst, label):
    """Copy files from src to dst.

    Also syncs slash commands: src/commands/{name}.md → COMMANDS_DIR/{name}.md
    (skipped on pull direction — commands are project → user only).
    """
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

    # 슬래시 커맨드 sync (push 방향: 프로젝트 skill/commands → ~/.claude/commands)
    is_push = (label == "→")
    if is_push:
        for name in COMMAND_FILES:
            s = src / "commands" / name
            d = COMMANDS_DIR / name
            if not s.exists():
                continue
            if file_hash(s) == file_hash(d):
                skipped += 1
                continue
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
            copied += 1
            print(f"  {label}: commands/{name} → ~/.claude/commands/")

    print(f"\n✅ {copied} file(s) copied, {skipped} unchanged.")
    return copied


def backup():
    """Create timestamped backup of installed skill.

    Stores OUTSIDE ~/.claude/skills/ to avoid the backup being
    auto-registered as a skill by Claude Code.
    """
    if not INSTALLED.exists():
        print("❌ No installed skill to backup.")
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = Path.home() / ".claude" / "skill_backups" / "hwpx"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_dir = backup_root / ts
    shutil.copytree(INSTALLED, backup_dir)
    print(f"✅ Backup created: {backup_dir}")
    return backup_dir


# ──────────────────────────────────────────────────────────
# GitHub upgrade
# ──────────────────────────────────────────────────────────

def _download(url: str, timeout: int = 15) -> bytes | None:
    """Download URL, return bytes. None on 404."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "hwpx-skill-updater/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def upgrade(repo: str = DEFAULT_REPO, ref: str = DEFAULT_REF,
            yes: bool = False) -> int:
    """Upgrade installed skill from GitHub.

    Downloads SYNC_FILES from raw.githubusercontent.com to a temp directory,
    shows diff, asks confirmation, then backs up and installs.

    Returns exit code (0 on success, non-zero on abort/error).
    """
    print(f"🌐 Upgrade source: github.com/{repo} @ {ref}")
    print(f"📍 Target:         {INSTALLED}")

    # 1. Download to temp
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        downloaded = []   # SYNC_FILES (relative paths under skill/)
        downloaded_cmds = []   # COMMAND_FILES (relative names)
        missing = []

        # 일반 sync 파일
        for rel in SYNC_FILES:
            url = RAW_URL_TMPL.format(repo=repo, ref=ref, path=rel)
            try:
                buf = _download(url)
            except urllib.error.URLError as e:
                print(f"\n❌ Network error: {e}")
                return 2
            if buf is None:
                missing.append(rel)
                continue
            dst = tmp_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(buf)
            downloaded.append(rel)

        # 슬래시 커맨드 (skill/commands/{name}.md)
        for name in COMMAND_FILES:
            url = RAW_URL_TMPL.format(repo=repo, ref=ref, path=f"commands/{name}")
            try:
                buf = _download(url)
            except urllib.error.URLError as e:
                print(f"\n❌ Network error: {e}")
                return 2
            if buf is None:
                missing.append(f"commands/{name}")
                continue
            dst = tmp_dir / "commands" / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(buf)
            downloaded_cmds.append(name)

        if not downloaded:
            print(f"\n❌ Nothing downloaded. Check repo/ref: {repo}@{ref}")
            return 3

        # 2. Diff preview
        print(f"\n📥 Downloaded {len(downloaded)} file(s) from GitHub.")
        if missing:
            print(f"ℹ️  {len(missing)} file(s) not present on remote "
                  f"(OK if older version): {', '.join(missing[:5])}"
                  + (f" +{len(missing) - 5} more" if len(missing) > 5 else ""))

        print(f"\n{'File':<45} {'Status'}")
        print("─" * 60)
        changes = []          # SYNC_FILES updates
        changes_cmds = []     # COMMAND_FILES updates

        for rel in downloaded:
            remote = tmp_dir / rel
            local = INSTALLED / rel
            rh = bytes_hash(remote.read_bytes())
            lh = file_hash(local)
            if lh is None:
                print(f"  {rel:<43} + new")
                changes.append(rel)
            elif rh != lh:
                diff = remote.stat().st_size - local.stat().st_size
                sign = "+" if diff > 0 else ""
                print(f"  {rel:<43} ≠ changed ({sign}{diff} bytes)")
                changes.append(rel)
            else:
                print(f"  {rel:<43} ✓ same")

        # 슬래시 커맨드 diff
        for name in downloaded_cmds:
            remote = tmp_dir / "commands" / name
            local = COMMANDS_DIR / name
            rh = bytes_hash(remote.read_bytes())
            lh = file_hash(local)
            label = f"commands/{name} (~/.claude/commands/)"
            if lh is None:
                print(f"  {label:<43} + new")
                changes_cmds.append(name)
            elif rh != lh:
                diff = remote.stat().st_size - local.stat().st_size
                sign = "+" if diff > 0 else ""
                print(f"  {label:<43} ≠ changed ({sign}{diff} bytes)")
                changes_cmds.append(name)
            else:
                print(f"  {label:<43} ✓ same")

        print("─" * 60)
        if not changes and not changes_cmds:
            print("✅ Already up to date.")
            return 0

        total = len(changes) + len(changes_cmds)
        print(f"\n⚠️  {total} file(s) will be updated "
              f"({len(changes)} skill, {len(changes_cmds)} command).")

        # 3. Confirm
        if not yes:
            try:
                answer = input("Proceed? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
            if answer not in ("y", "yes"):
                print("❎ Aborted. No changes made.")
                return 1

        # 4. Backup
        print()
        backup_dir = backup() if INSTALLED.exists() else None
        if backup_dir is None and INSTALLED.exists():
            print("❌ Backup failed. Aborting.")
            return 4

        # 5. Install — skill files
        print()
        installed_count = 0
        for rel in changes:
            src = tmp_dir / rel
            dst = INSTALLED / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            installed_count += 1
            print(f"  → {rel}")

        # Install — slash commands
        for name in changes_cmds:
            src = tmp_dir / "commands" / name
            dst = COMMANDS_DIR / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            installed_count += 1
            print(f"  → commands/{name} → ~/.claude/commands/")

        print(f"\n✅ Upgraded {installed_count} file(s) from github.com/{repo}@{ref}.")
        if backup_dir:
            print(f"💾 Backup: {backup_dir}")
            print(f"   Rollback: rm -rf {INSTALLED} && mv {backup_dir} {INSTALLED}")
        return 0


def _parse_flags(argv: list[str]) -> dict:
    """Parse --key value / --flag / positional args."""
    flags = {"repo": DEFAULT_REPO, "ref": DEFAULT_REF, "yes": False}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--yes", "-y"):
            flags["yes"] = True
        elif a == "--ref" and i + 1 < len(argv):
            flags["ref"] = argv[i + 1]
            i += 1
        elif a == "--repo" and i + 1 < len(argv):
            flags["repo"] = argv[i + 1]
            i += 1
        i += 1
    return flags


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

    elif cmd in ("upgrade", "update"):
        flags = _parse_flags(sys.argv[2:])
        sys.exit(upgrade(repo=flags["repo"], ref=flags["ref"], yes=flags["yes"]))

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
