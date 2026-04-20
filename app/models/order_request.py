from sqlalchemy import BigInteger, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class OrderRequest(TimestampMixin, Base):
    __tablename__ = "order_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    customer_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    payment_type: Mapped[str] = mapped_column(String(32), default="nasiya", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)