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
from app.services.orders import list_customer_open_orders
from app.services.users import create_or_update_user, get_user_by_telegram_id

router = Router()


def get_role(telegram_id: int) -> str:
    return "admin" if telegram_id in settings.admin_ids else "mijoz"


def format_number(value: Decimal | float | int | str) -> str:
    text = format(Decimal(str(value)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


@router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession) -> None:
    tg_user = message.from_user
    if tg_user is None:
        return

    role = get_role(tg_user.id)
    existing_user = await get_user_by_telegram_id(session, tg_user.id)

    if existing_user and existing_user.phone:
        await create_or_update_user(
            session=session,
            telegram_id=tg_user.id,
            full_name=tg_user.full_name,
            username=tg_user.username,
            phone=existing_user.phone,
            role=role,
        )

        if role == "admin":
            await message.answer(
                f"Assalomu alaykum, {existing_user.full_name}.\n\n"
                "Admin panelga xush kelibsiz.",
                reply_markup=admin_menu_keyboard(),
            )
        else:
            await message.answer(
                f"Assalomu alaykum, {existing_user.full_name}.\n\n"
                "Botga xush kelibsiz.",
                reply_markup=main_menu_keyboard(),
            )
        return

    await message.answer(
        "Assalomu alaykum.\n\n"
        "Botdan foydalanish uchun telefon raqamingizni yuboring.",
        reply_markup=contact_keyboard(),
    )


@router.message(F.contact)
async def contact_handler(message: Message, session: AsyncSession) -> None:
    tg_user = message.from_user
    contact: Contact | None = message.contact

    if tg_user is None or contact is None:
        return

    if contact.user_id != tg_user.id:
        await message.answer(
            "Iltimos, aynan o'zingizning raqamingizni yuboring.",
            reply_markup=contact_keyboard(),
        )
        return

    role = get_role(tg_user.id)

    user = await create_or_update_user(
        session=session,
        telegram_id=tg_user.id,
        full_name=tg_user.full_name,
        username=tg_user.username,
        phone=contact.phone_number,
        role=role,
    )

    await message.answer(
        f"Rahmat, {user.full_name}.\n\n"
        "Siz muvaffaqiyatli ro'yxatdan o'tdingiz.",
        reply_markup=remove_keyboard(),
    )

    if role == "admin":
        await message.answer(
            "Admin bo'limlaridan birini tanlang:",
            reply_markup=admin_menu_keyboard(),
        )
    else:
        await message.answer(
            "Asosiy bo'limlardan birini tanlang:",
            reply_markup=main_menu_keyboard(),
        )


@router.message(F.text == "💳 Mening qarzim")
async def my_debt_handler(message: Message, session: AsyncSession) -> None:
    tg_user = message.from_user
    if tg_user is None:
        return

    user = await get_user_by_telegram_id(session, tg_user.id)
    if user is None or not user.phone:
        await message.answer("Avval ro'yxatdan o'ting.")
        return

    customer = await get_customer_by_phone(session, user.phone)
    if customer is None:
        await message.answer("Siz uchun mijoz kartasi topilmadi.")
        return

    orders = await list_customer_open_orders(session, customer.id, limit=20)
    if not orders:
        await message.answer("Sizda hozircha ochiq qarz mavjud emas.")
        return

    lines = [f"{customer.full_name} uchun ochiq qarzlar:\n"]
    total_left = Decimal("0")

    for order in orders:
        total = Decimal(str(order.total_amount))
        paid = Decimal(str(order.paid_amount))
        left = total - paid
        total_left += left

        lines.append(
            f"Buyurtma ID: {order.id}\n"
            f"Jami: {format_number(total)} so'm\n"
            f"To'langan: {format_number(paid)} so'm\n"
            f"Qoldiq: {format_number(left)} so'm\n"
            f"Holat: {order.status}\n"
        )

    lines.append(f"Umumiy qarzingiz: {format_number(total_left)} so'm")
    await message.answer("\n".join(lines))


@router.message(F.text == "📦 Buyurtmalarim")
async def my_orders_handler(message: Message) -> None:
    await message.answer(
        "Hozircha bu bo'lim tayyor emas.\n"
        "Keyingi bosqichda buyurtmalar bo'limini ulaymiz."
    )


@router.message(F.text == "☎️ Aloqa")
async def contact_info_handler(message: Message) -> None:
    await message.answer(
        "Aloqa uchun admin bilan bog'laning.\n"
        "Keyingi bosqichda bu yerga aniq aloqa ma'lumoti qo'shamiz."
    )


@router.message(F.text == "📊 Hisobotlar")
async def reports_stub(message: Message) -> None:
    await message.answer("Hozircha bu bo'lim tayyor emas.")