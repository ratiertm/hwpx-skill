"""한국 공문(official document) generation package.

Based on 「2025 행정업무운영 편람」 (행정안전부).
Generates HWPX documents that comply with Korean government
document standards (규칙 제3조·제4조, 별지 제1호·제2호 서식).

Quick start::

    from pyhwpxlib.gongmun import Gongmun, GongmunBuilder, signer

    doc = Gongmun(
        기관명="행정안전부",
        수신="수신자 참조",
        제목="2024년 정보공개 종합평가 계획 안내",
        본문=[
            "「공공기관의 정보공개에 관한 법률」제24조에 의거 공공기관의 "
            "정보공개제도 운영 실태 평가를 위한 '2024년 정보공개 종합평가 "
            "계획'을 붙임과 같이 안내합니다.",
        ],
        붙임=["2024년 정보공개 종합평가 계획 1부."],
        발신명의="행정안전부장관",
        수신자="2024년 정보공개 종합평가 대상 기관(554개)",
        기안자=signer("행정사무관", "김OO"),
        검토자=signer("서기관", "홍OO"),
        결재권자=signer("정보공개과장", "김OO", 전결=True, 서명일자="2025. 9. 30."),
        시행_처리과명="정보공개과",
        시행_일련번호="000",
        시행일="2025. 9. 30.",
        우편번호="30112",
        도로명주소="세종특별자치시 도움6로 42 정부세종청사 중앙동",
        홈페이지="www.mois.go.kr",
        전화="(044)205-0000",
        팩스="(044)204-0000",
        이메일="abcde@mois.go.kr",
        공개구분="대국민공개",
    )
    GongmunBuilder(doc).save("output.hwpx")
"""

from .schema import (
    Gongmun,
    GongmunSimple,
    BulkGongmun,
    JointGongmun,
    Signer,
    signer,
)
from .builder import GongmunBuilder
from .reader import read_license, license_summary
from .validator import (
    Finding,
    Severity,
    validate_file,
    validate_text,
    format_report,
)
from .formatters import (
    format_date,
    format_datetime_with_weekday,
    format_time,
    format_money,
    to_korean_number,
    add_end_marker,
    format_attachment,
    format_item,
    item_marker,
    item_indent,
    format_address,
    format_phone_line,
    format_시행번호,
    format_related_doc,
    TWO_TA,
    ONE_TA,
)

__all__ = [
    # Schema
    "Gongmun",
    "GongmunSimple",
    "BulkGongmun",
    "JointGongmun",
    "Signer",
    "signer",
    # Builder
    "GongmunBuilder",
    # Reader
    "read_license",
    "license_summary",
    # Validator
    "Finding",
    "Severity",
    "validate_file",
    "validate_text",
    "format_report",
    # Formatters
    "format_date",
    "format_datetime_with_weekday",
    "format_time",
    "format_money",
    "to_korean_number",
    "add_end_marker",
    "format_attachment",
    "format_item",
    "item_marker",
    "item_indent",
    "format_address",
    "format_phone_line",
    "format_시행번호",
    "format_related_doc",
    "TWO_TA",
    "ONE_TA",
]
