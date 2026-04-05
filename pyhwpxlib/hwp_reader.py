"""HWP 5.x 바이너리 파일 리더 — olefile 기반

HWP 5.x 바이너리 형식(OLE2 Compound File)에서 텍스트, 스타일, 구조를 추출.
hwp2hwpx Java 라이브러리의 Python 포팅 (Phase A: 기본 읽기).

Usage:
    from pyhwpxlib.hwp_reader import read_hwp, hwp_to_hwpx

    # HWP 구조 읽기
    doc = read_hwp("input.hwp")
    print(doc['texts'])

    # HWP → HWPX 변환
    hwp_to_hwpx("input.hwp", "output.hwpx")
"""
import struct
import zlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import olefile
except ImportError:
    olefile = None
    logger.warning("olefile not installed. HWP 5.x reading disabled. pip install olefile")


# HWP 레코드 태그 ID
TAG_PARA_HEADER = 66
TAG_PARA_TEXT = 67
TAG_PARA_CHAR_SHAPE = 68
TAG_PARA_LINE_SEG = 69
TAG_CTRL_HEADER = 70
TAG_LIST_HEADER = 71
TAG_PAGE_DEF = 72
TAG_TABLE = 76
TAG_CELL = 77


def detect_format(filepath: str) -> str:
    """파일 형식 감지: HWP, HWPX, OWPML, UNKNOWN"""
    import zipfile
    try:
        with zipfile.ZipFile(filepath) as z:
            if 'Contents/section0.xml' in z.namelist():
                return 'HWPX'
    except zipfile.BadZipFile:
        pass

    with open(filepath, 'rb') as f:
        magic = f.read(8)
        if magic[:4] == b'\xd0\xcf\x11\xe0':
            return 'HWP'
        if magic[:2] == b'PK':
            return 'HWPX'
    return 'UNKNOWN'


def read_hwp(filepath: str) -> dict:
    """HWP 5.x 바이너리 파일 읽기 → 구조화된 dict 반환

    Returns
    -------
    dict with keys:
        version: str (e.g. "5.1.0.1")
        compressed: bool
        encrypted: bool
        texts: list of str (전체 텍스트)
        paragraphs: list of dict (단락별 상세)
        streams: list of str (OLE2 스트림 목록)
        bindata: list of str (임베디드 파일 목록)
    """
    if olefile is None:
        raise ImportError("olefile not installed. pip install olefile")

    ole = olefile.OleFileIO(filepath)
    try:
        result = {
            'source': str(Path(filepath).name),
            'format': 'HWP',
        }

        # 1. FileHeader
        fh = ole.openstream('FileHeader').read()
        version = struct.unpack_from('<I', fh, 32)[0]
        props = struct.unpack_from('<I', fh, 36)[0]
        result['version'] = f"{(version>>24)&0xFF}.{(version>>16)&0xFF}.{(version>>8)&0xFF}.{version&0xFF}"
        result['compressed'] = bool(props & 0x01)
        result['encrypted'] = bool(props & 0x02)

        if result['encrypted']:
            logger.warning("HWP file is encrypted — cannot read content")
            result['texts'] = []
            result['paragraphs'] = []
            return result

        # 2. 스트림 목록
        result['streams'] = ['/'.join(s) for s in ole.listdir()]

        # 3. BinData 목록
        result['bindata'] = [s for s in result['streams'] if s.startswith('BinData/')]

        # 4. DocInfo 파싱 (폰트, CharShape, ParaShape)
        docinfo = _parse_docinfo(ole, result['compressed'])
        result['face_names'] = docinfo['face_names']
        result['char_shapes'] = docinfo['char_shapes']
        result['para_shapes'] = docinfo['para_shapes']
        result['font_counts'] = docinfo['font_counts']

        # 5. 섹션별 텍스트 + 표 추출
        all_texts = []
        all_paragraphs = []
        all_tables = []
        section_idx = 0
        while True:
            stream_name = f'BodyText/Section{section_idx}'
            if not ole.exists(stream_name):
                break

            raw = ole.openstream(stream_name).read()
            if result['compressed']:
                try:
                    data = zlib.decompress(raw, -15)
                except zlib.error:
                    data = zlib.decompress(raw)
            else:
                data = raw

            paragraphs = _parse_section_records(data, section_idx)
            for p in paragraphs:
                all_paragraphs.append(p)
                if p['text']:
                    all_texts.append(p['text'])

            # 표 추출
            records = _parse_records(data)
            tables = _extract_tables_from_records(records)
            all_tables.extend(tables)

            section_idx += 1

        result['section_count'] = section_idx
        result['texts'] = all_texts
        result['paragraphs'] = all_paragraphs
        result['tables'] = all_tables

        return result

    finally:
        ole.close()


