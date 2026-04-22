from decimal import Decimal
from math import ceil
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.admin_products_inline import (
    products_main_keyboard,
    products_categories_keyboard,
    products_list_keyboard,
    product_back_keyboard,
)
from app.keyboards.common_inline import cancel_inline_keyboard
from app.services.products import (
    add_product_stock,
    archive_product,
    create_product,
    get_product_by_id,
    get_product_by_name,
    list_active_categories,
    list_products,
    list_products_by_category,
    search_products,
    update_product_fields,
    update_product_price,
)
from app.states.product_manage_state import (
    AddProductStockState,
    ArchiveProductState,
    EditProductPriceState,
    EditProductState,
)
from app.states.product_state import AddProductState, SearchProductState
from app.utils.helpers import is_admin, parse_decimal, format_number

router = Router()
ITEMS_PER_PAGE = 10


@router.callback_query(F.data == "admin_menu:products")
async def products_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("Mahsulotlar bo'limi:", reply_markup=products_main_keyboard())
    await callback.answer()


# ==================== KATEGORIYALAR (UMUMIY) ====================

async def show_categories_for_action(callback: CallbackQuery, state: FSMContext, session: AsyncSession, action: str):
    """Har bir action uchun kategoriyalarni ko'rsatish"""
    categories = await list_active_categories(session)
    if not categories:
        await callback.message.edit_text("Hech qanday kategoriya mavjud emas.",
                                         reply_markup=product_back_keyboard(action))
        await callback.answer()
        return

    await state.update_data(categories=categories, cat_page=1, current_action=action)
    total_pages = ceil(len(categories) / 8)
    await callback.message.edit_text(
        f"📂 Kategoriyalar ({action} uchun):",
        reply_markup=products_categories_keyboard(categories, page=1, total_pages=total_pages, action=action)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_products:cat_page:"))
async def categories_page(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    parts = callback.data.split(":")
    action = parts[2]
    page = int(parts[3])
    data = await state.get_data()
    categories = data.get("categories", [])
    if not categories:
        categories = await list_active_categories(session)
    total_pages = ceil(len(categories) / 8)
    await callback.message.edit_text(
        f"📂 Kategoriyalar ({action} uchun):",
        reply_markup=products_categories_keyboard(categories, page=page, total_pages=total_pages, action=action)
    )
    await callback.answer()


# ==================== KATEGORIYALAR (LIST) ====================

@router.callback_query(F.data == "admin_products:categories")
async def show_categories(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "list")


@router.callback_query(F.data.startswith("admin_products:list_category:"))
async def show_products_by_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    category = callback.data.split(":", 2)[2]
    products = await list_products_by_category(session, category, limit=1000, only_active=False)
    if not products:
        await callback.message.edit_text(f"'{category}' kategoriyasida mahsulot yo'q.",
                                         reply_markup=product_back_keyboard("list"))
        await callback.answer()
        return

    total_pages = ceil(len(products) / ITEMS_PER_PAGE)
    page = 1
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_products = products[start:end]

    await state.update_data(current_category=category, all_products=products, current_page=page,
                            total_pages=total_pages, current_action="list")
    await callback.message.edit_text(
        f"📂 {category} (sahifa {page}/{total_pages}):",
        reply_markup=products_list_keyboard(page_products, page, total_pages, category=category, action="list")
    )
    await callback.answer()


# ==================== TAHRIRLASH (EDIT) ====================

@router.callback_query(F.data == "admin_products:edit")
async def edit_product_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "edit")


@router.callback_query(F.data.startswith("admin_products:edit_category:"))
async def edit_products_by_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    category = callback.data.split(":", 2)[2]
    products = await list_products_by_category(session, category, limit=1000, only_active=False)
    if not products:
        await callback.message.edit_text(f"'{category}' kategoriyasida mahsulot yo'q.",
                                         reply_markup=product_back_keyboard("edit"))
        await callback.answer()
        return

    total_pages = ceil(len(products) / ITEMS_PER_PAGE)
    page = 1
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_products = products[start:end]

    await state.update_data(current_category=category, all_products=products, current_page=page,
                            total_pages=total_pages, current_action="edit")
    await callback.message.edit_text(
        f"✏️ Tahrirlash: {category} (sahifa {page}/{total_pages}):",
        reply_markup=products_list_keyboard(page_products, page, total_pages, category=category, action="edit")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_products:edit_back_categories")
async def edit_back_categories(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "edit")


@router.callback_query(F.data == "admin_products:edit_back")
async def edit_back(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "edit")


# ==================== QOLDIQ QO'SHISH (ADD STOCK) ====================

@router.callback_query(F.data == "admin_products:add_stock")
async def add_stock_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "add_stock")


@router.callback_query(F.data.startswith("admin_products:add_stock_category:"))
async def add_stock_products_by_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    category = callback.data.split(":", 2)[2]
    products = await list_products_by_category(session, category, limit=1000, only_active=False)
    if not products:
        await callback.message.edit_text(f"'{category}' kategoriyasida mahsulot yo'q.",
                                         reply_markup=product_back_keyboard("add_stock"))
        await callback.answer()
        return

    total_pages = ceil(len(products) / ITEMS_PER_PAGE)
    page = 1
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_products = products[start:end]

    await state.update_data(current_category=category, all_products=products, current_page=page,
                            total_pages=total_pages, current_action="add_stock")
    await callback.message.edit_text(
        f"📥 Qoldiq qo'shish: {category} (sahifa {page}/{total_pages}):",
        reply_markup=products_list_keyboard(page_products, page, total_pages, category=category, action="add_stock")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_products:add_stock_back_categories")
async def add_stock_back_categories(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "add_stock")


@router.callback_query(F.data == "admin_products:add_stock_back")
async def add_stock_back(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "add_stock")


# ==================== ARXIVLASH (ARCHIVE) ====================

@router.callback_query(F.data == "admin_products:archive")
async def archive_product_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "archive")


@router.callback_query(F.data.startswith("admin_products:archive_category:"))
async def archive_products_by_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    category = callback.data.split(":", 2)[2]
    products = await list_products_by_category(session, category, limit=1000, only_active=False)
    if not products:
        await callback.message.edit_text(f"'{category}' kategoriyasida mahsulot yo'q.",
                                         reply_markup=product_back_keyboard("archive"))
        await callback.answer()
        return

    total_pages = ceil(len(products) / ITEMS_PER_PAGE)
    page = 1
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_products = products[start:end]

    await state.update_data(current_category=category, all_products=products, current_page=page,
                            total_pages=total_pages, current_action="archive")
    await callback.message.edit_text(
        f"🗃 Arxivlash: {category} (sahifa {page}/{total_pages}):",
        reply_markup=products_list_keyboard(page_products, page, total_pages, category=category, action="archive")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_products:archive_back_categories")
async def archive_back_categories(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "archive")


@router.callback_query(F.data == "admin_products:archive_back")
async def archive_back(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "archive")


# ==================== NARX (EDIT PRICE) ====================

@router.callback_query(F.data == "admin_products:edit_price")
async def edit_price_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "edit_price")


@router.callback_query(F.data.startswith("admin_products:edit_price_category:"))
async def edit_price_products_by_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    category = callback.data.split(":", 2)[2]
    products = await list_products_by_category(session, category, limit=1000, only_active=False)
    if not products:
        await callback.message.edit_text(f"'{category}' kategoriyasida mahsulot yo'q.",
                                         reply_markup=product_back_keyboard("edit_price"))
        await callback.answer()
        return

    total_pages = ceil(len(products) / ITEMS_PER_PAGE)
    page = 1
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_products = products[start:end]

    await state.update_data(current_category=category, all_products=products, current_page=page,
                            total_pages=total_pages, current_action="edit_price")
    await callback.message.edit_text(
        f"💰 Narx o'zgartirish: {category} (sahifa {page}/{total_pages}):",
        reply_markup=products_list_keyboard(page_products, page, total_pages, category=category, action="edit_price")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_products:edit_price_back_categories")
async def edit_price_back_categories(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "edit_price")


@router.callback_query(F.data == "admin_products:edit_price_back")
async def edit_price_back(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "edit_price")


# ==================== PAGINATION (UMUMIY) ====================

@router.callback_query(F.data.startswith("admin_products:page:"))
async def products_page(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    parts = callback.data.split(":")
    action = parts[2]
    page = int(parts[3])
    data = await state.get_data()
    all_products = data.get("all_products", [])
    category = data.get("current_category")

    if not all_products:
        await callback.answer("Mahsulotlar topilmadi", show_alert=True)
        return

    total_pages = ceil(len(all_products) / ITEMS_PER_PAGE)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_products = all_products[start:end]

    await state.update_data(current_page=page)
    await callback.message.edit_text(
        f"{'📂 ' + category if category else '📋 Mahsulotlar'} (sahifa {page}/{total_pages}):",
        reply_markup=products_list_keyboard(page_products, page, total_pages, category=category, action=action)
    )
    await callback.answer()


# ==================== BARCHA MAHSULOTLAR ====================

@router.callback_query(F.data == "admin_products:list_all")
async def list_all_products(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    products = await list_products(session, limit=1000)
    if not products:
        await callback.message.edit_text("Mahsulotlar yo'q.", reply_markup=products_main_keyboard())
        await callback.answer()
        return

    total_pages = ceil(len(products) / ITEMS_PER_PAGE)
    page = 1
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_products = products[start:end]

    await state.update_data(all_products=products, current_category=None, current_page=page, total_pages=total_pages,
                            current_action="list")
    await callback.message.edit_text(
        f"📋 Barcha mahsulotlar (sahifa {page}/{total_pages}):",
        reply_markup=products_list_keyboard(page_products, page, total_pages, category=None, action="list")
    )
    await callback.answer()


# ==================== MAHSULOTNI KO'RISH ====================

@router.callback_query(F.data.startswith("admin_products:view:"))
async def view_product(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    product_id = int(callback.data.split(":")[2])
    product = await get_product_by_id(session, product_id)
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return

    holat = "Faol" if product.is_active else "Arxiv"
    tannarx = f"{format_number(product.cost_price)} so'm" if product.cost_price else "kiritilmagan"
    text = (
        f"📦 Mahsulot ma'lumoti:\n\n"
        f"ID: {product.id}\n"
        f"Nomi: {product.name}\n"
        f"Toifa: {product.category or 'kiritilmagan'}\n"
        f"Birlik: {product.unit}\n"
        f"Sotuv narxi: {format_number(product.sell_price)} so'm\n"
        f"Tannarx: {tannarx}\n"
        f"Qoldiq: {format_number(product.stock_quantity)} {product.unit}\n"
        f"Holat: {holat}"
    )
    await callback.message.edit_text(text, reply_markup=product_back_keyboard())
    await callback.answer()


# ==================== QO'SHISH ====================

@router.callback_query(F.data == "admin_products:add")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AddProductState.name)
    await callback.message.edit_text(
        "Yangi mahsulot nomini yuboring.\nMasalan: Sellofan Paket 40x60",
        reply_markup=cancel_inline_keyboard(),
    )
    await callback.answer()


@router.message(AddProductState.name)
async def add_product_name(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Nomi juda qisqa.", reply_markup=cancel_inline_keyboard())
        return
    existing = await get_product_by_name(session, name)
    if existing:
        await message.answer("Bu nom bilan mahsulot mavjud.", reply_markup=cancel_inline_keyboard())
        return
    await state.update_data(name=name)
    await state.set_state(AddProductState.category)
    await message.answer("Toifani yuboring (yoki '-' qoldiring).", reply_markup=cancel_inline_keyboard())


@router.message(AddProductState.category)
async def add_product_category(message: Message, state: FSMContext):
    category = (message.text or "").strip()
    await state.update_data(category=None if category == "-" else category)
    await state.set_state(AddProductState.unit)
    await message.answer("O'lchov birligini yuboring (masalan: dona, kg).", reply_markup=cancel_inline_keyboard())


@router.message(AddProductState.unit)
async def add_product_unit(message: Message, state: FSMContext):
    unit = (message.text or "").strip()
    if not unit:
        await message.answer("Birlikni kiriting.", reply_markup=cancel_inline_keyboard())
        return
    await state.update_data(unit=unit)
    await state.set_state(AddProductState.sell_price)
    await message.answer("Sotuv narxini kiriting (masalan: 25000).", reply_markup=cancel_inline_keyboard())


@router.message(AddProductState.sell_price)
async def add_product_sell_price(message: Message, state: FSMContext):
    price = parse_decimal(message.text or "")
    if price is None:
        await message.answer("Narx noto'g'ri.", reply_markup=cancel_inline_keyboard())
        return
    await state.update_data(sell_price=str(price))
    await state.set_state(AddProductState.cost_price)
    await message.answer("Tannarxni kiriting (yoki '-' qoldiring).", reply_markup=cancel_inline_keyboard())


@router.message(AddProductState.cost_price)
async def add_product_cost_price(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if text == "-":
        await state.update_data(cost_price=None)
    else:
        price = parse_decimal(text)
        if price is None:
            await message.answer("Noto'g'ri qiymat.", reply_markup=cancel_inline_keyboard())
            return
        await state.update_data(cost_price=str(price))
    await state.set_state(AddProductState.stock_quantity)
    await message.answer("Boshlang'ich qoldiqni kiriting (son).", reply_markup=cancel_inline_keyboard())


@router.message(AddProductState.stock_quantity)
async def add_product_stock_quantity(message: Message, state: FSMContext, session: AsyncSession):
    qty = parse_decimal(message.text or "")
    if qty is None:
        await message.answer("Noto'g'ri son.", reply_markup=cancel_inline_keyboard())
        return
    data = await state.get_data()
    product = await create_product(
        session=session,
        name=data["name"],
        category=data.get("category"),
        unit=data["unit"],
        sell_price=Decimal(data["sell_price"]),
        cost_price=Decimal(data["cost_price"]) if data.get("cost_price") else None,
        stock_quantity=qty,
    )
    await state.clear()
    await message.answer(
        f"✅ Mahsulot qo'shildi:\nID: {product.id}\nNomi: {product.name}\nNarx: {format_number(product.sell_price)} so'm\nQoldiq: {format_number(product.stock_quantity)} {product.unit}",
        reply_markup=products_main_keyboard(),
    )


# ==================== QIDIRISH ====================

@router.callback_query(F.data == "admin_products:search")
async def search_product_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(SearchProductState.query)
    await callback.message.edit_text("Qidiruv uchun mahsulot nomini yuboring.", reply_markup=cancel_inline_keyboard())
    await callback.answer()


@router.message(SearchProductState.query)
async def search_product_handler(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return
    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("Kamida 2 ta belgi.", reply_markup=cancel_inline_keyboard())
        return
    products = await search_products(session, query)
    if not products:
        await message.answer("Topilmadi.", reply_markup=products_main_keyboard())
        await state.clear()
        return

    total_pages = ceil(len(products) / ITEMS_PER_PAGE)
    page = 1
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    page_products = products[start:end]

    await state.update_data(all_products=products, current_category=None, current_page=page, total_pages=total_pages,
                            current_action="list")
    await message.answer(
        f"🔎 Qidiruv natijalari: '{query}' (sahifa {page}/{total_pages}):",
        reply_markup=products_list_keyboard(page_products, page, total_pages, category=None, action="list")
    )
    await state.clear()


# ==================== NARX (EDIT PRICE) – TANLASH ====================

@router.callback_query(F.data.startswith("admin_products:edit_price_choose:"))
async def edit_price_choose_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    product_id = int(callback.data.split(":")[2])
    product = await get_product_by_id(session, product_id)
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    await state.update_data(product_id=product.id, product_name=product.name)
    await state.set_state(EditProductPriceState.new_price)
    await callback.message.edit_text(
        f"Yangi narxni yuboring.\nMahsulot: {product.name}\nHozirgi narx: {format_number(product.sell_price)} so'm",
        reply_markup=cancel_inline_keyboard(),
    )
    await callback.answer()


@router.message(EditProductPriceState.new_price)
async def edit_price_save(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return
    new_price = parse_decimal(message.text or "")
    if new_price is None:
        await message.answer("Narx noto'g'ri.", reply_markup=cancel_inline_keyboard())
        return
    data = await state.get_data()
    product = await get_product_by_id(session, int(data["product_id"]))
    if not product:
        await state.clear()
        await message.answer("Mahsulot topilmadi.", reply_markup=products_main_keyboard())
        return
    product = await update_product_price(session, product, new_price)
    await state.clear()
    await message.answer(
        f"✅ Narx yangilandi:\n{product.name} | {format_number(product.sell_price)} so'm",
        reply_markup=products_main_keyboard(),
    )


# ==================== QOLDIQ QO'SHISH – TANLASH ====================

@router.callback_query(F.data.startswith("admin_products:add_stock_choose:"))
async def add_stock_choose_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    product_id = int(callback.data.split(":")[2])
    product = await get_product_by_id(session, product_id)
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    await state.update_data(product_id=product.id, product_name=product.name)
    await state.set_state(AddProductStockState.add_quantity)
    await callback.message.edit_text(
        f"Qo'shiladigan miqdorni yuboring:\n{product.name}\nHozirgi qoldiq: {format_number(product.stock_quantity)} {product.unit}",
        reply_markup=cancel_inline_keyboard(),
    )
    await callback.answer()


@router.message(AddProductStockState.add_quantity)
async def add_stock_save(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return
    add_qty = parse_decimal(message.text or "")
    if add_qty is None:
        await message.answer("Miqdor noto'g'ri.", reply_markup=cancel_inline_keyboard())
        return
    data = await state.get_data()
    product = await get_product_by_id(session, int(data["product_id"]))
    if not product:
        await state.clear()
        await message.answer("Mahsulot topilmadi.", reply_markup=products_main_keyboard())
        return
    product = await add_product_stock(session, product, add_qty)
    await state.clear()
    await message.answer(
        f"✅ Qoldiq qo'shildi:\n{product.name}\nYangi qoldiq: {format_number(product.stock_quantity)} {product.unit}",
        reply_markup=products_main_keyboard(),
    )


# ==================== ARXIVLASH – TANLASH ====================

@router.callback_query(F.data.startswith("admin_products:archive_choose:"))
async def archive_product_choose(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    product_id = int(callback.data.split(":")[2])
    product = await get_product_by_id(session, product_id)
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    await state.update_data(product_id=product.id, product_name=product.name)
    await state.set_state(ArchiveProductState.confirm)
    await callback.message.edit_text(
        f"Mahsulotni arxivlaysizmi?\n{product.name}\n\nHa yoki Yo'q?",
        reply_markup=cancel_inline_keyboard(),
    )
    await callback.answer()


@router.message(ArchiveProductState.confirm)
async def archive_product_confirm(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return
    answer = (message.text or "").strip().lower()
    if answer not in {"ha", "yo'q", "yoq"}:
        await message.answer("Ha yoki yo'q deb yozing.", reply_markup=cancel_inline_keyboard())
        return
    if answer in {"yo'q", "yoq"}:
        await state.clear()
        await message.answer("Arxivlash bekor qilindi.", reply_markup=products_main_keyboard())
        return
    data = await state.get_data()
    product = await get_product_by_id(session, int(data["product_id"]))
    if not product:
        await state.clear()
        await message.answer("Mahsulot topilmadi.", reply_markup=products_main_keyboard())
        return
    product = await archive_product(session, product)
    await state.clear()
    await message.answer(f"✅ Mahsulot arxivlandi: {product.name}", reply_markup=products_main_keyboard())


# ==================== TAHRIRLASH – TANLASH ====================

@router.callback_query(F.data.startswith("admin_products:edit_choose:"))
async def edit_product_choose(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    product_id = int(callback.data.split(":")[2])
    product = await get_product_by_id(session, product_id)
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    await state.update_data(product_id=product.id)
    await state.set_state(EditProductState.field)
    await callback.message.edit_text(
        f"Mahsulot: {product.name}\n\nQaysi maydonni o'zgartirmoqchisiz?\n"
        "nomi | toifa | birlik | narx | tannarx | qoldiq\n\n"
        "Shu so'zlardan birini yozing.",
        reply_markup=cancel_inline_keyboard(),
    )
    await callback.answer()


@router.message(EditProductState.field)
async def edit_product_choose_field(message: Message, state: FSMContext):
    field_raw = (message.text or "").strip().lower()
    mapping = {
        "nomi": "name", "toifa": "category", "birlik": "unit",
        "narx": "sell_price", "tannarx": "cost_price", "qoldiq": "stock_quantity"
    }
    field = mapping.get(field_raw)
    if not field:
        await message.answer("Noto'g'ri maydon. variantlar: nomi, toifa, birlik, narx, tannarx, qoldiq",
                             reply_markup=cancel_inline_keyboard())
        return
    await state.update_data(edit_field=field)
    await state.set_state(EditProductState.value)
    prompts = {
        "name": "Yangi nomni yuboring.",
        "category": "Yangi toifa (yoki '-'):",
        "unit": "Yangi birlik:",
        "sell_price": "Yangi narx:",
        "cost_price": "Yangi tannarx (yoki '-'):",
        "stock_quantity": "Yangi qoldiq:",
    }
    await message.answer(prompts[field], reply_markup=cancel_inline_keyboard())


@router.message(EditProductState.value)
async def edit_product_save(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return
    data = await state.get_data()
    product = await get_product_by_id(session, int(data["product_id"]))
    if not product:
        await state.clear()
        await message.answer("Mahsulot topilmadi.", reply_markup=products_main_keyboard())
        return
    field = data["edit_field"]
    raw_value = (message.text or "").strip()
    try:
        if field == "name":
            if len(raw_value) < 2:
                await message.answer("Nomi juda qisqa.", reply_markup=cancel_inline_keyboard())
                return
            existing = await get_product_by_name(session, raw_value)
            if existing and existing.id != product.id:
                await message.answer("Bu nom band.", reply_markup=cancel_inline_keyboard())
                return
            product = await update_product_fields(session, product, name=raw_value)
        elif field == "category":
            category = None if raw_value == "-" else raw_value
            product = await update_product_fields(session, product, category=category if category else "")
        elif field == "unit":
            product = await update_product_fields(session, product, unit=raw_value)
        elif field == "sell_price":
            price = parse_decimal(raw_value)
            if not price:
                await message.answer("Narx noto'g'ri.", reply_markup=cancel_inline_keyboard())
                return
            product = await update_product_fields(session, product, sell_price=price)
        elif field == "cost_price":
            if raw_value == "-":
                product.cost_price = None
                await session.commit()
            else:
                price = parse_decimal(raw_value)
                if not price:
                    await message.answer("Tannarx noto'g'ri.", reply_markup=cancel_inline_keyboard())
                    return
                product = await update_product_fields(session, product, cost_price=price)
        elif field == "stock_quantity":
            qty = parse_decimal(raw_value)
            if qty is None:
                await message.answer("Qoldiq noto'g'ri.", reply_markup=cancel_inline_keyboard())
                return
            product = await update_product_fields(session, product, stock_quantity=qty)
        await state.clear()
        await message.answer(
            f"✅ Mahsulot yangilandi:\n{product.name} | {format_number(product.sell_price)} so'm | Qoldiq: {format_number(product.stock_quantity)} {product.unit}",
            reply_markup=products_main_keyboard(),
        )
    except Exception as e:
        await message.answer(f"Xatolik: {e}", reply_markup=cancel_inline_keyboard())


# ==================== ORQAGA (BACK) – UMUMIY ====================

@router.callback_query(F.data == "admin_products:back")
async def products_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Mahsulotlar bo'limi:", reply_markup=products_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_products:list_back")
async def list_back(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "list")

@router.callback_query(F.data == "admin_products:back_to_categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_categories_for_action(callback, state, session, "list")