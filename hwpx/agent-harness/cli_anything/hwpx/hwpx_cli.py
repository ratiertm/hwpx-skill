#!/usr/bin/env python3
"""HWPX CLI -- A stateful command-line interface for Hancom Office HWPX documents.

Read, edit, create, and validate HWPX files without Hancom Office installation.

Usage:
    # One-shot commands
    cli-anything-hwpx document new --output my_doc.hwpx
    cli-anything-hwpx document open report.hwpx
    cli-anything-hwpx text extract report.hwpx
    cli-anything-hwpx text replace --old "draft" --new "final"
    cli-anything-hwpx export markdown --output report.md

    # Interactive REPL
    cli-anything-hwpx repl
"""

import sys
import os
import re
import json
import click
from typing import Optional

from cli_anything.hwpx.core.session import Session

_HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
from cli_anything.hwpx.core import document as doc_mod
from cli_anything.hwpx.core import text as text_mod
from cli_anything.hwpx.core import table as table_mod
from cli_anything.hwpx.core import image as image_mod
from cli_anything.hwpx.core import export as export_mod
from cli_anything.hwpx.core import validate as validate_mod
from cli_anything.hwpx.core import structure as struct_mod

# Global state
_session: Optional[Session] = None
_json_output = False
_repl_mode = False
_auto_save_path: Optional[str] = None


def get_session() -> Session:
    global _session
    if _session is None:
        _session = Session()
    return _session


def _auto_save_if_needed():
    """One-shot 모드(--file)에서 mutation 후 자동 저장."""
    if _auto_save_path and not _repl_mode:
        sess = get_session()
        sess.save(_auto_save_path)


def output(data, message: str = ""):
    if _json_output:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        if message:
            click.echo(message)
        if isinstance(data, dict):
            _print_dict(data)
        elif isinstance(data, list):
            _print_list(data)
        else:
            click.echo(str(data))


def _print_dict(d: dict, indent: int = 0):
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            click.echo(f"{prefix}{k}:")
            _print_dict(v, indent + 1)
        elif isinstance(v, list):
            click.echo(f"{prefix}{k}:")
            _print_list(v, indent + 1)
        else:
            click.echo(f"{prefix}{k}: {v}")


def _print_list(items: list, indent: int = 0):
    prefix = "  " * indent
    for i, item in enumerate(items):
        if isinstance(item, dict):
            click.echo(f"{prefix}[{i}]")
            _print_dict(item, indent + 1)
        else:
            click.echo(f"{prefix}- {item}")


def handle_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (FileNotFoundError, ValueError, IndexError, RuntimeError, OSError) as e:
            if _json_output:
                click.echo(json.dumps({"error": str(e), "type": type(e).__name__}))
            else:
                click.echo(f"Error: {e}", err=True)
            if not _repl_mode:
                sys.exit(1)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# ── Main CLI Group ─────────────────────────────────────────────────────

@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output as JSON")
@click.option("--file", "file_path", type=str, default=None,
              help="Path to .hwpx file to open")
@click.pass_context
def cli(ctx, use_json, file_path):
    """HWPX CLI -- Read, edit, and create Hancom Office HWPX documents.

    Run without a subcommand to enter interactive REPL mode.
    """
    global _json_output, _auto_save_path
    _json_output = use_json

    # SPEC: e2e-hwpx-skill-v1-005 -- Text Add Errors (file validation)
    if file_path:
        sess = get_session()
        if not sess.has_project():
            try:
                doc = doc_mod.open_document(file_path)
            except (FileNotFoundError, ValueError) as e:
                click.echo(f"Error: {e}", err=True)
                ctx.abort()
            sess.set_doc(doc, file_path)
        _auto_save_path = file_path

    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# ── Document Commands ──────────────────────────────────────────────────
# SPEC: e2e-hwpx-skill-v1-001 -- CLI New Document Screen

@cli.group()
def document():
    """Document management — create, open, save, info."""
    pass


@document.command("new")
@click.option("--output", "-o", type=str, default=None, help="Save path")
@handle_error
def document_new(output):
    """Create a new blank HWPX document."""
    doc = doc_mod.new_document()
    sess = get_session()
    sess.set_doc(doc, output)
    if output:
        doc_mod.save_document(doc, output)
    info = doc_mod.get_document_info(doc)
    globals()["output"](info, f"Created new document" + (f": {output}" if output else ""))


@document.command("open")
@click.argument("path")
@handle_error
def document_open(path):
    """Open an existing HWPX file."""
    doc = doc_mod.open_document(path)
    sess = get_session()
    sess.set_doc(doc, path)
    info = doc_mod.get_document_info(doc)
    globals()["output"](info, f"Opened: {path}")


@document.command("save")
@click.argument("path", required=False)
@handle_error
def document_save(path):
    """Save the current document."""
    sess = get_session()
    saved = sess.save(path)
    globals()["output"]({"saved": saved}, f"Saved to: {saved}")


@document.command("info")
@handle_error
def document_info():
    """Show document structure information."""
    sess = get_session()
    info = doc_mod.get_document_info(sess.get_doc())
    session_info = sess.info()
    info.update(session_info)
    globals()["output"](info)


# ── Text Commands ──────────────────────────────────────────────────────

@cli.group()
def text():
    """Text operations — extract, find, replace, add."""
    pass


# SPEC: e2e-hwpx-skill-v1-006 -- Text Extract Screen
# SPEC: e2e-hwpx-skill-v1-007 -- Text Extract Connection
# SPEC: e2e-hwpx-skill-v1-008 -- Text Extract Processing
# SPEC: e2e-hwpx-skill-v1-009 -- Text Extract Response
@text.command("extract")
@click.argument("path", required=False)
@click.option("--format", "-f", "fmt", type=click.Choice(["text", "markdown", "html"]),
              default="text", help="Output format")
