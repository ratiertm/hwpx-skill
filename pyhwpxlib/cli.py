"""pyhwpxlib CLI -- command-line tool for HWPX operations.

Usage::

    pyhwpxlib md2hwpx   input.md  -o output.hwpx
    pyhwpxlib hwpx2html input.hwpx -o output.html
    pyhwpxlib text      input.hwpx
    pyhwpxlib fill      template.hwpx -o out.hwpx -d name=Hong age=30
    pyhwpxlib info      input.hwpx
    pyhwpxlib merge     a.hwpx b.hwpx -o merged.hwpx
    pyhwpxlib unpack    input.hwpx -o unpacked/
    pyhwpxlib pack      unpacked/ -o output.hwpx
    pyhwpxlib validate  input.hwpx
    pyhwpxlib lint      input.hwpx
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _emit(result: dict, as_json: bool = False) -> None:
    """Output result as JSON or human-readable text."""
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _render_human(result)


def _render_human(result: dict) -> None:
    """Default human-readable rendering of a result dict."""
    cmd = result.get('command', '')
    ok = result.get('ok', True)
    f = result.get('file', '')

    if cmd == 'validate':
        print(f"\n{'=' * 50}")
        print(f"HWPX Validation: {f}")
        print(f"{'=' * 50}")
        print(f"Result: {'✅ VALID' if ok else '❌ INVALID'}")
        for check in result.get('checks', []):
            icon = '✅' if check['ok'] else '❌'
            print(f"  {icon} {check['name']}: {check.get('detail', '')}")

    elif cmd == 'lint':
        issues = result.get('issues', [])
        print(f"\nHWPX Lint: {f}")
        print(f"{'=' * 50}")
        if not issues:
            print("✅ No issues found.")
        else:
            for iss in issues:
                sev = iss['severity'].upper()
                icon = '⚠️' if sev == 'WARNING' else '❌'
                print(f"  {icon} [{iss['code']}] {iss['message']}")
                if iss.get('hint'):
                    print(f"     💡 {iss['hint']}")
            warns = sum(1 for i in issues if i['severity'] == 'warning')
            errs = sum(1 for i in issues if i['severity'] == 'error')
            print(f"\n{errs} error(s), {warns} warning(s)")

    elif cmd == 'font-check':
        fonts = result.get('fonts', [])
        print(f"\n📋 Fonts in document: {len(fonts)}")
        for fi in fonts:
            status = fi.get('status', 'ok')
            icons = {'ok': '✅', 'alias': '🔄', 'fallback': '⚠️', 'missing': '❌'}
            icon = icons.get(status, '?')
            line = f"  {icon} {fi['declared']}"
            if fi.get('resolved'):
                line += f" → {fi['resolved']}"
            if status == 'fallback':
                line += " (fallback)"
            print(line)

    elif cmd == 'themes list':
        for section in ('builtin', 'custom'):
            themes = [t for t in result.get('themes', []) if t['source'] == section]
            if themes:
                label = 'Built-in' if section == 'builtin' else 'Custom'
                print(f"\n{label} themes:")
                for t in themes:
                    print(f"  {t['name']:20s}  primary={t.get('primary', '?')}")


def _default_output(input_path: str, new_ext: str) -> str:
    """Derive a default output path by changing the extension."""
    return str(Path(input_path).with_suffix(new_ext))


def _cmd_md2hwpx(args: argparse.Namespace) -> None:
    from .api import convert_md_file_to_hwpx

    output = args.output or _default_output(args.input, ".hwpx")
    convert_md_file_to_hwpx(args.input, output, style=args.style)
    print(f"Converted: {args.input} -> {output}")


def _cmd_hwpx2html(args: argparse.Namespace) -> None:
    from .html_converter import convert_hwpx_to_html

    output = args.output or _default_output(args.input, ".html")
    convert_hwpx_to_html(args.input, output_path=output)
    print(f"Converted: {args.input} -> {output}")


def _cmd_text(args: argparse.Namespace) -> None:
    fmt = args.format

    if fmt == "text":
        from .api import extract_text
        print(extract_text(args.input))
    elif fmt == "markdown":
        from .api import extract_markdown
        print(extract_markdown(args.input))
    elif fmt == "html":
        from .api import extract_html
        print(extract_html(args.input))


def _cmd_fill(args: argparse.Namespace) -> None:
    from .api import fill_template

    if not args.output:
        print("Error: -o/--output is required for fill command.", file=sys.stderr)
        sys.exit(1)

    # Parse data from -d arguments
    data: dict[str, str] = {}
    if args.data:
        for item in args.data:
            if os.path.isfile(item) and item.endswith(".json"):
                # Load JSON file
                with open(item, "r", encoding="utf-8") as f:
                    json_data = json.load(f)
                if isinstance(json_data, dict):
                    data.update({str(k): str(v) for k, v in json_data.items()})
            elif "=" in item:
                key, _, value = item.partition("=")
                data[key] = value
            else:
                print(
                    f"Warning: skipping '{item}' (not key=value or .json file)",
                    file=sys.stderr,
                )

    fill_template(args.template, data, args.output)
    print(f"Filled: {args.template} -> {args.output}")


def _cmd_info(args: argparse.Namespace) -> None:
    import zipfile

    path = args.input
    print(f"File: {path}")
    print(f"Size: {os.path.getsize(path):,} bytes")

    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        sections = [n for n in names if "section" in n.lower() and n.endswith(".xml")]
        images = [n for n in names if n.startswith("BinData/") and not n.endswith("/")]

        print(f"Sections: {len(sections)}")
        print(f"Images: {len(images)}")
        print(f"Total files in ZIP: {len(names)}")

        if images:
            print("\nImages:")
            for img in images:
                size = zf.getinfo(img).file_size
                print(f"  {img} ({size:,} bytes)")

    # Extract text summary
    from .api import extract_text
    text = extract_text(path)
    char_count = len(text)
    line_count = text.count("\n") + 1
    print(f"\nText: {char_count:,} characters, {line_count:,} lines")
    if text:
        preview = text[:200].replace("\n", " ")
        print(f"Preview: {preview}...")


def _cmd_merge(args: argparse.Namespace) -> None:
    from .api import merge_documents

    if not args.output:
        print("Error: -o/--output is required for merge command.", file=sys.stderr)
        sys.exit(1)

    merge_documents(args.inputs, args.output)
    print(f"Merged {len(args.inputs)} files -> {args.output}")


def _cmd_unpack(args: argparse.Namespace) -> None:
    import zipfile

    hwpx_path = args.input
    output_dir = args.output or hwpx_path + ".unpacked"

    if not os.path.exists(hwpx_path):
        print(f"Error: {hwpx_path} not found", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    with zipfile.ZipFile(hwpx_path, "r") as z:
        z.extractall(output_dir)
        count = len(z.namelist())
    print(f"Unpacked {count} files → {output_dir}/")


def _cmd_pack(args: argparse.Namespace) -> None:
    import zipfile

    input_dir = args.input
    output_path = args.output

    if not os.path.isdir(input_dir):
        print(f"Error: {input_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    all_files = []
    for root, dirs, files in os.walk(input_dir):
        for f in files:
            full = os.path.join(root, f)
            arcname = os.path.relpath(full, input_dir)
            all_files.append((full, arcname))

    mimetype_file = None
    other_files = []
    for full, arcname in all_files:
        if arcname == "mimetype":
            mimetype_file = (full, arcname)
        else:
            other_files.append((full, arcname))

    with zipfile.ZipFile(output_path, "w") as zf:
        if mimetype_file:
            with open(mimetype_file[0], "rb") as f:
                data = f.read()
            zf.writestr(
                zipfile.ZipInfo("mimetype", date_time=(2026, 1, 1, 0, 0, 0)),
                data,
                compress_type=zipfile.ZIP_STORED,
            )
        for full, arcname in sorted(other_files):
            zf.write(full, arcname, compress_type=zipfile.ZIP_DEFLATED)

    size = os.path.getsize(output_path)
    print(f"Packed {len(all_files)} files → {output_path} ({size:,} bytes)")


def _cmd_template(args: argparse.Namespace) -> None:
    """Register / fill / show / list HWPX form templates."""
    action = getattr(args, "template_action", None)
    as_json = getattr(args, "json", False)
    if action is None:
        print("Usage: pyhwpxlib template {add|fill|show|list} ...", file=sys.stderr)
        sys.exit(2)

    if action == "add":
        from pyhwpxlib.templates import add as tpl_add
        info = tpl_add(args.input, name=args.name, shared=args.shared)
        if as_json:
            _emit({"command": "template add", **info}, True)
        else:
            print(f"Registered template '{info['name']}' ({info['source']})")
            print(f"  hwpx:   {info['hwpx_path']}")
            print(f"  schema: {info['schema_path']}")
            print(f"  fields: {info['fields']} across {info['tables']} table(s)")
            print(f"  title (kr): {info['title_kr']}")
        return

    if action == "fill":
        from pyhwpxlib.templates import fill as tpl_fill
        # Allow inline key=value,key=value or JSON file
        data_arg = args.data
        if "=" in data_arg and not os.path.exists(data_arg):
            data = {}
            for pair in data_arg.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    data[k.strip()] = v.strip()
        else:
            import json as _json
            data = _json.loads(open(data_arg, "r", encoding="utf-8").read())
        summary = tpl_fill(args.name, data, args.output)
        if as_json:
            _emit({"command": "template fill", **summary}, True)
        else:
            print(f"Filled template '{args.name}' -> {summary['output']}")
            print(f"  filled fields: {len(summary['filled'])}")
            if summary["missing_in_data"]:
                print(f"  missing in data: {len(summary['missing_in_data'])}: "
                      f"{summary['missing_in_data'][:5]}{'...' if len(summary['missing_in_data'])>5 else ''}")
            if summary["skipped"]:
                print(f"  skipped: {len(summary['skipped'])} (cell not found etc.)")
        return

    if action == "show":
        from pyhwpxlib.templates import show as tpl_show
        schema = tpl_show(args.name)
        if as_json:
            _emit(schema, True)
        else:
            print(f"Template: {schema.get('name')}  ({schema.get('title','')})")
            for tbl in schema.get("tables", []):
                print(f"  Table[{tbl.get('index')}] {tbl.get('rows','?')}x{tbl.get('cols','?')}: "
                      f"{len(tbl.get('fields',[]))} fields")
                for f in tbl.get("fields", [])[:10]:
                    cell = f.get('cell', [None, None])
                    label = f.get('label', '')
                    ph = f.get('placeholder', '')
                    extra = f" placeholder={ph!r}" if ph else ""
                    print(f"    {f['key']:<25}  cell={cell}  label={label!r}{extra}")
                if len(tbl.get("fields", [])) > 10:
                    print(f"    ... +{len(tbl['fields'])-10} more")
        return

    if action == "list":
        from pyhwpxlib.templates import list_templates
        items = list_templates()
        if as_json:
            _emit({"command": "template list", "templates": items}, True)
        else:
            if not items:
                print("(no templates registered)")
                return
            for it in items:
                src = "[skill]" if it["source"] == "skill" else "[user] "
                print(f"  {src} {it['name']:<25}  {it['hwpx_path']}")
        return

    print(f"Unknown template action: {action}", file=sys.stderr)
    sys.exit(2)


def _cmd_reflow_linesegs(args: argparse.Namespace) -> None:
    """Strip stale <hp:linesegarray> blocks to fix Hancom security warning."""
    import zipfile

    hwpx_path = args.input
    output_path = args.output or hwpx_path
    mode = args.mode
    as_json = getattr(args, "json", False)

    if not os.path.exists(hwpx_path):
        print(f"File not found: {hwpx_path}", file=sys.stderr)
        sys.exit(1)

    from pyhwpxlib.postprocess import (
        strip_linesegarrays,
        count_r3_violations,
        fix_textpos_overflow,
        count_textpos_overflow,
    )

    with zipfile.ZipFile(hwpx_path) as zin:
        infos = {n: zin.getinfo(n) for n in zin.namelist()}
        files = {n: zin.read(n) for n in zin.namelist()}

    section_files = sorted(
        n for n in files if n.startswith("Contents/section") and n.endswith(".xml")
    )
    total_changed = 0
    overflow_before = 0
    overflow_after = 0
    r3_before = 0
    r3_after = 0
    for sf in section_files:
        xml = files[sf].decode("utf-8")
        overflow_before += count_textpos_overflow(xml)
        r3_before += count_r3_violations(xml)
        if mode == "precise":
            new_xml, n = fix_textpos_overflow(xml)
        else:
            new_xml, n = strip_linesegarrays(xml, mode=mode)
        files[sf] = new_xml.encode("utf-8")
        total_changed += n
        overflow_after += count_textpos_overflow(new_xml)
        r3_after += count_r3_violations(new_xml)

    with zipfile.ZipFile(output_path, "w") as zout:
        for n, info in infos.items():
            ni = zipfile.ZipInfo(filename=n, date_time=info.date_time)
            ni.compress_type = info.compress_type
            ni.external_attr = info.external_attr
            zout.writestr(ni, files[n])

    result = {
        "command": "reflow-linesegs",
        "ok": True,
        "input": hwpx_path,
        "output": output_path,
        "mode": mode,
        "changes": total_changed,
        "textpos_overflow_before": overflow_before,
        "textpos_overflow_after": overflow_after,
        "r3_before": r3_before,
        "r3_after": r3_after,
    }
    _emit(result, as_json)


def _cmd_validate(args: argparse.Namespace) -> None:
    import zipfile
    import xml.etree.ElementTree as ET

    hwpx_path = args.input
    as_json = getattr(args, 'json', False)
    required = ["mimetype", "Contents/header.xml", "Contents/section0.xml", "Contents/content.hpf"]
    checks = []

    if not zipfile.is_zipfile(hwpx_path):
        result = {'command': 'validate', 'ok': False, 'file': hwpx_path,
                  'checks': [{'name': 'zip_open', 'ok': False, 'detail': 'Not a valid ZIP file'}]}
        _emit(result, as_json)
        sys.exit(1)

    with zipfile.ZipFile(hwpx_path, "r") as z:
        names = z.namelist()
        checks.append({'name': 'zip_open', 'ok': True, 'detail': f'{len(names)} files'})

        for req in required:
            present = req in names
            checks.append({'name': f'file_{req.split("/")[-1]}', 'ok': present,
                          'detail': 'present' if present else 'MISSING'})

        if "mimetype" in names:
            mt = z.read("mimetype").decode("utf-8").strip()
            checks.append({'name': 'mimetype_value', 'ok': True, 'detail': mt})

        for xml_file in ["Contents/header.xml", "Contents/section0.xml"]:
            if xml_file in names:
                try:
                    content = z.read(xml_file).decode("utf-8")
                    ET.fromstring(content)
                    checks.append({'name': f'xml_parse_{xml_file.split("/")[-1]}', 'ok': True,
                                  'detail': f'{len(content):,} bytes'})
                except ET.ParseError as e:
                    checks.append({'name': f'xml_parse_{xml_file.split("/")[-1]}', 'ok': False,
                                  'detail': str(e)})

    ok = all(c['ok'] for c in checks)
    result = {'command': 'validate', 'ok': ok, 'file': hwpx_path, 'checks': checks}
    _emit(result, as_json)
    sys.exit(0 if ok else 1)


def _cmd_lint(args: argparse.Namespace) -> None:
    """Lint HWPX for rendering/compatibility risks."""
    import zipfile
    import xml.etree.ElementTree as ET
    import re

    hwpx_path = args.input
    as_json = getattr(args, 'json', False)
    issues = []

    if not os.path.exists(hwpx_path):
        print(f"File not found: {hwpx_path}")
        sys.exit(1)

    try:
        with zipfile.ZipFile(hwpx_path) as z:
            names = z.namelist()

            # Lint all section XML files
            sec_files = sorted(n for n in names if n.startswith('Contents/section') and n.endswith('.xml'))
            for sec_file in sec_files:
                xml_str = z.read(sec_file).decode('utf-8')

                # Rule 1: \n inside <hp:t> text nodes
                for m in re.finditer(r'<hp:t[^>]*>([^<]*)</hp:t>', xml_str):
                    text = m.group(1)
                    if '\n' in text:
                        issues.append({
                            'code': 'TEXT_NEWLINE_IN_RUN',
                            'severity': 'error',
                            'message': f'Text node contains newline: "{text[:40]}..."',
                            'path': sec_file,
                            'hint': 'Split into separate <hp:p> paragraphs instead of \\n.',
                        })

                # Rule 2: Empty paragraph before first content (secPr issue)
                try:
                    root = ET.fromstring(xml_str)
                    ns = {'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph'}
                    paras = root.findall('.//hp:p', ns)
                    if len(paras) >= 2:
                        first_p = paras[0]
                        has_secpr = first_p.find('.//hp:secPr', ns) is not None
                        # Check if first para has secPr but no text
                        first_texts = [t.text for t in first_p.iter() if t.tag.endswith('}t') and t.text and t.text.strip()]
                        if not has_secpr and not first_texts:
                            issues.append({
                                'code': 'EMPTY_FIRST_PARAGRAPH',
                                'severity': 'warning',
                                'message': 'First paragraph has no text and no secPr.',
                                'path': sec_file,
                                'hint': 'Empty paragraphs before content may cause rendering issues.',
                            })
                except ET.ParseError:
                    pass  # validate catches this

                # Rule 2.5: Lineseg textpos > paragraph text length (Hancom security trigger)
                # Verified 2026-04-27 via binary search: Hancom flags external modification
                # when any <hp:lineseg textpos="N"/> references a position past the end of
                # the paragraph's actual UTF-16 text length.
                from pyhwpxlib.postprocess import count_textpos_overflow, count_r3_violations
                tp_overflow = count_textpos_overflow(xml_str)
                if tp_overflow > 0:
                    issues.append({
                        'code': 'TEXTPOS_OVERFLOW',
                        'severity': 'error',
                        'message': f'{tp_overflow} lineseg(s) with textpos past end of text — Hancom WILL show security warning.',
                        'path': sec_file,
                        'hint': 'Run `pyhwpxlib reflow-linesegs <file>` (precise mode, default).',
                    })
                # Rule 2.6: rhwp R3 informational (renderer-only, NOT a Hancom trigger)
                r3_count = count_r3_violations(xml_str)
                if r3_count > 0:
                    issues.append({
                        'code': 'RHWP_R3_RENDER_RISK',
                        'severity': 'warning',
                        'message': f'{r3_count} paragraph(s) with single lineseg over long text — rhwp/external renderers may overlap glyphs.',
                        'path': sec_file,
                        'hint': 'Hancom itself reflows OK; only matters for external renderers.',
                    })

                # Rule 3: Very long single run (>500 chars) — potential overflow
                for m in re.finditer(r'<hp:t[^>]*>([^<]{500,})</hp:t>', xml_str):
                    issues.append({
                        'code': 'LONG_TEXT_RUN',
                        'severity': 'warning',
                        'message': f'Very long text run ({len(m.group(1))} chars) may cause overflow.',
                        'path': sec_file,
                        'hint': 'Consider splitting into multiple paragraphs.',
                    })

                # Rule 4: Unescaped & in text (would cause parse error, but check raw string)
                for m in re.finditer(r'<hp:t[^>]*>([^<]*&[^<]*)</hp:t>', xml_str):
                    text = m.group(1)
                    # Check for unescaped & (not &amp; &lt; &gt; &quot; &apos; &#)
                    if re.search(r'&(?!amp;|lt;|gt;|quot;|apos;|#)', text):
                        issues.append({
                            'code': 'UNESCAPED_AMPERSAND',
                            'severity': 'error',
                            'message': f'Unescaped & in text: "{text[:40]}..."',
                            'path': sec_file,
                            'hint': 'Use &amp; instead of bare &.',
                        })

            # Rule 5: Font declared but not in font_map
            if 'Contents/header.xml' in names:
                header_xml = z.read('Contents/header.xml').decode('utf-8')
                try:
                    hroot = ET.fromstring(header_xml)
                    doc_fonts = set()
                    for font_el in hroot.iter('{http://www.hancom.co.kr/hwpml/2011/head}font'):
                        face = font_el.get('face')
                        if face:
                            doc_fonts.add(face)
                    try:
                        from .rhwp_bridge import _DEFAULT_FONT_MAP
                        known = set(_DEFAULT_FONT_MAP.keys())
                    except ImportError:
                        known = set()
                    for font in doc_fonts:
                        if font.lower() not in known and font not in {'나눔고딕', 'NanumGothic'}:
                            issues.append({
                                'code': 'FONT_NOT_IN_MAP',
                                'severity': 'warning',
                                'message': f'Font "{font}" not in font_map — preview may use fallback.',
                                'path': 'Contents/header.xml',
                                'hint': 'Add to font_map or use a bundled font.',
                            })
                except ET.ParseError:
                    pass

    except zipfile.BadZipFile:
        issues.append({
            'code': 'INVALID_ZIP',
            'severity': 'error',
            'message': 'File is not a valid ZIP archive.',
            'path': hwpx_path,
            'hint': 'Run validate first.',
        })

    ok = not any(i['severity'] == 'error' for i in issues)
    result = {'command': 'lint', 'ok': ok, 'file': hwpx_path, 'issues': issues}
    _emit(result, as_json)
    sys.exit(0 if ok else 1)


def _cmd_font_check(args: argparse.Namespace) -> None:
    """Check font availability and resolution for an HWPX file."""
    import zipfile
    import xml.etree.ElementTree as ET

    path = args.input
    as_json = getattr(args, 'json', False)

    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)

    doc_fonts: set[str] = set()
    try:
        with zipfile.ZipFile(path) as z:
            header_xml = z.read("Contents/header.xml").decode("utf-8")
        root = ET.fromstring(header_xml)
        for font_el in root.iter("{http://www.hancom.co.kr/hwpml/2011/head}font"):
            face = font_el.get("face")
            if face:
                doc_fonts.add(face)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        sys.exit(1)

    # Resolve each font against font_map
    try:
        from .rhwp_bridge import _DEFAULT_FONT_MAP
        font_map = dict(_DEFAULT_FONT_MAP)
    except ImportError:
        font_map = {}

    fonts_result = []
    for font in sorted(doc_fonts):
        lower = font.lower()
        resolved = font_map.get(lower, '')
        if resolved and os.path.exists(resolved):
            # Check if it's the bundled font (alias) or exact match
            if lower in ('나눔고딕', 'nanumgothic', 'nanum gothic'):
                status = 'ok'
            elif lower in ('함초롬돋움', '함초롬바탕'):
                status = 'alias'
            else:
                status = 'ok'
            fonts_result.append({'declared': font, 'resolved': resolved, 'status': status})
        elif resolved:
            # Path in map but file doesn't exist
            fonts_result.append({'declared': font, 'resolved': resolved, 'status': 'missing'})
        else:
            # Not in map at all — will use fallback
            fonts_result.append({'declared': font, 'resolved': '', 'status': 'fallback'})

    ok = not any(f['status'] in ('missing',) for f in fonts_result)
    result = {'command': 'font-check', 'ok': ok, 'file': path, 'fonts': fonts_result}
    _emit(result, as_json)


def _cmd_themes(args: argparse.Namespace) -> None:
    """List saved custom themes or extract/save a theme."""
    from .themes import BUILTIN_THEMES, _THEMES_DIR, extract_theme, save_theme, load_theme

    as_json = getattr(args, 'json', False)

    if args.action == 'list':
        themes_list = []
        for name in sorted(BUILTIN_THEMES):
            t = BUILTIN_THEMES[name]
            themes_list.append({'name': name, 'source': 'builtin', 'primary': t.palette.primary})
        if _THEMES_DIR.exists():
            for p in sorted(_THEMES_DIR.glob('*.json')):
                try:
                    t = load_theme(p)
                    themes_list.append({'name': t.name, 'source': 'custom',
                                       'primary': t.palette.primary, 'font': t.fonts.body_hangul})
                except Exception:
                    themes_list.append({'name': p.stem, 'source': 'custom', 'primary': '?'})
        result = {'command': 'themes list', 'ok': True, 'themes': themes_list}
        _emit(result, as_json)

    elif args.action == 'extract':
        if not args.input:
            print("Error: --input required for extract")
            sys.exit(1)
        name = args.name or Path(args.input).stem
        theme = extract_theme(args.input, name=name)
        path = save_theme(theme)
        print(f"Extracted theme '{theme.name}':")
        print(f"  Primary: {theme.palette.primary}")
        print(f"  Font:    {theme.fonts.body_hangul}")
        print(f"  Body:    {theme.sizes.body}pt")
        print(f"  Saved:   {path}")
        print(f"\nUse: HwpxBuilder(theme='custom/{theme.name}')")

    elif args.action == 'delete':
        if not args.name:
            print("Error: --name required for delete")
            sys.exit(1)
        target = _THEMES_DIR / f'{args.name}.json'
        if target.exists():
            target.unlink()
            print(f"Deleted theme: {args.name}")
        else:
            print(f"Theme not found: {args.name}")
            sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    """Entry point for the pyhwpxlib CLI."""
    parser = argparse.ArgumentParser(
        prog="pyhwpxlib",
        description="HWPX file tool -- create, convert, and manipulate HWPX documents.",
    )
    sub = parser.add_subparsers(dest="command")

    # md2hwpx
    p_md = sub.add_parser("md2hwpx", help="Convert Markdown to HWPX")
    p_md.add_argument("input", help="Input .md file")
    p_md.add_argument("-o", "--output", help="Output .hwpx file")
    p_md.add_argument("-s", "--style", default="github", help="Style preset (default: github)")

    # hwpx2html
    p_html = sub.add_parser("hwpx2html", help="Convert HWPX to HTML")
    p_html.add_argument("input", help="Input .hwpx file")
    p_html.add_argument("-o", "--output", help="Output .html file")

    # text
    p_text = sub.add_parser("text", help="Extract text from HWPX")
    p_text.add_argument("input", help="Input .hwpx file")
    p_text.add_argument(
        "-f", "--format",
        choices=["text", "markdown", "html"],
        default="text",
        help="Output format (default: text)",
    )

    # fill
    p_fill = sub.add_parser("fill", help="Fill template with data")
    p_fill.add_argument("template", help="Template .hwpx file")
    p_fill.add_argument("-o", "--output", help="Output .hwpx file")
    p_fill.add_argument(
        "-d", "--data",
        help="JSON data file or key=value pairs",
        nargs="+",
    )

    # info
    p_info = sub.add_parser("info", help="Show HWPX file info")
    p_info.add_argument("input", help="Input .hwpx file")

    # merge
    p_merge = sub.add_parser("merge", help="Merge multiple HWPX files")
    p_merge.add_argument("inputs", nargs="+", help="Input .hwpx files")
    p_merge.add_argument("-o", "--output", help="Output .hwpx file")

    # unpack
    p_unpack = sub.add_parser("unpack", help="Unpack HWPX to folder")
    p_unpack.add_argument("input", help="Input .hwpx file")
    p_unpack.add_argument("-o", "--output", help="Output directory")

    # pack
    p_pack = sub.add_parser("pack", help="Pack folder to HWPX")
    p_pack.add_argument("input", help="Input directory")
    p_pack.add_argument("-o", "--output", required=True, help="Output .hwpx file")

    # validate
    p_val = sub.add_parser("validate", help="Validate HWPX file structure")
    p_val.add_argument("input", help="Input .hwpx file")
    p_val.add_argument("--json", action="store_true", help="Output as JSON")

    # lint
    p_lint = sub.add_parser("lint", help="Check HWPX for rendering/compatibility risks")
    p_lint.add_argument("input", help="Input .hwpx file")
    p_lint.add_argument("--json", action="store_true", help="Output as JSON")

    # font-check
    p_fc = sub.add_parser("font-check", help="Check font availability and resolution")
    p_fc.add_argument("input", help="Input .hwpx file")
    p_fc.add_argument("--json", action="store_true", help="Output as JSON")

    # reflow-linesegs
    p_rls = sub.add_parser(
        "reflow-linesegs",
        help="Strip stale <hp:linesegarray> blocks (Hancom security fix for edited HWPX)",
    )
    p_rls.add_argument("input", help="Input .hwpx file")
    p_rls.add_argument("-o", "--output", help="Output .hwpx file (default: overwrite input)")
    p_rls.add_argument(
        "--mode",
        choices=["precise", "remove", "empty"],
        default="precise",
        help="precise (default): remove only linesegs with textpos > text len (Hancom-trigger fix); "
             "remove: delete entire <hp:linesegarray> blocks; "
             "empty: keep empty <hp:linesegarray></hp:linesegarray>",
    )
    p_rls.add_argument("--json", action="store_true", help="Output as JSON")

    # template
    p_tpl = sub.add_parser("template", help="Register and reuse HWPX form templates")
    tpl_sub = p_tpl.add_subparsers(dest="template_action")
    tpl_add = tpl_sub.add_parser("add", help="Convert + auto-schema + register a template")
    tpl_add.add_argument("input", help=".hwp or .hwpx file")
    tpl_add.add_argument("--name", help="ASCII template name (default: derived from filename)")
    tpl_add.add_argument("--shared", action="store_true",
                         help="Save into skill/templates/ (commit-intended) instead of user dir")
    tpl_add.add_argument("--json", action="store_true", help="JSON output")
    tpl_fill = tpl_sub.add_parser("fill", help="Fill a registered template with data")
    tpl_fill.add_argument("name", help="template name (or path to .hwpx)")
    tpl_fill.add_argument("-d", "--data", required=True, help="JSON data file or 'key=value,key=value'")
    tpl_fill.add_argument("-o", "--output", required=True, help="output .hwpx path")
    tpl_fill.add_argument("--json", action="store_true", help="JSON output")
    tpl_show = tpl_sub.add_parser("show", help="Show schema for a template")
    tpl_show.add_argument("name", help="template name")
    tpl_show.add_argument("--json", action="store_true", help="JSON output")
    tpl_list = tpl_sub.add_parser("list", help="List all registered templates")
    tpl_list.add_argument("--json", action="store_true", help="JSON output")

    # themes
    p_th = sub.add_parser("themes", help="Manage themes (list/extract/delete)")
    p_th.add_argument("action", choices=["list", "extract", "delete"],
                       help="list: show all themes, extract: save theme from HWPX, delete: remove custom theme")
    p_th.add_argument("--input", "-i", help="Input .hwpx file (for extract)")
    p_th.add_argument("--name", "-n", help="Theme name (for extract/delete)")
    p_th.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return

    dispatch = {
        "md2hwpx": _cmd_md2hwpx,
        "hwpx2html": _cmd_hwpx2html,
        "text": _cmd_text,
        "fill": _cmd_fill,
        "info": _cmd_info,
        "merge": _cmd_merge,
        "unpack": _cmd_unpack,
        "pack": _cmd_pack,
        "validate": _cmd_validate,
        "lint": _cmd_lint,
        "reflow-linesegs": _cmd_reflow_linesegs,
        "template": _cmd_template,
        "font-check": _cmd_font_check,
        "themes": _cmd_themes,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
