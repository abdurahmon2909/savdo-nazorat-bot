from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order_request import OrderRequest
from app.models.order_request_item import OrderRequestItem
from app.services.orders import create_order
from app.services.products import get_product_by_id, reduce_product_stock


async def create_order_request(
    session: AsyncSession,
    customer_id: int,
    customer_telegram_id: int,
    items: list[dict],
    payment_type: str,
) -> OrderRequest:
    total = sum(Decimal(str(item["quantity"])) * Decimal(str(item["price"])) for item in items)

    order_request = OrderRequest(
        customer_id=customer_id,
        customer_telegram_id=customer_telegram_id,
        total_amount=total,
        payment_type=payment_type,
        status="pending",
    )
    session.add(order_request)
    await session.flush()

    for item in items:
        session.add(
            OrderRequestItem(
                order_request_id=order_request.id,
                product_id=int(item["product_id"]),
                product_name=item["product_name"],
                product_unit=item["product_unit"],
                quantity=Decimal(str(item["quantity"])),
                price=Decimal(str(item["price"])),
            )
        )

    await session.commit()
    await session.refresh(order_request)
    return order_request


async def get_order_request_by_id(
    session: AsyncSession,
    request_id: int,
) -> OrderRequest | None:
    result = await session.execute(
        select(OrderRequest).where(OrderRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def list_pending_order_requests(
    session: AsyncSession,
    limit: int = 50,
) -> list[OrderRequest]:
    result = await session.execute(
        select(OrderRequest)
        .where(OrderRequest.status == "pending")
        .order_by(desc(OrderRequest.id))
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_customer_order_requests(
    session: AsyncSession,
    customer_telegram_id: int,
    limit: int = 20,
) -> list[OrderRequest]:
    result = await session.execute(
        select(OrderRequest)
        .where(OrderRequest.customer_telegram_id == customer_telegram_id)
        .order_by(desc(OrderRequest.id))
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_order_request_items(
    session: AsyncSession,
    request_id: int,
) -> list[OrderRequestItem]:
    result = await session.execute(
        select(OrderRequestItem)
        .where(OrderRequestItem.order_request_id == request_id)
        .order_by(OrderRequestItem.id)
    )
    return list(result.scalars().all())


async def approve_order_request(
    session: AsyncSession,
    order_request: OrderRequest,
    created_by: int,
):
    items = await list_order_request_items(session, order_request.id)

    if not items:
        return None, "Buyurtma ichida mahsulot yo'q."

    product_totals: dict[int, Decimal] = {}
    product_objects = {}

    for item in items:
        qty = Decimal(str(item.quantity))
        product_totals[item.product_id] = product_totals.get(item.product_id, Decimal("0")) + qty

    for product_id, total_qty in product_totals.items():
        product = await get_product_by_id(session, int(product_id))
        if product is None:
            return None, f"Mahsulot topilmadi: ID {product_id}"

        current_stock = Decimal(str(product.stock_quantity))
        if total_qty > current_stock:
            return None, f"Qoldiq yetarli emas: {product.name}"

        product_objects[product_id] = product

    order_items = [
        {
            "product_id": int(item.product_id),
            "quantity": Decimal(str(item.quantity)),
            "price": Decimal(str(item.price)),
        }
        for item in items
    ]

    order = await create_order(
        session=session,
        customer_id=int(order_request.customer_id),
        created_by=created_by,
        items=order_items,
        payment_type=order_request.payment_type,
    )

    for product_id, total_qty in product_totals.items():
        await reduce_product_stock(session, product_objects[product_id], total_qty)

    order_request.status = "approved"
    await session.commit()
    await session.refresh(order_request)

    return order, None


async def reject_order_request(
    session: AsyncSession,
    order_request: OrderRequest,
) -> OrderRequest:
    order_request.status = "rejected"
    await session.commit()
    await session.refresh(order_request)
    return order_request