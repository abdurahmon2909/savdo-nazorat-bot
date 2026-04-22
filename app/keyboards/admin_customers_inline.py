from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def customers_main_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="➕ Mijoz qo'shish", callback_data="admin_customers:add")],
        [InlineKeyboardButton(text="📋 Mijozlar ro'yxati", callback_data="admin_customers:list")],
        [InlineKeyboardButton(text="🔎 Mijoz qidirish", callback_data="admin_customers:search")],
        [InlineKeyboardButton(text="✏️ Mijoz tahrirlash", callback_data="admin_customers:edit")],
        [InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="admin_menu:home")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def customers_list_keyboard(customers: list, page: int, total_pages: int, action: str = "list") -> InlineKeyboardMarkup:
    """Mijozlar ro'yxati (pagination bilan)"""
    rows = []
    for c in customers:
        rows.append([InlineKeyboardButton(
            text=f"{c.id}. {c.full_name} | {c.phone}",
            callback_data=f"admin_customers:{action}_choose:{c.id}"
        )])

    # Pagination
    nav_buttons = []
    if page > 1:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"admin_customers:page:{action}:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(
            InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"admin_customers:page:{action}:{page + 1}"))
    if nav_buttons:
        rows.append(nav_buttons)

    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_customers:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def customer_detail_keyboard(customer_id: int) -> InlineKeyboardMarkup:
    """Mijoz ma'lumotlarini ko'rsatish uchun tugmalar (tahrirlash va o'chirish)"""
    buttons = [
        [InlineKeyboardButton(text="✏️ Ism-familiya",
                              callback_data=f"admin_customers:edit_field:{customer_id}:full_name")],
        [InlineKeyboardButton(text="📞 Telefon", callback_data=f"admin_customers:edit_field:{customer_id}:phone")],
        [InlineKeyboardButton(text="📍 Manzil", callback_data=f"admin_customers:edit_field:{customer_id}:address")],
        [InlineKeyboardButton(text="📝 Izoh", callback_data=f"admin_customers:edit_field:{customer_id}:note")],
        [InlineKeyboardButton(text="🏷 Holat", callback_data=f"admin_customers:edit_field:{customer_id}:status")],
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"admin_customers:delete_confirm:{customer_id}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_customers:edit_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_delete_keyboard(customer_id: int, customer_name: str) -> InlineKeyboardMarkup:
    """O'chirishni tasdiqlash uchun keyboard"""
    buttons = [
        [InlineKeyboardButton(text="✅ Ha, o'chirish",
                              callback_data=f"admin_customers:delete_confirm_yes:{customer_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_customers:delete_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def edit_field_keyboard(customer_id: int, field: str, current_value: str = "") -> InlineKeyboardMarkup:
    """Maydon tahrirlash uchun orqaga tugmasi"""
    buttons = [
        [InlineKeyboardButton(text="⬅️ Bekor qilish", callback_data=f"admin_customers:edit_field_back:{customer_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def customer_status_keyboard(customer_id: int, current_status: str) -> InlineKeyboardMarkup:
    """Holatni tanlash uchun inline tugmalar"""
    statuses = ["ishonchli", "qarzdor", "bloklangan", "muntazam"]
    buttons = []
    for s in statuses:
        mark = "✅ " if s == current_status else ""
        buttons.append([InlineKeyboardButton(
            text=f"{mark}{s}",
            callback_data=f"admin_customers:set_status:{customer_id}:{s}"
        )])
    buttons.append(
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"admin_customers:edit_field_back:{customer_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)