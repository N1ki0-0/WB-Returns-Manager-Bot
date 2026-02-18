import pytest
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from app.application.usecases_daily_supply import CreateDailySupplyUseCase, DailySupplyResult

pytestmark = pytest.mark.asyncio

class FakeMarketplace:
    def __init__(self):
        self.created = False
        self.added_orders = None

    async def get_new_orders(self):
        # два заказа, разные nmId
        return {
            "orders": [
                {"id": 1, "nmId": 111111, "quantity": 2, "offerName": "Samsung A25 Black"},
                {"id": 2, "nmId": 222222, "quantity": 3, "offerName": "Redmi 12 Blue"},
            ]
        }

    async def create_supply(self, name: str):
        self.created = True
        return {"id": "TEST-SUP-1"}

    async def add_orders_to_supply(self, supply_id: str, order_ids: list[int]):
        self.added_orders = list(order_ids)
        return {}

class SpyContentClient:
    def __init__(self):
        self.calls = []  # will collect texts searched (nmId as str)

    async def find_card_by_text(self, text: str, locale: str = "ru"):
        # record call and return synthetic card
        self.calls.append(text)
        nm = int(text)
        return {
            "cards": [
                {
                    "nmID": nm,
                    "title": f"FakeTitle {nm}",
                    "characteristics": [{"name": "Цвет", "value": ["black"]}],
                }
            ]
        }

class FakeProductCacheRepo:
    # simulate empty persistent cache so content client is used
    def __init__(self):
        self.store = {}

    async def get(self, nm_id: int):
        return None

    async def set(self, nm_id: int, title: str | None, color: str | None):
        self.store[nm_id] = (title, color)

class SpyDailyRepo:
    def __init__(self):
        self.did_mark_ok = False
        self.saved = None

    async def already_ran(self, day_key: str) -> bool:
        return False

    async def mark_ok(self, day_key: str, supply_id: str, created_at, order_count: int, report_text: str):
        self.did_mark_ok = True
        self.saved = {
            "day_key": day_key,
            "supply_id": supply_id,
            "order_count": order_count,
            "report_text": report_text,
        }

class SpyNotifier:
    def __init__(self):
        self.messages = []

    async def notify_admins(self, text: str):
        self.messages.append(text)

async def test_create_supply_and_call_content_for_each_nmId():
    mp = FakeMarketplace()
    content = SpyContentClient()
    cache_repo = FakeProductCacheRepo()
    daily_repo = SpyDailyRepo()
    notifier = SpyNotifier()

    uc = CreateDailySupplyUseCase(
        marketplace_client=mp,
        content_client=content,
        product_cache_repo=cache_repo,
        daily_repo=daily_repo,
        notifier=notifier,
        tz="Europe/Moscow",
        enabled=True,
        batch_size=2,         # process both without pause
        batch_pause_sec=0,
        cards_limit=100,
    )

    res = await uc.run()

    # Проверяем что supply создался и orders добавлены
    assert mp.created is True
    assert mp.added_orders == [1, 2]

    # Проверяем что Content client был вызван для каждого nmId (в виде строки)
    assert "111111" in content.calls
    assert "222222" in content.calls
    assert len(content.calls) >= 2

    # Проверяем что usecase отправил уведомление админам
    assert len(notifier.messages) >= 1
    assert daily_repo.did_mark_ok is True
    assert res.total_qty == 5  # 2 + 3
