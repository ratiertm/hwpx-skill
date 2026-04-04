"""
서식 생성 파이프라인 — OWPML/HWPX 서식 리버스 → JSON → pyhwpxlib 재생성

Usage:
    python form_pipeline.py extract <input.hwpx|owpml> -o <output.json>
    python form_pipeline.py generate <input.json> -o <output.hwpx>
    python form_pipeline.py clone <input.hwpx|owpml> -o <output.hwpx>
"""
import zipfile, json, sys, os
import xml.etree.ElementTree as ET
from collections import defaultdict

_HP = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
_HH = "{http://www.hancom.co.kr/hwpml/2011/head}"
_HC = "{http://www.hancom.co.kr/hwpml/2011/core}"
_HS = "{http://www.hancom.co.kr/hwpml/2011/section}"


# ============================================================
# EXTRACT: HWPX/OWPML → JSON
# ============================================================

def extract_form(path):
    """서식 파일에서 재생성에 필요한 모든 구조 데이터 추출 — p 단위"""
    with zipfile.ZipFile(path) as z:
        header_xml = z.read('Contents/header.xml').decode('utf-8')
        section_xml = z.read('Contents/section0.xml').decode('utf-8')

    hroot = ET.fromstring(header_xml)
    sroot = ET.fromstring(section_xml)

    # paraPr 매핑 (셀 추출에 필요)
    ppr_map = _build_ppr_map(hroot)

    # p 단위 구조 추출
    paragraphs = []
    for p in sroot.findall(f'{_HP}p'):
        para = _extract_paragraph(p, ppr_map)
        paragraphs.append(para)

    # 원본 header에서 fontfaces/charProperties/borderFills를 raw 문자열로 추출
    # ET.tostring은 ns0: 접두사로 변환하므로, 원본 XML 문자열에서 직접 추출
    import re
    def _extract_raw_block(xml_str, tag_name):
        """원본 XML 문자열에서 <hh:tagName ...>...</hh:tagName> 블록 추출"""
        pattern = r'<[^>]*?' + tag_name + r'[^>]*>.*?</[^>]*?' + tag_name + r'>'
        match = re.search(pattern, xml_str, re.DOTALL)
        return match.group(0) if match else ''

    raw_fontfaces = _extract_raw_block(header_xml, 'fontfaces')
    raw_charProperties = _extract_raw_block(header_xml, 'charProperties')
    raw_borderFills = _extract_raw_block(header_xml, 'borderFills')
    raw_paraProperties = _extract_raw_block(header_xml, 'paraProperties')
    # 원본 header.xml 전체도 보존
    raw_header_xml = header_xml

    form = {
        '_source': os.path.basename(path),
        'page': _extract_page(sroot),
        'fonts': _extract_fonts(hroot),
        'char_properties': _extract_char_properties(hroot),
        'para_properties': _extract_para_properties(hroot),
        'border_fills': _extract_border_fills(hroot),
        'paragraphs': paragraphs,
        '_raw_fontfaces': raw_fontfaces,
        '_raw_charProperties': raw_charProperties,
        '_raw_borderFills': raw_borderFills,
        '_raw_paraProperties': raw_paraProperties,
        '_raw_header_xml': raw_header_xml,
        # 하위 호환: 기존 필드도 유지
        'tables': _extract_tables(sroot, hroot),
        'before_table_text': _extract_before_table_text(sroot),
        'p_count': len(paragraphs),
        'secpr_and_tbl_same_p': any(
            p.get('has_secpr') and p.get('has_table') for p in paragraphs
        ),
    }
    return form


def _extract_page(sroot):
    pp = sroot.find(f'.//{_HP}pagePr')
    margin = pp.find(f'{_HP}margin') if pp is not None else None
    return {
        'width': int(pp.get('width', 59528)),
        'height': int(pp.get('height', 84188)),
        'landscape': pp.get('landscape', 'WIDELY'),
        'margin': {
            'left': int(margin.get('left', 8504)),
            'right': int(margin.get('right', 8504)),
            'top': int(margin.get('top', 5668)),
            'bottom': int(margin.get('bottom', 4252)),
            'header': int(margin.get('header', 4252)),
            'footer': int(margin.get('footer', 4252)),
        } if margin is not None else {}
    }


def _extract_fonts(hroot):
    fonts = []
    for ff in hroot.findall(f'.//{_HH}fontface'):
        lang = ff.get('lang', '')
        for f in ff.findall(f'{_HH}font'):
            fonts.append({'lang': lang, 'id': f.get('id'), 'face': f.get('face')})
    # 고유 폰트만
    unique = list({f['face'] for f in fonts})
    return unique


def _extract_char_properties(hroot):
    result = {}
    for cp in hroot.findall(f'.//{_HH}charPr'):
        cid = cp.get('id')
        bold = any(c.tag.endswith('bold') for c in cp)
        italic = any(c.tag.endswith('italic') for c in cp)
        sp_el = cp.find(f'.//{_HH}spacing')
        spacing = int(sp_el.get('hangul', '0')) if sp_el is not None else 0
        result[cid] = {
            'height': int(cp.get('height', 1000)),
            'textColor': cp.get('textColor', '#000000'),
            'bold': bold,
            'italic': italic,
            'spacing': spacing,
        }
    return result


def _extract_para_properties(hroot):
    result = {}
    for pp in hroot.findall(f'.//{_HH}paraPr'):
        pid = pp.get('id')
        align = pp.find(f'{_HH}align')
        # lineSpacing: 직계 또는 switch 안에 있을 수 있음
        ls = pp.find(f'{_HH}lineSpacing')
        if ls is None:
            ls = pp.find(f'.//{_HH}lineSpacing')  # switch 안 탐색
        margin = pp.find(f'{_HH}margin')
        if margin is None:
            margin = pp.find(f'.//{_HH}margin')  # switch 안 탐색

        info = {
            'horizontal': align.get('horizontal', 'JUSTIFY') if align is not None else 'JUSTIFY',
            'lineSpacing': int(ls.get('value', 0)) if ls is not None else 0,
        }

        if margin is not None:
            for ch in margin:
                tag = ch.tag.split('}')[1] if '}' in ch.tag else ch.tag
                val = int(ch.get('value', '0'))
                if val != 0:
                    info[f'margin_{tag}'] = val

        result[pid] = info
    return result


