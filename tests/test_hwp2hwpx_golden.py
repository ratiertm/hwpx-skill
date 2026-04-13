"""Golden tests: HWP→HWPX conversion produces no text loss."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pyhwpxlib.hwp_reader import read_hwp, detect_format
from pyhwpxlib.hwp2hwpx import convert
from pyhwpxlib.api import extract_text

PROJECT = os.path.dirname(os.path.dirname(__file__))

# HWP 5.x binary files (some have .hwpx extension but are actually HWP binary)
HWP_SAMPLES = []
for f in os.listdir(os.path.join(PROJECT, 'samples')):
    path = os.path.join(PROJECT, 'samples', f)
    if os.path.isfile(path):
        try:
            fmt = detect_format(path)
            if fmt == "HWP":
                HWP_SAMPLES.append(path)
        except Exception:
            pass


@pytest.mark.parametrize("src", HWP_SAMPLES, ids=[os.path.basename(p) for p in HWP_SAMPLES])
def test_hwp_to_hwpx_no_char_loss(src, tmp_path):
    """변환 후 원본에 있던 문자가 HWPX에서 누락되지 않는지 검증."""
    hwp_doc = read_hwp(src)
    hwp_chars = set()
    for t in hwp_doc.texts:
        hwp_chars.update(c for c in t if ord(c) >= 32)

    dst = str(tmp_path / "out.hwpx")
    convert(src, dst)
    hwpx_text = extract_text(dst)
    hwpx_chars = set(c for c in hwpx_text if ord(c) >= 32)

    missing = hwp_chars - hwpx_chars - {'\r', '\x00', '\x01'}
    assert not missing, f"Missing chars after conversion: {missing}"


@pytest.mark.parametrize("src", HWP_SAMPLES, ids=[os.path.basename(p) for p in HWP_SAMPLES])
def test_hwp_to_hwpx_validates(src, tmp_path):
    """변환 결과가 유효한 HWPX ZIP인지 검증."""
    import zipfile
    dst = str(tmp_path / "out.hwpx")
    convert(src, dst)
    assert os.path.exists(dst)
    with zipfile.ZipFile(dst) as z:
        names = z.namelist()
        assert 'mimetype' in names
        assert 'Contents/header.xml' in names
        assert 'Contents/section0.xml' in names