@handle_error
def text_extract(path, fmt):
    """Extract text content from the document."""
    sess = get_session()
    if path and not sess.has_project():
        doc = doc_mod.open_document(path)
        sess.set_doc(doc, path)

    doc = sess.get_doc()
    if fmt == "text":
        content = text_mod.extract_text(doc)
    elif fmt == "markdown":
        content = text_mod.extract_markdown(doc)
    else:
        content = text_mod.extract_html(doc)

    if _json_output:
        click.echo(json.dumps({"content": content, "format": fmt}))
    else:
        click.echo(content)


@text.command("find")
@click.argument("query")
@handle_error
def text_find(query):
    """Find text occurrences in the document."""
    sess = get_session()
    results = text_mod.find_text(sess.get_doc(), query)
    globals()["output"](results, f"Found {len(results)} match(es) for '{query}'")


@text.command("replace")
@click.option("--old", required=True, help="Text to find")
@click.option("--new", "new_text", required=True, help="Replacement text")
@handle_error
def text_replace(old, new_text):
    """Replace text throughout the document."""
    sess = get_session()
    sess.snapshot()
    count = text_mod.replace_text(sess.get_doc(), old, new_text)
    _auto_save_if_needed()
    globals()["output"]({"old": old, "new": new_text, "replaced": count},
                        f"Replaced {count} occurrence(s)")


# SPEC: e2e-hwpx-skill-v1-002 -- CLI Text Add Connection
# SPEC: e2e-hwpx-skill-v1-003 -- Text Add Processing (auto-save)
# SPEC: e2e-hwpx-skill-v1-004 -- Text Add Response
@text.command("add")
@click.argument("content")
@handle_error
def text_add(content):
    """Add a paragraph to the document."""
    sess = get_session()
    sess.snapshot()
    result = text_mod.add_paragraph(sess.get_doc(), content)
    _auto_save_if_needed()
    globals()["output"](result, f"Added paragraph: {content[:50]}...")


# ── Table Commands ─────────────────────────────────────────────────────

@cli.group()
def table():
    """Table operations — add, list."""
    pass


@table.command("add")
@click.option("--rows", "-r", type=int, required=True, help="Number of rows")
@click.option("--cols", "-c", type=int, required=True, help="Number of columns")
@click.option("--header", "-h", type=str, default=None,
              help="Comma-separated header row (e.g. '이름,역할,설명')")
@click.option("--data", "-d", type=str, multiple=True,
              help="Comma-separated data row (repeatable, e.g. -d 'A,B,C' -d 'D,E,F')")
@handle_error
def table_add(rows, cols, header, data):
    """Add a table to the document. Optionally fill with header and data."""
    sess = get_session()
    sess.snapshot()
    result = table_mod.add_table(sess.get_doc(), rows, cols, header=header, data=data)
    _auto_save_if_needed()
    globals()["output"](result, f"Added {rows}x{cols} table")


@table.command("list")
@handle_error
def table_list():
    """List all tables in the document."""
    sess = get_session()
    tables = table_mod.list_tables(sess.get_doc())
    globals()["output"](tables, f"Found {len(tables)} table(s)")


# ── Image Commands ─────────────────────────────────────────────────────

@cli.group()
def image():
    """Image operations — add, list, remove."""
    pass


@image.command("add")
@click.argument("path")
@click.option("--width", "-w", type=float, default=None, help="Width in mm")
@click.option("--height", "-h", type=float, default=None, help="Height in mm")
@handle_error
def image_add(path, width, height):
    """Add an image to the document."""
    sess = get_session()
    sess.snapshot()
    result = image_mod.add_image(sess.get_doc(), path, width, height)
    _auto_save_if_needed()
    globals()["output"](result, f"Added image: {path}")


@image.command("list")
@handle_error
def image_list():
    """List all images in the document."""
    sess = get_session()
    images = image_mod.list_images(sess.get_doc())
    globals()["output"](images, f"Found {len(images)} image(s)")


@image.command("remove")
@click.argument("index", type=int)
@handle_error
def image_remove(index):
    """Remove an image by index."""
    sess = get_session()
    sess.snapshot()
    result = image_mod.remove_image(sess.get_doc(), index)
    _auto_save_if_needed()
    globals()["output"](result, f"Removed image {index}")


# ── Export Commands ────────────────────────────────────────────────────

@cli.group("export")
def export_group():
    """Export document to various formats."""
    pass


@export_group.command("text")
@click.option("--output", "-o", required=True, help="Output file path")
@handle_error
def export_text(output):
    """Export as plain text."""
    sess = get_session()
    result = export_mod.export_to_file(sess.get_doc(), output, "text")
    globals()["output"](result, f"Exported text to: {output}")


@export_group.command("markdown")
@click.option("--output", "-o", required=True, help="Output file path")
@handle_error
def export_markdown(output):
    """Export as Markdown."""
    sess = get_session()
    result = export_mod.export_to_file(sess.get_doc(), output, "markdown")
    globals()["output"](result, f"Exported Markdown to: {output}")


@export_group.command("html")
@click.option("--output", "-o", required=True, help="Output file path")
@handle_error
def export_html(output):
    """Export as HTML."""
    sess = get_session()
    result = export_mod.export_to_file(sess.get_doc(), output, "html")
    globals()["output"](result, f"Exported HTML to: {output}")


# ── Validate Commands ──────────────────────────────────────────────────

@cli.group("validate")
def validate_group():
    """Validate HWPX document and package structure."""
    pass


@validate_group.command("schema")
@click.argument("path", required=False)
@handle_error
def validate_schema(path):
    """Validate document against XSD schema."""
    sess = get_session()
    target = path or sess.get_doc()
    result = validate_mod.validate_document(target)
    status = "VALID" if result["is_valid"] else "INVALID"
    globals()["output"](result, f"Schema validation: {status}")


@validate_group.command("package")
@click.argument("path")
@handle_error
def validate_package(path):
    """Validate ZIP/OPC package structure."""
    result = validate_mod.validate_package(path)
    status = "VALID" if result["is_valid"] else "INVALID"
    globals()["output"](result, f"Package validation: {status}")


# ── Structure Commands ─────────────────────────────────────────────────

@cli.group("structure")
def structure_group():
    """Document structure — sections, headers, footers, bookmarks."""
    pass


