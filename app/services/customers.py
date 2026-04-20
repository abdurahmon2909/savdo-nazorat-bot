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
    result = await session.execute(
        select(Customer).where(Customer.phone == phone.strip())
    )
    return result.scalar_one_or_none()


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