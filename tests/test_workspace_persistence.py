"""v0.17.0 hwpx-context-persistence — workspace + context + migration tests.

Test IDs (Plan/Design 매핑):
- T-WS-01 ~ T-WS-08  workspace folder lifecycle
- T-MIG-01 ~ T-MIG-05 v0.13.3 → v0.17.0 migration
- T-MCP-01 ~ T-MCP-03 MCP tool wrappers
- T-HOOK-01 ~ T-HOOK-02 install-hook + hook script
"""
from __future__ import annotations

import json
import os
import subprocess
import tarfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_HWPX = PROJECT_ROOT / "samples" / "(양식) 참여확인서.hwpx"


pytestmark = pytest.mark.skipif(
    not SAMPLE_HWPX.exists(), reason="sample form HWPX missing"
)


def _add_sample(name: str, root: Path) -> dict:
    os.environ["XDG_DATA_HOME"] = str(root)
    from pyhwpxlib.templates import add as tpl_add
    info = tpl_add(str(SAMPLE_HWPX), name=name)
    return info


# ─── T-WS-01 ~ T-WS-08 workspace lifecycle ─────────────────────────


def test_T_WS_01_add_creates_workspace_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    info = _add_sample("ws01", tmp_path)
    ws = tmp_path / "pyhwpxlib" / "templates" / "ws01"
    assert ws.is_dir()
    assert (ws / "source.hwpx").exists()
    assert (ws / "schema.json").exists()
    assert (ws / "decisions.md").exists()
    assert (ws / "history.json").exists()
    assert (ws / "outputs").is_dir()
    assert info["source"] == "user"
    assert info["workspace_path"] == str(ws)