def _parse_docinfo(ole, compressed: bool) -> dict:
    """DocInfo 스트림에서 폰트, CharShape, ParaShape 추출"""
    raw = ole.openstream('DocInfo').read()
    if compressed:
        try:
            data = zlib.decompress(raw, -15)
        except zlib.error:
            data = zlib.decompress(raw)
    else:
        data = raw

    # HWP DocInfo 태그 (HWPTAG_BEGIN = 16)
    TAG_ID_MAPPINGS = 17
    TAG_FACE_NAME = 19
    TAG_CHAR_SHAPE = 21
    TAG_PARA_SHAPE = 25

    font_counts = {}
    face_names = []
    char_shapes = []
    para_shapes = []

    pos = 0
    while pos < len(data):
        if pos + 4 > len(data):
            break
        header = struct.unpack_from('<I', data, pos)[0]
        tag_id = header & 0x3FF
        size = (header >> 20) & 0xFFF
        pos += 4
        if size == 0xFFF:
            if pos + 4 > len(data):
                break
            size = struct.unpack_from('<I', data, pos)[0]
            pos += 4
        if pos + size > len(data):
            break

        rec_data = data[pos:pos + size]

        if tag_id == TAG_ID_MAPPINGS:
            count_names = ['binData', 'hangulFont', 'englishFont', 'hanjaFont', 'japaneseFont',
                           'etcFont', 'symbolFont', 'userFont', 'borderFill', 'charShape',
                           'tabDef', 'numbering', 'bullet', 'paraShape', 'style', 'memoShape']
            for ci, cname in enumerate(count_names):
                if ci * 4 + 4 <= len(rec_data):
                    font_counts[cname] = struct.unpack_from('<I', rec_data, ci * 4)[0]

        elif tag_id == TAG_FACE_NAME and len(rec_data) >= 3:
            name_len = struct.unpack_from('<H', rec_data, 1)[0]
            if 3 + name_len * 2 <= len(rec_data):
                name = rec_data[3:3 + name_len * 2].decode('utf-16-le', errors='replace')
                face_names.append(name)

        elif tag_id == TAG_CHAR_SHAPE and len(rec_data) >= 54:
            hangul_font = struct.unpack_from('<H', rec_data, 0)[0]
            latin_font = struct.unpack_from('<H', rec_data, 2)[0]
            base_size = struct.unpack_from('<I', rec_data, 42)[0]
            prop = struct.unpack_from('<I', rec_data, 46)[0]
            text_color = struct.unpack_from('<I', rec_data, 50)[0]

            r = text_color & 0xFF
            g = (text_color >> 8) & 0xFF
            b = (text_color >> 16) & 0xFF

            char_shapes.append({
                'id': len(char_shapes),
                'height': base_size,
                'bold': bool(prop & 0x01),
                'italic': bool(prop & 0x02),
                'textColor': f'#{r:02X}{g:02X}{b:02X}',
                'hangul_font': hangul_font,
                'latin_font': latin_font,
            })

        elif tag_id == TAG_PARA_SHAPE and len(rec_data) >= 18:
            prop1 = struct.unpack_from('<I', rec_data, 0)[0]
            alignment = prop1 & 0x07
            left_margin = struct.unpack_from('<i', rec_data, 4)[0]
            right_margin = struct.unpack_from('<i', rec_data, 8)[0]
            indent = struct.unpack_from('<i', rec_data, 12)[0]
            line_spacing = struct.unpack_from('<i', rec_data, 24)[0] if len(rec_data) >= 28 else 0

            align_names = {0: 'JUSTIFY', 1: 'LEFT', 2: 'RIGHT', 3: 'CENTER',
                           4: 'DISTRIBUTE', 5: 'DISTRIBUTE_SPACE'}
            para_shapes.append({
                'id': len(para_shapes),
                'alignment': align_names.get(alignment, 'JUSTIFY'),
                'left_margin': left_margin,
                'right_margin': right_margin,
                'indent': indent,
                'line_spacing': line_spacing,
            })

        pos += size

    return {
        'face_names': face_names,
        'char_shapes': char_shapes,
        'para_shapes': para_shapes,
        'font_counts': font_counts,
    }


