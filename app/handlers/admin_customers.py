from math import ceil
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.admin_customers_inline import (
    customers_main_keyboard,
    customers_list_keyboard,
    customer_detail_keyboard,
    confirm_delete_keyboard,
    edit_field_keyboard,
    customer_status_keyboard,
)
from app.keyboards.common_inline import cancel_inline_keyboard
from app.services.customers import (
    create_customer,
    delete_customer_by_id,
    get_customer_by_id,
    get_customer_by_phone,
    list_customers,
    search_customers,
    update_customer_field,
)
from app.states.customer_state import AddCustomerState, SearchCustomerState, EditCustomerState
from app.utils.helpers import is_admin

router = Router()  # <-- BU MUHIM!
ITEMS_PER_PAGE = 10


@router.callback_query(F.data == "admin_menu:customers")
async def customers_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("Mijozlar bo'limi:", reply_markup=customers_main_keyboard())
    await callback.answer()


# ==================== MIJOZ QO'SHISH ====================

@router.callback_query(F.data == "admin_customers:add")
async def add_customer_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AddCustomerState.full_name)
    await callback.message.edit_text(
        "Yangi mijozning ism-familiyasini yuboring.\nMasalan: Ali Valiyev",
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
        f"✅ Mijoz qo'shildi:\nID: {customer.id}\nIsm: {customer.full_name}\nTelefon: {customer.phone}",
        reply_markup=customers_main_keyboard(),
    )


# ==================== MIJOZLAR RO'YXATI ====================

