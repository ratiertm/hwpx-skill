"""LLM Quick Reference Guide for pyhwpxlib.

Usage: python -m pyhwpxlib guide
"""

GUIDE = r"""
# pyhwpxlib v0.17.3 — LLM Quick Reference Guide

## Installation
```
pip install pyhwpxlib              # core
pip install pyhwpxlib[preview]     # + rhwp WASM (SVG preview, page-guard)
```

## When to use what (workflow router)

| User intent | Workflow |
|-------------|----------|
| "Create a new report / proposal" | §1 HwpxBuilder + §2 themes |
| "Fill this form / template" | §8 register → fill → save_session |
| "Edit this existing document" | §7 overlay or §9 JSON round-trip |
| "Convert .hwp to .hwpx" | §6 hwp2hwpx.convert() |
| "Generate Korean 공문 (기안문)" | §11 GongmunBuilder |
| "Read text / tables / images" | §5 extract_text / extract_overlay |

## CRITICAL RULES (must obey)

| # | Rule | Why |
|---|------|-----|
| 1 | No `\n` inside text — use separate `add_paragraph()` | Whale error |
| 2 | No `ET.tostring()` — use string replacement | Breaks namespace prefixes |
| 3 | Empty paragraph before/after heading, table, image | Spacing |
| 4 | Tables only when content is tabular | Don't force tables into prose |
| 5 | Always run `validate` + `lint` after create/edit | Catch breakage early |
| 6 | Pick a theme — never hardcode default blue | Visual variety |
| 7 | Render SVG/PNG preview, READ it before reporting "done" | Visual self-check |
| 8 | After edits, lineseg consistency required (v0.14.0+ opt-in) | Hancom security warning |
| 9 | We don't produce non-standard structures | rhwp alignment: detect, notify, never silent-rewrite |
| **10** | **Substitution-first edits** — replace text nodes, don't add new `<hp:p>` / `<hp:tbl>` | Format preservation |
| **11** | **Structural-change limits** — no add/delete/split/merge of `<hp:p>` / `<hp:tbl>` / `rowCnt` / `colCnt` without explicit user request | Reference fidelity |
| **12** | **Page count parity (when reference exists)** — output page count must equal reference | Form / 공문 trust |
| **13** | **`pyhwpxlib page-guard` must PASS before "done"** — `validate` passing is not enough | Mandatory gate (v0.16.0+) |

## 1. Create a new document
```python
from pyhwpxlib import HwpxBuilder

doc = HwpxBuilder(theme='forest')          # one of 10 themes
doc.add_heading("Title", level=1)
doc.add_paragraph("")                      # spacing (REQUIRED)
doc.add_paragraph("Body text.")
doc.add_paragraph("")
doc.add_table([["A", "B"], ["1", "2"]])    # only if data is tabular
doc.add_paragraph("")
doc.add_image("photo.png", width=42520, height=23918)  # full A4 width
doc.add_paragraph("")
doc.save("output.hwpx")
```

### Image size rule
Default width is **always 42520** (full A4). Compute height to keep aspect ratio:
```python
from PIL import Image
w, h = Image.open("photo.png").size
doc.add_image("photo.png", width=42520, height=int(42520 * h / w))
```
Logos/icons only: width 8000–12000.

## 2. Themes (10)

| Theme | Color | Use |
|-------|-------|-----|
| default | Blue #395da2 | Corporate / 공문 |
| forest | Green #2C5F2D | Environment / ESG |
| warm_executive | Brown #B85042 | Proposals |
| ocean_analytics | Teal #065A82 | Data |
| coral_energy | Coral #F96167 | Marketing |
| charcoal_minimal | Gray #36454F | Technical |
| teal_trust | Teal #028090 | Medical / finance |
| berry_cream | Wine #6D2E46 | Education |
| sage_calm | Sage #84B59F | Wellness |
| cherry_bold | Red #990011 | Warning / strong |

**Custom theme from existing doc**:
```python
from pyhwpxlib import extract_theme, save_theme, HwpxBuilder
theme = extract_theme("reference.hwpx", name="my_style")
save_theme(theme)                          # ~/.pyhwpxlib/themes/my_style.json
HwpxBuilder(theme='custom/my_style')
```

## 3. HwpxBuilder API — full surface (19 add_* methods, v0.15.0+)

| Group | Methods |
|-------|---------|
| Structure | `add_heading(text, level=1..4)` `add_paragraph(text, bold, italic, font_size, text_color, alignment)` `add_page_break()` `add_line()` |
| Emphasis | `add_highlight(text, color)` `add_footnote(text)` `add_equation(latex)` |
| Lists | `add_bullet_list(items)` `add_numbered_list(items)` `add_nested_bullet_list(items)` `add_nested_numbered_list(items)` |
| Visuals | `add_image(path, width, height)` `add_image_from_url(url, filename, width, height)` `add_table(data, header_bg, cell_colors, col_widths, row_heights)` `add_rectangle(...)` `add_draw_line(...)` |
| Decorum | `add_header(text)` `add_footer(text)` `add_page_number(pos="BOTTOM_CENTER")` |
| Save | `save(path)` |

`add_paragraph("")` is the spacing primitive — use liberally.

## 4. Read existing documents
```python
from pyhwpxlib.api import extract_text
text = extract_text("doc.hwpx")

from pyhwpxlib.json_io.overlay import extract_overlay
overlay = extract_overlay("doc.hwpx")
# overlay['texts'], overlay['tables'], overlay['images']
```

## 5. Edit existing — overlay (text replacement)
```python
from pyhwpxlib.json_io.overlay import extract_overlay, apply_overlay
o = extract_overlay("doc.hwpx")
for t in o['texts']:
    t['value'] = t['value'].replace('OLD', 'NEW')
apply_overlay("doc.hwpx", o, "out.hwpx")
```

Image replacement (base64 swap):
```python
import base64
o = extract_overlay("doc.hwpx")
for img in o['images']:
    with open("new.png", "rb") as f:
        img['new_data_b64'] = base64.b64encode(f.read()).decode()
apply_overlay("doc.hwpx", o, "out.hwpx")
```

## 6. Convert .hwp → .hwpx
```python
from pyhwpxlib.hwp2hwpx import convert
convert("old.hwp", "new.hwpx")
```

## 7. Forms — register, fill, persist (v0.17.0+)

The form-fill workflow is the most repeated. Each registered template owns
a workspace folder under `~/.local/share/pyhwpxlib/templates/<name>/` that
holds `original.hwpx`, `decisions.md` (free notes), `history.json` (last
fill payloads), and `outputs/`.

### Register once
```bash
pyhwpxlib template add <source.hwpx> --name <key>
pyhwpxlib template annotate <key> \
    --description "한 줄 설명" \
    --structure A|B \
    --page-standard 1page|free
```
- `--structure A` = label and value cells are adjacent (use `fill_template`)
- `--structure B` = label + value share one cell (use unpack→string-replace→pack)
- `--page-standard 1page` = strict 1-page output (지급조서 / 검수확인서 류)

### Each session: load, fill, save
```python
from pyhwpxlib.templates.context import load_context
ctx = load_context(name)                   # decisions + recent_data restored
print(ctx.to_markdown())                    # post into chat — model absorbs

from pyhwpxlib.api import fill_template
fill_template("template.hwpx",
              data={"성명": "홍길동", "생년월일": "1990-01-01"},
              output_path="filled.hwpx")
```

CLI alternatives:
```bash
pyhwpxlib template fill <key> -d data.json -o out.hwpx     # auto records
pyhwpxlib template context <key>                            # print restore md
pyhwpxlib template log-fill <key> -d data.json              # manual record
```

### Close the loop at session end (MCP, v0.17.1+)
```
hwpx_template_save_session(
  name="<key>",
  data='<filled JSON>',
  decision="이번 채팅에서 새로 합의한 규칙 (예: 'X 필드는 줄바꿈 금지')"
)
```
Single round-trip = `log_fill` + `annotate(add_decision=...)`. Either or both
fields may be empty; both empty → no-op.

### Page-guard mandatory gate (v0.16.0+, Critical Rule #13)
```bash
pyhwpxlib page-guard --reference original.hwpx --output filled.hwpx
# exit 0 (PASS) → done. exit 1 (FAIL) → autofit / shrink / retry.
```

## 8. JSON ↔ HWPX (v0.15.0+) — for external LLM/MCP

JSON expressivity now matches all 19 builder methods (heading, image,
header/footer, lists, footnote, equation, highlight, shapes, page_number,
page_break — full coverage).

```python
from pyhwpxlib.json_io import from_json, to_json

data = {
  "header": {"text": "Confidential"},
  "footer": {"text": "Acme"},
  "page_number": {"pos": "BOTTOM_CENTER"},
  "sections": [{
    "paragraphs": [
      {"runs": [{"content": {"type": "heading",
                              "heading": {"text": "1. Intro", "level": 1}}}]},
      {"runs": [{"content": {"type": "text", "text": "Body..."}}]},
      {"runs": [{"content": {"type": "bullet_list",
                              "bullet_list": {"items": ["a", "b", "c"]}}}]},
    ],
    "tables": [], "page_settings": {}
  }]
}
from_json(data, "out.hwpx")

parsed = to_json("out.hwpx")               # round-trip; image/footnote/
                                           # equation/shape detected
```

`RunContent.type` ∈ `text | table | heading | image | bullet_list |
numbered_list | nested_bullet_list | nested_numbered_list | footnote |
equation | highlight | shape_rect | shape_line | shape_draw_line`.
Unknown type → `ValueError` (rhwp policy: no silent skip).

## 9. CLI — validate / lint / doctor / page-guard / blueprint
```bash
# Health & rendering risks
pyhwpxlib validate <file>                          # default --mode both
pyhwpxlib validate <file> --mode strict            # OWPML spec strict (rhwp)
pyhwpxlib validate <file> --mode compat            # what Hancom accepts
pyhwpxlib lint <file>                              # rendering-risk check

# Diagnose / repair non-standard input (v0.14.0+, opt-in fix)
pyhwpxlib doctor <file>                            # report only
pyhwpxlib doctor <file> --fix                      # → <file>.fixed.hwpx
pyhwpxlib doctor <file> --fix --inplace            # overwrite

# Mandatory gate when a reference exists (v0.16.0+)
pyhwpxlib page-guard --reference REF --output OUT [--threshold N]

# Structural blueprint for understanding (v0.16.0+)
pyhwpxlib analyze <file> --blueprint --depth 1|2|3 [--json]

# Font resolution check (v0.17.1+ refined)
pyhwpxlib font-check <file> --json
pyhwpxlib font-check <file> --font-map fonts.json  # user override map
# status ∈ {ok, alias, fallback, missing}; source ∈ {map, override, fallback}

# Theme management
pyhwpxlib themes list

# All commands above support --json for automation.
```

## 10. Image utilities
```python
# Insert image into existing document
from pyhwpxlib.api import insert_image_to_existing
insert_image_to_existing("doc.hwpx", "photo.png", "out.hwpx",
    width=21260, height=15000, position='end')
```

## 11. Korean 공문 / 기안문 — 행정업무운영 편람 2025 준수
```python
from pyhwpxlib.gongmun import (Gongmun, GongmunBuilder, signer,
                                validate_file, format_report)

doc = Gongmun(
    기관명="행정안전부",
    수신="수신자 참조",                  # or "내부결재"
    제목="2024년 정보공개 종합평가 계획 안내",
    본문=[
        "「공공기관의 정보공개에 관한 법률」 ...",
        ("계약 개요", [                          # nested 가./나./다.
            "계약명: ...",
            "계약 금액: ...",
        ]),
    ],
    붙임=["계획서 1부."],                        # auto "끝." marker
    발신명의="행정안전부장관",
    기안자=signer("행정사무관", "김OO"),
    결재권자=signer("과장", "박OO", 전결=True, 서명일자="2025. 9. 30."),
    시행_처리과명="정보공개과", 시행_일련번호="000", 시행일="2025. 9. 30.",
    우편번호="30112", 도로명주소="세종특별자치시 도움6로 42",
    전화="(044)205-0000", 공개구분="대국민공개",
)
GongmunBuilder(doc).save("output.hwpx")
GongmunBuilder(doc, autofit=True).save("output.hwpx")  # 1-page strict
print(format_report(validate_file("output.hwpx")))     # 10-rule check
```

Auto-applied per 편람: date `2025. 9. 20.`, item-symbol 8 levels
`1.→가.→1)→가)→(1)→(가)→①→㉮`, 2-tap indent, `VV끝.` end-marker, 발신명의
omission for internal approvals (영 §13③), grey separator, etc.

Auto-detected violations: `DATE_FORMAT`, `AUTHORITATIVE_TONE`,
`DISCRIMINATORY_TERM`, `HANGUL_COMPAT_CHAR` (㉮ etc.), `DUEUM_ERROR`,
`LOANWORD_ERROR`, `END_MARKER_MISSING`.

## 12. Preview (SVG / HTML / RenderTree / PNG)
```python
from pyhwpxlib.rhwp_bridge import RhwpEngine     # needs [preview] extra
engine = RhwpEngine()
doc = engine.load("output.hwpx")
svg  = doc.render_page_svg(0, embed_fonts=True)  # for browser embedding
html = doc.render_page_html(0)                   # lighter, tens of KB
tree = doc.get_page_render_tree(0)               # {type, bbox, children}
                                                  # use bbox to assert overflow

# PNG export (v0.17.3+) — handles the Korean-tofu pitfall automatically
from pyhwpxlib.api import render_to_png
png_path = render_to_png("output.hwpx", page=0)  # → output_preview_p0.png
# Pipeline: rhwp SVG → regex-substitute every font-family to bundled
# NanumGothic (registered to fontconfig) → cairosvg.svg2png. The
# substitution is critical: cairosvg cannot resolve original Korean
# font names like 함초롬바탕 via fontconfig, so without it CJK text
# renders as tofu (□□□). Don't try render_page_svg(embed_fonts=True)
# + cairosvg — cairosvg's @font-face support fails for CJK even when
# the embedded subset is valid. Use render_to_png() instead.
```

CLI:
```bash
pyhwpxlib png input.hwpx                          # → input_preview_p0.png
pyhwpxlib png input.hwpx --page 1 --scale 2.0    # higher DPI
pyhwpxlib png input.hwpx --json                   # machine-readable result
```

MCP: `hwpx_render_png(hwpx_path, output_path, page, scale, font_name, register_fonts)`.

## 13. MCP tools (Claude Code / external orchestration)

| Tool | Purpose |
|------|---------|
| `hwpx_guide` | Returns this guide |
| `hwpx_validate` / `hwpx_lint` / `hwpx_font_check` / `hwpx_page_guard` | CLI wrappers |
| `hwpx_template_workspace_list` | List registered forms (v0.17.0+) |
| `hwpx_template_context` | Restore decisions + recent_data for one form |
| `hwpx_template_log_fill` | Append a fill record |
| `hwpx_template_save_session` | log_fill + annotate in one call (v0.17.1+) |
| `hwpx_render_png` | Render an HWPX page to PNG (Korean-safe, v0.17.3+) |

## Common LLM mistakes — avoid

- Writing XML directly → use `HwpxBuilder`
- `\n` inside text → Whale error; split into paragraphs
- No spacing between blocks → text sticks
- Tables for narrative → only when tabular
- `from hwpx import ...` → wrong; it's `from pyhwpxlib import ...`
- Skipping `validate` / `lint` / `page-guard` → broken file delivered
- 공문 labels like '기안자: ' attached → 편람 위반; use `GongmunBuilder`
- Date `2025.9.20` (no spaces) → use `format_date()` (`2025. 9. 20.`)
- Saving form output with manual path then forgetting `save_session` → next
  session loses the decisions; use `hwpx_template_save_session`
- LLM choosing font sizes by mm to fit page → wrong domain; delegate to
  `GongmunBuilder(autofit=True)` or autofit utility (deterministic)

## Version history (recent)

| Version | Highlights |
|---------|-----------|
| **0.17.3** | PNG export — `pyhwpxlib.api.render_to_png()` + CLI `pyhwpxlib png` + MCP `hwpx_render_png`. Bypasses cairosvg `@font-face` CJK limitation by font-family substitution to bundled NanumGothic |
| 0.17.2 | docs — built-in LLM guide refreshed (was stuck at v0.10.0) covering 0.13.3–0.17.1 features |
| 0.17.1 | font-check `--font-map` + ok/alias/fallback/missing precision + lazy wasmtime fix + MCP `hwpx_template_save_session` |
| **0.17.0** | Workspace persistence — `template add/annotate/context/log-fill/install-hook` + outputs/decisions.md/history.json |
| 0.16.1 | Default fonts → 나눔고딕 (SIL OFL) for license safety |
| **0.16.0** | `page-guard` mandatory gate + `analyze --blueprint` + Critical Rules #10–#13 |
| 0.15.0 | JSON 19/19 builder methods (full expressivity, opt-A) |
| **0.14.0** | rhwp alignment — silent-fix opt-in, `doctor`, `validate --mode strict\|compat\|both` |
| 0.13.4 | auto_schema cellSpan-aware grid + row-group label + `template diagnose` |
| 0.13.3 | Template workflow (XDG hierarchy) — `add/fill/show/list` |
| 0.13.0 | Korean official-document standard fonts/sizes/margins |
"""


def print_guide():
    print(GUIDE)
