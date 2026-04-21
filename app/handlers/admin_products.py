from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.reply import (
    cancel_keyboard,
    products_menu_keyboard,
)
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

router = Router()


def is_admin(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in settings.admin_ids)


def parse_decimal(value: str) -> Decimal | None:
    cleaned = value.strip().replace(" ", "").replace(",", ".")
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        return None

    if number < 0:
        return None
    return number


def format_number(value: Decimal | float | int | str | None) -> str:
    if value is None:
        return "kiritilmagan"

    if isinstance(value, Decimal):
        normalized = value.normalize()
        text = format(normalized, "f")
    else:
        text = f"{value}"

    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def build_product_lines(products: list) -> str:
    lines = ["Mahsulotlar:\n"]
    for p in products:
        holat = "Faol" if p.is_active else "Arxiv"
        lines.append(
            f"ID: {p.id}\n"
            f"Nomi: {p.name}\n"
            f"Toifa: {p.category or 'kiritilmagan'}\n"
            f"Narx: {format_number(p.sell_price)} so'm\n"
            f"Tannarx: {format_number(p.cost_price)}"
            + ("" if p.cost_price is None else " so'm")
            + "\n"
            f"Qoldiq: {format_number(p.stock_quantity)} {p.unit}\n"
            f"Holat: {holat}\n"
        )
    return "\n".join(lines)


def build_single_product_text(product) -> str:
    holat = "Faol" if product.is_active else "Arxiv"
    tannarx = (
        f"{format_number(product.cost_price)} so'm"
        if product.cost_price is not None
        else "kiritilmagan"
    )
    return (
        f"Mahsulot ma'lumoti:\n\n"
        f"ID: {product.id}\n"
        f"Nomi: {product.name}\n"
        f"Toifa: {product.category or 'kiritilmagan'}\n"
        f"O'lchov birligi: {product.unit}\n"
        f"Sotuv narxi: {format_number(product.sell_price)} so'm\n"
        f"Tannarx: {tannarx}\n"
        f"Qoldiq: {format_number(product.stock_quantity)} {product.unit}\n"
        f"Holat: {holat}"
    )


