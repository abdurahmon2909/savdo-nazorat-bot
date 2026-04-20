from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.models.order import Order
from app.services.orders import update_order_payment_status


async def create_payment(
    session: AsyncSession,
    order: Order,
    amount: Decimal,
    payment_method: str = "naqd",
) -> Payment:
    payment = Payment(
        order_id=order.id,
        amount=amount,
        payment_method=payment_method,
    )
    session.add(payment)
    await session.flush()

    current_paid = Decimal(str(order.paid_amount))
    new_paid = current_paid + amount

    await update_order_payment_status(session, order, new_paid)
    await session.refresh(payment)
    return payment