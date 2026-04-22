from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def products_main_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data="admin_products:add"),
         InlineKeyboardButton(text="📂 Kategoriyalar", callback_data="admin_products:categories")],
        [InlineKeyboardButton(text="🔎 Qidirish", callback_data="admin_products:search"),
         InlineKeyboardButton(text="✏️ Narx", callback_data="admin_products:edit_price")],
        [InlineKeyboardButton(text="📥 Qoldiq qo'shish", callback_data="admin_products:add_stock"),
         InlineKeyboardButton(text="🗃 Arxivlash", callback_data="admin_products:archive")],
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="admin_products:edit")],
        [InlineKeyboardButton(text="📋 Barcha mahsulotlar", callback_data="admin_products:list_all")],
        [InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="admin_menu:home")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def products_categories_keyboard(categories: list[str], page: int = 1, total_pages: int = 1) -> InlineKeyboardMarkup:
    """Kategoriyalar ro'yxati (pagination bilan)"""
    rows = []
    start = (page - 1) * 8
    end = start + 8
    for cat in categories[start:end]:
        rows.append([InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"admin_products:category:{cat}")])

    # Pagination tugmalari
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"admin_products:cat_page:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"admin_products:cat_page:{page + 1}"))
    if nav_buttons:
        rows.append(nav_buttons)

    rows.append([InlineKeyboardButton(text="🔎 Qidirish", callback_data="admin_products:search")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_products:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_list_keyboard(
        products: list,
        page: int,
        total_pages: int,
        category: str = None,
        action: str = "list"  # list, add_stock, archive, edit, edit_price
) -> InlineKeyboardMarkup:
    """Mahsulotlar ro'yxati (pagination va har bir mahsulot uchun tugmalar)"""
    rows = []
    for p in products:
        if action == "list":
            text = f"{p.id}. {p.name} | {p.sell_price} so'm | {p.stock_quantity} {p.unit}"
            callback = f"admin_products:view:{p.id}"
        elif action == "add_stock":
            text = f"➕ {p.id}. {p.name} | Qoldiq: {p.stock_quantity} {p.unit}"
            callback = f"admin_products:add_stock_choose:{p.id}"
        elif action == "archive":
            text = f"🗃 {p.id}. {p.name} | {'Faol' if p.is_active else 'Arxiv'}"
            callback = f"admin_products:archive_choose:{p.id}"
        elif action == "edit":
            text = f"✏️ {p.id}. {p.name} | {p.sell_price} so'm"
            callback = f"admin_products:edit_choose:{p.id}"
        elif action == "edit_price":
            text = f"💰 {p.id}. {p.name} | {p.sell_price} so'm"
            callback = f"admin_products:edit_price_choose:{p.id}"
        else:
            text = f"{p.id}. {p.name}"
            callback = f"admin_products:view:{p.id}"
        rows.append([InlineKeyboardButton(text=text, callback_data=callback)])

    # Pagination tugmalari
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"admin_products:page:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"admin_products:page:{page + 1}"))
    if nav_buttons:
        rows.append(nav_buttons)

    # Orqaga tugmasi
    if category:
        rows.append([InlineKeyboardButton(text="⬅️ Kategoriyalar", callback_data="admin_products:categories")])
    else:
        rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_products:back")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_back_keyboard() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin_products:back")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)