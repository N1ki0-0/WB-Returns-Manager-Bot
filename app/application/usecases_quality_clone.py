from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from app.domain.vendorcode import next_vendor_code

@dataclass
class CloneRunResult:
    checked: int
    triggered: int
    cloned: int
    errors: int

class CloneOnOneStarFeedbackUseCase:
    def __init__(self, feedbacks, cards_reader, cards_writer, clone_repo, notifier, enabled: bool):
        self._feedbacks = feedbacks
        self._cards_reader = cards_reader
        self._cards_writer = cards_writer
        self._clone_repo = clone_repo
        self._notifier = notifier
        self._enabled = enabled

    async def run(self) -> CloneRunResult:
        if not self._enabled:
            return CloneRunResult(0, 0, 0, 0)

        now = datetime.now(timezone.utc)

        checked = triggered = cloned = errors = 0

        # 1) получаем отзывы (простая версия, без lookback-фильтра — можно добавить по дате, если поле есть)
        data = await self._feedbacks.list_feedbacks(is_answered=False, take=500, skip=0)
        feedbacks = data.get("feedbacks", []) or data.get("data", []) or []

        for fb in feedbacks:
            checked += 1
            rating = fb.get("productValuation") or fb.get("valuation") or fb.get("rating")
            if int(rating or 0) != 1:
                continue

            feedback_id = str(fb.get("id") or fb.get("feedbackId") or fb.get("rid"))
            nm_id = int(((fb.get("productDetails") or {}).get("nmId")) or fb.get("nmId") or 0)
            if not feedback_id or nm_id == 0:
                continue

            if await self._clone_repo.was_processed(feedback_id):
                continue

            triggered += 1

            try:
                # 2) читаем исходную карточку
                card = await self._cards_reader.get_card_by_nm_id(nm_id)
                vendor_code = card["vendorCode"]
                subject_id = card["subjectID"]
                characteristics = card.get("characteristics", [])
                title = card.get("title")
                description = card.get("description")

                # 3) найдём существующие vendorCode, чтобы выбрать следующий (1),(2)...
                existing = await self._cards_reader.find_vendor_codes_like(vendor_code)
                new_vendor_code = next_vendor_code(vendor_code, existing)

                # 4) создаём новую карточку
                new_payload = {
                    "subjectID": subject_id,
                    "vendorCode": new_vendor_code,
                    "title": title,
                    "description": description,
                    "characteristics": characteristics,
                    # медиа и цены подключим отдельными шагами/портами
                }
                new_nm_id = await self._cards_writer.create_card(new_payload)

                await self._clone_repo.mark_cloned(feedback_id, nm_id, str(new_nm_id), now)
                cloned += 1

                await self._notifier.notify_admins(
                    "WB Quality Clone: создан клон карточки из-за 1⭐ отзыва\n"
                    f"- feedback_id: {feedback_id}\n"
                    f"- nmId: {nm_id}\n"
                    f"- new_vendorCode: {new_vendor_code}\n"
                    f"- new_nmId: {new_nm_id}"
                )

            except Exception as e:
                errors += 1
                err = f"{type(e).__name__}: {e}"
                await self._clone_repo.mark_failed(feedback_id, nm_id, now, err)
                await self._notifier.notify_admins(
                    "WB Quality Clone: ошибка при клонировании\n"
                    f"- feedback_id: {feedback_id}\n"
                    f"- nmId: {nm_id}\n"
                    f"- error: {err}"
                )

        return CloneRunResult(checked, triggered, cloned, errors)
