import asyncio
import logging
from decimal import Decimal
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.services.customers import get_customer_by_id
from app.services.orders import list_overdue_orders
from app.utils.helpers import format_number
from app.utils.timezone import now_utc, utc_to_tashkent


async def send_admin_report(bot: Bot, session: AsyncSession) -> None:
    orders = await list_overdue_orders(session, days=7, limit=100)
    if not orders:
        return

    lines = ["⏰ Kechikkan qarzlar:\n"]
    total_debt = Decimal("0")
    now = now_utc()

    for order in orders:
        customer = await get_customer_by_id(session, int(order.customer_id))
        customer_name = customer.full_name if customer else "Noma'lum mijoz"
        total = Decimal(str(order.total_amount))
        paid = Decimal(str(order.paid_amount))
        left = total - paid
        total_debt += left

        days_passed = (now.date() - order.created_at.date()).days

        lines.append(
            f"Buyurtma ID: {order.id}\n"
            f"Mijoz: {customer_name}\n"
            f"Qoldiq: {format_number(left)} so'm\n"
            f"Kechikish: {days_passed} kun\n"
        )
    lines.append(f"Umumiy kechikkan qarz: {format_number(total_debt)} so'm")
    text = "\n".join(lines)

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            logging.exception(f"Adminga {admin_id} xabar yuborishda xato: {e}")


async def send_customer_reminders(bot: Bot, session: AsyncSession) -> None:
    orders = await list_overdue_orders(session, days=7, limit=100)
    sent_to = set()
    now = now_utc()

    for order in orders:
        customer = await get_customer_by_id(session, int(order.customer_id))
        if not customer or not customer.linked_telegram_id:
            continue
        if customer.linked_telegram_id in sent_to:
            continue

        customer_orders = [o for o in orders if int(o.customer_id) == customer.id]
        total_left = Decimal("0")
        max_days = 0
        for co in customer_orders:
            total = Decimal(str(co.total_amount))
            paid = Decimal(str(co.paid_amount))
            total_left += total - paid
            days = (now.date() - co.created_at.date()).days
            if days > max_days:
                max_days = days

        text = (
            f"Assalomu alaykum, {customer.full_name}.\n\n"
            f"Sizda kechikkan qarz mavjud.\n"
            f"Umumiy qoldiq: {format_number(total_left)} so'm\n"
            f"Eng eski qarz: {max_days} kun oldingi.\n\n"
            f"Iltimos, to'lovni imkon qadar tezroq amalga oshiring."
        )
        try:
            await bot.send_message(customer.linked_telegram_id, text)
            sent_to.add(customer.linked_telegram_id)
        except Exception as e:
            logging.exception(f"Mijoz {customer.id} ga xabar yuborishda xato: {e}")


async def reminder_loop(bot: Bot, session_factory: async_sessionmaker[AsyncSession]) -> None:
    last_run_date = None
    while True:
        try:
            now = now_utc()
            tashkent_now = utc_to_tashkent(now)
            if tashkent_now.hour == 9 and tashkent_now.minute < 5:
                if last_run_date != tashkent_now.date():
                    async with session_factory() as session:
                        await send_admin_report(bot, session)
                        await send_customer_reminders(bot, session)
                    last_run_date = tashkent_now.date()
                    await asyncio.sleep(300)
                    continue
            await asyncio.sleep(30)
        except Exception as e:
            logging.exception(f"reminder_loop da xato: {e}")
            await asyncio.sleep(60)