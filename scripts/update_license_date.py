"""Rolling Change Date 갱신 스크립트.

각 릴리스 시 호출하면 LICENSE.md / README.md / README_KO.md 의 최신 버전 행을
``(version, today, today+4y)`` 로 갱신합니다.

사용:
    python scripts/update_license_date.py            # 오늘 + 4년
    python scripts/update_license_date.py --release-date 2026-05-01
    python scripts/update_license_date.py --append   # 이전 행 보존, 새 행 추가

LICENSE.md 의 표는 다음 마커 사이를 자동 갱신합니다:

    <!-- ROLLING_TABLE_START -->
    | 버전 | 릴리스일 | Change Date |
    |------|---------|------------|
    | 0.15.0 (current) | 2026-04-29 | 2030-04-29 |
    <!-- ROLLING_TABLE_END -->

마커가 없으면 처음 실행 시 자동으로 삽입합니다.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LICENSE_MD = ROOT / "LICENSE.md"
README_EN = ROOT / "README.md"
README_KO = ROOT / "README_KO.md"
PYPROJECT = ROOT / "pyproject.toml"

START = "<!-- ROLLING_TABLE_START -->"
END = "<!-- ROLLING_TABLE_END -->"


def read_version() -> str:
    txt = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', txt, flags=re.MULTILINE)
    if not m:
        raise RuntimeError("pyproject.toml 에서 version 을 찾을 수 없습니다")
    return m.group(1)


def add_four_years(d: date) -> date:
    """release_date + 4년. 윤년 2/29 는 2/28 로 안전 처리."""
    try:
        return d.replace(year=d.year + 4)
    except ValueError:
        return d.replace(month=2, day=28, year=d.year + 4)


def render_table(rows: list[tuple[str, date, date]]) -> str:
    lines = ["| 버전 | 릴리스일 | Change Date |", "|------|---------|------------|"]
    for version, rel, chg in rows:
        lines.append(f"| {version} | {rel.isoformat()} | {chg.isoformat()} |")
    return "\n".join(lines)


def parse_existing_rows(license_text: str) -> list[tuple[str, date, date]]:
    m = re.search(rf"{re.escape(START)}\s*\n(.*?)\n{re.escape(END)}",
                  license_text, flags=re.DOTALL)
    if not m:
        return []
    rows: list[tuple[str, date, date]] = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|") or "버전" in line or "----" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) != 3:
            continue
        version = parts[0].replace("(current)", "").strip()
        try:
            rel = date.fromisoformat(parts[1])
            chg = date.fromisoformat(parts[2])
        except ValueError:
            continue
        rows.append((version, rel, chg))
    return rows


def update_license(version: str, release_date: date, change_date: date,
                   append: bool) -> None:
    text = LICENSE_MD.read_text(encoding="utf-8")

    existing = parse_existing_rows(text) if append else []
    existing = [(v, r, c) for v, r, c in existing if v != version]
    rows = existing + [(f"{version} (current)", release_date, change_date)]
    new_table = render_table(rows)

    if START in text and END in text:
        text = re.sub(
            rf"{re.escape(START)}\s*\n.*?\n{re.escape(END)}",
            f"{START}\n{new_table}\n{END}",
            text, flags=re.DOTALL,
        )
    else:
        # 첫 실행 — 헤더 + 구분선 + (최소 1개) 데이터 행 전부를 마커 블록으로 교체
        static_pattern = re.compile(
            r"\| 버전 \| 릴리스일 \| Change Date \|\n"
            r"\|[\s\-|]+\|\n"
            r"(?:\|[^\n]+\|\n)+",
        )
        block = f"{START}\n{new_table}\n{END}\n"
        if static_pattern.search(text):
            text = static_pattern.sub(block, text, count=1)
        else:
            raise RuntimeError(
                "LICENSE.md 에서 Rolling 표를 찾을 수 없습니다. 수동 삽입 필요.")

    LICENSE_MD.write_text(text, encoding="utf-8")


def update_readme(path: Path, version: str, change_date: date, lang: str) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    iso = change_date.isoformat()
    if lang == "en":
        pattern = re.compile(
            r"(Rolling Change Date: each release converts to Apache 2\.0 "
            r"four years after its release date \(latest )"
            r"[^\)]+(\)\. See \[LICENSE\.md\]\(LICENSE\.md\)\.)"
        )
        replacement = rf"\g<1>{version} → {iso}\g<2>"
    else:  # ko
        pattern = re.compile(
            r"(Rolling Change Date: 각 릴리스는 릴리스일 \+ 4년 후 Apache 2\.0으로 "
            r"자동 전환 \(최신 )[^\)]+(\)\. 자세한 내용은 \[LICENSE\.md\]\(LICENSE\.md\)\.)"
        )
        replacement = rf"\g<1>{version} → {iso}\g<2>"

    new_text, n = pattern.subn(replacement, text)
    if n == 0:
        print(f"  ! {path.name}: Rolling 줄을 찾지 못해 건너뜀", file=sys.stderr)
        return
    path.write_text(new_text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--release-date",
                   help="ISO 형식 (YYYY-MM-DD). 생략 시 오늘.")
    p.add_argument("--version", help="릴리스 버전. 생략 시 pyproject.toml 에서 추출.")
    p.add_argument("--append", action="store_true",
                   help="이전 버전 행을 보존하고 새 행 추가 (히스토리 유지)")
    args = p.parse_args(argv)

    version = args.version or read_version()
    release_date = (date.fromisoformat(args.release_date)
                    if args.release_date else date.today())
    change_date = add_four_years(release_date)

    print(f"pyhwpxlib {version}")
    print(f"  릴리스일      : {release_date.isoformat()}")
    print(f"  Change Date  : {change_date.isoformat()} (+ 4년)")
    print(f"  history append: {args.append}")
    print()

    update_license(version, release_date, change_date, append=args.append)
    print(f"  ✓ LICENSE.md")
    update_readme(README_EN, version, change_date, lang="en")
    print(f"  ✓ README.md")
    update_readme(README_KO, version, change_date, lang="ko")
    print(f"  ✓ README_KO.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
