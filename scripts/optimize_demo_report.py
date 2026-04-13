"""Autonomous layout optimization for demo_report.hwpx.

Iterates by tuning font sizes and spacing until page fill ratio >= TARGET.
Claude inspects the resulting PNG visually for quality at each step.
"""
from pyhwpxlib.builder import HwpxBuilder
import sys
sys.path.insert(0, '.')
from scripts.preview import render_pages

TARGET_FILL = 0.88


def build(body_pt: int, spacer_pt: int, row_h: int, out: str) -> str:
    doc = HwpxBuilder()
    doc.add_heading("NVDA 투자 분석 보고서", level=1)
    doc.add_paragraph("2026년 1월 14일", font_size=12, text_color="#888888")
    doc.add_paragraph("", font_size=spacer_pt)

    doc.add_table(
        [
            ["종목", "등급", "현재가", "목표가"],
            ["NVDA", "Strong Buy", "$184.86", "$250 (+35%)"],
        ],
        row_heights=[row_h, row_h],
    )
    doc.add_paragraph("", font_size=spacer_pt)

    doc.add_heading("핵심 포인트", level=2)
    doc.add_paragraph(
        "토큰 비용 90% 절감. ChatGPT 돌리는 비용이 10분의 1로 줄어듭니다.",
        font_size=body_pt,
    )
    doc.add_paragraph("", font_size=spacer_pt)

    doc.add_heading("밸류에이션", level=2)
    doc.add_table(
        [
            ["P/E", "Forward P/E", "PEG Ratio"],
            ["45.6배", "35배", "0.78"],
        ],
        row_heights=[row_h, row_h],
    )
    doc.add_paragraph("", font_size=spacer_pt)

    doc.add_paragraph(
        "본 글은 투자 권유가 아닌 정보 제공 목적으로 작성되었습니다.",
        font_size=10, text_color="#999999",
    )
    return doc.save(out)


def try_params(body_pt, spacer_pt, row_h):
    path = build(body_pt, spacer_pt, row_h, "Test/demo_report_opt.hwpx")
    results = render_pages(path, "/tmp")
    fill = results[0]["fill_ratio"]
    pages = len(results)
    print(f"body={body_pt} spacer={spacer_pt} row_h={row_h} -> fill={fill:.2f} pages={pages}")
    return fill, pages, results[0]["png"]


if __name__ == "__main__":
    # Start conservative, escalate
    fill, pages, png = try_params(
        body_pt=int(sys.argv[1]) if len(sys.argv) > 1 else 14,
        spacer_pt=int(sys.argv[2]) if len(sys.argv) > 2 else 16,
        row_h=int(sys.argv[3]) if len(sys.argv) > 3 else 3000,
    )
    print(f"PNG: {png}")
