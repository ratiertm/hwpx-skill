"""Tests for HwpxBuilder — high-level document builder."""
import os
import zipfile
import pytest
from pathlib import Path

from scripts.create import HwpxBuilder, TABLE_PRESETS


OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# 기본 동작
# ============================================================

class TestBasicBuilder:
    def test_empty_document(self):
        doc = HwpxBuilder()
        out = doc.save(str(OUTPUT_DIR / "empty.hwpx"))
        assert os.path.exists(out)
        assert os.path.getsize(out) > 0

    def test_heading_and_paragraph(self):
        doc = HwpxBuilder()
        doc.add_heading("테스트 제목", level=1)
        doc.add_paragraph("본문 텍스트입니다.")
        out = doc.save(str(OUTPUT_DIR / "heading_para.hwpx"))
        assert os.path.exists(out)


# ============================================================
# 표 스타일 프리셋
# ============================================================

class TestTablePresets:
    def test_default_preset_applies_header_bg(self):
        """프리셋 기본값으로 헤더 배경색이 적용되는지 확인"""
        doc = HwpxBuilder()  # default preset
        doc.add_table([["Header", "Col2"], ["Data1", "Data2"]])
        action = doc._actions[0]
        assert action['cell_colors'] is not None
        assert (0, 0) in action['cell_colors']
        assert action['cell_colors'][(0, 0)] == '#395da2'

    def test_corporate_preset(self):
        doc = HwpxBuilder(table_preset='corporate')
        doc.add_table([["매출", "영업이익"], ["100억", "20억"]])
        action = doc._actions[0]
        assert action['cell_colors'][(0, 0)] == '#395da2'
        assert action['cell_margin'] == (283, 283, 200, 200)
        assert action['row_heights'][0] == 2400  # header
        # 헤더 흰색 텍스트 자동 적용
        assert action['cell_styles'][(0, 0)]['text_color'] == '#f7f7ff'

    def test_academic_preset_no_header_bg(self):
        doc = HwpxBuilder(table_preset='academic')
        doc.add_table([["변수", "값"], ["x", "1"]])
        action = doc._actions[0]
        # academic: 배경색 없음
        assert action['cell_colors'] is None

    def test_government_preset(self):
        doc = HwpxBuilder(table_preset='government')
        doc.add_table([["항목", "내용"], ["제목", "설명"]])
        action = doc._actions[0]
        assert action['cell_margin'] == (425, 425, 283, 283)
        assert action['cell_styles'][(0, 0)]['text_color'] == '#f7f7ff'

    def test_explicit_params_override_preset(self):
        """명시적 파라미터가 프리셋보다 우선"""
        doc = HwpxBuilder(table_preset='corporate')
        doc.add_table(
            [["A", "B"], ["1", "2"]],
            header_bg='#FF0000',
            cell_margin=(100, 100, 50, 50),
            row_heights=[2000, 1000],
        )
        action = doc._actions[0]
        assert action['cell_colors'][(0, 0)] == '#FF0000'
        assert action['cell_margin'] == (100, 100, 50, 50)
        assert action['row_heights'] == [2000, 1000]

    def test_empty_header_bg_disables_color(self):
        """header_bg='' 로 명시적으로 배경색 없음"""
        doc = HwpxBuilder()  # default has header_bg
        doc.add_table([["A", "B"], ["1", "2"]], header_bg='')
        action = doc._actions[0]
        assert action['cell_colors'] is None

    def test_use_preset_false(self):
        """use_preset=False면 프리셋 미적용"""
        doc = HwpxBuilder(table_preset='corporate')
        doc.add_table([["A", "B"], ["1", "2"]], use_preset=False)
        action = doc._actions[0]
        # 프리셋 없이 기본값: cell_margin None → 프리셋 적용 안 됨
        # header_bg None → preset 없으므로 '' → cell_colors None
        assert action['cell_colors'] is None


# ============================================================
# 페이지 분리
# ============================================================

