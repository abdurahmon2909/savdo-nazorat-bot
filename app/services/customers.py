import re
from sqlalchemy import or_, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.customer import Customer
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment


def normalize_phone(phone: str) -> str:
    """Telefon raqamni yagona formatga keltirish: +998xxxxxxxxx"""
    phone = re.sub(r'\D', '', phone)
    if phone.startswith('998') and len(phone) == 12:
        return f'+{phone}'
    if len(phone) == 9:
        return f'+998{phone}'
    if phone.startswith('+998') and len(phone) == 13:
        return phone
    return phone


async def create_customer(
        session: AsyncSession,
        full_name: str,
        phone: str,
        address: str | None = None,
        note: str | None = None,
        status: str = "ishonchli",
) -> Customer:
    customer = Customer(
        full_name=full_name.strip(),
        phone=normalize_phone(phone),
        address=address.strip() if address else None,
        note=note.strip() if note else None,
        status=status,
    )
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer


async def get_customer_by_id(session: AsyncSession, customer_id: int) -> Customer | None:
    result = await session.execute(select(Customer).where(Customer.id == customer_id))
    return result.scalar_one_or_none()


async def get_customer_by_phone(session: AsyncSession, phone: str) -> Customer | None:
    phone = normalize_phone(phone)
    result = await session.execute(select(Customer).where(Customer.phone == phone))
    return result.scalar_one_or_none()


async def get_customer_by_linked_telegram_id(
        session: AsyncSession,
        telegram_id: int,
) -> Customer | None:
    result = await session.execute(select(Customer).where(Customer.linked_telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def link_customer_to_telegram(
        session: AsyncSession,
        customer: Customer,
        telegram_id: int,
) -> Customer:
    customer.linked_telegram_id = telegram_id
    await session.commit()
    await session.refresh(customer)
    return customer


async def auto_link_customer_by_phone(
        session: AsyncSession,
        phone: str,
        telegram_id: int,
) -> Customer | None:
    phone = normalize_phone(phone)
    customer = await get_customer_by_phone(session, phone)
    if customer is None:
        return None
    if customer.linked_telegram_id != telegram_id:
        customer.linked_telegram_id = telegram_id
        await session.commit()
        await session.refresh(customer)
    return customer


async def list_customers(session: AsyncSession, limit: int = 1000, offset: int = 0) -> list[Customer]:
    result = await session.execute(
        select(Customer)
        .order_by(Customer.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def search_customers(session: AsyncSession, query: str, limit: int = 20) -> list[Customer]:
    q = query.strip()
    result = await session.execute(
        select(Customer)
        .where(
            or_(
                Customer.full_name.ilike(f"%{q}%"),
                Customer.phone.ilike(f"%{q}%"),
            )
        )
        .order_by(Customer.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def update_customer_field(
        session: AsyncSession,
        customer_id: int,
        field: str,
        new_value: str | None,
) -> Customer | None:
    """Mijozning bir maydonini yangilash"""
    customer = await get_customer_by_id(session, customer_id)
    if not customer:
        return None

    if field == "full_name":
        customer.full_name = new_value.strip() if new_value else customer.full_name
    elif field == "phone":
        customer.phone = normalize_phone(new_value) if new_value else customer.phone
    elif field == "address":
        customer.address = new_value.strip() if new_value else None
    elif field == "note":
        customer.note = new_value.strip() if new_value else None
    elif field == "status":
        valid_statuses = ["ishonchli", "qarzdor", "bloklangan", "muntazam"]
        customer.status = new_value if new_value in valid_statuses else "ishonchli"
    else:
        return None

    await session.commit()
    await session.refresh(customer)
    return customer


async def delete_customer_by_id(session: AsyncSession, customer_id: int) -> bool:
    """Mijozni va unga tegishli barcha ma'lumotlarni o'chirish"""
    try:
        # Avval to'lovlarni o'chirish
        await session.execute(
            delete(Payment).where(Payment.order_id.in_(
                select(Order.id).where(Order.customer_id == customer_id)
            ))
        )
        # OrderItem larni o'chirish
        await session.execute(
            delete(OrderItem).where(OrderItem.order_id.in_(
                select(Order.id).where(Order.customer_id == customer_id)
            ))
        )
        # Buyurtmalarni o'chirish
        await session.execute(
            delete(Order).where(Order.customer_id == customer_id)
        )
        # Mijozni o'chirish
        result = await session.execute(
            delete(Customer).where(Customer.id == customer_id)
        )
        await session.commit()
        return result.rowcount > 0
    except IntegrityError:
        await session.rollback()
        return False