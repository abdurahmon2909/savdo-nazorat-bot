from decimal import Decimal
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.products import get_product_by_id, list_products, set_product_stock
from app.states.stock_state import AdjustStockState
from app.utils.helpers import is_admin, parse_decimal, format_number

router = Router()


@router.message(F.text == "🧮 Qoldiqni to'g'rilash")
async def start_adjust_stock(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(message):
        return
    products = await list_products(session, limit=30)
    if not products:
        await message.answer("Hozircha mahsulotlar mavjud emas.")
        return
    lines = ["Mahsulot ID raqamini yuboring:\n"]
    for product in products:
        lines.append(f"{product.id}. {product.name} | Qoldiq: {format_number(product.stock_quantity)} {product.unit}")
    await state.clear()
    await state.set_state(AdjustStockState.product)
    await message.answer("\n".join(lines))


@router.message(AdjustStockState.product)
async def choose_stock_product(message: Message, state: FSMContext, session: AsyncSession) -> None:
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
    await state.update_data(product_id=product.id, product_name=product.name, product_unit=product.unit, old_stock=str(product.stock_quantity))
    await state.set_state(AdjustStockState.quantity)
    await message.answer(f"Yangi qoldiqni yuboring.\n\nMahsulot: {product.name}\nHozirgi qoldiq: {format_number(product.stock_quantity)} {product.unit}")


@router.message(AdjustStockState.quantity)
async def choose_new_stock(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return
    quantity = parse_decimal(message.text or "")
    if quantity is None:
        await message.answer("Iltimos, qoldiq sonini to'g'ri kiriting.")
        return
    data = await state.get_data()
    await state.update_data(new_stock=str(quantity))
    await state.set_state(AdjustStockState.confirm)
    await message.answer(
        f"Qoldiqni tasdiqlaysizmi?\n\n"
        f"Mahsulot: {data['product_name']}\n"
        f"Eski qoldiq: {format_number(data['old_stock'])} {data['product_unit']}\n"
        f"Yangi qoldiq: {format_number(quantity)} {data['product_unit']}\n\n"
        "Tasdiqlash uchun: ha\nBekor qilish uchun: yo'q"
    )


@router.message(AdjustStockState.confirm)
async def confirm_stock_adjust(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(message):
        return
    answer = (message.text or "").strip().lower()
    if answer not in {"ha", "yo'q", "yoq"}:
        await message.answer("Iltimos, 'ha' yoki 'yo'q' deb yuboring.")
        return
    if answer in {"yo'q", "yoq"}:
        await state.clear()
        await message.answer("Qoldiqni to'g'rilash bekor qilindi.")
        return
    data = await state.get_data()
    product = await get_product_by_id(session, int(data["product_id"]))
    if product is None:
        await state.clear()
        await message.answer("Mahsulot topilmadi.")
        return
    product = await set_product_stock(session=session, product=product, new_quantity=Decimal(str(data["new_stock"])))
    await state.clear()
    await message.answer(f"Qoldiq muvaffaqiyatli yangilandi.\n\nMahsulot: {product.name}\nYangi qoldiq: {format_number(product.stock_quantity)} {product.unit}")