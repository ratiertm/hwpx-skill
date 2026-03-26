# HWPX — Software-Specific SOP

## Overview

**HWPX** (Hancom Word Processor XML) is the modern document format for Hancom Office, the dominant office suite in South Korea. It replaces the legacy binary `.hwp` format with an open, XML-based structure.

## Format Structure

HWPX files are **ZIP archives** containing:
- `mimetype` — MIME type declaration
- `META-INF/container.xml` — OPC container metadata
- `Contents/` — Document body XML (sections, paragraphs, tables)
- `BinData/` — Embedded binary data (images, fonts)
- `header.xml` — Document-level metadata (styles, fonts, numbering)

## Underlying Library

This CLI wraps **python-hwpx** (https://github.com/airmang/python-hwpx):
- Author: 고규현 (Kyuhyun Koh)
- Version: 2.8.2+
- License: MIT
- Dependencies: lxml >= 4.9
- Python: >= 3.10

## Key API Classes

| Class | Purpose |
|-------|---------|
| `HwpxDocument` | High-level editing API (79 methods) |
| `HwpxPackage` | Low-level OPC container handling |
| `TextExtractor` | Section/paragraph iteration with annotations |
| `ObjectFinder` | Element search by tag, attributes, XPath |

## Existing CLI Tools (from python-hwpx)

| Command | Purpose |
|---------|---------|
| `hwpx-unpack` | Extract HWPX to working directory |
| `hwpx-pack` | Repack working directory to HWPX |
| `hwpx-validate` | XSD schema validation |
| `hwpx-validate-package` | ZIP/OPC structure validation |
| `hwpx-page-guard` | Document structure change detection |
| `hwpx-analyze-template` | Template analysis and extraction |
| `hwpx-text-extract` | Text extraction to plain text or Markdown |

## CLI-Anything Mapping

| CLI-Anything Command | python-hwpx API |
|---------------------|-----------------|
| `document new` | `HwpxDocument.new()` |
| `document open` | `HwpxDocument.open(path)` |
| `document save` | `doc.save_to_path(path)` |
| `text extract` | `doc.export_text()` / `doc.export_markdown()` |
| `text find` | Iterate `doc.sections[].paragraphs[].runs[]` |
| `text replace` | `doc.replace_text_in_runs(old, new)` |
| `text add` | `doc.add_paragraph(text)` |
| `table add` | `doc.add_table(rows, cols)` |
| `image add` | `doc.add_image(path, width, height)` |
| `export text/md/html` | `doc.export_text/markdown/html()` |
| `validate schema` | `doc.validate()` |
| `validate package` | `hwpx.tools.validate_package()` |
| `structure set-header` | `doc.set_header_text(text)` |
| `structure set-footer` | `doc.set_footer_text(text)` |

## Important Notes

- HWPX is NOT the same as legacy HWP (binary format) — this tool only handles HWPX
- No Hancom Office installation required — pure Python XML manipulation
- All document mutations are non-destructive (undo/redo via byte snapshots)
- The library preserves original ZIP entry order during pack/unpack cycles
