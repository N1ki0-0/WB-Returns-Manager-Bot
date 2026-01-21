from apscheduler.schedulers.asyncio import AsyncIOScheduler
from zoneinfo import ZoneInfo

def make_scheduler(timezone: str) -> AsyncIOScheduler:
    return AsyncIOScheduler(timezone=ZoneInfo(timezone))
