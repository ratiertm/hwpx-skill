"""FastAPI server for HWPX document generation.

Wraps python-hwpx to provide a web UI for:
1. Direct text input → HWPX
2. LLM instruction → Markdown → HWPX (Claude via subprocess, OAuth auth)
3. File upload (HTML/MD/TXT) → HWPX conversion
"""

from __future__ import annotations

import html as html_lib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from hwpx import HwpxDocument

app = FastAPI(title="HWPX Document Generator")

OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="hwpx_"))

# Reuse the enhanced markdown converter from CLI
import sys
_cli_path = str(Path(__file__).resolve().parent.parent)
if _cli_path not in sys.path:
    sys.path.insert(0, _cli_path)
from cli_anything.hwpx.hwpx_cli import _convert_markdown_to_hwpx, MD_STYLES
from web.css_parser import load_all_styles


def _reload_css_styles():
    """Reload CSS files from styles/ directory into MD_STYLES."""
    css_styles = load_all_styles()
    for key, style_dict in css_styles.items():
        MD_STYLES[key] = style_dict


# Initial load
_reload_css_styles()


def _create_hwpx_from_markdown(markdown: str, filename: str,
                                style_name: str = "github") -> Path:
    """Create a formatted HWPX file from Markdown content."""
    doc = HwpxDocument.new()
    _convert_markdown_to_hwpx(doc, markdown, style_name=style_name)
    out = OUTPUT_DIR / filename
    doc.save_to_path(str(out))
    return out


def _create_hwpx_simple(paragraphs: list[str], filename: str,
                         font_sizes: dict[int, int] | None = None) -> Path:
    """Create HWPX file from plain paragraphs (no formatting)."""
    doc = HwpxDocument.new()
    for i, text in enumerate(paragraphs):
        if font_sizes and i in font_sizes:
            style_id = doc.ensure_run_style(height=font_sizes[i])
            doc.add_paragraph(text, char_pr_id_ref=style_id)
        else:
            doc.add_paragraph(text)
    out = OUTPUT_DIR / filename
    doc.save_to_path(str(out))
    return out


# ── LLM Integration (Claude subprocess with OAuth) ──────────────────

_SYSTEM_PROMPT = (
    "You are a document writer. The user will give you an instruction "
    "to create a document. Generate the document content in Markdown format.\n\n"
    "Rules:\n"
    "- Use # for title, ## for sections, ### for subsections\n"
    "- Use **bold** and *italic* for emphasis\n"
    "- Use - for bullet lists, 1. for numbered lists\n"
    "- Use | table | format for data tables\n"
    "- Use ```language for code blocks when appropriate\n"
    "- Use > for important quotes or notes\n"
    "- Use --- for section separators when needed\n"
    "- Write in the same language as the user's instruction\n"
    "- Output ONLY the Markdown content, no explanations or commentary\n"
    "- Create realistic, detailed, professional content\n"
    "- NEVER use HTML tags (no <iframe>, <div>, <style>, <script>, <span>, <br>, etc.)\n"
    "- NEVER use inline HTML or raw HTML blocks\n"
    "- Use only pure Markdown syntax\n"
)


