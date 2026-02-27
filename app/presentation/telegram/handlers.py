from aiogram import Router, F, Dispatcher
from aiogram.types import Message


def _is_admin(message: Message, admin_ids: set[int]) -> bool:
    return message.from_user and message.from_user.id in admin_ids


def setup_handlers(dp: Dispatcher, accounts_registry: dict):
    """
    accounts_registry = {
        "acc1": {
            "returns": usecase,
            "daily": daily_usecase,
            "repo": repo,
            "admins": set(...)
        }
    }
    """

    router = Router()

    # --- helper ---
    def _get_account(name: str):
        return accounts_registry.get(name)

    # --- ping ---
    @router.message(F.text == "/ping")
    async def ping(m: Message):
        await m.answer("ok")

    # --- list accounts ---
    @router.message(F.text == "/accounts")
    async def accounts(m: Message):
        names = "\n".join(accounts_registry.keys())
        await m.answer(f"Аккаунты:\n{names}")

    # --- run returns ---
    @router.message(F.text.startswith("/run"))
    async def run(m: Message):
        parts = m.text.split()

        if len(parts) < 2:
            await m.answer("Используй: /run ACCOUNT")
            return

        name = parts[1]
        acc = _get_account(name)

        if not acc:
            await m.answer("Аккаунт не найден")
            return

        if not _is_admin(m, acc["admins"]):
            return

        res = await acc["returns"].run()

        await m.answer(
            f"{name}:\n"
            f"Проверено: {res.checked}\n"
            f"Обработано: {res.processed}\n"
            f"Ошибок: {res.errors}"
        )

    # --- supply run ---
    @router.message(F.text.startswith("/supply_run"))
    async def supply_run(m: Message):
        parts = m.text.split()

        if len(parts) < 2:
            await m.answer("Используй: /supply_run ACCOUNT")
            return

        name = parts[1]
        acc = _get_account(name)

        if not acc or "daily" not in acc:
            await m.answer("Аккаунт не найден")
            return

        if not _is_admin(m, acc["admins"]):
            return

        res = await acc["daily"].run()

        await m.answer(
            f"{name} supply:\n" + "\n".join(res.lines)
        )

    # --- last supply ---
    @router.message(F.text.startswith("/last_supply"))
    async def last_supply(m: Message):
        parts = m.text.split()

        if len(parts) < 2:
            await m.answer("Используй: /last_supply ACCOUNT")
            return

        name = parts[1]
        acc = _get_account(name)

        if not acc or "repo" not in acc:
            await m.answer("Аккаунт не найден")
            return

        if not _is_admin(m, acc["admins"]):
            return

        row = await acc["repo"].get_last_report()

        if not row or not row.report_text:
            await m.answer("Нет данных")
            return

        text = row.report_text

        if len(text) <= 3800:
            await m.answer(text)
        else:
            await m.answer(text[:3800] + "\n...\n(обрезано)")

    dp.include_router(router)