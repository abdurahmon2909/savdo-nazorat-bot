from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Contact, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.reply import (
    admin_menu_keyboard,
    contact_keyboard,
    main_menu_keyboard,
    remove_keyboard,
)
from app.services.customers import get_customer_by_phone
from app.services.orders import list_customer_orders, list_customer_open_orders
from app.services.users import create_or_update_user, get_user_by_telegram_id

router = Router()


def role(uid):
    return "admin" if uid in settings.admin_ids else "mijoz"


def fmt(x):
    t = format(Decimal(str(x)), "f")
    return t.rstrip("0").rstrip(".") if "." in t else t


@router.message(CommandStart())
async def start(message: Message, session: AsyncSession):
    u = message.from_user
    if not u:
        return

    r = role(u.id)
    ex = await get_user_by_telegram_id(session, u.id)

    if ex and ex.phone:
        await create_or_update_user(
            session,
            u.id,
            u.full_name,
            u.username,
            ex.phone,
            r,
        )

        kb = admin_menu_keyboard() if r == "admin" else main_menu_keyboard()
        await message.answer("Xush kelibsiz", reply_markup=kb)
        return

    await message.answer("Raqamingizni yuboring", reply_markup=contact_keyboard())


@router.message(F.contact)
async def contact(message: Message, session: AsyncSession):
    u = message.from_user
    c: Contact = message.contact

    if not u or not c or c.user_id != u.id:
        return

    r = role(u.id)

    user = await create_or_update_user(
        session,
        u.id,
        u.full_name,
        u.username,
        c.phone_number,
        r,
    )

    await message.answer("Ro'yxatdan o'tdingiz", reply_markup=remove_keyboard())

    kb = admin_menu_keyboard() if r == "admin" else main_menu_keyboard()
    await message.answer("Menu:", reply_markup=kb)


@router.message(F.text == "💳 Mening qarzim")
async def my_debt(message: Message, session: AsyncSession):
    u = message.from_user
    if not u:
        return

    user = await get_user_by_telegram_id(session, u.id)
    if not user or not user.phone:
        return

    cust = await get_customer_by_phone(session, user.phone)
    if not cust:
        return

    orders = await list_customer_open_orders(session, cust.id)

    if not orders:
        await message.answer("Qarz yo'q")
        return

    total = Decimal("0")
    out = []

    for o in orders:
        t = Decimal(str(o.total_amount))
        p = Decimal(str(o.paid_amount))
        l = t - p
        total += l

        out.append(f"ID:{o.id} Qoldiq:{fmt(l)}")

    out.append(f"Jami qarz: {fmt(total)} so'm")

    await message.answer("\n".join(out))


@router.message(F.text == "📦 Buyurtmalarim")
async def my_orders(message: Message, session: AsyncSession):
    u = message.from_user
    if not u:
        return

    user = await get_user_by_telegram_id(session, u.id)
    if not user or not user.phone:
        return

    cust = await get_customer_by_phone(session, user.phone)
    if not cust:
        return

    orders = await list_customer_orders(session, cust.id)

    if not orders:
        await message.answer("Buyurtmalar yo'q")
        return

    out = []

    for o in orders:
        t = Decimal(str(o.total_amount))
        p = Decimal(str(o.paid_amount))
        l = t - p

        out.append(f"ID:{o.id} Jami:{fmt(t)} Qoldiq:{fmt(l)}")

    await message.answer("\n".join(out))