@structure_group.command("sections")
@handle_error
def structure_sections():
    """List all sections."""
    sess = get_session()
    sections = struct_mod.list_sections(sess.get_doc())
    globals()["output"](sections, f"Found {len(sections)} section(s)")


@structure_group.command("add-section")
@handle_error
def structure_add_section():
    """Add a new section."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.add_section(sess.get_doc())
    _auto_save_if_needed()
    globals()["output"](result, "Added new section")


@structure_group.command("set-header")
@click.argument("text")
@handle_error
def structure_set_header(text):
    """Set header text."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.set_header(sess.get_doc(), text)
    _auto_save_if_needed()
    globals()["output"](result, f"Header set: {text}")


@structure_group.command("set-footer")
@click.argument("text")
@handle_error
def structure_set_footer(text):
    """Set footer text."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.set_footer(sess.get_doc(), text)
    _auto_save_if_needed()
    globals()["output"](result, f"Footer set: {text}")


@structure_group.command("bookmark")
@click.argument("name")
@handle_error
def structure_bookmark(name):
    """Add a bookmark."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.add_bookmark(sess.get_doc(), name)
    _auto_save_if_needed()
    globals()["output"](result, f"Bookmark added: {name}")


@structure_group.command("hyperlink")
@click.argument("url")
@click.option("--text", "-t", default=None, help="Display text")
@handle_error
def structure_hyperlink(url, text):
    """Add a hyperlink."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.add_hyperlink(sess.get_doc(), url, text)
    _auto_save_if_needed()
    globals()["output"](result, f"Hyperlink added: {url}")


@structure_group.command("page-number")
@click.option("--pos", default="BOTTOM_CENTER", help="Position (BOTTOM_CENTER, TOP_LEFT, etc.)")
@click.option("--format", "fmt", default="DIGIT", help="Format (DIGIT, ROMAN_CAPITAL, etc.)")
@handle_error
def structure_page_number(pos, fmt):
    """Add page number."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.add_page_number(sess.get_doc(), pos=pos, format_type=fmt)
    _auto_save_if_needed()
    globals()["output"](result, f"Page number added: {pos}")


@structure_group.command("footnote")
@click.argument("text")
@click.option("--anchor", "-a", default="", help="Anchor text in main body")
@handle_error
def structure_footnote(text, anchor):
    """Add a footnote."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.add_footnote(sess.get_doc(), text, anchor=anchor)
    _auto_save_if_needed()
    globals()["output"](result, f"Footnote added")


@structure_group.command("endnote")
@click.argument("text")
@click.option("--anchor", "-a", default="", help="Anchor text in main body")
@handle_error
def structure_endnote(text, anchor):
    """Add an endnote."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.add_endnote(sess.get_doc(), text, anchor=anchor)
    _auto_save_if_needed()
    globals()["output"](result, f"Endnote added")


@structure_group.command("equation")
@click.argument("script")
@handle_error
def structure_equation(script):
    """Add an equation (Hancom equation syntax)."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.add_equation(sess.get_doc(), script)
    _auto_save_if_needed()
    globals()["output"](result, f"Equation added")


@structure_group.command("rectangle")
@click.option("--width", "-w", type=int, default=14400, help="Width in hwpunit")
@click.option("--height", "-h", type=int, default=7200, help="Height in hwpunit")
@click.option("--color", default="#000000", help="Line color (#RRGGBB)")
@click.option("--line-width", default="283", help="Line thickness (283=1mm, 566=2mm, 850=3mm)")
@click.option("--fill", default=None, help="Fill color (#RRGGBB)")
@handle_error
def structure_rectangle(width, height, color, line_width, fill):
    """Add a rectangle shape."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.add_rectangle(sess.get_doc(), width, height,
                                      line_color=color, line_width=line_width, fill_color=fill)
    _auto_save_if_needed()
    globals()["output"](result, "Rectangle added")


@structure_group.command("ellipse")
@click.option("--width", "-w", type=int, default=14400, help="Width in hwpunit")
@click.option("--height", "-h", type=int, default=7200, help="Height in hwpunit")
@click.option("--color", default="#000000", help="Line color (#RRGGBB)")
@click.option("--line-width", default="283", help="Line thickness (283=1mm, 566=2mm, 850=3mm)")
@click.option("--fill", default=None, help="Fill color (#RRGGBB)")
@handle_error
def structure_ellipse(width, height, color, line_width, fill):
    """Add an ellipse shape."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.add_ellipse(sess.get_doc(), width, height,
                                    line_color=color, line_width=line_width, fill_color=fill)
    _auto_save_if_needed()
    globals()["output"](result, "Ellipse added")


@structure_group.command("line")
@click.option("--length", "-l", type=int, default=20000, help="Line length in hwpunit")
@click.option("--color", default="#000000", help="Line color (#RRGGBB)")
@click.option("--line-width", default="283", help="Line thickness (283=1mm, 566=2mm, 850=3mm)")
@handle_error
def structure_line(length, color, line_width):
    """Add a horizontal line."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.add_line(sess.get_doc(), length=length, line_color=color, line_width=line_width)
    _auto_save_if_needed()
    globals()["output"](result, "Line added")


@structure_group.command("bullet-list")
@click.argument("items")
@click.option("--char", default="●", help="Bullet character (●, ○, ■, ◆)")
@handle_error
def structure_bullet_list(items, char):
    """Add a bullet list. Items separated by commas."""
    sess = get_session()
    sess.snapshot()
    item_list = [i.strip() for i in items.split(",")]
    result = struct_mod.add_bullet_list(sess.get_doc(), item_list, bullet_char=char)
    _auto_save_if_needed()
    globals()["output"](result, f"Bullet list added ({len(item_list)} items)")


@structure_group.command("numbered-list")
@click.argument("items")
@click.option("--format", "fmt", default="^1.", help="Number format (^1. or ^1))")
@handle_error
def structure_numbered_list(items, fmt):
    """Add a numbered list. Items separated by commas."""
    sess = get_session()
    sess.snapshot()
    item_list = [i.strip() for i in items.split(",")]
    result = struct_mod.add_numbered_list(sess.get_doc(), item_list, format_string=fmt)
    _auto_save_if_needed()
    globals()["output"](result, f"Numbered list added ({len(item_list)} items)")


