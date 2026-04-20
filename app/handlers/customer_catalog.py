from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.reply import cancel_keyboard, main_menu_keyboard
from app.services.customers import get_customer_by_linked_telegram_id, get_customer_by_phone
from app.services.order_requests import create_order_request
from app.services.products import get_product_by_id, list_products
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


async def build_products_text(session: AsyncSession) -> str:
    products = await list_products(session, limit=50)
    if not products:
        return ""

    lines = ["Mahsulot ID raqamini yuboring:\n"]
    for product in products:
        lines.append(
            f"{product.id}. {product.name} | "
            f"Narx: {format_number(product.sell_price)} so'm | "
            f"Qoldiq: {format_number(product.stock_quantity)} {product.unit}"
        )
    return "\n".join(lines)


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


@router.message(F.text == "🛍 Buyurtma berish")
async def start_customer_order(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    user = message.from_user
    if user is None:
        return

    db_user = await get_user_by_telegram_id(session, user.id)
    if db_user is None or not db_user.phone:
        await message.answer("Avval ro'yxatdan o'ting.")
        return

    customer = await get_customer_by_linked_telegram_id(session, user.id)
    if customer is None:
        customer = await get_customer_by_phone(session, db_user.phone)

    if customer is None:
        await message.answer(
            "Siz uchun mijoz kartasi topilmadi.\n"
            "Admin bilan bog'laning."
        )
        return

    products_text = await build_products_text(session)
    if not products_text:
        await message.answer("Hozircha mahsulotlar mavjud emas.")
        return

    await state.clear()
    await state.update_data(
        customer_id=customer.id,
        customer_name=customer.full_name,
        items=[],
    )
    await state.set_state(CreateCustomerOrderRequestState.product)
    await message.answer(products_text, reply_markup=cancel_keyboard())


@router.message(CreateCustomerOrderRequestState.product)
async def choose_customer_product(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    text = (message.text or "").strip()

    if text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Buyurtma bekor qilindi.", reply_markup=main_menu_keyboard())
        return

    if not text.isdigit():
        await message.answer("Iltimos, mahsulot ID raqamini yuboring.")
        return

    product = await get_product_by_id(session, int(text))
    if product is None:
        await message.answer("Bunday mahsulot topilmadi.")
        return

    if Decimal(str(product.stock_quantity)) <= 0:
        await message.answer("Bu mahsulot hozir omborda qolmagan.")
        return

    await state.update_data(
        current_product_id=product.id,
        current_product_name=product.name,
        current_product_price=str(product.sell_price),
        current_product_unit=product.unit,
        current_product_stock=str(product.stock_quantity),
    )
    await state.set_state(CreateCustomerOrderRequestState.quantity)
    await message.answer(
        f"Miqdorni yuboring.\n\n"
        f"Mahsulot: {product.name}\n"
        f"Mavjud qoldiq: {format_number(product.stock_quantity)} {product.unit}"
    )


@router.message(CreateCustomerOrderRequestState.quantity)
async def choose_customer_quantity(
    message: Message,
    state: FSMContext,
) -> None:
    text = (message.text or "").strip()

    if text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Buyurtma bekor qilindi.", reply_markup=main_menu_keyboard())
        return

    qty = parse_decimal(text)
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

    await state.update_data(items=items)
    await state.set_state(CreateCustomerOrderRequestState.add_more)
    await message.answer(
        f"{build_cart_text(items)}\n\n"
        "Yana mahsulot qo'shasizmi?\n"
        "Javob: ha yoki yo'q"
    )


@router.message(CreateCustomerOrderRequestState.add_more)
async def add_more_customer_products(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    text = (message.text or "").strip().lower()

    if text == "❌ bekor qilish":
        await state.clear()
        await message.answer("Buyurtma bekor qilindi.", reply_markup=main_menu_keyboard())
        return

    if text not in {"ha", "yo'q", "yoq"}:
        await message.answer("Iltimos, 'ha' yoki 'yo'q' deb yuboring.")
        return

    if text == "ha":
        products_text = await build_products_text(session)
        if not products_text:
            await state.clear()
            await message.answer("Mahsulotlar topilmadi.", reply_markup=main_menu_keyboard())
            return

        await state.set_state(CreateCustomerOrderRequestState.product)
        await message.answer(products_text)
        return

    await state.set_state(CreateCustomerOrderRequestState.payment_type)
    await message.answer(
        "To'lov turini tanlang:\n\n"
        "Javob: naqd yoki nasiya"
    )


@router.message(CreateCustomerOrderRequestState.payment_type)
async def choose_customer_payment_type(
    message: Message,
    state: FSMContext,
) -> None:
    payment_type = (message.text or "").strip().lower()

    if payment_type == "❌ bekor qilish":
        await state.clear()
        await message.answer("Buyurtma bekor qilindi.", reply_markup=main_menu_keyboard())
        return

    if payment_type not in {"naqd", "nasiya"}:
        await message.answer("Iltimos, faqat 'naqd' yoki 'nasiya' deb yuboring.")
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
    await message.answer(
        f"{build_cart_text(items)}\n\n"
        f"To'lov turi: {payment_type}\n\n"
        "Buyurtmani yuborasizmi?\n"
        "Javob: ha yoki yo'q"
    )


@router.message(CreateCustomerOrderRequestState.confirm)
async def confirm_customer_order(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    answer = (message.text or "").strip().lower()

    if answer not in {"ha", "yo'q", "yoq"}:
        await message.answer("Iltimos, 'ha' yoki 'yo'q' deb yuboring.")
        return

    if answer in {"yo'q", "yoq"}:
        await state.clear()
        await message.answer("Buyurtma bekor qilindi.", reply_markup=main_menu_keyboard())
        return

    data = await state.get_data()
    user = message.from_user
    if user is None:
        await state.clear()
        return

    request = await create_order_request(
        session=session,
        customer_id=int(data["customer_id"]),
        customer_telegram_id=user.id,
        items=data["items"],
        payment_type=data["payment_type"],
    )

    await state.clear()
    await message.answer(
        "Buyurtmangiz yuborildi.\n\n"
        f"So'rov ID: {request.id}\n"
        f"Holat: kutilmoqda\n"
        "Admin tasdiqlagach yakuniy hisoblanadi.",
        reply_markup=main_menu_keyboard(),
    )