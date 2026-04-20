import asyncio
from datetime import datetime

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.services.customers import get_customer_by_id
from app.services.orders import list_overdue_orders


def format_number(x):
    from decimal import Decimal

    t = format(Decimal(str(x)), "f")
    return t.rstrip("0").rstrip(".") if "." in t else t


async def send_admin_report(bot: Bot, session: AsyncSession):
    orders = await list_overdue_orders(session)

    if not orders:
        return

    lines = ["⏰ Kechikkan qarzlar:\n"]

    for o in orders:
        customer = await get_customer_by_id(session, o.customer_id)
        name = customer.full_name if customer else "Noma'lum"

        total = o.total_amount
        paid = o.paid_amount
        left = float(total) - float(paid)

        days = (datetime.utcnow() - o.created_at).days

        lines.append(
            f"{name}\n"
            f"Qarz: {format_number(left)} so'm\n"
            f"{days} kun\n"
        )

    text = "\n".join(lines)

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except:
            pass


async def send_customer_reminders(bot: Bot, session: AsyncSession):
    orders = await list_overdue_orders(session)

    for o in orders:
        customer = await get_customer_by_id(session, o.customer_id)

        if not customer or not customer.phone:
            continue

        # ⚠️ bu joy keyinchalik user bilan bog‘lanadi
        # hozir skip qilamiz
        continue


async def reminder_loop(bot: Bot, sessionmaker: async_sessionmaker):
    while True:
        now = datetime.utcnow()

        # har kuni 09:00 (UTC moslash mumkin keyin)
        if now.hour == 9 and now.minute == 0:
            async with sessionmaker() as session:
                await send_admin_report(bot, session)
                await send_customer_reminders(bot, session)

            await asyncio.sleep(60)

        await asyncio.sleep(20)