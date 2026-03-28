"""Parse CSS files into HWPX style dicts.

Maps CSS properties to HWPX charPr/paraPr values.
Only extracts the properties we actually use for MD→HWPX conversion.

CSS unit → HWPX hwpunit mapping:
    1pt  = 100 hwpunit
    1px  ≈ 0.75pt = 75 hwpunit
    1em  = body font-size (default 16px = 12pt = 1200 hwpunit)
    1rem = same as em for our purposes
"""

from __future__ import annotations

import re
from pathlib import Path


def _parse_css_value_to_hwpunit(value: str, base_pt: float = 10.0) -> int:
    """Convert a CSS size value to HWPX hwpunit (100 = 1pt)."""
    value = value.strip().lower()

    # pt
    m = re.match(r"^([\d.]+)\s*pt$", value)
    if m:
        return int(float(m.group(1)) * 100)

    # px (1px ≈ 0.75pt)
    m = re.match(r"^([\d.]+)\s*px$", value)
    if m:
        return int(float(m.group(1)) * 75)

    # em/rem (relative to base)
    m = re.match(r"^([\d.]+)\s*(em|rem)$", value)
    if m:
        return int(float(m.group(1)) * base_pt * 100)

    # percentage
    m = re.match(r"^([\d.]+)\s*%$", value)
    if m:
        return int(float(m.group(1)) / 100.0 * base_pt * 100)

    # bare number (assume pt)
    m = re.match(r"^([\d.]+)$", value)
    if m:
        return int(float(m.group(1)) * 100)

    return int(base_pt * 100)  # fallback to base


def _parse_css_color(value: str) -> str | None:
    """Extract hex color from CSS value. Returns #RRGGBB or None."""
    value = value.strip()
    m = re.search(r"#([0-9a-fA-F]{6})", value)
    if m:
        return f"#{m.group(1).upper()}"
    m = re.search(r"#([0-9a-fA-F]{3})\b", value)
    if m:
        h = m.group(1)
        return f"#{h[0]*2}{h[1]*2}{h[2]*2}".upper()
    # rgba
    m = re.search(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", value)
    if m:
        return f"#{int(m.group(1)):02X}{int(m.group(2)):02X}{int(m.group(3)):02X}"
    return None


def _parse_border_width_to_hwpunit(value: str) -> str:
    """Convert CSS border-width to HWPX line width string."""
    value = value.strip().lower()
    m = re.match(r"^([\d.]+)\s*(px|pt|mm|em)$", value)
    if m:
        num = float(m.group(1))
        unit = m.group(2)
        if unit == "mm":
            mm = num
        elif unit == "px":
            mm = num * 0.264583
        elif unit == "pt":
            mm = num * 0.352778
        elif unit == "em":
            mm = num * 4.233  # 1em ≈ 16px ≈ 4.2mm
        else:
            mm = 0.5
        # Map to HWPX line width (283 = 1mm)
        return str(int(mm * 283))
    return "71"  # thin default


def _extract_rules(css_text: str) -> dict[str, dict[str, str]]:
    """Extract CSS rules into {selector: {property: value}}."""
    # Remove comments
    css_text = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)
    # Remove @media blocks (take only top-level light theme rules)
    # Simple approach: extract rules outside @media
    rules: dict[str, dict[str, str]] = {}

    # Find all rule blocks
    for m in re.finditer(r"([^{}@]+?)\{([^{}]+)\}", css_text):
        selectors = m.group(1).strip()
        props_text = m.group(2).strip()
        # Parse properties
        props: dict[str, str] = {}
        for prop_match in re.finditer(r"([\w-]+)\s*:\s*([^;]+)", props_text):
            prop = prop_match.group(1).strip()
            val = prop_match.group(2).strip()
            props[prop] = val
        # Store by each selector
        for sel in selectors.split(","):
            sel = sel.strip()
            if sel:
                if sel not in rules:
                    rules[sel] = {}
                rules[sel].update(props)
    return rules


