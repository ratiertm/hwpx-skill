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


def _warn_if_nonstandard(hwpx_path: str) -> None:
    """v0.14.0: rhwp 노선 — 비표준 lineseg 가 그대로 보존되었음을 사용자에게 고지.

    Saves silently checked output and emits a stderr warning when the file
    contains structures that Hancom would reflow but external renderers
    (rhwp) would render literally. Default behaviour is to NOT auto-fix —
    callers must opt in via --fix / fix_linesegs=True.
    """
    if not hwpx_path or not os.path.exists(hwpx_path):
        return
    try:
        import zipfile
        from pyhwpxlib.postprocess import count_textpos_overflow
        with zipfile.ZipFile(hwpx_path) as z:
            section_names = [n for n in z.namelist()
                             if n.startswith("Contents/section") and n.endswith(".xml")]
            total = sum(count_textpos_overflow(z.read(n).decode("utf-8"))
                        for n in section_names)
        if total > 0:
            print(
                f"[pyhwpxlib] 비표준 lineseg {total}건 (textpos > UTF-16 text). "
                f"한컴이 보안 경고를 띄울 수 있습니다. "
                f"보정하려면 --fix 또는 `pyhwpxlib doctor {hwpx_path} --fix`.",
                file=sys.stderr,
            )
    except Exception:
        # never let advisory warnings break the main command
        pass


