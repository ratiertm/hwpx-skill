"""Fix rendering issues in AI반도체_시장분석.hwpx:
- Summary boxes (1x1 tables) have cellSz heights too small → clipped text
- Section 5 (risk table) overflows page → add page break before it

Strategy: patch section0.xml directly (surgical edit), repack.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

SRC = Path("Test/AI반도체_시장분석.hwpx")
DST = Path("Test/AI반도체_시장분석_fixed.hwpx")
UNPACK = Path("/tmp/ai_fix_unpack")

NS = {
    "hp": "http://www.hancom.co.kr/hwpml/2011/paragraph",
    "hs": "http://www.hancom.co.kr/hwpml/2011/section",
}


def unpack():
    if UNPACK.exists():
        shutil.rmtree(UNPACK)
    subprocess.run(
        [sys.executable, "-m", "pyhwpxlib", "unpack", str(SRC), "-o", str(UNPACK)],
        check=True,
    )


def pack():
    if DST.exists():
        DST.unlink()
    subprocess.run(
        [sys.executable, "-m", "pyhwpxlib", "pack", str(UNPACK), "-o", str(DST)],
        check=True,
    )


def patch():
    sec = UNPACK / "Contents" / "section0.xml"
    xml = sec.read_text(encoding="utf-8")

    # Parse to find table IDs and heights we want to change
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml)
    tables = root.findall(".//hp:tbl", NS)
    targets: list[tuple[str, int]] = []  # (tbl_id, new_height)
    box_plan = {0: 8500, 2: 6500, 4: 4500}  # table index -> new height
    for i, t in enumerate(tables):
        if i in box_plan:
            tbl_id = t.get("id")
            old = int(t.find(".//hp:cellSz", NS).get("height"))
            targets.append((tbl_id, old, box_plan[i]))
            print(f"  table {i}: id={tbl_id} height {old} → {box_plan[i]}")

    # Each <hp:tbl> has TWO heights:
    #   - <hp:sz height="..."> = overall box on canvas (rhwp uses this)
    #   - <hp:cellSz height="..."> = inner cell dimension
    # Both must be kept in sync.
    for tbl_id, _old, new_h in targets:
        # 1) <hp:sz> (first occurrence inside this tbl)
        pat_sz = re.compile(
            r'(<hp:tbl[^>]*\bid="' + re.escape(tbl_id)
            + r'"[^>]*>.*?<hp:sz[^/]*?\bheight=")(\d+)(")',
            re.DOTALL,
        )
        new_xml, n = pat_sz.subn(rf"\g<1>{new_h}\g<3>", xml, count=1)
        if n != 1:
            raise RuntimeError(f"Failed to patch hp:sz for id={tbl_id}")
        xml = new_xml
        # 2) <hp:cellSz>
        pat_cell = re.compile(
            r'(<hp:tbl[^>]*\bid="' + re.escape(tbl_id)
            + r'"[^>]*>.*?<hp:cellSz[^/]*?\bheight=")(\d+)(")',
            re.DOTALL,
        )
        new_xml, n = pat_cell.subn(rf"\g<1>{new_h}\g<3>", xml, count=1)
        if n != 1:
            raise RuntimeError(f"Failed to patch hp:cellSz for id={tbl_id}")
        xml = new_xml

    # Find the paragraph containing "5. 리스크 요인" heading text and set
    # pageBreak="1" on the paragraph that CONTAINS it. In XML the paragraph
    # has pageBreak="0" near the start; we'll toggle to "1".
    heading_marker = "5. 리스크 요인"
    marker_idx = xml.find(heading_marker)
    if marker_idx < 0:
        raise RuntimeError("heading marker not found")
    # Walk backward to the nearest <hp:p ...>
    p_start = xml.rfind("<hp:p ", 0, marker_idx)
    if p_start < 0:
        raise RuntimeError("<hp:p not found before marker")
    p_end = xml.find(">", p_start)
    p_tag = xml[p_start:p_end + 1]
    if 'pageBreak="' in p_tag:
        new_p_tag = re.sub(r'pageBreak="\d+"', 'pageBreak="1"', p_tag, count=1)
    else:
        new_p_tag = p_tag[:-1] + ' pageBreak="1">'
    xml = xml[:p_start] + new_p_tag + xml[p_end + 1:]
    print(f"  page break inserted on <hp:p> before '{heading_marker}'")

    # Fix risk table row 0 col 1 inconsistent charPrIDRef (was 13 → should be 0)
    # The target text uniquely identifies the location.
    bad_run = '<hp:run charPrIDRef="13"><hp:t>미중 반도체 제재 확대 시 공급망 재편 가속</hp:t>'
    good_run = '<hp:run charPrIDRef="0"><hp:t>미중 반도체 제재 확대 시 공급망 재편 가속</hp:t>'
    if bad_run in xml:
        xml = xml.replace(bad_run, good_run, 1)
        print("  risk table r0c1 charPrIDRef: 13 → 0")
    else:
        # Fallback: regex in case attribute order differs
        pat = re.compile(
            r'<hp:run\s+charPrIDRef="13"\s*>(<hp:t>미중 반도체[^<]*</hp:t>)'
        )
        new_xml, n = pat.subn(r'<hp:run charPrIDRef="0">\1', xml, count=1)
        if n == 1:
            xml = new_xml
            print("  risk table r0c1 charPrIDRef: 13 → 0 (regex)")
        else:
            print("  WARN: risk row charPr patch did not match")

    sec.write_text(xml, encoding="utf-8")


def main():
    unpack()
    patch()
    pack()
    print(f"\nSaved: {DST}")


if __name__ == "__main__":
    main()
