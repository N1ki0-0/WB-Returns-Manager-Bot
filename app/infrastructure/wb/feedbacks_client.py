import httpx
from typing import Any

class WbFeedbacksClient:
    BASE = "https://feedbacks-api.wildberries.ru"

    def __init__(self, token: str, timeout: float = 30.0):
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": token},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def list_feedbacks(self, *, is_answered: bool = False, take: int = 500, skip: int = 0) -> dict[str, Any]:
        # Конкретные параметры могут отличаться; ориентируемся на раздел Feedbacks. :contentReference[oaicite:4]{index=4}
        r = await self._client.get(
            f"{self.BASE}/api/v1/feedbacks",
            params={
                "isAnswered": str(is_answered).lower(),
                "take": take,
                "skip": skip,
            },
        )
        r.raise_for_status()
        return r.json()