def test_T_WS_02_schema_meta_block_initialized(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("ws02", tmp_path)
    schema = json.loads(
        (tmp_path / "pyhwpxlib/templates/ws02/schema.json").read_text(
            encoding="utf-8")
    )
    assert "_meta" in schema
    meta = schema["_meta"]
    assert meta["page_standard"] == "free"
    assert meta["structure_type"] == "unknown"
    assert meta["usage_count"] == 0
    assert meta["last_used"] is None


def test_T_WS_03_load_context_returns_dataclass(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("ws03", tmp_path)
    from pyhwpxlib.templates.context import load_context
    ctx = load_context("ws03")
    assert ctx.name == "ws03"
    assert ctx.usage_count == 0
    assert ctx.last_used is None
    assert ctx.recent_data is None
    md = ctx.to_markdown()
    assert "ws03" in md or ctx.name_kr in md


def test_T_WS_04_annotate_meta_and_decision(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("ws04", tmp_path)
    from pyhwpxlib.templates.context import annotate, load_context
    result = annotate(
        "ws04",
        description="단위테스트 양식",
        page_standard="1page",
        structure_type="A",
        add_decision="필드명은 한글 그대로 유지",
    )
    assert "description" in result["meta_updated"]
    assert "page_standard" in result["meta_updated"]
    assert result["decision_added"] is True

    ctx = load_context("ws04")
    assert ctx.description == "단위테스트 양식"
    assert ctx.page_standard == "1page"
    assert ctx.structure_type == "A"
    assert any("한글 그대로 유지" in t for _, t in ctx.decisions)


def test_T_WS_05_log_fill_increments_usage_and_recent(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("ws05", tmp_path)
    from pyhwpxlib.templates.context import log_fill, load_context
    info1 = log_fill("ws05", {"name": "A"})
    info2 = log_fill("ws05", {"name": "B"})
    assert info2["usage_count"] == 2
    ctx = load_context("ws05")
    assert ctx.recent_data == {"name": "B"}


def test_T_WS_06_auto_output_path_dedup(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("ws06", tmp_path)
    from pyhwpxlib.templates.workspace import auto_output_path
    p1 = auto_output_path("ws06", {"name": "홍길동"})
    p1.touch()
    p2 = auto_output_path("ws06", {"name": "홍길동"})
    assert p1 != p2
    assert p2.name.endswith("_2.hwpx")


def test_T_WS_07_fill_auto_writes_to_outputs_and_logs(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("ws07", tmp_path)
    from pyhwpxlib.templates.fill import fill_template_file
    summary = fill_template_file(
        "ws07", {"field_1": "참여확인서", "field_2": "홍길동"},
        output_path=None,
    )
    out = Path(summary["output"])
    assert out.parent.name == "outputs"
    assert out.exists()
    assert summary["history"]["usage_count"] == 1


def test_T_WS_08_list_templates_includes_workspace_metadata(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("ws08", tmp_path)
    from pyhwpxlib.templates.context import annotate
    annotate("ws08", description="abc", add_decision="a")
    from pyhwpxlib.templates import list_templates
    items = [it for it in list_templates() if it["name"] == "ws08"]
    assert items, "ws08 not in list"
    it = items[0]
    assert it["source"] == "user"
    assert it["decisions_count"] >= 1
    assert it["_meta"].get("description") == "abc"


# ─── T-MIG-01 ~ T-MIG-05 migration ──────────────────────────────────


def _make_legacy_flat(root: Path, name: str = "legacy01") -> tuple[Path, Path]:
    """Simulate v0.13.3 flat layout."""
    flat_dir = root / "pyhwpxlib" / "templates"
    flat_dir.mkdir(parents=True, exist_ok=True)
    src = SAMPLE_HWPX.read_bytes()
    flat_hwpx = flat_dir / f"{name}.hwpx"
    flat_schema = flat_dir / f"{name}.schema.json"
    flat_hwpx.write_bytes(src)
    flat_schema.write_text(
        json.dumps({"name": name, "title": "레거시 양식", "tables": []},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return flat_hwpx, flat_schema


def test_T_MIG_01_plan_detects_legacy(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    flat, _ = _make_legacy_flat(tmp_path)
    from pyhwpxlib.templates.migration import plan_migration
    plan = plan_migration()
    assert flat in plan.flat_files
    assert plan.target_workspaces[0].name == "legacy01"


def test_T_MIG_02_execute_creates_workspace_and_backup(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _make_legacy_flat(tmp_path)
    from pyhwpxlib.templates.migration import plan_migration, execute_migration
    plan = plan_migration()
    result = execute_migration(plan)
    assert result["migrated"] == 1
    assert result["backup"] is not None
    backup_path = Path(result["backup"])
    assert backup_path.exists()
    with tarfile.open(backup_path, "r:gz") as tar:
        names = tar.getnames()
        assert any("legacy01.hwpx" in n for n in names)
    ws = tmp_path / "pyhwpxlib/templates/legacy01"
    assert (ws / "source.hwpx").exists()
    assert (ws / "schema.json").exists()


def test_T_MIG_03_meta_block_added_to_legacy_schema(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _make_legacy_flat(tmp_path)
    from pyhwpxlib.templates.migration import plan_migration, execute_migration
    execute_migration(plan_migration())
    schema = json.loads(
        (tmp_path / "pyhwpxlib/templates/legacy01/schema.json").read_text(
            encoding="utf-8")
    )
    meta = schema.get("_meta") or {}
    assert meta.get("_migrated_from") == "v0.13.3"
    assert meta.get("name_kr") == "레거시 양식"


def test_T_MIG_04_dry_run_no_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    flat, schema = _make_legacy_flat(tmp_path)
    from pyhwpxlib.templates.migration import plan_migration
    plan = plan_migration()
    # dry run = simply not calling execute_migration
    assert flat.exists() and schema.exists()
    ws = tmp_path / "pyhwpxlib/templates/legacy01"
    assert not (ws / "source.hwpx").exists()


def test_T_MIG_05_conflict_detected_when_workspace_exists(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _make_legacy_flat(tmp_path, name="dup")
    # Create existing workspace with same name
    ws = tmp_path / "pyhwpxlib/templates/dup"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "source.hwpx").write_bytes(b"existing")
    from pyhwpxlib.templates.migration import plan_migration, execute_migration
    plan = plan_migration()
    assert any("dup:" in c for c in plan.conflicts)
    result = execute_migration(plan, backup=False)
    assert result["skipped"] >= 1


# ─── T-MCP-01 ~ T-MCP-03 MCP tool wrappers ──────────────────────────


def test_T_MCP_01_template_context(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("mcp01", tmp_path)
    from pyhwpxlib.mcp_server.server import hwpx_template_context
    out = json.loads(hwpx_template_context("mcp01"))
    assert out["name"] == "mcp01"
    assert "markdown" in out


def test_T_MCP_02_template_workspace_list(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("mcp02", tmp_path)
    from pyhwpxlib.mcp_server.server import hwpx_template_workspace_list
    out = json.loads(hwpx_template_workspace_list())
    assert out["count"] >= 1
    names = [t["name"] for t in out["templates"]]
    assert "mcp02" in names


def test_T_MCP_03_template_log_fill(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("mcp03", tmp_path)
    from pyhwpxlib.mcp_server.server import hwpx_template_log_fill
    out = json.loads(
        hwpx_template_log_fill("mcp03",
                                json.dumps({"name": "Tester"}))
    )
    assert out["usage_count"] == 1


# ─── T-MCP-04 ~ T-MCP-07 save_session diarization-loop closer ──────


def test_T_MCP_04_save_session_data_only(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("mcp04", tmp_path)
    from pyhwpxlib.mcp_server.server import hwpx_template_save_session
    out = json.loads(hwpx_template_save_session(
        "mcp04",
        data=json.dumps({"name": "Tester"}),
    ))
    assert out["saved"] is True
    assert out["history"] is not None
    assert out["history"]["usage_count"] == 1
    assert out["decision_added"] is False


def test_T_MCP_05_save_session_decision_only(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("mcp05", tmp_path)
    from pyhwpxlib.mcp_server.server import hwpx_template_save_session
    out = json.loads(hwpx_template_save_session(
        "mcp05",
        decision="구조 B 형, 1매 표준으로 결정",
    ))
    assert out["saved"] is True
    assert out["history"] is None
    assert out["decision_added"] is True
    # decisions.md must contain the note
    decisions = (tmp_path / "pyhwpxlib/templates/mcp05/decisions.md").read_text(
        encoding="utf-8")
    assert "구조 B 형" in decisions


def test_T_MCP_06_save_session_both(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("mcp06", tmp_path)
    from pyhwpxlib.mcp_server.server import hwpx_template_save_session
    out = json.loads(hwpx_template_save_session(
        "mcp06",
        data=json.dumps({"name": "Tester", "amount": 100}),
        decision="amount 필드는 천 단위 콤마 자동 적용",
    ))
    assert out["saved"] is True
    assert out["history"]["usage_count"] == 1
    assert out["decision_added"] is True


def test_T_MCP_07_save_session_empty_is_noop(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("mcp07", tmp_path)
    from pyhwpxlib.mcp_server.server import hwpx_template_save_session
    out = json.loads(hwpx_template_save_session("mcp07"))
    assert out["saved"] is False
    assert "reason" in out


def test_T_MCP_08_save_session_invalid_json_data(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("mcp08", tmp_path)
    from pyhwpxlib.mcp_server.server import hwpx_template_save_session
    out = json.loads(hwpx_template_save_session(
        "mcp08", data="not-json{",
    ))
    assert "error" in out


# ─── T-HOOK-01 ~ T-HOOK-02 install-hook ─────────────────────────────


def test_T_HOOK_01_install_hook_writes_executable(tmp_path):
    from pyhwpxlib.templates.workspace import install_session_hook
    p = install_session_hook(tmp_path / "hooks")
    assert p.exists()
    # 실행 가능 비트 확인
    assert os.access(p, os.X_OK)
    text = p.read_text(encoding="utf-8")
    assert "SessionStart" in text


def test_T_HOOK_02_hook_outputs_valid_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    _add_sample("hook02", tmp_path)
    from pyhwpxlib.templates.workspace import install_session_hook
    script = install_session_hook(tmp_path / "hooks")
    # 같은 XDG 로 hook script 실행
    env = dict(os.environ)
    env["XDG_DATA_HOME"] = str(tmp_path)
    res = subprocess.run(
        ["python", str(script)],
        env=env, capture_output=True, text=True, check=True,
    )
    payload = json.loads(res.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "hook02" in payload["hookSpecificOutput"]["additionalContext"]