@router.message(F.text == "📦 Mahsulotlar")
async def products_menu(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    await state.clear()
    await message.answer(
        "Mahsulotlar bo'limi.",
        reply_markup=products_menu_keyboard(),
    )


@router.message(F.text == "➕ Mahsulot qo'shish")
async def add_product_start(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    await state.set_state(AddProductState.name)
    await message.answer(
        "Yangi mahsulot nomini yuboring.\n\n"
        "Masalan: Sellofan Paket 40x60",
        reply_markup=cancel_keyboard(),
    )


@router.message(F.text == "❌ Bekor qilish")
async def cancel_any_product_state(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    await state.clear()
    await message.answer(
        "Amal bekor qilindi.",
        reply_markup=products_menu_keyboard(),
    )


@router.message(AddProductState.name)
async def add_product_name(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not is_admin(message):
        return

    name = (message.text or "").strip()

    if len(name) < 2:
        await message.answer("Mahsulot nomini to'g'ri kiriting.")
        return

    existing = await get_product_by_name(session, name)
    if existing:
        await message.answer(
            "Bu nom bilan mahsulot allaqachon mavjud.\n"
            "Boshqa nom kiriting."
        )
        return

    await state.update_data(name=name)
    await state.set_state(AddProductState.category)
    await message.answer("Toifani yuboring yoki '-' yuboring.")


@router.message(AddProductState.category)
async def add_product_category(message: Message, state: FSMContext):
    category = (message.text or "").strip()
    await state.update_data(category=None if category == "-" else category)

    await state.set_state(AddProductState.unit)
    await message.answer("O'lchov birligini yuboring (masalan: dona)")


@router.message(AddProductState.unit)
async def add_product_unit(message: Message, state: FSMContext):
    unit = (message.text or "").strip()

    await state.update_data(unit=unit)
    await state.set_state(AddProductState.sell_price)

    await message.answer("Sotuv narxini kiriting (masalan: 25000)")


@router.message(AddProductState.sell_price)
async def add_product_sell_price(message: Message, state: FSMContext):
    price = parse_decimal(message.text or "")

    if price is None:
        await message.answer("Narx noto'g'ri.")
        return

    await state.update_data(sell_price=str(price))
    await state.set_state(AddProductState.cost_price)

    await message.answer("Tannarx (yoki '-')")


@router.message(AddProductState.cost_price)
async def add_product_cost_price(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if text == "-":
        await state.update_data(cost_price=None)
    else:
        price = parse_decimal(text)
        if price is None:
            await message.answer("Noto'g'ri qiymat.")
            return
        await state.update_data(cost_price=str(price))

    await state.set_state(AddProductState.stock_quantity)
    await message.answer("Boshlang'ich qoldiqni kiriting")


@router.message(AddProductState.stock_quantity)
async def add_product_stock_quantity(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    qty = parse_decimal(message.text or "")

    if qty is None:
        await message.answer("Noto'g'ri son.")
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

    tannarx_text = (
        f"{format_number(product.cost_price)} so'm"
        if product.cost_price is not None
        else "kiritilmagan"
    )

    await message.answer(
        "Mahsulot qo'shildi\n\n"
        f"ID: {product.id}\n"
        f"Nomi: {product.name}\n"
        f"Narx: {format_number(product.sell_price)} so'm\n"
        f"Tannarx: {tannarx_text}\n"
        f"Qoldiq: {format_number(product.stock_quantity)} {product.unit}",
        reply_markup=products_menu_keyboard(),
    )


@router.message(F.text == "📋 Mahsulotlar ro'yxati")
async def products_list(message: Message, session: AsyncSession):
    if not is_admin(message):
        return

    products = await list_products(session, limit=50)

    if not products:
        await message.answer("Mahsulotlar yo'q", reply_markup=products_menu_keyboard())
        return

    await message.answer(
        build_product_lines(products),
        reply_markup=products_menu_keyboard(),
    )


@router.message(F.text == "🔎 Mahsulot qidirish")
async def search_product_start(message: Message, state: FSMContext):
    if not is_admin(message):
        return

    await state.set_state(SearchProductState.query)
    await message.answer(
        "Qidiruv uchun nom yuboring",
        reply_markup=cancel_keyboard(),
    )


@router.message(SearchProductState.query)
async def search_product_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    if not is_admin(message):
        return

    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("Qidiruv uchun kamida 2 ta belgi kiriting.")
        return

    products = await search_products(session, query)

    if not products:
        await message.answer("Topilmadi", reply_markup=products_menu_keyboard())
        await state.clear()
        return

    await message.answer(
        build_product_lines(products),
        reply_markup=products_menu_keyboard(),
    )
    await state.clear()


@router.message(F.text == "✏️ Mahsulotni tahrirlash")
async def edit_product_start(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return

    products = await list_products(session, limit=30)
    if not products:
        await message.answer("Mahsulotlar yo'q.")
        return

    await state.set_state(EditProductState.product_id)
    await message.answer(
        build_product_lines(products)
        + "\nTahrirlash uchun mahsulot ID raqamini yuboring.",
        reply_markup=cancel_keyboard(),
    )


@router.message(EditProductState.product_id)
async def edit_product_choose_product(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    if not is_admin(message):
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Iltimos, mahsulot ID raqamini yuboring.")
        return

    product = await get_product_by_id(session, int(text))
    if product is None:
        await message.answer("Bunday mahsulot topilmadi.")
        return

    await state.update_data(product_id=product.id)
    await state.set_state(EditProductState.field)
    await message.answer(
        build_single_product_text(product)
        + "\n\nQaysi maydonni o'zgartirmoqchisiz?\n"
        "Variantlar:\n"
        "1. nomi\n"
        "2. toifa\n"
        "3. birlik\n"
        "4. narx\n"
        "5. tannarx\n"
        "6. qoldiq"
    )


@router.message(EditProductState.field)
async def edit_product_choose_field(message: Message, state: FSMContext):
    if not is_admin(message):
        return

    field_raw = (message.text or "").strip().lower()
    mapping = {
        "1": "name",
        "nomi": "name",
        "2": "category",
        "toifa": "category",
        "3": "unit",
        "birlik": "unit",
        "o'lchov": "unit",
        "4": "sell_price",
        "narx": "sell_price",
        "5": "cost_price",
        "tannarx": "cost_price",
        "6": "stock_quantity",
        "qoldiq": "stock_quantity",
    }
    field = mapping.get(field_raw)

    if field is None:
        await message.answer(
            "Maydon noto'g'ri.\n"
            "Variantlar: nomi, toifa, birlik, narx, tannarx, qoldiq"
        )
        return

    await state.update_data(edit_field=field)
    await state.set_state(EditProductState.value)

    prompts = {
        "name": "Yangi nomni yuboring.",
        "category": "Yangi toifani yuboring.\nBo'sh qilmoqchi bo'lsangiz '-' yuboring.",
        "unit": "Yangi o'lchov birligini yuboring.",
        "sell_price": "Yangi sotuv narxini yuboring.",
        "cost_price": "Yangi tannarxni yuboring.\nOlib tashlash uchun '-' yuboring.",
        "stock_quantity": "Yangi qoldiqni yuboring.",
    }
    await message.answer(prompts[field])


@router.message(EditProductState.value)
async def edit_product_save(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    if not is_admin(message):
        return

    data = await state.get_data()
    product = await get_product_by_id(session, int(data["product_id"]))
    if product is None:
        await state.clear()
        await message.answer("Mahsulot topilmadi.", reply_markup=products_menu_keyboard())
        return

    field = data["edit_field"]
    raw_value = (message.text or "").strip()

    if field == "name":
        if len(raw_value) < 2:
            await message.answer("Nomi juda qisqa.")
            return

        existing = await get_product_by_name(session, raw_value)
        if existing and existing.id != product.id:
            await message.answer("Bu nom bilan boshqa mahsulot mavjud.")
            return

        product = await update_product_fields(session, product, name=raw_value)

    elif field == "category":
        category = None if raw_value == "-" else raw_value
        product = await update_product_fields(
            session,
            product,
            category=category if category is not None else "",
        )

    elif field == "unit":
        if len(raw_value) < 1:
            await message.answer("Birlikni to'g'ri kiriting.")
            return
        product = await update_product_fields(session, product, unit=raw_value)

    elif field == "sell_price":
        value = parse_decimal(raw_value)
        if value is None or value == 0:
            await message.answer("Narxni to'g'ri kiriting.")
            return
        product = await update_product_fields(session, product, sell_price=value)

    elif field == "cost_price":
        if raw_value == "-":
            product.cost_price = None
            await session.commit()
            await session.refresh(product)
        else:
            value = parse_decimal(raw_value)
            if value is None:
                await message.answer("Tannarxni to'g'ri kiriting.")
                return
            product = await update_product_fields(session, product, cost_price=value)

    elif field == "stock_quantity":
        value = parse_decimal(raw_value)
        if value is None:
            await message.answer("Qoldiqni to'g'ri kiriting.")
            return
        product = await update_product_fields(session, product, stock_quantity=value)

    await state.clear()
    await message.answer(
        "Mahsulot yangilandi.\n\n" + build_single_product_text(product),
        reply_markup=products_menu_keyboard(),
    )


@router.message(F.text == "✏️ Narxni o'zgartirish")
async def edit_price_start(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return

    products = await list_products(session, limit=30)
    if not products:
        await message.answer("Mahsulotlar yo'q.")
        return

    await state.set_state(EditProductPriceState.product_id)
    await message.answer(
        build_product_lines(products) + "\nNarxini o'zgartirish uchun mahsulot ID raqamini yuboring.",
        reply_markup=cancel_keyboard(),
    )


@router.message(EditProductPriceState.product_id)
async def edit_price_choose_product(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    if not is_admin(message):
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Iltimos, mahsulot ID raqamini yuboring.")
        return

    product = await get_product_by_id(session, int(text))
    if product is None:
        await message.answer("Bunday mahsulot topilmadi.")
        return

    await state.update_data(product_id=product.id, product_name=product.name)
    await state.set_state(EditProductPriceState.new_price)
    await message.answer(
        f"Yangi narxni yuboring.\n\n"
        f"Mahsulot: {product.name}\n"
        f"Hozirgi narx: {format_number(product.sell_price)} so'm"
    )


@router.message(EditProductPriceState.new_price)
async def edit_price_save(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    if not is_admin(message):
        return

    new_price = parse_decimal(message.text or "")
    if new_price is None or new_price == 0:
        await message.answer("Narxni to'g'ri kiriting.")
        return

    data = await state.get_data()
    product = await get_product_by_id(session, int(data["product_id"]))
    if product is None:
        await state.clear()
        await message.answer("Mahsulot topilmadi.", reply_markup=products_menu_keyboard())
        return

    product = await update_product_price(session, product, new_price)
    await state.clear()

    await message.answer(
        "Narx yangilandi.\n\n"
        f"Mahsulot: {product.name}\n"
        f"Yangi narx: {format_number(product.sell_price)} so'm",
        reply_markup=products_menu_keyboard(),
    )


@router.message(F.text == "📥 Qoldiq qo'shish")
async def add_stock_start(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return

    products = await list_products(session, limit=30)
    if not products:
        await message.answer("Mahsulotlar yo'q.")
        return

    await state.set_state(AddProductStockState.product_id)
    await message.answer(
        build_product_lines(products) + "\nQoldiq qo'shish uchun mahsulot ID raqamini yuboring.",
        reply_markup=cancel_keyboard(),
    )


@router.message(AddProductStockState.product_id)
async def add_stock_choose_product(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    if not is_admin(message):
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Iltimos, mahsulot ID raqamini yuboring.")
        return

    product = await get_product_by_id(session, int(text))
    if product is None:
        await message.answer("Bunday mahsulot topilmadi.")
        return

    await state.update_data(product_id=product.id, product_name=product.name)
    await state.set_state(AddProductStockState.add_quantity)
    await message.answer(
        f"Qo'shiladigan qoldiqni yuboring.\n\n"
        f"Mahsulot: {product.name}\n"
        f"Hozirgi qoldiq: {format_number(product.stock_quantity)} {product.unit}"
    )


@router.message(AddProductStockState.add_quantity)
async def add_stock_save(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    if not is_admin(message):
        return

    add_qty = parse_decimal(message.text or "")
    if add_qty is None:
        await message.answer("Miqdorni to'g'ri kiriting.")
        return

    data = await state.get_data()
    product = await get_product_by_id(session, int(data["product_id"]))
    if product is None:
        await state.clear()
        await message.answer("Mahsulot topilmadi.", reply_markup=products_menu_keyboard())
        return

    product = await add_product_stock(session, product, add_qty)
    await state.clear()

    await message.answer(
        "Qoldiq qo'shildi.\n\n"
        f"Mahsulot: {product.name}\n"
        f"Yangi qoldiq: {format_number(product.stock_quantity)} {product.unit}",
        reply_markup=products_menu_keyboard(),
    )


@router.message(F.text == "🗃 Mahsulotni arxivlash")
async def archive_product_start(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return

    products = await list_products(session, limit=30)
    if not products:
        await message.answer("Mahsulotlar yo'q.")
        return

    await state.set_state(ArchiveProductState.product_id)
    await message.answer(
        build_product_lines(products) + "\nArxivlash uchun mahsulot ID raqamini yuboring.",
        reply_markup=cancel_keyboard(),
    )


@router.message(ArchiveProductState.product_id)
async def archive_product_choose(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    if not is_admin(message):
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Iltimos, mahsulot ID raqamini yuboring.")
        return

    product = await get_product_by_id(session, int(text))
    if product is None:
        await message.answer("Bunday mahsulot topilmadi.")
        return

    await state.update_data(product_id=product.id, product_name=product.name)
    await state.set_state(ArchiveProductState.confirm)
    await message.answer(
        f"Mahsulotni arxivlaysizmi?\n\n"
        f"Mahsulot: {product.name}\n\n"
        "Tasdiqlash uchun: ha\n"
        "Bekor qilish uchun: yo'q"
    )


@router.message(ArchiveProductState.confirm)
async def archive_product_confirm(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    if not is_admin(message):
        return

    answer = (message.text or "").strip().lower()
    if answer not in {"ha", "yo'q", "yoq"}:
        await message.answer("Iltimos, 'ha' yoki 'yo'q' deb yuboring.")
        return

    if answer in {"yo'q", "yoq"}:
        await state.clear()
        await message.answer("Arxivlash bekor qilindi.", reply_markup=products_menu_keyboard())
        return

    data = await state.get_data()
    product = await get_product_by_id(session, int(data["product_id"]))
    if product is None:
        await state.clear()
        await message.answer("Mahsulot topilmadi.", reply_markup=products_menu_keyboard())
        return

    product = await archive_product(session, product)
    await state.clear()

    await message.answer(
        f"Mahsulot arxivlandi.\n\n"
        f"Mahsulot: {product.name}",
        reply_markup=products_menu_keyboard(),
    )