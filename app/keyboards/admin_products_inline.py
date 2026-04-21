from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def products_main_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data="admin_products:add"),
         InlineKeyboardButton(text="📋 Ro'yxat", callback_data="admin_products:list")],
        [InlineKeyboardButton(text="🔎 Qidirish", callback_data="admin_products:search"),
         InlineKeyboardButton(text="✏️ Narx", callback_data="admin_products:edit_price")],
        [InlineKeyboardButton(text="📥 Qoldiq qo'shish", callback_data="admin_products:add_stock"),
         InlineKeyboardButton(text="🗃 Arxivlash", callback_data="admin_products:archive")],
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="admin_products:edit")],
        [InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="admin_menu:home")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def product_back_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_products:back")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)