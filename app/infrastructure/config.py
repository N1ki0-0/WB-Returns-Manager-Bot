# app/infrastructure/config.py
import os
import json
from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class AccountConfig:
    name: str
    telegram_token: str
    wb_token: str
    admin_ids: List[int]

@dataclass
class Settings:
    accounts: List[AccountConfig]
    db_url: str
    daily_supply_tz: str
    timezone: str
    interval_minutes: int
    delay_days: int
    daily_supply_hour: int
    daily_supply_minute: int
    wb_content_max_parallel: int
    default_reject_comment: str

def _parse_accounts(raw: Optional[str]) -> List[AccountConfig]:
    if not raw:
        return []
    raw = raw.strip()
    # Если передан путь к файлу - попробуем загрузить
    if os.path.exists(raw):
        with open(raw, "r", encoding="utf-8") as f:
            arr = json.load(f)
    else:
        try:
            arr = json.loads(raw)
        except Exception as e:
            raise RuntimeError("ACCOUNTS must be JSON string or path to JSON file: " + str(e))

    accounts: List[AccountConfig] = []
    for a in arr:
        name = a.get("name") or a.get("instance") or a.get("instance_name") or a.get("id")
        if not name:
            raise RuntimeError("Each account in ACCOUNTS must have a 'name' field")
        admin_ids = a.get("admin_ids") or a.get("adminIds") or []
        # ensure ints
        admin_ids = [int(x) for x in admin_ids if str(x).strip() != ""]
        accounts.append(AccountConfig(
            name=str(name),
            telegram_token=str(a["telegram_token"]),
            wb_token=str(a["wb_token"]),
            admin_ids=admin_ids
        ))
    return accounts

def load_settings(env_file: str = ".env") -> Settings:
    # If .env file exists, load it into env (simple key=value)
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k not in os.environ:
                        os.environ[k] = v
        except Exception:
            # не критично — продолжим читать из окружения
            pass

    accounts_raw = os.getenv("ACCOUNTS")
    accounts = _parse_accounts(accounts_raw)

    def gint(name: str, default: int) -> int:
        v = os.getenv(name)
        return int(v) if v and v.strip() != "" else default

    def gstr(name: str, default: str) -> str:
        v = os.getenv(name)
        return v if v and v.strip() != "" else default

    s = Settings(
        accounts=accounts,
        db_url=gstr("DB_URL", "sqlite+aiosqlite:///./data/data.db"),
        daily_supply_tz=gstr("DAILY_SUPPLY_TZ", "Europe/Moscow"),
        timezone=gstr("TIMEZONE", gstr("DAILY_SUPPLY_TZ", "Europe/Moscow")),
        interval_minutes=gint("INTERVAL_MINUTES", 1),
        delay_days=gint("DELAY_DAYS", 3),
        daily_supply_hour=gint("DAILY_SUPPLY_HOUR", 10),
        daily_supply_minute=gint("DAILY_SUPPLY_MINUTE", 0),
        wb_content_max_parallel=gint("WB_CONTENT_MAX_PARALLEL", 3),
        default_reject_comment=gstr("DEFAULT_REJECT_COMMENT", "Пришлось отклонить заявку — нужно чуть больше информации."),
    )
    return s
