"""LLM Quick Reference Guide for pyhwpxlib.

Usage: python -m pyhwpxlib guide
"""

GUIDE = r"""
# pyhwpxlib — LLM Quick Reference Guide

## Installation
```
pip install pyhwpxlib[preview]
```

## 1. Create a New Document
```python
from pyhwpxlib import HwpxBuilder, BUILTIN_THEMES

doc = HwpxBuilder(theme='forest')  # Choose from 10 themes
doc.add_heading("Title", level=1)
doc.add_paragraph("Body text.")
doc.add_table([["Col A", "Col B"], ["1", "2"]])
doc.save("output.hwpx")
```

## 2. Available Themes
| Theme | Color | Best For |
|-------|-------|----------|
| default | Blue #395da2 | Corporate, government |
| forest | Green #2C5F2D | Environment, ESG |
| warm_executive | Brown #B85042 | Proposals, branding |
| ocean_analytics | Teal #065A82 | Data, research |
| coral_energy | Coral #F96167 | Marketing |
| charcoal_minimal | Gray #36454F | Minimal, technical |
| teal_trust | Teal #028090 | Medical, finance |
| berry_cream | Wine #6D2E46 | Education, culture |
| sage_calm | Sage #84B59F | Wellness |
| cherry_bold | Red #990011 | Warning, strong claims |

## 3. Custom Theme (Fonts & Sizes)
```python
from pyhwpxlib.themes import Theme, FontSet, SizeSet, BUILTIN_THEMES

custom = Theme(
    name='my_theme',
    palette=BUILTIN_THEMES['forest'].palette,
    fonts=FontSet(heading_hangul='NanumSquareBold', heading_latin='Arial',
                  body_hangul='NanumMyeongjo', body_latin='Times New Roman',
                  caption_hangul='MalgunGothic', caption_latin='Verdana'),
    sizes=SizeSet(h1=28, h2=22, h3=18, h4=16, body=14, caption=11),
    margins=BUILTIN_THEMES['forest'].margins,
)
doc = HwpxBuilder(theme=custom)
```

## 4. HwpxBuilder API
| Method | Purpose |
|--------|---------|
| add_heading(text, level=1) | Heading (1-4) |
| add_paragraph(text, bold, italic, font_size, text_color, alignment) | Paragraph |
| add_table(data, header_bg, cell_colors, col_widths, row_heights) | Table |
| add_bullet_list(items) | Bullet list |
| add_numbered_list(items) | Numbered list |
| add_image(path, width, height) | Image |
| add_page_break() | Page break |
| add_line() | Horizontal line |
| add_header(text) | Header |
| add_footer(text) | Footer |
| add_page_number() | Page number |
| save(path) | Save to .hwpx |

## 5. Read Existing Documents
```python
from pyhwpxlib.api import extract_text
text = extract_text("document.hwpx")
```

## 6. Convert HWP to HWPX
```python
from pyhwpxlib.hwp2hwpx import convert
convert("old.hwp", "new.hwpx")
```

## 7. Edit Existing Documents (Overlay)
```python
from pyhwpxlib.json_io.overlay import extract_overlay, apply_overlay

overlay = extract_overlay("template.hwpx")

# Modify text fields
for t in overlay['texts']:
    t['value'] = t['value'].replace('old_text', 'new_text')

# Apply changes (preserves ALL formatting)
apply_overlay("template.hwpx", overlay, "output.hwpx")
```

## 8. Fill Form Templates
```python
from pyhwpxlib.api import fill_template_checkbox

fill_template_checkbox("form.hwpx",
    data={"old_label": "new_value"},
    checks=["agree"],  # Check boxes near this label
    output_path="filled.hwpx")
```

## 9. Preview (SVG/PNG)
```python
from pyhwpxlib.rhwp_bridge import RhwpEngine
engine = RhwpEngine()
doc = engine.load("output.hwpx")
svg = doc.render_page_svg(0, embed_fonts=True)
```

## CRITICAL RULES — Violating these breaks Whale/Hancom rendering

1. **No newlines in text** — Never `add_paragraph("line1\nline2")`.
   Use separate `add_paragraph()` for each line.

2. **No ET.tostring()** — Never re-serialize XML with ElementTree.
   It changes namespace prefixes and breaks Whale. Use string replacement.

3. **secPr position** — HwpxBuilder handles this automatically.
   Do NOT add empty paragraphs before your first content paragraph.

4. **Table cell text** — Long text in cells needs explicit line breaks
   via separate paragraphs, not `\n` characters.

5. **Validate after creation** — Always run:
   ```python
   import subprocess
   subprocess.run(["python", "-m", "pyhwpxlib", "validate", "output.hwpx"])
   ```

## Common Mistakes by LLMs

- Creating XML directly instead of using HwpxBuilder → BROKEN FILES
- Putting `\n` in text content → Whale error
- Not using themes → All documents look the same (blue)
- Using `from hwpx import ...` → Wrong package. Use `from pyhwpxlib import ...`
- Adding paragraphs before calling save without any content → Empty secPr paragraph breaks Whale
"""


def print_guide():
    print(GUIDE)
