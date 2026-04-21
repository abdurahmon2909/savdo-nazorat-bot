from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_customers_keyboard(customers: list[dict], prefix: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for customer in customers:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{customer['name']} — {customer['phone']}",
                    callback_data=f"{prefix}_customer:{customer['id']}",
                )
            ]
        )

    rows.append(
        [InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="admin_menu:home")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_categories_keyboard(categories: list[str], prefix: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for category in categories:
        rows.append(
            [
                InlineKeyboardButton(
                    text=category.title(),
                    callback_data=f"{prefix}_category:{category}",
                )
            ]
        )

    rows.append(
        [InlineKeyboardButton(text="⬅️ Mijozlar", callback_data=f"{prefix}_back_customers")]
    )
    rows.append(
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{prefix}_cancel")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_products_keyboard(products: list[dict], prefix: str) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for product in products:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{product['name']} — {product['price_text']} so'm",
                    callback_data=f"{prefix}_product:{product['id']}",
                )
            ]
        )

    rows.append(
        [InlineKeyboardButton(text="⬅️ Kategoriyalar", callback_data=f"{prefix}_back_categories")]
    )
    rows.append(
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{prefix}_cancel")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_quantity_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data=f"{prefix}_qty:1"),
                InlineKeyboardButton(text="2", callback_data=f"{prefix}_qty:2"),
                InlineKeyboardButton(text="5", callback_data=f"{prefix}_qty:5"),
                InlineKeyboardButton(text="10", callback_data=f"{prefix}_qty:10"),
            ],
            [InlineKeyboardButton(text="✍️ Boshqa miqdor", callback_data=f"{prefix}_qty_custom")],
            [InlineKeyboardButton(text="⬅️ Mahsulotlar", callback_data=f"{prefix}_back_products")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{prefix}_cancel")],
        ]
    )


def _fmt_qty(value: str | Decimal) -> str:
    text = format(Decimal(str(value)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def admin_cart_keyboard(prefix: str, items: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for index, item in enumerate(items):
        qty_text = _fmt_qty(item["quantity"])
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"➖ {index + 1}",
                    callback_data=f"{prefix}_minus:{index}",
                ),
                InlineKeyboardButton(
                    text=f"{qty_text}",
                    callback_data=f"{prefix}_noop",
                ),
                InlineKeyboardButton(
                    text=f"➕ {index + 1}",
                    callback_data=f"{prefix}_plus:{index}",
                ),
                InlineKeyboardButton(
                    text="❌",
                    callback_data=f"{prefix}_remove:{index}",
                ),
            ]
        )

    if items:
        rows.append(
            [InlineKeyboardButton(text="🧹 Korzinani tozalash", callback_data=f"{prefix}_clear")]
        )

    rows.append(
        [InlineKeyboardButton(text="➕ Yana mahsulot", callback_data=f"{prefix}_add_more")]
    )
    rows.append(
        [InlineKeyboardButton(text="💳 To'lov turini tanlash", callback_data=f"{prefix}_choose_payment")]
    )
    rows.append(
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{prefix}_cancel")]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_payment_type_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💵 Naqd", callback_data=f"{prefix}_payment:naqd")],
            [InlineKeyboardButton(text="🕒 Nasiya", callback_data=f"{prefix}_payment:nasiya")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"{prefix}_back_cart")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"{prefix}_cancel")],
        ]
    )


def admin_confirm_sale_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Saqlash", callback_data="admin_sale_confirm_yes")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_sale_confirm_no")],
        ]
    )


def admin_orders_keyboard(orders: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for order in orders:
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"ID {order['id']} • "
                        f"Qoldiq {order['left_text']} so'm"
                    ),
                    callback_data=f"admin_payment_order:{order['id']}",
                )
            ]
        )

    rows.append(
        [InlineKeyboardButton(text="⬅️ Bosh menyu", callback_data="admin_menu:home")]
    )
    rows.append(
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_payment_cancel")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_payment_amount_keyboard(order_id: int, left_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"💯 To'liq ({left_text})", callback_data=f"admin_payment_full:{order_id}")],
            [InlineKeyboardButton(text="✍️ Qisman to'lash", callback_data=f"admin_payment_custom:{order_id}")],
            [InlineKeyboardButton(text="⬅️ Buyurtmalar", callback_data="admin_payment_back_orders")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_payment_cancel")],
        ]
    )