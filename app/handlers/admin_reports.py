from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.common_inline import back_to_admin_home_keyboard
from app.services.reports import get_current_year_month, get_monthly_report, get_monthly_top_products
from app.utils.helpers import is_admin, fmt

router = Router()


@router.callback_query(F.data == "admin_menu:reports")
async def monthly_report(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    year, month = get_current_year_month()
    report = await get_monthly_report(session, year, month)
    top_products = await get_monthly_top_products(session, year, month, limit=5)

    lines = [
        f"📊 {month}-{year} hisobot:\n",
        f"📦 Buyurtmalar soni: {report['order_count']}",
        f"💰 Jami savdo: {fmt(report['total'])} so'm",
        f"💵 To'langan: {fmt(report['paid'])} so'm",
        f"📉 Qarz: {fmt(report['unpaid'])} so'm",
        f"📈 Sof foyda: {fmt(report['profit'])} so'm",  # <-- yangi qator
        "",
        "🔥 Tez sotilayotgan mahsulotlar:",
    ]
    if top_products:
        for idx, item in enumerate(top_products, 1):
            lines.append(f"{idx}. {item['name']} — {fmt(item['sold_qty'])} dona | Foyda: {fmt(item['profit'])} so'm")
    else:
        lines.append("Hozircha sotuv statistikasi yo'q.")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=back_to_admin_home_keyboard()
    )
    await callback.answer()