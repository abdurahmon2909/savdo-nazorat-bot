from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.order_item import OrderItem


async def create_order(session: AsyncSession, customer_id: int, created_by: int, items: list):
    total = sum(i["quantity"] * i["price"] for i in items)

    order = Order(
        customer_id=customer_id,
        created_by=created_by,
        total_amount=total,
        paid_amount=0,
        status="pending",
    )

    session.add(order)
    await session.flush()

    for i in items:
        item = OrderItem(
            order_id=order.id,
            product_id=i["product_id"],
            quantity=i["quantity"],
            price=i["price"],
        )
        session.add(item)

    await session.commit()
    await session.refresh(order)

    return order