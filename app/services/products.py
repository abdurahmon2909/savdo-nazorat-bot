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
        category=category.strip().lower() if category else None,
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


async def get_product_by_id(session: AsyncSession, product_id: int) -> Product | None:
    result = await session.execute(
        select(Product).where(Product.id == product_id)
    )
    return result.scalar_one_or_none()


async def get_product_by_name(session: AsyncSession, name: str) -> Product | None:
    result = await session.execute(
        select(Product).where(Product.name == name.strip())
    )
    return result.scalar_one_or_none()


async def update_product_price(
    session: AsyncSession,
    product: Product,
    new_price: Decimal,
) -> Product:
    product.sell_price = new_price
    await session.commit()
    await session.refresh(product)
    return product


async def add_product_stock(
    session: AsyncSession,
    product: Product,
    add_quantity: Decimal,
) -> Product:
    product.stock_quantity = Decimal(str(product.stock_quantity)) + add_quantity
    await session.commit()
    await session.refresh(product)
    return product


async def reduce_product_stock(
    session: AsyncSession,
    product: Product,
    quantity: Decimal,
) -> Product:
    product.stock_quantity = Decimal(str(product.stock_quantity)) - quantity
    await session.commit()
    await session.refresh(product)
    return product


async def set_product_stock(
    session: AsyncSession,
    product: Product,
    new_quantity: Decimal,
) -> Product:
    product.stock_quantity = new_quantity
    await session.commit()
    await session.refresh(product)
    return product


async def archive_product(
    session: AsyncSession,
    product: Product,
) -> Product:
    product.is_active = False
    await session.commit()
    await session.refresh(product)
    return product


async def list_products(session: AsyncSession, limit: int = 20) -> list[Product]:
    result = await session.execute(
        select(Product)
        .order_by(Product.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_active_categories(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(Product.category)
        .where(
            Product.is_active.is_(True),
            Product.stock_quantity > 0,
            Product.category.is_not(None),
        )
        .distinct()
        .order_by(Product.category.asc())
    )
    values = [row[0] for row in result.all() if row[0]]
    return values


async def list_products_by_category(
    session: AsyncSession,
    category: str,
    limit: int = 100,
) -> list[Product]:
    result = await session.execute(
        select(Product)
        .where(
            Product.is_active.is_(True),
            Product.stock_quantity > 0,
            Product.category == category.strip().lower(),
        )
        .order_by(Product.name.asc())
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