from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def order_request_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"orderreq_approve:{request_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"orderreq_reject:{request_id}",
                ),
            ]
        ]
    )


def reject_reason_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✍️ Izoh yozish",
                    callback_data=f"orderreq_reject_reason:{request_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Izohsiz rad etish",
                    callback_data=f"orderreq_reject_noreason:{request_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Orqaga",
                    callback_data=f"orderreq_reject_back:{request_id}",
                )
            ],
        ]
    )