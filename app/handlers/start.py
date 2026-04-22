from decimal import Decimal
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Contact, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.common_inline import admin_main_menu_keyboard, customer_main_menu_keyboard
from app.keyboards.reply import contact_keyboard, remove_keyboard
from app.services.customers import (
    auto_link_customer_by_phone,
    get_customer_by_linked_telegram_id,
    get_customer_by_phone,
)
from app.services.order_requests import list_customer_order_requests
from app.services.orders import list_customer_orders, list_customer_open_orders
from app.services.users import create_or_update_user, get_user_by_telegram_id
from app.utils.helpers import fmt, is_admin
from app.utils.statuses import uzbek_order_status
from app.utils.timezone import format_datetime_tashkent

router = Router()


def role(uid: int) -> str:
    return "admin" if uid in settings.admin_ids else "mijoz"


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
            await message.answer("Xush kelibsiz!", reply_markup=remove_keyboard())
            await message.answer("Asosiy menyu:", reply_markup=customer_main_menu_keyboard())
        else:
            await message.answer("Xush kelibsiz!", reply_markup=remove_keyboard())
            await message.answer("Admin panel:", reply_markup=admin_main_menu_keyboard())
        return

    await message.answer("Iltimos, telefon raqamingizni yuboring.", reply_markup=contact_keyboard())


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
        await message.answer("Ro'yxatdan o'tdingiz!", reply_markup=remove_keyboard())
        await message.answer("Asosiy menyu:", reply_markup=customer_main_menu_keyboard())
    else:
        await message.answer("Ro'yxatdan o'tdingiz!", reply_markup=remove_keyboard())
        await message.answer("Admin panel:", reply_markup=admin_main_menu_keyboard())


@router.callback_query(F.data == "customer_menu:my_debt")
async def my_debt(callback: CallbackQuery, session: AsyncSession):
    u = callback.from_user
    if not u:
        return

    user = await get_user_by_telegram_id(session, u.id)
    if not user or not user.phone:
        await callback.answer("Avval ro'yxatdan o'ting.", show_alert=True)
        return

    cust = await get_customer_by_linked_telegram_id(session, u.id)
    if cust is None:
        cust = await get_customer_by_phone(session, user.phone)

    if not cust:
        await callback.answer("Siz uchun mijoz kartasi topilmadi.", show_alert=True)
        return

    orders = await list_customer_open_orders(session, cust.id)

    if not orders:
        await callback.message.edit_text("Sizning qarzingiz yo'q.", reply_markup=customer_main_menu_keyboard())
        await callback.answer()
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
            f"Sana: {format_datetime_tashkent(o.created_at)}\n"
            f"Jami: {fmt(t)} so'm\n"
            f"To'langan: {fmt(p)} so'm\n"
            f"Qoldiq: {fmt(l)} so'm\n"
            f"Holat: {uzbek_order_status(o.status)}\n"
        )
    out.append(f"Jami qarz: {fmt(total)} so'm")
    await callback.message.edit_text("\n".join(out), reply_markup=customer_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "customer_menu:my_orders")
async def my_orders(callback: CallbackQuery, session: AsyncSession):
    u = callback.from_user
    if not u:
        return

    user = await get_user_by_telegram_id(session, u.id)
    if not user or not user.phone:
        await callback.answer("Avval ro'yxatdan o'ting.", show_alert=True)
        return

    cust = await get_customer_by_linked_telegram_id(session, u.id)
    if cust is None:
        cust = await get_customer_by_phone(session, user.phone)

    if not cust:
        await callback.answer("Siz uchun mijoz topilmadi.", show_alert=True)
        return

    orders = await list_customer_orders(session, cust.id)
    requests = await list_customer_order_requests(session, u.id, limit=20)

    if not orders and not requests:
        await callback.message.edit_text("Sizning buyurtmalaringiz yo'q.", reply_markup=customer_main_menu_keyboard())
        await callback.answer()
        return

    out = [f"{cust.full_name} buyurtmalari:\n"]
    if requests:
        out.append("So'rovlar:")
        for req in requests:
            out.append(
                f"So'rov ID: {req.id}\n"
                f"Sana: {format_datetime_tashkent(req.created_at)}\n"
                f"Jami: {fmt(req.total_amount)} so'm\n"
                f"To'lov turi: {req.payment_type}\n"
                f"Holat: {uzbek_order_status(req.status)}\n"
            )
    if orders:
        out.append("Tasdiqlangan buyurtmalar:")
        for o in orders:
            t = Decimal(str(o.total_amount))
            p = Decimal(str(o.paid_amount))
            l = t - p
            out.append(
                f"Buyurtma ID: {o.id}\n"
                f"Sana: {format_datetime_tashkent(o.created_at)}\n"
                f"Jami: {fmt(t)} so'm\n"
                f"To'langan: {fmt(p)} so'm\n"
                f"Qoldiq: {fmt(l)} so'm\n"
                f"Holat: {uzbek_order_status(o.status)}\n"
            )
    await callback.message.edit_text("\n".join(out), reply_markup=customer_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "customer_menu:contact")
async def contact_info(callback: CallbackQuery):
    await callback.message.edit_text(
        "Aloqa uchun admin bilan bog'laning.\nTelegram: @abdurahmon_2909",
        reply_markup=customer_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "customer_menu:home")
async def customer_home(callback: CallbackQuery):
    await callback.message.edit_text("Asosiy menyu:", reply_markup=customer_main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "global:cancel")
async def global_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = callback.from_user
    if role(user.id) == "admin":
        await callback.message.edit_text("Admin panel:", reply_markup=admin_main_menu_keyboard())
    else:
        await callback.message.edit_text("Asosiy menyu:", reply_markup=customer_main_menu_keyboard())
    await callback.answer("Amal bekor qilindi.")