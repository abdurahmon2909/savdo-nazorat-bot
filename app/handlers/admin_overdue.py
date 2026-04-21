from decimal import Decimal
from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.common_inline import back_to_admin_home_keyboard
from app.services.customers import get_customer_by_id
from app.services.orders import list_overdue_orders
from app.utils.helpers import is_admin, format_number
from app.utils.statuses import uzbek_order_status
from app.utils.timezone import now_utc

router = Router()


@router.callback_query(F.data == "admin_menu:overdue")
async def overdue(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    orders = await list_overdue_orders(session, days=7, limit=50)
    if not orders:
        await callback.message.edit_text(
            "Kechikkan qarz yo'q",
            reply_markup=back_to_admin_home_keyboard()
        )
        await callback.answer()
        return

    out = ["⏰ 7+ kun qarzlar:\n"]
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
    await callback.message.edit_text(
        "\n".join(out),
        reply_markup=back_to_admin_home_keyboard()
    )
    await callback.answer()