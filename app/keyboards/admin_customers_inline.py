from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def customers_main_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="➕ Mijoz qo'shish", callback_data="admin_customers:add")],
        [InlineKeyboardButton(text="📋 Mijozlar ro'yxati", callback_data="admin_customers:list")],
        [InlineKeyboardButton(text="🔎 Mijoz qidirish", callback_data="admin_customers:search")],
        [InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="admin_menu:home")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)