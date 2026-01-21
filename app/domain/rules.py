from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

@dataclass(frozen=True)
class AutoRejectRule:
    delay_days: int

    def is_due(self, created_at: datetime, now: datetime) -> bool:
        return now >= created_at + timedelta(days=self.delay_days)

def parse_wb_dt(dt_str: str) -> datetime:
    # WB отдаёт dt в формате "YYYY-MM-DDTHH:MM:SS.ffffff" (без timezone). :contentReference[oaicite:11]{index=11}
    # Будем считать это UTC (или локаль WB). При желании — вынести в настройку.
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
