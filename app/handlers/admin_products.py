from decimal import Decimal
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.admin_products_inline import products_main_keyboard, products_back_keyboard
from app.keyboards.common_inline import cancel_inline_keyboard
from app.services.products import (
    add_product_stock,
    archive_product,
    create_product,
    get_product_by_id,
    get_product_by_name,
    list_products,
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


@router.callback_query(F.data == "admin_menu:products")
async def products_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text("Mahsulotlar bo'limi:", reply_markup=products_main_keyboard())
    await callback.answer()


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
        f"Mahsulot qo'shildi:\nID: {product.id}\nNomi: {product.name}\nNarx: {format_number(product.sell_price)} so'm\nQoldiq: {format_number(product.stock_quantity)} {product.unit}",
        reply_markup=products_main_keyboard(),
    )


@router.callback_query(F.data == "admin_products:list")
async def products_list(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    products = await list_products(session, limit=50)
    if not products:
        await callback.message.edit_text("Mahsulotlar yo'q.", reply_markup=products_main_keyboard())
        await callback.answer()
        return
    lines = ["Mahsulotlar:\n"]
    for p in products:
        lines.append(
            f"ID: {p.id}\n{p.name} | {format_number(p.sell_price)} so'm | Qoldiq: {format_number(p.stock_quantity)} {p.unit}\n"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=products_main_keyboard())
    await callback.answer()


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
    lines = ["Topilgan mahsulotlar:\n"]
    for p in products:
        lines.append(f"ID: {p.id}\n{p.name} | {format_number(p.sell_price)} so'm\n")
    await message.answer("\n".join(lines), reply_markup=products_main_keyboard())
    await state.clear()


@router.callback_query(F.data == "admin_products:edit_price")
async def edit_price_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    products = await list_products(session, limit=30)
    if not products:
        await callback.message.edit_text("Mahsulotlar yo'q.", reply_markup=products_main_keyboard())
        await callback.answer()
        return
    lines = ["Narxini o'zgartirish uchun mahsulot ID sini yuboring:\n"]
    for p in products:
        lines.append(f"ID: {p.id} | {p.name} | {format_number(p.sell_price)} so'm")
    await state.set_state(EditProductPriceState.product_id)
    await callback.message.edit_text("\n".join(lines), reply_markup=cancel_inline_keyboard())
    await callback.answer()


@router.message(EditProductPriceState.product_id)
async def edit_price_choose_product(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Iltimos, mahsulot ID raqamini yuboring.", reply_markup=cancel_inline_keyboard())
        return
    product = await get_product_by_id(session, int(text))
    if not product:
        await message.answer("Bunday mahsulot yo'q.", reply_markup=cancel_inline_keyboard())
        return
    await state.update_data(product_id=product.id, product_name=product.name)
    await state.set_state(EditProductPriceState.new_price)
    await message.answer(
        f"Yangi narxni yuboring.\nMahsulot: {product.name}\nHozirgi narx: {format_number(product.sell_price)} so'm",
        reply_markup=cancel_inline_keyboard(),
    )


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
        f"Narx yangilandi:\n{product.name} | {format_number(product.sell_price)} so'm",
        reply_markup=products_main_keyboard(),
    )


@router.callback_query(F.data == "admin_products:add_stock")
async def add_stock_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    products = await list_products(session, limit=30)
    if not products:
        await callback.message.edit_text("Mahsulotlar yo'q.", reply_markup=products_main_keyboard())
        await callback.answer()
        return
    lines = ["Qoldiq qo'shish uchun mahsulot ID sini yuboring:\n"]
    for p in products:
        lines.append(f"ID: {p.id} | {p.name} | Qoldiq: {format_number(p.stock_quantity)} {p.unit}")
    await state.set_state(AddProductStockState.product_id)
    await callback.message.edit_text("\n".join(lines), reply_markup=cancel_inline_keyboard())
    await callback.answer()


@router.message(AddProductStockState.product_id)
async def add_stock_choose_product(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("ID raqamini yuboring.", reply_markup=cancel_inline_keyboard())
        return
    product = await get_product_by_id(session, int(text))
    if not product:
        await message.answer("Mahsulot topilmadi.", reply_markup=cancel_inline_keyboard())
        return
    await state.update_data(product_id=product.id, product_name=product.name)
    await state.set_state(AddProductStockState.add_quantity)
    await message.answer(
        f"Qo'shiladigan miqdorni yuboring:\n{product.name}\nHozirgi qoldiq: {format_number(product.stock_quantity)} {product.unit}",
        reply_markup=cancel_inline_keyboard(),
    )


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
        f"Qoldiq qo'shildi:\n{product.name}\nYangi qoldiq: {format_number(product.stock_quantity)} {product.unit}",
        reply_markup=products_main_keyboard(),
    )


@router.callback_query(F.data == "admin_products:archive")
async def archive_product_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    products = await list_products(session, limit=30)
    if not products:
        await callback.message.edit_text("Mahsulotlar yo'q.", reply_markup=products_main_keyboard())
        await callback.answer()
        return
    lines = ["Arxivlash uchun mahsulot ID sini yuboring:\n"]
    for p in products:
        lines.append(f"ID: {p.id} | {p.name} | {'Faol' if p.is_active else 'Arxiv'}")
    await state.set_state(ArchiveProductState.product_id)
    await callback.message.edit_text("\n".join(lines), reply_markup=cancel_inline_keyboard())
    await callback.answer()


@router.message(ArchiveProductState.product_id)
async def archive_product_choose(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("ID raqamini yuboring.", reply_markup=cancel_inline_keyboard())
        return
    product = await get_product_by_id(session, int(text))
    if not product:
        await message.answer("Mahsulot topilmadi.", reply_markup=cancel_inline_keyboard())
        return
    await state.update_data(product_id=product.id, product_name=product.name)
    await state.set_state(ArchiveProductState.confirm)
    await message.answer(
        f"Mahsulotni arxivlaysizmi?\n{product.name}\n\nHa yoki Yo'q?",
        reply_markup=cancel_inline_keyboard(),
    )


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
    await message.answer(f"Mahsulot arxivlandi: {product.name}", reply_markup=products_main_keyboard())


@router.callback_query(F.data == "admin_products:edit")
async def edit_product_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    products = await list_products(session, limit=30)
    if not products:
        await callback.message.edit_text("Mahsulotlar yo'q.", reply_markup=products_main_keyboard())
        await callback.answer()
        return
    lines = ["Tahrirlash uchun mahsulot ID sini yuboring:\n"]
    for p in products:
        lines.append(f"ID: {p.id} | {p.name} | {format_number(p.sell_price)} so'm")
    await state.set_state(EditProductState.product_id)
    await callback.message.edit_text("\n".join(lines), reply_markup=cancel_inline_keyboard())
    await callback.answer()


@router.message(EditProductState.product_id)
async def edit_product_choose_product(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return
    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("ID raqamini yuboring.", reply_markup=cancel_inline_keyboard())
        return
    product = await get_product_by_id(session, int(text))
    if not product:
        await message.answer("Mahsulot topilmadi.", reply_markup=cancel_inline_keyboard())
        return
    await state.update_data(product_id=product.id)
    await state.set_state(EditProductState.field)
    await message.answer(
        f"Mahsulot: {product.name}\n\nQaysi maydonni o'zgartirmoqchisiz?\n"
        "nomi | toifa | birlik | narx | tannarx | qoldiq\n\n"
        "Shu so'zlardan birini yozing.",
        reply_markup=cancel_inline_keyboard(),
    )


@router.message(EditProductState.field)
async def edit_product_choose_field(message: Message, state: FSMContext):
    field_raw = (message.text or "").strip().lower()
    mapping = {
        "nomi": "name", "toifa": "category", "birlik": "unit",
        "narx": "sell_price", "tannarx": "cost_price", "qoldiq": "stock_quantity"
    }
    field = mapping.get(field_raw)
    if not field:
        await message.answer("Noto'g'ri maydon. variantlar: nomi, toifa, birlik, narx, tannarx, qoldiq", reply_markup=cancel_inline_keyboard())
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
            f"Mahsulot yangilandi:\n{product.name} | {format_number(product.sell_price)} so'm | Qoldiq: {format_number(product.stock_quantity)} {product.unit}",
            reply_markup=products_main_keyboard(),
        )
    except Exception as e:
        await message.answer(f"Xatolik: {e}", reply_markup=cancel_inline_keyboard())


@router.callback_query(F.data == "admin_products:back")
async def products_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Mahsulotlar bo'limi:", reply_markup=products_main_keyboard())
    await callback.answer()