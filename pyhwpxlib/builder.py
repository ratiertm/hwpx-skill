#!/usr/bin/env python3
"""HwpxBuilder — HWPX document builder API.

Usage:
    from pyhwpxlib import HwpxBuilder, DS, TABLE_PRESETS

    doc = HwpxBuilder()
    doc.add_heading("제목", level=1)
    doc.add_paragraph("본문 텍스트")
    doc.add_table([["A", "B"], ["1", "2"]])
    doc.save("output.hwpx")
"""
import os
import sys
import zipfile
import shutil
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
BLANK_TEMPLATE = SCRIPT_DIR / "tools" / "blank.hwpx"

# HWPX 네임스페이스
NS = {
    'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hs': 'http://www.hancom.co.kr/hwpml/2011/section',
    'hh': 'http://www.hancom.co.kr/hwpml/2011/head',
    'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
}


def _esc(text: str) -> str:
    """XML 특수문자 이스케이프"""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))


# ── 표 스타일 프리셋 (SKILL.md 규격 기반) ──

# ── Administrative Slate 디자인 시스템 색상 ──
DS = {
    'primary': '#395da2',        # 헤더, 악센트 바
    'primary_dim': '#2b5195',    # 진한 블루
    'on_primary': '#f7f7ff',     # 블루 위 텍스트 (거의 흰색)
    'on_surface': '#2b3437',     # 본문 텍스트 (순검정 금지)
    'on_surface_var': '#586064', # 메타데이터, 캡션
    'surface': '#f8f9fa',        # 배경
    'surface_low': '#f1f4f6',    # 줄무늬 행, 2차 영역
    'surface_high': '#e3e9ec',   # 강조 배경
    'primary_container': '#d8e2ff',  # 하이라이트 섹션
    'outline_var': '#abb3b7',    # 연한 테두리
    'error': '#9f403d',          # 경고
    'tertiary_container': '#e2dbfd',  # 콜아웃
}

TABLE_PRESETS = {
    'corporate': {  # 기업 보고서 (Administrative Slate)
        'header_bg': DS['primary'],
        'header_text': DS['on_primary'],
        'cell_margin': (283, 283, 200, 200),
        'header_height': 2400,
        'row_height': 2000,
        'header_align': 'CENTER',
        'data_align': 'CENTER',
        'stripe_color': DS['surface_low'],
    },
    'government': {  # 정부 양식
        'header_bg': DS['primary'],
        'header_text': DS['on_primary'],
        'cell_margin': (425, 425, 283, 283),
        'header_height': 2400,
        'row_height': 2000,
        'header_align': 'CENTER',
        'data_align': 'CENTER',
        'stripe_color': DS['surface_low'],
    },
    'academic': {  # 학술 논문 (배경색 없음, 3선)
        'header_bg': '',
        'header_text': '',
        'cell_margin': (200, 200, 141, 141),
        'header_height': 2000,
        'row_height': 1800,
        'header_align': 'CENTER',
        'data_align': 'CENTER',
        'stripe_color': '',
    },
    'default': {  # 일반 문서
        'header_bg': DS['primary'],
        'header_text': DS['on_primary'],
        'cell_margin': (283, 283, 200, 200),
        'header_height': 2400,
        'row_height': 2000,
        'header_align': 'CENTER',
        'data_align': 'CENTER',
        'stripe_color': DS['surface_low'],
    },
}


