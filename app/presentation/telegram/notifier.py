from aiogram import Bot
import logging


class TelegramNotifier:
    def __init__(self, bot: Bot, admin_ids: list[int]):
        self._bot = bot
        self._admin_ids = admin_ids

    async def notify_admins(self, text: str):
        for admin in self._admin_ids:
            try:
                await self._bot.send_message(admin, text)
            except Exception as e:
                # логируем, но не падаем
                logging.getLogger("notifier").exception("notify_admins failed: %s", e)