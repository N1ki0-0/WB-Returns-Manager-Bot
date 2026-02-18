import asyncio
import os
from zoneinfo import ZoneInfo
from app.infrastructure.db.repo_product_cache import ProductCacheRepo
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
from app.infrastructure.db.repo_orders import OrderRepo
from app.infrastructure.wb.marketplace_client import WbMarketplaceClient
from app.infrastructure.wb.content_client import WbContentClient
from app.infrastructure.db.repo_daily_supply import DailySupplyRepo
from app.application.usecases_daily_supply import CreateDailySupplyUseCase
import logging
logging.basicConfig(level=logging.INFO)
async def main():
    settings = load_settings()
    sf, engine = make_session_factory(settings.db_url)
    await init_db(engine)

    scheduler = make_scheduler(settings.daily_supply_tz)
    scheduler.start()

    tasks = []

    for acct in settings.accounts:
        instance_name = acct.name

        # --- Telegram ---
        bot = Bot(token=acct.telegram_token)
        dp = Dispatcher()

        notifier = TelegramNotifier(bot=bot, admin_ids=acct.admin_ids)

        # --- WB clients ---
        wb_client = WbReturnsClient(acct.wb_token)
        wb_adapter = WbReturnsAdapter(wb_client)

        mp_client = WbMarketplaceClient(acct.wb_token)
        content_client = WbContentClient(acct.wb_token)

        # --- repos ---
        claims_repo = ClaimsRepo(sf, instance_name=instance_name)
        order_repo = OrderRepo(sf, instance_name=instance_name)
        product_cache_repo = ProductCacheRepo(sf, instance_name=instance_name)
        daily_repo = DailySupplyRepo(sf, instance_name=instance_name)

        # --- rules ---
        rule = AutoRejectRule(delay_days=settings.delay_days)

        # --- RETURNS USECASE ---
        usecase = ProcessClaimsUseCase(
            wb=wb_adapter,
            repo=claims_repo,
            rule=rule,
            default_comment=settings.default_comment,
            enabled=settings.enabled,
            notifier=notifier,
        )

        # --- DAILY SUPPLY USECASE ---
        daily_supply_usecase = CreateDailySupplyUseCase(
            marketplace_client=mp_client,
            content_client=content_client,
            daily_repo=daily_repo,
            notifier=notifier,
            tz=settings.daily_supply_tz,
            enabled=True,
            product_cache_repo=product_cache_repo,
        )

        # --- handlers ---
        setup_handlers(
            dp,
            usecase=usecase,
            daily_supply_usecase=daily_supply_usecase,
            instance_name=instance_name,
        )

        # --- scheduler ---
        register_jobs(
            scheduler,
            returns_usecase=usecase,
            returns_interval_minutes=settings.interval_minutes,
            daily_supply_usecase=daily_supply_usecase,
            daily_hour=settings.daily_supply_hour,
            daily_minute=settings.daily_supply_minute,
            timezone=settings.timezone,
            instance_name=instance_name,
        )

        # --- polling ---
        task = asyncio.create_task(dp.start_polling(bot))
        tasks.append((instance_name, task, bot, mp_client, content_client))

    try:
        await asyncio.gather(*(t for _, t, *_ in tasks))
    finally:
        for instance, task, bot, mp_client, content_client in tasks:
            await bot.session.close()
            await mp_client.close()
            await content_client.close()

        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
