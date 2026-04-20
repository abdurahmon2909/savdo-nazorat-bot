from decimal import Decimal

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.reports import get_current_year_month, get_monthly_report

router = Router()


def is_admin(message: Message):
    return message.from_user and message.from_user.id in settings.admin_ids


def fmt(x):
    t = format(Decimal(str(x)), "f")
    return t.rstrip("0").rstrip(".") if "." in t else t


@router.message(F.text == "📊 Hisobotlar")
async def monthly_report(message: Message, session: AsyncSession):
    if not is_admin(message):
        return

    y, m = get_current_year_month()
    d = await get_monthly_report(session, y, m)

    await message.answer(
        f"{m}-{y} hisobot:\n\n"
        f"Jami: {fmt(d['total'])} so'm\n"
        f"To'langan: {fmt(d['paid'])} so'm\n"
        f"Qarz: {fmt(d['unpaid'])} so'm"
    )