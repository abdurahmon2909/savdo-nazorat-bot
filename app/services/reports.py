from datetime import datetime
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.product import Product


async def get_monthly_report(session: AsyncSession, year: int, month: int) -> dict:
    # Jami savdo
    total_result = await session.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            extract("year", Order.created_at) == year,
            extract("month", Order.created_at) == month,
        )
    )
    total_amount = total_result.scalar() or 0

    # To'langan summa
    paid_result = await session.execute(
        select(func.coalesce(func.sum(Order.paid_amount), 0)).where(
            extract("year", Order.created_at) == year,
            extract("month", Order.created_at) == month,
        )
    )
    paid_amount = paid_result.scalar() or 0

    # Buyurtmalar soni
    order_count_result = await session.execute(
        select(func.count(Order.id)).where(
            extract("year", Order.created_at) == year,
            extract("month", Order.created_at) == month,
        )
    )
    order_count = order_count_result.scalar() or 0

    # SOF FOYDA: Sotilgan mahsulotlar * (sotuv_narxi - tannarx)
    profit_result = await session.execute(
        select(
            func.coalesce(
                func.sum(
                    OrderItem.quantity * (OrderItem.price - Product.cost_price)
                ), 0
            )
        )
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .where(
            extract("year", Order.created_at) == year,
            extract("month", Order.created_at) == month,
            Product.cost_price.is_not(None),
        )
    )
    profit = profit_result.scalar() or 0

    unpaid_amount = Decimal(str(total_amount)) - Decimal(str(paid_amount))

    return {
        "total": Decimal(str(total_amount)),
        "paid": Decimal(str(paid_amount)),
        "unpaid": unpaid_amount,
        "order_count": int(order_count),
        "profit": Decimal(str(profit)),  # <-- sof foyda
    }


async def get_monthly_top_products(
    session: AsyncSession,
    year: int,
    month: int,
    limit: int = 5,
) -> list[dict]:
    result = await session.execute(
        select(
            Product.name,
            func.coalesce(func.sum(OrderItem.quantity), 0).label("sold_qty"),
            func.coalesce(
                func.sum(OrderItem.quantity * (OrderItem.price - Product.cost_price)), 0
            ).label("profit"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            extract("year", Order.created_at) == year,
            extract("month", Order.created_at) == month,
        )
        .group_by(Product.name, Product.cost_price)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )

    return [
        {
            "name": row[0],
            "sold_qty": Decimal(str(row[1])),
            "profit": Decimal(str(row[2])) if row[2] else Decimal("0"),
        }
        for row in result.all()
    ]


def get_current_year_month() -> tuple[int, int]:
    now = datetime.utcnow()
    return now.year, now.month