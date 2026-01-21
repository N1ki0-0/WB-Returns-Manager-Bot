import pytest
from app.application.usecases_quality_clone import CloneOnOneStarFeedbackUseCase

pytestmark = pytest.mark.asyncio

class FakeFeedbacks:
    async def list_feedbacks(self, **kwargs):
        return {
            "feedbacks": [
                {"id": "F1", "productValuation": 1, "productDetails": {"nmId": 111}},
            ]
        }

class FakeCardsReader:
    async def get_card_by_nm_id(self, nm_id: int):
        return {
            "vendorCode": "Redmi 12",
            "subjectID": 123,
            "title": "Redmi 12",
            "description": "desc",
            "characteristics": [{"name": "Цвет", "value": ["белый"]}],
        }

    async def find_vendor_codes_like(self, vendor_code: str):
        return {"Redmi 12 (1)"}  # значит следующий должен стать (2)

class FakeCardsWriter:
    def __init__(self):
        self.created = []

    async def create_card(self, payload: dict):
        self.created.append(payload)
        return 999999

class FakeRepo:
    def __init__(self):
        self.processed = set()
        self.ok = []
        self.fail = []

    async def was_processed(self, feedback_id: str) -> bool:
        return feedback_id in self.processed

    async def mark_cloned(self, feedback_id: str, nm_id: int, new_nm_id: str, created_at):
        self.processed.add(feedback_id)
        self.ok.append((feedback_id, nm_id, new_nm_id))

    async def mark_failed(self, feedback_id: str, nm_id: int, created_at, error: str):
        self.fail.append((feedback_id, nm_id, error))

class FakeNotifier:
    def __init__(self):
        self.msgs = []
    async def notify_admins(self, text: str):
        self.msgs.append(text)

async def test_clone_created_on_one_star():
    uc = CloneOnOneStarFeedbackUseCase(
        feedbacks=FakeFeedbacks(),
        cards_reader=FakeCardsReader(),
        cards_writer=FakeCardsWriter(),
        clone_repo=FakeRepo(),
        notifier=FakeNotifier(),
        enabled=True,
    )

    res = await uc.run()
    assert res.triggered == 1
    assert res.cloned == 1
