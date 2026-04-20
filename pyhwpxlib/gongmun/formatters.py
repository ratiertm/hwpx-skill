"""Formatters for Korean 공문 notation rules.

Based on 2025 행정업무운영 편람 §4 문서의 작성 기준 (p49~):
- 날짜: 2025. 9. 20. (마침표+공백, 0 제거)
- 시간: 15:20 (24시각제)
- 금액: 금113,560원(금일십일만삼천오백육십원)
- 끝 표시: 본문 끝 2타(=스페이스바 2번) 띄우고 '끝.'
"""
from __future__ import annotations
import re
from datetime import date as _date, datetime as _datetime


# 2타 상수 (편람 p52: 한글 1자 = 영숫자 2자 = 스페이스바 2번)
TWO_TA = "  "   # space-bar × 2
ONE_TA = " "    # space-bar × 1 (기호와 내용 사이)


# ──────────────────────────────────────────────────────────
# 날짜·시간
# ──────────────────────────────────────────────────────────

def format_date(d: _date | _datetime | str) -> str:
    """날짜를 편람 표준 형식으로 변환.

    >>> format_date(date(2025, 9, 20))
    '2025. 9. 20.'
    >>> format_date(date(1985, 9, 6))
    '1985. 9. 6.'

    월·일의 '0'은 표기하지 않음. 공백 포함 마침표.
    """
    if isinstance(d, str):
        return d  # 이미 포맷된 값으로 간주
    return f"{d.year}. {d.month}. {d.day}."


def format_datetime_with_weekday(d: _date) -> str:
    """요일 포함 표기.

    >>> format_datetime_with_weekday(date(2023, 6, 27))
    '2023. 6. 27.(화)'
    """
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    return f"{format_date(d)}({weekdays[d.weekday()]})"


def format_time(h: int | _datetime, m: int | None = None) -> str:
    """시간 포맷 (24시각제, 쌍점).

    >>> format_time(15, 20)
    '15:20'
    >>> format_time(7, 9)
    '07:09'
    """
    if isinstance(h, _datetime):
        return h.strftime("%H:%M")
    return f"{h:02d}:{m:02d}"


# ──────────────────────────────────────────────────────────
# 금액
# ──────────────────────────────────────────────────────────

_DIGIT_KOR = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
_PLACE_KOR = ["", "십", "백", "천"]
_BIG_UNIT = ["", "만", "억", "조", "경"]


def _four_digit_to_korean(n: int) -> str:
    """0~9999 범위 아라비아 숫자를 한글로.

    편람 규칙 제2조제2항 예시 "금113,560원(금일십일만삼천오백육십원)"에
    맞춰 '일십', '일백', '일천', '일만' 모두 '일'을 유지한다.
    """
    if n == 0:
        return ""
    out = []
    s = f"{n:04d}"
    for i, ch in enumerate(s):
        d = int(ch)
        if d == 0:
            continue
        place = _PLACE_KOR[3 - i]
        out.append(_DIGIT_KOR[d] + place)
    return "".join(out)


def to_korean_number(n: int) -> str:
    """정수를 한글로 변환.

    >>> to_korean_number(113560)
    '일십일만삼천오백육십'
    >>> to_korean_number(1000)
    '일천'
    >>> to_korean_number(10000)
    '일만'
    """
    if n == 0:
        return "영"
    if n < 0:
        return "마이너스" + to_korean_number(-n)
    chunks = []
    big_idx = 0
    while n > 0:
        chunk = n % 10000
        if chunk > 0:
            chunk_str = _four_digit_to_korean(chunk)
            chunks.insert(0, chunk_str + _BIG_UNIT[big_idx])
        else:
            chunks.insert(0, "")
        n //= 10000
        big_idx += 1
    return "".join(chunks)


def format_money(amount: int) -> str:
    """금액 표기 — 편람 규칙 제2조제2항.

    >>> format_money(113560)
    '금113,560원(금일십일만삼천오백육십원)'
    """
    return f"금{amount:,}원(금{to_korean_number(amount)}원)"


# ──────────────────────────────────────────────────────────
# "끝" 표시
# ──────────────────────────────────────────────────────────

def add_end_marker(text: str) -> str:
    """본문 뒤에 2타+'끝.' 부착.

    >>> add_end_marker("주시기 바랍니다.")
    '주시기 바랍니다.  끝.'
    """
    if text.rstrip().endswith("끝."):
        return text
    return text.rstrip() + TWO_TA + "끝."


def format_attachment(items: list[str]) -> list[str]:
    """붙임 목록 포맷.

    단일:  '붙임  서식.hwpx 1부.  끝.'
    복수:  '붙임  1. 서식.hwpx 1부.'
           '      2. 계획서.hwpx 1부.  끝.'

    편람 p59~60 참조.
    """
    if not items:
        return []
    if len(items) == 1:
        return [f"붙임{TWO_TA}{items[0].rstrip('.')}.{TWO_TA}끝."]
    lines = [f"붙임{TWO_TA}1. {items[0].rstrip('.')}."]
    for i, item in enumerate(items[1:], start=2):
        suffix = f"{TWO_TA}끝." if i == len(items) else ""
        lines.append(f"      {i}. {item.rstrip('.')}.{suffix}")
    return lines


