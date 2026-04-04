"""
HWPX 재생성기 — 리버스 데이터로부터 동일한 HWPX 파일을 생성
Usage:
    python hwpx_generator.py extract <input.hwpx> <output.json>
    python hwpx_generator.py generate <input.json> <output.hwpx>
    python hwpx_generator.py verify <original.hwpx> <generated.hwpx>
"""
import zipfile, json, sys, os
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement

NS = {
    'ha': 'http://www.hancom.co.kr/hwpml/2011/app',
    'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hp10': 'http://www.hancom.co.kr/hwpml/2016/paragraph',
    'hs': 'http://www.hancom.co.kr/hwpml/2011/section',
    'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
    'hh': 'http://www.hancom.co.kr/hwpml/2011/head',
    'hhs': 'http://www.hancom.co.kr/hwpml/2011/history',
    'hm': 'http://www.hancom.co.kr/hwpml/2011/master-page',
    'hpf': 'http://www.hancom.co.kr/schema/2011/hpf',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'opf': 'http://www.idpf.org/2007/opf/',
    'ooxmlchart': 'http://www.hancom.co.kr/hwpml/2016/ooxmlchart',
    'hwpunitchar': 'http://www.hancom.co.kr/hwpml/2016/HwpUnitChar',
    'epub': 'http://www.idpf.org/2007/ops',
    'config': 'urn:oasis:names:tc:opendocument:xmlns:config:1.0',
}

NS_DECL = ' '.join(f'xmlns:{k}="{v}"' for k, v in NS.items())


# ============================================================
# EXTRACT: HWPX → JSON
# ============================================================

def extract_all(hwpx_path):
    """HWPX 파일에서 재생성에 필요한 모든 정보를 JSON으로 추출"""
    data = {'_source': os.path.basename(hwpx_path), 'files': {}}

    with zipfile.ZipFile(hwpx_path) as z:
        for name in z.namelist():
            raw = z.read(name)
            try:
                text = raw.decode('utf-8')
                data['files'][name] = text
            except:
                # binary → base64
                import base64
                data['files'][name] = {'_binary': True, '_b64': base64.b64encode(raw).decode('ascii')}

    return data


# ============================================================
# GENERATE: JSON → HWPX
# ============================================================

def generate_hwpx(data, output_path):
    """JSON 데이터로부터 HWPX 파일 생성"""
    import base64

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, content in data['files'].items():
            if isinstance(content, dict) and content.get('_binary'):
                raw = base64.b64decode(content['_b64'])
                zout.writestr(name, raw)
            else:
                zout.writestr(name, content.encode('utf-8'))


# ============================================================
# VERIFY: 원본 vs 생성 파일 비교
# ============================================================

def verify(original_path, generated_path):
    """두 HWPX 파일의 구조적 동일성 검증"""
    results = {'match': True, 'details': []}

    with zipfile.ZipFile(original_path) as z1, zipfile.ZipFile(generated_path) as z2:
        names1 = set(z1.namelist())
        names2 = set(z2.namelist())

        # 파일 목록 비교
        only1 = names1 - names2
        only2 = names2 - names1
        if only1:
            results['details'].append(f'원본에만 있음: {only1}')
            results['match'] = False
        if only2:
            results['details'].append(f'생성에만 있음: {only2}')
            results['match'] = False

        # 공통 파일 내용 비교
        for name in sorted(names1 & names2):
            d1 = z1.read(name)
            d2 = z2.read(name)

            if name.endswith('.xml') or name == 'mimetype':
                # XML 구조 비교 (공백/순서 무시)
                t1 = d1.decode('utf-8').strip()
                t2 = d2.decode('utf-8').strip()
                if t1 == t2:
                    results['details'].append(f'✅ {name}: 완전 일치')
                else:
                    # XML 파싱 비교
                    try:
                        r1 = ET.fromstring(t1)
                        r2 = ET.fromstring(t2)
                        if elements_equal(r1, r2):
                            results['details'].append(f'✅ {name}: XML 구조 일치 (공백 차이)')
                        else:
                            results['details'].append(f'❌ {name}: XML 구조 불일치')
                            results['match'] = False
                            # 차이점 찾기
                            diff = find_xml_diff(r1, r2, name)
                            results['details'].extend(diff)
                    except ET.ParseError:
                        if t1 == t2:
                            results['details'].append(f'✅ {name}: 텍스트 일치')
                        else:
                            results['details'].append(f'❌ {name}: 텍스트 불일치')
                            results['match'] = False
            elif name.endswith('.png'):
                if d1 == d2:
                    results['details'].append(f'✅ {name}: 바이너리 일치 ({len(d1)} bytes)')
                else:
                    results['details'].append(f'⚠️ {name}: 바이너리 다름 (원본={len(d1)}, 생성={len(d2)})')
            elif name.endswith('.txt'):
                t1 = d1.decode('utf-8', errors='replace').strip()
                t2 = d2.decode('utf-8', errors='replace').strip()
                if t1 == t2:
                    results['details'].append(f'✅ {name}: 텍스트 일치')
                else:
                    results['details'].append(f'❌ {name}: 텍스트 불일치')
                    results['match'] = False

    return results


