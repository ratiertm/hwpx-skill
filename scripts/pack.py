#!/usr/bin/env python3
"""XML 폴더 → hwpx 리팩 (mimetype STORED 보장)

Usage:
    python scripts/pack.py input_dir output.hwpx

HWPX/OWPML은 OPC 규격: mimetype 파일은 압축 없이(STORED) 첫 번째로 들어가야 함.
"""
import sys
import os
import zipfile


def pack(input_dir: str, output_path: str) -> str:
    if not os.path.isdir(input_dir):
        print(f"Error: {input_dir} is not a directory")
        sys.exit(1)

    # 모든 파일 수집
    all_files = []
    for root, dirs, files in os.walk(input_dir):
        for f in files:
            full = os.path.join(root, f)
            arcname = os.path.relpath(full, input_dir)
            all_files.append((full, arcname))

    # mimetype을 첫 번째로, STORED로
    mimetype_file = None
    other_files = []
    for full, arcname in all_files:
        if arcname == "mimetype":
            mimetype_file = (full, arcname)
        else:
            other_files.append((full, arcname))

    with zipfile.ZipFile(output_path, 'w') as zf:
        # mimetype: STORED (압축 없음)
        if mimetype_file:
            with open(mimetype_file[0], 'rb') as f:
                data = f.read()
            zf.writestr(
                zipfile.ZipInfo("mimetype", date_time=(2026, 1, 1, 0, 0, 0)),
                data,
                compress_type=zipfile.ZIP_STORED,
            )

        # 나머지: DEFLATED
        for full, arcname in sorted(other_files):
            zf.write(full, arcname, compress_type=zipfile.ZIP_DEFLATED)

    size = os.path.getsize(output_path)
    print(f"Packed {len(all_files)} files → {output_path} ({size:,} bytes)")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/pack.py <input_dir> <output.hwpx>")
        sys.exit(1)
    pack(sys.argv[1], sys.argv[2])
