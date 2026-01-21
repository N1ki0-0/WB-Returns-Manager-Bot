import pytest
import respx
import httpx

from app.infrastructure.wb.content_client import WbContentClient

pytestmark = pytest.mark.asyncio

@respx.mock
async def test_content_client_retries_on_429(monkeypatch):
    token = "test"
    client = WbContentClient(token)

    url = "https://content-api.wildberries.ru/content/v2/get/cards/list"

    # 1-й ответ 429, просит подождать 1 сек
    # 2-й ответ 200
    call_count = {"n": 0}

    def handler(request: httpx.Request):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return httpx.Response(
                429,
                headers={"X-Ratelimit-Retry": "1"},
                json={"error": "rate limited"},
            )
        return httpx.Response(
            200,
            json={"cards": [{"nmID": 123, "title": "Redmi 12", "characteristics": [{"name": "Цвет", "value": ["белый"]}]}]},
        )

    respx.post(url).mock(side_effect=handler)

    # Чтобы тест не ждал реально 2 секунды, подменяем sleep на “мгновенный”
    import asyncio
    async def fast_sleep(_):
        return None
    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    data = await client.find_card_by_text("123", locale="ru")
    await client.close()

    assert call_count["n"] == 2
    assert data["cards"][0]["title"] == "Redmi 12"
