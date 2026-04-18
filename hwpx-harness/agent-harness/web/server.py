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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from hwpx import HwpxDocument

import shutil
from contextlib import asynccontextmanager


OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="hwpx_"))


@asynccontextmanager
async def lifespan(app):
    yield
    # Cleanup temp files on shutdown
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)


app = FastAPI(title="HWPX Document Generator", lifespan=lifespan)

# Import converter from shared module (no sys.path hack needed)
from cli_anything.hwpx.core.converter import convert_markdown_to_hwpx as _convert_markdown_to_hwpx, MD_STYLES
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


_MAX_INSTRUCTION_LENGTH = 10000


@app.post("/api/direct")
async def direct_input(
    filename: str = Form("output.hwpx"),
    content: str = Form(""),
    style: str = Form("github"),
):
    if not content.strip():
        return JSONResponse(
            content={"error": "내용을 입력해주세요"}, status_code=400)

    _reload_css_styles()
    safe_filename = _sanitize_filename(filename)
    path = _create_hwpx_from_markdown(content, safe_filename, style_name=style)

    lines = [line for line in content.split("\n") if line.strip()]
    return {
        "filename": safe_filename,
        "paragraphs": len(lines),
        "download": f"/download/{safe_filename}",
        "preview": content,
    }


@app.post("/api/llm")
async def llm_instruction(
    filename: str = Form("ai-generated.hwpx"),
    instruction: str = Form(""),
    style: str = Form("github"),
):
    if not instruction.strip():
        return JSONResponse(
            content={"error": "지시문을 입력해주세요"}, status_code=400)
    if len(instruction) > _MAX_INSTRUCTION_LENGTH:
        return JSONResponse(
            content={"error": f"지시문이 너무 깁니다 (최대 {_MAX_INSTRUCTION_LENGTH}자)"},
            status_code=400)

    _reload_css_styles()

    try:
        markdown = _call_claude_subprocess(instruction)
    except ValueError as e:
        return JSONResponse(
            content={"error": str(e)}, status_code=500)
    except subprocess.TimeoutExpired:
        return JSONResponse(
            content={"error": "Claude 응답 시간 초과 (120초). 더 짧은 지시문을 시도하세요."},
            status_code=504)
    except Exception as e:
        return JSONResponse(
            content={"error": f"오류 발생: {e}"}, status_code=500)

    safe_filename = _sanitize_filename(filename)
    path = _create_hwpx_from_markdown(markdown, safe_filename, style_name=style)

    return {
        "filename": safe_filename,
        "paragraphs": markdown.count("\n") + 1,
        "download": f"/download/{safe_filename}",
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
    try:
        content = (await file.read()).decode("utf-8")
    except UnicodeDecodeError:
        return JSONResponse(
            content={"error": "UTF-8 텍스트 파일만 지원합니다."},
            status_code=400)

    ext = Path(file.filename or "").suffix.lower()
    supported = {".html", ".htm", ".md", ".markdown", ".txt", ".text"}
    if ext not in supported:
        return JSONResponse(
            content={"error": f"지원하지 않는 형식: {ext}. html, md, txt만 가능합니다."},
            status_code=400)

    if not content.strip():
        return JSONResponse(
            content={"error": "파일에 내용이 없습니다"}, status_code=400)

    _reload_css_styles()
    safe_filename = _sanitize_filename(filename)

    if ext in (".md", ".markdown"):
        path = _create_hwpx_from_markdown(content, safe_filename, style_name=style)
        paragraphs_count = content.count("\n") + 1
    elif ext in (".html", ".htm"):
        paragraphs = _parse_html(content)
        path = _create_hwpx_simple(paragraphs, safe_filename)
        paragraphs_count = len(paragraphs)
    else:
        paragraphs = [line.strip() for line in content.split("\n") if line.strip()]
        path = _create_hwpx_simple(paragraphs, safe_filename)
        paragraphs_count = len(paragraphs)

    return {
        "source": file.filename,
        "format": ext.lstrip("."),
        "paragraphs": paragraphs_count,
        "download": f"/download/{safe_filename}",
        "preview": content[:2000],
    }


def _parse_html(content: str) -> list[str]:
    content = re.sub(r"<br\s*/?>", "\n", content)
    content = re.sub(r"</(?:p|div|h[1-6]|li|tr|blockquote)>", "\n", content, flags=re.IGNORECASE)
    content = re.sub(r"<[^>]+>", "", content)
    content = html_lib.unescape(content)
    return [line.strip() for line in content.split("\n") if line.strip()]


@app.post("/api/image-to-hwpx")
async def image_to_hwpx(
    file: UploadFile = File(...),
    filename: str = Form("form-output.hwpx"),
):
    """Upload a form image → detect grid + OCR → generate HWPX."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
        return JSONResponse(
            content={"error": f"이미지 파일만 지원합니다 (png, jpg). 현재: {ext}"},
            status_code=400)

    # Save uploaded image to temp
    import tempfile as _tf
    tmp = _tf.NamedTemporaryFile(suffix=ext, delete=False)
    tmp.write(await file.read())
    tmp.close()

    try:
        from web.image_to_hwpx import analyze_image, generate_hwpx
        form = analyze_image(tmp.name)

        safe_filename = _sanitize_filename(filename)
        out_path = str(OUTPUT_DIR / safe_filename)
        generate_hwpx(form, out_path)

        # Build cell summary for preview
        cell_summary = []
        for c in form.cells:
            info = f"[{c['row']},{c['col']}]"
            if c["row_span"] > 1 or c["col_span"] > 1:
                info += f" span({c['row_span']},{c['col_span']})"
            if c["text"]:
                info += f": {c['text'][:30]}"
            cell_summary.append(info)

        return {
            "filename": safe_filename,
            "download": f"/download/{safe_filename}",
            "grid": f"{form.rows}x{form.cols}",
            "cells": len(form.cells),
            "row_heights_pct": form.row_heights_pct,
            "col_widths_pct": form.col_widths_pct,
            "preview": "\n".join(cell_summary),
        }
    except Exception as e:
        return JSONResponse(
            content={"error": f"이미지 분석 실패: {e}"}, status_code=500)
    finally:
        Path(tmp.name).unlink(missing_ok=True)


@app.get("/api/styles")
async def list_styles():
    """Return available style presets (reloads CSS from disk)."""
    _reload_css_styles()
    return {
        key: {"name": s["name"], "description": s["description"]}
        for key, s in MD_STYLES.items()
    }


def _sanitize_filename(name: str) -> str:
    """Remove path traversal characters, allow only safe filenames."""
    name = Path(name).name  # strip directory components
    name = re.sub(r"[^a-zA-Z0-9가-힣._-]", "_", name)
    return name or "untitled"


@app.post("/api/styles/upload")
async def upload_style(
    file: UploadFile = File(...),
):
    """Upload a custom CSS file as a new style preset."""
    from web.css_parser import css_to_hwpx_style
    try:
        content = (await file.read()).decode("utf-8")
    except UnicodeDecodeError:
        return JSONResponse(
            content={"error": "UTF-8 텍스트 파일만 지원합니다."},
            status_code=400,
        )
    name = _sanitize_filename(Path(file.filename or "custom").stem)
    style_dict = css_to_hwpx_style(content, name=name.title())
    MD_STYLES[name] = style_dict
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
    safe_name = _sanitize_filename(filename)
    path = (OUTPUT_DIR / safe_name).resolve()
    if not path.is_relative_to(OUTPUT_DIR.resolve()):
        return JSONResponse(
            content={"error": "잘못된 파일 경로입니다."},
            status_code=403,
        )
    if not path.exists():
        return JSONResponse(
            content={"error": "파일을 찾을 수 없습니다."},
            status_code=404,
        )
    return FileResponse(
        str(path),
        media_type="application/hwp+zip",
        filename=safe_name,
    )
