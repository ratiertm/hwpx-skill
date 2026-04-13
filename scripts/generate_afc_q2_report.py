"""Generate 2020년 2분기 AFC설비 정기점검 결과 report from Excel data.

Uses the 2021 1분기 계획서 template style but with Q2 2020 actual results.
"""
from __future__ import annotations

import sys
sys.path.insert(0, '.')

import openpyxl
from pyhwpxlib.builder import HwpxBuilder

EXCEL = 'samples/2분기_정기점검_결과(2020.04.20).xlsx'
OUT = 'Test/2020년_AFC설비_2분기_정기점검_결과.hwpx'


def load_issues():
    """Return (header_cols, issue_rows, summary_rows) from the Excel."""
    wb = openpyxl.load_workbook(EXCEL, data_only=True)
    ws = wb['이슈사항']

    rows = list(ws.iter_rows(values_only=True))
    # Find header row (contains 역명, 장비번호, 분류 ...)
    header_idx = None
    for i, r in enumerate(rows):
        if r and '역명' in r:
            header_idx = i
            break
    header = rows[header_idx]

    # Issue rows — stop at first row where 분류 cell is blank/space-only
    issues = []
    last_station = ''
    for r in rows[header_idx + 1:]:
        # r shape: (None, 역명, 장비번호, 분류, 문제사항, 상태, 비고, 조치사항, 비고2, 날짜)
        station = r[1] or ''
        eq_num = r[2]
        category = (r[3] or '').strip()
        issue = r[4] or ''
        note = r[6] or ''
        date = r[9] or ''

        if station:
            last_station = station
        if not category or category.strip() == '':
            break  # end of main table
        if eq_num is None and not issue and not note:
            break

        desc = issue or note or ''
        issues.append({
            '날짜': str(date).strip() if date else '',
            '역명': last_station,
            '장비번호': str(eq_num) if eq_num is not None else '',
            '분류': category,
            '문제/조치': desc,
        })

    # Summary rows are at the bottom (after blank rows)
    summary = []
    for r in rows[header_idx + 1:]:
        if r is None:
            continue
        name = r[2]
        cnt = r[3]
        if isinstance(name, str) and isinstance(cnt, int) and name in (
            '발권기', '발매기', '정산기', '게이트', '환급기'
        ):
            summary.append((name, cnt))
    total = sum(c for _, c in summary)
    return issues, summary, total


def build_report(issues, summary, total):
    b = HwpxBuilder()

    # Title
    b.add_heading('2020년 AFC설비 2분기 정기점검 결과', level=1, alignment='CENTER')
    b.add_paragraph('')

    # Header info (meta)
    if issues:
        dates = sorted({i['날짜'] for i in issues if i['날짜']})
        period = f"{dates[0]} ~ {dates[-1]}" if dates else ''
        stations = sorted({i['역명'] for i in issues if i['역명']})
    else:
        period = ''
        stations = []

    detail_count = len(issues)
    META_PT = 13
    b.add_paragraph(f'○ 점검기간 : {period}', font_size=META_PT)
    b.add_paragraph(f'○ 점검장소 : {", ".join(stations) if stations else ""}', font_size=META_PT)
    b.add_paragraph(f'○ 점검기관 : 롯데정보통신', font_size=META_PT)
    b.add_paragraph(
        f'○ 이슈 총 건수 : {detail_count}건  (Excel 요약표 상 {total}건)',
        font_size=META_PT,
    )
    b.add_paragraph('', font_size=META_PT)

    # Summary table: 설비 분류별 이슈 건수 (비고 제거, 본문에 별도 기재)
    b.add_heading('○ 설비별 이슈 요약', level=2)
    summary_rows = [['설비 분류', '이슈 건수']]
    for name, cnt in summary:
        summary_rows.append([name, f'{cnt}건'])
    summary_rows.append(['합계', f'{total}건'])
    b.add_table(
        summary_rows,
        col_widths=[21260, 21260],
        row_heights=[3200] + [3600] * (len(summary_rows) - 1),
    )
    b.add_paragraph('', font_size=META_PT)

    # 주요 비고 사항 (요약표에서 분리하여 본문에 기재)
    b.add_paragraph('※ 주요 비고', bold=True, font_size=META_PT)
    b.add_paragraph(
        '- 서울역 B2 발매기(201~205): 동전/지폐/승차권 보급이 안되어 있어 운영이 안되어, '
        '스피커 테스트를 진행하지 못함.',
        font_size=META_PT,
    )
    b.add_paragraph('', font_size=META_PT)

    # Detail issue table — 페이지 분리
    b.add_page_break()
    b.add_heading('○ 이슈 상세 내역', level=2)

    def _hard_wrap(text: str, max_chars: int = 30) -> str:
        """Break long text on commas/spaces to force explicit line breaks
        (rhwp renderer does not soft-wrap within cells)."""
        if len(text) <= max_chars:
            return text
        # Prefer breaking on ', ' then ' '
        parts = text.split(', ')
        lines: list[str] = []
        cur = ''
        for i, p in enumerate(parts):
            piece = p + (', ' if i < len(parts) - 1 else '')
            if not cur:
                cur = piece
            elif len(cur) + len(piece) <= max_chars:
                cur += piece
            else:
                lines.append(cur.rstrip(' ,'))
                cur = piece
        if cur:
            lines.append(cur.rstrip(' ,'))
        return '\n'.join(lines)

    header_row = ['날짜', '장비번호', '분류', '문제사항 / 조치사항']

    def _rh(text: str) -> int:
        line_count = text.count('\n') + 1
        return 1500 + line_count * 1300

    # Split issues into page-sized chunks. Each page can fit ~60000 HWP
    # units of vertical content. Header + chunk rows must stay under that.
    CHUNK_BUDGET = 55000  # leave margin
    chunks: list[list] = []
    current: list[tuple] = []
    current_h = 2500  # header row
    for it in issues:
        wrapped = _hard_wrap(it['문제/조치'], max_chars=30)
        rh = _rh(wrapped)
        if current and current_h + rh > CHUNK_BUDGET:
            chunks.append(current)
            current = []
            current_h = 2500
        current.append((
            it['날짜'], it['장비번호'], it['분류'], wrapped, rh,
        ))
        current_h += rh
    if current:
        chunks.append(current)

    for idx, chunk in enumerate(chunks):
        rows = [header_row] + [list(c[:4]) for c in chunk]
        row_heights = [2500] + [c[4] for c in chunk]
        b.add_table(
            rows,
            col_widths=[6500, 5500, 5500, 25020],
            row_heights=row_heights,
        )
        if idx < len(chunks) - 1:
            b.add_page_break()
    b.add_paragraph('')

    # Closing note
    b.add_paragraph(
        '본 보고서는 2020년 2분기 정기점검에서 발견된 이슈 사항을 정리한 것이며, '
        '조치가 필요한 항목은 역무설비팀과 협의 후 진행한다.',
        font_size=9, text_color='#666666',
    )

    return b.save(OUT)


def main():
    issues, summary, total = load_issues()
    print(f'Loaded: {len(issues)} issues, summary={summary}, total={total}')
    path = build_report(issues, summary, total)
    import os
    print(f'Saved: {path} ({os.path.getsize(path):,} bytes)')


if __name__ == '__main__':
    main()
