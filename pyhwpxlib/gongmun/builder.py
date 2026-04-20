"""GongmunBuilder — generate 공문(official document) HWPX files.

Based on 2025 행정업무운영 편람 별지 제1호·제2호 서식.
Wraps HwpxBuilder for low-level HWPX generation.

Minimal implementation (Phase 3-a): prioritizes structural correctness
(두문·본문·결문 순서, 명칭 규정, 날짜 포맷, 끝 표시) over pixel-perfect
visual reproduction. Visual fidelity can be iterated in Phase 4+.
"""
from __future__ import annotations
from pathlib import Path
from typing import Union

from ..builder import HwpxBuilder
from .schema import Gongmun, GongmunSimple, Signer
from .formatters import (
    format_date,
    format_address,
    format_phone_line,
    format_시행번호,
    format_item,
    format_attachment,
    add_end_marker,
    TWO_TA,
)


# 편람 표준 글자 크기 (rules.yaml: typography.sizes)
SIZE_기관명 = 16
SIZE_수신 = 13
SIZE_제목 = 13
SIZE_본문 = 12
SIZE_결문 = 10

COLOR_결문 = "#333333"
COLOR_구분바 = "#d9d9d9"


class GongmunBuilder:
    """공문 문서 빌더.

    Usage:
        from pyhwpxlib.gongmun import Gongmun, GongmunBuilder, signer

        doc = Gongmun(
            기관명="행정안전부",
            수신="수신자 참조",
            제목="2024년 정보공개 종합평가 계획 안내",
            본문=["공공기관을 대상으로...", "평가 담당자께서는..."],
            붙임=["2024년 정보공개 종합평가 계획 1부."],
            발신명의="행정안전부장관",
            기안자=signer("행정사무관", "김OO"),
            시행_처리과명="정보공개과",
            시행_일련번호="000",
            시행일="2025. 9. 30.",
            우편번호="30112",
            도로명주소="세종특별자치시 도움6로 42",
            홈페이지="www.mois.go.kr",
            전화="(044)205-0000",
            공개구분="대국민공개",
        )
        GongmunBuilder(doc).save("output.hwpx")
    """

    def __init__(self, data: Union[Gongmun, GongmunSimple], *,
                 theme: str = "default",
                 항목간_공백: bool = True,
                 compact: bool = False,
                 margins_mm: tuple[int, int, int, int, int, int] = (30, 15, 20, 20, 10, 10)):
        """
        Args:
            항목간_공백: 본문 항목 사이에 빈 줄 1개 추가 (편람 p52 허용 범위).
                         False면 붙여씀 (편람 기본).
            compact: True면 1페이지 맞춤 모드. 항목간_공백=False,
                     본문 앞·결문 앞 여백 최소화, 붙임 앞 빈 줄 제거.
                     편람 §4 p68 "1건 1매 주의" 원칙 준수에 유리.
            margins_mm: (상, 하, 좌, 우, 머리말, 꼬리말) mm 단위.
                        기본값은 실무 공문 표준: 상 30 / 하 15 / 좌우 20 / 머/꼬리 10.
        """
        self.data = data
        self._builder = HwpxBuilder(theme=theme)
        self.compact = compact
        # compact는 결문/붙임 주변 여백만 줄이고, 항목간 공백은 사용자 제어를 유지
        self.항목간_공백 = 항목간_공백
        self.margins_mm = margins_mm

    # ───────────────────────────────────────────────────
    # Public
    # ───────────────────────────────────────────────────

    def save(self, output_path: Union[str, Path]) -> str:
        """Build and save to output_path."""
        if isinstance(self.data, GongmunSimple):
            self._build_simple()
        else:
            self._build_general()
        out = self._builder.save(str(output_path))
        # Post-save: 공문 표준 여백 적용
        self._apply_margins(out)
        return out

    def _apply_margins(self, path: str) -> None:
        """Override page margins in saved HWPX.

        HwpxBuilder의 기본 blank template은 좌우 30mm로 좁은 컨텐츠 영역을 준다.
        공문 실무 표준은 상 30 / 하 15 / 좌우 20 / 머/꼬리 10 mm.
        section*.xml의 <hp:margin> 속성을 교체한다.
        """
        import zipfile, re, shutil, tempfile, os

        top_mm, bottom_mm, left_mm, right_mm, header_mm, footer_mm = self.margins_mm
        # 1mm = 283.46 HWPUNIT (1 inch = 25.4mm = 7200 HWPUNIT)
        def mm2hu(mm: int) -> int:
            return round(mm * 7200 / 25.4)

        new_attrs = (
            f'header="{mm2hu(header_mm)}" '
            f'footer="{mm2hu(footer_mm)}" '
            f'gutter="0" '
            f'left="{mm2hu(left_mm)}" '
            f'right="{mm2hu(right_mm)}" '
            f'top="{mm2hu(top_mm)}" '
            f'bottom="{mm2hu(bottom_mm)}"'
        )
        # 기존 <hp:margin ... /> 매칭 후 교체
        margin_re = re.compile(r'<hp:margin\s[^/>]*/>')

        # zip 내 section*.xml 모두 처리
        tmp = path + ".tmp"
        with zipfile.ZipFile(path, 'r') as zin, \
             zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                buf = zin.read(item.filename)
                if item.filename.startswith('Contents/section') and \
                   item.filename.endswith('.xml'):
                    text = buf.decode('utf-8')
                    text = margin_re.sub(f'<hp:margin {new_attrs}/>', text)
                    buf = text.encode('utf-8')
                # mimetype은 STORED 유지
                if item.filename == 'mimetype':
                    zout.writestr(item, buf, zipfile.ZIP_STORED)
                else:
                    zout.writestr(item, buf)
        shutil.move(tmp, path)

    # ───────────────────────────────────────────────────
    # 일반기안문 builder
    # ───────────────────────────────────────────────────

    def _build_general(self) -> None:
        d: Gongmun = self.data
        self._add_두문()
        self._add_본문()
        self._add_결문()

    def _add_두문(self) -> None:
        """두문: 행정기관명 + 수신 + (경유) + 제목."""
        d: Gongmun = self.data

        # 행정기관명 (중앙, 큰 글씨, 자간 여백)
        self._builder.add_paragraph(
            self._spaced(d.기관명), bold=True,
            font_size=SIZE_기관명, alignment="CENTER",
        )
        self._builder.add_paragraph("")   # 한 줄 공백

        # 수신
        self._builder.add_paragraph(
            f"수신{TWO_TA}{d.수신}", font_size=SIZE_수신,
        )
        # (경유) — 편람 p57: 없으면 빈칸, 있으면 설명문
        경유_text = f"(경유){TWO_TA}{d.경유}" if d.경유 else "(경유)"
        self._builder.add_paragraph(경유_text, font_size=SIZE_수신)

        # 제목 (밑줄 — 표현상 공백 뒤에 긴 밑줄 라인 추가)
        if d.제목:
            self._builder.add_paragraph(
                f"제목{TWO_TA}{d.제목}", font_size=SIZE_제목,
            )
            self._builder.add_line()   # 제목 아래 밑줄

    def _add_본문(self) -> None:
        d: Gongmun = self.data
        if not self.compact:
            self._builder.add_paragraph("")   # 상단 여백

        # 관련문서 표시 (선택적)
        if d.관련문서:
            self._builder.add_paragraph(
                d.관련문서, font_size=SIZE_본문,
            )
            self._builder.add_paragraph("")

        # 본문 항목들
        # 편람 p52: "가독성을 위하여 본문 항목 사이 위와 아래 여백을 자유롭게 조정 가능"
        # 각 항목은 str 또는 (headline, [sub, ...]) 형태.
        if d.본문:
            n = len(d.본문)
            for i, item in enumerate(d.본문):
                is_last_top = i == n - 1
                # 하위 항목 분리
                if isinstance(item, tuple) and len(item) == 2:
                    headline, subs = item
                else:
                    headline, subs = item, []

                # 레벨 1 헤드라인 출력
                if d.본문_자동번호:
                    head_line = format_item(level=1, index=i, content=headline)
                else:
                    head_line = headline

                # 하위 항목이 없고 마지막이면 '끝.' 이 헤드라인에 붙음
                if is_last_top and not subs and not d.붙임:
                    head_line = add_end_marker(head_line)

                self._builder.add_paragraph(head_line, font_size=SIZE_본문)

                # 레벨 2 하위 항목 출력 (가./나./다./라./...)
                m = len(subs)
                for j, sub in enumerate(subs):
                    if d.본문_자동번호:
                        sub_line = format_item(level=2, index=j, content=sub)
                    else:
                        sub_line = "  " + sub   # 들여쓰기만 추가
                    # 마지막 하위 + 이후 항목 없으면 '끝.'
                    if (j == m - 1 and is_last_top and not d.붙임):
                        sub_line = add_end_marker(sub_line)
                    self._builder.add_paragraph(sub_line, font_size=SIZE_본문)

                # 항목 간 공백 — compact 시 작은 공백 사용 (half-line 효과)
                if self.항목간_공백 and i < n - 1:
                    if self.compact:
                        self._builder.add_paragraph("", font_size=6)
                    else:
                        self._builder.add_paragraph("")

        # 붙임
        if d.붙임:
            if not self.compact:
                self._builder.add_paragraph("")   # 붙임 앞 한 줄 띄움 (선택)
            for line in format_attachment(d.붙임):
                self._builder.add_paragraph(line, font_size=SIZE_본문)

    def _add_결문(self) -> None:
        d: Gongmun = self.data
        # 결문은 본문과 약간의 여백 후 시작
        pad = 0 if self.compact else 3
        for _ in range(pad):
            self._builder.add_paragraph("")

        # 발신명의 (중앙, 큰 글씨)
        # 편람 p62 영 제13조제3항: 내부결재문서는 발신명의를 표시하지 않음
        if d.is_internal_decision():
            pass  # 내부결재: 발신명의 생략
        elif d.발신명의:
            label = d.발신명의
            if d.관인생략:
                label += f"{TWO_TA}(관인생략)"
            if d.서명생략:
                label += f"{TWO_TA}(서명생략)"
            self._builder.add_paragraph(
                self._spaced(label), bold=True,
                font_size=16, alignment="CENTER",
            )
            self._builder.add_paragraph("")

        # 수신자 (수신 = "수신자 참조"일 때)
        if d.수신자:
            self._builder.add_paragraph(
                f"수신자{TWO_TA}{d.수신자}", font_size=SIZE_결문,
                text_color=COLOR_결문,
            )
            self._builder.add_paragraph("")

        # 회색 구분선
        self._builder.add_line()
        self._builder.add_paragraph("")

        # 서명자 라인 (기안자/검토자/결재권자 — 용어는 표시 X, 직위+성명만)
        self._add_signers_line()

        # 협조자
        if d.협조자:
            co = "  ".join(f"{s.직위} {s.성명}" for s in d.협조자)
            self._builder.add_paragraph(
                f"협조자{TWO_TA}{co}", font_size=SIZE_결문,
                text_color=COLOR_결문,
            )

        # 시행/접수
        parts = []
        시행 = format_시행번호(d.시행_처리과명, d.시행_일련번호, d.시행일)
        접수 = format_시행번호(d.접수_처리과명, d.접수_일련번호, d.접수일).replace("시행", "접수") if d.접수_처리과명 else ""
        if 시행:
            parts.append(시행)
        if 접수:
            parts.append(접수)
        if parts:
            self._builder.add_paragraph(
                (TWO_TA + TWO_TA).join(parts),
                font_size=SIZE_결문, text_color=COLOR_결문,
            )

        # 주소
        if d.도로명주소:
            addr_line = format_address(d.우편번호, d.도로명주소)
            if d.홈페이지:
                addr_line += f"{TWO_TA} / {d.홈페이지}"
            self._builder.add_paragraph(
                addr_line, font_size=SIZE_결문, text_color=COLOR_결문,
            )

        # 전화/팩스/이메일/공개구분
        phone_line = format_phone_line(
            d.전화, d.팩스, d.이메일, d.공개구분,
        )
        if phone_line:
            self._builder.add_paragraph(
                phone_line, font_size=SIZE_결문, text_color=COLOR_결문,
            )

    def _add_signers_line(self) -> None:
        """기안자·검토자·결재권자 라인.

        편람 p71: 용어('기안자'·'검토자'·'결재권자')는 표시하지 않고
        직위(직급) + 서명만 표시한다.
        """
        d: Gongmun = self.data
        parts = []
        for signer in (d.기안자, d.검토자, d.결재권자):
            if signer is None:
                continue
            parts.append(self._signer_token(signer))
        if parts:
            self._builder.add_paragraph(
                (TWO_TA + TWO_TA).join(parts),
                font_size=SIZE_결문, text_color=COLOR_결문,
            )

    @staticmethod
    def _signer_token(s: Signer) -> str:
        """서명자 1명을 '직위 성명' 또는 '전결/대결 일자 성명' 형식으로."""
        prefix = ""
        if s.발의자:
            prefix += "★"
        if s.보고자:
            prefix += "●"

        tag = ""
        if s.전결:
            tag = f"전결 {s.서명일자} " if s.서명일자 else "전결 "
        elif s.대결:
            tag = f"대결 {s.서명일자} " if s.서명일자 else "대결 "

        return f"{prefix}{s.직위}{ONE_TA}{tag}{s.성명}".strip()

    # ───────────────────────────────────────────────────
    # 간이기안문 builder
    # ───────────────────────────────────────────────────

    def _build_simple(self) -> None:
        """간이기안문 — 편람 p73, p75 서식.

        레이아웃: 좌상 관리정보 표 + 우상 결재란 표 + 중앙 제목 박스
                + 하단 작성일·작성기관 중앙 정렬.

        최소 구현: 표는 1×2 레이아웃 1개 (좌:관리정보, 우:결재란),
        제목 박스는 중앙 정렬 큰 글자, 작성기관은 하단 중앙.
        """
        d: GongmunSimple = self.data
        b = self._builder

        # 상단 관리정보 + 결재란 (나란히) — 2열 표로 구현
        left = [
            ["생산등록번호", d.생산등록번호],
            ["등록일", d.등록일],
            ["결재일", d.결재일],
            ["공개 구분", d.공개구분],
        ]
        b.add_table(left, use_preset=False)

        b.add_paragraph("")

        # 협조자
        if d.협조자:
            co = "  ".join(f"{s.직위} {s.성명}" for s in d.협조자)
            b.add_paragraph(f"협조자{TWO_TA}{co}", font_size=SIZE_결문)

        # 결재 서명자 — 표로
        if d.결재_서명자:
            header = [s.직위 for s in d.결재_서명자]
            names = [s.성명 for s in d.결재_서명자]
            b.add_table([header, names])

        # 중앙 제목 박스
        for _ in range(3):
            b.add_paragraph("")
        if d.제목:
            b.add_paragraph(
                f"( {d.제목} )", bold=True,
                font_size=24, alignment="CENTER",
            )

        if d.보고근거_요약:
            b.add_paragraph("")
            b.add_paragraph(
                f"※ {d.보고근거_요약}",
                font_size=SIZE_본문, alignment="CENTER",
            )

        # 하단 여백 + 작성일
        for _ in range(5):
            b.add_paragraph("")
        if d.작성일:
            b.add_paragraph(
                d.작성일, font_size=SIZE_수신, alignment="CENTER",
            )
        b.add_paragraph("")

        # 작성기관 (중앙, 큰 글씨)
        if d.작성기관_부:
            b.add_paragraph(
                self._spaced(d.작성기관_부), bold=True,
                font_size=16, alignment="CENTER",
            )
        if d.작성기관_국과:
            b.add_paragraph(
                d.작성기관_국과, bold=True,
                font_size=14, alignment="CENTER",
            )

    # ───────────────────────────────────────────────────
    # Helpers
    # ───────────────────────────────────────────────────

    @staticmethod
    def _spaced(text: str) -> str:
        """기관명 자간 여백 (편람 예시처럼 '행 정 안 전 부' 띄워 쓰기).

        2자 이상일 때 각 글자 사이 공백 1개.
        """
        if len(text) <= 1:
            return text
        # 너무 긴 문자열에는 적용 안 함 (10자 초과 시 원본 유지)
        if len(text) > 10:
            return text
        return " ".join(text)


# 편람 p52: "1타" 상수 (기호와 내용 사이)
ONE_TA = " "
