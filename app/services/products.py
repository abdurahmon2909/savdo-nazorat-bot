from decimal import Decimal
from math import ceil

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
    result = await session.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def get_product_by_name(session: AsyncSession, name: str) -> Product | None:
    result = await session.execute(select(Product).where(Product.name == name.strip()))
    return result.scalar_one_or_none()


async def update_product_fields(
        session: AsyncSession,
        product: Product,
        *,
        name: str | None = None,
        category: str | None = None,
        unit: str | None = None,
        sell_price: Decimal | None = None,
        cost_price: Decimal | None = None,
        stock_quantity: Decimal | None = None,
) -> Product:
    if name is not None:
        product.name = name.strip()
    if category is not None:
        product.category = category.strip().lower() if category.strip() else None
    if unit is not None:
        product.unit = unit.strip()
    if sell_price is not None:
        product.sell_price = sell_price
    if cost_price is not None:
        product.cost_price = cost_price
    if stock_quantity is not None:
        product.stock_quantity = stock_quantity
    await session.commit()
    await session.refresh(product)
    return product


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


async def activate_product(
        session: AsyncSession,
        product: Product,
) -> Product:
    product.is_active = True
    await session.commit()
    await session.refresh(product)
    return product


async def list_products(session: AsyncSession, limit: int = 1000, offset: int = 0) -> list[Product]:
    result = await session.execute(
        select(Product)
        .order_by(Product.id.desc())
        .offset(offset)
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


async def list_all_categories(session: AsyncSession) -> list[str]:
    """Barcha kategoriyalar (qoldiq 0 bo'lsa ham)"""
    result = await session.execute(
        select(Product.category)
        .where(Product.category.is_not(None))
        .distinct()
        .order_by(Product.category.asc())
    )
    values = [row[0] for row in result.all() if row[0]]
    return values


async def list_products_by_category(
        session: AsyncSession,
        category: str,
        limit: int = 100,
        only_active: bool = True,
) -> list[Product]:
    conditions = [Product.category == category.strip().lower()]
    if only_active:
        conditions.append(Product.is_active.is_(True))
        conditions.append(Product.stock_quantity > 0)

    result = await session.execute(
        select(Product)
        .where(*conditions)
        .order_by(Product.name.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_products_by_category_paginated(
        session: AsyncSession,
        category: str,
        page: int = 1,
        limit: int = 10,
        only_active: bool = True,
) -> list[Product]:
    offset = (page - 1) * limit
    conditions = [Product.category == category.strip().lower()]
    if only_active:
        conditions.append(Product.is_active.is_(True))
        conditions.append(Product.stock_quantity > 0)

    result = await session.execute(
        select(Product)
        .where(*conditions)
        .order_by(Product.name.asc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_products_by_category(
        session: AsyncSession,
        category: str,
        only_active: bool = True,
) -> int:
    conditions = [Product.category == category.strip().lower()]
    if only_active:
        conditions.append(Product.is_active.is_(True))
        conditions.append(Product.stock_quantity > 0)

    result = await session.execute(
        select(Product).where(*conditions)
    )
    return len(result.scalars().all())


async def search_products(session: AsyncSession, query: str, limit: int = 100) -> list[Product]:
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


async def search_products_paginated(
        session: AsyncSession,
        query: str,
        page: int = 1,
        limit: int = 10,
) -> tuple[list[Product], int]:
    q = query.strip()
    offset = (page - 1) * limit

    # Mahsulotlarni olish
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
        .offset(offset)
        .limit(limit)
    )
    products = list(result.scalars().all())

    # Umumiy sonni olish
    count_result = await session.execute(
        select(Product)
        .where(
            or_(
                Product.name.ilike(f"%{q}%"),
                Product.category.ilike(f"%{q}%"),
                Product.unit.ilike(f"%{q}%"),
            )
        )
    )
    total = len(count_result.scalars().all())

    return products, total


async def get_low_stock_products(
        session: AsyncSession,
        threshold: Decimal,
        limit: int = 100,
) -> list[Product]:
    result = await session.execute(
        select(Product)
        .where(
            Product.is_active.is_(True),
            Product.stock_quantity <= threshold,
            Product.stock_quantity > 0,
        )
        .order_by(Product.stock_quantity.asc())
        .limit(limit)
    )
    return list(result.scalars().all())