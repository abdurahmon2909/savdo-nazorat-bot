from decimal import Decimal
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.common_inline import cancel_inline_keyboard, back_to_admin_home_keyboard
from app.services.customers import get_customer_by_id
from app.services.order_requests import (
    approve_order_request,
    get_order_request_by_id,
    list_order_request_items,
    list_pending_order_requests,
    reject_order_request,
)
from app.services.products import get_product_by_id
from app.services.stock_alerts import send_low_stock_alert
from app.states.admin_request_state import ManageOrderRequestState
from app.utils.helpers import is_admin, format_number
from app.utils.statuses import uzbek_order_status

router = Router()


@router.callback_query(F.data == "admin_menu:requests")
async def show_order_requests(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    requests = await list_pending_order_requests(session, limit=30)
    if not requests:
        await callback.message.edit_text(
            "Hozircha kutilayotgan buyurtma so'rovlari yo'q.",
            reply_markup=back_to_admin_home_keyboard()
        )
        await callback.answer()
        return

    lines = ["Kutilayotgan buyurtma so'rovlari:\n"]
    for req in requests:
        customer = await get_customer_by_id(session, int(req.customer_id))
        customer_name = customer.full_name if customer else "Noma'lum mijoz"
        lines.append(
            f"So'rov ID: {req.id}\n"
            f"Mijoz: {customer_name}\n"
            f"Jami: {format_number(req.total_amount)} so'm\n"
            f"To'lov turi: {req.payment_type}\n"
            f"Holat: {uzbek_order_status(req.status)}\n"
        )
    await state.clear()
    await state.set_state(ManageOrderRequestState.request_id)
    await callback.message.edit_text(
        "\n".join(lines) + "\nKo'rib chiqish uchun so'rov ID raqamini yuboring.",
        reply_markup=cancel_inline_keyboard()
    )
    await callback.answer()


@router.message(ManageOrderRequestState.request_id)
async def choose_order_request(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return

    text = (message.text or "").strip()
    if text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "Amal bekor qilindi.",
            reply_markup=back_to_admin_home_keyboard()
        )
        return

    if not text.isdigit():
        await message.answer(
            "Iltimos, so'rov ID raqamini yuboring.",
            reply_markup=cancel_inline_keyboard()
        )
        return

    request = await get_order_request_by_id(session, int(text))
    if not request:
        await message.answer(
            "Bunday so'rov topilmadi.",
            reply_markup=cancel_inline_keyboard()
        )
        return

    if request.status != "pending":
        await state.clear()
        await message.answer(
            f"Bu so'rov allaqachon ko'rib chiqilgan.\nHolat: {uzbek_order_status(request.status)}",
            reply_markup=back_to_admin_home_keyboard()
        )
        return

    customer = await get_customer_by_id(session, int(request.customer_id))
    customer_name = customer.full_name if customer else "Noma'lum mijoz"
    items = await list_order_request_items(session, request.id)

    lines = [
        f"So'rov ID: {request.id}",
        f"Mijoz: {customer_name}",
        f"To'lov turi: {request.payment_type}",
        f"Holat: {uzbek_order_status(request.status)}",
        f"Jami: {format_number(request.total_amount)} so'm",
        "",
        "Mahsulotlar:",
    ]
    for idx, item in enumerate(items, 1):
        qty = Decimal(str(item.quantity))
        price = Decimal(str(item.price))
        line_total = qty * price
        lines.append(
            f"{idx}. {item.product_name}\n"
            f"   Miqdor: {format_number(qty)} {item.product_unit}\n"
            f"   Narx: {format_number(price)} so'm\n"
            f"   Jami: {format_number(line_total)} so'm"
        )
    lines.append("")
    lines.append("Javob yuboring: tasdiqlash yoki rad")

    await state.update_data(request_id=request.id)
    await state.set_state(ManageOrderRequestState.decision)
    await message.answer("\n".join(lines), reply_markup=cancel_inline_keyboard())


@router.message(ManageOrderRequestState.decision)
async def decide_order_request(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return

    text = (message.text or "").strip().lower()
    if text == "❌ bekor qilish":
        await state.clear()
        await message.answer(
            "Amal bekor qilindi.",
            reply_markup=back_to_admin_home_keyboard()
        )
        return

    if text not in {"tasdiqlash", "rad"}:
        await message.answer(
            "Iltimos, 'tasdiqlash' yoki 'rad' deb yuboring.",
            reply_markup=cancel_inline_keyboard()
        )
        return

    data = await state.get_data()
    request = await get_order_request_by_id(session, int(data["request_id"]))
    if not request:
        await state.clear()
        await message.answer(
            "So'rov topilmadi.",
            reply_markup=back_to_admin_home_keyboard()
        )
        return

    if text == "tasdiqlash":
        items = await list_order_request_items(session, request.id)
        order, error = await approve_order_request(
            session=session,
            order_request=request,
            created_by=message.from_user.id,
        )
        await state.clear()
        if error:
            await message.answer(
                f"So'rovni tasdiqlab bo'lmadi.\nSabab: {error}",
                reply_markup=back_to_admin_home_keyboard()
            )
            return

        for item in items:
            product = await get_product_by_id(session, int(item.product_id))
            if product:
                await send_low_stock_alert(
                    bot=message.bot,
                    product_name=product.name,
                    stock_quantity=Decimal(str(product.stock_quantity)),
                    unit=product.unit,
                )

        try:
            await message.bot.send_message(
                request.customer_telegram_id,
                f"✅ Buyurtmangiz tasdiqlandi.\n\n"
                f"So'rov ID: {request.id}\n"
                f"Buyurtma ID: {order.id}\n"
                f"Holat: {uzbek_order_status(order.status)}"
            )
        except Exception:
            pass

        await message.answer(
            f"✅ So'rov tasdiqlandi.\n"
            f"So'rov ID: {request.id}\n"
            f"Buyurtma ID: {order.id}\n"
            f"Holat: {uzbek_order_status(order.status)}",
            reply_markup=back_to_admin_home_keyboard()
        )
        return

    # rad etish
    await reject_order_request(session, request)
    await state.clear()
    try:
        await message.bot.send_message(
            request.customer_telegram_id,
            f"❌ Buyurtmangiz rad etildi.\n\nSo'rov ID: {request.id}"
        )
    except Exception:
        pass
    await message.answer(
        f"❌ So'rov rad etildi.\nSo'rov ID: {request.id}",
        reply_markup=back_to_admin_home_keyboard()
    )