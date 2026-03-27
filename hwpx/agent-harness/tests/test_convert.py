"""Tests for file convert feature (e2e-hwpx-skill-v1-021~025).

SPEC: e2e-hwpx-skill-v1-021 -- File Upload Screen
SPEC: e2e-hwpx-skill-v1-022 -- File Upload Parse Connection
SPEC: e2e-hwpx-skill-v1-023 -- File Convert Processing
SPEC: e2e-hwpx-skill-v1-024 -- File Convert Response
SPEC: e2e-hwpx-skill-v1-025 -- File Convert Errors
"""

from __future__ import annotations

import os
from pathlib import Path

from click.testing import CliRunner

from cli_anything.hwpx.hwpx_cli import cli
from cli_anything.hwpx.core import document as doc_mod
from cli_anything.hwpx.core import text as text_mod


class TestConvertHTML:
    """e2e-022: HTML 파일 파싱 및 변환."""

    def test_html_to_hwpx(self, tmp_path):
        src = tmp_path / "source.html"
        src.write_text("<h1>제목</h1><p>본문입니다.</p><ul><li>항목1</li><li>항목2</li></ul>", encoding="utf-8")
        out = str(tmp_path / "output.hwpx")

        runner = CliRunner()
        result = runner.invoke(cli, ["convert", str(src), "-o", out])

        assert result.exit_code == 0
        assert "Converted" in result.output
        assert "paragraphs" in result.output
        assert os.path.exists(out)

        # Verify content
        doc = doc_mod.open_document(out)
        text = text_mod.extract_text(doc)
        assert "제목" in text
        assert "본문" in text

    def test_html_tags_stripped(self, tmp_path):
        src = tmp_path / "tags.html"
        src.write_text("<div><b>굵은글씨</b> 일반글씨</div>", encoding="utf-8")
        out = str(tmp_path / "output.hwpx")

        runner = CliRunner()
        runner.invoke(cli, ["convert", str(src), "-o", out])

        doc = doc_mod.open_document(out)
        text = text_mod.extract_text(doc)
        assert "굵은글씨" in text
        assert "<b>" not in text


class TestConvertMarkdown:
    """e2e-022: Markdown 파일 파싱 및 변환."""

    def test_markdown_to_hwpx(self, tmp_path):
        src = tmp_path / "source.md"
        src.write_text("# 제목\n\n본문입니다.\n\n- 항목1\n- 항목2\n", encoding="utf-8")
        out = str(tmp_path / "output.hwpx")

        runner = CliRunner()
        result = runner.invoke(cli, ["convert", str(src), "-o", out])

        assert result.exit_code == 0
        doc = doc_mod.open_document(out)
        text = text_mod.extract_text(doc)
        assert "# 제목" in text
        assert "항목1" in text

    def test_markdown_preserves_structure(self, tmp_path):
        src = tmp_path / "struct.md"
        src.write_text("# H1\n\n## H2\n\nParagraph\n\n- List\n", encoding="utf-8")
        out = str(tmp_path / "output.hwpx")

        runner = CliRunner()
        runner.invoke(cli, ["convert", str(src), "-o", out])

        doc = doc_mod.open_document(out)
        text = text_mod.extract_text(doc)
        assert "# H1" in text
        assert "## H2" in text
        assert "- List" in text


class TestConvertText:
    """e2e-022: 텍스트 파일 파싱 및 변환."""

    def test_text_to_hwpx(self, tmp_path):
        src = tmp_path / "source.txt"
        src.write_text("첫 줄\n둘째 줄\n셋째 줄\n", encoding="utf-8")
        out = str(tmp_path / "output.hwpx")

        runner = CliRunner()
        result = runner.invoke(cli, ["convert", str(src), "-o", out])

        assert result.exit_code == 0
        doc = doc_mod.open_document(out)
        text = text_mod.extract_text(doc)
        assert "첫 줄" in text
        assert "셋째 줄" in text

    def test_empty_lines_skipped(self, tmp_path):
        src = tmp_path / "empty.txt"
        src.write_text("줄1\n\n\n줄2\n", encoding="utf-8")
        out = str(tmp_path / "output.hwpx")

        runner = CliRunner()
        result = runner.invoke(cli, ["convert", str(src), "-o", out])

        assert "2 paragraphs" in result.output


class TestConvertErrors:
    """e2e-025: 파일 변환 에러 처리."""

    def test_unsupported_format(self, tmp_path):
        src = tmp_path / "source.pdf"
        src.write_bytes(b"%PDF-1.4")
        out = str(tmp_path / "output.hwpx")

        runner = CliRunner()
        result = runner.invoke(cli, ["convert", str(src), "-o", out])

        assert result.exit_code != 0

    def test_empty_file(self, tmp_path):
        src = tmp_path / "empty.txt"
        src.write_text("", encoding="utf-8")
        out = str(tmp_path / "output.hwpx")

        runner = CliRunner()
        result = runner.invoke(cli, ["convert", str(src), "-o", out])

        assert result.exit_code != 0

    def test_nonexistent_source(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["convert", "/tmp/nonexistent_999.txt", "-o", str(tmp_path / "out.hwpx")])

        assert result.exit_code != 0

    def test_response_format(self, tmp_path):
        """e2e-024: 응답에 source, format, paragraphs, output 포함."""
        src = tmp_path / "resp.md"
        src.write_text("# Test\n\nContent\n", encoding="utf-8")
        out = str(tmp_path / "output.hwpx")

        runner = CliRunner()
        result = runner.invoke(cli, ["convert", str(src), "-o", out])

        assert "source:" in result.output
        assert "format:" in result.output
        assert "paragraphs:" in result.output
        assert "output:" in result.output
