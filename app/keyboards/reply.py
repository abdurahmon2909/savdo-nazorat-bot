from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 Buyurtma berish")],
            [KeyboardButton(text="💳 Mening qarzim")],
            [KeyboardButton(text="📦 Buyurtmalarim")],
            [KeyboardButton(text="☎️ Aloqa")],
        ],
        resize_keyboard=True,
    )


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Admin panelni ochish")],
            [KeyboardButton(text="👥 Mijozlar")],
            [KeyboardButton(text="📦 Mahsulotlar")],
            [KeyboardButton(text="📥 Buyurtma so'rovlari")],
            [KeyboardButton(text="💰 To'lov kiritish")],
            [KeyboardButton(text="📉 Qarzdorlar")],
            [KeyboardButton(text="📚 Buyurtmalar tarixi")],
            [KeyboardButton(text="📊 Hisobotlar")],
            [KeyboardButton(text="⏰ Kechikkan qarzlar")],
            [KeyboardButton(text="🧮 Qoldiqni to'g'rilash")],
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
            [KeyboardButton(text="✏️ Mahsulotni tahrirlash")],
            [KeyboardButton(text="✏️ Narxni o'zgartirish")],
            [KeyboardButton(text="📥 Qoldiq qo'shish")],
            [KeyboardButton(text="🗃 Mahsulotni arxivlash")],
            [KeyboardButton(text="⬅️ Orqaga")],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()