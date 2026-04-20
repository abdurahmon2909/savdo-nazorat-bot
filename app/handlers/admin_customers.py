from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.reply import (
    admin_menu_keyboard,
    cancel_keyboard,
    customers_menu_keyboard,
)
from app.services.customers import (
    create_customer,
    get_customer_by_phone,
    list_customers,
    search_customers,
)
from app.states.customer_state import AddCustomerState, SearchCustomerState

router = Router()


def is_admin(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in settings.admin_ids)


@router.message(F.text == "👥 Mijozlar")
async def customers_menu(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    await state.clear()
    await message.answer(
        "Mijozlar bo'limi.",
        reply_markup=customers_menu_keyboard(),
    )


@router.message(F.text == "⬅️ Orqaga")
async def back_to_admin_menu(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    await state.clear()
    await message.answer(
        "Admin panelga qaytdingiz.",
        reply_markup=admin_menu_keyboard(),
    )


@router.message(F.text == "➕ Mijoz qo'shish")
async def add_customer_start(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    await state.set_state(AddCustomerState.full_name)
    await message.answer(
        "Yangi mijozning ism-familiyasini yuboring.\n\n"
        "Masalan: Ali Valiyev",
        reply_markup=cancel_keyboard(),
    )


@router.message(F.text == "❌ Bekor qilish")
async def cancel_any_state(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    await state.clear()
    await message.answer(
        "Amal bekor qilindi.",
        reply_markup=admin_menu_keyboard(),
    )


@router.message(AddCustomerState.full_name)
async def add_customer_full_name(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    full_name = (message.text or "").strip()
    if len(full_name) < 3:
        await message.answer("Iltimos, ism-familiyani to'g'ri kiriting.")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(AddCustomerState.phone)
    await message.answer(
        "Telefon raqamini yuboring.\n\n"
        "Masalan: +998901234567 yoki 901234567"
    )


@router.message(AddCustomerState.phone)
async def add_customer_phone(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not is_admin(message):
        return

    phone = (message.text or "").strip().replace(" ", "")
    if len(phone) < 9:
        await message.answer("Telefon raqamini to'g'ri kiriting.")
        return

    existing_customer = await get_customer_by_phone(session, phone)
    if existing_customer:
        await message.answer(
            "Bu telefon raqam bilan mijoz allaqachon mavjud.\n"
            "Boshqa raqam kiriting yoki amalni bekor qiling."
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(AddCustomerState.address)
    await message.answer(
        "Manzilni yuboring.\n\n"
        "Agar kerak bo'lmasa, '-' yuboring."
    )


@router.message(AddCustomerState.address)
async def add_customer_address(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    address = (message.text or "").strip()
    await state.update_data(address=None if address == "-" else address)
    await state.set_state(AddCustomerState.note)
    await message.answer(
        "Izoh yuboring.\n\n"
        "Agar kerak bo'lmasa, '-' yuboring."
    )


@router.message(AddCustomerState.note)
async def add_customer_note(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not is_admin(message):
        return

    note = (message.text or "").strip()
    data = await state.get_data()

    customer = await create_customer(
        session=session,
        full_name=data["full_name"],
        phone=data["phone"],
        address=data.get("address"),
        note=None if note == "-" else note,
        status="ishonchli",
    )

    await state.clear()

    await message.answer(
        "Mijoz muvaffaqiyatli qo'shildi.\n\n"
        f"ID: {customer.id}\n"
        f"Ism: {customer.full_name}\n"
        f"Telefon: {customer.phone}\n"
        f"Holat: {customer.status}",
        reply_markup=customers_menu_keyboard(),
    )


@router.message(F.text == "📋 Mijozlar ro'yxati")
async def customers_list(message: Message, session: AsyncSession) -> None:
    if not is_admin(message):
        return

    customers = await list_customers(session=session, limit=20)

    if not customers:
        await message.answer(
            "Hozircha mijozlar mavjud emas.",
            reply_markup=customers_menu_keyboard(),
        )
        return

    lines = ["So'nggi mijozlar ro'yxati:\n"]
    for index, customer in enumerate(customers, start=1):
        lines.append(
            f"{index}. {customer.full_name}\n"
            f"   Telefon: {customer.phone}\n"
            f"   Holat: {customer.status}\n"
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=customers_menu_keyboard(),
    )


@router.message(F.text == "🔎 Mijoz qidirish")
async def search_customer_start(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    await state.set_state(SearchCustomerState.query)
    await message.answer(
        "Qidirish uchun ism yoki telefon yuboring.\n\n"
        "Masalan: Ali\n"
        "yoki\n"
        "+998901234567",
        reply_markup=cancel_keyboard(),
    )


@router.message(SearchCustomerState.query)
async def search_customer_query(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not is_admin(message):
        return

    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("Qidiruv uchun kamida 2 ta belgi kiriting.")
        return

    customers = await search_customers(session=session, query=query, limit=20)

    if not customers:
        await message.answer(
            "Hech narsa topilmadi.",
            reply_markup=customers_menu_keyboard(),
        )
        await state.clear()
        return

    lines = ["Topilgan mijozlar:\n"]
    for index, customer in enumerate(customers, start=1):
        lines.append(
            f"{index}. {customer.full_name}\n"
            f"   Telefon: {customer.phone}\n"
            f"   Holat: {customer.status}\n"
            f"   Manzil: {customer.address or 'kiritilmagan'}\n"
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=customers_menu_keyboard(),
    )
    await state.clear()