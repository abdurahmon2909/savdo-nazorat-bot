from sqlalchemy import BigInteger, ForeignKey, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    paid_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    status: Mapped[str] = mapped_column(String(32), default="pending")

    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")