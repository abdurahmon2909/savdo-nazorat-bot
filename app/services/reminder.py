import asyncio
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.customers import get_customer_by_id
from app.services.orders import list_overdue_orders

TASHKENT_TZ = ZoneInfo("Asia/Tashkent")


def format_number(value) -> str:
    text = format(Decimal(str(value)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


async def send_admin_report(bot: Bot, session: AsyncSession) -> None:
    orders = await list_overdue_orders(session, days=7, limit=100)

    if not orders:
        for admin_id in []:
            _ = admin_id
        return

    lines = ["⏰ Kechikkan qarzlar:\n"]
    total_debt = Decimal("0")
    now = datetime.now(TASHKENT_TZ)

    for order in orders:
        customer = await get_customer_by_id(session, int(order.customer_id))
        customer_name = customer.full_name if customer else "Noma'lum mijoz"

        total = Decimal(str(order.total_amount))
        paid = Decimal(str(order.paid_amount))
        left = total - paid
        total_debt += left

        created_at = order.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=TASHKENT_TZ)
        else:
            created_at = created_at.astimezone(TASHKENT_TZ)

        days_passed = (now.date() - created_at.date()).days

        lines.append(
            f"Buyurtma ID: {order.id}\n"
            f"Mijoz: {customer_name}\n"
            f"Qoldiq: {format_number(left)} so'm\n"
            f"Kechikish: {days_passed} kun\n"
        )

    lines.append(f"Umumiy kechikkan qarz: {format_number(total_debt)} so'm")
    text = "\n".join(lines)

    from app.config import settings

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass


async def send_customer_reminders(bot: Bot, session: AsyncSession) -> None:
    orders = await list_overdue_orders(session, days=7, limit=100)

    sent_to: set[int] = set()

    for order in orders:
        customer = await get_customer_by_id(session, int(order.customer_id))
        if customer is None:
            continue

        if not customer.linked_telegram_id:
            continue

        if customer.linked_telegram_id in sent_to:
            continue

        customer_orders = [o for o in orders if int(o.customer_id) == int(customer.id)]

        total_left = Decimal("0")
        max_days = 0
        now = datetime.now(TASHKENT_TZ)

        for customer_order in customer_orders:
            total = Decimal(str(customer_order.total_amount))
            paid = Decimal(str(customer_order.paid_amount))
            left = total - paid
            total_left += left

            created_at = customer_order.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=TASHKENT_TZ)
            else:
                created_at = created_at.astimezone(TASHKENT_TZ)

            days_passed = (now.date() - created_at.date()).days
            if days_passed > max_days:
                max_days = days_passed

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
        except Exception:
            pass


async def reminder_loop(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    last_run_date: date | None = None

    while True:
        try:
            now = datetime.now(TASHKENT_TZ)

            if now.hour == 9 and now.minute == 0:
                if last_run_date != now.date():
                    async with session_factory() as session:
                        await send_admin_report(bot, session)
                        await send_customer_reminders(bot, session)

                    last_run_date = now.date()
                    await asyncio.sleep(65)
                    continue

            await asyncio.sleep(20)

        except Exception:
            await asyncio.sleep(30)