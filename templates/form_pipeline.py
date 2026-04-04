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
    """서식 파일에서 재생성에 필요한 모든 구조 데이터 추출"""
    with zipfile.ZipFile(path) as z:
        header_xml = z.read('Contents/header.xml').decode('utf-8')
        section_xml = z.read('Contents/section0.xml').decode('utf-8')

    hroot = ET.fromstring(header_xml)
    sroot = ET.fromstring(section_xml)

    form = {
        '_source': os.path.basename(path),
        'page': _extract_page(sroot),
        'fonts': _extract_fonts(hroot),
        'char_properties': _extract_char_properties(hroot),
        'para_properties': _extract_para_properties(hroot),
        'border_fills': _extract_border_fills(hroot),
        'tables': _extract_tables(sroot, hroot),
        'before_table_text': _extract_before_table_text(sroot),
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
        ls = pp.find(f'{_HH}lineSpacing')
        margin = pp.find(f'{_HH}margin')

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
        result[bfid] = borders
    return result


def _extract_before_table_text(sroot):
    """표 앞에 있는 텍스트 추출"""
    texts = []
    for p in sroot.findall(f'{_HP}p'):
        if p.find(f'.//{_HP}tbl') is not None:
            break
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

    # 줄별 정보 (paraPr + charPr + text)
    lines = []
    if sub is not None:
        for p in sub.findall(f'{_HP}p'):
            ppr = p.get('paraPrIDRef', '0')
            ppr_info = ppr_map.get(ppr, {'horizontal': 'JUSTIFY'})

            runs_data = []
            for run in p.findall(f'{_HP}run'):
                cpr = run.get('charPrIDRef', '0')
                t = run.find(f'{_HP}t')
                txt = t.text if t is not None and t.text else ''
                runs_data.append({'charPr': cpr, 'text': txt})

            lines.append({
                'paraPr': ppr,
                'horizontal': ppr_info.get('horizontal', 'JUSTIFY'),
                'lineSpacing': ppr_info.get('lineSpacing', 0),
                'margin_left': ppr_info.get('margin_left', 0),
                'margin_right': ppr_info.get('margin_right', 0),
                'runs': runs_data,
            })

    return {
        'row': r, 'col': c, 'colSpan': cs, 'rowSpan': rs,
        'width': w, 'height': h,
        'vertAlign': vert_align,
        'borderFillIDRef': bf,
        'cellMargin': cell_margin,
        'lines': lines,
    }


def _reverse_grid(cells, col_count, row_count):
    """연립방정식으로 컬럼/행 그리드 역산"""
    col_widths = [None] * col_count
    row_heights = [None] * row_count

    w_eq = [(c['col'], c['col'] + c['colSpan'], c['width']) for c in cells]
    h_eq = [(c['row'], c['row'] + c['rowSpan'], c['height']) for c in cells]

    for s, e, w in w_eq:
        if e - s == 1:
            col_widths[s] = w
    changed = True
    while changed:
        changed = False
        for s, e, w in w_eq:
            unknowns = [i for i in range(s, e) if col_widths[i] is None]
            knowns = sum(col_widths[i] for i in range(s, e) if col_widths[i] is not None)
            if len(unknowns) == 1:
                col_widths[unknowns[0]] = w - knowns
                changed = True

    for s, e, h in h_eq:
        if e - s == 1:
            row_heights[s] = h
    changed = True
    while changed:
        changed = False
        for s, e, h in h_eq:
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

    # 2. charPr 스타일 생성
    cpr_map = {}  # 원본 id → 새 id
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

    ppr_map = {}  # 키 = (horizontal, lineSpacing, margin_left, margin_right) → 새 id

    import copy

    def get_or_create_paraPr(horz, ls=0, ml=0, mr=0):
        key = (horz, ls, ml, mr)
        if key in ppr_map:
            return ppr_map[key]

        # 기존 paraPr 중 horizontal이 같은 게 있으면 재사용
        if ml == 0 and mr == 0:
            for pp in pp_container.findall(f"{_HH}paraPr"):
                a = pp.find(f"{_HH}align")
                if a is not None and a.get("horizontal") == horz:
                    ppr_map[key] = pp.get("id")
                    return pp.get("id")

        nonlocal next_pp_id
        pid = str(next_pp_id)

        # paraPr[0] 전체를 deep copy한 후 id와 horizontal만 변경
        if base_pp is not None:
            new_pp = copy.deepcopy(base_pp)
            new_pp.set("id", pid)
            a = new_pp.find(f"{_HH}align")
            if a is not None:
                a.set("horizontal", horz)
            # margin 변경 (필요시)
            if ml or mr:
                # switch 내부와 default 내부 모두 margin 수정
                for margin_el in new_pp.findall(f".//{_HH}margin"):
                    left_el = margin_el.find(f".//{_HC}left")
                    if left_el is None:
                        left_el = margin_el.find(f".//{_HH}left")
                    right_el = margin_el.find(f".//{_HC}right")
                    if right_el is None:
                        right_el = margin_el.find(f".//{_HH}right")
                    if left_el is not None:
                        left_el.set("value", str(ml))
                    if right_el is not None:
                        right_el.set("value", str(mr))
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

    # 4. borderFill 생성
    bf_container = header.element.find(f".//{_HH}borderFills")
    existing_bf = set(bf.get("id") for bf in bf_container.findall(f"{_HH}borderFill"))
    next_bf = max(int(i) for i in existing_bf) + 1 if existing_bf else 2

    bf_map = {}  # 원본 id → 새 id
    for orig_id, borders in form_data['border_fills'].items():
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
        next_bf += 1
    bf_container.set("itemCnt", str(len(bf_container)))

    # 5. 표 앞 텍스트 — secPr 문단의 run으로 추가 (별도 p 만들지 않음)
    #    원본 패턴: secPr p에 텍스트 run 포함 + linesegarray
    before_texts = form_data.get('before_table_text', [])
    if before_texts:
        default_cpr = cpr_map.get('4', cpr_map.get('0', 0))
        # secPr이 있는 첫 번째 p 찾기
        section_el = sec.element if hasattr(sec, 'element') else sec._element
        sec_ps = section_el.findall(f'{_HP}p')
        secpr_p = None
        for p in sec_ps:
            if p.find(f'.//{_HP}secPr') is not None:
                secpr_p = p
                break

        if secpr_p is not None:
            # secPr p에 텍스트 run 추가
            for text in before_texts:
                run = LET.SubElement(secpr_p, f'{_HP}run')
                run.set('charPrIDRef', str(default_cpr))
                t = LET.SubElement(run, f'{_HP}t')
                t.text = text
        else:
            # fallback: 별도 p
            for text in before_texts:
                doc.add_paragraph(text, char_pr_id_ref=default_cpr)

    # 6. 표 생성
    for tbl_data in form_data['tables']:
        _generate_table(doc, tbl_data, cpr_map, bf_map, get_or_create_paraPr)

    # paraPr itemCnt 업데이트
    pp_container.set("itemCnt", str(len(pp_container)))

    doc.save_to_path(output_path)
    return output_path


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

        # 텍스트 조합 (\n으로 줄 합침)
        text_parts = []
        for line in cell_data['lines']:
            line_text = ''.join(run['text'] for run in line['runs'])
            text_parts.append(line_text)
        full_text = '\n'.join(text_parts)

        if full_text.strip():
            table.set_cell_text(r, c, full_text)

        try:
            cell = table.cell(r, c)

            # charPr 적용 (첫 번째 run의 charPr 사용)
            if cell_data['lines']:
                first_runs = cell_data['lines'][0].get('runs', [])
                if first_runs:
                    orig_cpr = first_runs[0].get('charPr', '0')
                    new_cpr = cpr_map.get(orig_cpr, 0)
                    sub = cell.element.find(f"{_HP}subList")
                    if sub is not None:
                        for p in sub.findall(f"{_HP}p"):
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
        try:
            table.merge_cells(m['r1'], m['c1'], m['r2'], m['c2'])
        except Exception:
            pass
    for m in v_merges:
        try:
            table.merge_cells(m['r1'], m['c1'], m['r2'], m['c2'])
        except Exception:
            pass

    # 병합 후 cellSz를 원본 값으로 재설정 (병합이 크기를 바꿀 수 있음)
    for cell_data in tbl['cells']:
        r, c = cell_data['row'], cell_data['col']
        try:
            cell = table.cell(r, c)
            cell.set_size(width=cell_data['width'], height=cell_data['height'])
        except Exception:
            pass

    # 정렬 — 줄별 paraPr 적용
    for cell_data in tbl['cells']:
        r, c = cell_data['row'], cell_data['col']
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
                        line.get('lineSpacing', 150),
                        line.get('margin_left', 0),
                        line.get('margin_right', 0),
                    )
                    p.set("paraPrIDRef", ppid)
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
