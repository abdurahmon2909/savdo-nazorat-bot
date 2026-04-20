from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.reply import (
    admin_menu_keyboard,
    cancel_keyboard,
    products_menu_keyboard,
)
from app.services.products import (
    create_product,
    get_product_by_name,
    list_products,
    search_products,
)
from app.states.product import AddProductState

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


def format_number(value: Decimal | float | int) -> str:
    if isinstance(value, Decimal):
        normalized = value.normalize()
        text = format(normalized, "f")
    else:
        text = f"{value}"

    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


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
        "Masalan: Sellofan paket 40x60",
        reply_markup=cancel_keyboard(),
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

    existing_product = await get_product_by_name(session, name)
    if existing_product:
        await message.answer(
            "Bu nom bilan mahsulot allaqachon mavjud.\n"
            "Boshqa nom kiriting yoki amalni bekor qiling."
        )
        return

    await state.update_data(name=name)
    await state.set_state(AddProductState.category)
    await message.answer(
        "Toifani yuboring.\n\n"
        "Masalan: Paketlar\n"
        "Agar kerak bo'lmasa, '-' yuboring."
    )


@router.message(AddProductState.category)
async def add_product_category(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    category = (message.text or "").strip()
    await state.update_data(category=None if category == "-" else category)
    await state.set_state(AddProductState.unit)
    await message.answer(
        "O'lchov birligini yuboring.\n\n"
        "Masalan: dona, pachka, kg, rulon"
    )


@router.message(AddProductState.unit)
async def add_product_unit(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    unit = (message.text or "").strip()
    if len(unit) < 1:
        await message.answer("O'lchov birligini to'g'ri kiriting.")
        return

    await state.update_data(unit=unit)
    await state.set_state(AddProductState.sell_price)
    await message.answer(
        "Sotuv narxini yuboring.\n\n"
        "Masalan: 25000"
    )


@router.message(AddProductState.sell_price)
async def add_product_sell_price(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    sell_price = parse_decimal(message.text or "")
    if sell_price is None:
        await message.answer("Sotuv narxini to'g'ri kiriting.")
        return

    await state.update_data(sell_price=str(sell_price))
    await state.set_state(AddProductState.cost_price)
    await message.answer(
        "Tannarxni yuboring.\n\n"
        "Agar kerak bo'lmasa, '-' yuboring."
    )


@router.message(AddProductState.cost_price)
async def add_product_cost_price(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    text = (message.text or "").strip()
    if text == "-":
        await state.update_data(cost_price=None)
    else:
        cost_price = parse_decimal(text)
        if cost_price is None:
            await message.answer("Tannarxni to'g'ri kiriting yoki '-' yuboring.")
            return
        await state.update_data(cost_price=str(cost_price))

    await state.set_state(AddProductState.stock_quantity)
    await message.answer(
        "Boshlang'ich qoldiqni yuboring.\n\n"
        "Masalan: 100"
    )


@router.message(AddProductState.stock_quantity)
async def add_product_stock_quantity(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not is_admin(message):
        return

    stock_quantity = parse_decimal(message.text or "")
    if stock_quantity is None:
        await message.answer("Qoldiq miqdorini to'g'ri kiriting.")
        return

    data = await state.get_data()

    product = await create_product(
        session=session,
        name=data["name"],
        category=data.get("category"),
        unit=data["unit"],
        sell_price=Decimal(data["sell_price"]),
        cost_price=Decimal(data["cost_price"]) if data.get("cost_price") else None,
        stock_quantity=stock_quantity,
    )

    await state.clear()

    await message.answer(
        "Mahsulot muvaffaqiyatli qo'shildi.\n\n"
        f"ID: {product.id}\n"
        f"Nomi: {product.name}\n"
        f"Toifasi: {product.category or 'kiritilmagan'}\n"
        f"Birligi: {product.unit}\n"
        f"Sotuv narxi: {format_number(product.sell_price)} so'm\n"
        f"Tannarx: {format_number(product.cost_price) + ' so\\'m' if product.cost_price is not None else 'kiritilmagan'}\n"
        f"Qoldiq: {format_number(product.stock_quantity)} {product.unit}",
        reply_markup=products_menu_keyboard(),
    )


@router.message(F.text == "📋 Mahsulotlar ro'yxati")
async def products_list(message: Message, session: AsyncSession) -> None:
    if not is_admin(message):
        return

    products = await list_products(session=session, limit=20)

    if not products:
        await message.answer(
            "Hozircha mahsulotlar mavjud emas.",
            reply_markup=products_menu_keyboard(),
        )
        return

    lines = ["So'nggi mahsulotlar ro'yxati:\n"]
    for index, product in enumerate(products, start=1):
        lines.append(
            f"{index}. {product.name}\n"
            f"   Toifa: {product.category or 'kiritilmagan'}\n"
            f"   Narx: {format_number(product.sell_price)} so'm\n"
            f"   Qoldiq: {format_number(product.stock_quantity)} {product.unit}\n"
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=products_menu_keyboard(),
    )


@router.message(F.text == "🔎 Mahsulot qidirish")
async def search_product_start(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    await state.clear()
    await state.update_data(search_products_mode=True)
    await message.answer(
        "Qidirish uchun mahsulot nomi yoki toifani yuboring.\n\n"
        "Masalan: sellofan\n"
        "yoki\n"
        "paket",
        reply_markup=cancel_keyboard(),
    )


@router.message()
async def universal_product_search_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not is_admin(message):
        return

    data = await state.get_data()
    if not data.get("search_products_mode"):
        return

    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("Qidiruv uchun kamida 2 ta belgi kiriting.")
        return

    products = await search_products(session=session, query=query, limit=20)

    if not products:
        await message.answer(
            "Hech narsa topilmadi.",
            reply_markup=products_menu_keyboard(),
        )
        await state.clear()
        return

    lines = ["Topilgan mahsulotlar:\n"]
    for index, product in enumerate(products, start=1):
        lines.append(
            f"{index}. {product.name}\n"
            f"   Toifa: {product.category or 'kiritilmagan'}\n"
            f"   Birligi: {product.unit}\n"
            f"   Narx: {format_number(product.sell_price)} so'm\n"
            f"   Qoldiq: {format_number(product.stock_quantity)} {product.unit}\n"
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=products_menu_keyboard(),
    )
    await state.clear()