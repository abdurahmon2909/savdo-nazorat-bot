from decimal import Decimal
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.common_inline import cancel_inline_keyboard, back_to_admin_home_keyboard
from app.services.products import get_product_by_id, list_products, set_product_stock
from app.states.stock_state import AdjustStockState
from app.utils.helpers import is_admin, parse_decimal, format_number

router = Router()


@router.callback_query(F.data == "admin_menu:stock")
async def start_adjust_stock(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    products = await list_products(session, limit=30)
    if not products:
        await callback.message.edit_text(
            "Hozircha mahsulotlar mavjud emas.",
            reply_markup=back_to_admin_home_keyboard()
        )
        await callback.answer()
        return

    lines = ["Mahsulot ID raqamini yuboring:\n"]
    for p in products:
        lines.append(f"{p.id}. {p.name} | Qoldiq: {format_number(p.stock_quantity)} {p.unit}")

    await state.clear()
    await state.set_state(AdjustStockState.product)
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=cancel_inline_keyboard()
    )
    await callback.answer()


@router.message(AdjustStockState.product)
async def choose_stock_product(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer(
            "Iltimos, mahsulot ID raqamini yuboring.",
            reply_markup=cancel_inline_keyboard()
        )
        return

    product = await get_product_by_id(session, int(text))
    if not product:
        await message.answer(
            "Bunday mahsulot topilmadi.",
            reply_markup=cancel_inline_keyboard()
        )
        return

    await state.update_data(
        product_id=product.id,
        product_name=product.name,
        product_unit=product.unit,
        old_stock=str(product.stock_quantity),
    )
    await state.set_state(AdjustStockState.quantity)
    await message.answer(
        f"Yangi qoldiqni yuboring.\n\n"
        f"Mahsulot: {product.name}\n"
        f"Hozirgi qoldiq: {format_number(product.stock_quantity)} {product.unit}",
        reply_markup=cancel_inline_keyboard()
    )


@router.message(AdjustStockState.quantity)
async def choose_new_stock(message: Message, state: FSMContext):
    if not is_admin(message):
        return

    quantity = parse_decimal(message.text or "")
    if quantity is None:
        await message.answer(
            "Iltimos, qoldiq sonini to'g'ri kiriting.",
            reply_markup=cancel_inline_keyboard()
        )
        return

    data = await state.get_data()
    await state.update_data(new_stock=str(quantity))
    await state.set_state(AdjustStockState.confirm)
    await message.answer(
        f"Qoldiqni tasdiqlaysizmi?\n\n"
        f"Mahsulot: {data['product_name']}\n"
        f"Eski qoldiq: {format_number(data['old_stock'])} {data['product_unit']}\n"
        f"Yangi qoldiq: {format_number(quantity)} {data['product_unit']}\n\n"
        "Tasdiqlash uchun: ha\nBekor qilish uchun: yo'q",
        reply_markup=cancel_inline_keyboard()
    )


@router.message(AdjustStockState.confirm)
async def confirm_stock_adjust(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return

    answer = (message.text or "").strip().lower()
    if answer not in {"ha", "yo'q", "yoq"}:
        await message.answer(
            "Iltimos, 'ha' yoki 'yo'q' deb yuboring.",
            reply_markup=cancel_inline_keyboard()
        )
        return

    if answer in {"yo'q", "yoq"}:
        await state.clear()
        await message.answer(
            "Qoldiqni to'g'rilash bekor qilindi.",
            reply_markup=back_to_admin_home_keyboard()
        )
        return

    data = await state.get_data()
    product = await get_product_by_id(session, int(data["product_id"]))
    if not product:
        await state.clear()
        await message.answer(
            "Mahsulot topilmadi.",
            reply_markup=back_to_admin_home_keyboard()
        )
        return

    product = await set_product_stock(
        session=session,
        product=product,
        new_quantity=Decimal(str(data["new_stock"])),
    )
    await state.clear()
    await message.answer(
        f"✅ Qoldiq muvaffaqiyatli yangilandi.\n\n"
        f"Mahsulot: {product.name}\n"
        f"Yangi qoldiq: {format_number(product.stock_quantity)} {product.unit}",
        reply_markup=back_to_admin_home_keyboard()
    )