from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from .models import ProductCache
from sqlalchemy import select
from datetime import datetime

class ProductCacheRepo:
    def __init__(self, sf: async_sessionmaker[AsyncSession], instance_name: str = "default"):
        self._sf = sf
        self._instance_name = instance_name

    async def get(self, nm_id: int):
        async with self._sf() as s:
            q = await s.execute(
                select(ProductCache).where(
                    ProductCache.nm_id == nm_id,
                    ProductCache.instance_name == self._instance_name,
                )
            )
            return q.scalar_one_or_none()

    async def set(self, nm_id: int, title: str | None, color: str | None):
        async with self._sf() as s:
            q = await s.execute(
                select(ProductCache).where(
                    ProductCache.nm_id == nm_id,
                    ProductCache.instance_name == self._instance_name,
                )
            )
            row = q.scalar_one_or_none()

            if not row:
                row = ProductCache(
                    nm_id=nm_id,
                    instance_name=self._instance_name,
                    title=title,
                    color=color,
                    updated_at=datetime.utcnow(),
                )
            else:
                row.title = title
                row.color = color
                row.updated_at = datetime.utcnow()

            s.add(row)
            await s.commit()
