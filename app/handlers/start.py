from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Contact, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.reply import contact_keyboard, main_menu_keyboard, remove_keyboard
from app.services.users import create_or_update_user, get_user_by_telegram_id

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession) -> None:
    tg_user = message.from_user
    if tg_user is None:
        return

    existing_user = await get_user_by_telegram_id(session, tg_user.id)

    if existing_user and existing_user.phone:
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

    user = await create_or_update_user(
        session=session,
        telegram_id=tg_user.id,
        full_name=tg_user.full_name,
        username=tg_user.username,
        phone=contact.phone_number,
        role="mijoz",
    )

    await message.answer(
        f"Rahmat, {user.full_name}.\n\n"
        "Siz muvaffaqiyatli ro'yxatdan o'tdingiz.",
        reply_markup=remove_keyboard(),
    )

    await message.answer(
        "Asosiy bo'limlardan birini tanlang:",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == "💳 Mening qarzim")
async def my_debt_handler(message: Message) -> None:
    await message.answer(
        "Hozircha bu bo'lim tayyor emas.\n"
        "Keyingi bosqichda qarz bo'limini ulaymiz."
    )


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