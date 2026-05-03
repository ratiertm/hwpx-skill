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


mcp = FastMCP("hangul-docs", instructions="""
Korean 한/글 document tools (HWPX/OWPML).

## 절대 규칙 (MUST FOLLOW)

1. **모든 HWPX 생성/편집/변환 후 반드시 반환된 preview PNG를 확인한다.**
   각 tool은 `preview.png_base64` 필드를 반환. 이 이미지를 실제로 보고 문제를 찾아라.
   preview 확인 없이 사용자에게 "완료"를 보고하지 마라.

2. **양식 채우기는 analyze → 구조 판정 → 적절한 도구 호출**
   - `hwpx_analyze_form(file)`로 필드를 확인한다.
   - **구조 판정 필수**: analyze 결과의 label 셀 text가 "성 명       " 처럼 레이블+공백 placeholder를 포함하면 **구조 B (같은 셀)**. 별도 빈 값 셀이 있으면 **구조 A (인접 셀)**.
   - 구조 A → `hwpx_fill_form(file, mappings, output)` 사용 가능
   - 구조 B → `hwpx_fill_form` 사용 금지. 대신 `hwpx_patch(file, section, edits, output)`으로 원본 문자열 교체.
   - analyze 없이 fill_form 호출 금지.

3. **문서 생성은 단계별 빌드 권장**
   - 복잡한 문서는 `hwpx_build_step`을 여러 번 호출하여 점진적으로 구축한다.
   - 각 단계마다 반환된 PNG를 확인하고 다음 단계로 진행한다.

4. **출력 경로는 절대 경로 사용**
   - 프로젝트 루트: `/Users/leeeunmi/Projects/active/hwpx-skill`
   - 상대 경로는 프로젝트 루트 기준으로 자동 변환됨.
   - 생성된 파일은 `Test/` 디렉터리에 저장 권장.

## 표준 워크플로우

### A. 양식 채우기 (의견제출서, 신청서 등)
```
1. hwpx_analyze_form(file)           → 필드 목록 확인
2. 사용자에게 필드별 입력값 요청
3. hwpx_fill_form(file, mappings, output) → 채우기 + PNG 프리뷰 자동
4. preview.png_base64 확인 → 문제 있으면 mappings 수정 후 재호출
```

### B. 새 문서 생성 (보고서, 공문서)
```
1. hwpx_build_step([제목 action])       → PNG 확인
2. hwpx_build_step([제목, 메타, 표])    → 누적 빌드, PNG 확인
3. ... 반복 ...
4. 최종 output 파일을 사용자에게 전달
```

### C. 기존 문서 편집
```
1. hwpx_inspect(file)                → 구조 파악
2. hwpx_to_json(file, section)       → 특정 섹션 JSON 추출
3. JSON 편집
4. hwpx_patch(file, section, edits, output) → 섹션 교체 + PNG 자동
5. preview.png_base64 확인
```

### D. 공문(기안문) 생성 — 편람 2025 준수 (v0.10.0+)
행정안전부 「2025 행정업무운영 편람」 규정 자동 준수.
MCP 도구 대신 `pyhwpxlib.gongmun` 파이썬 모듈 사용 권장:

```python
from pyhwpxlib.gongmun import Gongmun, GongmunBuilder, signer, validate_file

doc = Gongmun(
    기관명="OO부", 수신="내부결재", 제목="...",
    본문=[
        "도입 문단",
        ("계약 개요", ["계약명: ...", "계약 금액: ..."]),  # 자동 가./나./다.
    ],
    붙임=["계획서 1부."],                              # 자동 '끝.'
    기안자=signer("행정사무관", "김OO"),
    결재권자=signer("과장", "박OO", 전결=True),
    시행_처리과명="OO과", 시행_일련번호="000",
    시행일="2025. 9. 20.", 공개구분="대국민공개",
)
GongmunBuilder(doc).save("output.hwpx")
print(validate_file("output.hwpx"))  # 규정 검증
```

자동 적용: 편람 표준 여백(상30/하15/좌우20/머꼬10) · 8단계 항목기호 · 2타 들여쓰기 ·
"끝" 표시 · 내부결재 시 발신명의 생략 · 기안자·결재권자 용어 생략.
자동 검사: 날짜 포맷 · 위압적 어투 · 차별적 표현 · 두음법칙 · 외래어 · 한글호환영역 특수문자.

## 시작할 때

처음 HWPX 관련 작업을 시작하면 **hwpx_guide()를 호출**하여 최신 가이드를 읽는다.
가이드에 테마, 워크플로우, Critical Rules, 디자인 규칙이 모두 포함되어 있다.

## 금지 사항

- preview 확인 없이 "완료" 보고
- analyze 없이 fill_form 호출
- 상대 경로로 저장 (프로젝트 루트 밖으로 새는 경우)
- PNG에 명백한 오류(깨진 텍스트, 빈 페이지 등)가 보이는데 넘어감
""")


