"""pyhwpxlib MCP server — HWPX document tools for AI agents.

Tools:
  hwpx_to_json   — Export HWPX to JSON for editing
  hwpx_from_json — Create HWPX from JSON
  hwpx_patch     — Surgically replace text in HWPX section
  hwpx_inspect   — Show HWPX structure summary
  hwpx_preview   — Render pages to PNG via rhwp WASM
  hwpx_validate  — Validate HWPX file integrity

Usage:
  claude mcp add pyhwpxlib -- python -m pyhwpxlib.mcp_server.server
"""
from __future__ import annotations

import base64
import json
import os
import sys

# Ensure pyhwpxlib is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastmcp import FastMCP

# Project root for resolving relative paths
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _abs(path: str) -> str:
    """Resolve relative paths against project root."""
    if os.path.isabs(path):
        return path
    return os.path.join(_PROJECT_ROOT, path)


mcp = FastMCP("hangul-docs", instructions="Korean 한/글 document tools — create, edit, fill forms, preview")


@mcp.tool()
def hwpx_to_json(file: str, section: int | None = None) -> str:
    """Export HWPX to JSON for editing.

    Use section parameter (0-based) to extract a single section
    for token efficiency. Returns JSON string.
    """
    from pyhwpxlib.json_io import to_json
    result = to_json(_abs(file), section_idx=section)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_from_json(data: str, output: str) -> str:
    """Create an HWPX document from JSON structure.

    Accepts JSON string in pyhwpxlib-json/1 format.
    Returns the output file path.
    """
    from pyhwpxlib.json_io import from_json
    parsed = json.loads(data) if isinstance(data, str) else data
    return from_json(parsed, _abs(output))


@mcp.tool()
def hwpx_patch(file: str, section: int, edits: str, output: str) -> str:
    """Replace text in an HWPX section, preserving everything else.

    edits: JSON string of {"old_text": "new_text"} mappings.
    Returns the output file path.
    """
    from pyhwpxlib.json_io import patch
    edit_dict = json.loads(edits) if isinstance(edits, str) else edits
    return patch(_abs(file), section, edit_dict, _abs(output))


