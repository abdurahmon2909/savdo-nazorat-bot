from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.order_requests import (
    approve_order_request,
    reject_order_request,
    get_order_request_by_id,
)
from app.keyboards.admin_order_inline import reject_reason_keyboard

router = Router()


def is_admin(cb: CallbackQuery):
    return cb.from_user.id in settings.admin_ids


@router.callback_query(F.data.startswith("orderreq_approve:"))
async def approve_request(cb: CallbackQuery, session: AsyncSession):
    if not is_admin(cb):
        return

    request_id = int(cb.data.split(":")[1])
    request = await get_order_request_by_id(session, request_id)

    if not request:
        await cb.answer("Topilmadi", show_alert=True)
        return

    order, error = await approve_order_request(
        session=session,
        order_request=request,
        created_by=cb.from_user.id,
    )

    if error:
        await cb.answer(error, show_alert=True)
        return

    await cb.message.edit_text(f"✅ Tasdiqlandi\nBuyurtma ID: {order.id}")
    await cb.answer()


@router.callback_query(F.data.startswith("orderreq_reject:"))
async def reject_request_menu(cb: CallbackQuery):
    if not is_admin(cb):
        return

    request_id = int(cb.data.split(":")[1])

    await cb.message.edit_reply_markup(
        reply_markup=reject_reason_keyboard(request_id)
    )
    await cb.answer()


@router.callback_query(F.data.startswith("orderreq_reject_noreason:"))
async def reject_no_reason(cb: CallbackQuery, session: AsyncSession):
    if not is_admin(cb):
        return

    request_id = int(cb.data.split(":")[1])
    request = await get_order_request_by_id(session, request_id)

    await reject_order_request(session, request)

    await cb.message.edit_text("❌ Rad etildi")
    await cb.answer()