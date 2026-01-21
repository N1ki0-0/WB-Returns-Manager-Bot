from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    telegram_token: str
    wb_token: str
    admin_ids: set[int]
    db_url: str
    timezone: str
    daily_supply_enabled: bool
    daily_supply_hour: int
    daily_supply_minute: int

    auto_enabled: bool
    delay_days: int
    interval_minutes: int
    default_reject_comment: str

def _bool(v: str) -> bool:
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}

def load_settings() -> Settings:
    admin_ids = set()
    raw_admins = os.getenv("ADMIN_TELEGRAM_IDS", "").strip()
    if raw_admins:
        admin_ids = {int(x.strip()) for x in raw_admins.split(",") if x.strip()}

    return Settings(
        telegram_token=os.environ["TELEGRAM_BOT_TOKEN"],
        wb_token=os.environ["WB_API_TOKEN"],
        admin_ids=admin_ids,
        db_url=os.getenv("DB_URL", "sqlite+aiosqlite:///./data.db"),
        auto_enabled=_bool(os.getenv("AUTO_ACTION_ENABLED", "true")),
        delay_days=int(os.getenv("AUTO_ACTION_DELAY_DAYS", "3")),
        interval_minutes=int(os.getenv("SCHED_INTERVAL_MINUTES", "60")),
        default_reject_comment=os.getenv(
            "DEFAULT_REJECT_COMMENT",
            "Заявка отклонена автоматически."
        ).replace("\\n", "\n"),
        timezone=os.getenv("TIMEZONE", "Europe/Moscow"),
        daily_supply_enabled=_bool(os.getenv("DAILY_SUPPLY_ENABLED", "true")),
        daily_supply_hour=int(os.getenv("DAILY_SUPPLY_HOUR", "9")),
        daily_supply_minute=int(os.getenv("DAILY_SUPPLY_MINUTE", "30")),
    )
