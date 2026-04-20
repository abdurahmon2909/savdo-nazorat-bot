from decimal import Decimal

from sqlalchemy import desc, select
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


async def get_order_by_id(session: AsyncSession, order_id: int) -> Order | None:
    result = await session.execute(
        select(Order).where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def list_customer_open_orders(
    session: AsyncSession,
    customer_id: int,
    limit: int = 20,
) -> list[Order]:
    result = await session.execute(
        select(Order)
        .where(
            Order.customer_id == customer_id,
            Order.status.in_(["unpaid", "partial"]),
        )
        .order_by(desc(Order.id))
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_debtor_orders(
    session: AsyncSession,
    limit: int = 50,
) -> list[Order]:
    result = await session.execute(
        select(Order)
        .where(Order.status.in_(["unpaid", "partial"]))
        .order_by(desc(Order.id))
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_order_payment_status(
    session: AsyncSession,
    order: Order,
    new_paid_amount: Decimal,
) -> Order:
    total_amount = Decimal(str(order.total_amount))
    paid_amount = Decimal(str(new_paid_amount))

    if paid_amount >= total_amount:
        order.paid_amount = total_amount
        order.status = "paid"
    elif paid_amount > 0:
        order.paid_amount = paid_amount
        order.status = "partial"
    else:
        order.paid_amount = Decimal("0")
        order.status = "unpaid"

    await session.commit()
    await session.refresh(order)
    return order