"""Vendored third-party binaries and license notices.

Bundled fonts:
  NanumGothic-Regular.ttf, NanumGothic-Bold.ttf
  Copyright (c) 2010, NAVER Corporation. Licensed under SIL OFL 1.1.
  See OFL-NanumGothic.txt for full license text.

See NOTICE.md for attribution and license information.
"""
from pathlib import Path

_VENDOR_DIR = Path(__file__).parent

NANUM_GOTHIC_REGULAR = _VENDOR_DIR / "NanumGothic-Regular.ttf"
NANUM_GOTHIC_BOLD = _VENDOR_DIR / "NanumGothic-Bold.ttf"
