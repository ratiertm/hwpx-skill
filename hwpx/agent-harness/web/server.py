"""FastAPI server for HWPX document generation.

Wraps python-hwpx to provide a web UI for:
1. Direct text input → HWPX
2. LLM instruction → HWPX (generates content from instruction)
3. File upload (HTML/MD/TXT) → HWPX conversion
"""

from __future__ import annotations

import html as html_lib
import re
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from hwpx import HwpxDocument

app = FastAPI(title="HWPX Document Generator")

OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="hwpx_"))


def _create_hwpx(paragraphs: list[str], filename: str,
                  font_sizes: dict[int, int] | None = None) -> Path:
    """Create HWPX file from paragraphs. Returns file path."""
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


def _parse_html(content: str) -> list[str]:
    content = re.sub(r"<br\s*/?>", "\n", content)
    content = re.sub(r"</(?:p|div|h[1-6]|li|tr|blockquote)>", "\n", content, flags=re.IGNORECASE)
    content = re.sub(r"<[^>]+>", "", content)
    content = html_lib.unescape(content)
    return [line.strip() for line in content.split("\n") if line.strip()]


def _parse_md(content: str) -> list[str]:
    return [line.strip() for line in content.split("\n") if line.strip()]


def _parse_txt(content: str) -> list[str]:
    return [line.strip() for line in content.split("\n") if line.strip()]


# ── API Endpoints ─────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return Path(__file__).parent.joinpath("index.html").read_text(encoding="utf-8")


@app.post("/api/direct")
async def direct_input(
    filename: str = Form("output.hwpx"),
    content: str = Form(""),
    title_size: int = Form(20),
):
    lines = [line for line in content.split("\n") if line.strip()]
    if not lines:
        return {"error": "내용을 입력해주세요"}

    # First line as title with larger font
    font_sizes = {0: title_size * 100}
    path = _create_hwpx(lines, filename, font_sizes)
    return {
        "filename": filename,
        "paragraphs": len(lines),
        "download": f"/download/{filename}",
        "preview": "\n".join(lines),
    }


@app.post("/api/llm")
async def llm_instruction(
    filename: str = Form("ai-generated.hwpx"),
    instruction: str = Form(""),
):
    if not instruction.strip():
        return {"error": "지시문을 입력해주세요"}

    # AI가 지시문을 해석해서 내용을 생성하는 부분
    # 실제로는 LLM API를 호출하지만, 여기서는 지시문 기반 템플릿 생성
    paragraphs = _generate_from_instruction(instruction)
    font_sizes = {0: 2000}  # 20pt title
    path = _create_hwpx(paragraphs, filename, font_sizes)
    return {
        "filename": filename,
        "paragraphs": len(paragraphs),
        "download": f"/download/{filename}",
        "preview": "\n".join(paragraphs),
        "instruction": instruction,
    }


def _generate_from_instruction(instruction: str) -> list[str]:
    """Generate document content from instruction.

    In production, this would call an LLM API.
    For now, creates structured content based on the instruction.
    """
    return [
        instruction,
        "",
        "이 문서는 AI 에이전트가 자동으로 생성했습니다.",
        "",
        "cli-anything-hwpx를 사용하여 HWPX 문서를 생성합니다.",
        "한컴오피스 설치 없이, Python만으로 동작합니다.",
    ]


@app.post("/api/convert")
async def convert_file(
    file: UploadFile = File(...),
    filename: str = Form("converted.hwpx"),
):
    content = (await file.read()).decode("utf-8")
    ext = Path(file.filename or "").suffix.lower()

    if ext in (".html", ".htm"):
        paragraphs = _parse_html(content)
    elif ext in (".md", ".markdown"):
        paragraphs = _parse_md(content)
    elif ext in (".txt", ".text"):
        paragraphs = _parse_txt(content)
    else:
        return {"error": f"지원하지 않는 형식: {ext}. html, md, txt만 가능합니다."}

    if not paragraphs:
        return {"error": "파일에 내용이 없습니다"}

    path = _create_hwpx(paragraphs, filename)
    return {
        "source": file.filename,
        "format": ext.lstrip("."),
        "paragraphs": len(paragraphs),
        "download": f"/download/{filename}",
        "preview": "\n".join(paragraphs[:20]),
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
