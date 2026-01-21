from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Boolean, Text
from sqlalchemy import String, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
class Base(DeclarativeBase):
    pass

class ClaimProcessing(Base):
    __tablename__ = "claim_processing"
    claim_id: Mapped[str] = mapped_column(String, primary_key=True)
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

class FeedbackClone(Base):
    __tablename__ = "feedback_clone"
    feedback_id: Mapped[str] = mapped_column(String, primary_key=True)
    nm_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)  # CLONED / FAILED
    new_nm_id: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)