@router.callback_query(F.data == "admin_customers:list")
async def list_customers_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    customers = await list_customers(session, limit=1000)
    if not customers:
        await callback.message.edit_text("Hozircha mijozlar yo'q.", reply_markup=customers_main_keyboard())
        await callback.answer()
        return

    total_pages = ceil(len(customers) / ITEMS_PER_PAGE)
    page = 1
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_customers = customers[start:end]

    await state.update_data(all_customers=customers, current_page=page, total_pages=total_pages)
    await callback.message.edit_text(
        f"📋 Mijozlar ro'yxati (sahifa {page}/{total_pages}):",
        reply_markup=customers_list_keyboard(page_customers, page, total_pages, action="list")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_customers:list_choose:"))
async def view_customer(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    customer_id = int(callback.data.split(":")[2])
    customer = await get_customer_by_id(session, customer_id)
    if not customer:
        await callback.answer("Mijoz topilmadi", show_alert=True)
        return

    await state.update_data(editing_customer_id=customer.id)
    text = (
        f"👤 Mijoz ma'lumotlari:\n\n"
        f"ID: {customer.id}\n"
        f"Ism: {customer.full_name}\n"
        f"Telefon: {customer.phone}\n"
        f"Manzil: {customer.address or '❌ kiritilmagan'}\n"
        f"Izoh: {customer.note or '❌ kiritilmagan'}\n"
        f"Holat: {customer.status}\n"
        f"Telegram ID: {customer.linked_telegram_id or '❌ bog'lanmagan'}"
    )
    await callback.message.edit_text(text, reply_markup=customer_detail_keyboard(customer.id))
    await callback.answer()

    # ==================== MIJOZ TAHRIRLASH ====================

    @ router.callback_query(F.data == "admin_customers:edit")
    async

    def edit_customer_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        if not is_admin(callback):
            await callback.answer("Ruxsat yo'q", show_alert=True)
            return
        customers = await list_customers(session, limit=1000)
        if not customers:
            await callback.message.edit_text("Hozircha mijozlar yo'q.", reply_markup=customers_main_keyboard())
            await callback.answer()
            return

        total_pages = ceil(len(customers) / ITEMS_PER_PAGE)
        page = 1
        start = (page - 1) * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        page_customers = customers[start:end]

        await state.update_data(all_customers=customers, current_page=page, total_pages=total_pages)
        await callback.message.edit_text(
            f"✏️ Tahrirlash uchun mijozni tanlang (sahifa {page}/{total_pages}):",
            reply_markup=customers_list_keyboard(page_customers, page, total_pages, action="edit")
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin_customers:edit_choose:"))
    async def edit_customer_choose(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        if not is_admin(callback):
            await callback.answer("Ruxsat yo'q", show_alert=True)
            return
        customer_id = int(callback.data.split(":")[2])
        customer = await get_customer_by_id(session, customer_id)
        if not customer:
            await callback.answer("Mijoz topilmadi", show_alert=True)
            return

        await state.update_data(editing_customer_id=customer.id)
        text = (
            f"👤 Mijoz ma'lumotlari:\n\n"
            f"ID: {customer.id}\n"
            f"Ism: {customer.full_name}\n"
            f"Telefon: {customer.phone}\n"
            f"Manzil: {customer.address or '❌ kiritilmagan'}\n"
            f"Izoh: {customer.note or '❌ kiritilmagan'}\n"
            f"Holat: {customer.status}\n"
        )
        await callback.message.edit_text(text, reply_markup=customer_detail_keyboard(customer.id))
        await callback.answer()

    @router.callback_query(F.data.startswith("admin_customers:edit_field:"))
    async def edit_customer_field(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        if not is_admin(callback):
            await callback.answer("Ruxsat yo'q", show_alert=True)
            return
        parts = callback.data.split(":")
        customer_id = int(parts[2])
        field = parts[3]

        customer = await get_customer_by_id(session, customer_id)
        if not customer:
            await callback.answer("Mijoz topilmadi", show_alert=True)
            return

        await state.update_data(editing_customer_id=customer.id, editing_field=field)

        field_names = {
            "full_name": "Ism-familiya",
            "phone": "Telefon raqam",
            "address": "Manzil",
            "note": "Izoh",
        }

        if field == "status":
            await callback.message.edit_text(
                f"🏷 Holatni tanlang (hozirgi: {customer.status}):",
                reply_markup=customer_status_keyboard(customer.id, customer.status)
            )
            await callback.answer()
            return

        current_value = getattr(customer, field) or "kiritilmagan"
        await state.set_state(EditCustomerState.waiting_for_value)
        await callback.message.edit_text(
            f"✏️ {field_names.get(field, field)} o'zgartirish:\n\n"
            f"Hozirgi qiymat: {current_value}\n\n"
            f"Yangi qiymatni yuboring:",
            reply_markup=edit_field_keyboard(customer.id, field, current_value)
        )
        await callback.answer()

    @router.message(EditCustomerState.waiting_for_value)
    async def save_edited_field(message: Message, state: FSMContext, session: AsyncSession):
        if not is_admin(message):
            return

        data = await state.get_data()
        customer_id = data.get("editing_customer_id")
        field = data.get("editing_field")

        if not customer_id or not field:
            await state.clear()
            await message.answer("Xatolik yuz berdi.", reply_markup=customers_main_keyboard())
            return

        new_value = (message.text or "").strip()
        if new_value == "-":
            new_value = None

        customer = await update_customer_field(session, customer_id, field, new_value)

        if customer:
            await state.clear()
            text = (
                f"✅ {field} yangilandi!\n\n"
                f"ID: {customer.id}\n"
                f"Ism: {customer.full_name}\n"
                f"Telefon: {customer.phone}\n"
                f"Manzil: {customer.address or '❌ kiritilmagan'}\n"
                f"Izoh: {customer.note or '❌ kiritilmagan'}\n"
                f"Holat: {customer.status}\n"
            )
            await message.answer(text, reply_markup=customer_detail_keyboard(customer.id))
        else:
            await message.answer("Xatolik yuz berdi.", reply_markup=customers_main_keyboard())

    @router.callback_query(F.data.startswith("admin_customers:set_status:"))
    async def set_customer_status(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        if not is_admin(callback):
            await callback.answer("Ruxsat yo'q", show_alert=True)
            return
        parts = callback.data.split(":")
        customer_id = int(parts[2])
        new_status = parts[3]

        customer = await update_customer_field(session, customer_id, "status", new_status)

        if customer:
            text = (
                f"✅ Holat yangilandi!\n\n"
                f"ID: {customer.id}\n"
                f"Ism: {customer.full_name}\n"
                f"Telefon: {customer.phone}\n"
                f"Manzil: {customer.address or '❌ kiritilmagan'}\n"
                f"Izoh: {customer.note or '❌ kiritilmagan'}\n"
                f"Holat: {customer.status}\n"
            )
            await callback.message.edit_text(text, reply_markup=customer_detail_keyboard(customer.id))
        else:
            await callback.message.edit_text("Xatolik yuz berdi.", reply_markup=customers_main_keyboard())
        await callback.answer()

    @router.callback_query(F.data.startswith("admin_customers:edit_field_back:"))
    async def edit_field_back(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        if not is_admin(callback):
            await callback.answer("Ruxsat yo'q", show_alert=True)
            return
        parts = callback.data.split(":")
        customer_id = int(parts[2])
        customer = await get_customer_by_id(session, customer_id)

        if customer:
            text = (
                f"👤 Mijoz ma'lumotlari:\n\n"
                f"ID: {customer.id}\n"
                f"Ism: {customer.full_name}\n"
                f"Telefon: {customer.phone}\n"
                f"Manzil: {customer.address or '❌ kiritilmagan'}\n"
                f"Izoh: {customer.note or '❌ kiritilmagan'}\n"
                f"Holat: {customer.status}\n"
            )
            await callback.message.edit_text(text, reply_markup=customer_detail_keyboard(customer.id))
        else:
            await callback.message.edit_text("Mijoz topilmadi.", reply_markup=customers_main_keyboard())
        await state.clear()
        await callback.answer()

    # ==================== MIJOZ O'CHIRISH ====================

    @router.callback_query(F.data.startswith("admin_customers:delete_confirm:"))
    async def delete_customer_confirm_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        if not is_admin(callback):
            await callback.answer("Ruxsat yo'q", show_alert=True)
            return
        customer_id = int(callback.data.split(":")[2])
        customer = await get_customer_by_id(session, customer_id)
        if not customer:
            await callback.answer("Mijoz topilmadi", show_alert=True)
            return

        await callback.message.edit_text(
            f"⚠️ Mijozni o'chirishga rozimisiz?\n\n"
            f"ID: {customer.id}\n"
            f"Ism: {customer.full_name}\n"
            f"Telefon: {customer.phone}\n\n"
            f"❌ Diqqat! Bu mijozning barcha buyurtmalari ham o'chadi!",
            reply_markup=confirm_delete_keyboard(customer.id, customer.full_name)
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("admin_customers:delete_confirm_yes:"))
    async def delete_customer_final(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        if not is_admin(callback):
            await callback.answer("Ruxsat yo'q", show_alert=True)
            return
        customer_id = int(callback.data.split(":")[2])
        success = await delete_customer_by_id(session, customer_id)

        if success:
            await callback.message.edit_text(
                f"✅ Mijoz muvaffaqiyatli o'chirildi.\nID: {customer_id}",
                reply_markup=customers_main_keyboard()
            )
        else:
            await callback.message.edit_text(
                f"❌ Mijoz o'chirilmadi. Xatolik yuz berdi.",
                reply_markup=customers_main_keyboard()
            )
        await state.clear()
        await callback.answer()

    @router.callback_query(F.data == "admin_customers:delete_cancel")
    async def delete_customer_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
        if not is_admin(callback):
            await callback.answer("Ruxsat yo'q", show_alert=True)
            return

        data = await state.get_data()
        customer_id = data.get("editing_customer_id")

        if customer_id:
            customer = await get_customer_by_id(session, customer_id)
            if customer:
                text = (
                    f"👤 Mijoz ma'lumotlari:\n\n"
                    f"ID: {customer.id}\n"
                    f"Ism: {customer.full_name}\n"
                    f"Telefon: {customer.phone}\n"
                    f"Manzil: {customer.address or '❌ kiritilmagan'}\n"
                    f"Izoh: {customer.note or '❌ kiritilmagan'}\n"
                    f"Holat: {customer.status}\n"
                )
                await callback.message.edit_text(text, reply_markup=customer_detail_keyboard(customer.id))
            else:
                await callback.message.edit_text("Mijozlar bo'limi:", reply_markup=customers_main_keyboard())
        else:
            await callback.message.edit_text("Mijozlar bo'limi:", reply_markup=customers_main_keyboard())

        await state.clear()
        await callback.answer()

    # ==================== MIJOZ QIDIRISH ====================

    @router.callback_query(F.data == "admin_customers:search")
    async def search_customer_start(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback):
            await callback.answer("Ruxsat yo'q", show_alert=True)
            return
        await state.set_state(SearchCustomerState.query)
        await callback.message.edit_text(
            "Qidiruv uchun ism yoki telefon yuboring.",
            reply_markup=cancel_inline_keyboard()
        )
        await callback.answer()

    @router.message(SearchCustomerState.query)
    async def search_customer_query(message: Message, state: FSMContext, session: AsyncSession):
        if not is_admin(message):
            return
        query = (message.text or "").strip()
        if len(query) < 2:
            await message.answer("Kamida 2 ta belgi.", reply_markup=cancel_inline_keyboard())
            return
        customers = await search_customers(session, query, limit=50)
        if not customers:
            await message.answer("Topilmadi.", reply_markup=customers_main_keyboard())
            await state.clear()
            return

        lines = ["🔎 Topilgan mijozlar:\n"]
        for c in customers:
            lines.append(f"ID: {c.id}\n{c.full_name} | {c.phone}\n")
        await message.answer("\n".join(lines), reply_markup=customers_main_keyboard())
        await state.clear()

    # ==================== PAGINATION ====================

    @router.callback_query(F.data.startswith("admin_customers:page:"))
    async def customers_page(callback: CallbackQuery, state: FSMContext):
        if not is_admin(callback):
            await callback.answer("Ruxsat yo'q", show_alert=True)
            return
        parts = callback.data.split(":")
        action = parts[2]
        page = int(parts[3])
        data = await state.get_data()
        all_customers = data.get("all_customers", [])

        if not all_customers:
            await callback.answer("Mijozlar topilmadi", show_alert=True)
            return

        total_pages = data.get("total_pages", 1)
        start = (page - 1) * ITEMS_PER_PAGE
        end = start + ITEMS_PER_PAGE
        page_customers = all_customers[start:end]

        await state.update_data(current_page=page)

        titles = {
            "list": "📋 Mijozlar ro'yxati",
            "edit": "✏️ Tahrirlash uchun mijozni tanlang",
        }
        title = titles.get(action, "Mijozlar")

        await callback.message.edit_text(
            f"{title} (sahifa {page}/{total_pages}):",
            reply_markup=customers_list_keyboard(page_customers, page, total_pages, action=action)
        )
        await callback.answer()

    # ==================== ORQAGA ====================

    @router.callback_query(F.data == "admin_customers:back")
    async def customers_back(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.edit_text("Mijozlar bo'limi:", reply_markup=customers_main_keyboard())
        await callback.answer()

    @router.callback_query(F.data == "admin_customers:edit_back")
    async def edit_back(callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.edit_text("Mijozlar bo'limi:", reply_markup=customers_main_keyboard())
        await callback.answer()