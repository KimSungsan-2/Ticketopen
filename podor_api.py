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