def _render_human(result: dict) -> None:
    """Default human-readable rendering of a result dict."""
    cmd = result.get('command', '')
    ok = result.get('ok', True)
    f = result.get('file', '')

    if cmd == 'validate':
        print(f"\n{'=' * 50}")
        print(f"HWPX Validation: {f}")
        print(f"{'=' * 50}")
        mode = result.get('mode', 'compat')
        if mode == 'both':
            compat = result.get('compat') or {}
            strict = result.get('strict') or {}
            cok = compat.get('ok', True)
            sok = strict.get('ok', True)
            print(f"Compat (Hancom OK): {'✅ PASS' if cok else '❌ FAIL'}")
            for c in compat.get('checks', []):
                icon = '✅' if c['ok'] else '❌'
                print(f"  {icon} {c['name']}: {c.get('detail', '')}")
            print(f"\nStrict (OWPML spec): {'✅ PASS' if sok else '⚠️  ISSUES'}")
            for c in strict.get('checks', []):
                icon = '✅' if c['ok'] else '⚠️ '
                print(f"  {icon} {c['name']}: {c.get('detail', '')}")
            if cok and not sok:
                print("\n[pyhwpxlib] 한컴은 받아들이지만 OWPML 명세 어긋남. 외부 렌더(rhwp 등)에서 깨질 수 있음.")
                print("  보정: `pyhwpxlib doctor <file> --fix` 또는 명시적 --fix 플래그.")
        else:
            print(f"Mode: {mode}")
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
        info = tpl_add(
            args.input, name=args.name, shared=args.shared,
            fix_linesegs=getattr(args, "fix", False),
        )
        if as_json:
            _emit({"command": "template add", **info}, True)
        else:
            print(f"Registered template '{info['name']}' ({info['source']})")
            print(f"  hwpx:   {info['hwpx_path']}")
            print(f"  schema: {info['schema_path']}")
            print(f"  fields: {info['fields']} across {info['tables']} table(s)")
            print(f"  title (kr): {info['title_kr']}")
        _warn_if_nonstandard(info["hwpx_path"])
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
        summary = tpl_fill(
            args.name, data, args.output,
            fix_linesegs=getattr(args, "fix", False),
            log_history=not getattr(args, "no_history", False),
        )
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
            fixed = summary.get("linesegs_fixed", 0)
            if fixed > 0:
                print(f"  [pyhwpxlib] 비표준 lineseg {fixed}건 보정됨 (precise)")
            hist = summary.get("history")
            if hist:
                print(f"  [history] 누적 {hist['usage_count']}회 사용 "
                      f"(최근 {hist['history_count']}건 보존)")
        if not getattr(args, "fix", False):
            _warn_if_nonstandard(summary.get("output", args.output))
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

    if action == "diagnose":
        from pyhwpxlib.templates.diagnose import main as diagnose_main
        diagnose_argv = [args.hwpx]
        if getattr(args, "schema", None):
            diagnose_argv += ["--schema", args.schema]
        if as_json:
            diagnose_argv.append("--json")
        sys.exit(diagnose_main(diagnose_argv))

    if action == "context":
        from pyhwpxlib.templates.context import load_context
        ctx = load_context(args.name)
        if as_json:
            _emit(ctx.to_dict(), True)
        else:
            print(ctx.to_markdown())
        return

    if action == "annotate":
        from pyhwpxlib.templates.context import annotate as tpl_annot
        result = tpl_annot(
            args.name,
            description=getattr(args, "description", None),
            page_standard=getattr(args, "page_standard", None),
            structure_type=getattr(args, "structure_type", None),
            notes=getattr(args, "notes", None),
            add_decision=getattr(args, "add_decision", None),
        )
        if as_json:
            _emit({"command": "template annotate",
                   "name": args.name, **result}, True)
        else:
            if result["meta_updated"]:
                print(f"Updated _meta: {', '.join(result['meta_updated'])}")
            if result["decision_added"]:
                print(f"Decision appended to decisions.md (today's block)")
            if not result["meta_updated"] and not result["decision_added"]:
                print("(nothing changed — pass --description / --decision / etc.)")
        return

    if action == "log-fill":
        from pyhwpxlib.templates.context import log_fill
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
        info = log_fill(args.name, data,
                        output_path=getattr(args, "output_path", None))
        if as_json:
            _emit({"command": "template log-fill",
                   "name": args.name, **info}, True)
        else:
            print(f"history: 누적 {info['usage_count']}회 "
                  f"(최근 {info['history_count']}건 보존)")
        return

    if action == "open":
        from pyhwpxlib.templates.context import open_workspace
        rc = open_workspace(args.name)
        if as_json:
            _emit({"command": "template open",
                   "name": args.name, "returncode": rc}, True)
        else:
            if rc == 0:
                print(f"Opened workspace: {args.name}")
            else:
                print(f"Failed to open workspace: {args.name}",
                      file=sys.stderr)
                sys.exit(1)
        return

    if action == "migrate":
        from pyhwpxlib.templates.migration import (
            plan_migration, execute_migration,
        )
        from pathlib import Path as _Path
        root = _Path(args.root) if getattr(args, "root", None) else None
        plan = plan_migration(root)

        if getattr(args, "dry_run", False):
            if as_json:
                _emit({
                    "command": "template migrate (dry-run)",
                    "flat_files": [str(p) for p in plan.flat_files],
                    "targets": [str(p) for p in plan.target_workspaces],
                    "conflicts": plan.conflicts,
                    "backup_path": str(plan.backup_path),
                }, True)
            else:
                print(plan.report())
                if not plan.flat_files:
                    print("\n(마이그레이션 대상 없음 — 이미 v0.17.0 구조)")
            return

        if not plan.flat_files:
            if as_json:
                _emit({"command": "template migrate",
                       "migrated": 0, "skipped": 0,
                       "message": "no legacy flat files"}, True)
            else:
                print("(마이그레이션 대상 없음 — 이미 v0.17.0 구조)")
            return

        result = execute_migration(
            plan,
            backup=not getattr(args, "no_backup", False),
            overwrite=getattr(args, "overwrite", False),
        )
        if as_json:
            _emit({"command": "template migrate", **result}, True)
        else:
            print(f"Migrated: {result['migrated']}, Skipped: {result['skipped']}")
            if result.get("backup"):
                print(f"  Backup: {result['backup']}")
            if result.get("errors"):
                print(f"  Errors: {len(result['errors'])}")
                for err in result["errors"][:5]:
                    print(f"    - {err}")
        return

    print(f"Unknown template action: {action}", file=sys.stderr)
    sys.exit(2)


def _cmd_install_hook(args: argparse.Namespace) -> None:
    """Install Claude Code SessionStart hook script + show settings snippet."""
    from pathlib import Path as _Path
    from pyhwpxlib.templates.workspace import (
        install_session_hook, hook_settings_snippet,
    )

    target = _Path(args.target).expanduser() if getattr(args, "target", None) \
        else None
    script_path = install_session_hook(target)
    snippet = hook_settings_snippet(script_path)

    as_json = getattr(args, "json", False)
    if as_json:
        _emit({
            "command": "install-hook",
            "script_path": str(script_path),
            "settings_snippet": snippet,
        }, True)
    else:
        print(f"Installed SessionStart hook: {script_path}")
        print()
        print("Add to ~/.claude/settings.json (merge with existing hooks):")
        print(json.dumps(snippet, ensure_ascii=False, indent=2))
        print()
        print("이후 새 채팅 시작 시 등록된 양식 목록이 컨텍스트에 자동 주입됩니다.")


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