def css_to_hwpx_style(css_text: str, name: str = "Custom") -> dict:
    """Convert CSS text to an HWPX style dict.

    Reads CSS rules for body, h1-h6, code, pre, a, blockquote, table th, hr
    and maps them to HWPX style properties.
    """
    rules = _extract_rules(css_text)

    # Determine base font size from body
    body = rules.get("body", rules.get(".markdown-body", {}))
    body_font_size_css = body.get("font-size", "16px")
    base_pt = _parse_css_value_to_hwpunit(body_font_size_css, 10.0) / 100.0
    body_height = int(base_pt * 100)

    def _heading_height(sel: str, default_em: float) -> int:
        r = rules.get(sel, {})
        fs = r.get("font-size")
        if fs:
            return _parse_css_value_to_hwpunit(fs, base_pt)
        return int(default_em * base_pt * 100)

    def _has_border_bottom(sel: str) -> bool:
        r = rules.get(sel, {})
        bb = r.get("border-bottom", r.get("padding-bottom", ""))
        return bool(bb) and "none" not in bb.lower()

    # Heading border color
    heading_border_color = "#D1D9E0"
    for sel in ("h1", "h2"):
        r = rules.get(sel, {})
        bb = r.get("border-bottom", "")
        c = _parse_css_color(bb)
        if c:
            heading_border_color = c
            break
    # Also check CSS variables
    for key, val in body.items():
        if "borderColor" in key and "muted" in key:
            c = _parse_css_color(val)
            if c:
                heading_border_color = c

    # Code block
    pre_rules = rules.get("pre", rules.get("pre > code", {}))
    code_rules = rules.get("code", {})
    code_bg = _parse_css_color(pre_rules.get("background", pre_rules.get("background-color", "")))
    code_text = _parse_css_color(code_rules.get("color", ""))
    code_border = _parse_css_color(pre_rules.get("border", pre_rules.get("border-color", "")))
    code_height_css = code_rules.get("font-size", "85%")
    code_height = _parse_css_value_to_hwpunit(code_height_css, base_pt)

    # Link
    a_rules = rules.get("a", {})
    link_color = _parse_css_color(a_rules.get("color", "")) or "#0969DA"

    # Blockquote
    bq_rules = rules.get("blockquote", {})
    quote_color = _parse_css_color(bq_rules.get("color", "")) or "#59636E"

    # Table header
    th_rules = rules.get("table th", rules.get("th", {}))
    table_header_bg = _parse_css_color(
        th_rules.get("background", th_rules.get("background-color", ""))
    ) or "#F0F0F0"

    # HR
    hr_rules = rules.get("hr", {})
    hr_color_raw = hr_rules.get("border-bottom", hr_rules.get("background-color", ""))
    hr_color = _parse_css_color(hr_color_raw) or heading_border_color
    hr_width_raw = hr_rules.get("height", "")
    hr_width = _parse_border_width_to_hwpunit(hr_width_raw) if hr_width_raw else "71"

    # Body text color
    body_color = _parse_css_color(body.get("color", "")) or "#000000"

    # Body line-height → HWPX line spacing percent
    line_height_css = body.get("line-height", "1.5")
    lh_match = re.match(r"^([\d.]+)", line_height_css.strip())
    if lh_match:
        lh_val = float(lh_match.group(1))
        if lh_val < 10:  # unitless (e.g. 1.5)
            line_spacing = int(lh_val * 100)
        else:  # px value (e.g. 22px)
            line_spacing = int(lh_val / (base_pt * 1.333) * 100)
    else:
        line_spacing = 160

    # Body font-family → extract first sans-serif font name
    body_font_css = body.get("font-family", "")
    body_font = None
    if body_font_css:
        for f in body_font_css.split(","):
            f = f.strip().strip('"').strip("'")
            if f and not f.startswith("-") and f not in ("system-ui", "sans-serif", "serif", "monospace"):
                body_font = f
                break

    # Code font-family
    code_font_css = code_rules.get("font-family", "")
    code_font = "D2Coding"
    if code_font_css:
        for f in code_font_css.split(","):
            f = f.strip().strip('"').strip("'")
            if f and f not in ("monospace",) and not f.startswith("-") and not f.startswith("var("):
                code_font = f
                break

    # Heading color (h1-h6, fallback to body color)
    heading_color = None
    for sel in ("h1", "h2", "h3"):
        r = rules.get(sel, {})
        c = _parse_css_color(r.get("color", ""))
        if c:
            heading_color = c
            break

    # Heading spacing: has margin-top? → add blank line before
    heading_spacing = True  # default: add spacing
    h1_rules = rules.get("h1", {})
    mt = h1_rules.get("margin-top", "24px")
    mt_match = re.match(r"^([\d.]+)", mt.strip())
    if mt_match and float(mt_match.group(1)) < 5:
        heading_spacing = False

    # Blockquote border-left width
    bq_border_raw = bq_rules.get("border-left", "")
    bq_border_width = "71"  # thin default
    bq_border_color = _parse_css_color(bq_border_raw) or heading_border_color
    bw_match = re.match(r"([\d.]+)\s*(px|em|mm|pt)", bq_border_raw)
    if bw_match:
        bq_border_width = _parse_border_width_to_hwpunit(bw_match.group(0))

    # Table border color
    table_border_color = None
    for sel in ("table th", "th", "table td", "td"):
        r = rules.get(sel, {})
        for prop in ("border-bottom", "border", "border-color"):
            c = _parse_css_color(r.get(prop, ""))
            if c:
                table_border_color = c
                break
        if table_border_color:
            break
    table_border_color = table_border_color or "#D1D9E0"

    # Table cell padding: CSS "padding: Vpx Hpx" → (V_hwpunit, H_hwpunit)
    td_rules = rules.get("table td", rules.get("td", {}))
    th_padding = th_rules.get("padding", td_rules.get("padding", "6px 13px"))
    pad_parts = re.findall(r"[\d.]+", th_padding)
    if len(pad_parts) >= 2:
        pad_v = int(float(pad_parts[0]) * 75)
        pad_h = int(float(pad_parts[1]) * 75)
    elif len(pad_parts) == 1:
        pad_v = pad_h = int(float(pad_parts[0]) * 75)
    else:
        pad_v, pad_h = 450, 975

    return {
        "name": name,
        "description": f"Parsed from CSS: {name}",
        "body_height": body_height,
        "h1_height": _heading_height("h1", 2.0),
        "h2_height": _heading_height("h2", 1.5),
        "h3_height": _heading_height("h3", 1.25),
        "h4_height": _heading_height("h4", 1.0),
        "h5_height": _heading_height("h5", 0.875),
        "h6_height": _heading_height("h6", 0.85),
        "h1_h2_border": _has_border_bottom("h1") or _has_border_bottom("h2"),
        "heading_border_color": heading_border_color,
        "code_height": code_height,
        "code_bg": code_bg or "#F6F8FA",
        "code_text": code_text or "#1F2328",
        "code_border": code_border or "#D1D9E0",
        "inline_code_text": code_text or "#1F2328",
        "link_color": link_color,
        "quote_color": quote_color,
        "hr_color": hr_color,
        "hr_width": hr_width,
        "table_header_bg": table_header_bg,
        "body_color": body_color,
        "body_font": body_font,
        "line_spacing": line_spacing,
        "code_font": code_font,
        "heading_color": heading_color,
        "heading_spacing": heading_spacing,
        "quote_border_width": bq_border_width,
        "quote_border_color": bq_border_color,
        "table_border_color": table_border_color,
        "table_cell_padding": (pad_v, pad_h),
        "bullet_chars": ["•", "◦", "▪", "‣", "⁃"],
    }


def load_css_file(path: str | Path) -> dict:
    """Load a CSS file and convert to HWPX style dict."""
    p = Path(path)
    css_text = p.read_text(encoding="utf-8")
    name = p.stem.replace("-", " ").replace("_", " ").title()
    return css_to_hwpx_style(css_text, name=name)


def load_all_styles(styles_dir: str | Path | None = None) -> dict[str, dict]:
    """Load all .css files from a directory into style dicts."""
    if styles_dir is None:
        styles_dir = Path(__file__).parent / "styles"
    styles_dir = Path(styles_dir)
    if not styles_dir.exists():
        return {}
    result = {}
    for css_file in sorted(styles_dir.glob("*.css")):
        key = css_file.stem
        result[key] = load_css_file(css_file)
    return result
