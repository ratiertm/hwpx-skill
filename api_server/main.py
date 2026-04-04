"""pyhwpxlib FastAPI MVP Server

Endpoints:
    POST /convert/md-to-hwpx   — Markdown → HWPX download
    POST /form/clone            — Clone (reverse-engineer) an HWPX form
    POST /form/fill             — Fill a template HWPX with JSON data

Run:
    uvicorn api_server.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

# Resolve project root so we can import pyhwpxlib and templates
_THIS = Path(__file__).resolve().parent
_ROOT = _THIS.parent
sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="pyhwpxlib API",
    version="0.1.0",
    description="REST API for creating and transforming HWPX (Hancom Office) documents",
)

_TMP_DIR = Path(tempfile.mkdtemp(prefix="pyhwpx_api_"))


def _tmp(suffix: str) -> str:
    import uuid
    return str(_TMP_DIR / f"{uuid.uuid4().hex}{suffix}")


# ============================================================
# /convert/md-to-hwpx
# ============================================================

@app.post(
    "/convert/md-to-hwpx",
    summary="Convert Markdown to HWPX",
    response_description="HWPX file download",
)
async def convert_md_to_hwpx(
    markdown: str = Form(..., description="Markdown text to convert"),
    filename: str = Form("output.hwpx", description="Output filename"),
):
    """Convert Markdown text to a downloadable HWPX file.

    Supports: headings, bold/italic, bullet/numbered lists, tables,
    code blocks, blockquotes, and horizontal rules.
    """
    from pyhwpxlib.api import create_document, save
    from pyhwpxlib.converter import convert_markdown_to_hwpx

    output_path = _tmp(".hwpx")
    try:
        doc = create_document()
        convert_markdown_to_hwpx(doc, markdown)
        save(doc, output_path)
    except Exception as e:
        logger.error("md-to-hwpx conversion failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Conversion failed: {e}")

    return FileResponse(
        output_path,
        media_type="application/octet-stream",
        filename=filename if filename.endswith(".hwpx") else filename + ".hwpx",
    )


# ============================================================
# /form/clone
# ============================================================

@app.post(
    "/form/clone",
    summary="Clone a government form (서식 복제)",
    response_description="Cloned HWPX file download",
)
async def form_clone(
    file: UploadFile = File(..., description="Source .hwpx or .owpml form file"),
):
    """Reverse-engineer and clone an HWPX/OWPML form.

    Upload any Korean government form (.hwpx or .owpml) and receive an
    exact structural clone that can be filled programmatically.
    Preserves table structure, cell sizes, merges, styles, and text.
    """
    suffix = Path(file.filename or "form.hwpx").suffix.lower()
    if suffix not in (".hwpx", ".owpml"):
        raise HTTPException(status_code=400, detail="Only .hwpx and .owpml files are supported")

    input_path = _tmp(suffix)
    output_path = _tmp(".hwpx")

    try:
        with open(input_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    try:
        sys.path.insert(0, str(_ROOT / "templates"))
        from form_pipeline import extract_form, generate_form
        form_data = extract_form(input_path)
        generate_form(form_data, output_path)
    except Exception as e:
        logger.error("form/clone failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Clone failed: {e}")
    finally:
        if os.path.exists(input_path):
            os.unlink(input_path)

    stem = Path(file.filename or "form").stem
    return FileResponse(
        output_path,
        media_type="application/octet-stream",
        filename=f"{stem}_clone.hwpx",
    )


# ============================================================
# /form/fill
# ============================================================

@app.post(
    "/form/fill",
    summary="Fill a template with data (양식 채우기)",
    response_description="Filled HWPX file download",
)
async def form_fill(
    file: UploadFile = File(..., description="Template .hwpx file with {{placeholder}} markers"),
    data: str = Form(..., description='JSON object of placeholder values, e.g. {"이름": "홍길동"}'),
    filename: str = Form("filled.hwpx", description="Output filename"),
):
    """Fill an HWPX template by replacing {{placeholder}} markers with data.

    Upload a template .hwpx file and a JSON object mapping placeholder
    names to their replacement values.

    Example data: ``{"이름": "홍길동", "날짜": "2026-04-05", "제목": "납품 확인서"}``
    """
    import json as _json

    try:
        fill_data: dict = _json.loads(data)
    except _json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON data: {e}")

    if not isinstance(fill_data, dict):
        raise HTTPException(status_code=400, detail="data must be a JSON object")

    input_path = _tmp(".hwpx")
    output_path = _tmp(".hwpx")

    suffix = Path(file.filename or "template.hwpx").suffix.lower()
    if suffix != ".hwpx":
        raise HTTPException(status_code=400, detail="Only .hwpx template files are supported for fill")

    try:
        with open(input_path, "wb") as f:
            f.write(await file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

    try:
        from pyhwpxlib.api import fill_template
        fill_template(input_path, {str(k): str(v) for k, v in fill_data.items()}, output_path)
    except Exception as e:
        logger.error("form/fill failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Fill failed: {e}")
    finally:
        if os.path.exists(input_path):
            os.unlink(input_path)

    return FileResponse(
        output_path,
        media_type="application/octet-stream",
        filename=filename if filename.endswith(".hwpx") else filename + ".hwpx",
    )


# ============================================================
# Health check
# ============================================================

@app.get("/health", summary="Health check")
async def health():
    """Returns API status and pyhwpxlib version."""
    import pyhwpxlib
    return {"status": "ok", "version": pyhwpxlib.__version__}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server.main:app", host="0.0.0.0", port=8000, reload=True)
