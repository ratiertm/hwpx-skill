"""Template Builder — HWPX 서식에서 입력 필드를 지정하고 schema.json 저장

Usage:
    python template_builder.py <template.hwpx|owpml> [--port 8081]

1. 서식 업로드 → 전체 필드 스캔
2. LLM/규칙 기반 입력 필드 자동 추천
3. 사용자가 토글로 확인/수정
4. schema.json 저장 → form_editor.py에서 사용
"""
import http.server
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pyhwpxlib.api import extract_schema, analyze_schema_with_llm

TEMPLATE_PATH = ""
ANALYZED = {}


def generate_builder_html(analyzed):
    title = analyzed.get('title', '서식')
    source = analyzed.get('source', '')

    input_fields = analyzed.get('input_fields', [])
    fixed_fields = analyzed.get('fixed_fields', [])
    header_fields = analyzed.get('header_fields', [])
    checkboxes = analyzed.get('checkboxes', [])

    all_fields = []
    for f in input_fields:
        all_fields.append({**f, '_recommended': 'input'})
    for f in fixed_fields:
        all_fields.append({**f, '_recommended': 'fixed'})
    for f in header_fields:
        all_fields.append({**f, '_recommended': 'header'})

    # 중복 제거
    seen = set()
    unique = []
    for f in all_fields:
        key = f['label']
        if key not in seen:
            seen.add(key)
            unique.append(f)
    all_fields = unique

    field_rows = ""
    for i, f in enumerate(all_fields):
        label = f['label']
        rec = f['_recommended']
        checked_input = 'checked' if rec == 'input' else ''
        checked_fixed = 'checked' if rec == 'fixed' else ''
        checked_header = 'checked' if rec == 'header' else ''
        bg = '#e8f5e9' if rec == 'input' else '#fff'

        field_rows += f"""
        <tr class="field-row" data-type="{rec}" style="background:{bg}">
            <td class="label-cell">{label}</td>
            <td class="toggle-cell">
                <label><input type="radio" name="field_{i}" value="input" {checked_input}> 입력</label>
                <label><input type="radio" name="field_{i}" value="fixed" {checked_fixed}> 고정</label>
                <label><input type="radio" name="field_{i}" value="header" {checked_header}> 제목</label>
            </td>
        </tr>"""

    checkbox_rows = ""
    for i, c in enumerate(checkboxes):
        raw = c.get('raw_text', '')[:60]
        options = ', '.join(c.get('options', [])[:5])
        checkbox_rows += f"""
        <tr>
            <td class="label-cell">{raw}</td>
            <td class="toggle-cell"><span class="badge">체크박스</span> {options}</td>
        </tr>"""

    allfields_json = json.dumps([{'label': f['label'], 'fill_pattern': f.get('fill_pattern',''), 'table': f.get('table',0)} for f in all_fields], ensure_ascii=False)
    checkboxes_json = json.dumps(checkboxes, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>Template Builder — {title}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Pretendard', 'Apple SD Gothic Neo', sans-serif; background: #f0f2f5; padding: 20px; }}
.container {{ max-width: 900px; margin: 0 auto; }}
h1 {{ font-size: 22px; color: #1a1a2e; margin-bottom: 4px; }}
.subtitle {{ color: #666; font-size: 13px; margin-bottom: 16px; }}
.stats {{ display: flex; gap: 12px; margin-bottom: 16px; }}
.stat {{ background: white; padding: 12px 20px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
.stat .num {{ font-size: 24px; font-weight: 700; color: #4361ee; }}
.stat .lbl {{ font-size: 12px; color: #888; }}
.card {{ background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); padding: 20px; margin-bottom: 16px; }}
.card h2 {{ font-size: 15px; color: #333; margin-bottom: 12px; border-bottom: 2px solid #4361ee; padding-bottom: 6px; }}
table {{ width: 100%; border-collapse: collapse; }}
tr {{ border-bottom: 1px solid #eee; }}
td {{ padding: 8px; font-size: 13px; }}
td.label-cell {{ width: 55%; font-weight: 500; }}
td.toggle-cell {{ width: 45%; }}
td.toggle-cell label {{ margin-right: 10px; cursor: pointer; font-size: 12px; }}
input[type="radio"] {{ accent-color: #4361ee; }}
.badge {{ background: #e0e7ff; color: #4361ee; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
.field-row[data-type="input"] {{ background: #e8f5e9; }}
.field-row[data-type="fixed"] {{ background: #fff; }}
.field-row[data-type="header"] {{ background: #fff3e0; }}
.btn-group {{ display: flex; gap: 12px; margin-top: 16px; }}
button {{ padding: 12px 28px; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }}
.btn-primary {{ background: #4361ee; color: white; }}
.btn-primary:hover {{ background: #3451d1; }}
.btn-secondary {{ background: #e0e0e0; color: #333; }}
.status {{ margin-top: 12px; padding: 10px; border-radius: 6px; display: none; font-size: 13px; }}
.status.success {{ display: block; background: #d4edda; color: #155724; }}
</style>
</head>
<body>
<div class="container">
    <h1>Template Builder</h1>
    <p class="subtitle">{source} — 필드를 입력/고정/제목으로 분류하세요</p>

    <div class="stats">
        <div class="stat"><div class="num" id="inputCount">{len(input_fields)}</div><div class="lbl">입력 필드</div></div>
        <div class="stat"><div class="num" id="fixedCount">{len(fixed_fields)}</div><div class="lbl">고정 텍스트</div></div>
        <div class="stat"><div class="num">{len(checkboxes)}</div><div class="lbl">체크박스</div></div>
    </div>

    <form id="builderForm">
    <div class="card">
        <h2>필드 분류 (초록=입력, 흰색=고정, 주황=제목)</h2>
        <table id="fieldTable">{field_rows}
        </table>
    </div>

    <div class="card">
        <h2>체크박스 (자동 감지)</h2>
        <table>{checkbox_rows}
        </table>
    </div>

    <div class="btn-group">
        <button type="button" class="btn-primary" onclick="saveSchema()">schema.json 저장</button>
        <button type="button" class="btn-secondary" onclick="resetToRecommended()">추천값 초기화</button>
    </div>
    </form>

    <div id="status" class="status"></div>
</div>

<script>
const allFields = ALLFIELDS_PLACEHOLDER;

// 라디오 변경 시 배경색 업데이트 + 카운트
document.querySelectorAll('input[type="radio"]').forEach(r => {{
    r.addEventListener('change', () => {{
        const row = r.closest('tr');
        const val = r.value;
        row.dataset.type = val;
        row.style.background = val === 'input' ? '#e8f5e9' : val === 'header' ? '#fff3e0' : '#fff';
        updateCounts();
    }});
}});

function updateCounts() {{
    const rows = document.querySelectorAll('.field-row');
    let inp = 0, fix = 0;
    rows.forEach(r => {{
        if (r.dataset.type === 'input') inp++;
        else fix++;
    }});
    document.getElementById('inputCount').textContent = inp;
    document.getElementById('fixedCount').textContent = fix;
}}

function resetToRecommended() {{
    document.querySelectorAll('.field-row').forEach((row, i) => {{
        const rec = row.dataset.type;
        const radio = row.querySelector(`input[value="${{rec}}"]`);
        if (radio) radio.checked = true;
    }});
    updateCounts();
}}

async function saveSchema() {{
    const fields = [];
    document.querySelectorAll('.field-row').forEach((row, i) => {{
        const selected = row.querySelector('input[type="radio"]:checked');
        const type = selected ? selected.value : 'fixed';
        fields.push({{
            ...allFields[i],
            field_type: type
        }});
    }});

    const schema = {{
        title: '{title}',
        source: '{source}',
        fields: fields,
        checkboxes: CHECKBOXES_PLACEHOLDER
    }};

    const resp = await fetch('/save-schema', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(schema)
    }});

    const status = document.getElementById('status');
    if (resp.ok) {{
        const result = await resp.json();
        status.textContent = '✅ ' + result.message;
        status.className = 'status success';
    }}
}}
</script>
</body>
</html>"""

    html = html.replace('ALLFIELDS_PLACEHOLDER', allfields_json)
    html = html.replace('CHECKBOXES_PLACEHOLDER', checkboxes_json)
    return html


class BuilderHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            html = generate_builder_html(ANALYZED)
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/save-schema':
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len).decode('utf-8')
            schema = json.loads(body)

            # schema.json 저장 (템플릿 파일 옆에)
            out_dir = Path(TEMPLATE_PATH).parent
            schema_path = out_dir / f'{Path(TEMPLATE_PATH).stem}_schema.json'
            with open(schema_path, 'w', encoding='utf-8') as f:
                json.dump(schema, f, ensure_ascii=False, indent=2)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({
                'message': f'저장 완료: {schema_path}',
                'path': str(schema_path),
            }, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        print(f'[{self.log_date_time_string()}] {format % args}')


def main():
    global TEMPLATE_PATH, ANALYZED

    if len(sys.argv) < 2:
        print('Usage: python template_builder.py <template.hwpx|owpml> [--port 8081]')
        sys.exit(1)

    TEMPLATE_PATH = sys.argv[1]
    port = 8081
    if '--port' in sys.argv:
        port = int(sys.argv[sys.argv.index('--port') + 1])

    schema = extract_schema(TEMPLATE_PATH)
    ANALYZED = analyze_schema_with_llm(schema)

    print(f'Template: {TEMPLATE_PATH}')
    print(f'Input fields: {len(ANALYZED["input_fields"])}')
    print(f'Fixed fields: {len(ANALYZED["fixed_fields"])}')
    print(f'Checkboxes: {len(ANALYZED["checkboxes"])}')
    print(f'Builder UI: http://localhost:{port}')

    server = http.server.HTTPServer(('', port), BuilderHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutdown.')


if __name__ == '__main__':
    main()
