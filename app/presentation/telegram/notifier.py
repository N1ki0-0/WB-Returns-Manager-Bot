from aiogram import Bot

class TelegramNotifier:
    def __init__(self, bot: Bot, admin_ids: set[int]):
        self._bot = bot
        self._admin_ids = admin_ids

    async def notify_admins(self, text: str) -> None:
        # Отправляем всем админам; ошибки отправки одному админу не должны ломать весь процесс
        for admin_id in self._admin_ids:
            try:
                await self._bot.send_message(chat_id=admin_id, text=text)
            except Exception:
                # Здесь можно логировать, но не бросаем исключение наружу
                pass
