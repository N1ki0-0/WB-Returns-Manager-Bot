import asyncio
import httpx
from typing import Any

class WbContentClient:
    BASE = "https://content-api.wildberries.ru"

    def __init__(self, token: str, timeout: float = 30.0):
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": token},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _post_with_rate_limit_retry(self, url: str, *, params: dict[str, Any] | None, json: dict[str, Any]) -> httpx.Response:
        # 429: ждать X-Ratelimit-Retry секунд и повторить :contentReference[oaicite:1]{index=1}
        max_attempts = 6
        for attempt in range(1, max_attempts + 1):
            r = await self._client.post(url, params=params, json=json)

            if r.status_code != 429:
                return r

            # 429 handling
            retry_s = r.headers.get("X-Ratelimit-Retry")
            try:
                wait = int(retry_s) if retry_s is not None else 2
            except ValueError:
                wait = 2

            # небольшой дополнительный буфер, чтобы не попасть снова
            wait = max(wait, 1) + 1

            if attempt == max_attempts:
                return r

            await asyncio.sleep(wait)

        # сюда не должны попасть
        return r

    async def find_card_by_text(self, text: str, locale: str = "ru") -> dict[str, Any]:
        payload = {
            "settings": {
                "cursor": {"limit": 10},
                "filter": {"textSearch": text, "withPhoto": -1},
            }
        }

        r = await self._post_with_rate_limit_retry(
            f"{self.BASE}/content/v2/get/cards/list",
            params={"locale": locale},
            json=payload,
        )
        r.raise_for_status()
        return r.json()