def _parse_records(data: bytes) -> list:
    """바이너리 데이터에서 HWP 레코드 리스트 추출"""
    records = []
    pos = 0
    while pos < len(data):
        if pos + 4 > len(data):
            break
        header = struct.unpack_from('<I', data, pos)[0]
        tag_id = header & 0x3FF
        level = (header >> 10) & 0x3FF
        size = (header >> 20) & 0xFFF
        pos += 4
        if size == 0xFFF:
            if pos + 4 > len(data):
                break
            size = struct.unpack_from('<I', data, pos)[0]
            pos += 4
        if pos + size > len(data):
            break
        records.append({
            'tag': tag_id, 'level': level, 'size': size,
            'data': data[pos:pos + size]
        })
        pos += size
    return records


def _extract_tables_from_records(records: list) -> list:
    """레코드 리스트에서 표 구조 추출

    HWP 표 구조:
    - PARA_TEXT에 ch=11 → 표 시작
    - 이후 LIST_HEADER(level+1) + CELL_DEF → 셀 시작
    - 셀 안 PARA_TEXT(level+2) → 셀 텍스트
    - level이 원래로 돌아오면 → 표 끝
    """
    tables = []

    # 1. 표 시작점 찾기 (PARA_TEXT에 ch=11)
    table_starts = []
    for i, r in enumerate(records):
        if r['tag'] == TAG_PARA_TEXT:
            j = 0
            while j < len(r['data']) - 1:
                ch = struct.unpack_from('<H', r['data'], j)[0]
                j += 2
                if ch == 11:  # table control
                    table_starts.append(i)
                    break
                elif 1 <= ch <= 23:
                    j += 14
                elif ch == 13:
                    break

    # 2. 각 표의 셀 추출
    TAG_CELL_DEF = 77
    for ti, start_idx in enumerate(table_starts):
        base_level = records[start_idx]['level']
        cells = []
        current_cell_texts = []
        in_cell = False
        expect_cell_def = False

        remaining = records[start_idx + 1:]
        for ri, r in enumerate(remaining):
            # 표 밖으로: base_level 미만의 PARA_HEADER
            if r['level'] < base_level and r['tag'] == TAG_PARA_HEADER:
                if in_cell and current_cell_texts:
                    cells.append({'text': '\n'.join(current_cell_texts)})
                break

            # LIST_HEADER 다음에 CELL_DEF가 오면 셀 시작
            if r['tag'] == TAG_LIST_HEADER and r['level'] >= base_level:
                # 다음 레코드가 CELL_DEF인지 확인
                next_r = remaining[ri + 1] if ri + 1 < len(remaining) else None
                if next_r and next_r['tag'] == TAG_CELL_DEF:
                    if in_cell and current_cell_texts:
                        cells.append({'text': '\n'.join(current_cell_texts)})
                    current_cell_texts = []
                    in_cell = True
                    continue

            # 셀 텍스트: PARA_TEXT at level > base_level
            if r['tag'] == TAG_PARA_TEXT and in_cell and r['level'] > base_level:
                text = _extract_text_from_record(r['data'])
                if text:
                    current_cell_texts.append(text)

        if in_cell and current_cell_texts:
            cells.append({'text': '\n'.join(current_cell_texts)})

        if cells:
            tables.append({'cells': cells, 'cell_count': len(cells)})

    return tables