def _extract_border_fills(hroot):
    result = {}
    for bf in hroot.findall(f'.//{_HH}borderFill'):
        bfid = bf.get('id')
        borders = {}
        for side in ['leftBorder', 'rightBorder', 'topBorder', 'bottomBorder']:
            b = bf.find(f'{_HH}{side}')
            if b is not None:
                borders[side] = {
                    'type': b.get('type', 'NONE'),
                    'width': b.get('width', '0.1 mm'),
                    'color': b.get('color', '#000000'),
                }
        # fillColor 추출
        wb = bf.find(f'.//{_HC}winBrush')
        if wb is not None:
            fc = wb.get('faceColor', '')
            if fc and fc != 'none':
                borders['_fillColor'] = fc
                borders['_hatchColor'] = wb.get('hatchColor', '#000000')
                borders['_alpha'] = wb.get('alpha', '0')
        result[bfid] = borders
    return result


def _build_ppr_map(hroot):
    """paraPr id → 정보 매핑"""
    ppr_map = {}
    for pp in hroot.findall(f'.//{_HH}paraPr'):
        pid = pp.get('id')
        a = pp.find(f'{_HH}align')
        ls = pp.find(f'{_HH}lineSpacing')
        if ls is None:
            ls = pp.find(f'.//{_HH}lineSpacing')
        m = pp.find(f'{_HH}margin')
        if m is None:
            m = pp.find(f'.//{_HH}margin')
        info = {'horizontal': a.get('horizontal', 'JUSTIFY') if a is not None else 'JUSTIFY'}
        if ls is not None:
            info['lineSpacing'] = int(ls.get('value', 0))
        if m is not None:
            for ch in m:
                tag = ch.tag.split('}')[1] if '}' in ch.tag else ch.tag
                val = int(ch.get('value', '0'))
                if val != 0:
                    info[f'margin_{tag}'] = val
        ppr_map[pid] = info
    return ppr_map


def _extract_paragraph(p, ppr_map):
    """단일 p의 전체 구조 추출"""
    has_secpr = p.find(f'.//{_HP}secPr') is not None
    ppr_id = p.get('paraPrIDRef', '0')

    # run별 내용 추출
    runs = []
    for run in p.findall(f'{_HP}run'):
        cpr = run.get('charPrIDRef', '0')
        run_data = {'charPrIDRef': cpr, 'contents': []}

        for ch in run:
            tag = ch.tag.split('}')[1] if '}' in ch.tag else ch.tag

            if tag == 't':
                txt = ch.text if ch.text else ''
                run_data['contents'].append({'type': 'text', 'text': txt})

            elif tag == 'tbl':
                tbl_data = _extract_single_table(ch, ppr_map)
                run_data['contents'].append({'type': 'table', 'table': tbl_data})

            elif tag == 'secPr':
                run_data['contents'].append({'type': 'secPr'})

            elif tag == 'ctrl':
                run_data['contents'].append({'type': 'ctrl'})
            # linesegarray, 기타는 스킵 (한컴 자동 생성)

        runs.append(run_data)

    # 표 포함 여부
    has_table = any(
        c['type'] == 'table'
        for r in runs for c in r['contents']
    )
    # 텍스트 추출
    texts = []
    for r in runs:
        for c in r['contents']:
            if c['type'] == 'text' and c['text'].strip():
                texts.append(c['text'])

    return {
        'paraPrIDRef': ppr_id,
        'has_secpr': has_secpr,
        'has_table': has_table,
        'texts': texts,
        'runs': runs,
    }


def _extract_single_table(tbl, ppr_map):
    """단일 표(중첩 포함) 추출 — 재귀"""
    rows = int(tbl.get('rowCnt', 0))
    cols = int(tbl.get('colCnt', 0))
    sz = tbl.find(f'{_HP}sz')
    tw = int(sz.get('width', 0)) if sz is not None else 0
    th = int(sz.get('height', 0)) if sz is not None else 0

    om = tbl.find(f'{_HP}outMargin')
    im = tbl.find(f'{_HP}inMargin')
    pos = tbl.find(f'{_HP}pos')

    # 직계 셀만 추출 (tr > tc)
    cells = []
    for tr in tbl.findall(f'{_HP}tr'):
        for tc in tr.findall(f'{_HP}tc'):
            cell = _extract_cell(tc, ppr_map)
            cells.append(cell)

    # 그리드 역산
    col_widths, row_heights = _reverse_grid(cells, cols, rows)

    # 병합 추출
    merges = _extract_merges(cells)

    return {
        'rows': rows, 'cols': cols,
        'width': tw, 'height': th,
        'col_widths': col_widths,
        'row_heights': row_heights,
        'outMargin': int(om.get('left', 0)) if om is not None else 0,
        'inMargin': int(im.get('left', 0)) if im is not None else 0,
        'pos': dict(pos.attrib) if pos is not None else {},
        'borderFillIDRef': tbl.get('borderFillIDRef', '1'),
        'pageBreak': tbl.get('pageBreak', 'CELL'),
        'cells': cells,
        'merges': merges,
    }


def _extract_before_table_text(sroot):
    """표 앞에 있는 텍스트 추출 + p 구조 정보"""
    texts = []
    # secPr과 표가 같은 p에 있는지 확인
    secpr_has_table = False
    for p in sroot.findall(f'{_HP}p'):
        has_secpr = p.find(f'.//{_HP}secPr') is not None
        has_tbl = p.find(f'.//{_HP}tbl') is not None
        if has_secpr and has_tbl:
            secpr_has_table = True
            # secPr p 안의 텍스트도 추출 (표 앞에 있는 run)
            for run in p.findall(f'{_HP}run'):
                if run.find(f'{_HP}tbl') is not None:
                    break
                t = run.find(f'{_HP}t')
                if t is not None and t.text and t.text.strip():
                    texts.append(t.text)
            break
        if has_tbl:
            break
        if has_secpr:
            # secPr p 안의 텍스트
            for run in p.findall(f'{_HP}run'):
                t = run.find(f'{_HP}t')
                if t is not None and t.text and t.text.strip():
                    texts.append(t.text)
            continue
        # secPr 없는 표 앞 p
        for run in p.findall(f'{_HP}run'):
            t = run.find(f'{_HP}t')
            if t is not None and t.text and t.text.strip():
                texts.append(t.text)
    return texts


