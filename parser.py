"""인터파크 상세 페이지에서 티켓오픈 정보를 파싱"""
import re
from config import KIDS_KEYWORDS


def _convert_time(ampm: str, hour: int, minute: int = 0) -> str:
    """오전/오후 + 시 → HH:MM 형식으로 변환"""
    if ampm == "오후" and hour != 12:
        hour += 12
    elif ampm == "오전" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def parse_open_info(text: str) -> list[dict]:
    """
    상세 페이지 텍스트에서 티켓오픈 정보를 추출.
    반환: [{"오픈날짜": "YYYY-MM-DD", "오픈시간": "HH:MM", "기타": "차수", "오픈회차": "기간문자열"}, ...]
    """
    results = []

    # 패턴: ※ {차수} 티켓오픈 일시 : {날짜} {시간}
    date_pattern = re.compile(
        r"※\s*([\w]+)\s*티켓오픈\s*일시\s*[:：]\s*"
        r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(?:\([^)]*\))?\s*"
        r"(오전|오후)\s*(\d{1,2})시(?:\s*(\d{1,2})분)?",
        re.MULTILINE,
    )

    # 패턴: ※ {차수} 티켓오픈 오픈 회차 : {기간}
    round_pattern = re.compile(
        r"※\s*([\w]+)\s*티켓오픈\s*오픈\s*회차\s*[:：]\s*(.+?)(?:\n|$)",
        re.MULTILINE,
    )

    # 날짜/시간 파싱
    date_matches = {}
    for m in date_pattern.finditer(text):
        차수 = m.group(1)
        year = int(m.group(2))
        month = int(m.group(3))
        day = int(m.group(4))
        ampm = m.group(5)
        hour = int(m.group(6))
        minute = int(m.group(7)) if m.group(7) else 0
        date_matches[차수] = {
            "오픈날짜": f"{year}-{month:02d}-{day:02d}",
            "오픈시간": _convert_time(ampm, hour, minute),
            "기타": 차수,
        }

    # 오픈 회차 파싱
    round_matches = {}
    for m in round_pattern.finditer(text):
        차수 = m.group(1)
        기간 = m.group(2).strip()
        # "2026년 4월 11일(토) ~ 4월 26일(일)" → "4월 11일 - 4월 26일"
        기간_clean = re.sub(r"\d{4}년\s*", "", 기간)
        기간_clean = re.sub(r"\([^)]*\)", "", 기간_clean)
        기간_clean = re.sub(r"\s*~\s*", " - ", 기간_clean).strip()
        round_matches[차수] = 기간_clean

    # 합치기
    for 차수, info in date_matches.items():
        info["오픈회차"] = round_matches.get(차수, "")
        results.append(info)

    # 차수 정렬 (1차, 2차, ... 마지막)
    def sort_key(r):
        g = r["기타"]
        if g == "마지막":
            return 9999
        m = re.match(r"(\d+)", g)
        return int(m.group(1)) if m else 5000
    results.sort(key=sort_key)

    return results


def parse_performance_period(text: str) -> tuple[str, str] | None:
    """
    상세 페이지에서 전체 공연기간을 추출.
    반환: ("YYYY-MM-DD", "YYYY-MM-DD") 또는 None
    """
    pattern = re.compile(
        r"공연기간\s*[:：]?\s*(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})\s*~\s*(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})"
    )
    m = pattern.search(text)
    if not m:
        return None
    start = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    end = f"{m.group(4)}-{int(m.group(5)):02d}-{int(m.group(6)):02d}"
    return (start, end)


def parse_venue(text: str) -> str | None:
    """상세 페이지에서 공연장소를 추출."""
    pattern = re.compile(r"공연장소\s*[:：]?\s*(.+?)(?:\n|$)")
    m = pattern.search(text)
    if not m:
        return None
    return m.group(1).strip()


def parse_title(text: str) -> str | None:
    """상세 페이지에서 공연명을 추출."""
    pattern = re.compile(r"공연명\s*[:：]?\s*(.+?)(?:\n|$)")
    m = pattern.search(text)
    if not m:
        return None
    return m.group(1).strip()


def is_kids_musical(title: str) -> bool:
    """어린이 뮤지컬 여부 판별"""
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in KIDS_KEYWORDS)
