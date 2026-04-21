from decimal import Decimal, InvalidOperation
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.admin_panel_inline import admin_back_home_keyboard
from app.keyboards.admin_sale_inline import (
    admin_cart_keyboard,
    admin_categories_keyboard,
    admin_confirm_sale_keyboard,
    admin_customers_keyboard,
    admin_orders_keyboard,
    admin_payment_amount_keyboard,
    admin_payment_type_keyboard,
    admin_products_keyboard,
    admin_quantity_keyboard,
)
from app.services.customers import get_customer_by_id, list_customers
from app.services.orders import create_order, get_order_by_id, list_customer_open_orders
from app.services.payments import create_payment
from app.services.products import (
    get_product_by_id,
    list_active_categories,
    list_products_by_category,
    reduce_product_stock,
)
from app.services.stock_alerts import send_low_stock_alert
from app.states.admin_sale_inline_state import AdminInlinePaymentState, AdminInlineSaleState
from app.utils.helpers import is_admin, parse_decimal, format_number as fmt

router = Router()


def uz_status(status: str | None) -> str:
    mapping = {
        "pending": "Kutilmoqda", "approved": "Tasdiqlangan", "rejected": "Rad etilgan",
        "cancelled": "Bekor qilingan", "draft": "Qoralama", "unpaid": "To'lanmagan",
        "partial": "Qisman to'langan", "paid": "To'langan", "overdue": "Kechikkan",
    }
    if not status:
        return "Noma'lum"
    return mapping.get(str(status).lower(), str(status))


def build_cart_text(items: list[dict]) -> str:
    if not items:
        return "Korzina bo'sh."
    lines = ["🛒 Korzina:\n"]
    total = Decimal("0")
    for index, item in enumerate(items, start=1):
        qty = Decimal(str(item["quantity"]))
        price = Decimal(str(item["price"]))
        line_total = qty * price
        total += line_total
        lines.append(
            f"{index}. {item['product_name']}\n"
            f"   Miqdor: {fmt(qty)} {item['product_unit']}\n"
            f"   Narx: {fmt(price)} so'm\n"
            f"   Jami: {fmt(line_total)} so'm\n"
        )
    lines.append(f"💰 Umumiy jami: {fmt(total)} so'm")
    return "\n".join(lines)


def merge_item_into_cart(data: dict, qty: Decimal) -> list[dict]:
    items = data.get("items", []).copy()
    current_product_id = int(data["current_product_id"])
    stock = Decimal(str(data["current_product_stock"]))
    for item in items:
        if int(item["product_id"]) == current_product_id:
            existing_qty = Decimal(str(item["quantity"]))
            new_qty = existing_qty + qty
            if new_qty > stock:
                raise ValueError("Buncha mahsulot yo'q")
            item["quantity"] = str(new_qty)
            return items
    items.append({
        "product_id": current_product_id,
        "product_name": data["current_product_name"],
        "product_unit": data["current_product_unit"],
        "quantity": str(qty),
        "price": str(data["current_product_price"]),
        "max_stock": str(stock),
    })
    return items


def recalculate_item_stock_limit(items: list[dict], item_index: int, stock: Decimal) -> None:
    if 0 <= item_index < len(items):
        items[item_index]["max_stock"] = str(stock)


