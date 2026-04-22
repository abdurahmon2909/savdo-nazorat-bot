from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


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
        phone=phone.strip(),
        address=address.strip() if address else None,
        note=note.strip() if note else None,
        status=status,
    )
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    return customer


async def get_customer_by_id(session: AsyncSession, customer_id: int) -> Customer | None:
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    return result.scalar_one_or_none()


async def get_customer_by_phone(session: AsyncSession, phone: str) -> Customer | None:
    phone = normalize_phone(phone)
    result = await session.execute(select(Customer).where(Customer.phone == phone))
    return result.scalar_one_or_none()


async def get_customer_by_linked_telegram_id(
    session: AsyncSession,
    telegram_id: int,
) -> Customer | None:
    result = await session.execute(
        select(Customer).where(Customer.linked_telegram_id == telegram_id)
    )
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


async def auto_link_customer_by_phone(session: AsyncSession, phone: str, telegram_id: int):
    phone = normalize_phone(phone)

    # To'liq moslik
    customer = await get_customer_by_phone(session, phone)

    # Agar topilmasa, 9 xonali versiyasini tekshirish
    if not customer and phone.startswith('+998'):
        short_phone = phone[4:]  # +998901234567 -> 901234567
        customer = await get_customer_by_phone(session, short_phone)

    if not customer:
        return None

    if customer.linked_telegram_id != telegram_id:
        customer.linked_telegram_id = telegram_id
        await session.commit()
        await session.refresh(customer)

    return customer

    if customer.linked_telegram_id != telegram_id:
        customer.linked_telegram_id = telegram_id
        await session.commit()
        await session.refresh(customer)

    return customer


async def list_customers(session: AsyncSession, limit: int = 20) -> list[Customer]:
    result = await session.execute(
        select(Customer)
        .order_by(Customer.id.desc())
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
def normalize_phone(phone: str) -> str:
    """Telefon raqamni yagona formatga keltirish: +998xxxxxxxxx"""
    phone = re.sub(r'\D', '', phone)  # faqat raqamlar
    if phone.startswith('998') and len(phone) == 12:
        return f'+{phone}'
    if len(phone) == 9:
        return f'+998{phone}'
    if phone.startswith('+998') and len(phone) == 13:
        return phone
    return phone