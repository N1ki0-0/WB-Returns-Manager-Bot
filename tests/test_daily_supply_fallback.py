import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from app.application.usecases_daily_supply import CreateDailySupplyUseCase

pytestmark = pytest.mark.asyncio

class FakeMarketplace:
    async def get_new_orders(self):
        return {
            "orders": [
                {"id": 1, "nmId": 111, "quantity": 1, "colorCode": "черный"},
                {"id": 2, "nmId": 111, "quantity": 1, "colorCode": "черный"},
                {"id": 3, "nmId": 222, "quantity": 1, "colorCode": "белый"},
            ]
        }

    async def create_supply(self, name: str):
        return {"id": "SUP-1"}

    async def add_orders_to_supply(self, supply_id: str, order_ids: list[int]):
        return {}

class Always429Content:
    async def find_card_by_text(self, text: str, locale: str = "ru"):
        raise Exception("HTTPStatusError: 429 Too Many Requests")

class FakeRepo:
    def __init__(self):
        self.saved = None
        self.ran = False

    async def already_ran(self, day_key: str) -> bool:
        return False

    async def mark_ok(self, day_key: str, supply_id: str, created_at, order_count: int, report_text: str):
        self.saved = {"day_key": day_key, "supply_id": supply_id, "order_count": order_count, "report_text": report_text}

    async def mark_failed(self, day_key: str, created_at, error: str):
        self.saved = {"day_key": day_key, "error": error}

class FakeNotifier:
    def __init__(self):
        self.messages = []

    async def notify_admins(self, text: str) -> None:
        self.messages.append(text)

async def test_daily_supply_sends_report_even_if_content_rate_limited():
    mp = FakeMarketplace()
    content = Always429Content()
    repo = FakeRepo()
    notifier = FakeNotifier()

    usecase = CreateDailySupplyUseCase(
        marketplace_client=mp,
        content_client=content,
        daily_repo=repo,
        notifier=notifier,
        tz="Europe/Moscow",
        enabled=True,
    )

    res = await usecase.run()

    # supply создан
    assert res.supply_id == "SUP-1"
    # итог по количеству (3 заказа по 1)
    assert res.total_qty == 3

    # сообщение отправлено, даже если карточки не получены
    assert len(notifier.messages) >= 1
    msg = notifier.messages[-1]
    assert "Создана поставка: SUP-1" in msg
    assert "3 шт" in msg  # общий итог

    # отчёт сохранён в репо
    assert repo.saved is not None
    assert "report_text" in repo.saved
