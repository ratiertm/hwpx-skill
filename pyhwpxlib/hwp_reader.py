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

        # 4. 섹션별 텍스트 추출
        all_texts = []
        all_paragraphs = []
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

            section_idx += 1

        result['section_count'] = section_idx
        result['texts'] = all_texts
        result['paragraphs'] = all_paragraphs

        return result

    finally:
        ole.close()


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

    from .api import create_document, add_paragraph, save

    hwpx = create_document()
    count = 0
    for para in doc_data['paragraphs']:
        if para['text']:
            # 줄바꿈을 별도 단락으로 분리
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
