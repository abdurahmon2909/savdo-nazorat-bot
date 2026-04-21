from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def cancel_inline_keyboard() -> InlineKeyboardMarkup:
    """Bekor qilish uchun inline tugma (FSM holatlarida)"""
    buttons = [[InlineKeyboardButton(text="❌ Bekor qilish", callback_data="global:cancel")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_to_admin_home_keyboard() -> InlineKeyboardMarkup:
    """Admin bosh menyusiga qaytish"""
    buttons = [[InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="admin_menu:home")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_to_customer_main_keyboard() -> InlineKeyboardMarkup:
    """Mijoz bosh menyusiga qaytish"""
    buttons = [[InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="customer_menu:home")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Admin asosiy menyusi (inline)"""
    buttons = [
        [InlineKeyboardButton(text="🛒 Yangi savdo", callback_data="admin_menu:new_sale"),
         InlineKeyboardButton(text="📥 So'rovlar", callback_data="admin_menu:requests")],
        [InlineKeyboardButton(text="💰 To'lov", callback_data="admin_menu:payments"),
         InlineKeyboardButton(text="📉 Qarzdorlar", callback_data="admin_menu:debtors")],
        [InlineKeyboardButton(text="👥 Mijozlar", callback_data="admin_menu:customers"),
         InlineKeyboardButton(text="📦 Mahsulotlar", callback_data="admin_menu:products")],
        [InlineKeyboardButton(text="📚 Tarix", callback_data="admin_menu:history"),
         InlineKeyboardButton(text="📊 Hisobot", callback_data="admin_menu:reports")],
        [InlineKeyboardButton(text="⏰ Kechikkanlar", callback_data="admin_menu:overdue"),
         InlineKeyboardButton(text="🧮 Qoldiq", callback_data="admin_menu:stock")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def customer_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Mijoz asosiy menyusi (inline)"""
    buttons = [
        [InlineKeyboardButton(text="🛍 Buyurtma berish", callback_data="customer_menu:order")],
        [InlineKeyboardButton(text="💳 Mening qarzim", callback_data="customer_menu:my_debt"),
         InlineKeyboardButton(text="📦 Buyurtmalarim", callback_data="customer_menu:my_orders")],
        [InlineKeyboardButton(text="☎️ Aloqa", callback_data="customer_menu:contact")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)