def elements_equal(e1, e2):
    """두 XML Element의 구조적 동일성 비교"""
    if e1.tag != e2.tag:
        return False
    if (e1.text or '').strip() != (e2.text or '').strip():
        return False
    if (e1.tail or '').strip() != (e2.tail or '').strip():
        return False
    if e1.attrib != e2.attrib:
        return False
    if len(e1) != len(e2):
        return False
    return all(elements_equal(c1, c2) for c1, c2 in zip(e1, e2))


def find_xml_diff(e1, e2, path='', max_diffs=5):
    """XML 트리 차이점 찾기"""
    diffs = []
    if e1.tag != e2.tag:
        diffs.append(f'   {path}: 태그 다름 {e1.tag} vs {e2.tag}')
        return diffs
    if e1.attrib != e2.attrib:
        for k in set(list(e1.attrib.keys()) + list(e2.attrib.keys())):
            v1 = e1.attrib.get(k, '(없음)')
            v2 = e2.attrib.get(k, '(없음)')
            if v1 != v2:
                tag_short = e1.tag.split('}')[1] if '}' in e1.tag else e1.tag
                diffs.append(f'   {path}/{tag_short}@{k}: "{v1}" vs "{v2}"')
    t1 = (e1.text or '').strip()
    t2 = (e2.text or '').strip()
    if t1 != t2:
        tag_short = e1.tag.split('}')[1] if '}' in e1.tag else e1.tag
        diffs.append(f'   {path}/{tag_short} text: "{t1[:50]}" vs "{t2[:50]}"')
    if len(e1) != len(e2):
        tag_short = e1.tag.split('}')[1] if '}' in e1.tag else e1.tag
        diffs.append(f'   {path}/{tag_short}: 자식 수 {len(e1)} vs {len(e2)}')
    else:
        for c1, c2 in zip(e1, e2):
            tag_short = e1.tag.split('}')[1] if '}' in e1.tag else e1.tag
            sub_diffs = find_xml_diff(c1, c2, f'{path}/{tag_short}')
            diffs.extend(sub_diffs)
            if len(diffs) >= max_diffs:
                diffs.append('   ... (추가 차이 생략)')
                return diffs
    return diffs


# ============================================================
# CLI
# ============================================================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == 'extract':
        if len(sys.argv) < 4:
            print('Usage: extract <input.hwpx> <output.json>')
            return
        data = extract_all(sys.argv[2])
        with open(sys.argv[3], 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'추출 완료: {sys.argv[3]} ({len(data["files"])}개 파일)')

    elif cmd == 'generate':
        if len(sys.argv) < 4:
            print('Usage: generate <input.json> <output.hwpx>')
            return
        with open(sys.argv[2], 'r', encoding='utf-8') as f:
            data = json.load(f)
        generate_hwpx(data, sys.argv[3])
        print(f'생성 완료: {sys.argv[3]}')

    elif cmd == 'verify':
        if len(sys.argv) < 4:
            print('Usage: verify <original.hwpx> <generated.hwpx>')
            return
        results = verify(sys.argv[2], sys.argv[3])
        print(f'\n{"="*60}')
        print(f'검증 결과: {"✅ 일치" if results["match"] else "❌ 불일치"}')
        print(f'{"="*60}')
        for d in results['details']:
            print(d)

    elif cmd == 'roundtrip':
        # extract → generate → verify 한 번에
        if len(sys.argv) < 3:
            print('Usage: roundtrip <input.hwpx>')
            return
        src = sys.argv[2]
        json_path = src + '.extracted.json'
        gen_path = src.replace('.hwpx', '_generated.hwpx').replace('.owpml', '_generated.owpml')

        print(f'1. 추출: {src} → {json_path}')
        data = extract_all(src)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f'   {len(data["files"])}개 파일 추출')

        print(f'2. 생성: {json_path} → {gen_path}')
        generate_hwpx(data, gen_path)

        print(f'3. 검증: {src} vs {gen_path}')
        results = verify(src, gen_path)
        print(f'\n{"="*60}')
        print(f'라운드트립 결과: {"✅ 일치" if results["match"] else "❌ 불일치"}')
        print(f'{"="*60}')
        for d in results['details']:
            print(d)

        # cleanup
        os.remove(json_path)
        return results['match']

    else:
        print(f'Unknown command: {cmd}')
        print(__doc__)


if __name__ == '__main__':
    main()
