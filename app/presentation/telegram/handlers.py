from aiogram import Router, F
from aiogram.types import Message
from app.application.usecases import ProcessClaimsUseCase

router = Router()

def _is_admin(message: Message, admin_ids: set[int]) -> bool:
    return message.from_user and message.from_user.id in admin_ids

def setup_handlers(router: Router, returns_usecase, admin_ids: set[int], daily_supply_usecase=None, daily_repo=None):
    @router.message(F.text == "/ping")
    async def ping(m: Message):
        if not _is_admin(m, admin_ids):
            return
        await m.answer("ok")

    @router.message(F.text == "/run")
    async def run(m: Message):
        if not _is_admin(m, admin_ids):
            return
        res = await returns_usecase.run()
        await m.answer(
            f"Готово.\n"
            f"Проверено: {res.checked}\n"
            f"Обработано: {res.processed}\n"
            f"Пропущено (уже было): {res.skipped_already_done}\n"
            f"Ошибок: {res.errors}"
        )

    @router.message(F.text == "/supply_run")
    async def supply_run(m: Message):
        if not _is_admin(m, admin_ids) or daily_supply_usecase is None:
            return
        res = await daily_supply_usecase.run()
        await m.answer("Supply job выполнен.\n" + "\n".join(res.lines))

    @router.message(F.text == "/last_supply")
    async def last_supply(m: Message):
        if not _is_admin(m, admin_ids) or daily_repo is None:
            return

        row = await daily_repo.get_last_report()
        if row is None or not row.report_text:
            await m.answer("Нет данных о поставках (ещё не создавались или не сохранён отчёт).")
            return

        # Telegram лимит на сообщение ~4096 символов
        text = row.report_text
        if len(text) <= 3800:
            await m.answer(text)
        else:
            await m.answer(text[:3800] + "\n...\n(сообщение обрезано)")
