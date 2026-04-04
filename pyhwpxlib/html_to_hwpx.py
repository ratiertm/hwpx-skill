"""HTML -> HWPX converter using only Python standard library.

Uses ``html.parser.HTMLParser`` to parse HTML and calls pyhwpxlib API
functions to build the HWPX document.

Public API::

    from pyhwpxlib.html_to_hwpx import convert_html_to_hwpx, convert_html_file_to_hwpx

    # From string
    doc = create_document()
    convert_html_to_hwpx(doc, html_string)
    save(doc, "output.hwpx")

    # From file
    convert_html_file_to_hwpx("input.html", "output.hwpx")
"""
from __future__ import annotations

import base64
import logging
import os
import re
import tempfile
from html.parser import HTMLParser
from typing import Optional

from . import api

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CSS inline-style parser
# ---------------------------------------------------------------------------

def _parse_inline_style(style_str: str) -> dict:
    """Parse a CSS inline style string into a dict of properties."""
    result: dict = {}
    if not style_str:
        return result
    for decl in style_str.split(";"):
        decl = decl.strip()
        if ":" not in decl:
            continue
        prop, _, val = decl.partition(":")
        result[prop.strip().lower()] = val.strip()
    return result


def _css_color_to_hex(color_str: str) -> Optional[str]:
    """Convert a CSS color value to #RRGGBB hex string.

    Handles: #RGB, #RRGGBB, rgb(r,g,b).  Returns None for unsupported.
    """
    color_str = color_str.strip()
    if color_str.startswith("#"):
        h = color_str[1:]
        if len(h) == 3:
            return "#" + "".join(c * 2 for c in h)
        if len(h) == 6:
            return color_str.upper()
        return None
    m = re.match(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color_str)
    if m:
        return "#{:02X}{:02X}{:02X}".format(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def _css_size_to_pt(size_str: str) -> Optional[int]:
    """Convert a CSS font-size value to integer pt.

    Handles: Npt, Npx (approximate).  Returns None for unsupported.
    """
    size_str = size_str.strip().lower()
    m = re.match(r"([\d.]+)\s*pt", size_str)
    if m:
        return int(float(m.group(1)))
    m = re.match(r"([\d.]+)\s*px", size_str)
    if m:
        # Approximate: 1px ~ 0.75pt
        return max(1, int(float(m.group(1)) * 0.75))
    return None


# ---------------------------------------------------------------------------
# Style context — tracks inline formatting state
# ---------------------------------------------------------------------------

class _StyleCtx:
    """Tracks the current inline formatting state from nested tags."""
    __slots__ = ("bold", "italic", "underline", "strikeout",
                 "text_color", "font_size", "bg_color")

    def __init__(
        self,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        strikeout: bool = False,
        text_color: Optional[str] = None,
        font_size: Optional[int] = None,
        bg_color: Optional[str] = None,
    ):
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.strikeout = strikeout
        self.text_color = text_color
        self.font_size = font_size
        self.bg_color = bg_color

    def copy(self) -> _StyleCtx:
        return _StyleCtx(
            bold=self.bold,
            italic=self.italic,
            underline=self.underline,
            strikeout=self.strikeout,
            text_color=self.text_color,
            font_size=self.font_size,
            bg_color=self.bg_color,
        )

    def has_style(self) -> bool:
        return (self.bold or self.italic or self.underline
                or self.text_color is not None or self.font_size is not None)


# ---------------------------------------------------------------------------
# Block-level tags
# ---------------------------------------------------------------------------

_BLOCK_TAGS = frozenset({
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "div", "section", "article", "main", "aside", "nav",
    "blockquote", "pre", "hr", "br",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td",
    "figure", "figcaption", "details", "summary",
})

_INLINE_STYLE_TAGS = frozenset({
    "strong", "b", "em", "i", "u", "s", "strike", "del",
    "mark", "span", "code", "a", "sub", "sup",
})

_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})

_VOID_TAGS = frozenset({"br", "hr", "img", "input", "meta", "link"})


# ---------------------------------------------------------------------------
# The parser
# ---------------------------------------------------------------------------