# ──────────────────────────────────────────────────────────
# 항목 기호 (편람 p51)
# ──────────────────────────────────────────────────────────

_LEVEL_1 = [f"{n}." for n in range(1, 100)]                                  # 1. 2. 3.
_LEVEL_2 = [c + "." for c in "가나다라마바사아자차카타파하"]                  # 가. 나. ...
_LEVEL_3 = [f"{n})" for n in range(1, 100)]                                  # 1) 2) ...
_LEVEL_4 = [c + ")" for c in "가나다라마바사아자차카타파하"]                 # 가) 나) ...
_LEVEL_5 = [f"({n})" for n in range(1, 100)]                                 # (1) (2) ...
_LEVEL_6 = [f"({c})" for c in "가나다라마바사아자차카타파하"]                # (가) (나) ...
_LEVEL_7 = [chr(0x2460 + i) for i in range(50)]                              # ① ② ③
_LEVEL_8 = [chr(0x327F + i) for i in range(14)]                              # ㉮ 등 (유니코드 원문자)

LEVEL_MARKERS = [_LEVEL_1, _LEVEL_2, _LEVEL_3, _LEVEL_4, _LEVEL_5, _LEVEL_6, _LEVEL_7, _LEVEL_8]


def item_marker(level: int, index: int) -> str:
    """레벨 n의 index번째 항목 기호.

    >>> item_marker(1, 0)
    '1.'
    >>> item_marker(2, 0)
    '가.'
    >>> item_marker(5, 2)
    '(3)'
    """
    if not (1 <= level <= 8):
        raise ValueError(f"Level must be 1-8, got {level}")
    markers = LEVEL_MARKERS[level - 1]
    if index >= len(markers):
        raise ValueError(f"Level {level} index {index} overflows. "
                         f"편람 p51: 단모음 순 (하→거→너...) 필요")
    return markers[index]


def item_indent(level: int) -> str:
    """레벨 n의 왼쪽 들여쓰기 (2타 × (n-1)).

    Level 1은 왼쪽 기본선에서 시작 (들여쓰기 없음).
    """
    return TWO_TA * (level - 1)


def format_item(level: int, index: int, content: str) -> str:
    """항목 라인을 완성된 형태로.

    >>> format_item(1, 0, "공공기관 대상으로...")
    '1. 공공기관 대상으로...'
    >>> format_item(2, 0, "세부 내용")
    '  가. 세부 내용'
    """
    return item_indent(level) + item_marker(level, index) + ONE_TA + content


# ──────────────────────────────────────────────────────────
# 주소 블록
# ──────────────────────────────────────────────────────────

def format_address(우편번호: str, 도로명주소: str) -> str:
    """도로명주소 포맷.

    >>> format_address("30112", "세종특별자치시 도움6로 42 정부세종청사 중앙동")
    '우 30112  세종특별자치시 도움6로 42 정부세종청사 중앙동'
    """
    if not 우편번호:
        return 도로명주소
    return f"우 {우편번호}{TWO_TA}{도로명주소}"


def format_phone_line(전화: str, 팩스: str = "", 이메일: str = "",
                      공개구분: str = "") -> str:
    """전화/팩스/이메일/공개구분 한 줄 포맷.

    편람 p72 예시:
    '전화번호 (044)205-0000  팩스번호 (044)204-0000 / abcde@mois.go.kr / 대국민공개'
    """
    parts = []
    if 전화:
        parts.append(f"전화번호 {전화}")
    if 팩스:
        parts.append(f"팩스번호 {팩스}")
    line = TWO_TA.join(parts)
    tail = []
    if 이메일:
        tail.append(이메일)
    if 공개구분:
        tail.append(공개구분)
    if tail:
        line += " / " + " / ".join(tail)
    return line


def format_시행번호(처리과명: str, 일련번호: str, 시행일: str = "") -> str:
    """시행 처리과명-일련번호(시행일) 포맷.

    >>> format_시행번호('정보공개과', '000', '2025. 9. 30.')
    '시행  정보공개과-000 (2025. 9. 30.)'
    """
    if not 처리과명:
        return ""
    line = f"시행{TWO_TA}{처리과명}-{일련번호}"
    if 시행일:
        line += f" ({시행일})"
    return line


# ──────────────────────────────────────────────────────────
# 관련문서 표시 (편람 p59)
# ──────────────────────────────────────────────────────────

def format_related_doc(기관명: str, 처리과명: str, 등록번호: str,
                       등록일: str, 제목: str) -> str:
    """관련문서 표시.

    >>> format_related_doc('OO부', 'OOO과', '123', '2025. 9. 20.', 'OO 행사 관련')
    'OO부 OOO과-123(2025. 9. 20., "OO 행사 관련")호'
    """
    return f'{기관명} {처리과명}-{등록번호}({등록일}, "{제목}")호'
