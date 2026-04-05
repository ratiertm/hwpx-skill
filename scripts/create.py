#!/usr/bin/env python3
"""HWPX 새 문서 생성 — blank 템플릿 기반 XML 직접 구성

Usage:
    from scripts.create import HwpxBuilder

    doc = HwpxBuilder()
    doc.add_heading("제목", level=1)
    doc.add_paragraph("본문 텍스트")
    doc.add_table([["A", "B"], ["1", "2"]])
    doc.save("output.hwpx")

docx-js 패턴 대응: 프로그래밍으로 새 HWPX 문서를 처음부터 생성.
pyhwpxlib 대신 XML을 직접 구성하여 header.xml 완전 제어.
"""
import os
import sys
import zipfile
import shutil
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
BLANK_TEMPLATE = SCRIPT_DIR / "templates" / "blank.hwpx"

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


class HwpxBuilder:
    """HWPX 문서 빌더 — XML 직접 구성"""

    def __init__(self):
        self._actions: list[dict] = []  # 동작 기록 (pyhwpxlib API로 재생용)

    # ── 콘텐츠 추가 API (동작 기록) ──

    def add_heading(self, text: str, level: int = 1):
        """제목 추가 (level 1~4)"""
        self._actions.append({'kind': 'heading', 'text': text, 'level': level})

    def add_paragraph(self, text: str, bold=False, italic=False,
                       font_size=None, text_color=None, alignment='JUSTIFY'):
        """일반 단락 추가"""
        styled = bold or italic or font_size or text_color
        self._actions.append({
            'kind': 'paragraph', 'text': text, 'styled': styled,
            'bold': bold, 'italic': italic,
            'font_size': font_size, 'text_color': text_color,
        })

    def add_table(self, data: list[list[str]], header_bg: str = ''):
        """표 추가"""
        rows = len(data)
        cols = max(len(r) for r in data) if data else 0
        if cols > 0:
            self._actions.append({
                'kind': 'table', 'data': data, 'rows': rows, 'cols': cols,
            })

    def add_line(self):
        """구분선 추가"""
        self._actions.append({'kind': 'line'})

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
                                    save as hwpx_save)

        doc = create_document()

        # 기록된 동작을 pyhwpxlib API로 재생
        for action in self._actions:
            kind = action['kind']
            if kind == 'heading':
                api_add_heading(doc, action['text'], level=action['level'])
            elif kind == 'paragraph':
                if action.get('styled'):
                    api_add_styled(doc, action['text'],
                                   bold=action.get('bold', False),
                                   italic=action.get('italic', False),
                                   font_size=action.get('font_size'),
                                   text_color=action.get('text_color'))
                else:
                    api_add_para(doc, action['text'])
            elif kind == 'table':
                api_add_table(doc, rows=action['rows'], cols=action['cols'],
                              data=action['data'])
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
