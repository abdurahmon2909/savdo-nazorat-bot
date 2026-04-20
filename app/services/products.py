from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


async def create_product(
    session: AsyncSession,
    name: str,
    category: str | None,
    unit: str,
    sell_price: Decimal,
    cost_price: Decimal | None,
    stock_quantity: Decimal,
) -> Product:
    product = Product(
        name=name.strip(),
        category=category.strip() if category else None,
        unit=unit.strip(),
        sell_price=sell_price,
        cost_price=cost_price,
        stock_quantity=stock_quantity,
        is_active=True,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


async def get_product_by_name(session: AsyncSession, name: str) -> Product | None:
    result = await session.execute(
        select(Product).where(Product.name == name.strip())
    )
    return result.scalar_one_or_none()


async def list_products(session: AsyncSession, limit: int = 20) -> list[Product]:
    result = await session.execute(
        select(Product)
        .order_by(Product.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def search_products(session: AsyncSession, query: str, limit: int = 20) -> list[Product]:
    q = query.strip()
    result = await session.execute(
        select(Product)
        .where(
            or_(
                Product.name.ilike(f"%{q}%"),
                Product.category.ilike(f"%{q}%"),
                Product.unit.ilike(f"%{q}%"),
            )
        )
        .order_by(Product.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())