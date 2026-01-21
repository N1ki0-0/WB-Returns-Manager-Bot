from typing import Any
from app.application.ports import WbReturnsPort
from .client import WbReturnsClient

class WbReturnsAdapter(WbReturnsPort):
    def __init__(self, client: WbReturnsClient):
        self._client = client

    async def get_open_claims(self) -> list[dict[str, Any]]:
        # можно пагинировать, если total > limit
        resp = await self._client.get_claims(is_archive=False, limit=200, offset=0)
        return resp.get("claims", [])

    async def answer_claim(self, claim_id: str, action: str, comment: str | None) -> dict[str, Any]:
        return await self._client.answer_claim(claim_id, action, comment)
