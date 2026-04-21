from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.customers_inline import customers_cancel_keyboard, customers_main_keyboard
from app.keyboards.admin_panel_inline import admin_main_keyboard
from app.services.customers import (
    create_customer,
    get_customer_by_phone,
    list_customers,
    search_customers,
)
from app.states.customer_state import AddCustomerState, SearchCustomerState
from app.utils.helpers import is_admin

router = Router()


@router.callback_query(F.data == "admin_menu:customers")
async def customers_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.clear()
    if callback.message:
        await callback.message.edit_text("Mijozlar bo'limi:", reply_markup=customers_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_customers:add")
async def add_customer_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AddCustomerState.full_name)
    if callback.message:
        await callback.message.edit_text(
            "Yangi mijozning ism-familiyasini yuboring.\n\nMasalan: Ali Valiyev",
            reply_markup=customers_cancel_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_customers:cancel")
async def cancel_any_state(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.clear()
    if callback.message:
        await callback.message.edit_text("Amal bekor qilindi.", reply_markup=admin_main_keyboard())
    await callback.answer()


@router.message(AddCustomerState.full_name)
async def add_customer_full_name(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return
    full_name = (message.text or "").strip()
    if len(full_name) < 3:
        await message.answer("Iltimos, ism-familiyani to'g'ri kiriting.", reply_markup=customers_cancel_keyboard())
        return
    await state.update_data(full_name=full_name)
    await state.set_state(AddCustomerState.phone)
    await message.answer(
        "Telefon raqamini yuboring.\n\nMasalan: +998901234567 yoki 901234567",
        reply_markup=customers_cancel_keyboard(),
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
        await message.answer("Telefon raqamini to'g'ri kiriting.", reply_markup=customers_cancel_keyboard())
        return
    existing_customer = await get_customer_by_phone(session, phone)
    if existing_customer:
        await message.answer(
            "Bu telefon raqam bilan mijoz allaqachon mavjud.\n"
            "Boshqa raqam kiriting yoki amalni bekor qiling.",
            reply_markup=customers_cancel_keyboard(),
        )
        return
    await state.update_data(phone=phone)
    await state.set_state(AddCustomerState.address)
    await message.answer("Manzilni yuboring.\n\nAgar kerak bo'lmasa, '-' yuboring.", reply_markup=customers_cancel_keyboard())


@router.message(AddCustomerState.address)
async def add_customer_address(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return
    address = (message.text or "").strip()
    await state.update_data(address=None if address == "-" else address)
    await state.set_state(AddCustomerState.note)
    await message.answer("Izoh yuboring.\n\nAgar kerak bo'lmasa, '-' yuboring.", reply_markup=customers_cancel_keyboard())


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
        reply_markup=customers_main_keyboard(),
    )


@router.callback_query(F.data == "admin_customers:list")
async def customers_list(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    customers = await list_customers(session=session, limit=20)
    if not customers:
        if callback.message:
            await callback.message.edit_text(
                "Hozircha mijozlar mavjud emas.",
                reply_markup=customers_main_keyboard(),
            )
        await callback.answer()
        return
    lines = ["So'nggi mijozlar ro'yxati:\n"]
    for index, customer in enumerate(customers, start=1):
        lines.append(
            f"{index}. {customer.full_name}\n"
            f"   Telefon: {customer.phone}\n"
            f"   Holat: {customer.status}\n"
        )
    if callback.message:
        await callback.message.edit_text(
            "\n".join(lines),
            reply_markup=customers_main_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_customers:search")
async def search_customer_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(SearchCustomerState.query)
    if callback.message:
        await callback.message.edit_text(
            "Qidirish uchun ism yoki telefon yuboring.\n\nMasalan: Ali\nyoki\n+998901234567",
            reply_markup=customers_cancel_keyboard(),
        )
    await callback.answer()


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
        await message.answer("Qidiruv uchun kamida 2 ta belgi kiriting.", reply_markup=customers_cancel_keyboard())
        return
    customers = await search_customers(session=session, query=query, limit=20)
    if not customers:
        await message.answer(
            "Hech narsa topilmadi.",
            reply_markup=customers_main_keyboard(),
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
        reply_markup=customers_main_keyboard(),
    )
    await state.clear()