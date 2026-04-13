"""Fill 의견제출서 form with sample data.

Strategy: unpack → find empty <hp:t> in target cells by cellAddr → insert text → repack.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, '.')

SRC = Path("Test/doc_sample.hwpx")
DST = Path("Test/의견제출서_홍길동.hwpx")
WORK = Path("/tmp/opinion_fill")

# Sample data
FILL_DATA = {
    "성명": "홍길동",
    "전화번호": "010-1234-5678",
    "주소": "부산시 남구 대연동 123-45",
    "의견": "통학구역 조정에 찬성합니다. 학생 안전을 위해 적극 지지합니다.",
    "기타": "없음",
    "날짜": "2025년  3월  15일",
}


def fill():
    if WORK.exists():
        shutil.rmtree(WORK)
    subprocess.run(
        [sys.executable, "-m", "pyhwpxlib", "unpack", str(SRC), "-o", str(WORK)],
        check=True,
    )

    sec = WORK / "Contents" / "section0.xml"
    xml = sec.read_text(encoding="utf-8")

    # Strategy: each empty value cell has a pattern like:
    #   <hp:cellAddr colAddr="X" rowAddr="Y"/>
    # preceded by a <hp:t/> or <hp:t></hp:t> (empty text node).
    # We locate the cell by cellAddr and fill the FIRST empty <hp:t> inside it.

    # Cell targets: (colAddr, rowAddr) → fill text
    targets = [
        ("3", "2", FILL_DATA["성명"]),       # r2 col3 = 성명 값
        ("5", "2", FILL_DATA["전화번호"]),    # r2 col5 = 전화번호 값
        ("3", "3", FILL_DATA["주소"]),        # r3 col3 = 주소 값
        ("3", "4", FILL_DATA["의견"]),        # r4 col3 = 의견 값
        ("3", "5", FILL_DATA["기타"]),        # r5 col3 = 기타 값
    ]

    for col, row, text in targets:
        addr_pat = f'colAddr="{col}" rowAddr="{row}"'
        addr_idx = xml.find(addr_pat)
        if addr_idx < 0:
            print(f"  WARN: cellAddr {col},{row} not found")
            continue

        # Walk backward to find the <hp:tc that contains this cellAddr
        tc_start = xml.rfind("<hp:tc", 0, addr_idx)
        # Walk forward to find </hp:tc>
        tc_end = xml.find("</hp:tc>", addr_idx) + len("</hp:tc>")
        tc_block = xml[tc_start:tc_end]

        # Find the first empty <hp:t> (either <hp:t/> or <hp:t></hp:t>)
        new_block = tc_block
        # Try <hp:t/> first
        if "<hp:t/>" in new_block:
            new_block = new_block.replace("<hp:t/>", f"<hp:t>{text}</hp:t>", 1)
        elif "<hp:t></hp:t>" in new_block:
            new_block = new_block.replace("<hp:t></hp:t>", f"<hp:t>{text}</hp:t>", 1)
        else:
            # Find <hp:t> with None-like content
            empty_t = re.search(r"<hp:t>(\s*)</hp:t>", new_block)
            if empty_t:
                new_block = new_block[:empty_t.start()] + f"<hp:t>{text}</hp:t>" + new_block[empty_t.end():]

        xml = xml[:tc_start] + new_block + xml[tc_end:]
        print(f"  filled ({col},{row}): {text}")

    # Fill date line: "2025년    월    일" → "2025년  3월  15일"
    xml = xml.replace(
        ">2025년    월    일<",
        f">{FILL_DATA['날짜']}<",
        1,
    )
    # Fill 제출인 주소
    xml = xml.replace(
        ">       제출인  주   소<",
        f">       제출인  주   소  {FILL_DATA['주소']}<",
        1,
    )
    # Fill 제출인 성명
    xml = xml.replace(
        ">               성   명                              (서명 또는 인)<",
        f">               성   명  {FILL_DATA['성명']}          (서명 또는 인)<",
        1,
    )
    print("  filled: 날짜, 제출인 주소, 성명")

    sec.write_text(xml, encoding="utf-8")

    if DST.exists():
        DST.unlink()
    subprocess.run(
        [sys.executable, "-m", "pyhwpxlib", "pack", str(WORK), "-o", str(DST)],
        check=True,
    )
    print(f"\nSaved: {DST}")


if __name__ == "__main__":
    fill()
