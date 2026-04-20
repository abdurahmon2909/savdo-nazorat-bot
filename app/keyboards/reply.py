from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📱 Raqamni yuborish",
                    request_contact=True,
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💳 Mening qarzim")],
            [KeyboardButton(text="📦 Buyurtmalarim")],
            [KeyboardButton(text="☎️ Aloqa")],
        ],
        resize_keyboard=True,
    )


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Yangi savdo")],
            [KeyboardButton(text="💰 To'lov kiritish")],
            [KeyboardButton(text="👥 Mijozlar")],
            [KeyboardButton(text="📦 Mahsulotlar")],
            [KeyboardButton(text="📉 Qarzdorlar")],
            [KeyboardButton(text="📚 Buyurtmalar tarixi")],
            [KeyboardButton(text="🧮 Qoldiqni to'g'rilash")],
            [KeyboardButton(text="📊 Hisobotlar")],
        ],
        resize_keyboard=True,
    )


def customers_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mijoz qo'shish")],
            [KeyboardButton(text="📋 Mijozlar ro'yxati")],
            [KeyboardButton(text="🔎 Mijoz qidirish")],
            [KeyboardButton(text="⬅️ Orqaga")],
        ],
        resize_keyboard=True,
    )


def products_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mahsulot qo'shish")],
            [KeyboardButton(text="📋 Mahsulotlar ro'yxati")],
            [KeyboardButton(text="🔎 Mahsulot qidirish")],
            [KeyboardButton(text="⬅️ Orqaga")],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()