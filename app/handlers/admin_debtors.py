from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.customers import get_customer_by_id, list_customers
from app.services.orders import get_order_by_id, list_customer_open_orders
from app.services.payments import create_payment
from app.states.payment_state import AddPaymentState

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


def format_number(value: Decimal | float | int | str) -> str:
    text = format(Decimal(str(value)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


@router.message(F.text == "💰 To'lov kiritish")
async def start_payment(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not is_admin(message):
        return

    customers = await list_customers(session, limit=20)
    if not customers:
        await message.answer("Hozircha mijozlar mavjud emas.")
        return

    lines = ["To'lov kiritish uchun mijoz ID raqamini yuboring:\n"]
    for customer in customers:
        lines.append(f"{customer.id}. {customer.full_name} — {customer.phone}")

    await state.clear()
    await state.set_state(AddPaymentState.customer)
    await message.answer("\n".join(lines))


@router.message(AddPaymentState.customer)
async def choose_payment_customer(
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

    customer = await get_customer_by_id(session, int(text))
    if customer is None:
        await message.answer("Bunday mijoz topilmadi.")
        return

    orders = await list_customer_open_orders(session, customer.id, limit=20)
    if not orders:
        await state.clear()
        await message.answer("Bu mijozning ochiq qarzi yo'q.")
        return

    lines = [f"{customer.full_name} uchun ochiq buyurtmalar:\n"]
    for order in orders:
        total = Decimal(str(order.total_amount))
        paid = Decimal(str(order.paid_amount))
        left = total - paid

        lines.append(
            f"Buyurtma ID: {order.id}\n"
            f"Jami: {format_number(total)} so'm\n"
            f"To'langan: {format_number(paid)} so'm\n"
            f"Qoldiq: {format_number(left)} so'm\n"
            f"Holat: {order.status}\n"
        )

    await state.update_data(
        customer_id=customer.id,
        customer_name=customer.full_name,
    )
    await state.set_state(AddPaymentState.order)
    await message.answer(
        "\n".join(lines) + "\nTo'lov kiritish uchun buyurtma ID raqamini yuboring."
    )


@router.message(AddPaymentState.order)
async def choose_payment_order(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if not is_admin(message):
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("Iltimos, buyurtma ID raqamini yuboring.")
        return

    order = await get_order_by_id(session, int(text))
    if order is None:
        await message.answer("Bunday buyurtma topilmadi.")
        return

    data = await state.get_data()
    if int(order.customer_id) != int(data["customer_id"]):
        await message.answer("Bu buyurtma tanlangan mijozga tegishli emas.")
        return

    if order.status == "paid":
        await state.clear()
        await message.answer("Bu buyurtma allaqachon to'liq yopilgan.")
        return

    total = Decimal(str(order.total_amount))
    paid = Decimal(str(order.paid_amount))
    left = total - paid

    await state.update_data(
        order_id=order.id,
        order_total=str(total),
        order_paid=str(paid),
        order_left=str(left),
    )
    await state.set_state(AddPaymentState.amount)
    await message.answer(
        f"To'lov summasini yuboring.\n\n"
        f"Buyurtma ID: {order.id}\n"
        f"Qoldiq: {format_number(left)} so'm"
    )


@router.message(AddPaymentState.amount)
async def choose_payment_amount(
    message: Message,
    state: FSMContext,
) -> None:
    if not is_admin(message):
        return

    amount = parse_decimal(message.text or "")
    if amount is None:
        await message.answer("Iltimos, to'lov summasini to'g'ri kiriting.")
        return

    data = await state.get_data()
    left = Decimal(str(data["order_left"]))

    if amount > left:
        await message.answer(
            f"To'lov qoldiqdan katta bo'lishi mumkin emas.\n"
            f"Mavjud qoldiq: {format_number(left)} so'm"
        )
        return

    await state.update_data(payment_amount=str(amount))
    await state.set_state(AddPaymentState.confirm)
    await message.answer(
        f"To'lovni tasdiqlaysizmi?\n\n"
        f"Mijoz: {data['customer_name']}\n"
        f"Buyurtma ID: {data['order_id']}\n"
        f"To'lov: {format_number(amount)} so'm\n\n"
        "Tasdiqlash uchun: ha\n"
        "Bekor qilish uchun: yo'q"
    )


@router.message(AddPaymentState.confirm)
async def confirm_payment(
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
        await message.answer("To'lov bekor qilindi.")
        return

    data = await state.get_data()
    order = await get_order_by_id(session, int(data["order_id"]))
    if order is None:
        await state.clear()
        await message.answer("Buyurtma topilmadi.")
        return

    payment_amount = Decimal(str(data["payment_amount"]))
    payment = await create_payment(
        session=session,
        order=order,
        amount=payment_amount,
        payment_method="naqd",
    )

    await state.clear()
    await message.answer(
        "To'lov muvaffaqiyatli saqlandi.\n\n"
        f"To'lov ID: {payment.id}\n"
        f"Buyurtma ID: {order.id}\n"
        f"To'lov summasi: {format_number(payment.amount)} so'm\n"
        f"Yangi holat: {order.status}\n"
        f"Jami to'langan: {format_number(order.paid_amount)} so'm"
    )