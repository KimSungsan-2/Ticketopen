# NOL 티켓 오픈 스크래퍼 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 인터파크에서 뮤지컬/서울 티켓 오픈 정보를 매일 스크래핑하여 podor 미등록 항목을 이메일로 알림

**Architecture:** Playwright로 인터파크 동적 페이지 스크래핑 → podor REST API로 표준명/시즌 매칭 및 중복 체크 → Gmail SMTP로 결과 메일 발송. GitHub Actions cron으로 매일 09:00 KST 자동 실행.

**Tech Stack:** Python 3.11, Playwright, requests, smtplib, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-03-16-ticket-open-scraper-design.md`

---

## Chunk 1: 프로젝트 셋업 & config

### Task 1: 프로젝트 초기화 및 config.py

**Files:**
- Create: `config.py`
- Create: `requirements.txt`

- [ ] **Step 1: requirements.txt 작성**

```txt
playwright==1.49.1
requests==2.32.3
```

- [ ] **Step 2: config.py 작성**

```python
import os

# podor API
PODOR_BASE_URL = "https://podor.co.kr"
PODOR_USER_ID = os.environ.get("PODOR_USER_ID", "")
PODOR_PASSWORD = os.environ.get("PODOR_PASSWORD", "")

# 메일
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "tingsung93@naver.com")

# 인터파크
INTERPARK_NOTICE_URL = "https://tickets.interpark.com/contents/notice"

# 어린이 뮤지컬 제외 키워드 (대소문자 무시)
KIDS_KEYWORDS = ["어린이", "키즈", "kids", "가족", "패밀리", "family", "주니어", "jr"]

# 스크래핑 설정
PAGE_TIMEOUT_MS = 30000
PAGE_DELAY_SEC = 1.5
MAX_RETRIES = 2
RETRY_DELAY_SEC = 5
```

- [ ] **Step 3: 의존성 설치**

Run: `pip install -r requirements.txt && playwright install chromium`

- [ ] **Step 4: 커밋**

```bash
git add config.py requirements.txt
git commit -m "feat: add project config and dependencies"
```

---

## Chunk 2: 상세 페이지 파서 (parser.py)

### Task 2: 티켓오픈 정보 파싱 테스트 작성

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_parser.py`

- [ ] **Step 1: tests 디렉토리 초기화**

```python
# tests/__init__.py
# (빈 파일)
```

- [ ] **Step 2: 파서 테스트 작성**

인터파크 상세 페이지에서 추출할 텍스트 패턴들을 테스트. 실제 페이지에서 확인된 형식 기반.

