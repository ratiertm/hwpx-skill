"""HWPX 서식 편집기 — 브라우저에서 필드 입력 → HWPX 생성 다운로드

Usage:
    python form_editor.py <template.hwpx|owpml> [--port 8080]
"""
import http.server
import json
import os
import sys
import urllib.parse
import tempfile
import shutil
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pyhwpxlib.api import extract_schema, fill_template_checkbox

TEMPLATE_PATH = ""
SCHEMA = {}


def generate_html(schema):
    """스키마에서 웹 폼 HTML 생성"""
    title = schema.get("title", "서식 편집기")
    source = schema.get("source", "")

    # 1페이지(표[0]) 필드만 필터
    fields = [f for f in schema["fields"] if f["table"] == 0]
    checkboxes = [c for c in schema["checkboxes"] if c["table"] == 0]

    # 노이즈 필터 — 채울 수 없는 라벨 제거
    skip_labels = {
        "근로지원인 서비스 신청서", "14일", "대 표", "근로지원인 서비스 신청 내용",
        "신청서 작성", "접 수", "검 토", "결 재", "결정 통지",
        "처 리 기 관(한국장애인고용공단)", "년       월       일",
        "사업체유형", "보조공학기기사용여부",
    }
    fields = [f for f in fields if f["label"] not in skip_labels]

    # 중복 제거 (수행시간 등)
    seen = set()
    unique_fields = []
    for f in fields:
        key = f["label"]
        if key in seen:
            continue
        seen.add(key)
        unique_fields.append(f)
    fields = unique_fields

    field_rows = ""
    for f in fields:
        label = f["label"]
        field_id = label.replace(" ", "_").replace("(", "").replace(")", "")
        field_rows += f"""
        <tr>
            <td class="label">{label}</td>
            <td><input type="text" name="{label}" id="{field_id}" placeholder="{label} 입력"></td>
        </tr>"""

    checkbox_rows = ""
    for cg in checkboxes:
        options_html = ""
        for opt in cg["options"]:
            opt_clean = opt.strip("()")
            if not opt_clean or opt_clean in ("중증여부",):
                continue
            options_html += f"""
                <label class="check-label">
                    <input type="checkbox" name="check_{opt_clean}" value="{opt_clean}"> {opt_clean}
                </label>"""
        if options_html:
            raw = cg["raw_text"][:40]
            checkbox_rows += f"""
        <tr>
            <td class="label">{raw}...</td>
            <td class="check-group">{options_html}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{title} — 서식 편집기</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Pretendard', 'Apple SD Gothic Neo', sans-serif; background: #f5f7fa; padding: 20px; }}
.container {{ max-width: 800px; margin: 0 auto; }}
h1 {{ font-size: 24px; margin-bottom: 8px; color: #1a1a2e; }}
.source {{ color: #666; font-size: 13px; margin-bottom: 20px; }}
.card {{ background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 24px; margin-bottom: 16px; }}
.card h2 {{ font-size: 16px; color: #333; margin-bottom: 16px; border-bottom: 2px solid #4361ee; padding-bottom: 8px; }}
table {{ width: 100%; border-collapse: collapse; }}
tr {{ border-bottom: 1px solid #eee; }}
td {{ padding: 10px 8px; vertical-align: middle; }}
td.label {{ width: 180px; font-weight: 600; color: #444; font-size: 14px; }}
input[type="text"] {{ width: 100%; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }}
input[type="text"]:focus {{ outline: none; border-color: #4361ee; box-shadow: 0 0 0 3px rgba(67,97,238,0.1); }}
.check-group {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.check-label {{ display: flex; align-items: center; gap: 4px; font-size: 13px; padding: 4px 10px; background: #f0f0f0; border-radius: 16px; cursor: pointer; }}
.check-label:hover {{ background: #e0e7ff; }}
input[type="checkbox"] {{ accent-color: #4361ee; }}
.btn-group {{ display: flex; gap: 12px; margin-top: 20px; }}
button {{ padding: 12px 32px; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; }}
.btn-primary {{ background: #4361ee; color: white; }}
.btn-primary:hover {{ background: #3451d1; }}
.btn-secondary {{ background: #e0e0e0; color: #333; }}
.status {{ margin-top: 12px; padding: 10px; border-radius: 6px; display: none; }}
.status.success {{ display: block; background: #d4edda; color: #155724; }}
.status.error {{ display: block; background: #f8d7da; color: #721c24; }}
</style>
</head>
<body>
<div class="container">
    <h1>{title}</h1>
    <p class="source">원본: {source}</p>

    <form id="formEditor" method="POST" action="/generate">
    <div class="card">
        <h2>입력 필드</h2>
        <table>{field_rows}
        </table>
    </div>

    <div class="card">
        <h2>체크박스</h2>
        <table>{checkbox_rows}
        </table>
    </div>

    <div class="btn-group">
        <button type="submit" class="btn-primary">HWPX 생성 & 다운로드</button>
        <button type="reset" class="btn-secondary">초기화</button>
    </div>
    </form>

    <div id="status" class="status"></div>
</div>

<script>
document.getElementById('formEditor').addEventListener('submit', async (e) => {{
    e.preventDefault();
    const form = new FormData(e.target);
    const data = {{}};
    const checks = [];

    for (const [key, value] of form.entries()) {{
        if (key.startsWith('check_') && value) {{
            checks.push(value);
        }} else if (value.trim()) {{
            data[key] = value.trim();
        }}
    }}

    const status = document.getElementById('status');
    status.className = 'status';
    status.style.display = 'none';

    try {{
        const resp = await fetch('/generate', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ data, checks }})
        }});

        if (resp.ok) {{
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = '{source.replace(".owpml", "").replace(".hwpx", "")}_filled.hwpx';
            a.click();
            status.textContent = '✅ 파일이 생성되었습니다!';
            status.className = 'status success';
        }} else {{
            const err = await resp.text();
            status.textContent = '❌ 생성 실패: ' + err;
            status.className = 'status error';
        }}
    }} catch (err) {{
        status.textContent = '❌ 서버 연결 실패: ' + err;
        status.className = 'status error';
    }}
}});
</script>
</body>
</html>"""


class FormEditorHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            html = generate_html(SCHEMA)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
        elif self.path == "/schema":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(SCHEMA, ensure_ascii=False, indent=2).encode("utf-8"))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/generate":
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8")

            try:
                payload = json.loads(body)
                data_input = payload.get("data", {})
                checks = payload.get("checks", [])

                # data를 fill_pattern 형식으로 변환
                fill_data = {}
                for field in SCHEMA["fields"]:
                    label = field["label"]
                    if label in data_input:
                        fill_data[f">{label}<"] = f">{label}  {data_input[label]}<"

                # 체크박스: [  ] → [√] 변환
                check_replacements = {}
                for check_val in checks:
                    check_replacements[f"{check_val} [  ]"] = f"{check_val} [√]"
                    # □ 방식도 처리
                fill_data.update(check_replacements)

                # 생성
                with tempfile.NamedTemporaryFile(suffix=".hwpx", delete=False) as tmp:
                    output_path = tmp.name

                fill_template_checkbox(
                    TEMPLATE_PATH,
                    data=fill_data,
                    checks=checks,
                    output_path=output_path,
                )

                with open(output_path, "rb") as f:
                    content = f.read()
                os.unlink(output_path)

                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", "attachment; filename=filled.hwpx")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"Error: {e}".encode("utf-8"))
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    global TEMPLATE_PATH, SCHEMA

    if len(sys.argv) < 2:
        print("Usage: python form_editor.py <template.hwpx|owpml> [--port 8080]")
        sys.exit(1)

    TEMPLATE_PATH = sys.argv[1]
    if not os.path.exists(TEMPLATE_PATH):
        print(f"Error: {TEMPLATE_PATH} not found")
        sys.exit(1)

    port = 8080
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])

    SCHEMA = extract_schema(TEMPLATE_PATH)
    print(f"Template: {TEMPLATE_PATH}")
    print(f"Fields: {len(SCHEMA['fields'])}, Checkboxes: {len(SCHEMA['checkboxes'])}")
    print(f"Server: http://localhost:{port}")

    server = http.server.HTTPServer(("", port), FormEditorHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutdown.")
        server.server_close()


if __name__ == "__main__":
    main()
