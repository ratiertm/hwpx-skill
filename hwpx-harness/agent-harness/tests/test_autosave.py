"""Tests for one-shot auto-save feature (e2e-hwpx-skill-v1-003).

SPEC: e2e-hwpx-skill-v1-003 -- Text Add Processing (auto-save)
SPEC: e2e-hwpx-skill-v1-005 -- Text Add Errors
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from click.testing import CliRunner

from cli_anything.hwpx.hwpx_cli import cli


@classmethod
def setup_runner():
    return CliRunner()


class TestAutoSave:
    """e2e-003: --file 모드에서 text add 후 파일에 자동 저장되는지 검증."""

    def test_text_add_persists_to_file(self, tmp_path):
        """text add 1회 후 text extract로 내용 확인."""
        hwpx = str(tmp_path / "test.hwpx")
        runner = CliRunner()

        # Create document
        result = runner.invoke(cli, ["document", "new", "--output", hwpx])
        assert result.exit_code == 0
        assert os.path.exists(hwpx)

        # Add text — should auto-save
        result = runner.invoke(cli, ["--file", hwpx, "text", "add", "첫 번째 문단"])
        assert result.exit_code == 0
        assert "Added paragraph" in result.output

        # Extract in new process — should see the added text
        result = runner.invoke(cli, ["--file", hwpx, "text", "extract"])
        assert result.exit_code == 0
        assert "첫 번째 문단" in result.output

    def test_consecutive_text_add_accumulates(self, tmp_path):
        """연속 text add 3회 후 모든 내용이 누적되는지 검증."""
        hwpx = str(tmp_path / "test.hwpx")
        runner = CliRunner()

        runner.invoke(cli, ["document", "new", "--output", hwpx])
        runner.invoke(cli, ["--file", hwpx, "text", "add", "문단 1"])
        runner.invoke(cli, ["--file", hwpx, "text", "add", "문단 2"])
        runner.invoke(cli, ["--file", hwpx, "text", "add", "문단 3"])

        result = runner.invoke(cli, ["--file", hwpx, "text", "extract"])
        assert "문단 1" in result.output
        assert "문단 2" in result.output
        assert "문단 3" in result.output

    def test_text_replace_persists(self, tmp_path):
        """text replace 후 변경이 파일에 저장되는지 검증."""
        hwpx = str(tmp_path / "test.hwpx")
        runner = CliRunner()

        runner.invoke(cli, ["document", "new", "--output", hwpx])
        runner.invoke(cli, ["--file", hwpx, "text", "add", "초안 문서"])

        result = runner.invoke(cli, ["--file", hwpx, "text", "replace", "--old", "초안", "--new", "최종"])
        assert result.exit_code == 0

        result = runner.invoke(cli, ["--file", hwpx, "text", "extract"])
        assert "최종 문서" in result.output
        assert "초안" not in result.output

    def test_read_only_does_not_modify_file(self, tmp_path):
        """e2e-010: 읽기 전용 명령은 파일을 수정하지 않음."""
        hwpx = str(tmp_path / "test.hwpx")
        runner = CliRunner()

        runner.invoke(cli, ["document", "new", "--output", hwpx])
        runner.invoke(cli, ["--file", hwpx, "text", "add", "내용"])

        mtime_before = os.path.getmtime(hwpx)
        runner.invoke(cli, ["--file", hwpx, "text", "extract"])
        mtime_after = os.path.getmtime(hwpx)

        assert mtime_before == mtime_after

    def test_missing_file_error(self, tmp_path):
        """e2e-005: 없는 파일 경로는 에러."""
        import cli_anything.hwpx.hwpx_cli as cli_mod
        cli_mod._session = None
        cli_mod._auto_save_path = None

        missing = str(tmp_path / "absolutely_does_not_exist.hwpx")
        runner = CliRunner()
        result = runner.invoke(cli, ["--file", missing, "text", "add", "x"])
        assert result.exit_code != 0 or result.exception is not None
