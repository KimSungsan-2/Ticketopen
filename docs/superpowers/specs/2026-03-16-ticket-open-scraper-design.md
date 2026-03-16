# NOL 티켓 오픈 스크래퍼 설계

## 목적

인터파크(NOL 티켓)에서 뮤지컬/서울 지역의 티켓 오픈 예정 목록을 매일 자동으로 수집하고, podor.co.kr에 미등록된 항목을 메일로 알려주는 시스템.

## 전체 흐름

```
[GitHub Actions - 매일 오전 9시 KST]
        │
        ▼
[1. 인터파크 스크래핑 (Playwright)]
   - tickets.interpark.com/contents/notice 접속
   - 장르: 뮤지컬, 지역: 서울 필터 적용
   - 목록에서 각 공연 상세 페이지 URL 수집
   - 각 상세 페이지에서 추출:
     · 공연명 (원문)
     · 티켓오픈 일시 (날짜 + 시간)
     · 오픈차수 (1차, 2차, 마지막 등)
     · 오픈공연기간
     · 공연장
     · 전체공연기간
   - 어린이 뮤지컬 필터링 (키워드: 어린이, 키즈, Kids, 가족, 패밀리)
        │
        ▼
[2. podor API 매칭]
   - POST /accounts/login/ → JWT 토큰 획득
   - GET /api/performance/ → 표준 공연명 매칭
   - GET /api/performance-place/ → 표준 공연장명 매칭
   - GET /api/performance-season/ → 시즌 id 매칭 (공연기간 포함 여부 비교)
        │
        ▼
[3. 중복 체크]
   - GET /api/performance-open/ → 기존 데이터 조회
   - 공연명 + 기타(오픈차수) 조합으로 중복 확인
        │
        ▼
[4. 메일 발송]
   - 신규/미등록/매칭실패/스킵 항목을 분류하여 메일 발송
   - 수신: tingsung93@naver.com
```

## 데이터 매핑

인터파크 상세 페이지에서 추출한 데이터를 podor API의 `performance-open` 필드에 매핑:

| podor 필드 | 소스 | 예시 |
|---|---|---|
| `시즌` | season id (공연기간 포함 여부로 매칭) | `1705` |
| `공연명` | 표준 공연명 (GET /api/performance/ 에서 매칭) | `"은밀하게 위대하게"` |
| `오픈날짜` | 상세 페이지 티켓오픈 날짜 (YYYY-MM-DD) | `"2026-03-17"` |
| `오픈시간` | 상세 페이지 티켓오픈 시간 (HH:MM) | `"11:00"` |
| `기타` | 오픈차수 | `"마지막"` |
| `오픈회차` | 오픈공연기간 | `"4월 11일 - 4월 26일"` |

## 어린이 뮤지컬 필터링

공연명에 아래 키워드가 포함되면 제외:
- 어린이, 키즈, Kids, 가족, 패밀리, Family

## 엣지 케이스 처리

1. **표준 공연명 매칭 실패**: 인터파크 공연명에서 부제/콜론 이후를 제거하며 유사도 검색. 못 찾으면 "매칭 실패"로 분류.
2. **시즌 매칭 실패**: 같은 공연명의 시즌이 여러 개일 때 전체공연기간이 겹치는 시즌 선택. 못 찾으면 "시즌 미등록"으로 분류.
3. **podor 미등록 공연**: performance API에 공연 자체가 없으면 "podor 미등록 공연"으로 분류.
4. **티켓오픈 정보 파싱 실패**: 상세 페이지 텍스트에서 정규식으로 추출. 다양한 형식 대응.
5. **하나의 상세 페이지에 여러 오픈 차수**: 각 차수별 별도 레코드로 처리.

## 메일 양식

```
[NOL 티켓 오픈 알림] 2026-03-16

■ 신규 발견 2건 (등록 가능):
1. 은밀하게 위대하게 | 마지막 | 3월 17일 11시 | 4월 11일-4월 26일
2. 팬레터 | 3차 | 3월 19일 14시 | 4월 28일-5월 17일

■ podor 미등록 공연 1건 (공연정보 자체가 없음):
- "뉴뮤지컬 OO" — podor에 공연 등록 필요

■ 시즌 미등록 1건 (공연은 있으나 해당 시즌 없음):
- "홍련" — 공연기간 2026.03~06에 해당하는 시즌 없음

■ 매칭 실패 1건 (공연명 추정 불가):
- "은밀하게 위대하게:THE LAST-10주년 기념공연" — 유사 공연명 못 찾음

■ 이미 등록됨 8건 (스킵)

■ 어린이 뮤지컬 제외 2건:
- 키즈뮤지컬 OO, 가족뮤지컬 XX
```

## 프로젝트 구조

```
Ticketopen/
├── .github/
│   └── workflows/
│       └── daily_scrape.yml    # GitHub Actions 워크플로우 (매일 09:00 KST)
├── main.py                     # 진입점 - 전체 흐름 실행
├── scraper.py                  # 인터파크 스크래핑 (Playwright)
├── podor_api.py                # podor API 연동 (로그인, 조회)
├── matcher.py                  # 공연명/공연장/시즌 매칭 로직
├── parser.py                   # 상세 페이지 텍스트 파싱 (오픈일시, 차수 추출)
├── mailer.py                   # 메일 발송 (SMTP)
├── config.py                   # 설정 (필터 키워드 등, 민감정보는 환경변수)
└── requirements.txt            # playwright, requests
```

## 기술 스택

- **Python 3.11**
- **Playwright**: 인터파크 동적 페이지 스크래핑
- **requests**: podor API 호출
- **smtplib**: 메일 발송 (Gmail SMTP)
- **GitHub Actions**: 매일 자동 실행 (cron)

## 환경 변수 (GitHub Secrets)

- `PODOR_USER_ID`: podor 로그인 ID
- `PODOR_PASSWORD`: podor 로그인 비밀번호
- `SMTP_EMAIL`: 발송용 Gmail 주소
- `SMTP_PASSWORD`: Gmail 앱 비밀번호
- `NOTIFY_EMAIL`: 수신 메일 (tingsung93@naver.com)

## 중복 체크 기준

`공연명` + `기타`(오픈차수)가 동일하면 중복으로 판단하여 스킵.
