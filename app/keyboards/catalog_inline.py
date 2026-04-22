from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    """Kategoriyalar ro'yxati (2 ustunli)"""
    rows = []
    # 2 ustunli qilib chiqarish
    for i in range(0, len(categories), 2):
        row = []
        row.append(InlineKeyboardButton(text=categories[i].title(), callback_data=f"catalog_category:{categories[i]}"))
        if i + 1 < len(categories):
            row.append(InlineKeyboardButton(text=categories[i + 1].title(),
                                            callback_data=f"catalog_category:{categories[i + 1]}"))
        rows.append(row)

    rows.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="catalog_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def products_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for product in products:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{product['name']} — {product['price_text']} so'm",
                    callback_data=f"catalog_product:{product['id']}",
                )
            ]
        )

    rows.append(
        [InlineKeyboardButton(text="⬅️ Kategoriyalar", callback_data="catalog_back_categories")]
    )
    rows.append(
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="catalog_cancel")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quantity_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="catalog_qty:1"),
                InlineKeyboardButton(text="2", callback_data="catalog_qty:2"),
                InlineKeyboardButton(text="5", callback_data="catalog_qty:5"),
                InlineKeyboardButton(text="10", callback_data="catalog_qty:10"),
            ],
            [InlineKeyboardButton(text="✍️ Boshqa miqdor", callback_data="catalog_qty_custom")],
            [InlineKeyboardButton(text="⬅️ Mahsulotlar", callback_data="catalog_back_products")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="catalog_cancel")],
        ]
    )


def cart_action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yana mahsulot", callback_data="catalog_add_more")],
            [InlineKeyboardButton(text="💳 To'lov turini tanlash", callback_data="catalog_choose_payment")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="catalog_cancel")],
        ]
    )


def payment_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💵 Naqd", callback_data="catalog_payment:naqd")],
            [InlineKeyboardButton(text="🕒 Nasiya", callback_data="catalog_payment:nasiya")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="catalog_back_cart")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="catalog_cancel")],
        ]
    )


def confirm_order_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Yuborish", callback_data="catalog_confirm_yes")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="catalog_confirm_no")],
        ]
    )