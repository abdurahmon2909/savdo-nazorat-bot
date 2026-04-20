from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.keyboards.admin_order_inline import order_request_keyboard
from app.keyboards.catalog_inline import (
    cart_action_keyboard,
    categories_keyboard,
    confirm_order_keyboard,
    payment_type_keyboard,
    products_keyboard,
    quantity_keyboard,
)
from app.keyboards.reply import main_menu_keyboard
from app.services.customers import get_customer_by_linked_telegram_id, get_customer_by_phone
from app.services.order_requests import create_order_request
from app.services.products import (
    get_product_by_id,
    list_active_categories,
    list_products_by_category,
)
from app.services.users import get_user_by_telegram_id
from app.states.customer_order_state import CreateCustomerOrderRequestState

router = Router()


def parse_decimal(value: str) -> Decimal | None:
    try:
        number = Decimal((value or "").strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None

    if number <= 0:
        return None
    return number


def format_number(value: Decimal | float | int | str) -> str:
    text = format(Decimal(str(value)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def build_cart_text(items: list[dict]) -> str:
    if not items:
        return "Korzina bo'sh."

    lines = ["Korzina:\n"]
    total = Decimal("0")

    for index, item in enumerate(items, start=1):
        qty = Decimal(str(item["quantity"]))
        price = Decimal(str(item["price"]))
        line_total = qty * price
        total += line_total

        lines.append(
            f"{index}. {item['product_name']}\n"
            f"   Miqdor: {format_number(qty)} {item['product_unit']}\n"
            f"   Narx: {format_number(price)} so'm\n"
            f"   Jami: {format_number(line_total)} so'm\n"
        )

    lines.append(f"Umumiy jami: {format_number(total)} so'm")
    return "\n".join(lines)


async def get_customer_for_user(session: AsyncSession, telegram_id: int):
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is None or not user.phone:
        return None, "Avval ro'yxatdan o'ting."

    customer = await get_customer_by_linked_telegram_id(session, telegram_id)
    if customer is None:
        customer = await get_customer_by_phone(session, user.phone)

    if customer is None:
        return None, "Siz uchun mijoz kartasi topilmadi.\nAdmin bilan bog'laning."

    return customer, None


async def show_categories(callback_or_message, state: FSMContext, session: AsyncSession):
    categories = await list_active_categories(session)
    if not categories:
        if hasattr(callback_or_message, "answer"):
            await callback_or_message.answer("Hozircha mavjud mahsulotlar yo'q.")
        return False

    await state.set_state(CreateCustomerOrderRequestState.category)

    if isinstance(callback_or_message, Message):
        await callback_or_message.answer(
            "Kategoriya tanlang:",
            reply_markup=categories_keyboard(categories),
        )
    else:
        if callback_or_message.message:
            await callback_or_message.message.edit_text(
                "Kategoriya tanlang:",
                reply_markup=categories_keyboard(categories),
            )
        await callback_or_message.answer()
    return True


async def show_products_by_current_category(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> bool:
    data = await state.get_data()
    category = data.get("current_category")
    if not category:
        await callback.answer("Kategoriya topilmadi", show_alert=True)
        return False

    products = await list_products_by_category(session, category, limit=100)
    if not products:
        await callback.answer("Bu kategoriyada mahsulot yo'q", show_alert=True)
        return False

    product_rows = [
        {
            "id": product.id,
            "name": product.name,
            "price_text": format_number(product.sell_price),
        }
        for product in products
    ]

    await state.set_state(CreateCustomerOrderRequestState.product)

    if callback.message:
        await callback.message.edit_text(
            f"{category.title()} bo'limi:\nMahsulot tanlang:",
            reply_markup=products_keyboard(product_rows),
        )
    await callback.answer()
    return True


def append_item_to_cart(data: dict, qty: Decimal) -> list[dict]:
    items = data.get("items", []).copy()
    items.append(
        {
            "product_id": int(data["current_product_id"]),
            "product_name": data["current_product_name"],
            "product_unit": data["current_product_unit"],
            "quantity": str(qty),
            "price": str(data["current_product_price"]),
        }
    )
    return items


@router.message(F.text == "🛍 Buyurtma berish")
async def start_customer_order(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    user = message.from_user
    if user is None:
        return

    customer, error = await get_customer_for_user(session, user.id)
    if error:
        await message.answer(error)
        return

    await state.clear()
    await state.update_data(
        customer_id=customer.id,
        customer_name=customer.full_name,
        items=[],
    )
    await show_categories(message, state, session)


@router.callback_query(F.data == "catalog_cancel")
async def catalog_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message:
        await callback.message.edit_text("Buyurtma bekor qilindi.")
        await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "catalog_back_categories")
async def back_to_categories(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await show_categories(callback, state, session)


@router.callback_query(F.data.startswith("catalog_category:"))
async def choose_category(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    category = callback.data.split(":", 1)[1]
    await state.update_data(current_category=category)
    await show_products_by_current_category(callback, state, session)


@router.callback_query(F.data.startswith("catalog_product:"))
async def choose_product(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    product_id = int(callback.data.split(":", 1)[1])
    product = await get_product_by_id(session, product_id)

    if product is None:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return

    if Decimal(str(product.stock_quantity)) <= 0:
        await callback.answer("Bu mahsulot tugagan", show_alert=True)
        return

    await state.update_data(
        current_product_id=product.id,
        current_product_name=product.name,
        current_product_price=str(product.sell_price),
        current_product_unit=product.unit,
        current_product_stock=str(product.stock_quantity),
    )
    await state.set_state(CreateCustomerOrderRequestState.product)

    if callback.message:
        await callback.message.edit_text(
            f"Mahsulot: {product.name}\n"
            f"Narx: {format_number(product.sell_price)} so'm\n\n"
            "Miqdor tanlang:",
            reply_markup=quantity_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "catalog_back_products")
async def back_to_products(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await show_products_by_current_category(callback, state, session)


@router.callback_query(F.data.startswith("catalog_qty:"))
async def choose_quantity_preset(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    qty_value = callback.data.split(":", 1)[1]
    qty = parse_decimal(qty_value)

    if qty is None:
        await callback.answer("Miqdor noto'g'ri", show_alert=True)
        return

    data = await state.get_data()
    stock = Decimal(str(data["current_product_stock"]))

    if qty > stock:
        await callback.answer("Buncha mahsulot yo'q", show_alert=True)
        return

    items = append_item_to_cart(data, qty)

    await state.update_data(items=items)
    await state.set_state(CreateCustomerOrderRequestState.add_more)

    if callback.message:
        await callback.message.edit_text(
            build_cart_text(items),
            reply_markup=cart_action_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "catalog_qty_custom")
async def choose_quantity_custom(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(CreateCustomerOrderRequestState.quantity_custom)

    if callback.message:
        await callback.message.edit_text(
            "Kerakli miqdorni xabar qilib yuboring.\n\n"
            "Masalan: 3 yoki 12"
        )

    await callback.answer()


@router.message(CreateCustomerOrderRequestState.quantity_custom)
async def choose_quantity_custom_message(
    message: Message,
    state: FSMContext,
) -> None:
    qty = parse_decimal(message.text or "")
    if qty is None:
        await message.answer("Iltimos, miqdorni to'g'ri kiriting.")
        return

    data = await state.get_data()
    stock = Decimal(str(data["current_product_stock"]))

    if qty > stock:
        await message.answer(
            f"Buncha mahsulot yo'q.\n"
            f"Mavjud qoldiq: {format_number(stock)} {data['current_product_unit']}"
        )
        return

    items = append_item_to_cart(data, qty)

    await state.update_data(items=items)
    await state.set_state(CreateCustomerOrderRequestState.add_more)

    await message.answer(
        build_cart_text(items),
        reply_markup=cart_action_keyboard(),
    )


@router.callback_query(F.data == "catalog_add_more")
async def add_more_products(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await show_categories(callback, state, session)


@router.callback_query(F.data == "catalog_choose_payment")
async def choose_payment_step(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    items = data.get("items", [])

    if not items:
        await callback.answer("Korzina bo'sh", show_alert=True)
        return

    await state.set_state(CreateCustomerOrderRequestState.payment_type)

    if callback.message:
        await callback.message.edit_text(
            build_cart_text(items),
            reply_markup=payment_type_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data == "catalog_back_cart")
async def back_to_cart(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    items = data.get("items", [])

    if callback.message:
        await callback.message.edit_text(
            build_cart_text(items),
            reply_markup=cart_action_keyboard(),
        )
    await state.set_state(CreateCustomerOrderRequestState.add_more)
    await callback.answer()


@router.callback_query(F.data.startswith("catalog_payment:"))
async def choose_payment_type(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    payment_type = callback.data.split(":", 1)[1]

    if payment_type not in {"naqd", "nasiya"}:
        await callback.answer("Noto'g'ri to'lov turi", show_alert=True)
        return

    data = await state.get_data()
    items = data.get("items", [])

    total = Decimal("0")
    for item in items:
        total += Decimal(str(item["quantity"])) * Decimal(str(item["price"]))

    await state.update_data(
        payment_type=payment_type,
        total_amount=str(total),
    )
    await state.set_state(CreateCustomerOrderRequestState.confirm)

    if callback.message:
        await callback.message.edit_text(
            f"{build_cart_text(items)}\n\n"
            f"To'lov turi: {payment_type}",
            reply_markup=confirm_order_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data == "catalog_confirm_no")
async def cancel_confirm(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.message:
        await callback.message.edit_text("Buyurtma bekor qilindi.")
        await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "catalog_confirm_yes")
async def confirm_order_request(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    user = callback.from_user
    data = await state.get_data()

    request = await create_order_request(
        session=session,
        customer_id=int(data["customer_id"]),
        customer_telegram_id=user.id,
        items=data["items"],
        payment_type=data["payment_type"],
    )

    admin_text = (
        f"🆕 Yangi buyurtma so'rovi\n\n"
        f"So'rov ID: {request.id}\n"
        f"Mijoz: {data['customer_name']}\n"
        f"To'lov turi: {data['payment_type']}\n\n"
        f"{build_cart_text(data['items'])}"
    )

    for admin_id in settings.admin_ids:
        try:
            await callback.bot.send_message(
                admin_id,
                admin_text,
                reply_markup=order_request_keyboard(request.id),
            )
        except Exception:
            pass

    await state.clear()

    if callback.message:
        await callback.message.edit_text(
            "Buyurtmangiz yuborildi.\n\n"
            f"So'rov ID: {request.id}\n"
            "Holat: kutilmoqda\n"
            "Admin tasdiqlagach yakuniy hisoblanadi."
        )
        await callback.message.answer("Asosiy menyu:", reply_markup=main_menu_keyboard())

    await callback.answer("Buyurtma yuborildi")