def _parse_section_records(data: bytes, section_idx: int) -> list:
    """섹션 바이너리에서 레코드 파싱 → 단락 리스트"""
    paragraphs = []
    pos = 0
    current_para = None

    while pos < len(data):
        if pos + 4 > len(data):
            break
        header = struct.unpack_from('<I', data, pos)[0]
        tag_id = header & 0x3FF
        level = (header >> 10) & 0x3FF
        size = (header >> 20) & 0xFFF
        pos += 4

        if size == 0xFFF:
            if pos + 4 > len(data):
                break
            size = struct.unpack_from('<I', data, pos)[0]
            pos += 4

        if pos + size > len(data):
            break

        rec_data = data[pos:pos + size]

        if tag_id == TAG_PARA_HEADER:
            if current_para is not None:
                paragraphs.append(current_para)
            current_para = {
                'section': section_idx,
                'text': '',
                'char_shape_ids': [],
                'has_table': False,
                'has_ctrl': False,
            }
            # PARA_HEADER: nchars(4) + controlMask(4) + paraShapeID(2) + ...
            if len(rec_data) >= 10:
                current_para['nchars'] = struct.unpack_from('<I', rec_data, 0)[0]
                current_para['para_shape_id'] = struct.unpack_from('<H', rec_data, 8)[0]

        elif tag_id == TAG_PARA_TEXT and current_para is not None:
            text = _extract_text_from_record(rec_data)
            current_para['text'] = text
            # 표 제어 문자 감지 (ch=11)
            j = 0
            while j < len(rec_data) - 1:
                ch = struct.unpack_from('<H', rec_data, j)[0]
                j += 2
                if ch == 11:
                    current_para['has_table'] = True
                    break
                elif 1 <= ch <= 23:
                    j += 14
                elif ch == 13:
                    break

        elif tag_id == TAG_PARA_CHAR_SHAPE and current_para is not None:
            # charPrIDRef 매핑 (4바이트 position + 4바이트 charShapeID 쌍)
            shapes = []
            i = 0
            while i + 8 <= len(rec_data):
                char_pos = struct.unpack_from('<I', rec_data, i)[0]
                shape_id = struct.unpack_from('<I', rec_data, i + 4)[0]
                shapes.append({'pos': char_pos, 'shape_id': shape_id})
                i += 8
            current_para['char_shape_ids'] = shapes

        elif tag_id == TAG_TABLE:
            if current_para is not None:
                current_para['has_table'] = True

        elif tag_id == TAG_CTRL_HEADER:
            if current_para is not None:
                current_para['has_ctrl'] = True

        pos += size

    if current_para is not None:
        paragraphs.append(current_para)

    return paragraphs


def _extract_text_from_record(rec_data: bytes) -> str:
    """PARA_TEXT 레코드에서 텍스트 추출

    HWP PARA_TEXT: 2바이트(wchar) 단위
    - 0x0020 이상: 일반 문자
    - 0x0001~0x0008: 인라인 제어 (16바이트 확장)
    - 0x000A: 줄바꿈
    - 0x000D: 단락 끝
    """
    text = []
    i = 0
    while i < len(rec_data) - 1:
        ch = struct.unpack_from('<H', rec_data, i)[0]
        i += 2

        if ch >= 0x0020:
            text.append(chr(ch))
        elif ch == 0x000A:
            text.append('\n')
        elif ch == 0x000D:
            break
        elif 0x0001 <= ch <= 0x0008:
            # 인라인 제어: 8 wchar 확장 (총 16바이트, 이미 2 읽음)
            i += 14
        elif ch in (0x0009, 0x000B, 0x000C, 0x000E, 0x000F,
                    0x0010, 0x0011, 0x0012, 0x0013, 0x0014,
                    0x0015, 0x0016, 0x0017):
            # 기타 제어 문자: 8 wchar 확장
            i += 14

    return ''.join(text).strip()


