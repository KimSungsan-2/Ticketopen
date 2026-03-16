"""인터파크 NOL 티켓 오픈 예정 스크래핑"""
import time
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from config import (
    INTERPARK_NOTICE_URL,
    PAGE_TIMEOUT_MS,
    PAGE_DELAY_SEC,
    MAX_RETRIES,
    RETRY_DELAY_SEC,
)

logger = logging.getLogger(__name__)


def _retry(func, *args, retries=MAX_RETRIES, delay=RETRY_DELAY_SEC):
    """재시도 래퍼"""
    for attempt in range(retries + 1):
        try:
            return func(*args)
        except (PlaywrightTimeout, Exception) as e:
            if attempt == retries:
                logger.error(f"Failed after {retries + 1} attempts: {e}")
                raise
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)


def scrape_notice_list(page) -> list[dict]:
    """
    인터파크 오픈 예정 목록에서 뮤지컬/서울 필터 적용 후 공연 목록 수집.
    반환: [{"title": "공연명", "url": "상세URL"}, ...]
    """
    logger.info(f"Navigating to {INTERPARK_NOTICE_URL}")
    page.goto(INTERPARK_NOTICE_URL, timeout=PAGE_TIMEOUT_MS)
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    # 장르 필터: 뮤지컬 선택
    logger.info("Applying genre filter: 뮤지컬")
    page.click('button[aria-label="장르 필터 열기"]')
    time.sleep(0.5)
    page.click('main.FilterDropDown_badge__cUHfo button:has-text("뮤지컬")')
    time.sleep(1)

    # 지역 필터: 서울 선택
    logger.info("Applying region filter: 서울")
    page.click('button[aria-label="지역 필터 열기"]')
    time.sleep(0.5)
    page.click('main.FilterDropDown_badge__cUHfo button:has-text("서울")')
    time.sleep(1)

    page.wait_for_load_state("networkidle")
    time.sleep(1)

    # 목록 수집 — 스크롤하며 모든 항목 로드
    prev_count = 0
    max_scroll_attempts = 20

    for _ in range(max_scroll_attempts):
        cards = page.query_selector_all('a[href*="/contents/notice/detail/"]')
        current_count = len(cards)
        if current_count == prev_count:
            break  # 더 이상 새 항목 없음
        prev_count = current_count
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

    items = []
    cards = page.query_selector_all('a[href*="/contents/notice/detail/"]')
    for card in cards:
        href = card.get_attribute("href")
        # 카드 내 공연명 텍스트 추출
        title_el = card.query_selector("strong, h3, p")
        title = title_el.inner_text().strip() if title_el else ""
        if href:
            full_url = f"https://tickets.interpark.com{href}" if href.startswith("/") else href
            items.append({"title": title, "url": full_url})

    logger.info(f"Found {len(items)} items in notice list")
    return items


def scrape_detail_page(page, url: str) -> dict | None:
    """
    상세 페이지에서 공연 정보 추출.
    반환: {"raw_title": str, "text_content": str, "url": str}
    """
    try:
        logger.info(f"Scraping detail: {url}")
        page.goto(url, timeout=PAGE_TIMEOUT_MS)
        page.wait_for_load_state("networkidle")
        time.sleep(PAGE_DELAY_SEC)

        # 페이지 전체 텍스트 추출
        text_content = page.inner_text("body")

        # 공연명 (페이지 상단 타이틀 — [class*=title] 첫 번째 요소)
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
    반환: [{"raw_title": str, "text_content": str, "url": str}, ...]
    """
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="ko-KR",
        )
        page = context.new_page()

        try:
            items = _retry(scrape_notice_list, page)
        except Exception as e:
            logger.error(f"Failed to scrape notice list: {e}")
            browser.close()
            return []

        for item in items:
            detail = _retry(scrape_detail_page, page, item["url"])
            if detail:
                # 목록에서 가져온 제목도 함께 보관
                detail["list_title"] = item["title"]
                results.append(detail)
            time.sleep(PAGE_DELAY_SEC)

        browser.close()

    logger.info(f"Scraped {len(results)} detail pages")
    return results