def _validate_compat(hwpx_path: str) -> dict:
    """Compat mode: zip integrity, required files, XML parse.

    This is the historical (≤ v0.13.x) behaviour — checks whether the file
    is a structurally well-formed HWPX that Hancom would open. Does NOT
    check OWPML spec conformance.
    """
    import zipfile
    import xml.etree.ElementTree as ET

    required = ["mimetype", "Contents/header.xml", "Contents/section0.xml", "Contents/content.hpf"]
    checks = []

    if not zipfile.is_zipfile(hwpx_path):
        return {"ok": False, "checks": [{"name": "zip_open", "ok": False,
                                          "detail": "Not a valid ZIP file"}]}

    with zipfile.ZipFile(hwpx_path, "r") as z:
        names = z.namelist()
        checks.append({"name": "zip_open", "ok": True, "detail": f"{len(names)} files"})
        for req in required:
            present = req in names
            checks.append({"name": f'file_{req.split("/")[-1]}', "ok": present,
                          "detail": "present" if present else "MISSING"})
        if "mimetype" in names:
            mt = z.read("mimetype").decode("utf-8").strip()
            checks.append({"name": "mimetype_value", "ok": True, "detail": mt})
        for xml_file in ["Contents/header.xml", "Contents/section0.xml"]:
            if xml_file in names:
                try:
                    content = z.read(xml_file).decode("utf-8")
                    ET.fromstring(content)
                    checks.append({"name": f'xml_parse_{xml_file.split("/")[-1]}',
                                   "ok": True, "detail": f"{len(content):,} bytes"})
                except ET.ParseError as e:
                    checks.append({"name": f'xml_parse_{xml_file.split("/")[-1]}',
                                   "ok": False, "detail": str(e)})
    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks}


def _validate_strict(hwpx_path: str) -> dict:
    """Strict mode: OWPML spec conformance — may flag files Hancom accepts.

    This is the rhwp-aligned check: does the file declare what the spec says
    it should, with values consistent with the actual content? A failing
    strict check does NOT mean Hancom rejects the file — it means external
    renderers / validators may render incorrectly because Hancom silently
    reflows on load.

    Checks
    ------
    - lineseg ``textpos`` ≤ UTF-16 length of paragraph text
    - paired ``<hp:t>...</hp:t>`` vs self-closing ``<hp:t/>`` — both legal
      but reported as info for visibility
    - core namespace declarations present (xmlns:hp, xmlns:hh)
    - first paragraph ordering: secPr if present, otherwise non-empty content
    """
    import zipfile
    import re
    import xml.etree.ElementTree as ET
    from pyhwpxlib.postprocess import count_textpos_overflow

    checks = []
    if not zipfile.is_zipfile(hwpx_path):
        return {"ok": False, "checks": [{"name": "zip_open", "ok": False,
                                          "detail": "Not a valid ZIP file"}]}

    with zipfile.ZipFile(hwpx_path, "r") as z:
        names = z.namelist()
        section_names = sorted(n for n in names
                               if n.startswith("Contents/section") and n.endswith(".xml"))

        # Check 1: lineseg textpos consistency
        total_overflow = 0
        for n in section_names:
            xml_str = z.read(n).decode("utf-8")
            total_overflow += count_textpos_overflow(xml_str)
        checks.append({
            "name": "lineseg_textpos_consistency",
            "ok": total_overflow == 0,
            "detail": (f"{total_overflow} lineseg(s) with textpos > UTF-16 text length"
                       if total_overflow else "all lineseg textpos within text bounds"),
        })

        # Check 2: hp:t form mix (info, not pass/fail)
        sc_count = 0
        paired_count = 0
        for n in section_names:
            xml_str = z.read(n).decode("utf-8")
            sc_count += len(re.findall(r"<hp:t[^>]*?/>", xml_str))
            paired_count += len(re.findall(r"<hp:t[^>]*>[^<]*</hp:t>", xml_str))
        checks.append({
            "name": "hp_t_form",
            "ok": True,  # informational
            "detail": f"paired={paired_count}, self_closing={sc_count}",
        })

        # Check 3: namespace declarations
        if "Contents/section0.xml" in names:
            try:
                xml_str = z.read("Contents/section0.xml").decode("utf-8")
                root = ET.fromstring(xml_str)
                ns_attrs = {k: v for k, v in root.attrib.items() if k.startswith("xmlns")}
                # ET strips xmlns: prefix to {namespace} form, so check via raw scan
                has_hp = "xmlns:hp=" in xml_str or 'xmlns="http://www.hancom.co.kr/hwpml/2011/paragraph"' in xml_str
                checks.append({
                    "name": "namespace_hp",
                    "ok": has_hp,
                    "detail": "hp namespace declared" if has_hp else "missing xmlns:hp",
                })
            except ET.ParseError as e:
                checks.append({"name": "namespace_hp", "ok": False, "detail": str(e)})

        # Check 4: first paragraph ordering / empty para before content
        if "Contents/section0.xml" in names:
            xml_str = z.read("Contents/section0.xml").decode("utf-8")
            try:
                root = ET.fromstring(xml_str)
                ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
                paras = root.findall(".//hp:p", ns)
                if paras:
                    first = paras[0]
                    has_secpr = first.find(".//hp:secPr", ns) is not None
                    first_texts = [t.text for t in first.iter()
                                    if t.tag.endswith("}t") and t.text and t.text.strip()]
                    bad_empty_first = (not has_secpr) and (not first_texts) and len(paras) >= 2
                    checks.append({
                        "name": "first_paragraph_ordering",
                        "ok": not bad_empty_first,
                        "detail": ("empty first paragraph without secPr — may break rendering"
                                   if bad_empty_first else "first paragraph valid"),
                    })
            except ET.ParseError:
                pass

    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks}


