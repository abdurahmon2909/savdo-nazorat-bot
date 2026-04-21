from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.admin_customers_inline import customers_main_keyboard
from app.keyboards.common_inline import cancel_inline_keyboard, back_to_admin_home_keyboard
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
async def customers_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("Mijozlar bo'limi:", reply_markup=customers_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_customers:add")
async def add_customer_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AddCustomerState.full_name)
    await callback.message.edit_text(
        "Yangi mijozning ism-familiyasini yuboring.\n\nMasalan: Ali Valiyev",
        reply_markup=cancel_inline_keyboard(),
    )
    await callback.answer()


@router.message(AddCustomerState.full_name)
async def add_customer_full_name(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    full_name = (message.text or "").strip()
    if len(full_name) < 3:
        await message.answer("Ism-familiya juda qisqa.", reply_markup=cancel_inline_keyboard())
        return
    await state.update_data(full_name=full_name)
    await state.set_state(AddCustomerState.phone)
    await message.answer("Telefon raqamini yuboring.\nMasalan: +998901234567", reply_markup=cancel_inline_keyboard())


@router.message(AddCustomerState.phone)
async def add_customer_phone(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return
    phone = (message.text or "").strip().replace(" ", "")
    if len(phone) < 9:
        await message.answer("Telefon raqam to'g'ri emas.", reply_markup=cancel_inline_keyboard())
        return
    existing = await get_customer_by_phone(session, phone)
    if existing:
        await message.answer("Bu raqam allaqachon mavjud.", reply_markup=cancel_inline_keyboard())
        return
    await state.update_data(phone=phone)
    await state.set_state(AddCustomerState.address)
    await message.answer("Manzilni yuboring (yoki '-' qoldiring).", reply_markup=cancel_inline_keyboard())


@router.message(AddCustomerState.address)
async def add_customer_address(message: Message, state: FSMContext):
    if not is_admin(message):
        return
    address = (message.text or "").strip()
    await state.update_data(address=None if address == "-" else address)
    await state.set_state(AddCustomerState.note)
    await message.answer("Izoh yuboring (yoki '-' qoldiring).", reply_markup=cancel_inline_keyboard())


@router.message(AddCustomerState.note)
async def add_customer_note(message: Message, state: FSMContext, session: AsyncSession):
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
        f"Mijoz qo'shildi:\nID: {customer.id}\nIsm: {customer.full_name}\nTelefon: {customer.phone}",
        reply_markup=customers_main_keyboard(),
    )


@router.callback_query(F.data == "admin_customers:list")
async def customers_list(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    customers = await list_customers(session, limit=20)
    if not customers:
        await callback.message.edit_text("Mijozlar yo'q.", reply_markup=customers_main_keyboard())
        await callback.answer()
        return
    lines = ["Mijozlar:\n"]
    for c in customers:
        lines.append(f"ID: {c.id}\n{c.full_name}\nTel: {c.phone}\nHolat: {c.status}\n")
    await callback.message.edit_text("\n".join(lines), reply_markup=customers_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_customers:search")
async def search_customer_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(SearchCustomerState.query)
    await callback.message.edit_text("Qidiruv uchun ism yoki telefon yuboring.", reply_markup=cancel_inline_keyboard())
    await callback.answer()


@router.message(SearchCustomerState.query)
async def search_customer_query(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return
    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("Kamida 2 ta belgi kiriting.", reply_markup=cancel_inline_keyboard())
        return
    customers = await search_customers(session, query, limit=20)
    if not customers:
        await message.answer("Topilmadi.", reply_markup=customers_main_keyboard())
        await state.clear()
        return
    lines = ["Topilganlar:\n"]
    for c in customers:
        lines.append(f"{c.id}. {c.full_name} | {c.phone}")
    await message.answer("\n".join(lines), reply_markup=customers_main_keyboard())
    await state.clear()


@router.callback_query(F.data == "admin_customers:cancel")
async def cancel_customers(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Amal bekor qilindi.", reply_markup=customers_main_keyboard())
    await callback.answer()