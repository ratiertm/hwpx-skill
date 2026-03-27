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
import json
import click
from typing import Optional

from cli_anything.hwpx.core.session import Session
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
@handle_error
def table_add(rows, cols):
    """Add a table to the document."""
    sess = get_session()
    sess.snapshot()
    result = table_mod.add_table(sess.get_doc(), rows, cols)
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
    import re
    from pathlib import Path

    src = Path(source)
    ext = src.suffix.lower()
    supported = {".html", ".htm", ".md", ".markdown", ".txt", ".text"}
    if ext not in supported:
        raise ValueError(f"Unsupported format: {ext}. Supported: html, md, txt")

    content = src.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"File is empty: {source}")

    # Parse into paragraphs based on format
    if ext in (".html", ".htm"):
        # Strip HTML tags, split by block elements
        content = re.sub(r"<br\s*/?>", "\n", content)
        content = re.sub(r"</(?:p|div|h[1-6]|li|tr|blockquote)>", "\n", content, flags=re.IGNORECASE)
        content = re.sub(r"<[^>]+>", "", content)
        import html as html_mod_builtin
        content = html_mod_builtin.unescape(content)
        paragraphs = [line.strip() for line in content.split("\n") if line.strip()]
    elif ext in (".md", ".markdown"):
        # Keep headings and paragraphs, strip markdown syntax minimally
        paragraphs = [line.strip() for line in content.split("\n") if line.strip()]
    else:
        # Plain text: each non-empty line is a paragraph
        paragraphs = [line.strip() for line in content.split("\n") if line.strip()]

    # Create HWPX document
    doc = doc_mod.new_document()
    for para in paragraphs:
        doc.add_paragraph(para)
    doc_mod.save_document(doc, output)

    # SPEC: e2e-hwpx-skill-v1-024 -- File Convert Response
    result = {
        "source": source,
        "format": ext.lstrip("."),
        "paragraphs": len(paragraphs),
        "output": output,
    }
    globals()["output"](result, f"Converted {len(paragraphs)} paragraphs from {source} to {output}")


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
