from datetime import datetime
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select, desc
from .models import DailySupplyRun

class DailySupplyRepo:
    def __init__(self, sf: async_sessionmaker[AsyncSession], instance_name: str = "default"):
        self._sf = sf
        self._instance_name = instance_name

    async def already_ran(self, day_key: str) -> bool:
        async with self._sf() as s:
            stmt = select(DailySupplyRun).where(
                DailySupplyRun.day_key == day_key,
                DailySupplyRun.instance_name == self._instance_name,
            )
            res = await s.execute(stmt)
            row = res.scalar_one_or_none()
            return row is not None and row.supply_id is not None and row.error is None

    async def mark_ok(self, day_key: str, supply_id: str, created_at: datetime, order_count: int, report_text: str) -> None:
        async with self._sf() as s:
            stmt = select(DailySupplyRun).where(
                DailySupplyRun.day_key == day_key,
                DailySupplyRun.instance_name == self._instance_name,
            )
            res = await s.execute(stmt)
            row = res.scalar_one_or_none()
            if not row:
                row = DailySupplyRun(day_key=day_key, instance_name=self._instance_name)
            row.supply_id = supply_id
            row.created_at = created_at
            row.order_count = order_count
            row.error = None
            row.report_text = report_text
            s.add(row)
            await s.commit()

    async def mark_failed(self, day_key: str, created_at: datetime, error: str) -> None:
        async with self._sf() as s:
            stmt = select(DailySupplyRun).where(
                DailySupplyRun.day_key == day_key,
                DailySupplyRun.instance_name == self._instance_name,
            )
            res = await s.execute(stmt)
            row = res.scalar_one_or_none()
            if not row:
                row = DailySupplyRun(day_key=day_key, instance_name=self._instance_name)
            row.created_at = created_at
            row.error = error
            s.add(row)
            await s.commit()

    async def get_last_report(self) -> DailySupplyRun | None:
        async with self._sf() as s:
            stmt = select(DailySupplyRun).where(
                DailySupplyRun.instance_name == self._instance_name
            ).order_by(desc(DailySupplyRun.created_at)).limit(1)
            res = await s.execute(stmt)
            return res.scalar_one_or_none()