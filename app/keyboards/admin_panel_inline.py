from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛒 Yangi savdo", callback_data="admin_menu:new_sale"),
                InlineKeyboardButton(text="📥 So'rovlar", callback_data="admin_menu:requests"),
            ],
            [
                InlineKeyboardButton(text="💰 To'lov", callback_data="admin_menu:payments"),
                InlineKeyboardButton(text="📉 Qarzdorlar", callback_data="admin_menu:debtors"),
            ],
            [
                InlineKeyboardButton(text="👥 Mijozlar", callback_data="admin_menu:customers"),
                InlineKeyboardButton(text="📦 Mahsulotlar", callback_data="admin_menu:products"),
            ],
            [
                InlineKeyboardButton(text="📚 Tarix", callback_data="admin_menu:history"),
                InlineKeyboardButton(text="📊 Hisobot", callback_data="admin_menu:reports"),
            ],
            [
                InlineKeyboardButton(text="⏰ Kechikkanlar", callback_data="admin_menu:overdue"),
                InlineKeyboardButton(text="🧮 Qoldiq", callback_data="admin_menu:stock"),
            ],
        ]
    )


def admin_products_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Qo'shish", callback_data="admin_products:add"),
                InlineKeyboardButton(text="📋 Ro'yxat", callback_data="admin_products:list"),
            ],
            [
                InlineKeyboardButton(text="🔎 Qidirish", callback_data="admin_products:search"),
                InlineKeyboardButton(text="✏️ Narx", callback_data="admin_products:edit_price"),
            ],
            [
                InlineKeyboardButton(text="📥 Qoldiq", callback_data="admin_products:add_stock"),
                InlineKeyboardButton(text="🗃 Arxiv", callback_data="admin_products:archive"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_menu:home"),
            ],
        ]
    )


def admin_customers_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Qo'shish", callback_data="admin_customers:add"),
                InlineKeyboardButton(text="📋 Ro'yxat", callback_data="admin_customers:list"),
            ],
            [
                InlineKeyboardButton(text="🔎 Qidirish", callback_data="admin_customers:search"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_menu:home"),
            ],
        ]
    )


def admin_back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="admin_menu:home")]
        ]
    )