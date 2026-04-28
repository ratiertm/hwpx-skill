"""Slugify Korean labels into ASCII keys for schema fields.

Strategy: small mapping table for common form labels, then fallback to
romanization-free placeholder ``field_NNN`` when no mapping matches.
The full Korean label is preserved on each field as ``label`` and on the
schema as ``name_kr``, so nothing is lost.
"""
from __future__ import annotations

import re
import unicodedata


# Common Korean form labels → English snake_case key
_LABEL_MAP = {
    # 인적사항
    "팀명": "team_name", "팀  명": "team_name", "팀 명": "team_name",
    "성명": "name", "성  명": "name", "성 명": "name", "이름": "name",
    "학과": "dept", "학과(부)": "dept", "학  과": "dept", "학  과(부)": "dept",
    "학번": "student_id", "학  번": "student_id",
    "서명": "signature", "서  명": "signature", "(인)": "signature",
    "구분": "category", "구  분": "category",
    "주소": "address", "주  소": "address",
    "연락처": "contact", "전화": "phone", "휴대폰": "mobile",
    "이메일": "email", "메일": "email",
    "본명": "real_name",
    # 프로젝트
    "프로젝트명": "project_name", "프로젝트": "project_name",
    "사업명": "project_name",
    "활동기간": "period", "기간": "period",
    "활동내용": "activity", "활용내용": "activity",
    "수행내용": "activity",
    # 보고
    "최종보고서류 작성일": "report_date",
    "작성일": "draft_date", "제출일": "submit_date",
    "보고서": "report",
    # 금액
    "지급액": "amount", "지 급 액": "amount",
    "지급시기": "payment_schedule",
    "계좌정보": "account", "계좌": "account",
    "단가": "unit_price", "총액": "total_amount",
    "정산": "settlement",
    # 사진/첨부
    "사진": "photo", "활동사진": "photo",
    "첨부": "attachment", "붙임": "attachment",
    # 일반
    "비고": "remarks", "기타": "etc",
    "기관명": "org", "회사명": "company", "소속": "affiliation",
    "직위": "position", "직급": "rank",
    "프로그램명": "program_name",
    "용역": "service",
    "경력사항": "career", "학력": "education",
    "역할": "role", "담당": "responsibility",
    # 행 그룹 라벨 (rs > 1 셀에서 등장하는 그룹 레이블)
    "참여자": "member", "참 여 자": "member", "참여 자": "member",
    "회원": "member", "위원": "committee", "직원": "staff",
    "신청인": "applicant", "신청자": "applicant",
    "학생": "student", "응시자": "applicant",
    "지원자": "applicant",
}


def slugify(text: str, fallback_index: int = 0) -> str:
    """Slugify a single label string into a snake_case ASCII key.

    1. Strip whitespace
    2. Look up in mapping table (exact + collapsed)
    3. Fallback: drop accents, keep [a-z0-9_], else ``field_NNN``.
    """
    t = (text or "").strip()
    if not t:
        return f"field_{fallback_index}"

    if t in _LABEL_MAP:
        return _LABEL_MAP[t]
    collapsed = re.sub(r"\s+", "", t)
    if collapsed in _LABEL_MAP:
        return _LABEL_MAP[collapsed]

    # Strip accents
    n = unicodedata.normalize("NFKD", t)
    ascii_only = "".join(c for c in n if not unicodedata.combining(c))
    ascii_only = re.sub(r"[^A-Za-z0-9]+", "_", ascii_only).strip("_").lower()
    if ascii_only and re.search(r"[a-z]", ascii_only):
        return ascii_only
    return f"field_{fallback_index}"


def label_to_key(label: str, used: set, fallback_index: int = 0) -> str:
    """Slugify and disambiguate against an already-used set.

    Adds ``_2``, ``_3``, ... suffix on collisions.
    """
    base = slugify(label, fallback_index=fallback_index)
    if base not in used:
        used.add(base)
        return base
    n = 2
    while f"{base}_{n}" in used:
        n += 1
    new_key = f"{base}_{n}"
    used.add(new_key)
    return new_key