class HwpxBuilder:
    """HWPX 문서 빌더 — XML 직접 구성"""

    def __init__(self, table_preset: str = 'default', theme: str | 'Theme' = 'default'):
        """
        Args:
            table_preset: 표 기본 스타일 ('corporate', 'government', 'academic', 'default')
            theme: 테마 이름(str) 또는 Theme 인스턴스. 기본 'default' = Administrative Slate.
        """
        from pyhwpxlib.themes import Theme, BUILTIN_THEMES, _make_table_presets

        # Resolve theme
        if isinstance(theme, str):
            if theme not in BUILTIN_THEMES:
                raise ValueError(
                    f"Unknown theme '{theme}'. "
                    f"Available: {', '.join(sorted(BUILTIN_THEMES.keys()))}"
                )
            self._theme: Theme = BUILTIN_THEMES[theme]
        elif isinstance(theme, Theme):
            self._theme = theme
        else:
            raise TypeError(f"theme must be str or Theme, got {type(theme).__name__}")

        # Detect whether this is the built-in default theme (backward compat path)
        self._is_default_theme = (self._theme is BUILTIN_THEMES.get('default'))

        self._actions: list[dict] = []

        # Per-instance table presets derived from theme palette
        self._table_presets_dict = _make_table_presets(self._theme.palette)
        self._table_preset = self._table_presets_dict.get(
            table_preset, self._table_presets_dict['default']
        )

    # ── 콘텐츠 추가 API (동작 기록) ──

    def add_heading(self, text: str, level: int = 1, alignment: str = 'JUSTIFY'):
        """제목 추가 (level 1~4)"""
        self._actions.append({
            'kind': 'heading', 'text': text, 'level': level,
            'alignment': alignment,
        })

    def add_paragraph(self, text: str, bold=False, italic=False,
                       font_size=None, text_color=None, alignment='JUSTIFY'):
        """일반 단락 추가

        Args:
            alignment: 'JUSTIFY' | 'CENTER' | 'LEFT' | 'RIGHT'
        """
        styled = bold or italic or font_size or text_color
        self._actions.append({
            'kind': 'paragraph', 'text': text, 'styled': styled,
            'bold': bold, 'italic': italic,
            'font_size': font_size, 'text_color': text_color,
            'alignment': alignment,
        })

    def add_table(self, data: list[list[str]], header_bg: str | None = None,
                   cell_colors: dict | None = None,
                   cell_margin: tuple | None = None,
                   col_widths: list | None = None,
                   row_heights: list | None = None,
                   merge_info: list | None = None,
                   cell_gradients: dict | None = None,
                   cell_aligns: dict | None = None,
                   cell_styles: dict | None = None,
                   width: int = 42520,
                   use_preset: bool = True):
        """표 추가

        Args:
            header_bg: 헤더 행 배경색. None이면 프리셋 사용, ''이면 배경색 없음.
            cell_colors: {(row,col): '#hex'} 셀별 배경색
            cell_margin: (left, right, top, bottom) HWPX 단위 셀 패딩. None이면 프리셋 사용.
            col_widths: 컬럼별 너비 리스트 (HWPX 단위)
            row_heights: 행별 높이 리스트. None이면 프리셋 기반 자동 계산.
            merge_info: [(r1,c1,r2,c2), ...] 병합 정보
            cell_gradients: {(row,col): {start, end, type, angle}}
            cell_aligns: {(row,col): 'CENTER'|'LEFT'|'RIGHT'} 셀별 텍스트 정렬
            cell_styles: {(row,col): {bold, text_color, font_size}} 셀별 글자 스타일
            width: 표 전체 너비 (기본 42520 = A4 content width)
            use_preset: False면 프리셋 자동 적용 안 함
        """
        rows = len(data)
        cols = max(len(r) for r in data) if data else 0
        if cols == 0:
            return

        preset = self._table_preset if use_preset else {}

        # cell_margin: 명시하지 않으면 프리셋 적용
        if cell_margin is None and preset.get('cell_margin'):
            cell_margin = preset['cell_margin']

        # row_heights: 명시하지 않으면 프리셋 기반 (헤더행 + 데이터행)
        if row_heights is None and rows > 0:
            h_h = preset.get('header_height', 1500)
            r_h = preset.get('row_height', 1200)
            row_heights = [h_h] + [r_h] * (rows - 1)

        # header_bg: None이면 프리셋, ''이면 명시적 없음
        if header_bg is None:
            header_bg = preset.get('header_bg', '')
        if header_bg:
            cell_colors = cell_colors or {}
            for c in range(cols):
                if (0, c) not in cell_colors:
                    cell_colors[(0, c)] = header_bg

        # cell_aligns: 프리셋에서 헤더 + 데이터 행 정렬 자동 적용
        h_align = preset.get('header_align')
        d_align = preset.get('data_align')
        if (h_align or d_align) and cell_aligns is None:
            cell_aligns = {}
        if h_align:
            for c in range(cols):
                if (0, c) not in cell_aligns:
                    cell_aligns[(0, c)] = h_align
        if d_align:
            for r in range(1, rows):
                for c in range(cols):
                    if (r, c) not in cell_aligns:
                        cell_aligns[(r, c)] = d_align

        # header_text: 프리셋에서 헤더 행 글자 스타일 자동 적용
        h_text = preset.get('header_text')
        if h_text:
            cell_styles = cell_styles or {}
            for c in range(cols):
                if (0, c) not in cell_styles:
                    cell_styles[(0, c)] = {'text_color': h_text, 'bold': True}

        # stripe_color: 프리셋에서 짝수행 배경색 자동 적용
        stripe = preset.get('stripe_color')
        if stripe and rows > 2:
            cell_colors = cell_colors or {}
            for r in range(2, rows, 2):
                for c in range(cols):
                    if (r, c) not in cell_colors:
                        cell_colors[(r, c)] = stripe

        self._actions.append({
            'kind': 'table', 'data': data, 'rows': rows, 'cols': cols,
            'cell_colors': cell_colors or None,
            'cell_margin': cell_margin,
            'col_widths': col_widths,
            'row_heights': row_heights,
            'merge_info': merge_info,
            'cell_gradients': cell_gradients,
            'cell_aligns': cell_aligns or None,
            'cell_styles': cell_styles or None,
            'width': width,
        })

    def add_image(self, image_path: str, width: int | None = None,
                   height: int | None = None):
        """로컬 이미지 삽입

        Args:
            image_path: 이미지 파일 경로
            width: 표시 너비 (HWPX 단위). None이면 원본 크기
            height: 표시 높이 (HWPX 단위). None이면 원본 크기
        """
        self._actions.append({
            'kind': 'image', 'path': image_path,
            'width': width, 'height': height,
        })

    def add_image_from_url(self, url: str, filename: str = '',
                            width: int | None = None, height: int | None = None):
        """URL에서 이미지 다운로드 후 삽입

        Args:
            url: 이미지 URL
            filename: 저장할 파일명 (없으면 URL에서 추출)
            width: 표시 너비 (HWPX 단위)
            height: 표시 높이 (HWPX 단위)
        """
        import urllib.request
        import tempfile
        from urllib.parse import urlparse

        if not filename:
            parsed = urlparse(url)
            filename = Path(parsed.path).name or 'image.png'
            if '.' not in filename:
                filename += '.png'

        tmp_dir = Path(tempfile.gettempdir()) / 'hwpx_images'
        tmp_dir.mkdir(exist_ok=True)
        local_path = str(tmp_dir / filename)

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
        })
        with urllib.request.urlopen(req) as resp:
            with open(local_path, 'wb') as f:
                f.write(resp.read())

        self._actions.append({
            'kind': 'image', 'path': local_path,
            'width': width, 'height': height,
        })
        return local_path

    def add_page_break(self):
        """페이지 나누기 삽입"""
        self._actions.append({'kind': 'page_break'})

    def add_line(self):
        """구분선 추가"""
        self._actions.append({'kind': 'line'})

    # ── 목록 ──

    def add_bullet_list(self, items: list[str], bullet_char: str = '-',
                         indent: int = 2000, native: bool = False):
        """글머리 기호 목록

        Args:
            bullet_char: 블릿 문자 (기본 '-', '•'=작은 원, '◦'=빈 원)
            indent: 왼쪽 들여쓰기 (HWPX 단위, 기본 2000)
            native: True면 HWPX 네이티브 블릿 사용 (Whale에서 문자 무시될 수 있음)
                    False면 텍스트로 직접 블릿 삽입 (확실하게 보임)
        """
        self._actions.append({
            'kind': 'bullet_list', 'items': items, 'bullet_char': bullet_char,
            'indent': indent, 'native': native,
        })

    def add_numbered_list(self, items: list[str], format_string: str = '^1.'):
        """번호 목록

        Args:
            format_string: '^1.' → 1. 2. 3. / '^1)' → 1) 2) 3) / '(^1)' → (1) (2) (3)
        """
        self._actions.append({
            'kind': 'numbered_list', 'items': items, 'format_string': format_string,
        })

    def add_nested_bullet_list(self, items: list[tuple[int, str]]):
        """중첩 글머리 기호 목록

        Args:
            items: [(level, text), ...] — level 0~6
        """
        self._actions.append({'kind': 'nested_bullet_list', 'items': items})

    def add_nested_numbered_list(self, items: list[tuple[int, str]]):
        """중첩 번호 목록

        Args:
            items: [(level, text), ...] — level 0~6
        """
        self._actions.append({'kind': 'nested_numbered_list', 'items': items})

    # ── 머리말/꼬리말/페이지번호 ──

    def add_header(self, text: str):
        """머리말 추가"""
        self._actions.append({'kind': 'header', 'text': text})

    def add_footer(self, text: str):
        """꼬리말 추가"""
        self._actions.append({'kind': 'footer', 'text': text})

    def add_page_number(self, pos: str = 'BOTTOM_CENTER'):
        """페이지 번호 추가

        Args:
            pos: 'BOTTOM_CENTER' | 'BOTTOM_RIGHT' | 'TOP_CENTER' | 'TOP_RIGHT'
        """
        self._actions.append({'kind': 'page_number', 'pos': pos})

    # ── 각주/수식/도형 ──

    def add_footnote(self, text: str, number: int = 1):
        """각주 추가"""
        self._actions.append({'kind': 'footnote', 'text': text, 'number': number})

    def add_equation(self, script: str):
        """수식 삽입"""
        self._actions.append({'kind': 'equation', 'script': script})

    def add_highlight(self, text: str, color: str = '#FFFF00'):
        """텍스트 하이라이트 (배경색 강조)"""
        self._actions.append({'kind': 'highlight', 'text': text, 'color': color})

    def add_rectangle(self, width: int = 14400, height: int = 7200,
                       line_color: str = '#000000', line_width: int = 283):
        """사각형 도형"""
        self._actions.append({
            'kind': 'rectangle', 'width': width, 'height': height,
            'line_color': line_color, 'line_width': line_width,
        })

    def add_draw_line(self, x1: int = 0, y1: int = 0, x2: int = 42520, y2: int = 0,
                       line_color: str = '#000000', line_width: int = 283):
        """직선 도형"""
        self._actions.append({
            'kind': 'draw_line', 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'line_color': line_color, 'line_width': line_width,
        })

    # ── 테마 스타일 헬퍼 ──

    def _heading_style_kwargs(self, level: int) -> dict:
        """Return ensure_char_style kwargs for a heading at the given level.

        For the default theme, returns only bold+height (backward compat).
        For custom themes, adds font_name and text_color from the theme.
        """
        sizes = self._theme.sizes
        height = {1: sizes.h1, 2: sizes.h2, 3: sizes.h3, 4: sizes.h4}.get(level, 12) * 100
        kwargs: dict = {'bold': True, 'height': height}

        if not self._is_default_theme:
            kwargs['font_name'] = self._theme.fonts.heading_hangul
            kwargs['text_color'] = self._theme.palette.on_surface

        return kwargs

    # ── 저장 ──
    # (legacy _build_header/_build_section 제거 — pyhwpxlib API 직접 사용)

    def _build_header_legacy(self) -> str:
        # fontfaces
        fontfaces = '''<hh:fontfaces>
  <hh:fontface lang="HANGUL"><hh:font id="0" face="함초롬돋움" type="TTF" /></hh:fontface>
  <hh:fontface lang="LATIN"><hh:font id="0" face="함초롬돋움" type="TTF" /></hh:fontface>
  <hh:fontface lang="HANJA"><hh:font id="0" face="함초롬돋움" type="TTF" /></hh:fontface>
  <hh:fontface lang="JAPANESE"><hh:font id="0" face="함초롬돋움" type="TTF" /></hh:fontface>
  <hh:fontface lang="OTHER"><hh:font id="0" face="함초롬돋움" type="TTF" /></hh:fontface>
  <hh:fontface lang="SYMBOL"><hh:font id="0" face="함초롬돋움" type="TTF" /></hh:fontface>
  <hh:fontface lang="USER"><hh:font id="0" face="함초롬돋움" type="TTF" /></hh:fontface>
</hh:fontfaces>'''

        # borderFills
        borders = '''<hh:borderFills itemCnt="1">
  <hh:borderFill id="1" threeD="0" shadow="0" slash="0" backSlash="0" cropCell="0" fillBrush="0">
    <hh:leftBorder type="NONE" width="0.1 mm" color="#000000" />
    <hh:rightBorder type="NONE" width="0.1 mm" color="#000000" />
    <hh:topBorder type="NONE" width="0.1 mm" color="#000000" />
    <hh:bottomBorder type="NONE" width="0.1 mm" color="#000000" />
  </hh:borderFill>
</hh:borderFills>'''

        # charProperties
        char_xml = f'<hh:charProperties itemCnt="{len(self._char_styles)}">\n'
        for cs in self._char_styles:
            char_xml += f'  <hh:charPr id="{cs["id"]}" height="{cs["height"]}" textColor="{cs["textColor"]}">\n'
            char_xml += '    <hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0" />\n'
            char_xml += '    <hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100" />\n'
            char_xml += '    <hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0" />\n'
            char_xml += '    <hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100" />\n'
            char_xml += '    <hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0" />\n'
            if cs.get('bold'):
                char_xml += '    <hh:bold />\n'
            if cs.get('italic'):
                char_xml += '    <hh:italic />\n'
            char_xml += '    <hh:underline type="NONE" shape="NONE" color="#000000" />\n'
            char_xml += '    <hh:strikeout shape="NONE" color="#000000" />\n'
            char_xml += '    <hh:outline type="NONE" />\n'
            char_xml += '    <hh:shadow type="NONE" color="#B2B2B2" offsetX="10" offsetY="10" />\n'
            char_xml += f'  </hh:charPr>\n'
        char_xml += '</hh:charProperties>'

        # paraProperties
        para_xml = f'<hh:paraProperties itemCnt="{len(self._para_styles)}">\n'
        for ps in self._para_styles:
            para_xml += f'  <hh:paraPr id="{ps["id"]}" tabPrIDRef="0" condense="{ps.get("condense",0)}" fontLineHeight="0" snapToGrid="1" suppressLineNumbers="0" checked="0">\n'
            para_xml += f'    <hh:align horizontal="{ps["alignment"]}" vertical="BASELINE" />\n'
            para_xml += '    <hh:heading type="NONE" idRef="0" level="0" />\n'
            para_xml += '    <hh:breakSetting breakLatinWord="BREAK_WORD" breakNonLatinWord="KEEP_WORD" widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK" />\n'
            para_xml += '    <hh:autoSpacing eAsianEng="0" eAsianNum="0" />\n'
            para_xml += '    <hh:margin><hc:intent value="0" unit="HWPUNIT" /><hc:left value="0" unit="HWPUNIT" /><hc:right value="0" unit="HWPUNIT" /><hc:prev value="0" unit="HWPUNIT" /><hc:next value="0" unit="HWPUNIT" /></hh:margin>\n'
            para_xml += f'    <hh:lineSpacing type="PERCENT" value="{ps["lineSpacing"]}" unit="HWPUNIT" />\n'
            para_xml += '    <hh:border borderFillIDRef="1" offsetLeft="0" offsetRight="0" offsetTop="0" offsetBottom="0" connect="0" ignoreMargin="0" />\n'
            para_xml += f'  </hh:paraPr>\n'
        para_xml += '</hh:paraProperties>'

        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hh:head xmlns:hh="{NS['hh']}" xmlns:hc="{NS['hc']}" xmlns:hp="{NS['hp']}" version="1.4" secCnt="1">
  <hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1" />
  <hh:refList>
    {fontfaces}
    {borders}
    {char_xml}
    {para_xml}
  </hh:refList>
  <hh:compatibleDocument targetProgram="HWP201X"><hh:layoutCompatibility /></hh:compatibleDocument>