def _build_header_xml(doc_data: dict) -> str:
    """HWP DocInfo에서 추출한 데이터로 HWPX header.xml 직접 생성"""
    face_names = doc_data.get('face_names', [])
    char_shapes = doc_data.get('char_shapes', [])
    para_shapes = doc_data.get('para_shapes', [])
    font_counts = doc_data.get('font_counts', {})

    # 언어별 폰트 분배
    hangul_cnt = font_counts.get('hangulFont', 0)
    latin_cnt = font_counts.get('englishFont', 0)
    hanja_cnt = font_counts.get('hanjaFont', 0)
    japanese_cnt = font_counts.get('japaneseFont', 0)
    etc_cnt = font_counts.get('etcFont', 0)
    symbol_cnt = font_counts.get('symbolFont', 0)
    user_cnt = font_counts.get('userFont', 0)

    # 폰트를 언어별로 분할
    offset = 0
    lang_fonts = {}
    for lang, cnt in [('HANGUL', hangul_cnt), ('LATIN', latin_cnt), ('HANJA', hanja_cnt),
                       ('JAPANESE', japanese_cnt), ('OTHER', etc_cnt),
                       ('SYMBOL', symbol_cnt), ('USER', user_cnt)]:
        lang_fonts[lang] = face_names[offset:offset + cnt]
        offset += cnt

    # fontfaces XML
    fontfaces_xml = '<hh:fontfaces>\n'
    for lang, fonts in lang_fonts.items():
        if fonts:
            fontfaces_xml += f'  <hh:fontface lang="{lang}">\n'
            for i, name in enumerate(fonts):
                fontfaces_xml += f'    <hh:font id="{i}" face="{name}" type="TTF" />\n'
            fontfaces_xml += '  </hh:fontface>\n'
    fontfaces_xml += '</hh:fontfaces>'

    # charProperties XML
    char_xml = f'<hh:charProperties itemCnt="{len(char_shapes)}">\n'
    for cs in char_shapes:
        height = cs['height']
        color = cs['textColor']
        hf = cs['hangul_font']
        lf = cs['latin_font']

        char_xml += f'  <hh:charPr id="{cs["id"]}" height="{height}" textColor="{color}">\n'
        char_xml += f'    <hh:fontRef hangul="{hf}" latin="{lf}" hanja="{hf}" japanese="{hf}" other="{hf}" symbol="{hf}" user="{hf}" />\n'
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
        char_xml += '  </hh:charPr>\n'
    char_xml += '</hh:charProperties>'

    # paraProperties XML
    para_xml = f'<hh:paraProperties itemCnt="{len(para_shapes)}">\n'
    for ps in para_shapes:
        alignment = ps['alignment']
        indent = ps.get('indent', 0)
        left = ps.get('left_margin', 0)
        right = ps.get('right_margin', 0)
        ls = ps.get('line_spacing', 160)

        para_xml += f'  <hh:paraPr id="{ps["id"]}" tabPrIDRef="0" condense="0" fontLineHeight="0" snapToGrid="1" suppressLineNumbers="0" checked="0">\n'
        para_xml += f'    <hh:align horizontal="{alignment}" vertical="BASELINE" />\n'
        para_xml += '    <hh:heading type="NONE" idRef="0" level="0" />\n'
        para_xml += '    <hh:breakSetting breakLatinWord="BREAK_WORD" breakNonLatinWord="KEEP_WORD" widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK" />\n'
        para_xml += '    <hh:autoSpacing eAsianEng="0" eAsianNum="0" />\n'
        para_xml += '    <hh:margin>\n'
        para_xml += f'      <hc:intent value="{indent}" unit="HWPUNIT" />\n'
        para_xml += f'      <hc:left value="{left}" unit="HWPUNIT" />\n'
        para_xml += f'      <hc:right value="{right}" unit="HWPUNIT" />\n'
        para_xml += '      <hc:prev value="0" unit="HWPUNIT" />\n'
        para_xml += '      <hc:next value="0" unit="HWPUNIT" />\n'
        para_xml += '    </hh:margin>\n'
        para_xml += f'    <hh:lineSpacing type="PERCENT" value="{ls}" unit="HWPUNIT" />\n'
        para_xml += '    <hh:border borderFillIDRef="1" offsetLeft="0" offsetRight="0" offsetTop="0" offsetBottom="0" connect="0" ignoreMargin="0" />\n'
        para_xml += '  </hh:paraPr>\n'
    para_xml += '</hh:paraProperties>'

    # borderFills (최소 1개 필요)
    border_xml = '<hh:borderFills itemCnt="1">\n'
    border_xml += '  <hh:borderFill id="1" threeD="0" shadow="0" slash="0" backSlash="0" cropCell="0" fillBrush="0">\n'
    border_xml += '    <hh:leftBorder type="NONE" width="0.1 mm" color="#000000" />\n'
    border_xml += '    <hh:rightBorder type="NONE" width="0.1 mm" color="#000000" />\n'
    border_xml += '    <hh:topBorder type="NONE" width="0.1 mm" color="#000000" />\n'
    border_xml += '    <hh:bottomBorder type="NONE" width="0.1 mm" color="#000000" />\n'
    border_xml += '  </hh:borderFill>\n'
    border_xml += '</hh:borderFills>'

    # 전체 header.xml 조립
    header = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"
         xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core"
         xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"
         version="1.4" secCnt="1">
  <hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1" />
  <hh:refList>
    {fontfaces_xml}
    {border_xml}
    {char_xml}
    {para_xml}
  </hh:refList>
  <hh:compatibleDocument targetProgram="HWP201X">
    <hh:layoutCompatibility />
  </hh:compatibleDocument>
