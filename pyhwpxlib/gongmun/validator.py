"""Gongmun compliance validator.

Scans a generated HWPX document (or raw text) against the 2025 행정업무운영 편람
rules codified in rules.yaml.

Returns a list of Finding objects. Severity levels:
- ERROR   : clear violation (must fix)
- WARNING : suspicious pattern (likely violation)
- INFO    : style recommendation (편람 권장 사항)
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional, Union


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Finding:
    severity: Severity
    code: str           # e.g. "DATE_FORMAT", "AUTHORITATIVE_TONE"
    message: str        # human-readable description
    excerpt: str = ""   # snippet of offending text
    rule_ref: str = ""  # 편람 reference (e.g. "§4 p49")

    def __str__(self) -> str:
        loc = f" [{self.rule_ref}]" if self.rule_ref else ""
        snip = f" — '{self.excerpt}'" if self.excerpt else ""
        return f"[{self.severity}] {self.code}{loc}: {self.message}{snip}"


# ──────────────────────────────────────────────────────────
# Rule definitions (extracted from rules.yaml)
# ──────────────────────────────────────────────────────────

# 1. 날짜 포맷 — "2025. 9. 20." / "1985. 9. 6."
# 올바름: 공백 포함 마침표, 월·일 0 제거
RE_DATE_GOOD = re.compile(r"\b\d{4}\.\s\d{1,2}\.\s\d{1,2}\.(?!\d)")
RE_DATE_BAD_ZERO = re.compile(r"\b\d{4}\.\s0\d\.\s\d{1,2}\.")  # 0 남아있음
RE_DATE_BAD_NOSPACE = re.compile(r"\b\d{4}\.\d{1,2}\.\d{1,2}\.(?!\d)")  # 공백 없음
RE_DATE_DASH = re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b")  # dash 사용 (한국 공문에선 쓰지 않음)

# 2. 위압적 어미
FORBIDDEN_ENDINGS = [
    (r"할\s*것[\.\s]", "할 것",
     "위압감을 주는 표현. '하시기 바랍니다' 또는 '하십시오'로 대체 권장"),
    (r"하기\s*바람[\.\s]?", "하기 바람",
     "위압감을 주는 표현. '하시기 바랍니다'로 대체 권장"),
    (r"제출\s*바람[\.\s]?", "제출 바람",
     "'제출하시기 바랍니다'로 대체 권장"),
    (r"참석\s*바람[\.\s]?", "참석 바람",
     "'참석하시기 바랍니다'로 대체 권장"),
    (r"문의\s*바람[\.\s]?", "문의 바람",
     "'문의하시기 바랍니다'로 대체 권장"),
]

# 3. 권위적 표현
AUTHORITATIVE_TERMS = [
    ("치하했다", "말했다", "권위적 표현"),
    ("치하하", "언급하", "권위적 표현"),
    ("영접", "맞이", "권위적 표현 (행정기관 간)"),
]

# 4. 차별적 표현
DISCRIMINATORY_TERMS = [
    ("결손가정", "한 부모 가정", "차별적 표현 — 성별/가족 구성 차별"),
    ("자매결연", "업무협약 / 우호교류", "성별 비유 기반 표현"),
    ("절름발이 행정", "기울어진 행정 / 편중된 행정", "장애 비하 표현"),
    ("학부형", "학부모", "성차별 표현"),
]

# 5. 한글호환영역 특수문자 (유니코드 U+3200~U+33FF 일부 — 기계판독성 저해)
#    편람 p35 + p51: 전자적으로 입력하기 어렵거나 오류 발생 가능한 특수기호 사용 금지
#    주요 대상: ㉠~㉿, ㈀~㈎, ㊀~㊺, ㎕~㏿ 등
def is_hangul_compat_special(ch: str) -> bool:
    """한글 호환 영역 특수문자인지."""
    cp = ord(ch)
    # 괄호 한글 자모 (㈀-㉿), 원 한글 자모 (㉠-㉯), 단위 기호 (㎕-㎽)
    return (
        0x3131 <= cp <= 0x318E or   # 한글 자모
        0x3200 <= cp <= 0x321E or   # 괄호 한글 자모
        0x3260 <= cp <= 0x327E or   # 원 한글 자모
        0x327F <= cp <= 0x32B0 or   # 원문자 (㉮ 등)
        0x3371 <= cp <= 0x33DF or   # CJK 호환 기호 (㎕ 등)
        0x3380 <= cp <= 0x33DF
    )

# 단, 편람이 직접 사용하는 "①~⑩" (U+2460~U+2469)은 허용
#    - 이는 enclosed alphanumerics, 국제 유니코드 표준
ALLOWED_ENCLOSED_NUMS = set(range(0x2460, 0x2474))  # ①~⑳

# 6. 영문 약어 — 괄호 안 한글 설명 없으면 경고
ENGLISH_ABBREVS = [
    "AI", "B2B", "P2P", "ICT", "IoT", "MOU", "IR", "ODA",
    "R&D", "Task Force", "TF", "KPI",
]

# 7. 외래어 오표기
LOANWORD_ERRORS = {
    "컨퍼런스": "콘퍼런스",
    "서포터즈": "서포터스",
    "숏츠": "쇼트 폼",
    "메세지": "메시지",
    "뱃지": "배지",
    "어플리케이션": "애플리케이션",
    "워크샵": "워크숍",
    "파트너쉽": "파트너십",
}

# 8. 두음법칙 오류
DUEUM_ERRORS = {
    "년간": "연간",
    "시설 년도": "시설 연도",
    "회계 년도": "회계 연도",
    "남여": "남녀",
}


# ──────────────────────────────────────────────────────────
# Validator
# ──────────────────────────────────────────────────────────

def _check_date_format(text: str) -> list[Finding]:
    out = []
    for m in RE_DATE_BAD_NOSPACE.finditer(text):
        out.append(Finding(
            Severity.ERROR, "DATE_FORMAT",
            "날짜 포맷 오류: 마침표 뒤 공백이 없음",
            excerpt=m.group(0),
            rule_ref="§4 p49 (영 제7조제5항)",
        ))
    for m in RE_DATE_BAD_ZERO.finditer(text):
        out.append(Finding(
            Severity.ERROR, "DATE_FORMAT",
            "날짜 포맷 오류: 월·일의 '0'을 표기하지 말 것",
            excerpt=m.group(0),
            rule_ref="§4 p49",
        ))
    for m in RE_DATE_DASH.finditer(text):
        out.append(Finding(
            Severity.WARNING, "DATE_DASH",
            "날짜 구분자로 dash(-) 사용. 편람 표준은 마침표 + 공백",
            excerpt=m.group(0),
            rule_ref="§4 p49",
        ))
    return out


def _check_forbidden_endings(text: str) -> list[Finding]:
    out = []
    for pattern, label, reason in FORBIDDEN_ENDINGS:
        for m in re.finditer(pattern, text):
            out.append(Finding(
                Severity.WARNING, "AUTHORITATIVE_TONE",
                f"고압적 어투: {reason}",
                excerpt=m.group(0),
                rule_ref="§3 p47",
            ))
    return out


def _check_authoritative_terms(text: str) -> list[Finding]:
    out = []
    for term, replacement, reason in AUTHORITATIVE_TERMS:
        if term in text:
            out.append(Finding(
                Severity.WARNING, "AUTHORITATIVE_TERM",
                f"권위적 표현 '{term}' → '{replacement}' 권장 ({reason})",
                excerpt=term,
                rule_ref="§3 p48",
            ))
    return out


def _check_discriminatory_terms(text: str) -> list[Finding]:
    out = []
    for term, replacement, reason in DISCRIMINATORY_TERMS:
        if term in text:
            out.append(Finding(
                Severity.ERROR, "DISCRIMINATORY_TERM",
                f"차별적 표현 '{term}' → '{replacement}' 권장 ({reason})",
                excerpt=term,
                rule_ref="§3 p48",
            ))
    return out


def _check_hangul_compat_chars(text: str) -> list[Finding]:
    out = []
    seen = set()
    for ch in text:
        if is_hangul_compat_special(ch) and ch not in seen:
            if ord(ch) in ALLOWED_ENCLOSED_NUMS:
                continue
            seen.add(ch)
            out.append(Finding(
                Severity.INFO, "HANGUL_COMPAT_CHAR",
                f"한글 호환 영역 특수문자 '{ch}' (U+{ord(ch):04X}) "
                "— 전자적 처리 시 오류 가능, 유니코드 표준 문자 사용 권장",
                excerpt=ch,
                rule_ref="§3 p35, p51",
            ))
    return out


def _check_english_abbrevs(text: str) -> list[Finding]:
    """영문 약어 뒤에 '(한글 설명)' 없으면 INFO."""
    out = []
    for abbr in ENGLISH_ABBREVS:
        # match "AI" but not followed by alpha (to avoid matching "AIR" etc)
        pattern = rf"(?<![A-Za-z])({re.escape(abbr)})(?![A-Za-z0-9])"
        for m in re.finditer(pattern, text):
            # 뒤 30자 내 괄호 안 한글 있는지
            tail = text[m.end():m.end() + 30]
            if not re.match(r"\s*\([가-힣]", tail):
                out.append(Finding(
                    Severity.INFO, "ENGLISH_ABBREV",
                    f"영문 약어 '{abbr}' 뒤에 한글 설명 권장",
                    excerpt=abbr,
                    rule_ref="§3 p38",
                ))
                break  # 같은 약어는 한 번만 보고
    return out


def _check_loanword_errors(text: str) -> list[Finding]:
    out = []
    for wrong, correct in LOANWORD_ERRORS.items():
        if wrong in text:
            out.append(Finding(
                Severity.WARNING, "LOANWORD_ERROR",
                f"외래어 오표기 '{wrong}' → '{correct}'",
                excerpt=wrong,
                rule_ref="§3 p42",
            ))
    return out


def _check_dueum_errors(text: str) -> list[Finding]:
    out = []
    for wrong, correct in DUEUM_ERRORS.items():
        if wrong in text:
            out.append(Finding(
                Severity.ERROR, "DUEUM_ERROR",
                f"두음법칙 오류 '{wrong}' → '{correct}'",
                excerpt=wrong,
                rule_ref="§3 p41",
            ))
    return out


def _check_end_marker(text: str) -> list[Finding]:
    """본문/붙임 끝에 '끝.' 표시가 있는지 (편람 §4 p61)."""
    out = []
    # 간단 휴리스틱: 텍스트에 '붙임'이 있는데 뒤에 '끝.'이 없으면 경고
    if "붙임" in text and "끝." not in text:
        out.append(Finding(
            Severity.WARNING, "END_MARKER_MISSING",
            "붙임이 있으나 '끝.' 표시가 없음 (본문/붙임 마지막에 2타+끝.)",
            rule_ref="§4 p61 (규칙 제4조제5항)",
        ))
    return out


def validate_text(text: str) -> list[Finding]:
    """공문 텍스트 규정 준수 검사.

    Args:
        text: 공문의 본문 텍스트 (extract_text 결과)

    Returns:
        Finding 목록. 비어있으면 이슈 없음.
    """
    findings: list[Finding] = []
    findings += _check_date_format(text)
    findings += _check_forbidden_endings(text)
    findings += _check_authoritative_terms(text)
    findings += _check_discriminatory_terms(text)
    findings += _check_hangul_compat_chars(text)
    findings += _check_english_abbrevs(text)
    findings += _check_loanword_errors(text)
    findings += _check_dueum_errors(text)
    findings += _check_end_marker(text)
    return findings


def validate_file(path: Union[str, Path]) -> list[Finding]:
    """HWPX 파일 규정 준수 검사.

    내부적으로 pyhwpxlib.api.extract_text로 텍스트를 추출한 뒤
    validate_text에 위임한다.
    """
    from ..api import extract_text
    text = extract_text(str(path))
    return validate_text(text)


def format_report(findings: Iterable[Finding]) -> str:
    """Pretty-print findings as a human-readable report."""
    lines = []
    errors = [f for f in findings if f.severity == Severity.ERROR]
    warnings = [f for f in findings if f.severity == Severity.WARNING]
    infos = [f for f in findings if f.severity == Severity.INFO]

    lines.append("─" * 60)
    lines.append(f"공문 규정 검증 결과")
    lines.append("─" * 60)
    lines.append(f"ERROR:   {len(errors)}")
    lines.append(f"WARNING: {len(warnings)}")
    lines.append(f"INFO:    {len(infos)}")
    lines.append("")

    for severity, bucket in [
        (Severity.ERROR, errors),
        (Severity.WARNING, warnings),
        (Severity.INFO, infos),
    ]:
        if not bucket:
            continue
        lines.append(f"━━━ {severity} ({len(bucket)}) ━━━")
        for f in bucket:
            lines.append(f"  • {f.code}: {f.message}")
            if f.excerpt:
                lines.append(f"      → '{f.excerpt}'")
            if f.rule_ref:
                lines.append(f"      ({f.rule_ref})")
        lines.append("")

    if not errors and not warnings and not infos:
        lines.append("✅ 위반 사항 없음")

    return "\n".join(lines)
