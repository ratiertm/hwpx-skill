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
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


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


def _cmd_validate(args: argparse.Namespace) -> None:
    import zipfile
    import xml.etree.ElementTree as ET

    hwpx_path = args.input
    required = ["mimetype", "Contents/header.xml", "Contents/section0.xml", "Contents/content.hpf"]
    errors, info = [], {}

    if not zipfile.is_zipfile(hwpx_path):
        print(f"❌ INVALID: Not a valid ZIP file")
        sys.exit(1)

    with zipfile.ZipFile(hwpx_path, "r") as z:
        names = z.namelist()
        info["file_count"] = len(names)

        for req in required:
            if req not in names:
                errors.append(f"Missing: {req}")

        if "mimetype" in names:
            mt = z.read("mimetype").decode("utf-8").strip()
            info["mimetype"] = mt

        for xml_file in ["Contents/header.xml", "Contents/section0.xml"]:
            if xml_file in names:
                try:
                    content = z.read(xml_file).decode("utf-8")
                    ET.fromstring(content)
                    info[xml_file] = f"OK ({len(content):,} bytes)"
                except ET.ParseError as e:
                    errors.append(f"XML error in {xml_file}: {e}")

    valid = len(errors) == 0
    print(f"\n{'=' * 50}")
    print(f"HWPX Validation: {hwpx_path}")
    print(f"{'=' * 50}")
    print(f"Result: {'✅ VALID' if valid else '❌ INVALID'}")
    print(f"Files: {info.get('file_count', '?')}")
    print(f"Mimetype: {info.get('mimetype', 'N/A')}")
    for xf in ["Contents/header.xml", "Contents/section0.xml"]:
        if xf in info:
            print(f"{xf}: {info[xf]}")
    if errors:
        for e in errors:
            print(f"  ❌ {e}")
    elif valid:
        print("\n✅ All checks passed!")
    sys.exit(0 if valid else 1)


def _cmd_font_check(args: argparse.Namespace) -> None:
    """Check font availability for an HWPX file."""
    import zipfile
    import xml.etree.ElementTree as ET

    path = args.input
    if not os.path.exists(path):
        print(f"File not found: {path}")
        sys.exit(1)

    # Extract font names from header.xml
    doc_fonts: set[str] = set()
    try:
        with zipfile.ZipFile(path) as z:
            header_xml = z.read("Contents/header.xml").decode("utf-8")
        root = ET.fromstring(header_xml)
        ns = {"hh": "http://www.hancom.co.kr/hwpml/2011/head",
              "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
        for font_el in root.iter("{http://www.hancom.co.kr/hwpml/2011/head}font"):
            face = font_el.get("face")
            if face:
                doc_fonts.add(face)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        sys.exit(1)

    if not doc_fonts:
        print("No fonts found in document.")
        return

    # Check against font_map
    from .vendor import NANUM_GOTHIC_REGULAR
    bundled = {"나눔고딕", "NanumGothic"}
    try:
        from .rhwp_bridge import _DEFAULT_FONT_MAP
        known = set(k for k in _DEFAULT_FONT_MAP)
    except ImportError:
        known = set()

    print(f"📋 Fonts in document: {len(doc_fonts)}")
    ok_count = 0
    warn_count = 0
    for font in sorted(doc_fonts):
        lower = font.lower()
        if font in bundled or lower in known:
            print(f"  ✅ {font}")
            ok_count += 1
        else:
            print(f"  ⚠️  {font} — not in font_map (may render with fallback)")
            warn_count += 1

    print(f"\nBundled font: 나눔고딕 ({'exists' if NANUM_GOTHIC_REGULAR.exists() else 'MISSING'})")
    if warn_count:
        print(f"\n⚠️  {warn_count} font(s) may need manual installation or font_map entry.")
    else:
        print(f"\n✅ All {ok_count} font(s) available.")


def _cmd_themes(args: argparse.Namespace) -> None:
    """List saved custom themes or extract/save a theme."""
    from .themes import BUILTIN_THEMES, _THEMES_DIR, extract_theme, save_theme, load_theme

    if args.action == 'list':
        # Built-in themes
        print("Built-in themes:")
        for name in sorted(BUILTIN_THEMES):
            t = BUILTIN_THEMES[name]
            print(f"  {name:20s}  primary={t.palette.primary}")

        # Custom themes
        if _THEMES_DIR.exists():
            customs = sorted(_THEMES_DIR.glob('*.json'))
            if customs:
                print(f"\nCustom themes ({_THEMES_DIR}):")
                for p in customs:
                    try:
                        t = load_theme(p)
                        print(f"  {t.name:20s}  primary={t.palette.primary}  font={t.fonts.body_hangul}")
                    except Exception:
                        print(f"  {p.stem:20s}  (error loading)")
            else:
                print("\nNo custom themes saved yet.")
        else:
            print("\nNo custom themes saved yet.")

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
    p_val = sub.add_parser("validate", help="Validate HWPX file")
    p_val.add_argument("input", help="Input .hwpx file")

    # font-check
    p_fc = sub.add_parser("font-check", help="Check font availability for HWPX")
    p_fc.add_argument("input", help="Input .hwpx file")

    # themes
    p_th = sub.add_parser("themes", help="Manage themes (list/extract/delete)")
    p_th.add_argument("action", choices=["list", "extract", "delete"],
                       help="list: show all themes, extract: save theme from HWPX, delete: remove custom theme")
    p_th.add_argument("--input", "-i", help="Input .hwpx file (for extract)")
    p_th.add_argument("--name", "-n", help="Theme name (for extract/delete)")

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
