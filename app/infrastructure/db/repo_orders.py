from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select, update
from .models import Order
from datetime import datetime

class OrderRepo:
    def __init__(self, sf: async_sessionmaker[AsyncSession], instance_name: str = "default"):
        self._sf = sf
        self._instance_name = instance_name

    async def upsert_order(self, order_wb: dict):
        """
        order_wb: dict with keys: id, nmId, quantity, offerName, vendorCode
        """
        async with self._sf() as s:
            # try find by order_id
            q = await s.execute(select(Order).where(Order.order_id == int(order_wb["id"]),
                                                    Order.instance_name == self._instance_name))
            row = q.scalars().first()
            if row:
                row.nm_id = int(order_wb.get("nmId", row.nm_id))
                row.quantity = int(order_wb.get("quantity", row.quantity))
                row.offer_name = order_wb.get("offerName") or row.offer_name
                row.vendor_code = order_wb.get("vendorCode") or row.vendor_code
                row.updated_at = datetime.utcnow()
            else:
                row = Order(
                    order_id=int(order_wb["id"]),
                    nm_id=int(order_wb.get("nmId", 0)),
                    quantity=int(order_wb.get("quantity", 1)),
                    offer_name=order_wb.get("offerName"),
                    vendor_code=order_wb.get("vendorCode"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    instance_name=self._instance_name
                )
                s.add(row)
            await s.commit()
            return row

    async def get_unassigned_orders(self):
        async with self._sf() as s:
            q = await s.execute(select(Order).where(Order.supply_id == None, Order.instance_name == self._instance_name))
            return q.scalars().all()

    async def mark_orders_assigned(self, order_ids: list[int], supply_id: str):
        async with self._sf() as s:
            await s.execute(update(Order).where(Order.order_id.in_(order_ids), Order.instance_name == self._instance_name).values(supply_id=supply_id, updated_at=datetime.utcnow()))
            await s.commit()

    async def get_orders_for_supply(self, supply_id: str):
        async with self._sf() as s:
            q = await s.execute(select(Order).where(Order.supply_id == supply_id, Order.instance_name == self._instance_name))
            return q.scalars().all()
