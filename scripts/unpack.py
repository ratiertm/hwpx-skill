#!/usr/bin/env python3
"""hwpx → XML 폴더로 풀기

Usage:
    python scripts/unpack.py input.hwpx [output_dir]

output_dir 생략 시 input.hwpx.unpacked/ 에 풀림
"""
import sys
import os
import zipfile


def unpack(hwpx_path: str, output_dir: str = "") -> str:
    if not os.path.exists(hwpx_path):
        print(f"Error: {hwpx_path} not found")
        sys.exit(1)

    if not output_dir:
        output_dir = hwpx_path + ".unpacked"

    os.makedirs(output_dir, exist_ok=True)

    with zipfile.ZipFile(hwpx_path, 'r') as z:
        z.extractall(output_dir)
        count = len(z.namelist())

    print(f"Unpacked {count} files → {output_dir}/")
    return output_dir


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/unpack.py <input.hwpx> [output_dir]")
        sys.exit(1)
    hwpx = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else ""
    unpack(hwpx, out)