```python
# tests/test_parser.py
from parser import parse_open_info, is_kids_musical


class TestParseOpenInfo:
    def test_parse_last_open(self):
        """마지막 티켓오픈 파싱"""
        text = """
※ 마지막 티켓오픈 일시 : 2026년 3월 17일(화) 오전 11시
※ 마지막 티켓오픈 오픈 회차 : 2026년 4월 11일(토) ~ 4월 26일(일)
"""
        results = parse_open_info(text)
        assert len(results) >= 1
        r = results[0]
        assert r["오픈날짜"] == "2026-03-17"
        assert r["오픈시간"] == "11:00"
        assert r["기타"] == "마지막"
        assert "4월 11일" in r["오픈회차"]
        assert "4월 26일" in r["오픈회차"]

    def test_parse_numbered_open(self):
        """N차 티켓오픈 파싱"""
        text = """
※ 2차 티켓오픈 일시 : 2026년 3월 18일(수) 오후 1시
※ 2차 티켓오픈 오픈 회차 : 2026년 4월 28일(월) ~ 5월 10일(토)
"""
        results = parse_open_info(text)
        assert len(results) >= 1
        r = results[0]
        assert r["오픈날짜"] == "2026-03-18"
        assert r["오픈시간"] == "13:00"
        assert r["기타"] == "2차"

    def test_parse_preview_open(self):
        """프리뷰 티켓오픈 파싱"""
        text = """
※ 프리뷰 티켓오픈 일시 : 2026년 3월 23일(일) 오후 2시
※ 프리뷰 티켓오픈 오픈 회차 : 2026년 5월 12일(월) ~ 5월 17일(토)
"""
        results = parse_open_info(text)
        assert len(results) >= 1
        assert results[0]["기타"] == "프리뷰"

    def test_parse_multiple_opens(self):
        """여러 차수 동시 파싱"""
        text = """
※ 1차 티켓오픈 일시 : 2026년 2월 10일(화) 오후 2시
※ 1차 티켓오픈 오픈 회차 : 2026년 3월 1일(토) ~ 3월 15일(토)
※ 2차 티켓오픈 일시 : 2026년 3월 1일(토) 오후 2시
※ 2차 티켓오픈 오픈 회차 : 2026년 3월 16일(일) ~ 3월 31일(월)
"""
        results = parse_open_info(text)
        assert len(results) == 2
        assert results[0]["기타"] == "1차"
        assert results[1]["기타"] == "2차"

    def test_parse_no_open_info(self):
        """오픈 정보가 없는 텍스트"""
        text = "공연 소개 텍스트만 있는 페이지입니다."
        results = parse_open_info(text)
        assert len(results) == 0

    def test_parse_am_pm_time(self):
        """오전/오후 시간 변환"""
        text = "※ 3차 티켓오픈 일시 : 2026년 4월 1일(화) 오후 8시"
        results = parse_open_info(text)
        assert results[0]["오픈시간"] == "20:00"

    def test_parse_time_with_minutes(self):
        """시간에 분이 포함된 경우"""
        text = "※ 1차 티켓오픈 일시 : 2026년 4월 1일(화) 오후 2시 30분"
        results = parse_open_info(text)
        assert results[0]["오픈시간"] == "14:30"


class TestIsKidsMusical:
    def test_kids_keyword(self):
        assert is_kids_musical("어린이 뮤지컬 피노키오") is True

    def test_family_keyword(self):
        assert is_kids_musical("가족뮤지컬 빨간모자") is True

    def test_normal_musical(self):
        assert is_kids_musical("뮤지컬 데스노트") is False

    def test_case_insensitive(self):
        assert is_kids_musical("KIDS Musical ABC") is True

    def test_jr_keyword(self):
        assert is_kids_musical("뮤지컬 위키드 Jr.") is True
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

Run: `python -m pytest tests/test_parser.py -v`
Expected: FAIL (parser 모듈 없음)

- [ ] **Step 4: 커밋**

```bash
git add tests/
git commit -m "test: add parser unit tests for ticket open info parsing"
```

### Task 3: parser.py 구현

**Files:**
- Create: `parser.py`

- [ ] **Step 1: parser.py 구현**

```python
# parser.py
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
```

- [ ] **Step 2: 테스트 실행 — 통과 확인**

Run: `python -m pytest tests/test_parser.py -v`
Expected: ALL PASS

- [ ] **Step 3: 커밋**

```bash
git add parser.py
git commit -m "feat: implement parser for ticket open info extraction"
```

---

## Chunk 3: 매칭 로직 (matcher.py)

### Task 4: 매칭 로직 테스트 작성

**Files:**
- Create: `tests/test_matcher.py`

- [ ] **Step 1: 매칭 테스트 작성**

```python
# tests/test_matcher.py
from matcher import match_performance_name, match_season, check_duplicate


class TestMatchPerformanceName:
    PERFORMANCE_LIST = [
        {"id": 199, "공연명": "은밀하게 위대하게"},
        {"id": 34, "공연명": "데스노트"},
        {"id": 230, "공연명": "팬레터"},
        {"id": 111, "공연명": "브라더스 까라마조프"},
        {"id": 577, "공연명": "몽유도원"},
    ]

    def test_exact_match(self):
        result = match_performance_name("데스노트", self.PERFORMANCE_LIST)
        assert result["공연명"] == "데스노트"

    def test_match_with_subtitle_colon(self):
        result = match_performance_name(
            "은밀하게 위대하게:THE LAST-10주년 기념공연", self.PERFORMANCE_LIST
        )
        assert result["공연명"] == "은밀하게 위대하게"

    def test_match_with_subtitle_hyphen(self):
        result = match_performance_name(
            "팬레터 - 10주년 기념 앵콜 공연", self.PERFORMANCE_LIST
        )
        assert result["공연명"] == "팬레터"

    def test_match_with_angle_brackets(self):
        """인터파크에서 뮤지컬 〈공연명〉 형식 사용"""
        result = match_performance_name(
            "뮤지컬 〈데스노트〉", self.PERFORMANCE_LIST
        )
        assert result["공연명"] == "데스노트"

    def test_no_match(self):
        result = match_performance_name("존재하지않는공연", self.PERFORMANCE_LIST)
        assert result is None

    def test_substring_match(self):
        result = match_performance_name(
            "브라더스 까라마조프 시즌2", self.PERFORMANCE_LIST
        )
        assert result["공연명"] == "브라더스 까라마조프"


