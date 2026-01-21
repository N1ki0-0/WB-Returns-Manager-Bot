import httpx
from typing import Any

class WbReturnsClient:
    BASE = "https://returns-api.wildberries.ru"

    def __init__(self, token: str, timeout: float = 20.0):
        self._headers = {"Authorization": token}  # WB использует HeaderApiKey (токен) в заголовке
        self._client = httpx.AsyncClient(timeout=timeout, headers=self._headers)

    async def close(self) -> None:
        await self._client.aclose()

    async def get_claims(self, is_archive: bool, limit: int = 200, offset: int = 0) -> dict[str, Any]:
        # GET /api/v1/claims (current 14 days)  :contentReference[oaicite:8]{index=8}
        r = await self._client.get(
            f"{self.BASE}/api/v1/claims",
            params={"is_archive": str(is_archive).lower(), "limit": limit, "offset": offset},
        )
        r.raise_for_status()
        return r.json()

    async def answer_claim(self, claim_id: str, action: str, comment: str | None = None) -> dict[str, Any]:
        # PATCH /api/v1/claim  :contentReference[oaicite:9]{index=9}
        payload: dict[str, Any] = {"id": claim_id, "action": action}
        if comment is not None:
            payload["comment"] = comment

        r = await self._client.patch(f"{self.BASE}/api/v1/claim", json=payload)
        r.raise_for_status()
        return r.json() if r.content else {}
