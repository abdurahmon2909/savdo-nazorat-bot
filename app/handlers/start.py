from datetime import datetime
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Contact, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.admin_panel_inline import admin_main_keyboard
from app.keyboards.reply import (
    admin_menu_keyboard,
    contact_keyboard,
    main_menu_keyboard,
    remove_keyboard,
)
from app.services.customers import (
    auto_link_customer_by_phone,
    get_customer_by_linked_telegram_id,
    get_customer_by_phone,
)
from app.services.order_requests import list_customer_order_requests
from app.services.orders import list_customer_orders, list_customer_open_orders
from app.services.users import create_or_update_user, get_user_by_telegram_id

router = Router()


def role(uid: int) -> str:
    return "admin" if uid in settings.admin_ids else "mijoz"


def fmt(x) -> str:
    t = format(Decimal(str(x)), "f")
    return t.rstrip("0").rstrip(".") if "." in t else t


def fmt_dt(dt_value) -> str:
    if dt_value is None:
        return "Noma'lum vaqt"

    try:
        return dt_value.strftime("%d-%m-%Y %H:%M")
    except Exception:
        return str(dt_value)


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

        if r != "admin":
            await auto_link_customer_by_phone(session, ex.phone, u.id)
            await message.answer("Xush kelibsiz", reply_markup=main_menu_keyboard())
        else:
            await message.answer("Xush kelibsiz", reply_markup=admin_menu_keyboard())
            await message.answer("Admin panel:", reply_markup=admin_main_keyboard())
        return

    await message.answer("Raqamingizni yuboring", reply_markup=contact_keyboard())


@router.message(F.contact)
async def contact(message: Message, session: AsyncSession):
    u = message.from_user
    c: Contact = message.contact

    if not u or not c or c.user_id != u.id:
        return

    r = role(u.id)

    await create_or_update_user(
        session,
        u.id,
        u.full_name,
        u.username,
        c.phone_number,
        r,
    )

    if r != "admin":
        await auto_link_customer_by_phone(session, c.phone_number, u.id)
        await message.answer("Ro'yxatdan o'tdingiz", reply_markup=remove_keyboard())
        await message.answer("Menu:", reply_markup=main_menu_keyboard())
    else:
        await message.answer("Ro'yxatdan o'tdingiz", reply_markup=remove_keyboard())
        await message.answer("Admin panel:", reply_markup=admin_main_keyboard())


@router.message(F.text == "💳 Mening qarzim")
async def my_debt(message: Message, session: AsyncSession):
    u = message.from_user
    if not u:
        return

    user = await get_user_by_telegram_id(session, u.id)
    if not user or not user.phone:
        await message.answer("Avval ro'yxatdan o'ting.")
        return

    cust = await get_customer_by_linked_telegram_id(session, u.id)
    if cust is None:
        cust = await get_customer_by_phone(session, user.phone)

    if not cust:
        await message.answer("Siz uchun mijoz kartasi topilmadi.")
        return

    orders = await list_customer_open_orders(session, cust.id)

    if not orders:
        await message.answer("Qarz yo'q")
        return

    total = Decimal("0")
    out = [f"{cust.full_name} uchun ochiq qarzlar:\n"]

    for o in orders:
        t = Decimal(str(o.total_amount))
        p = Decimal(str(o.paid_amount))
        l = t - p
        total += l

        out.append(
            f"Buyurtma ID: {o.id}\n"
            f"Sana: {fmt_dt(o.created_at)}\n"
            f"Jami: {fmt(t)} so'm\n"
            f"To'langan: {fmt(p)} so'm\n"
            f"Qoldiq: {fmt(l)} so'm\n"
            f"Holat: {o.status}\n"
        )

    out.append(f"Jami qarz: {fmt(total)} so'm")

    await message.answer("\n".join(out))


@router.message(F.text == "📦 Buyurtmalarim")
async def my_orders(message: Message, session: AsyncSession):
    u = message.from_user
    if not u:
        return

    user = await get_user_by_telegram_id(session, u.id)
    if not user or not user.phone:
        await message.answer("Avval ro'yxatdan o'ting.")
        return

    cust = await get_customer_by_linked_telegram_id(session, u.id)
    if cust is None:
        cust = await get_customer_by_phone(session, user.phone)

    if not cust:
        await message.answer("Siz uchun mijoz topilmadi.")
        return

    orders = await list_customer_orders(session, cust.id)
    requests = await list_customer_order_requests(session, u.id, limit=20)

    if not orders and not requests:
        await message.answer("Buyurtmalar yo'q")
        return

    out = [f"{cust.full_name} buyurtmalari:\n"]

    if requests:
        out.append("So'rovlar:")
        for req in requests:
            out.append(
                f"So'rov ID: {req.id}\n"
                f"Sana: {fmt_dt(req.created_at)}\n"
                f"Jami: {fmt(req.total_amount)} so'm\n"
                f"To'lov turi: {req.payment_type}\n"
                f"Holat: {req.status}\n"
            )

    if orders:
        out.append("Tasdiqlangan buyurtmalar:")
        for o in orders:
            t = Decimal(str(o.total_amount))
            p = Decimal(str(o.paid_amount))
            l = t - p

            out.append(
                f"Buyurtma ID: {o.id}\n"
                f"Sana: {fmt_dt(o.created_at)}\n"
                f"Jami: {fmt(t)} so'm\n"
                f"To'langan: {fmt(p)} so'm\n"
                f"Qoldiq: {fmt(l)} so'm\n"
                f"Holat: {o.status}\n"
            )

    await message.answer("\n".join(out))


@router.message(F.text == "☎️ Aloqa")
async def contact_info(message: Message):
    await message.answer(
        "Aloqa uchun admin bilan bog'laning.\n"
        "Keyingi bosqichda bu yerga aniq aloqa ma'lumoti qo'shamiz."
    )