"""NOL 티켓 오픈 스크래퍼 진입점"""
import sys
import io
import logging
from datetime import date

# Windows cp949 인코딩 문제 방지
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from scraper import run_scraper
from parser import parse_open_info, parse_performance_period, parse_venue, parse_title, is_kids_musical
from podor_api import PodorAPI
from matcher import match_performance_name, match_season, check_duplicate
from mailer import build_report, build_excel, send_email

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    today = date.today().strftime("%Y-%m-%d")
    logger.info("=== NOL 티켓 오픈 스크래퍼 시작 ===")

    # 1. 인터파크 스크래핑
    logger.info("Step 1: 인터파크 스크래핑")
    scraped_pages = run_scraper()

    if not scraped_pages:
        logger.warning("스크래핑 결과 0건")
        report = f"[NOL 티켓 오픈 알림] {today}\n\n수집 결과 없음 (스크래핑 오류 가능성이 있습니다. 확인 필요)"
        if not send_email(f"[NOL 티켓 오픈 알림] {today}", report):
            print(report)
        return

    # 2. podor API 데이터 로드
    logger.info("Step 2: podor API 데이터 로드")
    api = PodorAPI()
    api.login()
    performances = api.get_performances()
    seasons = api.get_seasons()
    existing_opens = api.get_opens()

    # 3. 각 항목 처리
    logger.info("Step 3: 데이터 매칭 & 분류")
    new_items = []
    unregistered_performances = []
    unregistered_seasons = []
    parse_failures = []
    match_failures = []
    duplicates = []
    kids_excluded = []

    for page_data in scraped_pages:
        raw_title = page_data.get("raw_title", "") or page_data.get("list_title", "")
        text = page_data["text_content"]

        # 어린이 뮤지컬 필터
        if is_kids_musical(raw_title):
            kids_excluded.append({"raw_title": raw_title})
            logger.info(f"어린이 뮤지컬 제외: {raw_title}")
            continue

        # 공연명 파싱 (상세 페이지 텍스트에서)
        parsed_title = parse_title(text) or raw_title

        # 공연명 매칭
        matched_perf = match_performance_name(parsed_title, performances)
        if matched_perf is None:
            match_failures.append({"raw_title": raw_title})
            logger.warning(f"매칭 실패: {raw_title}")
            continue

        std_name = matched_perf["공연명"]

        # 전체공연기간 파싱
        period = parse_performance_period(text)
        if period is None:
            unregistered_seasons.append({
                "공연명": std_name,
                "raw_title": raw_title,
                "period_start": "?",
                "period_end": "?",
            })
            logger.warning(f"공연기간 파싱 실패: {raw_title}")
            continue

        period_start, period_end = period

        # 시즌 매칭
        matched_season = match_season(std_name, period_start, period_end, seasons)
        if matched_season is None:
            unregistered_seasons.append({
                "공연명": std_name,
                "raw_title": raw_title,
                "period_start": period_start,
                "period_end": period_end,
            })
            logger.warning(f"시즌 미등록: {std_name} ({period_start}~{period_end})")
            continue

        season_id = matched_season["id"]

        # 티켓오픈 정보 파싱
        open_infos = parse_open_info(text)
        if not open_infos:
            # 폴백: API 데이터에서 오픈 일시 추출
            api_data = page_data.get("api_data", {})
            open_date_str = api_data.get("openDateStr", "")
            open_type_str = api_data.get("openTypeStr", "")
            if open_date_str:
                # "2026-03-18 13:00:00" → 날짜와 시간 분리
                parts = open_date_str.split(" ")
                api_date = parts[0] if len(parts) >= 1 else ""
                api_time = parts[1][:5] if len(parts) >= 2 else ""
                # 오픈차수 추정: openTypeStr 또는 텍스트에서 추출
                import re as _re
                round_m = _re.search(r"(\d+)차|마지막|프리뷰", open_type_str + " " + text)
                기타 = round_m.group(0) if round_m else open_type_str or "?"
                open_infos = [{
                    "오픈날짜": api_date,
                    "오픈시간": api_time,
                    "기타": 기타,
                    "오픈회차": "",
                }]
                logger.info(f"API 폴백 사용: {raw_title} → {api_date} {api_time} ({기타})")
            else:
                parse_failures.append({"raw_title": raw_title})
                logger.warning(f"오픈 정보 파싱 실패: {raw_title}")
                continue

        # 각 오픈 차수별 처리
        for open_info in open_infos:
            open_round = open_info["기타"]

            # 중복 체크
            if check_duplicate(season_id, open_round, existing_opens):
                duplicates.append({
                    "공연명": std_name,
                    "기타": open_round,
                })
                logger.info(f"중복 스킵: {std_name} / {open_round}")
                continue

            # 공연장: API 데이터 또는 텍스트 파싱
            api_data = page_data.get("api_data", {})
            venue = parse_venue(text) or api_data.get("venueName", "")

            # 전체공연기간 포맷
            전체공연기간 = ""
            if period:
                from mailer import _format_date
                전체공연기간 = f"{_format_date(period_start)} - {_format_date(period_end)}"

            new_items.append({
                "시즌": season_id,
                "공연명": std_name,
                "오픈날짜": open_info["오픈날짜"],
                "오픈시간": open_info["오픈시간"],
                "기타": open_round,
                "오픈회차": open_info["오픈회차"],
                "공연장": venue,
                "전체공연기간": 전체공연기간,
                "raw_title": raw_title,
            })
            logger.info(f"신규 발견: {std_name} / {open_round}")

    # 4. 리포트 생성 & 발송
    logger.info("Step 4: 메일 발송")
    report = build_report(
        new_items=new_items,
        unregistered_performances=unregistered_performances,
        unregistered_seasons=unregistered_seasons,
        parse_failures=parse_failures,
        match_failures=match_failures,
        duplicates=duplicates,
        kids_excluded=kids_excluded,
    )

    subject = f"[NOL 티켓 오픈 알림] {today}"

    # 엑셀 파일 생성 (신규 항목이 있을 때)
    excel_path = build_excel(new_items)

    # 메일 발송 시도, 실패 시 stdout 출력
    if not send_email(subject, report, excel_path=excel_path):
        logger.error("메일 발송 실패 — stdout으로 리포트 출력")

    # stdout에도 리포트 출력 (GitHub Actions 로그용)
    logger.info(
        f"완료 — 신규 {len(new_items)}건, "
        f"미등록공연 {len(unregistered_performances)}건, "
        f"시즌미등록 {len(unregistered_seasons)}건, "
        f"파싱실패 {len(parse_failures)}건, "
        f"매칭실패 {len(match_failures)}건, "
        f"중복 {len(duplicates)}건, "
        f"어린이제외 {len(kids_excluded)}건"
    )
    print("=" * 60)
    print(report)
    print("=" * 60)


if __name__ == "__main__":
    main()
