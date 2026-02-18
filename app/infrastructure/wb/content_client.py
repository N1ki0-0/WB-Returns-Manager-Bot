import asyncio
import httpx
from typing import Any
import random
from typing import Any
import logging

log = logging.getLogger("wb_content")

class WbContentClient:
    BASE = "https://content-api.wildberries.ru"

    def __init__(self, token: str, timeout: float = 30.0, max_parallel: int = 3):
        self._client = httpx.AsyncClient(timeout=timeout, headers={"Authorization": token})
        self._sem = asyncio.Semaphore(max_parallel)
        self._max_parallel = max_parallel

    async def close(self):
        await self._client.aclose()

    async def _post_with_rate_limit_retry(self, url: str, params=None, json=None, max_attempts: int = 6):
        attempt = 0
        base_sleep = 1.0
        while True:
            attempt += 1
            try:
                r = await self._client.post(url, params=params, json=json)
            except (httpx.RequestError, httpx.ConnectError) as e:
                log.warning("Content POST request error (attempt %s): %s", attempt, e)
                if attempt >= max_attempts:
                    raise
                await asyncio.sleep(min(30, base_sleep * (2 ** (attempt - 1)) + random.random()))
                continue

            # Logging for diagnostics
            if r.status_code == 429:
                log.warning("Content API 429. headers=%s body_snippet=%s", dict(r.headers), r.text[:200])

            if r.status_code == 429:
                retry_s = r.headers.get("X-Ratelimit-Retry") or r.headers.get("Retry-After") or r.headers.get("X-RateLimit-Reset")
                try:
                    wait = int(retry_s)
                except Exception:
                    wait = int(min(30, base_sleep * (2 ** (attempt - 1)) + random.random()))
                if attempt >= max_attempts:
                    return r
                await asyncio.sleep(wait + 1)
                continue

            if 500 <= r.status_code < 600:
                log.warning("Content API 5xx (%s). attempt=%s", r.status_code, attempt)
                if attempt >= max_attempts:
                    return r
                await asyncio.sleep(min(30, base_sleep * (2 ** (attempt - 1)) + random.random()))
                continue

            return r

    async def find_card_by_text(self, text: str, locale: str = "ru", limit: int = 100) -> dict[str, Any]:
        payload = {
            "settings": {
                "cursor": {"limit": limit},
                "filter": {"textSearch": text, "withPhoto": -1},
            }
        }
        # семафор вокруг запроса: не более N параллельных вызовов
        async with self._sem:
            r = await self._post_with_rate_limit_retry(f"{self.BASE}/content/v2/get/cards/list", params={"locale": locale}, json=payload)
        try:
            r.raise_for_status()
        except Exception:
            # логируем полный ответ для диагностики
            log.warning("Content API error for text=%s status=%s body=%s", text, getattr(r, "status_code", None), getattr(r, "text", "")[:1000])
            raise
        return r.json()