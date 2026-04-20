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

    existing = await get_product_by_name(session, name)
    if existing:
        await message.answer(
            "Bu nom bilan mahsulot allaqachon mavjud.\n"
            "Boshqa nom kiriting."
        )
        return

    await state.update_data(name=name)
    await state.set_state(AddProductState.category)

    await message.answer(
        "Toifani yuboring yoki '-' yuboring."
    )


@router.message(AddProductState.category)
async def add_product_category(message: Message, state: FSMContext):
    category = message.text.strip()
    await state.update_data(category=None if category == "-" else category)

    await state.set_state(AddProductState.unit)
    await message.answer("O'lchov birligini yuboring (masalan: dona)")


@router.message(AddProductState.unit)
async def add_product_unit(message: Message, state: FSMContext):
    unit = message.text.strip()

    await state.update_data(unit=unit)
    await state.set_state(AddProductState.sell_price)

    await message.answer("Sotuv narxini kiriting (masalan: 25000)")


@router.message(AddProductState.sell_price)
async def add_product_sell_price(message: Message, state: FSMContext):
    price = parse_decimal(message.text)

    if price is None:
        await message.answer("Narx noto‘g‘ri.")
        return

    await state.update_data(sell_price=str(price))
    await state.set_state(AddProductState.cost_price)

    await message.answer("Tannarx (yoki '-')")


@router.message(AddProductState.cost_price)
async def add_product_cost_price(message: Message, state: FSMContext):
    text = message.text.strip()

    if text == "-":
        await state.update_data(cost_price=None)
    else:
        price = parse_decimal(text)
        if price is None:
            await message.answer("Noto‘g‘ri qiymat.")
            return
        await state.update_data(cost_price=str(price))

    await state.set_state(AddProductState.stock_quantity)
    await message.answer("Boshlang‘ich qoldiqni kiriting")


@router.message(AddProductState.stock_quantity)
async def add_product_stock_quantity(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    qty = parse_decimal(message.text)

    if qty is None:
        await message.answer("Noto‘g‘ri son.")
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

    # 🔥 MUHIM FIX (xato shu yerda edi)
    tannarx_text = (
        f"{format_number(product.cost_price)} so'm"
        if product.cost_price is not None
        else "kiritilmagan"
    )

    await message.answer(
        "Mahsulot qo‘shildi\n\n"
        f"Nomi: {product.name}\n"
        f"Narx: {format_number(product.sell_price)} so'm\n"
        f"Tannarx: {tannarx_text}\n"
        f"Qoldiq: {format_number(product.stock_quantity)} {product.unit}",
        reply_markup=products_menu_keyboard(),
    )


@router.message(F.text == "📋 Mahsulotlar ro'yxati")
async def products_list(message: Message, session: AsyncSession):
    products = await list_products(session)

    if not products:
        await message.answer("Mahsulotlar yo‘q")
        return

    text = "Mahsulotlar:\n\n"

    for p in products:
        text += (
            f"{p.name}\n"
            f"Narx: {format_number(p.sell_price)} so'm\n"
            f"Qoldiq: {format_number(p.stock_quantity)} {p.unit}\n\n"
        )

    await message.answer(text)


@router.message(F.text == "🔎 Mahsulot qidirish")
async def search_product_start(message: Message, state: FSMContext):
    await state.set_data({"search": True})
    await message.answer("Qidiruv uchun nom yuboring")


@router.message()
async def search_product_handler(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
):
    data = await state.get_data()

    if not data.get("search"):
        return

    products = await search_products(session, message.text)

    if not products:
        await message.answer("Topilmadi")
        return

    text = "Topildi:\n\n"

    for p in products:
        text += f"{p.name} - {format_number(p.sell_price)} so'm\n"

    await message.answer(text)
    await state.clear()