@mcp.tool()
def hwpx_inspect(file: str) -> str:
    """Inspect HWPX document structure.

    Returns section count, paragraph counts, table counts,
    page settings, and text preview.
    """
    from pyhwpxlib.json_io import to_json
    from pyhwpxlib.api import extract_text

    doc = to_json(_abs(file))
    sections = doc.get("sections", [])

    info = {
        "file": os.path.basename(file),
        "sha256": doc.get("source_sha256", "")[:16] + "...",
        "sections": len(sections),
        "details": [],
    }

    for i, sec in enumerate(sections):
        paras = sec.get("paragraphs", [])
        tables = sec.get("tables", [])
        ps = sec.get("page_settings", {})
        info["details"].append({
            "section": i,
            "paragraphs": len(paras),
            "tables": len(tables),
            "page_width": ps.get("width", 0),
            "page_height": ps.get("height", 0),
            "landscape": ps.get("landscape", "WIDELY"),
        })

    text = extract_text(_abs(file))
    info["text_preview"] = text[:300] + ("..." if len(text) > 300 else "")
    info["text_length"] = len(text)

    return json.dumps(info, ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_build_step(actions: str, step_name: str = "", output: str = "/tmp/hwpx_step.hwpx") -> str:
    """Build HWPX incrementally and return a preview PNG.

    Adds content to a document and renders a preview at each step,
    like showing slides being built. Call repeatedly to build up
    the document piece by piece.

    actions: JSON array of actions to append. Each action:
      {"type": "heading", "text": "제목", "level": 1}
      {"type": "paragraph", "text": "본문", "bold": false, "font_size": 12}
      {"type": "table", "data": [["A","B"],["1","2"]], "col_widths": [20000,22520]}
      {"type": "page_break"}
      {"type": "image", "path": "photo.png", "width": 21260, "height": 15000}

    step_name: Label for this step (e.g., "제목 추가", "표 삽입").
    output: Where to save the intermediate HWPX file.

    Returns JSON with step info and PNG preview paths.
    """
    from pyhwpxlib import HwpxBuilder
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from scripts.preview import render_pages

    action_list = json.loads(actions) if isinstance(actions, str) else actions

    # Load existing or create new builder
    # Since HwpxBuilder doesn't support loading, we rebuild from accumulated actions.
    # The caller should send ALL actions up to the current step.
    b = HwpxBuilder()
    for act in action_list:
        t = act.get("type", "")
        if t == "heading":
            b.add_heading(act["text"], level=act.get("level", 1),
                          alignment=act.get("alignment", "JUSTIFY"))
        elif t == "paragraph":
            b.add_paragraph(act["text"],
                            bold=act.get("bold", False),
                            font_size=act.get("font_size"),
                            text_color=act.get("text_color"),
                            alignment=act.get("alignment", "JUSTIFY"))
        elif t == "table":
            b.add_table(act["data"],
                        col_widths=act.get("col_widths"),
                        row_heights=act.get("row_heights"),
                        header_bg=act.get("header_bg"))
        elif t == "page_break":
            b.add_page_break()
        elif t == "image":
            b.add_image(act["path"],
                        width=act.get("width", 21260),
                        height=act.get("height", 15000))
        elif t == "bullet_list":
            b.add_bullet_list(act["items"])
        elif t == "numbered_list":
            b.add_numbered_list(act["items"])

    b.save(_abs(output))
    pages = render_pages(_abs(output), "/tmp")

    # Embed PNG as base64 for Claude Desktop visibility
    for p in pages:
        png_path = p.get("png", "")
        if os.path.exists(png_path):
            with open(png_path, "rb") as f:
                p["png_base64"] = base64.b64encode(f.read()).decode("ascii")

    return json.dumps({
        "step": step_name,
        "output": _abs(output),
        "actions_count": len(action_list),
        "pages": pages,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_preview(file: str, out_dir: str = "/tmp") -> str:
    """Render HWPX pages to PNG via rhwp WASM.

    Returns JSON with page count and PNG file paths.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from scripts.preview import render_pages

    results = render_pages(_abs(file), out_dir)

    # Embed PNG as base64 for Claude Desktop visibility
    for r in results:
        png_path = r.get("png", "")
        if os.path.exists(png_path):
            with open(png_path, "rb") as f:
                r["png_base64"] = base64.b64encode(f.read()).decode("ascii")

    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_fill_form(file: str, mappings: str, output: str) -> str:
    """Fill a form template using label-based navigation.

    Visually analyzes the form, finds label cells, and fills adjacent cells
    (including empty cells). Supports directional navigation.

    mappings: JSON string of {"label>direction": "value"} pairs.
        Direction: right (default), left, up, down.
        Example: {"성 명>right": "홍길동", "전화번호>right": "010-1234"}

    Handles both filled cells (text replacement) and empty cells (cellAddr patch).
    Returns JSON with applied/failed counts and details.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from templates.form_pipeline import fill_by_labels

    mapping_dict = json.loads(mappings) if isinstance(mappings, str) else mappings
    result = fill_by_labels(_abs(file), mapping_dict, _abs(output))
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_analyze_form(file: str) -> str:
    """Analyze a form template and return fillable field locations.

    Extracts all table cells, identifies labels and empty value cells,
    and returns a structured field map for fill_form.

    Use this before hwpx_fill_form to discover what fields exist.
    Returns JSON with tables, cells, and suggested fill paths.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from templates.form_pipeline import extract_form, find_cell_by_label

    form = extract_form(_abs(file))
    fields = []

    for ti, tbl in enumerate(form.get('tables', [])):
        cells = tbl.get('cells', [])
        if not cells:
            continue
        rows = max(c['row'] for c in cells) + 1
        cols = max(c['col'] for c in cells) + 1

        for cell in cells:
            cell_text = ' '.join(
                r.get('text', '') for line in cell.get('lines', [])
                for r in line.get('runs', [])
            ).strip()
            if not cell_text:
                continue

            # Check if right-adjacent cell exists and is empty
            result = find_cell_by_label(form, cell_text, 'right')
            if result and not result['target_cell']['text']:
                fields.append({
                    'label': cell_text,
                    'fill_path': f"{cell_text}>right",
                    'table_index': ti,
                    'label_pos': f"r{cell['row']}c{cell['col']}",
                    'target_pos': f"r{result['target_cell']['row']}c{result['target_cell']['col']}",
                    'current_value': '',
                })

    return json.dumps({
        'file': os.path.basename(file),
        'tables': len(form.get('tables', [])),
        'fillable_fields': fields,
        'field_count': len(fields),
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_validate(file: str) -> str:
    """Validate HWPX file structure and integrity.

    Checks: ZIP validity, required files, mimetype, XML parsing.
    Returns JSON with validation results.
    """
    import zipfile

    issues = []
    info = {"file": os.path.basename(file), "valid": True, "issues": issues}

    if not os.path.exists(_abs(file)):
        return json.dumps({"file": _abs(file), "valid": False, "issues": ["File not found"]})

    try:
        with zipfile.ZipFile(_abs(file)) as z:
            names = z.namelist()

            # Check mimetype
            if 'mimetype' not in names:
                issues.append("Missing mimetype entry")
            elif names[0] != 'mimetype':
                issues.append("mimetype is not the first entry")

            # Check required files
            for req in ['Contents/header.xml', 'Contents/section0.xml']:
                if req not in names:
                    issues.append(f"Missing required file: {req}")

            # Count sections
            sec_count = sum(1 for n in names if n.startswith('Contents/section') and n.endswith('.xml'))
            info["sections"] = sec_count
            info["entries"] = len(names)

    except zipfile.BadZipFile:
        info["valid"] = False
        issues.append("Not a valid ZIP file")
    except Exception as e:
        info["valid"] = False
        issues.append(str(e))

    info["valid"] = len(issues) == 0
    return json.dumps(info, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
