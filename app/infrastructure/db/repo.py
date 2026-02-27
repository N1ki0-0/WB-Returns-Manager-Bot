from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.application.ports import ClaimsRepoPort
from .models import ClaimProcessing

# app/infrastructure/db/repo_claims.py (или где у тебя ClaimsRepo)
from sqlalchemy import select, update
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

class ClaimsRepo(ClaimsRepoPort):
    def __init__(self, sf: async_sessionmaker[AsyncSession], instance_name: str = "default"):
        self._sf = sf
        self._instance_name = instance_name

    async def was_processed(self, claim_id: str) -> bool:
        async with self._sf() as s:
            stmt = select(ClaimProcessing).where(
                ClaimProcessing.claim_id == claim_id,
                ClaimProcessing.instance_name == self._instance_name,
            )
            res = await s.execute(stmt)
            row = res.scalar_one_or_none()
            return bool(row and row.processed)

    async def mark_done(self, claim_id: str, action: str, processed_at: datetime) -> None:
        async with self._sf() as s:
            stmt = select(ClaimProcessing).where(
                ClaimProcessing.claim_id == claim_id,
                ClaimProcessing.instance_name == self._instance_name,
            )
            res = await s.execute(stmt)
            row = res.scalar_one_or_none()
            if not row:
                row = ClaimProcessing(claim_id=claim_id, instance_name=self._instance_name)
            row.processed = True
            row.action = action
            row.processed_at = processed_at
            row.error = None
            s.add(row)
            await s.commit()

    async def mark_failed(self, claim_id: str, error: str, processed_at: datetime) -> None:
        async with self._sf() as s:
            stmt = select(ClaimProcessing).where(
                ClaimProcessing.claim_id == claim_id,
                ClaimProcessing.instance_name == self._instance_name,
            )
            res = await s.execute(stmt)
            row = res.scalar_one_or_none()
            if not row:
                row = ClaimProcessing(claim_id=claim_id, instance_name=self._instance_name)
            row.processed = False
            # row.action оставляем как было (не перезаписываем)
            row.processed_at = processed_at
            row.error = error
            s.add(row)
            await s.commit()

