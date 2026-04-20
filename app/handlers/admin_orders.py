from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.customers import list_customers
from app.services.products import list_products
from app.services.orders import create_order
from app.states.order import CreateOrderState

router = Router()


def is_admin(message: Message):
    return message.from_user.id in settings.admin_ids


@router.message(F.text == "🛒 Yangi savdo")
async def start_order(message: Message, state: FSMContext, session: AsyncSession):
    if not is_admin(message):
        return

    customers = await list_customers(session)

    text = "Mijozni tanlang:\n\n"
    for c in customers[:10]:
        text += f"{c.id}. {c.full_name}\n"

    await state.set_state(CreateOrderState.customer)
    await message.answer(text)


@router.message(CreateOrderState.customer)
async def choose_customer(message: Message, state: FSMContext):
    await state.update_data(customer_id=int(message.text))
    await state.set_state(CreateOrderState.product)

    await message.answer("Mahsulot ID kiriting")


@router.message(CreateOrderState.product)
async def choose_product(message: Message, state: FSMContext):
    await state.update_data(product_id=int(message.text))
    await state.set_state(CreateOrderState.quantity)

    await message.answer("Miqdorni kiriting")


@router.message(CreateOrderState.quantity)
async def choose_quantity(message: Message, state: FSMContext, session: AsyncSession):
    qty = Decimal(message.text)

    data = await state.get_data()

    item = {
        "product_id": data["product_id"],
        "quantity": qty,
        "price": 10000,  # MVP
    }

    await state.update_data(items=[item])

    await state.set_state(CreateOrderState.confirm)
    await message.answer("Tasdiqlaysizmi? (ha/yo'q)")


@router.message(CreateOrderState.confirm)
async def confirm_order(message: Message, state: FSMContext, session: AsyncSession):
    if message.text.lower() != "ha":
        await state.clear()
        await message.answer("Bekor qilindi")
        return

    data = await state.get_data()

    order = await create_order(
        session,
        customer_id=data["customer_id"],
        created_by=message.from_user.id,
        items=data["items"],
    )

    await state.clear()

    await message.answer(f"Buyurtma yaratildi. ID: {order.id}")