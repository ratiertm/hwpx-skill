"""Dataclass schema for 공문(official documents).

Based on 2025 행정업무운영 편람, 규칙 제3조·제4조.
See rules.yaml for the full rule codification.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional
from datetime import date as _date


# ──────────────────────────────────────────────────────────
# Common types
# ──────────────────────────────────────────────────────────

@dataclass
class Signer:
    """기안자/검토자/협조자/결재권자.

    편람 p71: 용어('기안자'·'검토자'·'결재권자') 자체는 표시하지 않고,
    직위/직급과 서명만 표시한다.
    """
    직위: str                       # 예: "행정사무관", "서기관", "과장"
    성명: str                       # 예: "김갑동"
    서명일자: Optional[str] = None  # 예: "2025. 9. 30." (전결·대결 시 필수)
    전결: bool = False               # "전결" 표시 여부
    대결: bool = False               # "대결" 표시 여부
    발의자: bool = False             # ★ 표시
    보고자: bool = False             # ● 표시


DisclosureKind = Literal["공개", "부분공개", "비공개", "대국민공개"]

LicenseKind = Literal["KOGL", "CCL", None]
"""저작권 라이선스 종류.

- KOGL (공공누리): 공공저작물 자유이용 허락 — 정부 공개 문서 표준
    유형 1: 출처표시
    유형 2: 출처표시 + 상업적 이용금지
    유형 3: 출처표시 + 변경금지
    유형 4: 출처표시 + 상업적 이용금지 + 변경금지
- CCL (Creative Commons): 국제 표준 라이선스
    flag는 BY(1) + SA(2) + NC(4) + ND(8) 비트마스크 조합
- None: 라이선스 미적용 (내부 비공개 문서)
"""


# ──────────────────────────────────────────────────────────
# 일반기안문 (규칙 제3조제1항, 별지 제1호서식)
# ──────────────────────────────────────────────────────────

@dataclass
class Gongmun:
    """일반기안문/시행문 데이터.

    대외 발송용 일반 공문. 두문/본문/결문 3부 구성.
    """
    # ── 두문 ──
    기관명: str                       # 예: "행정안전부" (중앙 정렬 표시)
    수신: str                         # 예: "수신자 참조", "국무조정실장", "내부결재"
    경유: str = ""                    # 경유기관 (없으면 빈 문자열)
    제목: str = ""                    # 제목 (밑줄 표시)

    # ── 본문 ──
    관련문서: str = ""                # 예: "ㅇㅇ부 ㅇㅇㅇ과-123(2025. 9. 20., '제목')호"
    본문: list = field(default_factory=list)
    # 각 항목은 str 또는 tuple(str, list[str]) 형태.
    #   - str: 레벨 1 단락 (1. 2. 3. 자동 부여)
    #   - (headline, [sub1, sub2, ...]): 레벨 1 headline 아래 레벨 2 가./나./다./라. 자동 부여
    # 예시:
    #   본문 = [
    #       "도입 문단",
    #       ("계약 개요", [
    #           "계약명: ...",
    #           "계약 금액: ...",
    #       ]),
    #       "마무리 문단",
    #   ]
    본문_자동번호: bool = True         # True면 자동으로 1. 가. 1) ... 부여
    붙임: list[str] = field(default_factory=list)   # 예: ["서식승인 목록 1부.", "승인서식 2부."]

    # ── 결문 ──
    발신명의: str = ""                # 예: "행정안전부장관" (중앙, 큰 글씨)
    수신자: str = ""                  # 수신 = "수신자 참조"일 때 실제 수신기관 목록
    기안자: Optional[Signer] = None
    검토자: Optional[Signer] = None
    결재권자: Optional[Signer] = None
    협조자: list[Signer] = field(default_factory=list)

    # 시행번호·시행일
    시행_처리과명: str = ""           # 예: "정보공개과"
    시행_일련번호: str = ""           # 예: "000" 또는 "840"
    시행일: str = ""                  # YYYY. M. D.
    접수_처리과명: str = ""
    접수_일련번호: str = ""
    접수일: str = ""

    # 주소 블록
    우편번호: str = ""                # 예: "30112" (접두어 "우" 자동 부착)
    도로명주소: str = ""              # 예: "세종특별자치시 도움6로 42 정부세종청사 중앙동"
    홈페이지: str = ""                # 예: "www.mois.go.kr"
    전화: str = ""                    # 예: "(044)205-0000"
    팩스: str = ""                    # 예: "(044)204-0000"
    이메일: str = ""                  # 예: "abcde@mois.go.kr"
    공개구분: DisclosureKind = "공개"
    관인생략: bool = False
    서명생략: bool = False

    # 저작권 라이선스 (공공누리/CCL)
    # 편람 대응: 공공기관 문서는 공공누리 제1유형(KOGL 1)을 원칙으로 표기
    라이선스_종류: LicenseKind = None   # "KOGL" / "CCL" / None
    라이선스_유형: Optional[int] = None  # KOGL: 1~4 / CCL: BY+SA+NC+ND 비트마스크

    def is_internal_decision(self) -> bool:
        """내부결재문서 여부."""
        return self.수신.strip() == "내부결재"


# ──────────────────────────────────────────────────────────
# 간이기안문 (규칙 제3조제1항, 별지 제2호서식)
# ──────────────────────────────────────────────────────────

@dataclass
class GongmunSimple:
    """간이기안문 데이터.

    내부결재 전용 (보고서·계획서·검토서).
    시행문으로 변환 불가 (규칙 제3조제3항).
    """
    # 좌상 관리정보
    생산등록번호: str                  # 예: "정보공개과-840"
    등록일: str                        # "YYYY. M. D."
    결재일: str
    공개구분: DisclosureKind = "공개"

    # 우상 결재란 — 직위별 서명
    결재_서명자: list[Signer] = field(default_factory=list)
    협조자: list[Signer] = field(default_factory=list)

    # 중앙 제목
    제목: str = ""
    보고근거_요약: str = ""             # 제목 아래 선택적 요약

    # 하단
    작성일: str = ""                   # "YYYY. M. D."
    작성기관_부: str = ""              # 예: "행정안전부"
    작성기관_국과: str = ""            # 예: "정보공개과" 또는 "정부혁신국"


# ──────────────────────────────────────────────────────────
# 일괄기안 / 공동기안
# ──────────────────────────────────────────────────────────

@dataclass
class BulkGongmun:
    """일괄기안: 서로 관련된 2+ 안건을 동시에 기안.

    각 안건은 완전한 Gongmun 객체로 구성되며,
    각각의 두문·본문·결문을 모두 갖춘다 (편람 p76).
    '제1안·제2안' 용어 사용 금지.
    """
    안건_목록: list[Gongmun] = field(default_factory=list)
    공통_등록일: str = ""


@dataclass
class JointGongmun:
    """공동기안: 2+ 행정기관 공동 명의.

    주관기관 먼저, 관계기관 뒤. 관인은 주관기관만 날인.
    """
    주관기관_문서: Gongmun = None
    관계기관: list[tuple[str, str]] = field(default_factory=list)  # [(기관명, 서명자)]
    결재_레이아웃: Literal["가로", "세로"] = "가로"


# ──────────────────────────────────────────────────────────
# Convenience helpers
# ──────────────────────────────────────────────────────────

def signer(직위: str, 성명: str, **kwargs) -> Signer:
    """Shorthand: signer('행정사무관', '김OO')."""
    return Signer(직위=직위, 성명=성명, **kwargs)