class TestMatchSeason:
    SEASON_LIST = [
        {"id": 954, "공연명": "은밀하게 위대하게", "공연기간": "2022.05.14;2022.07.03"},
        {"id": 1098, "공연명": "은밀하게 위대하게", "공연기간": "2023.03.04;2023.05.07"},
        {"id": 1705, "공연명": "은밀하게 위대하게", "공연기간": "2026.01.30;2026.04.10"},
    ]

    def test_match_by_period(self):
        result = match_season("은밀하게 위대하게", "2026-01-30", "2026-04-26", self.SEASON_LIST)
        assert result["id"] == 1705

    def test_no_match_wrong_period(self):
        result = match_season("은밀하게 위대하게", "2025-01-01", "2025-03-01", self.SEASON_LIST)
        assert result is None

    def test_no_match_wrong_name(self):
        result = match_season("데스노트", "2026-01-30", "2026-04-26", self.SEASON_LIST)
        assert result is None


class TestCheckDuplicate:
    EXISTING_OPENS = [
        {"시즌": 1705, "공연명": "은밀하게 위대하게", "기타": "마지막"},
        {"시즌": 1649, "공연명": "데스노트", "기타": "9차"},
    ]

    def test_duplicate_found(self):
        assert check_duplicate(1705, "마지막", self.EXISTING_OPENS) is True

    def test_no_duplicate(self):
        assert check_duplicate(1705, "1차", self.EXISTING_OPENS) is False

    def test_same_name_different_season(self):
        assert check_duplicate(9999, "마지막", self.EXISTING_OPENS) is False
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `python -m pytest tests/test_matcher.py -v`
Expected: FAIL (matcher 모듈 없음)

- [ ] **Step 3: 커밋**

```bash
git add tests/test_matcher.py
git commit -m "test: add matcher unit tests for name, season, and duplicate matching"
```

### Task 5: matcher.py 구현

**Files:**
- Create: `matcher.py`

- [ ] **Step 1: matcher.py 구현**

```python
# matcher.py
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
```

- [ ] **Step 2: 테스트 실행 — 통과 확인**

Run: `python -m pytest tests/test_matcher.py -v`
Expected: ALL PASS

- [ ] **Step 3: 커밋**

```bash
git add matcher.py
git commit -m "feat: implement performance name, season, and duplicate matching"
```

---

## Chunk 4: podor API 클라이언트 (podor_api.py)

### Task 6: podor_api.py 구현

**Files:**
- Create: `podor_api.py`

- [ ] **Step 1: podor_api.py 구현**

```python
# podor_api.py
"""podor.co.kr API 클라이언트"""
import requests
from config import PODOR_BASE_URL, PODOR_USER_ID, PODOR_PASSWORD


class PodorAPI:
    def __init__(self):
        self.base_url = PODOR_BASE_URL
        self.token = None
        self._performances = None
        self._places = None
        self._seasons = None
        self._opens = None

    def login(self) -> str:
        """JWT 토큰 획득"""
        resp = requests.post(
            f"{self.base_url}/accounts/login/",
            json={"user_id": PODOR_USER_ID, "password": PODOR_PASSWORD},
            timeout=10,
        )
        resp.raise_for_status()
        self.token = resp.json()["token"]
        return self.token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    def _get(self, path: str) -> list:
        resp = requests.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def get_performances(self) -> list[dict]:
        """전체 공연 목록 (캐싱)"""
        if self._performances is None:
            self._performances = self._get("/api/performance/")
        return self._performances

    def get_places(self) -> list[dict]:
        """전체 공연장 목록 (캐싱)"""
        if self._places is None:
            self._places = self._get("/api/performance-place/")
        return self._places

    def get_seasons(self) -> list[dict]:
        """전체 시즌 목록 (캐싱)"""
        if self._seasons is None:
            self._seasons = self._get("/api/performance-season/")
        return self._seasons

    def get_opens(self) -> list[dict]:
        """전체 performance-open 목록 (캐싱)"""
        if self._opens is None:
            self._opens = self._get("/api/performance-open/")
        return self._opens
```

- [ ] **Step 2: 커밋**

```bash
git add podor_api.py
git commit -m "feat: implement podor API client with login and cached data fetching"
```

