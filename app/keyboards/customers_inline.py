from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def customers_main_keyboard() -> InlineKeyboardMarkup:
    """Mijozlar bo'limi uchun inline tugmalar"""
    buttons = [
        [InlineKeyboardButton(text="➕ Mijoz qo'shish", callback_data="admin_customers:add")],
        [InlineKeyboardButton(text="📋 Mijozlar ro'yxati", callback_data="admin_customers:list")],
        [InlineKeyboardButton(text="🔎 Mijoz qidirish", callback_data="admin_customers:search")],
        [InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="admin_menu:home")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def customers_cancel_keyboard() -> InlineKeyboardMarkup:
    """Bekor qilish uchun inline tugma"""
    buttons = [[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_customers:cancel")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)