def _with_preview(hwpx_path: str) -> dict:
    """Auto-generate PNG preview for any HWPX output. Always included."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from scripts.preview import render_pages

    pages = render_pages(hwpx_path, "/tmp")
    for p in pages:
        png_path = p.get("png", "")
        if os.path.exists(png_path):
            with open(png_path, "rb") as f:
                p["png_base64"] = base64.b64encode(f.read()).decode("ascii")
    return {
        "output": hwpx_path,
        "preview": pages,
        "next_step": (
            "각 페이지의 preview.png_base64를 반드시 확인하고 아래 3가지를 글로 적어라:\n"
            "1. 관찰1 — 첫 페이지에 무엇이 보이나? (제목/팔레트/레이아웃)\n"
            "2. 관찰2 — 깨진 텍스트/넘침/빈 페이지/잘린 표가 있나?\n"
            "3. 관찰3 — 주제 대비 디자인 적절성?\n"
            "관찰 없이 '완료' 보고 금지. 문제 시 수정 후 재호출."
        ),
    }


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
    out = from_json(parsed, _abs(output))
    return json.dumps(_with_preview(out), ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_patch(file: str, section: int, edits: str, output: str) -> str:
    """Replace text in an HWPX section, preserving everything else.

    edits: JSON string of {"old_text": "new_text"} mappings.
    Returns the output file path.
    """
    from pyhwpxlib.json_io import patch
    edit_dict = json.loads(edits) if isinstance(edits, str) else edits
    out = patch(_abs(file), section, edit_dict, _abs(output))
    return json.dumps(_with_preview(out), ensure_ascii=False, indent=2)


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
    result["preview"] = _with_preview(_abs(output))["preview"]
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


@mcp.tool()
def hwpx_hwp_to_hwpx(hwp_path: str, output: str) -> str:
    """Convert HWP 5.x binary to HWPX.

    Use when the input file has .hwp extension. Returns output path + PNG preview.
    """
    from pyhwpxlib.hwp2hwpx import convert
    convert(_abs(hwp_path), _abs(output))
    return json.dumps(_with_preview(_abs(output)), ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_md_to_hwpx(md_path: str, output: str, style: str = "github") -> str:
    """Convert Markdown file to HWPX.

    style: github | vscode | minimal | academic
    """
    import subprocess
    subprocess.run(
        [sys.executable, "-m", "pyhwpxlib", "md2hwpx",
         _abs(md_path), "-o", _abs(output), "-s", style],
        check=True, capture_output=True,
    )
    return json.dumps(_with_preview(_abs(output)), ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_html_to_hwpx(html_path: str, output: str) -> str:
    """Convert HTML file to HWPX. Strips <a> tags automatically."""
    from pyhwpxlib.api import convert_html_file_to_hwpx
    convert_html_file_to_hwpx(_abs(html_path), _abs(output))
    return json.dumps(_with_preview(_abs(output)), ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_fill_batch(template: str, records: str, output_dir: str,
                    filename_field: str = "") -> str:
    """Generate multiple filled documents from one template.

    records: JSON array of {"data": {...}, "checks": [...], "filename": "..."}.
    filename_field: key in data to use as filename (e.g. "성 명").
    Returns JSON with list of output paths.
    """
    from pyhwpxlib.api import fill_template_batch
    rec_list = json.loads(records) if isinstance(records, str) else records
    outputs = fill_template_batch(
        _abs(template), rec_list, _abs(output_dir), filename_field
    )
    return json.dumps({
        "template": _abs(template),
        "count": len(outputs),
        "outputs": outputs,
        "next_step": "각 파일의 내용이 맞는지 hwpx_preview로 몇 개 샘플링하여 확인하세요.",
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_build(actions: str, output: str) -> str:
    """Build a new HWPX document from a full action list (one-shot, not cumulative).

    actions: JSON array. Each action:
      {"type": "heading", "text": "제목", "level": 1, "alignment": "CENTER"}
      {"type": "paragraph", "text": "본문", "bold": false, "font_size": 12,
       "text_color": "#000000", "alignment": "JUSTIFY"}
      {"type": "table", "data": [[...]], "col_widths": [...], "header_bg": "#..."}
      {"type": "bullet_list", "items": [...]}
      {"type": "numbered_list", "items": [...]}
      {"type": "page_break"}
      {"type": "line"}
      {"type": "image", "path": "photo.png", "width": 21260, "height": 15000}
      {"type": "image_url", "url": "...", "filename": "a.png", "width": 42520, "height": 21260}
      {"type": "header", "text": "머리말"}
      {"type": "footer", "text": "꼬리말"}
      {"type": "page_number", "pos": "BOTTOM_CENTER"}
      {"type": "highlight", "text": "...", "color": "#ffff00"}
    """
    from pyhwpxlib import HwpxBuilder
    acts = json.loads(actions) if isinstance(actions, str) else actions
    b = HwpxBuilder()
    for a in acts:
        t = a.get("type", "")
        if t == "heading":
            b.add_heading(a["text"], level=a.get("level", 1),
                          alignment=a.get("alignment", "JUSTIFY"))
        elif t == "paragraph":
            b.add_paragraph(a["text"], bold=a.get("bold", False),
                            italic=a.get("italic", False),
                            font_size=a.get("font_size"),
                            text_color=a.get("text_color"),
                            alignment=a.get("alignment", "JUSTIFY"))
        elif t == "table":
            b.add_table(a["data"], col_widths=a.get("col_widths"),
                        row_heights=a.get("row_heights"),
                        header_bg=a.get("header_bg"),
                        cell_colors=a.get("cell_colors"),
                        cell_styles=a.get("cell_styles"))
        elif t == "bullet_list":
            b.add_bullet_list(a["items"], bullet_char=a.get("bullet_char", "•"))
        elif t == "numbered_list":
            b.add_numbered_list(a["items"])
        elif t == "page_break":
            b.add_page_break()
        elif t == "line":
            b.add_line()
        elif t == "image":
            b.add_image(_abs(a["path"]),
                        width=a.get("width", 21260),
                        height=a.get("height", 15000))
        elif t == "image_url":
            b.add_image_from_url(a["url"], filename=a.get("filename"),
                                 width=a.get("width", 42520),
                                 height=a.get("height", 21260))
        elif t == "header":
            b.add_header(a["text"])
        elif t == "footer":
            b.add_footer(a["text"])
        elif t == "page_number":
            b.add_page_number(a.get("pos", "BOTTOM_CENTER"))
        elif t == "highlight":
            b.add_highlight(a["text"], color=a.get("color", "#ffff00"))
    b.save(_abs(output))
    return json.dumps(_with_preview(_abs(output)), ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_build_preset(preset: str, title: str, sections: str, output: str,
                       subtitle: str = "", organization: str = "", date: str = "") -> str:
    """Build a document using a named preset (official | report | proposal).

    Applies the preset's page margins, fonts, colors, and optional cover page.

    sections: JSON array of {"heading": "제목", "body": ["단락1", ...]} or free actions
              (same schema as hwpx_build actions).

    preset: "official" (공문서), "report" (보고서), "proposal" (제안서)
    """
    from pyhwpxlib import HwpxBuilder
    from pyhwpxlib.presets import get_preset, build_cover_page

    p = get_preset(preset)
    b = HwpxBuilder()
    # Cover page for report/proposal (official uses inline title)
    if preset in ("report", "proposal"):
        build_cover_page(b, p, title, subtitle=subtitle,
                         organization=organization, date=date)
    else:
        ts = p.get("title", {})
        b.add_paragraph(title, bold=True, font_size=ts.get("font_size", 16),
                        alignment=ts.get("alignment", "CENTER"))
        b.add_paragraph("")

    sec_list = json.loads(sections) if isinstance(sections, str) else sections
    colors = p.get("colors", {})
    body_size = p.get("body", {}).get("font_size", 12)
    h2 = p.get("heading2", {})

    for sec in sec_list:
        if "heading" in sec:
            b.add_paragraph(sec["heading"],
                            bold=h2.get("bold", True),
                            font_size=h2.get("font_size", 14),
                            text_color=colors.get("heading", "#000000"))
            for para in sec.get("body", []):
                if isinstance(para, str):
                    b.add_paragraph(para, font_size=body_size)
                elif isinstance(para, dict) and para.get("type") == "table":
                    b.add_table(para["data"],
                                col_widths=para.get("col_widths"),
                                header_bg=para.get("header_bg",
                                                   colors.get("table_header")))
            b.add_paragraph("")
        elif "type" in sec:
            # Free-form action (delegate to builder)
            t = sec["type"]
            if t == "page_break":
                b.add_page_break()
            elif t == "paragraph":
                b.add_paragraph(sec["text"], font_size=sec.get("font_size", body_size))

    b.save(_abs(output))
    return json.dumps({
        "preset": preset,
        **_with_preview(_abs(output)),
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_template_context(name: str) -> str:
    """Load workspace context for a registered HWPX template (v0.17.0+).

    워크스페이스 폴더 (`~/.local/share/pyhwpxlib/templates/<name>/`) 에서 schema._meta,
    decisions.md, history.json (최근 채우기) 를 로드해서 LLM 주입용 markdown + json
    으로 반환. 새 채팅 세션 진입 시 양식명만 알면 이전 합의·결정·최근 데이터를
    그대로 복원할 수 있다 — `pyhwpxlib template context <name>` 의 MCP 인터페이스.
    """
    try:
        from pyhwpxlib.templates.context import load_context
    except ImportError:
        return json.dumps(
            {"error": "context module not available (pyhwpxlib < 0.17.0)"},
            ensure_ascii=False,
        )
    try:
        ctx = load_context(name)
    except FileNotFoundError as e:
        return json.dumps(
            {"error": f"template not registered: {name}",
             "hint": "Use `pyhwpxlib template add <file>` first",
             "detail": str(e)},
            ensure_ascii=False,
        )
    return json.dumps({
        "markdown": ctx.to_markdown(),
        **ctx.to_dict(),
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_template_workspace_list() -> str:
    """List all registered HWPX templates with workspace metadata (v0.17.0+).

    User workspaces (folder structure) + skill bundle (flat) 모두 포함.
    각 항목은 name / name_kr / source / decisions_count / outputs_count / _meta 를
    담아 LLM 이 양식 매칭에 사용할 수 있다.
    """
    try:
        from pyhwpxlib.templates.resolver import list_all_templates
    except ImportError:
        return json.dumps(
            {"error": "templates module not available"},
            ensure_ascii=False,
        )
    items = list_all_templates()
    return json.dumps({
        "count": len(items),
        "templates": items,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_template_log_fill(name: str, data: str,
                            output_path: str = "") -> str:
    """Append a fill entry to a template's history.json (v0.17.0+).

    `hwpx_fill_form` 같은 외부 채우기 후 수동으로 기록을 남기고 싶을 때 사용.
    `pyhwpxlib template fill` 을 통한 호출은 자동 기록이라 호출 불필요.

    Args:
        name: registered template name (workspace 등록 필요)
        data: JSON string of fill data
        output_path: optional output file path to record alongside the entry
    """
    try:
        from pyhwpxlib.templates.context import log_fill
    except ImportError:
        return json.dumps(
            {"error": "context module not available (pyhwpxlib < 0.17.0)"},
            ensure_ascii=False,
        )
    try:
        data_dict = json.loads(data) if isinstance(data, str) else data
    except json.JSONDecodeError as e:
        return json.dumps(
            {"error": f"invalid JSON data: {e}"},
            ensure_ascii=False,
        )
    try:
        info = log_fill(name, data_dict,
                        output_path=output_path or None)
    except FileNotFoundError as e:
        return json.dumps(
            {"error": f"workspace not found: {name}",
             "detail": str(e)},
            ensure_ascii=False,
        )
    return json.dumps({"name": name, **info}, ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_template_save_session(name: str,
                                data: str = "",
                                decision: str = "",
                                output_path: str = "") -> str:
    """Close the diarization loop in one call (v0.17.0+).

    Combines `hwpx_template_log_fill` + `annotate(add_decision=...)` so the
    session-end "save state" step is a single round-trip. Use at the very
    end of a form-fill session to persist what just happened:

      - `data`: fill payload (JSON string). Appended to history.json.
      - `decision`: free-form note for decisions.md (e.g. structure type
        choice, page standard, edge cases discovered this session).
      - `output_path`: optional, recorded alongside the history entry.

    At least one of `data` or `decision` must be non-empty. When both are
    empty the call is a no-op and returns ``{"saved": false}``.

    Args:
        name: registered template name (must exist in the workspace).
        data: JSON string of fill data, or "" to skip log-fill.
        decision: text appended to decisions.md, or "" to skip annotate.
        output_path: optional output file path (paired with `data`).

    Returns:
        JSON string with shape:
          {
            "name": "<name>",
            "saved": true|false,
            "history": {...} | null,    # log_fill return when called
            "decision_added": true|false
          }
    """
    has_data = bool(data and data.strip())
    has_decision = bool(decision and decision.strip())

    if not has_data and not has_decision:
        return json.dumps({
            "name": name,
            "saved": False,
            "reason": "both data and decision empty — nothing to save",
        }, ensure_ascii=False)

    try:
        from pyhwpxlib.templates.context import log_fill, annotate
    except ImportError:
        return json.dumps(
            {"error": "context module not available (pyhwpxlib < 0.17.0)"},
            ensure_ascii=False,
        )

    history_info = None
    if has_data:
        try:
            data_dict = json.loads(data)
        except json.JSONDecodeError as e:
            return json.dumps(
                {"error": f"invalid JSON data: {e}"},
                ensure_ascii=False,
            )
        try:
            history_info = log_fill(name, data_dict,
                                     output_path=output_path or None)
        except FileNotFoundError as e:
            return json.dumps(
                {"error": f"workspace not found: {name}",
                 "detail": str(e)},
                ensure_ascii=False,
            )

    decision_added = False
    if has_decision:
        try:
            anno = annotate(name, add_decision=decision.strip())
            decision_added = bool(anno.get("decision_added"))
        except FileNotFoundError as e:
            return json.dumps(
                {"error": f"workspace not found: {name}",
                 "detail": str(e),
                 "history": history_info},
                ensure_ascii=False,
            )

    return json.dumps({
        "name": name,
        "saved": True,
        "history": history_info,
        "decision_added": decision_added,
    }, ensure_ascii=False, indent=2)


@mcp.tool()
def hwpx_guide() -> str:
    """Get the latest pyhwpxlib usage guide.

    Returns the built-in LLM quick-reference guide (API surface, themes,
    workflows, critical rules, design guidelines). Call this first when
    starting any HWPX document task to ensure you have the latest
    instructions.
    """
    from pyhwpxlib.llm_guide import GUIDE
    return GUIDE


if __name__ == "__main__":
    mcp.run()
