"""Workspace 헬퍼 — 자동 outputs/ 경로 생성 + SessionStart 훅 설치 (v0.17.0+).

이 모듈은 ``context.py`` (메타·이력 관리) 와 ``fill.py`` (실제 채우기) 사이의
얇은 어댑터 — 양식 채우기 시 출력 파일을 자동으로 워크스페이스 outputs/
폴더에 저장하도록 경로를 만들어주고, Claude Code SessionStart hook 설치를
도와준다.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Optional

from pyhwpxlib.templates.resolver import (
    user_workspaces_dir,
    workspace_path,
)


# ── auto output path ──────────────────────────────────────────────


def _slug_segment(text: str, max_len: int = 24) -> str:
    """파일명에 안전한 슬러그 — 한글/영문/숫자만 keep, 나머지 _."""
    text = text.strip()
    # 한글 + 영문 + 숫자 + 일부 punctuation 제외 모두 _
    cleaned = re.sub(r"[^\w가-힣\-]+", "_", text, flags=re.UNICODE)
    cleaned = cleaned.strip("_")
    return cleaned[:max_len] or "filled"


def _pick_data_key(data: dict[str, Any]) -> str:
    """data 에서 파일명 hint 추출 (의미 있는 첫 짧은 string 값)."""
    # 우선순위 1: name / 성명 / 이름 / title / 제목 키
    priority = ("name", "성명", "이름", "title", "제목", "사업명", "과제명")
    for k in priority:
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return _slug_segment(v)
    # 우선순위 2: 첫 번째 비어있지 않은 짧은 string
    for v in data.values():
        if isinstance(v, str) and 0 < len(v.strip()) <= 32:
            return _slug_segment(v)
    return "filled"


def auto_output_path(name: str, data: dict[str, Any]) -> Path:
    """워크스페이스 outputs/ 안에 ``YYYY-MM-DD_<key>.hwpx`` 생성.

    같은 이름이 이미 있으면 ``_2`` ``_3`` 자동 접미.
    """
    ws = workspace_path(name)
    outputs = ws / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    key = _pick_data_key(data)
    base = f"{today}_{key}"

    candidate = outputs / f"{base}.hwpx"
    n = 2
    while candidate.exists():
        candidate = outputs / f"{base}_{n}.hwpx"
        n += 1
    return candidate


def is_workspace_template(name: str) -> bool:
    """name 이 user 워크스페이스 (폴더 구조) 로 등록되어 있는지."""
    ws = workspace_path(name)
    return (ws / "source.hwpx").exists()


# ── SessionStart hook ─────────────────────────────────────────────


HOOK_SCRIPT = """#!/usr/bin/env python3
\"\"\"Claude Code SessionStart hook — pyhwpxlib 양식 컨텍스트 자동 안내.

워크스페이스에 등록된 양식 목록을 sessionContext 에 주입하여 새 채팅이
시작될 때 모델이 곧장 인식할 수 있게 한다.
\"\"\"
from __future__ import annotations

import json
import sys

try:
    from pyhwpxlib.templates.resolver import list_all_templates
except Exception:
    sys.exit(0)


def main() -> int:
    items = list_all_templates()
    if not items:
        return 0
    lines = [
        "## 등록된 HWPX 양식 (pyhwpxlib)",
        "",
        f"총 {len(items)}건. 양식명 언급 시 `pyhwpxlib template context <name>` 로 컨텍스트 자동 로드.",
        "",
    ]
    for it in items[:20]:
        nk = it.get("name_kr") or it["name"]
        meta = it.get("_meta") or {}
        hint = meta.get("description", "") or ""
        lines.append(f"- `{it['name']}` — {nk}" + (f"  ({hint})" if hint else ""))
    if len(items) > 20:
        lines.append(f"- … 외 {len(items)-20}건 (`pyhwpxlib template list` 로 전체)")
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\\n".join(lines),
        }
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == \"__main__\":
    sys.exit(main())
"""


def install_session_hook(target_dir: Optional[Path] = None) -> Path:
    """Claude Code SessionStart hook 스크립트를 ``~/.claude/hooks/`` 에 설치.

    Returns: 설치된 스크립트 경로.
    """
    if target_dir is None:
        target_dir = Path.home() / ".claude" / "hooks"
    target_dir.mkdir(parents=True, exist_ok=True)
    script_path = target_dir / "pyhwpxlib_session_start.py"
    script_path.write_text(HOOK_SCRIPT, encoding="utf-8")
    script_path.chmod(0o755)
    return script_path


def hook_settings_snippet(script_path: Path) -> dict:
    """settings.json 에 추가할 hook 등록 스니펫 반환 (사용자가 직접 병합)."""
    return {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "*",
                    "hooks": [
                        {"type": "command", "command": str(script_path)}
                    ],
                }
            ]
        }
    }
