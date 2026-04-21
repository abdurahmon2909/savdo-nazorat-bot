from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.admin_order_inline import order_request_keyboard, reject_reason_keyboard
from app.services.order_requests import (
    approve_order_request,
    get_order_request_by_id,
    reject_order_request,
)
from app.states.admin_request_state import ManageOrderRequestState
from app.utils.statuses import uzbek_order_status

router = Router()


def is_admin(callback_or_message) -> bool:
    return bool(
        callback_or_message.from_user
        and callback_or_message.from_user.id in settings.admin_ids
    )


@router.callback_query(F.data.startswith("orderreq_approve:"))
async def approve_request(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])
    request = await get_order_request_by_id(session, request_id)

    if request is None:
        await callback.answer("So'rov topilmadi", show_alert=True)
        return

    if request.status != "pending":
        await callback.answer("Bu so'rov allaqachon ko'rib chiqilgan", show_alert=True)
        return

    order, error = await approve_order_request(
        session=session,
        order_request=request,
        created_by=callback.from_user.id,
    )

    if error:
        await callback.answer(error, show_alert=True)
        return

    await callback.message.edit_text(
        f"✅ So'rov tasdiqlandi\n\n"
        f"So'rov ID: {request.id}\n"
        f"Buyurtma ID: {order.id}\n"
        f"Holat: {uzbek_order_status(order.status)}"
    )

    try:
        await callback.bot.send_message(
            request.customer_telegram_id,
            f"✅ Buyurtmangiz tasdiqlandi.\n\n"
            f"So'rov ID: {request.id}\n"
            f"Buyurtma ID: {order.id}\n"
            f"Holat: {uzbek_order_status(order.status)}"
        )
    except Exception:
        pass

    await callback.answer("Tasdiqlandi")


@router.callback_query(F.data.startswith("orderreq_reject:"))
async def reject_request_menu(callback: CallbackQuery):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])

    await callback.message.edit_reply_markup(
        reply_markup=reject_reason_keyboard(request_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("orderreq_reject_back:"))
async def reject_back(callback: CallbackQuery):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])

    await callback.message.edit_reply_markup(
        reply_markup=order_request_keyboard(request_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("orderreq_reject_noreason:"))
async def reject_no_reason(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])
    request = await get_order_request_by_id(session, request_id)

    if request is None:
        await callback.answer("So'rov topilmadi", show_alert=True)
        return

    if request.status != "pending":
        await callback.answer("Bu so'rov allaqachon ko'rib chiqilgan", show_alert=True)
        return

    await reject_order_request(session, request)

    await callback.message.edit_text(
        f"❌ So'rov rad etildi\n\n"
        f"So'rov ID: {request.id}"
    )

    try:
        await callback.bot.send_message(
            request.customer_telegram_id,
            f"❌ Buyurtmangiz rad etildi.\n\n"
            f"So'rov ID: {request.id}"
        )
    except Exception:
        pass

    await callback.answer("Rad etildi")


@router.callback_query(F.data.startswith("orderreq_reject_reason:"))
async def reject_with_reason_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])

    await state.clear()
    await state.update_data(request_id=request_id)
    await state.set_state(ManageOrderRequestState.reject_reason)

    await callback.message.answer(
        f"So'rov ID {request_id} uchun rad etish izohini yuboring."
    )
    await callback.answer("Izohni xabar qilib yuboring")


@router.message(ManageOrderRequestState.reject_reason)
async def reject_with_reason_save(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not is_admin(message):
        return

    reason = (message.text or "").strip()
    if len(reason) < 2:
        await message.answer("Iltimos, izohni to'g'ri kiriting.")
        return

    data = await state.get_data()
    request_id = int(data["request_id"])

    request = await get_order_request_by_id(session, request_id)
    if request is None:
        await state.clear()
        await message.answer("So'rov topilmadi.")
        return

    if request.status != "pending":
        await state.clear()
        await message.answer("Bu so'rov allaqachon ko'rib chiqilgan.")
        return

    await reject_order_request(session, request)
    await state.clear()

    try:
        await message.bot.send_message(
            request.customer_telegram_id,
            f"❌ Buyurtmangiz rad etildi.\n\n"
            f"So'rov ID: {request.id}\n"
            f"Izoh: {reason}"
        )
    except Exception:
        pass

    await message.answer(
        f"So'rov rad etildi.\n\n"
        f"So'rov ID: {request.id}\n"
        f"Izoh yuborildi."
    )