# tests/test_daily_supply_fake_orders.py
import pytest
from datetime import datetime
from app.application.usecases_daily_supply import CreateDailySupplyUseCase

# ---------------- FAKE WB MARKETPLACE ----------------

class FakeMarketplace:
    def __init__(self):
        self.created_supply = None
        self.added_orders = []

    async def get_new_orders(self):
        return {
            "orders": [
                {
                    "id": 1,
                    "nmId": 111,
                    "offerName": "Смартфон Xiaomi Redmi Note 13 8/256GB Black",
                    "quantity": 2,
                },
                {
                    "id": 2,
                    "nmId": 222,
                    "offerName": "Apple iPhone 13 128GB Blue",
                    "quantity": 1,
                },
                {
                    "id": 3,
                    "nmId": 111,
                    "offerName": "Смартфон Xiaomi Redmi Note 13 8/256GB Black",
                    "quantity": 1,
                },
            ]
        }

    async def create_supply(self, name):
        self.created_supply = "TEST-SUPPLY-1"
        return {"id": self.created_supply}

    async def add_orders_to_supply(self, supply_id, order_ids):
        self.added_orders.extend(order_ids)

# ---------------- FAKE CONTENT API ----------------

class FakeContentClient:
    async def find_card_by_text(self, text: str, locale="ru"):
        nm_id = int(text)

        if nm_id == 111:
            return {
                "cards": [{
                    "nmID": 111,
                    "title": "Xiaomi Redmi Note 13 8/256GB",
                    "characteristics": [{"name": "Цвет", "value": ["Black"]}]
                }]
            }

        if nm_id == 222:
            return {
                "cards": [{
                    "nmID": 222,
                    "title": "Apple iPhone 13 128GB",
                    "characteristics": [{"name": "Цвет", "value": ["Blue"]}]
                }]
            }

        return {"cards": []}

# ---------------- FAKE REPO + NOTIFIER ----------------

class FakeDailyRepo:
    async def already_ran(self, day_key):
        return False

    # Поддерживаем сигнатуру, которую вызывает usecase:
    async def mark_ok(self, day_key, supply_id, created_at, order_count, report_text):
        # В тесте ничего не делаем — но принимаем аргументы
        return

    async def mark_failed(self, day_key, created_at=None, error=None):
        return

class FakeNotifier:
    def __init__(self):
        self.messages = []

    async def notify_admins(self, text):
        self.messages.append(text)

# ---------------- TEST ----------------

@pytest.mark.asyncio
async def test_daily_supply_builds_phone_list_from_orders():
    mp = FakeMarketplace()
    content = FakeContentClient()
    repo = FakeDailyRepo()
    notifier = FakeNotifier()

    uc = CreateDailySupplyUseCase(
        marketplace_client=mp,
        content_client=content,
        daily_repo=repo,
        notifier=notifier,
        tz="Europe/Moscow",
        enabled=True,
        batch_size=10,
        batch_pause_sec=0,
    )

    result = await uc.run()

    # Supply создан
    assert result.supply_id == "TEST-SUPPLY-1"

    # Всего товаров: 2 + 1 + 1 = 4
    assert result.total_qty == 4

    # Проверяем, что нормализованный список содержит ожидаемые пары "13 black" и "13 blue"
    text = "\n".join(result.lines)
    assert "13 black" in text.lower() or "13 black" in text
    assert "13 blue" in text.lower() or "13 blue" in text

    # Проверяем что сообщение реально отправилось
    assert len(notifier.messages) == 1

    print("\n=== СФОРМИРОВАННЫЙ СПИСОК ===")
    print(notifier.messages[0])
