from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.order_item import OrderItem


async def create_order(
    session: AsyncSession,
    customer_id: int,
    created_by: int,
    items: list[dict],
    payment_type: str,
) -> Order:
    total = sum(Decimal(str(item["quantity"])) * Decimal(str(item["price"])) for item in items)

    paid_amount = total if payment_type == "naqd" else Decimal("0")
    status = "paid" if payment_type == "naqd" else "unpaid"

    order = Order(
        customer_id=customer_id,
        created_by=created_by,
        total_amount=total,
        paid_amount=paid_amount,
        status=status,
    )

    session.add(order)
    await session.flush()

    for item_data in items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item_data["product_id"],
            quantity=Decimal(str(item_data["quantity"])),
            price=Decimal(str(item_data["price"])),
        )
        session.add(order_item)

    await session.commit()
    await session.refresh(order)
    return order