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
