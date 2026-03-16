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
