"""인터파크 NOL 티켓 오픈 예정 스크래핑"""
import time
import logging
import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from config import (
    PAGE_TIMEOUT_MS,
    PAGE_DELAY_SEC,
    MAX_RETRIES,
    RETRY_DELAY_SEC,
)

logger = logging.getLogger(__name__)

# 인터파크 내부 API
NOTICE_LIST_API = "https://tickets.interpark.com/contents/api/open-notice/notice-list"
DETAIL_BASE_URL = "https://tickets.interpark.com/contents/notice/detail"


def fetch_notice_list() -> list[dict]:
    """
    인터파크 API로 뮤지컬/서울 오픈 예정 목록 조회.
    반환: [{"noticeId": int, "title": str, "openDateStr": str, "venueName": str, ...}, ...]
    """
    params = {
        "goodsGenre": "MUSICAL",
        "goodsRegion": "SEOUL",
        "offset": 0,
        "pageSize": 100,
        "sorting": "OPEN_ASC",
    }

    all_items = []
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(NOTICE_LIST_API, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                all_items = data
                break
        except Exception as e:
            if attempt == MAX_RETRIES:
                logger.error(f"Failed to fetch notice list: {e}")
                return []
            logger.warning(f"API attempt {attempt + 1} failed: {e}")
            time.sleep(RETRY_DELAY_SEC)

    logger.info(f"Fetched {len(all_items)} items from API")
    return all_items


def scrape_detail_page(page, notice_id: int) -> dict | None:
    """
    상세 페이지에서 공연 정보 추출.
    반환: {"raw_title": str, "text_content": str, "url": str}
    """
    url = f"{DETAIL_BASE_URL}/{notice_id}"
    try:
        logger.info(f"Scraping detail: {url}")
        page.goto(url, timeout=PAGE_TIMEOUT_MS)
        page.wait_for_load_state("networkidle")
        time.sleep(PAGE_DELAY_SEC)

        # 페이지 전체 텍스트 추출
        text_content = page.inner_text("body")

        # 공연명 (페이지 상단 타이틀)
        title_el = page.query_selector("[class*='title' i]")
        raw_title = title_el.inner_text().strip() if title_el else ""

        return {
            "raw_title": raw_title,
            "text_content": text_content,
            "url": url,
        }
    except PlaywrightTimeout:
        logger.error(f"Timeout on detail page: {url}")
        return None
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return None


def run_scraper() -> list[dict]:
    """
    전체 스크래핑 실행.
    1. API로 목록 조회
    2. Playwright로 각 상세 페이지 스크래핑
    반환: [{"raw_title": str, "text_content": str, "url": str, "list_title": str, "api_data": dict}, ...]
    """
    # 1. API로 목록 조회 (Playwright 불필요)
    notice_items = fetch_notice_list()
    if not notice_items:
        return []

    # 2. Playwright로 상세 페이지 스크래핑
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ko-KR",
        )
        page = context.new_page()

        for i, item in enumerate(notice_items):
            notice_id = item["noticeId"]
            list_title = item.get("title", "")
            logger.info(f"[{i+1}/{len(notice_items)}] {list_title}")

            detail = None
            for attempt in range(MAX_RETRIES + 1):
                detail = scrape_detail_page(page, notice_id)
                if detail:
                    break
                logger.warning(f"Retry {attempt + 1} for notice {notice_id}")
                time.sleep(RETRY_DELAY_SEC)

            if detail:
                detail["list_title"] = list_title
                detail["api_data"] = item
                results.append(detail)

            time.sleep(PAGE_DELAY_SEC)

        browser.close()

    logger.info(f"Scraped {len(results)} detail pages")
    return results
