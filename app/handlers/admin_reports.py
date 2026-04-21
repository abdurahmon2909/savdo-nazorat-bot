from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.reports import get_current_year_month, get_monthly_report, get_monthly_top_products
from app.utils.helpers import is_admin, fmt

router = Router()


@router.message(F.text == "📊 Hisobotlar")
async def monthly_report(message: Message, session: AsyncSession):
    if not is_admin(message):
        return
    year, month = get_current_year_month()
    report = await get_monthly_report(session, year, month)
    top_products = await get_monthly_top_products(session, year, month, limit=5)

    lines = [
        f"{month}-{year} hisobot:\n",
        f"Buyurtmalar soni: {report['order_count']}",
        f"Jami savdo: {fmt(report['total'])} so'm",
        f"To'langan: {fmt(report['paid'])} so'm",
        f"Qarz: {fmt(report['unpaid'])} so'm",
        "",
        "Tez sotilayotgan mahsulotlar:",
    ]
    if top_products:
        for index, item in enumerate(top_products, start=1):
            lines.append(f"{index}. {item['name']} — {fmt(item['sold_qty'])} dona")
    else:
        lines.append("Hozircha sotuv statistikasi yo'q.")
    await message.answer("\n".join(lines))