import asyncio

from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher
from app.infrastructure.config import load_settings
from app.infrastructure.wb.client import WbReturnsClient
from app.infrastructure.wb.mapper import WbReturnsAdapter
from app.infrastructure.db.session import make_session_factory, init_db
from app.infrastructure.db.repo import ClaimsRepo
from app.domain.rules import AutoRejectRule
from app.application.usecases import ProcessClaimsUseCase
from app.infrastructure.scheduler.scheduler import make_scheduler
from app.infrastructure.scheduler.jobs import register_jobs
from .handlers import router, setup_handlers
from app.presentation.telegram.notifier import TelegramNotifier
from app.infrastructure.wb.marketplace_client import WbMarketplaceClient
from app.infrastructure.wb.content_client import WbContentClient
from app.infrastructure.db.repo_daily_supply import DailySupplyRepo
from app.application.usecases_daily_supply import CreateDailySupplyUseCase
import logging
logging.basicConfig(level=logging.INFO)

async def main():
    settings = load_settings()

    # Telegram
    bot = Bot(token=settings.telegram_token)
    dp = Dispatcher()

    # DB
    sf, engine = make_session_factory(settings.db_url)
    await init_db(engine)
    repo = ClaimsRepo(sf)

    # WB
    wb_client = WbReturnsClient(settings.wb_token)
    wb = WbReturnsAdapter(wb_client)

    # Notifier
    notifier = TelegramNotifier(bot=bot, admin_ids=settings.admin_ids)

    mp_client = WbMarketplaceClient(settings.wb_token)
    content_client = WbContentClient(settings.wb_token)

    daily_repo = DailySupplyRepo(sf)

    # Use case
    rule = AutoRejectRule(delay_days=settings.delay_days)
    usecase = ProcessClaimsUseCase(
        wb=wb,
        repo=repo,
        rule=rule,
        default_comment=settings.default_reject_comment,
        enabled=settings.auto_enabled,
        notifier=notifier,
    )

    daily_supply_usecase = CreateDailySupplyUseCase(
        marketplace_client=mp_client,
        content_client=content_client,
        daily_repo=daily_repo,
        notifier=notifier,
        tz=getattr(settings, "timezone", "Europe/Moscow"),  # см. settings ниже
        enabled=getattr(settings, "daily_supply_enabled", True),
    )

    # Scheduler
    sched = make_scheduler(settings.timezone)
    register_jobs(
        sched,
        returns_usecase=usecase,
        returns_interval_minutes=settings.interval_minutes,
        daily_supply_usecase=daily_supply_usecase,
        daily_hour=getattr(settings, "daily_supply_hour", 9),
        daily_minute=getattr(settings, "daily_supply_minute", 30),
        timezone=getattr(settings, "timezone", "Europe/Moscow"),
    )
    sched.start()


    setup_handlers(router, usecase, settings.admin_ids, daily_supply_usecase=daily_supply_usecase, daily_repo=daily_repo)
    dp.include_router(router)

    try:
        await dp.start_polling(bot)
    finally:
        await wb_client.close()
        await bot.session.close()
        await engine.dispose()
        await mp_client.close()
        await content_client.close()

if __name__ == "__main__":
    asyncio.run(main())