---

## Chunk 5: 인터파크 스크래퍼 (scraper.py)

### Task 7: scraper.py 구현

**Files:**
- Create: `scraper.py`

- [ ] **Step 1: scraper.py 구현**

```python
# scraper.py
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
    items = []
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

        # 공연명 (페이지 상단 타이틀)
        title_el = page.query_selector("h2, h1, .prdTitle")
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
```

- [ ] **Step 2: 커밋**

```bash
git add scraper.py
git commit -m "feat: implement interpark scraper with Playwright"
```

---

## Chunk 6: 메일 발송 (mailer.py)

### Task 8: mailer.py 구현

**Files:**
- Create: `mailer.py`

- [ ] **Step 1: mailer.py 구현**

```python
# mailer.py
"""메일 발송"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
from config import SMTP_EMAIL, SMTP_PASSWORD, NOTIFY_EMAIL

logger = logging.getLogger(__name__)


def build_report(
    new_items: list[dict],
    unregistered_performances: list[dict],
    unregistered_seasons: list[dict],
    parse_failures: list[dict],
    match_failures: list[dict],
    duplicates: list[dict],
    kids_excluded: list[dict],
) -> str:
    """메일 본문 생성"""
    today = date.today().strftime("%Y-%m-%d")
    lines = [f"[NOL 티켓 오픈 알림] {today}", ""]

    # 신규 발견
    if new_items:
        lines.append(f"■ 신규 발견 {len(new_items)}건 (등록 가능):")
        for i, item in enumerate(new_items, 1):
            lines.append(
                f"{i}. {item['공연명']} | {item['기타']} | "
                f"{item['오픈날짜']} {item['오픈시간']} | {item['오픈회차']}"
            )
        lines.append("")

    # podor 미등록 공연
    if unregistered_performances:
        lines.append(f"■ podor 미등록 공연 {len(unregistered_performances)}건 (공연정보 자체가 없음):")
        for item in unregistered_performances:
            lines.append(f"- \"{item['raw_title']}\" — podor에 공연 등록 필요")
        lines.append("")

    # 시즌 미등록
    if unregistered_seasons:
        lines.append(f"■ 시즌 미등록 {len(unregistered_seasons)}건 (공연은 있으나 해당 시즌 없음):")
        for item in unregistered_seasons:
            lines.append(
                f"- \"{item['공연명']}\" — 전체공연기간 {item.get('period_start', '?')}~{item.get('period_end', '?')}에 해당하는 시즌 없음"
            )
        lines.append("")

    # 파싱 실패
    if parse_failures:
        lines.append(f"■ 파싱 실패 {len(parse_failures)}건 (티켓오픈 정보 추출 불가):")
        for item in parse_failures:
            lines.append(f"- \"{item['raw_title']}\" — 오픈 일시 형식 인식 실패")
        lines.append("")

    # 매칭 실패
    if match_failures:
        lines.append(f"■ 매칭 실패 {len(match_failures)}건 (공연명 추정 불가):")
        for item in match_failures:
            lines.append(f"- \"{item['raw_title']}\" — podor 공연 목록에서 유사 공연명 못 찾음")
        lines.append("")

    # 이미 등록됨
    if duplicates:
        lines.append(f"■ 이미 등록됨 {len(duplicates)}건 (스킵)")
        lines.append("")

    # 어린이 뮤지컬 제외
    if kids_excluded:
        lines.append(f"■ 어린이 뮤지컬 제외 {len(kids_excluded)}건:")
        names = ", ".join(item["raw_title"] for item in kids_excluded)
        lines.append(f"- {names}")
        lines.append("")

    # 아무 내용도 없으면
    if not any([new_items, unregistered_performances, unregistered_seasons,
                parse_failures, match_failures, duplicates, kids_excluded]):
        lines.append("수집 결과 없음 (스크래핑 오류 가능성이 있습니다. 확인 필요)")

    return "\n".join(lines)


def send_email(subject: str, body: str) -> bool:
    """Gmail SMTP로 메일 발송. 실패 시 False 반환."""
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_EMAIL
        msg["To"] = NOTIFY_EMAIL
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, NOTIFY_EMAIL, msg.as_string())

        logger.info(f"Email sent to {NOTIFY_EMAIL}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False
```

- [ ] **Step 2: 커밋**

```bash
git add mailer.py
git commit -m "feat: implement email report builder and sender"
```

---