@structure_group.command("code-block")
@click.argument("code")
@click.option("--lang", default=None, help="Language label (e.g. python, javascript)")
@click.option("--font", default="D2Coding", help="Monospace font name")
@handle_error
def structure_code_block(code, lang, font):
    """Add a code block with monospace font and background."""
    sess = get_session()
    sess.snapshot()
    # Replace \\n with actual newlines for multi-line code
    code_text = code.replace("\\n", "\n")
    result = struct_mod.add_code_block(sess.get_doc(), code_text, language=lang, font=font)
    _auto_save_if_needed()
    globals()["output"](result, f"Code block added ({result['lines']} lines)")


@structure_group.command("nested-bullet-list")
@click.argument("items")
@handle_error
def structure_nested_bullet_list(items):
    """Add a nested bullet list. Format: 'level:text,level:text,...'
    Example: '0:Item 1,1:Sub A,1:Sub B,0:Item 2'"""
    sess = get_session()
    sess.snapshot()
    parsed = []
    for item in items.split(","):
        parts = item.strip().split(":", 1)
        if len(parts) == 2:
            parsed.append((int(parts[0]), parts[1].strip()))
        else:
            parsed.append((0, parts[0].strip()))
    result = struct_mod.add_nested_bullet_list(sess.get_doc(), parsed)
    _auto_save_if_needed()
    globals()["output"](result, f"Nested bullet list added ({result['items']} items)")


@structure_group.command("nested-numbered-list")
@click.argument("items")
@handle_error
def structure_nested_numbered_list(items):
    """Add a nested numbered list. Format: 'level:text,level:text,...'
    Example: '0:First,1:Sub A,0:Second'"""
    sess = get_session()
    sess.snapshot()
    parsed = []
    for item in items.split(","):
        parts = item.strip().split(":", 1)
        if len(parts) == 2:
            parsed.append((int(parts[0]), parts[1].strip()))
        else:
            parsed.append((0, parts[0].strip()))
    result = struct_mod.add_nested_numbered_list(sess.get_doc(), parsed)
    _auto_save_if_needed()
    globals()["output"](result, f"Nested numbered list added ({result['items']} items)")


@structure_group.command("set-columns")
@click.option("--count", "-n", type=int, default=2, help="Number of columns")
@click.option("--gap", "-g", type=int, default=1200, help="Gap between columns (hwpunit)")
@click.option("--separator", default=None, help="Separator line type (SOLID, DASH, etc.)")
@handle_error
def structure_set_columns(count, gap, separator):
    """Set column layout (e.g. 2-column)."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.set_columns(sess.get_doc(), count, gap=gap, separator=separator)
    _auto_save_if_needed()
    globals()["output"](result, f"Set {count}-column layout")


@table.command("set-gradient")
@click.option("--table", "tbl_idx", type=int, default=0, help="Table index (0-based)")
@click.option("--row", "-r", type=int, required=True, help="Row index")
@click.option("--col", "-c", type=int, required=True, help="Column index")
@click.option("--start", required=True, help="Start color (#RRGGBB)")
@click.option("--end", required=True, help="End color (#RRGGBB)")
@click.option("--type", "grad_type", default="LINEAR", help="Gradient type (LINEAR, RADIAL, CONICAL, SQUARE)")
@click.option("--angle", type=int, default=0, help="Angle in degrees (for LINEAR)")
@handle_error
def table_set_gradient(tbl_idx, row, col, start, end, grad_type, angle):
    """Set gradient fill on a table cell."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.set_cell_gradient(
        sess.get_doc(), tbl_idx, row, col,
        start_color=start, end_color=end,
        gradient_type=grad_type, angle=angle,
    )
    _auto_save_if_needed()
    globals()["output"](result, f"Cell ({row},{col}) gradient set {start} → {end}")


# ── Style Commands ────────────────────────────────────────────────────

@cli.group("style")
def style_group():
    """Text styling — bold, italic, color, size."""
    pass


