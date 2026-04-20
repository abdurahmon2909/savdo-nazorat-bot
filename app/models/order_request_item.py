from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OrderRequestItem(Base):
    __tablename__ = "order_request_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_request_id: Mapped[int] = mapped_column(ForeignKey("order_requests.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_unit: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)