</hh:head>'''

    return header


def hwp_to_hwpx(hwp_path: str, hwpx_path: str, max_paragraphs: int = 0) -> str:
    """HWP 5.x → HWPX 변환 (텍스트 기반, Phase A)

    Parameters
    ----------
    hwp_path : str
        입력 HWP 파일 경로
    hwpx_path : str
        출력 HWPX 파일 경로
    max_paragraphs : int
        최대 단락 수 (0=무제한)

    현재 지원:
    - 텍스트 추출 + HWPX 문서 생성
    - 단락 구조 보존

    미지원 (향후):
    - 표, 이미지, 도형
    - charPr/paraPr 스타일 매핑
    - 머리말/꼬리말
    """
    doc_data = read_hwp(hwp_path)

    if doc_data.get('encrypted'):
        raise ValueError("암호화된 HWP 파일은 변환할 수 없습니다.")

    import zipfile, shutil, tempfile

    # 1. pyhwpxlib로 기본 HWPX 생성 (정상 구조 보장)
    from .api import create_document, add_paragraph, add_table, save

    hwpx = create_document()
    count = 0
    table_idx = 0
    tables = doc_data.get('tables', [])

    for para in doc_data['paragraphs']:
        if para.get('has_table') and table_idx < len(tables):
            # 표 생성 — 셀 텍스트를 data 배열로 전달
            tbl = tables[table_idx]
            cells = tbl['cells']
            if cells:
                n_cells = len(cells)
                cell_data = [[c.get('text', '').replace('\n', ' ')[:100] for c in cells]]
                add_table(hwpx, 1, n_cells, data=cell_data)
            table_idx += 1
            count += 1
        elif para['text']:
            lines = para['text'].split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    add_paragraph(hwpx, line)
                    count += 1
                    if max_paragraphs and count >= max_paragraphs:
                        break
        if max_paragraphs and count >= max_paragraphs:
            break

    save(hwpx, hwpx_path)
    logger.info("HWP → HWPX 변환 완료: %s → %s (%d/%d 단락)",
                hwp_path, hwpx_path, count, len(doc_data['paragraphs']))
    return hwpx_path