def _call_claude_subprocess(instruction: str) -> str:
    """Call Claude via 'claude -p' subprocess using OAuth authentication.

    This uses Claude Code's headless mode (-p) which inherits the user's
    existing OAuth session — no API key needed.
    """
    # Find claude CLI
    claude_path = _find_claude_cli()
    if not claude_path:
        raise ValueError(
            "claude CLI를 찾을 수 없습니다.\n"
            "Claude Code가 설치되어 있는지 확인하세요."
        )

    # Remove ANTHROPIC_API_KEY from env to force OAuth
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    prompt = f"{_SYSTEM_PROMPT}\n\nUser instruction:\n{instruction}"

    result = subprocess.run(
        [claude_path, "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        stdin=subprocess.DEVNULL,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise ValueError(f"Claude CLI 오류: {stderr or 'unknown error'}")

    output = result.stdout.strip()
    if not output:
        raise ValueError("Claude가 빈 응답을 반환했습니다.")

    return output


def _find_claude_cli() -> str | None:
    """Find the claude CLI binary path."""
    # Common locations
    candidates = [
        os.path.expanduser("~/.local/bin/claude"),
        "/usr/local/bin/claude",
        "/opt/homebrew/bin/claude",
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    # Try which
    try:
        result = subprocess.run(
            ["which", "claude"], capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    return None


# ── API Endpoints ─────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return Path(__file__).parent.joinpath("index.html").read_text(encoding="utf-8")


@app.post("/api/direct")
async def direct_input(
    filename: str = Form("output.hwpx"),
    content: str = Form(""),
    style: str = Form("github"),
):
    if not content.strip():
        return {"error": "내용을 입력해주세요"}

    _reload_css_styles()
    path = _create_hwpx_from_markdown(content, filename, style_name=style)

    lines = [line for line in content.split("\n") if line.strip()]
    return {
        "filename": filename,
        "paragraphs": len(lines),
        "download": f"/download/{filename}",
        "preview": content,
    }


@app.post("/api/llm")
async def llm_instruction(
    filename: str = Form("ai-generated.hwpx"),
    instruction: str = Form(""),
    style: str = Form("github"),
):
    if not instruction.strip():
        return {"error": "지시문을 입력해주세요"}

    _reload_css_styles()

    try:
        markdown = _call_claude_subprocess(instruction)
    except ValueError as e:
        return {"error": str(e)}
    except subprocess.TimeoutExpired:
        return {"error": "Claude 응답 시간 초과 (120초). 더 짧은 지시문을 시도하세요."}
    except Exception as e:
        return {"error": f"오류 발생: {e}"}

    path = _create_hwpx_from_markdown(markdown, filename, style_name=style)

    return {
        "filename": filename,
        "paragraphs": markdown.count("\n") + 1,
        "download": f"/download/{filename}",
        "preview": markdown,
        "instruction": instruction,
        "style": style,
    }


@app.post("/api/convert")
async def convert_file(
    file: UploadFile = File(...),
    filename: str = Form("converted.hwpx"),
    style: str = Form("github"),
):
    content = (await file.read()).decode("utf-8")
    ext = Path(file.filename or "").suffix.lower()

    supported = {".html", ".htm", ".md", ".markdown", ".txt", ".text"}
    if ext not in supported:
        return {"error": f"지원하지 않는 형식: {ext}. html, md, txt만 가능합니다."}

    if not content.strip():
        return {"error": "파일에 내용이 없습니다"}

    _reload_css_styles()

    if ext in (".md", ".markdown"):
        path = _create_hwpx_from_markdown(content, filename, style_name=style)
        paragraphs_count = content.count("\n") + 1
    elif ext in (".html", ".htm"):
        paragraphs = _parse_html(content)
        path = _create_hwpx_simple(paragraphs, filename)
        paragraphs_count = len(paragraphs)
    else:
        paragraphs = [line.strip() for line in content.split("\n") if line.strip()]
        path = _create_hwpx_simple(paragraphs, filename)
        paragraphs_count = len(paragraphs)

    return {
        "source": file.filename,
        "format": ext.lstrip("."),
        "paragraphs": paragraphs_count,
        "download": f"/download/{filename}",
        "preview": content[:2000],
    }


def _parse_html(content: str) -> list[str]:
    content = re.sub(r"<br\s*/?>", "\n", content)
    content = re.sub(r"</(?:p|div|h[1-6]|li|tr|blockquote)>", "\n", content, flags=re.IGNORECASE)
    content = re.sub(r"<[^>]+>", "", content)
    content = html_lib.unescape(content)
    return [line.strip() for line in content.split("\n") if line.strip()]


@app.get("/api/styles")
async def list_styles():
    """Return available style presets (reloads CSS from disk)."""
    _reload_css_styles()
    return {
        key: {"name": s["name"], "description": s["description"]}
        for key, s in MD_STYLES.items()
    }


@app.post("/api/styles/upload")
async def upload_style(
    file: UploadFile = File(...),
):
    """Upload a custom CSS file as a new style preset."""
    from web.css_parser import css_to_hwpx_style
    content = (await file.read()).decode("utf-8")
    name = Path(file.filename or "custom").stem
    style_dict = css_to_hwpx_style(content, name=name.title())
    MD_STYLES[name] = style_dict
    # Also save to styles dir
    styles_dir = Path(__file__).parent / "styles"
    styles_dir.mkdir(exist_ok=True)
    (styles_dir / f"{name}.css").write_text(content, encoding="utf-8")
    return {
        "key": name,
        "name": style_dict["name"],
        "description": style_dict["description"],
        "message": f"Style '{name}' uploaded and ready to use",
    }


@app.get("/download/{filename}")
async def download(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        return {"error": "파일을 찾을 수 없습니다"}
    return FileResponse(
        str(path),
        media_type="application/hwp+zip",
        filename=filename,
    )
