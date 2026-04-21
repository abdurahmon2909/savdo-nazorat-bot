from decimal import Decimal
from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.customers import get_customer_by_id
from app.services.orders import list_debtor_orders
from app.utils.helpers import is_admin, format_number
from app.utils.statuses import uzbek_order_status

router = Router()


@router.message(F.text == "📉 Qarzdorlar")
async def show_debtors(message: Message, session: AsyncSession) -> None:
    if not is_admin(message):
        return
    orders = await list_debtor_orders(session, limit=50)
    if not orders:
        await message.answer("Hozircha qarzdorlar mavjud emas.")
        return
    lines = ["📉 Qarzdor buyurtmalar:\n"]
    total_debt = Decimal("0")
    for order in orders:
        customer = await get_customer_by_id(session, int(order.customer_id))
        customer_name = customer.full_name if customer else "Noma'lum mijoz"
        total = Decimal(str(order.total_amount))
        paid = Decimal(str(order.paid_amount))
        left = total - paid
        total_debt += left
        lines.append(
            f"Buyurtma ID: {order.id}\n"
            f"Mijoz: {customer_name}\n"
            f"Jami: {format_number(total)} so'm\n"
            f"To'langan: {format_number(paid)} so'm\n"
            f"Qoldiq: {format_number(left)} so'm\n"
            f"Holat: {uzbek_order_status(order.status)}\n"
        )
    lines.append(f"Umumiy qarz: {format_number(total_debt)} so'm")
    await message.answer("\n".join(lines))