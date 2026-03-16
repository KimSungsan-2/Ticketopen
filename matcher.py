"""podor 표준 공연명, 시즌, 공연장 매칭 로직"""
import re
from datetime import date


def _normalize(name: str) -> str:
    """공백, 특수문자 정규화"""
    name = re.sub(r"[〈〉<>《》「」『』\[\]()（）]", "", name)
    name = re.sub(r"뮤지컬\s*", "", name)
    return name.strip()


def _strip_subtitles(name: str) -> list[str]:
    """
    부제를 순차적으로 제거하며 후보 이름 목록 생성.
    "은밀하게 위대하게:THE LAST-10주년" → ["은밀하게 위대하게:THE LAST-10주년", "은밀하게 위대하게:THE LAST", "은밀하게 위대하게"]
    """
    candidates = [name]
    separators = [":", "：", " - ", "-"]
    current = name
    for sep in separators:
        if sep in current:
            current = current.rsplit(sep, 1)[0].strip()
            candidates.append(current)
    return candidates


def match_performance_name(interpark_name: str, performance_list: list[dict]) -> dict | None:
    """
    인터파크 공연명으로 podor 표준 공연명 매칭.
    반환: 매칭된 performance dict 또는 None
    """
    podor_names = {_normalize(p["공연명"]): p for p in performance_list}

    # 1단계: 부제 제거하며 정확 매칭 시도
    candidates = _strip_subtitles(interpark_name)
    for candidate in candidates:
        normalized = _normalize(candidate)
        if normalized in podor_names:
            return podor_names[normalized]

    # 2단계: substring 매칭 (podor명이 인터파크명에 포함)
    normalized_input = _normalize(interpark_name)
    for podor_norm, p in podor_names.items():
        if podor_norm in normalized_input or normalized_input in podor_norm:
            return p

    return None


def _parse_season_period(period_str: str) -> tuple[date, date] | None:
    """시즌 공연기간 문자열 파싱. "2026.01.30;2026.04.10" → (date, date)"""
    parts = period_str.split(";")
    if len(parts) != 2:
        return None
    try:
        start = date(*[int(x) for x in parts[0].split(".")])
        end = date(*[int(x) for x in parts[1].split(".")])
        return (start, end)
    except (ValueError, TypeError):
        return None


def match_season(
    performance_name: str,
    period_start: str,
    period_end: str,
    season_list: list[dict],
) -> dict | None:
    """
    표준 공연명 + 전체공연기간으로 시즌 매칭.
    period_start/end: "YYYY-MM-DD" 형식
    """
    try:
        scraped_start = date.fromisoformat(period_start)
    except ValueError:
        return None

    matching_seasons = []
    for season in season_list:
        if season["공연명"] != performance_name:
            continue
        period = _parse_season_period(season.get("공연기간", ""))
        if period is None:
            continue
        season_start, season_end = period
        # 스크래핑된 시작일이 시즌 기간 내에 있는지 확인
        if season_start <= scraped_start <= season_end:
            matching_seasons.append((season, abs((scraped_start - season_start).days)))

    if not matching_seasons:
        return None

    # 가장 가까운 시작일 매칭
    matching_seasons.sort(key=lambda x: x[1])
    return matching_seasons[0][0]


def check_duplicate(season_id: int, open_round: str, existing_opens: list[dict]) -> bool:
    """시즌 id + 오픈차수 조합으로 중복 확인"""
    return any(
        o.get("시즌") == season_id and o.get("기타") == open_round
        for o in existing_opens
    )