## Chunk 7: 메인 실행 & GitHub Actions

### Task 9: main.py 구현

**Files:**
- Create: `main.py`

- [ ] **Step 1: main.py 구현**

```python
# main.py
"""NOL 티켓 오픈 스크래퍼 진입점"""
import logging
from datetime import date

from scraper import run_scraper
from parser import parse_open_info, parse_performance_period, parse_venue, parse_title, is_kids_musical
from podor_api import PodorAPI
from matcher import match_performance_name, match_season, check_duplicate
from mailer import build_report, send_email

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
            # 기간 없이도 시즌 매칭 시도 불가 → 시즌 미등록으로 분류
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

            new_items.append({
                "시즌": season_id,
                "공연명": std_name,
                "오픈날짜": open_info["오픈날짜"],
                "오픈시간": open_info["오픈시간"],
                "기타": open_round,
                "오픈회차": open_info["오픈회차"],
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

    # 메일 발송 시도, 실패 시 stdout 출력
    if not send_email(subject, report):
        logger.error("메일 발송 실패 — stdout으로 리포트 출력")
        print("=" * 60)
        print(report)
        print("=" * 60)
    else:
        # 성공해도 로그에 요약 출력
        logger.info(
            f"완료 — 신규 {len(new_items)}건, "
            f"미등록공연 {len(unregistered_performances)}건, "
            f"시즌미등록 {len(unregistered_seasons)}건, "
            f"파싱실패 {len(parse_failures)}건, "
            f"매칭실패 {len(match_failures)}건, "
            f"중복 {len(duplicates)}건, "
            f"어린이제외 {len(kids_excluded)}건"
        )

    # stdout에도 리포트 출력 (GitHub Actions 로그용)
    print(report)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 커밋**

```bash
git add main.py
git commit -m "feat: implement main orchestrator for scrape, match, and report"
```

### Task 10: GitHub Actions 워크플로우

**Files:**
- Create: `.github/workflows/daily_scrape.yml`

- [ ] **Step 1: 워크플로우 작성**

```yaml
# .github/workflows/daily_scrape.yml
name: Daily Ticket Open Scraper

on:
  schedule:
    # 매일 오전 9시 KST = 자정 UTC
    - cron: '0 0 * * *'
  workflow_dispatch:  # 수동 실행 가능

jobs:
  scrape:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium
          playwright install-deps

      - name: Run scraper
        env:
          PODOR_USER_ID: ${{ secrets.PODOR_USER_ID }}
          PODOR_PASSWORD: ${{ secrets.PODOR_PASSWORD }}
          SMTP_EMAIL: ${{ secrets.SMTP_EMAIL }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
          NOTIFY_EMAIL: ${{ secrets.NOTIFY_EMAIL }}
        run: python main.py
```

- [ ] **Step 2: 커밋**

```bash
git add .github/
git commit -m "ci: add GitHub Actions daily scrape workflow"
```

### Task 11: 수동 테스트 실행

- [ ] **Step 1: 로컬에서 환경변수 설정 후 테스트 실행**

```bash
export PODOR_USER_ID="podor"
export PODOR_PASSWORD="tndlrckdcnfgkwk!"
export SMTP_EMAIL="your-gmail@gmail.com"
export SMTP_PASSWORD="your-app-password"
export NOTIFY_EMAIL="tingsung93@naver.com"
python main.py
```

출력 확인: 스크래핑 → 매칭 → 메일 발송 로그가 정상적으로 나오는지 확인

- [ ] **Step 2: 스크래퍼 셀렉터 문제 시 scraper.py 디버깅**

Playwright가 인터파크 페이지의 실제 DOM 구조와 맞지 않는 셀렉터를 사용할 수 있음. `headless=False`로 변경하여 브라우저를 직접 보며 셀렉터 수정.

- [ ] **Step 3: GitHub에 push 및 Secrets 설정**

```bash
git remote add origin <your-github-repo-url>
git push -u origin master
```

GitHub repo → Settings → Secrets and variables → Actions에서 5개 시크릿 등록:
- `PODOR_USER_ID`
- `PODOR_PASSWORD`
- `SMTP_EMAIL`
- `SMTP_PASSWORD`
- `NOTIFY_EMAIL`

- [ ] **Step 4: GitHub Actions 수동 실행으로 E2E 테스트**

GitHub repo → Actions → Daily Ticket Open Scraper → Run workflow 버튼 클릭.
메일 수신 확인.
