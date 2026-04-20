from datetime import datetime

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order


async def get_monthly_report(session: AsyncSession, year: int, month: int) -> dict:
    total_result = await session.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            extract("year", Order.created_at) == year,
            extract("month", Order.created_at) == month,
        )
    )
    total_amount = total_result.scalar() or 0

    paid_result = await session.execute(
        select(func.coalesce(func.sum(Order.paid_amount), 0)).where(
            extract("year", Order.created_at) == year,
            extract("month", Order.created_at) == month,
        )
    )
    paid_amount = paid_result.scalar() or 0

    unpaid_amount = float(total_amount) - float(paid_amount)

    return {
        "total": float(total_amount),
        "paid": float(paid_amount),
        "unpaid": float(unpaid_amount),
    }


def get_current_year_month():
    now = datetime.utcnow()
    return now.year, now.month