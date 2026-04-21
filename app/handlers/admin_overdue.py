from datetime import datetime
from decimal import Decimal
from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.customers import get_customer_by_id
from app.services.orders import list_overdue_orders
from app.utils.helpers import is_admin, format_number
from app.utils.statuses import uzbek_order_status
from app.utils.timezone import now_utc, utc_to_tashkent

router = Router()


@router.message(F.text == "⏰ Kechikkan qarzlar")
async def overdue(message: Message, session: AsyncSession):
    if not is_admin(message):
        return
    orders = await list_overdue_orders(session, days=7, limit=50)
    if not orders:
        await message.answer("Kechikkan qarz yo'q")
        return
    out = ["7+ kun qarzlar:\n"]
    now = now_utc()
    for o in orders:
        c = await get_customer_by_id(session, o.customer_id)
        name = c.full_name if c else "Noma'lum"
        total = Decimal(str(o.total_amount))
        paid = Decimal(str(o.paid_amount))
        left = total - paid
        days = (now.date() - o.created_at.date()).days
        out.append(
            f"ID: {o.id}\n"
            f"Mijoz: {name}\n"
            f"Qoldiq: {format_number(left)} so'm\n"
            f"Holat: {uzbek_order_status(o.status)}\n"
            f"Kechikish: {days} kun\n"
        )
    await message.answer("\n".join(out))