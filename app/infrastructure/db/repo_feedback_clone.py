from datetime import datetime
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from .models import FeedbackClone

class FeedbackCloneRepo:
    def __init__(self, sf: async_sessionmaker[AsyncSession]):
        self._sf = sf

    async def was_processed(self, feedback_id: str) -> bool:
        async with self._sf() as s:
            return await s.get(FeedbackClone, feedback_id) is not None

    async def mark_cloned(self, feedback_id: str, nm_id: int, new_nm_id: str, created_at: datetime) -> None:
        async with self._sf() as s:
            row = FeedbackClone(
                feedback_id=feedback_id,
                nm_id=nm_id,
                created_at=created_at,
                status="CLONED",
                new_nm_id=new_nm_id,
                error=None,
            )
            s.add(row)
            await s.commit()

    async def mark_failed(self, feedback_id: str, nm_id: int, created_at: datetime, error: str) -> None:
        async with self._sf() as s:
            row = FeedbackClone(
                feedback_id=feedback_id,
                nm_id=nm_id,
                created_at=created_at,
                status="FAILED",
                new_nm_id=None,
                error=error,
            )
            s.add(row)
            await s.commit()