async def render_cart_message(target, items: list[dict]) -> None:
    text = build_cart_text(items) if items else "Korzina bo'sh."
    markup = admin_cart_keyboard("admin_sale", items)
    if isinstance(target, CallbackQuery):
        if target.message:
            await target.message.edit_text(text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


async def show_sale_customers(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    customers = await list_customers(session, limit=30)
    if not customers:
        if callback.message:
            await callback.message.edit_text("Hozircha mijozlar yo'q.", reply_markup=admin_back_home_keyboard())
        await callback.answer()
        return
    rows = [{"id": c.id, "name": c.full_name, "phone": c.phone} for c in customers]
    await state.clear()
    await state.update_data(items=[])
    await state.set_state(AdminInlineSaleState.customer)
    if callback.message:
        await callback.message.edit_text("Mijoz tanlang:", reply_markup=admin_customers_keyboard(rows, "admin_sale"))
    await callback.answer()


async def show_sale_categories(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    categories = await list_active_categories(session)
    if not categories:
        await callback.answer("Kategoriya topilmadi", show_alert=True)
        return
    await state.set_state(AdminInlineSaleState.category)
    if callback.message:
        await callback.message.edit_text("Kategoriya tanlang:", reply_markup=admin_categories_keyboard(categories, "admin_sale"))
    await callback.answer()


async def show_sale_products(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    category = data.get("current_category")
    if not category:
        await callback.answer("Kategoriya topilmadi", show_alert=True)
        return
    products = await list_products_by_category(session, category, limit=100)
    if not products:
        await callback.answer("Bu kategoriyada mahsulot yo'q", show_alert=True)
        return
    rows = [{"id": p.id, "name": p.name, "price_text": fmt(p.sell_price)} for p in products]
    await state.set_state(AdminInlineSaleState.product)
    if callback.message:
        await callback.message.edit_text(f"{category.title()} bo'limi:\nMahsulot tanlang:", reply_markup=admin_products_keyboard(rows, "admin_sale"))
    await callback.answer()


async def show_payment_customers(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    customers = await list_customers(session, limit=30)
    if not customers:
        if callback.message:
            await callback.message.edit_text("Hozircha mijozlar yo'q.", reply_markup=admin_back_home_keyboard())
        await callback.answer()
        return
    rows = [{"id": c.id, "name": c.full_name, "phone": c.phone} for c in customers]
    await state.clear()
    await state.set_state(AdminInlinePaymentState.customer)
    if callback.message:
        await callback.message.edit_text("To'lov uchun mijoz tanlang:", reply_markup=admin_customers_keyboard(rows, "admin_payment"))
    await callback.answer()


@router.callback_query(F.data == "admin_menu:new_sale")
async def start_inline_sale(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_sale_customers(callback, state, session)


@router.callback_query(F.data == "admin_sale_back_customers")
async def sale_back_customers(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_sale_customers(callback, state, session)


@router.callback_query(F.data == "admin_sale_cancel")
async def sale_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.clear()
    if callback.message:
        await callback.message.edit_text("Savdo bekor qilindi.", reply_markup=admin_back_home_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_sale_customer:"))
async def sale_choose_customer(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    customer_id = int(callback.data.split(":")[1])
    customer = await get_customer_by_id(session, customer_id)
    if customer is None:
        await callback.answer("Mijoz topilmadi", show_alert=True)
        return
    await state.update_data(customer_id=customer.id, customer_name=customer.full_name, items=[])
    await show_sale_categories(callback, state, session)


@router.callback_query(F.data.startswith("admin_sale_category:"))
async def sale_choose_category(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    category = callback.data.split(":", 1)[1]
    await state.update_data(current_category=category)
    await show_sale_products(callback, state, session)


@router.callback_query(F.data == "admin_sale_back_categories")
async def sale_back_categories(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_sale_categories(callback, state, session)


@router.callback_query(F.data.startswith("admin_sale_product:"))
async def sale_choose_product(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    product_id = int(callback.data.split(":", 1)[1])
    product = await get_product_by_id(session, product_id)
    if product is None:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    if Decimal(str(product.stock_quantity)) <= 0:
        await callback.answer("Bu mahsulot omborda qolmagan", show_alert=True)
        return
    await state.update_data(
        current_product_id=product.id,
        current_product_name=product.name,
        current_product_price=str(product.sell_price),
        current_product_unit=product.unit,
        current_product_stock=str(product.stock_quantity),
    )
    await state.set_state(AdminInlineSaleState.product)
    if callback.message:
        await callback.message.edit_text(
            f"Mahsulot: {product.name}\nNarx: {fmt(product.sell_price)} so'm\nQoldiq: {fmt(product.stock_quantity)} {product.unit}\n\nMiqdor tanlang:",
            reply_markup=admin_quantity_keyboard("admin_sale"),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_sale_back_products")
async def sale_back_products(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_sale_products(callback, state, session)


@router.callback_query(F.data.startswith("admin_sale_qty:"))
async def sale_choose_qty_preset(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    qty = parse_decimal(callback.data.split(":", 1)[1])
    if qty is None:
        await callback.answer("Miqdor noto'g'ri", show_alert=True)
        return
    data = await state.get_data()
    try:
        items = merge_item_into_cart(data, qty)
    except ValueError:
        await callback.answer("Buncha mahsulot yo'q", show_alert=True)
        return
    await state.update_data(items=items)
    await state.set_state(AdminInlineSaleState.add_more)
    await render_cart_message(callback, items)
    await callback.answer("Korzinaga qo'shildi")


@router.callback_query(F.data == "admin_sale_qty_custom")
async def sale_qty_custom(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.set_state(AdminInlineSaleState.quantity_custom)
    if callback.message:
        await callback.message.edit_text("Kerakli miqdorni xabar qilib yuboring.")
    await callback.answer()


@router.message(AdminInlineSaleState.quantity_custom)
async def sale_qty_custom_message(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return
    qty = parse_decimal(message.text or "")
    if qty is None:
        await message.answer("Iltimos, miqdorni to'g'ri kiriting.")
        return
    data = await state.get_data()
    try:
        items = merge_item_into_cart(data, qty)
    except ValueError:
        await message.answer("Buncha mahsulot yo'q.")
        return
    await state.update_data(items=items)
    await state.set_state(AdminInlineSaleState.add_more)
    await render_cart_message(message, items)


@router.callback_query(F.data.startswith("admin_sale_remove:"))
async def sale_remove_item(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    data = await state.get_data()
    items = data.get("items", []).copy()
    try:
        index = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Xatolik", show_alert=True)
        return
    if index < 0 or index >= len(items):
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    removed = items.pop(index)
    await state.update_data(items=items)
    await state.set_state(AdminInlineSaleState.add_more)
    await render_cart_message(callback, items)
    await callback.answer(f"{removed['product_name']} o'chirildi")


@router.callback_query(F.data.startswith("admin_sale_minus:"))
async def sale_minus_item(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    data = await state.get_data()
    items = data.get("items", []).copy()
    try:
        index = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Xatolik", show_alert=True)
        return
    if index < 0 or index >= len(items):
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    item = items[index]
    qty = Decimal(str(item["quantity"]))
    if qty <= 1:
        items.pop(index)
    else:
        item["quantity"] = str(qty - Decimal("1"))
    await state.update_data(items=items)
    await state.set_state(AdminInlineSaleState.add_more)
    await render_cart_message(callback, items)
    await callback.answer("Kamaytirildi")


@router.callback_query(F.data.startswith("admin_sale_plus:"))
async def sale_plus_item(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    data = await state.get_data()
    items = data.get("items", []).copy()
    try:
        index = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("Xatolik", show_alert=True)
        return
    if index < 0 or index >= len(items):
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    item = items[index]
    product = await get_product_by_id(session, int(item["product_id"]))
    if product is None:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    current_qty = Decimal(str(item["quantity"]))
    current_stock = Decimal(str(product.stock_quantity))
    recalculate_item_stock_limit(items, index, current_stock)
    if current_qty + Decimal("1") > current_stock:
        await callback.answer("Buncha mahsulot yo'q", show_alert=True)
        return
    item["quantity"] = str(current_qty + Decimal("1"))
    await state.update_data(items=items)
    await state.set_state(AdminInlineSaleState.add_more)
    await render_cart_message(callback, items)
    await callback.answer("Ko'paytirildi")


@router.callback_query(F.data == "admin_sale_clear")
async def sale_clear_cart(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.update_data(items=[])
    await state.set_state(AdminInlineSaleState.add_more)
    await render_cart_message(callback, [])
    await callback.answer("Tozalandi")


@router.callback_query(F.data == "admin_sale_add_more")
async def sale_add_more(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_sale_categories(callback, state, session)


@router.callback_query(F.data == "admin_sale_choose_payment")
async def sale_choose_payment(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    data = await state.get_data()
    items = data.get("items", [])
    if not items:
        await callback.answer("Korzina bo'sh", show_alert=True)
        return
    await state.set_state(AdminInlineSaleState.payment_type)
    if callback.message:
        await callback.message.edit_text(build_cart_text(items) + "\n\nTo'lov turini tanlang:", reply_markup=admin_payment_type_keyboard("admin_sale"))
    await callback.answer()


@router.callback_query(F.data == "admin_sale_back_cart")
async def sale_back_cart(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    data = await state.get_data()
    items = data.get("items", [])
    await state.set_state(AdminInlineSaleState.add_more)
    await render_cart_message(callback, items)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_sale_payment:"))
async def sale_choose_payment_type(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    payment_type = callback.data.split(":", 1)[1]
    if payment_type not in {"naqd", "nasiya"}:
        await callback.answer("Noto'g'ri to'lov turi", show_alert=True)
        return
    data = await state.get_data()
    items = data.get("items", [])
    total = Decimal("0")
    for item in items:
        total += Decimal(str(item["quantity"])) * Decimal(str(item["price"]))
    await state.update_data(payment_type=payment_type, total_amount=str(total))
    await state.set_state(AdminInlineSaleState.confirm)
    if callback.message:
        await callback.message.edit_text(
            f"Mijoz: {data['customer_name']}\n\n{build_cart_text(items)}\n\nTo'lov turi: {payment_type}",
            reply_markup=admin_confirm_sale_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_sale_confirm_no")
async def sale_confirm_no(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.clear()
    if callback.message:
        await callback.message.edit_text("Savdo bekor qilindi.", reply_markup=admin_back_home_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_sale_confirm_yes")
async def sale_confirm_yes(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    data = await state.get_data()
    items = data.get("items", [])
    if not items:
        await callback.answer("Korzina bo'sh", show_alert=True)
        return
    product_map = {}
    product_objects = {}
    for item in items:
        product_id = int(item["product_id"])
        qty = Decimal(str(item["quantity"]))
        product_map[product_id] = product_map.get(product_id, Decimal("0")) + qty
    for product_id, total_qty in product_map.items():
        product = await get_product_by_id(session, product_id)
        if product is None:
            await callback.answer("Mahsulot topilmadi", show_alert=True)
            return
        current_stock = Decimal(str(product.stock_quantity))
        if total_qty > current_stock:
            await callback.answer(f"Qoldiq yetarli emas: {product.name}", show_alert=True)
            return
        product_objects[product_id] = product
    order_items = [{"product_id": int(item["product_id"]), "quantity": Decimal(str(item["quantity"])), "price": Decimal(str(item["price"]))} for item in items]
    order = await create_order(session=session, customer_id=int(data["customer_id"]), created_by=callback.from_user.id, items=order_items, payment_type=data["payment_type"])
    for product_id, total_qty in product_map.items():
        updated_product = await reduce_product_stock(session, product_objects[product_id], total_qty)
        await send_low_stock_alert(bot=callback.bot, product_name=updated_product.name, stock_quantity=Decimal(str(updated_product.stock_quantity)), unit=updated_product.unit)
    await state.clear()
    if callback.message:
        await callback.message.edit_text(
            f"Savdo saqlandi.\n\nBuyurtma ID: {order.id}\nMijoz: {data['customer_name']}\nJami: {fmt(data['total_amount'])} so'm\nTo'lov turi: {data['payment_type']}\nHolat: {uz_status(order.status)}",
            reply_markup=admin_back_home_keyboard(),
        )
    await callback.answer("Saqlandi")


@router.callback_query(F.data == "admin_menu:payments")
async def start_inline_payment(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await show_payment_customers(callback, state, session)


@router.callback_query(F.data == "admin_payment_cancel")
async def payment_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    await state.clear()
    if callback.message:
        await callback.message.edit_text("To'lov amali bekor qilindi.", reply_markup=admin_back_home_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_payment_customer:"))
async def payment_choose_customer(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    customer_id = int(callback.data.split(":")[1])
    customer = await get_customer_by_id(session, customer_id)
    if customer is None:
        await callback.answer("Mijoz topilmadi", show_alert=True)
        return
    orders = await list_customer_open_orders(session, customer.id, limit=20)
    if not orders:
        if callback.message:
            await callback.message.edit_text("Bu mijozning ochiq qarzi yo'q.", reply_markup=admin_back_home_keyboard())
        await callback.answer()
        return
    rows = [{"id": order.id, "left_text": fmt(Decimal(str(order.total_amount)) - Decimal(str(order.paid_amount)))} for order in orders]
    await state.update_data(customer_id=customer.id, customer_name=customer.full_name)
    await state.set_state(AdminInlinePaymentState.order)
    if callback.message:
        await callback.message.edit_text(f"{customer.full_name} uchun ochiq buyurtmalar:", reply_markup=admin_orders_keyboard(rows))
    await callback.answer()


@router.callback_query(F.data == "admin_payment_back_orders")
async def payment_back_orders(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    data = await state.get_data()
    customer_id = data.get("customer_id")
    if not customer_id:
        await callback.answer("Mijoz topilmadi", show_alert=True)
        return
    customer = await get_customer_by_id(session, int(customer_id))
    if customer is None:
        await callback.answer("Mijoz topilmadi", show_alert=True)
        return
    orders = await list_customer_open_orders(session, customer.id, limit=20)
    if not orders:
        if callback.message:
            await callback.message.edit_text("Ochiq buyurtmalar yo'q.", reply_markup=admin_back_home_keyboard())
        await callback.answer()
        return
    rows = [{"id": order.id, "left_text": fmt(Decimal(str(order.total_amount)) - Decimal(str(order.paid_amount)))} for order in orders]
    await state.set_state(AdminInlinePaymentState.order)
    if callback.message:
        await callback.message.edit_text(f"{customer.full_name} uchun ochiq buyurtmalar:", reply_markup=admin_orders_keyboard(rows))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_payment_order:"))
async def payment_choose_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    order = await get_order_by_id(session, order_id)
    if order is None:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return
    total = Decimal(str(order.total_amount))
    paid = Decimal(str(order.paid_amount))
    left = total - paid
    if left <= 0:
        await callback.answer("Bu buyurtma yopilgan", show_alert=True)
        return
    await state.update_data(order_id=order.id, order_left=str(left))
    if callback.message:
        await callback.message.edit_text(f"Buyurtma ID: {order.id}\nQoldiq: {fmt(left)} so'm\nHolat: {uz_status(order.status)}\n\nTo'lov turini tanlang:", reply_markup=admin_payment_amount_keyboard(order.id, fmt(left)))
    await callback.answer()


@router.callback_query(F.data.startswith("admin_payment_full:"))
async def payment_full(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    order = await get_order_by_id(session, order_id)
    if order is None:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return
    total = Decimal(str(order.total_amount))
    paid = Decimal(str(order.paid_amount))
    left = total - paid
    payment = await create_payment(session=session, order=order, amount=left, payment_method="naqd")
    await state.clear()
    if callback.message:
        await callback.message.edit_text(
            f"To'lov saqlandi.\n\nTo'lov ID: {payment.id}\nBuyurtma ID: {order.id}\nTo'lov summasi: {fmt(payment.amount)} so'm\nYangi holat: {uz_status(order.status)}\nJami to'langan: {fmt(order.paid_amount)} so'm",
            reply_markup=admin_back_home_keyboard(),
        )
    await callback.answer("To'liq to'landi")


@router.callback_query(F.data.startswith("admin_payment_custom:"))
async def payment_custom(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(callback):
        await callback.answer("Ruxsat yo'q", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    order = await get_order_by_id(session, order_id)
    if order is None:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return
    total = Decimal(str(order.total_amount))
    paid = Decimal(str(order.paid_amount))
    left = total - paid
    await state.update_data(order_id=order_id, order_left=str(left))
    await state.set_state(AdminInlinePaymentState.custom_amount)
    if callback.message:
        await callback.message.edit_text(f"Qisman to'lov summasini yuboring.\n\nBuyurtma ID: {order.id}\nQoldiq: {fmt(left)} so'm\nHolat: {uz_status(order.status)}")
    await callback.answer()


@router.message(AdminInlinePaymentState.custom_amount)
async def payment_custom_amount_message(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(message):
        return
    amount = parse_decimal(message.text or "")
    if amount is None:
        await message.answer("Iltimos, summani to'g'ri kiriting.")
        return
    data = await state.get_data()
    order_id = int(data["order_id"])
    order = await get_order_by_id(session, order_id)
    if order is None:
        await state.clear()
        await message.answer("Buyurtma topilmadi.")
        return
    total = Decimal(str(order.total_amount))
    paid = Decimal(str(order.paid_amount))
    left = total - paid
    if amount > left:
        await message.answer(f"To'lov qoldiqdan katta bo'lishi mumkin emas.\nQoldiq: {fmt(left)} so'm")
        return
    payment = await create_payment(session=session, order=order, amount=amount, payment_method="naqd")
    await state.clear()
    await message.answer(
        f"Qisman to'lov saqlandi.\n\nTo'lov ID: {payment.id}\nBuyurtma ID: {order.id}\nTo'lov summasi: {fmt(payment.amount)} so'm\nYangi holat: {uz_status(order.status)}\nJami to'langan: {fmt(order.paid_amount)} so'm",
        reply_markup=admin_back_home_keyboard(),
    )