def _extract_tables(sroot, hroot):
    # paraPr 매핑
    ppr_map = {}
    for pp in hroot.findall(f'.//{_HH}paraPr'):
        pid = pp.get('id')
        a = pp.find(f'{_HH}align')
        ls = pp.find(f'{_HH}lineSpacing')
        m = pp.find(f'{_HH}margin')
        info = {'horizontal': a.get('horizontal', 'JUSTIFY') if a is not None else 'JUSTIFY'}
        if ls is not None:
            info['lineSpacing'] = int(ls.get('value', 150))
        if m is not None:
            for ch in m:
                tag = ch.tag.split('}')[1] if '}' in ch.tag else ch.tag
                val = int(ch.get('value', '0'))
                if val != 0:
                    info[f'margin_{tag}'] = val
        ppr_map[pid] = info

    tables = []
    for tbl in sroot.findall(f'.//{_HP}tbl'):
        rows = int(tbl.get('rowCnt', 0))
        cols = int(tbl.get('colCnt', 0))
        sz = tbl.find(f'{_HP}sz')
        tw = int(sz.get('width', 0))
        th = int(sz.get('height', 0))

        om = tbl.find(f'{_HP}outMargin')
        im = tbl.find(f'{_HP}inMargin')
        pos = tbl.find(f'{_HP}pos')

        # 표 pos 속성 보존
        pos_attrs = dict(pos.attrib) if pos is not None else {}

        # 표 감싸는 p의 paraPrIDRef
        tbl_p_paraPrIDRef = None
        for p in sroot.findall(f'{_HP}p'):
            if p.find(f'.//{_HP}tbl') is not None:
                tbl_p_paraPrIDRef = p.get('paraPrIDRef')
                break

        # 셀 추출
        cells = []
        for tc in tbl.findall(f'.//{_HP}tc'):
            cells.append(_extract_cell(tc, ppr_map))

        # 그리드 역산
        col_widths, row_heights = _reverse_grid(cells, cols, rows)

        # 병합 추출
        merges = _extract_merges(cells)

        table_info = {
            'rows': rows, 'cols': cols,
            'width': tw, 'height': th,
            'col_widths': col_widths,
            'row_heights': row_heights,
            'outMargin': int(om.get('left', 0)) if om is not None else 0,
            'inMargin': int(im.get('left', 0)) if im is not None else 0,
            'pos': pos_attrs,
            'tbl_p_paraPrIDRef': tbl_p_paraPrIDRef,
            'cells': cells,
            'merges': merges,
        }
        tables.append(table_info)

    return tables


def _extract_cell(tc, ppr_map):
    addr = tc.find(f'{_HP}cellAddr')
    span = tc.find(f'{_HP}cellSpan')
    csz = tc.find(f'{_HP}cellSz')
    cm = tc.find(f'{_HP}cellMargin')
    sub = tc.find(f'{_HP}subList')

    r = int(addr.get('rowAddr', 0))
    c = int(addr.get('colAddr', 0))
    cs = int(span.get('colSpan', 1))
    rs = int(span.get('rowSpan', 1))
    w = int(csz.get('width', 0))
    h = int(csz.get('height', 0))

    vert_align = sub.get('vertAlign', 'CENTER') if sub is not None else 'CENTER'
    bf = tc.get('borderFillIDRef', '1')
    has_margin = tc.get('hasMargin', '0')
    cell_margin = int(cm.get('left', 141)) if cm is not None else 141

    # 줄별 정보 (paraPr + charPr + text + 중첩 표)
    # 중첩 표는 해당 line에 포함 (순서 보존)
    lines = []
    nested_tables = []  # 하위 호환
    if sub is not None:
        for p in sub.findall(f'{_HP}p'):
            ppr = p.get('paraPrIDRef', '0')
            ppr_info = ppr_map.get(ppr, {'horizontal': 'JUSTIFY'})

            runs_data = []
            line_nested = []
            for run in p.findall(f'{_HP}run'):
                cpr = run.get('charPrIDRef', '0')
                t = run.find(f'{_HP}t')
                txt = t.text if t is not None and t.text else ''
                runs_data.append({'charPr': cpr, 'text': txt})

                # 중첩 표 추출 (재귀) — 이 line에 포함
                for ntbl in run.findall(f'{_HP}tbl'):
                    ntbl_data = _extract_single_table(ntbl, ppr_map)
                    line_nested.append(ntbl_data)
                    nested_tables.append(ntbl_data)

            lines.append({
                'paraPr': ppr,
                'horizontal': ppr_info.get('horizontal', 'JUSTIFY'),
                'lineSpacing': ppr_info.get('lineSpacing', 0),
                'margin_left': ppr_info.get('margin_left', 0),
                'margin_right': ppr_info.get('margin_right', 0),
                'margin_prev': ppr_info.get('margin_prev', 0),
                'margin_next': ppr_info.get('margin_next', 0),
                'runs': runs_data,
                'nested_tables': line_nested,
            })

    return {
        'row': r, 'col': c, 'colSpan': cs, 'rowSpan': rs,
        'width': w, 'height': h,
        'vertAlign': vert_align,
        'borderFillIDRef': bf,
        'cellMargin': cell_margin,
        'lines': lines,
        'nested_tables': nested_tables,
    }


def _reverse_grid(cells, col_count, row_count):
    """연립방정식으로 컬럼/행 그리드 역산"""
    col_widths = [None] * col_count
    row_heights = [None] * row_count

    w_eq = [(c['col'], c['col'] + c['colSpan'], c['width']) for c in cells]
    h_eq = [(c['row'], c['row'] + c['rowSpan'], c['height']) for c in cells]

    for s, e, w in w_eq:
        if e - s == 1 and s < col_count:
            col_widths[s] = w
    changed = True
    while changed:
        changed = False
        for s, e, w in w_eq:
            if e > col_count: continue
            unknowns = [i for i in range(s, e) if col_widths[i] is None]
            knowns = sum(col_widths[i] for i in range(s, e) if col_widths[i] is not None)
            if len(unknowns) == 1:
                col_widths[unknowns[0]] = w - knowns
                changed = True

    for s, e, h in h_eq:
        if e - s == 1 and s < row_count:
            row_heights[s] = h
    changed = True
    while changed:
        changed = False
        for s, e, h in h_eq:
            if e > row_count: continue
            unknowns = [i for i in range(s, e) if row_heights[i] is None]
            knowns = sum(row_heights[i] for i in range(s, e) if row_heights[i] is not None)
            if len(unknowns) == 1:
                row_heights[unknowns[0]] = h - knowns
                changed = True

    return col_widths, row_heights


