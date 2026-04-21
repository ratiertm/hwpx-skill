"""Reader utilities for 공문 metadata (license, disclosure, etc).

Counterpart to builder.py: extracts metadata injected into HWPX files
by GongmunBuilder.
"""
from __future__ import annotations
import re
import zipfile
from pathlib import Path
from typing import Optional, Union


# 공공누리 유형 설명
KOGL_TYPE_DESC = {
    1: "출처표시",
    2: "출처표시 + 상업적 이용금지",
    3: "출처표시 + 변경금지",
    4: "출처표시 + 상업적 이용금지 + 변경금지",
}

# CCL 비트 분해
CCL_BITS = [
    (1, "BY", "저작자표시"),
    (2, "SA", "동일조건변경허락"),
    (4, "NC", "비영리"),
    (8, "ND", "변경금지"),
]


def _decode_ccl_flag(flag: int) -> str:
    """CCL flag bitmask → 'BY-SA-NC' 등 short label."""
    parts = [short for bit, short, _ in CCL_BITS if flag & bit]
    return "-".join(parts) if parts else ""


def read_license(file: Union[str, Path]) -> Optional[dict]:
    """Extract license mark from HWPX file's header.xml.

    Args:
        file: HWPX file path.

    Returns:
        Dict with license info, or None if no license found.
        Keys: 종류, 유형, flag, lang, 설명, short

    Examples:
        >>> read_license("gov_doc.hwpx")
        {
            "종류": "KOGL",
            "유형": 1,
            "flag": 1,
            "lang": 1042,
            "설명": "공공누리 제1유형: 출처표시",
            "short": "KOGL-1",
        }

        >>> read_license("private.hwpx")
        None
    """
    path = Path(file)
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("Contents/header.xml").decode("utf-8")
    except (zipfile.BadZipFile, KeyError, FileNotFoundError):
        return None

    m = re.search(
        r'<hh:licensemark\s+type="([^"]*)"\s+flag="([^"]*)"(?:\s+lang="([^"]*)")?',
        xml,
    )
    if not m:
        return None

    kind = m.group(1)
    flag = int(m.group(2)) if m.group(2).isdigit() else m.group(2)
    lang = int(m.group(3)) if m.group(3) and m.group(3).isdigit() else None

    # 설명 생성
    if kind == "KOGL":
        desc = KOGL_TYPE_DESC.get(flag, f"공공누리 제{flag}유형")
        설명 = f"공공누리 제{flag}유형: {desc}"
        short = f"KOGL-{flag}"
    elif kind == "CCL":
        attrs = _decode_ccl_flag(flag)
        설명 = f"CC {attrs}" if attrs else "Creative Commons"
        short = f"CCL-{attrs}" if attrs else "CCL"
    else:
        설명 = kind
        short = kind

    return {
        "종류": kind,
        "유형": flag,
        "flag": flag,
        "lang": lang,
        "설명": 설명,
        "short": short,
    }


def license_summary(file: Union[str, Path]) -> Optional[str]:
    """Short-form license identifier for summary use.

    Returns e.g. "KOGL-1", "CCL-BY-SA", or None.
    """
    info = read_license(file)
    return info["short"] if info else None
