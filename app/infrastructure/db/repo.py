from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.application.ports import ClaimsRepoPort
from .models import ClaimProcessing

class ClaimsRepo(ClaimsRepoPort):
    def __init__(self, sf: async_sessionmaker[AsyncSession], instance_name: str = "default"):
        self._sf = sf
        self._instance_name = instance_name

    async def was_processed(self, claim_id: str) -> bool:
        async with self._sf() as s:
            row = await s.get(ClaimProcessing, claim_id)
            return bool(row and row.processed)

    async def mark_done(self, claim_id: str, action: str, processed_at: datetime) -> None:
        async with self._sf() as s:
            row = await s.get(ClaimProcessing, claim_id) or ClaimProcessing(claim_id=claim_id)
            row.processed = True
            row.action = action
            row.processed_at = processed_at
            row.error = None
            s.add(row)
            await s.commit()

    async def mark_failed(self, claim_id: str, error: str, processed_at: datetime) -> None:
        async with self._sf() as s:
            row = await s.get(ClaimProcessing, claim_id) or ClaimProcessing(claim_id=claim_id)
            row.processed = False
            row.action = row.action
            row.processed_at = processed_at
            row.error = error
            s.add(row)
            await s.commit()
