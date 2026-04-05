#!/usr/bin/env python3
"""HWPX 파일 구조 검증

Usage:
    python scripts/validate.py input.hwpx

검증 항목:
1. ZIP 구조 유효성
2. 필수 파일 존재 (mimetype, header.xml, section0.xml, content.hpf)
3. mimetype 내용 확인
4. XML 파싱 유효성 (header.xml, section0.xml)
5. 네임스페이스 확인
"""
import sys
import os
import zipfile
import xml.etree.ElementTree as ET


REQUIRED_FILES = [
    "mimetype",
    "Contents/header.xml",
    "Contents/section0.xml",
    "Contents/content.hpf",
]

EXPECTED_MIMETYPE = "application/hwp+zip"

HWPX_NAMESPACES = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
    "hh": "http://www.hancom.co.kr/hwpml/2011/head",
    "hc": "http://www.hancom.co.kr/hwpml/2011/core",
}


def validate(hwpx_path: str) -> dict:
    result = {"path": hwpx_path, "errors": [], "warnings": [], "info": {}}
    errors = result["errors"]
    warnings = result["warnings"]
    info = result["info"]

    # 1. ZIP 유효성
    if not zipfile.is_zipfile(hwpx_path):
        errors.append("Not a valid ZIP file")
        return result

    with zipfile.ZipFile(hwpx_path, 'r') as z:
        names = z.namelist()
        info["file_count"] = len(names)

        # 2. 필수 파일
        for req in REQUIRED_FILES:
            if req not in names:
                errors.append(f"Missing required file: {req}")

        # 3. mimetype
        if "mimetype" in names:
            mt = z.read("mimetype").decode("utf-8").strip()
            info["mimetype"] = mt
            if mt != EXPECTED_MIMETYPE:
                warnings.append(f"Unexpected mimetype: {mt} (expected {EXPECTED_MIMETYPE})")

            # mimetype이 첫 번째 엔트리인지
            if names[0] != "mimetype":
                warnings.append(f"mimetype is not first entry (found at index {names.index('mimetype')})")

            # mimetype이 STORED인지
            mi = z.getinfo("mimetype")
            if mi.compress_type != zipfile.ZIP_STORED:
                warnings.append("mimetype should be STORED (uncompressed)")

        # 4. XML 파싱
        for xml_file in ["Contents/header.xml", "Contents/section0.xml"]:
            if xml_file in names:
                try:
                    content = z.read(xml_file).decode("utf-8")
                    ET.fromstring(content)
                    info[xml_file] = f"OK ({len(content):,} bytes)"
                except ET.ParseError as e:
                    errors.append(f"XML parse error in {xml_file}: {e}")

        # 5. section0.xml 네임스페이스 확인
        if "Contents/section0.xml" in names:
            content = z.read("Contents/section0.xml").decode("utf-8")
            for prefix, uri in HWPX_NAMESPACES.items():
                if uri not in content:
                    warnings.append(f"Missing namespace {prefix}: {uri}")

        # 6. 파일 목록
        info["files"] = names

    result["valid"] = len(errors) == 0
    return result


def print_result(result: dict) -> None:
    path = result["path"]
    valid = result.get("valid", False)
    errors = result["errors"]
    warnings = result["warnings"]
    info = result["info"]

    print(f"\n{'=' * 50}")
    print(f"HWPX Validation: {path}")
    print(f"{'=' * 50}")
    print(f"Result: {'✅ VALID' if valid else '❌ INVALID'}")
    print(f"Files: {info.get('file_count', '?')}")
    print(f"Mimetype: {info.get('mimetype', 'N/A')}")

    for xml_file in ["Contents/header.xml", "Contents/section0.xml"]:
        if xml_file in info:
            print(f"{xml_file}: {info[xml_file]}")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  ❌ {e}")
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  ⚠️  {w}")

    if valid and not warnings:
        print("\n✅ All checks passed!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate.py <input.hwpx>")
        sys.exit(1)
    result = validate(sys.argv[1])
    print_result(result)
    sys.exit(0 if result.get("valid") else 1)
