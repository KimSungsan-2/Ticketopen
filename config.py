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
