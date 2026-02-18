import pytest
from app.application.usecases_daily_supply import CreateDailySupplyUseCase

pytestmark = pytest.mark.asyncio

class FakeMP:
    async def get_new_orders(self):
        return {
            "orders": [
                {"id": 1, "nmId": 111, "quantity": 2, "offerName": "Samsung A25 Black"},
                {"id": 2, "nmId": 222, "quantity": 3, "offerName": "Redmi 12 Blue"},
            ]
        }
    async def create_supply(self, name):
        return {"id": "S1"}
    async def add_orders_to_supply(self, supply_id, order_ids):
        return {}

class ContentAlwaysError:
    async def find_card_by_text(self, text, locale="ru"):
        raise Exception("Content down")

class FakeRepo:
    async def already_ran(self, day_key): return False
    async def mark_ok(self, *args, **kwargs): pass

class FakeNotifier:
    def __init__(self): self.msgs=[]
    async def notify_admins(self, text): self.msgs.append(text)

class FakeCacheRepo:
    async def get(self, nm_id): return None
    async def set(self, nm_id, title, color): pass

async def test_fallback_to_offerName():
    mp = FakeMP()
    content = ContentAlwaysError()
    cache_repo = FakeCacheRepo()
    repo = FakeRepo()
    notifier = FakeNotifier()

    uc = CreateDailySupplyUseCase(
        marketplace_client=mp,
        content_client=content,
        daily_repo=repo,
        notifier=notifier,
        tz="Europe/Moscow",
        enabled=True,
        product_cache_repo=cache_repo,
        batch_size=2,
        batch_pause_sec=0,
    )

    res = await uc.run()

    # проверяем, что в lines нет UNKNOWN, а стоят короткие нормализованные имена
    assert any("A25" in l or "Redmi" in l for l in res.lines)
    assert "UNKNOWN" not in " ".join(res.lines)