def _cmd_page_guard(args: argparse.Namespace) -> None:
    """page-guard CLI 핸들러. exit code 로 fail/pass 신호."""
    from . import page_guard
    rc = page_guard.main([
        "--reference", args.reference,
        "--output", args.output,
        "--threshold", str(args.threshold),
        "--mode", args.mode,
        *(["--json"] if args.json else []),
    ])
    sys.exit(rc)


def _cmd_analyze(args: argparse.Namespace) -> None:
    """analyze CLI 핸들러."""
    from . import blueprint
    rc = blueprint.main([
        args.file,
        *(["--blueprint"] if args.blueprint else []),
        "--depth", str(args.depth),
        *(["--json"] if args.json else []),
    ])
    sys.exit(rc)


def _cmd_doctor(args: argparse.Namespace) -> None:
    """Delegate to pyhwpxlib.doctor.main with the same argv."""
    from pyhwpxlib.doctor import main as doctor_main
    argv = [args.input]
    if getattr(args, "fix", False):
        argv.append("--fix")
    if getattr(args, "output", None):
        argv += ["-o", args.output]
    if getattr(args, "inplace", False):
        argv.append("--inplace")
    if getattr(args, "mode", None):
        argv += ["--mode", args.mode]
    if getattr(args, "json", False):
        argv.append("--json")
    sys.exit(doctor_main(argv))