</hh:head>'''

    # ── section0.xml 생성 ──

    def _build_section(self) -> str:
        paras = '\n'.join(self._paragraphs)
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hs:sec xmlns:hp="{NS['hp']}" xmlns:hs="{NS['hs']}" xmlns:hc="{NS['hc']}" xmlns:hh="{NS['hh']}">
<hp:p id="0" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="0">
    <hp:secPr textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000" outlineShapeIDRef="1" memoShapeIDRef="0" textVerticalWidthHead="0">
      <hp:pageSize width="59528" height="84188" />
      <hp:pageMarg header="4252" footer="4252" left="8504" right="8504" top="5668" bottom="4252" />
    </hp:secPr>
  </hp:run>
</hp:p>
{paras}
</hs:sec>'''

    # ── 저장 ──

    def save(self, output_path: str) -> str:
        """HWPX 파일 저장 — pyhwpxlib API로 생성 + 원본 XML 문자열 보존"""
        sys.path.insert(0, str(SCRIPT_DIR.parent))
        from pyhwpxlib.api import (create_document, add_paragraph as api_add_para,
                                    add_heading as api_add_heading,
                                    add_styled_paragraph as api_add_styled,
                                    add_table as api_add_table,
                                    _add_page_break,
                                    save as hwpx_save)
        from pyhwpxlib.style_manager import ensure_para_style, ensure_char_style, font_size_to_height

        # Pass font_set only for non-default themes (backward compat)
        font_set = None if self._is_default_theme else self._theme.fonts
        doc = create_document(font_set=font_set)

        # 기록된 동작을 pyhwpxlib API로 재생
        # header/footer/page_number는 반드시 마지막에 재생
        # (SecPr 구조보다 먼저 삽입하면 Whale 에러)
        deferred = ('header', 'footer', 'page_number')
        normal_actions = [a for a in self._actions if a['kind'] not in deferred]
        deferred_actions = [a for a in self._actions if a['kind'] in deferred]

        for action in normal_actions + deferred_actions:
            kind = action['kind']
            if kind == 'heading':
                align = action.get('alignment', 'JUSTIFY')
                # Compute theme-derived heading style
                heading_kwargs = self._heading_style_kwargs(action['level'])
                if align != 'JUSTIFY':
                    # heading + alignment: charPr 직접 생성 + paraPr alignment
                    char_pr_id = ensure_char_style(doc, **heading_kwargs)
                    para_pr_id = ensure_para_style(doc, align=align)
                    api_add_para(doc, action['text'],
                                 char_pr_id_ref=char_pr_id,
                                 para_pr_id_ref=para_pr_id)
                else:
                    api_add_heading(doc, action['text'], level=action['level'],
                                   **{k: v for k, v in heading_kwargs.items()
                                      if k not in ('bold',)})
            elif kind == 'paragraph':
                align = action.get('alignment', 'JUSTIFY')
                needs_align = align != 'JUSTIFY'
                para_pr_id = "0"
                if needs_align:
                    para_pr_id = ensure_para_style(doc, align=align)
                if action.get('styled'):
                    char_pr_id = ensure_char_style(
                        doc,
                        bold=action.get('bold', False),
                        italic=action.get('italic', False),
                        height=font_size_to_height(action.get('font_size')),
                        text_color=action.get('text_color'),
                    )
                    api_add_para(doc, action['text'],
                                 char_pr_id_ref=char_pr_id,
                                 para_pr_id_ref=para_pr_id)
                else:
                    api_add_para(doc, action['text'],
                                 para_pr_id_ref=para_pr_id)
            elif kind == 'table':
                api_add_table(doc, rows=action['rows'], cols=action['cols'],
                              data=action['data'],
                              cell_colors=action.get('cell_colors'),
                              cell_margin=action.get('cell_margin'),
                              col_widths=action.get('col_widths'),
                              row_heights=action.get('row_heights'),
                              merge_info=action.get('merge_info'),
                              cell_gradients=action.get('cell_gradients'),
                              cell_aligns=action.get('cell_aligns'),
                              cell_styles=action.get('cell_styles'),
                              width=action.get('width', 42520))
            elif kind == 'image':
                from pyhwpxlib.api import add_image as api_add_image
                api_add_image(doc, action['path'],
                              width=action.get('width'),
                              height=action.get('height'))
            elif kind == 'bullet_list':
                bc = action.get('bullet_char', '-')
                for item in action['items']:
                    api_add_para(doc, f'    {bc} {item}')
            elif kind == 'numbered_list':
                from pyhwpxlib.api import add_numbered_list as api_nl
                api_nl(doc, action['items'], format_string=action.get('format_string', '^1.'))
            elif kind == 'nested_bullet_list':
                from pyhwpxlib.api import add_nested_bullet_list as api_nbl
                api_nbl(doc, action['items'])
            elif kind == 'nested_numbered_list':
                from pyhwpxlib.api import add_nested_numbered_list as api_nnl
                api_nnl(doc, action['items'])
            elif kind == 'header':
                from pyhwpxlib.api import add_header as api_hdr
                api_hdr(doc, action['text'])
            elif kind == 'footer':
                from pyhwpxlib.api import add_footer as api_ftr
                api_ftr(doc, action['text'])
            elif kind == 'page_number':
                from pyhwpxlib.api import add_page_number as api_pn
                api_pn(doc, pos=action.get('pos', 'BOTTOM_CENTER'))
            elif kind == 'footnote':
                from pyhwpxlib.api import add_footnote as api_fn
                api_fn(doc, action['text'], number=action.get('number', 1))
            elif kind == 'equation':
                from pyhwpxlib.api import add_equation as api_eq
                api_eq(doc, action['script'])
            elif kind == 'highlight':
                from pyhwpxlib.api import add_highlight as api_hl
                api_hl(doc, action['text'], color=action.get('color', '#FFFF00'))
            elif kind == 'rectangle':
                from pyhwpxlib.api import add_rectangle as api_rect
                api_rect(doc, width=action['width'], height=action['height'],
                         line_color=action.get('line_color', '#000000'),
                         line_width=action.get('line_width', 283))
            elif kind == 'draw_line':
                from pyhwpxlib.api import add_line as api_draw
                api_draw(doc, x1=action['x1'], y1=action['y1'],
                         x2=action['x2'], y2=action['y2'],
                         line_color=action.get('line_color', '#000000'),
                         line_width=action.get('line_width', 283))
            elif kind == 'page_break':
                _add_page_break(doc)
            elif kind == 'line':
                api_add_para(doc, "─" * 40)

        hwpx_save(doc, output_path)
        return output_path


if __name__ == "__main__":
    # 데모: 주식 보고서 생성
    doc = HwpxBuilder()
    doc.add_heading("NVDA 투자 분석 보고서", level=1)
    doc.add_paragraph("2026년 1월 14일", font_size=10, text_color="#888888")
    doc.add_paragraph("")
    doc.add_table([
        ["종목", "등급", "현재가", "목표가"],
        ["NVDA", "Strong Buy", "$184.86", "$250 (+35%)"],
    ])
    doc.add_paragraph("")
    doc.add_heading("핵심 포인트", level=2)
    doc.add_paragraph("토큰 비용 90% 절감. ChatGPT 돌리는 비용이 10분의 1로 줄어듭니다.")
    doc.add_paragraph("")
    doc.add_heading("밸류에이션", level=2)
    doc.add_table([
        ["P/E", "Forward P/E", "PEG Ratio"],
        ["45.6배", "35배", "0.78"],
    ])
    doc.add_paragraph("")
    doc.add_paragraph("본 글은 투자 권유가 아닌 정보 제공 목적으로 작성되었습니다.",
                       font_size=9, text_color="#999999")

    out = doc.save("demo_report.hwpx")
    print(f"Created: {out} ({os.path.getsize(out):,} bytes)")