def _extract_merges(cells):
    """span > 1인 셀에서 병합 정보 추출"""
    merges = []
    for c in cells:
        if c['colSpan'] > 1 or c['rowSpan'] > 1:
            merges.append({
                'r1': c['row'], 'c1': c['col'],
                'r2': c['row'] + c['rowSpan'] - 1,
                'c2': c['col'] + c['colSpan'] - 1,
            })
    return merges


# ============================================================
# GENERATE: JSON → HWPX (pyhwpxlib API)
# ============================================================

def generate_form(form_data, output_path):
    """JSON 구조 데이터로부터 pyhwpxlib API로 HWPX 생성"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ratiertm-hwpx', 'src'))
    from hwpx import HwpxDocument
    try:
        from lxml import etree as LET
    except ImportError:
        import xml.etree.ElementTree as LET

    doc = HwpxDocument.new()
    sec = doc.sections[0]
    header = doc.headers[0]

    # 1. 페이지 설정
    pg = form_data['page']
    m = pg['margin']
    sec.properties.set_page_margins(
        left=m['left'], right=m['right'],
        top=m['top'], bottom=m['bottom'],
        header=m.get('header', 4252), footer=m.get('footer', 4252)
    )

    # 2. fontfaces + charProperties + borderFills: 원본 XML 통째 교체
    raw_ff = form_data.get('_raw_fontfaces', '')
    raw_cp = form_data.get('_raw_charProperties', '')
    raw_bf = form_data.get('_raw_borderFills', '')
    _use_raw_header = bool(raw_ff and raw_cp and raw_bf)

    if _use_raw_header:
        # 원본 id = 클론 id (동일 매핑) — 실제 XML 교체는 save 후 regex로
        cpr_map = {orig_id: int(orig_id) for orig_id in form_data['char_properties']}
        bf_map = {orig_id: orig_id for orig_id in form_data['border_fills']}
    else:
        # fallback: ensure_run_style로 charPr 개별 생성
        cpr_map = {}
        bf_map = {}
        for orig_id, cp in form_data['char_properties'].items():
            sp = cp.get('spacing', 0)
            sp_kwargs = {}
            if sp != 0:
                for lang in ['hangul', 'latin', 'hanja', 'japanese', 'other', 'symbol', 'user']:
                    sp_kwargs[f'spacing_{lang}'] = sp
            new_id = doc.ensure_run_style(
                bold=cp.get('bold', False),
                height=cp.get('height', 1000),
                **sp_kwargs
            )
            cpr_map[orig_id] = new_id

    # 3. paraPr 생성 — 기존 paraPr[0]을 복제한 후 horizontal/margin만 변경
    pp_container = header.element.find(f".//{_HH}paraProperties")
    existing_pp = {pp.get("id") for pp in pp_container.findall(f"{_HH}paraPr")}
    next_pp_id = max(int(i) for i in existing_pp) + 1 if existing_pp else 0

    # 기본 paraPr[0] 템플릿 찾기 (복제 원본)
    base_pp = None
    for pp in pp_container.findall(f"{_HH}paraPr"):
        if pp.get("id") == "0":
            base_pp = pp
            break

    ppr_map = {}  # 키 = (horizontal, lineSpacing, ml, mr, mp, mn) → 새 id

    import copy

    def get_or_create_paraPr(horz, ls=0, ml=0, mr=0, mp=0, mn=0):
        key = (horz, ls, ml, mr, mp, mn)
        if key in ppr_map:
            return ppr_map[key]

        # 기존 paraPr 중 모든 조건 일치하는 게 있으면 재사용
        if ml == 0 and mr == 0 and mp == 0 and mn == 0:
            for pp in pp_container.findall(f"{_HH}paraPr"):
                a = pp.find(f"{_HH}align")
                if a is not None and a.get("horizontal") == horz:
                    pp_ls = pp.find(f'.//{_HH}lineSpacing')
                    pp_ls_val = int(pp_ls.get('value', 0)) if pp_ls is not None else 0
                    if pp_ls_val == ls or (ls == 0 and pp_ls_val == 0):
                        ppr_map[key] = pp.get("id")
                        return pp.get("id")

        nonlocal next_pp_id
        pid = str(next_pp_id)

        # paraPr[0] 전체를 deep copy한 후 horizontal + lineSpacing 변경
        if base_pp is not None:
            new_pp = copy.deepcopy(base_pp)
            new_pp.set("id", pid)
            a = new_pp.find(f"{_HH}align")
            if a is not None:
                a.set("horizontal", horz)
            # lineSpacing 변경
            if ls > 0:
                for ls_el in new_pp.findall(f'.//{_HH}lineSpacing'):
                    ls_el.set("value", str(ls))
            # margin 변경 (필요시)
            if ml or mr or mp or mn:
                # switch 내부와 default 내부 모두 margin 수정
                for margin_el in new_pp.findall(f".//{_HH}margin"):
                    for tag, val in [("left", ml), ("right", mr), ("prev", mp), ("next", mn)]:
                        if val:
                            el = margin_el.find(f".//{_HC}{tag}")
                            if el is None:
                                el = margin_el.find(f".//{_HH}{tag}")
                            if el is not None:
                                el.set("value", str(val))
            pp_container.append(new_pp)
        else:
            # fallback: 최소 구조
            pp_el = LET.SubElement(pp_container, f"{_HH}paraPr")
            pp_el.set("id", pid)
            pp_el.set("tabPrIDRef", "0")
            pp_el.set("condense", "0")
            a = LET.SubElement(pp_el, f"{_HH}align")
            a.set("horizontal", horz)
            a.set("vertical", "BASELINE")

        ppr_map[key] = pid
        next_pp_id += 1
        return pid

    # 4. borderFill 생성 (raw로 이미 교체된 경우 스킵)
    bf_container = header.element.find(f".//{_HH}borderFills")
    existing_bf = set(bf.get("id") for bf in bf_container.findall(f"{_HH}borderFill"))
    next_bf = max(int(i) for i in existing_bf) + 1 if existing_bf else 2

    for orig_id, borders in form_data['border_fills'].items():
        if _use_raw_header:
            continue
        # 기본 borderFill(id=1 NONE)은 스킵
        if all(b.get('type') == 'NONE' for b in borders.values()):
            bf_map[orig_id] = '1'  # 기존 NONE bf 사용
            continue

        bid = str(next_bf)
        bf_map[orig_id] = bid
        bf_el = LET.SubElement(bf_container, f"{_HH}borderFill")
        bf_el.set("id", bid)
        bf_el.set("threeD", "0")
        bf_el.set("shadow", "0")
        bf_el.set("centerLine", "NONE")
        bf_el.set("breakCellSeparateLine", "0")
        LET.SubElement(bf_el, f"{_HH}slash").attrib.update(
            {"type": "NONE", "Crooked": "0", "isCounter": "0"})
        LET.SubElement(bf_el, f"{_HH}backSlash").attrib.update(
            {"type": "NONE", "Crooked": "0", "isCounter": "0"})
        for side in ['leftBorder', 'rightBorder', 'topBorder', 'bottomBorder']:
            b = borders.get(side, {'type': 'NONE', 'width': '0.1 mm', 'color': '#000000'})
            LET.SubElement(bf_el, f"{_HH}{side}").attrib.update(
                {"type": b['type'], "width": b['width'], "color": b['color']})
        LET.SubElement(bf_el, f"{_HH}diagonal").attrib.update(
            {"type": "SOLID", "width": "0.12 mm", "color": "#000000"})
        # fillColor 적용
        fill_color = borders.get('_fillColor')
        if fill_color:
            fb = LET.SubElement(bf_el, f"{_HC}fillBrush")
            wb = LET.SubElement(fb, f"{_HC}winBrush")
            wb.set("faceColor", fill_color)
            wb.set("hatchColor", borders.get('_hatchColor', '#000000'))
            wb.set("alpha", borders.get('_alpha', '0'))
        next_bf += 1
    bf_container.set("itemCnt", str(len(bf_container)))

    # 5. p 단위 생성 (paragraphs 기반)
    paragraphs = form_data.get('paragraphs', [])

    if paragraphs:
        _generate_from_paragraphs(doc, sec, paragraphs, cpr_map, bf_map,
                                  get_or_create_paraPr, form_data)
    else:
        # 하위 호환: 기존 tables + before_table_text 방식
        before_texts = form_data.get('before_table_text', [])
        if before_texts:
            default_cpr = cpr_map.get('4', cpr_map.get('0', 0))
            for text in before_texts:
                doc.add_paragraph(text, char_pr_id_ref=default_cpr)
        for tbl_data in form_data['tables']:
            _generate_table(doc, tbl_data, cpr_map, bf_map, get_or_create_paraPr)

    # paraPr itemCnt 업데이트
    pp_container.set("itemCnt", str(len(pp_container)))

    doc.save_to_path(output_path)

    # save_to_path가 header를 재생성하므로, fontfaces/charProperties/borderFills만 원본으로 교체
    if _use_raw_header:
        import shutil, tempfile, re
        tmp = tempfile.mktemp(suffix='.hwpx')
        shutil.copy2(output_path, tmp)

        with zipfile.ZipFile(tmp, 'r') as zin:
            saved_header = zin.read('Contents/header.xml').decode('utf-8')

        for tag_name, raw_xml in [('fontfaces', raw_ff), ('charProperties', raw_cp), ('borderFills', raw_bf)]:
            pattern = r'<[^>]*?' + tag_name + r'[^>]*>.*?</[^>]*?' + tag_name + r'>'
            match = re.search(pattern, saved_header, re.DOTALL)
            if match:
                saved_header = saved_header[:match.start()] + raw_xml + saved_header[match.end():]

        # paraPr의 border borderFillIDRef를 "1"(NONE)로 변경 — 글자 박스 방지
        saved_header = re.sub(
            r'(<[^>]*?border[^>]*borderFillIDRef=")[^"]*(")',
            r'\g<1>1\2',
            saved_header
        )

        with zipfile.ZipFile(tmp, 'r') as zin, zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.namelist():
                if item == 'Contents/header.xml':
                    zout.writestr(item, saved_header)
                else:
                    zout.writestr(item, zin.read(item))
        os.remove(tmp)

    return output_path


def _generate_from_paragraphs(doc, sec, paragraphs, cpr_map, bf_map,
                               get_or_create_paraPr, form_data):
    """p 단위로 원본 구조를 재생성 — 다중 페이지/다중 표 지원"""
    try:
        from lxml import etree as LET
    except ImportError:
        import xml.etree.ElementTree as LET

    section_el = sec.element if hasattr(sec, 'element') else sec._element

    # pyhwpxlib가 만든 기본 secPr p 찾기
    base_secpr_p = None
    for p in list(section_el.findall(f'{_HP}p')):
        if p.find(f'.//{_HP}secPr') is not None:
            base_secpr_p = p
            break

    # 첫 번째 p(secPr 포함)는 이미 존재 — 나머지 p의 내용을 추가
    first_para = True
    for para_data in paragraphs:
        if para_data['has_secpr'] and first_para:
            # secPr p는 이미 존재 — 여기에 텍스트/표 run 추가
            target_p = base_secpr_p
            first_para = False

            if target_p is None:
                continue

            # 원본 paraPrIDRef 적용
            orig_ppr = para_data.get('paraPrIDRef', '0')
            orig_pp_info = form_data['para_properties'].get(orig_ppr, {})
            horz = orig_pp_info.get('horizontal', 'JUSTIFY')
            ls = orig_pp_info.get('lineSpacing', 0)
            ml = orig_pp_info.get('margin_left', 0)
            mr = orig_pp_info.get('margin_right', 0)
            ppid = get_or_create_paraPr(horz, ls, ml, mr)
            target_p.set('paraPrIDRef', ppid)

            # run 내용 추가 (secPr/ctrl 제외, 텍스트/표만)
            for run_data in para_data['runs']:
                new_cpr = cpr_map.get(run_data['charPrIDRef'], 0)
                for content in run_data['contents']:
                    if content['type'] == 'text' and content['text'].strip():
                        run = LET.SubElement(target_p, f'{_HP}run')
                        run.set('charPrIDRef', str(new_cpr))
                        t = LET.SubElement(run, f'{_HP}t')
                        t.text = content['text']
                    elif content['type'] == 'table':
                        # 표를 add_table로 생성 후 secPr p로 이동
                        tbl_data = content['table']
                        _generate_table(doc, tbl_data, cpr_map, bf_map, get_or_create_paraPr)
                        # 방금 생성된 표 p를 찾아서 secPr p로 이동
                        for p in list(section_el.findall(f'{_HP}p')):
                            if p is not target_p and p.find(f'.//{_HP}tbl') is not None:
                                for run in list(p.findall(f'{_HP}run')):
                                    p.remove(run)
                                    target_p.append(run)
                                section_el.remove(p)
                                break

        elif para_data['has_table']:
            # 표 포함 p — 표 생성
            for run_data in para_data['runs']:
                for content in run_data['contents']:
                    if content['type'] == 'table':
                        tbl_data = content['table']
                        _generate_table(doc, tbl_data, cpr_map, bf_map, get_or_create_paraPr)

                        # 표를 감싸는 p의 paraPrIDRef 설정
                        orig_ppr = para_data.get('paraPrIDRef', '0')
                        orig_pp_info = form_data['para_properties'].get(orig_ppr, {})
                        horz = orig_pp_info.get('horizontal', 'JUSTIFY')
                        ls = orig_pp_info.get('lineSpacing', 0)
                        ml = orig_pp_info.get('margin_left', 0)
                        mr = orig_pp_info.get('margin_right', 0)
                        ppid = get_or_create_paraPr(horz, ls, ml, mr)

                        # 마지막으로 추가된 표 p 찾아서 paraPrIDRef 설정
                        for p in reversed(list(section_el.findall(f'{_HP}p'))):
                            if p.find(f'.//{_HP}tbl') is not None:
                                p.set('paraPrIDRef', ppid)
                                break

            first_para = False

        elif para_data['texts']:
            # 텍스트 전용 p
            default_cpr = cpr_map.get(
                para_data['runs'][0]['charPrIDRef'] if para_data['runs'] else '0', 0)
            for text in para_data['texts']:
                doc.add_paragraph(text, char_pr_id_ref=default_cpr)

            # paraPrIDRef 설정
            orig_ppr = para_data.get('paraPrIDRef', '0')
            orig_pp_info = form_data['para_properties'].get(orig_ppr, {})
            horz = orig_pp_info.get('horizontal', 'JUSTIFY')
            ls = orig_pp_info.get('lineSpacing', 0)
            ppid = get_or_create_paraPr(horz, ls)
            # 마지막 추가된 p에 적용
            last_p = list(section_el.findall(f'{_HP}p'))[-1]
            last_p.set('paraPrIDRef', ppid)

            first_para = False

        else:
            # 빈 p (구분선 등)
            if not first_para:
                doc.add_paragraph("")
            first_para = False


def _generate_table(doc, tbl, cpr_map, bf_map, get_or_create_paraPr):
    """단일 표 생성"""
    rows = tbl['rows']
    cols = tbl['cols']
    tw = tbl['width']
    th = tbl['height']
    col_widths = tbl['col_widths']
    row_heights = tbl['row_heights']
    out_margin = tbl.get('outMargin', 140)
    in_margin = tbl.get('inMargin', 140)

    table = doc.add_table(rows, cols, width=tw)

    # 표 pos 속성 원본값 복원
    orig_pos = tbl.get('pos', {})
    if orig_pos:
        pos_el = table.element.find(f"{_HP}pos")
        if pos_el is not None:
            for k, v in orig_pos.items():
                pos_el.set(k, v)

    # 표 크기
    sz_el = table.element.find(f"{_HP}sz")
    sz_el.set("width", str(tw))
    sz_el.set("height", str(th))

    # 표 마진
    table.set_in_margin(left=in_margin, right=in_margin, top=in_margin, bottom=in_margin)
    om = table.element.find(f"{_HP}outMargin")
    if om is not None:
        for k in ["left", "right", "top", "bottom"]:
            om.set(k, str(out_margin))

    # 셀 크기 + 마진
    for r in range(rows):
        for c in range(cols):
            try:
                cell = table.cell(r, c)
                cw = col_widths[c] if c < len(col_widths) and col_widths[c] is not None else tw // cols
                rh = row_heights[r] if r < len(row_heights) and row_heights[r] is not None else 3600
                cell.set_size(width=cw, height=rh)
                cm = tbl['cells'][0].get('cellMargin', 141) if tbl['cells'] else 141
                cell.set_margin(left=cm, right=cm, top=cm, bottom=cm)
            except Exception:
                pass

    # 셀 텍스트 + 스타일 (set_cell_text 사용)
    for cell_data in tbl['cells']:
        r, c = cell_data['row'], cell_data['col']

        # 범위 체크 (중첩 표 등에서 선언된 크기 초과하는 셀 스킵)
        if r >= rows or c >= cols:
            continue

        # 셀 텍스트 + charPr — 직접 p/run 구성 (run 단위 charPr 보존)
        try:
            from lxml import etree as LET3
        except ImportError:
            import xml.etree.ElementTree as LET3

        # 중첩 표 유무 + 다중 run 유무 판단
        has_nested = any(line.get('nested_tables') for line in cell_data['lines'])
        has_multi_run = any(len(line.get('runs', [])) > 1 for line in cell_data['lines'])

        if has_multi_run or has_nested:
            # 다중 run 또는 중첩 표 — 모든 line을 순서대로 직접 p/run 구성
            try:
                from lxml import etree as LET3
            except ImportError:
                import xml.etree.ElementTree as LET3

            cell = table.cell(r, c)
            sub = cell.element.find(f"{_HP}subList")
            if sub is not None:
                for old_p in list(sub.findall(f"{_HP}p")):
                    sub.remove(old_p)

                for line in cell_data['lines']:
                    if line.get('nested_tables'):
                        # 중첩 표 line — 표 생성 후 여기에 삽입 (마커 p)
                        marker_p = LET3.SubElement(sub, f"{_HP}p")
                        marker_p.set("id", "0"); marker_p.set("paraPrIDRef", "0")
                        marker_p.set("styleIDRef", "0"); marker_p.set("pageBreak", "0")
                        marker_p.set("columnBreak", "0"); marker_p.set("merged", "0")
                        marker_p.set("_nested_marker", "1")  # 나중에 표로 교체
                    else:
                        new_p = LET3.SubElement(sub, f"{_HP}p")
                        new_p.set("id", "0"); new_p.set("paraPrIDRef", "0")
                        new_p.set("styleIDRef", "0"); new_p.set("pageBreak", "0")
                        new_p.set("columnBreak", "0"); new_p.set("merged", "0")
                        for run_data in line.get('runs', []):
                            new_cpr = cpr_map.get(run_data.get('charPr', '0'), 0)
                            new_run = LET3.SubElement(new_p, f"{_HP}run")
                            new_run.set("charPrIDRef", str(new_cpr))
                            t_el = LET3.SubElement(new_run, f"{_HP}t")
                            t_el.text = run_data.get('text', '') or None
        else:
            # 단일 run + 중첩 표 없음 — set_cell_text 사용 (안정적)
            text_parts = []
            for line in cell_data['lines']:
                line_text = ''.join(run['text'] for run in line['runs'])
                text_parts.append(line_text)
            full_text = '\n'.join(text_parts)
            if full_text.strip():
                try:
                    table.set_cell_text(r, c, full_text)
                except (IndexError, Exception):
                    continue

        try:
            cell = table.cell(r, c)

            if not (has_multi_run or has_nested):
                # 단일 run — p별 첫 run charPr 적용
                sub = cell.element.find(f"{_HP}subList")
                if sub is not None and cell_data['lines']:
                    ps_list = sub.findall(f"{_HP}p")
                    for pi, p in enumerate(ps_list):
                        if pi < len(cell_data['lines']):
                            line_runs = cell_data['lines'][pi].get('runs', [])
                            if line_runs:
                                new_cpr = cpr_map.get(line_runs[0].get('charPr', '0'), 0)
                                for run in p.findall(f"{_HP}run"):
                                    run.set("charPrIDRef", str(new_cpr))

            # borderFill 적용
            orig_bf = cell_data.get('borderFillIDRef', '1')
            new_bf = bf_map.get(orig_bf, '1')
            cell.set_border_fill_id(new_bf)
        except Exception:
            pass

    # 병합 — 가로 먼저, 세로 나중 (빈 행 방지)
    h_merges = [m for m in tbl['merges'] if m['r1'] == m['r2'] and m['c1'] != m['c2']]
    v_merges = [m for m in tbl['merges'] if m['r1'] != m['r2']]
    hv_merges = [m for m in tbl['merges'] if m['r1'] != m['r2'] and m['c1'] != m['c2']]

    for m in h_merges:
        if m['r2'] >= rows or m['c2'] >= cols:
            continue
        try:
            table.merge_cells(m['r1'], m['c1'], m['r2'], m['c2'])
        except Exception:
            pass
    for m in v_merges:
        if m['r2'] >= rows or m['c2'] >= cols:
            continue
        try:
            table.merge_cells(m['r1'], m['c1'], m['r2'], m['c2'])
        except Exception:
            pass

    # 병합 후 cellSz를 원본 값으로 재설정 (병합이 크기를 바꿀 수 있음)
    for cell_data in tbl['cells']:
        r, c = cell_data['row'], cell_data['col']
        if r >= rows or c >= cols:
            continue
        try:
            cell = table.cell(r, c)
            cell.set_size(width=cell_data['width'], height=cell_data['height'])
        except Exception:
            pass

    # 정렬 — 줄별 paraPr 적용
    for cell_data in tbl['cells']:
        r, c = cell_data['row'], cell_data['col']
        if r >= rows or c >= cols:
            continue
        try:
            cell = table.cell(r, c)
            sub = cell.element.find(f"{_HP}subList")
            if sub is None:
                continue

            sub.set("vertAlign", cell_data.get('vertAlign', 'CENTER'))

            ps = sub.findall(f"{_HP}p")
            for i, p in enumerate(ps):
                if i < len(cell_data['lines']):
                    line = cell_data['lines'][i]
                    ppid = get_or_create_paraPr(
                        line.get('horizontal', 'JUSTIFY'),
                        line.get('lineSpacing', 0),
                        line.get('margin_left', 0),
                        line.get('margin_right', 0),
                        line.get('margin_prev', 0),
                        line.get('margin_next', 0),
                    )
                    p.set("paraPrIDRef", ppid)
        except Exception:
            pass

    # 중첩 표 생성 — 셀 안에 표 삽입 (재귀)
    try:
        from lxml import etree as LET2
    except ImportError:
        import xml.etree.ElementTree as LET2

    for cell_data in tbl['cells']:
        # line별 중첩 표 확인
        has_any_nested = any(
            line.get('nested_tables', [])
            for line in cell_data.get('lines', [])
        )
        # 하위호환: 기존 nested_tables도 확인
        if not has_any_nested and not cell_data.get('nested_tables', []):
            continue
        r, c = cell_data['row'], cell_data['col']
        if r >= rows or c >= cols:
            continue
        try:
            cell = table.cell(r, c)
            sub = cell.element.find(f"{_HP}subList")
            if sub is None:
                continue

            # line별 중첩 표 수집 (순서 보존)
            all_nested = []
            for li, line in enumerate(cell_data.get('lines', [])):
                for ntbl_data in line.get('nested_tables', []):
                    all_nested.append((li, ntbl_data))
            # 하위호환
            if not all_nested:
                for ntbl_data in cell_data.get('nested_tables', []):
                    all_nested.append((-1, ntbl_data))

            for insert_after_line, ntbl_data in all_nested:
                # 중첩 표를 위한 새 p > run > tbl 구조 생성
                # 임시로 doc.add_table 사용 후 표 element를 셀 안으로 이동
                ntbl_rows = ntbl_data['rows']
                ntbl_cols = ntbl_data['cols']
                ntbl_w = ntbl_data['width']
                ntbl_h = ntbl_data['height']

                # 임시 표 생성
                temp_tbl = doc.add_table(ntbl_rows, ntbl_cols, width=ntbl_w)

                # 표 크기 설정
                nsz = temp_tbl.element.find(f"{_HP}sz")
                nsz.set("width", str(ntbl_w))
                nsz.set("height", str(ntbl_h))

                # pos 복원
                npos = temp_tbl.element.find(f"{_HP}pos")
                if npos is not None and ntbl_data.get('pos'):
                    for k, v in ntbl_data['pos'].items():
                        npos.set(k, v)

                # 셀 크기 + 텍스트
                ncol_widths = ntbl_data.get('col_widths', [])
                nrow_heights = ntbl_data.get('row_heights', [])
                for nr in range(ntbl_rows):
                    for nc in range(ntbl_cols):
                        try:
                            ncell = temp_tbl.cell(nr, nc)
                            cw = ncol_widths[nc] if nc < len(ncol_widths) and ncol_widths[nc] else ntbl_w // ntbl_cols
                            rh = nrow_heights[nr] if nr < len(nrow_heights) and nrow_heights[nr] else 3600
                            ncell.set_size(width=cw, height=rh)
                        except:
                            pass

                # 셀 텍스트 + charPr + borderFill + lineSpacing
                for ncell_data in ntbl_data.get('cells', []):
                    nr, nc = ncell_data['row'], ncell_data['col']
                    if nr >= ntbl_rows or nc >= ntbl_cols:
                        continue
                    text_parts = []
                    for line in ncell_data.get('lines', []):
                        line_text = ''.join(run['text'] for run in line.get('runs', []))
                        text_parts.append(line_text)
                    full_text = '\n'.join(text_parts)
                    if full_text.strip():
                        try:
                            temp_tbl.set_cell_text(nr, nc, full_text)
                        except:
                            pass

                    try:
                        ncell = temp_tbl.cell(nr, nc)

                        # charPr 적용
                        if ncell_data.get('lines'):
                            first_runs = ncell_data['lines'][0].get('runs', [])
                            if first_runs:
                                orig_cpr = first_runs[0].get('charPr', '0')
                                new_cpr = cpr_map.get(orig_cpr, 0)
                                nsub = ncell.element.find(f"{_HP}subList")
                                if nsub is not None:
                                    for np in nsub.findall(f"{_HP}p"):
                                        for nrun in np.findall(f"{_HP}run"):
                                            nrun.set("charPrIDRef", str(new_cpr))

                        # borderFill 적용
                        orig_bf = ncell_data.get('borderFillIDRef', '1')
                        new_bf = bf_map.get(orig_bf, '1')
                        ncell.set_border_fill_id(new_bf)

                        # cellMargin
                        cm = ncell_data.get('cellMargin', 141)
                        ncell.set_margin(left=cm, right=cm, top=cm, bottom=cm)

                        # lineSpacing — 줄별 paraPr 적용
                        nsub = ncell.element.find(f"{_HP}subList")
                        if nsub is not None:
                            nsub.set("vertAlign", ncell_data.get('vertAlign', 'CENTER'))
                            nps = nsub.findall(f"{_HP}p")
                            for ni, np in enumerate(nps):
                                if ni < len(ncell_data.get('lines', [])):
                                    line = ncell_data['lines'][ni]
                                    ppid = get_or_create_paraPr(
                                        line.get('horizontal', 'JUSTIFY'),
                                        line.get('lineSpacing', 0),
                                        line.get('margin_left', 0),
                                        line.get('margin_right', 0),
                                        line.get('margin_prev', 0),
                                        line.get('margin_next', 0),
                                    )
                                    np.set("paraPrIDRef", ppid)
                    except Exception:
                        pass

                # cellSz 재설정 (병합 후 변경 대비)
                for ncell_data in ntbl_data.get('cells', []):
                    nr, nc = ncell_data['row'], ncell_data['col']
                    if nr >= ntbl_rows or nc >= ntbl_cols:
                        continue
                    try:
                        ncell = temp_tbl.cell(nr, nc)
                        ncell.set_size(width=ncell_data['width'], height=ncell_data['height'])
                    except:
                        pass

                # 병합
                for m in ntbl_data.get('merges', []):
                    if m['r2'] < ntbl_rows and m['c2'] < ntbl_cols:
                        try:
                            temp_tbl.merge_cells(m['r1'], m['c1'], m['r2'], m['c2'])
                        except:
                            pass

                # 생성된 표 element를 셀의 subList 안으로 이동 (올바른 위치에)
                section_el = doc.sections[0].element if hasattr(doc.sections[0], 'element') else doc.sections[0]._element
                for sp in list(section_el.findall(f'{_HP}p')):
                    tbl_el = sp.find(f'.//{_HP}tbl')
                    if tbl_el is not None and tbl_el is temp_tbl.element:
                        new_p = LET2.Element(f'{_HP}p')
                        new_p.set('id', '0')
                        new_p.set('paraPrIDRef', '0')
                        new_p.set('styleIDRef', '0')
                        new_p.set('pageBreak', '0')
                        new_p.set('columnBreak', '0')
                        new_p.set('merged', '0')
                        new_run = LET2.SubElement(new_p, f'{_HP}run')
                        new_run.set('charPrIDRef', '0')
                        for run in sp.findall(f'{_HP}run'):
                            for ch in list(run):
                                tag = ch.tag.split('}')[1] if '}' in ch.tag else ch.tag
                                if tag == 'tbl':
                                    run.remove(ch)
                                    new_run.append(ch)
                        # 마커 p를 찾아서 교체, 없으면 line index로 삽입
                        marker_found = False
                        for mp in list(sub.findall(f'{_HP}p')):
                            if mp.get('_nested_marker') == '1':
                                idx = list(sub).index(mp)
                                sub.remove(mp)
                                sub.insert(idx, new_p)
                                marker_found = True
                                break
                        if not marker_found:
                            existing_ps = list(sub.findall(f'{_HP}p'))
                            if insert_after_line >= 0 and insert_after_line < len(existing_ps):
                                insert_idx = list(sub).index(existing_ps[insert_after_line]) + 1
                                sub.insert(insert_idx, new_p)
                            else:
                                sub.append(new_p)
                        section_el.remove(sp)
                        break
        except Exception:
            pass


# ============================================================
# CLI
# ============================================================

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == 'extract':
        src = sys.argv[2]
        out = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == '-o' else src + '.form.json'
        form = extract_form(src)
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(form, f, ensure_ascii=False, indent=2, default=str)
        n_cells = sum(len(t['cells']) for t in form['tables'])
        n_merges = sum(len(t['merges']) for t in form['tables'])
        print(f'✅ 추출: {out}')
        print(f'   표 {len(form["tables"])}개, 셀 {n_cells}개, 병합 {n_merges}개')
        print(f'   charPr {len(form["char_properties"])}개, paraPr {len(form["para_properties"])}개, borderFill {len(form["border_fills"])}개')

    elif cmd == 'generate':
        src = sys.argv[2]
        out = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == '-o' else 'generated.hwpx'
        with open(src, 'r', encoding='utf-8') as f:
            form = json.load(f)
        generate_form(form, out)
        print(f'✅ 생성: {out} ({os.path.getsize(out):,} bytes)')

    elif cmd == 'clone':
        src = sys.argv[2]
        out = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == '-o' else src.replace('.hwpx', '_clone.hwpx').replace('.owpml', '_clone.hwpx')
        print(f'1. 추출: {src}')
        form = extract_form(src)
        print(f'   표 {len(form["tables"])}개, 셀 {sum(len(t["cells"]) for t in form["tables"])}개')
        print(f'2. 생성: {out}')
        generate_form(form, out)
        print(f'✅ 클론 완료: {out} ({os.path.getsize(out):,} bytes)')

    else:
        print(f'Unknown command: {cmd}')
        print(__doc__)


if __name__ == '__main__':
    main()
