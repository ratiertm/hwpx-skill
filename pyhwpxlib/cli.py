"""pyhwpxlib CLI -- command-line tool for HWPX operations.

Usage::

    python -m pyhwpxlib md2hwpx  input.md  -o output.hwpx
    python -m pyhwpxlib hwpx2html input.hwpx -o output.html
    python -m pyhwpxlib text     input.hwpx
    python -m pyhwpxlib fill     template.hwpx -o out.hwpx -d name=Hong age=30
    python -m pyhwpxlib info     input.hwpx
    python -m pyhwpxlib merge    a.hwpx b.hwpx -o merged.hwpx
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
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
