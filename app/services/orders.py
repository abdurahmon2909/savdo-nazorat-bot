from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.order_item import OrderItem
from app.utils.timezone import now_utc


async def create_order(
    session: AsyncSession,
    customer_id: int,
    created_by: int,
    items: list[dict],
    payment_type: str,
) -> Order:
    total = sum(Decimal(str(i["quantity"])) * Decimal(str(i["price"])) for i in items)

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

    for i in items:
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=i["product_id"],
                quantity=Decimal(str(i["quantity"])),
                price=Decimal(str(i["price"])),
            )
        )

    await session.commit()
    await session.refresh(order)
    return order


async def get_order_by_id(session: AsyncSession, order_id: int) -> Order | None:
    result = await session.execute(select(Order).where(Order.id == order_id))
    return result.scalar_one_or_none()


async def list_customer_orders(session: AsyncSession, customer_id: int, limit: int = 20):
    result = await session.execute(
        select(Order)
        .where(Order.customer_id == customer_id)
        .order_by(desc(Order.id))
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_customer_open_orders(session: AsyncSession, customer_id: int, limit: int = 20):
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


async def list_recent_orders(session: AsyncSession, limit: int = 50):
    result = await session.execute(select(Order).order_by(desc(Order.id)).limit(limit))
    return list(result.scalars().all())


async def list_debtor_orders(session: AsyncSession, limit: int = 50):
    result = await session.execute(
        select(Order)
        .where(Order.status.in_(["unpaid", "partial"]))
        .order_by(desc(Order.id))
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_overdue_orders(session: AsyncSession, days: int = 7, limit: int = 50):
    border = now_utc() - timedelta(days=days)
    result = await session.execute(
        select(Order)
        .where(
            Order.status.in_(["unpaid", "partial"]),
            Order.created_at <= border,
        )
        .order_by(Order.created_at)
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_order_payment_status(session: AsyncSession, order: Order, new_paid: Decimal):
    total = Decimal(str(order.total_amount))

    if new_paid >= total:
        order.paid_amount = total
        order.status = "paid"
    elif new_paid > 0:
        order.paid_amount = new_paid
        order.status = "partial"
    else:
        order.paid_amount = Decimal("0")
        order.status = "unpaid"

    await session.commit()
    await session.refresh(order)
    return order