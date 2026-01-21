import httpx
from typing import Any

class WbMarketplaceClient:
    BASE = "https://marketplace-api.wildberries.ru"

    def __init__(self, token: str, timeout: float = 30.0):
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": token},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_new_orders(self) -> dict[str, Any]:
        # GET /api/v3/orders/new  :contentReference[oaicite:1]{index=1}
        r = await self._client.get(f"{self.BASE}/api/v3/orders/new")
        r.raise_for_status()
        return r.json()

    async def create_supply(self, name: str) -> dict[str, Any]:
        # POST /api/v3/supplies  :contentReference[oaicite:2]{index=2}
        r = await self._client.post(f"{self.BASE}/api/v3/supplies", json={"name": name})
        r.raise_for_status()
        return r.json()

    async def add_orders_to_supply(self, supply_id: str, order_ids: list[int]) -> dict[str, Any]:
        # PATCH /api/marketplace/v3/supplies/{supplyId}/orders  :contentReference[oaicite:2]{index=2}
        r = await self._client.patch(
            f"{self.BASE}/api/marketplace/v3/supplies/{supply_id}/orders",
            json={"orders": order_ids[:100]},  # за раз до 100 заказов :contentReference[oaicite:3]{index=3}
        )
        r.raise_for_status()
        return r.json() if r.content else {}
