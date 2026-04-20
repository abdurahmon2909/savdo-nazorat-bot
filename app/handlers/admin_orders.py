from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.customers import get_customer_by_id, list_customers
from app.services.orders import create_order
from app.services.products import get_product_by_id, list_products, reduce_product_stock
from app.states.order_state import CreateOrderState

router = Router()


def is_admin(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in settings.admin_ids)


def parse_decimal(value: str) -> Decimal | None:
    try:
        number = Decimal((value or "").strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None

    if number <= 0:
        return None
    return number


def format_number(value: Decimal | float | int) -> str:
    text = format(Decimal(str(value)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


@router.message(F.text == "🛒 Yangi savdo")
async def start_order(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(message):
        return

    customers = await list_customers(session, limit=20)

    if not customers:
        await message.answer(
            "Hozircha mijozlar mavjud emas.\n"
            "Avval mijoz qo'shing."
        )
        return

    lines = ["Mijoz ID raqamini yuboring:\n"]
    for customer in customers:
        lines.append(f"{customer.id}. {customer.full_name} — {customer.phone}")

    await state.clear()
    await state.set_state(CreateOrderState.customer)
    await message.answer("\n".join(lines))


@router.message(CreateOrderState.customer)
async def choose_customer(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not is_admin(message):
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Iltimos, mijoz ID raqamini yuboring.")
        return

    customer_id = int(text)
    customer = await get_customer_by_id(session, customer_id)

    if customer is None:
        await message.answer("Bunday mijoz topilmadi. Qaytadan urinib ko'ring.")
        return

    products = await list_products(session, limit=20)
    if not products:
        await message.answer(
            "Hozircha mahsulotlar mavjud emas.\n"
            "Avval mahsulot qo'shing."
        )
        await state.clear()
        return

    lines = ["Mahsulot ID raqamini yuboring:\n"]
    for product in products:
        lines.append(
            f"{product.id}. {product.name} | "
            f"Narx: {format_number(product.sell_price)} so'm | "
            f"Qoldiq: {format_number(product.stock_quantity)} {product.unit}"
        )

    await state.update_data(
        customer_id=customer.id,
        customer_name=customer.full_name,
    )
    await state.set_state(CreateOrderState.product)
    await message.answer("\n".join(lines))


@router.message(CreateOrderState.product)
async def choose_product(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not is_admin(message):
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Iltimos, mahsulot ID raqamini yuboring.")
        return

    product_id = int(text)
    product = await get_product_by_id(session, product_id)

    if product is None:
        await message.answer("Bunday mahsulot topilmadi. Qaytadan urinib ko'ring.")
        return

    if Decimal(str(product.stock_quantity)) <= 0:
        await message.answer("Bu mahsulot omborda qolmagan.")
        return

    await state.update_data(
        product_id=product.id,
        product_name=product.name,
        product_price=str(product.sell_price),
        product_unit=product.unit,
        product_stock=str(product.stock_quantity),
    )
    await state.set_state(CreateOrderState.quantity)
    await message.answer(
        f"Miqdorni yuboring.\n\n"
        f"Mahsulot: {product.name}\n"
        f"Mavjud qoldiq: {format_number(product.stock_quantity)} {product.unit}"
    )


@router.message(CreateOrderState.quantity)
async def choose_quantity(
    message: Message,
    state: FSMContext,
) -> None:
    if not is_admin(message):
        return

    qty = parse_decimal(message.text or "")
    if qty is None:
        await message.answer("Iltimos, miqdorni to'g'ri kiriting.")
        return

    data = await state.get_data()
    stock = Decimal(str(data["product_stock"]))

    if qty > stock:
        await message.answer(
            f"Buncha mahsulot yo'q.\n"
            f"Mavjud qoldiq: {format_number(stock)} {data['product_unit']}"
        )
        return

    await state.update_data(quantity=str(qty))
    await state.set_state(CreateOrderState.payment_type)
    await message.answer(
        "To'lov turini yuboring:\n\n"
        "1. naqd\n"
        "2. nasiya\n\n"
        "Javob: naqd yoki nasiya"
    )


@router.message(CreateOrderState.payment_type)
async def choose_payment_type(
    message: Message,
    state: FSMContext,
) -> None:
    if not is_admin(message):
        return

    payment_type = (message.text or "").strip().lower()
    if payment_type not in {"naqd", "nasiya"}:
        await message.answer("Iltimos, faqat 'naqd' yoki 'nasiya' deb yuboring.")
        return

    data = await state.get_data()

    qty = Decimal(str(data["quantity"]))
    price = Decimal(str(data["product_price"]))
    total = qty * price

    await state.update_data(
        payment_type=payment_type,
        total_amount=str(total),
        items=[
            {
                "product_id": data["product_id"],
                "quantity": str(qty),
                "price": str(price),
            }
        ],
    )
    await state.set_state(CreateOrderState.confirm)

    await message.answer(
        "Savdoni tasdiqlaysizmi?\n\n"
        f"Mijoz: {data['customer_name']}\n"
        f"Mahsulot: {data['product_name']}\n"
        f"Miqdor: {format_number(qty)} {data['product_unit']}\n"
        f"Narx: {format_number(price)} so'm\n"
        f"Jami: {format_number(total)} so'm\n"
        f"To'lov turi: {payment_type}\n\n"
        "Tasdiqlash uchun: ha\n"
        "Bekor qilish uchun: yo'q"
    )


@router.message(CreateOrderState.confirm)
async def confirm_order(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not is_admin(message):
        return

    answer = (message.text or "").strip().lower()
    if answer not in {"ha", "yo'q", "yoq"}:
        await message.answer("Iltimos, 'ha' yoki 'yo'q' deb yuboring.")
        return

    if answer in {"yo'q", "yoq"}:
        await state.clear()
        await message.answer("Savdo bekor qilindi.")
        return

    data = await state.get_data()

    product = await get_product_by_id(session, int(data["product_id"]))
    if product is None:
        await state.clear()
        await message.answer("Mahsulot topilmadi. Savdo bekor qilindi.")
        return

    qty = Decimal(str(data["quantity"]))
    current_stock = Decimal(str(product.stock_quantity))

    if qty > current_stock:
        await state.clear()
        await message.answer(
            "Savdoni yakunlab bo'lmadi.\n"
            "Mahsulot qoldig'i o'zgarib ketgan."
        )
        return

    order = await create_order(
        session=session,
        customer_id=int(data["customer_id"]),
        created_by=message.from_user.id,
        items=[
            {
                "product_id": int(data["product_id"]),
                "quantity": qty,
                "price": Decimal(str(data["product_price"])),
            }
        ],
        payment_type=data["payment_type"],
    )

    await reduce_product_stock(session, product, qty)
    await state.clear()

    await message.answer(
        "Savdo muvaffaqiyatli saqlandi.\n\n"
        f"Buyurtma ID: {order.id}\n"
        f"Mijoz: {data['customer_name']}\n"
        f"Mahsulot: {data['product_name']}\n"
        f"Miqdor: {format_number(qty)} {data['product_unit']}\n"
        f"Jami: {format_number(data['total_amount'])} so'm\n"
        f"To'lov turi: {data['payment_type']}\n"
        f"Holat: {order.status}"
    )