def _cmd_validate(args: argparse.Namespace) -> None:
    """Validate HWPX. v0.14.0: --mode {strict|compat|both} (default both)."""
    hwpx_path = args.input
    as_json = getattr(args, "json", False)
    mode = getattr(args, "mode", "both")

    compat_result = _validate_compat(hwpx_path) if mode in ("compat", "both") else None
    strict_result = _validate_strict(hwpx_path) if mode in ("strict", "both") else None

    if mode == "both":
        # exit code follows compat (= file usable in Hancom);
        # strict failures are advisory.
        ok = bool(compat_result and compat_result["ok"])
        result = {
            "command": "validate",
            "ok": ok,
            "file": hwpx_path,
            "mode": "both",
            "compat": compat_result,
            "strict": strict_result,
            # Back-compat: surface compat checks at top level too so older
            # consumers and the human renderer keep working.
            "checks": compat_result["checks"] if compat_result else [],
        }
    elif mode == "compat":
        result = {"command": "validate", "ok": compat_result["ok"], "file": hwpx_path,
                  "mode": "compat", "checks": compat_result["checks"]}
        ok = compat_result["ok"]
    else:  # strict
        result = {"command": "validate", "ok": strict_result["ok"], "file": hwpx_path,
                  "mode": "strict", "checks": strict_result["checks"]}
        ok = strict_result["ok"]

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
    """Check font availability and resolution for an HWPX file.

    Status values:
      ok       — declared font resolves to its own family file (direct hit).
      alias    — declared font resolves, but to a different family
                 (e.g. 함초롬돋움 → bundled NanumGothic).
      fallback — declared font is not in any map; rhwp will pick the
                 platform Korean/Latin fallback at render time.
      missing  — declared font is mapped, but the target file is absent
                 from disk (broken install / removed bundle).
    """
    import zipfile
    import xml.etree.ElementTree as ET

    path = args.input
    as_json = getattr(args, 'json', False)
    user_map_path = getattr(args, 'font_map', None)

    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)

    # Load user override map if provided
    user_overrides: dict[str, str] = {}
    if user_map_path:
        if not os.path.exists(user_map_path):
            print(f"Font map not found: {user_map_path}")
            sys.exit(1)
        try:
            with open(user_map_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                raise ValueError("font-map JSON must be an object {name: path}")
            user_overrides = {str(k).lower(): str(v) for k, v in raw.items()}
        except (OSError, ValueError, json.JSONDecodeError) as e:
            print(f"Error reading font-map {user_map_path}: {e}")
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

    # Build effective map = bundled defaults + user overrides
    try:
        from .rhwp_bridge import (
            _DEFAULT_FONT_MAP,
            _BUNDLED_REGULAR,
            _BUNDLED_BOLD,
            _KOREAN_FALLBACK,
            _LATIN_FALLBACK,
            _TextMeasurer,
        )
    except ImportError:
        _DEFAULT_FONT_MAP, _BUNDLED_REGULAR, _BUNDLED_BOLD = {}, '', ''
        _KOREAN_FALLBACK = _LATIN_FALLBACK = ''
        _TextMeasurer = None  # type: ignore[assignment]

    font_map = dict(_DEFAULT_FONT_MAP)
    font_map.update(user_overrides)

    bundled_paths = {_BUNDLED_REGULAR, _BUNDLED_BOLD}
    fallback_paths = {_KOREAN_FALLBACK, _LATIN_FALLBACK}

    def _is_nanum_family(name_lower: str) -> bool:
        return any(token in name_lower for token in ('nanum', '나눔'))

    fonts_result = []
    for font in sorted(doc_fonts):
        lower = font.lower()
        direct_hit = lower in font_map
        in_overrides = lower in user_overrides

        # Prefer rhwp-aligned resolver if available — same logic rhwp uses
        # at render time, so the reported path is what actually resolves.
        if _TextMeasurer is not None:
            measurer = _TextMeasurer(font_map=user_overrides if user_overrides else None)
            resolved = measurer._resolve_path([lower])
        else:
            resolved = font_map.get(lower, '')

        # Mapped path that doesn't exist on disk
        if direct_hit and font_map[lower] and not os.path.exists(font_map[lower]):
            status = 'missing'
            resolved = font_map[lower]
        elif not resolved or not os.path.exists(resolved):
            status = 'missing'
        elif not direct_hit and resolved in fallback_paths:
            # No mapping — rhwp would pick a platform fallback
            status = 'fallback'
        elif resolved in bundled_paths and not _is_nanum_family(lower):
            # Mapped to bundled NanumGothic but declared is a different family
            status = 'alias'
        else:
            status = 'ok'

        fonts_result.append({
            'declared': font,
            'resolved': resolved,
            'status': status,
            'source': 'override' if in_overrides else ('map' if direct_hit else 'fallback'),
        })

    ok = not any(f['status'] == 'missing' for f in fonts_result)
    result = {
        'command': 'font-check',
        'ok': ok,
        'file': path,
        'font_map': user_map_path or None,
        'fonts': fonts_result,
    }
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
    p_val = sub.add_parser(
        "validate",
        help="Validate HWPX. --mode strict (OWPML spec) / compat (Hancom-OK) / both (default)",
    )
    p_val.add_argument("input", help="Input .hwpx file")
    p_val.add_argument(
        "--mode", choices=["strict", "compat", "both"], default="both",
        help="strict = OWPML spec (rhwp-aligned), compat = Hancom acceptance, both = report side-by-side (default)",
    )
    p_val.add_argument("--json", action="store_true", help="Output as JSON")

    # doctor (v0.14.0+)
    p_doc = sub.add_parser(
        "doctor",
        help="Diagnose non-standard HWPX structures; --fix to repair (rhwp-aligned, opt-in)",
    )
    p_doc.add_argument("input", help="Input .hwpx file")
    p_doc.add_argument("--fix", action="store_true",
                       help="apply precise textpos-overflow fix (writes new file)")
    p_doc.add_argument("-o", "--output",
                       help="output path when --fix (default: <input>.fixed.hwpx)")
    p_doc.add_argument("--inplace", action="store_true",
                       help="overwrite the input file instead of writing a new one (only with --fix)")
    p_doc.add_argument("--mode", choices=["precise", "remove"], default="precise",
                       help="precise: remove only overflow linesegs (default). remove: strip every <hp:linesegarray>.")
    p_doc.add_argument("--json", action="store_true", help="JSON output")

    # lint
    p_lint = sub.add_parser("lint", help="Check HWPX for rendering/compatibility risks")
    p_lint.add_argument("input", help="Input .hwpx file")
    p_lint.add_argument("--json", action="store_true", help="Output as JSON")

    # font-check
    p_fc = sub.add_parser("font-check", help="Check font availability and resolution")
    p_fc.add_argument("input", help="Input .hwpx file")
    p_fc.add_argument("--json", action="store_true", help="Output as JSON")
    p_fc.add_argument(
        "--font-map",
        dest="font_map",
        metavar="PATH",
        help="JSON file with {font_name: file_path} overrides "
             "(merged on top of the bundled font map; case-insensitive keys)",
    )

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
    tpl_add.add_argument("--fix", action="store_true",
                         help="Apply precise textpos-overflow fix (Hancom security trigger workaround). "
                              "Default off in v0.14.0+ — register form as-is.")
    tpl_add.add_argument("--json", action="store_true", help="JSON output")
    tpl_fill = tpl_sub.add_parser("fill", help="Fill a registered template with data")
    tpl_fill.add_argument("name", help="template name (or path to .hwpx)")
    tpl_fill.add_argument("-d", "--data", required=True, help="JSON data file or 'key=value,key=value'")
    tpl_fill.add_argument("-o", "--output", default=None,
                          help="output .hwpx path. v0.17.0+: omit for workspace-templates → auto outputs/YYYY-MM-DD_<key>.hwpx")
    tpl_fill.add_argument("--no-history", action="store_true",
                          help="skip history.json + usage_count update (workspace templates)")
    tpl_fill.add_argument("--fix", action="store_true",
                          help="Apply precise textpos-overflow fix on save (Hancom security trigger workaround). "
                               "Default off in v0.14.0+ — pyhwpxlib will warn but won't silently rewrite.")
    tpl_fill.add_argument("--json", action="store_true", help="JSON output")
    tpl_show = tpl_sub.add_parser("show", help="Show schema for a template")
    tpl_show.add_argument("name", help="template name")
    tpl_show.add_argument("--json", action="store_true", help="JSON output")
    tpl_list = tpl_sub.add_parser("list", help="List all registered templates")
    tpl_list.add_argument("--json", action="store_true", help="JSON output")
    tpl_diag = tpl_sub.add_parser(
        "diagnose",
        help="Diagnose auto_schema heuristics on a HWPX form (incl. optional overlap vs manual schema)",
    )
    tpl_diag.add_argument("hwpx", help="path to .hwpx form")
    tpl_diag.add_argument(
        "--schema",
        help="optional path to a manually authored schema.json for overlap comparison",
    )
    tpl_diag.add_argument("--json", action="store_true", help="JSON output")

    # v0.17.0+ workspace commands
    tpl_ctx = tpl_sub.add_parser(
        "context",
        help="(v0.17.0+) Print workspace context for LLM injection (markdown or --json)",
    )
    tpl_ctx.add_argument("name", help="template name")
    tpl_ctx.add_argument("--json", action="store_true", help="JSON output")

    tpl_annot = tpl_sub.add_parser(
        "annotate",
        help="(v0.17.0+) Update _meta + append decision to decisions.md",
    )
    tpl_annot.add_argument("name", help="template name")
    tpl_annot.add_argument("--description", help="set _meta.description")
    tpl_annot.add_argument("--page-standard", choices=["1page", "free"],
                           dest="page_standard",
                           help="set _meta.page_standard")
    tpl_annot.add_argument("--structure", choices=["A", "B", "unknown"],
                           dest="structure_type",
                           help="set _meta.structure_type")
    tpl_annot.add_argument("--notes", help="set _meta.notes")
    tpl_annot.add_argument(
        "--decision",
        dest="add_decision",
        help="append decision line to decisions.md (today's block)",
    )
    tpl_annot.add_argument("--json", action="store_true", help="JSON output")

    tpl_log = tpl_sub.add_parser(
        "log-fill",
        help="(v0.17.0+) Manually log a fill entry into history.json",
    )
    tpl_log.add_argument("name", help="template name")
    tpl_log.add_argument("-d", "--data", required=True,
                         help="JSON file or 'k=v,k=v'")
    tpl_log.add_argument("--output-path", help="optional output_path entry")
    tpl_log.add_argument("--json", action="store_true", help="JSON output")

    tpl_open = tpl_sub.add_parser(
        "open",
        help="(v0.17.0+) Open workspace folder in OS file manager",
    )
    tpl_open.add_argument("name", help="template name")
    tpl_open.add_argument("--json", action="store_true", help="JSON output")

    tpl_mig = tpl_sub.add_parser(
        "migrate",
        help="(v0.17.0+) Migrate v0.13.3 flat templates → v0.17.0 workspace folders",
    )
    tpl_mig.add_argument("--dry-run", action="store_true",
                         help="Preview migration plan without writing")
    tpl_mig.add_argument("--no-backup", action="store_true",
                         help="Skip the safety tar.gz backup (NOT recommended)")
    tpl_mig.add_argument("--overwrite", action="store_true",
                         help="Overwrite existing workspace folders if conflict")
    tpl_mig.add_argument("--root", help="custom templates root (default: XDG)")
    tpl_mig.add_argument("--json", action="store_true", help="JSON output")

    # themes
    # page-guard (v0.16.0+) — 레퍼런스/결과 페이지 카운트 강제 게이트
    p_pg = sub.add_parser(
        "page-guard",
        help="Reference vs output 페이지 카운트 비교 (강제 게이트)",
    )
    p_pg.add_argument("--reference", required=True, help="기준 HWPX 경로")
    p_pg.add_argument("--output", required=True, help="검증할 HWPX 경로")
    p_pg.add_argument("--threshold", type=int, default=0,
                      help="허용 페이지 차이 (default 0)")
    p_pg.add_argument("--mode", choices=["auto", "rhwp", "static"],
                      default="auto", help="페이지 카운트 측정 방법")
    p_pg.add_argument("--json", action="store_true", help="JSON 출력")

    # analyze (v0.16.0+) — HWPX 구조 청사진
    p_an = sub.add_parser(
        "analyze",
        help="HWPX 구조 청사진 (charPr/paraPr/borderFill/표/페이지)",
    )
    p_an.add_argument("file", help="분석할 HWPX 경로")
    p_an.add_argument("--blueprint", action="store_true",
                      help="청사진 모드 (현재 유일한 모드)")
    p_an.add_argument("--depth", type=int, choices=[1, 2, 3], default=2,
                      help="분석 깊이 (default 2)")
    p_an.add_argument("--json", action="store_true", help="JSON 출력")

    # v0.17.0+ — Claude Code SessionStart hook 설치
    p_hook = sub.add_parser(
        "install-hook",
        help="(v0.17.0+) Install Claude Code SessionStart hook for auto template context injection",
    )
    p_hook.add_argument(
        "--target",
        help="custom hook dir (default: ~/.claude/hooks)",
    )
    p_hook.add_argument("--json", action="store_true", help="JSON output")

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
        "doctor": _cmd_doctor,
        "page-guard": _cmd_page_guard,
        "analyze": _cmd_analyze,
        "install-hook": _cmd_install_hook,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