class HwpxHtmlParser(HTMLParser):
    """State-machine HTML parser that emits pyhwpxlib API calls."""

    def __init__(self, hwpx_file):
        super().__init__(convert_charrefs=True)
        self.hwpx = hwpx_file

        # Text accumulation
        self._text_buf: str = ""

        # Inline style stack
        self._style_stack: list[_StyleCtx] = [_StyleCtx()]

        # Block context
        self._in_heading: int = 0        # 1-6 or 0
        self._in_blockquote: bool = False
        self._in_pre: bool = False
        self._pre_text: str = ""

        # List context
        self._list_stack: list[str] = []  # "ul" or "ol"
        self._list_items: list[str] = []
        self._in_li: bool = False

        # Table context
        self._in_table: bool = False
        self._table_data: list[list[str]] = []
        self._current_row: list[str] = []
        self._in_td: bool = False

        # Skip content inside <head>, <style>, <script>, <title>
        self._skip_depth: int = 0

        # Link context
        self._in_a: bool = False
        self._a_href: str = ""
        self._a_text: str = ""

        # Ruby context
        self._in_ruby: bool = False
        self._ruby_main: str = ""
        self._in_rt: bool = False
        self._rt_text: str = ""

        # Select/option context
        self._in_select: bool = False
        self._select_items: list[tuple[str, str]] = []
        self._select_name: str = "ComboBox1"

        # Mark context
        self._in_mark: bool = False
        self._mark_text: str = ""

        # Temp files to clean up
        self._temp_files: list[str] = []

        # Counter for form element names
        self._form_counter: int = 0

    # -- current style property -----------------------------------------------

    @property
    def _cur_style(self) -> _StyleCtx:
        return self._style_stack[-1]

    def _push_style(self, **overrides) -> None:
        new = self._cur_style.copy()
        for k, v in overrides.items():
            setattr(new, k, v)
        self._style_stack.append(new)

    def _pop_style(self) -> None:
        if len(self._style_stack) > 1:
            self._style_stack.pop()

    # -- text buffer helpers --------------------------------------------------

    def _flush_text(self) -> None:
        """Flush accumulated text as a paragraph with current style."""
        text = self._text_buf.strip()
        self._text_buf = ""
        if not text:
            return

        # Delegate to the appropriate context
        if self._in_td or self._in_li or self._in_a or self._in_mark:
            return  # handled by their respective end-tag handlers
        if self._in_pre:
            return  # handled by </pre>
        if self._in_ruby or self._in_rt:
            return  # handled by </ruby>
        if self._in_select:
            return

        self._emit_text(text)

    def _emit_text(self, text: str) -> None:
        """Emit a single text paragraph with the current style."""
        if not text:
            return

        s = self._cur_style

        if self._in_heading:
            level = min(self._in_heading, 4)  # API supports 1-4
            api.add_heading(self.hwpx, text, level=level)
        elif self._in_blockquote:
            api.add_styled_paragraph(
                self.hwpx, text, italic=True, text_color="#666666",
            )
        elif s.bg_color and not s.has_style():
            # highlight-only
            api.add_highlight(self.hwpx, text, color=s.bg_color)
        elif s.has_style():
            api.add_styled_paragraph(
                self.hwpx, text,
                bold=s.bold, italic=s.italic, underline=s.underline,
                font_size=s.font_size, text_color=s.text_color,
            )
        else:
            api.add_paragraph(self.hwpx, text)

    # -- tag dispatch ---------------------------------------------------------

    _SKIP_TAGS = frozenset({"head", "style", "script", "title"})

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]):
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        attr_dict = dict(attrs)

        try:
            self._handle_starttag_inner(tag, attr_dict)
        except Exception as e:
            logger.warning("HTML start tag handler error [<%s>]: %s", tag, e)

    def _handle_starttag_inner(self, tag: str, attrs: dict) -> None:
        # --- Block-level: flush text first ---
        if tag in _BLOCK_TAGS and tag not in ("br",):
            self._flush_text()

        # --- Headings ---
        if tag in _HEADING_TAGS:
            self._in_heading = int(tag[1])
            return

        # --- Paragraph / div ---
        if tag in ("p", "div"):
            style = _parse_inline_style(attrs.get("style", ""))
            overrides: dict = {}
            if style.get("font-weight") in ("bold", "700", "800", "900"):
                overrides["bold"] = True
            if style.get("font-style") == "italic":
                overrides["italic"] = True
            if style.get("text-decoration") and "underline" in style["text-decoration"]:
                overrides["underline"] = True
            color = _css_color_to_hex(style.get("color", ""))
            if color:
                overrides["text_color"] = color
            size = _css_size_to_pt(style.get("font-size", ""))
            if size:
                overrides["font_size"] = size
            bg = _css_color_to_hex(style.get("background-color", ""))
            if bg:
                overrides["bg_color"] = bg
            if overrides:
                self._push_style(**overrides)
            return

        # --- Blockquote ---
        if tag == "blockquote":
            self._in_blockquote = True
            return

        # --- Pre / code ---
        if tag == "pre":
            self._in_pre = True
            self._pre_text = ""
            return
        if tag == "code" and not self._in_pre:
            # Inline code — treat as monospace, but we just use normal text
            self._push_style(bold=False)
            return

        # --- Lists ---
        if tag in ("ul", "ol"):
            self._list_stack.append(tag)
            self._list_items = []
            return
        if tag == "li":
            self._in_li = True
            self._text_buf = ""
            return

        # --- Table ---
        if tag == "table":
            self._in_table = True
            self._table_data = []
            return
        if tag == "tr":
            self._current_row = []
            return
        if tag in ("td", "th"):
            self._in_td = True
            self._text_buf = ""
            return

        # --- Inline styles ---
        if tag in ("strong", "b"):
            self._flush_text()
            self._push_style(bold=True)
            return
        if tag in ("em", "i"):
            self._flush_text()
            self._push_style(italic=True)
            return
        if tag == "u":
            self._flush_text()
            self._push_style(underline=True)
            return
        if tag in ("s", "strike", "del"):
            self._flush_text()
            self._push_style(strikeout=True)
            return
        if tag == "mark":
            self._flush_text()
            self._in_mark = True
            self._mark_text = ""
            return
        if tag == "span":
            self._flush_text()
            style = _parse_inline_style(attrs.get("style", ""))
            overrides = {}
            if style.get("font-weight") in ("bold", "700", "800", "900"):
                overrides["bold"] = True
            if style.get("font-style") == "italic":
                overrides["italic"] = True
            if style.get("text-decoration") and "underline" in style["text-decoration"]:
                overrides["underline"] = True
            color = _css_color_to_hex(style.get("color", ""))
            if color:
                overrides["text_color"] = color
            size = _css_size_to_pt(style.get("font-size", ""))
            if size:
                overrides["font_size"] = size
            bg = _css_color_to_hex(style.get("background-color", ""))
            if bg:
                overrides["bg_color"] = bg
            self._push_style(**overrides)
            return

        # --- Link ---
        if tag == "a":
            self._flush_text()
            self._in_a = True
            self._a_href = attrs.get("href", "")
            self._a_text = ""
            return

        # --- Image ---
        if tag == "img":
            self._flush_text()
            src = attrs.get("src", "")
            self._handle_image(src)
            return

        # --- Horizontal rule ---
        if tag == "hr":
            api.add_line(self.hwpx, x1=0, y1=0, x2=42520, y2=0,
                         line_color="#CCCCCC", line_width=283)
            return

        # --- Line break ---
        if tag == "br":
            if self._in_pre:
                self._pre_text += "\n"
            elif self._in_li:
                self._text_buf += "\n"
            elif self._in_td:
                self._text_buf += " "
            else:
                # Flush current text, start new implicit paragraph
                self._flush_text()
            return

        # --- Form controls ---
        if tag == "input":
            self._flush_text()
            input_type = attrs.get("type", "text").lower()
            self._form_counter += 1
            name = attrs.get("name", f"FormCtrl{self._form_counter}")
            if input_type == "checkbox":
                checked = "checked" in attrs
                caption = attrs.get("value", "")
                api.add_checkbox(self.hwpx, caption=caption, checked=checked,
                                 name=name)
            elif input_type == "radio":
                checked = "checked" in attrs
                caption = attrs.get("value", "")
                group = attrs.get("name", "")
                api.add_radio_button(self.hwpx, caption=caption,
                                     group=group, checked=checked, name=name)
            else:
                # text, password, etc -> edit field
                value = attrs.get("value", "")
                api.add_edit_field(self.hwpx, text=value, name=name)
            return

        if tag == "button":
            self._flush_text()
            self._form_counter += 1
            self._push_style()  # button text accumulates
            return

        if tag == "select":
            self._flush_text()
            self._in_select = True
            self._select_items = []
            self._form_counter += 1
            self._select_name = attrs.get("name", f"ComboBox{self._form_counter}")
            return
        if tag == "option":
            # accumulate text
            return

        if tag == "textarea":
            self._flush_text()
            self._form_counter += 1
            name = attrs.get("name", f"Edit{self._form_counter}")
            self._push_style()  # text accumulates, handled at end
            return

        # --- Ruby ---
        if tag == "ruby":
            self._flush_text()
            self._in_ruby = True
            self._ruby_main = ""
            return
        if tag == "rt":
            self._in_rt = True
            self._rt_text = ""
            return

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in self._SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth > 0:
            return
        try:
            self._handle_endtag_inner(tag)
        except Exception as e:
            logger.warning("HTML end tag handler error [</%s>]: %s", tag, e)

    def _handle_endtag_inner(self, tag: str) -> None:
        # --- Headings ---
        if tag in _HEADING_TAGS:
            text = self._text_buf.strip()
            self._text_buf = ""
            if text:
                level = min(self._in_heading, 4)
                api.add_heading(self.hwpx, text, level=level)
            self._in_heading = 0
            return

        # --- Paragraph / div ---
        if tag in ("p", "div"):
            text = self._text_buf.strip()
            self._text_buf = ""
            if text:
                self._emit_text(text)
            # Pop style if we pushed one in starttag
            # (we pushed only if there were CSS overrides — pop cautiously)
            if len(self._style_stack) > 1:
                self._pop_style()
            return

        # --- Blockquote ---
        if tag == "blockquote":
            text = self._text_buf.strip()
            self._text_buf = ""
            if text:
                self._emit_text(text)
            self._in_blockquote = False
            return

        # --- Pre / code ---
        if tag == "pre":
            code_text = self._pre_text or self._text_buf
            self._text_buf = ""
            self._pre_text = ""
            self._in_pre = False
            if code_text.strip():
                api.add_code_block(self.hwpx, code_text.strip())
            return
        if tag == "code" and not self._in_pre:
            # Inline code end — emit text with current style
            text = self._text_buf.strip()
            self._text_buf = ""
            if text:
                self._emit_text(text)
            self._pop_style()
            return

        # --- Lists ---
        if tag == "li":
            text = self._text_buf.strip()
            self._text_buf = ""
            self._in_li = False
            if text:
                self._list_items.append(text)
            return
        if tag in ("ul", "ol"):
            items = self._list_items[:]
            self._list_items = []
            list_type = self._list_stack.pop() if self._list_stack else tag
            if items:
                if list_type == "ul":
                    api.add_bullet_list(self.hwpx, items)
                else:
                    api.add_numbered_list(self.hwpx, items)
            return

        # --- Table ---
        if tag in ("td", "th"):
            text = self._text_buf.strip()
            self._text_buf = ""
            self._in_td = False
            self._current_row.append(text)
            return
        if tag == "tr":
            if self._current_row:
                self._table_data.append(self._current_row[:])
            self._current_row = []
            return
        if tag == "table":
            self._in_table = False
            if self._table_data:
                rows = len(self._table_data)
                cols = max(len(r) for r in self._table_data) if self._table_data else 0
                if cols > 0:
                    # Normalize: pad short rows
                    normalized = []
                    for r in self._table_data:
                        padded = r + [""] * (cols - len(r))
                        normalized.append(padded)
                    api.add_table(self.hwpx, rows=rows, cols=cols, data=normalized)
            self._table_data = []
            return

        # --- Inline styles ---
        if tag in ("strong", "b", "em", "i", "u", "s", "strike", "del"):
            text = self._text_buf.strip()
            self._text_buf = ""
            if text:
                self._emit_text(text)
            self._pop_style()
            return

        if tag == "span":
            text = self._text_buf.strip()
            self._text_buf = ""
            if text:
                self._emit_text(text)
            self._pop_style()
            return

        # --- Mark ---
        if tag == "mark":
            text = self._mark_text or self._text_buf.strip()
            self._text_buf = ""
            self._in_mark = False
            self._mark_text = ""
            if text:
                api.add_highlight(self.hwpx, text)
            return

        # --- Link ---
        if tag == "a":
            text = self._a_text or self._text_buf.strip()
            self._text_buf = ""
            self._in_a = False
            if text and self._a_href:
                api.add_hyperlink(self.hwpx, text, self._a_href)
            elif text:
                api.add_paragraph(self.hwpx, text)
            self._a_href = ""
            self._a_text = ""
            return

        # --- Button ---
        if tag == "button":
            text = self._text_buf.strip()
            self._text_buf = ""
            self._pop_style()
            api.add_button(self.hwpx, caption=text or "Button")
            return

        # --- Select ---
        if tag == "option":
            text = self._text_buf.strip()
            self._text_buf = ""
            if text:
                self._select_items.append((text, text))
            return
        if tag == "select":
            self._in_select = False
            items = self._select_items[:]
            self._select_items = []
            api.add_combobox(self.hwpx, items=items or None,
                             name=self._select_name)
            return

        # --- Textarea ---
        if tag == "textarea":
            text = self._text_buf.strip()
            self._text_buf = ""
            self._pop_style()
            self._form_counter += 1
            api.add_edit_field(self.hwpx, text=text,
                               name=f"TextArea{self._form_counter}",
                               multi_line=True)
            return

        # --- Ruby ---
        if tag == "rt":
            self._in_rt = False
            return
        if tag == "ruby":
            main_text = self._ruby_main.strip()
            sub_text = self._rt_text.strip()
            self._in_ruby = False
            self._ruby_main = ""
            self._rt_text = ""
            if main_text and sub_text:
                api.add_dutmal(self.hwpx, main_text, sub_text)
            elif main_text:
                api.add_paragraph(self.hwpx, main_text)
            return

        # --- Ignored closing tags ---
        if tag in ("thead", "tbody", "tfoot", "section", "article",
                    "main", "aside", "nav", "figure", "figcaption",
                    "details", "summary", "html", "head", "body",
                    "title", "style", "script", "noscript",
                    "header", "footer"):
            return

    def handle_data(self, data: str):
        if self._skip_depth > 0:
            return
        try:
            self._handle_data_inner(data)
        except Exception as e:
            logger.warning("HTML data handler error: %s", e)

    def _handle_data_inner(self, data: str) -> None:
        # Skip content inside <style> and <script>
        # HTMLParser calls handle_data for text inside all tags

        if self._in_pre:
            self._pre_text += data
            return

        if self._in_rt:
            self._rt_text += data
            return

        if self._in_ruby and not self._in_rt:
            self._ruby_main += data
            return

        if self._in_a:
            self._a_text += data
            return

        if self._in_mark:
            self._mark_text += data
            return

        # Collapse whitespace for non-pre content
        data = re.sub(r"\s+", " ", data)

        self._text_buf += data

    def handle_entityref(self, name: str):
        # convert_charrefs=True handles most, but just in case
        import html
        try:
            ch = html.unescape(f"&{name};")
            self.handle_data(ch)
        except Exception:
            self.handle_data(f"&{name};")

    def handle_charref(self, name: str):
        import html
        try:
            ch = html.unescape(f"&#{name};")
            self.handle_data(ch)
        except Exception:
            pass

    # -- finalize -----------------------------------------------------------

    def finalize(self) -> None:
        """Flush any remaining text buffer."""
        text = self._text_buf.strip()
        self._text_buf = ""
        if text:
            self._emit_text(text)

    def cleanup(self) -> None:
        """Remove any temporary files created for images."""
        for f in self._temp_files:
            try:
                os.unlink(f)
            except OSError:
                pass
        self._temp_files.clear()

    # -- image handling -----------------------------------------------------

    def _handle_image(self, src: str) -> None:
        """Handle <img src="...">.

        Supports:
        - data:image/...;base64,...  (decode and write to temp file)
        - file:///...  (local file path)
        - relative or absolute file paths
        - http(s)://... URLs are skipped (stdlib only, no requests)
        """
        if not src:
            return

        # Base64 data URI
        if src.startswith("data:"):
            self._handle_base64_image(src)
            return

        # HTTP/HTTPS — skip (we only use stdlib)
        if src.startswith(("http://", "https://")):
            # Try urllib if available (it's stdlib)
            try:
                self._handle_url_image(src)
            except Exception:
                # Can't download — emit placeholder text
                api.add_paragraph(self.hwpx, f"[Image: {src}]")
            return

        # file:// URI
        if src.startswith("file://"):
            path = src[7:]  # strip file://
            if os.path.isfile(path):
                api.add_image(self.hwpx, path)
            else:
                api.add_paragraph(self.hwpx, f"[Image not found: {path}]")
            return

        # Regular file path
        if os.path.isfile(src):
            api.add_image(self.hwpx, src)
        else:
            api.add_paragraph(self.hwpx, f"[Image: {src}]")

    def _handle_base64_image(self, data_uri: str) -> None:
        """Decode a base64 data URI image and add it to the document."""
        m = re.match(r"data:image/(\w+);base64,(.+)", data_uri, re.DOTALL)
        if not m:
            return

        fmt = m.group(1).lower()
        if fmt == "jpeg":
            fmt = "jpg"
        b64_data = m.group(2)

        try:
            img_bytes = base64.b64decode(b64_data)
        except Exception as e:
            logger.warning("Failed to decode base64 image data: %s", e)
            return

        # Write to temp file
        suffix = f".{fmt}"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        try:
            os.write(fd, img_bytes)
            os.close(fd)
            self._temp_files.append(tmp_path)
            api.add_image(self.hwpx, tmp_path)
        except OSError as e:
            logger.warning("Failed to write base64 image to temp file: %s", e)
            try:
                os.close(fd)
            except OSError:
                pass

    def _handle_url_image(self, url: str) -> None:
        """Download an image from a URL and add it to the document."""
        from urllib.request import urlopen
        from urllib.error import URLError

        try:
            resp = urlopen(url, timeout=10)
            img_bytes = resp.read()
        except (URLError, OSError):
            api.add_paragraph(self.hwpx, f"[Image: {url}]")
            return

        # Guess format from URL or content-type
        content_type = resp.headers.get("Content-Type", "")
        if "png" in content_type or url.lower().endswith(".png"):
            fmt = "png"
        elif "gif" in content_type or url.lower().endswith(".gif"):
            fmt = "gif"
        elif "bmp" in content_type or url.lower().endswith(".bmp"):
            fmt = "bmp"
        else:
            fmt = "jpg"

        suffix = f".{fmt}"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        try:
            os.write(fd, img_bytes)
            os.close(fd)
            self._temp_files.append(tmp_path)
            api.add_image(self.hwpx, tmp_path)
        except OSError as e:
            logger.warning("Failed to write URL image to temp file [%s]: %s", url, e)
            try:
                os.close(fd)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_html_to_hwpx(hwpx_file, html_content: str) -> int:
    """Convert HTML string to HWPX elements in an existing document.

    Parameters
    ----------
    hwpx_file : HWPXFile
        An existing HWPX document (from ``api.create_document()``).
    html_content : str
        HTML content to convert.

    Returns
    -------
    int
        Number of elements added (approximate — not all elements are counted).
    """
    parser = HwpxHtmlParser(hwpx_file)
    try:
        parser.feed(html_content)
        parser.finalize()
    except Exception as e:
        logger.warning("HTML parser error (partial output may be returned): %s", e)
    finally:
        parser.cleanup()

    # Return approximate element count from section
    try:
        section = hwpx_file.section_xml_file_list.get(0)
        return section.count_of_para() - 1  # subtract the blank SecPr para
    except (AttributeError, IndexError, TypeError):
        return 0


def convert_html_file_to_hwpx(html_path: str, hwpx_path: str) -> None:
    """Convert an HTML file to a HWPX file.

    Parameters
    ----------
    html_path : str
        Path to the input HTML file.
    hwpx_path : str
        Path for the output .hwpx file.
    """
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    doc = api.create_document()
    convert_html_to_hwpx(doc, content)
    api.save(doc, hwpx_path)
