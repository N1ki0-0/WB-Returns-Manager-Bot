from apscheduler.triggers.cron import CronTrigger

def register_jobs(
    sched,
    returns_usecase,
    returns_interval_minutes: int,
    daily_supply_usecase=None,
    daily_hour: int = 9,
    daily_minute: int = 55,
    timezone: str = "Europe/Amsterdam",
):
    # Возвраты — interval
    sched.add_job(
        func=returns_usecase.run,
        trigger="interval",
        minutes=returns_interval_minutes,
        id="process_claims",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Ежедневная поставка — cron
    if daily_supply_usecase is not None:
        sched.add_job(
            func=daily_supply_usecase.run,
            trigger=CronTrigger(hour=daily_hour, minute=daily_minute, timezone=timezone),
            id="daily_supply",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