@style_group.command("add")
@click.argument("content")
@click.option("--bold", "-b", is_flag=True, help="Bold text")
@click.option("--italic", "-i", is_flag=True, help="Italic text")
@click.option("--underline", "-u", is_flag=True, help="Underline text")
@click.option("--font-size", "-s", type=int, default=None, help="Font size in pt")
@click.option("--color", "-c", default=None, help="Text color (#RRGGBB)")
@handle_error
def style_add(content, bold, italic, underline, font_size, color):
    """Add styled text to the document."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.add_styled_text(
        sess.get_doc(), content,
        bold=bold, italic=italic, underline=underline,
        font_size=font_size, text_color=color,
    )
    _auto_save_if_needed()
    globals()["output"](result, f"Styled text added: {content[:50]}...")


# ── Table Background ──────────────────────────────────────────────────

@table.command("set-bgcolor")
@click.option("--table", "tbl_idx", type=int, default=0, help="Table index (0-based)")
@click.option("--row", "-r", type=int, required=True, help="Row index")
@click.option("--col", "-c", type=int, required=True, help="Column index")
@click.option("--color", required=True, help="Background color (#RRGGBB)")
@handle_error
def table_set_bgcolor(tbl_idx, row, col, color):
    """Set table cell background color."""
    sess = get_session()
    sess.snapshot()
    result = struct_mod.set_cell_background(sess.get_doc(), tbl_idx, row, col, color)
    _auto_save_if_needed()
    globals()["output"](result, f"Cell ({row},{col}) background set to {color}")


# ── MD→HWPX Style Presets ─────────────────────────────────────────────

MD_STYLES: dict[str, dict] = {
    "github": {
        "name": "GitHub",
        "description": "GitHub Flavored Markdown (github-markdown-css)",
        "body_height": 1000, "body_color": "#1F2328", "body_font": None,
        "line_spacing": 150,
        "h1_height": 2000, "h2_height": 1500, "h3_height": 1300,
        "h4_height": 1000, "h5_height": 900, "h6_height": 850,
        "h1_h2_border": True, "heading_border_color": "#D1D9E0",
        "heading_color": None, "heading_spacing": True,
        "code_height": 850, "code_bg": "#F6F8FA", "code_text": "#1F2328",
        "code_border": "#D1D9E0", "code_font": "D2Coding",
        "inline_code_text": "#1F2328",
        "link_color": "#0969DA",
        "quote_color": "#59636E", "quote_border_width": "283",
        "quote_border_color": "#D1D9E0",
        "hr_color": "#D1D9E0", "hr_width": "283",
        "table_header_bg": "#F0F0F0", "table_border_color": "#D1D9E0",
        "table_cell_padding": (450, 975),
        "bullet_chars": ["•", "◦", "▪", "‣", "⁃"],
    },
    "vscode": {
        "name": "VS Code",
        "description": "VS Code Markdown Preview (markdown.css)",
        "body_height": 1000, "body_color": "#333333", "body_font": None,
        "line_spacing": 157,
        "h1_height": 2000, "h2_height": 1500, "h3_height": 1300,
        "h4_height": 1000, "h5_height": 900, "h6_height": 850,
        "h1_h2_border": True, "heading_border_color": "#C8C8C8",
        "heading_color": None, "heading_spacing": True,
        "code_height": 1000, "code_bg": "#F0F0F0", "code_text": "#333333",
        "code_border": "#C8C8C8", "code_font": "D2Coding",
        "inline_code_text": "#333333",
        "link_color": "#4080D0",
        "quote_color": "#6A737D", "quote_border_width": "375",
        "quote_border_color": "#C8C8C8",
        "hr_color": "#C8C8C8", "hr_width": "71",
        "table_header_bg": "#E8E8E8", "table_border_color": "#C8C8C8",
        "table_cell_padding": (375, 750),
        "bullet_chars": ["•", "◦", "▪", "‣", "⁃"],
    },
    "minimal": {
        "name": "Minimal",
        "description": "Clean, no decorations, tight spacing",
        "body_height": 1000, "body_color": "#333333", "body_font": None,
        "line_spacing": 160,
        "h1_height": 1600, "h2_height": 1300, "h3_height": 1100,
        "h4_height": 1000, "h5_height": 900, "h6_height": 850,
        "h1_h2_border": False, "heading_border_color": "#CCCCCC",
        "heading_color": None, "heading_spacing": True,
        "code_height": 900, "code_bg": "#F5F5F5", "code_text": "#333333",
        "code_border": "#DDDDDD", "code_font": "D2Coding",
        "inline_code_text": "#C7254E",
        "link_color": "#0563C1",
        "quote_color": "#555555", "quote_border_width": "71",
        "quote_border_color": "#CCCCCC",
        "hr_color": "#CCCCCC", "hr_width": "71",
        "table_header_bg": "#D0D0D0", "table_border_color": "#CCCCCC",
        "table_cell_padding": (450, 975),
        "bullet_chars": ["•", "◦", "▪", "‣", "⁃"],
    },
    "academic": {
        "name": "Academic",
        "description": "Formal document style, larger headings, serif feel",
        "body_height": 1100, "body_color": "#000000", "body_font": None,
        "line_spacing": 180,
        "h1_height": 2200, "h2_height": 1800, "h3_height": 1400,
        "h4_height": 1100, "h5_height": 1000, "h6_height": 900,
        "h1_h2_border": True, "heading_border_color": "#000000",
        "heading_color": None, "heading_spacing": True,
        "code_height": 950, "code_bg": "#F8F8F8", "code_text": "#000000",
        "code_border": "#CCCCCC", "code_font": "D2Coding",
        "inline_code_text": "#000000",
        "link_color": "#000080",
        "quote_color": "#444444", "quote_border_width": "142",
        "quote_border_color": "#000000",
        "hr_color": "#000000", "hr_width": "142",
        "table_header_bg": "#D8D8D8", "table_border_color": "#000000",
        "table_cell_padding": (450, 975),
        "bullet_chars": ["•", "–", "·", "‣", "⁃"],
    },
}

DEFAULT_STYLE = "github"


def _convert_markdown_to_hwpx(doc, content: str, style_name: str = DEFAULT_STYLE) -> int:
    """Parse Markdown and build HWPX with selectable CSS-based styling.

    Style Reference (github-markdown-css):
        Body:  16px → 10pt (1000 hwpunit), line-height 1.5 → 160%
        H1:    2em (32px) → 20pt (2000), bold, border-bottom
        H2:    1.5em (24px) → 15pt (1500), bold, border-bottom
        H3:    1.25em (20px) → 13pt (1300), bold
        H4:    1em (16px) → 10pt (1000), bold
        Code:  85% (12px) → 8.5pt (850), bg #F6F8FA
        Quote: border-left .25em, color #59636E
        Link:  color #0969DA, underline on hover
        Table: header bold, border #D1D9E0, cell padding 6px 13px
        HR:    .25em height → 1mm line
        Bullet: disc → circle → square → (• ◦ ▪)
        Spacing: heading margin-top 24px → empty paragraph before H1/H2/H3
    """
    s = MD_STYLES.get(style_name, MD_STYLES[DEFAULT_STYLE])
    lines = content.split("\n")
    element_count = 0
    i = 0

    while i < len(lines):
        line = lines[i]

        # ── Code block (```) ──
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip() or None
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1
            doc.add_code_block(
                "\n".join(code_lines), language=lang,
                font=s.get("code_font", "D2Coding"),
                font_size=s["code_height"], bg_color=s["code_bg"],
                text_color=s["code_text"], border_color=s["code_border"],
            )
            element_count += len(code_lines) + (1 if lang else 0)
            doc.add_paragraph("")
            continue

        # ── Table (|) ──
        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            rows = []
            for tl in table_lines:
                cells = [c.strip() for c in tl.strip().strip("|").split("|")]
                if all(set(c) <= {"-", ":", " "} for c in cells):
                    continue
                rows.append(cells)
            if rows:
                max_cols = max(len(r) for r in rows)
                # Content-based column widths (MD preview style)
                page_width = 42520
                col_max_len = [0] * max_cols
                for row_data in rows:
                    for c_idx, cell_val in enumerate(row_data[:max_cols]):
                        text_len = len(_strip_inline_md(cell_val))
                        # CJK characters count as 2
                        cjk_count = sum(1 for ch in cell_val if ord(ch) > 0x2E80)
                        effective_len = text_len + cjk_count
                        col_max_len[c_idx] = max(col_max_len[c_idx], effective_len, 1)
                total_len = sum(col_max_len)
                col_widths = [int(page_width * cl / total_len) for cl in col_max_len]
                # Adjust rounding error
                diff = page_width - sum(col_widths)
                if diff != 0 and col_widths:
                    col_widths[-1] += diff

                tbl = doc.add_table(len(rows), max_cols, width=page_width)
                # Set individual column widths
                for c_idx, cw in enumerate(col_widths):
                    try:
                        for r_idx in range(len(rows)):
                            cell = tbl.cell(r_idx, c_idx)
                            cell_sz = cell.element.find(f"{{{_HP_NS}}}cellSz")
                            if cell_sz is not None:
                                cell_sz.set("width", str(cw))
                    except Exception:
                        pass

                # Cell padding from style (CSS padding: top/bottom left/right)
                pad = s.get("table_cell_padding", (450, 975))  # (v, h) in hwpunit
                pad_v, pad_h = pad[0], pad[1]

                for r_idx, row_data in enumerate(rows):
                    for c_idx, cell_val in enumerate(row_data[:max_cols]):
                        tbl.set_cell_text(r_idx, c_idx, _strip_inline_md(cell_val))
                        try:
                            # Header row: center, data rows: left
                            h_align = "CENTER" if r_idx == 0 else "LEFT"
                            tbl.set_cell_align(r_idx, c_idx,
                                               horizontal=h_align, vertical="CENTER")
                        except Exception:
                            pass
                        try:
                            tbl.cell(r_idx, c_idx).set_margin(
                                left=pad_h, right=pad_h,
                                top=pad_v, bottom=pad_v)
                        except Exception:
                            pass
                if len(rows) > 1:
                    for c_idx in range(max_cols):
                        try:
                            tbl.set_cell_background(0, c_idx, s["table_header_bg"])
                        except Exception:
                            pass
                element_count += 1
                doc.add_paragraph("")
            continue

        # ── Horizontal rule ──
        stripped = line.strip()
        if stripped and all(c in "-*_ " for c in stripped) and len(stripped.replace(" ", "")) >= 3:
            clean = stripped.replace(" ", "")
            if len(set(clean)) == 1 and clean[0] in "-*_":
                doc.add_line(42520, 0, 42520, 0,
                             line_color=s["hr_color"], line_width=s["hr_width"])
                element_count += 1
                i += 1
                continue

        # ── Empty line ──
        if not stripped:
            i += 1
            continue

        # ── Heading (#) ──
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = _strip_inline_md(heading_match.group(2))
            if element_count > 0 and s.get("heading_spacing", True):
                doc.add_paragraph("")
            heading_sizes = {
                1: s["h1_height"], 2: s["h2_height"], 3: s["h3_height"],
                4: s["h4_height"], 5: s["h5_height"], 6: s["h6_height"],
            }
            h_size = heading_sizes.get(level, s["body_height"])
            h_color = s.get("heading_color") or s.get("body_color")
            h_kw = {}
            if h_color:
                h_kw["text_color"] = h_color
            char_id = doc.ensure_run_style(bold=True, height=h_size, **h_kw)
            doc.add_paragraph(heading_text, char_pr_id_ref=char_id)
            if s["h1_h2_border"] and level <= 2:
                doc.add_line(42520, 0, 42520, 0,
                             line_color=s["heading_border_color"], line_width="71")
            element_count += 1
            i += 1
            continue

        # ── Blockquote (>) ──
        if stripped.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                qt = re.sub(r"^>\s?", "", lines[i].strip())
                quote_lines.append(qt)
                i += 1
            quote_text = " ".join(quote_lines)
            char_id = doc.ensure_run_style(
                italic=True, text_color=s["quote_color"], height=s["body_height"])
            doc.add_paragraph(f"  {quote_text}", char_pr_id_ref=char_id)
            element_count += 1
            doc.add_paragraph("")
            continue

        # ── Bullet list (-/*/+) ──
        list_match = re.match(r"^(\s*)([-*+])\s+(.+)$", stripped)
        if list_match:
            bullet_items = []
            while i < len(lines):
                bm = re.match(r"^(\s*)([-*+])\s+(.+)$", lines[i])
                if not bm:
                    break
                indent_level = len(bm.group(1)) // 2
                bullet_items.append((indent_level, _strip_inline_md(bm.group(3))))
                i += 1
            chars = s["bullet_chars"]
            if any(level > 0 for level, _ in bullet_items):
                doc.add_nested_bullet_list(bullet_items, bullet_chars=chars)
            else:
                doc.add_bullet_list(
                    [text for _, text in bullet_items], bullet_char=chars[0])
            element_count += len(bullet_items)
            continue

        # ── Numbered list (1.) ──
        num_match = re.match(r"^(\s*)\d+[.)]\s+(.+)$", stripped)
        if num_match:
            num_items = []
            while i < len(lines):
                nm = re.match(r"^(\s*)\d+[.)]\s+(.+)$", lines[i])
                if not nm:
                    break
                indent_level = len(nm.group(1)) // 2
                num_items.append((indent_level, _strip_inline_md(nm.group(2))))
                i += 1
            if any(level > 0 for level, _ in num_items):
                doc.add_nested_numbered_list(num_items)
            else:
                doc.add_numbered_list([text for _, text in num_items])
            element_count += len(num_items)
            continue

        # ── Regular paragraph (inline formatting) ──
        _add_rich_paragraph(doc, stripped, style=s)
        element_count += 1
        i += 1

    return element_count


def _parse_inline_segments(text: str) -> list[tuple[str, str]]:
    """Parse inline markdown into segments of (style, text).

    style is one of: 'normal', 'bold', 'italic', 'bold_italic',
    'code', 'link:URL'.
    """
    segments: list[tuple[str, str]] = []
    # Pattern matches: ***bold_italic***, **bold**, *italic*, `code`, [text](url), ![alt](url)
    pattern = re.compile(
        r"!\[([^\]]*)\]\([^)]+\)"        # image ![alt](url) → alt text
        r"|\[([^\]]+)\]\(([^)]+)\)"       # link [text](url)
        r"|`([^`]+)`"                     # inline code
        r"|\*\*\*(.+?)\*\*\*"            # bold+italic
        r"|\*\*(.+?)\*\*"                # bold
        r"|\*(.+?)\*"                     # italic
    )
    last_end = 0
    for m in pattern.finditer(text):
        # Text before this match
        if m.start() > last_end:
            segments.append(("normal", text[last_end:m.start()]))
        if m.group(1) is not None:      # image
            segments.append(("normal", m.group(1) or ""))
        elif m.group(2) is not None:    # link
            segments.append((f"link:{m.group(3)}", m.group(2)))
        elif m.group(4) is not None:    # code
            segments.append(("code", m.group(4)))
        elif m.group(5) is not None:    # bold+italic
            segments.append(("bold_italic", m.group(5)))
        elif m.group(6) is not None:    # bold
            segments.append(("bold", m.group(6)))
        elif m.group(7) is not None:    # italic
            segments.append(("italic", m.group(7)))
        last_end = m.end()
    # Remaining text
    if last_end < len(text):
        segments.append(("normal", text[last_end:]))
    if not segments:
        segments.append(("normal", text))
    return segments


def _add_rich_paragraph(doc, md_text: str, style: dict | None = None) -> None:
    """Add a single paragraph with inline bold/italic/code/hyperlink formatting.

    All segments (including hyperlinks) are placed in one paragraph
    to avoid unwanted line breaks.
    """
    import xml.etree.ElementTree as ET
    import uuid as _uuid

    _HP = f"{{{_HP_NS}}}"

    segments = _parse_inline_segments(md_text)

    # Fast path: no formatting at all
    if len(segments) == 1 and segments[0][0] == "normal":
        doc.add_paragraph(segments[0][1])
        return

    # Create one paragraph, append all segments as runs
    first_style, first_text = segments[0]
    if first_style.startswith("link:"):
        # First segment is a link — create empty paragraph first
        para = doc.add_paragraph("", include_run=False)
    else:
        char_id = _style_for_segment(doc, first_style, style=style)
        para = doc.add_paragraph(first_text, char_pr_id_ref=char_id)

    def _mk(parent, tag, attrib=None):
        child = parent.makeelement(tag, attrib or {})
        parent.append(child)
        return child

    # If first segment was a link, we still need to add it
    start_idx = 0 if first_style.startswith("link:") else 1

    for seg_type, text in segments[start_idx:]:
        if not text:
            continue

        if seg_type.startswith("link:"):
            url = seg_type[5:]
            field_id = str(_uuid.uuid4().int % (2**31))
            begin_id = str(_uuid.uuid4().int % (2**31))

            # Run: fieldBegin
            run1 = _mk(para.element, f"{_HP}run", {"charPrIDRef": "0"})
            ctrl1 = _mk(run1, f"{_HP}ctrl")
            fb = _mk(ctrl1, f"{_HP}fieldBegin", {
                "id": begin_id, "type": "HYPERLINK", "name": "",
                "editable": "0", "dirty": "0", "zorder": "-1", "fieldid": field_id,
            })
            params = _mk(fb, f"{_HP}parameters", {"cnt": "6", "name": ""})
            p0 = _mk(params, f"{_HP}integerParam", {"name": "Prop"})
            p0.text = "0"
            escaped_url = url.replace(":", "\\:")
            p1 = _mk(params, f"{_HP}stringParam", {"name": "Command"})
            p1.text = f"{escaped_url};1;0;0;"
            p2 = _mk(params, f"{_HP}stringParam", {"name": "Path"})
            p2.text = url
            p3 = _mk(params, f"{_HP}stringParam", {"name": "Category"})
            p3.text = "HWPHYPERLINK_TYPE_URL"
            p4 = _mk(params, f"{_HP}stringParam", {"name": "TargetType"})
            p4.text = "HWPHYPERLINK_TARGET_BOOKMARK"
            p5 = _mk(params, f"{_HP}stringParam", {"name": "DocOpenType"})
            p5.text = "HWPHYPERLINK_JUMP_CURRENTTAB"

            # Run: link text (blue + underline)
            link_char_id = doc.ensure_run_style(
                underline=True, text_color="#0969DA", height=1000,
            )
            run2 = _mk(para.element, f"{_HP}run", {"charPrIDRef": str(link_char_id)})
            t = _mk(run2, f"{_HP}t")
            t.text = text

            # Run: fieldEnd
            run3 = _mk(para.element, f"{_HP}run", {"charPrIDRef": "0"})
            ctrl3 = _mk(run3, f"{_HP}ctrl")
            _mk(ctrl3, f"{_HP}fieldEnd", {"beginIDRef": begin_id, "fieldid": field_id})
        else:
            # Normal/bold/italic/code — just add a styled run
            seg_char_id = _style_for_segment(doc, seg_type, style=style)
            run = para.element.makeelement(f"{_HP}run", {"charPrIDRef": str(seg_char_id)})
            t = run.makeelement(f"{_HP}t", {})
            t.text = text
            run.append(t)
            para.element.append(run)


def _style_for_segment(doc, seg_style: str, style: dict | None = None) -> str:
    """Return a charPrIDRef using the active MD style preset."""
    s = style or MD_STYLES[DEFAULT_STYLE]
    h = s["body_height"]
    color = s.get("body_color")
    font = s.get("body_font")
    font_kw = {}
    if font:
        font_kw = {"font_hangul": font, "font_latin": font}
    if seg_style == "bold":
        return doc.ensure_run_style(bold=True, height=h, text_color=color, **font_kw)
    elif seg_style == "italic":
        return doc.ensure_run_style(italic=True, height=h, text_color=color, **font_kw)
    elif seg_style == "bold_italic":
        return doc.ensure_run_style(bold=True, italic=True, height=h, text_color=color, **font_kw)
    elif seg_style == "code":
        code_font = s.get("code_font", "D2Coding")
        return doc.ensure_run_style(
            font_latin=code_font, font_hangul=code_font,
            height=s["code_height"], text_color=s["inline_code_text"])
    return "0"


def _strip_inline_md(text: str) -> str:
    """Strip inline markdown formatting (bold, italic, code, links)."""
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text)
    text = re.sub(r"___(.+?)___", r"\1", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    return text


# ── Convert Commands ──────────────────────────────────────────────────
# SPEC: e2e-hwpx-skill-v1-021 -- File Upload Screen
# SPEC: e2e-hwpx-skill-v1-022 -- File Upload Parse Connection
# SPEC: e2e-hwpx-skill-v1-023 -- File Convert Processing

@cli.command("convert")
@click.argument("source", type=click.Path(exists=True))
@click.option("--output", "-o", required=True, help="Output .hwpx file path")
@handle_error
def convert_file(source, output):
    """Convert HTML, Markdown, or plain text file to HWPX document."""
    from pathlib import Path

    src = Path(source)
    ext = src.suffix.lower()
    supported = {".html", ".htm", ".md", ".markdown", ".txt", ".text"}
    if ext not in supported:
        raise ValueError(f"Unsupported format: {ext}. Supported: html, md, txt")

    content = src.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"File is empty: {source}")

    doc = doc_mod.new_document()
    element_count = 0

    if ext in (".html", ".htm"):
        # Strip HTML tags, split by block elements
        content = re.sub(r"<br\s*/?>", "\n", content)
        content = re.sub(r"</(?:p|div|h[1-6]|li|tr|blockquote)>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"<[^>]+>", "", content)
        import html as html_mod_builtin
        content = html_mod_builtin.unescape(content)
        for line in content.split("\n"):
            line = line.strip()
            if line:
                doc.add_paragraph(line)
                element_count += 1

    elif ext in (".md", ".markdown"):
        element_count = _convert_markdown_to_hwpx(doc, content)

    else:
        # Plain text: each non-empty line is a paragraph
        for line in content.split("\n"):
            line = line.strip()
            if line:
                doc.add_paragraph(line)
                element_count += 1

    doc_mod.save_document(doc, output)

    # SPEC: e2e-hwpx-skill-v1-024 -- File Convert Response
    result = {
        "source": source,
        "format": ext.lstrip("."),
        "paragraphs": element_count,
        "output": output,
    }
    globals()["output"](result, f"Converted {element_count} paragraphs from {source} to {output}")


# ── Session Commands ───────────────────────────────────────────────────

@cli.command("undo")
@handle_error
def session_undo():
    """Undo the last operation."""
    sess = get_session()
    if sess.undo():
        globals()["output"]({"status": "undone"}, "Undone")
    else:
        globals()["output"]({"status": "nothing_to_undo"}, "Nothing to undo")


@cli.command("redo")
@handle_error
def session_redo():
    """Redo the last undone operation."""
    sess = get_session()
    if sess.redo():
        globals()["output"]({"status": "redone"}, "Redone")
    else:
        globals()["output"]({"status": "nothing_to_redo"}, "Nothing to redo")


# ── REPL ───────────────────────────────────────────────────────────────

@cli.command("repl")
@handle_error
def repl():
    """Enter interactive REPL mode."""
    global _repl_mode
    _repl_mode = True

    from cli_anything.hwpx.utils.repl_skin import ReplSkin

    skin = ReplSkin("hwpx", version="1.0.0")
    skin.print_banner()

    pt_session = skin.create_prompt_session()
    sess = get_session()

    skin.info("Type 'help' for commands, 'quit' to exit")
    skin.info("HWPX documents: Korean word processor format (ZIP + XML)")
    print()

    while True:
        try:
            project_name = ""
            if sess.has_project():
                project_name = os.path.basename(sess.path or "untitled")

            user_input = skin.get_input(
                pt_session,
                project_name=project_name,
                modified=sess.modified,
            )

            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "q"):
                if sess.modified:
                    skin.warning("You have unsaved changes!")
                    confirm = input("  Quit without saving? (y/N): ").strip().lower()
                    if confirm != "y":
                        continue
                skin.print_goodbye()
                break

            if user_input.lower() == "help":
                skin.help({
                    "document new [--output PATH]": "Create a new document",
                    "document open PATH":          "Open an existing .hwpx file",
                    "document save [PATH]":         "Save current document",
                    "document info":                "Show document information",
                    "text extract [--format FMT]":  "Extract text (text/markdown/html)",
                    "text find QUERY":              "Search for text",
                    "text replace --old X --new Y": "Replace text",
                    "text add TEXT":                "Add a paragraph",
                    "table add -r ROWS -c COLS":    "Add a table",
                    "table list":                   "List all tables",
                    "image add PATH":               "Add an image",
                    "image list":                   "List all images",
                    "export text -o PATH":          "Export as plain text",
                    "export markdown -o PATH":      "Export as Markdown",
                    "export html -o PATH":          "Export as HTML",
                    "validate schema [PATH]":       "Validate document schema",
                    "validate package PATH":        "Validate package structure",
                    "structure sections":            "List sections",
                    "structure set-header TEXT":     "Set header text",
                    "structure set-footer TEXT":     "Set footer text",
                    "undo":                          "Undo last change",
                    "redo":                          "Redo last undo",
                    "quit":                          "Exit REPL",
                })
                continue

            # Parse and dispatch command via Click
            try:
                args = user_input.split()
                cli.main(args=args, standalone_mode=False)
            except SystemExit:
                pass
            except click.exceptions.UsageError as e:
                skin.error(str(e))
            except Exception as e:
                skin.error(f"{type(e).__name__}: {e}")

        except KeyboardInterrupt:
            print()
            skin.warning("Use 'quit' to exit")
        except EOFError:
            skin.print_goodbye()
            break


# ── Entry Point ────────────────────────────────────────────────────────

def main():
    cli()


if __name__ == "__main__":
    main()
