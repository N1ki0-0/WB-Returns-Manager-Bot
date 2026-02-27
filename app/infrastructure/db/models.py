from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, Column, Text, Boolean
from datetime import datetime
class Base(DeclarativeBase):
    pass

class ClaimProcessing(Base):
    __tablename__ = "claim_processing"
    claim_id: Mapped[str] = mapped_column(String, primary_key=True)
    instance_name = Column(String, nullable=False, index=True, default="default")
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    action: Mapped[str | None] = mapped_column(String, nullable=True)
    processed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

class DailySupplyRun(Base):
    __tablename__ = "daily_supply_run"
    day_key: Mapped[str] = mapped_column(String, primary_key=True)  # "YYYY-MM-DD"
    supply_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order_count: Mapped[int] = mapped_column(default=0, nullable=False)
    report_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    instance_name = Column(String, index=True, nullable=False, default="default")

class FeedbackClone(Base):
    __tablename__ = "feedback_clone"
    feedback_id: Mapped[str] = mapped_column(String, primary_key=True)
    nm_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)  # CLONED / FAILED
    new_nm_id: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, index=True, nullable=False)  # id из WB
    nm_id = Column(Integer, index=True, nullable=False)
    quantity = Column(Integer, default=1)
    offer_name = Column(String, nullable=True)
    vendor_code = Column(String, nullable=True)
    supply_id = Column(String, index=True, nullable=True)  # wb supply id when assigned
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    instance_name = Column(String, index=True, nullable=False, default="default")

class ProductCache(Base):
    __tablename__ = "product_cache"
    nm_id = Column(Integer, primary_key=True)
    title = Column(String, nullable=True)
    color = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    instance_name = Column(String, index=True, nullable=False, primary_key = True,default="default")