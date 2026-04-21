from decimal import Decimal
from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.customers import get_customer_by_id
from app.services.orders import list_recent_orders
from app.utils.helpers import is_admin, format_number
from app.utils.statuses import uzbek_order_status

router = Router()


@router.message(F.text == "📚 Buyurtmalar tarixi")
async def show_order_history(message: Message, session: AsyncSession):
    if not is_admin(message):
        return
    orders = await list_recent_orders(session, limit=50)
    if not orders:
        await message.answer("Hozircha buyurtmalar mavjud emas.")
        return
    lines = ["📚 So‘nggi buyurtmalar:\n"]
    for order in orders:
        customer = await get_customer_by_id(session, int(order.customer_id))
        name = customer.full_name if customer else "Noma'lum"
        total = Decimal(str(order.total_amount))
        paid = Decimal(str(order.paid_amount))
        left = total - paid
        lines.append(
            f"ID: {order.id}\n"
            f"Mijoz: {name}\n"
            f"Jami: {format_number(total)} so'm\n"
            f"To‘langan: {format_number(paid)} so'm\n"
            f"Qoldiq: {format_number(left)} so'm\n"
            f"Holat: {uzbek_order_status(order.status)}\n"
        )
    await message.answer("\n".join(lines))