class TestPageBreak:
    def test_page_break_recorded(self):
        doc = HwpxBuilder()
        doc.add_heading("표지", level=1)
        doc.add_page_break()
        doc.add_heading("본문", level=1)
        assert doc._actions[1]['kind'] == 'page_break'

    def test_cover_and_body_pages(self):
        """표지 + 페이지 나누기 + 본문 문서 생성"""
        doc = HwpxBuilder(table_preset='corporate')
        # 표지
        doc.add_paragraph("")  # 상단 여백
        doc.add_paragraph("")
        doc.add_heading("NVDA 투자 분석 보고서", level=1, alignment='CENTER')
        doc.add_paragraph("")
        doc.add_paragraph("2026년 4월", font_size=14, alignment='CENTER')
        doc.add_paragraph("")
        doc.add_paragraph("작성: 투자전략팀", font_size=12,
                           text_color="#888888", alignment='CENTER')
        # 페이지 나누기
        doc.add_page_break()
        # 본문
        doc.add_heading("1. 핵심 요약", level=2)
        doc.add_table([
            ["지표", "현재", "목표"],
            ["주가", "$184.86", "$250"],
            ["P/E", "45.6배", "35배"],
        ])
        out = doc.save(str(OUTPUT_DIR / "cover_body.hwpx"))
        assert os.path.exists(out)
        assert os.path.getsize(out) > 0


# ============================================================
# Alignment
# ============================================================

class TestAlignment:
    def test_center_paragraph(self):
        doc = HwpxBuilder()
        doc.add_paragraph("가운데 정렬", alignment='CENTER')
        action = doc._actions[0]
        assert action['alignment'] == 'CENTER'

    def test_center_heading(self):
        doc = HwpxBuilder()
        doc.add_heading("중앙 제목", level=1, alignment='CENTER')
        action = doc._actions[0]
        assert action['alignment'] == 'CENTER'

    def test_alignment_in_save(self):
        """alignment가 save()에서 에러 없이 처리되는지"""
        doc = HwpxBuilder()
        doc.add_paragraph("왼쪽", alignment='LEFT')
        doc.add_paragraph("중앙", bold=True, font_size=20, alignment='CENTER')
        doc.add_heading("오른쪽 제목", level=2, alignment='RIGHT')
        out = doc.save(str(OUTPUT_DIR / "alignment.hwpx"))
        assert os.path.exists(out)


# ============================================================
# 통합 테스트: 기업 보고서 전체 생성
# ============================================================

class TestCorporateReport:
    def test_full_corporate_report(self):
        doc = HwpxBuilder(table_preset='corporate')

        # 표지
        for _ in range(5):
            doc.add_paragraph("")
        doc.add_heading("분기별 실적 보고서", level=1, alignment='CENTER')
        doc.add_paragraph("")
        doc.add_paragraph("2026년 1분기", font_size=16, alignment='CENTER')
        doc.add_paragraph("주식회사 예시컴퍼니", font_size=12,
                           text_color="#888888", alignment='CENTER')
        doc.add_page_break()

        # 목차 (수동)
        doc.add_heading("목차", level=2)
        doc.add_paragraph("1. 경영 실적 요약")
        doc.add_paragraph("2. 재무제표")
        doc.add_paragraph("3. 향후 전망")
        doc.add_page_break()

        # 본문
        doc.add_heading("1. 경영 실적 요약", level=2)
        doc.add_paragraph("2026년 1분기 매출은 전년 대비 15% 증가한 500억원을 기록하였습니다.")
        doc.add_table([
            ["구분", "당기", "전기", "증감"],
            ["매출액", "500억", "435억", "+15%"],
            ["영업이익", "80억", "65억", "+23%"],
            ["순이익", "55억", "42억", "+31%"],
        ])

        doc.add_paragraph("")
        doc.add_heading("2. 재무제표", level=2)
        doc.add_table([
            ["계정과목", "금액", "비율"],
            ["자산총계", "2,000억", "100%"],
            ["부채총계", "800억", "40%"],
            ["자본총계", "1,200억", "60%"],
        ])

        out = doc.save(str(OUTPUT_DIR / "corporate_report.hwpx"))
        assert os.path.exists(out)
        size = os.path.getsize(out)
        assert size > 5000  # 의미 있는 크기
        # hwpx는 zip이므로 유효한 zip인지 확인
        assert zipfile.is_zipfile(out)
